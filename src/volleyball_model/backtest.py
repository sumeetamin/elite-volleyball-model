"""Leakage-aware expanding-window evaluation for precomputed match features."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def _season_sort_key(value: str) -> tuple[int, int, str]:
    """Sort season labels chronologically by their first embedded four-digit year.

    This supports both year-first labels (``2024/25``) and competition-prefixed
    labels (``World League 2006`` or ``VNL 2026``). Labels without a year sort
    before dated seasons; they remain deterministic through the lexical tie-break.
    """
    match = re.search(r"(?:19|20)\d{2}", value)
    if match is None:
        return (0, 0, value.casefold())
    return (1, int(match.group()), value.casefold())


def expanding_date_splits(dates: pd.Series, min_train_fraction: float = .5,
                          test_fraction: float = .1, embargo_days: int = 1):
    """Yield expanding train/test indices with all same-day games kept together."""
    d = pd.to_datetime(dates, utc=True).dt.normalize()
    unique = np.array(sorted(d.dropna().unique()))
    if len(unique) < 5:
        raise ValueError("Need at least five distinct match dates for chronological evaluation")
    if not 0 < min_train_fraction < 1 or not 0 < test_fraction < 1 or embargo_days < 0:
        raise ValueError("fractions must be in (0,1) and embargo_days cannot be negative")
    n = len(unique)
    train_end = max(2, int(n * min_train_fraction))
    block = max(1, int(n * test_fraction))
    while train_end < n:
        test_start = train_end
        test_end = min(n, test_start + block)
        cutoff = unique[test_start] - np.timedelta64(embargo_days, "D")
        train_mask = d.to_numpy() < cutoff
        test_dates = unique[test_start:test_end]
        test_mask = d.isin(test_dates).to_numpy()
        if train_mask.any() and test_mask.any():
            yield np.flatnonzero(train_mask), np.flatnonzero(test_mask)
        train_end = test_end


def _metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    result = {"n": int(len(y)), "accuracy": float(accuracy_score(y, p >= .5)),
              "log_loss": float(log_loss(y, p)), "brier": float(brier_score_loss(y, p))}
    result["roc_auc"] = float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else float("nan")
    edges = np.linspace(0.0, 1.0, 11)
    ece = 0.0
    for i, (lo, hi) in enumerate(zip(edges[:-1], edges[1:])):
        in_bin = (p >= lo) & ((p < hi) if i < 9 else (p <= hi))
        if in_bin.any():
            ece += float(in_bin.mean()) * abs(float(y[in_bin].mean()) - float(p[in_bin].mean()))
    result["ece_10_equal_width"] = ece
    return result


def _clustered_intervals(y: np.ndarray, p: np.ndarray, clusters: np.ndarray,
                         n_bootstrap: int = 500, seed: int = 7) -> dict[str, list[float]]:
    """Percentile intervals resampling whole match dates to retain within-day dependence."""
    unique = np.unique(clusters)
    if len(unique) < 10:
        return {}
    rng = np.random.default_rng(seed)
    by_cluster = {key: np.flatnonzero(clusters == key) for key in unique}
    samples: dict[str, list[float]] = {key: [] for key in ("accuracy", "log_loss", "brier", "ece_10_equal_width")}
    for _ in range(n_bootstrap):
        chosen = rng.choice(unique, size=len(unique), replace=True)
        ix = np.concatenate([by_cluster[key] for key in chosen])
        m = _metrics(y[ix], p[ix])
        for key in samples:
            samples[key].append(m[key])
    return {key: [float(np.quantile(values, .025)), float(np.quantile(values, .975))]
            for key, values in samples.items()}


def _paired_clustered_differences(y: np.ndarray, model_p: np.ndarray, baseline_p: np.ndarray,
                                 clusters: np.ndarray, n_bootstrap: int = 500,
                                 seed: int = 11) -> dict[str, list[float]]:
    """95% intervals for model-minus-baseline metrics, resampling whole match dates."""
    unique = np.unique(clusters)
    if len(unique) < 10:
        return {}
    rng = np.random.default_rng(seed)
    by_cluster = {key: np.flatnonzero(clusters == key) for key in unique}
    keys = ("accuracy_diff", "log_loss_diff", "brier_diff", "ece_10_equal_width_diff")
    samples: dict[str, list[float]] = {key: [] for key in keys}
    for _ in range(n_bootstrap):
        chosen = rng.choice(unique, size=len(unique), replace=True)
        ix = np.concatenate([by_cluster[key] for key in chosen])
        m, b = _metrics(y[ix], model_p[ix]), _metrics(y[ix], baseline_p[ix])
        for key, metric in zip(keys, ("accuracy", "log_loss", "brier", "ece_10_equal_width")):
            samples[key].append(m[metric] - b[metric])
    return {key: [float(np.quantile(values, .025)), float(np.quantile(values, .975))]
            for key, values in samples.items()}


def evaluate_walk_forward(df: pd.DataFrame, date_col: str, target_col: str,
                          feature_cols: list[str], baseline_col: str | None = None,
                          calibration_fraction: float = .15,
                          final_test_fraction: float = .15) -> tuple[pd.DataFrame, dict]:
    """Tune with expanding folds, then evaluate once on a later untouched test tail.

    Feature columns must already be reconstructed using information available before
    each match. This routine rejects rows with missing date/target/features. The
    returned prediction file contains only the final holdout; development-fold metrics
    are reported separately and must not be used as the final performance estimate.
    """
    required = [date_col, target_col, *feature_cols]
    if baseline_col and baseline_col not in df.columns:
        raise ValueError(f"Baseline column {baseline_col!r} is not present in the input")
    data = df.dropna(subset=required).copy().reset_index(drop=True)
    data[date_col] = pd.to_datetime(data[date_col], utc=True)
    y = data[target_col].astype(int).to_numpy()
    if set(np.unique(y)) - {0, 1}:
        raise ValueError("Target must be binary 0/1")
    if not 0 < final_test_fraction < .5:
        raise ValueError("final_test_fraction must be in (0, .5)")
    all_dates = data[date_col].dt.normalize()
    unique_dates = np.array(sorted(all_dates.dropna().unique()))
    season_order = []
    if "season" in data.columns and data["season"].notna().all():
        season_order = sorted(data["season"].astype(str).unique(), key=_season_sort_key)
    multiple_competitions = "competition_key" in data and data["competition_key"].nunique() > 1
    if len(season_order) >= 3 and not multiple_competitions:
        holdout_season_count = max(2, int(np.ceil(len(season_order) * final_test_fraction)))
        final_seasons = season_order[-holdout_season_count:]
        final_mask = data["season"].astype(str).isin(final_seasons).to_numpy()
        split_method = "whole_seasons"
    else:
        holdout_days = max(1, int(np.ceil(len(unique_dates) * final_test_fraction)))
        final_start = unique_dates[-holdout_days]
        final_mask = (all_dates >= final_start).to_numpy()
        final_seasons = []
        split_method = "distinct_date_tail"
    development_mask = ~final_mask
    final_test = data.loc[final_mask].copy().reset_index(drop=True)
    final_y = final_test[target_col].astype(int).to_numpy()
    data = data.loc[development_mask].copy().reset_index(drop=True)
    y = data[target_col].astype(int).to_numpy()
    predictions = []
    for fold, (train_idx, test_idx) in enumerate(expanding_date_splits(data[date_col]), 1):
        train = data.iloc[train_idx]
        dates = train[date_col].dt.normalize().drop_duplicates().sort_values().to_numpy()
        cal_n = max(1, int(len(dates) * calibration_fraction))
        cal_start = dates[-cal_n]
        fit_idx = train_idx[train[date_col].dt.normalize().to_numpy() < cal_start]
        cal_idx = train_idx[train[date_col].dt.normalize().to_numpy() >= cal_start]
        if len(fit_idx) < 20 or len(cal_idx) < 5 or len(np.unique(y[fit_idx])) < 2 or len(np.unique(y[cal_idx])) < 2:
            continue
        model = make_pipeline(StandardScaler(), LogisticRegression(C=.5, max_iter=2000))
        model.fit(data.iloc[fit_idx][feature_cols], y[fit_idx])
        cal_p = model.predict_proba(data.iloc[cal_idx][feature_cols])[:, 1]
        # Fit Platt scaling only on the chronologically later calibration block.
        cal_logits = np.log(np.clip(cal_p, 1e-6, 1-1e-6) / np.clip(1-cal_p, 1e-6, 1))[:, None]
        calibrator = LogisticRegression(C=1e6, max_iter=1000).fit(cal_logits, y[cal_idx])
        test_p = model.predict_proba(data.iloc[test_idx][feature_cols])[:, 1]
        test_logits = np.log(np.clip(test_p, 1e-6, 1-1e-6) / np.clip(1-test_p, 1e-6, 1))[:, None]
        p = calibrator.predict_proba(test_logits)[:, 1]
        for ix, prob in zip(test_idx, p):
            predictions.append({"row_index": int(ix), "fold": fold,
                "match_date": data.iloc[ix][date_col].isoformat(), "target": int(y[ix]),
                "probability": float(prob),
                "baseline_probability": float(data.iloc[ix][baseline_col]) if baseline_col else np.nan})
    development_pred = pd.DataFrame(predictions)
    if development_pred.empty:
        raise ValueError("No valid folds; provide more dates and both classes in fit/calibration windows")
    development_summary = {"model": _metrics(development_pred.target.to_numpy(), development_pred.probability.to_numpy()),
               "evaluated_rows": len(development_pred), "first_test_date": development_pred.match_date.min(),
               "last_test_date": development_pred.match_date.max(), "folds": int(development_pred.fold.nunique()),
               "interval_method": "95% percentile bootstrap by match date (500 draws); omitted below 10 dates"}
    development_summary["model_intervals_95"] = _clustered_intervals(
        development_pred.target.to_numpy(), development_pred.probability.to_numpy(),
        pd.to_datetime(development_pred.match_date, utc=True).dt.normalize().astype(str).to_numpy())
    if "baseline_probability" in development_pred:
        baseline_values = development_pred.baseline_probability.to_numpy(dtype=float)
        paired = np.isfinite(baseline_values)
        if paired.any():
            pair_y = development_pred.loc[paired, "target"].to_numpy()
            pair_model = development_pred.loc[paired, "probability"].to_numpy()
            pair_baseline = baseline_values[paired]
            development_summary["paired_rows"] = int(paired.sum())
            development_summary["model_on_baseline_rows"] = _metrics(pair_y, pair_model)
            development_summary["baseline"] = _metrics(pair_y, pair_baseline)
            development_summary["paired_model_minus_baseline"] = {
                "accuracy_diff": development_summary["model_on_baseline_rows"]["accuracy"] - development_summary["baseline"]["accuracy"],
                "log_loss_diff": development_summary["model_on_baseline_rows"]["log_loss"] - development_summary["baseline"]["log_loss"],
                "brier_diff": development_summary["model_on_baseline_rows"]["brier"] - development_summary["baseline"]["brier"],
                "ece_10_equal_width_diff": development_summary["model_on_baseline_rows"]["ece_10_equal_width"] - development_summary["baseline"]["ece_10_equal_width"],
            }
            dev_dates = pd.to_datetime(development_pred.loc[paired, "match_date"], utc=True).dt.normalize().astype(str).to_numpy()
            development_summary["paired_difference_intervals_95"] = _paired_clustered_differences(
                pair_y, pair_model, pair_baseline, dev_dates)

    development_dates = data[date_col].dt.normalize().drop_duplicates().sort_values().to_numpy()
    cal_n = max(1, int(len(development_dates) * calibration_fraction))
    cal_start = development_dates[-cal_n]
    fit_mask = (data[date_col].dt.normalize() < cal_start).to_numpy()
    cal_mask = ~fit_mask
    fit_y = y[fit_mask]
    cal_y = y[cal_mask]
    if len(fit_y) < 20 or len(cal_y) < 5 or len(np.unique(fit_y)) < 2 or len(np.unique(cal_y)) < 2:
        raise ValueError("Final holdout requires at least 20 fit rows and 5 later calibration rows with both classes")
    final_model = make_pipeline(StandardScaler(), LogisticRegression(C=.5, max_iter=2000))
    final_model.fit(data.loc[fit_mask, feature_cols], fit_y)
    cal_p = final_model.predict_proba(data.loc[cal_mask, feature_cols])[:, 1]
    cal_logits = np.log(np.clip(cal_p, 1e-6, 1-1e-6) / np.clip(1-cal_p, 1e-6, 1))[:, None]
    calibrator = LogisticRegression(C=1e6, max_iter=1000).fit(cal_logits, cal_y)
    final_p_raw = final_model.predict_proba(final_test[feature_cols])[:, 1]
    final_logits = np.log(np.clip(final_p_raw, 1e-6, 1-1e-6) / np.clip(1-final_p_raw, 1e-6, 1))[:, None]
    final_p = calibrator.predict_proba(final_logits)[:, 1]
    final_dates = pd.to_datetime(final_test[date_col], utc=True)
    pred = pd.DataFrame({
        "row_index": np.flatnonzero(final_mask), "fold": "final_test",
        "match_date": final_dates.map(lambda value: value.isoformat()),
        "target": final_y, "probability": final_p,
    })
    segment_cols = [column for column in ("competition_key", "sex", "season") if column in final_test.columns]
    for column in segment_cols:
        pred[column] = final_test[column].to_numpy()
    if baseline_col:
        pred["baseline_probability"] = pd.to_numeric(final_test[baseline_col], errors="coerce").to_numpy()
    summary = {"model": _metrics(final_y, final_p), "evaluated_rows": len(pred),
               "first_test_date": pred.match_date.min(), "last_test_date": pred.match_date.max(),
               # Keep both requested and realized fractions explicit. When whole
               # seasons are held out, rounding up to two seasons can make the
               # actual holdout much larger than the requested date fraction.
               "final_test_fraction": final_test_fraction,
               "realized_final_test_fraction": float(final_mask.mean()),
               "final_test_split_method": split_method,
               "final_test_seasons": final_seasons,
               "development_walk_forward": development_summary}
    summary["model_intervals_95"] = _clustered_intervals(
        final_y, final_p, final_dates.dt.normalize().astype(str).to_numpy())
    summary["segment_metrics"] = {}
    for column in segment_cols:
        segments = {}
        for value, indices in final_test.groupby(column, dropna=False, sort=True).groups.items():
            positions = np.asarray(list(indices), dtype=int)
            label = str(value) if pd.notna(value) else "unknown"
            segments[label] = {"n": int(len(positions)),
                               "metrics": _metrics(final_y[positions], final_p[positions]) if len(positions) >= 20 else None}
        summary["segment_metrics"][column] = segments
    if baseline_col:
        baseline_values = pred.baseline_probability.to_numpy(dtype=float)
        ok = np.isfinite(baseline_values)
        if ok.any():
            y_pair = pred.loc[ok, "target"].to_numpy()
            model_pair = pred.loc[ok, "probability"].to_numpy()
            baseline_pair = pred.loc[ok, "baseline_probability"].to_numpy()
            if np.any((baseline_pair < 0) | (baseline_pair > 1)):
                raise ValueError("Baseline probabilities must be within [0,1]")
            model_metrics = _metrics(y_pair, model_pair)
            baseline_metrics = _metrics(y_pair, baseline_pair)
            summary["paired_rows"] = int(ok.sum())
            summary["model_on_baseline_rows"] = model_metrics
            summary["baseline"] = baseline_metrics
            summary["paired_model_minus_baseline"] = {
                "accuracy_diff": model_metrics["accuracy"] - baseline_metrics["accuracy"],
                "log_loss_diff": model_metrics["log_loss"] - baseline_metrics["log_loss"],
                "brier_diff": model_metrics["brier"] - baseline_metrics["brier"],
                "ece_10_equal_width_diff": model_metrics["ece_10_equal_width"] - baseline_metrics["ece_10_equal_width"]}
            paired_dates = pd.to_datetime(pred.loc[ok, "match_date"], utc=True).dt.normalize().astype(str).to_numpy()
            summary["paired_difference_intervals_95"] = _paired_clustered_differences(
                y_pair, model_pair, baseline_pair, paired_dates)
    return pred, summary
