"""Normalize supported repository match tables for model feature building."""
from __future__ import annotations

from pathlib import Path
import hashlib
import re

import pandas as pd


CANONICAL_COLUMNS = [
    "competition_key", "sex", "season", "match_date", "home_team", "away_team",
    "home_sets", "away_sets", "match_status", "phase", "source", "source_match_id",
    "source_url", "source_sha256", "home_advantage_points", "date_precision",
    "home_team_id", "away_team_id", "date_source_url", "date_source_sha256",
]
SUPPORTED_FILES = {
    "cbv_superliga_matches.csv", "cev_champions_league_matches.csv",
    "cev_champions_league_matches_2000_2026_27.csv",
    "fivb_vis_matches.csv", "italy_superlega_m_2024_25.csv", "italy_superlega_matches_2000_2026.csv",
    "italy_serie_a1_women_matches.csv",
    "plusliga_m_2024_25.csv", "plusliga_m_2000_01_head_to_head.csv",
    "plusliga_m_2001_02_matches.csv", "plusliga_m_2002_03_matches.csv",
    "plusliga_m_2003_04_matches.csv", "plusliga_m_2004_05_matches.csv",
    "plusliga_m_2005_06_matches.csv",
    "plusliga_m_2006_07_matches.csv",
    "plusliga_m_2007_08_matches.csv",
}


def _col(frame: pd.DataFrame, name: str, default: object) -> pd.Series:
    if name in frame.columns:
        return frame[name]
    if isinstance(default, pd.Series):
        return default.reindex(frame.index)
    return pd.Series(default, index=frame.index)


def _fivb_lineage(row: pd.Series) -> tuple[str, str] | None:
    title = str(row.get("competition_name", ""))
    folded = title.casefold()
    if re.search(r"qualification|qualifying|qualifier|test only", folded):
        return None
    sex = {"M": "M", "F": "F", "W": "F"}.get(str(row.get("gender", "")).upper())
    if not sex:
        return None
    if sex == "M" and "world league" not in folded and not re.search(r"\bvnl\b|volleyball nations league", folded):
        return None
    if sex == "F" and "world grand prix" not in folded and not re.search(r"\bvnl\b|volleyball nations league", folded):
        return None
    year_match = re.search(r"\b(20\d{2})\b", str(row.get("edition_year", ""))) or re.search(r"\b(20\d{2})\b", title)
    if not year_match:
        return None
    year = int(year_match.group(1))
    title_year = re.search(r"\b(20\d{2})\b", title)
    if title_year and int(title_year.group(1)) != year:
        return None
    season = f"VNL {year}" if year >= 2018 else f"{'World League' if sex == 'M' else 'World Grand Prix'} {year}"
    return sex, season


def _season_from_cev(value: object) -> str:
    match = re.search(r"\b(20\d{2})\s*/\s*(?:20)?(\d{2})\b", str(value))
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    label = str(value)
    edition = re.search(r"\b(20\d{2})\s+CEV\b|\bCEV\b.*\b(20\d{2})\b", label, re.IGNORECASE)
    if edition and "champions league" in label.casefold():
        end_year = int(edition.group(1) or edition.group(2))
        return f"{end_year - 1}/{end_year % 100:02d}"
    return ""


def _parse_match_date(value: object) -> pd.Timestamp:
    text = str(value).strip()
    if not text or text.casefold() in {"nan", "nat", "none"}:
        return pd.NaT
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return pd.to_datetime(text, utc=True, format="mixed", errors="coerce")
    # Some CEV archive rounds give a multi-day window (e.g. 15./16./17. 02.2005).
    # Assign its final possible day to prevent any result in that window from
    # updating ratings for another fixture in the same window.
    window = re.match(r"^(?P<days>\d{1,2}(?:\./\d{1,2})*)\.?\s+(?P<month>\d{1,2})\.(?P<year>\d{4})$", text)
    if window:
        day = max(int(part) for part in re.findall(r"\d{1,2}", window.group("days")))
        return pd.to_datetime(f"{window.group('year')}-{window.group('month')}-{day}", utc=True, errors="coerce")
    return pd.to_datetime(text, utc=True, dayfirst=True, format="mixed", errors="coerce")


def _normalize_table(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
    columns = set(frame.columns)
    common = {"competition_key", "season", "match_date", "home_team", "away_team", "home_sets", "away_sets"}
    if common <= columns:
        out = frame.copy()
        out["sex"] = out["sex"] if "sex" in columns else "unknown"
        out["match_status"] = out.get("match_status", out.get("status", "unknown"))
        out["phase"] = out.get("phase", "unknown")
        out["source"] = out.get("source", path.name)
        out["source_match_id"] = out.get("source_match_id", out.get("match_id", ""))
        out["source_url"] = out.get("source_url", "")
        out["source_sha256"] = out.get("source_sha256", "")
        out["home_advantage_points"] = 50.0
    elif {"season_name", "team_a", "team_b", "sets_a", "sets_b"} <= columns:
        sex = frame["gender"].astype(str).str.upper().replace({"W": "F", "WOMEN": "F"})
        out = pd.DataFrame({
            "competition_key": "cev_cl", "sex": sex,
            "season": frame["season_name"].map(_season_from_cev),
            "match_date": _col(frame, "played_at_local", ""), "home_team": frame["team_a"], "away_team": frame["team_b"],
            "home_sets": frame["sets_a"], "away_sets": frame["sets_b"],
            "match_status": _col(frame, "match_status", "unknown"), "phase": _col(frame, "phase", "unknown"),
            "source": _col(frame, "source", "cev_champions_league"),
            "source_match_id": _col(frame, "match_id", _col(frame, "source_record_id", "")),
            "source_url": _col(frame, "source_url", ""), "source_sha256": _col(frame, "source_sha256", ""),
            # CEV archive team ordering does not prove a home court. Avoid injecting home advantage.
            "home_advantage_points": 0.0,
            "date_precision": _col(frame, "played_at_local", "").map(
                lambda value: "range_end" if re.match(r"^\d{1,2}(?:\./\d{1,2})+\.?\s+\d{1,2}\.\d{4}$", str(value).strip()) else "archive_date"
            ),
        })
    elif {"competition_name", "team_a_name", "team_b_name", "sets_a", "sets_b"} <= columns:
        kept = []
        seasons = []
        for _, row in frame.iterrows():
            mapped = _fivb_lineage(row)
            kept.append(mapped is not None)
            seasons.append(mapped)
        source = frame.loc[kept].copy().reset_index(drop=True)
        mapped_seasons = [season for season, keep in zip(seasons, kept) if keep]
        out = pd.DataFrame({
            "competition_key": "vnl", "sex": [x[0] for x in mapped_seasons], "season": [x[1] for x in mapped_seasons],
            "match_date": _col(source, "scheduled_at_utc", ""), "home_team": source["team_a_name"], "away_team": source["team_b_name"],
            "home_team_id": _col(source, "team_a_id", ""), "away_team_id": _col(source, "team_b_id", ""),
            "home_sets": source["sets_a"], "away_sets": source["sets_b"],
            "match_status": _col(source, "status", "unknown"), "phase": _col(source, "phase", "tournament"),
            "source": _col(source, "source", "fivb_vis"), "source_match_id": _col(source, "match_id", ""),
            "source_url": _col(source, "source_url", ""), "source_sha256": _col(source, "source_sha256", ""),
            "home_advantage_points": 0.0,
            "date_precision": "timestamp_utc",
        })
    else:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)
    for column in CANONICAL_COLUMNS:
        if column not in out:
            out[column] = ""
    out = out[CANONICAL_COLUMNS].copy()
    out["match_date"] = out["match_date"].map(_parse_match_date)
    if {"season_name", "team_a", "team_b"} <= columns:
        start_year = pd.to_numeric(out["season"].astype(str).str.extract(r"^(20\d{2})/")[0], errors="coerce")
        match_year = out["match_date"].dt.year
        in_club_season = (
            (match_year.eq(start_year) & out["match_date"].dt.month.ge(7))
            | (match_year.eq(start_year + 1) & out["match_date"].dt.month.le(6))
        )
        wrong_edition = match_year.notna() & start_year.notna() & ~in_club_season
        out.loc[wrong_edition, "match_date"] = pd.NaT
    for column in ("home_sets", "away_sets", "home_advantage_points"):
        out[column] = pd.to_numeric(out[column], errors="coerce")
    valid_score = (
        out["home_sets"].notna() & out["away_sets"].notna() & out["home_sets"].ne(out["away_sets"])
        & out[["home_sets", "away_sets"]].max(axis=1).eq(3)
        & out[["home_sets", "away_sets"]].min(axis=1).between(0, 2)
    )
    explicit_non_results = out["match_status"].astype(str).str.casefold().isin(
        {"cancelled", "canceled", "abandoned", "not_scheduled", "postponed", "walkover"}
    )
    out.loc[valid_score & ~explicit_non_results, "match_status"] = "completed"
    out.loc[explicit_non_results, ["home_sets", "away_sets"]] = float("nan")
    out["sex"] = out["sex"].astype(str).str.upper().replace({"W": "F", "WOMEN": "F", "MEN": "M"})
    return out


def _paths(inputs: list[str | Path]) -> list[Path]:
    found = []
    for value in inputs:
        path = Path(value)
        if path.is_dir():
            found.extend(p for p in sorted(path.rglob("*.csv")) if p.name in SUPPORTED_FILES)
        elif path.is_file():
            found.append(path)
        else:
            raise FileNotFoundError(path)
    return list(dict.fromkeys(found))


def load_match_sources(inputs: list[str | Path]) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    """Read supported CSVs into one provenance-preserving canonical match table."""
    frames = []
    manifest = []
    for path in _paths(inputs):
        raw = pd.read_csv(path, low_memory=False)
        normalized = _normalize_table(raw, path)
        frames.append(normalized)
        manifest.append({"path": str(path.resolve()), "rows_read": int(len(raw)),
                         "rows_supported": int(len(normalized)), "source_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "columns": list(raw.columns)})
    if not frames:
        raise ValueError("No supported match source CSVs found")
    matches = pd.concat(frames, ignore_index=True)
    source_rows = len(matches)
    rows_without_date = int(matches["match_date"].isna().sum())
    rows_without_teams = int((matches[["home_team", "away_team"]].isna().any(axis=1)).sum())
    matches = matches.dropna(subset=["match_date", "home_team", "away_team"])
    rows_without_season = int(matches["season"].astype(str).str.strip().eq("").sum())
    matches = matches[matches["season"].astype(str).str.strip().ne("")]
    source_ids = matches["source_match_id"].fillna("").astype(str).str.strip()
    fallback = (
        matches["match_date"].astype(str) + "|" + matches[["home_team", "away_team"]].astype(str).apply(
            lambda row: "|".join(sorted(value.casefold().strip() for value in row)), axis=1
        )
    )
    matches["_identity"] = source_ids.where(source_ids.ne(""), fallback)
    before_dedupe = len(matches)
    matches = matches.drop_duplicates(subset=["competition_key", "sex", "_identity"], keep="first").drop(columns="_identity")
    matches = matches.sort_values(["match_date", "competition_key", "sex", "source_match_id"], kind="stable").reset_index(drop=True)
    manifest.append({"normalization_quality": {
        "source_rows_normalized": source_rows,
        "rows_without_timestamp_dropped": rows_without_date,
        "rows_without_team_names_dropped": rows_without_teams,
        "rows_without_season_dropped": rows_without_season,
        "duplicate_rows_dropped": before_dedupe - len(matches),
        "rows_available_to_feature_builder": len(matches),
    }})
    return matches, manifest
