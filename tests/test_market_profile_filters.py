import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from upset_model.standardize import filter_rows_by_market_profile, load_training_rows, market_profile_for_row


class MarketProfileFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        sample_path = (
            PROJECT_ROOT
            / "data"
            / "interim"
            / "titan007"
            / "merged_88_windows_fast4"
            / "training_rows.csv"
        )
        cls.rows = load_training_rows(sample_path)

    def test_market_profile_for_row_detects_full_markets(self) -> None:
        row = next(row for row in self.rows if row.open_ah_line is not None and row.open_over25_odds is not None)
        self.assertEqual(market_profile_for_row(row), "full_markets")

    def test_market_profile_for_row_detects_1x2_only(self) -> None:
        row = next(row for row in self.rows if row.open_ah_line is None and row.open_over25_odds is None)
        self.assertEqual(market_profile_for_row(row), "1x2_only")

    def test_filter_rows_by_market_profile_splits_rows(self) -> None:
        full_rows = filter_rows_by_market_profile(self.rows, "full_markets")
        one_x2_rows = filter_rows_by_market_profile(self.rows, "1x2_only")
        partial_rows = filter_rows_by_market_profile(self.rows, "partial_markets")

        self.assertEqual(len(full_rows), 2223)
        self.assertEqual(len(one_x2_rows), 289)
        self.assertEqual(len(partial_rows), 6)


if __name__ == "__main__":
    unittest.main()
