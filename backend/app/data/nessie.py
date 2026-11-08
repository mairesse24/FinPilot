"""Read-only Nessie sandbox import. Never creates bank transactions or merges demo rows.

Balances are authoritative snapshots, not reconstructed from incomplete histories.
Schedules are explicit inputs: deposits alone do not establish future salary dates.
"""
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.calc.models import Account, Bill, IncomeSource, Transaction, User
from app.db.memory import InMemoryRepository
from app.db.repository import SeedDataset


class Schedule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    amount: Decimal = Field(gt=0, allow_inf_nan=False, decimal_places=2)
    frequency: str = Field(pattern="^(weekly|biweekly|monthly)$")
    date: date
    category: str = "other"
    liability_account_id: str | None = None


class Schedules(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_id: str
    income: list[Schedule] = []
    bills: list[Schedule] = []
    transaction_categories: dict[str, str] = {}
    default_checking_purchase_category: str | None = None
    loan_balances: dict[str, Decimal] = {}


def money(value, signed=False):
    result = Decimal(str(value))
    if not result.is_finite() or (result < 0 and not signed) or result != result.quantize(Decimal("0.01")):
        raise ValueError("Nessie amounts must be finite nonnegative cents")
    return result


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Invalid Nessie identifier")
    return value


class NessieClient:
    def __init__(self, key, base_url="https://api.nessieisreal.com", client=None):
        if base_url.rstrip("/") not in {"https://api.nessieisreal.com", "https://api.reimaginebanking.com"}:
            raise ValueError("Use an approved HTTPS Nessie sandbox host")
        self.key, self.base_url = key, base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=15, follow_redirects=False)

    def get(self, path):
        try:
            response = self.client.get(self.base_url + path, params={"key": self.key})
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            # httpx exception strings contain the API key in the URL. Do not propagate them.
            raise ValueError("Nessie request failed; check sandbox host, key and customer ID") from None

    def close(self):
        self.client.close()


def import_customer(client, customer_id, as_of, schedules=None):
    uid = identifier(customer_id)
    customer = client.get(f"/customers/{uid}")
    if customer.get("_id") != uid:
        raise ValueError("Nessie returned another customer")
    customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
    # Older seeded sandbox profiles used a product label as the customer's surname.
    # Keep the stable Nessie customer ID, but present the demo persona as a real name.
    if customer_name == "Alex FinPilot Demo":
        customer_name = "Alex Rivera"
    ds = SeedDataset(users=[User(uid, customer_name, "")])
    warnings = ["Nessie sandbox snapshot; restart the API to refresh balances and history.",
                "Internal transfers, credit-card activity and cash withdrawals are excluded from cash-spending history.",
                "Loan balances require explicit confirmed outstanding principal; original loan amounts are not assumed to be current debt."]
    accounts = client.get(f"/customers/{uid}/accounts")
    seen = set()
    for a in accounts:
        aid = identifier(a["_id"])
        if a.get("customer_id") != uid or aid in seen:
            raise ValueError("Duplicate or foreign Nessie account")
        seen.add(aid)
        kind = {"Checking": "checking", "Savings": "savings", "Credit Card": "credit_card"}.get(a["type"])
        if kind is None:
            raise ValueError("Unsupported Nessie account type")
        ds.accounts.append(Account(aid, uid, a.get("nickname") or a["type"], kind, money(a["balance"], signed=kind in {"checking", "savings"})))
        for loan in client.get(f"/accounts/{aid}/loans"):
            lid = identifier(loan['_id'])
            loan_id = f"loan:{lid}"
            if loan_id in seen or loan.get('account_id', aid) != aid:
                raise ValueError("Duplicate or foreign Nessie loan")
            seen.add(loan_id)
            if loan.get('status') != 'approved':
                continue
            if not schedules or lid not in schedules.loan_balances:
                warnings.append("An approved loan has no confirmed outstanding balance and is omitted from net worth; supply loan_balances in the schedule file.")
                continue
            ds.accounts.append(Account(loan_id, uid, loan.get('description') or f"{loan.get('type', 'Unknown')} loan",
                                       'loan', money(schedules.loan_balances[lid])))
            if not any(b.liability_account_id==loan_id for b in schedules.bills):
                warnings.append("Loan payment dates must be supplied as bills; loan monthly_payment alone is not a payment calendar.")
        for endpoint, sign in (("purchases", -1), ("withdrawals", -1), ("deposits", 1)):
            for row in client.get(f"/accounts/{aid}/{endpoint}"):
                if row.get("status") != "completed":
                    continue
                # Live Nessie deposits/withdrawals omit owner fields. Their
                # account-scoped endpoint binds them to the verified account;
                # validate an explicit owner when the API supplies one.
                owner = (row.get("payer_id") if endpoint == "purchases" else
                         row.get("payee_id", row.get("account_id", aid)) if endpoint == "deposits" else
                         row.get("payer_id", row.get("account_id", aid)))
                if owner != aid:
                    raise ValueError("Foreign Nessie transaction")
                rid = f"{endpoint}:{identifier(row['_id'])}"
                if rid in seen:
                    raise ValueError("Duplicate Nessie transaction")
                seen.add(rid)
                when = date.fromisoformat(row.get("purchase_date") or row["transaction_date"])
                if when > as_of:
                    continue
                # ATM withdrawals are cash movement, not verified consumption. Deposits are
                # external inflows, not necessarily earned income. Transfers endpoint is omitted.
                if endpoint == "withdrawals":
                    warnings.append("ATM withdrawals excluded: cash spending is unobserved.")
                    continue
                if kind != "checking":
                    warnings.append("Card activity excluded from checking forecast: repayment schedules must be supplied explicitly.")
                    continue
                category = "other" if sign < 0 else "income"
                mapped = None
                if schedules:
                    mapped = schedules.transaction_categories.get(rid)
                    if mapped is None and sign < 0:
                        mapped = schedules.default_checking_purchase_category
                if mapped is not None:
                    from app.calc.categories import FIXED, VARIABLE
                    category = mapped
                    if category not in FIXED | VARIABLE | {"income", "transfer", "refund"}:
                        raise ValueError("Unsupported transaction category in schedule file")
                    if category == "transfer":
                        continue
                ds.transactions.append(Transaction(rid, aid, sign * money(row["amount"]), category, when))
    if schedules is not None:
        if schedules.customer_id != uid:
            raise ValueError("Schedule file belongs to another customer")
        for i, s in enumerate(schedules.income):
            ds.income_sources.append(IncomeSource(f"income-{i}", uid, s.name, s.amount, s.frequency, s.date))
        for i, s in enumerate(schedules.bills):
            if s.liability_account_id and s.liability_account_id not in {a.id for a in ds.accounts if a.account_type in {'loan','credit_card'}}:
                raise ValueError('Schedule debt bill must link to an imported liability')
            ds.bills.append(Bill(f"bill-{i}", uid, s.name, s.amount, s.category, s.frequency, s.date,s.liability_account_id))
    if not ds.income_sources:
        warnings.append("No confirmed future income schedule; forecast assumes no future deposits.")
    if not ds.bills:
        warnings.append("No confirmed future bills; forecast omits unprovided obligations.")
    if any(t.amount>0 and t.category=='income' for t in ds.transactions):
        warnings.append("Checking deposits are shown as inflows, not verified salary.")
    if any(t.amount<0 and t.category=='other' for t in ds.transactions):
        warnings.append("Unmapped purchases use category other. Map historical scheduled-bill payments to fixed categories to avoid double counting them in variable spending.")
    return ds, list(dict.fromkeys(warnings))


def build_nessie_repo(settings):
    if not settings.nessie_api_key or not settings.nessie_customer_id:
        raise ValueError("DATA_SOURCE=nessie requires NESSIE_API_KEY and NESSIE_CUSTOMER_ID; no demo substitution")
    schedules = None
    if settings.nessie_schedules_file:
        schedules = Schedules.model_validate(json.loads(Path(settings.nessie_schedules_file).read_text()))
    client = NessieClient(settings.nessie_api_key, settings.nessie_base_url)
    try:
        ds, warnings = import_customer(client, settings.nessie_customer_id, settings.as_of_date or date.today(), schedules)
    finally:
        client.close()
    repo = InMemoryRepository(ds)
    repo.source, repo.warnings = "Nessie sandbox", warnings
    repo.loaded_at = datetime.now(timezone.utc).isoformat()
    return repo
