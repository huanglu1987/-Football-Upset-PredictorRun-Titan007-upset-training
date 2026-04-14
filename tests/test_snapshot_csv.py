import csv
import tempfile
import unittest
from pathlib import Path

from upset_model.standardize import load_snapshot_rows


class SnapshotCsvTests(unittest.TestCase):
    def test_load_snapshot_rows_accepts_normalized_alias_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "snapshot.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
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
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "competition_code": "E0",
                        "match_date": "2026-04-18",
                        "kickoff_time": "15:00",
                        "home_team": "Brentford",
                        "away_team": "Everton",
                        "B365H": "2.10",
                        "B365D": "3.30",
                        "B365A": "3.50",
                        "B365CH": "2.05",
                        "B365CD": "3.25",
                        "B365CA": "3.60",
                    }
                )

            rows = load_snapshot_rows(path, season_key="manual")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].home_team, "Brentford")
        self.assertEqual(rows[0].upset_label, "unknown")
        self.assertEqual(rows[0].match_date, "2026-04-18")


if __name__ == "__main__":
    unittest.main()
