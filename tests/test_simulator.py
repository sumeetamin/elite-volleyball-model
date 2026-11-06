"""Fast invariant tests for the exact point-to-set-to-match simulator."""
import math
import unittest

from volleyball_model.simulator import match_probabilities, set_win_probability


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


if __name__ == "__main__":
    unittest.main()
