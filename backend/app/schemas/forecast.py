from datetime import date

from pydantic import BaseModel

from app.schemas.common import Meta, Money


class ForecastPoint(BaseModel):
    date: date
    projected_balance: Money
    low: Money
    high: Money
    predicted_spend: Money


class ProjectedLow(BaseModel):
    date: date
    balance: Money


class ForecastResult(BaseModel):
    days: int
    series: list[ForecastPoint]
    projected_low: ProjectedLow | None
    safety_buffer: Money
    shortfall: bool
    assumptions: list[str]
    evaluation: dict[str, float] | None = None
    meta: Meta
