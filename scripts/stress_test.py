"""CSV-driven behavioral stress suite, distinct from statistical model backtesting."""
import argparse
import csv
from datetime import date, timedelta
import json
from pathlib import Path
import numpy as np
import pandas as pd
from backend.intelligence.data import ROOT, load_daily
from backend.intelligence.forecasting import forecast_spending
from backend.intelligence.service import analyze_with_spending
from backend.intelligence.simulator import simulate

AS_OF = '2026-10-31'
CUSTOMER_FIELDS = ('checking_balance', 'savings_balance', 'monthly_income', 'monthly_variable_spending',
    'monthly_debt_payments', 'budget', 'savings_floor', 'variable_rate_debt_balance',
    'high_interest_debt_balance', 'equity_exposure', 'planned_equity_withdrawal_90d')
INDICATORS = ('inflation_yoy_pct', 'unemployment_pct', 'unemployment_change_3m_pp', 'policy_rate_pct',
              'market_return_3m_pct', 'market_drawdown_252d_pct')


def make_history(pattern, original):
    h = original.copy().reset_index(drop=True)
    h['customer_id'] = 'STRESS-HISTORY'
    rng = np.random.default_rng(42)
    if pattern == 'zero':
        h['spending'] = 0.
    elif pattern == 'irregular':
        h['spending'] = np.where(rng.random(len(h)) < .6, rng.lognormal(3.5, .8, len(h)), 0).round(2)
    elif pattern == 'surge':
        h.loc[h.index[-28:], 'spending'] *= 3
    elif pattern == 'one_off_spike':
        h.loc[h.index[-1], 'spending'] += 5000
    elif pattern == 'short':
        h = h.tail(28)
    elif pattern == 'gap':
        h = h.drop(h.index[-10])
    elif pattern == 'duplicate':
        h = pd.concat([h, h.iloc[[-1]]], ignore_index=True)
    elif pattern == 'nan':
        h.loc[h.index[-1], 'spending'] = np.nan
    elif pattern == 'negative':
        h.loc[h.index[-1], 'spending'] = -1
    elif pattern != 'pnc':
        raise ValueError('Unknown stress history pattern')
    return h


def run_case(row, original, cache, economic_history=None):
    case_id = row['case_id']
    result = {'case_id': case_id, 'engine': row['engine'], 'pattern': row['pattern'], 'passed': False,
              'description': row['description'], 'failures': [], 'simulations': []}
    expected_error = row['expect_error'] == '1'
    try:
        if row['engine'] == 'research':
            from backend.intelligence.economic_outlook import research_outlook
            if economic_history is None:
                raise RuntimeError('FRED research cache missing; run python -m scripts.fetch_economy')
            raw = economic_history.loc[economic_history.index <= pd.Timestamp(AS_OF)].copy()
            pattern = row['pattern']
            if pattern in ('inflation_spike', 'labor_shock', 'rate_hike'):
                column = {'inflation_spike': 'CPIAUCSL', 'labor_shock': 'UNRATE', 'rate_hike': 'FEDFUNDS'}[pattern]
                affected = raw[column].dropna().index[-3:]
                if pattern == 'inflation_spike':
                    raw.loc[affected, column] *= 1.1
                else:
                    raw.loc[affected, column] += 2
            elif pattern == 'market_crash':
                affected = raw.SP500.dropna().index[-21:]
                raw.loc[affected, 'SP500'] *= np.linspace(1, .7, len(affected))
            elif pattern == 'missing_month':
                raw = raw.loc[raw.index.to_period('M') != pd.Period('2026-08')]
            elif pattern == 'short_history':
                raw = raw.loc[raw.index >= pd.Timestamp(AS_OF)-pd.DateOffset(months=6)]
            elif pattern != 'base':
                raise ValueError('Unknown research pattern')
            research = research_outlook(raw, AS_OF)
            result['research'] = research
            result['market_up_probability'] = research['market']['experimental_up_probability']
            result['inflation_estimate'] = research['household']['next_inflation']['ridge_estimate_pct']
            result['unemployment_estimate'] = research['household']['next_unemployment']['ridge_estimate_pct']
            result['conditions'] = {'economy': {'label': 'not_applicable'}, 'market': {'label': 'research_abstains'}}
            result['alerts'] = []
            if research['market']['direction'] != 'abstain' or research['point_in_time_validated']:
                result['failures'].append('Research output incorrectly releases a validated directional signal')
            if expected_error:
                result['failures'].append('Expected insufficient-history rejection')
            json.dumps(result, allow_nan=False)
            result['passed'] = not result['failures']
            return result
        customer = {'customer_id': case_id, 'as_of': AS_OF, 'paydays': [1, 15], 'safety_buffer': 500.,
                    **{k: float(row[k]) for k in CUSTOMER_FIELDS},
                    'fund_shortfalls_from_savings': row['fund_shortfalls_from_savings'] == '1',
                    'bills': [{'name': 'combined_scheduled_bills', 'amount': float(row['bill_amount']), 'day': int(row['bill_day'])}]}
        indicators = None
        if row['include_indicators'] == '1':
            stamp = (date.fromisoformat(AS_OF)-timedelta(days=int(row['indicator_age_days']))).isoformat()
            indicators = {'as_of': AS_OF, **{k: float(row[k]) for k in INDICATORS},
                          'observation_dates': {k: stamp for k in INDICATORS}, 'source': 'HYPOTHETICAL CSV STRESS FIXTURE'}
        days = int(row['days'])
        if row['engine'] == 'ml':
            key = (row['pattern'], days)
            h = make_history(row['pattern'], original)
            if key not in cache:
                cache[key] = forecast_spending(h, days)
            path = cache[key]
            result['history_diagnostics'] = {'source_customer': 'C026', 'transformation': row['pattern'],
                'mean_daily_spending_last_28_days': round(float(h.spending.iloc[-28:].mean()), 2),
                'maximum_daily_spending': round(float(h.spending.max()), 2),
                'zero_day_fraction': round(float((h.spending == 0).mean()), 4)}
        elif row['engine'] == 'controlled':
            amount = float(row['daily_spending'])
            path = {'model': 'controlled_known_spending_fixture_NOT_ML', 'days': days, 'daily': [
                {'date': d.date().isoformat(), 'spending': amount, 'lower': amount, 'upper': amount}
                for d in pd.date_range('2026-11-01', periods=days)]}
        else:
            raise ValueError('Unknown engine')
        analysis = analyze_with_spending(customer, path, indicators)
        if expected_error:
            result['failures'].append('Expected input rejection, but analysis accepted it')
        codes = {a['id'] for a in analysis['guardian']}
        for code in filter(None, row['required_alerts'].split('|')):
            if code not in codes:
                result['failures'].append(f'Missing required alert: {code}')
        for code in filter(None, row['forbidden_alerts'].split('|')):
            if code in codes:
                result['failures'].append(f'Unexpected alert: {code}')
        conditions = analysis['economy']['conditions']
        for label in ('economy', 'market'):
            if conditions[label]['label'] != row[f'expected_{label}']:
                result['failures'].append(f'Wrong {label} label: {conditions[label]["label"]}')
        fc = analysis['forecast']
        for point in fc['daily']:
            if not point['balance_lower'] <= point['balance'] <= point['balance_upper']:
                result['failures'].append('Balance outside stress envelope')
            if point['savings_balance'] < 0:
                result['failures'].append('Negative savings')
        # Execute every offered scenario; record whether it actually improves checking.
        for alert in analysis['guardian']:
            if alert['suggested_simulation']:
                comparison = simulate(customer, path, alert['suggested_simulation'], indicators)
                result['simulations'].append({'alert_id': alert['id'], 'scenario': alert['suggested_simulation'],
                    'ending_checking_change': comparison['ending_balance_change'],
                    'minimum_checking_change': round(comparison['after']['forecast']['minimum_balance']-comparison['before']['forecast']['minimum_balance'], 2),
                    'note': 'Stress scenarios may worsen balances; this is not an automatic improvement recommendation.'})
        result.update(analysis=analysis, conditions=conditions, alerts=analysis['guardian'],
            forecast_warnings=path.get('warnings', []),
            total_spending=round(sum(p['spending'] for p in fc['daily']), 2), ending_checking=fc['ending_balance'],
            minimum_checking=fc['minimum_balance'], ending_savings=fc['ending_savings'], serving_model=path['model'])
        json.dumps(result, allow_nan=False)
    except ValueError as error:
        result['error'] = str(error)
        if not expected_error:
            result['failures'].append(f'Unexpected ValueError: {error}')
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
        result['failures'].append('Unexpected runtime failure')
    result['passed'] = not result['failures']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, default=ROOT / 'data/synthetic/stress-cases.csv')
    args = parser.parse_args()
    if not args.cases.exists():
        parser.error('Run python -m scripts.generate_stress_cases first')
    with args.cases.open(newline='', encoding='utf-8-sig') as handle:
        cases = list(csv.DictReader(handle))
    daily = load_daily()
    original = daily[daily.customer_id == 'C026']
    economic_path = ROOT / 'data/economy/fred.csv'
    economic_history = pd.read_csv(economic_path, index_col='date', parse_dates=True) if economic_path.exists() else None
    cache, results = {}, []
    for row in cases:
        result = run_case(row, original, cache, economic_history)
        results.append(result)
        print(f"{'PASS' if result['passed'] else 'FAIL'} {row['case_id']}: "
              + (result.get('error') or ('research sensitivity only; not the alert engine' if 'research' in result else '')
                 or ', '.join(a['id'] for a in result.get('alerts', [])) or 'no alerts'), flush=True)
        if 'research' in result:
            print(f"  Research response: inflation={result['inflation_estimate']}%, unemployment={result['unemployment_estimate']}%, uncalibrated P(up)={result['market_up_probability']}; direction=abstain", flush=True)
        for warning in result.get('forecast_warnings', []):
            print(f'  WARNING: {warning}', flush=True)
        for failure in result['failures']:
            print(f'  {failure}', flush=True)
    folder = ROOT / 'artifacts/reports'
    folder.mkdir(parents=True, exist_ok=True)
    report = {'method': 'Synthetic behavioral stress tests. Passing expectations is NOT measured prediction accuracy.',
              'cases': len(results), 'passed': sum(r['passed'] for r in results), 'results': results}
    pnc = {int(r['case_id'].split('_')[-1]): r for r in results if r['case_id'] in ('ml_pnc_7', 'ml_pnc_30', 'ml_pnc_90')}
    prefix_ok = bool(len(pnc) == 3 and all(pnc[n].get('analysis', {}).get('forecast', {}).get('daily') ==
        pnc[90].get('analysis', {}).get('forecast', {}).get('daily', [])[:n] for n in (7, 30)))
    report['cross_case_checks'] = {'ml_horizons_share_identical_prefixes': prefix_ok}
    reference = pnc.get(90, {}).get('total_spending')
    for r in results:
        if r['engine'] == 'ml' and 'analysis' in r and r['analysis']['forecast']['days'] == 90:
            r['same_horizon_pnc_total'] = reference
            r['change_from_pnc_total'] = round(r['total_spending']-reference, 2) if reference is not None else None
    (folder / 'stress-results.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    fields = ['case_id', 'engine', 'pattern', 'passed', 'economy', 'market', 'alerts', 'total_spending',
              'serving_model', 'ending_checking', 'minimum_checking', 'ending_savings', 'change_from_pnc_total',
              'inflation_estimate', 'unemployment_estimate', 'market_up_probability', 'error', 'failures']
    fields.append('forecast_warnings')
    with (folder / 'stress-results.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, '') for k in fields} | {
                'economy': r.get('conditions', {}).get('economy', {}).get('label', ''),
                'market': r.get('conditions', {}).get('market', {}).get('label', ''),
                'alerts': '|'.join(a['id'] for a in r.get('alerts', [])), 'failures': '|'.join(r['failures'])})
    lines = ['# FinPilot behavioral stress results', '', report['method'], '',
             f"Cases: {report['passed']}/{report['cases']} passed. Horizon-prefix check: {'PASS' if prefix_ok else 'FAIL'}.", '',
             'Controlled cases feed known scenario spending into the rules. ML cases load saved LightGBM models. Research cases refit the economic algorithms on deliberately modified FRED histories and retain abstention; their predictions are hypothetical sensitivity outputs.', '',
             '| Case | Engine | Result | Economy / market | Forecast spending | Alerts or expected rejection |',
             '| --- | --- | --- | --- | ---: | --- |']
    for r in results:
        conditions = r.get('conditions', {})
        labels = f"{conditions.get('economy', {}).get('label', '')} / {conditions.get('market', {}).get('label', '')}"
        alerts = ', '.join(a['id'] for a in r.get('alerts', [])) or r.get('error', 'none')
        lines.append(f"| {r['case_id']} | {r['engine']} | {'PASS' if r['passed'] else 'FAIL'} | {labels} | {r.get('total_spending', '')} | {alerts} |")
    lines.extend(['', '## Actual model sensitivity outputs', '',
        '| ML history | Serving method | 90-day spending | Change from PNC history forecast |', '| --- | --- | ---: | ---: |'])
    for r in results:
        if 'same_horizon_pnc_total' in r:
            lines.append(f"| {r['pattern']} | {r['serving_model']} | {r['total_spending']} | {r['change_from_pnc_total']} |")
            for warning in r.get('forecast_warnings', []):
                lines.append(f"| {r['case_id']} warning | {warning} | | |")
    lines.extend(['', '| Economic history variant | Inflation estimate % | Unemployment estimate % | Uncalibrated P(up) |',
                  '| --- | ---: | ---: | ---: |'])
    for r in results:
        if 'research' in r:
            lines.append(f"| {r['pattern']} | {r['inflation_estimate']} | {r['unemployment_estimate']} | {r['market_up_probability']} |")
    lines.extend(['', '## Alert guidance and actual scenario responses', ''])
    for r in results:
        if not r.get('alerts'):
            continue
        lines.extend([f"### {r['case_id']}", ''])
        for alert in r['alerts']:
            lines.append(f"- **{alert['id']}**: {alert.get('guidance', alert['explanation'])}")
            if alert.get('tradeoff'):
                lines.append(f"  Tradeoff: {alert['tradeoff']}")
        for comparison in r['simulations']:
            lines.append(f"- Tested `{json.dumps(comparison['scenario'])}`: ending checking changes by ${comparison['ending_checking_change']:,.2f}; minimum checking changes by ${comparison['minimum_checking_change']:,.2f}.")
        lines.append('')
    (folder / 'stress-results.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(f"\n{report['passed']}/{report['cases']} passed. Reports: {folder / 'stress-results.csv'} and stress-results.json")
    print(f"ML horizon prefix consistency: {'PASS' if prefix_ok else 'FAIL'}. Readable report: {folder / 'stress-results.md'}")
    if report['passed'] != report['cases'] or not prefix_ok:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
