"""Blend three requested models; tune weights on earlier validation only."""
import hashlib
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from compare_models import ROOT, FEATURES
from volleyball_model.backtest import _metrics, _paired_clustered_differences

def main():
    path=ROOT/'artifacts/current_features.csv'
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    names=['gradient_boosting','catboost','lightgbm']
    bundles=[joblib.load(ROOT/f'artifacts/{n}_current.joblib') for n in names]
    assert all(b['input_sha256']==digest for b in bundles)
    data=pd.read_csv(path,low_memory=False).dropna(subset=FEATURES+['target_home_win','match_date','elo_home_win_probability']).copy()
    data['day']=pd.to_datetime(data.match_date,utc=True).dt.normalize()
    days=sorted(data.day.unique()); vs,ts=days[int(len(days)*.70)],days[int(len(days)*.85)]
    train=data[data.day<vs-pd.Timedelta(days=1)]
    val=data[(data.day>=vs)&(data.day<ts-pd.Timedelta(days=1))]
    test=data[data.day>=ts]
    vp=[]
    for b in bundles:
        m=clone(b['model']).fit(train[FEATURES],train.target_home_win.astype(int))
        vp.append(m.predict_proba(val[FEATURES])[:,1])
    vp=np.column_stack(vp)
    grid=[np.array([a,b,20-a-b])/20 for a in range(21) for b in range(21-a)]
    weights=min(grid,key=lambda w:_metrics(val.target_home_win.to_numpy(),vp@w)['log_loss'])
    configs={'equal_blend':np.ones(3)/3,'validation_weighted_blend':weights}
    results={n:{'weights':dict(zip(names,w.tolist())),'validation':_metrics(val.target_home_win.to_numpy(),vp@w)} for n,w in configs.items()}
    selected=min(results,key=lambda n:results[n]['validation']['log_loss'])
    # Saved base models were fitted exclusively before the final test cutoff.
    assert all(pd.Timestamp(b['training_end'])<ts-pd.Timedelta(days=1) for b in bundles)
    tp=np.column_stack([b['model'].predict_proba(test[FEATURES])[:,1] for b in bundles])
    old=pd.read_csv(ROOT/'artifacts/current_comparison_predictions.csv')
    assert len(old)==len(test) and np.allclose(old.gradient_boosting.to_numpy(),tp[:,0])
    output=test[['match_date','competition_key','sex','season','target_home_win']].copy()
    for n,w in configs.items():
        output[n]=tp@w
        results[n]['test']=_metrics(test.target_home_win.to_numpy(),tp@w)
        joblib.dump({'base_models':[b['model'] for b in bundles],'base_names':names,'features':FEATURES,'weights':w,'input_sha256':digest,'training_end':bundles[0]['training_end']},ROOT/f'artifacts/top_three_{n}.joblib')
    report={'selected_on_validation_log_loss':selected,'input_sha256':digest,'test_rows':len(test),'models':results,'previous_gradient_boosting':_metrics(test.target_home_win.to_numpy(),tp[:,0]),'paired_intervals_vs_gradient_boosting':_paired_clustered_differences(test.target_home_win.to_numpy(),output[selected].to_numpy(),tp[:,0],test.day.astype(str).to_numpy()),'limitations':'Exploratory retrospective result: these three model families were chosen after inspecting earlier test results. Although weights use earlier validation only, this is not an untouched test or a prospective performance estimate.'}
    output.to_csv(ROOT/'artifacts/top_three_predictions.csv',index=False)
    (ROOT/'reports/top_three_blend.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
