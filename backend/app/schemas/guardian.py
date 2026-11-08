from typing import Literal

from pydantic import BaseModel

from app.schemas.common import Meta, SpendingCut


class Alert(BaseModel):
    id: str
    rule: str
    severity: Literal["low", "medium", "high"]
    title: str
    cause: str
    numbers: dict[str, float | str]
    recommended_action: str
    suggested_scenario: SpendingCut | None = None
    economic_scenario: dict | None = None


class GuardianResult(BaseModel):
    alerts: list[Alert]
    meta: Meta
