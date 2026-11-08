from datetime import date

from pydantic import BaseModel

from app.schemas.accounts import AccountOut
from app.schemas.common import Meta, Money
from app.schemas.guardian import Alert


class CategorySpend(BaseModel):
    category: str
    amount: Money


class UpcomingBill(BaseModel):
    name: str
    amount: Money
    due_date: date


class DashboardResult(BaseModel):
    net_worth: Money
    assets: Money
    liabilities: Money
    accounts: list[AccountOut]
    income_30d: Money
    spending_30d: Money
    by_category: list[CategorySpend]
    upcoming_bills: list[UpcomingBill]
    health_score: float
    active_alerts: list[Alert]
    meta: Meta
