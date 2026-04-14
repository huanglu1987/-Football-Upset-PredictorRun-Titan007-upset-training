from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.error import URLError
from urllib.request import Request, urlopen

from upset_model.config import (
    TITAN007_1X2_DATA_BASE_URL,
    TITAN007_1X2_PAGE_BASE_URL,
    TITAN007_SCHEDULE_BASE_URL,
    normalize_titan007_competition_filters,
    resolve_titan007_competition_code,
    titan007_competition_matches_filter,
)

DEFAULT_TIMEOUT_SECONDS = 30
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
PREFERRED_BOOKMAKERS = ("Bet 365", "Pinnacle", "William Hill")
PREFERRED_LINE_COMPANY_IDS = (8,)


@dataclass(frozen=True)
class Titan007ScheduledMatch:
    schedule_id: int
    competition_name: str
    competition_code: str
    match_date: str
    kickoff_time: str
    home_team: str
    away_team: str
    full_time_result: str
    home_goals: int | None
    away_goals: int | None
    asian_line_text: str | None
    over_under_text: str | None
    source_url: str


@dataclass(frozen=True)
class Titan007EuropeOddsCompany:
    company_id: int
    odds_id: int
    company_name: str
    open_home_odds: float | None
    open_draw_odds: float | None
    open_away_odds: float | None
    close_home_odds: float | None
    close_draw_odds: float | None
    close_away_odds: float | None
    change_time: str
    company_label: str
    is_major: bool


@dataclass(frozen=True)
class Titan007EuropeOddsSnapshot:
    schedule_id: int
    competition_name: str
    home_team: str
    away_team: str
    primary_company_name: str
    primary_open_home_odds: float | None
    primary_open_draw_odds: float | None
    primary_open_away_odds: float | None
    primary_close_home_odds: float | None
    primary_close_draw_odds: float | None
    primary_close_away_odds: float | None
    avg_open_home_odds: float | None
    avg_open_draw_odds: float | None
    avg_open_away_odds: float | None
    avg_close_home_odds: float | None
    avg_close_draw_odds: float | None
    avg_close_away_odds: float | None
    source_page_url: str
    source_data_url: str
    company_count: int
    companies: list[Titan007EuropeOddsCompany]


@dataclass(frozen=True)
class Titan007LineOddsCompany:
    company_id: int
    company_label: str
    trend_class: str | None
    open_left_odds: float | None
    open_line: float | None
    open_right_odds: float | None
    close_left_odds: float | None
    close_line: float | None
    close_right_odds: float | None


@dataclass(frozen=True)
class Titan007AsianOddsSnapshot:
    schedule_id: int
    company_id: int
    company_label: str
    open_home_odds: float | None
    open_line: float | None
    open_away_odds: float | None
    close_home_odds: float | None
    close_line: float | None
    close_away_odds: float | None
    source_url: str


@dataclass(frozen=True)
class Titan007OverUnderSnapshot:
    schedule_id: int
    company_id: int
    company_label: str
    open_over_odds: float | None
    open_line: float | None
    open_under_odds: float | None
    close_over_odds: float | None
    close_line: float | None
    close_under_odds: float | None
    source_url: str


def build_schedule_url(match_date: date | str) -> str:
    target_date = _normalize_date(match_date)
    return f"{TITAN007_SCHEDULE_BASE_URL}/Next_{target_date.strftime('%Y%m%d')}.htm"


def build_finished_schedule_url(match_date: date | str) -> str:
    target_date = _normalize_date(match_date)
    return f"{TITAN007_SCHEDULE_BASE_URL}/Over_{target_date.strftime('%Y%m%d')}.htm"


def build_1x2_page_url(schedule_id: int) -> str:
    return f"{TITAN007_1X2_PAGE_BASE_URL}/{schedule_id}.htm"


def build_1x2_data_url(schedule_id: int) -> str:
    return f"{TITAN007_1X2_DATA_BASE_URL}/{schedule_id}.js"


def build_asian_odds_url(schedule_id: int) -> str:
    return f"https://vip.titan007.com/AsianOdds_n.aspx?id={schedule_id}&l=0"


def build_over_under_url(schedule_id: int) -> str:
    return f"https://vip.titan007.com/OverDown_n.aspx?id={schedule_id}&l=0"


def iter_match_dates(start_date: date | str, end_date: date | str) -> list[str]:
    start = _normalize_date(start_date)
    end = _normalize_date(end_date)
    if end < start:
        raise ValueError("end_date must be on or after start_date")
    values: list[str] = []
    current = start
    while current <= end:
        values.append(current.isoformat())
        current += timedelta(days=1)
    return values


def fetch_text(
    url: str,
    encoding: str = "utf-8",
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    output_path: Path | None = None,
) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
    except Exception as exc:
        if not _should_retry_with_curl(url, exc):
            raise
        body = _fetch_text_with_curl(url=url, timeout=timeout)
    text = body.decode(encoding, errors="ignore")
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    return text


def _should_retry_with_curl(url: str, exc: Exception) -> bool:
    if "titan007.com" not in url or not url.lower().startswith("https://"):
        return False
    if not isinstance(exc, URLError):
        return False
    message = str(exc).lower()
    return "certificate verify failed" in message or "unable to get local issuer certificate" in message


def _fetch_text_with_curl(url: str, timeout: int) -> bytes:
    try:
        result = subprocess.run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--location",
                "--http1.1",
                "--max-time",
                str(timeout),
                "--user-agent",
                USER_AGENT,
                url,
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore").strip()
        raise RuntimeError(f"curl fallback failed for {url}: {stderr or exc}") from exc
    return result.stdout


def parse_schedule_matches(
    html_text: str,
    match_date: date | str,
    source_url: str,
    allowed_competition_codes: Iterable[str] | None = None,
) -> list[Titan007ScheduledMatch]:
    target_page_date = _normalize_date(match_date)
    target_date = target_page_date.isoformat()
    allowed_filters = normalize_titan007_competition_filters(list(allowed_competition_codes) if allowed_competition_codes else None)
    table_match = re.search(r"id=['\"]table_live['\"]>(?P<body>.*?)</table>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if table_match is None:
        raise ValueError("Could not find table_live in Titan007 schedule page")

    scheduled_matches: list[Titan007ScheduledMatch] = []
    for row_match in re.finditer(
        r"<tr[^>]*sId=['\"](?P<schedule_id>\d+)['\"][^>]*>(?P<body>.*?)</tr>",
        table_match.group("body"),
        flags=re.IGNORECASE | re.DOTALL,
    ):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_match.group("body"), flags=re.IGNORECASE | re.DOTALL)
        if len(cells) < 10:
            continue

        competition_name = _clean_cell_text(cells[0])
        competition_code = resolve_titan007_competition_code(competition_name)
        if not titan007_competition_matches_filter(
            competition_name=competition_name,
            competition_code=competition_code,
            allowed_filters=allowed_filters,
        ):
            continue

        row_match_date, kickoff_time = _parse_schedule_row_datetime(_clean_cell_text(cells[1]), page_date=target_page_date)
        if row_match_date != target_date:
            continue
        home_team = _clean_team_name(cells[3])
        away_team = _clean_team_name(cells[5])
        home_goals, away_goals = _extract_score(cells[4])
        full_time_result = _resolve_match_result(home_goals, away_goals)

        scheduled_matches.append(
            Titan007ScheduledMatch(
                schedule_id=int(row_match.group("schedule_id")),
                competition_name=competition_name,
                competition_code=competition_code,
                match_date=target_date,
                kickoff_time=kickoff_time,
                home_team=home_team,
                away_team=away_team,
                full_time_result=full_time_result,
                home_goals=home_goals,
                away_goals=away_goals,
                asian_line_text=_clean_optional_text(cells[7]),
                over_under_text=_clean_optional_text(cells[8]),
                source_url=source_url,
            )
        )

    scheduled_matches.sort(
        key=lambda item: (item.match_date, item.kickoff_time, item.competition_code, item.home_team, item.away_team)
    )
    return scheduled_matches


def _parse_schedule_row_datetime(raw_value: str, *, page_date: date) -> tuple[str, str]:
    month_day_match = re.search(r"(?P<month>\d{1,2})-(?P<day>\d{1,2})\s+(?P<time>\d{1,2}:\d{2})", raw_value)
    if month_day_match is not None:
        month = int(month_day_match.group("month"))
        day = int(month_day_match.group("day"))
        year = _resolve_schedule_row_year(page_date=page_date, month=month)
        return date(year, month, day).isoformat(), month_day_match.group("time")

    day_only_match = re.search(r"(?P<day>\d{1,2})日(?P<time>\d{1,2}:\d{2})", raw_value)
    if day_only_match is not None:
        day = int(day_only_match.group("day"))
        row_date = date(page_date.year, page_date.month, day)
        return row_date.isoformat(), day_only_match.group("time")

    kickoff_match = re.search(r"(?P<time>\d{1,2}:\d{2})", raw_value)
    kickoff_time = kickoff_match.group("time") if kickoff_match else ""
    return page_date.isoformat(), kickoff_time


def _resolve_schedule_row_year(*, page_date: date, month: int) -> int:
    if month - page_date.month >= 6:
        return page_date.year - 1
    if page_date.month - month >= 6:
        return page_date.year + 1
    return page_date.year


def parse_europe_odds_snapshot(js_text: str, schedule_id: int | None = None) -> Titan007EuropeOddsSnapshot:
    parsed_schedule_id = int(_extract_js_var(js_text, "ScheduleID"))
    if schedule_id is not None and parsed_schedule_id != int(schedule_id):
        raise ValueError(f"ScheduleID mismatch: expected {schedule_id}, got {parsed_schedule_id}")

    companies: list[Titan007EuropeOddsCompany] = []
    for raw_entry in _extract_js_array(js_text, "game"):
        company = _parse_game_entry(raw_entry)
        if company is not None:
            companies.append(company)

    if not companies:
        raise ValueError("No company odds rows found in Titan007 Europe odds script")

    primary_company = _select_primary_company(companies)
    return Titan007EuropeOddsSnapshot(
        schedule_id=parsed_schedule_id,
        competition_name=_extract_js_var(js_text, "matchname_cn"),
        home_team=_extract_js_var(js_text, "hometeam_cn"),
        away_team=_extract_js_var(js_text, "guestteam_cn"),
        primary_company_name=primary_company.company_name,
        primary_open_home_odds=primary_company.open_home_odds,
        primary_open_draw_odds=primary_company.open_draw_odds,
        primary_open_away_odds=primary_company.open_away_odds,
        primary_close_home_odds=primary_company.close_home_odds,
        primary_close_draw_odds=primary_company.close_draw_odds,
        primary_close_away_odds=primary_company.close_away_odds,
        avg_open_home_odds=_average_company_value(companies, "open_home_odds"),
        avg_open_draw_odds=_average_company_value(companies, "open_draw_odds"),
        avg_open_away_odds=_average_company_value(companies, "open_away_odds"),
        avg_close_home_odds=_average_company_value(companies, "close_home_odds"),
        avg_close_draw_odds=_average_company_value(companies, "close_draw_odds"),
        avg_close_away_odds=_average_company_value(companies, "close_away_odds"),
        source_page_url=build_1x2_page_url(parsed_schedule_id),
        source_data_url=build_1x2_data_url(parsed_schedule_id),
        company_count=len(companies),
        companies=companies,
    )


def parse_asian_odds_snapshot(html_text: str, schedule_id: int) -> Titan007AsianOddsSnapshot:
    companies = _parse_line_odds_companies(html_text)
    if not companies:
        raise ValueError("No Asian odds rows found in Titan007 odds table")
    company = _select_primary_line_company(companies)
    return Titan007AsianOddsSnapshot(
        schedule_id=schedule_id,
        company_id=company.company_id,
        company_label=_normalize_company_label(company.company_id, company.company_label),
        open_home_odds=company.open_left_odds,
        open_line=company.open_line,
        open_away_odds=company.open_right_odds,
        close_home_odds=company.close_left_odds,
        close_line=company.close_line,
        close_away_odds=company.close_right_odds,
        source_url=build_asian_odds_url(schedule_id),
    )


def parse_over_under_snapshot(html_text: str, schedule_id: int) -> Titan007OverUnderSnapshot:
    companies = _parse_line_odds_companies(html_text)
    if not companies:
        raise ValueError("No over/under odds rows found in Titan007 odds table")
    company = _select_primary_line_company(companies)
    return Titan007OverUnderSnapshot(
        schedule_id=schedule_id,
        company_id=company.company_id,
        company_label=_normalize_company_label(company.company_id, company.company_label),
        open_over_odds=company.open_left_odds,
        open_line=company.open_line,
        open_under_odds=company.open_right_odds,
        close_over_odds=company.close_left_odds,
        close_line=company.close_line,
        close_under_odds=company.close_right_odds,
        source_url=build_over_under_url(schedule_id),
    )


def build_snapshot_row(
    match: Titan007ScheduledMatch,
    odds: Titan007EuropeOddsSnapshot,
    asian: Titan007AsianOddsSnapshot | None = None,
    over_under: Titan007OverUnderSnapshot | None = None,
) -> dict[str, str]:
    if match.schedule_id != odds.schedule_id:
        raise ValueError("Schedule match and Europe odds snapshot refer to different schedule IDs")

    row = {
        "competition_code": match.competition_code,
        "competition_name": match.competition_name,
        "match_date": match.match_date,
        "kickoff_time": match.kickoff_time,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "FTR": match.full_time_result,
        "FTHG": "" if match.home_goals is None else str(match.home_goals),
        "FTAG": "" if match.away_goals is None else str(match.away_goals),
        "B365H": _format_float(odds.primary_open_home_odds),
        "B365D": _format_float(odds.primary_open_draw_odds),
        "B365A": _format_float(odds.primary_open_away_odds),
        "B365CH": _format_float(odds.primary_close_home_odds),
        "B365CD": _format_float(odds.primary_close_draw_odds),
        "B365CA": _format_float(odds.primary_close_away_odds),
        "AvgH": _format_float(odds.avg_open_home_odds),
        "AvgD": _format_float(odds.avg_open_draw_odds),
        "AvgA": _format_float(odds.avg_open_away_odds),
        "AvgCH": _format_float(odds.avg_close_home_odds),
        "AvgCD": _format_float(odds.avg_close_draw_odds),
        "AvgCA": _format_float(odds.avg_close_away_odds),
        "source_schedule_id": str(match.schedule_id),
        "source_schedule_url": match.source_url,
        "source_euro_page_url": odds.source_page_url,
        "source_euro_data_url": odds.source_data_url,
        "primary_bookmaker": odds.primary_company_name,
        "data_completeness": "1x2_only",
    }
    if asian is not None:
        row.update(
            {
                "AHh": _format_float(asian.open_line),
                "AHCh": _format_float(asian.close_line),
                "B365AHH": _format_float(asian.open_home_odds),
                "B365AHA": _format_float(asian.open_away_odds),
                "B365CAHH": _format_float(asian.close_home_odds),
                "B365CAHA": _format_float(asian.close_away_odds),
                "source_asian_url": asian.source_url,
                "source_asian_company": asian.company_label,
            }
        )
    if over_under is not None:
        row.update(
            {
                "B365>2.5": _format_float(over_under.open_over_odds),
                "B365<2.5": _format_float(over_under.open_under_odds),
                "B365C>2.5": _format_float(over_under.close_over_odds),
                "B365C<2.5": _format_float(over_under.close_under_odds),
                "source_over_under_url": over_under.source_url,
                "source_total_company": over_under.company_label,
                "source_open_total_line": _format_float(over_under.open_line),
                "source_close_total_line": _format_float(over_under.close_line),
            }
        )
    parts = ["1x2"]
    if asian is not None:
        parts.append("asian")
    if over_under is not None:
        parts.append("over_under")
    row["data_completeness"] = "+".join(parts)
    return row


def serialize_schedule_matches(matches: Iterable[Titan007ScheduledMatch]) -> list[dict[str, object]]:
    return [asdict(match) for match in matches]


def serialize_europe_snapshot(snapshot: Titan007EuropeOddsSnapshot) -> dict[str, object]:
    return asdict(snapshot)


def serialize_asian_snapshot(snapshot: Titan007AsianOddsSnapshot) -> dict[str, object]:
    return asdict(snapshot)


def serialize_over_under_snapshot(snapshot: Titan007OverUnderSnapshot) -> dict[str, object]:
    return asdict(snapshot)


def _normalize_date(value: date | str) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _clean_cell_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value)
    text = unescape(text).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_team_name(value: str) -> str:
    text = _clean_cell_text(value)
    text = re.sub(r"\[[^\]]+\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_optional_text(value: str) -> str | None:
    text = _clean_cell_text(value)
    return text or None


def _extract_score(value: str) -> tuple[int | None, int | None]:
    text = _clean_cell_text(value)
    score_match = re.search(r"(\d+)\s*-\s*(\d+)", text)
    if score_match is None:
        return None, None
    return int(score_match.group(1)), int(score_match.group(2))


def _resolve_match_result(home_goals: int | None, away_goals: int | None) -> str:
    if home_goals is None or away_goals is None:
        return ""
    if home_goals > away_goals:
        return "H"
    if away_goals > home_goals:
        return "A"
    return "D"


def _extract_js_var(js_text: str, name: str) -> str:
    string_match = re.search(rf'var\s+{re.escape(name)}="(?P<value>.*?)";', js_text, flags=re.DOTALL)
    if string_match is not None:
        return string_match.group("value")
    number_match = re.search(rf"var\s+{re.escape(name)}=(?P<value>[^;]+);", js_text)
    if number_match is not None:
        return number_match.group("value").strip().strip('"')
    raise ValueError(f"Could not find JS variable: {name}")


def _extract_js_array(js_text: str, name: str) -> list[str]:
    array_match = re.search(
        rf"var\s+{re.escape(name)}=Array\((?P<body>.*?)\);",
        js_text,
        flags=re.DOTALL,
    )
    if array_match is None:
        return []
    return re.findall(r'"([^"]*)"', array_match.group("body"))


def _parse_line_odds_companies(html_text: str) -> list[Titan007LineOddsCompany]:
    table_match = re.search(r'id=["\']odds["\'][^>]*>(?P<body>.*?)</table>', html_text, flags=re.IGNORECASE | re.DOTALL)
    if table_match is None:
        raise ValueError("Could not find odds table in Titan007 line odds page")

    companies: list[Titan007LineOddsCompany] = []
    for row_match in re.finditer(r"<tr\b[^>]*>(?P<body>.*?)</tr>", table_match.group("body"), flags=re.IGNORECASE | re.DOTALL):
        row_html = row_match.group(0)
        if "name=\"oddsShow\"" not in row_html and "name='oddsShow'" not in row_html:
            continue
        company_id_match = re.search(r"data-id=[\"']?(\d+)", row_html)
        if company_id_match is None:
            continue
        cells = re.findall(r"<td([^>]*)>(.*?)</td>", row_html, flags=re.IGNORECASE | re.DOTALL)
        if len(cells) < 9:
            continue
        trend_class_match = re.search(r"class=['\"]([^'\"]+)", cells[2][1])
        companies.append(
            Titan007LineOddsCompany(
                company_id=int(company_id_match.group(1)),
                company_label=_clean_cell_text(cells[1][1]),
                trend_class=trend_class_match.group(1) if trend_class_match else None,
                open_left_odds=_parse_float(_clean_cell_text(cells[3][1])),
                open_line=_extract_goals_value(cells[4][0]),
                open_right_odds=_parse_float(_clean_cell_text(cells[5][1])),
                close_left_odds=_parse_float(_clean_cell_text(cells[6][1])),
                close_line=_extract_goals_value(cells[7][0]),
                close_right_odds=_parse_float(_clean_cell_text(cells[8][1])),
            )
        )
    return companies


def _parse_game_entry(raw_entry: str) -> Titan007EuropeOddsCompany | None:
    parts = raw_entry.split("|")
    if len(parts) < 23:
        return None
    return Titan007EuropeOddsCompany(
        company_id=int(parts[0]),
        odds_id=int(parts[1]),
        company_name=parts[2].strip(),
        open_home_odds=_parse_float(parts[3]),
        open_draw_odds=_parse_float(parts[4]),
        open_away_odds=_parse_float(parts[5]),
        close_home_odds=_parse_float(parts[10]),
        close_draw_odds=_parse_float(parts[11]),
        close_away_odds=_parse_float(parts[12]),
        change_time=parts[20].strip(),
        company_label=parts[21].strip(),
        is_major=parts[22].strip() == "1",
    )


def _extract_goals_value(attrs_text: str) -> float | None:
    goals_match = re.search(r'goals=["\']?(-?\d+(?:\.\d+)?)', attrs_text)
    if goals_match is None:
        return None
    return _parse_float(goals_match.group(1))


def _select_primary_company(companies: list[Titan007EuropeOddsCompany]) -> Titan007EuropeOddsCompany:
    for preferred_name in PREFERRED_BOOKMAKERS:
        for company in companies:
            if company.company_name == preferred_name and _has_complete_1x2(company):
                return company
    for company in companies:
        if _has_complete_1x2(company):
            return company
    return companies[0]


def _select_primary_line_company(companies: list[Titan007LineOddsCompany]) -> Titan007LineOddsCompany:
    for preferred_id in PREFERRED_LINE_COMPANY_IDS:
        for company in companies:
            if company.company_id == preferred_id and _has_complete_line_odds(company):
                return company
    for company in companies:
        if _has_complete_line_odds(company):
            return company
    return companies[0]


def _normalize_company_label(company_id: int, company_label: str) -> str:
    if company_id == 8:
        return "Bet 365"
    return company_label


def _average_company_value(companies: Iterable[Titan007EuropeOddsCompany], field_name: str) -> float | None:
    values = [
        value
        for company in companies
        for value in [getattr(company, field_name)]
        if value is not None
    ]
    if not values:
        return None
    return sum(values) / len(values)


def _parse_float(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _has_complete_1x2(company: Titan007EuropeOddsCompany) -> bool:
    return None not in (
        company.open_home_odds,
        company.open_draw_odds,
        company.open_away_odds,
        company.close_home_odds,
        company.close_draw_odds,
        company.close_away_odds,
    )


def _has_complete_line_odds(company: Titan007LineOddsCompany) -> bool:
    return None not in (
        company.open_left_odds,
        company.open_line,
        company.open_right_odds,
        company.close_left_odds,
        company.close_line,
        company.close_right_odds,
    )


def _format_float(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"
