from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from app.calc.models import FinancialProfile, Transaction, User


@dataclass
class SeedDataset:
    users: list = field(default_factory=list)
    accounts: list = field(default_factory=list)
    transactions: list = field(default_factory=list)
    bills: list = field(default_factory=list)
    income_sources: list = field(default_factory=list)


class Repository(Protocol):
    def get_user(self, user_id: str) -> User | None: ...

    def load_profile(self, user_id: str, as_of: date) -> FinancialProfile | None:
        """Profile with transactions from the last 180 days up to as_of."""

    def list_transactions(self, user_id: str, *, limit: int, offset: int,
                          category: str | None = None, date_from: date | None = None,
                          date_to: date | None = None) -> tuple[list[Transaction], int]:
        """Newest first; returns (page, total matching)."""

    def reset(self) -> None: ...

    def insert_dataset(self, ds: SeedDataset) -> None: ...

    def ping(self) -> bool: ...
