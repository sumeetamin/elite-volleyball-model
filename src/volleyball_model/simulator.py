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
    # At tied deuce, the next two rallies form a repeating two-point cycle.
    if a == b and a >= target - 1:
        p_first = p
        p_second_if_a = 1.0 - p_so_b  # A serves after winning point one.
        p_second_if_b = p_so_a        # A receives after losing point one.
        win_two = p_first * p_second_if_a
        lose_two = (1.0 - p_first) * (1.0 - p_second_if_b)
        split = 1.0 - win_two - lose_two
        return win_two / (1.0 - split)
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
