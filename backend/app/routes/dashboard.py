from fastapi import APIRouter, Depends

from app.calc.models import FinancialProfile
from app.deps import get_gateway, get_profile
from app.schemas.dashboard import DashboardResult
from app.services.dashboard import build_dashboard
from app.services.gateway import Gateway

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResult)
def dashboard(p: FinancialProfile = Depends(get_profile), gateway: Gateway = Depends(get_gateway)):
    return build_dashboard(p, gateway)
