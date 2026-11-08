from datetime import date

from fastapi import Depends, HTTPException, Query, Request

from app.calc.models import FinancialProfile
from app.config import Settings
from app.db.repository import Repository
from app.services.gateway import Gateway


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_repo(request: Request) -> Repository:
    return request.app.state.repo


def get_gateway(request: Request) -> Gateway:
    return Gateway(request.app.state.settings.intelligence_mode)


def get_as_of(settings: Settings = Depends(get_settings_dep)) -> date:
    return settings.as_of_date or date.today()


def get_user_id(user_id: str | None = Query(None),
                settings: Settings = Depends(get_settings_dep),
                repo: Repository = Depends(get_repo)) -> str:
    uid = user_id or (settings.nessie_customer_id if settings.data_source == "nessie" else settings.demo_user_id)
    if settings.data_source == "nessie" and uid != settings.nessie_customer_id:
        raise HTTPException(404, "Customer not available in this sandbox session")
    if repo.get_user(uid) is None:
        raise HTTPException(404, f"user '{uid}' not found")
    return uid


def get_profile(uid: str = Depends(get_user_id), repo: Repository = Depends(get_repo),
                as_of: date = Depends(get_as_of)) -> FinancialProfile:
    profile = repo.load_profile(uid, as_of)
    if profile is None:
        raise HTTPException(404, f"user '{uid}' not found")
    return profile
