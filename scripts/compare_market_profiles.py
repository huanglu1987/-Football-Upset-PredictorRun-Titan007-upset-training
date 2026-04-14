from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from upset_model.config import TRAINING_REPORT_DIR
from upset_model.draw_model import recommend_draw_threshold, save_draw_training_report, score_draw_rows
from upset_model.modeling import (
    recommend_decision_threshold,
    save_model_artifact,
    save_training_report,
    score_rows,
    split_rows_by_latest_season,
    train_softmax_model,
)
from upset_model.standardize import (
    DRAW_LABELS,
    filter_rows_by_market_profile,
    load_training_rows,
    relabel_rows_for_draw,
    save_training_rows,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Titan007 model quality across market-completeness cohorts.")
    parser.add_argument(
        "--input-path",
        type=Path,
        required=True,
        help="Normalized Titan007 training rows CSV.",
    )
    parser.add_argument(
        "--validation-season",
        default="2526",
        help="Season key held out for validation.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional output directory. Defaults to data/interim/titan007/market_profile_comparison_<run_id>/.",
    )
    return parser.parse_args(argv)


def _run_main_model(rows, validation_season: str, model_path: Path, report_path: Path) -> dict[str, object]:
    split = split_rows_by_latest_season(rows, validation_season=validation_season)
    artifact = train_softmax_model(
        split=split,
        epochs=120,
        learning_rate=0.04,
        l2=0.0005,
        class_weight_strategy="none",
    )
    validation_predictions = score_rows(split.validation_rows, artifact)
    threshold_result = recommend_decision_threshold(
        validation_predictions,
        accuracy_floor=0.60,
        min_predicted_upsets=10,
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
    save_model_artifact(artifact, output_path=model_path)
    save_training_report(artifact, output_path=report_path)
    return {
        "train_size": artifact.train_size,
        "validation_size": artifact.validation_size,
        "top_10_upset_precision": artifact.metrics["top_10_upset_precision"],
        "top_20_upset_precision": artifact.metrics["top_20_upset_precision"],
        "top_20_home_upset_win_precision": artifact.metrics["top_20_home_upset_win_precision"],
        "top_20_away_upset_win_precision": artifact.metrics["top_20_away_upset_win_precision"],
        "accuracy": artifact.metrics["accuracy"],
        "decision_threshold": artifact.decision_threshold,
        "decision_accuracy": artifact.decision_metrics["accuracy"],
        "decision_upset_precision": artifact.decision_metrics["upset_precision"],
        "decision_upset_recall": artifact.decision_metrics["upset_recall"],
        "model_path": str(model_path),
        "report_path": str(report_path),
    }


def _run_draw_model(rows, validation_season: str, model_path: Path, report_path: Path) -> dict[str, object]:
    relabeled_rows = relabel_rows_for_draw(rows)
    split = split_rows_by_latest_season(relabeled_rows, validation_season=validation_season)
    artifact = train_softmax_model(
        split=split,
        labels=list(DRAW_LABELS),
        epochs=120,
        learning_rate=0.06,
        l2=0.0005,
        class_weight_strategy="sqrt_balanced",
    )
    validation_predictions = score_draw_rows(split.validation_rows, artifact)
    threshold_result = recommend_draw_threshold(
        validation_predictions,
        accuracy_floor=0.60,
        min_predicted_draws=10,
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
    save_model_artifact(artifact, output_path=model_path)
    save_draw_training_report(artifact, output_path=report_path)
    return {
        "train_size": artifact.train_size,
        "validation_size": artifact.validation_size,
        "top_10_draw_upset_precision": artifact.metrics["top_10_draw_upset_precision"],
        "top_20_draw_upset_precision": artifact.metrics["top_20_draw_upset_precision"],
        "accuracy": artifact.metrics["accuracy"],
        "decision_threshold": artifact.decision_threshold,
        "decision_accuracy": artifact.decision_metrics["accuracy"],
        "decision_draw_precision": artifact.decision_metrics["draw_precision"],
        "decision_draw_recall": artifact.decision_metrics["draw_recall"],
        "model_path": str(model_path),
        "report_path": str(report_path),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = load_training_rows(args.input_path)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir or (
        PROJECT_ROOT / "data" / "interim" / "titan007" / f"market_profile_comparison_{run_id}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    TRAINING_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    cohorts = {
        "all": rows,
        "full_markets": filter_rows_by_market_profile(rows, "full_markets"),
        "1x2_only": filter_rows_by_market_profile(rows, "1x2_only"),
    }

    summary: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_path": str(args.input_path),
        "validation_season": args.validation_season,
        "cohorts": {},
    }

    for cohort_name, cohort_rows in cohorts.items():
        cohort_dir = output_dir / cohort_name
        cohort_dir.mkdir(parents=True, exist_ok=True)
        rows_path = save_training_rows(cohort_rows, output_path=cohort_dir / "training_rows.csv")
        cohort_summary: dict[str, object] = {
            "row_count": len(cohort_rows),
            "training_rows_path": str(rows_path),
        }
        try:
            main_metrics = _run_main_model(
                cohort_rows,
                validation_season=args.validation_season,
                model_path=cohort_dir / "main_model.json",
                report_path=cohort_dir / "main_report.json",
            )
            draw_metrics = _run_draw_model(
                cohort_rows,
                validation_season=args.validation_season,
                model_path=cohort_dir / "draw_model.json",
                report_path=cohort_dir / "draw_report.json",
            )
            cohort_summary["main_model"] = main_metrics
            cohort_summary["draw_model"] = draw_metrics
        except Exception as exc:
            cohort_summary["error"] = str(exc)
        summary["cohorts"][cohort_name] = cohort_summary

    all_metrics = summary["cohorts"].get("all", {})
    full_metrics = summary["cohorts"].get("full_markets", {})
    recommendation = {
        "suggested_primary_dataset": "full_markets"
        if isinstance(full_metrics, dict)
        and isinstance(full_metrics.get("main_model"), dict)
        and isinstance(all_metrics, dict)
        and isinstance(all_metrics.get("main_model"), dict)
        and full_metrics["main_model"]["top_20_upset_precision"] >= all_metrics["main_model"]["top_20_upset_precision"]
        else "all",
        "suggested_fallback_dataset": "1x2_only",
    }
    summary["recommendation"] = recommendation

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Comparison summary saved to {summary_path}")
    for cohort_name, cohort_summary in summary["cohorts"].items():
        print(f"[{cohort_name}] rows={cohort_summary.get('row_count', 0)}")
        if "error" in cohort_summary:
            print(f"  error={cohort_summary['error']}")
            continue
        main_metrics = cohort_summary["main_model"]
        draw_metrics = cohort_summary["draw_model"]
        print(
            "  main_top20="
            f"{main_metrics['top_20_upset_precision']:.4f}, "
            f"home_top20={main_metrics['top_20_home_upset_win_precision']:.4f}, "
            f"away_top20={main_metrics['top_20_away_upset_win_precision']:.4f}"
        )
        print(
            "  draw_top20="
            f"{draw_metrics['top_20_draw_upset_precision']:.4f}, "
            f"main_decision_acc={main_metrics['decision_accuracy']:.4f}"
        )
    print(f"Suggested primary dataset: {recommendation['suggested_primary_dataset']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
