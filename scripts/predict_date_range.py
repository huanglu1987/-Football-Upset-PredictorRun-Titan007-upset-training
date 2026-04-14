from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict, fields
from datetime import date
from pathlib import Path

from upset_model.config import FEATURES_DIR
from upset_model.modeling import load_model_artifact, save_prediction_report, score_rows
from upset_model.standardize import build_training_rows, load_training_rows, save_training_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score matches in a date range and output upset probabilities plus a ranked shortlist.",
    )
    parser.add_argument("--start-date", required=True, help="Inclusive start date in YYYY-MM-DD format.")
    parser.add_argument("--end-date", required=True, help="Inclusive end date in YYYY-MM-DD format.")
    parser.add_argument("--top-n", type=int, default=20, help="How many highest-upset-score matches to show.")
    parser.add_argument(
        "--competition",
        action="append",
        help="Optional competition code filter. Can be passed multiple times, for example --competition E0 --competition SP1.",
    )
    parser.add_argument(
        "--refresh-rows",
        action="store_true",
        help="Rebuild the normalized training rows CSV from raw downloaded files before scoring.",
    )
    return parser.parse_args()


def ensure_training_rows(refresh_rows: bool) -> Path:
    target = FEATURES_DIR / "football_data_training_rows.csv"
    if refresh_rows or not target.exists():
        rows = build_training_rows()
        return save_training_rows(rows, output_path=target)
    return target


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
    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)
    if start_date > end_date:
        raise ValueError("start-date must be earlier than or equal to end-date")

    rows_path = ensure_training_rows(refresh_rows=args.refresh_rows)
    rows = load_training_rows(rows_path)
    artifact = load_model_artifact()
    competition_filter = {value.upper() for value in args.competition} if args.competition else None

    filtered_rows = [
        row
        for row in rows
        if start_date <= date.fromisoformat(row.match_date) <= end_date
        and (competition_filter is None or row.competition_code in competition_filter)
    ]
    if not filtered_rows:
        print("No matches found in the requested date range.")
        return 0

    predictions = score_rows(filtered_rows, artifact)
    top_predictions = sorted(predictions, key=lambda row: row.upset_score, reverse=True)[: args.top_n]

    report_path = save_prediction_report(predictions)
    csv_path = save_prediction_csv(
        predictions,
        report_path.with_suffix(".csv"),
    )

    print(
        f"Scored {len(predictions)} matches from {args.start_date} to {args.end_date}. "
        f"Top {len(top_predictions)} by upset score:",
    )
    for prediction in top_predictions:
        print(
            f"{prediction.match_date} {prediction.competition_code} "
            f"{prediction.home_team} vs {prediction.away_team} "
            f"home={prediction.home_upset_probability:.3f} "
            f"away={prediction.away_upset_probability:.3f} "
            f"candidate={prediction.candidate_label}({prediction.candidate_probability:.3f}) "
            f"score={prediction.upset_score:.3f} "
            f"pred={prediction.predicted_label} "
            f"explain={prediction.explanation}",
        )
    print(f"Prediction report saved to {report_path}")
    print(f"Prediction CSV saved to {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
