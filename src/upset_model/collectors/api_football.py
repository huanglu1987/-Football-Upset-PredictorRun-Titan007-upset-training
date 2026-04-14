from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from upset_model.config import API_FOOTBALL_BASE_URL, API_FOOTBALL_RAW_DIR, DEFAULT_TIMEZONE

DEFAULT_TIMEOUT_SECONDS = 30


@dataclass
class ApiFootballProbeResult:
    created_at_utc: str
    timezone: str
    league_searches: dict[str, list[dict[str, Any]]]
    fixtures: list[dict[str, Any]]
    odds_by_fixture: dict[str, list[dict[str, Any]]]


class ApiFootballClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = API_FOOTBALL_BASE_URL,
        timezone: str = DEFAULT_TIMEZONE,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = api_key or os.environ.get("API_FOOTBALL_KEY")
        if not self.api_key:
            raise ValueError("API_FOOTBALL_KEY environment variable is required")
        self.base_url = base_url.rstrip("/")
        self.timezone = timezone
        self.timeout = timeout

    def _request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = urlencode({key: value for key, value in (params or {}).items() if value is not None})
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        if query:
            url = f"{url}?{query}"

        request = Request(
            url,
            headers={
                "x-apisports-key": self.api_key,
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
        )
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _paged_request(self, endpoint: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        initial = self._request(endpoint, params=params)
        responses = list(initial.get("response", []))
        paging = initial.get("paging") or {}
        total_pages = int(paging.get("total", 1) or 1)
        current_page = int(paging.get("current", 1) or 1)

        while current_page < total_pages:
            current_page += 1
            page_params = dict(params or {})
            page_params["page"] = current_page
            payload = self._request(endpoint, params=page_params)
            responses.extend(payload.get("response", []))
        return responses

    def search_leagues(
        self,
        search: str,
        season: int | None = None,
        country: str | None = None,
        current: bool | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"search": search}
        if season is not None:
            params["season"] = season
        if country is not None:
            params["country"] = country
        if current is not None:
            params["current"] = "true" if current else "false"
        return self._paged_request("/leagues", params=params)

    def fetch_fixtures(
        self,
        date_from: str,
        date_to: str,
        league: int | None = None,
        season: int | None = None,
        timezone: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "from": date_from,
            "to": date_to,
            "timezone": timezone or self.timezone,
        }
        if league is not None:
            params["league"] = league
        if season is not None:
            params["season"] = season
        return self._paged_request("/fixtures", params=params)

    def fetch_odds(
        self,
        fixture: int | None = None,
        league: int | None = None,
        season: int | None = None,
        date: str | None = None,
        bookmaker: int | None = None,
        bet: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if fixture is not None:
            params["fixture"] = fixture
        if league is not None:
            params["league"] = league
        if season is not None:
            params["season"] = season
        if date is not None:
            params["date"] = date
        if bookmaker is not None:
            params["bookmaker"] = bookmaker
        if bet is not None:
            params["bet"] = bet
        return self._paged_request("/odds", params=params)

    def fetch_bookmakers(self, search: str | None = None) -> list[dict[str, Any]]:
        return self._paged_request("/odds/bookmakers", params={"search": search} if search else None)

    def fetch_bets(self, search: str | None = None) -> list[dict[str, Any]]:
        return self._paged_request("/odds/bets", params={"search": search} if search else None)


def build_probe_result(
    client: ApiFootballClient,
    league_search_terms: list[str],
    date_from: str,
    date_to: str,
    season: int,
    limit_fixtures: int = 10,
) -> ApiFootballProbeResult:
    league_searches: dict[str, list[dict[str, Any]]] = {}
    fixtures: list[dict[str, Any]] = []
    odds_by_fixture: dict[str, list[dict[str, Any]]] = {}
    seen_fixture_ids: set[int] = set()

    for search_term in league_search_terms:
        leagues = client.search_leagues(search=search_term, season=season, current=None)
        league_searches[search_term] = leagues
        if not leagues:
            continue
        league_id = leagues[0]["league"]["id"]
        league_fixtures = client.fetch_fixtures(
            date_from=date_from,
            date_to=date_to,
            league=league_id,
            season=season,
        )
        for fixture_payload in league_fixtures:
            fixture_id = fixture_payload["fixture"]["id"]
            if fixture_id in seen_fixture_ids:
                continue
            seen_fixture_ids.add(fixture_id)
            fixtures.append(fixture_payload)
            if len(fixtures) >= limit_fixtures:
                break
        if len(fixtures) >= limit_fixtures:
            break

    for fixture_payload in fixtures:
        fixture_id = fixture_payload["fixture"]["id"]
        odds_by_fixture[str(fixture_id)] = client.fetch_odds(fixture=fixture_id)

    return ApiFootballProbeResult(
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        timezone=client.timezone,
        league_searches=league_searches,
        fixtures=fixtures,
        odds_by_fixture=odds_by_fixture,
    )


def save_probe_result(result: ApiFootballProbeResult, output_path: Path | None = None) -> Path:
    API_FOOTBALL_RAW_DIR.mkdir(parents=True, exist_ok=True)
    target = output_path or API_FOOTBALL_RAW_DIR / (
        f"api_football_probe_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    target.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
    return target
