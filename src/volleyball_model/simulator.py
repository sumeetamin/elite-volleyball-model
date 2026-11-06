from functools import lru_cache


def _check(p_so_a: float, p_so_b: float) -> None:
    if not (0.0 <= p_so_a <= 1.0 and 0.0 <= p_so_b <= 1.0):
        raise ValueError("side-out probabilities must be in [0, 1]")


@lru_cache(maxsize=None)
def _set_win(a: int, b: int, server: int, p_so_a: float, p_so_b: float, target: int) -> float:
    if a >= target and a - b >= 2:
        return 1.0
    if b >= target and b - a >= 2:
        return 0.0
    p = (1.0 - p_so_b) if server == 0 else p_so_a
    # At tied deuce, model both possible serving states. A split pair can end
    # with either team serving, so the tie state does not always repeat.
    if a == b and a >= target - 1:
        p0 = 1.0 - p_so_b  # A wins a rally while A serves.
        p1 = p_so_a        # A wins a rally while B serves.
        win_from_a_serve = p0 * p0
        split_to_a_serve = (1.0 - p0) * p1
        split_to_b_serve = p0 * p_so_b
        win_from_b_serve = p1 * p0
        split_b_to_a_serve = (1.0 - p1) * p1
        split_b_to_b_serve = p1 * p_so_b

        # Solve V0 = W0 + X00*V0 + X01*V1 and
        # V1 = W1 + X10*V0 + X11*V1 for A's win probability.
        m00, m01 = 1.0 - split_to_a_serve, -split_to_b_serve
        m10, m11 = -split_b_to_a_serve, 1.0 - split_b_to_b_serve
        determinant = m00 * m11 - m01 * m10
        if abs(determinant) < 1e-15:
            raise ValueError("Deuce state has no absorbing path under these side-out probabilities")
        v0 = (win_from_a_serve * m11 - m01 * win_from_b_serve) / determinant
        v1 = (m00 * win_from_b_serve - m10 * win_from_a_serve) / determinant
        return v0 if server == 0 else v1
    if server == 0:
        return p * _set_win(a + 1, b, 0, p_so_a, p_so_b, target) + (1-p) * _set_win(a, b + 1, 1, p_so_a, p_so_b, target)
    return p * _set_win(a + 1, b, 0, p_so_a, p_so_b, target) + (1-p) * _set_win(a, b + 1, 1, p_so_a, p_so_b, target)


def set_win_probability(p_so_a: float, p_so_b: float, target: int = 25) -> float:
    _check(p_so_a, p_so_b)
    if target < 2:
        raise ValueError("target must be at least 2")
    p_a_start = round(_set_win(0, 0, 0, p_so_a, p_so_b, target), 12)
    p_b_start = round(_set_win(0, 0, 1, p_so_a, p_so_b, target), 12)
    return (p_a_start + p_b_start) / 2


def match_probabilities(p_so_a: float, p_so_b: float) -> dict[str, float]:
    p = set_win_probability(p_so_a, p_so_b, 25)
    fifth = set_win_probability(p_so_a, p_so_b, 15)
    q = 1-p
    scores = {
        "3-0": p**3,
        "3-1": 3*p**3*q,
        "3-2": 6*p**2*q**2*fifth,
        "0-3": q**3,
        "1-3": 3*q**3*p,
        "2-3": 6*q**2*p**2*(1-fifth),
    }
    scores["team_a_win"] = sum(scores[k] for k in ("3-0", "3-1", "3-2"))
    return scores
