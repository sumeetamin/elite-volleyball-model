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

Run `volley-model backtest --input data/gold/ml_feature_matrix.parquet --date match_date --target target_home_win --features elo_diff,rest_days_diff --baseline elo_home_win_probability --output reports/walk_forward`. By default, the final test reserves at least the last 15% of distinct match dates; when three or more season labels exist it holds out at least two complete latest seasons. The report records both requested and realized holdout fractions. The predictions CSV contains only that holdout. Earlier expanding-fold metrics are reported separately for development. Features must be strictly pre-match. The command intentionally fails when there is not enough dated history to form fit, calibration, development, and final test windows.

Build features from the supported source tables with `volley-model build-features --input ..\elite-volleyball-dataset\data\silver --output artifacts\selected_features.csv`. The adapter recognizes CBV, CEV, FIVB VIS, Lega Volley and PlusLiga schemas, preserves source IDs/URLs/hashes, filters FIVB to the World League/Grand Prix/VNL lineage, and writes a source-hash manifest beside the feature CSV. CEV and international rows receive zero home advantage because the archive’s team ordering does not establish a home venue; domestic schedules receive 50 Elo points. All matches on the same date share the same prior state, and results update ratings/form only after that date. Unscored fixtures can support rest features but never update ratings or receive a target. Use `elo_diff,home_advantage_points,rest_days_diff,form_diff` and compare with `elo_home_win_probability`. Mixed-competition evaluation reserves one global chronological date tail so matches from different competition calendars cannot put a later date in model training for an earlier test match. The report segments final metrics by competition, sex and season when samples support them.
