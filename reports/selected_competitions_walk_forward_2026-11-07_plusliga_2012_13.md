# Selected competitions walk-forward evaluation — PlusLiga 2012/13 included

Retrospective evaluation of the local source snapshot with a feature cutoff of 2026-11-07. The feature matrix contains 18,786 rows, including the 90 imported PlusLiga 2012/13 regular-season results; 18,686 rows have completed outcomes. Input feature SHA-256: `ad7935635d4693436129d7c93c8d92cbc82ef9d61a6b66a488c9e652b3735ce8`.

Features are `elo_diff`, `home_advantage_points`, `rest_days_diff`, `form_diff`, and prior-only `set_margin_diff`. The baseline is Elo probability on the same rows. Same-date matches share the same prior state; domestic home advantage is 50 Elo points, and international/neutral rows use zero.

## Evaluation design

- Five chronological development walk-forward folds: 7,220 outcomes from 2014-02-16 through 2024-02-22.
- Final test: latest 15% distinct-date tail, same-date grouped with a one-day embargo; 2,183 paired predictions from 2024-02-23 through 2026-11-05.
- This remains a retrospective test, not a set frozen before feature or model development. The new historical season extends Elo history but is outside this test window.
- Model and dataset suites passed 25/25 and 61/61 respectively on 2026-11-07.

## Final-test metrics

| Metric | Model | Elo baseline | Model minus Elo |
|---|---:|---:|---:|
| Accuracy | 0.7219 | 0.7000 | +0.0220 |
| Log loss | 0.5564 | 0.5731 | -0.0167 |
| Brier score | 0.1874 | 0.1947 | -0.0073 |
| ROC AUC | 0.7900 | 0.7822 | +0.0078 |
| 10-bin ECE | 0.0283 | 0.0666 | -0.0383 |

Date-cluster bootstrap 95% intervals for model-minus-Elo: accuracy [+0.0045, +0.0387], log loss [-0.0277, -0.0066], Brier [-0.0114, -0.0032], and ECE [-0.0548, -0.0108]. Development paired differences also favored the model: log loss -0.0399 (95% interval [-0.0457, -0.0340]); Brier -0.0162 ([-0.0185, -0.0137]).

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


## Latest refresh after PlusLiga 2012/13 backfill

Feature matrix: 18,786 rows (18,686 completed), SHA-256 d7935635d4693436129d7c93c8d92cbc82ef9d61a6b66a488c9e652b3735ce8. Final test: n=2,183, 2024-02-23–2026-11-05. Model vs Elo: accuracy 0.7219 vs 0.7000; log loss 0.5564 vs 0.5731; Brier 0.1874 vs 0.1947; AUC 0.7900 vs 0.7822; ECE 0.0283 vs 0.0666. Paired 95% date-cluster intervals for model-minus-Elo: accuracy [+0.0045,+0.0387], log loss [-0.0277,-0.0066], Brier [-0.0114,-0.0032], ECE [-0.0548,-0.0108]. This remains retrospective evidence; rating remains 6/10, and no odds baseline or frozen prospective test is available. 


