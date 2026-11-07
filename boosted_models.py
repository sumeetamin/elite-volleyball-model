"""Validation-selected XGBoost, CatBoost and LightGBM comparison."""
import hashlib
import json
import joblib
import numpy as np
import pandas as pd
import xgboost
import catboost
import lightgbm
from sklearn.base import clone
from compare_models import ROOT, FEATURES
from volleyball_model.backtest import _metrics, _clustered_intervals, _paired_clustered_differences

def main():
    path = ROOT/'artifacts/current_features.csv'
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    previous = json.loads((ROOT/'reports/current_model_comparison.json').read_text())
    assert digest == previous['input_sha256']
    data = pd.read_csv(path, low_memory=False).dropna(subset=FEATURES+['target_home_win','match_date','elo_home_win_probability']).copy()
    data['day'] = pd.to_datetime(data.match_date,utc=True).dt.normalize()
    days = sorted(data.day.unique())
    vs,ts = days[int(len(days)*.70)],days[int(len(days)*.85)]
    train = data[data.day < vs-pd.Timedelta(days=1)]
    validation = data[(data.day >= vs)&(data.day < ts-pd.Timedelta(days=1))]
    test = data[data.day >= ts]
    fit = data[data.day < ts-pd.Timedelta(days=1)]
    assert train.day.max()<validation.day.min() and validation.day.max()<test.day.min()
    factories = {
        'xgboost': lambda d:xgboost.XGBClassifier(n_estimators=300,max_depth=d,learning_rate=.03,min_child_weight=30,reg_lambda=10,subsample=.9,colsample_bytree=1,tree_method='hist',eval_metric='logloss',n_jobs=2,random_state=7),
        'catboost': lambda d:catboost.CatBoostClassifier(iterations=300,depth=d,learning_rate=.03,l2_leaf_reg=10,loss_function='Logloss',thread_count=2,random_seed=7,verbose=False,allow_writing_files=False),
        'lightgbm': lambda d:lightgbm.LGBMClassifier(n_estimators=300,max_depth=d,num_leaves=2**d,min_child_samples=80,learning_rate=.03,reg_lambda=10,n_jobs=2,random_state=7,verbosity=-1),
    }
    results, selected_models = {}, {}
    for name,factory in factories.items():
        trials=[]
        for depth in (2,4,6):
            model=factory(depth)
            model.fit(train[FEATURES],train.target_home_win.astype(int))
            trials.append({'depth':depth,'metrics':_metrics(validation.target_home_win.to_numpy(),model.predict_proba(validation[FEATURES])[:,1])})
        best=min(trials,key=lambda t:t['metrics']['log_loss'])
        results[name]={'validation_trials':trials,'selected_depth':best['depth'],'validation':best['metrics']}
        selected_models[name]=factory(best['depth'])
        print(f'{name}: selected depth {best["depth"]}, validation log loss {best["metrics"]["log_loss"]:.5f}',flush=True)
    selected=min(results,key=lambda n:results[n]['validation']['log_loss'])
    predictions=test[['match_date','competition_key','sex','season','target_home_win']].copy()
    for name,model in selected_models.items():
        model.fit(fit[FEATURES],fit.target_home_win.astype(int))
        predictions[name]=model.predict_proba(test[FEATURES])[:,1]
        results[name]['test']=_metrics(test.target_home_win.to_numpy(),predictions[name].to_numpy())
        joblib.dump({'model':model,'features':FEATURES,'training_end':str(fit.day.max()),'input_sha256':digest},ROOT/f'artifacts/{name}_current.joblib')
    old=pd.read_csv(ROOT/'artifacts/current_comparison_predictions.csv')
    for col in ('match_date','competition_key','sex','season','target_home_win'):
        assert old[col].reset_index(drop=True).equals(predictions[col].reset_index(drop=True)),f'Test alignment differs: {col}'
    y=test.target_home_win.to_numpy(); clusters=test.day.astype(str).to_numpy()
    report={'selected_on_validation_log_loss':selected,'input_sha256':digest,'features':FEATURES,'train_rows':len(train),'validation_rows':len(validation),'refit_rows':len(fit),'test_rows':len(test),'test_start':str(test.day.min()),'test_end':str(test.day.max()),'versions':{m.__name__:m.__version__ for m in (xgboost,catboost,lightgbm)},'models':results,'previous_gradient_boosting':previous['models']['gradient_boosting']['test'],'elo':previous['elo_test'],'selected_intervals':_clustered_intervals(y,predictions[selected].to_numpy(),clusters),'selected_minus_previous_gradient_boosting_intervals':_paired_clustered_differences(y,predictions[selected].to_numpy(),old.gradient_boosting.to_numpy(),clusters),'limitations':'Retrospective test period already examined in previous experiments. Depth and family selection use earlier validation log loss only. No prospective performance or profitability claim.'}
    predictions.to_csv(ROOT/'artifacts/current_boosted_predictions.csv',index=False)
    (ROOT/'reports/current_boosted_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
