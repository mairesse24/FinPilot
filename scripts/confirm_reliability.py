"""Additional untouched-seed confirmation after freezing the calibration policy.

Never fits parameters, modifies prior final records, or changes serving policy.
"""
import json
import hashlib
import numpy as np
import pandas as pd
import lightgbm as lgb
from backend.intelligence.intervals import POLICY,positive_bounds
from backend.intelligence.forecasting import forecast_spending
from scripts.reliability_generalization import independent,records,OUT,MODEL_DIR


def main():
    frozen=POLICY.read_bytes();policy=json.loads(frozen)
    boosters=[lgb.Booster(model_file=str(MODEL_DIR/f'{n}.txt')) for n in ('lower','median','upper')]
    rows=[]
    for i,(hist,future) in enumerate(independent(20261003)):
        new=records(hist,future,'confirmation_20261003',boosters)
        for row in new:
            row['lower_after'],row['upper_after']=positive_bounds(row['lower_before'],row['upper_before'],row['serving'],policy['groups'][row['group']]['q'],row['scale'])
        if i==0:
            actual=forecast_spending(hist,30)
            assert all(r['lower']==n['lower_after'] and r['upper']==n['upper_after'] for r,n in zip(actual['daily'],new))
        rows+=new
    frame=pd.DataFrame(rows);frame.to_csv(OUT/'confirmation_predictions.csv',index=False)
    result=[]
    for group,g in frame.groupby('group'):
        for stage in ('before','after'):
            pos=g[g.actual>0]
            result.append({'group':group,'stage':stage,'positive_n':len(pos),
                'positive_coverage':((pos.actual>=pos[f'lower_{stage}'])&(pos.actual<=pos[f'upper_{stage}'])).mean(),
                'positive_width':(pos[f'upper_{stage}']-pos[f'lower_{stage}']).mean()})
    pd.DataFrame(result).to_csv(OUT/'confirmation_coverage.csv',index=False)
    metrics=[{'model':name,'MAE':abs(frame[name]-frame.actual).mean()} for name in ('lightgbm','serving','calendar_average','rolling_30','previous_week')]
    pd.DataFrame(metrics).to_csv(OUT/'confirmation_generalization.csv',index=False)
    assert frozen==POLICY.read_bytes()
    (OUT/'confirmation_manifest.json').write_text(json.dumps({'seed':20261003,'profiles':60,'policy_sha256':hashlib.sha256(frozen).hexdigest(),'production_interval_parity':'PASS','fitting_performed':False},indent=2))
    print(pd.DataFrame(result).to_string(index=False));print(pd.DataFrame(metrics).to_string(index=False))


if __name__=='__main__':main()
