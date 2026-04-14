import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from upset_model.collectors.titan007_public import (
    Titan007AsianOddsSnapshot,
    Titan007EuropeOddsSnapshot,
    Titan007OverUnderSnapshot,
    Titan007ScheduledMatch,
)
from upset_model.history_expander import load_history_window_groups, merge_training_row_files, recover_titan007_history_from_raw
from upset_model.standardize import load_training_rows, row_to_training_row, save_training_rows


def make_row(date: str, home: str, away: str, season_key: str):
    raw_row = {
        "Div": "E0",
        "Date": date,
        "Time": "15:00",
        "HomeTeam": home,
        "AwayTeam": away,
        "FTHG": "2",
        "FTAG": "1",
        "FTR": "H",
        "B365H": "3.20",
        "B365D": "3.20",
        "B365A": "2.15",
        "B365CH": "3.70",
        "B365CD": "3.25",
        "B365CA": "1.92",
        "AvgH": "3.20",
        "AvgD": "3.20",
        "AvgA": "2.15",
        "AvgCH": "3.70",
        "AvgCD": "3.25",
        "AvgCA": "1.92",
        "AHh": "0",
        "AHCh": "0",
        "B365AHH": "1.95",
        "B365AHA": "1.95",
        "B365CAHH": "1.92",
        "B365CAHA": "1.98",
        "B365>2.5": "1.90",
        "B365<2.5": "1.95",
        "B365C>2.5": "1.88",
        "B365C<2.5": "1.98",
    }
    row = row_to_training_row(raw_row, season_key=season_key)
    assert row is not None
    return row


class HistoryExpanderTests(unittest.TestCase):
    def test_load_history_window_groups_reads_json(self) -> None:
        payload = {
            "windows": [
                {
                    "label": "season_2324",
                    "note": "x",
                    "competitions": ["E0", "SP1"],
                    "date_ranges": ["2023-08-18:2023-08-21"],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "windows.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            groups = load_history_window_groups(path)

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].label, "season_2324")
        self.assertEqual(groups[0].date_ranges, ["2023-08-18:2023-08-21"])

    def test_merge_training_row_files_dedupes_identical_matches(self) -> None:
        row_a = make_row("01/08/2023", "A", "B", "2324")
        row_dup = make_row("01/08/2023", "A", "B", "2324")
        row_b = make_row("02/08/2023", "C", "D", "2324")

        with tempfile.TemporaryDirectory() as tmp_dir:
            first_path = Path(tmp_dir) / "first.csv"
            second_path = Path(tmp_dir) / "second.csv"
            output_path = Path(tmp_dir) / "merged.csv"
            save_training_rows([row_a], output_path=first_path)
            save_training_rows([row_dup, row_b], output_path=second_path)

            merged_path, merged_count = merge_training_row_files([first_path, second_path], output_path=output_path)
            merged_rows = load_training_rows(merged_path)

        self.assertEqual(merged_count, 2)
        self.assertEqual(len(merged_rows), 2)
        self.assertEqual({row.home_team for row in merged_rows}, {"A", "C"})

    def test_recover_titan007_history_from_raw_builds_rows(self) -> None:
        fake_match = Titan007ScheduledMatch(
            schedule_id=123,
            competition_name="Premier League",
            competition_code="E0",
            match_date="2026-04-10",
            kickoff_time="19:30",
            home_team="A",
            away_team="B",
            full_time_result="A",
            home_goals=1,
            away_goals=2,
            asian_line_text=None,
            over_under_text=None,
            source_url="schedule.html",
        )
        fake_euro = Titan007EuropeOddsSnapshot(
            schedule_id=123,
            competition_name="Premier League",
            home_team="A",
            away_team="B",
            primary_company_name="Bet 365",
            primary_open_home_odds=3.2,
            primary_open_draw_odds=3.2,
            primary_open_away_odds=2.15,
            primary_close_home_odds=3.7,
            primary_close_draw_odds=3.25,
            primary_close_away_odds=1.92,
            avg_open_home_odds=3.2,
            avg_open_draw_odds=3.2,
            avg_open_away_odds=2.15,
            avg_close_home_odds=3.7,
            avg_close_draw_odds=3.25,
            avg_close_away_odds=1.92,
            source_page_url="page",
            source_data_url="data",
            company_count=1,
            companies=[],
        )
        fake_asian = Titan007AsianOddsSnapshot(
            schedule_id=123,
            company_id=8,
            company_label="Bet365",
            open_home_odds=1.95,
            open_line=0.0,
            open_away_odds=1.95,
            close_home_odds=1.92,
            close_line=0.0,
            close_away_odds=1.98,
            source_url="asian",
        )
        fake_total = Titan007OverUnderSnapshot(
            schedule_id=123,
            company_id=8,
            company_label="Bet365",
            open_over_odds=1.9,
            open_line=2.5,
            open_under_odds=1.95,
            close_over_odds=1.88,
            close_line=2.5,
            close_under_odds=1.98,
            source_url="total",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            raw_dir = root / "raw"
            interim_dir = root / "interim"
            for subdir, suffix in (("schedule", "html"), ("1x2", "js"), ("asian", "html"), ("over_under", "html")):
                target = raw_dir / subdir
                target.mkdir(parents=True, exist_ok=True)
                filename = "2026-04-10.html" if subdir == "schedule" else f"123.{suffix}"
                (target / filename).write_text("stub", encoding="utf-8")
            output_path = root / "training_rows.csv"

            with patch("upset_model.history_expander.parse_schedule_matches", return_value=[fake_match]), patch(
                "upset_model.history_expander.parse_europe_odds_snapshot",
                return_value=fake_euro,
            ), patch(
                "upset_model.history_expander.parse_asian_odds_snapshot",
                return_value=fake_asian,
            ), patch(
                "upset_model.history_expander.parse_over_under_snapshot",
                return_value=fake_total,
            ):
                summary = recover_titan007_history_from_raw(
                    raw_run_dir=raw_dir,
                    interim_run_dir=interim_dir,
                    output_path=output_path,
                    allowed_competition_codes=["E0"],
                )

            rows = load_training_rows(output_path)

        self.assertEqual(summary["training_row_count"], 1)
        self.assertEqual(summary["failure_count"], 0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].home_team, "A")


if __name__ == "__main__":
    unittest.main()
