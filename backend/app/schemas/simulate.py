from pydantic import BaseModel

from app.schemas.common import Meta, Money, SpendingCut
from app.schemas.forecast import ForecastPoint, ProjectedLow
from app.schemas.guardian import Alert

__all__ = ["SpendingCut", "ScenarioOutcome", "SimulateRequest", "SimulationResult"]


class ScenarioOutcome(BaseModel):
    projected_low: ProjectedLow | None
    end_balance: Money
    health_score: float
    alerts: list[Alert]
    series: list[ForecastPoint]


class SimulateRequest(BaseModel):
    scenario: SpendingCut


class SimulationResult(BaseModel):
    baseline: ScenarioOutcome
    scenario: ScenarioOutcome
    delta: dict[str, float]
    meta: Meta
