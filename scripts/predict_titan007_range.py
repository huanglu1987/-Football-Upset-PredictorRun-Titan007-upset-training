from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, fields
from datetime import date, datetime, timezone
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
    TITAN007_INTERIM_DIR,
    TITAN007_RAW_DIR,
    current_european_season_start_year,
    normalize_titan007_competition_filters,
    season_key,
)
from upset_model.draw_model import score_draw_rows
from upset_model.modeling import load_model_artifact, save_prediction_report, score_rows
from upset_model.standardize import snapshot_row_to_training_row


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Titan007 public pages for a date range and score upcoming matches with the trained upset model.",
    )
    parser.add_argument("--start-date", required=True, help="Inclusive start date in YYYY-MM-DD format.")
    parser.add_argument("--end-date", required=True, help="Inclusive end date in YYYY-MM-DD format.")
    parser.add_argument("--top-n", type=int, default=20, help="How many highest-upset-score matches to print.")
    parser.add_argument(
        "--competitions",
        nargs="*",
        help="Optional competition filters. Supports existing codes and Titan007 competition names. Defaults to all competitions.",
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
    return parser.parse_args(argv)


def save_csv(rows: list[dict[str, object]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return output_path

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
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


def prediction_season_key(match_date: str) -> str:
    current_date = date.fromisoformat(match_date)
    start_year = current_european_season_start_year(today=current_date)
    return season_key(start_year)


def prediction_match_key(match_date: str, kickoff_time: str, competition_code: str, home_team: str, away_team: str) -> tuple[str, str, str, str, str]:
    return (match_date, kickoff_time, competition_code, home_team, away_team)


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
) -> None:
    summary = {
        "run_id": run_id,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "competition_filter_mode": competition_filter_mode,
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
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_run_dir = TITAN007_RAW_DIR / run_id
    interim_run_dir = TITAN007_INTERIM_DIR / run_id
    interim_run_dir.mkdir(parents=True, exist_ok=True)
    requested_competitions = sorted(normalize_titan007_competition_filters(args.competitions))
    competition_filter_mode = "explicit" if requested_competitions else "all"
    selected_competitions: set[str] = set()

    structured_matches: list[dict[str, object]] = []
    structured_snapshots: list[dict[str, object]] = []
    structured_asian: list[dict[str, object]] = []
    structured_over_under: list[dict[str, object]] = []
    snapshot_rows: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []

    for match_date in iter_match_dates(args.start_date, args.end_date):
        schedule_url = build_schedule_url(match_date)
        schedule_path = raw_run_dir / "schedule" / f"{match_date}.html"
        try:
            schedule_html = fetch_text(schedule_url, encoding="gb18030", output_path=schedule_path)
            matches = parse_schedule_matches(
                schedule_html,
                match_date=match_date,
                source_url=schedule_url,
                allowed_competition_codes=args.competitions,
            )
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

        for match in matches:
            euro_url = build_1x2_data_url(match.schedule_id)
            euro_path = raw_run_dir / "1x2" / f"{match.schedule_id}.js"
            try:
                euro_js = fetch_text(euro_url, encoding="utf-8", output_path=euro_path)
                snapshot = parse_europe_odds_snapshot(euro_js, schedule_id=match.schedule_id)
                structured_snapshots.append(serialize_europe_snapshot(snapshot))
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
                continue

            asian_snapshot = None
            asian_url = build_asian_odds_url(match.schedule_id)
            asian_path = raw_run_dir / "asian" / f"{match.schedule_id}.html"
            try:
                asian_html = fetch_text(asian_url, encoding="gb18030", output_path=asian_path)
                asian_snapshot = parse_asian_odds_snapshot(asian_html, schedule_id=match.schedule_id)
                structured_asian.append(serialize_asian_snapshot(asian_snapshot))
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

            over_under_snapshot = None
            over_under_url = build_over_under_url(match.schedule_id)
            over_under_path = raw_run_dir / "over_under" / f"{match.schedule_id}.html"
            try:
                over_under_html = fetch_text(over_under_url, encoding="gb18030", output_path=over_under_path)
                over_under_snapshot = parse_over_under_snapshot(over_under_html, schedule_id=match.schedule_id)
                structured_over_under.append(serialize_over_under_snapshot(over_under_snapshot))
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

            snapshot_rows.append(build_snapshot_row(match, snapshot, asian=asian_snapshot, over_under=over_under_snapshot))

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
            requested_competitions=requested_competitions,
            selected_competitions=selected_competitions,
            raw_run_dir=raw_run_dir,
            structured_matches=structured_matches,
            snapshot_rows=snapshot_rows,
            scored_row_count=0,
            snapshot_csv_path=snapshot_csv_path,
        )
        print("No valid Titan007 snapshot rows were produced for the requested date range.")
        print(f"Schedule pages cached under: {raw_run_dir / 'schedule'}")
        print(f"Failure report saved to: {interim_run_dir / 'failures.json'}")
        return 1

    artifact = load_model_artifact(args.model_path)
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
    )

    print(
        f"Collected {len(structured_matches)} Titan007 matches, built {len(snapshot_rows)} snapshot rows, "
        f"scored {len(predictions)} matches.",
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
