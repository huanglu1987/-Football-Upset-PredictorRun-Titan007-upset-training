import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import predict_titan007_range
from scripts.predict_titan007_range import (
    apply_combined_ranking_fields,
    resolve_prediction_window,
    save_csv,
    sort_combined_rankings,
    sort_draw_rankings,
)
from upset_model.betting_recommendations import (
    apply_betting_recommendation_fields,
    build_final_betting_rows,
    filter_actionable_betting_recommendations,
    sort_betting_recommendations,
)
from upset_model.modeling import PredictionRow, SoftmaxModelArtifact, load_model_artifact, save_model_artifact, score_rows, split_rows_by_latest_season, train_softmax_model
from upset_model.standardize import load_training_rows, row_to_training_row, save_training_rows


def make_row(date: str, result: str, open_home: str, open_draw: str, open_away: str, close_home: str, close_draw: str, close_away: str, season_key: str):
    raw_row = {
        "Div": "E0",
        "Date": date,
        "Time": "15:00",
        "HomeTeam": f"H{date}",
        "AwayTeam": f"A{date}",
        "FTHG": "2" if result == "H" else "0",
        "FTAG": "2" if result == "A" else "0",
        "FTR": result,
        "B365H": open_home,
        "B365D": open_draw,
        "B365A": open_away,
        "B365CH": close_home,
        "B365CD": close_draw,
        "B365CA": close_away,
        "AvgH": open_home,
        "AvgD": open_draw,
        "AvgA": open_away,
        "AvgCH": close_home,
        "AvgCD": close_draw,
        "AvgCA": close_away,
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


def make_artifact(
    *,
    labels: list[str],
    threshold: float,
    betting_policy: dict[str, object] | None = None,
    training_competition_scope: str | None = None,
    training_competitions: list[str] | None = None,
) -> SoftmaxModelArtifact:
    return SoftmaxModelArtifact(
        created_at_utc="2026-04-14T00:00:00+00:00",
        labels=labels,
        feature_names=["feature_a"],
        feature_means=[0.0],
        feature_stds=[1.0],
        weights=[[0.0, 0.0] for _ in labels],
        class_weights={label: 1.0 for label in labels},
        validation_season="2526",
        train_size=100,
        validation_size=50,
        metrics={},
        decision_threshold=threshold,
        decision_metrics={},
        betting_policy=betting_policy,
        training_competition_scope=training_competition_scope,
        training_competitions=training_competitions,
    )


class PredictionFlowTests(unittest.TestCase):
    def test_resolve_requested_competition_scope_defaults_to_training_domain(self) -> None:
        competition_filters, requested_competitions, competition_filter_mode = (
            predict_titan007_range._resolve_requested_competition_scope(None, artifact=None)
        )

        self.assertEqual(competition_filters, ["E0", "SP1", "D1", "I1", "F1"])
        self.assertCountEqual(requested_competitions, ["E0", "SP1", "D1", "I1", "F1"])
        self.assertEqual(competition_filter_mode, "default_training_domain")

    def test_resolve_requested_competition_scope_prefers_model_training_domain(self) -> None:
        artifact = make_artifact(
            labels=["home_upset_win", "away_upset_win", "non_upset"],
            threshold=0.40,
            training_competition_scope="explicit",
            training_competitions=["E0", "T7_U4E2D_U4E59"],
        )

        competition_filters, requested_competitions, competition_filter_mode = (
            predict_titan007_range._resolve_requested_competition_scope(None, artifact=artifact)
        )

        self.assertEqual(competition_filters, ["E0", "T7_U4E2D_U4E59"])
        self.assertCountEqual(requested_competitions, ["E0", "T7_U4E2D_U4E59"])
        self.assertEqual(competition_filter_mode, "model_training_domain_explicit")

    def test_resolve_requested_competition_scope_supports_model_wide_scope(self) -> None:
        artifact = make_artifact(
            labels=["home_upset_win", "away_upset_win", "non_upset"],
            threshold=0.40,
            training_competition_scope="all",
            training_competitions=[],
        )

        competition_filters, requested_competitions, competition_filter_mode = (
            predict_titan007_range._resolve_requested_competition_scope(None, artifact=artifact)
        )

        self.assertEqual(competition_filters, [])
        self.assertEqual(requested_competitions, [])
        self.assertEqual(competition_filter_mode, "model_training_domain_all")

    def test_resolve_prediction_window_accepts_datetime_window(self) -> None:
        args = predict_titan007_range.parse_args(
            [
                "--start-datetime",
                "2026-04-17 22:00",
                "--end-datetime",
                "2026-04-18 12:00",
            ]
        )

        window = resolve_prediction_window(args)

        self.assertEqual(window.fetch_start_date, "2026-04-17")
        self.assertEqual(window.fetch_end_date, "2026-04-18")
        self.assertEqual(window.start_datetime.strftime("%Y-%m-%d %H:%M"), "2026-04-17 22:00")
        self.assertEqual(window.end_datetime.strftime("%Y-%m-%d %H:%M"), "2026-04-18 12:00")

    def test_parse_args_accepts_skip_side_markets(self) -> None:
        args = predict_titan007_range.parse_args(
            [
                "--start-date",
                "2026-04-18",
                "--end-date",
                "2026-04-18",
                "--skip-side-markets",
            ]
        )

        self.assertTrue(args.skip_side_markets)

    def test_save_csv_handles_rows_with_different_side_market_fields(self) -> None:
        rows = [
            {
                "match_date": "2026-04-18",
                "home_team": "A",
                "away_team": "B",
            },
            {
                "match_date": "2026-04-18",
                "home_team": "C",
                "away_team": "D",
                "AHh": "0.25",
                "B365AHH": "1.95",
            },
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "snapshot_rows.csv"
            save_csv(rows, output_path)
            content = output_path.read_text(encoding="utf-8")

        self.assertIn("AHh", content)
        self.assertIn("B365AHH", content)

    def test_prediction_run_writes_failures_when_schedule_fetch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            raw_dir = root / "raw"
            interim_dir = root / "interim"
            with (
                patch("scripts.predict_titan007_range.TITAN007_RAW_DIR", raw_dir),
                patch("scripts.predict_titan007_range.TITAN007_INTERIM_DIR", interim_dir),
                patch("scripts.predict_titan007_range.iter_match_dates", return_value=["2026-04-17"]),
                patch("scripts.predict_titan007_range.fetch_text", side_effect=RuntimeError("SSL cert failed")),
            ):
                exit_code = predict_titan007_range.main(
                    [
                        "--start-date",
                        "2026-04-17",
                        "--end-date",
                        "2026-04-17",
                    ]
                )

            run_dirs = [path for path in interim_dir.iterdir() if path.is_dir()]
            self.assertEqual(len(run_dirs), 1)
            failures = json.loads((run_dirs[0] / "failures.json").read_text(encoding="utf-8"))
            summary = json.loads((run_dirs[0] / "run_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(failures[0]["scope"], "schedule")
        self.assertIn("SSL cert failed", failures[0]["error"])
        self.assertEqual(summary["scheduled_match_count"], 0)
        self.assertEqual(summary["snapshot_row_count"], 0)
        self.assertEqual(summary["scored_row_count"], 0)
        self.assertEqual(summary["failure_count"], 1)
        self.assertEqual(summary["prediction_report_path"], "")

    def test_prediction_run_skip_side_markets_avoids_side_market_fetches(self) -> None:
        prediction = PredictionRow(
            match_date="2026-04-17",
            kickoff_time="15:00",
            competition_code="E0",
            competition_name="Premier League",
            season_key="2526",
            home_team="A",
            away_team="B",
            home_upset_probability=0.41,
            away_upset_probability=0.18,
            non_upset_probability=0.41,
            upset_score=0.59,
            candidate_label="home_upset_win",
            candidate_probability=0.41,
            predicted_label="home_upset_win",
            actual_label="unknown",
            explanation="x",
        )
        artifact = make_artifact(labels=["home_upset_win", "away_upset_win", "non_upset"], threshold=0.40)

        def fake_fetch_text(url: str, encoding: str, output_path: Path):
            if "Next_" in url:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("schedule", encoding="utf-8")
                return "schedule"
            if "1x2d.titan007.com" in url:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("europe", encoding="utf-8")
                return "europe"
            raise AssertionError(f"unexpected side-market fetch: {url}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            raw_dir = root / "raw"
            interim_dir = root / "interim"
            with (
                patch("scripts.predict_titan007_range.TITAN007_RAW_DIR", raw_dir),
                patch("scripts.predict_titan007_range.TITAN007_INTERIM_DIR", interim_dir),
                patch("scripts.predict_titan007_range.iter_match_dates", return_value=["2026-04-17"]),
                patch("scripts.predict_titan007_range.load_model_artifact", return_value=artifact),
                patch("scripts.predict_titan007_range.fetch_text", side_effect=fake_fetch_text),
                patch(
                    "scripts.predict_titan007_range.parse_schedule_matches",
                    return_value=[
                        SimpleNamespace(
                            schedule_id=123,
                            competition_code="E0",
                            match_date="2026-04-17",
                            kickoff_time="15:00",
                            home_team="A",
                            away_team="B",
                        )
                    ],
                ),
                patch(
                    "scripts.predict_titan007_range.serialize_schedule_matches",
                    return_value=[
                        {
                            "match_date": "2026-04-17",
                            "kickoff_time": "15:00",
                            "competition_code": "E0",
                            "competition_name": "Premier League",
                            "home_team": "A",
                            "away_team": "B",
                            "schedule_id": 123,
                        }
                    ],
                ),
                patch("scripts.predict_titan007_range.parse_europe_odds_snapshot", return_value={"schedule_id": 123}),
                patch("scripts.predict_titan007_range.serialize_europe_snapshot", return_value={"schedule_id": 123}),
                patch(
                    "scripts.predict_titan007_range.build_snapshot_row",
                    return_value={
                        "match_date": "2026-04-17",
                        "kickoff_time": "15:00",
                        "competition_code": "E0",
                        "competition_name": "Premier League",
                        "home_team": "A",
                        "away_team": "B",
                        "source_schedule_id": "123",
                        "source_euro_page_url": "https://1x2d.titan007.com/123.js",
                        "B365H": "2.10",
                        "B365D": "3.20",
                        "B365A": "3.40",
                        "B365CH": "2.00",
                        "B365CD": "3.10",
                        "B365CA": "3.80",
                        "AvgH": "2.10",
                        "AvgD": "3.20",
                        "AvgA": "3.40",
                        "AvgCH": "2.00",
                        "AvgCD": "3.10",
                        "AvgCA": "3.80",
                    },
                ),
                patch("scripts.predict_titan007_range.score_rows", return_value=[prediction]),
            ):
                exit_code = predict_titan007_range.main(
                    [
                        "--start-date",
                        "2026-04-17",
                        "--end-date",
                        "2026-04-17",
                        "--skip-side-markets",
                    ]
                )

            run_dirs = [path for path in interim_dir.iterdir() if path.is_dir()]
            self.assertEqual(len(run_dirs), 1)
            summary = json.loads((run_dirs[0] / "run_summary.json").read_text(encoding="utf-8"))
            asian_rows = json.loads((run_dirs[0] / "asian_odds.json").read_text(encoding="utf-8"))
            over_under_rows = json.loads((run_dirs[0] / "over_under_odds.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(summary["fetch_market_profile"], "1x2_only")
        self.assertEqual(asian_rows, [])
        self.assertEqual(over_under_rows, [])

    def test_prediction_run_full_markets_fetches_side_markets(self) -> None:
        prediction = PredictionRow(
            match_date="2026-04-17",
            kickoff_time="15:00",
            competition_code="E0",
            competition_name="Premier League",
            season_key="2526",
            home_team="A",
            away_team="B",
            home_upset_probability=0.41,
            away_upset_probability=0.18,
            non_upset_probability=0.41,
            upset_score=0.59,
            candidate_label="home_upset_win",
            candidate_probability=0.41,
            predicted_label="home_upset_win",
            actual_label="unknown",
            explanation="x",
        )
        artifact = make_artifact(labels=["home_upset_win", "away_upset_win", "non_upset"], threshold=0.40)
        built_snapshot_args: dict[str, object] = {}

        def fake_fetch_text(url: str, encoding: str, output_path: Path):
            if "Next_" in url:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("schedule", encoding="utf-8")
                return "schedule"
            if "1x2d.titan007.com" in url:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("europe", encoding="utf-8")
                return "europe"
            if "AsianOdds_n.aspx" in url:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("asian", encoding="utf-8")
                return "asian"
            if "OverDown_n.aspx" in url:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("over-under", encoding="utf-8")
                return "over-under"
            raise AssertionError(f"unexpected fetch: {url}")

        def fake_build_snapshot_row(match, snapshot, *, asian=None, over_under=None):
            built_snapshot_args["asian"] = asian
            built_snapshot_args["over_under"] = over_under
            return {
                "match_date": "2026-04-17",
                "kickoff_time": "15:00",
                "competition_code": "E0",
                "competition_name": "Premier League",
                "home_team": "A",
                "away_team": "B",
                "source_schedule_id": "123",
                "source_euro_page_url": "https://1x2d.titan007.com/123.js",
                "B365H": "2.10",
                "B365D": "3.20",
                "B365A": "3.40",
                "B365CH": "2.00",
                "B365CD": "3.10",
                "B365CA": "3.80",
                "AvgH": "2.10",
                "AvgD": "3.20",
                "AvgA": "3.40",
                "AvgCH": "2.00",
                "AvgCD": "3.10",
                "AvgCA": "3.80",
            }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            raw_dir = root / "raw"
            interim_dir = root / "interim"
            with (
                patch("scripts.predict_titan007_range.TITAN007_RAW_DIR", raw_dir),
                patch("scripts.predict_titan007_range.TITAN007_INTERIM_DIR", interim_dir),
                patch("scripts.predict_titan007_range.iter_match_dates", return_value=["2026-04-17"]),
                patch("scripts.predict_titan007_range.load_model_artifact", return_value=artifact),
                patch("scripts.predict_titan007_range.fetch_text", side_effect=fake_fetch_text),
                patch(
                    "scripts.predict_titan007_range.parse_schedule_matches",
                    return_value=[
                        SimpleNamespace(
                            schedule_id=123,
                            competition_code="E0",
                            match_date="2026-04-17",
                            kickoff_time="15:00",
                            home_team="A",
                            away_team="B",
                        )
                    ],
                ),
                patch(
                    "scripts.predict_titan007_range.serialize_schedule_matches",
                    return_value=[
                        {
                            "match_date": "2026-04-17",
                            "kickoff_time": "15:00",
                            "competition_code": "E0",
                            "competition_name": "Premier League",
                            "home_team": "A",
                            "away_team": "B",
                            "schedule_id": 123,
                        }
                    ],
                ),
                patch("scripts.predict_titan007_range.parse_europe_odds_snapshot", return_value={"schedule_id": 123}),
                patch("scripts.predict_titan007_range.serialize_europe_snapshot", return_value={"schedule_id": 123}),
                patch("scripts.predict_titan007_range.parse_asian_odds_snapshot", return_value={"schedule_id": 123, "market": "asian"}),
                patch("scripts.predict_titan007_range.serialize_asian_snapshot", return_value={"schedule_id": 123, "market": "asian"}),
                patch(
                    "scripts.predict_titan007_range.parse_over_under_snapshot",
                    return_value={"schedule_id": 123, "market": "over_under"},
                ),
                patch(
                    "scripts.predict_titan007_range.serialize_over_under_snapshot",
                    return_value={"schedule_id": 123, "market": "over_under"},
                ),
                patch("scripts.predict_titan007_range.build_snapshot_row", side_effect=fake_build_snapshot_row),
                patch("scripts.predict_titan007_range.score_rows", return_value=[prediction]),
            ):
                exit_code = predict_titan007_range.main(
                    [
                        "--start-date",
                        "2026-04-17",
                        "--end-date",
                        "2026-04-17",
                    ]
                )

            run_dirs = [path for path in interim_dir.iterdir() if path.is_dir()]
            self.assertEqual(len(run_dirs), 1)
            summary = json.loads((run_dirs[0] / "run_summary.json").read_text(encoding="utf-8"))
            asian_rows = json.loads((run_dirs[0] / "asian_odds.json").read_text(encoding="utf-8"))
            over_under_rows = json.loads((run_dirs[0] / "over_under_odds.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(summary["fetch_market_profile"], "full_markets")
        self.assertEqual(asian_rows, [{"schedule_id": 123, "market": "asian"}])
        self.assertEqual(over_under_rows, [{"schedule_id": 123, "market": "over_under"}])
        self.assertIsNotNone(built_snapshot_args.get("asian"))
        self.assertIsNotNone(built_snapshot_args.get("over_under"))

    def test_prediction_run_reuses_fresh_cache_files_without_refetching(self) -> None:
        prediction = PredictionRow(
            match_date="2026-04-17",
            kickoff_time="15:00",
            competition_code="E0",
            competition_name="Premier League",
            season_key="2526",
            home_team="A",
            away_team="B",
            home_upset_probability=0.41,
            away_upset_probability=0.18,
            non_upset_probability=0.41,
            upset_score=0.59,
            candidate_label="home_upset_win",
            candidate_probability=0.41,
            predicted_label="home_upset_win",
            actual_label="unknown",
            explanation="x",
        )
        artifact = make_artifact(labels=["home_upset_win", "away_upset_win", "non_upset"], threshold=0.40)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            raw_dir = root / "raw"
            interim_dir = root / "interim"
            cache_dir = raw_dir / "prediction_cache"
            (cache_dir / "schedule").mkdir(parents=True, exist_ok=True)
            (cache_dir / "1x2").mkdir(parents=True, exist_ok=True)
            (cache_dir / "asian").mkdir(parents=True, exist_ok=True)
            (cache_dir / "over_under").mkdir(parents=True, exist_ok=True)
            (cache_dir / "schedule" / "2026-04-17.html").write_text("cached-schedule", encoding="utf-8")
            (cache_dir / "1x2" / "123.js").write_text("cached-europe", encoding="utf-8")
            (cache_dir / "asian" / "123.html").write_text("cached-asian", encoding="utf-8")
            (cache_dir / "over_under" / "123.html").write_text("cached-over-under", encoding="utf-8")

            with (
                patch("scripts.predict_titan007_range.TITAN007_RAW_DIR", raw_dir),
                patch("scripts.predict_titan007_range.TITAN007_INTERIM_DIR", interim_dir),
                patch("scripts.predict_titan007_range.iter_match_dates", return_value=["2026-04-17"]),
                patch("scripts.predict_titan007_range.load_model_artifact", return_value=artifact),
                patch("scripts.predict_titan007_range.fetch_text", side_effect=AssertionError("network fetch should not run")),
                patch(
                    "scripts.predict_titan007_range.parse_schedule_matches",
                    return_value=[
                        SimpleNamespace(
                            schedule_id=123,
                            competition_code="E0",
                            match_date="2026-04-17",
                            kickoff_time="15:00",
                            home_team="A",
                            away_team="B",
                        )
                    ],
                ),
                patch(
                    "scripts.predict_titan007_range.serialize_schedule_matches",
                    return_value=[
                        {
                            "match_date": "2026-04-17",
                            "kickoff_time": "15:00",
                            "competition_code": "E0",
                            "competition_name": "Premier League",
                            "home_team": "A",
                            "away_team": "B",
                            "schedule_id": 123,
                        }
                    ],
                ),
                patch("scripts.predict_titan007_range.parse_europe_odds_snapshot", return_value={"schedule_id": 123}),
                patch("scripts.predict_titan007_range.serialize_europe_snapshot", return_value={"schedule_id": 123}),
                patch("scripts.predict_titan007_range.parse_asian_odds_snapshot", return_value={"schedule_id": 123, "market": "asian"}),
                patch("scripts.predict_titan007_range.serialize_asian_snapshot", return_value={"schedule_id": 123, "market": "asian"}),
                patch(
                    "scripts.predict_titan007_range.parse_over_under_snapshot",
                    return_value={"schedule_id": 123, "market": "over_under"},
                ),
                patch(
                    "scripts.predict_titan007_range.serialize_over_under_snapshot",
                    return_value={"schedule_id": 123, "market": "over_under"},
                ),
                patch(
                    "scripts.predict_titan007_range.build_snapshot_row",
                    return_value={
                        "match_date": "2026-04-17",
                        "kickoff_time": "15:00",
                        "competition_code": "E0",
                        "competition_name": "Premier League",
                        "home_team": "A",
                        "away_team": "B",
                        "source_schedule_id": "123",
                        "source_euro_page_url": "https://1x2d.titan007.com/123.js",
                        "B365H": "2.10",
                        "B365D": "3.20",
                        "B365A": "3.40",
                        "B365CH": "2.00",
                        "B365CD": "3.10",
                        "B365CA": "3.80",
                        "AvgH": "2.10",
                        "AvgD": "3.20",
                        "AvgA": "3.40",
                        "AvgCH": "2.00",
                        "AvgCD": "3.10",
                        "AvgCA": "3.80",
                    },
                ),
                patch("scripts.predict_titan007_range.score_rows", return_value=[prediction]),
            ):
                exit_code = predict_titan007_range.main(
                    [
                        "--start-date",
                        "2026-04-17",
                        "--end-date",
                        "2026-04-17",
                    ]
                )

            run_dirs = [path for path in interim_dir.iterdir() if path.is_dir()]
            self.assertEqual(len(run_dirs), 1)
            summary = json.loads((run_dirs[0] / "run_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(summary["fetch_market_profile"], "full_markets")
        self.assertEqual(summary["failure_count"], 0)

    def test_prediction_run_filters_out_of_window_matches_before_odds_fetch(self) -> None:
        artifact = make_artifact(labels=["home_upset_win", "away_upset_win", "non_upset"], threshold=0.40)

        def fake_fetch_text(url: str, encoding: str, output_path: Path):
            if "Next_" in url:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("schedule", encoding="utf-8")
                return "schedule"
            raise AssertionError(f"unexpected odds fetch for out-of-window match: {url}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            raw_dir = root / "raw"
            interim_dir = root / "interim"
            with (
                patch("scripts.predict_titan007_range.TITAN007_RAW_DIR", raw_dir),
                patch("scripts.predict_titan007_range.TITAN007_INTERIM_DIR", interim_dir),
                patch("scripts.predict_titan007_range.iter_match_dates", return_value=["2026-04-17"]),
                patch("scripts.predict_titan007_range.load_model_artifact", return_value=artifact),
                patch("scripts.predict_titan007_range.fetch_text", side_effect=fake_fetch_text),
                patch(
                    "scripts.predict_titan007_range.parse_schedule_matches",
                    return_value=[
                        SimpleNamespace(
                            schedule_id=123,
                            competition_code="E0",
                            match_date="2026-04-17",
                            kickoff_time="17:00",
                            home_team="Before",
                            away_team="Window",
                        )
                    ],
                ),
                patch("scripts.predict_titan007_range.serialize_schedule_matches", return_value=[]),
            ):
                exit_code = predict_titan007_range.main(
                    [
                        "--start-datetime",
                        "2026-04-17 22:00",
                        "--end-datetime",
                        "2026-04-18 12:00",
                    ]
                )

            run_dirs = [path for path in interim_dir.iterdir() if path.is_dir()]
            self.assertEqual(len(run_dirs), 1)
            summary = json.loads((run_dirs[0] / "run_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(summary["scheduled_match_count"], 0)
        self.assertEqual(summary["snapshot_row_count"], 0)
        self.assertEqual(summary["failure_count"], 0)

    def test_training_rows_round_trip_through_csv(self) -> None:
        rows = [
            make_row("01/08/2023", "H", "3.20", "3.20", "2.15", "3.70", "3.25", "1.92", "2324"),
            make_row("02/08/2023", "H", "1.70", "3.80", "5.10", "1.62", "4.00", "5.60", "2324"),
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "rows.csv"
            save_training_rows(rows, output_path=path)
            loaded_rows = load_training_rows(path)

        self.assertEqual(len(loaded_rows), 2)
        self.assertEqual(loaded_rows[0].upset_label, rows[0].upset_label)
        self.assertAlmostEqual(loaded_rows[0].feature_close_home_odds or 0.0, rows[0].feature_close_home_odds or 0.0)

    def test_score_rows_uses_saved_model_artifact(self) -> None:
        rows = [
            make_row("01/08/2023", "H", "3.20", "3.20", "2.15", "3.70", "3.25", "1.92", "2324"),
            make_row("02/08/2023", "A", "2.00", "3.30", "3.45", "1.86", "3.35", "3.90", "2324"),
            make_row("03/08/2023", "H", "1.70", "3.80", "5.10", "1.62", "4.00", "5.60", "2324"),
            make_row("01/08/2024", "H", "3.25", "3.15", "2.10", "3.80", "3.20", "1.90", "2425"),
        ]
        split = split_rows_by_latest_season(rows, validation_season="2425")
        artifact = train_softmax_model(split=split, epochs=160, learning_rate=0.10, l2=0.0001)
        artifact.training_competition_scope = "explicit"
        artifact.training_competitions = ["E0"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / "model.json"
            save_model_artifact(artifact, output_path=model_path)
            loaded_artifact = load_model_artifact(model_path)
            predictions = score_rows(split.validation_rows, loaded_artifact)

        self.assertEqual(len(predictions), 1)
        self.assertEqual(loaded_artifact.training_competition_scope, "explicit")
        self.assertEqual(loaded_artifact.training_competitions, ["E0"])
        self.assertGreater(predictions[0].home_upset_probability, predictions[0].non_upset_probability)
        self.assertEqual(predictions[0].candidate_label, "home_upset_win")
        self.assertIn("主胜赔率", predictions[0].explanation)

    def test_combined_and_draw_rankings_use_draw_probability_when_available(self) -> None:
        predictions = [
            PredictionRow(
                match_date="2026-04-18",
                kickoff_time="15:00",
                competition_code="E0",
                competition_name="Premier League",
                season_key="2526",
                home_team="A",
                away_team="B",
                home_upset_probability=0.31,
                away_upset_probability=0.22,
                non_upset_probability=0.47,
                upset_score=0.53,
                candidate_label="home_upset_win",
                candidate_probability=0.31,
                predicted_label="non_upset",
                actual_label="unknown",
                explanation="x",
                draw_upset_probability=0.56,
            ),
            PredictionRow(
                match_date="2026-04-18",
                kickoff_time="18:00",
                competition_code="E0",
                competition_name="Premier League",
                season_key="2526",
                home_team="C",
                away_team="D",
                home_upset_probability=0.42,
                away_upset_probability=0.18,
                non_upset_probability=0.40,
                upset_score=0.60,
                candidate_label="home_upset_win",
                candidate_probability=0.42,
                predicted_label="home_upset_win",
                actual_label="unknown",
                explanation="y",
                draw_upset_probability=0.21,
            ),
        ]

        apply_combined_ranking_fields(predictions)
        combined_rankings = sort_combined_rankings(predictions)
        draw_rankings = sort_draw_rankings(predictions)

        self.assertEqual(predictions[0].combined_candidate_label, "draw_upset")
        self.assertAlmostEqual(predictions[0].combined_candidate_probability or 0.0, 0.56)
        self.assertEqual(predictions[0].secondary_candidate_label, "home_upset_win")
        self.assertAlmostEqual(predictions[0].secondary_candidate_probability or 0.0, 0.31)
        self.assertEqual(predictions[1].combined_candidate_label, "home_upset_win")
        self.assertEqual(predictions[1].secondary_candidate_label, "draw_upset")
        self.assertAlmostEqual(predictions[1].secondary_candidate_probability or 0.0, 0.21)
        self.assertEqual(combined_rankings[0].home_team, "A")
        self.assertEqual(draw_rankings[0].home_team, "A")

    def test_prediction_window_filters_matches_outside_hour_range(self) -> None:
        predictions = [
            PredictionRow(
                match_date="2026-04-17",
                kickoff_time="17:00",
                competition_code="E0",
                competition_name="Premier League",
                season_key="2526",
                home_team="Before",
                away_team="Window",
                home_upset_probability=0.31,
                away_upset_probability=0.22,
                non_upset_probability=0.47,
                upset_score=0.53,
                candidate_label="home_upset_win",
                candidate_probability=0.31,
                predicted_label="non_upset",
                actual_label="unknown",
                explanation="x",
                draw_upset_probability=0.56,
            ),
            PredictionRow(
                match_date="2026-04-17",
                kickoff_time="22:00",
                competition_code="E0",
                competition_name="Premier League",
                season_key="2526",
                home_team="Inside",
                away_team="Window",
                home_upset_probability=0.42,
                away_upset_probability=0.18,
                non_upset_probability=0.40,
                upset_score=0.60,
                candidate_label="home_upset_win",
                candidate_probability=0.42,
                predicted_label="home_upset_win",
                actual_label="unknown",
                explanation="y",
                draw_upset_probability=0.21,
            ),
        ]
        args = predict_titan007_range.parse_args(
            [
                "--start-datetime",
                "2026-04-17 22:00",
                "--end-datetime",
                "2026-04-18 12:00",
            ]
        )
        window = resolve_prediction_window(args)

        filtered = predict_titan007_range._filter_predictions_by_window(predictions, window)

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].home_team, "Inside")

    def test_betting_recommendations_add_direction_confidence_and_reason(self) -> None:
        predictions = [
            PredictionRow(
                match_date="2026-04-18",
                kickoff_time="15:00",
                competition_code="E0",
                competition_name="Premier League",
                season_key="2526",
                home_team="A",
                away_team="B",
                home_upset_probability=0.31,
                away_upset_probability=0.11,
                non_upset_probability=0.58,
                upset_score=0.53,
                candidate_label="home_upset_win",
                candidate_probability=0.31,
                predicted_label="non_upset",
                actual_label="unknown",
                explanation="主胜赔率 3.20 -> 3.70",
                draw_upset_probability=0.58,
            ),
            PredictionRow(
                match_date="2026-04-18",
                kickoff_time="16:00",
                competition_code="E0",
                competition_name="Premier League",
                season_key="2526",
                home_team="E",
                away_team="F",
                home_upset_probability=0.31,
                away_upset_probability=0.13,
                non_upset_probability=0.56,
                upset_score=0.55,
                candidate_label="home_upset_win",
                candidate_probability=0.31,
                predicted_label="non_upset",
                actual_label="unknown",
                explanation="主胜赔率 3.10 -> 3.10",
                draw_upset_probability=0.56,
            ),
            PredictionRow(
                match_date="2026-04-18",
                kickoff_time="17:00",
                competition_code="E0",
                competition_name="Premier League",
                season_key="2526",
                home_team="G",
                away_team="H",
                home_upset_probability=0.37,
                away_upset_probability=0.13,
                non_upset_probability=0.50,
                upset_score=0.55,
                candidate_label="home_upset_win",
                candidate_probability=0.37,
                predicted_label="non_upset",
                actual_label="unknown",
                explanation="主胜赔率 2.95 -> 3.05",
                draw_upset_probability=0.50,
            ),
            PredictionRow(
                match_date="2026-04-18",
                kickoff_time="18:00",
                competition_code="E0",
                competition_name="Premier League",
                season_key="2526",
                home_team="C",
                away_team="D",
                home_upset_probability=0.34,
                away_upset_probability=0.30,
                non_upset_probability=0.36,
                upset_score=0.57,
                candidate_label="home_upset_win",
                candidate_probability=0.34,
                predicted_label="non_upset",
                actual_label="unknown",
                explanation="主胜赔率 2.80 -> 2.95",
                draw_upset_probability=0.28,
            ),
        ]

        apply_combined_ranking_fields(predictions)
        apply_betting_recommendation_fields(
            predictions,
            main_artifact=make_artifact(labels=["home_upset_win", "away_upset_win", "non_upset"], threshold=0.58),
            draw_artifact=make_artifact(labels=["draw_upset", "non_draw_upset"], threshold=0.48),
        )
        betting_rankings = sort_betting_recommendations(predictions)
        actionable_rankings = filter_actionable_betting_recommendations(predictions)
        final_rows = build_final_betting_rows(predictions)

        self.assertEqual(predictions[0].bet_direction, "冷平")
        self.assertEqual(predictions[0].bet_confidence, "强")
        self.assertEqual(predictions[0].bet_recommendation, "建议投注")
        self.assertIn("达到门槛", predictions[0].bet_reason or "")
        self.assertEqual(predictions[1].bet_direction, "冷平")
        self.assertEqual(predictions[1].bet_confidence, "中")
        self.assertEqual(predictions[1].bet_recommendation, "建议投注")
        self.assertEqual(predictions[2].bet_direction, "冷平")
        self.assertEqual(predictions[2].bet_confidence, "弱")
        self.assertEqual(predictions[2].bet_recommendation, "谨慎关注")
        self.assertEqual(predictions[3].bet_direction, "不投注")
        self.assertEqual(predictions[3].bet_recommendation, "不投注")
        self.assertGreater(predictions[0].bet_confidence_score or 0.0, predictions[1].bet_confidence_score or 0.0)
        self.assertGreater(predictions[1].bet_confidence_score or 0.0, predictions[2].bet_confidence_score or 0.0)
        self.assertEqual(betting_rankings[0].home_team, "A")
        self.assertEqual([prediction.home_team for prediction in actionable_rankings], ["A", "E"])
        self.assertEqual(
            final_rows,
            [
                {
                    "比赛时间": "2026-04-18 15:00",
                    "联赛": "Premier League",
                    "对阵": "A vs B",
                    "等级": "强",
                    "建议方向": "冷平",
                    "原因": predictions[0].bet_reason or "",
                },
                {
                    "比赛时间": "2026-04-18 16:00",
                    "联赛": "Premier League",
                    "对阵": "E vs F",
                    "等级": "中",
                    "建议方向": "冷平",
                    "原因": predictions[1].bet_reason or "",
                }
            ],
        )

    def test_betting_recommendations_require_single_direction_probability_for_non_draw(self) -> None:
        predictions = [
            PredictionRow(
                match_date="2026-04-18",
                kickoff_time="19:00",
                competition_code="E0",
                competition_name="Premier League",
                season_key="2526",
                home_team="I",
                away_team="J",
                home_upset_probability=0.42,
                away_upset_probability=0.20,
                non_upset_probability=0.38,
                upset_score=0.62,
                candidate_label="home_upset_win",
                candidate_probability=0.42,
                predicted_label="non_upset",
                actual_label="unknown",
                explanation="主胜赔率 2.85 -> 3.10",
                draw_upset_probability=None,
            ),
        ]

        apply_combined_ranking_fields(predictions)
        apply_betting_recommendation_fields(
            predictions,
            main_artifact=make_artifact(labels=["home_upset_win", "away_upset_win", "non_upset"], threshold=0.58),
            draw_artifact=None,
        )

        self.assertEqual(predictions[0].combined_candidate_label, "home_upset_win")
        self.assertEqual(predictions[0].bet_direction, "不投注")
        self.assertEqual(predictions[0].bet_recommendation, "不投注")
        self.assertIn("主冷概率 0.42，低于门槛 0.58", predictions[0].bet_reason or "")

    def test_betting_recommendations_use_calibrated_betting_policy_thresholds(self) -> None:
        predictions = [
            PredictionRow(
                match_date="2026-04-18",
                kickoff_time="20:00",
                competition_code="E0",
                competition_name="Premier League",
                season_key="2526",
                home_team="K",
                away_team="L",
                home_upset_probability=0.46,
                away_upset_probability=0.12,
                non_upset_probability=0.42,
                upset_score=0.58,
                candidate_label="home_upset_win",
                candidate_probability=0.46,
                predicted_label="non_upset",
                actual_label="unknown",
                explanation="主胜赔率 3.40 -> 3.75",
                draw_upset_probability=0.18,
            ),
        ]

        apply_combined_ranking_fields(predictions)
        apply_betting_recommendation_fields(
            predictions,
            main_artifact=make_artifact(
                labels=["home_upset_win", "away_upset_win", "non_upset"],
                threshold=0.60,
                betting_policy={
                    "direction_threshold": 0.45,
                    "strong_confidence_threshold": 0.20,
                    "medium_confidence_threshold": 0.05,
                    "min_direction_gap": 0.06,
                    "confidence_gap_weight": 0.50,
                },
            ),
            draw_artifact=None,
        )

        self.assertEqual(predictions[0].bet_direction, "主冷")
        self.assertEqual(predictions[0].bet_confidence, "中")
        self.assertEqual(predictions[0].bet_recommendation, "建议投注")
        self.assertIn("主冷概率 0.46，达到门槛 0.45", predictions[0].bet_reason or "")

    def test_betting_recommendations_prefer_interval_confidence_buckets_when_present(self) -> None:
        predictions = [
            PredictionRow(
                match_date="2026-04-18",
                kickoff_time="20:30",
                competition_code="E0",
                competition_name="Premier League",
                season_key="2526",
                home_team="M",
                away_team="N",
                home_upset_probability=0.48,
                away_upset_probability=0.10,
                non_upset_probability=0.42,
                upset_score=0.58,
                candidate_label="home_upset_win",
                candidate_probability=0.48,
                predicted_label="non_upset",
                actual_label="unknown",
                explanation="主胜赔率 3.50 -> 3.80",
                draw_upset_probability=0.18,
            ),
        ]

        apply_combined_ranking_fields(predictions)
        apply_betting_recommendation_fields(
            predictions,
            main_artifact=make_artifact(
                labels=["home_upset_win", "away_upset_win", "non_upset"],
                threshold=0.60,
                betting_policy={
                    "direction_threshold": 0.45,
                    "min_direction_gap": 0.06,
                    "confidence_gap_weight": 0.50,
                    "confidence_buckets": [
                        {"label": "强", "min_priority": 0.19, "max_priority": 0.24},
                        {"label": "中", "min_priority": 0.12, "max_priority": 0.189999},
                        {"label": "弱", "min_priority": 0.0, "max_priority": 0.119999},
                    ],
                },
            ),
            draw_artifact=None,
        )

        self.assertEqual(predictions[0].bet_direction, "主冷")
        self.assertEqual(predictions[0].bet_confidence, "中")
        self.assertEqual(predictions[0].bet_recommendation, "建议投注")


if __name__ == "__main__":
    unittest.main()
