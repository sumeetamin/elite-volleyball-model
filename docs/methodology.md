# Modeling contract

## Inputs and targets

One row represents one match at a declared `prediction_cutoff`. All ratings, EWMAs, lineups, and odds must have been available by that timestamp. Results and post-match box scores are targets or historical observations only. Preserve missingness and distinguish observed statistics from estimates; estimated box scores are excluded by default.

## Features

Begin with set Elo, point-ratio Elo, rest days (cap 7), recent sets in 72 hours, and prior-match EWMAs. Ratios retain numerator/denominator for shrinkage and sample-size controls. Add attack, serve, reception, block, K1/K2, and rotation only when observed and audited. Build each feature sequentially: emit pre-match state, then update after the match. Use gender/competition interactions or separately validated models; do not assume separate models improve accuracy.

## Validation and calibration

Reserve the final chronological tail of distinct match dates before development-fold evaluation and do not use it for feature selection or calibration choices. Use expanding chronological folds within the earlier development period, keeping every same-date match together. Generate stack meta-features from strictly earlier out-of-fold predictions. Fit probability calibration on a later held-out calibration interval, never on training predictions. Evaluate the chosen pipeline once on the final holdout. Report log loss, Brier score, 10-bin equal-width expected calibration error, accuracy, date range and sample size against Elo and market baselines. Baseline and model metrics must use the same final-test rows; report model-minus-baseline differences. The evaluation code adds 95% percentile intervals via bootstrap resampling whole match dates (500 draws; omitted below 10 dates), including paired differences. Treat these intervals as uncertainty summaries, not a guarantee of future performance.

## Volleyball simulator

For Team A, receiving rally win probability is `p_so_a`; serving rally win probability is `1 - p_so_b`. The server retains serve after winning and loses it after losing. Sets end at target (25, fifth set 15) by two. Model first server explicitly or average the two possible starts. Dynamic programming calculates set probabilities and point/set distributions; do not cap deuce recursion with an arbitrary 0.5 fallback. Match score probabilities use a best-of-five absorbing state and distinguish fifth-set probabilities. Validate probability mass sums to one and symmetry at equal team strengths.

## Betting fields

Store decimal odds, provider, bookmaker, market, line, selection, observed timestamp, and quote age. Expected value is `p * decimal_odds - 1` before commission/tax. Do not emit stakes or imply profitability from a backtest alone. Remove bookmaker margin for market-probability comparisons. Record settlement rules.
