# Selected competitions walk-forward evaluation

This report is generated from the local, provenance-preserving feature matrix after applying an explicit as-of cutoff of 2026-11-06. It is an evaluation artifact, not a claim of complete historical coverage. The source adapter uses CBV, CEV, FIVB VIS, Lega Volley and PlusLiga tables; bulk source rows whose redistribution rights are unclear remain local.

## Test design

- Features: `elo_diff`, `home_advantage_points`, `rest_days_diff`, `form_diff`, and prior-only `set_margin_diff`.
- Baseline: same-row Elo probability.
- Same-date matches share the same prior state; domestic rows use 50 Elo home-advantage points and CEV/international rows use zero because their source ordering does not establish a home side.
- Walk-forward development folds use a later calibration block. The final test is the latest 15% chronological date tail, with same-date grouping and a one-day embargo.
- Final test: 1,395 paired predictions from 2024-04-01 through 2026-11-04. The realized fraction is 12.82% after filtering to completed outcomes and the as-of cutoff.
- Feature matrix SHA-256: `fe43f4f9ab48a6cd6c7cfd0f4822870e3dead1e86bae7208d1fa6623a3a882b0`.

## Final test metrics

| Metric | Model | Elo baseline | Difference |
|---|---:|---:|---:|
| Accuracy | 0.7254 | 0.7125 | +0.0129 |
| Log loss | 0.5501 | 0.5582 | -0.0081 |
| Brier score | 0.1851 | 0.1884 | -0.0033 |
| ROC AUC | 0.7947 | 0.7901 | +0.0045 |
| 10-bin ECE | 0.0481 | 0.0512 | -0.0031 |

Date-cluster bootstrap 95% intervals for model minus Elo include zero for accuracy [-0.0044, 0.0309], log loss [-0.0196, 0.0032], Brier [-0.0079, 0.0014], and ECE [-0.0285, 0.0251]. The observed improvement is encouraging but not statistically conclusive.

## Acceptance status

The model pipeline now has 17/17 passing tests in the project virtual environment, an explicit source/date cutoff, provenance manifests, chronological calibration, and a multi-competition final test. It still does not qualify for 8/10: the final test is retrospective, the proper-score intervals include zero, there is no timestamp-aligned bookmaker baseline, and historical source coverage is uneven across the 274-row scope ledger. Keep the quality rating provisional at 6/10 until a frozen, multi-period evaluation demonstrates stable proper-score gains and the remaining source gaps are resolved or formally dispositioned.

Reproduce the run with:

```powershell
$env:PYTHONPATH = 'src'
python -m volleyball_model.cli build-features --input ..\elite-volleyball-dataset\data\silver --as-of-date 2026-11-06 --output artifacts\selected_competitions_features.csv
python -m volleyball_model.cli backtest --input artifacts\selected_competitions_features.csv --date match_date --target target_home_win --features elo_diff,home_advantage_points,rest_days_diff,form_diff,set_margin_diff --baseline elo_home_win_probability --output artifacts\selected_competitions_walk_forward_v3
```
