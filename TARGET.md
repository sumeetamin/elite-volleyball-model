# Model acceptance target

Deliver reproducible pre-match probabilities with an evidence-based quality rating of at least **8/10**. A rating is withheld until a leakage audit and chronological out-of-sample backtest have run on documented match history.

## Required evaluation

- Reconstruct every feature as of its prediction cutoff; no post-match statistics or future results.
- Chronological walk-forward splits, same-date grouping, documented embargo, separate later calibration interval, and untouched test predictions.
- Compare with simple Elo on the same test rows; compare with de-vigged market probabilities only when timestamped odds are available.
- Report sample size/date span, log loss, Brier score, accuracy, calibration error, confidence intervals, and competition/season segments with adequate samples.
- Publish data/version hashes, configuration, predictions, and metric outputs so the run can be reproduced.

## 10-point rating rubric

| Area | Points | Full-credit evidence |
| --- | ---: | --- |
| Leakage control and point-in-time features | 2 | Auditable cutoffs; automated safeguards; no known leakage |
| Chronological evaluation design | 2 | Multiple seasons, same-date grouped, embargo and untouched final test |
| Baseline comparison | 2 | Paired Elo comparison; proper-score improvement with uncertainty |
| Calibration | 2 | Later-window calibration; Brier/log-loss/ECE and reliability analysis |
| Robustness | 1 | Stable performance across seasons and major segments, with sample sizes |
| Reproducibility | 1 | Pinned environment, commands, data/config hashes and saved OOS outputs |

An **8/10** requires at least 8 earned points and no failure in leakage control or evaluation design. A high accuracy number alone is insufficient. The current provisional score is **6/10**, not the acceptance target. The refreshed as-of 2026-11-07 feature matrix has 18,786 rows (18,686 completed) and includes the reconciled PlusLiga 2010/11, 2011/12, and 2012/13 seasons. The latest retrospective final test has 2,183 paired predictions through 2026-11-05 UTC: log loss/Brier 0.5564/0.1874 versus Elo's 0.5731/0.1947. Date-cluster 95% intervals favor the model for both proper scores, but there is no timestamp-aligned odds baseline; VNL and some season segments still trail Elo; historical source coverage is uneven; and stability across frozen prospective periods is not demonstrated. Details: `reports/selected_competitions_walk_forward_2026-11-07_plusliga_2012_13.md`.


