from dataclasses import replace
from datetime import date, timedelta

from app.calc.models import FinancialProfile, Transaction, User
from app.db.repository import SeedDataset


class InMemoryRepository:
    def __init__(self, ds: SeedDataset | None = None):
        self.reset()
        if ds:
            self.insert_dataset(ds)

    def reset(self) -> None:
        self._ds = SeedDataset()

    def insert_dataset(self, ds: SeedDataset) -> None:
        for name in ("users", "accounts", "transactions", "bills", "income_sources"):
            getattr(self._ds, name).extend(getattr(ds, name))

    def ping(self) -> bool:
        return True

    def get_user(self, user_id: str) -> User | None:
        return next((u for u in self._ds.users if u.id == user_id), None)

    def _user_txs(self, user_id: str) -> list[Transaction]:
        ids = {a.id for a in self._ds.accounts if a.user_id == user_id}
        return [t for t in self._ds.transactions if t.account_id in ids]

    def load_profile(self, user_id: str, as_of: date) -> FinancialProfile | None:
        user = self.get_user(user_id)
        if user is None:
            return None
        start = as_of - timedelta(days=180)
        txs = [t for t in self._user_txs(user_id) if start < t.date <= as_of]
        return FinancialProfile(
            user=user, as_of=as_of,
            accounts=[a for a in self._ds.accounts if a.user_id == user_id],
            transactions=sorted(txs, key=lambda t: t.date),
            bills=[b for b in self._ds.bills if b.user_id == user_id],
            income_sources=[s for s in self._ds.income_sources if s.user_id == user_id])

    def list_transactions(self, user_id, *, limit, offset, category=None,
                          date_from=None, date_to=None):
        txs = self._user_txs(user_id)
        if category:
            txs = [t for t in txs if t.category == category]
        if date_from:
            txs = [t for t in txs if t.date >= date_from]
        if date_to:
            txs = [t for t in txs if t.date <= date_to]
        txs.sort(key=lambda t: (t.date, t.id), reverse=True)
        return txs[offset:offset + limit], len(txs)
