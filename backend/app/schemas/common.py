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


class SpendingCut(BaseModel):
    type: Literal["spending_cut"] = "spending_cut"
    reduction_amount: Money = Field(gt=0, le=100000)
    horizon_days: int = Field(default=30, ge=1, le=90)
    category: str | None = None
