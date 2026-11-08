"""Baseline Guardian: three explainable risk rules."""
import math
from decimal import Decimal

from app.calc import categories as cat
from app.calc import metrics as m
from app.calc.models import FinancialProfile
from app.schemas.common import SpendingCut
from app.schemas.forecast import ForecastResult
from app.schemas.guardian import Alert

_ORDER = {"high": 0, "medium": 1, "low": 2}


def _round_up_50(v: Decimal) -> Decimal:
    return max(Decimal(math.ceil(v / 50) * 50), Decimal(50))


def _low_balance(p: FinancialProfile, f: ForecastResult) -> Alert | None:
    if not f.shortfall or f.projected_low is None:
        return None
    low, buf = f.projected_low.balance, f.safety_buffer
    sev = "high" if low < 0 or low < buf * Decimal("0.25") else "medium"
    cut = _round_up_50(max(buf - low, Decimal(0)))
    horizon = max(1, (f.projected_low.date - p.as_of).days)
    cash = m.cash_balance(p)
    return Alert(
        id=f"low_projected_balance:{p.as_of}", rule="low_projected_balance", severity=sev,
        title="Checking balance projected to dip below your safety buffer",
        cause=(f"Checking holds ${cash:,.2f} today but is projected to fall to ${low:,.2f} on "
               f"{f.projected_low.date:%b %d}, below your ${buf:,.2f} safety buffer."),
        numbers={"current": float(cash), "projected_low": float(low),
                 "safety_buffer": float(buf), "low_date": str(f.projected_low.date)},
        recommended_action=(f"Trim about ${cut:,.0f} of discretionary spending over the next "
                            f"{horizon} days to stay above the buffer."),
        suggested_scenario=SpendingCut(reduction_amount=cut, horizon_days=min(horizon, 90)))


def _debt_burden(p: FinancialProfile) -> Alert | None:
    debt, income = m.monthly_debt_payments(p), m.monthly_income(p)
    if debt <= 0:
        return None
    ratio = float(debt / income) if income > 0 else float("inf")
    if ratio <= 0.36:
        return None
    shown = round(ratio, 3) if math.isfinite(ratio) else 9.99
    return Alert(
        id=f"high_debt_burden:{p.as_of}", rule="high_debt_burden",
        severity="high" if ratio > 0.50 else "medium", title="Debt payments take a large share of income",
        cause=(f"Monthly debt payments of ${debt:,.2f} are {shown:.0%} of "
               f"${income:,.2f} monthly income (guideline: under 36%)."),
        numbers={"monthly_debt_payments": float(debt), "monthly_income": float(income),
                 "debt_to_income": shown},
        recommended_action="Prioritise paying down the highest-APR balance and avoid new debt.")


def _emergency(p: FinancialProfile) -> Alert | None:
    essentials = sum((v for k, v in m.spend_by_category(p, 90).items() if k in cat.ESSENTIAL),
                     Decimal(0)) / 3
    if essentials <= 0:
        return None
    liquid = m.liquid_balance(p)
    months = float(liquid / essentials)
    if months >= 3:
        return None
    return Alert(
        id=f"low_emergency_savings:{p.as_of}", rule="low_emergency_savings",
        severity="high" if months < 1 else "medium", title="Emergency savings are thin",
        cause=(f"Liquid savings of ${liquid:,.2f} cover {months:.1f} months of essential "
               f"spending (${essentials:,.2f}/month); 3 months is the usual target."),
        numbers={"liquid_balance": float(liquid), "monthly_essentials": float(essentials.quantize(Decimal('0.01'))),
                 "months_covered": round(months, 2)},
        recommended_action="Build a cash reserve of at least three months of essentials.")


def evaluate(p: FinancialProfile, forecast: ForecastResult) -> list[Alert]:
    alerts = [a for a in (_low_balance(p, forecast), _debt_burden(p), _emergency(p)) if a]
    return sorted(alerts, key=lambda a: _ORDER[a.severity])
