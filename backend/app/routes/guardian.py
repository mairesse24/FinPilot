from fastapi import APIRouter, Depends

from app.calc.models import FinancialProfile
from app.deps import get_gateway, get_profile
from app.schemas.guardian import GuardianResult
from app.services.gateway import Gateway
from app.services.guardian import get_guardian

router = APIRouter(prefix="/api", tags=["guardian"])


@router.get("/guardian", response_model=GuardianResult)
def guardian_route(p: FinancialProfile = Depends(get_profile),
                   gateway: Gateway = Depends(get_gateway)):
    return get_guardian(p, gateway)
