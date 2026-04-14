from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from upset_model.config import TRAINING_REPORT_DIR
from upset_model.modeling import recommend_decision_threshold, score_rows, split_rows_by_latest_season, train_softmax_model
from upset_model.standardize import build_training_rows, load_training_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare weighting strategies and select a balanced cold-upset screening policy.",
    )
    parser.add_argument(
        "--validation-season",
        help="Season key to hold out for validation, for example 2526. Defaults to the latest available season.",
    )
    parser.add_argument(
        "--accuracy-floor",
        type=float,
        default=0.60,
        help="Minimum acceptable overall accuracy for the threshold policy.",
    )
    parser.add_argument(
        "--min-predicted-upsets",
        type=int,
        default=20,
        help="Minimum number of upset predictions required for the threshold policy.",
    )
    parser.add_argument(
        "--strategy",
        action="append",
        dest="strategies",
        choices=["none", "balanced", "sqrt_balanced"],
        help="Optional subset of weighting strategies to compare.",
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        help="Optional normalized training rows CSV path. Defaults to the bundled historical dataset.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        help="Optional output path for the tuning report JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = load_training_rows(args.input_path) if args.input_path else build_training_rows()
    split = split_rows_by_latest_season(rows, validation_season=args.validation_season)
    strategies = args.strategies or ["none", "sqrt_balanced", "balanced"]

    candidates = []
    for strategy in strategies:
        artifact = train_softmax_model(split=split, class_weight_strategy=strategy)
        threshold_result = recommend_decision_threshold(
            score_rows(split.validation_rows, artifact),
            accuracy_floor=args.accuracy_floor,
            min_predicted_upsets=args.min_predicted_upsets,
        )
        ranking_metrics = artifact.metrics
        candidates.append(
            {
                "strategy": strategy,
                "ranking_metrics": ranking_metrics,
                "directional_balance_top_20": min(
                    ranking_metrics.get("top_20_home_upset_win_precision", 0.0),
                    ranking_metrics.get("top_20_away_upset_win_precision", 0.0),
                ),
                "class_weights": artifact.class_weights,
                "recommended_threshold": threshold_result.threshold,
                "decision_metrics": {
                    "accuracy": threshold_result.accuracy,
                    "upset_precision": threshold_result.upset_precision,
                    "upset_recall": threshold_result.upset_recall,
                    "upset_f1": threshold_result.upset_f1,
                    "predicted_upsets": threshold_result.predicted_upsets,
                    "candidate_rate": threshold_result.candidate_rate,
                    "per_class": threshold_result.per_class,
                },
            }
        )

    best = max(
        candidates,
        key=lambda item: (
            item["ranking_metrics"]["top_20_upset_precision"],
            item["directional_balance_top_20"],
            item["ranking_metrics"]["top_10_upset_precision"],
            item["decision_metrics"]["upset_f1"],
            item["decision_metrics"]["accuracy"],
        ),
    )

    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "validation_season": split.validation_season,
        "accuracy_floor": args.accuracy_floor,
        "min_predicted_upsets": args.min_predicted_upsets,
        "candidates": candidates,
        "recommended": best,
    }
    TRAINING_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = args.output_path or (
        TRAINING_REPORT_DIR / f"football_data_balance_tuning_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Recommended strategy: {best['strategy']}")
    print(f"Top-20 upset precision: {best['ranking_metrics']['top_20_upset_precision']:.4f}")
    print(f"Top-20 directional balance: {best['directional_balance_top_20']:.4f}")
    print(
        f"Decision threshold: {best['recommended_threshold']:.2f} "
        f"(accuracy={best['decision_metrics']['accuracy']:.4f}, "
        f"upset_f1={best['decision_metrics']['upset_f1']:.4f})",
    )
    print(f"Report saved to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
