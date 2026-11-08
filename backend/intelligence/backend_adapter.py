"""Typed adapters for backend-mvp. Existing dictionary/CLI interfaces stay intact.

Use the backend's Decimal schedule projection rather than approximating its weekly
or biweekly events with the legacy monthly dictionary contract.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import pandas as pd


def _meta(profile, source='model', warning=None):
    from app.schemas.common import Meta
    return Meta(source=source, as_of=profile.as_of, generated_at=datetime.now(timezone.utc), warning=warning)


def _validate_profile(profile):
    uid = profile.user.id
    ids = [a.id for a in profile.accounts]
    if len(ids) != len(set(ids)) or any(a.user_id != uid for a in profile.accounts):
        raise ValueError('Accounts must be unique and owned by profile user')
    tx_ids = [t.id for t in profile.transactions]
    if len(tx_ids) != len(set(tx_ids)) or any(t.account_id not in ids for t in profile.transactions):
        raise ValueError('Transactions must be unique and belong to profile accounts')
    if any(t.date > profile.as_of for t in profile.transactions):
        raise ValueError('Future transactions are not historical features')
    if any(x.user_id != uid for x in [*profile.bills, *profile.income_sources]):
        raise ValueError('Schedules must belong to profile user')


def _history(profile):
    from app.calc.categories import VARIABLE
    _validate_profile(profile)
    if not profile.transactions:
        raise ValueError('ML requires observed history; use backend baseline for an empty profile')
    start = max(min(t.date for t in profile.transactions), profile.as_of-timedelta(days=179))
    dates = pd.date_range(start, profile.as_of)
    amounts = {}
    for tx in profile.transactions:
        if tx.amount < 0 and tx.category in VARIABLE and start <= tx.date <= profile.as_of:
            amounts[tx.date] = amounts.get(tx.date, Decimal(0))-tx.amount
    return pd.DataFrame({'customer_id': profile.user.id, 'date': dates,
                         'spending': [float(amounts.get(d.date(), 0)) for d in dates]})


def _customer(profile):
    from app.calc import metrics
    from app.calc.categories import VARIABLE
    _validate_profile(profile)
    start = profile.as_of-timedelta(days=30)
    spend = sum((-t.amount for t in profile.transactions if start < t.date <= profile.as_of
                 and t.amount < 0 and t.category in VARIABLE), Decimal(0))
    bills = sum((b.amount for _, b in metrics.bill_occurrences(profile, 30)), Decimal(0))
    return {'customer_id': profile.user.id, 'as_of': profile.as_of.isoformat(),
        'checking_balance': float(metrics.cash_balance(profile)),
        'savings_balance': float(sum((a.balance for a in profile.accounts if a.account_type == 'savings'), Decimal(0))),
        'monthly_income': float(metrics.monthly_income(profile)), 'monthly_variable_spending': float(spend),
        'monthly_debt_payments': float(metrics.monthly_debt_payments(profile)),
        'bills': [{'name': 'scheduled_outflows_next_30_days', 'amount': float(bills), 'day': 1}],
        'paydays': [1], 'safety_buffer': float(profile.user.safety_buffer), 'budget': None}


def health_profile(profile):
    from .health_score import health_score
    from app.schemas.health import ComponentScore, HealthResult
    raw = health_score(_customer(profile))
    available = [c for c in raw['components'] if c['score'] is not None]
    keys = {'cash_flow_stability': 'cash_flow', 'emergency_savings': 'emergency', 'debt_management': 'debt',
            'spending_discipline': 'discipline', 'payment_readiness': 'readiness'}
    components = [ComponentScore(key=keys[c['name']], name=c['name'].replace('_', ' ').title(),
        weight=c['weight']/raw['observed_weight']*100, score=c['score'],
        metrics={'value': c['metric']}, explanation=c['formula']) for c in available]
    return HealthResult(score=raw['score'], components=components,
        strengths=[f'{c.name}: {c.score:g}/100' for c in components if c.score >= 75],
        weaknesses=[f'{c.name}: {c.score:g}/100' for c in components if c.score < 50],
        meta=_meta(profile, warning='Member 3 prototype score; unavailable components are omitted and weights renormalized. See engineering audit.'))


def _project(profile, path):
    from app.calc.projection import project_balance
    from app.schemas.forecast import ForecastPoint, ForecastResult, ProjectedLow
    rows = {pd.Timestamp(r['date']).date(): r for r in path['daily']}
    days = len(rows)
    quantize = lambda value: value.quantize(Decimal('.01'))
    central = project_balance(profile, days, lambda d: Decimal(str(rows[d]['spending'])))
    lower = project_balance(profile, days, lambda d: Decimal(str(rows[d]['upper'])))
    upper = project_balance(profile, days, lambda d: Decimal(str(rows[d]['lower'])))
    points = [ForecastPoint(date=p.date, projected_balance=quantize(p.balance), low=quantize(lo.balance),
              high=quantize(hi.balance), predicted_spend=quantize(p.spend))
              for p, lo, hi in zip(central, lower, upper)]
    low = min(points, key=lambda p: p.projected_balance) if points else None
    warning = '; '.join(path.get('warnings', [])) or None
    return ForecastResult(days=days, series=points,
        projected_low=ProjectedLow(date=low.date, balance=low.projected_balance) if low else None,
        safety_buffer=profile.user.safety_buffer, shortfall=bool(low and low.projected_balance < profile.user.safety_buffer),
        assumptions=[f"Member 3 variable-spending method: {path['model']}.",
            'Income and bills follow the backend profile schedules using Decimal cash arithmetic.',
            'Backend category vocabulary differs from PNC training data; inference may use a warned baseline fallback.',
            path.get('uncertainty', 'Bounds are uncalibrated stress envelopes, not balance probabilities.'),
            'Synthetic prototype; original engineering-audit findings remain relevant.'], evaluation=None,
        meta=_meta(profile, 'model' if path['model'] == 'lightgbm' else 'baseline', warning))


def forecast_profile(profile, days):
    from .forecasting import forecast_spending
    return _project(profile, forecast_spending(_history(profile), days))


def guardian_profile(profile, forecast):
    from app.calc import metrics
    from app.schemas.guardian import Alert
    from app.schemas.common import SpendingCut
    from .guardian import detect_risks
    from .health_score import health_score
    customer = _customer(profile)
    scheduled = {}
    for day, bill in metrics.bill_occurrences(profile, forecast.days):
        scheduled[day] = scheduled.get(day, Decimal(0))+bill.amount
    raw = {'minimum_balance': min([customer['checking_balance']]+[float(p.projected_balance) for p in forecast.series]),
        'minimum_savings': customer['savings_balance'], 'reserve_policy': 'backend_no_implicit_transfer',
        'daily': [{'date': p.date.isoformat(), 'balance': float(p.projected_balance),
                   'spending': float(p.predicted_spend), 'savings_balance': customer['savings_balance'],
                   'bills': float(scheduled.get(p.date, 0))} for p in forecast.series]}
    alerts = detect_risks(customer, raw, health_score(customer))
    result = []
    for a in alerts:
        cut = a['suggested_simulation'].get('monthly_spending_cut')
        scenario = SpendingCut(reduction_amount=Decimal(str(cut))*forecast.days/30, horizon_days=forecast.days) if cut else None
        numbers = {k: v if isinstance(v, (float, int, str)) else json.dumps(v) for k, v in a['evidence'].items() if v is not None}
        result.append(Alert(id=a['event_key'], rule=a['id'], severity={'critical': 'high', 'info': 'low'}.get(a['severity'], a['severity']),
            title=a['id'].replace('_', ' ').title(), cause=a['explanation'], numbers=numbers,
            recommended_action=a.get('guidance', 'Compare the suggested spending scenario while preserving essential payments.'),
            suggested_scenario=scenario))
    return result


def simulate_profile(profile, cut):
    from app.baseline.simulate import apply_spending_cut
    from app.schemas.simulate import ScenarioOutcome, SimulationResult
    from .forecasting import forecast_spending
    if cut.category is not None:
        raise ValueError('Category-specific forecast cuts are not implemented by this adapter')
    days = max(30, cut.horizon_days)
    path = forecast_spending(_history(profile), days)
    base = _project(profile, path)
    scenario_path = deepcopy(path)
    per_day = cut.reduction_amount/cut.horizon_days
    for row in scenario_path['daily'][:cut.horizon_days]:
        spend = Decimal(str(row['spending']))
        new_spend = max(Decimal(0), spend-per_day)
        factor = float(new_spend/spend) if spend else 1.
        row['spending'] = float(new_spend)
        row['lower'] *= factor
        row['upper'] *= factor
    altered = apply_spending_cut(profile, cut)
    scen = _project(altered, scenario_path)
    def outcome(p, fc):
        return ScenarioOutcome(projected_low=fc.projected_low, end_balance=fc.series[-1].projected_balance,
                               health_score=health_profile(p).score, alerts=guardian_profile(p, fc), series=fc.series)
    b, s = outcome(profile, base), outcome(altered, scen)
    return SimulationResult(baseline=b, scenario=s,
        delta={'low_balance_change': round(float(s.projected_low.balance-b.projected_low.balance), 2),
               'end_balance_change': round(float(s.end_balance-b.end_balance), 2),
               'health_score_change': round(s.health_score-b.health_score, 2)},
        meta=_meta(profile, base.meta.source, base.meta.warning))
