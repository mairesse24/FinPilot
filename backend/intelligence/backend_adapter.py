"""Typed adapters for backend-mvp. Existing dictionary/CLI interfaces stay intact.

Use the backend's Decimal schedule projection rather than approximating its weekly
or biweekly events with the legacy monthly dictionary contract.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import math
import os
import pandas as pd


def _meta(profile, source='model', warning=None):
    from app.schemas.common import Meta
    if (any(b.category=='debt_payment' and not b.liability_account_id for b in profile.bills)
        and any(a.min_payment for a in profile.accounts if a.account_type in ('credit_card','loan'))):
        warning = (warning+'; ' if warning else '')+'Unlinked debt bills and account minimums overlap ambiguously; debt burden uses an aggregate floor. Link bills to liability_account_id for exact attribution.'
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
    from app.calc.metrics import checking_variable_transactions
    for tx in checking_variable_transactions(profile):
        if tx.amount < 0 and tx.category in VARIABLE and start <= tx.date <= profile.as_of:
            amounts[tx.date] = amounts.get(tx.date, Decimal(0))-tx.amount
    return pd.DataFrame({'customer_id': profile.user.id, 'date': dates,
                         'spending': [float(amounts.get(d.date(), 0)) for d in dates]})


def _customer(profile):
    from app.calc import metrics
    from app.calc.categories import VARIABLE
    _validate_profile(profile)
    start = profile.as_of-timedelta(days=30)
    spend = sum((-t.amount for t in metrics.checking_variable_transactions(profile)
                 if start < t.date <= profile.as_of), Decimal(0))
    bills = sum((b.amount for _, b in metrics.bill_occurrences(profile, 30)), Decimal(0))
    c = {'customer_id': profile.user.id, 'as_of': profile.as_of.isoformat(),
        'checking_balance': float(metrics.cash_balance(profile)),
        'savings_balance': float(sum((a.balance for a in profile.accounts if a.account_type == 'savings'), Decimal(0))),
        'monthly_income': float(metrics.monthly_income(profile)), 'monthly_variable_spending': float(spend),
        'monthly_debt_payments': float(metrics.monthly_debt_payments(profile)),
        'bills': [{'name': 'scheduled_outflows_next_30_days', 'amount': float(bills), 'day': 1}],
        'paydays': [1], 'safety_buffer': float(profile.user.safety_buffer), 'budget': None}
    try:
        budget = float(os.environ.get('DEFAULT_MONTHLY_BUDGET', '').strip())
    except ValueError:
        budget = 0.
    if not c['budget'] and math.isfinite(budget) and budget > 0:
        c['budget'] = budget
        c.setdefault('assumptions', []).append(f'Demo assumption: monthly variable-spending budget of ${budget:g} (DEFAULT_MONTHLY_BUDGET); not a user-entered budget.')
    return c


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
        meta=_meta(profile, warning='Prototype health score: unavailable components are omitted and weights renormalized. This is not a credit score.'))


def _project(profile, path):
    from app.calc.projection import project_balance
    from app.schemas.forecast import ForecastPoint, ForecastResult, ProjectedLow
    from app.schemas.common import ForecastReliability
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
        assumptions=[f"Variable-spending method: {path['model']}.",
            'Income and bills follow the backend profile schedules using Decimal cash arithmetic.',
            'Backend category vocabulary differs from PNC training data; inference may use a warned baseline fallback.',
            path.get('uncertainty', 'Bounds are uncalibrated stress envelopes, not balance probabilities.'),
            'Synthetic prototype; original engineering-audit findings remain relevant.'], evaluation=None,
        meta=_meta(profile, 'model' if path['model'] == 'lightgbm' else 'baseline', warning).model_copy(update={
            'forecast_reliability':ForecastReliability(
                method=path['model'],status='estimated',validation='unvalidated' if path.get('support_check',{}).get('outside_training_frequency') or path['model']!='lightgbm' else 'synthetic_evaluated',
                reasons=['pattern_shift'] if path.get('support_check',{}).get('outside_training_frequency') else ['synthetic_only'],
                support_check=path.get('support_check',{}))}))


def forecast_profile(profile, days):
    from .forecasting import forecast_spending
    # Calendar support cannot be checked on short history. Use the existing
    # observed-day baseline, not a possibly incompatible calendar-trained model.
    from app.baseline.forecast import forecast as baseline
    if not profile.transactions or len(_history(profile))<90:
        return baseline(profile,days)
    return _project(profile, forecast_spending(_history(profile), days))


def _low_balance_scenario(projected_low, buffer, forecast_daily, as_of):
    from app.schemas.common import SpendingCut
    shortfall = Decimal(str(buffer))-Decimal(str(projected_low))
    if shortfall <= 0 or not forecast_daily:
        return None
    amount = min(Decimal(100000), max(Decimal(50), (shortfall/50).to_integral_value('ROUND_CEILING')*50))
    low_day = min(forecast_daily, key=lambda r: r['balance'])['date']
    days = (pd.Timestamp(low_day).date()-as_of).days
    return SpendingCut(reduction_amount=amount, horizon_days=max(1, min(90, days)))


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
        if a['id'] == 'low_balance':
            scenario = _low_balance_scenario(a['evidence']['projected_low'], a['evidence']['buffer'], raw['daily'], profile.as_of) or scenario
        numbers = {k: v if isinstance(v, (float, int, str)) else json.dumps(v) for k, v in a['evidence'].items() if v is not None}
        result.append(Alert(id=a['event_key'], rule=a['id'], severity={'critical': 'high', 'info': 'low'}.get(a['severity'], a['severity']),
            title=a['id'].replace('_', ' ').title(), cause=a['explanation'], numbers=numbers,
            recommended_action=a.get('guidance', 'Compare the suggested spending scenario while preserving essential payments.'),
            suggested_scenario=scenario))
    if forecast.status in ('abstained','limited_history'):
        result.append(Alert(id=f'forecast_uncertain:{profile.as_of}',rule='forecast_uncertain',severity='medium',
            title='Cash forecast is uncertain',cause=forecast.meta.warning or 'History is incomplete.',numbers={},
            recommended_action='Confirm upcoming income, bills and a spending budget; do not interpret missing history as zero spending.'))
    return result


def simulate_profile(profile, cut):
    from app.baseline.simulate import apply_spending_cut
    from app.schemas.simulate import ScenarioOutcome, SimulationResult
    from .forecasting import forecast_spending
    if not profile.transactions or len(_history(profile))<90:
        from app.baseline.simulate import simulate
        return simulate(profile,cut)
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
                               health_score=health_profile(p).score, alerts=guardian_profile(p, fc), series=fc.series,
                               forecast_reliability=fc.meta.forecast_reliability)
    b, s = outcome(profile, base), outcome(altered, scen)
    return SimulationResult(baseline=b, scenario=s,
        delta={'low_balance_change': round(float(s.projected_low.balance-b.projected_low.balance), 2),
               'end_balance_change': round(float(s.end_balance-b.end_balance), 2),
               'health_score_change': round(s.health_score-b.health_score, 2)},
        meta=base.meta)
