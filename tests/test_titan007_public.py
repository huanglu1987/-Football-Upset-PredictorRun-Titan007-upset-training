import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError

from upset_model.collectors.titan007_public import (
    build_snapshot_row,
    fetch_text,
    parse_asian_odds_snapshot,
    parse_europe_odds_snapshot,
    parse_over_under_snapshot,
    parse_schedule_matches,
)
from upset_model.standardize import snapshot_row_to_training_row


SCHEDULE_HTML = """
<html>
  <body>
    <table id='table_live'>
      <tr bgColor=#990000 align=center>
        <td>联赛</td><td>赛事时间</td><td></td><td>主场球队</td><td>比分</td><td>客场球队</td><td>半场</td><td>亚让</td><td>进球数</td><td>资料</td>
      </tr>
      <tr height=18 align=center bgColor=#FFFDF3 id='tr1_1' name='36,0' infoid='1' sId='2961297'>
        <td bgcolor=#ec8531 style='color:white'><span>英超</span><span></span></td>
        <td>4-18 15:00</td>
        <td></td>
        <td align=right><span name='order'><font color=#888888>[12]</font></span>布伦特福德</td>
        <td><b>-</b></td>
        <td align=left>埃弗顿<span name='order'><font color=#888888>[16]</font></span></td>
        <td></td>
        <td></td>
        <td></td>
        <td align=left>&nbsp;<a href=javascript: onclick='AsianOdds(2961297)'>亚</a> <a href=javascript: onclick='EuropeOdds(2961297)'>欧</a></td>
      </tr>
      <tr height=18 align=center bgColor=#FFFDF3 id='tr1_2' name='686,0' infoid='45' sId='1111111'>
        <td bgcolor=#8e9cdf style='color:white'><span>中乙</span><span></span></td>
        <td>4-18 15:00</td>
        <td></td>
        <td align=right>北京理工</td>
        <td><b>-</b></td>
        <td align=left>上海海港B队</td>
        <td></td>
        <td></td>
        <td></td>
        <td align=left>&nbsp;<a href=javascript: onclick='EuropeOdds(1111111)'>欧</a></td>
      </tr>
    </table>
  </body>
</html>
"""

CROSS_DAY_SCHEDULE_HTML = """
<html>
  <body>
    <table id='table_live'>
      <tr bgColor=#990000 align=center>
        <td>联赛</td><td>赛事时间</td><td></td><td>主场球队</td><td>比分</td><td>客场球队</td><td>半场</td><td>亚让</td><td>进球数</td><td>资料</td>
      </tr>
      <tr height=18 align=center bgColor=#FFFDF3 id='tr1_1' name='36,0' infoid='1' sId='2961297'>
        <td bgcolor=#ec8531 style='color:white'><span>英超</span><span></span></td>
        <td>4-15 22:00</td>
        <td></td>
        <td align=right>球队A</td>
        <td><b>-</b></td>
        <td align=left>球队B</td>
        <td></td>
        <td></td>
        <td></td>
        <td align=left>&nbsp;<a href=javascript: onclick='EuropeOdds(2961297)'>欧</a></td>
      </tr>
      <tr height=18 align=center bgColor=#F0F0F0 id='tr1_2' name='290,0' infoid='21' sId='2795053'>
        <td bgcolor=#00CCFF style='color:white'><span>捷乙</span><span></span></td>
        <td>4-16 00:00</td>
        <td></td>
        <td align=right>塔波斯科</td>
        <td><b>-</b></td>
        <td align=left>布德约维茨迪纳摩</td>
        <td></td>
        <td></td>
        <td></td>
        <td align=left>&nbsp;<a href=javascript: onclick='EuropeOdds(2795053)'>欧</a></td>
      </tr>
    </table>
  </body>
</html>
"""

FINISHED_SCHEDULE_HTML = """
<html>
  <body>
    <table id='table_live'>
      <tr bgColor=#990000 align=center>
        <td>联赛</td><td>赛事时间</td><td>状态</td><td>主场球队</td><td>比分</td><td>客场球队</td><td>半场</td><td>亚让</td><td>进球数</td><td>资料</td>
      </tr>
      <tr height=18 align=center bgColor=#FFFDF3 id='tr1_1' name='36,0' infoid='1' sId='2961297'>
        <td bgcolor=#ec8531 style='color:white'><span>英超</span><span></span></td>
        <td>18日15:00</td>
        <td class=style1>完</td>
        <td align=right><span name='order'><font color=#888888>[12]</font></span>布伦特福德</td>
        <td class=style1><font color=red>2</font>-<font color=blue>1</font></td>
        <td align=left>埃弗顿<span name='order'><font color=#888888>[16]</font></span></td>
        <td><font color=red>1</font>-<font color=blue>0</font></td>
        <td></td>
        <td></td>
        <td align=left>&nbsp;<a href=javascript: onclick='AsianOdds(2961297)'>亚</a> <a href=javascript: onclick='EuropeOdds(2961297)'>欧</a></td>
      </tr>
    </table>
  </body>
</html>
"""


EUROPE_JS = """
var matchname_cn="英超";
var ScheduleID=2961297;
var hometeam_cn="布伦特福德";
var guestteam_cn="埃弗顿";
var game=Array(
  "281|152823209|Bet 365|2.10|3.30|3.50|0|0|0|0|2.05|3.25|3.60|0|0|0|0|0|0|0|2026,04-17,18,20,00|36*(英国)|1|0|0.55|0.89|1.15",
  "177|152823490|Pinnacle|2.12|3.28|3.45|0|0|0|0|2.08|3.24|3.58|0|0|0|0|0|0|0|2026,04-17,18,13,00|Pinna*(荷兰)|1|0|0.51|0.79|1.43"
);
var gameDetail=Array(
  "152823209^2.05|3.25|3.60|04-17 18:20|0.55|0.89|1.15|2026;",
  "152823490^2.08|3.24|3.58|04-17 18:13|0.51|0.79|1.43|2026;"
);
var jcEuropeOddsData="";
var jcEuropeOddsDetail="";
"""

ASIAN_HTML = """
<html>
  <body>
    <table id="odds">
      <tr align="center" class='thead2'><th>公司</th></tr>
      <tr bgcolor="#FFFFFF">
        <td width="35" class="lb rb"><input type="checkbox" name="oddsShow" data-id="8" value="0"></td>
        <td height="25">36*</td>
        <td><span class='' companyID='8'></span></td>
        <td title="2026-04-13 18:43">0.80</td>
        <td title="2026-04-13 18:43" goals="-0.25">受让平手/半球</td>
        <td title="2026-04-13 18:43">1.00</td>
        <td oddstype="wholeLastOdds">0.90</td>
        <td goals="-0.75" oddstype="wholeLastOdds">受让半球/一球</td>
        <td oddstype="wholeLastOdds">0.90</td>
        <td>history</td>
      </tr>
      <tr bgcolor="#FAFAFA">
        <td width="35" class="lb rb"><input type="checkbox" name="oddsShow" data-id="42" value="0"></td>
        <td height="25">18*</td>
        <td><span class='down' companyID='42'></span></td>
        <td title="2026-04-13 18:59">0.78</td>
        <td title="2026-04-13 18:59" goals="-0.25">受让平手/半球</td>
        <td title="2026-04-13 18:59">0.78</td>
        <td oddstype="wholeLastOdds">0.81</td>
        <td goals="-0.75" oddstype="wholeLastOdds">受让半球/一球</td>
        <td oddstype="wholeLastOdds">0.75</td>
        <td>history</td>
      </tr>
    </table>
  </body>
</html>
"""

OVER_UNDER_HTML = """
<html>
  <body>
    <table id="odds">
      <tr align="center" class='thead2'><th>公司</th></tr>
      <tr bgcolor="#FFFFFF">
        <td width="35" class="lb rb"><input type="checkbox" name="oddsShow" data-id="8" value="0"></td>
        <td height="25">36*</td>
        <td><span class='' companyID='8'></span></td>
        <td title="2026-04-13 18:43">0.95</td>
        <td title="2026-04-13 18:43" goals="2.25">2/2.5</td>
        <td title="2026-04-13 18:43">0.85</td>
        <td oddstype="wholeLastOdds">1.03</td>
        <td goals="2.5" oddstype="wholeLastOdds">2.5</td>
        <td oddstype="wholeLastOdds">0.78</td>
        <td>history</td>
      </tr>
      <tr bgcolor="#FAFAFA">
        <td width="35" class="lb rb"><input type="checkbox" name="oddsShow" data-id="22" value="0"></td>
        <td height="25">10*</td>
        <td><span class='down' companyID='22'></span></td>
        <td title="2026-04-13 18:59">0.78</td>
        <td title="2026-04-13 18:59" goals="2.25">2/2.5</td>
        <td title="2026-04-13 18:59">0.89</td>
        <td oddstype="wholeLastOdds">0.73</td>
        <td goals="2.25" oddstype="wholeLastOdds">2/2.5</td>
        <td oddstype="wholeLastOdds">0.95</td>
        <td>history</td>
      </tr>
    </table>
  </body>
</html>
"""


class Titan007PublicTests(unittest.TestCase):
    def test_fetch_text_falls_back_to_curl_on_ssl_certificate_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "page.html"
            with (
                patch(
                    "upset_model.collectors.titan007_public.urlopen",
                    side_effect=URLError("certificate verify failed: unable to get local issuer certificate"),
                ),
                patch(
                    "upset_model.collectors.titan007_public.subprocess.run",
                    return_value=Mock(stdout="联赛".encode("gb18030"), stderr=b""),
                ) as mock_run,
                ):
                text = fetch_text(
                    "https://bf.titan007.com/football/Next_20260417.htm",
                    encoding="gb18030",
                    output_path=output_path,
                )
                saved_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(text, "联赛")
        self.assertEqual(saved_text, "联赛")
        mock_run.assert_called_once()
        self.assertEqual(mock_run.call_args.args[0][0], "curl")

    def test_parse_schedule_matches_filters_to_supported_competitions(self) -> None:
        matches = parse_schedule_matches(
            SCHEDULE_HTML,
            match_date="2026-04-18",
            source_url="https://bf.titan007.com/football/Next_20260418.htm",
        )

        self.assertEqual(len(matches), 2)
        match = matches[0]
        self.assertEqual(match.schedule_id, 2961297)
        self.assertEqual(match.competition_code, "E0")
        self.assertEqual(match.home_team, "布伦特福德")
        self.assertEqual(match.away_team, "埃弗顿")
        self.assertEqual(match.kickoff_time, "15:00")
        self.assertEqual(match.full_time_result, "")
        self.assertIsNone(match.home_goals)
        self.assertTrue(matches[1].competition_code.startswith("T7_"))
        self.assertEqual(matches[1].competition_name, "中乙")

    def test_parse_schedule_matches_honors_explicit_competition_filter(self) -> None:
        matches = parse_schedule_matches(
            SCHEDULE_HTML,
            match_date="2026-04-18",
            source_url="https://bf.titan007.com/football/Next_20260418.htm",
            allowed_competition_codes=["E0"],
        )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].competition_code, "E0")

    def test_parse_schedule_matches_skips_rows_from_adjacent_dates(self) -> None:
        matches = parse_schedule_matches(
            CROSS_DAY_SCHEDULE_HTML,
            match_date="2026-04-15",
            source_url="https://bf.titan007.com/football/Next_20260415.htm",
        )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].match_date, "2026-04-15")
        self.assertEqual(matches[0].home_team, "球队A")

    def test_parse_finished_schedule_extracts_score_and_result(self) -> None:
        match = parse_schedule_matches(
            FINISHED_SCHEDULE_HTML,
            match_date="2026-04-18",
            source_url="https://bf.titan007.com/football/Over_20260418.htm",
        )[0]

        self.assertEqual(match.home_goals, 2)
        self.assertEqual(match.away_goals, 1)
        self.assertEqual(match.full_time_result, "H")

    def test_parse_europe_odds_snapshot_builds_primary_and_average_odds(self) -> None:
        snapshot = parse_europe_odds_snapshot(EUROPE_JS, schedule_id=2961297)

        self.assertEqual(snapshot.primary_company_name, "Bet 365")
        self.assertAlmostEqual(snapshot.primary_open_home_odds or 0.0, 2.10)
        self.assertAlmostEqual(snapshot.primary_close_away_odds or 0.0, 3.60)
        self.assertAlmostEqual(snapshot.avg_open_home_odds or 0.0, 2.11)
        self.assertEqual(snapshot.company_count, 2)

    def test_parse_asian_odds_snapshot_prefers_company_8(self) -> None:
        snapshot = parse_asian_odds_snapshot(ASIAN_HTML, schedule_id=2961297)

        self.assertEqual(snapshot.company_id, 8)
        self.assertEqual(snapshot.company_label, "Bet 365")
        self.assertAlmostEqual(snapshot.open_home_odds or 0.0, 0.80)
        self.assertAlmostEqual(snapshot.open_line or 0.0, -0.25)
        self.assertAlmostEqual(snapshot.close_line or 0.0, -0.75)

    def test_parse_over_under_snapshot_prefers_company_8(self) -> None:
        snapshot = parse_over_under_snapshot(OVER_UNDER_HTML, schedule_id=2961297)

        self.assertEqual(snapshot.company_id, 8)
        self.assertEqual(snapshot.company_label, "Bet 365")
        self.assertAlmostEqual(snapshot.open_line or 0.0, 2.25)
        self.assertAlmostEqual(snapshot.close_line or 0.0, 2.5)
        self.assertAlmostEqual(snapshot.close_under_odds or 0.0, 0.78)

    def test_build_snapshot_row_round_trips_into_training_row(self) -> None:
        match = parse_schedule_matches(
            FINISHED_SCHEDULE_HTML,
            match_date="2026-04-18",
            source_url="https://bf.titan007.com/football/Over_20260418.htm",
        )[0]
        snapshot = parse_europe_odds_snapshot(EUROPE_JS, schedule_id=2961297)
        asian_snapshot = parse_asian_odds_snapshot(ASIAN_HTML, schedule_id=2961297)
        over_under_snapshot = parse_over_under_snapshot(OVER_UNDER_HTML, schedule_id=2961297)
        row = build_snapshot_row(match, snapshot, asian=asian_snapshot, over_under=over_under_snapshot)
        training_row = snapshot_row_to_training_row(row, season_key="2526", default_competition_code="E0")
        labeled_training_row = snapshot_row_to_training_row(
            row,
            season_key="2526",
            default_competition_code="E0",
            preserve_result=True,
        )

        self.assertIsNotNone(training_row)
        self.assertIsNotNone(labeled_training_row)
        assert training_row is not None
        assert labeled_training_row is not None
        self.assertEqual(training_row.home_team, "布伦特福德")
        self.assertEqual(training_row.competition_code, "E0")
        self.assertEqual(training_row.upset_label, "unknown")
        self.assertAlmostEqual(training_row.close_home_odds or 0.0, 2.05)
        self.assertAlmostEqual(training_row.avg_close_away_odds or 0.0, 3.59)
        self.assertAlmostEqual(training_row.open_ah_line or 0.0, -0.25)
        self.assertAlmostEqual(training_row.close_ah_line or 0.0, -0.75)
        self.assertAlmostEqual(training_row.open_over25_odds or 0.0, 0.95)
        self.assertAlmostEqual(training_row.close_under25_odds or 0.0, 0.78)
        self.assertEqual(labeled_training_row.full_time_result, "H")
        self.assertEqual(labeled_training_row.home_goals, 2)
        self.assertEqual(labeled_training_row.away_goals, 1)
        self.assertEqual(labeled_training_row.upset_label, "non_upset")

    def test_snapshot_row_to_training_row_accepts_unknown_titan007_competition(self) -> None:
        raw_row = {
            "competition_code": "T7_U4E2D_U4E59",
            "competition_name": "中乙",
            "match_date": "2026-04-18",
            "kickoff_time": "15:00",
            "home_team": "北京理工",
            "away_team": "上海海港B队",
            "B365H": "3.20",
            "B365D": "3.20",
            "B365A": "2.15",
            "B365CH": "3.70",
            "B365CD": "3.25",
            "B365CA": "1.92",
            "AvgH": "3.20",
            "AvgD": "3.20",
            "AvgA": "2.15",
            "AvgCH": "3.70",
            "AvgCD": "3.25",
            "AvgCA": "1.92",
        }

        training_row = snapshot_row_to_training_row(
            raw_row,
            season_key="2526",
            default_competition_code="T7_U4E2D_U4E59",
        )

        self.assertIsNotNone(training_row)
        assert training_row is not None
        self.assertEqual(training_row.competition_code, "T7_U4E2D_U4E59")
        self.assertEqual(training_row.competition_name, "中乙")
        self.assertEqual(training_row.feature_is_premier_league, 0.0)
        self.assertEqual(training_row.feature_is_la_liga, 0.0)


if __name__ == "__main__":
    unittest.main()
