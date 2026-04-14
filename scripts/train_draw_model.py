from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from upset_model.draw_model import recommend_draw_threshold, save_draw_training_report, score_draw_rows
from upset_model.modeling import save_model_artifact, split_rows_by_latest_season, train_softmax_model
from upset_model.standardize import DRAW_LABELS, build_training_rows, filter_rows_by_market_profile, load_training_rows, relabel_rows_for_draw


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the football draw-upset model from normalized odds rows.")
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
        help="How strongly to upweight rare draw-upset samples during training.",
    )
    parser.add_argument(
        "--accuracy-floor",
        type=float,
        default=0.60,
        help="Minimum acceptable overall accuracy when selecting the final decision threshold.",
    )
    parser.add_argument(
        "--min-predicted-draws",
        type=int,
        default=10,
        help="Minimum number of draw-upset predictions required when selecting the final decision threshold.",
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        help="Optional path to a normalized training rows CSV. If omitted, rebuild from the default historical source.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        help="Optional output path for the trained draw model artifact JSON.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        help="Optional output path for the draw training report JSON.",
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
    source_rows = load_training_rows(args.input_path) if args.input_path else build_training_rows()
    if args.market_profile != "all":
        source_rows = filter_rows_by_market_profile(source_rows, args.market_profile)
        if not source_rows:
            print(f"No rows matched market profile: {args.market_profile}")
            return 1
    rows = relabel_rows_for_draw(source_rows)
    split = split_rows_by_latest_season(rows, validation_season=args.validation_season)
    artifact = train_softmax_model(
        split=split,
        labels=list(DRAW_LABELS),
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        l2=args.l2,
        class_weight_strategy=args.class_weight_strategy,
    )

    validation_predictions = score_draw_rows(split.validation_rows, artifact)
    threshold_result = recommend_draw_threshold(
        validation_predictions,
        accuracy_floor=args.accuracy_floor,
        min_predicted_draws=args.min_predicted_draws,
    )
    artifact.decision_threshold = threshold_result.threshold
    artifact.decision_metrics = {
        "accuracy": threshold_result.accuracy,
        "draw_precision": threshold_result.draw_precision,
        "draw_recall": threshold_result.draw_recall,
        "draw_f1": threshold_result.draw_f1,
        "predicted_draws": threshold_result.predicted_draws,
        "candidate_rate": threshold_result.candidate_rate,
        "per_class": threshold_result.per_class,
    }

    model_path = save_model_artifact(artifact, output_path=args.model_path)
    report_path = save_draw_training_report(artifact, output_path=args.report_path)

    print(
        f"Trained draw model with {artifact.train_size} train rows and "
        f"{artifact.validation_size} validation rows (season {artifact.validation_season}).",
    )
    print(f"Accuracy: {artifact.metrics['accuracy']:.4f}")
    print(f"Log loss: {artifact.metrics['log_loss']:.4f}")
    print(f"Top-20 draw-upset precision: {artifact.metrics['top_20_draw_upset_precision']:.4f}")
    print(f"Market profile: {args.market_profile}")
    print(f"Class weights: {artifact.class_weights}")
    print(
        "Decision threshold: "
        f"{artifact.decision_threshold:.2f} "
        f"(accuracy={artifact.decision_metrics['accuracy']:.4f}, "
        f"draw_precision={artifact.decision_metrics['draw_precision']:.4f}, "
        f"draw_recall={artifact.decision_metrics['draw_recall']:.4f})",
    )
    print(f"Model saved to {model_path}")
    print(f"Report saved to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
