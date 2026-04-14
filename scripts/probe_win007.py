from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from upset_model.collectors.win007_probe import run_probe, save_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe Win007 public hosts and save a JSON report.")
    parser.add_argument(
        "--include-http",
        action="store_true",
        help="Probe both https and http candidate hosts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_probe(include_http=args.include_http)
    path = save_report(report)
    print(f"saved probe report to: {path}")
    ok_count = sum(1 for result in report.results if result.ok)
    print(f"successful checks: {ok_count}/{len(report.results)}")


if __name__ == "__main__":
    main()
