from app.calc import metrics as m
from app.calc.models import FinancialProfile
from app.schemas.accounts import AccountOut
from app.schemas.dashboard import CategorySpend, DashboardResult, UpcomingBill
from app.services.gateway import Gateway, make_meta
from app.services.guardian import get_guardian
from app.services.health import get_health


def build_dashboard(p: FinancialProfile, gateway: Gateway) -> DashboardResult:
    cats = sorted(m.spend_by_category(p, 30).items(), key=lambda kv: kv[1], reverse=True)
    bills = [UpcomingBill(name=b.name, amount=b.amount, due_date=d)
             for d, b in m.bill_occurrences(p, 14)]
    guardian = get_guardian(p, gateway)
    health = get_health(p, gateway)
    warnings=list(dict.fromkeys(w for w in (guardian.meta.warning,health.meta.warning) if w))
    from app.services.notices import merge_notices
    meta=guardian.meta.model_copy(update={'warning':'; '.join(warnings) if warnings else None,
                                        'notices':merge_notices(guardian.meta.notices,health.meta.notices)})
    return DashboardResult(
        net_worth=m.net_worth(p), assets=m.assets(p), liabilities=m.liabilities(p),
        accounts=[AccountOut(id=a.id, name=a.name, account_type=a.account_type,
                             balance=a.balance,apr=a.apr,min_payment=a.min_payment,
                             credit_limit=a.credit_limit) for a in p.accounts],
        income_30d=m.window_inflow(p, 30), spending_30d=m.window_outflow(p, 30),
        by_category=[CategorySpend(category=c, amount=v) for c, v in cats],
        upcoming_bills=sorted(bills, key=lambda b: b.due_date),
        health_score=health.score, active_alerts=guardian.alerts,
        meta=meta)
