# Selected competitions walk-forward evaluation

This report is generated from the local, provenance-preserving feature matrix after applying an explicit as-of cutoff of 2026-11-06. It is an evaluation artifact, not a claim of complete historical coverage. The source adapter uses CBV, CEV, FIVB VIS, Lega Volley and PlusLiga tables; bulk source rows whose redistribution rights are unclear remain local.

## Test design

- Features: `elo_diff`, `home_advantage_points`, `rest_days_diff`, `form_diff`, and prior-only `set_margin_diff`.
- Baseline: same-row Elo probability.
- Same-date matches share the same prior state; domestic rows use 50 Elo home-advantage points and CEV/international rows use zero because their source ordering does not establish a home side.
- Walk-forward development folds use a later calibration block. The final test is the latest 15% chronological date tail, with same-date grouping and a one-day embargo.
- Final test: 2,044 paired predictions from 2024-04-05 through 2026-11-05. The realized fraction is 12.62% after filtering to completed outcomes and the as-of cutoff.
- The source set includes PlusLiga 2001/02, 2002/03, and 2003/04 (90 dated regular-season results each) and CBV Superliga 2025/26 (132/132 men's and 131/132 women's results), extending team rating histories. Feature matrix SHA-256: `8b8beac600dfe9b1b3f65d2a0e15cfb6c545626b2b2f5062eb5b955942e962b0`.

## Final test metrics

| Metric | Model | Elo baseline | Difference |
|---|---:|---:|---:|
| Accuracy | 0.7265 | 0.7006 | +0.0259 |
| Log loss | 0.5515 | 0.5723 | -0.0208 |
| Brier score | 0.1856 | 0.1943 | -0.0087 |
| ROC AUC | 0.7932 | 0.7845 | +0.0087 |
| 10-bin ECE | 0.0266 | 0.0720 | -0.0454 |

Date-cluster bootstrap 95% intervals for model minus Elo: accuracy [+0.0117, +0.0431], log loss [-0.0324, -0.0102], Brier [-0.0134, -0.0047], and ECE [-0.0562, -0.0150]. This expanded retrospective run shows gains against Elo across the reported metrics; it is a sensitivity update after adding historical data, not an untouched confirmation set.

## Acceptance status

The model pipeline has 25 passing tests, an explicit source/date cutoff, provenance manifests, chronological calibration, and a multi-competition final test. The deuce simulator now models post-rally serving-state transitions with an exact two-state Markov solution. This does not yet qualify for 8/10: the evaluation is retrospective and no timestamp-aligned bookmaker baseline or prospective shadow test is available; historical source coverage is also uneven across the 274-row scope ledger. Keep the quality rating provisional at 6/10 until a frozen, multi-period evaluation demonstrates stable gains and the remaining source gaps are resolved or formally dispositioned.

Reproduce the run with:

```powershell
$env:PYTHONPATH = 'src'
python -m volleyball_model.cli build-features --input ..\elite-volleyball-dataset\data\silver ..\elite-volleyball-dataset\data\local --as-of-date 2026-11-06 --output artifacts\selected_features_2026-11-06.csv
python -m volleyball_model.cli backtest --input artifacts\selected_features_2026-11-06.csv --date match_date --target target_home_win --features elo_diff,home_advantage_points,rest_days_diff,form_diff,set_margin_diff --baseline elo_home_win_probability --output artifacts\selected_2003_cbv_walk_forward_2026-11-06
```
