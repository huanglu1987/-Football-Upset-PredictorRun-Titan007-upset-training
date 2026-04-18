from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path
import re
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"
PROBE_REPORT_DIR = DATA_ROOT / "interim" / "probes"
DOWNLOAD_REPORT_DIR = DATA_ROOT / "interim" / "download_reports"
TRAINING_REPORT_DIR = DATA_ROOT / "interim" / "training_reports"
PREDICTION_REPORT_DIR = DATA_ROOT / "interim" / "prediction_reports"
CHROME_SESSION_RAW_DIR = DATA_ROOT / "raw" / "chrome_session"
FOOTBALL_DATA_RAW_DIR = DATA_ROOT / "raw" / "football_data"
API_FOOTBALL_RAW_DIR = DATA_ROOT / "raw" / "api_football"
TITAN007_RAW_DIR = DATA_ROOT / "raw" / "titan007"
TITAN007_INTERIM_DIR = DATA_ROOT / "interim" / "titan007"
FEATURES_DIR = DATA_ROOT / "features"
MODELS_DIR = DATA_ROOT / "models"

WIN007_HTTPS_HOSTS = (
    "https://www.win007.com",
    "https://m.win007.com",
    "https://live.win007.com",
    "https://bf.win007.com",
)

CHROME_APP_NAME = "Google Chrome"
DEFAULT_CHROME_SOURCE_WAIT_SECONDS = 4
FOOTBALL_DATA_BASE_URL = "https://www.football-data.co.uk/mmz4281"
API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
TITAN007_SCHEDULE_BASE_URL = "https://bf.titan007.com/football"
TITAN007_1X2_PAGE_BASE_URL = "https://1x2.titan007.com/oddslist"
TITAN007_1X2_DATA_BASE_URL = "https://1x2d.titan007.com"
DEFAULT_TIMEZONE = os.environ.get("UPSET_MODEL_TIMEZONE", "Asia/Shanghai")


@dataclass(frozen=True)
class FootballDataCompetition:
    code: str
    slug: str
    display_name: str


FOOTBALL_DATA_COMPETITIONS = {
    "E0": FootballDataCompetition(code="E0", slug="premier-league", display_name="Premier League"),
    "SP1": FootballDataCompetition(code="SP1", slug="la-liga", display_name="La Liga"),
    "D1": FootballDataCompetition(code="D1", slug="bundesliga", display_name="Bundesliga"),
    "I1": FootballDataCompetition(code="I1", slug="serie-a", display_name="Serie A"),
    "F1": FootballDataCompetition(code="F1", slug="ligue-1", display_name="Ligue 1"),
}
DEFAULT_TITAN007_TRAINING_COMPETITION_CODES = tuple(FOOTBALL_DATA_COMPETITIONS.keys())

FOOTBALL_DATA_COMPETITION_ALIASES = {
    "premierleague": "E0",
    "premier-league": "E0",
    "epl": "E0",
    "e0": "E0",
    "laliga": "SP1",
    "la-liga": "SP1",
    "sp1": "SP1",
    "bundesliga": "D1",
    "d1": "D1",
    "seriea": "I1",
    "serie-a": "I1",
    "i1": "I1",
    "ligue1": "F1",
    "ligue-1": "F1",
    "f1": "F1",
}

TITAN007_COMPETITION_NAME_TO_CODE = {
    "英超": "E0",
    "西甲": "SP1",
    "德甲": "D1",
    "意甲": "I1",
    "法甲": "F1",
}

TITAN007_COMPETITION_CODE_TO_NAME = {
    code: name for name, code in TITAN007_COMPETITION_NAME_TO_CODE.items()
}


def normalize_titan007_competition_name(value: str) -> str:
    return re.sub(r"\s+", "", value).strip().lower()


def _ascii_safe_titan007_token(value: str) -> str:
    pieces: list[str] = []
    for char in value.strip():
        if char.isascii() and char.isalnum():
            pieces.append(char.upper())
        elif char in {" ", "-", "/", "_"}:
            pieces.append("_")
        else:
            pieces.append(f"U{ord(char):04X}")
    token = re.sub(r"_+", "_", "".join(pieces)).strip("_")
    return token or "UNKNOWN"


def resolve_titan007_competition_code(competition_name: str) -> str:
    clean_name = competition_name.strip()
    known_code = TITAN007_COMPETITION_NAME_TO_CODE.get(clean_name)
    if known_code is not None:
        return known_code
    return f"T7_{_ascii_safe_titan007_token(clean_name)}"


def normalize_titan007_competition_filter(value: str) -> str | None:
    clean_value = value.strip()
    if not clean_value:
        return None

    upper_value = clean_value.upper()
    if upper_value in FOOTBALL_DATA_COMPETITIONS or upper_value.startswith("T7_"):
        return upper_value

    normalized_name = normalize_titan007_competition_name(clean_value)
    known_code = TITAN007_COMPETITION_NAME_TO_CODE.get(clean_value)
    if known_code is not None:
        return known_code

    football_data_code = FOOTBALL_DATA_COMPETITION_ALIASES.get(normalized_name)
    if football_data_code is not None:
        return football_data_code

    return normalized_name


def normalize_titan007_competition_filters(values: Sequence[str] | None = None) -> set[str]:
    if not values:
        return set()
    normalized: set[str] = set()
    for value in values:
        token = normalize_titan007_competition_filter(value)
        if token:
            normalized.add(token)
    return normalized


def titan007_competition_filter_tokens(competition_name: str, competition_code: str) -> set[str]:
    tokens = {
        competition_code.upper(),
        normalize_titan007_competition_name(competition_name),
    }
    normalized_name_token = normalize_titan007_competition_filter(competition_name)
    if normalized_name_token is not None:
        tokens.add(normalized_name_token)

    known_competition = FOOTBALL_DATA_COMPETITIONS.get(competition_code)
    if known_competition is not None:
        english_token = normalize_titan007_competition_filter(known_competition.display_name)
        if english_token is not None:
            tokens.add(english_token)
    return tokens


def titan007_competition_matches_filter(
    competition_name: str,
    competition_code: str,
    allowed_filters: set[str] | None = None,
) -> bool:
    if not allowed_filters:
        return True
    return bool(titan007_competition_filter_tokens(competition_name, competition_code) & allowed_filters)


def expand_probe_urls(include_http: bool = False) -> list[str]:
    urls = list(WIN007_HTTPS_HOSTS)
    if include_http:
        urls.extend(url.replace("https://", "http://", 1) for url in WIN007_HTTPS_HOSTS)
    return urls


def season_key(start_year: int) -> str:
    if start_year < 2000 or start_year > 2099:
        raise ValueError(f"Unsupported start year: {start_year}")
    end_year = start_year + 1
    return f"{start_year % 100:02d}{end_year % 100:02d}"


def current_european_season_start_year(today: date | None = None, season_start_month: int = 7) -> int:
    current_day = today or date.today()
    if not 1 <= season_start_month <= 12:
        raise ValueError(f"Invalid season start month: {season_start_month}")
    return current_day.year if current_day.month >= season_start_month else current_day.year - 1


def recent_season_keys(
    count: int = 3,
    today: date | None = None,
    season_start_month: int = 7,
) -> list[str]:
    if count <= 0:
        raise ValueError("count must be positive")
    current_start_year = current_european_season_start_year(
        today=today,
        season_start_month=season_start_month,
    )
    first_start_year = current_start_year - count + 1
    return [season_key(year) for year in range(first_start_year, current_start_year + 1)]


def resolve_football_data_competitions(values: Sequence[str] | None = None) -> list[FootballDataCompetition]:
    if not values:
        return [FOOTBALL_DATA_COMPETITIONS[code] for code in FOOTBALL_DATA_COMPETITIONS]

    resolved: list[FootballDataCompetition] = []
    seen_codes: set[str] = set()
    for value in values:
        normalized = value.strip().lower()
        code = FOOTBALL_DATA_COMPETITION_ALIASES.get(normalized, value.strip().upper())
        competition = FOOTBALL_DATA_COMPETITIONS.get(code)
        if competition is None:
            raise ValueError(f"Unsupported football-data competition: {value}")
        if competition.code not in seen_codes:
            resolved.append(competition)
            seen_codes.add(competition.code)
    return resolved
