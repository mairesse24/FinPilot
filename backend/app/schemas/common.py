from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, PlainSerializer

# Decimal in Python, JSON number rounded to 2 decimals on the wire.
Money = Annotated[Decimal, PlainSerializer(lambda v: round(float(v), 2), return_type=float,
                                           when_used="json")]


class Meta(BaseModel):
    source: Literal["model", "baseline"]
    is_prototype_estimate: bool = True
    as_of: date
    generated_at: datetime
    warning: str | None = None
    notices: list['Notice'] = Field(default_factory=list)
    forecast_reliability: 'ForecastReliability | None' = None


class Notice(BaseModel):
    code: str
    context: str
    category: Literal['critical', 'data_limitation', 'diagnostic']
    message: str
    technical_detail: str


class ForecastReliability(BaseModel):
    method: str
    status: Literal['estimated', 'limited_history', 'abstained']
    validation: Literal['unvalidated', 'synthetic_evaluated', 'unavailable']
    reasons: list[str] = Field(default_factory=list)
    support_check: dict = Field(default_factory=dict)
    interval: str = 'Uncalibrated balance stress envelope; no coverage guarantee.'


Meta.model_rebuild()


class SpendingCut(BaseModel):
    type: Literal["spending_cut"] = "spending_cut"
    reduction_amount: Money = Field(gt=0, le=100000)
    horizon_days: int = Field(default=30, ge=1, le=90)
    category: str | None = None
