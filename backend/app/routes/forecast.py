from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import AfterValidator

from app.calc.models import FinancialProfile
from app.deps import get_gateway, get_profile
from app.schemas.forecast import ForecastResult
from app.services.forecast import get_forecast
from app.services.gateway import Gateway


def _horizon(v: int) -> int:
    if v not in (7, 30, 90):
        raise ValueError("days must be 7, 30 or 90")
    return v


router = APIRouter(prefix="/api", tags=["forecast"])


@router.get("/forecast", response_model=ForecastResult)
def forecast_route(days: Annotated[int, Query(), AfterValidator(_horizon)] = 30, p: FinancialProfile = Depends(get_profile),
                   gateway: Gateway = Depends(get_gateway)):
    return get_forecast(p, gateway, days)
