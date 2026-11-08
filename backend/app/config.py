from datetime import date
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.data.synthetic import DEMO_USER_ID


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    database_url: str | None = None
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    demo_user_id: str = DEMO_USER_ID
    intelligence_mode: Literal["auto", "baseline"] = "auto"
    as_of_date: date | None = None
    data_source: Literal["demo", "nessie"] = "demo"
    nessie_api_key: str | None = None
    nessie_customer_id: str | None = None
    nessie_base_url: str = "https://api.nessieisreal.com"
    nessie_schedules_file: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split(cls, v):
        return [s.strip() for s in v.split(",") if s.strip()] if isinstance(v, str) else v


@lru_cache
def get_settings() -> Settings:
    return Settings()
