from __future__ import annotations

import argparse
import sys
from pathlib import Path

from upset_model.modeling import (
    recommend_decision_threshold,
    save_model_artifact,
    save_training_report,
    score_rows,
    split_rows_by_latest_season,
    train_softmax_model,
)
from upset_model.standardize import build_training_rows, filter_rows_by_market_profile, load_training_rows, save_training_rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the football upset baseline model from normalized odds rows.")
    parser.add_argument(
        "--validation-season",
        help="Season key to hold out for validation, for example 2526. Defaults to the latest available season.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=180,
        help="Number of batch-gradient epochs.",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.06,
        help="Initial learning rate for gradient descent.",
    )
    parser.add_argument(
        "--l2",
        type=float,
        default=0.0005,
        help="L2 regularization strength.",
    )
    parser.add_argument(
        "--class-weight-strategy",
        choices=["none", "balanced", "sqrt_balanced"],
        default="sqrt_balanced",
        help="How strongly to upweight rare upset classes during training.",
    )
    parser.add_argument(
        "--skip-save-rows",
        action="store_true",
        help="Do not rewrite the normalized training rows CSV before training.",
    )
    parser.add_argument(
        "--accuracy-floor",
        type=float,
        default=0.60,
        help="Minimum acceptable overall accuracy when selecting the final decision threshold.",
    )
    parser.add_argument(
        "--min-predicted-upsets",
        type=int,
        default=20,
        help="Minimum number of upset predictions required when selecting the final decision threshold.",
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        help="Optional path to a normalized training rows CSV. If omitted, rebuild from the default historical source.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        help="Optional output path for the trained model artifact JSON.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        help="Optional output path for the training report JSON.",
    )
    parser.add_argument(
        "--market-profile",
        choices=["all", "full_markets", "1x2_only", "partial_markets"],
        default="all",
        help="Optional market-completeness filter applied before training.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = load_training_rows(args.input_path) if args.input_path else build_training_rows()
    if args.market_profile != "all":
        rows = filter_rows_by_market_profile(rows, args.market_profile)
        if not rows:
            print(f"No rows matched market profile: {args.market_profile}")
            return 1
    if not args.skip_save_rows and args.input_path is None:
        rows_path = save_training_rows(rows)
        print(f"Normalized training rows saved to {rows_path}")

    split = split_rows_by_latest_season(rows, validation_season=args.validation_season)
    artifact = train_softmax_model(
        split=split,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        l2=args.l2,
        class_weight_strategy=args.class_weight_strategy,
    )
    validation_predictions = score_rows(split.validation_rows, artifact)
    threshold_result = recommend_decision_threshold(
        validation_predictions,
        accuracy_floor=args.accuracy_floor,
        min_predicted_upsets=args.min_predicted_upsets,
    )
    artifact.decision_threshold = threshold_result.threshold
    artifact.decision_metrics = {
        "accuracy": threshold_result.accuracy,
        "upset_precision": threshold_result.upset_precision,
        "upset_recall": threshold_result.upset_recall,
        "upset_f1": threshold_result.upset_f1,
        "predicted_upsets": threshold_result.predicted_upsets,
        "candidate_rate": threshold_result.candidate_rate,
        "per_class": threshold_result.per_class,
    }

    model_path = save_model_artifact(artifact, output_path=args.model_path)
    report_path = save_training_report(artifact, output_path=args.report_path)

    print(
        f"Trained model with {artifact.train_size} train rows and "
        f"{artifact.validation_size} validation rows (season {artifact.validation_season}).",
    )
    print(f"Accuracy: {artifact.metrics['accuracy']:.4f}")
    print(f"Log loss: {artifact.metrics['log_loss']:.4f}")
    print(f"Top-20 upset precision: {artifact.metrics['top_20_upset_precision']:.4f}")
    print(f"Market profile: {args.market_profile}")
    print(f"Class weights: {artifact.class_weights}")
    print(
        "Decision threshold: "
        f"{artifact.decision_threshold:.2f} "
        f"(accuracy={artifact.decision_metrics['accuracy']:.4f}, "
        f"upset_precision={artifact.decision_metrics['upset_precision']:.4f}, "
        f"upset_recall={artifact.decision_metrics['upset_recall']:.4f})",
    )
    print(f"Model saved to {model_path}")
    print(f"Report saved to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
