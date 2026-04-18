import unittest

from upset_model.betting_calibration import (
    evaluate_betting_direction_threshold,
    recommend_confidence_bucket_thresholds,
)
from upset_model.modeling import PredictionRow


def make_prediction(
    *,
    home_team: str,
    combined_label: str,
    combined_probability: float,
    secondary_probability: float,
    actual_label: str,
    home_probability: float,
    away_probability: float,
    draw_probability: float | None,
) -> PredictionRow:
    return PredictionRow(
        match_date="2026-04-18",
        kickoff_time="15:00",
        competition_code="E0",
        competition_name="Premier League",
        season_key="2526",
        home_team=home_team,
        away_team=f"{home_team}-away",
        home_upset_probability=home_probability,
        away_upset_probability=away_probability,
        non_upset_probability=0.20,
        upset_score=home_probability + away_probability,
        candidate_label="home_upset_win" if home_probability >= away_probability else "away_upset_win",
        candidate_probability=max(home_probability, away_probability),
        predicted_label="non_upset",
        actual_label=actual_label,
        explanation="x",
        draw_upset_probability=draw_probability,
        combined_candidate_label=combined_label,
        combined_candidate_probability=combined_probability,
        secondary_candidate_label="draw_upset" if combined_label != "draw_upset" else "home_upset_win",
        secondary_candidate_probability=secondary_probability,
    )


class BettingCalibrationTests(unittest.TestCase):
    def test_evaluate_betting_direction_threshold_uses_exact_direction_hits(self) -> None:
        predictions = [
            make_prediction(
                home_team="A",
                combined_label="home_upset_win",
                combined_probability=0.72,
                secondary_probability=0.22,
                actual_label="home_upset_win",
                home_probability=0.72,
                away_probability=0.08,
                draw_probability=0.22,
            ),
            make_prediction(
                home_team="B",
                combined_label="away_upset_win",
                combined_probability=0.61,
                secondary_probability=0.28,
                actual_label="away_upset_win",
                home_probability=0.12,
                away_probability=0.61,
                draw_probability=0.28,
            ),
            make_prediction(
                home_team="C",
                combined_label="draw_upset",
                combined_probability=0.57,
                secondary_probability=0.26,
                actual_label="draw_upset",
                home_probability=0.17,
                away_probability=0.20,
                draw_probability=0.57,
            ),
            make_prediction(
                home_team="D",
                combined_label="away_upset_win",
                combined_probability=0.58,
                secondary_probability=0.35,
                actual_label="non_upset",
                home_probability=0.07,
                away_probability=0.58,
                draw_probability=0.35,
            ),
            make_prediction(
                home_team="E",
                combined_label="home_upset_win",
                combined_probability=0.54,
                secondary_probability=0.50,
                actual_label="home_upset_win",
                home_probability=0.54,
                away_probability=0.10,
                draw_probability=0.50,
            ),
        ]

        result = evaluate_betting_direction_threshold(
            predictions,
            main_direction_threshold=0.55,
            draw_threshold=0.48,
            min_direction_gap=0.06,
        )

        self.assertEqual(result.actionable_count, 4)
        self.assertEqual(result.total_hits, 3)
        self.assertAlmostEqual(result.precision, 0.75)

    def test_recommend_confidence_bucket_thresholds_returns_thresholds(self) -> None:
        predictions = [
            make_prediction(
                home_team="A",
                combined_label="home_upset_win",
                combined_probability=0.74,
                secondary_probability=0.20,
                actual_label="home_upset_win",
                home_probability=0.74,
                away_probability=0.06,
                draw_probability=0.20,
            ),
            make_prediction(
                home_team="B",
                combined_label="away_upset_win",
                combined_probability=0.70,
                secondary_probability=0.23,
                actual_label="away_upset_win",
                home_probability=0.07,
                away_probability=0.70,
                draw_probability=0.23,
            ),
            make_prediction(
                home_team="C",
                combined_label="draw_upset",
                combined_probability=0.62,
                secondary_probability=0.18,
                actual_label="draw_upset",
                home_probability=0.11,
                away_probability=0.09,
                draw_probability=0.62,
            ),
            make_prediction(
                home_team="D",
                combined_label="away_upset_win",
                combined_probability=0.60,
                secondary_probability=0.19,
                actual_label="away_upset_win",
                home_probability=0.11,
                away_probability=0.60,
                draw_probability=0.19,
            ),
            make_prediction(
                home_team="E",
                combined_label="home_upset_win",
                combined_probability=0.59,
                secondary_probability=0.24,
                actual_label="non_upset",
                home_probability=0.59,
                away_probability=0.06,
                draw_probability=0.24,
            ),
        ]

        payload = recommend_confidence_bucket_thresholds(
            predictions,
            main_direction_threshold=0.55,
            draw_threshold=0.48,
            min_direction_gap=0.06,
            gap_weight=0.50,
            min_bucket_size=1,
            min_weak_remainder=1,
        )

        self.assertEqual(payload["overall_actionable_count"], 5)
        self.assertIn(payload["confidence_bucket_strategy"], {"interval_search", "fallback_split"})
        self.assertEqual([bucket["label"] for bucket in payload["confidence_buckets"]], ["强", "中", "弱"])
        self.assertGreater(payload["strong_bucket"]["count"], 0)
        self.assertGreater(payload["weak_bucket"]["count"], 0)
        self.assertGreaterEqual(payload["strong_bucket"]["precision"], payload["medium_bucket"]["precision"])
        self.assertGreaterEqual(payload["medium_bucket"]["precision"], payload["weak_bucket"]["precision"])


if __name__ == "__main__":
    unittest.main()
