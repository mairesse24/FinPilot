from app.baseline.health import compute_health_score
from app.calc.models import FinancialProfile
from app.schemas.health import HealthResult
from app.services.gateway import Gateway, make_meta


def get_health(p: FinancialProfile, gateway: Gateway) -> HealthResult:
    outcome = gateway.run("health_score", "compute_health_score", compute_health_score, p,
                          expect=HealthResult)
    result = outcome.value.model_copy(update={"meta": make_meta(outcome, p.as_of)})
    return result
