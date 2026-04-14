from __future__ import annotations

import argparse
import sys

from upset_model.collectors.football_data import (
    build_download_targets,
    download_targets,
    save_download_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download historical football odds CSV files from football-data.co.uk.",
    )
    parser.add_argument(
        "--competitions",
        nargs="*",
        help="Competition codes or aliases, for example: E0 SP1 D1 I1 F1",
    )
    parser.add_argument(
        "--seasons",
        nargs="*",
        help="Season keys like 2324 2425 2526. Defaults to the most recent 3 European seasons.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-download files even if they already exist locally.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout in seconds.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    targets = build_download_targets(
        competitions=args.competitions,
        season_keys=args.seasons,
    )
    results = download_targets(
        targets=targets,
        overwrite=args.overwrite,
        timeout=args.timeout,
    )
    report_path = save_download_report(results)

    total_rows = sum(result.row_count for result in results)
    print(f"Downloaded {len(results)} files with {total_rows} rows in total.")
    for result in results:
        cache_label = "cache" if result.used_cache else "fresh"
        print(
            f"{result.season_key} {result.competition_code} "
            f"rows={result.row_count} cols={result.column_count} mode={cache_label}",
        )
    print(f"Report saved to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
