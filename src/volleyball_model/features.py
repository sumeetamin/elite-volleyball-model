from __future__ import annotations
import pandas as pd


def build_elo_features(matches: pd.DataFrame, k_factor: float = 20.0,
                       home_advantage: float = 50.0) -> pd.DataFrame:
    """Build prior-only team Elo features without using outcomes from the same date.

    Input requires competition_key, match_date, home_team, away_team,
    home_sets, and away_sets. Rows without valid final set scores still receive
    pre-match features but never update ratings or receive a target.
    """
    required = {"competition_key", "match_date", "home_team", "away_team", "home_sets", "away_sets"}
    missing = required - set(matches.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    if k_factor <= 0:
        raise ValueError("k_factor must be positive")

    data = matches.copy()
    data["_position"] = range(len(data))
    data["_date"] = pd.to_datetime(data["match_date"], utc=True, errors="coerce").dt.normalize()
    if data["_date"].isna().any():
        raise ValueError("match_date contains missing or invalid values")
    for column in ("competition_key", "home_team", "away_team"):
        if data[column].isna().any() or data[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"{column} contains missing or blank values")
    data = data.sort_values(["_date", "competition_key", "_position"])
    output = pd.DataFrame(index=range(len(data)), columns=[
        "home_elo", "away_elo", "elo_diff", "elo_home_win_probability", "target_home_win"
    ])
    ratings: dict[tuple[str, str], float] = {}

    for (date, competition), day in data.groupby(["_date", "competition_key"], sort=True):
        updates: dict[tuple[str, str], float] = {}
        for _, row in day.iterrows():
            home_key = (str(competition), str(row["home_team"]))
            away_key = (str(competition), str(row["away_team"]))
            home_rating = ratings.get(home_key, 1500.0)
            away_rating = ratings.get(away_key, 1500.0)
            diff = home_rating + home_advantage - away_rating
            expected = 1.0 / (1.0 + 10.0 ** (-diff / 400.0))
            pos = int(row["_position"])
            output.loc[pos] = [home_rating, away_rating, home_rating - away_rating, expected, float("nan")]
            try:
                hs, aws = int(row["home_sets"]), int(row["away_sets"])
            except (TypeError, ValueError):
                continue
            if hs == aws or min(hs, aws) < 0 or max(hs, aws) != 3 or min(hs, aws) > 2:
                continue
            actual = 1.0 if hs > aws else 0.0
            output.loc[pos, "target_home_win"] = actual
            delta = k_factor * (actual - expected)
            updates[home_key] = updates.get(home_key, 0.0) + delta
            updates[away_key] = updates.get(away_key, 0.0) - delta
        for team_key, delta in updates.items():
            ratings[team_key] = ratings.get(team_key, 1500.0) + delta

    output = output.sort_index()
    for column in output.columns:
        output[column] = pd.to_numeric(output[column], errors="coerce")
    output.index = matches.index
    return output


def sequential_ewma(matches: pd.DataFrame, team_column: str, value_column: str, span: int) -> pd.Series:
    """Return prior-only EWMA aligned to rows; same-date matches see same prior state."""
    if span < 1:
        raise ValueError("span must be positive")
    out = pd.Series(index=matches.index, dtype="float64")
    ordered = matches.copy()
    ordered["_match_day"] = pd.to_datetime(ordered["match_date"], utc=True).dt.normalize()
    ordered = ordered.sort_values([team_column, "_match_day", "match_id"])
    for _, group in ordered.groupby(team_column, sort=False):
        history: list[float] = []
        for _, date_group in group.groupby("_match_day", sort=True):
            prior = pd.Series(history, dtype="float64").ewm(span=span, adjust=False).mean().iloc[-1] if history else float("nan")
            out.loc[date_group.index] = prior
            # Update only after emitting every simultaneous fixture's prior.
            history.extend(date_group[value_column].dropna().astype(float).tolist())
    return out


def rest_days(matches: pd.DataFrame, team_column: str) -> pd.Series:
    """Return days since the team's previous match date, capped at seven.

    All matches for a team on the same date receive the same prior-rest value;
    simultaneous fixtures never create a zero-day gap for one another.
    """
    dates = pd.to_datetime(matches["match_date"], utc=True, errors="coerce").dt.normalize()
    daily = matches[[team_column]].assign(_date=dates).drop_duplicates([team_column, "_date"])
    daily = daily.sort_values([team_column, "_date"])
    daily["_rest_days"] = (
        daily.groupby(team_column)["_date"].diff().dt.total_seconds().div(86400).clip(0, 7)
    )
    lookup = daily.set_index([team_column, "_date"])["_rest_days"]
    keys = pd.MultiIndex.from_arrays([matches[team_column], dates])
    return pd.Series(lookup.reindex(keys).to_numpy(), index=matches.index, dtype="float64")
