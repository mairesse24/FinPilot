from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.data.synthetic import DEMO_USER_ID


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    database_url: str | None = None
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    demo_user_id: str = DEMO_USER_ID
    intelligence_mode: Literal["auto", "baseline"] = "auto"
    as_of_date: date | None = None
    gemini_api_key: SecretStr | None = None
    gemini_model: str = Field(default="gemini-3.1-flash-lite", min_length=1)
    copilot_timeout_seconds: float = Field(default=20, ge=1, le=25)
    copilot_max_rounds: int = Field(default=4, ge=1, le=6)
    copilot_max_tool_calls: int = Field(default=8, ge=1, le=12)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split(cls, v):
        return [s.strip() for s in v.split(",") if s.strip()] if isinstance(v, str) else v


@lru_cache
def get_settings() -> Settings:
    return Settings()
