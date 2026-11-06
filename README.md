# Elite Volleyball Model

Leakage-aware volleyball match prediction and evaluation. Consumes versioned normalized records from `elite-volleyball-dataset`; this project does not scrape providers or fabricate observations.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
volley-model simulate --p-so-a 0.66 --p-so-b 0.64
```

See `docs/methodology.md`. Historical backtests must use chronological splits and features reconstructed as of each prediction cutoff. Model performance is reported against a simple Elo baseline. Probabilities are calibrated only on a later calibration window.

## Evaluation

Run `volley-model backtest --input data/gold/ml_feature_matrix.parquet --date match_date --target target_team_a_won --features elo_diff,rest_days_diff --baseline elo_probability --output reports/walk_forward`. By default, the last 15% of distinct match dates is held out once as the final test; the predictions CSV contains only that holdout. Earlier expanding-fold metrics are reported separately for development. Features must be strictly pre-match. The command intentionally fails when there is not enough dated history to form fit, calibration, development, and final test windows.

Build Elo, rest, and recent-form features from normalized match results with `volley-model build-features --input matches.csv --phase-column phase --phase-value regular_season --output artifacts/regular_features.csv`. The input CSV needs `competition_key`, `match_date`, `home_team`, `away_team`, `home_sets`, and `away_sets`; `sex` is used to keep division ratings separate when present. Every match on the same date receives features from the same prior state; results update ratings and form only after that date. Unscored fixtures receive Elo/rest features but do not update state or become labeled training rows. Example backtest features: `elo_diff,rest_days_diff,form_diff`; compare against `elo_home_win_probability` on the identical holdout rows. Final test metrics also report segments by competition, sex, and season when those columns exist.
