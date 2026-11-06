# Selected competitions walk-forward evaluation — PlusLiga 2011/12 included

Retrospective evaluation of the local source snapshot with a feature cutoff of 2026-11-07. The feature matrix contains 18,696 rows, including the 90 imported PlusLiga 2011/12 regular-season results; 18,596 rows have completed outcomes. Input feature SHA-256: `e43813a01c693490a1da23f793d13b8d89340229579d07c777e46eee90291a13`.

Features are `elo_diff`, `home_advantage_points`, `rest_days_diff`, `form_diff`, and prior-only `set_margin_diff`. The baseline is Elo probability on the same rows. Same-date matches share the same prior state; domestic home advantage is 50 Elo points, and international/neutral rows use zero.

## Evaluation design

- Six chronological development walk-forward folds: 7,166 outcomes from 2014-05-31 through 2024-02-27.
- Final test: latest 15% distinct-date tail, same-date grouped with a one-day embargo; 2,159 paired predictions from 2024-02-28 through 2026-11-05.
- This remains a retrospective test, not a set frozen before feature or model development. The new historical season extends Elo history but is outside this test window.
- Model and dataset suites passed 25/25 and 60/60 respectively on 2026-11-07.

## Final-test metrics

| Metric | Model | Elo baseline | Model minus Elo |
|---|---:|---:|---:|
| Accuracy | 0.7216 | 0.7008 | +0.0208 |
| Log loss | 0.5562 | 0.5729 | -0.0167 |
| Brier score | 0.1872 | 0.1945 | -0.0073 |
| ROC AUC | 0.7904 | 0.7826 | +0.0078 |
| 10-bin ECE | 0.0279 | 0.0658 | -0.0379 |

Date-cluster bootstrap 95% intervals for model-minus-Elo: accuracy [+0.0048, +0.0372], log loss [-0.0281, -0.0053], Brier [-0.0117, -0.0029], and ECE [-0.0531, -0.0094]. Development paired differences also favored the model: log loss -0.0399 (95% interval [-0.0457, -0.0340]); Brier -0.0162 ([-0.0185, -0.0137]).

## Segment checks

Paired segment differences below are model minus Elo; negative log loss/Brier favors the model. These descriptive slices are not separately multiplicity-adjusted.

| Segment | n | Log-loss difference | Brier difference |
|---|---:|---:|---:|
| Brazil Superliga | 637 | -0.0101 | -0.0051 |
| CEV Champions League | 49 | -0.0462 | -0.0246 |
| Italy women's Serie A1 | 366 | -0.0581 | -0.0236 |
| Italy SuperLega | 281 | -0.0215 | -0.0072 |
| PlusLiga | 158 | -0.0197 | -0.0081 |
| VNL (all editions) | 668 | +0.0047 | +0.0008 |
| Domestic 2023/24 | 130 | +0.0359 | +0.0133 |
| Domestic 2024/25 | 751 | -0.0161 | -0.0079 |
| Domestic 2025/26 | 580 | -0.0485 | -0.0187 |
| Domestic 2026/27 | 30 | -0.1171 | -0.0443 |
| VNL 2024 | 208 | -0.0016 | -0.0008 |
| VNL 2025 | 230 | +0.0001 | +0.0012 |
| VNL 2026 | 230 | +0.0149 | +0.0018 |

The VNL aggregate and 2026/27 edition still trail Elo on proper scores, and 2023/24 is a weak domestic segment. The 30-row 2026/27 domestic slice is especially uncertain. Pooled improvement is not proof of stable calibration in every competition.

## Acceptance status

**Provisional rating remains 6/10; the ≥8 target is unmet.** The retrospective model improves over Elo on pooled accuracy, log loss, Brier, AUC and ECE with paired date-cluster intervals favoring it on the reported differences. Remaining evidence gaps: timestamp-aligned de-vigged bookmaker probabilities, a frozen prospective shadow evaluation, stable gains across adequately sized competition/season segments, and closure or verified disposition of historical coverage gaps. No rating uplift is claimed from adding data alone.

## Reproduction

```powershell
$env:PYTHONPATH = 'src'
python -m volleyball_model.cli build-features --input ..\elite-volleyball-dataset\data\silver ..\elite-volleyball-dataset\data\local --as-of-date 2026-11-07 --output artifacts\selected_features_2026-11-07-plusliga-2011-12.csv
python -m volleyball_model.cli backtest --input artifacts\selected_features_2026-11-07-plusliga-2011-12.csv --date match_date --target target_home_win --features elo_diff,home_advantage_points,rest_days_diff,form_diff,set_margin_diff --baseline elo_home_win_probability --output artifacts\selected_competitions_walk_forward_2026-11-07-plusliga-2011-12
```

Local metrics and predictions are `artifacts/selected_competitions_walk_forward_2026-11-07-plusliga-2011-12.metrics.json` and `.predictions.csv`. The feature matrix and manifest are local/ignored artifacts. Recorded runtime: Python 3.14.3, pandas 3.0.2, scikit-learn 1.8.0.
