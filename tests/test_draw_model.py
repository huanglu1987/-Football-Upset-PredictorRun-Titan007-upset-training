import unittest

from upset_model.draw_model import recommend_draw_threshold, score_draw_rows
from upset_model.modeling import split_rows_by_latest_season, train_softmax_model
from upset_model.standardize import DRAW_LABEL_NONE, DRAW_LABEL_UPSET, DRAW_LABELS, relabel_rows_for_draw, row_to_training_row


def make_raw_row(
    *,
    date: str,
    home_team: str,
    away_team: str,
    result: str,
    fthg: str,
    ftag: str,
    open_home: str,
    open_draw: str,
    open_away: str,
    close_home: str,
    close_draw: str,
    close_away: str,
) -> dict[str, str]:
    return {
        "Div": "E0",
        "Date": date,
        "Time": "15:00",
        "HomeTeam": home_team,
        "AwayTeam": away_team,
        "FTHG": fthg,
        "FTAG": ftag,
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


class DrawModelTests(unittest.TestCase):
    def test_relabel_rows_for_draw_marks_only_nonfavorite_draws(self) -> None:
        rows = [
            row_to_training_row(
                make_raw_row(
                    date="01/08/2023",
                    home_team="DrawDog",
                    away_team="Fav",
                    result="D",
                    fthg="1",
                    ftag="1",
                    open_home="2.10",
                    open_draw="3.20",
                    open_away="3.60",
                    close_home="1.95",
                    close_draw="3.30",
                    close_away="4.10",
                ),
                season_key="2324",
            ),
            row_to_training_row(
                make_raw_row(
                    date="02/08/2023",
                    home_team="DrawFav",
                    away_team="Even",
                    result="D",
                    fthg="0",
                    ftag="0",
                    open_home="3.10",
                    open_draw="2.30",
                    open_away="3.30",
                    close_home="3.25",
                    close_draw="2.15",
                    close_away="3.45",
                ),
                season_key="2324",
            ),
            row_to_training_row(
                make_raw_row(
                    date="03/08/2023",
                    home_team="HomeWin",
                    away_team="Away",
                    result="H",
                    fthg="2",
                    ftag="0",
                    open_home="1.75",
                    open_draw="3.60",
                    open_away="4.80",
                    close_home="1.68",
                    close_draw="3.75",
                    close_away="5.20",
                ),
                season_key="2324",
            ),
        ]
        clean_rows = [row for row in rows if row is not None]
        relabeled_rows = relabel_rows_for_draw(clean_rows)

        self.assertEqual(relabeled_rows[0].upset_label, DRAW_LABEL_UPSET)
        self.assertEqual(relabeled_rows[1].upset_label, DRAW_LABEL_NONE)
        self.assertEqual(relabeled_rows[2].upset_label, DRAW_LABEL_NONE)

    def test_draw_model_scores_draw_upset_probability(self) -> None:
        specs = [
            ("2324", "01/08/2023", "DU1", "A1", "D", "1", "1", "2.10", "3.20", "3.60", "1.95", "3.30", "4.10"),
            ("2324", "02/08/2023", "DU2", "A2", "D", "0", "0", "2.05", "3.10", "3.75", "1.88", "3.25", "4.25"),
            ("2324", "03/08/2023", "NF1", "B1", "H", "2", "0", "1.70", "3.70", "5.10", "1.62", "3.90", "5.60"),
            ("2324", "04/08/2023", "NF2", "B2", "A", "0", "2", "5.20", "4.00", "1.65", "5.60", "4.15", "1.58"),
            ("2324", "05/08/2023", "DN1", "B3", "D", "1", "1", "3.20", "2.20", "3.40", "3.35", "2.10", "3.60"),
            ("2425", "01/08/2024", "DU3", "C1", "D", "1", "1", "2.15", "3.25", "3.55", "1.92", "3.35", "4.05"),
            ("2425", "02/08/2024", "NF3", "C2", "H", "1", "0", "1.75", "3.75", "4.90", "1.66", "3.95", "5.40"),
            ("2425", "03/08/2024", "DN2", "C3", "D", "0", "0", "3.10", "2.25", "3.30", "3.25", "2.15", "3.45"),
        ]
        rows = []
        for season_key, date, home, away, result, fthg, ftag, open_home, open_draw, open_away, close_home, close_draw, close_away in specs:
            row = row_to_training_row(
                make_raw_row(
                    date=date,
                    home_team=home,
                    away_team=away,
                    result=result,
                    fthg=fthg,
                    ftag=ftag,
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

        draw_rows = relabel_rows_for_draw(rows)
        split = split_rows_by_latest_season(draw_rows, validation_season="2425")
        artifact = train_softmax_model(
            split=split,
            labels=list(DRAW_LABELS),
            epochs=220,
            learning_rate=0.08,
            l2=0.0001,
            class_weight_strategy="sqrt_balanced",
        )
        predictions = score_draw_rows(split.validation_rows, artifact)
        threshold_result = recommend_draw_threshold(predictions, accuracy_floor=0.50, min_predicted_draws=1)

        by_home = {prediction.home_team: prediction for prediction in predictions}
        self.assertGreater(by_home["DU3"].draw_upset_probability, by_home["NF3"].draw_upset_probability)
        self.assertEqual(by_home["DU3"].actual_label, DRAW_LABEL_UPSET)
        self.assertIn("平赔", by_home["DU3"].explanation)
        self.assertGreaterEqual(threshold_result.accuracy, 0.50)


if __name__ == "__main__":
    unittest.main()
