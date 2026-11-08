from datetime import date

from pydantic import BaseModel, Field

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


class SimulatedTransactionRequest(BaseModel):
    account_id: str = Field(min_length=1, max_length=200)
    amount: Money = Field(gt=0, allow_inf_nan=False, decimal_places=2)
    description: str = Field(default="Synthetic purchase", min_length=1, max_length=100)
    category: str = Field(default="shopping", pattern="^[a-z_]{2,30}$")


class SimulatedTransactionResult(BaseModel):
    mode: str = "simulation"
    executed: bool = False
    account_id: str
    account_name: str
    amount: Money
    balance_before: Money
    balance_after: Money
    total_liquid_before: Money
    total_liquid_after: Money
    account_share_percent: float
    liquid_share_percent: float
    alerts: list[DemoAlert]
