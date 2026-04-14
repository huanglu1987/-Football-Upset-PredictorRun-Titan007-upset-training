from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict, fields
from pathlib import Path

from upset_model.modeling import load_model_artifact, save_prediction_report, score_rows
from upset_model.standardize import load_snapshot_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score a manually prepared odds snapshot CSV without requiring a live API key.",
    )
    parser.add_argument("--input", required=True, help="Path to the snapshot CSV file.")
    parser.add_argument("--top-n", type=int, default=20, help="How many highest-upset-score matches to show.")
    parser.add_argument(
        "--season-key",
        default="manual",
        help="Logical season key written into the output rows, for example 2526 or manual.",
    )
    parser.add_argument(
        "--default-competition",
        default="E0",
        help="Fallback competition code when the input CSV omits competition_code/Div.",
    )
    return parser.parse_args()


def save_prediction_csv(predictions: list, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[field.name for field in fields(predictions[0].__class__)])
        writer.writeheader()
        for prediction in predictions:
            writer.writerow(asdict(prediction))
    return output_path


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    rows = load_snapshot_rows(
        input_path=input_path,
        season_key=args.season_key,
        default_competition_code=args.default_competition,
    )
    if not rows:
        print("No valid snapshot rows were loaded from the input CSV.")
        print(
            "Required columns are either football-data style "
            "(Div,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A,B365CH,B365CD,B365CA) "
            "or normalized aliases "
            "(competition_code,match_date,kickoff_time,home_team,away_team, ... same odds fields).",
        )
        return 1

    artifact = load_model_artifact()
    predictions = score_rows(rows, artifact)
    top_predictions = sorted(predictions, key=lambda row: row.upset_score, reverse=True)[: args.top_n]

    report_path = save_prediction_report(predictions)
    csv_path = save_prediction_csv(predictions, report_path.with_name(f"{input_path.stem}_predictions.csv"))

    print(f"Scored {len(predictions)} snapshot rows from {input_path}. Top {len(top_predictions)} by upset score:")
    for prediction in top_predictions:
        print(
            f"{prediction.match_date} {prediction.competition_code} "
            f"{prediction.home_team} vs {prediction.away_team} "
            f"candidate={prediction.candidate_label}({prediction.candidate_probability:.3f}) "
            f"score={prediction.upset_score:.3f} explain={prediction.explanation}",
        )
    print(f"Prediction report saved to {report_path}")
    print(f"Prediction CSV saved to {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
