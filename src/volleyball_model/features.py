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
    data["_rating_scope"] = data["competition_key"].astype(str)
    if "sex" in data.columns:
        data["_rating_scope"] += "::" + data["sex"].fillna("unknown").astype(str)
    if "home_advantage_points" in data.columns:
        row_home_advantage = pd.to_numeric(data["home_advantage_points"], errors="coerce").fillna(home_advantage)
    else:
        row_home_advantage = pd.Series(home_advantage, index=data.index, dtype=float)
    data["_home_advantage"] = row_home_advantage
    data = data.sort_values(["_date", "_rating_scope", "_position"])
    output = pd.DataFrame(index=range(len(data)), columns=[
        "home_elo", "away_elo", "elo_diff", "home_advantage_points",
        "elo_home_win_probability", "target_home_win"
    ])
    ratings: dict[tuple[str, str], float] = {}

    for (date, competition), day in data.groupby(["_date", "_rating_scope"], sort=True):
        updates: dict[tuple[str, str], float] = {}
        for _, row in day.iterrows():
            home_key = (str(competition), str(row["home_team"]))
            away_key = (str(competition), str(row["away_team"]))
            home_rating = ratings.get(home_key, 1500.0)
            away_rating = ratings.get(away_key, 1500.0)
            row_advantage = float(row["_home_advantage"])
            diff = home_rating + row_advantage - away_rating
            expected = 1.0 / (1.0 + 10.0 ** (-diff / 400.0))
            pos = int(row["_position"])
            output.loc[pos] = [home_rating, away_rating, home_rating - away_rating,
                               row_advantage, expected, float("nan")]
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


def build_match_features(matches: pd.DataFrame, k_factor: float = 20.0,
                         home_advantage: float = 50.0, form_span: int = 5) -> pd.DataFrame:
    """Build prior-only Elo, rest, and recent-win-form match features."""
    if form_span < 1:
        raise ValueError("form_span must be positive")
    required = {"competition_key", "match_date", "home_team", "away_team", "home_sets", "away_sets"}
    missing = required - set(matches.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    base = matches.copy()
    base["_row_position"] = range(len(base))
    base["_rating_scope"] = base["competition_key"].astype(str)
    if "sex" in base.columns:
        base["_rating_scope"] += "::" + base["sex"].fillna("unknown").astype(str)
    base["_home_team_key"] = base["_rating_scope"] + "::" + base["home_team"].astype(str)
    base["_away_team_key"] = base["_rating_scope"] + "::" + base["away_team"].astype(str)

    elo = build_elo_features(matches, k_factor, home_advantage)
    home_schedule = base.rename(columns={"_home_team_key": "_team_key"})
    away_schedule = base.rename(columns={"_away_team_key": "_team_key"})
    home_rest = rest_days(home_schedule, "_team_key").to_numpy()
    away_rest = rest_days(away_schedule, "_team_key").to_numpy()

    events = []
    for _, row in base.iterrows():
        try:
            hs, aws = int(row["home_sets"]), int(row["away_sets"])
        except (TypeError, ValueError):
            continue
        if hs == aws or min(hs, aws) < 0 or max(hs, aws) != 3 or min(hs, aws) > 2:
            continue
        home_won = float(hs > aws)
        position = int(row["_row_position"])
        event_id = row.get("match_id", row.get("source_match_id", position))
        date = row["match_date"]
        set_margin = hs - aws
        events.append((position, event_id, date, row["_home_team_key"], home_won, set_margin))
        events.append((position, event_id, date, row["_away_team_key"], 1.0 - home_won, -set_margin))
    event_frame = pd.DataFrame(events, columns=["_row_position", "match_id", "match_date", "_team_key", "win", "set_margin"])
    form_by_position = {}
    if not event_frame.empty:
        event_frame["_form_prior"] = sequential_ewma(event_frame, "_team_key", "win", form_span)
        event_frame["_set_margin_prior"] = sequential_ewma(event_frame, "_team_key", "set_margin", form_span)
        home_keys = base["_home_team_key"].tolist()
        away_keys = base["_away_team_key"].tolist()
        for position, group in event_frame.groupby("_row_position", sort=False):
            home_event = group[group["_team_key"].eq(home_keys[position])]
            away_event = group[group["_team_key"].eq(away_keys[position])]
            form_by_position[position] = (
                home_event["_form_prior"].iloc[0] if not home_event.empty else float("nan"),
                away_event["_form_prior"].iloc[0] if not away_event.empty else float("nan"),
                home_event["_set_margin_prior"].iloc[0] if not home_event.empty else float("nan"),
                away_event["_set_margin_prior"].iloc[0] if not away_event.empty else float("nan"),
            )

    features = elo.copy()
    features["home_rest_days"] = home_rest
    features["away_rest_days"] = away_rest
    features["rest_days_diff"] = features["home_rest_days"] - features["away_rest_days"]
    forms = [form_by_position.get(i, (float("nan"),) * 4) for i in range(len(base))]
    features["home_form_ewma"] = [x[0] for x in forms]
    features["away_form_ewma"] = [x[1] for x in forms]
    features["form_diff"] = features["home_form_ewma"] - features["away_form_ewma"]
    features["home_set_margin_ewma"] = [x[2] for x in forms]
    features["away_set_margin_ewma"] = [x[3] for x in forms]
    features["set_margin_diff"] = features["home_set_margin_ewma"] - features["away_set_margin_ewma"]
    features.index = matches.index
    return features


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
            day_values = date_group[value_column].dropna().astype(float)
            if not day_values.empty:
                history.append(float(day_values.mean()))
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
