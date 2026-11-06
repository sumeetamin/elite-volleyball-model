import unittest

import pandas as pd

from volleyball_model.backtest import evaluate_walk_forward


class FinalHoldoutTests(unittest.TestCase):
    def test_predictions_are_only_from_later_final_holdout(self):
        dates = pd.date_range("2024-01-01", periods=60, freq="D", tz="UTC")
        target = [i % 2 for i in range(len(dates))]
        frame = pd.DataFrame({
            "match_date": dates,
            "target": target,
            "signal": [float(value) for value in target],
            "baseline": [0.5] * len(dates),
            "competition_key": ["league"] * len(dates),
            "sex": ["M" if i % 2 else "F" for i in range(len(dates))],
            "season": ["2024/25"] * len(dates),
        })

        predictions, summary = evaluate_walk_forward(
            frame, "match_date", "target", ["signal"], "baseline"
        )

        self.assertEqual(set(predictions["fold"]), {"final_test"})
        self.assertGreater(predictions["match_date"].min(), summary["development_walk_forward"]["last_test_date"])
        self.assertEqual(summary["evaluated_rows"], len(predictions))
        self.assertIn("sex", summary["segment_metrics"])
        self.assertIn("season", predictions.columns)

    def test_final_holdout_keeps_the_latest_two_seasons_whole(self):
        dates = pd.date_range("2020-01-01", periods=150, freq="D", tz="UTC")
        frame = pd.DataFrame({
            "match_date": dates,
            "target": [i % 2 for i in range(len(dates))],
            "signal": [float(i % 2) for i in range(len(dates))],
            "season": [f"{2020 + i // 30}/{str(2021 + i // 30)[-2:]}" for i in range(len(dates))],
        })
        predictions, summary = evaluate_walk_forward(
            frame, "match_date", "target", ["signal"]
        )
        self.assertEqual(summary["final_test_split_method"], "whole_seasons")
        self.assertEqual(summary["final_test_seasons"], ["2023/24", "2024/25"])
        self.assertEqual(summary["final_test_fraction"], 0.15)
        self.assertAlmostEqual(summary["realized_final_test_fraction"], 0.4)
        self.assertEqual(predictions["match_date"].min(), dates[90].isoformat())

    def test_final_holdout_orders_competition_prefixed_seasons_by_embedded_year(self):
        labels = [
            "World League 2006", "World Grand Prix 2007", "World League 2008",
            "World Grand Prix 2009", "VNL 2020", "VNL 2026",
        ]
        dates = [date for label in labels for date in pd.date_range(
            f"{label[-4:]}-01-01", periods=30, freq="D", tz="UTC")]
        frame = pd.DataFrame({
            "match_date": dates,
            "target": [i % 2 for i in range(len(dates))],
            "signal": [float(i % 2) for i in range(len(dates))],
            "season": [labels[i // 30] for i in range(len(dates))],
        })

        predictions, summary = evaluate_walk_forward(
            frame, "match_date", "target", ["signal"]
        )

        self.assertEqual(summary["final_test_seasons"], ["VNL 2020", "VNL 2026"])
        self.assertEqual(predictions["match_date"].min(), dates[120].isoformat())


if __name__ == "__main__":
    unittest.main()
