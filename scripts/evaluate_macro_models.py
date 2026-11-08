"""Additional regression metrics for existing transient macro experiments.

Uses cached current-revised observations: never claims vintage-safe validation.
"""
import json
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from backend.intelligence.economic_outlook import monthly_features,FEATURES,research_outlook
from scripts.evaluate_ml import OUT,ROOT,metrics,digest


def main():
    raw=pd.read_csv(ROOT/'data/economy/fred.csv',index_col='date',parse_dates=True)
    as_of='2026-10-31'
    native=research_outlook(raw,as_of)
    native['cache_sha256']=digest(ROOT/'data/economy/fred.csv')
    (OUT/'economic_research.json').write_text(json.dumps(native,indent=2))
    frame=monthly_features(raw,as_of)
    records=[]
    for target,baseline in [('next_inflation','inflation_lag'),('next_unemployment','unemployment_lag')]:
        labeled=frame.dropna(subset=[target]);y=[];p=[];b=[]
        for i in range(max(48,len(labeled)-24),len(labeled)):
            origin=labeled.index[i]
            eligible=labeled.iloc[:i]
            eligible=eligible[eligible.target_month+pd.offsets.MonthEnd(2)<=origin]
            model=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(eligible[FEATURES],eligible[target])
            y.append(float(labeled.iloc[i][target]));p.append(float(model.predict(labeled.iloc[[i]][FEATURES])[0]));b.append(float(labeled.iloc[i][baseline]))
        assert round(metrics(y,p)['MAE'],4)==native['household'][target]['mae_percentage_points']
        for name,values in [('ridge',p),('persistence',b)]:
            records.append({'target':target,'model':name,'unit':'percentage points',**metrics(y,values)})
    pd.DataFrame(records).to_csv(OUT/'macro_regression_metrics.csv',index=False)
    print('Macro regression metrics reproduced native MAEs; current-revised history only.')


if __name__=='__main__':main()
