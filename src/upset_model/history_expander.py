from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from upset_model.collectors.titan007_public import (
    build_snapshot_row,
    parse_asian_odds_snapshot,
    parse_europe_odds_snapshot,
    parse_over_under_snapshot,
    parse_schedule_matches,
    serialize_asian_snapshot,
    serialize_europe_snapshot,
    serialize_over_under_snapshot,
    serialize_schedule_matches,
)
from upset_model.config import current_european_season_start_year, normalize_titan007_competition_filters, season_key
from upset_model.standardize import TrainingRow, load_training_rows, save_training_rows
from upset_model.standardize import snapshot_row_to_training_row


@dataclass(frozen=True)
class HistoryWindowGroup:
    label: str
    date_ranges: list[str]
    competitions: list[str]
    note: str = ""


def load_history_window_groups(config_path: Path) -> list[HistoryWindowGroup]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    raw_groups = payload.get("windows", [])
    groups: list[HistoryWindowGroup] = []
    for index, raw_group in enumerate(raw_groups):
        label = str(raw_group.get("label", "")).strip()
        date_ranges = [str(item).strip() for item in raw_group.get("date_ranges", []) if str(item).strip()]
        competitions = [str(item).strip() for item in raw_group.get("competitions", []) if str(item).strip()]
        note = str(raw_group.get("note", "")).strip()
        if not label:
            raise ValueError(f"Window group {index} is missing a label")
        if not date_ranges:
            raise ValueError(f"Window group {label} is missing date_ranges")
        groups.append(
            HistoryWindowGroup(
                label=label,
                date_ranges=date_ranges,
                competitions=competitions,
                note=note,
            )
        )
    if not groups:
        raise ValueError(f"No history window groups found in {config_path}")
    return groups


def training_row_identity(row: TrainingRow) -> tuple[str, str, str, str, str, str]:
    return (
        row.season_key,
        row.match_date,
        row.kickoff_time,
        row.competition_code,
        row.home_team,
        row.away_team,
    )


def merge_training_row_files(input_paths: Iterable[Path], output_path: Path) -> tuple[Path, int]:
    deduped_rows: dict[tuple[str, str, str, str, str, str], TrainingRow] = {}
    for input_path in input_paths:
        for row in load_training_rows(input_path):
            deduped_rows[training_row_identity(row)] = row

    merged_rows = sorted(
        deduped_rows.values(),
        key=lambda row: (
            row.season_key,
            row.match_date,
            row.kickoff_time,
            row.competition_code,
            row.home_team,
            row.away_team,
        ),
    )
    save_training_rows(merged_rows, output_path=output_path)
    return output_path, len(merged_rows)


def recover_titan007_history_from_raw(
    *,
    raw_run_dir: Path,
    interim_run_dir: Path,
    output_path: Path,
    allowed_competition_codes: Iterable[str] | None = None,
) -> dict[str, object]:
    requested_competitions = sorted(normalize_titan007_competition_filters(list(allowed_competition_codes) if allowed_competition_codes else None))
    competition_filter_mode = "explicit" if requested_competitions else "all"
    selected_competitions: set[str] = set()
    schedule_dir = raw_run_dir / "schedule"
    interim_run_dir.mkdir(parents=True, exist_ok=True)

    structured_matches: list[dict[str, object]] = []
    structured_europe: list[dict[str, object]] = []
    structured_asian: list[dict[str, object]] = []
    structured_over_under: list[dict[str, object]] = []
    snapshot_rows: list[dict[str, str]] = []
    training_rows: list[TrainingRow] = []
    failures: list[dict[str, str]] = []

    for schedule_path in sorted(schedule_dir.glob("*.html")):
        match_date = schedule_path.stem
        try:
            schedule_html = schedule_path.read_text(encoding="utf-8")
            matches = parse_schedule_matches(
                schedule_html,
                match_date=match_date,
                source_url=str(schedule_path),
                allowed_competition_codes=allowed_competition_codes,
            )
            matches = _dedupe_matches_by_schedule_id(matches)
            structured_matches.extend(serialize_schedule_matches(matches))
            selected_competitions.update(match.competition_code for match in matches)
        except Exception as exc:
            failures.append(
                {
                    "scope": "schedule_recovery",
                    "match_date": match_date,
                    "schedule_id": "",
                    "url": str(schedule_path),
                    "error": str(exc),
                }
            )
            continue

        for match in matches:
            euro_path = raw_run_dir / "1x2" / f"{match.schedule_id}.js"
            if not euro_path.exists():
                failures.append(
                    {
                        "scope": "europe_odds_missing",
                        "match_date": match.match_date,
                        "schedule_id": str(match.schedule_id),
                        "url": str(euro_path),
                        "error": "Missing raw Europe odds file",
                    }
                )
                continue

            euro_snapshot = None
            asian_snapshot = None
            over_under_snapshot = None
            try:
                euro_snapshot = parse_europe_odds_snapshot(
                    euro_path.read_text(encoding="utf-8"),
                    schedule_id=match.schedule_id,
                )
                structured_europe.append(serialize_europe_snapshot(euro_snapshot))
            except Exception as exc:
                failures.append(
                    {
                        "scope": "europe_odds_recovery",
                        "match_date": match.match_date,
                        "schedule_id": str(match.schedule_id),
                        "url": str(euro_path),
                        "error": str(exc),
                    }
                )
                continue

            asian_path = raw_run_dir / "asian" / f"{match.schedule_id}.html"
            if asian_path.exists():
                try:
                    asian_snapshot = parse_asian_odds_snapshot(
                        asian_path.read_text(encoding="utf-8"),
                        schedule_id=match.schedule_id,
                    )
                    structured_asian.append(serialize_asian_snapshot(asian_snapshot))
                except Exception as exc:
                    failures.append(
                        {
                            "scope": "asian_odds_recovery",
                            "match_date": match.match_date,
                            "schedule_id": str(match.schedule_id),
                            "url": str(asian_path),
                            "error": str(exc),
                        }
                    )

            over_under_path = raw_run_dir / "over_under" / f"{match.schedule_id}.html"
            if over_under_path.exists():
                try:
                    over_under_snapshot = parse_over_under_snapshot(
                        over_under_path.read_text(encoding="utf-8"),
                        schedule_id=match.schedule_id,
                    )
                    structured_over_under.append(serialize_over_under_snapshot(over_under_snapshot))
                except Exception as exc:
                    failures.append(
                        {
                            "scope": "over_under_odds_recovery",
                            "match_date": match.match_date,
                            "schedule_id": str(match.schedule_id),
                            "url": str(over_under_path),
                            "error": str(exc),
                        }
                    )

            snapshot_row = build_snapshot_row(match, euro_snapshot, asian=asian_snapshot, over_under=over_under_snapshot)
            snapshot_rows.append(snapshot_row)
            training_row = snapshot_row_to_training_row(
                snapshot_row,
                season_key=_history_season_key(match.match_date),
                default_competition_code=match.competition_code,
                preserve_result=True,
            )
            if training_row is None:
                failures.append(
                    {
                        "scope": "standardize_recovery",
                        "match_date": match.match_date,
                        "schedule_id": str(match.schedule_id),
                        "url": str(euro_path),
                        "error": "snapshot_row_to_training_row returned None",
                    }
                )
                continue
            training_rows.append(training_row)

    rows_path = save_training_rows(training_rows, output_path=output_path)
    (interim_run_dir / "matches.json").write_text(json.dumps(structured_matches, ensure_ascii=False, indent=2), encoding="utf-8")
    (interim_run_dir / "europe_odds.json").write_text(json.dumps(structured_europe, ensure_ascii=False, indent=2), encoding="utf-8")
    (interim_run_dir / "asian_odds.json").write_text(json.dumps(structured_asian, ensure_ascii=False, indent=2), encoding="utf-8")
    (interim_run_dir / "over_under_odds.json").write_text(json.dumps(structured_over_under, ensure_ascii=False, indent=2), encoding="utf-8")
    (interim_run_dir / "snapshot_rows.json").write_text(json.dumps(snapshot_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (interim_run_dir / "failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "raw_dir": str(raw_run_dir),
        "interim_dir": str(interim_run_dir),
        "training_rows_path": str(rows_path),
        "scheduled_match_count": len(structured_matches),
        "snapshot_row_count": len(snapshot_rows),
        "training_row_count": len(training_rows),
        "failure_count": len(failures),
        "competition_filter_mode": competition_filter_mode,
        "requested_competitions": requested_competitions,
        "selected_competitions": sorted(selected_competitions),
    }
    (interim_run_dir / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _history_season_key(match_date: str) -> str:
    return season_key(current_european_season_start_year(today=date.fromisoformat(match_date)))


def _dedupe_matches_by_schedule_id(matches: list) -> list:
    deduped_matches = []
    seen_schedule_ids: set[int] = set()
    for match in sorted(matches, key=lambda item: (item.match_date, item.kickoff_time, item.schedule_id)):
        if match.schedule_id in seen_schedule_ids:
            continue
        seen_schedule_ids.add(match.schedule_id)
        deduped_matches.append(match)
    return deduped_matches
