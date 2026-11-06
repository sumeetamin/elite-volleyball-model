import argparse
from .simulator import match_probabilities
from .backtest import evaluate_walk_forward
import json
import hashlib
import platform
import sklearn
from pathlib import Path
import pandas as pd
from .features import build_match_features


def main() -> None:
    parser = argparse.ArgumentParser(description="Volleyball model utilities")
    sub = parser.add_subparsers(dest="command", required=True)
    sim = sub.add_parser("simulate", help="simulate match probabilities from side-out rates")
    sim.add_argument("--p-so-a", type=float, required=True)
    sim.add_argument("--p-so-b", type=float, required=True)
    features = sub.add_parser("build-features", help="build prior-only Elo, rest, and recent-form features")
    features.add_argument("--input", required=True, help="normalized matches CSV")
    features.add_argument("--output", default="elo_features.csv")
    features.add_argument("--k-factor", type=float, default=20.0)
    features.add_argument("--home-advantage", type=float, default=50.0)
    features.add_argument("--phase-column", default=None, help="optional phase field to filter before feature building")
    features.add_argument("--phase-value", default=None, help="required value when --phase-column is supplied")
    bt = sub.add_parser("backtest", help="evaluate binary match predictions with chronological folds")
    bt.add_argument("--input", required=True, help="CSV or Parquet feature table")
    bt.add_argument("--date", default="match_date")
    bt.add_argument("--target", default="target_team_a_won")
    bt.add_argument("--features", required=True, help="comma-separated pre-match feature columns")
    bt.add_argument("--baseline", default=None, help="optional baseline probability column")
    bt.add_argument("--final-test-fraction", type=float, default=.15,
                    help="chronological tail reserved for the single final evaluation (default: 0.15)")
    bt.add_argument("--output", default="backtest")
    args = parser.parse_args()
    if args.command == "simulate":
        for score, probability in match_probabilities(args.p_so_a, args.p_so_b).items():
            print(f"{score}: {probability:.6f}")
    elif args.command == "build-features":
        matches = pd.read_csv(args.input)
        if bool(args.phase_column) != bool(args.phase_value):
            raise SystemExit("--phase-column and --phase-value must be provided together")
        if args.phase_column:
            if args.phase_column not in matches.columns:
                raise SystemExit(f"Phase column {args.phase_column!r} is not present in the input")
            matches = matches.loc[matches[args.phase_column].eq(args.phase_value)].copy()
        features = build_match_features(matches, args.k_factor, args.home_advantage)
        output = matches.join(features)
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        output.to_csv(target, index=False)
        print(f"Wrote {len(output)} rows with prior-only Elo features to {target}")
    elif args.command == "backtest":
        path=Path(args.input)
        df=pd.read_parquet(path) if path.suffix.lower()==".parquet" else pd.read_csv(path)
        input_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        predictions, summary=evaluate_walk_forward(df,args.date,args.target,
            [c.strip() for c in args.features.split(",") if c.strip()],args.baseline,
            final_test_fraction=args.final_test_fraction)
        summary["run_metadata"] = {
            "input_path": str(path.resolve()), "input_sha256": input_sha256,
            "date_column": args.date, "target_column": args.target,
            "feature_columns": [c.strip() for c in args.features.split(",") if c.strip()],
            "baseline_column": args.baseline, "final_test_fraction": args.final_test_fraction,
            "python_version": platform.python_version(), "pandas_version": pd.__version__,
            "scikit_learn_version": sklearn.__version__,
        }
        out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
        predictions.to_csv(out.with_suffix(".predictions.csv"),index=False)
        out.with_suffix(".metrics.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
        print(json.dumps(summary,indent=2))


if __name__ == "__main__":
    main()
