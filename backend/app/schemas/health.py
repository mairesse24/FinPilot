from pydantic import BaseModel

from app.schemas.common import Meta


class ComponentScore(BaseModel):
    key: str
    name: str
    weight: float
    score: float
    metrics: dict[str, float | None]
    explanation: str


class HealthResult(BaseModel):
    score: float
    components: list[ComponentScore]
    strengths: list[str]
    weaknesses: list[str]
    meta: Meta
