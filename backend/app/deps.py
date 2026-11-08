from datetime import date
from datetime import timedelta
from dataclasses import replace

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
    return replace(profile,data_warnings=tuple(getattr(repo,'warnings',[])))


def get_assessment_profile(p:FinancialProfile=Depends(get_profile),repo:Repository=Depends(get_repo)) -> FinancialProfile:
    """Longer owned history for six-month diagnostics; legacy API lookback is unchanged."""
    txs,total=repo.list_transactions(p.user.id,limit=20000,offset=0,
        date_from=p.as_of-timedelta(days=366),date_to=p.as_of)
    if total>len(txs):raise HTTPException(422,'Assessment history exceeds safe read limit; completeness is not established')
    return replace(p,transactions=sorted(txs,key=lambda t:(t.date,t.id)))
