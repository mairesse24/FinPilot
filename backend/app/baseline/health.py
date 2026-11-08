"""Explainable baseline financial health score (0-100), five weighted components."""
from datetime import datetime, timezone
from decimal import Decimal

from app.calc import categories as cat
from app.calc import metrics as m
from app.calc.models import FinancialProfile
from app.schemas.health import ComponentScore, HealthResult
from app.schemas.common import Meta

# --- design assumptions (tunable thresholds) -------------------------------
WEIGHTS = {"cash_flow": 25, "emergency": 25, "debt": 20, "discipline": 15, "readiness": 15}
NAMES = {"cash_flow": "Cash flow", "emergency": "Emergency fund", "debt": "Debt burden",
         "discipline": "Spending discipline", "readiness": "Bill readiness"}
CASH_FLOW_RATIO = (0.8, 1.2)      # inflow/outflow: 0 at <=0.8, 100 at >=1.2
EMERGENCY_FULL_MONTHS = 6.0       # 100 at >= 6 months of essentials
DTI = (0.50, 0.10)                # debt/income: 0 at >=0.50, 100 at <=0.10
DISCRETIONARY_SHARE = (0.40, 0.15)  # 0 at >=0.40, 100 at <=0.15
READINESS_COVER = (0.5, 2.0)      # cash/bills: 0 at <=0.5, 100 at >=2.0
STRENGTH_MIN, WEAKNESS_MAX = 75, 50
# ---------------------------------------------------------------------------


def _lin(x: float, zero_at: float, full_at: float) -> float:
    """Linear 0..100 between anchors (works for either direction), clamped."""
    v = (x - zero_at) / (full_at - zero_at) * 100
    return max(0.0, min(100.0, v))


def _f(d: Decimal | float) -> float:
    return round(float(d), 2)


def _cash_flow(p):
    inflow, outflow = m.window_inflow(p, 30), m.window_outflow(p, 30)
    if outflow > 0:
        ratio = float(inflow / outflow)
        score = _lin(ratio, *CASH_FLOW_RATIO)
        ex = f"Over the last 30 days ${_f(inflow):,.2f} came in vs ${_f(outflow):,.2f} went out (ratio {ratio:.2f})."
        met = {"inflow_30d": _f(inflow), "outflow_30d": _f(outflow), "inflow_outflow_ratio": round(ratio, 3)}
    elif inflow > 0:
        score, ex = 100.0, f"${_f(inflow):,.2f} came in over the last 30 days with no spending."
        met = {"inflow_30d": _f(inflow), "outflow_30d": 0.0, "inflow_outflow_ratio": None}
    else:
        score, ex = 50.0, "No money in or out in the last 30 days, so cash flow is neutral."
        met = {"inflow_30d": 0.0, "outflow_30d": 0.0, "inflow_outflow_ratio": None}
    return score, met, ex


def _emergency(p):
    liquid = m.liquid_balance(p)
    ess = sum((v for k, v in m.spend_by_category(p, 90).items() if k in cat.ESSENTIAL), Decimal(0))
    monthly = ess / 3
    if monthly <= 0:
        return 100.0, {"liquid": _f(liquid), "monthly_essentials": 0.0, "months_covered": None}, \
            "No essential spending in the last 90 days, so no emergency cushion is required."
    months = float(liquid / monthly)
    score = _lin(months, 0, EMERGENCY_FULL_MONTHS)
    return score, {"liquid": _f(liquid), "monthly_essentials": _f(monthly),
                   "months_covered": round(months, 2)}, \
        f"Liquid savings of ${_f(liquid):,.2f} cover {months:.1f} months of essentials (${_f(monthly):,.2f}/month)."


def _debt(p):
    inc, debt = m.monthly_income(p), m.monthly_debt_payments(p)
    if inc <= 0:
        score = 0.0 if debt > 0 else 100.0
        dti = None
        ex = (f"Debt payments of ${_f(debt):,.2f}/month with no recorded income." if debt > 0
              else "No debt payments and no recorded income.")
    else:
        dti = float(debt / inc)
        score = _lin(dti, *DTI)
        ex = f"Debt payments of ${_f(debt):,.2f} are {dti:.0%} of ${_f(inc):,.2f} monthly income."
    return score, {"monthly_debt_payments": _f(debt), "monthly_income": _f(inc),
                   "debt_to_income": None if dti is None else round(dti, 3)}, ex


def _discipline(p):
    spend = m.spend_by_category(p, 90)
    var = sum((v for k, v in spend.items() if k in cat.VARIABLE), Decimal(0))
    if var <= 0:
        return 100.0, {"variable_spend_90d": 0.0, "discretionary_share": None}, \
            "No variable spending in the last 90 days."
    disc = sum((v for k, v in spend.items() if k in cat.DISCRETIONARY), Decimal(0))
    share = float(disc / var)
    return _lin(share, *DISCRETIONARY_SHARE), \
        {"variable_spend_90d": _f(var), "discretionary_spend_90d": _f(disc),
         "discretionary_share": round(share, 3)}, \
        f"Discretionary items are {share:.0%} of ${_f(var):,.2f} variable spending over 90 days."


def _readiness(p):
    cash = m.cash_balance(p)
    bills = sum((b.amount for _, b in m.bill_occurrences(p, 30)), Decimal(0))
    if bills <= 0:
        return 100.0, {"cash": _f(cash), "bills_due_30d": 0.0, "cover_ratio": None}, \
            f"No bills due in the next 30 days; checking holds ${_f(cash):,.2f}."
    cover = float(cash / bills)
    return _lin(cover, *READINESS_COVER), \
        {"cash": _f(cash), "bills_due_30d": _f(bills), "cover_ratio": round(cover, 2)}, \
        f"Checking holds ${_f(cash):,.2f} against ${_f(bills):,.2f} of bills due in 30 days ({cover:.1f}x)."


_FUNCS = {"cash_flow": _cash_flow, "emergency": _emergency, "debt": _debt,
          "discipline": _discipline, "readiness": _readiness}


def compute_health_score(p: FinancialProfile) -> HealthResult:
    comps, strengths, weaknesses = [], [], []
    for key, fn in _FUNCS.items():
        score, met, ex = fn(p)
        score = round(score, 1)
        comps.append(ComponentScore(key=key, name=NAMES[key], weight=WEIGHTS[key], score=score,
                                    metrics=met, explanation=ex))
        if score >= STRENGTH_MIN:
            strengths.append(f"{NAMES[key]} is strong ({score:.0f}/100): {ex}")
        elif score < WEAKNESS_MAX:
            weaknesses.append(f"{NAMES[key]} needs attention ({score:.0f}/100): {ex}")
    total = round(sum(c.weight * c.score for c in comps) / 100, 1)
    meta = Meta(source="baseline", as_of=p.as_of, generated_at=datetime.now(timezone.utc))
    return HealthResult(score=total, components=comps, strengths=strengths,
                        weaknesses=weaknesses, meta=meta)
