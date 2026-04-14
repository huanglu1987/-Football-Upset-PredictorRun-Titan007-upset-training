from __future__ import annotations

import csv
import sys
from pathlib import Path


HEADER = [
    "competition_code",
    "match_date",
    "kickoff_time",
    "home_team",
    "away_team",
    "B365H",
    "B365D",
    "B365A",
    "B365CH",
    "B365CD",
    "B365CA",
    "AvgH",
    "AvgD",
    "AvgA",
    "AvgCH",
    "AvgCD",
    "AvgCA",
    "AHh",
    "AHCh",
    "B365AHH",
    "B365AHA",
    "B365CAHH",
    "B365CAHA",
    "B365>2.5",
    "B365<2.5",
    "B365C>2.5",
    "B365C<2.5",
]

EXAMPLE_ROW = [
    "E0",
    "2026-04-18",
    "15:00",
    "Brentford",
    "Everton",
    "2.10",
    "3.30",
    "3.50",
    "2.05",
    "3.25",
    "3.60",
    "2.14",
    "3.28",
    "3.45",
    "2.08",
    "3.24",
    "3.58",
    "-0.25",
    "-0.25",
    "1.95",
    "1.95",
    "1.93",
    "1.97",
    "1.92",
    "1.96",
    "1.90",
    "1.98",
]


def main() -> int:
    output_path = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path.cwd() / "snapshot_template.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerow(EXAMPLE_ROW)
    print(f"Snapshot template written to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
