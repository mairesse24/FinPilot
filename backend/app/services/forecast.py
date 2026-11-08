from app.baseline.forecast import forecast as baseline_forecast
from app.calc.models import FinancialProfile
from app.schemas.forecast import ForecastResult
from app.services.gateway import Gateway, make_meta
from app.services.notices import with_profile_notices


def get_forecast(p: FinancialProfile, gateway: Gateway, days: int) -> ForecastResult:
    out = gateway.run("forecast", "forecast", baseline_forecast, p, days, expect=ForecastResult)
    meta=with_profile_notices(make_meta(out,p.as_of),p)
    if meta.forecast_reliability:
        critical=[n.code for n in meta.notices if n.category=='critical']
        meta=meta.model_copy(update={'forecast_reliability':meta.forecast_reliability.model_copy(update={
            'reasons':list(dict.fromkeys(meta.forecast_reliability.reasons+critical))})})
    if meta.forecast_reliability and meta.forecast_reliability.validation=='unvalidated':
        from app.schemas.common import Notice
        from app.services.notices import merge_notices
        # A pattern-shift notice already communicates this limitation.
        if not any(n.code in ('forecast_pattern_shift','forecast_short_history') for n in meta.notices):
            meta=meta.model_copy(update={'notices':merge_notices(meta.notices,[Notice(code='forecast_unvalidated',context='forecast',category='critical',
                message='This is a planning estimate. Its accuracy has not been validated for this spending pattern.',
                technical_detail='Serving baseline has no applicable independent real-customer validation.')])})
    return out.value.model_copy(update={"meta":meta})
