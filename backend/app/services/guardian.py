from app.baseline.guardian import evaluate
from app.calc.models import FinancialProfile
from app.schemas.guardian import GuardianResult
from app.services.forecast import get_forecast
from app.services.gateway import Gateway, make_meta


def get_guardian(p: FinancialProfile, gateway: Gateway) -> GuardianResult:
    fc = get_forecast(p, gateway, 30)
    out = gateway.run("guardian", "evaluate", evaluate, p, fc, expect=list)
    return GuardianResult(alerts=out.value, meta=make_meta(out, p.as_of))
