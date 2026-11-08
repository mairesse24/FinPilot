"""Member 2 can call analyze() inside authenticated FastAPI routes."""
from datetime import date, timedelta
from .validation import validate_customer
from .forecasting import forecast_spending, project_cash
from .health_score import health_score
from .guardian import detect_risks
from .economic_pressure import economic_pressure


def analyze(customer, history, days=30, indicators=None):
    validate_customer(customer)
    if set(history.customer_id.unique()) != {customer['customer_id']}:
        raise ValueError('History must belong to the supplied customer')
    if str(history.date.max().date()) != customer['as_of']:
        raise ValueError('History must end on customer as_of date')
    spending = forecast_spending(history, days)
    return analyze_with_spending(customer, spending, indicators)


def analyze_with_spending(customer, spending, indicators=None):
    validate_customer(customer)
    if indicators and date.fromisoformat(indicators['as_of']) > date.fromisoformat(customer['as_of']):
        raise ValueError('Economic snapshot cannot postdate customer as_of; use aligned snapshots')
    expected = date.fromisoformat(customer['as_of']) + timedelta(days=1)
    if not spending['daily']:
        raise ValueError('Spending path cannot be empty')
    for row in spending['daily']:
        if row['date'] != expected.isoformat():
            raise ValueError('Forecast must start after as_of and contain consecutive dates')
        from .validation import number
        for field in ('lower', 'spending', 'upper'):
            number(row[field], field)
        if not row['lower'] <= row['spending'] <= row['upper']:
            raise ValueError('Forecast bounds must bracket spending')
        expected += timedelta(days=1)
    forecast = project_cash(customer, spending)
    health = health_score(customer)
    economy = economic_pressure(customer, indicators)
    return {'customer_id': customer['customer_id'], 'as_of': customer['as_of'], 'synthetic': True,
            'health': health, 'forecast': forecast, 'economy': economy,
            'guardian': detect_risks(customer, forecast, health, economy)}


def analyze_horizons(customer, history, horizons=(7, 30, 90), indicators=None):
    """One recursive path, consistently truncated for each requested horizon."""
    if not horizons or any(type(n) is not int or not 1 <= n <= 90 for n in horizons):
        raise ValueError('horizons must contain integers 1..90')
    longest = analyze(customer, history, max(horizons), indicators)
    spending = longest['forecast']
    return {str(n): analyze_with_spending(customer, {**spending, 'days': n, 'daily': spending['daily'][:n]}, indicators)
            for n in sorted(set(horizons))}
