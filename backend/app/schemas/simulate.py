from pydantic import BaseModel

from app.schemas.common import Meta, Money, SpendingCut, ForecastReliability
from app.schemas.forecast import ForecastPoint, ProjectedLow
from app.schemas.guardian import Alert

__all__ = ["SpendingCut", "ScenarioOutcome", "SimulateRequest", "SimulationResult"]


class ScenarioOutcome(BaseModel):
    projected_low: ProjectedLow | None
    end_balance: Money | None
    health_score: float
    alerts: list[Alert]
    series: list[ForecastPoint]
    forecast_reliability: ForecastReliability | None = None


class SimulateRequest(BaseModel):
    scenario: SpendingCut


class SimulationResult(BaseModel):
    baseline: ScenarioOutcome
    scenario: ScenarioOutcome
    delta: dict[str, float | None]
    meta: Meta
