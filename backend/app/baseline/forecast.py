"""Baseline cash-flow forecast: weekday-mean variable spend + known bills/income."""
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable

from app.calc.categories import VARIABLE
from app.calc.metrics import cash_balance, checking_variable_transactions
from app.calc.models import FinancialProfile
from app.calc.projection import project_balance
from app.schemas.common import Meta, ForecastReliability
from app.schemas.forecast import ForecastPoint, ForecastResult, ProjectedLow

ZERO = Decimal("0")
CENTS = Decimal("0.01")
Z80 = 1.28


def _daily_variable(p: FinancialProfile, window: int = 90) -> dict[date, Decimal]:
    if p.transactions:
        window = min(window, max(1, (p.as_of-min(t.date for t in p.transactions)).days+1))
    else:
        return {}
    start = p.as_of - timedelta(days=window)
    out = {p.as_of - timedelta(days=i): ZERO for i in range(window)}
    for t in checking_variable_transactions(p):
        if start < t.date <= p.as_of and t.amount < 0 and t.category in VARIABLE:
            out[t.date] += -t.amount
    return out


def weekday_spend_profile(p: FinancialProfile) -> tuple[dict[int, Decimal], float]:
    """Mean daily VARIABLE outflow per weekday (trailing 90 days) and sigma of daily spend."""
    daily = _daily_variable(p)
    if not daily:
        return {w: ZERO for w in range(7)}, 0.
    if len(daily) < 29:
        mean = sum(daily.values(), ZERO)/len(daily)
        return {w: mean for w in range(7)}, float(mean)
    sums = {w: ZERO for w in range(7)}
    counts = {w: 0 for w in range(7)}
    for d, v in daily.items():
        sums[d.weekday()] += v
        counts[d.weekday()] += 1
    means = {w: (sums[w] / counts[w] if counts[w] else ZERO) for w in range(7)}
    vals = [float(v) for v in daily.values()]
    mu = sum(vals) / len(vals)
    sigma = math.sqrt(sum((x - mu) ** 2 for x in vals) / len(vals))
    return means, sigma


def forecast(p: FinancialProfile, days: int,
             daily_spend_override: Callable[[date], Decimal] | None = None) -> ForecastResult:
    observed_days = len(_daily_variable(p))
    if not observed_days or (observed_days<29 and not any(_daily_variable(p).values())):
        return ForecastResult(days=days,series=[],projected_low=None,safety_buffer=p.user.safety_buffer,
            shortfall=cash_balance(p)<p.user.safety_buffer, status="abstained",
            assumptions=["No observed history: variable spending and future checking balances cannot be estimated."],
            meta=Meta(source="baseline",as_of=p.as_of,generated_at=datetime.now(timezone.utc),
                      warning="Forecast abstained: provide transaction history or a confirmed spending budget.",
                      forecast_reliability=ForecastReliability(method='none',status='abstained',validation='unavailable',reasons=['insufficient_history'])))
    cold = observed_days < 29
    means, sigma = weekday_spend_profile(p)
    raw_spend_fn = daily_spend_override or (lambda d: means[d.weekday()])
    # Reconcile using the same cent amounts exposed in the API. Accumulating
    # fractional cents and rounding only the displayed path creates drift.
    spend_fn = lambda d: raw_spend_fn(d).quantize(CENTS)
    points = project_balance(p, days, spend_fn)
    series = []
    for i, pt in enumerate(points):
        band = Decimal(str(2*sigma*(i+1) if cold else Z80 * sigma * math.sqrt(i + 1)))
        bal = pt.balance
        series.append(ForecastPoint(
            date=pt.date, projected_balance=bal.quantize(CENTS),
            low=(bal - band).quantize(CENTS), high=(bal + (Decimal(str(sigma*(i+1))) if cold else band)).quantize(CENTS),
            predicted_spend=pt.spend.quantize(CENTS)))
    low = None
    if series:
        m = min(series, key=lambda s: s.projected_balance)
        low = ProjectedLow(date=m.date, balance=m.projected_balance)
    buffer = p.user.safety_buffer
    return ForecastResult(
        days=days, series=series, projected_low=low, safety_buffer=buffer,
        shortfall=bool(low and low.balance < buffer),
        assumptions=[
            ("Limited-history planning estimate repeats the observed-day mean; earlier missing days are not zeros." if cold else "Variable spending uses weekday averages over observed history, up to 90 days."),
            "The low/high band is an uncalibrated heuristic stress envelope that widens with the horizon; it does not establish 80% coverage.",
            "Based on simulated data - prototype estimate.",
        ],
        evaluation=None,
        status="limited_history" if cold else "estimated",
        meta=Meta(source="baseline", as_of=p.as_of, generated_at=datetime.now(timezone.utc),
            forecast_reliability=ForecastReliability(method='observed_mean' if cold else 'weekday_mean_90',status='limited_history' if cold else 'estimated',validation='unvalidated',reasons=['short_history'] if cold else ['baseline_not_validated']),
            warning=(f"Only {observed_days} observed history days. Repeating the observed-day mean is an uncertain planning assumption, not a validated forecast; earlier missing days are not zeros. Stress bounds are deliberately broad and uncalibrated." if cold else None)))
