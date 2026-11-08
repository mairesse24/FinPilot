from app.baseline.forecast import forecast as baseline_forecast
from app.calc.models import FinancialProfile
from app.schemas.forecast import ForecastResult
from app.services.gateway import Gateway, make_meta


def get_forecast(p: FinancialProfile, gateway: Gateway, days: int) -> ForecastResult:
    out = gateway.run("forecast", "forecast", baseline_forecast, p, days, expect=ForecastResult)
    return out.value.model_copy(update={"meta": make_meta(out, p.as_of)})
