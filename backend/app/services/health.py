from app.baseline.health import compute_health_score
from app.calc.models import FinancialProfile
from app.schemas.health import HealthResult
from app.services.gateway import Gateway, make_meta


def get_health(p: FinancialProfile, gateway: Gateway) -> HealthResult:
    outcome = gateway.run("health_score", "compute_health_score", compute_health_score, p,
                          expect=HealthResult)
    result = outcome.value.model_copy(update={"meta": make_meta(outcome, p.as_of)})
    if (any(b.category=="debt_payment" and not b.liability_account_id for b in p.bills)
        and any(a.min_payment for a in p.accounts if a.account_type in ("credit_card","loan"))):
        note="Unlinked debt bills may overlap account minimums; debt burden is an aggregate floor. Supply liability_account_id for exact attribution."
        if 'aggregate floor' not in (result.meta.warning or ''):
            result=result.model_copy(update={"meta":result.meta.model_copy(update={"warning":(result.meta.warning+'; ' if result.meta.warning else '')+note})})
    from app.services.notices import with_profile_notices
    return result.model_copy(update={'meta':with_profile_notices(result.meta,p)})
