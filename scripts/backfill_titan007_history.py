from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from upset_model.collectors.titan007_public import (
    build_asian_odds_url,
    build_finished_schedule_url,
    build_1x2_data_url,
    build_over_under_url,
    build_snapshot_row,
    fetch_text,
    iter_match_dates,
    parse_asian_odds_snapshot,
    parse_europe_odds_snapshot,
    parse_over_under_snapshot,
    parse_schedule_matches,
    serialize_asian_snapshot,
    serialize_europe_snapshot,
    serialize_over_under_snapshot,
    serialize_schedule_matches,
)
from upset_model.config import (
    TITAN007_INTERIM_DIR,
    TITAN007_RAW_DIR,
    current_european_season_start_year,
    normalize_titan007_competition_filters,
    season_key,
)
from upset_model.standardize import save_training_rows, snapshot_row_to_training_row


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill labeled Titan007 historical odds rows for one or more finished date ranges.",
    )
    parser.add_argument(
        "--date-range",
        dest="date_ranges",
        action="append",
        required=True,
        help="Inclusive range in START:END format, for example 2025-04-18:2025-04-20. Repeatable.",
    )
    parser.add_argument(
        "--competitions",
        nargs="*",
        help="Optional competition filters. Supports existing codes and Titan007 competition names. Defaults to all competitions.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        help="Optional output path for the normalized training rows CSV.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        help="Optional existing raw cache directory. When provided, existing files are reused and missing files are fetched into this directory.",
    )
    parser.add_argument(
        "--interim-dir",
        type=Path,
        help="Optional existing interim directory. When provided, summaries and JSON artifacts are written here.",
    )
    parser.add_argument(
        "--skip-side-markets",
        action="store_true",
        help="Only fetch finished schedules and 1X2 odds, skipping Asian handicap and over/under pages.",
    )
    return parser.parse_args(argv)


def expand_date_ranges(ranges: list[str]) -> list[str]:
    all_dates: set[str] = set()
    for raw_range in ranges:
        if ":" not in raw_range:
            raise ValueError(f"Invalid date range: {raw_range}")
        start_date, end_date = raw_range.split(":", 1)
        all_dates.update(iter_match_dates(start_date, end_date))
    return sorted(all_dates)


def partition_finished_dates(target_dates: list[str], *, today: date | None = None) -> tuple[list[str], list[str]]:
    cutoff = today or date.today()
    finished_dates: list[str] = []
    future_dates: list[str] = []
    for raw_date in target_dates:
        parsed = date.fromisoformat(raw_date)
        if parsed > cutoff:
            future_dates.append(raw_date)
            continue
        finished_dates.append(raw_date)
    return finished_dates, future_dates


def history_season_key(match_date: str) -> str:
    current_date = date.fromisoformat(match_date)
    return season_key(current_european_season_start_year(today=current_date))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_run_dir = args.raw_dir or (TITAN007_RAW_DIR / f"history_{run_id}")
    interim_run_dir = args.interim_dir or (TITAN007_INTERIM_DIR / f"history_{run_id}")
    interim_run_dir.mkdir(parents=True, exist_ok=True)
    requested_competitions = sorted(normalize_titan007_competition_filters(args.competitions))
    competition_filter_mode = "explicit" if requested_competitions else "all"
    selected_competitions: set[str] = set()
    requested_dates = expand_date_ranges(args.date_ranges)
    target_dates, skipped_future_dates = partition_finished_dates(requested_dates)

    structured_matches: list[dict[str, object]] = []
    structured_europe: list[dict[str, object]] = []
    structured_asian: list[dict[str, object]] = []
    structured_over_under: list[dict[str, object]] = []
    snapshot_rows: list[dict[str, str]] = []
    training_rows = []
    failures: list[dict[str, str]] = []

    for match_date in target_dates:
        schedule_url = build_finished_schedule_url(match_date)
        schedule_path = raw_run_dir / "schedule" / f"{match_date}.html"
        try:
            schedule_html = load_or_fetch_text(schedule_path, schedule_url, encoding="gb18030")
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
            euro_snapshot = None
            asian_snapshot = None
            over_under_snapshot = None

            euro_url = build_1x2_data_url(match.schedule_id)
            try:
                euro_js = load_or_fetch_text(raw_run_dir / "1x2" / f"{match.schedule_id}.js", euro_url, encoding="utf-8")
                euro_snapshot = parse_europe_odds_snapshot(euro_js, schedule_id=match.schedule_id)
                structured_europe.append(serialize_europe_snapshot(euro_snapshot))
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

            if not args.skip_side_markets:
                asian_url = build_asian_odds_url(match.schedule_id)
                try:
                    asian_html = load_or_fetch_text(raw_run_dir / "asian" / f"{match.schedule_id}.html", asian_url, encoding="gb18030")
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

                over_under_url = build_over_under_url(match.schedule_id)
                try:
                    over_under_html = load_or_fetch_text(
                        raw_run_dir / "over_under" / f"{match.schedule_id}.html",
                        over_under_url,
                        encoding="gb18030",
                    )
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

            snapshot_row = build_snapshot_row(match, euro_snapshot, asian=asian_snapshot, over_under=over_under_snapshot)
            snapshot_rows.append(snapshot_row)
            training_row = snapshot_row_to_training_row(
                snapshot_row,
                season_key=history_season_key(match.match_date),
                default_competition_code=match.competition_code,
                preserve_result=True,
            )
            if training_row is None:
                failures.append(
                    {
                        "scope": "standardize",
                        "match_date": match.match_date,
                        "schedule_id": str(match.schedule_id),
                        "url": euro_url,
                        "error": "snapshot_row_to_training_row returned None",
                    }
                )
                continue
            training_rows.append(training_row)

    output_path = args.output_path or (interim_run_dir / "training_rows.csv")
    rows_path = save_training_rows(training_rows, output_path=output_path)
    (interim_run_dir / "matches.json").write_text(json.dumps(structured_matches, ensure_ascii=False, indent=2), encoding="utf-8")
    (interim_run_dir / "europe_odds.json").write_text(json.dumps(structured_europe, ensure_ascii=False, indent=2), encoding="utf-8")
    (interim_run_dir / "asian_odds.json").write_text(json.dumps(structured_asian, ensure_ascii=False, indent=2), encoding="utf-8")
    (interim_run_dir / "over_under_odds.json").write_text(json.dumps(structured_over_under, ensure_ascii=False, indent=2), encoding="utf-8")
    (interim_run_dir / "snapshot_rows.json").write_text(json.dumps(snapshot_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (interim_run_dir / "failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "run_id": run_id,
        "date_ranges": args.date_ranges,
        "requested_date_count": len(requested_dates),
        "date_count": len(target_dates),
        "skipped_future_dates": skipped_future_dates,
        "competition_filter_mode": competition_filter_mode,
        "requested_competitions": requested_competitions,
        "selected_competitions": sorted(selected_competitions),
        "skip_side_markets": args.skip_side_markets,
        "scheduled_match_count": len(structured_matches),
        "snapshot_row_count": len(snapshot_rows),
        "training_row_count": len(training_rows),
        "failure_count": len(failures),
        "raw_dir": str(raw_run_dir),
        "interim_dir": str(interim_run_dir),
        "training_rows_path": str(rows_path),
    }
    (interim_run_dir / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"Backfilled {len(training_rows)} Titan007 historical rows from {len(target_dates)} dates "
        f"across {len(args.date_ranges)} range(s).",
    )
    if skipped_future_dates:
        print(f"Skipped {len(skipped_future_dates)} future date(s): {', '.join(skipped_future_dates)}")
    print(f"Training rows saved to {rows_path}")
    print(f"Failure report saved to {interim_run_dir / 'failures.json'}")
    return 0


def load_or_fetch_text(output_path: Path, url: str, *, encoding: str) -> str:
    if output_path.exists():
        return output_path.read_text(encoding="utf-8")
    return fetch_text(url, encoding=encoding, output_path=output_path)


if __name__ == "__main__":
    sys.exit(main())
