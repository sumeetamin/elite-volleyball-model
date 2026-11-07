"""Reproducible chronological model comparison; select using validation only."""
from pathlib import Path
import hashlib
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from volleyball_model.backtest import _metrics, _clustered_intervals

ROOT = Path(__file__).resolve().parent
FEATURES = ['elo_diff', 'home_advantage_points', 'rest_days_diff', 'form_diff', 'set_margin_diff']

def main():
    path = ROOT / 'artifacts/current_features.csv'
    raw = pd.read_csv(path, low_memory=False)
    data = raw.dropna(subset=FEATURES + ['target_home_win', 'match_date', 'elo_home_win_probability']).copy()
    data['day'] = pd.to_datetime(data.match_date, utc=True).dt.normalize()
    days = sorted(data.day.unique())
    validation_start, test_start = days[int(len(days)*.70)], days[int(len(days)*.85)]
    train = data[data.day < validation_start - pd.Timedelta(days=1)]
    validation = data[(data.day >= validation_start) & (data.day < test_start - pd.Timedelta(days=1))]
    test = data[data.day >= test_start]
    assert train.day.max() < validation.day.min() < test.day.min()
    candidates = {
        'logistic': make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=2000)),
        'gradient_boosting': HistGradientBoostingClassifier(max_iter=150, max_leaf_nodes=7, min_samples_leaf=80, l2_regularization=10, learning_rate=.05, early_stopping=False, random_state=7),
        'random_forest': RandomForestClassifier(n_estimators=300, max_depth=7, min_samples_leaf=60, n_jobs=2, random_state=7),
    }
    results = {}
    for name, model in candidates.items():
        model.fit(train[FEATURES], train.target_home_win.astype(int))
        results[name] = {'validation': _metrics(validation.target_home_win.to_numpy(), model.predict_proba(validation[FEATURES])[:,1])}
    selected = min(results, key=lambda name: results[name]['validation']['log_loss'])
    # Selection is fixed before inspecting any test outcomes. Refit on all eligible earlier dates.
    fit = data[data.day < test_start - pd.Timedelta(days=1)]
    predictions = test[['match_date','competition_key','sex','season','target_home_win']].copy()
    for name, model in candidates.items():
        model.fit(fit[FEATURES], fit.target_home_win.astype(int))
        probability = model.predict_proba(test[FEATURES])[:,1]
        predictions[name] = probability
        results[name]['test'] = _metrics(test.target_home_win.to_numpy(), probability)
        joblib.dump({'model': model, 'features': FEATURES, 'training_end': str(fit.day.max()), 'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}, ROOT / f'artifacts/{name}_current.joblib')
    predictions['elo'] = test.elo_home_win_probability.to_numpy()
    baseline = _metrics(test.target_home_win.to_numpy(), predictions.elo.to_numpy())
    report = {'selected_on_validation_log_loss': selected, 'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'usable_completed_rows': len(data), 'excluded_rows': len(raw)-len(data), 'train_rows': len(train), 'validation_rows': len(validation), 'refit_rows': len(fit), 'test_rows': len(test), 'test_start': str(test.day.min()), 'test_end': str(test.day.max()), 'models': results, 'elo_test': baseline, 'selected_test_intervals': _clustered_intervals(test.target_home_win.to_numpy(), predictions[selected].to_numpy(), test.day.astype(str).to_numpy()), 'limitations': 'Retrospective comparison; historical test dates have been inspected in earlier development. No prospective accuracy or profitability claim. Features update from earlier observed results; model parameters fixed throughout test.'}
    predictions.to_csv(ROOT/'artifacts/current_comparison_predictions.csv', index=False)
    (ROOT/'reports/current_model_comparison.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
