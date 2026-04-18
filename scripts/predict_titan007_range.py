from __future__ import annotations

import argparse
import csv
import json
import sys
import time as time_module
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, fields
from datetime import date, datetime, time, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from upset_model.collectors.titan007_public import (
    build_asian_odds_url,
    build_1x2_data_url,
    build_over_under_url,
    build_schedule_url,
    build_snapshot_row,
    fetch_text,
    iter_match_dates,
    parse_asian_odds_snapshot,
    parse_europe_odds_snapshot,
    parse_over_under_snapshot,
    serialize_asian_snapshot,
    parse_schedule_matches,
    serialize_europe_snapshot,
    serialize_over_under_snapshot,
    serialize_schedule_matches,
)
from upset_model.betting_recommendations import (
    apply_betting_recommendation_fields,
    build_final_betting_rows,
)
from upset_model.config import (
    DEFAULT_TITAN007_TRAINING_COMPETITION_CODES,
    TITAN007_INTERIM_DIR,
    TITAN007_RAW_DIR,
    current_european_season_start_year,
    normalize_titan007_competition_filters,
    season_key,
)
from upset_model.draw_model import score_draw_rows
from upset_model.modeling import load_model_artifact, save_prediction_report, score_rows
from upset_model.standardize import snapshot_row_to_training_row

PREDICTION_CACHE_TTL_SECONDS = 15 * 60
SIDE_MARKET_FETCH_MAX_WORKERS = 8


@dataclass(frozen=True)
class PredictionWindow:
    fetch_start_date: str
    fetch_end_date: str
    start_datetime: datetime
    end_datetime: datetime


@dataclass(frozen=True)
class SideMarketFetchResult:
    schedule_id: int
    asian_snapshot: object | None
    asian_row: dict[str, object] | None
    over_under_snapshot: object | None
    over_under_row: dict[str, object] | None
    failures: list[dict[str, str]]


@dataclass(frozen=True)
class MatchFetchResult:
    schedule_id: int
    europe_snapshot: object | None
    europe_row: dict[str, object] | None
    asian_snapshot: object | None
    asian_row: dict[str, object] | None
    over_under_snapshot: object | None
    over_under_row: dict[str, object] | None
    failures: list[dict[str, str]]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Titan007 public pages for a date range and score upcoming matches with the trained upset model.",
    )
    parser.add_argument("--start-date", help="Inclusive start date in YYYY-MM-DD format.")
    parser.add_argument("--end-date", help="Inclusive end date in YYYY-MM-DD format.")
    parser.add_argument("--start-datetime", help="Inclusive start datetime in YYYY-MM-DD HH:MM format.")
    parser.add_argument("--end-datetime", help="Inclusive end datetime in YYYY-MM-DD HH:MM format.")
    parser.add_argument("--top-n", type=int, default=20, help="How many highest-upset-score matches to print.")
    parser.add_argument(
        "--skip-side-markets",
        action="store_true",
        help="Only fetch schedule pages and 1X2 odds, skipping Asian handicap and over/under pages for faster prediction.",
    )
    parser.add_argument(
        "--competitions",
        nargs="*",
        help="Optional competition filters. Supports existing codes and Titan007 competition names. Defaults to the active model training domain when available.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        help="Optional model artifact path. Defaults to the active baseline model.",
    )
    parser.add_argument(
        "--draw-model-path",
        type=Path,
        help="Optional draw-upset model artifact path. When provided, predictions also include draw_upset_probability.",
    )
    args = parser.parse_args(argv)
    _validate_window_args(parser, args)
    return args


def _validate_window_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if not args.start_date and not args.start_datetime:
        parser.error("one of --start-date or --start-datetime is required")
    if not args.end_date and not args.end_datetime:
        parser.error("one of --end-date or --end-datetime is required")
    if args.start_date and args.start_datetime:
        parser.error("use either --start-date or --start-datetime, not both")
    if args.end_date and args.end_datetime:
        parser.error("use either --end-date or --end-datetime, not both")


def _parse_prediction_datetime(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported datetime format: {value}")


def resolve_prediction_window(args: argparse.Namespace) -> PredictionWindow:
    if args.start_datetime:
        start_datetime = _parse_prediction_datetime(args.start_datetime)
    else:
        start_datetime = datetime.combine(date.fromisoformat(args.start_date), time(hour=0, minute=0))
    if args.end_datetime:
        end_datetime = _parse_prediction_datetime(args.end_datetime)
    else:
        end_datetime = datetime.combine(date.fromisoformat(args.end_date), time(hour=23, minute=59))
    if end_datetime < start_datetime:
        raise ValueError("end datetime must be on or after start datetime")
    return PredictionWindow(
        fetch_start_date=start_datetime.date().isoformat(),
        fetch_end_date=end_datetime.date().isoformat(),
        start_datetime=start_datetime,
        end_datetime=end_datetime,
    )


def _kickoff_datetime(match_date: str, kickoff_time: str) -> datetime:
    kickoff_value = kickoff_time.strip() if kickoff_time else "00:00"
    return datetime.strptime(f"{match_date} {kickoff_value}", "%Y-%m-%d %H:%M")


def _is_in_prediction_window(match_date: str, kickoff_time: str, window: PredictionWindow) -> bool:
    kickoff_datetime = _kickoff_datetime(match_date, kickoff_time)
    return window.start_datetime <= kickoff_datetime <= window.end_datetime


def _filter_structured_matches_by_window(
    rows: list[dict[str, object]],
    window: PredictionWindow,
) -> tuple[list[dict[str, object]], set[int]]:
    filtered_rows: list[dict[str, object]] = []
    schedule_ids: set[int] = set()
    for row in rows:
        match_date = str(row.get("match_date", ""))
        kickoff_time = str(row.get("kickoff_time", ""))
        if _is_in_prediction_window(match_date, kickoff_time, window):
            filtered_rows.append(row)
            schedule_id = row.get("schedule_id")
            if schedule_id is not None:
                schedule_ids.add(int(schedule_id))
    return filtered_rows, schedule_ids


def _filter_matches_by_window(matches: list, window: PredictionWindow) -> list:
    return [
        match
        for match in matches
        if _is_in_prediction_window(match.match_date, match.kickoff_time, window)
    ]


def _filter_snapshot_rows_by_window(rows: list[dict[str, str]], window: PredictionWindow) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if _is_in_prediction_window(row.get("match_date", ""), row.get("kickoff_time", ""), window)
    ]


def _filter_serialized_odds_by_schedule_ids(rows: list[dict[str, object]], schedule_ids: set[int]) -> list[dict[str, object]]:
    return [row for row in rows if int(row.get("schedule_id", -1)) in schedule_ids]


def _filter_predictions_by_window(predictions: list, window: PredictionWindow) -> list:
    return [
        prediction
        for prediction in predictions
        if _is_in_prediction_window(prediction.match_date, prediction.kickoff_time, window)
    ]


def _dedupe_matches_by_schedule_id(matches: list) -> list:
    deduped_matches = []
    seen_schedule_ids: set[int] = set()
    for match in sorted(matches, key=lambda item: (item.match_date, item.kickoff_time, item.schedule_id)):
        if match.schedule_id in seen_schedule_ids:
            continue
        seen_schedule_ids.add(match.schedule_id)
        deduped_matches.append(match)
    return deduped_matches


def save_csv(rows: list[dict[str, object]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return output_path

    fieldnames: list[str] = []
    seen_fieldnames: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key in seen_fieldnames:
                continue
            seen_fieldnames.add(key)
            fieldnames.append(key)

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return output_path


def save_prediction_csv(predictions: list, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[field.name for field in fields(predictions[0].__class__)])
        writer.writeheader()
        for prediction in predictions:
            writer.writerow(asdict(prediction))
    return output_path


def prediction_raw_cache_dir() -> Path:
    return TITAN007_RAW_DIR / "prediction_cache"


def _is_fresh_cache_file(path: Path, *, max_age_seconds: int) -> bool:
    if not path.exists():
        return False
    age_seconds = max(0.0, time_module.time() - path.stat().st_mtime)
    return age_seconds <= max_age_seconds


def load_or_fetch_text(
    output_path: Path,
    url: str,
    *,
    encoding: str,
    max_age_seconds: int = PREDICTION_CACHE_TTL_SECONDS,
) -> str:
    if _is_fresh_cache_file(output_path, max_age_seconds=max_age_seconds):
        return output_path.read_text(encoding="utf-8")
    return fetch_text(url, encoding=encoding, output_path=output_path)


def prediction_season_key(match_date: str) -> str:
    current_date = date.fromisoformat(match_date)
    start_year = current_european_season_start_year(today=current_date)
    return season_key(start_year)


def prediction_match_key(match_date: str, kickoff_time: str, competition_code: str, home_team: str, away_team: str) -> tuple[str, str, str, str, str]:
    return (match_date, kickoff_time, competition_code, home_team, away_team)


def _fetch_side_markets_for_match(match, *, raw_cache_dir: Path) -> SideMarketFetchResult:
    failures: list[dict[str, str]] = []
    asian_snapshot = None
    asian_row = None
    over_under_snapshot = None
    over_under_row = None

    asian_url = build_asian_odds_url(match.schedule_id)
    asian_path = raw_cache_dir / "asian" / f"{match.schedule_id}.html"
    try:
        asian_html = load_or_fetch_text(asian_path, asian_url, encoding="gb18030")
        asian_snapshot = parse_asian_odds_snapshot(asian_html, schedule_id=match.schedule_id)
        asian_row = serialize_asian_snapshot(asian_snapshot)
    except Exception as exc:
        failures.append(
            {
                "scope": "asian_odds",
                "match_date": match.match_date,
                "schedule_id": str(match.schedule_id),
                "url": asian_url,
                "error": str(exc),
            }
        )

    over_under_url = build_over_under_url(match.schedule_id)
    over_under_path = raw_cache_dir / "over_under" / f"{match.schedule_id}.html"
    try:
        over_under_html = load_or_fetch_text(over_under_path, over_under_url, encoding="gb18030")
        over_under_snapshot = parse_over_under_snapshot(over_under_html, schedule_id=match.schedule_id)
        over_under_row = serialize_over_under_snapshot(over_under_snapshot)
    except Exception as exc:
        failures.append(
            {
                "scope": "over_under_odds",
                "match_date": match.match_date,
                "schedule_id": str(match.schedule_id),
                "url": over_under_url,
                "error": str(exc),
            }
        )

    return SideMarketFetchResult(
        schedule_id=match.schedule_id,
        asian_snapshot=asian_snapshot,
        asian_row=asian_row,
        over_under_snapshot=over_under_snapshot,
        over_under_row=over_under_row,
        failures=failures,
    )


def _fetch_match_for_prediction(
    match,
    *,
    raw_cache_dir: Path,
) -> MatchFetchResult:
    failures: list[dict[str, str]] = []
    europe_snapshot = None
    europe_row = None
    euro_url = build_1x2_data_url(match.schedule_id)
    euro_path = raw_cache_dir / "1x2" / f"{match.schedule_id}.js"
    try:
        euro_js = load_or_fetch_text(euro_path, euro_url, encoding="utf-8")
        europe_snapshot = parse_europe_odds_snapshot(euro_js, schedule_id=match.schedule_id)
        europe_row = serialize_europe_snapshot(europe_snapshot)
    except Exception as exc:
        failures.append(
            {
                "scope": "europe_odds",
                "match_date": match.match_date,
                "schedule_id": str(match.schedule_id),
                "url": euro_url,
                "error": str(exc),
            }
        )
        return MatchFetchResult(
            schedule_id=match.schedule_id,
            europe_snapshot=None,
            europe_row=None,
            asian_snapshot=None,
            asian_row=None,
            over_under_snapshot=None,
            over_under_row=None,
            failures=failures,
        )

    side_market_result = _fetch_side_markets_for_match(match, raw_cache_dir=raw_cache_dir)
    failures.extend(side_market_result.failures)
    return MatchFetchResult(
        schedule_id=match.schedule_id,
        europe_snapshot=europe_snapshot,
        europe_row=europe_row,
        asian_snapshot=side_market_result.asian_snapshot,
        asian_row=side_market_result.asian_row,
        over_under_snapshot=side_market_result.over_under_snapshot,
        over_under_row=side_market_result.over_under_row,
        failures=failures,
    )


def _fetch_matches_for_prediction(
    matches: list,
    *,
    raw_cache_dir: Path,
    include_side_markets: bool,
) -> tuple[dict[int, MatchFetchResult], list[dict[str, str]]]:
    if not matches:
        return {}, []

    results_by_schedule_id: dict[int, MatchFetchResult] = {}
    failures: list[dict[str, str]] = []
    match_by_schedule_id = {match.schedule_id: match for match in matches}
    max_workers = min(SIDE_MARKET_FETCH_MAX_WORKERS, len(matches))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_schedule_id = {
            executor.submit(
                _fetch_match_for_prediction if include_side_markets else _fetch_europe_only_for_prediction,
                match,
                raw_cache_dir=raw_cache_dir,
            ): match.schedule_id
            for match in matches
        }
        for future in as_completed(future_to_schedule_id):
            schedule_id = future_to_schedule_id[future]
            match = match_by_schedule_id[schedule_id]
            try:
                result = future.result()
            except Exception as exc:
                failures.append(
                    {
                        "scope": "side_markets",
                        "match_date": match.match_date,
                        "schedule_id": str(match.schedule_id),
                        "url": "",
                        "error": str(exc),
                    }
                )
                continue
            results_by_schedule_id[schedule_id] = result
            failures.extend(result.failures)
    return results_by_schedule_id, failures


def _fetch_europe_only_for_prediction(
    match,
    *,
    raw_cache_dir: Path,
) -> MatchFetchResult:
    failures: list[dict[str, str]] = []
    euro_url = build_1x2_data_url(match.schedule_id)
    euro_path = raw_cache_dir / "1x2" / f"{match.schedule_id}.js"
    try:
        euro_js = load_or_fetch_text(euro_path, euro_url, encoding="utf-8")
        europe_snapshot = parse_europe_odds_snapshot(euro_js, schedule_id=match.schedule_id)
        europe_row = serialize_europe_snapshot(europe_snapshot)
    except Exception as exc:
        failures.append(
            {
                "scope": "europe_odds",
                "match_date": match.match_date,
                "schedule_id": str(match.schedule_id),
                "url": euro_url,
                "error": str(exc),
            }
        )
        return MatchFetchResult(
            schedule_id=match.schedule_id,
            europe_snapshot=None,
            europe_row=None,
            asian_snapshot=None,
            asian_row=None,
            over_under_snapshot=None,
            over_under_row=None,
            failures=failures,
        )
    return MatchFetchResult(
        schedule_id=match.schedule_id,
        europe_snapshot=europe_snapshot,
        europe_row=europe_row,
        asian_snapshot=None,
        asian_row=None,
        over_under_snapshot=None,
        over_under_row=None,
        failures=failures,
    )


def _resolve_requested_competition_scope(
    raw_values: list[str] | None,
    artifact=None,
) -> tuple[list[str], list[str], str]:
    if raw_values:
        competition_filters = list(raw_values)
        competition_filter_mode = "explicit"
    elif artifact is not None and getattr(artifact, "training_competition_scope", None) == "all":
        competition_filters = []
        competition_filter_mode = "model_training_domain_all"
    elif artifact is not None and getattr(artifact, "training_competitions", None):
        competition_filters = list(artifact.training_competitions or [])
        competition_filter_mode = "model_training_domain_explicit"
    else:
        competition_filters = list(DEFAULT_TITAN007_TRAINING_COMPETITION_CODES)
        competition_filter_mode = "default_training_domain"
    requested_competitions = sorted(normalize_titan007_competition_filters(competition_filters))
    return competition_filters, requested_competitions, competition_filter_mode


def rank_candidate_scores(prediction) -> list[tuple[str, float]]:
    candidate_scores = [
        ("home_upset_win", prediction.home_upset_probability),
        ("away_upset_win", prediction.away_upset_probability),
    ]
    if prediction.draw_upset_probability is not None:
        candidate_scores.append(("draw_upset", prediction.draw_upset_probability))
    return sorted(candidate_scores, key=lambda item: (item[1], item[0]), reverse=True)


def apply_combined_ranking_fields(predictions: list) -> None:
    for prediction in predictions:
        ranked_candidates = rank_candidate_scores(prediction)
        combined_label, combined_probability = ranked_candidates[0]
        prediction.combined_candidate_label = combined_label
        prediction.combined_candidate_probability = combined_probability
        if len(ranked_candidates) > 1:
            secondary_label, secondary_probability = ranked_candidates[1]
            prediction.secondary_candidate_label = secondary_label
            prediction.secondary_candidate_probability = secondary_probability
        else:
            prediction.secondary_candidate_label = None
            prediction.secondary_candidate_probability = None


def sort_combined_rankings(predictions: list) -> list:
    return sorted(
        predictions,
        key=lambda row: (
            row.combined_candidate_probability or 0.0,
            (row.combined_candidate_probability or 0.0) - (row.secondary_candidate_probability or 0.0),
            row.upset_score,
            row.draw_upset_probability or 0.0,
        ),
        reverse=True,
    )


def sort_draw_rankings(predictions: list) -> list:
    return sorted(
        predictions,
        key=lambda row: (
            row.draw_upset_probability if row.draw_upset_probability is not None else -1.0,
            row.combined_candidate_probability or 0.0,
            row.upset_score,
        ),
        reverse=True,
    )


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_run_outputs(
    *,
    interim_run_dir: Path,
    failures: list[dict[str, str]],
    run_id: str,
    args: argparse.Namespace,
    competition_filter_mode: str,
    fetch_market_profile: str,
    requested_competitions: list[str],
    selected_competitions: set[str],
    raw_run_dir: Path,
    structured_matches: list[dict[str, object]],
    snapshot_rows: list[dict[str, str]],
    scored_row_count: int,
    snapshot_csv_path: Path,
    report_path: Path | None = None,
    prediction_csv_path: Path | None = None,
    combined_ranking_csv_path: Path | None = None,
    draw_ranking_csv_path: Path | None = None,
    betting_ranking_csv_path: Path | None = None,
    betting_ranking_json_path: Path | None = None,
    prediction_window: PredictionWindow,
) -> None:
    summary = {
        "run_id": run_id,
        "start_date": prediction_window.fetch_start_date,
        "end_date": prediction_window.fetch_end_date,
        "start_datetime": prediction_window.start_datetime.strftime("%Y-%m-%d %H:%M"),
        "end_datetime": prediction_window.end_datetime.strftime("%Y-%m-%d %H:%M"),
        "competition_filter_mode": competition_filter_mode,
        "fetch_market_profile": fetch_market_profile,
        "requested_competitions": requested_competitions,
        "selected_competitions": sorted(selected_competitions),
        "scheduled_match_count": len(structured_matches),
        "snapshot_row_count": len(snapshot_rows),
        "scored_row_count": scored_row_count,
        "failure_count": len(failures),
        "raw_dir": str(raw_run_dir),
        "interim_dir": str(interim_run_dir),
        "prediction_report_path": str(report_path) if report_path else "",
        "prediction_csv_path": str(prediction_csv_path) if prediction_csv_path else "",
        "combined_ranking_csv_path": str(combined_ranking_csv_path) if combined_ranking_csv_path else "",
        "draw_ranking_csv_path": str(draw_ranking_csv_path) if draw_ranking_csv_path else "",
        "betting_ranking_csv_path": str(betting_ranking_csv_path) if betting_ranking_csv_path else "",
        "betting_ranking_json_path": str(betting_ranking_json_path) if betting_ranking_json_path else "",
        "snapshot_csv_path": str(snapshot_csv_path),
    }
    write_json(interim_run_dir / "run_summary.json", summary)
    write_json(interim_run_dir / "failures.json", failures)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    artifact = load_model_artifact(args.model_path)
    prediction_window = resolve_prediction_window(args)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_run_dir = prediction_raw_cache_dir()
    interim_run_dir = TITAN007_INTERIM_DIR / run_id
    interim_run_dir.mkdir(parents=True, exist_ok=True)
    competition_filters, requested_competitions, competition_filter_mode = _resolve_requested_competition_scope(
        args.competitions,
        artifact=artifact,
    )
    fetch_market_profile = "1x2_only" if args.skip_side_markets else "full_markets"
    selected_competitions: set[str] = set()

    structured_matches: list[dict[str, object]] = []
    structured_snapshots: list[dict[str, object]] = []
    structured_asian: list[dict[str, object]] = []
    structured_over_under: list[dict[str, object]] = []
    snapshot_rows: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []

    for match_date in iter_match_dates(prediction_window.fetch_start_date, prediction_window.fetch_end_date):
        schedule_url = build_schedule_url(match_date)
        schedule_path = raw_run_dir / "schedule" / f"{match_date}.html"
        try:
            schedule_html = load_or_fetch_text(schedule_path, schedule_url, encoding="gb18030")
            matches = parse_schedule_matches(
                schedule_html,
                match_date=match_date,
                source_url=schedule_url,
                allowed_competition_codes=competition_filters,
            )
            matches = _dedupe_matches_by_schedule_id(matches)
            matches = _filter_matches_by_window(matches, prediction_window)
            structured_matches.extend(serialize_schedule_matches(matches))
            selected_competitions.update(match.competition_code for match in matches)
        except Exception as exc:
            failures.append(
                {
                    "scope": "schedule",
                    "match_date": match_date,
                    "schedule_id": "",
                    "url": schedule_url,
                    "error": str(exc),
                }
            )
            continue

        fetched_matches, match_fetch_failures = _fetch_matches_for_prediction(
            matches,
            raw_cache_dir=raw_run_dir,
            include_side_markets=not args.skip_side_markets,
        )
        failures.extend(match_fetch_failures)

        for match in matches:
            fetched_match = fetched_matches.get(match.schedule_id)
            if fetched_match is None or fetched_match.europe_snapshot is None:
                continue
            if fetched_match.europe_row is not None:
                structured_snapshots.append(fetched_match.europe_row)
            if fetched_match.asian_row is not None:
                structured_asian.append(fetched_match.asian_row)
            if fetched_match.over_under_row is not None:
                structured_over_under.append(fetched_match.over_under_row)
            snapshot_rows.append(
                build_snapshot_row(
                    match,
                    fetched_match.europe_snapshot,
                    asian=fetched_match.asian_snapshot,
                    over_under=fetched_match.over_under_snapshot,
                )
            )

    structured_matches, filtered_schedule_ids = _filter_structured_matches_by_window(structured_matches, prediction_window)
    structured_snapshots = _filter_serialized_odds_by_schedule_ids(structured_snapshots, filtered_schedule_ids)
    structured_asian = _filter_serialized_odds_by_schedule_ids(structured_asian, filtered_schedule_ids)
    structured_over_under = _filter_serialized_odds_by_schedule_ids(structured_over_under, filtered_schedule_ids)
    snapshot_rows = _filter_snapshot_rows_by_window(snapshot_rows, prediction_window)
    selected_competitions = {str(row.get("competition_code", "")) for row in structured_matches if row.get("competition_code")}

    snapshot_csv_path = interim_run_dir / "snapshot_rows.csv"
    save_csv(snapshot_rows, snapshot_csv_path)
    write_json(interim_run_dir / "matches.json", structured_matches)
    write_json(interim_run_dir / "europe_odds.json", structured_snapshots)
    write_json(interim_run_dir / "asian_odds.json", structured_asian)
    write_json(interim_run_dir / "over_under_odds.json", structured_over_under)

    training_rows = []
    for snapshot_row in snapshot_rows:
        season = prediction_season_key(snapshot_row["match_date"])
        row = snapshot_row_to_training_row(
            snapshot_row,
            season_key=season,
            default_competition_code=snapshot_row["competition_code"],
        )
        if row is not None:
            training_rows.append(row)
        else:
            failures.append(
                {
                    "scope": "standardize",
                    "match_date": snapshot_row["match_date"],
                    "schedule_id": snapshot_row.get("source_schedule_id", ""),
                    "url": snapshot_row.get("source_euro_page_url", ""),
                    "error": "snapshot_row_to_training_row returned None",
                }
            )

    if not training_rows:
        write_run_outputs(
            interim_run_dir=interim_run_dir,
            failures=failures,
            run_id=run_id,
            args=args,
            competition_filter_mode=competition_filter_mode,
            fetch_market_profile=fetch_market_profile,
            requested_competitions=requested_competitions,
            selected_competitions=selected_competitions,
            raw_run_dir=raw_run_dir,
            structured_matches=structured_matches,
            snapshot_rows=snapshot_rows,
            scored_row_count=0,
            snapshot_csv_path=snapshot_csv_path,
            prediction_window=prediction_window,
        )
        print("No valid Titan007 snapshot rows were produced for the requested prediction window.")
        print(f"Schedule pages cached under: {raw_run_dir / 'schedule'}")
        print(f"Failure report saved to: {interim_run_dir / 'failures.json'}")
        return 1

    draw_artifact = None
    predictions = score_rows(training_rows, artifact)
    if args.draw_model_path:
        draw_artifact = load_model_artifact(args.draw_model_path)
        draw_predictions = score_draw_rows(training_rows, draw_artifact)
        draw_by_match = {
            prediction_match_key(
                prediction.match_date,
                prediction.kickoff_time,
                prediction.competition_code,
                prediction.home_team,
                prediction.away_team,
            ): prediction
            for prediction in draw_predictions
        }
        for prediction in predictions:
            draw_prediction = draw_by_match.get(
                prediction_match_key(
                    prediction.match_date,
                    prediction.kickoff_time,
                    prediction.competition_code,
                    prediction.home_team,
                    prediction.away_team,
                )
            )
            if draw_prediction is not None:
                prediction.draw_upset_probability = draw_prediction.draw_upset_probability
    predictions = _filter_predictions_by_window(predictions, prediction_window)
    if not predictions:
        write_run_outputs(
            interim_run_dir=interim_run_dir,
            failures=failures,
            run_id=run_id,
            args=args,
            competition_filter_mode=competition_filter_mode,
            fetch_market_profile=fetch_market_profile,
            requested_competitions=requested_competitions,
            selected_competitions=selected_competitions,
            raw_run_dir=raw_run_dir,
            structured_matches=structured_matches,
            snapshot_rows=snapshot_rows,
            scored_row_count=0,
            snapshot_csv_path=snapshot_csv_path,
            prediction_window=prediction_window,
        )
        print("No matches remained after applying the requested prediction window.")
        print(f"Failure report saved to {interim_run_dir / 'failures.json'}")
        return 1
    apply_combined_ranking_fields(predictions)
    apply_betting_recommendation_fields(
        predictions,
        main_artifact=artifact,
        draw_artifact=draw_artifact,
    )
    combined_rankings = sort_combined_rankings(predictions)
    draw_rankings = sort_draw_rankings(predictions) if args.draw_model_path else []
    final_betting_rows = build_final_betting_rows(predictions)
    top_predictions = combined_rankings[: args.top_n]
    report_path = save_prediction_report(predictions, output_path=interim_run_dir / "predictions.json")
    prediction_csv_path = save_prediction_csv(predictions, interim_run_dir / "predictions.csv")
    combined_ranking_csv_path = save_prediction_csv(combined_rankings, interim_run_dir / "combined_rankings.csv")
    draw_ranking_csv_path = None
    betting_ranking_csv_path = save_csv(final_betting_rows, interim_run_dir / "betting_recommendations.csv")
    betting_ranking_json_path = interim_run_dir / "betting_recommendations.json"
    write_json(betting_ranking_json_path, final_betting_rows)
    if draw_rankings:
        draw_ranking_csv_path = save_prediction_csv(draw_rankings, interim_run_dir / "draw_rankings.csv")

    write_run_outputs(
        interim_run_dir=interim_run_dir,
        failures=failures,
        run_id=run_id,
        args=args,
        competition_filter_mode=competition_filter_mode,
        fetch_market_profile=fetch_market_profile,
        requested_competitions=requested_competitions,
        selected_competitions=selected_competitions,
        raw_run_dir=raw_run_dir,
        structured_matches=structured_matches,
        snapshot_rows=snapshot_rows,
        scored_row_count=len(predictions),
        snapshot_csv_path=snapshot_csv_path,
        report_path=report_path,
        prediction_csv_path=prediction_csv_path,
        combined_ranking_csv_path=combined_ranking_csv_path,
        draw_ranking_csv_path=draw_ranking_csv_path,
        betting_ranking_csv_path=betting_ranking_csv_path,
        betting_ranking_json_path=betting_ranking_json_path,
        prediction_window=prediction_window,
    )

    print(
        f"Collected {len(structured_matches)} Titan007 matches, built {len(snapshot_rows)} snapshot rows, "
        f"scored {len(predictions)} matches. Fetch mode: {fetch_market_profile}.",
    )
    print("Combined leaderboard:")
    for prediction in top_predictions:
        print(
            f"{prediction.match_date} {prediction.competition_code} "
            f"{prediction.home_team} vs {prediction.away_team} "
            f"primary={prediction.combined_candidate_label}({(prediction.combined_candidate_probability or 0.0):.3f}) "
            f"{f'secondary={prediction.secondary_candidate_label}({prediction.secondary_candidate_probability:.3f}) ' if prediction.secondary_candidate_label and prediction.secondary_candidate_probability is not None else ''}"
            f"candidate={prediction.candidate_label}({prediction.candidate_probability:.3f}) "
            f"score={prediction.upset_score:.3f} "
            f"{f'draw={prediction.draw_upset_probability:.3f} ' if prediction.draw_upset_probability is not None else ''}"
            f"explain={prediction.explanation}",
        )
    if draw_rankings:
        print("Draw leaderboard:")
        for prediction in draw_rankings[: args.top_n]:
            print(
                f"{prediction.match_date} {prediction.competition_code} "
                f"{prediction.home_team} vs {prediction.away_team} "
                f"draw={prediction.draw_upset_probability:.3f} "
                f"combined={prediction.combined_candidate_label}({(prediction.combined_candidate_probability or 0.0):.3f})",
            )
    print("Betting recommendations:")
    if final_betting_rows:
        for row in final_betting_rows[: args.top_n]:
            print(
                f"{row['比赛时间']} | "
                f"{row['对阵']} | "
                f"{row['建议方向']} | "
                f"{row['原因']}",
            )
    else:
        print("No actionable betting recommendations (only `建议投注` 的 `强/中` 会被保留).")
    print(f"Prediction report saved to {report_path}")
    print(f"Prediction CSV saved to {prediction_csv_path}")
    print(f"Combined ranking CSV saved to {combined_ranking_csv_path}")
    if draw_ranking_csv_path:
        print(f"Draw ranking CSV saved to {draw_ranking_csv_path}")
    print(f"Betting recommendation CSV saved to {betting_ranking_csv_path}")
    print(f"Betting recommendation JSON saved to {betting_ranking_json_path}")
    print(f"Failure report saved to {interim_run_dir / 'failures.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
