from app.baseline.guardian import evaluate
from app.calc.models import FinancialProfile
from app.schemas.guardian import GuardianResult
from app.services.forecast import get_forecast
from app.services.gateway import Gateway, make_meta


def get_guardian(p: FinancialProfile, gateway: Gateway) -> GuardianResult:
    fc = get_forecast(p, gateway, 30)
    out = gateway.run("guardian", "evaluate", evaluate, p, fc, expect=list)
    if fc.meta.warning and fc.meta.warning not in (out.warning or ''):
        out.warning = (out.warning+'; ' if out.warning else '')+fc.meta.warning
    out.forecast_reliability=fc.meta.forecast_reliability
    out.notices=fc.meta.notices
    from app.services.economic_intelligence import contextual
    from app.schemas.guardian import Alert
    for candidate in contextual(p)['alerts']:
        out.value.append(Alert(id=candidate['id'],rule=candidate['id'],severity=candidate['severity'],
            title=candidate['id'].replace('_',' ').title(),cause=candidate['cause'],
            numbers={k:v for k,v in candidate['numbers'].items() if v is not None},
            recommended_action=candidate['action'],economic_scenario=candidate['scenario']))
    from app.services.notices import with_profile_notices
    return GuardianResult(alerts=out.value, meta=with_profile_notices(make_meta(out,p.as_of),p))
