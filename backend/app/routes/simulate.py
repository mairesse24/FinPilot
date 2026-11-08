from fastapi import APIRouter, Depends

from app.calc.models import FinancialProfile
from app.deps import get_gateway, get_profile
from app.schemas.simulate import SimulateRequest, SimulationResult
from app.services.gateway import Gateway
from app.services.simulate import run_simulation

router = APIRouter(prefix="/api", tags=["simulate"])


@router.post("/simulate", response_model=SimulationResult)
def simulate_route(req: SimulateRequest, p: FinancialProfile = Depends(get_profile),
                   gateway: Gateway = Depends(get_gateway)):
    return run_simulation(p, gateway, req.scenario)
