"""Evaluate household macro forecasts separately from S&P 500 direction research."""
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import pandas as pd
from backend.intelligence.data import ROOT, load_customer
from backend.intelligence.economic_outlook import research_outlook
from backend.intelligence.economic_pressure import economic_pressure


def indicator_snapshot(raw, as_of):
    available = raw.loc[raw.index <= pd.Timestamp(as_of)]
    # Partial-month monthly observations are actual published values in current FRED cache,
    # but their vintage availability is not verified for historical dates.
    cpi = available.CPIAUCSL.dropna().resample('MS').last()
    inflation_series = ((cpi/cpi.shift(12))-1)*100
    series = {'inflation_yoy_pct': inflation_series.dropna(), 'unemployment_pct': available.UNRATE.dropna(),
              'policy_rate_pct': available.FEDFUNDS.dropna()}
    if any(s.empty for s in series.values()):
        raise ValueError('Insufficient indicator observations')
    snapshot = {'as_of': as_of, **{k: float(s.iloc[-1]) for k, s in series.items()},
            'observation_dates': {k: str(s.index[-1].date()) for k, s in series.items()},
            'source': 'FRED current-revised cache; historical vintage availability unverified'}
    unemployment = available.UNRATE.dropna().resample('MS').last()
    change = (unemployment-unemployment.shift(3)).dropna()
    if not change.empty:
        snapshot['unemployment_change_3m_pp'] = round(float(change.iloc[-1]), 6)
        snapshot['observation_dates']['unemployment_change_3m_pp'] = str(change.index[-1].date())
    if 'SP500' in available:
        prices = available.SP500.dropna()
        if (prices <= 0).any():
            raise ValueError('Market prices must be positive')
        if not prices.empty:
            stamp = prices.index[-1]
            prior = prices.loc[prices.index <= stamp-pd.DateOffset(months=3)]
            if not prior.empty:
                snapshot['market_return_3m_pct'] = float((prices.iloc[-1]/prior.iloc[-1]-1)*100)
                snapshot['observation_dates']['market_return_3m_pct'] = str(stamp.date())
            if len(prices) >= 252:
                snapshot['market_drawdown_252d_pct'] = float((prices.iloc[-1]/prices.iloc[-252:].max()-1)*100)
                snapshot['observation_dates']['market_drawdown_252d_pct'] = str(stamp.date())
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', default=datetime.now(ZoneInfo('America/Chicago')).date().isoformat())
    parser.add_argument('--customer', default='C002')
    args = parser.parse_args()
    cache = ROOT / 'data/economy/fred.csv'
    if not cache.exists():
        parser.error('No FRED cache. First run: python -m scripts.fetch_economy')
    raw = pd.read_csv(cache, index_col='date', parse_dates=True)
    report = research_outlook(raw, args.as_of)
    report['indicators'] = indicator_snapshot(raw, args.as_of)
    report['customer_pressure'] = economic_pressure(load_customer(args.customer), report['indicators'])
    report['provenance'] = json.loads((cache.parent / 'provenance.json').read_text(encoding='utf-8'))
    destination = ROOT / 'artifacts/reports/economic-outlook.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
