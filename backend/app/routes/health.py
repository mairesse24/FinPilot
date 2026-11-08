from fastapi import APIRouter, Depends

from app.calc.models import FinancialProfile
from app.deps import get_gateway, get_profile
from app.schemas.health import HealthResult
from app.services.gateway import Gateway
from app.services.health import get_health

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResult)
def health(p: FinancialProfile = Depends(get_profile), gateway: Gateway = Depends(get_gateway)):
    return get_health(p, gateway)
