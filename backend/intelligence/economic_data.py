"""Versioned economic snapshots. Requests occur only in the explicit refresh CLI.

An as-of FRED vintage establishes knowledge by a date, NOT exact publication time.
Yahoo adjusted prices are current-revised and are never used for historical PIT tests.
"""
import json
import math
import time
import threading
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / 'data/economic_snapshots'
# frequency, original publisher, age policy in days (product data-quality limits).
CATALOG = {
    'CPIAUCSL': ('monthly','BLS',100), 'CPILFESL': ('monthly','BLS',100),
    'PCEPI': ('monthly','BEA',100), 'UNRATE': ('monthly','BLS',75),
    'ICSA': ('weekly','US Department of Labor',21), 'FEDFUNDS': ('monthly','Federal Reserve Board',75),
    'DGS10': ('daily','Federal Reserve Board',10), 'DGS2': ('daily','Federal Reserve Board',10),
    'T10Y2Y': ('daily','Federal Reserve Bank of St. Louis',10),
    'INDPRO': ('monthly','Federal Reserve Board',100), 'RSAFS': ('monthly','US Census Bureau',100),
    'GDPC1': ('quarterly','BEA',200), 'BAMLH0A0HYM2': ('daily','ICE Data Indices',10),
    'SAHMREALTIME': ('monthly','Claudia Sahm',75),
    'SP500': ('daily','S&P Dow Jones Indices',10), 'VIXCLS': ('daily','CBOE',10),
}
TICKERS = ('^GSPC','^IXIC','^DJI','^VIX','^TNX','SPY','AGG','TLT')
_PACE_LOCK=threading.Lock()
_LAST_REQUEST=0.


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class FredClient:
    def __init__(self,key,client=None,sleep=time.sleep):
        self.key=key;self.client=client or httpx.Client(timeout=20);self.sleep=sleep
        self.network=client is None

    def get(self,path,params):
        if not self.key: raise ValueError('FRED_API_KEY missing; no official vintage request performed')
        status=None
        for attempt in range(3):
            try:
                if self.network:
                    global _LAST_REQUEST
                    with _PACE_LOCK:
                        time.sleep(max(0.,.55-(time.monotonic()-_LAST_REQUEST)))
                        _LAST_REQUEST=time.monotonic()
                r=self.client.get('https://api.stlouisfed.org/fred/'+path,params={**params,'api_key':self.key,'file_type':'json'})
                status=r.status_code
                if r.status_code==429 or r.status_code>=500:
                    if attempt<2:
                        try: delay=min(15,max(1,float(r.headers.get('Retry-After',2**attempt))))
                        except ValueError: delay=2**attempt
                        self.sleep(delay);continue
                r.raise_for_status()
                return r.json()
            except (httpx.HTTPError,ValueError):
                if attempt<2:self.sleep(2**attempt)
        raise ValueError(f'FRED request failed (HTTP {status if status is not None else "unavailable"}) after bounded retries; check key, vintage availability or limits')

    def series(self,identifier,as_of):
        if identifier not in CATALOG:raise ValueError('Unsupported FRED series')
        metadata_body=self.get('series',{'series_id':identifier,'realtime_start':as_of,'realtime_end':as_of})
        if not metadata_body.get('seriess'):raise ValueError('Series metadata unavailable for requested vintage')
        metadata=metadata_body['seriess'][0]
        raw=self.get('series/observations',{'series_id':identifier,'realtime_start':as_of,'realtime_end':as_of,
            'observation_start':'1998-01-01','observation_end':as_of,'limit':100000})
        if raw.get('count',len(raw['observations']))>len(raw['observations']):
            raise ValueError('FRED observation pagination required; refuse truncated history')
        rows=[];missing=0
        for row in raw['observations']:
            if row['value']=='.':missing+=1;continue
            value=float(row['value'])
            if not math.isfinite(value):raise ValueError('Nonfinite FRED observation')
            if row['date']>as_of:raise ValueError('Future observation in FRED vintage')
            rows.append({'date':row['date'],'value':value,'available_on':as_of})
        if len({r['date'] for r in rows})!=len(rows):raise ValueError('Duplicate FRED observations')
        if not rows:raise ValueError('No observations available for requested vintage')
        publication=None
        try:
            first=self.get('series/observations',{'series_id':identifier,'observation_start':rows[-1]['date'],
                'observation_end':rows[-1]['date'],'realtime_start':'1776-07-04','realtime_end':as_of,'output_type':4})
            dates=[r.get('realtime_start') for r in first.get('observations',[]) if r.get('date')==rows[-1]['date']]
            publication=min((d for d in dates if d and '1776-07-04'<d<=as_of),default=None)
        except ValueError:pass # Initial-release dates are not available for every series.
        return {'id':identifier,'source':'FRED/ALFRED official API','publisher':CATALOG[identifier][1],
            'source_url':f'https://fred.stlouisfed.org/series/{identifier}',
            'frequency':metadata['frequency'],'units':metadata['units'],'seasonal_adjustment':metadata['seasonal_adjustment'],
            'title':metadata['title'],'last_updated':metadata.get('last_updated'),
            'release_timestamp':None,'initial_release_date':publication,
            'availability_basis':'Available in the official FRED vintage on knowledge_date; initial release date queried separately where available, exact publication time unknown',
            'knowledge_date':as_of,'retrieved_at':utc_now(),'point_in_time':True,'missing_rows':missing,'observations':rows}

    def close(self):self.client.close()


def yahoo_series(ticker,as_of):
    if ticker not in TICKERS:raise ValueError('Unsupported market ticker')
    import yfinance as yf
    # Only completed prior sessions. Do not consume a potentially partial as-of day.
    for attempt in range(3):
        try:
            frame=yf.Ticker(ticker).history(start='2006-01-01',end=as_of,auto_adjust=True,actions=False,raise_errors=True,timeout=20)
            if frame.empty:raise ValueError('No Yahoo observations')
            rows=[]
            for stamp,value in frame.Close.items():
                value=float(value)
                if not math.isfinite(value) or value<=0:raise ValueError('Invalid market close')
                rows.append({'date':stamp.date().isoformat(),'value':value,'available_on':None})
            return {'id':ticker,'source':'Yahoo Finance via yfinance; research/personal use',
                'source_url':'https://finance.yahoo.com/quote/'+ticker.replace('^','%5E')+'/',
                'frequency':'daily market session','units':'adjusted price; ^TNX is a yield proxy, ^VIX an index',
                'seasonal_adjustment':'not applicable','retrieved_at':utc_now(),'knowledge_date':as_of,
                'point_in_time':False,'release_timestamp':None,'adjusted':True,'observations':rows,
                'availability_basis':'Current adjusted history; historical adjustment vintages unverified'}
        except Exception:
            if attempt<2:time.sleep(2**attempt)
    raise ValueError('Yahoo data unavailable after bounded retries; no replacement values fabricated')


def refresh(as_of,key,include_market=True):
    if date.fromisoformat(as_of)>datetime.now(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/Chicago')).date():
        raise ValueError('Cannot request a future economic snapshot')
    from concurrent.futures import ThreadPoolExecutor
    def fetch(identifier):
        client=FredClient(key)
        try:return identifier,client.series(identifier,as_of),None
        except ValueError as exc:return identifier,None,str(exc)
        except (KeyError,TypeError,IndexError):return identifier,None,'Provider schema unavailable or invalid; no values substituted'
        finally:client.close()
    snapshot={'as_of':as_of,'retrieved_at':utc_now(),'series':{},'errors':{},'synthetic':False}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for identifier,series,error in pool.map(fetch,CATALOG):
            if series:snapshot['series'][identifier]=series
            else:snapshot['errors'][identifier]=error
    if include_market:
        # Yahoo has no verified adjustment vintages. Only refresh for today's display.
        today=datetime.now(__import__('zoneinfo').ZoneInfo('America/Chicago')).date().isoformat()
        if as_of==today:
            for ticker in TICKERS:
                try:snapshot['series'][ticker]=yahoo_series(ticker,as_of)
                except ValueError as exc:snapshot['errors'][ticker]=str(exc)
        else:snapshot['errors']['Yahoo']='Historical adjusted-price vintages unavailable; skipped for PIT replay'
    CACHE.mkdir(parents=True,exist_ok=True)
    version=as_of+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'
    (CACHE/version).write_text(json.dumps(snapshot,indent=2,allow_nan=False))
    # Latest pointer is local only, no network at application request time.
    (CACHE/'latest.json').write_text(json.dumps(snapshot,allow_nan=False))
    return snapshot


def cached(as_of=None):
    def read(path):
        try:
            value=json.loads(path.read_text())
            if not isinstance(value.get('series'),dict):raise ValueError('Invalid cache')
            return value
        except (ValueError,OSError,TypeError,AttributeError):
            return {'as_of':as_of,'series':{},'errors':{'cache':'Cache unavailable or invalid; refresh explicitly'},'synthetic':False}
    if as_of:
        paths=sorted(CACHE.glob(as_of+'_*.json'))
        if not paths:return {'as_of':as_of,'series':{},'errors':{'cache':'No matching vintage cached'},'synthetic':False}
        return read(paths[-1])
    path=CACHE/'latest.json'
    return read(path) if path.exists() else {'series':{},'errors':{'cache':'Run python -m scripts.refresh_intelligence'},'synthetic':False}
