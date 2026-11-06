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
        })

        predictions, summary = evaluate_walk_forward(
            frame, "match_date", "target", ["signal"], "baseline"
        )

        self.assertEqual(set(predictions["fold"]), {"final_test"})
        self.assertGreater(predictions["match_date"].min(), summary["development_walk_forward"]["last_test_date"])
        self.assertEqual(summary["evaluated_rows"], len(predictions))


if __name__ == "__main__":
    unittest.main()
