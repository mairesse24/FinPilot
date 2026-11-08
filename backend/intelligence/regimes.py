"""Descriptive macro dimensions, not recession forecasts or calibrated probabilities."""
from datetime import date
import numpy as np
import pandas as pd
from .economic_data import CATALOG


def sahm(unemployment):
    average=unemployment.rolling(3,min_periods=3).mean()
    return average-average.shift(1).rolling(12,min_periods=12).min()


def classify(snapshot,as_of,historical=False):
    origin=date.fromisoformat(as_of);usable={};indicators=[];excluded=[]
    for name,source in snapshot.get('series',{}).items():
        knowledge=source.get('knowledge_date')
        released=source.get('initial_release_date') or (source.get('release_timestamp') or '')[:10]
        if not knowledge or knowledge>as_of or (released and released>as_of) or (historical and not source.get('point_in_time')):
            excluded.append(name+': availability/vintage unverified for this origin');continue
        rows=[r for r in source.get('observations',[]) if r['date']<=as_of and
              ((r.get('available_on') is not None and r['available_on']<=as_of) or (not historical and not source.get('point_in_time')))]
        if not rows:continue
        series=pd.Series([r['value'] for r in rows],index=pd.to_datetime([r['date'] for r in rows]),dtype=float).sort_index()
        if series.index.has_duplicates or not np.isfinite(series).all():
            excluded.append(name+': invalid/duplicate observations');continue
        age=(origin-series.index[-1].date()).days
        limit=CATALOG.get(name,('daily','Yahoo Finance',7))[2]
        stale=age>limit
        indicators.append({'id':name,'value':float(series.iloc[-1]),'observation_date':str(series.index[-1].date()),
            'knowledge_date':knowledge,'release_timestamp':source.get('release_timestamp'),
            'initial_release_date':source.get('initial_release_date'),
            'retrieved_at':source.get('retrieved_at'),'age_days':age,'stale':stale,
            'source_url':source.get('source_url'),'publisher':source.get('publisher',source.get('source')),
            'units':source.get('units'),'frequency':source.get('frequency'),'seasonal_adjustment':source.get('seasonal_adjustment'),
            'point_in_time':source.get('point_in_time',False)})
        if not stale:usable[name]=series
    def monthly(name):
        if name not in usable:return None
        return usable[name].resample('MS').last().asfreq('MS')
    def last(series):
        return float(series.iloc[-1]) if series is not None and len(series) and pd.notna(series.iloc[-1]) else None
    features={}
    for name in ('CPIAUCSL','CPILFESL','PCEPI'):
        s=monthly(name)
        if s is not None:
            features[name+'_yoy_pct']=last(100*(s/s.shift(12)-1))
            features[name+'_mom_pct']=last(100*(s/s.shift(1)-1))
            features[name+'_acceleration_pp']=last(100*(s/s.shift(12)-1)-100*(s.shift(3)/s.shift(15)-1))
    u=monthly('UNRATE');features['sahm_computed_pp']=last(sahm(u)) if u is not None else None
    features['sahm_official_pp']=last(usable.get('SAHMREALTIME'))
    features['claims_4w_vs_prior13w_pct']=None
    if 'ICSA' in usable and len(usable['ICSA'])>=17:
        s=usable['ICSA'];features['claims_4w_vs_prior13w_pct']=float(100*(s.tail(4).mean()/s.iloc[-17:-4].mean()-1))
    for name in ('INDPRO','RSAFS'):
        s=monthly(name)
        features[name+'_3m_pct']=last(100*(s/s.shift(3)-1)) if s is not None else None
    g=usable.get('GDPC1')
    features['gdp_qoq_annualized_pct']=None
    if g is not None:
        q=g.resample('QS').last().asfreq('QS')
        features['gdp_qoq_annualized_pct']=last(100*((q/q.shift(1))**4-1))
    features['yield_spread_pp']=last(usable.get('T10Y2Y'))
    features['policy_rate_pct']=last(usable.get('FEDFUNDS'))
    features['ten_year_yield_pct']=last(usable.get('DGS10'))
    features['two_year_yield_pct']=last(usable.get('DGS2'))
    treasury=usable.get('DGS10')
    features['ten_year_change_63sessions_pp']=float(treasury.iloc[-1]-treasury.iloc[-64]) if treasury is not None and len(treasury)>=64 else None
    features['policy_rate_change_3m_pp']=None
    rate=monthly('FEDFUNDS')
    if rate is not None:features['policy_rate_change_3m_pp']=last(rate-rate.shift(3))
    features['credit_spread_pct']=last(usable.get('BAMLH0A0HYM2'))
    features['credit_prior90_pctile']=None
    credit=usable.get('BAMLH0A0HYM2')
    if credit is not None and len(credit)>=253:features['credit_prior90_pctile']=float(credit.iloc[:-1].tail(2520).quantile(.9))
    equity=usable.get('SPY',usable.get('^GSPC',usable.get('SP500')))
    features.update({'equity_return_63sessions_pct':None,'drawdown_252sessions_pct':None,'realized_vol20_annualized_pct':None,'market_vol_prior90_pctile':None,'equity_vs_bond_63sessions_pp':None})
    if equity is not None and len(equity)>=253:
        returns=np.log(equity/equity.shift(1));vol=100*returns.rolling(20).std()*np.sqrt(252)
        features['equity_return_63sessions_pct']=float(100*(equity.iloc[-1]/equity.iloc[-64]-1))
        features['drawdown_252sessions_pct']=float(100*(equity.iloc[-1]/equity.tail(252).max()-1))
        features['realized_vol20_annualized_pct']=last(vol)
        features['market_vol_prior90_pctile']=float(vol.iloc[:-1].dropna().tail(2520).quantile(.9))
        bond=usable.get('AGG')
        if bond is not None and len(bond)>=64:features['equity_vs_bond_63sessions_pp']=features['equity_return_63sessions_pct']-float(100*(bond.iloc[-1]/bond.iloc[-64]-1))
    dimensions=[]
    def dimension(name,known,signals,explanation):
        dimensions.append({'name':name,'available':known,'signals':signals,'explanation':explanation,'flagged':bool(signals)})
    pce=features.get('PCEPI_yoy_pct');core=features.get('CPILFESL_yoy_pct')
    dimension('inflation',pce is not None,[s for s,flag in [('PCE inflation above 2% objective',pce is not None and pce>2),('PCE inflation accelerating',features.get('PCEPI_acceleration_pp') is not None and features['PCEPI_acceleration_pp']>0)] if flag],
        'The 2% longer-run objective is PCE, not CPI. Annual and monthly rates are reported separately.')
    sahm_value=features['sahm_official_pp'] if features['sahm_official_pp'] is not None else features['sahm_computed_pp']
    dimension('labor',sahm_value is not None,[s for s,flag in [('Sahm recession indicator triggered',sahm_value is not None and sahm_value>=.5),('Claims rising relative to prior weeks',features['claims_4w_vs_prior13w_pct'] is not None and features['claims_4w_vs_prior13w_pct']>0)] if flag],
        'Sahm >=0.50 percentage points is a published recession indicator, not an individual job-loss prediction. Claims direction is descriptive.')
    growth=[features.get(k) for k in ('gdp_qoq_annualized_pct','INDPRO_3m_pct','RSAFS_3m_pct')]
    dimension('growth',any(v is not None for v in growth),[s for s,value in zip(['Real GDP contraction','Industrial output decline','Nominal retail decline'],growth) if value is not None and value<0],
        'GDP is quarterly annualized; industrial/retail changes are separate 3-month rates. Retail sales are nominal, not real GDP.')
    spread=features['yield_spread_pp'];change=features['policy_rate_change_3m_pp']
    dimension('monetary_credit',spread is not None or change is not None,[s for s,flag in [('Yield curve inverted',spread is not None and spread<0),('Policy rate rising',change is not None and change>0),('High-yield spread above prior 90th percentile',features['credit_prior90_pctile'] is not None and features['credit_spread_pct']>features['credit_prior90_pctile'])] if flag],
        'Inversion is a term-spread sign, not a recession declaration. Credit threshold is a product-defined historical percentile.')
    vol=features['realized_vol20_annualized_pct'];benchmark=features['market_vol_prior90_pctile'];dd=features['drawdown_252sessions_pct']
    vix=usable.get('^VIX',usable.get('VIXCLS'));features['vix_level']=last(vix)
    features['vix_prior90_pctile']=float(vix.iloc[:-1].tail(2520).quantile(.9)) if vix is not None and len(vix)>=253 else None
    dimension('market',vol is not None or features['vix_prior90_pctile'] is not None,[s for s,flag in [('Realized volatility above prior 90th percentile',vol is not None and benchmark is not None and vol>benchmark),('VIX above prior 90th percentile',features['vix_prior90_pctile'] is not None and features['vix_level']>features['vix_prior90_pctile']),('Equity drawdown exceeds 10%',dd is not None and dd<=-10)] if flag],
        'One equity series avoids redundant index votes; 10% drawdown and 90th percentile are FinPilot descriptive policy assumptions, not validated risk thresholds.')
    available=sum(d['available'] for d in dimensions);flags=sum(d['available'] and d['flagged'] for d in dimensions)
    labels=[s for d in dimensions for s in d['signals']]
    if available<3:status='Insufficient Data'
    elif flags and flags<available:status='Mixed Signals'
    elif flags:status='Multiple pressure signals'
    else:status='No configured pressure signals'
    return {'version':'economic-dimensions-v2','as_of':as_of,'status':status,'labels':labels,
        'dimensions':dimensions,'features':features,'indicators':indicators,'excluded':excluded,'provider_errors':snapshot.get('errors',{}),
        'pressure_breadth_index':round(100*flags/available,2) if available>=4 else None,
        'evidence_quality':{'available_dimensions':available,'total_dimensions':5,'kind':'data coverage, not probability'},
        'method':'Transparent descriptive rules; no learned regime or directional forecast',
        'historical_vintage_required':historical}
