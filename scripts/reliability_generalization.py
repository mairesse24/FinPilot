"""Disjoint synthetic calibration/test cohorts and positive-spending calibration.

The independent generator deliberately avoids PNC's fixed posting-day formula.
The PNC final dates, data and trained point models are never modified.
"""
import json
import numpy as np
import pandas as pd
import lightgbm as lgb
from backend.intelligence.data import ROOT,load_daily
from backend.intelligence.forecasting import forecast_spending
from backend.intelligence.intervals import context,positive_bounds,POLICY
from scripts.evaluate_ml import MODEL_DIR,recursive_fast,digest

OUT=ROOT/'reports/reliability'


def independent(seed,n=60):
    rng=np.random.default_rng(seed)
    dates=pd.date_range('2025-11-01',periods=210)
    for i in range(n):
        probability=rng.uniform(.10,.28) if i<n//2 else rng.uniform(.4,.85)
        typical=rng.uniform(15,140)
        # Independent irregular purchase occurrence, weekend effects, heavy tails,
        # heterogeneous scales, and a modest pre-generated drift; not PNC dates.
        p=np.minimum(.95,probability*(1+.2*(dates.day_of_week>=5)))
        spending=np.where(rng.random(210)<p,rng.lognormal(np.log(typical),.65,210),0.)
        spending*=np.linspace(1,rng.uniform(.85,1.2),210)
        frame=pd.DataFrame({'customer_id':f'NEW-{seed}-{i:03}','date':dates,'spending':spending.round(2)})
        yield frame.iloc[:180].copy(),frame.iloc[180:].copy()


def records(hist,future,cohort,boosters):
    native=forecast_spending(hist,30,use_calibration=False)
    values=np.array([[r['spending'],r['lower'],r['upper']] for r in native['daily']])
    group,scale=context(hist.tail(125))
    candidates={'serving':values[:,0]}
    for name in ('lightgbm','calendar_average','rolling_30','previous_week'):
        candidates[name]=recursive_fast(hist.tail(125),future.date,boosters,name)[:,0]
    return [{'customer_id':hist.customer_id.iloc[0],'cohort':cohort,'group':group,'step':i+1,
             'actual':float(y),'lower_before':values[i,1],'upper_before':values[i,2],'scale':scale,
             'serving_method':native['model'],**{name:float(p[i]) for name,p in candidates.items()}}
            for i,y in enumerate(future.spending)]


def bootstrap(values):
    x=np.asarray(values,float);rng=np.random.default_rng(42)
    draws=np.mean(rng.choice(x,size=(2000,len(x)),replace=True),axis=1)
    return [float(v) for v in np.quantile(draws,[.025,.975])]


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    boosters=[lgb.Booster(model_file=str(MODEL_DIR/f'{n}.txt')) for n in ('lower','median','upper')]
    calibration=[]
    # Held-out customers and validation dates only; no original final test labels.
    daily=load_daily();held=['C025','C026','C027','C028','C029','C030']
    for cid in held:
        g=daily[daily.customer_id==cid]
        for origin in pd.to_datetime(['2026-04-03','2026-05-03','2026-06-02']):
            calibration+=records(g[g.date<=origin].tail(125),g[g.date>origin].head(30),'calibration_pnc',boosters)
    for hist,future in independent(20261001):
        calibration+=records(hist,future,'calibration_independent',boosters)
    cal=pd.DataFrame(calibration)
    params={}
    for group,g in cal[cal.actual>0].groupby('group'):
        residual=np.maximum(g.lower_before-g.actual,g.actual-g.upper_before)/g.scale
        # A fixed 80% empirical positive-outcome quantile; no final-set adjustment.
        q=max(0.,float(np.quantile(residual,.8,method='higher')))
        params[group]={'q':q,'positive_rows':len(g),'profiles':g.customer_id.nunique()}
    policy={'nominal_positive_coverage':.8,'overall_nominal_coverage':None,'groups':params,
            'model_sha256':{n:digest(MODEL_DIR/f'{n}.txt') for n in ('lower','median','upper')},
            'calibration_seeds':[20261001],'final_seed':20261002,
            'limitations':'Empirical positive-spending residual calibration; temporally dependent rows. No exchangeability or real-world coverage guarantee. Sparse mass at zero prevents overall exact 80% when zero and >=80% positives are both covered.'}
    # Freeze policy BEFORE constructing/evaluating final independent outcomes.
    POLICY.write_text(json.dumps(policy,indent=2))
    cal.to_csv(OUT/'interval_calibration_rows.csv',index=False)
    final=[]
    for hist,future in independent(20261002):
        final+=records(hist,future,'final_independent',boosters)
    for cid,g in daily[daily.customer_id.isin(held)].groupby('customer_id'):
        for origin in pd.to_datetime(['2026-07-17','2026-08-16','2026-09-15']):
            final+=records(g[g.date<=origin].tail(125),g[g.date>origin].head(30),'final_pnc',boosters)
    frame=pd.DataFrame(final)
    bounds=[positive_bounds(lo,up,p,params[group]['q'],scale) for lo,up,p,group,scale in zip(frame.lower_before,frame.upper_before,frame.serving,frame.group,frame.scale)]
    frame['lower_after']=[v[0] for v in bounds]
    frame['upper_after']=[v[1] for v in bounds]
    frame.to_csv(OUT/'independent_and_interval_predictions.csv',index=False)
    metrics=[];coverage=[];confidence=[]
    for cohort,g in frame.groupby('cohort'):
        for model in ('serving','lightgbm','calendar_average','rolling_30','previous_week'):
            error=abs(g[model]-g.actual)
            metrics.append({'cohort':cohort,'model':model,'n':len(g),'MAE':error.mean(),'RMSE':np.sqrt(np.mean((g[model]-g.actual)**2)),
                            'WAPE_pct':100*error.sum()/g.actual.sum()})
        for group,part in g.groupby('group'):
            for stage in ('before','after'):
                for level,rows in [('all',part),('positive',part[part.actual>0])]:
                    coverage.append({'cohort':cohort,'group':group,'stage':stage,'level':level,'n':len(rows),
                        'coverage':((rows.actual>=rows[f'lower_{stage}'])&(rows.actual<=rows[f'upper_{stage}'])).mean(),
                        'width':(rows[f'upper_{stage}']-rows[f'lower_{stage}']).mean()})
        profile_errors=g.groupby('customer_id').apply(lambda p:pd.Series({
            'model_minus_calendar_MAE':abs(p.lightgbm-p.actual).mean()-abs(p.calendar_average-p.actual).mean(),
            'model_minus_rolling_MAE':abs(p.lightgbm-p.actual).mean()-abs(p.rolling_30-p.actual).mean()}),include_groups=False)
        for column in profile_errors:
            confidence.append({'cohort':cohort,'quantity':column,'mean':profile_errors[column].mean(),'cluster_95_CI':bootstrap(profile_errors[column])})
    pd.DataFrame(metrics).to_csv(OUT/'independent_generalization_metrics.csv',index=False)
    pd.DataFrame(coverage).to_csv(OUT/'interval_before_after.csv',index=False)
    (OUT/'generalization_bootstrap.json').write_text(json.dumps(confidence,indent=2))
    print(pd.DataFrame(metrics).to_string(index=False))
    print(pd.DataFrame(coverage).to_string(index=False))


if __name__=='__main__':main()
