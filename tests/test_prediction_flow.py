import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import predict_titan007_range
from scripts.predict_titan007_range import (
    apply_combined_ranking_fields,
    resolve_prediction_window,
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


def make_artifact(*, labels: list[str], threshold: float) -> SoftmaxModelArtifact:
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
    )


class PredictionFlowTests(unittest.TestCase):
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

        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / "model.json"
            save_model_artifact(artifact, output_path=model_path)
            loaded_artifact = load_model_artifact(model_path)
            predictions = score_rows(split.validation_rows, loaded_artifact)

        self.assertEqual(len(predictions), 1)
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
        self.assertEqual([prediction.home_team for prediction in actionable_rankings], ["A", "E", "G"])
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
                },
                {
                    "比赛时间": "2026-04-18 17:00",
                    "联赛": "Premier League",
                    "对阵": "G vs H",
                    "等级": "弱",
                    "建议方向": "冷平",
                    "原因": predictions[2].bet_reason or "",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
