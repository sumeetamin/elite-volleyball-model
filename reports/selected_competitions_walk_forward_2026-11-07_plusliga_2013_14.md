# Selected competitions walk-forward evaluation — PlusLiga 2013/14 included

The as-of 2026-11-07 feature matrix has 18,918 rows (18,818 completed) and includes the official PlusLiga 2013/14 regular-season capture. Feature SHA-256: `921d26eb62e41c9eadc5e63b385d215aae3a18d9545ec1dee81374ccecc9ab6e`.

The model uses prior-only Elo difference, home advantage, rest days, recent form and set margin. Evaluation uses six chronological development folds (7,317 outcomes; 2014-01-08 to 2024-02-17) and a grouped distinct-date final tail (n=2,199; 2024-02-18 to 2026-11-05). This retrospective test was not frozen before development.

| Metric | Model | Elo | Difference |
|---|---:|---:|---:|
| Accuracy | 0.7249 | 0.6999 | +0.0250 |
| Log loss | 0.5570 | 0.5736 | -0.0166 |
| Brier | 0.1876 | 0.1949 | -0.0073 |
| AUC | 0.7901 | 0.7817 | +0.0084 |
| ECE | 0.0297 | 0.0665 | -0.0368 |

Paired 95% date-cluster intervals, model minus Elo: accuracy [+0.0102,+0.0400], log loss [-0.0278,-0.0052], Brier [-0.0116,-0.0028], ECE [-0.0513,-0.0039].

**Rating remains 6/10; the 8/10 target is unmet.** No timestamped odds benchmark or prospective frozen test exists, and some competition segments remain weaker than Elo. The dataset result gate is 141/264 denominator-verified seasons (53.4%); see the dataset repository coverage audit. Bronze captures and generated feature/evaluation files are local/ignored. The new result IDs are explicitly derived because the archive capture did not retain official IDs.
