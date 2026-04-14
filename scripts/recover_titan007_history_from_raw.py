from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from upset_model.history_expander import recover_titan007_history_from_raw


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recover Titan007 historical training rows from an existing raw history run directory.",
    )
    parser.add_argument("--raw-dir", type=Path, required=True, help="Raw Titan007 history directory containing schedule/1x2/asian/over_under.")
    parser.add_argument("--interim-dir", type=Path, required=True, help="Interim output directory for recovered JSON summaries and failures.")
    parser.add_argument("--output-path", type=Path, required=True, help="Output CSV path for recovered training rows.")
    parser.add_argument(
        "--competitions",
        nargs="*",
        help="Optional competition filters. Supports existing codes and Titan007 competition names. Defaults to all competitions.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = recover_titan007_history_from_raw(
        raw_run_dir=args.raw_dir,
        interim_run_dir=args.interim_dir,
        output_path=args.output_path,
        allowed_competition_codes=args.competitions,
    )
    print(
        f"Recovered {summary['training_row_count']} Titan007 rows from raw dir {args.raw_dir}. "
        f"Failure count: {summary['failure_count']}.",
    )
    print(f"Training rows saved to {summary['training_rows_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
