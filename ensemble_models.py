"""Chronological OOF stacking and probability blends of the existing learners."""
import hashlib
import itertools
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from volleyball_model.backtest import _metrics, _clustered_intervals, _paired_clustered_differences
from compare_models import ROOT, FEATURES

def main():
    path = ROOT/'artifacts/current_features.csv'
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    previous = json.loads((ROOT/'reports/current_model_comparison.json').read_text())
    assert digest == previous['input_sha256'], 'Dataset changed; regenerate base comparison first'
    data = pd.read_csv(path, low_memory=False).dropna(subset=FEATURES+['target_home_win','match_date','elo_home_win_probability']).copy()
    data['day'] = pd.to_datetime(data.match_date, utc=True).dt.normalize()
    days = sorted(data.day.unique())
    vs, ts = days[int(len(days)*.70)], days[int(len(days)*.85)]
    train = data[data.day < vs-pd.Timedelta(days=1)]
    val = data[(data.day >= vs)&(data.day < ts-pd.Timedelta(days=1))]
    test = data[data.day >= ts]
    fit = data[data.day < ts-pd.Timedelta(days=1)]
    names = ['logistic','gradient_boosting','random_forest']
    templates = [clone(joblib.load(ROOT/f'artifacts/{name}_current.joblib')['model']) for name in names]
    td = sorted(train.day.unique())
    boundaries = [int(len(td)*f) for f in (.4,.6,.8,1.)]
    oof, targets, lineage = [], [], []
    for start, end in zip(boundaries[:-1], boundaries[1:]):
        block = train[train.day.isin(td[start:end])]
        earlier = train[train.day < td[start]-pd.Timedelta(days=1)]
        assert earlier.day.max() < block.day.min()
        p = []
        for template in templates:
            model = clone(template).fit(earlier[FEATURES], earlier.target_home_win.astype(int))
            p.append(model.predict_proba(block[FEATURES])[:,1])
        oof.append(np.column_stack(p)); targets.extend(block.target_home_win.astype(int))
        lineage.append({'training_end':str(earlier.day.max()),'prediction_start':str(block.day.min()),'prediction_end':str(block.day.max()),'rows':len(block)})
    # Meta learner sees only predictions made by models trained on earlier dates.
    meta = LogisticRegression(C=1, max_iter=2000).fit(np.vstack(oof), targets)
    vp = []
    for template in templates:
        model = clone(template).fit(train[FEATURES], train.target_home_win.astype(int))
        vp.append(model.predict_proba(val[FEATURES])[:,1])
    vp = np.column_stack(vp)
    grid = [np.array([a,b,10-a-b])/10 for a in range(11) for b in range(11-a)]
    weights = min(grid, key=lambda w: _metrics(val.target_home_win.to_numpy(), vp@w)['log_loss'])
    validation_predictions = {'soft_voting':vp.mean(axis=1),'weighted_blend':vp@weights,'chronological_stacking':meta.predict_proba(vp)[:,1]}
    results = {name:{'validation':_metrics(val.target_home_win.to_numpy(),p)} for name,p in validation_predictions.items()}
    selected = min(results,key=lambda name: results[name]['validation']['log_loss'])
    bases = [clone(t).fit(fit[FEATURES],fit.target_home_win.astype(int)) for t in templates]
    tp = np.column_stack([m.predict_proba(test[FEATURES])[:,1] for m in bases])
    probabilities = {'soft_voting':tp.mean(axis=1),'weighted_blend':tp@weights,'chronological_stacking':meta.predict_proba(tp)[:,1]}
    output = test[['match_date','competition_key','sex','season','target_home_win']].copy()
    for name,p in probabilities.items():
        results[name]['test'] = _metrics(test.target_home_win.to_numpy(),p)
        output[name] = p
        joblib.dump({'base_models':bases,'base_names':names,'features':FEATURES,'method':name,'weights':weights if name=='weighted_blend' else np.ones(3)/3,'meta_model':meta if name=='chronological_stacking' else None,'input_sha256':digest,'training_end':str(fit.day.max())},ROOT/f'artifacts/{name}_current.joblib')
    # Confirm same historical test sample and base probabilities as previous comparison.
    old = pd.read_csv(ROOT/'artifacts/current_comparison_predictions.csv')
    assert len(old)==len(test) and np.array_equal(old.target_home_win.to_numpy(),test.target_home_win.to_numpy())
    assert np.allclose(tp[:,1],old.gradient_boosting.to_numpy())
    y = test.target_home_win.to_numpy(); clusters = test.day.astype(str).to_numpy()
    report = {'selected_on_validation_log_loss':selected,'input_sha256':digest,'test_rows':len(test),'test_start':str(test.day.min()),'test_end':str(test.day.max()),'oof_folds':lineage,'weighted_blend_weights':dict(zip(names,weights.tolist())),'models':results,'selected_accuracy_intervals':_clustered_intervals(y,probabilities[selected],clusters),'selected_minus_gradient_boosting_intervals':_paired_clustered_differences(y,probabilities[selected],tp[:,1],clusters),'gradient_boosting_test':_metrics(y,tp[:,1]),'elo_test':_metrics(y,test.elo_home_win_probability.to_numpy()),'limitations':'Retrospective, repeatedly examined historical test period; requires a new prospective evaluation. Selection uses validation log loss, not test accuracy. Stacking meta learner trained on earlier out-of-fold predictions only.'}
    output.to_csv(ROOT/'artifacts/current_ensemble_predictions.csv',index=False)
    (ROOT/'reports/current_ensemble_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
