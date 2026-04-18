from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from upset_model.config import MODELS_DIR, PREDICTION_REPORT_DIR, TRAINING_REPORT_DIR
from upset_model.standardize import FEATURE_COLUMNS, TrainingRow, UPSET_LABELS


@dataclass
class SplitDataset:
    train_rows: list[TrainingRow]
    validation_rows: list[TrainingRow]
    validation_season: str


@dataclass
class SoftmaxModelArtifact:
    created_at_utc: str
    labels: list[str]
    feature_names: list[str]
    feature_means: list[float]
    feature_stds: list[float]
    weights: list[list[float]]
    class_weights: dict[str, float]
    validation_season: str
    train_size: int
    validation_size: int
    metrics: dict[str, object]
    decision_threshold: float | None = None
    decision_metrics: dict[str, object] | None = None
    betting_policy: dict[str, object] | None = None
    training_competition_scope: str | None = None
    training_competitions: list[str] | None = None
    training_market_profile: str | None = None


@dataclass
class PredictionRow:
    match_date: str
    kickoff_time: str
    competition_code: str
    competition_name: str
    season_key: str
    home_team: str
    away_team: str
    home_upset_probability: float
    away_upset_probability: float
    non_upset_probability: float
    upset_score: float
    candidate_label: str
    candidate_probability: float
    predicted_label: str
    actual_label: str
    explanation: str
    draw_upset_probability: float | None = None
    combined_candidate_label: str | None = None
    combined_candidate_probability: float | None = None
    secondary_candidate_label: str | None = None
    secondary_candidate_probability: float | None = None
    bet_direction: str | None = None
    bet_confidence: str | None = None
    bet_recommendation: str | None = None
    bet_reason: str | None = None
    direction_probability: float | None = None
    direction_gap: float | None = None
    bet_confidence_score: float | None = None


@dataclass
class ThresholdPolicyResult:
    threshold: float
    accuracy: float
    upset_precision: float
    upset_recall: float
    upset_f1: float
    predicted_upsets: int
    candidate_rate: float
    per_class: dict[str, dict[str, float]]


def split_rows_by_latest_season(rows: Iterable[TrainingRow], validation_season: str | None = None) -> SplitDataset:
    row_list = sorted(rows, key=lambda row: (row.season_key, row.match_date, row.kickoff_time, row.home_team))
    seasons = sorted({row.season_key for row in row_list})
    if len(seasons) < 2:
        raise ValueError("Need at least two seasons to create a train/validation split")

    selected_validation_season = validation_season or seasons[-1]
    train_rows = [row for row in row_list if row.season_key < selected_validation_season]
    validation_rows = [row for row in row_list if row.season_key == selected_validation_season]
    if not train_rows or not validation_rows:
        raise ValueError("Train/validation split is empty")
    return SplitDataset(
        train_rows=train_rows,
        validation_rows=validation_rows,
        validation_season=selected_validation_season,
    )


def compute_class_weights(
    rows: Iterable[TrainingRow],
    strategy: str = "balanced",
    labels: Iterable[str] | None = None,
) -> dict[str, float]:
    if strategy not in {"none", "balanced", "sqrt_balanced"}:
        raise ValueError(f"Unsupported class-weight strategy: {strategy}")

    rows_list = list(rows)
    selected_labels = list(labels or UPSET_LABELS)
    supports = {label: 0 for label in selected_labels}
    for row in rows_list:
        if row.upset_label in supports:
            supports[row.upset_label] += 1

    if strategy == "none":
        return {label: 1.0 for label in selected_labels}

    total = len(rows_list)
    base_weights = {
        label: (total / (len(selected_labels) * count)) if count else 1.0
        for label, count in supports.items()
    }
    if strategy == "balanced":
        return base_weights
    return {label: math.sqrt(weight) for label, weight in base_weights.items()}


def _feature_value(row: TrainingRow, name: str) -> float | None:
    value = getattr(row, name)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def compute_feature_stats(rows: Iterable[TrainingRow], feature_names: list[str]) -> tuple[list[float], list[float]]:
    row_list = list(rows)
    means: list[float] = []
    stds: list[float] = []
    for feature_name in feature_names:
        values = [_feature_value(row, feature_name) for row in row_list]
        present_values = [value for value in values if value is not None]
        if not present_values:
            means.append(0.0)
            stds.append(1.0)
            continue
        mean = sum(present_values) / len(present_values)
        variance = sum((value - mean) ** 2 for value in present_values) / len(present_values)
        means.append(mean)
        stds.append(math.sqrt(variance) or 1.0)
    return means, stds


def vectorize_row(row: TrainingRow, feature_names: list[str], means: list[float], stds: list[float]) -> list[float]:
    vector: list[float] = []
    for feature_name, mean, std in zip(feature_names, means, stds):
        value = _feature_value(row, feature_name)
        effective_value = mean if value is None else value
        vector.append((effective_value - mean) / std if std else 0.0)
    return vector


def _softmax(logits: list[float]) -> list[float]:
    max_logit = max(logits)
    exps = [math.exp(logit - max_logit) for logit in logits]
    total = sum(exps)
    return [value / total for value in exps]


def _dot(lhs: list[float], rhs: list[float]) -> float:
    return sum(left * right for left, right in zip(lhs, rhs))


def _predict_probabilities_from_vector(vector: list[float], weights: list[list[float]]) -> list[float]:
    logits = []
    for class_weights in weights:
        bias = class_weights[-1]
        logits.append(_dot(vector, class_weights[:-1]) + bias)
    return _softmax(logits)


def train_softmax_model(
    split: SplitDataset,
    feature_names: list[str] | None = None,
    labels: list[str] | None = None,
    epochs: int = 180,
    learning_rate: float = 0.06,
    l2: float = 0.0005,
    class_weight_strategy: str = "sqrt_balanced",
) -> SoftmaxModelArtifact:
    selected_feature_names = list(feature_names or FEATURE_COLUMNS)
    selected_labels = list(labels or UPSET_LABELS)
    label_to_index = {label: index for index, label in enumerate(selected_labels)}
    sample_class_weights = compute_class_weights(
        split.train_rows,
        strategy=class_weight_strategy,
        labels=selected_labels,
    )

    means, stds = compute_feature_stats(split.train_rows, selected_feature_names)
    train_vectors = [vectorize_row(row, selected_feature_names, means, stds) for row in split.train_rows]
    validation_vectors = [vectorize_row(row, selected_feature_names, means, stds) for row in split.validation_rows]
    train_targets = [label_to_index[row.upset_label] for row in split.train_rows]

    weights = [[0.0 for _ in range(len(selected_feature_names) + 1)] for _ in selected_labels]
    sample_count = len(train_vectors)

    for epoch_index in range(epochs):
        gradients = [[0.0 for _ in range(len(selected_feature_names) + 1)] for _ in selected_labels]
        for vector, target_index in zip(train_vectors, train_targets):
            probabilities = _predict_probabilities_from_vector(vector, weights)
            sample_weight = sample_class_weights[selected_labels[target_index]]
            for class_index, probability in enumerate(probabilities):
                error = sample_weight * (probability - (1.0 if class_index == target_index else 0.0))
                for feature_index, value in enumerate(vector):
                    gradients[class_index][feature_index] += error * value
                gradients[class_index][-1] += error

        effective_learning_rate = learning_rate / math.sqrt(epoch_index + 1)
        for class_index, class_weight_vector in enumerate(weights):
            for weight_index, _ in enumerate(class_weight_vector[:-1]):
                regularization = l2 * class_weight_vector[weight_index]
                gradients[class_index][weight_index] = gradients[class_index][weight_index] / sample_count + regularization
            gradients[class_index][-1] = gradients[class_index][-1] / sample_count

            for weight_index in range(len(class_weight_vector)):
                class_weight_vector[weight_index] -= effective_learning_rate * gradients[class_index][weight_index]

    metrics = evaluate_model(
        rows=split.validation_rows,
        vectors=validation_vectors,
        weights=weights,
        labels=selected_labels,
    )

    return SoftmaxModelArtifact(
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        labels=selected_labels,
        feature_names=selected_feature_names,
        feature_means=means,
        feature_stds=stds,
        weights=weights,
        class_weights=sample_class_weights,
        validation_season=split.validation_season,
        train_size=len(split.train_rows),
        validation_size=len(split.validation_rows),
        metrics=metrics,
    )


def predict_row_probabilities(row: TrainingRow, artifact: SoftmaxModelArtifact) -> dict[str, float]:
    vector = vectorize_row(
        row=row,
        feature_names=artifact.feature_names,
        means=artifact.feature_means,
        stds=artifact.feature_stds,
    )
    probabilities = _predict_probabilities_from_vector(vector=vector, weights=artifact.weights)
    return {label: probability for label, probability in zip(artifact.labels, probabilities)}


def choose_predicted_label(
    probabilities: dict[str, float],
    threshold: float | None = None,
) -> tuple[str, str, float, float]:
    upset_score = probabilities["home_upset_win"] + probabilities["away_upset_win"]
    candidate_label = (
        "home_upset_win"
        if probabilities["home_upset_win"] >= probabilities["away_upset_win"]
        else "away_upset_win"
    )
    candidate_probability = probabilities[candidate_label]
    if threshold is None:
        predicted_label = max(probabilities, key=probabilities.get)
    else:
        predicted_label = candidate_label if candidate_probability >= threshold else "non_upset"
    return predicted_label, candidate_label, candidate_probability, upset_score


def evaluate_model(
    rows: list[TrainingRow],
    vectors: list[list[float]],
    weights: list[list[float]],
    labels: list[str],
) -> dict[str, object]:
    label_to_index = {label: index for index, label in enumerate(labels)}
    positive_labels = [label for label in labels if not label.startswith("non_")]
    predictions: list[dict[str, object]] = []
    correct = 0
    log_loss_total = 0.0

    for row, vector in zip(rows, vectors):
        probabilities = _predict_probabilities_from_vector(vector=vector, weights=weights)
        predicted_index = max(range(len(labels)), key=lambda index: probabilities[index])
        true_index = label_to_index[row.upset_label]
        if predicted_index == true_index:
            correct += 1
        log_loss_total += -math.log(max(probabilities[true_index], 1e-12))
        predictions.append(
            {
                "row": row,
                "probabilities": probabilities,
                "probabilities_by_label": {label: probability for label, probability in zip(labels, probabilities)},
                "predicted_label": labels[predicted_index],
                "upset_score": sum(probabilities[label_to_index[label]] for label in positive_labels),
            }
        )

    per_class: dict[str, dict[str, float]] = {}
    for label in labels:
        true_positive = 0
        false_positive = 0
        false_negative = 0
        for prediction in predictions:
            actual = prediction["row"].upset_label
            predicted = prediction["predicted_label"]
            if predicted == label and actual == label:
                true_positive += 1
            elif predicted == label and actual != label:
                false_positive += 1
            elif predicted != label and actual == label:
                false_negative += 1
        precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
        recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "support": sum(1 for prediction in predictions if prediction["row"].upset_label == label),
        }

    sorted_predictions = sorted(predictions, key=lambda item: item["upset_score"], reverse=True)
    top_k_metrics: dict[str, float] = {}
    for limit in (10, 20, 50):
        if not sorted_predictions:
            top_k_metrics[f"top_{limit}_upset_precision"] = 0.0
            continue
        subset = sorted_predictions[: min(limit, len(sorted_predictions))]
        hits = sum(1 for item in subset if item["row"].upset_label in positive_labels)
        top_k_metrics[f"top_{limit}_upset_precision"] = hits / len(subset)

    directional_top_k_metrics: dict[str, float] = {}
    for limit in (10, 20, 50):
        for label in positive_labels:
            ranked = sorted(
                predictions,
                key=lambda item: item["probabilities_by_label"][label],
                reverse=True,
            )
            if not ranked:
                directional_top_k_metrics[f"top_{limit}_{label}_precision"] = 0.0
                continue
            subset = ranked[: min(limit, len(ranked))]
            hits = sum(1 for item in subset if item["row"].upset_label == label)
            directional_top_k_metrics[f"top_{limit}_{label}_precision"] = hits / len(subset)

    return {
        "accuracy": correct / len(predictions) if predictions else 0.0,
        "log_loss": log_loss_total / len(predictions) if predictions else 0.0,
        "per_class": per_class,
        **top_k_metrics,
        **directional_top_k_metrics,
    }


def evaluate_threshold_policy(
    predictions: Iterable[PredictionRow],
    threshold: float,
) -> ThresholdPolicyResult:
    prediction_list = list(predictions)
    correct = 0
    predicted_upsets = 0
    true_upsets = 0
    true_positive = 0
    per_class_counts = {
        label: {"tp": 0, "fp": 0, "fn": 0}
        for label in UPSET_LABELS
    }

    for prediction in prediction_list:
        predicted_label = prediction.candidate_label if prediction.candidate_probability >= threshold else "non_upset"
        actual_label = prediction.actual_label
        if predicted_label == actual_label:
            correct += 1
        if actual_label != "non_upset":
            true_upsets += 1
        if predicted_label != "non_upset":
            predicted_upsets += 1
            if actual_label != "non_upset":
                true_positive += 1

        for label in UPSET_LABELS:
            if predicted_label == label and actual_label == label:
                per_class_counts[label]["tp"] += 1
            elif predicted_label == label and actual_label != label:
                per_class_counts[label]["fp"] += 1
            elif predicted_label != label and actual_label == label:
                per_class_counts[label]["fn"] += 1

    upset_precision = true_positive / predicted_upsets if predicted_upsets else 0.0
    upset_recall = true_positive / true_upsets if true_upsets else 0.0
    upset_f1 = (
        2 * upset_precision * upset_recall / (upset_precision + upset_recall)
        if (upset_precision + upset_recall)
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

    return ThresholdPolicyResult(
        threshold=threshold,
        accuracy=correct / len(prediction_list) if prediction_list else 0.0,
        upset_precision=upset_precision,
        upset_recall=upset_recall,
        upset_f1=upset_f1,
        predicted_upsets=predicted_upsets,
        candidate_rate=predicted_upsets / len(prediction_list) if prediction_list else 0.0,
        per_class=per_class,
    )


def recommend_decision_threshold(
    predictions: Iterable[PredictionRow],
    accuracy_floor: float = 0.60,
    min_predicted_upsets: int = 20,
    thresholds: Iterable[float] | None = None,
) -> ThresholdPolicyResult:
    prediction_list = list(predictions)
    candidate_thresholds = list(thresholds or [value / 100 for value in range(20, 81)])
    evaluated = [
        evaluate_threshold_policy(prediction_list, threshold=threshold)
        for threshold in candidate_thresholds
    ]

    valid = [
        result
        for result in evaluated
        if result.accuracy >= accuracy_floor and result.predicted_upsets >= min_predicted_upsets
    ]
    pool = valid or [result for result in evaluated if result.accuracy >= accuracy_floor] or evaluated
    return max(
        pool,
        key=lambda result: (
            result.upset_f1,
            result.upset_precision,
            result.accuracy,
            -abs(result.candidate_rate - 0.15),
        ),
    )


def save_model_artifact(artifact: SoftmaxModelArtifact, output_path: Path | None = None) -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    target = output_path or MODELS_DIR / "football_data_softmax_model.json"
    target.write_text(json.dumps(asdict(artifact), ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def load_model_artifact(input_path: Path | None = None) -> SoftmaxModelArtifact:
    source = input_path or MODELS_DIR / "football_data_softmax_model.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    return SoftmaxModelArtifact(**payload)


def _format_float(value: float | None, signed: bool = False) -> str:
    if value is None:
        return "NA"
    return f"{value:+.2f}" if signed else f"{value:.2f}"


def build_prediction_explanation(row: TrainingRow, candidate_label: str) -> str:
    parts: list[str] = []

    if candidate_label == "home_upset_win":
        parts.append(
            f"主胜赔率 {_format_float(row.open_home_odds)} -> {_format_float(row.close_home_odds)}，"
            f"变化 {_format_float(row.feature_home_odds_delta, signed=True)}"
        )
    else:
        parts.append(
            f"客胜赔率 {_format_float(row.open_away_odds)} -> {_format_float(row.close_away_odds)}，"
            f"变化 {_format_float(row.feature_away_odds_delta, signed=True)}"
        )

    parts.append(
        f"最低赔与次低赔差距 {_format_float(row.feature_favorite_gap_open)} -> "
        f"{_format_float(row.feature_favorite_gap_close)}"
    )

    if row.open_ah_line is not None or row.close_ah_line is not None:
        parts.append(
            f"亚盘 { _format_float(row.open_ah_line, signed=True) } -> "
            f"{ _format_float(row.close_ah_line, signed=True) }"
        )
    elif row.open_over25_odds is not None or row.close_over25_odds is not None:
        parts.append(
            f"大2.5赔率 {_format_float(row.open_over25_odds)} -> {_format_float(row.close_over25_odds)}"
        )

    return "；".join(parts)


def save_training_report(artifact: SoftmaxModelArtifact, output_path: Path | None = None) -> Path:
    TRAINING_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    target = output_path or TRAINING_REPORT_DIR / (
        f"football_data_training_report_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
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
        "betting_policy": artifact.betting_policy,
        "training_competition_scope": artifact.training_competition_scope,
        "training_competitions": artifact.training_competitions,
        "training_market_profile": artifact.training_market_profile,
        "feature_names": artifact.feature_names,
    }
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def score_rows(rows: Iterable[TrainingRow], artifact: SoftmaxModelArtifact) -> list[PredictionRow]:
    scored_rows: list[PredictionRow] = []
    for row in rows:
        probabilities = predict_row_probabilities(row, artifact)
        predicted_label, candidate_label, candidate_probability, upset_score = choose_predicted_label(
            probabilities=probabilities,
            threshold=artifact.decision_threshold,
        )
        scored_rows.append(
            PredictionRow(
                match_date=row.match_date,
                kickoff_time=row.kickoff_time,
                competition_code=row.competition_code,
                competition_name=row.competition_name,
                season_key=row.season_key,
                home_team=row.home_team,
                away_team=row.away_team,
                home_upset_probability=probabilities["home_upset_win"],
                away_upset_probability=probabilities["away_upset_win"],
                non_upset_probability=probabilities["non_upset"],
                upset_score=upset_score,
                candidate_label=candidate_label,
                candidate_probability=candidate_probability,
                predicted_label=predicted_label,
                actual_label=row.upset_label,
                explanation=build_prediction_explanation(row, candidate_label),
            )
        )
    scored_rows.sort(key=lambda row: (row.match_date, -row.upset_score, row.competition_code, row.home_team))
    return scored_rows


def save_prediction_report(predictions: Iterable[PredictionRow], output_path: Path | None = None) -> Path:
    PREDICTION_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    target = output_path or PREDICTION_REPORT_DIR / (
        f"football_data_predictions_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    payload = {"predictions": [asdict(row) for row in predictions]}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
