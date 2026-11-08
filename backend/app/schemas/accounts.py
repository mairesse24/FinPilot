from datetime import date

from pydantic import BaseModel

from app.schemas.common import Money


class AccountOut(BaseModel):
    id: str
    name: str
    account_type: str
    balance: Money


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
