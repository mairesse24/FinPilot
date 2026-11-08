"""Baseline cash-flow forecast: weekday-mean variable spend + known bills/income."""
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable

from app.calc.categories import VARIABLE
from app.calc.metrics import cash_balance
from app.calc.models import FinancialProfile
from app.calc.projection import project_balance
from app.schemas.common import Meta
from app.schemas.forecast import ForecastPoint, ForecastResult, ProjectedLow

ZERO = Decimal("0")
CENTS = Decimal("0.01")
Z80 = 1.28


def _daily_variable(p: FinancialProfile, window: int = 90) -> dict[date, Decimal]:
    start = p.as_of - timedelta(days=window)
    out = {p.as_of - timedelta(days=i): ZERO for i in range(window)}
    for t in p.transactions:
        if start < t.date <= p.as_of and t.amount < 0 and t.category in VARIABLE:
            out[t.date] += -t.amount
    return out


def weekday_spend_profile(p: FinancialProfile) -> tuple[dict[int, Decimal], float]:
    """Mean daily VARIABLE outflow per weekday (trailing 90 days) and sigma of daily spend."""
    daily = _daily_variable(p)
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
    means, sigma = weekday_spend_profile(p)
    spend_fn = daily_spend_override or (lambda d: means[d.weekday()])
    points = project_balance(p, days, spend_fn)
    series = []
    for i, pt in enumerate(points):
        band = Decimal(str(Z80 * sigma * math.sqrt(i + 1)))
        bal = pt.balance
        series.append(ForecastPoint(
            date=pt.date, projected_balance=bal.quantize(CENTS),
            low=(bal - band).quantize(CENTS), high=(bal + band).quantize(CENTS),
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
            "Variable spending is projected from the weekday average of the trailing 90 days.",
            "The low/high band is an uncalibrated heuristic stress envelope that widens with the horizon; it does not establish 80% coverage.",
            "Based on simulated data - prototype estimate.",
        ],
        evaluation=None,
        meta=Meta(source="baseline", as_of=p.as_of, generated_at=datetime.now(timezone.utc)))
