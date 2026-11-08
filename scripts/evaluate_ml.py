"""Reproducible frozen-artifact evaluation; never overwrites production models.

Run: python -m scripts.evaluate_ml
Synthetic labeled consumption is the only accuracy ground truth. Cumulative
spending errors imply conditional balance errors, NOT observed bank accuracy.
"""
import hashlib
import json
import os
import platform
from pathlib import Path

import lightgbm as lgb
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'reports/ml_evaluation/.mplcache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from backend.intelligence.data import PNC, ROOT, load_daily
from backend.intelligence.features import FEATURES, make_features
from backend.intelligence.forecasting import forecast_spending
from backend.intelligence.training import MODEL_DIR

OUT = ROOT / 'reports/ml_evaluation'
BASELINES = ['previous_day', 'previous_week', 'rolling_7', 'rolling_30', 'calendar_average']


def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    e, ae = p-y, np.abs(p-y)
    denominator = np.abs(y)+np.abs(p)
    return {'n': len(y), 'MAE': float(ae.mean()), 'RMSE': float(np.sqrt(mean_squared_error(y, p))),
            'WAPE_pct': float(100*ae.sum()/np.abs(y).sum()) if np.abs(y).sum() else None,
            'sMAPE_pct': float(200*np.mean(np.divide(ae, denominator, out=np.zeros_like(ae), where=denominator!=0))),
            'R2': float(r2_score(y, p)) if len(y)>1 and np.var(y)>0 else None,
            'bias': float(e.mean()), 'median_AE': float(np.median(ae)),
            'p90_AE': float(np.quantile(ae, .9)), 'p95_AE': float(np.quantile(ae, .95))}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table(frame):
    # Avoid an optional tabulate dependency.
    f = frame.copy()
    for c in f.select_dtypes(include='number'):
        f[c] = f[c].map(lambda x: f'{x:.4f}' if pd.notna(x) else 'N/A')
    return '| ' + ' | '.join(f.columns) + ' |\n|' + '|'.join(['---']*len(f.columns)) + '|\n' + '\n'.join('| '+' | '.join(map(str, row))+' |' for row in f.itertuples(index=False, name=None))


def frozen_predictions(frame, boosters):
    q = np.sort(np.maximum(0, np.array([b.predict(frame[FEATURES], num_threads=1) for b in boosters])), axis=0)
    return q


def recursive_fast(history, dates, boosters, method):
    """Scalar equivalent of production feature recursion, parity-tested below.

    Each baseline consumes ONLY its own earlier predictions, never future labels.
    """
    observed = dict(zip(pd.to_datetime(history.date), history.spending.astype(float)))
    values = list(history.spending.astype(float))
    results = []
    for day in dates:
        lag1 = observed.get(day-pd.DateOffset(months=1), np.mean(values[-28:]))
        calendars = [observed.get(day-pd.DateOffset(months=m), np.nan) for m in (1, 2, 3)]
        calendar_mean = np.nanmean(calendars) if any(np.isfinite(calendars)) else np.mean(values[-28:])
        if method == 'lightgbm':
            row = np.array([[day.day_of_week, day.day, day.month, min(abs(day.day-d) for d in (1,15,28)),
                             values[-1], values[-7], values[-28], np.mean(values[-7:]),
                             np.mean(values[-28:]), np.std(values[-28:], ddof=1), lag1, calendar_mean]])
            lower, point, upper = sorted(max(0., float(b.predict(row, num_threads=1)[0])) for b in boosters)
        else:
            point = {'previous_day': lambda: values[-1], 'previous_week': lambda: values[-7],
                     'rolling_7': lambda: np.mean(values[-7:]), 'rolling_30': lambda: np.mean(values[-30:]),
                     'calendar_average': lambda: calendar_mean}[method]()
            lower = upper = float(point)
        results.append((round(float(point), 2), round(float(lower), 2), round(float(upper), 2)))
        observed[day] = point
        values.append(point)
    return np.array(results)


def evaluate():
    OUT.mkdir(parents=True, exist_ok=True)
    metadata = json.loads((MODEL_DIR/'metadata.json').read_text())
    hashes = {name: digest(MODEL_DIR/f'{name}.txt') for name in ('lower','median','upper')}
    boosters = [lgb.Booster(model_file=str(MODEL_DIR/f'{name}.txt')) for name in hashes]
    daily = load_daily()
    frame = make_features(daily)
    # Compute 30-day baseline on the ORIGINAL daily grid, not the dropna feature grid.
    thirty = daily.sort_values(['customer_id','date']).copy()
    thirty['mean_30_eval'] = thirty.groupby('customer_id').spending.transform(lambda s: s.shift(1).rolling(30).mean())
    frame = frame.merge(thirty[['customer_id','date','mean_30_eval']], on=['customer_id','date'], validate='one_to_one')
    train_end = pd.Timestamp(metadata['train_end_exclusive'])
    test_start = pd.Timestamp(metadata['validation_end_exclusive'])
    heldout = set(metadata['heldout_customers'])
    test = frame[frame.date>=test_start].copy()
    test['cohort'] = np.where(test.customer_id.isin(heldout), 'unseen_customers', 'known_customers')
    q = frozen_predictions(test, boosters)
    test['lightgbm'], test['lower'], test['upper'] = q[1], q[0], q[2]
    for name, col in zip(BASELINES, ['lag_1','lag_7','mean_7','mean_30_eval','calendar_mean_3']):
        test[name] = test[col]
    one_day = []
    for cohort, part in test.groupby('cohort'):
        for model in BASELINES+['lightgbm']:
            one_day.append({'cohort':cohort,'model':model,**metrics(part.spending,part[model])})
    scores = pd.DataFrame(one_day)
    for cohort in scores.cohort.unique():
        mask = scores.cohort==cohort
        best = scores[mask & scores.model.isin(BASELINES)].MAE.min()
        scores.loc[mask,'improvement_vs_best_baseline_pct'] = 100*(best-scores.loc[mask,'MAE'])/best
    scores.to_csv(OUT/'one_day_metrics.csv', index=False)
    test.to_csv(OUT/'one_day_predictions.csv', index=False)
    print('Frozen one-day evaluation complete', flush=True)

    # Non-overlapping 30-day blocks per customer. 90-day forecasts use the first
    # origin and are reported separately; observations across horizons overlap.
    recursive_rows, horizon_metrics, coverage_rows = [], [], []
    pooled = {}
    for cid, group in daily.groupby('customer_id'):
        group = group.sort_values('date')
        for offset in (0,30,60):
            origin = test_start-pd.Timedelta(days=1)+pd.Timedelta(days=offset)
            history = group[group.date<=origin].tail(125)
            future = group[group.date>origin].head(90 if offset==0 else 30)
            if len(future)<30:
                continue
            for model in BASELINES+['lightgbm']:
                predicted = recursive_fast(history, future.date, boosters, model)
                if cid == sorted(daily.customer_id.unique())[0] and offset==0 and model=='lightgbm':
                    native = forecast_spending(history, len(future), use_calibration=False)
                    native_values = np.array([[r['spending'],r['lower'],r['upper']] for r in native['daily']])
                    if not np.array_equal(predicted, native_values):
                        raise AssertionError(f'Fast evaluator differs from production by {np.max(abs(predicted-native_values))}')
                for horizon in (1,7,14,30,90):
                    if horizon>len(future):
                        continue
                    y, p = future.spending.to_numpy()[:horizon], predicted[:horizon,0]
                    m = metrics(y,p)
                    cohort = 'unseen_customers' if cid in heldout else 'known_customers'
                    pooled.setdefault((cohort,model,horizon),[]).append((y,p))
                    recursive_rows.append({'customer_id':cid,'cohort':'unseen_customers' if cid in heldout else 'known_customers',
                        'origin':str(origin.date()),'horizon':horizon,'model':model, **m,
                        'total_spending_error':float((p-y).sum()),
                        'conditional_ending_balance_error':float((y-p).sum()),
                        'conditional_balance_path_MAE':float(np.mean(np.abs(np.cumsum(y-p))))})
                    if model=='lightgbm':
                        for i in range(horizon):
                            coverage_rows.append({'customer_id':cid,'origin':str(origin.date()),'horizon':horizon,
                                'actual':y[i],'point':p[i],'lower':predicted[i,1],'upper':predicted[i,2]})
        print(f'Recursive evaluation {cid}', flush=True)
    rec = pd.DataFrame(recursive_rows)
    rec.to_csv(OUT/'recursive_origin_metrics.csv',index=False)
    # Aggregate origin metrics with equal horizons; report dollar path error and
    # cumulative ending error separately, never label these observed bank errors.
    for (cohort,model,h), g in rec.groupby(['cohort','model','horizon']):
        pairs = pooled[(cohort,model,h)]
        aggregate = metrics(np.concatenate([y for y,p in pairs]),np.concatenate([p for y,p in pairs]))
        horizon_metrics.append({'cohort':cohort,'model':model,'horizon':h,'origins':len(g),
            **{k:v for k,v in aggregate.items() if k not in ('MAE','RMSE')},
            'daily_MAE':g.MAE.mean(),'daily_RMSE':float(np.sqrt(np.mean(g.RMSE**2))),
            'ending_balance_MAE_conditional':g.conditional_ending_balance_error.abs().mean(),
            'balance_path_MAE_conditional':g.conditional_balance_path_MAE.mean(),
            'spending_total_bias':g.total_spending_error.mean()})
    horizons = pd.DataFrame(horizon_metrics)
    horizons.to_csv(OUT/'horizon_metrics.csv',index=False)
    cov = pd.DataFrame(coverage_rows)
    cov['covered'] = (cov.actual>=cov.lower)&(cov.actual<=cov.upper)
    cov['width'] = cov.upper-cov.lower
    cov['level'] = np.where(cov.actual==0,'zero',np.where(cov.actual<=test[test.spending>0].spending.median(),'positive_low','positive_high'))
    calibration = []
    for dimension in ('horizon','customer_id','level'):
        subset = cov if dimension=='horizon' else cov[cov.horizon==30]
        for key,g in subset.groupby(dimension):
            calibration.append({'dimension':dimension,'group':str(key),'n':len(g),
                'coverage_80':g.covered.mean(),'width_USD':g.width.mean()})
    pd.DataFrame(calibration).to_csv(OUT/'interval_calibration.csv',index=False)

    # Expanding fits use the SAME predeclared hyperparameters; no fit saved and
    # no production selection changed. Held-out customers stay out of all fitting.
    walk = []
    dates = sorted(frame.date.unique())
    known = frame[~frame.customer_id.isin(heldout)]
    for frac in (.55,.70,.85):
        cut = pd.Timestamp(dates[int(len(dates)*frac)])
        val_start = cut-pd.Timedelta(days=30)
        tr,va,te = known[known.date<val_start],known[(known.date>=val_start)&(known.date<cut)],known[(known.date>=cut)&(known.date<cut+pd.Timedelta(days=30))]
        model = lgb.LGBMRegressor(objective='quantile',alpha=.5,n_estimators=400,learning_rate=.04,
            num_leaves=23,min_child_samples=40,random_state=42,n_jobs=2,verbosity=-1)
        model.fit(tr[FEATURES],tr.spending,eval_set=[(va[FEATURES],va.spending)],callbacks=[lgb.early_stopping(35,verbose=False)])
        for name,p in [('lightgbm_median',model.predict(te[FEATURES])),('calendar_average',te.calendar_mean_3)]:
            walk.append({'test_start':str(cut.date()),'test_end_exclusive':str((cut+pd.Timedelta(days=30)).date()),
                         'train_rows':len(tr),'validation_rows':len(va),'model':name,**metrics(te.spending,np.maximum(0,p))})
    pd.DataFrame(walk).to_csv(OUT/'expanding_walk_forward.csv',index=False)

    tx = pd.read_csv(PNC/'transactions.csv')
    summary = {'python':platform.python_version(),'lightgbm':lgb.__version__,'numpy':np.__version__,
        'pandas':pd.__version__,'seed':42,'model_sha256':hashes,
        'data_sha256':digest(PNC/'transactions.csv'),'daily_rows':len(daily),'feature_rows':len(frame),
        'customers':int(daily.customer_id.nunique()),'daily_start':str(daily.date.min()),'daily_end':str(daily.date.max()),
        'transaction_rows':len(tx),'transaction_columns':list(tx.columns),
        'duplicate_transaction_rows':int(tx.duplicated().sum()),
        'duplicate_transaction_ids':int(tx.duplicated('transaction_id').sum()) if 'transaction_id' in tx else None,
        'negative_source_amounts':int((tx.amount<0).sum()),
        'test_rows':len(test),'training_rows':metadata['training_rows'],
        'train_end':str(train_end),'test_start':str(test_start),'features':FEATURES,
        'heldout_customers':sorted(heldout),'target_zero_fraction':float((daily.spending==0).mean()),
        'quantile_crossing_rows_raw':int(np.any(np.diff(np.array([b.predict(test[FEATURES],num_threads=1) for b in boosters]),axis=0)<0,axis=0).sum()),
        'negative_served_predictions':int((test.lightgbm<0).sum()),
        'bounds_order_failures':int((cov.lower>cov.upper).sum()),
        'one_day_coverage_80':float(((test.spending>=test.lower)&(test.spending<=test.upper)).mean()),
        'ninety_percent_interval':'NOT EVALUATED: .05/.95 models not implemented; cannot infer from .1/.9 models',
        'guardian_historical_classification':'Separate historical synthetic ledger replay in guardian_metrics.csv; risk labels derived from existing balance_after, not real customer validation',
        'conditional_balance_error':'Negative cumulative spending error with identical known flows; not historical account-balance accuracy',
        'fast_recursive_parity':'PASS: exact rounded path equality against production forecast_spending for first customer, 90 days',
        'model_files_unchanged':hashes=={name:digest(MODEL_DIR/f'{name}.txt') for name in hashes}}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    plots(test,scores,horizons,pd.DataFrame(calibration))
    print('Evaluation artifacts written:',OUT,flush=True)
    return summary,scores,horizons,pd.DataFrame(walk)


def plots(test,scores,horizons,calibration):
    plt.style.use('seaborn-v0_8-whitegrid')
    def save(name):
        plt.tight_layout(); plt.savefig(OUT/f'{name}.png',dpi=160); plt.close()
    example = test[test.customer_id==sorted(test.customer_id.unique())[0]]
    plt.figure(figsize=(11,4)); plt.plot(example.date,example.spending,label='Actual synthetic spending');plt.plot(example.date,example.lightgbm,label='LightGBM one-day');plt.legend();plt.ylabel('USD/day');plt.xticks(rotation=30);save('predicted_vs_actual')
    plt.figure(figsize=(8,4));plt.hist(test.lightgbm-test.spending,bins=70);plt.xlabel('Prediction minus actual (USD)');plt.ylabel('Daily observations');save('residual_distribution')
    pivot=scores.pivot(index='model',columns='cohort',values='MAE');pivot.plot.bar(figsize=(10,5));plt.ylabel('Daily MAE (USD)');plt.xticks(rotation=25);save('baseline_comparison')
    for cohort,g in horizons[horizons.model=='lightgbm'].groupby('cohort'):
        plt.plot(g.horizon,g.daily_MAE,marker='o',label=cohort)
    plt.legend();plt.xlabel('Recursive horizon (days)');plt.ylabel('Daily spending MAE (USD)');save('mae_by_horizon')
    by_profile=test.groupby('customer_id').apply(lambda g: np.abs(g.lightgbm-g.spending).mean(),include_groups=False)
    by_profile.plot.bar(figsize=(12,4));plt.ylabel('One-day spending MAE (USD)');save('error_by_profile')
    c=calibration[calibration.dimension=='horizon'];plt.figure(figsize=(7,4));plt.plot(c.group.astype(int),c.coverage_80,marker='o');plt.axhline(.8,color='red',linestyle='--',label='Nominal 80%');plt.ylim(0,1);plt.xlabel('Recursive horizon (days)');plt.ylabel('Empirical daily interval coverage');plt.legend();save('interval_coverage')


if __name__ == '__main__':
    evaluate()
