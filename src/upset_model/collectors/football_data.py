from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

from upset_model.config import (
    DOWNLOAD_REPORT_DIR,
    FOOTBALL_DATA_BASE_URL,
    FOOTBALL_DATA_RAW_DIR,
    FootballDataCompetition,
    recent_season_keys,
    resolve_football_data_competitions,
)

DEFAULT_TIMEOUT_SECONDS = 30
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"


@dataclass(frozen=True)
class FootballDataDownloadTarget:
    competition: FootballDataCompetition
    season_key: str
    url: str
    output_path: Path


@dataclass
class FootballDataDownloadResult:
    competition_code: str
    competition_name: str
    season_key: str
    url: str
    output_path: str
    row_count: int
    column_count: int
    used_cache: bool
    content_type: str | None
    downloaded_at_utc: str


def build_csv_url(season_key: str, competition_code: str) -> str:
    return f"{FOOTBALL_DATA_BASE_URL}/{season_key}/{competition_code}.csv"


def build_output_path(season_key: str, competition_code: str) -> Path:
    return FOOTBALL_DATA_RAW_DIR / season_key / f"{competition_code}.csv"


def build_download_targets(
    competitions: Iterable[str] | None = None,
    season_keys: Iterable[str] | None = None,
) -> list[FootballDataDownloadTarget]:
    selected_competitions = resolve_football_data_competitions(list(competitions) if competitions else None)
    selected_seasons = list(season_keys) if season_keys else recent_season_keys()

    targets: list[FootballDataDownloadTarget] = []
    for season_key in selected_seasons:
        for competition in selected_competitions:
            targets.append(
                FootballDataDownloadTarget(
                    competition=competition,
                    season_key=season_key,
                    url=build_csv_url(season_key=season_key, competition_code=competition.code),
                    output_path=build_output_path(season_key=season_key, competition_code=competition.code),
                )
            )
    return targets


def parse_csv_rows(csv_text: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    headers = list(reader.fieldnames or [])
    rows = [dict(row) for row in reader]
    return headers, rows


def fetch_csv_text(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> tuple[str, str | None]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        csv_text = response.read().decode("utf-8-sig")
        return csv_text, response.headers.get("Content-Type")


def download_target(
    target: FootballDataDownloadTarget,
    overwrite: bool = False,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> FootballDataDownloadResult:
    if target.output_path.exists() and not overwrite:
        csv_text = target.output_path.read_text(encoding="utf-8")
        content_type = None
        used_cache = True
    else:
        csv_text, content_type = fetch_csv_text(target.url, timeout=timeout)
        target.output_path.parent.mkdir(parents=True, exist_ok=True)
        target.output_path.write_text(csv_text, encoding="utf-8")
        used_cache = False

    headers, rows = parse_csv_rows(csv_text)
    return FootballDataDownloadResult(
        competition_code=target.competition.code,
        competition_name=target.competition.display_name,
        season_key=target.season_key,
        url=target.url,
        output_path=str(target.output_path),
        row_count=len(rows),
        column_count=len(headers),
        used_cache=used_cache,
        content_type=content_type,
        downloaded_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def download_targets(
    targets: Iterable[FootballDataDownloadTarget],
    overwrite: bool = False,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> list[FootballDataDownloadResult]:
    return [
        download_target(target=target, overwrite=overwrite, timeout=timeout)
        for target in targets
    ]


def save_download_report(
    results: Iterable[FootballDataDownloadResult],
    output_path: Path | None = None,
) -> Path:
    DOWNLOAD_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    target = output_path or DOWNLOAD_REPORT_DIR / (
        f"football_data_download_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"results": [asdict(result) for result in results]}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
