from __future__ import annotations

from collections.abc import Iterable

from upset_model.modeling import PredictionRow, SoftmaxModelArtifact

LABEL_TO_BET_DIRECTION = {
    "home_upset_win": "主冷",
    "away_upset_win": "客冷",
    "draw_upset": "冷平",
}

NO_BET_DIRECTION = "不投注"
NO_BET_CONFIDENCE = "不投注"
NO_BET_RECOMMENDATION = "不投注"

CONFIDENCE_RANK = {
    "强": 3,
    "中": 2,
    "弱": 1,
    NO_BET_CONFIDENCE: 0,
}

RECOMMENDATION_RANK = {
    "建议投注": 2,
    "谨慎关注": 1,
    NO_BET_RECOMMENDATION: 0,
}

MIN_DIRECTION_GAP = 0.06
# Validation-season retuning uses a priority score to keep actionable sample volume
# while enforcing `强 > 中 > 弱` on the held-out 2526 season.
CONFIDENCE_PRIORITY_GAP_WEIGHT = 0.50
STRONG_CONFIDENCE_PRIORITY_THRESHOLD = 0.225784
MEDIUM_CONFIDENCE_PRIORITY_THRESHOLD = 0.185494
ACTIONABLE_CONFIDENCES = {"强", "中", "弱"}


def _format_probability(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:.2f}"


def _primary_probability(prediction: PredictionRow) -> float:
    return prediction.combined_candidate_probability or prediction.candidate_probability


def _secondary_probability(prediction: PredictionRow) -> float:
    return prediction.secondary_candidate_probability or 0.0


def _direction_gap(prediction: PredictionRow) -> float:
    return _primary_probability(prediction) - _secondary_probability(prediction)


def _confidence_priority(score: float, threshold: float, direction_gap: float) -> float:
    return max(score - threshold, 0.0) + CONFIDENCE_PRIORITY_GAP_WEIGHT * direction_gap


def _resolve_confidence_bucket(priority_score: float) -> str:
    if priority_score >= STRONG_CONFIDENCE_PRIORITY_THRESHOLD:
        return "强"
    if priority_score >= MEDIUM_CONFIDENCE_PRIORITY_THRESHOLD:
        return "中"
    return "弱"


def _direction_threshold_and_score(
    prediction: PredictionRow,
    *,
    main_artifact: SoftmaxModelArtifact,
    draw_artifact: SoftmaxModelArtifact | None,
) -> tuple[float, float, str]:
    if prediction.combined_candidate_label == "draw_upset":
        threshold = draw_artifact.decision_threshold if draw_artifact and draw_artifact.decision_threshold is not None else 0.0
        score = prediction.draw_upset_probability or prediction.combined_candidate_probability or 0.0
        return threshold, score, "冷平概率"
    threshold = main_artifact.decision_threshold or 0.0
    score = prediction.upset_score
    return threshold, score, "综合冷门分"


def _build_decision_reasons(
    prediction: PredictionRow,
    *,
    main_artifact: SoftmaxModelArtifact,
    draw_artifact: SoftmaxModelArtifact | None,
) -> tuple[str, str, str, float, float, float]:
    candidate_label = prediction.combined_candidate_label or prediction.candidate_label
    direction_gap = _direction_gap(prediction)
    threshold, score, score_label = _direction_threshold_and_score(
        prediction,
        main_artifact=main_artifact,
        draw_artifact=draw_artifact,
    )
    threshold_met = score >= threshold
    gap_met = direction_gap >= MIN_DIRECTION_GAP

    threshold_reason = (
        f"{score_label} {_format_probability(score)}，达到门槛 {_format_probability(threshold)}"
        if threshold_met
        else f"{score_label} {_format_probability(score)}，低于门槛 {_format_probability(threshold)}"
    )
    gap_reason = (
        f"主方向领先次方向 {_format_probability(direction_gap)}，方向更明确"
        if gap_met
        else f"主次方向差仅 {_format_probability(direction_gap)}，信号不够集中"
    )

    if not threshold_met or not gap_met:
        return NO_BET_DIRECTION, NO_BET_CONFIDENCE, NO_BET_RECOMMENDATION, score, direction_gap, 0.0

    confidence_priority = _confidence_priority(score, threshold, direction_gap)
    confidence = _resolve_confidence_bucket(confidence_priority)

    recommendation = "建议投注" if confidence in {"强", "中"} else "谨慎关注"
    return (
        LABEL_TO_BET_DIRECTION.get(candidate_label, NO_BET_DIRECTION),
        confidence,
        recommendation,
        score,
        direction_gap,
        confidence_priority,
    )


def apply_betting_recommendation_fields(
    predictions: Iterable[PredictionRow],
    *,
    main_artifact: SoftmaxModelArtifact,
    draw_artifact: SoftmaxModelArtifact | None,
) -> None:
    for prediction in predictions:
        threshold, score, score_label = _direction_threshold_and_score(
            prediction,
            main_artifact=main_artifact,
            draw_artifact=draw_artifact,
        )
        direction_gap = _direction_gap(prediction)
        bet_direction, bet_confidence, bet_recommendation, _, _, confidence_priority = _build_decision_reasons(
            prediction,
            main_artifact=main_artifact,
            draw_artifact=draw_artifact,
        )

        threshold_reason = (
            f"{score_label} {_format_probability(score)}，达到门槛 {_format_probability(threshold)}"
            if score >= threshold
            else f"{score_label} {_format_probability(score)}，低于门槛 {_format_probability(threshold)}"
        )
        gap_reason = (
            f"主方向领先次方向 {_format_probability(direction_gap)}，方向更明确"
            if direction_gap >= MIN_DIRECTION_GAP
            else f"主次方向差仅 {_format_probability(direction_gap)}，建议观望"
        )
        market_reason = prediction.explanation.strip() if prediction.explanation else ""

        reason_parts = [threshold_reason, gap_reason]
        if market_reason:
            reason_parts.append(market_reason)

        prediction.bet_direction = bet_direction
        prediction.bet_confidence = bet_confidence
        prediction.bet_recommendation = bet_recommendation
        prediction.bet_reason = "；".join(part for part in reason_parts if part)
        prediction.direction_probability = _primary_probability(prediction)
        prediction.direction_gap = direction_gap
        prediction.bet_confidence_score = confidence_priority


def sort_betting_recommendations(predictions: Iterable[PredictionRow]) -> list[PredictionRow]:
    return sorted(
        predictions,
        key=lambda row: (
            RECOMMENDATION_RANK.get(row.bet_recommendation or NO_BET_RECOMMENDATION, 0),
            CONFIDENCE_RANK.get(row.bet_confidence or NO_BET_CONFIDENCE, 0),
            row.bet_confidence_score or 0.0,
            row.direction_probability or 0.0,
            row.direction_gap or 0.0,
            row.upset_score,
        ),
        reverse=True,
    )


def filter_actionable_betting_recommendations(predictions: Iterable[PredictionRow]) -> list[PredictionRow]:
    return [
        prediction
        for prediction in sort_betting_recommendations(predictions)
        if prediction.bet_confidence in ACTIONABLE_CONFIDENCES and prediction.bet_direction != NO_BET_DIRECTION
    ]


def build_final_betting_rows(predictions: Iterable[PredictionRow]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for prediction in filter_actionable_betting_recommendations(predictions):
        rows.append(
            {
                "比赛时间": f"{prediction.match_date} {prediction.kickoff_time}",
                "联赛": prediction.competition_name,
                "对阵": f"{prediction.home_team} vs {prediction.away_team}",
                "等级": prediction.bet_confidence or "",
                "建议方向": prediction.bet_direction or "",
                "原因": prediction.bet_reason or "",
            }
        )
    return rows
