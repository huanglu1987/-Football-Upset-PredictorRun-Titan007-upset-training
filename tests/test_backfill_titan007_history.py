import sys
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.backfill_titan007_history import expand_date_ranges, load_or_fetch_text, parse_args, partition_finished_dates
from upset_model.collectors.titan007_public import Titan007EuropeOddsSnapshot, Titan007ScheduledMatch


class BackfillTitan007HistoryTests(unittest.TestCase):
    def test_expand_date_ranges_merges_and_sorts_unique_dates(self) -> None:
        target_dates = expand_date_ranges(
            [
                "2026-04-10:2026-04-12",
                "2026-04-12:2026-04-13",
            ]
        )

        self.assertEqual(
            target_dates,
            [
                "2026-04-10",
                "2026-04-11",
                "2026-04-12",
                "2026-04-13",
            ],
        )

    def test_partition_finished_dates_splits_future_days(self) -> None:
        finished_dates, future_dates = partition_finished_dates(
            [
                "2026-04-10",
                "2026-04-13",
                "2026-04-14",
                "2026-04-20",
            ],
            today=date(2026, 4, 13),
        )

        self.assertEqual(finished_dates, ["2026-04-10", "2026-04-13"])
        self.assertEqual(future_dates, ["2026-04-14", "2026-04-20"])

    def test_load_or_fetch_text_prefers_existing_file(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "cached.html"
            path.write_text("cached-body", encoding="utf-8")
            with patch("scripts.backfill_titan007_history.fetch_text") as fetch_mock:
                body = load_or_fetch_text(path, "https://example.com/x", encoding="utf-8")

        self.assertEqual(body, "cached-body")
        fetch_mock.assert_not_called()

    def test_parse_args_accepts_skip_side_markets(self) -> None:
        args = parse_args(["--date-range", "2026-04-10:2026-04-12", "--skip-side-markets"])
        self.assertTrue(args.skip_side_markets)

    def test_main_skips_side_market_fetch_when_flag_enabled(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            raw_dir = root / "raw"
            interim_dir = root / "interim"
            output_path = interim_dir / "training_rows.csv"
            match = Titan007ScheduledMatch(
                schedule_id=123,
                competition_name="英超",
                competition_code="E0",
                match_date="2026-04-10",
                kickoff_time="20:00",
                home_team="Home",
                away_team="Away",
                full_time_result="H",
                home_goals=2,
                away_goals=1,
                asian_line_text=None,
                over_under_text=None,
                source_url="schedule-url",
            )
            euro_snapshot = Titan007EuropeOddsSnapshot(
                schedule_id=123,
                competition_name="英超",
                home_team="Home",
                away_team="Away",
                primary_company_name="Bet 365",
                primary_open_home_odds=2.2,
                primary_open_draw_odds=3.2,
                primary_open_away_odds=3.4,
                primary_close_home_odds=2.4,
                primary_close_draw_odds=3.1,
                primary_close_away_odds=3.2,
                avg_open_home_odds=2.25,
                avg_open_draw_odds=3.25,
                avg_open_away_odds=3.45,
                avg_close_home_odds=2.35,
                avg_close_draw_odds=3.15,
                avg_close_away_odds=3.25,
                source_page_url="page-url",
                source_data_url="data-url",
                company_count=1,
                companies=[],
            )

            def fake_load_or_fetch_text(output_path: Path, url: str, *, encoding: str) -> str:
                text_path = str(output_path)
                if "/asian/" in text_path or "/over_under/" in text_path:
                    raise AssertionError("skip-side-markets should not fetch side markets")
                return "payload"

            with (
                patch("scripts.backfill_titan007_history.load_or_fetch_text", side_effect=fake_load_or_fetch_text),
                patch("scripts.backfill_titan007_history.parse_schedule_matches", return_value=[match]),
                patch("scripts.backfill_titan007_history.serialize_schedule_matches", return_value=[{"schedule_id": 123}]),
                patch("scripts.backfill_titan007_history.parse_europe_odds_snapshot", return_value=euro_snapshot),
                patch("scripts.backfill_titan007_history.serialize_europe_snapshot", return_value={"schedule_id": 123}),
                patch(
                    "scripts.backfill_titan007_history.build_snapshot_row",
                    return_value={
                        "competition_code": "E0",
                        "competition_name": "英超",
                        "match_date": "2026-04-10",
                        "kickoff_time": "20:00",
                        "home_team": "Home",
                        "away_team": "Away",
                        "FTR": "H",
                        "FTHG": "2",
                        "FTAG": "1",
                        "B365H": "2.2",
                        "B365D": "3.2",
                        "B365A": "3.4",
                        "B365CH": "2.4",
                        "B365CD": "3.1",
                        "B365CA": "3.2",
                        "AvgH": "2.25",
                        "AvgD": "3.25",
                        "AvgA": "3.45",
                        "AvgCH": "2.35",
                        "AvgCD": "3.15",
                        "AvgCA": "3.25",
                        "data_completeness": "1x2_only",
                    },
                ),
                patch("scripts.backfill_titan007_history.snapshot_row_to_training_row", return_value=object()),
                patch("scripts.backfill_titan007_history.save_training_rows", return_value=output_path),
            ):
                exit_code = __import__("scripts.backfill_titan007_history", fromlist=["main"]).main(
                    [
                        "--date-range",
                        "2026-04-10:2026-04-10",
                        "--raw-dir",
                        str(raw_dir),
                        "--interim-dir",
                        str(interim_dir),
                        "--output-path",
                        str(output_path),
                        "--skip-side-markets",
                    ]
                )
                summary = (interim_dir / "run_summary.json").read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn('"skip_side_markets": true', summary.lower())


if __name__ == "__main__":
    unittest.main()
