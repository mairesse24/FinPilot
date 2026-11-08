from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Meta
from intelligence.personal_finance import FinancialFacts


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)
    financial_facts: FinancialFacts | None = None


class ToolCallRecord(BaseModel):
    name: str
    args: dict
    summary: str


class ChatResult(BaseModel):
    reply: str
    tool_calls: list[ToolCallRecord]
    meta: Meta
