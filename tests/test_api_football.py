import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from upset_model.collectors.api_football import ApiFootballClient, build_probe_result, save_probe_result


class FakeJsonResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "FakeJsonResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def fake_api_payload(url: str) -> dict:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    path = parsed.path

    if path.endswith("/leagues"):
        page = int(query.get("page", ["1"])[0])
        if page == 1:
            return {
                "paging": {"current": 1, "total": 2},
                "response": [{"league": {"id": 39, "name": "Premier League"}}],
            }
        return {
            "paging": {"current": 2, "total": 2},
            "response": [{"league": {"id": 140, "name": "La Liga"}}],
        }

    if path.endswith("/fixtures"):
        return {
            "paging": {"current": 1, "total": 1},
            "response": [
                {
                    "fixture": {"id": 1001, "date": "2026-04-12T15:00:00+00:00"},
                    "league": {"id": 39},
                    "teams": {"home": {"name": "A"}, "away": {"name": "B"}},
                }
            ],
        }

    if path.endswith("/odds"):
        fixture_id = query.get("fixture", ["0"])[0]
        return {
            "paging": {"current": 1, "total": 1},
            "response": [{"fixture": {"id": int(fixture_id)}, "bookmakers": []}],
        }

    if path.endswith("/odds/bookmakers"):
        return {"paging": {"current": 1, "total": 1}, "response": [{"id": 8, "name": "Bet365"}]}

    if path.endswith("/odds/bets"):
        return {"paging": {"current": 1, "total": 1}, "response": [{"id": 1, "name": "Match Winner"}]}

    raise AssertionError(f"Unexpected URL: {url}")


class ApiFootballTests(unittest.TestCase):
    @patch("upset_model.collectors.api_football.urlopen")
    def test_paged_request_collects_multiple_pages(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = lambda request, timeout=30: FakeJsonResponse(fake_api_payload(request.full_url))
        client = ApiFootballClient(api_key="demo-key")
        leagues = client.search_leagues(search="Premier League", season=2025)

        self.assertEqual(len(leagues), 2)
        self.assertEqual(leagues[0]["league"]["id"], 39)
        first_request = mock_urlopen.call_args_list[0].args[0]
        self.assertEqual(first_request.headers["X-apisports-key"], "demo-key")

    @patch("upset_model.collectors.api_football.urlopen")
    def test_build_probe_result_fetches_fixtures_and_odds(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = lambda request, timeout=30: FakeJsonResponse(fake_api_payload(request.full_url))
        client = ApiFootballClient(api_key="demo-key")
        result = build_probe_result(
            client=client,
            league_search_terms=["Premier League"],
            date_from="2026-04-10",
            date_to="2026-04-13",
            season=2025,
            limit_fixtures=3,
        )

        self.assertEqual(len(result.fixtures), 1)
        self.assertIn("1001", result.odds_by_fixture)
        self.assertEqual(result.odds_by_fixture["1001"][0]["fixture"]["id"], 1001)

    def test_save_probe_result_writes_json(self) -> None:
        client_result = {
            "created_at_utc": "2026-04-13T00:00:00+00:00",
            "timezone": "Asia/Shanghai",
            "league_searches": {"Premier League": []},
            "fixtures": [],
            "odds_by_fixture": {},
        }
        from upset_model.collectors.api_football import ApiFootballProbeResult

        result = ApiFootballProbeResult(**client_result)
        output_path = Path.cwd() / "data" / "raw" / "api_football" / "test_probe_result.json"
        if output_path.exists():
            output_path.unlink()
        path = save_probe_result(result, output_path=output_path)
        self.assertTrue(path.exists())
        self.assertIn('"timezone"', path.read_text(encoding="utf-8"))
        output_path.unlink()


if __name__ == "__main__":
    unittest.main()
