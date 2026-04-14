from __future__ import annotations

import sys

from upset_model.standardize import build_training_rows, save_training_rows


def main() -> int:
    rows = build_training_rows()
    output_path = save_training_rows(rows)
    label_counts: dict[str, int] = {}
    for row in rows:
        label_counts[row.upset_label] = label_counts.get(row.upset_label, 0) + 1

    print(f"Saved {len(rows)} training rows to {output_path}")
    for label, count in sorted(label_counts.items()):
        print(f"{label}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
