import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from upset_model.collectors.football_data import (
    FootballDataDownloadTarget,
    build_csv_url,
    build_download_targets,
    download_target,
    parse_csv_rows,
)
from upset_model.config import (
    FOOTBALL_DATA_COMPETITIONS,
    recent_season_keys,
    resolve_football_data_competitions,
    season_key,
)


SAMPLE_CSV = "Div,Date,HomeTeam,AwayTeam,FTR,B365H,B365D,B365A,B365CH,B365CD,B365CA\nE0,11/08/2023,Burnley,Man City,A,8,5.5,1.33,9,5.25,1.33\n"


class FakeResponse:
    def __init__(self, body: str, content_type: str = "text/csv") -> None:
        self._body = body.encode("utf-8")
        self.headers = {"Content-Type": content_type}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class FootballDataTests(unittest.TestCase):
    def test_season_key_formats_expected_suffix(self) -> None:
        self.assertEqual(season_key(2023), "2324")

    def test_recent_season_keys_follow_european_calendar(self) -> None:
        self.assertEqual(
            recent_season_keys(count=3, today=date(2026, 4, 13)),
            ["2324", "2425", "2526"],
        )

    def test_resolve_football_data_competitions_accepts_aliases(self) -> None:
        competitions = resolve_football_data_competitions(["premier-league", "sp1", "E0"])
        self.assertEqual([competition.code for competition in competitions], ["E0", "SP1"])

    def test_build_csv_url_uses_expected_pattern(self) -> None:
        self.assertEqual(
            build_csv_url(season_key="2324", competition_code="E0"),
            "https://www.football-data.co.uk/mmz4281/2324/E0.csv",
        )

    def test_parse_csv_rows_reads_headers_and_rows(self) -> None:
        headers, rows = parse_csv_rows(SAMPLE_CSV)
        self.assertIn("B365CH", headers)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["AwayTeam"], "Man City")

    @patch("upset_model.collectors.football_data.urlopen")
    def test_download_target_fetches_and_writes_csv(self, mock_urlopen) -> None:
        mock_urlopen.return_value = FakeResponse(SAMPLE_CSV)
        competition = FOOTBALL_DATA_COMPETITIONS["E0"]
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "2324" / "E0.csv"
            target = FootballDataDownloadTarget(
                competition=competition,
                season_key="2324",
                url=build_csv_url(season_key="2324", competition_code="E0"),
                output_path=output_path,
            )
            result = download_target(target=target, overwrite=True, timeout=5)
            self.assertTrue(output_path.exists())

        self.assertEqual(result.competition_code, "E0")
        self.assertEqual(result.row_count, 1)
        self.assertEqual(result.column_count, 11)
        self.assertFalse(result.used_cache)

    def test_build_download_targets_defaults_to_five_leagues_and_three_seasons(self) -> None:
        targets = build_download_targets()
        self.assertEqual(len(targets), 15)


if __name__ == "__main__":
    unittest.main()
