import tempfile
import unittest
from pathlib import Path

import pandas as pd

from volleyball_model.sources import _parse_match_date, load_match_sources


class SourceNormalizationTests(unittest.TestCase):
    def test_supported_source_directory_maps_league_cev_and_fivb_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pd.DataFrame([{
                "source": "CBV", "source_match_id": "m1", "competition_key": "brazil_superliga",
                "season": "2024/25", "sex": "F", "match_date": "2024-10-01", "home_team": "A",
                "away_team": "B", "home_sets": 3, "away_sets": 1, "match_status": "completed",
                "source_url": "https://official.invalid/m1", "source_sha256": "abc", "phase": "regular_season",
            }]).to_csv(root / "cbv_superliga_matches.csv", index=False)
            pd.DataFrame([{
                "match_id": "CEV_1", "season_name": "2000/01 EUROPEAN CHAMPIONS LEAGUE WOMEN",
                "gender": "W", "team_a": "C", "team_b": "D", "sets_a": 3, "sets_b": 2,
                "match_status": "completed", "played_at_local": "05/12/2000 20:00",
                "phase": "Main Phase", "source_url": "https://official.invalid/cev", "source_sha256": "def",
            }]).to_csv(root / "cev_champions_league_matches.csv", index=False)
            pd.DataFrame([
                {"match_id": "FIVB_VIS_1", "competition_name": "FIVB Men's World League 2006", "edition_year": 2006,
                 "gender": "M", "team_a_name": "E", "team_b_name": "F", "sets_a": 3, "sets_b": 0,
                 "status": "Closed", "scheduled_at_utc": "2006-07-01T10:00:00Z", "source_url": "https://official.invalid/fivb",
                 "source_sha256": "ghi"},
                {"match_id": "FIVB_VIS_2", "competition_name": "FIVB Men's World Championship 2006", "edition_year": 2006,
                 "gender": "M", "team_a_name": "G", "team_b_name": "H", "sets_a": 3, "sets_b": 0,
                 "status": "Closed", "scheduled_at_utc": "2006-07-02T10:00:00Z"},
                {"match_id": "FIVB_VIS_3", "competition_name": "FIVB Men's World League 2006", "edition_year": 2006,
                 "gender": "M", "team_a_name": "I", "team_b_name": "J", "sets_a": 3, "sets_b": 1,
                 "status": "Closed", "scheduled_at_utc": ""},
            ]).to_csv(root / "fivb_vis_matches.csv", index=False)

            matches, manifest = load_match_sources([root])

        self.assertEqual(len(matches), 3)
        cev = matches.loc[matches.competition_key.eq("cev_cl")].iloc[0]
        self.assertEqual(cev.sex, "F")
        self.assertEqual(cev.season, "2000/01")
        self.assertEqual(cev.home_advantage_points, 0.0)
        self.assertEqual(cev.match_date.isoformat(), "2000-12-05T20:00:00+00:00")
        international = matches.loc[matches.competition_key.eq("vnl")].iloc[0]
        self.assertEqual(international.season, "World League 2006")
        self.assertEqual(international.home_advantage_points, 0.0)
        domestic = matches.loc[matches.competition_key.eq("brazil_superliga")].iloc[0]
        self.assertEqual(domestic.home_advantage_points, 50.0)
        self.assertEqual(domestic.source_url, "https://official.invalid/m1")
        self.assertEqual(sum("path" in item for item in manifest), 3)
        quality = next(item["normalization_quality"] for item in manifest if "normalization_quality" in item)
        self.assertEqual(quality["rows_without_timestamp_dropped"], 1)

    def test_ceV_multi_day_archive_window_uses_latest_possible_date(self):
        self.assertEqual(_parse_match_date("15./16./17. 02.2005").isoformat(), "2005-02-17T00:00:00+00:00")
        self.assertEqual(_parse_match_date("2026-06-10T05:00:00Z").isoformat(), "2026-06-10T05:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
