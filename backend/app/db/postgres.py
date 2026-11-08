"""Postgres (Supabase) repository. Ids are uuid columns, exposed as str."""
from datetime import date, timedelta
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.calc.models import Account, Bill, FinancialProfile, IncomeSource, Transaction, User
from app.db.repository import SeedDataset

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
_TABLES = "financial_snapshots, risk_alerts, transactions, recurring_bills, income_sources, accounts, users"

_USER = "id::text AS id, name, email, safety_buffer"
_ACCOUNT = ("id::text AS id, user_id::text AS user_id, name, account_type, balance, apr, "
            "min_payment, credit_limit")
_TX = "t.id::text AS id, t.account_id::text AS account_id, t.amount, t.category, t.date"
_BILL = "id::text AS id, user_id::text AS user_id, name, amount, category, frequency, due_date, to_jsonb(recurring_bills)->>'liability_account_id' AS liability_account_id"
_INCOME = "id::text AS id, user_id::text AS user_id, name, amount, frequency, next_pay_date"


class PgRepository:
    def __init__(self, database_url: str):
        self._pool = ConnectionPool(
            database_url, min_size=1, max_size=5, open=True, timeout=15,
            kwargs={"row_factory": dict_row, "prepare_threshold": None})

    def apply_schema(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(SCHEMA_PATH.read_text())

    def ping(self) -> bool:
        try:
            with self._pool.connection() as conn:
                return conn.execute("SELECT 1 AS ok").fetchone()["ok"] == 1
        except Exception:
            return False

    def get_user(self, user_id: str) -> User | None:
        try:
            with self._pool.connection() as conn:
                row = conn.execute(f"SELECT {_USER} FROM users WHERE id = %s::uuid",
                                   (user_id,)).fetchone()
        except Exception as exc:
            if _is_bad_uuid(exc):
                return None
            raise
        return User(**row) if row else None

    def load_profile(self, user_id: str, as_of: date) -> FinancialProfile | None:
        user = self.get_user(user_id)
        if user is None:
            return None
        start = as_of - timedelta(days=180)
        with self._pool.connection() as conn:
            accounts = conn.execute(
                f"SELECT {_ACCOUNT} FROM accounts WHERE user_id = %s::uuid ORDER BY name, id",
                (user_id,)).fetchall()
            txs = conn.execute(
                f"SELECT {_TX} FROM transactions t JOIN accounts a ON a.id = t.account_id "
                "WHERE a.user_id = %s::uuid AND t.date > %s AND t.date <= %s "
                "ORDER BY t.date, t.id", (user_id, start, as_of)).fetchall()
            bills = conn.execute(
                f"SELECT {_BILL} FROM recurring_bills WHERE user_id = %s::uuid ORDER BY due_date, id",
                (user_id,)).fetchall()
            income = conn.execute(
                f"SELECT {_INCOME} FROM income_sources WHERE user_id = %s::uuid ORDER BY id",
                (user_id,)).fetchall()
        return FinancialProfile(
            user=user, as_of=as_of,
            accounts=[Account(**r) for r in accounts],
            transactions=[Transaction(**r) for r in txs],
            bills=[Bill(**r) for r in bills],
            income_sources=[IncomeSource(**r) for r in income])

    def list_transactions(self, user_id, *, limit, offset, category=None,
                          date_from=None, date_to=None):
        where = ["a.user_id = %s::uuid"]
        params: list = [user_id]
        if category:
            where.append("t.category = %s")
            params.append(category)
        if date_from:
            where.append("t.date >= %s")
            params.append(date_from)
        if date_to:
            where.append("t.date <= %s")
            params.append(date_to)
        clause = " AND ".join(where)
        frm = "FROM transactions t JOIN accounts a ON a.id = t.account_id WHERE " + clause
        with self._pool.connection() as conn:
            total = conn.execute(f"SELECT count(*) AS n {frm}", params).fetchone()["n"]
            rows = conn.execute(
                f"SELECT {_TX} {frm} ORDER BY t.date DESC, t.id DESC LIMIT %s OFFSET %s",
                [*params, limit, offset]).fetchall()
        return [Transaction(**r) for r in rows], total

    def reset(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE")

    def insert_dataset(self, ds: SeedDataset) -> None:
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO users (id, name, email, safety_buffer) VALUES (%s,%s,%s,%s)",
                [(u.id, u.name, u.email, u.safety_buffer) for u in ds.users])
            cur.executemany(
                "INSERT INTO accounts (id, user_id, name, account_type, balance, apr, "
                "min_payment, credit_limit) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                [(a.id, a.user_id, a.name, a.account_type, a.balance, a.apr, a.min_payment,
                  a.credit_limit) for a in ds.accounts])
            cur.executemany(
                "INSERT INTO transactions (id, account_id, amount, category, date) "
                "VALUES (%s,%s,%s,%s,%s)",
                [(t.id, t.account_id, t.amount, t.category, t.date) for t in ds.transactions])
            cur.executemany(
                "INSERT INTO recurring_bills (id, user_id, name, amount, category, frequency, "
                "due_date) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                [(b.id, b.user_id, b.name, b.amount, b.category, b.frequency, b.due_date)
                 for b in ds.bills])
            for bill in ds.bills:
                if bill.liability_account_id:
                    cur.execute("UPDATE recurring_bills SET liability_account_id=%s::uuid WHERE id=%s::uuid",
                                (bill.liability_account_id,bill.id))
            cur.executemany(
                "INSERT INTO income_sources (id, user_id, name, amount, frequency, next_pay_date) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                [(s.id, s.user_id, s.name, s.amount, s.frequency, s.next_pay_date)
                 for s in ds.income_sources])

    def close(self) -> None:
        self._pool.close()


def _is_bad_uuid(exc: Exception) -> bool:
    return type(exc).__name__ in ("InvalidTextRepresentation", "DataError")
