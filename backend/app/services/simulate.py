from app.baseline.simulate import simulate
from app.calc.models import FinancialProfile
from app.schemas.common import SpendingCut
from app.schemas.simulate import SimulationResult
from app.services.gateway import Gateway, make_meta


def run_simulation(p: FinancialProfile, gateway: Gateway, cut: SpendingCut) -> SimulationResult:
    out = gateway.run("simulate", "simulate", simulate, p, cut, expect=SimulationResult)
    from app.services.notices import with_profile_notices
    return out.value.model_copy(update={"meta":with_profile_notices(make_meta(out,p.as_of),p)})
