"""Fast invariant tests for the exact point-to-set-to-match simulator."""
import math
import unittest

from volleyball_model.simulator import _set_win, match_probabilities, set_win_probability


class SimulatorTests(unittest.TestCase):
    def test_match_score_probability_mass(self):
        scores = match_probabilities(0.64, 0.61)
        mass = sum(scores[key] for key in ("3-0", "3-1", "3-2", "0-3", "1-3", "2-3"))
        self.assertTrue(math.isclose(mass, 1.0, abs_tol=1e-10))

    def test_equal_sides_are_symmetric(self):
        self.assertTrue(math.isclose(set_win_probability(0.62, 0.62), 0.5, abs_tol=1e-9))
        result = match_probabilities(0.62, 0.62)
        self.assertTrue(math.isclose(result["team_a_win"], 0.5, abs_tol=1e-9))
        self.assertTrue(math.isclose(result["3-0"], result["0-3"], abs_tol=1e-9))

    def test_invalid_probabilities_are_rejected(self):
        with self.assertRaises(ValueError):
            match_probabilities(1.01, 0.5)

    def test_deuce_accounts_for_server_state_after_split_rallies(self):
        # Exact two-state Markov solution at 2:2 in a target-3 set.
        expected_a_serves = 0.6213592233009708
        expected_b_serves = 0.7572815533980582
        self.assertAlmostEqual(_set_win(2, 2, 0, 0.75, 0.6, 3), expected_a_serves, places=12)
        self.assertAlmostEqual(_set_win(2, 2, 1, 0.75, 0.6, 3), expected_b_serves, places=12)

    def test_deuce_without_any_absorbing_path_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "no absorbing path"):
            _set_win(24, 24, 0, 1.0, 1.0, 25)


if __name__ == "__main__":
    unittest.main()
