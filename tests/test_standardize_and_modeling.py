import unittest

from upset_model.modeling import (
    PredictionRow,
    compute_class_weights,
    evaluate_threshold_policy,
    predict_row_probabilities,
    recommend_decision_threshold,
    score_rows,
    split_rows_by_latest_season,
    train_softmax_model,
)
from upset_model.standardize import (
    UPSET_LABEL_AWAY,
    UPSET_LABEL_HOME,
    UPSET_LABEL_NONE,
    row_to_training_row,
)


def make_raw_row(
    *,
    date: str,
    home_team: str,
    away_team: str,
    result: str,
    open_home: str,
    open_draw: str,
    open_away: str,
    close_home: str,
    close_draw: str,
    close_away: str,
    open_ah_line: str = "0",
    close_ah_line: str = "0",
) -> dict[str, str]:
    return {
        "Div": "E0",
        "Date": date,
        "Time": "15:00",
        "HomeTeam": home_team,
        "AwayTeam": away_team,
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
        "AHh": open_ah_line,
        "AHCh": close_ah_line,
        "B365AHH": "1.95",
        "B365AHA": "1.95",
        "B365CAHH": "1.92",
        "B365CAHA": "1.98",
        "B365>2.5": "1.90",
        "B365<2.5": "1.95",
        "B365C>2.5": "1.88",
        "B365C<2.5": "1.98",
    }


class StandardizeAndModelingTests(unittest.TestCase):
    def test_compute_class_weights_upweights_rare_classes(self) -> None:
        rows = [
            row_to_training_row(
                make_raw_row(
                    date="01/08/2023",
                    home_team="A",
                    away_team="B",
                    result="H",
                    open_home="3.40",
                    open_draw="3.10",
                    open_away="2.10",
                    close_home="3.80",
                    close_draw="3.20",
                    close_away="1.95",
                ),
                season_key="2324",
            ),
            row_to_training_row(
                make_raw_row(
                    date="02/08/2023",
                    home_team="C",
                    away_team="D",
                    result="H",
                    open_home="1.75",
                    open_draw="3.70",
                    open_away="4.80",
                    close_home="1.68",
                    close_draw="3.90",
                    close_away="5.20",
                ),
                season_key="2324",
            ),
            row_to_training_row(
                make_raw_row(
                    date="03/08/2023",
                    home_team="E",
                    away_team="F",
                    result="H",
                    open_home="1.80",
                    open_draw="3.60",
                    open_away="4.60",
                    close_home="1.70",
                    close_draw="3.80",
                    close_away="5.10",
                ),
                season_key="2324",
            ),
        ]
        clean_rows = [row for row in rows if row is not None]
        weights = compute_class_weights(clean_rows, strategy="balanced")
        self.assertGreater(weights[UPSET_LABEL_HOME], weights[UPSET_LABEL_NONE])

    def test_row_to_training_row_marks_home_upset_when_home_not_lowest_closing_price(self) -> None:
        row = row_to_training_row(
            make_raw_row(
                date="01/08/2023",
                home_team="Home",
                away_team="Away",
                result="H",
                open_home="3.40",
                open_draw="3.10",
                open_away="2.10",
                close_home="3.80",
                close_draw="3.20",
                close_away="1.95",
            ),
            season_key="2324",
        )
        assert row is not None
        self.assertEqual(row.upset_label, UPSET_LABEL_HOME)
        self.assertAlmostEqual(row.feature_home_odds_delta or 0.0, 0.40, places=6)
        self.assertAlmostEqual(row.feature_open_home_implied_prob or 0.0, 1 / 3.40, places=6)

    def test_row_to_training_row_marks_non_upset_when_favorite_wins(self) -> None:
        row = row_to_training_row(
            make_raw_row(
                date="02/08/2023",
                home_team="Fav",
                away_team="Dog",
                result="H",
                open_home="1.75",
                open_draw="3.70",
                open_away="4.80",
                close_home="1.68",
                close_draw="3.90",
                close_away="5.20",
            ),
            season_key="2324",
        )
        assert row is not None
        self.assertEqual(row.upset_label, UPSET_LABEL_NONE)

    def test_softmax_training_produces_reasonable_validation_probabilities(self) -> None:
        training_specs = [
            ("2324", "01/08/2023", "HU1", "X1", "H", "3.20", "3.20", "2.15", "3.70", "3.25", "1.92"),
            ("2324", "02/08/2023", "HU2", "X2", "H", "3.10", "3.25", "2.20", "3.55", "3.30", "1.95"),
            ("2324", "03/08/2023", "AU1", "Y1", "A", "2.00", "3.30", "3.45", "1.86", "3.35", "3.90"),
            ("2324", "04/08/2023", "AU2", "Y2", "A", "1.95", "3.35", "3.60", "1.82", "3.40", "4.05"),
            ("2324", "05/08/2023", "NF1", "Z1", "H", "1.70", "3.80", "5.10", "1.62", "4.00", "5.60"),
            ("2324", "06/08/2023", "NF2", "Z2", "A", "5.40", "4.00", "1.62", "5.80", "4.10", "1.55"),
            ("2425", "01/08/2024", "HU3", "X3", "H", "3.25", "3.15", "2.10", "3.80", "3.20", "1.90"),
            ("2425", "02/08/2024", "AU3", "Y3", "A", "2.05", "3.25", "3.50", "1.90", "3.30", "3.95"),
            ("2425", "03/08/2024", "NF3", "Z3", "H", "1.72", "3.75", "5.00", "1.64", "3.95", "5.50"),
        ]
        rows = []
        for season_key, date, home, away, result, open_home, open_draw, open_away, close_home, close_draw, close_away in training_specs:
            row = row_to_training_row(
                make_raw_row(
                    date=date,
                    home_team=home,
                    away_team=away,
                    result=result,
                    open_home=open_home,
                    open_draw=open_draw,
                    open_away=open_away,
                    close_home=close_home,
                    close_draw=close_draw,
                    close_away=close_away,
                ),
                season_key=season_key,
            )
            assert row is not None
            rows.append(row)

        split = split_rows_by_latest_season(rows, validation_season="2425")
        artifact = train_softmax_model(split=split, epochs=220, learning_rate=0.12, l2=0.0001)

        self.assertEqual(artifact.validation_season, "2425")
        self.assertGreaterEqual(artifact.metrics["accuracy"], 2 / 3)
        self.assertEqual(set(artifact.class_weights), {UPSET_LABEL_HOME, UPSET_LABEL_AWAY, UPSET_LABEL_NONE})
        self.assertIn("top_10_home_upset_win_precision", artifact.metrics)
        self.assertIn("top_20_home_upset_win_precision", artifact.metrics)
        self.assertIn("top_10_away_upset_win_precision", artifact.metrics)
        self.assertIn("top_20_away_upset_win_precision", artifact.metrics)

        validation_predictions = {
            row.home_team: predict_row_probabilities(row, artifact)
            for row in split.validation_rows
        }
        self.assertGreater(
            validation_predictions["HU3"][UPSET_LABEL_HOME],
            validation_predictions["HU3"][UPSET_LABEL_NONE],
        )
        self.assertGreater(
            validation_predictions["AU3"][UPSET_LABEL_AWAY],
            validation_predictions["AU3"][UPSET_LABEL_NONE],
        )

    def test_recommend_decision_threshold_can_recover_accuracy_floor(self) -> None:
        training_specs = [
            ("2324", "01/08/2023", "HU1", "X1", "H", "3.20", "3.20", "2.15", "3.70", "3.25", "1.92"),
            ("2324", "02/08/2023", "HU2", "X2", "H", "3.10", "3.25", "2.20", "3.55", "3.30", "1.95"),
            ("2324", "03/08/2023", "AU1", "Y1", "A", "2.00", "3.30", "3.45", "1.86", "3.35", "3.90"),
            ("2324", "04/08/2023", "NF1", "Z1", "H", "1.70", "3.80", "5.10", "1.62", "4.00", "5.60"),
            ("2324", "05/08/2023", "NF2", "Z2", "A", "5.40", "4.00", "1.62", "5.80", "4.10", "1.55"),
            ("2425", "01/08/2024", "HU3", "X3", "H", "3.25", "3.15", "2.10", "3.80", "3.20", "1.90"),
            ("2425", "02/08/2024", "AU3", "Y3", "A", "2.05", "3.25", "3.50", "1.90", "3.30", "3.95"),
            ("2425", "03/08/2024", "NF3", "Z3", "H", "1.72", "3.75", "5.00", "1.64", "3.95", "5.50"),
            ("2425", "04/08/2024", "NF4", "Z4", "A", "5.10", "4.10", "1.65", "5.50", "4.20", "1.58"),
        ]
        rows = []
        for season_key, date, home, away, result, open_home, open_draw, open_away, close_home, close_draw, close_away in training_specs:
            row = row_to_training_row(
                make_raw_row(
                    date=date,
                    home_team=home,
                    away_team=away,
                    result=result,
                    open_home=open_home,
                    open_draw=open_draw,
                    open_away=open_away,
                    close_home=close_home,
                    close_draw=close_draw,
                    close_away=close_away,
                ),
                season_key=season_key,
            )
            assert row is not None
            rows.append(row)

        split = split_rows_by_latest_season(rows, validation_season="2425")
        artifact = train_softmax_model(split=split, epochs=180, learning_rate=0.10, l2=0.0001)
        threshold_result = recommend_decision_threshold(
            score_rows(split.validation_rows, artifact),
            accuracy_floor=0.50,
            min_predicted_upsets=1,
        )
        self.assertGreaterEqual(threshold_result.accuracy, 0.50)
        threshold_metrics = evaluate_threshold_policy(
            score_rows(split.validation_rows, artifact),
            threshold=threshold_result.threshold,
        )
        self.assertAlmostEqual(threshold_metrics.threshold, threshold_result.threshold)

    def test_evaluate_threshold_policy_uses_candidate_probability_gate(self) -> None:
        predictions = [
            PredictionRow(
                match_date="2026-04-18",
                kickoff_time="15:00",
                competition_code="E0",
                competition_name="Premier League",
                season_key="2526",
                home_team="A",
                away_team="B",
                home_upset_probability=0.34,
                away_upset_probability=0.30,
                non_upset_probability=0.36,
                upset_score=0.64,
                candidate_label=UPSET_LABEL_HOME,
                candidate_probability=0.34,
                predicted_label=UPSET_LABEL_HOME,
                actual_label=UPSET_LABEL_NONE,
                explanation="x",
            ),
        ]

        threshold_metrics = evaluate_threshold_policy(predictions, threshold=0.50)

        self.assertEqual(threshold_metrics.predicted_upsets, 0)
        self.assertEqual(threshold_metrics.accuracy, 1.0)


if __name__ == "__main__":
    unittest.main()
