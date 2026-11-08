"""Read-only sandbox/training comparison. Publishes aggregates, never credentials/IDs.

Historical purchase outcomes are synthetic and category coverage is incomplete;
this is a retrospective diagnostic, not real-customer validation or model selection.
"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.config import Settings
from app.data.nessie import build_nessie_repo
from backend.intelligence.backend_adapter import _history
from backend.intelligence.data import load_daily,PNC
from backend.intelligence.forecasting import forecast_spending
from scripts.evaluate_ml import recursive_fast,MODEL_DIR
from app.calc.metrics import checking_variable_transactions


def describe(frame):
    x=frame.spending
    return {'days':len(x),'zero_day_fraction':float((x==0).mean()),
            'positive_day_mean':float(x[x>0].mean()) if (x>0).any() else None,
            'daily_mean':float(x.mean()),'daily_p95':float(x.quantile(.95))}


def main():
    settings=Settings();repo=build_nessie_repo(settings)
    p=repo.load_profile(settings.nessie_customer_id,settings.as_of_date or __import__('datetime').date.today())
    history=_history(p)
    metadata=json.loads((MODEL_DIR/'metadata.json').read_text())
    # Match the training period, excluding held-out customers.
    daily=load_daily();train=daily[(daily.date<pd.Timestamp('2026-04-04')) & ~daily.customer_id.isin([f'C{i:03}' for i in range(25,31)])]
    counts={};amounts={}
    for t in p.transactions:
        counts[t.category]=counts.get(t.category,0)+1
        if t.amount<0:amounts[t.category]=amounts.get(t.category,0)+float(-t.amount)
    raw=pd.read_csv(PNC/'transactions.csv',parse_dates=['posted_date'])
    raw=raw[(raw.posted_date<pd.Timestamp('2026-04-04')) & ~raw.customer_id.isin([f'C{i:03}' for i in range(25,31)])]
    categories=raw[(raw.flow_class=='expense') & raw.category.isin({'groceries','transport','dining','shopping','other_spending'})].groupby('category').amount.sum()
    variable_rows=raw[(raw.flow_class=='expense') & raw.category.isin({'groceries','transport','dining','shopping','other_spending'})]
    normalized_variable=checking_variable_transactions(p)
    variable_amount=sum(float(-t.amount) for t in normalized_variable)
    result={'training_daily':describe(train),'nessie_daily':describe(history),
            'nessie_recent125':describe(history.tail(125)),
            'training_profile':metadata.get('training_history_profile'),
            'normalized_transaction_category_counts':counts,'normalized_outflows_by_category':amounts,
            'training_variable_category_amount_share':(categories/categories.sum()).to_dict(),
            'training_transaction_frequency':{'variable_transactions':len(variable_rows),
                'transactions_per_customer_day':len(variable_rows)/len(train),'customers':train.customer_id.nunique(),
                'calendar_history_days_each':int(train.groupby('customer_id').size().median())},
            'nessie_transaction_frequency':{'variable_transactions':len(normalized_variable),
                'transactions_per_day':len(normalized_variable)/len(history),
                'transactions_per_positive_day':len(normalized_variable)/max(1,int((history.spending>0).sum())),
                'unclassified_variable_amount_fraction':sum(float(-t.amount) for t in normalized_variable if t.category=='other')/max(1,variable_amount)},
            'import_notices':repo.warnings,
            'limitations':['One configured synthetic customer, not a representative independent customer cohort.',
                          'Category mappings do not prove completeness. Account balances cannot be backtested from an incomplete movement ledger.',
                          'No model or threshold is selected from these outcomes; fallback remains unvalidated for real customer use.']}
    rows=[]
    # Two non-overlapping future blocks; only prior rows enter forecast features.
    for end in (90,120):
        if len(history)<end+30:continue
        h=history.iloc[:end].copy();future=history.iloc[end:end+30]
        serving=forecast_spending(h,30,use_calibration=False)
        methods={'serving':np.array([r['spending'] for r in serving['daily']]),
                 'fixed_mean_28':np.repeat(h.spending.tail(28).mean(),30)}
        for method in ('calendar_average','previous_week','rolling_30'):
            methods[method]=recursive_fast(h,future.date,[],method)[:,0]
        for method,pred in methods.items():
            for horizon in (7,30):
                actual=future.spending.to_numpy()[:horizon];estimate=pred[:horizon]
                rows.append({'origin':str(h.date.iloc[-1].date()),'days':horizon,'method':method,
                             'daily_mae':float(np.mean(abs(actual-estimate))),
                             'total_error':float(estimate.sum()-actual.sum()),'actual_spending':float(actual.sum())})
    out=ROOT/'reports/warning_reliability';out.mkdir(parents=True,exist_ok=True)
    (out/'data_comparison.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    pd.DataFrame(rows).to_csv(out/'nessie_historical_spending.csv',index=False)
    print(json.dumps({k:result[k] for k in ('training_daily','nessie_daily','nessie_recent125','normalized_transaction_category_counts')},indent=2))
    print(pd.DataFrame(rows).to_string(index=False))


if __name__=='__main__':main()
