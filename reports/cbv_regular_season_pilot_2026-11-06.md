# Brazil Superliga regular-season pilot

This is an exploratory retrospective pilot, not the registered final evaluation of a production model. The final two seasons were inspected during model development, so they are not an untouched acceptance holdout.

## Data and split

- Competition: Brazil Superliga regular season, men and women, CBV Data Project.
- Source matrix: 2,113 match-list rows, of which 2,101 have valid completed match results.
- Matrix spans 2017-09-17 through 2025-03-27 and eight season labels.
- Feature rows: 2,101; the two-season holdout contains 495 paired model/Elo predictions. The holdout included 523 completed matches; 28 were omitted because one or more required features were missing.
- Test seasons: 2023/24 and 2024/25; dates 2023-11-07 through 2025-03-27.
- The requested test fraction was 15%; the realized holdout is 25.5% of cleaned feature rows because at least two complete seasons are retained.
- Features: pre-match Elo difference, capped rest-day difference, and prior form difference. Same-day fixtures share a common pre-result state. Evaluator performs later-window probability calibration.
- Baseline: same-row Elo home-win probability.

## Results on paired rows (n=495)

| Metric | Model | Elo baseline | Model minus Elo |
|---|---:|---:|---:|
| Accuracy | 0.7192 | 0.7212 | -0.0020 |
| Log loss | 0.5362 | 0.5430 | -0.0068 |
| Brier score | 0.1816 | 0.1826 | -0.0010 |
| ROC AUC | 0.8163 | 0.8111 | +0.0052 |
| 10-bin ECE | 0.0705 | 0.0762 | -0.0057 |

Paired 95% date-cluster bootstrap intervals for model-minus-Elo include zero: accuracy [-0.0246, 0.0227], log loss [-0.0273, 0.0150], Brier [-0.0085, 0.0065], ECE [-0.0253, 0.0371]. The observed differences are not conclusive evidence of an advantage. Holdout ECE is about 7%, with season-level ECE around 9–10%.

## Interpretation and next gate

This pilot does not qualify the model for an 8/10 score. It covers only one national competition and eight recent seasons, has no timestamp-aligned market baseline, shows weak-ish probability calibration, and does not demonstrate a statistically reliable proper-score gain over Elo. Keep the quality rating withheld until a frozen pipeline succeeds on a genuinely untouched later time period and multiple competitions, with sufficient sample sizes and calibrated probabilities.

The original normalized dataset and generated feature matrix are not committed here. Their source is the local dataset repository's CBV import; the run metadata in the generated metrics JSON records the feature-matrix SHA-256 and software versions. Rebuild features and rerun with:

```powershell
$env:PYTHONPATH = 'src'
python -m volleyball_model.cli build-features --input ..\elite-volleyball-dataset\data\silver\cbv_superliga_matches.csv --phase-column phase --phase-value regular_season --output artifacts\cbv_regular_features.csv
python -m volleyball_model.cli backtest --input artifacts\cbv_regular_features.csv --date match_date --target target_home_win --features elo_diff,rest_days_diff,form_diff --baseline elo_home_win_probability --output artifacts\cbv_walk_forward_two_seasons
```
