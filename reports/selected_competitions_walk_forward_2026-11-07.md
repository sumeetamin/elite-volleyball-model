# Selected competitions walk-forward evaluation — 2026-11-07

This is a retrospective evaluation of the current local source snapshot, built with an explicit as-of cutoff of 2026-11-07. It does not establish complete historical coverage or prospective performance. The model uses `elo_diff`, `home_advantage_points`, `rest_days_diff`, `form_diff`, and prior-only `set_margin_diff`; the baseline is Elo probability on the exact same rows. Same-date matches share the same prior state, domestic home advantage is 50 Elo points, and international/neutral rows use zero.

## Data and design

- Feature matrix: 18,606 rows, of which 18,506 have completed outcomes; input SHA-256 `0503e4866d4228bc35468495605009573d38f2a7ec500d2cc4f592dd69e6c68c`.
- New history: official PlusLiga 2010/11 regular season, 90/90 results. Source extraction details and its limitations are recorded in the dataset repository's `reports/plusliga_m_2010_11_provenance.md`.
- Development: six chronological walk-forward folds, 7,072 evaluated outcomes. Their 95% date-cluster bootstrap intervals for model-minus-Elo are accuracy [+0.0069, +0.0246], log loss [-0.0457, -0.0350], Brier [-0.0185, -0.0140], and 10-bin ECE [-0.0602, -0.0394].
- Final test: latest 15% chronological distinct-date tail, same-date grouped, one-day embargo; 2,137 paired predictions from 2024-03-04 through 2026-11-05. It is retrospective and was not frozen before feature/model development.

## Final-test metrics

| Metric | Model | Elo baseline | Model minus Elo |
|---|---:|---:|---:|
| Accuracy | 0.7234 | 0.7010 | +0.0225 |
| Log loss | 0.5545 | 0.5724 | -0.0178 |
| Brier score | 0.1868 | 0.1944 | -0.0076 |
| ROC AUC | 0.7910 | 0.7832 | +0.0078 |
| 10-bin ECE | 0.0287 | 0.0684 | -0.0397 |

Date-cluster bootstrap 95% intervals for model-minus-Elo: accuracy [+0.0073, +0.0387], log loss [-0.0286, -0.0063], Brier [-0.0117, -0.0033], and ECE [-0.0558, -0.0110].

Competition sample sizes are Brazil Superliga 628, CEV Champions League 49, Italy women's Serie A1 359, Italy SuperLega 275, PlusLiga 158, and VNL 668. The small CEV sample is noisy. The final test spans multiple seasons and tournament editions, but some individual segments remain small and reliability varies; do not infer that every competition is calibrated from the pooled ECE.

Paired segment differences below are model minus Elo; negative log loss/Brier favors the model. These are descriptive and not separately multiplicity-adjusted.

| Segment | n | Log-loss difference | Brier difference |
|---|---:|---:|---:|
| Brazil Superliga | 628 | -0.0115 | -0.0056 |
| CEV Champions League | 49 | -0.0477 | -0.0251 |
| Italy women's Serie A1 | 359 | -0.0573 | -0.0234 |
| Italy SuperLega | 275 | -0.0266 | -0.0083 |
| PlusLiga | 158 | -0.0200 | -0.0078 |
| VNL (all editions) | 668 | +0.0037 | +0.0007 |
| Domestic 2023/24 | 108 | +0.0312 | +0.0132 |
| Domestic 2024/25 | 751 | -0.0167 | -0.0079 |
| Domestic 2025/26 | 580 | -0.0483 | -0.0186 |
| Domestic 2026/27 | 30 | -0.1149 | -0.0438 |
| VNL 2024 | 208 | -0.0028 | -0.0010 |
| VNL 2025 | 230 | -0.0002 | +0.0012 |
| VNL 2026 | 230 | +0.0136 | +0.0017 |

## Acceptance status

**Provisional model rating: 6/10; target ≥8/10 not met.** The model test suite passed 25/25 and the dataset suite passed 59/59 on 2026-11-07. Evidence supports improvement over same-row Elo in this retrospective sample, including date-cluster intervals for proper scores. Still missing: timestamp-aligned de-vigged odds comparison, a frozen prospective shadow evaluation, stronger season/competition stability evidence, and resolution or explicit disposition of uneven historical data coverage. The report is not a claim of independent replication.

## Reproduction

From the model repository, with the dataset repository at the sibling path shown:

```powershell
$env:PYTHONPATH = 'src'
python -m volleyball_model.cli build-features --input ..\elite-volleyball-dataset\data\silver ..\elite-volleyball-dataset\data\local --as-of-date 2026-11-07 --output artifacts\selected_features_2026-11-07.csv
python -m volleyball_model.cli backtest --input artifacts\selected_features_2026-11-07.csv --date match_date --target target_home_win --features elo_diff,home_advantage_points,rest_days_diff,form_diff,set_margin_diff --baseline elo_home_win_probability --output artifacts\selected_competitions_walk_forward_2026-11-07
```

Saved local run outputs are `artifacts/selected_competitions_walk_forward_2026-11-07.metrics.json` and `artifacts/selected_competitions_walk_forward_2026-11-07.predictions.csv`; the input feature matrix and manifest are also retained locally. Python 3.14.3, pandas 3.1.1, and scikit-learn 1.9.1 were recorded by the run. The large source-derived CSV artifacts are ignored by repository policy, so reproduction requires the same local inputs; the SHA-256 above identifies the evaluated feature matrix.
