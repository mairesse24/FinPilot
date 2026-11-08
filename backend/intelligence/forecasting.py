"""Recursive spending forecasts plus scheduled cash arithmetic; savings excluded."""
import calendar
import json
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd
from .features import FEATURES, make_features
from .training import MODEL_DIR


def forecast_spending(history, days=30, model_dir=MODEL_DIR, use_calibration=True):
    if type(days) is not int or not 1 <= days <= 90:
        raise ValueError('days must be an integer from 1 to 90')
    if history.customer_id.nunique() != 1 or len(history) < 29:
        raise ValueError('Provide at least 29 consecutive daily observations for one customer')
    h = history.sort_values('date').reset_index(drop=True).copy()
    h['date'] = pd.to_datetime(h.date)
    if h.date.duplicated().any() or not h.date.diff().dropna().eq(pd.Timedelta(days=1)).all():
        raise ValueError('Daily history must be unique and contiguous, including zero spending days')
    if not np.isfinite(h.spending).all() or (h.spending < 0).any():
        raise ValueError('Spending must be finite and nonnegative')
    h = h.tail(125).reset_index(drop=True)
    from .intervals import policy_for, positive_bounds
    calibrated = policy_for(h,model_dir) if use_calibration and len(h)>=90 else None
    path = Path(model_dir)
    metadata = json.loads((path / 'metadata.json').read_text()) if (path / 'metadata.json').exists() else {}
    if metadata and metadata.get('features') != FEATURES:
        raise ValueError('Model feature schema changed. Retrain with python -m backend.intelligence.training')
    mode = metadata.get('serving_model', 'moving_average_28')
    requested_model = mode
    warnings = []
    if calibrated and days>30:
        warnings.append('Positive-spending residual calibration was evaluated only through day 30; later bounds remain uncalibrated.')
    profile = metadata.get('training_history_profile')
    zero_fraction = float((h.spending == 0).mean())
    outside_support = bool(profile and len(h) >= 90 and
        zero_fraction < profile['zero_day_fraction_min']-profile['fallback_margin'])
    if outside_support:
        mode = 'moving_average_28'
        warnings.append('Spending occurs much more frequently than in training data; using an unvalidated rolling-average fallback instead of the synthetic-calendar model.')
    if len(history) < 90:
        warnings.append('Fewer than 90 history days; the calendar-pattern support check is unavailable.')
        mode='moving_average_28'
    boosters = {k: lgb.Booster(model_file=str(path / f'{k}.txt')) for k in ('lower', 'median', 'upper')} if metadata and not outside_support and len(history)>=90 else {}
    points = []
    for step in range(days):
        day = h.date.iloc[-1] + pd.Timedelta(days=1)
        h.loc[len(h)] = {'customer_id': h.customer_id.iloc[0], 'date': day, 'spending': 0.0}
        row = make_features(h).iloc[[-1]]
        if boosters:
            lower, median, upper = sorted(max(0., float(boosters[k].predict(row[FEATURES], num_threads=1)[0])) for k in boosters)
        else:
            median = float(row.mean_28.iloc[0])
            lower, upper = 0., median + 1.28 * float(row.std_28.iloc[0])
        baseline_column = {'seasonal_7': 'lag_7', 'calendar_month': 'calendar_lag_1'}.get(mode, 'mean_28')
        point = median if mode == 'lightgbm' else float(row[baseline_column].iloc[0])
        lower, upper = min(lower, point), max(upper, point)
        if calibrated and step<30:
            q,scale,_ = calibrated
            lower,upper=positive_bounds(lower,upper,point,q,scale)
        points.append({'date': day.date().isoformat(), 'spending': round(point, 2),
                       'lower': round(lower, 2), 'upper': round(upper, 2)})
        h.loc[h.index[-1], 'spending'] = point
    return {'model': mode, 'days': days, 'daily': points,
            'requested_model': requested_model, 'warnings': warnings,
            'support_check': {'outside_training_frequency': outside_support, 'history_zero_day_fraction': round(zero_fraction, 4),
                              'validated': False},
            'point_estimate': 'recursive daily median' if mode == 'lightgbm' else 'recursive baseline',
            'aggregation_note': 'Summed daily medians are a planning total, not an expected total or calibrated quantile of horizon spending.',
            'uncertainty': ('Empirical positive-spending residual band targeting 80% coverage; held-out coverage varies and overall coverage is not nominal 80%' if calibrated else 'Daily empirical 10th/90th quantiles' if boosters else 'Rolling-average plus historical-volatility heuristic') + '; accumulated bounds are stress envelopes, not calibrated balance intervals.',
            'synthetic': True}


def project_cash(customer, spending):
    from .validation import validate_customer
    validate_customer(customer)
    cash = low = high = customer['checking_balance']
    points = []
    savings = customer['savings_balance']
    total_transferred = 0.
    for row in spending['daily']:
        day = pd.Timestamp(row['date'])
        month_end = calendar.monthrange(day.year, day.month)[1]
        due = sum(b['amount'] for b in customer['bills'] if min(b['day'], month_end) == day.day)
        paydays = sorted(set(min(d, month_end) for d in customer['paydays']))
        income = (sum(e['amount'] for e in customer['income_schedule'] if min(e['day'],month_end)==day.day)
                  if 'income_schedule' in customer else customer['monthly_income']/len(paydays) if day.day in paydays else 0.)
        cash_fraction = customer.get('cash_variable_fraction', 1.)
        cash_spend = round(row['spending']*cash_fraction, 2)
        movement = sum(e['amount'] for e in customer.get('cash_movement_schedule',[]) if min(e['day'],month_end)==day.day)
        savings_deposit = customer.get('monthly_savings_transfer', 0.) if day.day == 5 else 0.
        savings += savings_deposit
        cash += income - due - cash_spend - savings_deposit + movement
        low += income - due - round(row['upper']*cash_fraction,2) - savings_deposit + movement
        high += income - due - round(row['lower']*cash_fraction,2) - savings_deposit + movement
        transfer = 0.
        if customer.get('fund_shortfalls_from_savings', False):
            transfer = min(savings, max(0., -cash))
            savings -= transfer
            total_transferred += transfer
            cash += transfer
        # Stress envelopes retain unfunded checking assumptions; savings path is central-case only.
        points.append({**row, 'income': round(income, 2), 'bills': round(due, 2), 'cash_spending':cash_spend,'cash_movement':movement,
                       'balance': round(cash, 2), 'balance_lower': round(low+total_transferred, 2), 'balance_upper': round(high+total_transferred, 2),
                       'savings_balance': round(savings, 2), 'savings_withdrawal': round(transfer, 2),
                       'savings_deposit': round(savings_deposit, 2),
                       'combined_liquid_balance': round(cash+savings, 2)})
    return {**spending, 'daily': points, 'starting_balance': customer['checking_balance'],
            'minimum_balance': min([customer['checking_balance']] + [r['balance'] for r in points]),
            'ending_balance': points[-1]['balance'],
            'minimum_savings': min([customer['savings_balance']] + [r['savings_balance'] for r in points]),
            'ending_savings': points[-1]['savings_balance'],
            'reserve_policy': 'hypothetical_savings_funding' if customer.get('fund_shortfalls_from_savings', False) else 'no_savings_funding',
            'assumptions': customer.get('assumptions', [])}
