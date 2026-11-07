# Full lineages walk-forward evaluation — 2026-11-07

Retrospective evaluation rebuilt from the local dataset snapshot with an explicit as-of cutoff of 2026-11-07. The feature matrix has 21,703 dated rows, 21,594 completed outcomes, and SHA-256 `a5c5e4b00fed1426aa05bdfc87423bb0caf3aba091d29ab9ee5e331dc6b839d3`. The model uses prior-only Elo difference, home advantage, rest, recent form, and prior set-margin form; the baseline is Elo probability on the same test rows.

## Design

- Six expanding chronological development folds; same-day matches stay together and a one-day embargo prevents same-date result leakage.
- Later calibration window, then a distinct-date final tail (15% requested; 2,998 paired results).
- Final test dates: 2024-02-02–2026-11-04 UTC. Future fixture rows after the explicit cutoff were excluded.
- This is retrospective; the final tail was not frozen before model development.

## Final-test metrics

| Metric | Model | Elo | Difference |
|---|---:|---:|---:|
| Accuracy | 0.7178 | 0.7058 | +0.0120 |
| Log loss | 0.5574 | 0.5673 | -0.0100 |
| Brier | 0.1880 | 0.1923 | -0.0043 |
| AUC | 0.7883 | 0.7849 | +0.0034 |
| 10-bin ECE | 0.0303 | 0.0587 | -0.0284 |

Paired date-cluster 95% intervals, model minus Elo: accuracy [-0.0008, +0.0229], log loss [-0.0177, -0.0018], Brier [-0.0070, -0.0013], ECE [-0.0449, -0.0011]. Development-fold metrics also favored the model on these measures.

## Acceptance status

Provisional quality remains **6/10**, below the requested 8/10. The retrospective model beats Elo on the pooled final tail, but there is no timestamp-aligned de-vigged odds benchmark or frozen prospective shadow test; source coverage remains uneven; VNL/season stability and calibration need deeper review. The dataset gate is currently 213/260 eligible seasons meeting 80% outcome coverage.

Feature matrix and predictions are local/ignored artifacts. Reproduction commands from the model repository:

```powershell
$env:PYTHONPATH = 'src'
python -m volleyball_model.cli build-features --input ..\elite-volleyball-dataset\data\silver --as-of-date 2026-11-07 --output artifacts\selected_features_2026-11-07_asof.csv
python -m volleyball_model.cli backtest --input artifacts\selected_features_2026-11-07_asof.csv --date match_date --target target_home_win --features elo_diff,home_advantage_points,rest_days_diff,form_diff,set_margin_diff --baseline elo_home_win_probability --output artifacts\selected_competitions_walk_forward_2026-11-07_asof
```

