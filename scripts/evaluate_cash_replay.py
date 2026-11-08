"""Historical synthetic ledger replay, using ONLY origin-available assumptions.

These labels are from the existing PNC ledger, not stress-generated ground truth.
Synthetic cash-management transfers keep balances funded and limit validity.
"""
import json
from decimal import Decimal
import numpy as np
import pandas as pd
import lightgbm as lgb
from backend.intelligence.data import PNC, VARIABLE
from backend.intelligence.forecasting import project_cash
from backend.intelligence.guardian import detect_risks
from backend.intelligence.health_score import health_score
from scripts.evaluate_ml import OUT, MODEL_DIR, BASELINES, load_daily, recursive_fast, metrics


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tx = pd.read_csv(PNC/'transactions.csv',parse_dates=['posted_date'])
    cents = lambda value: int(Decimal(str(value))*100)
    balances, changes = tx.balance_after.map(cents), tx.balance_change.map(cents)
    residual = (balances-balances.groupby(tx.account_id).shift()-changes).dropna()
    transfers = tx[tx.flow_class=='internal_transfer'].copy()
    liabilities = {'credit_card','auto_loan','personal_loan','mortgage'}
    transfers['wealth_delta'] = [cents(v)*(-1 if a in liabilities else 1) for v,a in zip(transfers.balance_change,transfers.account_type)]
    transfer_sums = transfers.groupby('transfer_id').wealth_delta.sum()
    integrity = {'account_continuity_violations_cents':int((residual!=0).sum()),
                 'internal_transfer_pairs':len(transfer_sums),
                 'internal_transfer_wealth_residual_violations':int((transfer_sums!=0).sum()),
                 'cash_replay_limitation':'Existing ledger is internally reconciled but artificially calibrated; not real bank ground truth'}
    (OUT/'ledger_integrity.json').write_text(json.dumps(integrity,indent=2))
    tx = tx.sort_values('posted_date',kind='stable')
    daily = load_daily()
    meta = json.loads((MODEL_DIR/'metadata.json').read_text())
    boosters = [lgb.Booster(model_file=str(MODEL_DIR/f'{name}.txt')) for name in ('lower','median','upper')]
    test_start = pd.Timestamp(meta['validation_end_exclusive'])
    cash_rows, risk_rows = [], []
    for cid,g in daily.groupby('customer_id'):
        ledger = tx[(tx.customer_id==cid)&(tx.account_type=='checking')]
        assert ledger.account_id.nunique()==1,'Replay needs one checking account per synthetic customer'
        for offset in (0,30,60):
            origin = test_start-pd.Timedelta(days=1)+pd.Timedelta(days=offset)
            history = g[g.date<=origin].tail(125)
            future = g[g.date>origin].head(90 if offset==0 else 30)
            past = ledger[ledger.posted_date<=origin]
            if past.empty:
                continue
            checking = float(past.balance_after.iloc[-1])
            recent = past[past.posted_date>origin-pd.Timedelta(days=90)]
            income = recent[recent.flow_class=='income']
            expenses = recent[(recent.balance_change<0)&(~recent.category.isin(VARIABLE))&
                              (~recent.flow_class.isin(['external_transfer']))]
            bills = [{'name':cat,'amount':round(float(-part.balance_change.sum()/3),2),
                      'day':int(part.posted_date.dt.day.mode().iloc[0])} for cat,part in expenses.groupby('category')]
            saved = tx[(tx.customer_id==cid)&(tx.account_type=='savings')&(tx.posted_date<=origin)]
            customer = {'customer_id':cid,'as_of':str(origin.date()),'checking_balance':checking,
                'savings_balance':float(saved.balance_after.iloc[-1]) if len(saved) else 0.,
                'monthly_income':round(float(income.balance_change.sum()/3),2),
                'monthly_variable_spending':float(history.tail(90).spending.sum()/3),
                'monthly_debt_payments':sum(b['amount'] for b in bills if b['name']=='debt_payment'),
                'bills':bills,'paydays':sorted(set(income.posted_date.dt.day)) or [1,15],
                'budget':None,'safety_buffer':500.}
            # End-of-day cash labels from actual ledger balance_after, not a
            # cash balance reconstructed from model consumption targets.
            actual = ledger.groupby('posted_date',sort=True).balance_after.last()
            actual = actual.reindex(pd.date_range(origin,future.date.max())).ffill()
            actual.iloc[0] = checking
            actual = actual.ffill().iloc[1:].to_numpy(float)
            for model in BASELINES+['lightgbm']:
                prediction = recursive_fast(history,future.date,boosters,model)
                path = {'daily':[{'date':str(d.date()),'spending':p,'lower':lo,'upper':hi}
                                 for d,(p,lo,hi) in zip(future.date,prediction)]}
                projected = project_cash(customer,path)
                predicted = np.array([r['balance'] for r in projected['daily']])
                for horizon in (1,7,14,30,90):
                    if horizon>len(actual):
                        continue
                    cash_rows.append({'customer_id':cid,'cohort':'unseen_customers' if cid in meta['heldout_customers'] else 'known_customers',
                        'origin':str(origin.date()),'model':model,'horizon':horizon,
                        **metrics(actual[:horizon],predicted[:horizon]),
                        'ending_error':float(predicted[horizon-1]-actual[horizon-1]),
                        'actual_min':float(min(checking,actual[:horizon].min())),
                        'predicted_min':float(min(checking,predicted[:horizon].min()))})
                    if model!='lightgbm':
                        continue
                    for threshold in (500,1000,2000):
                        c = {**customer,'safety_buffer':threshold}
                        fc = {**projected,'daily':projected['daily'][:horizon],
                              'minimum_balance':float(min(checking,predicted[:horizon].min()))}
                        alerts = detect_risks(c,fc,health_score(c))
                        risk_rows.append({'customer_id':cid,'origin':str(origin.date()),'horizon':horizon,'threshold':threshold,
                            'predicted':int(any(a['id']=='low_balance' for a in alerts)),
                            'actual':int(min(checking,actual[:horizon].min())<threshold)})
    cash = pd.DataFrame(cash_rows)
    cash.to_csv(OUT/'historical_cash_origin_metrics.csv',index=False)
    grouped = cash.groupby(['cohort','model','horizon']).agg(origins=('MAE','size'),balance_path_MAE=('MAE','mean'),
        ending_balance_MAE=('ending_error',lambda x:x.abs().mean()),ending_bias=('ending_error','mean')).reset_index()
    grouped.to_csv(OUT/'historical_cash_metrics.csv',index=False)
    risk = pd.DataFrame(risk_rows)
    risk.to_csv(OUT/'guardian_labeled_replay.csv',index=False)
    records=[]
    for (h,t),g in risk.groupby(['horizon','threshold']):
        tp=int(((g.predicted==1)&(g.actual==1)).sum());tn=int(((g.predicted==0)&(g.actual==0)).sum())
        fp=int(((g.predicted==1)&(g.actual==0)).sum());fn=int(((g.predicted==0)&(g.actual==1)).sum())
        records.append({'horizon':h,'threshold':t,'n':len(g),'TP':tp,'TN':tn,'FP':fp,'FN':fn,
            'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None,
            'F1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
            'false_positive_rate':fp/(fp+tn) if fp+tn else None,'false_negative_rate':fn/(fn+tp) if fn+tp else None})
    result=pd.DataFrame(records)
    result.to_csv(OUT/'guardian_metrics.csv',index=False)
    import matplotlib.pyplot as plt
    r=result[(result.horizon==30)&(result.threshold==500)].iloc[0]
    matrix=np.array([[r.TN,r.FP],[r.FN,r.TP]])
    fig,ax=plt.subplots(); ax.imshow(matrix,cmap='Blues')
    for (i,j),v in np.ndenumerate(matrix): ax.text(j,i,int(v),ha='center',va='center')
    ax.set(xticks=[0,1],yticks=[0,1],xticklabels=['No alert','Alert'],yticklabels=['No observed breach','Observed breach'],
           xlabel='Guardian prediction',ylabel='Synthetic ledger outcome',title='30-day / $500 buffer · synthetic historical replay')
    fig.tight_layout();fig.savefig(OUT/'guardian_confusion_matrix.png',dpi=160);plt.close(fig)
    print(result.to_string(index=False))


if __name__=='__main__':
    main()
