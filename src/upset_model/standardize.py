from __future__ import annotations

import csv
import hashlib
from dataclasses import asdict, dataclass, fields, replace
from datetime import datetime
from pathlib import Path
from typing import Iterable, get_args, get_origin, get_type_hints

from upset_model.config import FEATURES_DIR, FOOTBALL_DATA_COMPETITIONS, FOOTBALL_DATA_RAW_DIR

UPSET_LABEL_HOME = "home_upset_win"
UPSET_LABEL_AWAY = "away_upset_win"
UPSET_LABEL_NONE = "non_upset"
UPSET_LABELS = (UPSET_LABEL_HOME, UPSET_LABEL_AWAY, UPSET_LABEL_NONE)
DRAW_LABEL_UPSET = "draw_upset"
DRAW_LABEL_NONE = "non_draw_upset"
DRAW_LABELS = (DRAW_LABEL_UPSET, DRAW_LABEL_NONE)

COMPETITION_FEATURES = (
    ("E0", "feature_is_premier_league"),
    ("SP1", "feature_is_la_liga"),
    ("D1", "feature_is_bundesliga"),
    ("I1", "feature_is_serie_a"),
    ("F1", "feature_is_ligue_1"),
)
COMPETITION_BUCKET_COUNT = 12
COMPETITION_BUCKET_FEATURE_NAMES = tuple(
    f"feature_competition_bucket_{index}"
    for index in range(COMPETITION_BUCKET_COUNT)
)

@dataclass
class TrainingRow:
    competition_code: str
    competition_name: str
    season_key: str
    match_date: str
    kickoff_time: str
    home_team: str
    away_team: str
    full_time_result: str
    home_goals: int | None
    away_goals: int | None
    upset_label: str
    open_home_odds: float | None
    open_draw_odds: float | None
    open_away_odds: float | None
    close_home_odds: float | None
    close_draw_odds: float | None
    close_away_odds: float | None
    avg_open_home_odds: float | None
    avg_open_draw_odds: float | None
    avg_open_away_odds: float | None
    avg_close_home_odds: float | None
    avg_close_draw_odds: float | None
    avg_close_away_odds: float | None
    open_ah_line: float | None
    close_ah_line: float | None
    open_ah_home_odds: float | None
    open_ah_away_odds: float | None
    close_ah_home_odds: float | None
    close_ah_away_odds: float | None
    open_over25_odds: float | None
    open_under25_odds: float | None
    close_over25_odds: float | None
    close_under25_odds: float | None
    feature_open_home_odds: float | None
    feature_open_draw_odds: float | None
    feature_open_away_odds: float | None
    feature_close_home_odds: float | None
    feature_close_draw_odds: float | None
    feature_close_away_odds: float | None
    feature_home_odds_delta: float | None
    feature_draw_odds_delta: float | None
    feature_away_odds_delta: float | None
    feature_avg_home_odds_delta: float | None
    feature_avg_draw_odds_delta: float | None
    feature_avg_away_odds_delta: float | None
    feature_open_home_implied_prob: float | None
    feature_open_draw_implied_prob: float | None
    feature_open_away_implied_prob: float | None
    feature_close_home_implied_prob: float | None
    feature_close_draw_implied_prob: float | None
    feature_close_away_implied_prob: float | None
    feature_home_implied_prob_delta: float | None
    feature_draw_implied_prob_delta: float | None
    feature_away_implied_prob_delta: float | None
    feature_favorite_gap_open: float | None
    feature_favorite_gap_close: float | None
    feature_home_away_close_ratio: float | None
    feature_home_away_implied_prob_gap_close: float | None
    feature_open_ah_line: float | None
    feature_close_ah_line: float | None
    feature_ah_line_delta: float | None
    feature_open_ah_home_odds: float | None
    feature_open_ah_away_odds: float | None
    feature_close_ah_home_odds: float | None
    feature_close_ah_away_odds: float | None
    feature_ah_home_odds_delta: float | None
    feature_ah_away_odds_delta: float | None
    feature_open_over25_odds: float | None
    feature_open_under25_odds: float | None
    feature_close_over25_odds: float | None
    feature_close_under25_odds: float | None
    feature_over25_odds_delta: float | None
    feature_under25_odds_delta: float | None
    feature_is_premier_league: float
    feature_is_la_liga: float
    feature_is_bundesliga: float
    feature_is_serie_a: float
    feature_is_ligue_1: float
    feature_competition_bucket_0: float
    feature_competition_bucket_1: float
    feature_competition_bucket_2: float
    feature_competition_bucket_3: float
    feature_competition_bucket_4: float
    feature_competition_bucket_5: float
    feature_competition_bucket_6: float
    feature_competition_bucket_7: float
    feature_competition_bucket_8: float
    feature_competition_bucket_9: float
    feature_competition_bucket_10: float
    feature_competition_bucket_11: float


TRAINING_ROW_TYPE_HINTS = get_type_hints(TrainingRow)


FEATURE_COLUMNS = [
    field.name
    for field in fields(TrainingRow)
    if field.name.startswith("feature_")
]


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _parse_match_date(raw_date: str) -> str:
    return datetime.strptime(raw_date.strip(), "%d/%m/%Y").date().isoformat()


def _delta(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return current - previous


def _implied_probability(decimal_odds: float | None) -> float | None:
    if decimal_odds is None or decimal_odds <= 0:
        return None
    return 1.0 / decimal_odds


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _favorite_gap(values: Iterable[float | None]) -> float | None:
    available = sorted(value for value in values if value is not None)
    if len(available) < 2:
        return None
    return available[1] - available[0]


def _competition_bucket_features(competition_code: str) -> dict[str, float]:
    normalized_code = competition_code.strip().upper() or "UNKNOWN"
    digest = hashlib.blake2b(normalized_code.encode("utf-8"), digest_size=2).digest()
    bucket_index = int.from_bytes(digest, byteorder="big") % COMPETITION_BUCKET_COUNT
    return {
        feature_name: 1.0 if index == bucket_index else 0.0
        for index, feature_name in enumerate(COMPETITION_BUCKET_FEATURE_NAMES)
    }


def _resolve_result_label(full_time_result: str, close_home_odds: float | None, close_draw_odds: float | None, close_away_odds: float | None) -> str:
    closing_prices = [value for value in (close_home_odds, close_draw_odds, close_away_odds) if value is not None]
    if len(closing_prices) < 3:
        return UPSET_LABEL_NONE

    favorite_price = min(closing_prices)
    if full_time_result == "H" and close_home_odds is not None and close_home_odds > favorite_price:
        return UPSET_LABEL_HOME
    if full_time_result == "A" and close_away_odds is not None and close_away_odds > favorite_price:
        return UPSET_LABEL_AWAY
    return UPSET_LABEL_NONE


def _resolve_draw_label(full_time_result: str, close_home_odds: float | None, close_draw_odds: float | None, close_away_odds: float | None) -> str:
    closing_prices = [value for value in (close_home_odds, close_draw_odds, close_away_odds) if value is not None]
    if len(closing_prices) < 3:
        return DRAW_LABEL_NONE

    favorite_price = min(closing_prices)
    if full_time_result == "D" and close_draw_odds is not None and close_draw_odds > favorite_price:
        return DRAW_LABEL_UPSET
    return DRAW_LABEL_NONE


def row_to_training_row(raw_row: dict[str, str], season_key: str) -> TrainingRow | None:
    open_home_odds = _parse_float(raw_row.get("B365H"))
    open_draw_odds = _parse_float(raw_row.get("B365D"))
    open_away_odds = _parse_float(raw_row.get("B365A"))
    close_home_odds = _parse_float(raw_row.get("B365CH"))
    close_draw_odds = _parse_float(raw_row.get("B365CD"))
    close_away_odds = _parse_float(raw_row.get("B365CA"))

    if None in (open_home_odds, open_draw_odds, open_away_odds, close_home_odds, close_draw_odds, close_away_odds):
        return None

    competition_code = raw_row["Div"].strip()
    competition = FOOTBALL_DATA_COMPETITIONS.get(competition_code)
    competition_name = str(raw_row.get("competition_name", "")).strip()
    if competition is not None:
        resolved_competition_name = competition.display_name
    elif competition_name:
        resolved_competition_name = competition_name
    else:
        resolved_competition_name = competition_code

    avg_open_home_odds = _parse_float(raw_row.get("AvgH"))
    avg_open_draw_odds = _parse_float(raw_row.get("AvgD"))
    avg_open_away_odds = _parse_float(raw_row.get("AvgA"))
    avg_close_home_odds = _parse_float(raw_row.get("AvgCH"))
    avg_close_draw_odds = _parse_float(raw_row.get("AvgCD"))
    avg_close_away_odds = _parse_float(raw_row.get("AvgCA"))
    open_ah_line = _parse_float(raw_row.get("AHh"))
    close_ah_line = _parse_float(raw_row.get("AHCh"))
    open_ah_home_odds = _parse_float(raw_row.get("B365AHH"))
    open_ah_away_odds = _parse_float(raw_row.get("B365AHA"))
    close_ah_home_odds = _parse_float(raw_row.get("B365CAHH"))
    close_ah_away_odds = _parse_float(raw_row.get("B365CAHA"))
    open_over25_odds = _parse_float(raw_row.get("B365>2.5"))
    open_under25_odds = _parse_float(raw_row.get("B365<2.5"))
    close_over25_odds = _parse_float(raw_row.get("B365C>2.5"))
    close_under25_odds = _parse_float(raw_row.get("B365C<2.5"))

    full_time_result = raw_row.get("FTR", "").strip()
    upset_label = _resolve_result_label(
        full_time_result=full_time_result,
        close_home_odds=close_home_odds,
        close_draw_odds=close_draw_odds,
        close_away_odds=close_away_odds,
    )

    open_home_implied_prob = _implied_probability(open_home_odds)
    open_draw_implied_prob = _implied_probability(open_draw_odds)
    open_away_implied_prob = _implied_probability(open_away_odds)
    close_home_implied_prob = _implied_probability(close_home_odds)
    close_draw_implied_prob = _implied_probability(close_draw_odds)
    close_away_implied_prob = _implied_probability(close_away_odds)

    competition_features = {
        feature_name: 1.0 if competition_code == code else 0.0
        for code, feature_name in COMPETITION_FEATURES
    }
    competition_bucket_features = _competition_bucket_features(competition_code)

    return TrainingRow(
        competition_code=competition_code,
        competition_name=resolved_competition_name,
        season_key=season_key,
        match_date=_parse_match_date(raw_row["Date"]),
        kickoff_time=raw_row.get("Time", "").strip(),
        home_team=raw_row["HomeTeam"].strip(),
        away_team=raw_row["AwayTeam"].strip(),
        full_time_result=full_time_result,
        home_goals=_parse_int(raw_row.get("FTHG")),
        away_goals=_parse_int(raw_row.get("FTAG")),
        upset_label=upset_label,
        open_home_odds=open_home_odds,
        open_draw_odds=open_draw_odds,
        open_away_odds=open_away_odds,
        close_home_odds=close_home_odds,
        close_draw_odds=close_draw_odds,
        close_away_odds=close_away_odds,
        avg_open_home_odds=avg_open_home_odds,
        avg_open_draw_odds=avg_open_draw_odds,
        avg_open_away_odds=avg_open_away_odds,
        avg_close_home_odds=avg_close_home_odds,
        avg_close_draw_odds=avg_close_draw_odds,
        avg_close_away_odds=avg_close_away_odds,
        open_ah_line=open_ah_line,
        close_ah_line=close_ah_line,
        open_ah_home_odds=open_ah_home_odds,
        open_ah_away_odds=open_ah_away_odds,
        close_ah_home_odds=close_ah_home_odds,
        close_ah_away_odds=close_ah_away_odds,
        open_over25_odds=open_over25_odds,
        open_under25_odds=open_under25_odds,
        close_over25_odds=close_over25_odds,
        close_under25_odds=close_under25_odds,
        feature_open_home_odds=open_home_odds,
        feature_open_draw_odds=open_draw_odds,
        feature_open_away_odds=open_away_odds,
        feature_close_home_odds=close_home_odds,
        feature_close_draw_odds=close_draw_odds,
        feature_close_away_odds=close_away_odds,
        feature_home_odds_delta=_delta(close_home_odds, open_home_odds),
        feature_draw_odds_delta=_delta(close_draw_odds, open_draw_odds),
        feature_away_odds_delta=_delta(close_away_odds, open_away_odds),
        feature_avg_home_odds_delta=_delta(avg_close_home_odds, avg_open_home_odds),
        feature_avg_draw_odds_delta=_delta(avg_close_draw_odds, avg_open_draw_odds),
        feature_avg_away_odds_delta=_delta(avg_close_away_odds, avg_open_away_odds),
        feature_open_home_implied_prob=open_home_implied_prob,
        feature_open_draw_implied_prob=open_draw_implied_prob,
        feature_open_away_implied_prob=open_away_implied_prob,
        feature_close_home_implied_prob=close_home_implied_prob,
        feature_close_draw_implied_prob=close_draw_implied_prob,
        feature_close_away_implied_prob=close_away_implied_prob,
        feature_home_implied_prob_delta=_delta(close_home_implied_prob, open_home_implied_prob),
        feature_draw_implied_prob_delta=_delta(close_draw_implied_prob, open_draw_implied_prob),
        feature_away_implied_prob_delta=_delta(close_away_implied_prob, open_away_implied_prob),
        feature_favorite_gap_open=_favorite_gap((open_home_odds, open_draw_odds, open_away_odds)),
        feature_favorite_gap_close=_favorite_gap((close_home_odds, close_draw_odds, close_away_odds)),
        feature_home_away_close_ratio=_ratio(close_home_odds, close_away_odds),
        feature_home_away_implied_prob_gap_close=(
            None if close_home_implied_prob is None or close_away_implied_prob is None else close_home_implied_prob - close_away_implied_prob
        ),
        feature_open_ah_line=open_ah_line,
        feature_close_ah_line=close_ah_line,
        feature_ah_line_delta=_delta(close_ah_line, open_ah_line),
        feature_open_ah_home_odds=open_ah_home_odds,
        feature_open_ah_away_odds=open_ah_away_odds,
        feature_close_ah_home_odds=close_ah_home_odds,
        feature_close_ah_away_odds=close_ah_away_odds,
        feature_ah_home_odds_delta=_delta(close_ah_home_odds, open_ah_home_odds),
        feature_ah_away_odds_delta=_delta(close_ah_away_odds, open_ah_away_odds),
        feature_open_over25_odds=open_over25_odds,
        feature_open_under25_odds=open_under25_odds,
        feature_close_over25_odds=close_over25_odds,
        feature_close_under25_odds=close_under25_odds,
        feature_over25_odds_delta=_delta(close_over25_odds, open_over25_odds),
        feature_under25_odds_delta=_delta(close_under25_odds, open_under25_odds),
        feature_is_premier_league=competition_features["feature_is_premier_league"],
        feature_is_la_liga=competition_features["feature_is_la_liga"],
        feature_is_bundesliga=competition_features["feature_is_bundesliga"],
        feature_is_serie_a=competition_features["feature_is_serie_a"],
        feature_is_ligue_1=competition_features["feature_is_ligue_1"],
        feature_competition_bucket_0=competition_bucket_features["feature_competition_bucket_0"],
        feature_competition_bucket_1=competition_bucket_features["feature_competition_bucket_1"],
        feature_competition_bucket_2=competition_bucket_features["feature_competition_bucket_2"],
        feature_competition_bucket_3=competition_bucket_features["feature_competition_bucket_3"],
        feature_competition_bucket_4=competition_bucket_features["feature_competition_bucket_4"],
        feature_competition_bucket_5=competition_bucket_features["feature_competition_bucket_5"],
        feature_competition_bucket_6=competition_bucket_features["feature_competition_bucket_6"],
        feature_competition_bucket_7=competition_bucket_features["feature_competition_bucket_7"],
        feature_competition_bucket_8=competition_bucket_features["feature_competition_bucket_8"],
        feature_competition_bucket_9=competition_bucket_features["feature_competition_bucket_9"],
        feature_competition_bucket_10=competition_bucket_features["feature_competition_bucket_10"],
        feature_competition_bucket_11=competition_bucket_features["feature_competition_bucket_11"],
    )


def snapshot_row_to_training_row(
    raw_row: dict[str, str],
    season_key: str = "manual",
    default_competition_code: str = "E0",
    preserve_result: bool = False,
) -> TrainingRow | None:
    normalized = dict(raw_row)

    if "Div" not in normalized and "competition_code" in normalized:
        normalized["Div"] = normalized["competition_code"]
    if "Date" not in normalized and "match_date" in normalized:
        match_date = normalized["match_date"].strip()
        if "-" in match_date:
            year, month, day = match_date.split("-")
            normalized["Date"] = f"{day}/{month}/{year}"
        else:
            normalized["Date"] = match_date
    if "Time" not in normalized and "kickoff_time" in normalized:
        normalized["Time"] = normalized["kickoff_time"]
    if "HomeTeam" not in normalized and "home_team" in normalized:
        normalized["HomeTeam"] = normalized["home_team"]
    if "AwayTeam" not in normalized and "away_team" in normalized:
        normalized["AwayTeam"] = normalized["away_team"]

    normalized.setdefault("Div", default_competition_code)
    normalized.setdefault("FTR", "")
    normalized.setdefault("FTHG", "")
    normalized.setdefault("FTAG", "")

    training_row = row_to_training_row(normalized, season_key=season_key)
    if training_row is None:
        return None
    if not preserve_result:
        training_row.full_time_result = ""
        training_row.home_goals = None
        training_row.away_goals = None
        training_row.upset_label = "unknown"
    return training_row


def relabel_rows_for_draw(rows: Iterable[TrainingRow]) -> list[TrainingRow]:
    relabeled_rows: list[TrainingRow] = []
    for row in rows:
        relabeled_rows.append(
            replace(
                row,
                upset_label=_resolve_draw_label(
                    full_time_result=row.full_time_result,
                    close_home_odds=row.close_home_odds,
                    close_draw_odds=row.close_draw_odds,
                    close_away_odds=row.close_away_odds,
                ),
            )
        )
    return relabeled_rows


def build_training_rows(raw_root: Path = FOOTBALL_DATA_RAW_DIR) -> list[TrainingRow]:
    rows: list[TrainingRow] = []
    for csv_path in sorted(raw_root.glob("*/*.csv")):
        season_key = csv_path.parent.name
        with csv_path.open(encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for raw_row in reader:
                training_row = row_to_training_row(raw_row=raw_row, season_key=season_key)
                if training_row is not None:
                    rows.append(training_row)
    rows.sort(key=lambda row: (row.match_date, row.kickoff_time, row.competition_code, row.home_team, row.away_team))
    return rows


def save_training_rows(rows: Iterable[TrainingRow], output_path: Path | None = None) -> Path:
    target = output_path or FEATURES_DIR / "football_data_training_rows.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    row_list = list(rows)
    fieldnames = [field.name for field in fields(TrainingRow)]
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in row_list:
            payload = asdict(row)
            writer.writerow(
                {
                    key: "" if value is None else value
                    for key, value in payload.items()
                }
            )
    return target


def _coerce_field_value(field_name: str, raw_value: str) -> object:
    if raw_value == "":
        return None
    field_type = TRAINING_ROW_TYPE_HINTS[field_name]
    origin = get_origin(field_type)
    args = get_args(field_type)
    if field_type is str:
        return raw_value
    if field_type is float:
        return float(raw_value)
    if field_type is int:
        return int(raw_value)
    if origin is None and isinstance(field_type, type):
        return raw_value
    if len(args) == 2 and type(None) in args:
        concrete_type = args[0] if args[1] is type(None) else args[1]
        if concrete_type is float:
            return float(raw_value)
        if concrete_type is int:
            return int(raw_value)
        if concrete_type is str:
            return raw_value
    return raw_value


def load_training_rows(input_path: Path | None = None) -> list[TrainingRow]:
    source = input_path or FEATURES_DIR / "football_data_training_rows.csv"
    rows: list[TrainingRow] = []
    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            payload = {
                field.name: _coerce_field_value(field.name, raw_row.get(field.name, ""))
                for field in fields(TrainingRow)
            }
            rows.append(TrainingRow(**payload))
    return rows


def row_has_asian_markets(row: TrainingRow) -> bool:
    return all(
        value is not None
        for value in (
            row.open_ah_line,
            row.close_ah_line,
            row.open_ah_home_odds,
            row.open_ah_away_odds,
            row.close_ah_home_odds,
            row.close_ah_away_odds,
        )
    )


def row_has_over_under_markets(row: TrainingRow) -> bool:
    return all(
        value is not None
        for value in (
            row.open_over25_odds,
            row.open_under25_odds,
            row.close_over25_odds,
            row.close_under25_odds,
        )
    )


def market_profile_for_row(row: TrainingRow) -> str:
    has_asian = row_has_asian_markets(row)
    has_over_under = row_has_over_under_markets(row)
    if has_asian and has_over_under:
        return "full_markets"
    if not has_asian and not has_over_under:
        return "1x2_only"
    return "partial_markets"


def filter_rows_by_market_profile(rows: Iterable[TrainingRow], profile: str) -> list[TrainingRow]:
    selected = [row for row in rows if market_profile_for_row(row) == profile]
    selected.sort(key=lambda row: (row.season_key, row.match_date, row.kickoff_time, row.competition_code, row.home_team, row.away_team))
    return selected


def load_snapshot_rows(
    input_path: Path,
    season_key: str = "manual",
    default_competition_code: str = "E0",
    preserve_result: bool = False,
) -> list[TrainingRow]:
    rows: list[TrainingRow] = []
    with input_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            row = snapshot_row_to_training_row(
                raw_row,
                season_key=season_key,
                default_competition_code=default_competition_code,
                preserve_result=preserve_result,
            )
            if row is not None:
                rows.append(row)
    rows.sort(key=lambda row: (row.match_date, row.kickoff_time, row.competition_code, row.home_team, row.away_team))
    return rows
