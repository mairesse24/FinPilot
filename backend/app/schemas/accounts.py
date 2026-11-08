from datetime import date

from pydantic import BaseModel

from app.schemas.common import Money


class AccountOut(BaseModel):
    id: str
    name: str
    account_type: str
    balance: Money
    apr: float | None = None
    min_payment: Money | None = None
    credit_limit: Money | None = None


class AccountsResult(BaseModel):
    accounts: list[AccountOut]


class TransactionOut(BaseModel):
    id: str
    account_id: str
    amount: Money
    category: str
    date: date


class TransactionsResult(BaseModel):
    items: list[TransactionOut]
    total: int


class DemoAlert(BaseModel):
    id: str
    title: str
    severity: str
    cause: str
    recommended_action: str


class SavingsStressResult(BaseModel):
    mode: str
    executed: bool
    percentage: int
    purchase_amount: Money
    savings_before: Money
    savings_after: Money
    alert: DemoAlert
