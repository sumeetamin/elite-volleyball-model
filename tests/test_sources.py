import tempfile
import unittest
from pathlib import Path

import pandas as pd

from volleyball_model.sources import _normalize_table, _parse_match_date, _season_from_cev, load_match_sources


class SourceNormalizationTests(unittest.TestCase):
    def test_plusliga_2001_02_archive_is_supported_with_date_lineage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for season, filename, match_id in (
                ("2001/02", "plusliga_m_2001_02_matches.csv", "1000256"),
                ("2003/04", "plusliga_m_2003_04_matches.csv", "1002256"),
                ("2004/05", "plusliga_m_2004_05_matches.csv", "1003256"),
                ("2005/06", "plusliga_m_2005_06_matches.csv", "1004256"),
                ("2006/07", "plusliga_m_2006_07_matches.csv", "1005256"),
                ("2007/08", "plusliga_m_2007_08_matches.csv", "1006256"),
                ("2008/09", "plusliga_m_2008_09_matches.csv", "1007256"),
                ("2009/10", "plusliga_m_2009_10_matches.csv", "1008256"),
                ("2010/11", "plusliga_m_2010_11_matches.csv", "1009256"),
                ("2011/12", "plusliga_m_2011_12_matches.csv", "derived-sha256:test"),
            ):
                pd.DataFrame([{
                    "source": "official Polish league team-comparison archive",
                    "source_match_id": match_id, "competition_key": "plusliga",
                    "competition": "Polish PlusLiga", "sex": "M", "season": season,
                    "phase": "regular_season", "match_date": f"{season[:4]}-09-30",
                    "home_team": "Team A", "away_team": "Team B", "home_sets": 3,
                    "away_sets": 1, "status": "completed",
                    "source_url": "https://official.invalid/match",
                    "source_sha256": "abc", "date_source_url": "https://official.invalid/team",
                    "date_source_sha256": "def",
                }]).to_csv(root / filename, index=False)
            matches, manifest = load_match_sources([root])
        self.assertEqual(len(matches), 10)
        self.assertEqual(set(matches.season), {"2001/02", "2003/04", "2004/05", "2005/06", "2006/07", "2007/08", "2008/09", "2009/10", "2010/11", "2011/12"})
        self.assertTrue(matches.match_status.eq("completed").all())
        self.assertTrue(matches.date_source_url.eq("https://official.invalid/team").all())
        self.assertEqual(sum("path" in item for item in manifest), 10)

    def test_cbv_official_page_team_ids_survive_normalization(self):
        row = pd.DataFrame([{
            "competition_key": "brazil_superliga", "season": "2025/26", "sex": "M",
            "match_date": "2025-10-21", "home_team": "Team A", "away_team": "Team B",
            "home_team_id": "2152471", "away_team_id": "2152472",
            "home_sets": 3, "away_sets": 1, "match_status": "completed",
            "source_match_id": "2252776", "date_source_url": "https://cbv.com.br/official",
            "date_source_sha256": "abc",
        }])
        normalized = _normalize_table(row, Path("cbv_superliga_matches.csv"))
        self.assertEqual(normalized.iloc[0].home_team_id, "2152471")
        self.assertEqual(normalized.iloc[0].away_team_id, "2152472")
        self.assertEqual(normalized.iloc[0].date_source_url, "https://cbv.com.br/official")

    def test_ceV_match_date_outside_named_season_is_quarantined(self):
        row = pd.DataFrame([{
            "match_id": "CEV_4150", "season_name": "2000/01 EUROPEAN CHAMPIONS LEAGUE",
            "gender": "M", "team_a": "A", "team_b": "B", "sets_a": 3,
            "sets_b": 1, "match_status": "completed", "played_at_local": "24/01/2000 20:00",
        }])
        normalized = _normalize_table(row, Path("cev.csv"))
        self.assertTrue(pd.isna(normalized.iloc[0]["match_date"]))

    def test_ceV_final_year_title_maps_to_club_season(self):
        self.assertEqual(_season_from_cev("2012 CEV Volleyball Champions League - Men"), "2011/12")
        self.assertEqual(_season_from_cev("CEV XTB Champions League Volley 2027 | Men"), "2026/27")
        self.assertEqual(_season_from_cev("2011 CEV Volleyball Cup"), "")

    def test_cancelled_fixture_with_stale_score_cannot_be_training_result(self):
        row = pd.DataFrame([{
            "competition_key": "brazil_superliga", "season": "2020/21", "sex": "M",
            "match_date": "2020-11-01", "home_team": "A", "away_team": "B",
            "home_sets": 3, "away_sets": 1, "match_status": "cancelled",
        }])
        normalized = _normalize_table(row, Path("fixture.csv"))
        self.assertEqual(normalized.iloc[0]["match_status"], "cancelled")
        self.assertTrue(pd.isna(normalized.iloc[0]["home_sets"]))

    def test_supported_source_directory_maps_league_cev_and_fivb_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pd.DataFrame([{
                "source": "CBV", "source_match_id": "m1", "competition_key": "brazil_superliga",
                "season": "2024/25", "sex": "F", "match_date": "2024-10-01", "home_team": "A",
                "away_team": "B", "home_sets": 3, "away_sets": 1, "match_status": "completed",
                "source_url": "https://official.invalid/m1", "source_sha256": "abc", "phase": "regular_season",
                "date_source_url": "https://official.invalid/roster", "date_source_sha256": "xyz",
            }]).to_csv(root / "cbv_superliga_matches.csv", index=False)
            pd.DataFrame([{
                "source_match_id": "w1", "competition_key": "italy_serie_a1_women",
                "season": "2024/25", "sex": "F", "match_date": "2024-10-02",
                "home_team": "Women A", "away_team": "Women B", "home_sets": 3,
                "away_sets": 1, "status": "completed", "phase": "regular_season",
                "source_url": "https://official.invalid/w1", "source_sha256": "sha",
            }]).to_csv(root / "italy_serie_a1_women_matches.csv", index=False)
            pd.DataFrame([{
                "match_id": "CEV_1", "season_name": "2000/01 EUROPEAN CHAMPIONS LEAGUE WOMEN",
                "gender": "W", "team_a": "C", "team_b": "D", "sets_a": 3, "sets_b": 2,
                "match_status": "completed", "played_at_local": "05/12/2000 20:00",
                "phase": "Main Phase", "source_url": "https://official.invalid/cev", "source_sha256": "def",
            }]).to_csv(root / "cev_champions_league_matches.csv", index=False)
            pd.DataFrame([
                {"match_id": "FIVB_VIS_1", "competition_name": "FIVB Men's World League 2006", "edition_year": 2006,
                 "gender": "M", "team_a_id": "POL", "team_a_name": "E", "team_b_id": "BRA", "team_b_name": "F", "sets_a": 3, "sets_b": 0,
                 "status": "Closed", "scheduled_at_utc": "2006-07-01T10:00:00Z", "source_url": "https://official.invalid/fivb",
                 "source_sha256": "ghi"},
                {"match_id": "FIVB_VIS_2", "competition_name": "FIVB Men's World Championship 2006", "edition_year": 2006,
                 "gender": "M", "team_a_name": "G", "team_b_name": "H", "sets_a": 3, "sets_b": 0,
                 "status": "Closed", "scheduled_at_utc": "2006-07-02T10:00:00Z"},
                {"match_id": "FIVB_VIS_3", "competition_name": "FIVB Men's World League 2006", "edition_year": 2006,
                 "gender": "M", "team_a_id": "POL", "team_a_name": "I", "team_b_id": "BRA", "team_b_name": "J", "sets_a": 3, "sets_b": 1,
                 "status": "Closed", "scheduled_at_utc": ""},
            ]).to_csv(root / "fivb_vis_matches.csv", index=False)

            matches, manifest = load_match_sources([root])

        self.assertEqual(len(matches), 4)
        cev = matches.loc[matches.competition_key.eq("cev_cl")].iloc[0]
        self.assertEqual(cev.sex, "F")
        self.assertEqual(cev.season, "2000/01")
        self.assertEqual(cev.home_advantage_points, 0.0)
        self.assertEqual(cev.match_date.isoformat(), "2000-12-05T20:00:00+00:00")
        international = matches.loc[matches.competition_key.eq("vnl")].iloc[0]
        self.assertEqual(international.season, "World League 2006")
        self.assertEqual(international.home_advantage_points, 0.0)
        self.assertEqual(international.home_team_id, "POL")
        self.assertEqual(international.away_team_id, "BRA")
        domestic = matches.loc[matches.competition_key.eq("brazil_superliga")].iloc[0]
        self.assertEqual(domestic.home_advantage_points, 50.0)
        self.assertEqual(domestic.source_url, "https://official.invalid/m1")
        self.assertEqual(domestic.date_source_url, "https://official.invalid/roster")
        self.assertEqual(domestic.date_source_sha256, "xyz")
        self.assertEqual(sum("path" in item for item in manifest), 4)
        self.assertEqual(len(matches.loc[matches.competition_key.eq("italy_serie_a1_women")]), 1)
        quality = next(item["normalization_quality"] for item in manifest if "normalization_quality" in item)
        self.assertEqual(quality["rows_without_timestamp_dropped"], 1)

    def test_ceV_multi_day_archive_window_uses_latest_possible_date(self):
        self.assertEqual(_parse_match_date("15./16./17. 02.2005").isoformat(), "2005-02-17T00:00:00+00:00")
        self.assertEqual(_parse_match_date("2026-06-10T05:00:00Z").isoformat(), "2026-06-10T05:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
