from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from upset_model.config import PREDICTION_REPORT_DIR, TRAINING_REPORT_DIR
from upset_model.modeling import SoftmaxModelArtifact, predict_row_probabilities
from upset_model.standardize import DRAW_LABEL_NONE, DRAW_LABEL_UPSET, TrainingRow


@dataclass
class DrawPredictionRow:
    match_date: str
    kickoff_time: str
    competition_code: str
    competition_name: str
    season_key: str
    home_team: str
    away_team: str
    draw_upset_probability: float
    non_draw_upset_probability: float
    predicted_label: str
    actual_label: str
    explanation: str


@dataclass
class DrawThresholdPolicyResult:
    threshold: float
    accuracy: float
    draw_precision: float
    draw_recall: float
    draw_f1: float
    predicted_draws: int
    candidate_rate: float
    per_class: dict[str, dict[str, float]]


def _format_float(value: float | None, signed: bool = False) -> str:
    if value is None:
        return "NA"
    return f"{value:+.2f}" if signed else f"{value:.2f}"


def _draw_gap(draw_odds: float | None, other_odds: Iterable[float | None]) -> float | None:
    if draw_odds is None:
        return None
    comparable = [value for value in other_odds if value is not None]
    if not comparable:
        return None
    return draw_odds - min(comparable)


def build_draw_prediction_explanation(row: TrainingRow) -> str:
    parts = [
        f"平赔 {_format_float(row.open_draw_odds)} -> {_format_float(row.close_draw_odds)}，变化 {_format_float(row.feature_draw_odds_delta, signed=True)}",
        (
            f"平赔相对主客最低赔差距 {_format_float(_draw_gap(row.open_draw_odds, (row.open_home_odds, row.open_away_odds)))} -> "
            f"{_format_float(_draw_gap(row.close_draw_odds, (row.close_home_odds, row.close_away_odds)))}"
        ),
    ]
    if row.open_over25_odds is not None or row.close_over25_odds is not None:
        parts.append(f"大2.5赔率 {_format_float(row.open_over25_odds)} -> {_format_float(row.close_over25_odds)}")
    return "；".join(parts)


def score_draw_rows(rows: Iterable[TrainingRow], artifact: SoftmaxModelArtifact) -> list[DrawPredictionRow]:
    scored_rows: list[DrawPredictionRow] = []
    for row in rows:
        probabilities = predict_row_probabilities(row, artifact)
        draw_upset_probability = probabilities.get(DRAW_LABEL_UPSET, 0.0)
        non_draw_upset_probability = probabilities.get(DRAW_LABEL_NONE, 0.0)
        predicted_label = (
            DRAW_LABEL_UPSET
            if artifact.decision_threshold is not None and draw_upset_probability >= artifact.decision_threshold
            else max(probabilities, key=probabilities.get)
            if artifact.decision_threshold is None
            else DRAW_LABEL_NONE
        )
        scored_rows.append(
            DrawPredictionRow(
                match_date=row.match_date,
                kickoff_time=row.kickoff_time,
                competition_code=row.competition_code,
                competition_name=row.competition_name,
                season_key=row.season_key,
                home_team=row.home_team,
                away_team=row.away_team,
                draw_upset_probability=draw_upset_probability,
                non_draw_upset_probability=non_draw_upset_probability,
                predicted_label=predicted_label,
                actual_label=row.upset_label,
                explanation=build_draw_prediction_explanation(row),
            )
        )
    scored_rows.sort(key=lambda row: (row.match_date, -row.draw_upset_probability, row.competition_code, row.home_team))
    return scored_rows


def evaluate_draw_threshold_policy(
    predictions: Iterable[DrawPredictionRow],
    threshold: float,
) -> DrawThresholdPolicyResult:
    prediction_list = list(predictions)
    correct = 0
    predicted_draws = 0
    true_draws = 0
    true_positive = 0
    per_class_counts = {
        label: {"tp": 0, "fp": 0, "fn": 0}
        for label in (DRAW_LABEL_UPSET, DRAW_LABEL_NONE)
    }

    for prediction in prediction_list:
        predicted_label = DRAW_LABEL_UPSET if prediction.draw_upset_probability >= threshold else DRAW_LABEL_NONE
        actual_label = prediction.actual_label
        if predicted_label == actual_label:
            correct += 1
        if actual_label == DRAW_LABEL_UPSET:
            true_draws += 1
        if predicted_label == DRAW_LABEL_UPSET:
            predicted_draws += 1
            if actual_label == DRAW_LABEL_UPSET:
                true_positive += 1

        for label in (DRAW_LABEL_UPSET, DRAW_LABEL_NONE):
            if predicted_label == label and actual_label == label:
                per_class_counts[label]["tp"] += 1
            elif predicted_label == label and actual_label != label:
                per_class_counts[label]["fp"] += 1
            elif predicted_label != label and actual_label == label:
                per_class_counts[label]["fn"] += 1

    draw_precision = true_positive / predicted_draws if predicted_draws else 0.0
    draw_recall = true_positive / true_draws if true_draws else 0.0
    draw_f1 = (
        2 * draw_precision * draw_recall / (draw_precision + draw_recall)
        if (draw_precision + draw_recall)
        else 0.0
    )

    per_class: dict[str, dict[str, float]] = {}
    for label, counts in per_class_counts.items():
        precision = counts["tp"] / (counts["tp"] + counts["fp"]) if (counts["tp"] + counts["fp"]) else 0.0
        recall = counts["tp"] / (counts["tp"] + counts["fn"]) if (counts["tp"] + counts["fn"]) else 0.0
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "support": sum(1 for prediction in prediction_list if prediction.actual_label == label),
        }

    return DrawThresholdPolicyResult(
        threshold=threshold,
        accuracy=correct / len(prediction_list) if prediction_list else 0.0,
        draw_precision=draw_precision,
        draw_recall=draw_recall,
        draw_f1=draw_f1,
        predicted_draws=predicted_draws,
        candidate_rate=predicted_draws / len(prediction_list) if prediction_list else 0.0,
        per_class=per_class,
    )


def recommend_draw_threshold(
    predictions: Iterable[DrawPredictionRow],
    accuracy_floor: float = 0.60,
    min_predicted_draws: int = 10,
    thresholds: Iterable[float] | None = None,
) -> DrawThresholdPolicyResult:
    prediction_list = list(predictions)
    candidate_thresholds = list(thresholds or [value / 100 for value in range(20, 81)])
    evaluated = [
        evaluate_draw_threshold_policy(prediction_list, threshold=threshold)
        for threshold in candidate_thresholds
    ]

    valid = [
        result
        for result in evaluated
        if result.accuracy >= accuracy_floor and result.predicted_draws >= min_predicted_draws
    ]
    pool = valid or [result for result in evaluated if result.accuracy >= accuracy_floor] or evaluated
    return max(
        pool,
        key=lambda result: (
            result.draw_f1,
            result.draw_precision,
            result.accuracy,
            -abs(result.candidate_rate - 0.12),
        ),
    )


def save_draw_training_report(artifact: SoftmaxModelArtifact, output_path: Path | None = None) -> Path:
    TRAINING_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    target = output_path or TRAINING_REPORT_DIR / (
        f"draw_upset_training_report_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    report = {
        "created_at_utc": artifact.created_at_utc,
        "validation_season": artifact.validation_season,
        "train_size": artifact.train_size,
        "validation_size": artifact.validation_size,
        "class_weights": artifact.class_weights,
        "metrics": artifact.metrics,
        "decision_threshold": artifact.decision_threshold,
        "decision_metrics": artifact.decision_metrics,
        "feature_names": artifact.feature_names,
    }
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def save_draw_prediction_report(predictions: Iterable[DrawPredictionRow], output_path: Path | None = None) -> Path:
    PREDICTION_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    target = output_path or PREDICTION_REPORT_DIR / (
        f"draw_upset_predictions_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    payload = {"predictions": [asdict(row) for row in predictions]}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
