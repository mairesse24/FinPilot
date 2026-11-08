"""Domain dataclasses. Money is Decimal; ids are str."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class User:
    id: str
    name: str
    email: str
    safety_buffer: Decimal = Decimal("500")


@dataclass(frozen=True)
class Account:
    id: str
    user_id: str
    name: str
    account_type: str  # checking | savings | credit_card | loan
    balance: Decimal  # positive: amount held (assets) or owed (credit_card, loan)
    apr: Decimal | None = None
    min_payment: Decimal | None = None
    credit_limit: Decimal | None = None


@dataclass(frozen=True)
class Transaction:
    id: str
    account_id: str
    amount: Decimal  # negative = money out, positive = money in
    category: str
    date: date


@dataclass(frozen=True)
class Bill:
    id: str
    user_id: str
    name: str
    amount: Decimal
    category: str
    frequency: str  # weekly | biweekly | monthly
    due_date: date
    liability_account_id: str | None = None


@dataclass(frozen=True)
class IncomeSource:
    id: str
    user_id: str
    name: str
    amount: Decimal
    frequency: str
    next_pay_date: date


@dataclass(frozen=True)
class FinancialProfile:
    user: User
    as_of: date
    accounts: list[Account] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)
    bills: list[Bill] = field(default_factory=list)
    income_sources: list[IncomeSource] = field(default_factory=list)
    data_warnings: tuple[str, ...] = ()
