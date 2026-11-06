# Expanded CEV candidate evaluation (2026-11-06)

This exploratory run uses the local CEV multi-season archive in addition to the selected-competition silver tables. The CEV archive's redistribution rights remain restricted; feature and prediction CSVs stay in ignored local `artifacts/`. The date cutoff is 2026-11-06 UTC. CEV titles naming only a final calendar year are mapped to the club season ending in that year; rows dated outside their named club season are dropped from model input.

The feature builder wrote 14,134 dated rows, including 14,091 valid completed outcomes. The source manifest records 876 normalized rows dropped for missing or conflicting dates, 24 for missing season, and 415 duplicate source rows. Feature matrix SHA-256: `ea9a4c026fcb519c6259968f003a04fe095d85b32b86ffc44d4579d7e3dbdbd4`.

Final chronological test: 1,579 paired predictions from 2024-02-06 through 2026-11-05 UTC, with same-date grouping and the existing one-day embargo. Model accuracy 0.7163, log loss 0.5612, Brier 0.1900, AUC 0.7849, ECE 0.0417. Elo accuracy 0.7004, log loss 0.5671, Brier 0.1924, AUC 0.7793, ECE 0.0420. Model-minus-Elo differences: accuracy +0.0158, log loss -0.0059, Brier -0.0024. Date-cluster 95% intervals for those differences are [-0.0037, 0.0336], [-0.0182, 0.0074], and [-0.0072, 0.0028] respectively. Every interval includes zero.

This run is a sensitivity analysis, not an untouched confirmation: the CEV candidate archive has observed results in all 54 gender-season slices but only the two 2000/01 denominators are verified. It also has unresolved source date and phase issues. Do not promote this run to the 8/10 acceptance gate or claim improved historical completeness from the larger training row count.

Rebuild from the model repository using the local dataset repository:

```powershell
$env:PYTHONPATH = 'src'
python -m volleyball_model.cli build-features --input ..\elite-volleyball-dataset\data\local\cev_champions_league_matches_2000_2026_27.csv ..\elite-volleyball-dataset\data\silver --as-of-date 2026-11-06 --output artifacts\expanded_cev_features_2026-11-06.csv
python -m volleyball_model.cli backtest --input artifacts\expanded_cev_features_2026-11-06.csv --date match_date --target target_home_win --features elo_diff,home_advantage_points,rest_days_diff,form_diff,set_margin_diff --baseline elo_home_win_probability --output artifacts\expanded_cev_walk_forward_2026-11-06
```
