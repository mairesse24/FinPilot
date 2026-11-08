"""Cash error attribution and validation-selected risk margins. No final tuning."""
import json
import numpy as np
import pandas as pd
import lightgbm as lgb
from backend.intelligence.data import PNC,VARIABLE,load_daily,ROOT
from backend.intelligence.forecasting import project_cash
from backend.intelligence.ledger_projection import ledger_assumptions
from backend.intelligence.guardian import detect_risks
from backend.intelligence.health_score import health_score
from scripts.evaluate_ml import MODEL_DIR,recursive_fast

OUT=ROOT/'reports/reliability'


def f1(y,p):
    tp=int(np.sum(y&p)); fp=int(np.sum(~y&p)); fn=int(np.sum(y&~p));tn=int(np.sum(~y&~p))
    return {'TP':tp,'FP':fp,'FN':fn,'TN':tn,'precision':tp/(tp+fp) if tp+fp else None,
            'recall':tp/(tp+fn) if tp+fn else None,'F1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    tx=pd.read_csv(PNC/'transactions.csv',parse_dates=['posted_date']).sort_values('posted_date',kind='stable')
    daily=load_daily();boosters=[lgb.Booster(model_file=str(MODEL_DIR/f'{n}.txt')) for n in ('lower','median','upper')]
    records=[];components=[]
    for cid,g in daily.groupby('customer_id'):
        ledger=tx[(tx.customer_id==cid)&(tx.account_type=='checking')]
        for split,origins in [('development',pd.to_datetime(['2026-04-03','2026-05-03','2026-06-02'])),
                              ('final',pd.to_datetime(['2026-07-17','2026-08-16','2026-09-15']))]:
            for origin in origins:
                past=ledger[ledger.posted_date<=origin];recent=past[past.posted_date>origin-pd.Timedelta(days=90)]
                history=g[g.date<=origin].tail(125);future=g[g.date>origin].head(30)
                checking=float(past.balance_after.iloc[-1]);inc=recent[recent.flow_class=='income']
                fixed=recent[(recent.balance_change<0)&~recent.category.isin(VARIABLE)&(recent.flow_class!='external_transfer')]
                bills=[{'name':cat,'amount':round(float(-part.balance_change.sum()/3),2),'day':int(part.posted_date.dt.day.mode().iloc[0])} for cat,part in fixed.groupby('category')]
                c={'customer_id':cid,'as_of':str(origin.date()),'checking_balance':checking,'savings_balance':0.,
                   'monthly_income':float(inc.balance_change.sum()/3),'monthly_variable_spending':float(history.tail(90).spending.sum()/3),
                   'monthly_debt_payments':0.,'bills':bills,'paydays':sorted(set(inc.posted_date.dt.day)) or [1,15],'safety_buffer':500.}
                predicted=recursive_fast(history,future.date,boosters,'lightgbm')
                path={'daily':[{'date':str(d.date()),'spending':p,'lower':lo,'upper':hi} for d,(p,lo,hi) in zip(future.date,predicted)]}
                before=project_cash(c,path)
                assumptions=ledger_assumptions(tx[tx.customer_id==cid],origin)
                after=project_cash({**c,**assumptions},path)
                observed=ledger[(ledger.posted_date>origin)&(ledger.posted_date<=future.date.max())]
                def events(mask,column='balance_change'):
                    return observed[mask].groupby('posted_date')[column].sum().reindex(future.date,fill_value=0).to_numpy(float)
                y=checking+np.cumsum(events(pd.Series(True,index=observed.index)))
                ai=events(observed.flow_class=='income')
                av=-events((observed.balance_change<0)&observed.category.isin(VARIABLE))
                ab=-events((observed.balance_change<0)&~observed.category.isin(VARIABLE)&(observed.flow_class!='external_transfer'))
                external=events(observed.flow_class=='external_transfer')
                b=np.array([r['balance'] for r in before['daily']]);a=np.array([r['balance'] for r in after['daily']])
                probes={'before':b,'oracle_variable':b+np.cumsum(predicted[:,0]-av)}
                probes['oracle_income']=probes['oracle_variable']+np.cumsum(ai-np.array([r['income'] for r in before['daily']]))
                probes['oracle_bills']=probes['oracle_income']+np.cumsum(np.array([r['bills'] for r in before['daily']])-ab)
                probes['oracle_external']=probes['oracle_bills']+np.cumsum(external)
                other=events(pd.Series(True,index=observed.index))-(ai-av-ab+external)
                probes['oracle_other']=probes['oracle_external']+np.cumsum(other)
                for horizon in (7,30):
                    actual_min=min(checking,*y[:horizon])
                    native_flags={}
                    for stage,customer,out in [('before',c,before),('after',{**c,**assumptions},after)]:
                        customer={**customer,'safety_buffer':2000.}
                        fc={**out,'daily':out['daily'][:horizon],
                            'minimum_balance':min(checking,*[r['balance'] for r in out['daily'][:horizon]])}
                        native_flags[stage]=int(any(a['id']=='low_balance' for a in detect_risks(customer,fc,health_score(customer))))
                        assert native_flags[stage]==int(fc['minimum_balance']<2000)
                    records.append({'customer_id':cid,'split':split,'origin':str(origin.date()),'horizon':horizon,
                        'before_native_guardian_2000':native_flags['before'],'after_native_guardian_2000':native_flags['after'],
                        'before_path_MAE':np.abs(b[:horizon]-y[:horizon]).mean(),'after_path_MAE':np.abs(a[:horizon]-y[:horizon]).mean(),
                        'before_ending_AE':abs(b[horizon-1]-y[horizon-1]),'after_ending_AE':abs(a[horizon-1]-y[horizon-1]),
                        'actual_min':actual_min,'before_min':min(checking,*b[:horizon]),'after_min':min(checking,*a[:horizon])})
                    for name,values in probes.items():
                        components.append({'split':split,'horizon':horizon,'stage':name,'ending_AE':abs(values[horizon-1]-y[horizon-1]),'path_MAE':np.abs(values[:horizon]-y[:horizon]).mean()})
    frame=pd.DataFrame(records);frame.to_csv(OUT/'cash_before_after.csv',index=False)
    pd.DataFrame(components).groupby(['split','horizon','stage']).mean().reset_index().to_csv(OUT/'cash_attribution.csv',index=False)
    # Fixed candidate margins and fixed precision gate, selected on development only.
    margins={};rows=[]
    for h in (7,30):
        dev=frame[(frame.split=='development')&(frame.horizon==h)]
        candidates=[]
        for margin in (0,100,250,500,1000,1500,2000):
            metrics=f1((dev.actual_min<2000).to_numpy(),(dev.after_min-margin<2000).to_numpy())
            candidates.append((margin,metrics))
        eligible=[(m,r) for m,r in candidates if r['precision'] is not None and r['precision']>=.5]
        chosen=max(eligible,key=lambda v:(v[1]['F1'],-v[0]))[0] if eligible else 0
        margins[str(h)]=chosen
        for split in ('development','final'):
            part=frame[(frame.split==split)&(frame.horizon==h)]
            for threshold in (500,1000,2000):
                for name,score in [('before',part.before_min),('after_point',part.after_min),('after_watch',part.after_min-chosen)]:
                    rows.append({'split':split,'horizon':h,'threshold':threshold,'policy':name,'margin':chosen if name=='after_watch' else 0,
                        **f1((part.actual_min<threshold).to_numpy(),(score<threshold).to_numpy())})
    pd.DataFrame(rows).to_csv(OUT/'guardian_before_after.csv',index=False)
    (OUT/'guardian_development_policy.json').write_text(json.dumps({'margins':margins,'selection':'Development F1, precision >= .5, ties smaller margin; $2000 buffer. Final labels never used.','deployment':'Research-only: cash-ledger calibration does not establish validity for Nessie profiles.'},indent=2))
    print(frame[frame.split=='final'].groupby('horizon')[['before_path_MAE','after_path_MAE','before_ending_AE','after_ending_AE']].mean())
    print('Development selected margins:',margins)


if __name__=='__main__':main()
