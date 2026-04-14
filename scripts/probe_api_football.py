from __future__ import annotations

import argparse
import sys

from upset_model.collectors.api_football import ApiFootballClient, build_probe_result, save_probe_result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe API-Football league/fixture/odds endpoints and save raw JSON for inspection.",
    )
    parser.add_argument("--start-date", required=True, help="Inclusive start date in YYYY-MM-DD format.")
    parser.add_argument("--end-date", required=True, help="Inclusive end date in YYYY-MM-DD format.")
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="Season start year used by API-Football, for example 2025 for the 2025/2026 season.",
    )
    parser.add_argument(
        "--league-search",
        action="append",
        dest="league_searches",
        help="League display name to search, can be passed multiple times.",
    )
    parser.add_argument(
        "--limit-fixtures",
        type=int,
        default=10,
        help="Maximum number of fixtures to include in the probe.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    league_searches = args.league_searches or [
        "Premier League",
        "La Liga",
        "Bundesliga",
        "Serie A",
        "Ligue 1",
    ]

    try:
        client = ApiFootballClient()
    except ValueError as exc:
        print(f"API-Football probe failed: {exc}")
        print("Please export API_FOOTBALL_KEY before running this script.")
        return 1
    result = build_probe_result(
        client=client,
        league_search_terms=league_searches,
        date_from=args.start_date,
        date_to=args.end_date,
        season=args.season,
        limit_fixtures=args.limit_fixtures,
    )
    output_path = save_probe_result(result)

    print(
        f"Saved API-Football probe with {len(result.fixtures)} fixtures and "
        f"{len(result.odds_by_fixture)} odds payloads to {output_path}",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
