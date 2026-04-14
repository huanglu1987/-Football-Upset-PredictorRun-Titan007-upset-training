from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from upset_model.collectors.chrome_session import capture_current_tab_source, get_active_tab


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture the page source of the current Google Chrome tab via the live browser session."
    )
    parser.add_argument("--output", type=Path, help="Optional path to save the captured HTML source.")
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=4,
        help="Seconds to wait after opening the view-source tab before copying content.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        active_tab = get_active_tab()
        path = capture_current_tab_source(output_path=args.output, wait_seconds=args.wait_seconds)
    except RuntimeError as exc:
        raise SystemExit(
            "Chrome source capture failed. Please make sure Google Chrome is open and the target page is the active tab.\n"
            f"Details: {exc}"
        ) from exc
    print(f"captured source for: {active_tab.url}")
    print(f"saved to: {path}")


if __name__ == "__main__":
    main()
