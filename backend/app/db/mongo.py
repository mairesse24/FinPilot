"""MongoDB repository. Money is stored as Decimal128, dates as ISO "YYYY-MM-DD" strings."""
from datetime import date, timedelta
from decimal import Decimal

import pymongo
from bson import Decimal128

from app.calc.models import Account, Bill, FinancialProfile, IncomeSource, Transaction, User
from app.db.repository import SeedDataset

_COLLECTIONS = ("users", "accounts", "transactions", "recurring_bills", "income_sources")


def _to_decimal128(value: Decimal) -> Decimal128:
    return Decimal128(value)


def _from_decimal128(value: Decimal128) -> Decimal:
    return value.to_decimal()


def _m(value):  # optional money -> Decimal128 | None
    return None if value is None else _to_decimal128(value)


def _d(value):  # optional Decimal128 -> Decimal | None
    return None if value is None else _from_decimal128(value)


def _user(r) -> User:
    return User(id=r["_id"], name=r["name"], email=r["email"], safety_buffer=_from_decimal128(r["safety_buffer"]))


def _account(r) -> Account:
    return Account(id=r["_id"], user_id=r["user_id"], name=r["name"], account_type=r["account_type"],
                   balance=_from_decimal128(r["balance"]), apr=_d(r.get("apr")),
                   min_payment=_d(r.get("min_payment")), credit_limit=_d(r.get("credit_limit")))


def _tx(r) -> Transaction:
    return Transaction(id=r["_id"], account_id=r["account_id"], amount=_from_decimal128(r["amount"]),
                       category=r["category"], date=date.fromisoformat(r["date"]))


def _bill(r) -> Bill:
    return Bill(id=r["_id"], user_id=r["user_id"], name=r["name"], amount=_from_decimal128(r["amount"]),
                category=r["category"], frequency=r["frequency"], due_date=date.fromisoformat(r["due_date"]))


def _income(r) -> IncomeSource:
    return IncomeSource(id=r["_id"], user_id=r["user_id"], name=r["name"], amount=_from_decimal128(r["amount"]),
                        frequency=r["frequency"], next_pay_date=date.fromisoformat(r["next_pay_date"]))


class MongoRepository:
    def __init__(self, uri: str, db_name: str = "finpilot", client=None):
        if client is None:
            try:
                client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
            except Exception as exc:
                # Never chain or echo the original error: it can contain the connection string.
                raise RuntimeError(f"could not create MongoDB client ({type(exc).__name__})") from None
        self._client = client
        self._db = client[db_name]

    def close(self) -> None:
        self._client.close()

    def ping(self) -> bool:
        try:
            self._client.admin.command("ping")
            return True
        except Exception:
            return False

    def reset(self) -> None:
        for name in _COLLECTIONS:
            self._db.drop_collection(name)

    def insert_dataset(self, ds: SeedDataset) -> None:
        db = self._db
        acct_owner = {a.id: a.user_id for a in ds.accounts}
        if ds.users:
            db["users"].insert_many([
                {"_id": u.id, "name": u.name, "email": u.email, "safety_buffer": _to_decimal128(u.safety_buffer)}
                for u in ds.users])
        if ds.accounts:
            db["accounts"].insert_many([
                {"_id": a.id, "user_id": a.user_id, "name": a.name, "account_type": a.account_type,
                 "balance": _to_decimal128(a.balance), "apr": _m(a.apr), "min_payment": _m(a.min_payment),
                 "credit_limit": _m(a.credit_limit)} for a in ds.accounts])
        if ds.transactions:
            db["transactions"].insert_many([
                {"_id": t.id, "user_id": acct_owner.get(t.account_id), "account_id": t.account_id,
                 "amount": _to_decimal128(t.amount), "category": t.category, "date": t.date.isoformat()}
                for t in ds.transactions])
        if ds.bills:
            db["recurring_bills"].insert_many([
                {"_id": b.id, "user_id": b.user_id, "name": b.name, "amount": _to_decimal128(b.amount),
                 "category": b.category, "frequency": b.frequency, "due_date": b.due_date.isoformat()}
                for b in ds.bills])
        if ds.income_sources:
            db["income_sources"].insert_many([
                {"_id": s.id, "user_id": s.user_id, "name": s.name, "amount": _to_decimal128(s.amount),
                 "frequency": s.frequency, "next_pay_date": s.next_pay_date.isoformat()}
                for s in ds.income_sources])
        db["transactions"].create_index([("user_id", 1), ("date", -1)])
        db["transactions"].create_index([("user_id", 1), ("category", 1), ("date", -1)])

    def get_user(self, user_id: str) -> User | None:
        r = self._db["users"].find_one({"_id": user_id})
        return _user(r) if r else None

    def load_profile(self, user_id: str, as_of: date) -> FinancialProfile | None:
        user = self.get_user(user_id)
        if user is None:
            return None
        # Same window as the Postgres/in-memory repositories: (as_of - 180d, as_of].
        start = (as_of - timedelta(days=180)).isoformat()
        db = self._db
        txs = db["transactions"].find(
            {"user_id": user_id, "date": {"$gt": start, "$lte": as_of.isoformat()}}
        ).sort([("date", 1), ("_id", 1)])
        return FinancialProfile(
            user=user, as_of=as_of,
            accounts=[_account(r) for r in db["accounts"].find({"user_id": user_id}).sort([("name", 1), ("_id", 1)])],
            transactions=[_tx(r) for r in txs],
            bills=[_bill(r) for r in db["recurring_bills"].find({"user_id": user_id}).sort([("due_date", 1), ("_id", 1)])],
            income_sources=[_income(r) for r in db["income_sources"].find({"user_id": user_id}).sort("_id", 1)])

    def list_transactions(self, user_id, *, limit, offset, category=None, date_from=None, date_to=None):
        q: dict = {"user_id": user_id}
        if category:
            q["category"] = category
        rng = {}
        if date_from:
            rng["$gte"] = date_from.isoformat()
        if date_to:
            rng["$lte"] = date_to.isoformat()
        if rng:
            q["date"] = rng
        coll = self._db["transactions"]
        total = coll.count_documents(q)
        cur = coll.find(q).sort([("date", -1), ("_id", -1)]).skip(offset).limit(limit)
        return [_tx(r) for r in cur], total
