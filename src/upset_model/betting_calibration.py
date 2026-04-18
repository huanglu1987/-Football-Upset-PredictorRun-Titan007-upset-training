from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from upset_model.draw_model import DrawPredictionRow, score_draw_rows
from upset_model.modeling import PredictionRow, SoftmaxModelArtifact, score_rows
from upset_model.standardize import DRAW_LABEL_UPSET, UPSET_LABEL_NONE, TrainingRow, relabel_rows_for_draw


DEFAULT_MIN_DIRECTION_GAP = 0.06
DEFAULT_CONFIDENCE_GAP_WEIGHT = 0.50
DEFAULT_MIN_PREDICTED_MATCHES = 30
DEFAULT_MIN_BUCKET_SIZE = 10
DEFAULT_MIN_WEAK_REMAINDER = 20
DEFAULT_DYNAMIC_BUCKET_RATE = 0.08
DEFAULT_DYNAMIC_BUCKET_CAP = 50


@dataclass(frozen=True)
class BettingDirectionPolicyResult:
    threshold: float
    precision: float
    recall: float
    f1: float
    actionable_count: int
    candidate_rate: float
    total_hits: int
    total_positive: int


@dataclass(frozen=True)
class BettingConfidenceBucketResult:
    threshold: float | None
    count: int
    hits: int
    precision: float
    min_priority: float | None
    max_priority: float | None


@dataclass(frozen=True)
class BettingConfidenceBucketRange:
    label: str
    min_priority: float | None
    max_priority: float | None
    count: int
    hits: int
    precision: float


def _prediction_key(prediction: PredictionRow | DrawPredictionRow | TrainingRow) -> tuple[str, str, str, str, str]:
    return (
        prediction.match_date,
        prediction.kickoff_time,
        prediction.competition_code,
        prediction.home_team,
        prediction.away_team,
    )


def _apply_combined_ranking_fields(predictions: list[PredictionRow]) -> None:
    for prediction in predictions:
        candidate_scores = [
            ("home_upset_win", prediction.home_upset_probability),
            ("away_upset_win", prediction.away_upset_probability),
        ]
        if prediction.draw_upset_probability is not None:
            candidate_scores.append(("draw_upset", prediction.draw_upset_probability))
        ranked = sorted(candidate_scores, key=lambda item: (item[1], item[0]), reverse=True)
        prediction.combined_candidate_label = ranked[0][0]
        prediction.combined_candidate_probability = ranked[0][1]
        if len(ranked) > 1:
            prediction.secondary_candidate_label = ranked[1][0]
            prediction.secondary_candidate_probability = ranked[1][1]
        else:
            prediction.secondary_candidate_label = None
            prediction.secondary_candidate_probability = None


def build_validation_predictions(
    validation_rows: Iterable[TrainingRow],
    *,
    main_artifact: SoftmaxModelArtifact,
    draw_artifact: SoftmaxModelArtifact,
) -> list[PredictionRow]:
    validation_list = list(validation_rows)
    predictions = score_rows(validation_list, main_artifact)
    draw_rows = relabel_rows_for_draw(validation_list)
    draw_predictions = score_draw_rows(draw_rows, draw_artifact)
    draw_probability_by_match = {
        _prediction_key(prediction): prediction
        for prediction in draw_predictions
    }
    draw_actual_by_match = {
        _prediction_key(row): row.upset_label
        for row in draw_rows
    }

    for prediction in predictions:
        match_key = _prediction_key(prediction)
        draw_prediction = draw_probability_by_match.get(match_key)
        if draw_prediction is not None:
            prediction.draw_upset_probability = draw_prediction.draw_upset_probability
        if draw_actual_by_match.get(match_key) == DRAW_LABEL_UPSET:
            prediction.actual_label = DRAW_LABEL_UPSET

    _apply_combined_ranking_fields(predictions)
    return predictions


def _combined_direction_score(
    prediction: PredictionRow,
    *,
    main_direction_threshold: float,
    draw_threshold: float,
) -> tuple[float, float]:
    combined_label = prediction.combined_candidate_label or prediction.candidate_label
    if combined_label == "draw_upset":
        return prediction.draw_upset_probability or 0.0, draw_threshold
    if combined_label == "home_upset_win":
        return prediction.home_upset_probability, main_direction_threshold
    return prediction.away_upset_probability, main_direction_threshold


def _direction_gap(prediction: PredictionRow) -> float:
    primary = prediction.combined_candidate_probability or prediction.candidate_probability
    secondary = prediction.secondary_candidate_probability or 0.0
    return primary - secondary


def _is_actionable_prediction(
    prediction: PredictionRow,
    *,
    main_direction_threshold: float,
    draw_threshold: float,
    min_direction_gap: float,
) -> bool:
    score, threshold = _combined_direction_score(
        prediction,
        main_direction_threshold=main_direction_threshold,
        draw_threshold=draw_threshold,
    )
    return score >= threshold and _direction_gap(prediction) >= min_direction_gap


def evaluate_betting_direction_threshold(
    predictions: Iterable[PredictionRow],
    *,
    main_direction_threshold: float,
    draw_threshold: float,
    min_direction_gap: float = DEFAULT_MIN_DIRECTION_GAP,
) -> BettingDirectionPolicyResult:
    prediction_list = list(predictions)
    actual_positive = sum(1 for prediction in prediction_list if prediction.actual_label != UPSET_LABEL_NONE)
    actionable_predictions = [
        prediction
        for prediction in prediction_list
        if _is_actionable_prediction(
            prediction,
            main_direction_threshold=main_direction_threshold,
            draw_threshold=draw_threshold,
            min_direction_gap=min_direction_gap,
        )
    ]
    hits = sum(
        1
        for prediction in actionable_predictions
        if (prediction.combined_candidate_label or prediction.candidate_label) == prediction.actual_label
    )
    precision = hits / len(actionable_predictions) if actionable_predictions else 0.0
    recall = hits / actual_positive if actual_positive else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return BettingDirectionPolicyResult(
        threshold=main_direction_threshold,
        precision=precision,
        recall=recall,
        f1=f1,
        actionable_count=len(actionable_predictions),
        candidate_rate=len(actionable_predictions) / len(prediction_list) if prediction_list else 0.0,
        total_hits=hits,
        total_positive=actual_positive,
    )


def recommend_betting_direction_threshold(
    predictions: Iterable[PredictionRow],
    *,
    draw_threshold: float,
    min_direction_gap: float = DEFAULT_MIN_DIRECTION_GAP,
    min_predicted_matches: int = DEFAULT_MIN_PREDICTED_MATCHES,
    thresholds: Iterable[float] | None = None,
) -> BettingDirectionPolicyResult:
    prediction_list = list(predictions)
    candidate_thresholds = list(thresholds or [value / 100 for value in range(25, 71)])
    evaluated = [
        evaluate_betting_direction_threshold(
            prediction_list,
            main_direction_threshold=threshold,
            draw_threshold=draw_threshold,
            min_direction_gap=min_direction_gap,
        )
        for threshold in candidate_thresholds
    ]
    pool = [
        result
        for result in evaluated
        if result.actionable_count >= min_predicted_matches
    ] or evaluated
    return max(
        pool,
        key=lambda result: (
            result.f1,
            result.precision,
            result.actionable_count,
            -abs(result.candidate_rate - 0.35),
        ),
    )


def _priority_score(*, score: float, threshold: float, direction_gap: float, gap_weight: float) -> float:
    return max(score - threshold, 0.0) + gap_weight * direction_gap


def _precision(rows: list[tuple[float, bool]]) -> float:
    if not rows:
        return 0.0
    return sum(1 for _, hit in rows if hit) / len(rows)


def _bucket_result(
    rows: list[tuple[float, bool]],
    *,
    threshold: float | None,
) -> BettingConfidenceBucketResult:
    hits = sum(1 for _, hit in rows if hit)
    priorities = [priority for priority, _ in rows]
    return BettingConfidenceBucketResult(
        threshold=threshold,
        count=len(rows),
        hits=hits,
        precision=hits / len(rows) if rows else 0.0,
        min_priority=min(priorities) if priorities else None,
        max_priority=max(priorities) if priorities else None,
    )


def _effective_min_bucket_size(total_count: int, configured_min: int) -> int:
    if total_count < 300:
        return configured_min
    dynamic_min = int(total_count * DEFAULT_DYNAMIC_BUCKET_RATE)
    return max(configured_min, min(DEFAULT_DYNAMIC_BUCKET_CAP, dynamic_min))


def _segment_hits(prefix_hits: list[int], start: int, end: int) -> int:
    return prefix_hits[end] - prefix_hits[start]


def _segment_precision(prefix_hits: list[int], start: int, end: int) -> float:
    count = end - start
    if count <= 0:
        return 0.0
    return _segment_hits(prefix_hits, start, end) / count


def _bucket_range_payload(
    label: str,
    rows: list[tuple[float, bool]],
) -> BettingConfidenceBucketRange:
    hits = sum(1 for _, hit in rows if hit)
    priorities = [priority for priority, _ in rows]
    return BettingConfidenceBucketRange(
        label=label,
        min_priority=min(priorities) if priorities else None,
        max_priority=max(priorities) if priorities else None,
        count=len(rows),
        hits=hits,
        precision=hits / len(rows) if rows else 0.0,
    )


def _fallback_confidence_bucket_payload(
    actionable_rows: list[tuple[float, bool]],
    *,
    effective_min_bucket_size: int,
) -> dict[str, object]:
    total_count = len(actionable_rows)
    if total_count == 0:
        empty_bucket = _bucket_range_payload("强", [])
        return {
            "strong_confidence_threshold": None,
            "medium_confidence_threshold": None,
            "overall_actionable_precision": 0.0,
            "overall_actionable_count": 0,
            "strong_floor": 0.0,
            "medium_floor": 0.0,
            "effective_min_bucket_size": effective_min_bucket_size,
            "confidence_bucket_strategy": "empty",
            "confidence_buckets": [],
            "strong_bucket": empty_bucket.__dict__,
            "medium_bucket": _bucket_range_payload("中", []).__dict__,
            "weak_bucket": _bucket_range_payload("弱", []).__dict__,
        }

    if total_count < 3 * effective_min_bucket_size:
        base_bucket_size = max(1, total_count // 3)
        strong_rows = actionable_rows[-base_bucket_size:]
        medium_rows = actionable_rows[-2 * base_bucket_size : -base_bucket_size]
        weak_rows = actionable_rows[: -2 * base_bucket_size]
    else:
        strong_start = total_count - effective_min_bucket_size
        medium_start = max(effective_min_bucket_size, strong_start - effective_min_bucket_size)
        weak_rows = actionable_rows[:medium_start]
        medium_rows = actionable_rows[medium_start:strong_start]
        strong_rows = actionable_rows[strong_start:]

    strong_bucket = _bucket_range_payload("强", strong_rows)
    medium_bucket = _bucket_range_payload("中", medium_rows)
    weak_bucket = _bucket_range_payload("弱", weak_rows)
    return {
        "strong_confidence_threshold": None,
        "medium_confidence_threshold": None,
        "overall_actionable_precision": _precision(actionable_rows),
        "overall_actionable_count": total_count,
        "strong_floor": strong_bucket.precision,
        "medium_floor": medium_bucket.precision,
        "effective_min_bucket_size": effective_min_bucket_size,
        "confidence_bucket_strategy": "fallback_split",
        "confidence_buckets": [
            strong_bucket.__dict__,
            medium_bucket.__dict__,
            weak_bucket.__dict__,
        ],
        "strong_bucket": strong_bucket.__dict__,
        "medium_bucket": medium_bucket.__dict__,
        "weak_bucket": weak_bucket.__dict__,
    }


def _recommend_interval_confidence_buckets(
    actionable_rows: list[tuple[float, bool]],
    *,
    effective_min_bucket_size: int,
    min_weak_remainder: int,
) -> dict[str, object] | None:
    total_count = len(actionable_rows)
    minimum_weak_count = max(effective_min_bucket_size, min_weak_remainder)
    if total_count < minimum_weak_count + 2 * effective_min_bucket_size:
        return None

    prefix_hits = [0]
    for _, hit in actionable_rows:
        prefix_hits.append(prefix_hits[-1] + int(hit))

    best_candidate: tuple[tuple[float, float, float, int, int, int, int], int, int] | None = None
    for medium_start in range(minimum_weak_count, total_count - 2 * effective_min_bucket_size + 1):
        for strong_start in range(medium_start + effective_min_bucket_size, total_count - effective_min_bucket_size + 1):
            weak_count = medium_start
            medium_count = strong_start - medium_start
            strong_count = total_count - strong_start
            if weak_count < minimum_weak_count:
                continue
            if medium_count < effective_min_bucket_size or strong_count < effective_min_bucket_size:
                continue

            weak_precision = _segment_precision(prefix_hits, 0, medium_start)
            medium_precision = _segment_precision(prefix_hits, medium_start, strong_start)
            strong_precision = _segment_precision(prefix_hits, strong_start, total_count)
            if strong_precision < medium_precision or medium_precision < weak_precision:
                continue

            strong_hits = _segment_hits(prefix_hits, strong_start, total_count)
            medium_hits = _segment_hits(prefix_hits, medium_start, strong_start)
            candidate_key = (
                strong_precision,
                medium_precision,
                -weak_precision,
                strong_hits,
                medium_hits,
                strong_count,
                medium_count,
            )
            if best_candidate is None or candidate_key > best_candidate[0]:
                best_candidate = (candidate_key, medium_start, strong_start)

    if best_candidate is None:
        return None

    _, medium_start, strong_start = best_candidate
    weak_rows = actionable_rows[:medium_start]
    medium_rows = actionable_rows[medium_start:strong_start]
    strong_rows = actionable_rows[strong_start:]

    strong_bucket = _bucket_range_payload("强", strong_rows)
    medium_bucket = _bucket_range_payload("中", medium_rows)
    weak_bucket = _bucket_range_payload("弱", weak_rows)
    return {
        "strong_confidence_threshold": strong_bucket.min_priority,
        "medium_confidence_threshold": medium_bucket.min_priority,
        "overall_actionable_precision": _precision(actionable_rows),
        "overall_actionable_count": total_count,
        "strong_floor": strong_bucket.precision,
        "medium_floor": medium_bucket.precision,
        "effective_min_bucket_size": effective_min_bucket_size,
        "confidence_bucket_strategy": "interval_search",
        "confidence_buckets": [
            strong_bucket.__dict__,
            medium_bucket.__dict__,
            weak_bucket.__dict__,
        ],
        "strong_bucket": strong_bucket.__dict__,
        "medium_bucket": medium_bucket.__dict__,
        "weak_bucket": weak_bucket.__dict__,
    }


def recommend_confidence_bucket_thresholds(
    predictions: Iterable[PredictionRow],
    *,
    main_direction_threshold: float,
    draw_threshold: float,
    min_direction_gap: float = DEFAULT_MIN_DIRECTION_GAP,
    gap_weight: float = DEFAULT_CONFIDENCE_GAP_WEIGHT,
    min_bucket_size: int = DEFAULT_MIN_BUCKET_SIZE,
    min_weak_remainder: int = DEFAULT_MIN_WEAK_REMAINDER,
) -> dict[str, object]:
    actionable_rows: list[tuple[float, bool]] = []
    for prediction in predictions:
        if not _is_actionable_prediction(
            prediction,
            main_direction_threshold=main_direction_threshold,
            draw_threshold=draw_threshold,
            min_direction_gap=min_direction_gap,
        ):
            continue
        score, threshold = _combined_direction_score(
            prediction,
            main_direction_threshold=main_direction_threshold,
            draw_threshold=draw_threshold,
        )
        priority = _priority_score(
            score=score,
            threshold=threshold,
            direction_gap=_direction_gap(prediction),
            gap_weight=gap_weight,
        )
        hit = (prediction.combined_candidate_label or prediction.candidate_label) == prediction.actual_label
        actionable_rows.append((priority, hit))

    actionable_rows.sort(key=lambda item: item[0])
    total_count = len(actionable_rows)
    effective_min_bucket_size = _effective_min_bucket_size(total_count, min_bucket_size)
    if total_count < max(3, 3 * effective_min_bucket_size):
        return _fallback_confidence_bucket_payload(
            actionable_rows,
            effective_min_bucket_size=effective_min_bucket_size,
        )

    interval_payload = _recommend_interval_confidence_buckets(
        actionable_rows,
        effective_min_bucket_size=effective_min_bucket_size,
        min_weak_remainder=min_weak_remainder,
    )
    if interval_payload is not None:
        return interval_payload
    return _fallback_confidence_bucket_payload(
        actionable_rows,
        effective_min_bucket_size=effective_min_bucket_size,
    )


def calibrate_betting_policy(
    validation_rows: Iterable[TrainingRow],
    *,
    main_artifact: SoftmaxModelArtifact,
    draw_artifact: SoftmaxModelArtifact,
    min_direction_gap: float = DEFAULT_MIN_DIRECTION_GAP,
    gap_weight: float = DEFAULT_CONFIDENCE_GAP_WEIGHT,
    min_predicted_matches: int = DEFAULT_MIN_PREDICTED_MATCHES,
    min_bucket_size: int = DEFAULT_MIN_BUCKET_SIZE,
    min_weak_remainder: int = DEFAULT_MIN_WEAK_REMAINDER,
) -> tuple[SoftmaxModelArtifact, dict[str, object]]:
    predictions = build_validation_predictions(
        validation_rows,
        main_artifact=main_artifact,
        draw_artifact=draw_artifact,
    )
    direction_result = recommend_betting_direction_threshold(
        predictions,
        draw_threshold=draw_artifact.decision_threshold or 0.0,
        min_direction_gap=min_direction_gap,
        min_predicted_matches=min_predicted_matches,
    )
    actionable_predictions = [
        prediction
        for prediction in predictions
        if _is_actionable_prediction(
            prediction,
            main_direction_threshold=direction_result.threshold,
            draw_threshold=draw_artifact.decision_threshold or 0.0,
            min_direction_gap=min_direction_gap,
        )
    ]
    confidence_payload = recommend_confidence_bucket_thresholds(
        predictions,
        main_direction_threshold=direction_result.threshold,
        draw_threshold=draw_artifact.decision_threshold or 0.0,
        min_direction_gap=min_direction_gap,
        gap_weight=gap_weight,
        min_bucket_size=min_bucket_size,
        min_weak_remainder=min_weak_remainder,
    )
    report = {
        "validation_season": main_artifact.validation_season,
        "direction_threshold": direction_result.threshold,
        "direction_precision": direction_result.precision,
        "direction_recall": direction_result.recall,
        "direction_f1": direction_result.f1,
        "actionable_count": direction_result.actionable_count,
        "candidate_rate": direction_result.candidate_rate,
        "total_hits": direction_result.total_hits,
        "total_positive": direction_result.total_positive,
        "draw_threshold": draw_artifact.decision_threshold,
        "min_direction_gap": min_direction_gap,
        "confidence_gap_weight": gap_weight,
        **confidence_payload,
    }
    main_artifact.betting_policy = report
    return main_artifact, report
