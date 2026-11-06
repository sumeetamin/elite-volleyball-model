# CEV and Italy women expansion check (2026-11-06)

The local feature build combines expanded CEV and official Italy women regular-season archives with existing silver sources, cutoff 2026-11-06. It contains 17,314 dated rows and 17,215 valid outcomes. Feature CSV SHA-256: `a6a0ea4248319118fe16c1f1fe62c19a4af4a656fcbbd68b85f420f08980ba14`. Raw local league archives remain untracked pending redistribution permission.

The chronological final test has 2,053 matches from 2024-01-16 through 2026-11-05 UTC. Model log loss/Brier: 0.5456/0.1837; Elo: 0.5555/0.1877. Date-cluster 95% intervals for model-minus-Elo log loss and Brier include zero: [-0.0205, 0.0007] and [-0.0080, 0.0004]. This is a sensitivity run, not an untouched confirmation. The model remains below the 8/10 gate.

The dataset audit now verifies 73/274 slices (26.64%) at 10,652/10,704 valid results; this pooled figure applies only to verified slices. Italy women contributes 3,687/3,701 eligible results in 26 seasons. Of those, 3,124 have exact dates; undated results are excluded from the chronological feature build. See the dataset repository's `docs/italy-women-backfill.md` for source and season details.

Rebuild with `build-features --input ..\elite-volleyball-dataset\data\local\cev_champions_league_matches_2000_2026_27.csv ..\elite-volleyball-dataset\data\silver --as-of-date 2026-11-06`, followed by the documented walk-forward backtest command in `reports/expanded_cev_candidate_2026-11-06.md` using the combined artifact paths.
