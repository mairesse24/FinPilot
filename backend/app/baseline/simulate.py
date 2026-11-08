"""Baseline Digital Twin: apply a spending cut and compare against the unchanged baseline."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.baseline.forecast import forecast, weekday_spend_profile
from app.baseline.guardian import evaluate
from app.baseline.health import compute_health_score
from app.calc.categories import DISCRETIONARY
from app.calc.models import FinancialProfile
from app.schemas.common import Meta, SpendingCut
from app.schemas.forecast import ForecastResult
from app.schemas.simulate import ScenarioOutcome, SimulationResult

ZERO = Decimal("0")
CENTS = Decimal("0.01")


def apply_spending_cut(p: FinancialProfile, cut: SpendingCut) -> FinancialProfile:
    """Copy of p with last-30-day DISCRETIONARY outflows scaled down by the cut (30-day rate)."""
    start = p.as_of - timedelta(days=30)

    def hit(t):
        return t.amount < 0 and t.category in DISCRETIONARY and start < t.date <= p.as_of

    spend = sum((-t.amount for t in p.transactions if hit(t)), ZERO)
    if spend <= 0:
        return p
    reduction = min(cut.reduction_amount * 30 / cut.horizon_days, spend)
    factor = 1 - reduction / spend
    txs = [replace(t, amount=(t.amount * factor).quantize(CENTS)) if hit(t) else t
           for t in p.transactions]
    return replace(p, transactions=txs)


def _outcome(p: FinancialProfile, fc: ForecastResult) -> ScenarioOutcome:
    return ScenarioOutcome(
        projected_low=fc.projected_low,
        end_balance=fc.series[-1].projected_balance if fc.series else ZERO,
        health_score=compute_health_score(p).score,
        alerts=evaluate(p, fc), series=fc.series)


def simulate(p: FinancialProfile, cut: SpendingCut) -> SimulationResult:
    days = max(30, cut.horizon_days)
    base_fc = forecast(p, days)
    means, _ = weekday_spend_profile(p)
    per_day = cut.reduction_amount / cut.horizon_days
    horizon_end = p.as_of + timedelta(days=cut.horizon_days)

    def spend(d: date) -> Decimal:
        s = means[d.weekday()]
        return s - min(s, per_day) if d <= horizon_end else s

    scen_p = apply_spending_cut(p, cut)
    scen_fc = forecast(p, days, spend)
    base, scen = _outcome(p, base_fc), _outcome(scen_p, scen_fc)
    low_b = base.projected_low.balance if base.projected_low else ZERO
    low_s = scen.projected_low.balance if scen.projected_low else ZERO
    delta = {
        "low_balance_change": round(float(low_s - low_b), 2),
        "end_balance_change": round(float(scen.end_balance - base.end_balance), 2),
        "health_score_change": round(scen.health_score - base.health_score, 1),
    }
    return SimulationResult(baseline=base, scenario=scen, delta=delta, meta=Meta(
        source="baseline", as_of=p.as_of, generated_at=datetime.now(timezone.utc)))
