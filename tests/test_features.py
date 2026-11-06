import unittest

import pandas as pd

from volleyball_model.features import build_elo_features, build_match_features, rest_days, sequential_ewma


class RestDaysTests(unittest.TestCase):
    def test_same_date_matches_share_prior_rest(self):
        matches = pd.DataFrame({
            "team": ["A", "A", "A", "B"],
            "match_date": pd.to_datetime(["2024-01-01", "2024-01-04", "2024-01-04", "2024-01-11"]),
        })

        actual = rest_days(matches, "team").tolist()

        self.assertTrue(pd.isna(actual[0]))
        self.assertEqual(actual[1:3], [3.0, 3.0])
        self.assertTrue(pd.isna(actual[3]))

    def test_rest_is_capped_at_seven_days(self):
        matches = pd.DataFrame({
            "team": ["A", "A"],
            "match_date": pd.to_datetime(["2024-01-01", "2024-01-20"]),
        })
        self.assertEqual(rest_days(matches, "team").iloc[1], 7.0)

    def test_ewma_groups_simultaneous_kickoff_times_by_calendar_day(self):
        matches = pd.DataFrame({
            "team": ["A", "A", "A"],
            "match_id": [1, 2, 3],
            "match_date": pd.to_datetime(["2024-01-01 10:00Z", "2024-01-02 11:00Z", "2024-01-02 21:00Z"]),
            "value": [4.0, 10.0, 20.0],
        })
        actual = sequential_ewma(matches, "team", "value", span=2)
        self.assertEqual(actual.iloc[1], 4.0)
        self.assertEqual(actual.iloc[2], 4.0)


class EloFeatureTests(unittest.TestCase):
    def test_same_day_results_do_not_change_same_day_ratings(self):
        matches = pd.DataFrame({
            "competition_key": ["league"] * 3,
            "match_date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-02"]),
            "home_team": ["A", "A", "B"],
            "away_team": ["B", "B", "A"],
            "home_sets": [3, 3, 0],
            "away_sets": [0, 0, 3],
        })

        features = build_elo_features(matches)

        self.assertEqual(features.loc[1, "home_elo"], features.loc[2, "away_elo"])
        self.assertEqual(features.loc[1, "away_elo"], features.loc[2, "home_elo"])
        self.assertEqual(features.loc[1, "target_home_win"], 1.0)
        self.assertEqual(features.loc[2, "target_home_win"], 0.0)

    def test_missing_result_has_features_but_does_not_update_rating(self):
        matches = pd.DataFrame({
            "competition_key": ["league"] * 3,
            "match_date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "home_team": ["A", "A", "A"],
            "away_team": ["B", "B", "B"],
            "home_sets": [3, None, 3],
            "away_sets": [1, None, 1],
        })

        features = build_elo_features(matches)

        self.assertTrue(pd.isna(features.loc[1, "target_home_win"]))
        self.assertEqual(features.loc[1, "home_elo"], features.loc[2, "home_elo"])

    def test_elo_histories_are_separate_by_gender(self):
        matches = pd.DataFrame({
            "competition_key": ["league", "league"],
            "sex": ["M", "F"],
            "match_date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "home_team": ["A", "A"],
            "away_team": ["B", "B"],
            "home_sets": [3, 0],
            "away_sets": [0, 3],
        })
        features = build_elo_features(matches)
        self.assertEqual(features.loc[1, "home_elo"], 1500.0)
        self.assertEqual(features.loc[1, "away_elo"], 1500.0)


class MatchFeatureTests(unittest.TestCase):
    def test_same_date_games_share_prior_form_and_rest(self):
        matches = pd.DataFrame({
            "competition_key": ["league"] * 3,
            "sex": ["M"] * 3,
            "match_date": pd.to_datetime(["2024-01-01 12:00Z", "2024-01-02 10:00Z", "2024-01-02 20:00Z"]),
            "home_team": ["A", "A", "A"],
            "away_team": ["B", "B", "C"],
            "home_sets": [3, 0, 0],
            "away_sets": [0, 3, 3],
        })
        features = build_match_features(matches)
        self.assertTrue(pd.isna(features.loc[0, "home_form_ewma"]))
        self.assertEqual(features.loc[1, "home_form_ewma"], 1.0)
        self.assertEqual(features.loc[2, "home_form_ewma"], 1.0)
        self.assertEqual(features.loc[1, "home_rest_days"], 1.0)
        self.assertEqual(features.loc[2, "home_rest_days"], 1.0)


if __name__ == "__main__":
    unittest.main()
