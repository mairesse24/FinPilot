"""Pure metrics over a FinancialProfile. All zero-safe."""
import calendar
from datetime import date, timedelta
from decimal import Decimal

from app.calc.models import Bill, FinancialProfile

ZERO = Decimal("0")
CENTS = Decimal("0.01")
NON_CONSUMPTION = {"transfer", "internal_transfer", "external_transfer", "debt_payment", "refund"}


def checking_variable_transactions(p: FinancialProfile):
    """Cash spending only; card consumption is paid through scheduled repayments."""
    from app.calc.categories import VARIABLE
    checking = {a.id for a in p.accounts if a.account_type == "checking"}
    return [t for t in p.transactions if t.account_id in checking and t.amount < 0 and t.category in VARIABLE]


def _q(v: Decimal) -> Decimal:
    return v.quantize(CENTS)


def add_months(d: date, n: int, day: int | None = None) -> date:
    """Shift by n months, clamping to month end. `day` overrides the target day-of-month."""
    m = d.month - 1 + n
    y, mo = d.year + m // 12, m % 12 + 1
    return date(y, mo, min(day or d.day, calendar.monthrange(y, mo)[1]))


def _sum_accounts(p: FinancialProfile, types: tuple[str, ...]) -> Decimal:
    return sum((a.balance for a in p.accounts if a.account_type in types), ZERO)


def cash_balance(p: FinancialProfile) -> Decimal:
    return _sum_accounts(p, ("checking",))


def liquid_balance(p: FinancialProfile) -> Decimal:
    return _sum_accounts(p, ("checking", "savings"))


def assets(p: FinancialProfile) -> Decimal:
    return liquid_balance(p)


def liabilities(p: FinancialProfile) -> Decimal:
    return _sum_accounts(p, ("credit_card", "loan"))


def net_worth(p: FinancialProfile) -> Decimal:
    return assets(p) - liabilities(p)


def _in_window(p: FinancialProfile, days: int):
    start = p.as_of - timedelta(days=days)
    return [t for t in p.transactions if start < t.date <= p.as_of]


def window_inflow(p: FinancialProfile, days: int) -> Decimal:
    return sum((t.amount for t in _in_window(p, days) if t.amount > 0 and t.category not in NON_CONSUMPTION), ZERO)


def window_outflow(p: FinancialProfile, days: int) -> Decimal:
    """Positive number: total money out in the window."""
    return sum((-t.amount for t in _in_window(p, days) if t.amount < 0 and t.category not in NON_CONSUMPTION), ZERO)


def spend_by_category(p: FinancialProfile, days: int) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for t in _in_window(p, days):
        if t.amount < 0 and t.category not in NON_CONSUMPTION:
            out[t.category] = out.get(t.category, ZERO) - t.amount
    return out


def _per_30_days(amount: Decimal, frequency: str) -> Decimal:
    if frequency == "weekly":
        return amount * 30 / 7
    if frequency == "biweekly":
        return amount * 30 / 14
    return amount


def monthly_income(p: FinancialProfile) -> Decimal:
    return _q(sum((_per_30_days(s.amount, s.frequency) for s in p.income_sources), ZERO))


def monthly_debt_payments(p: FinancialProfile) -> Decimal:
    liabilities = {a.id: a.min_payment or ZERO for a in p.accounts
                   if a.account_type in ("credit_card", "loan")}
    linked, unlinked = {}, ZERO
    for b in p.bills:
        if b.category != "debt_payment":
            continue
        amount = _per_30_days(b.amount, b.frequency)
        if b.liability_account_id:
            if b.liability_account_id not in liabilities:
                raise ValueError("Debt bill must link to a liability owned by this profile")
            linked[b.liability_account_id] = linked.get(b.liability_account_id, ZERO)+amount
        else:
            unlinked += amount
    confirmed = sum((max(liabilities[aid], amount) for aid, amount in linked.items()), ZERO)
    remaining = sum((v for aid, v in liabilities.items() if aid not in linked), ZERO)
    # Legacy rows do not identify which debt a bill pays. These are alternative
    # observations of obligations, not additive debt. A floor avoids duplicating
    # the same payment; explicit linkage is needed for an exact total.
    return _q(confirmed + max(remaining, unlinked))


def _occurrences(start: date, frequency: str, as_of: date, days: int) -> list[date]:
    end = as_of + timedelta(days=days)
    out: list[date] = []
    d, i = start, 0
    while d <= end:
        if d > as_of:
            out.append(d)
        i += 1
        if frequency == "weekly":
            d = start + timedelta(days=7 * i)
        elif frequency == "biweekly":
            d = start + timedelta(days=14 * i)
        else:
            d = add_months(start, i)
    return out


def bill_occurrences(p: FinancialProfile, days: int) -> list[tuple[date, Bill]]:
    res = [(d, b) for b in p.bills for d in _occurrences(b.due_date, b.frequency, p.as_of, days)]
    return sorted(res, key=lambda x: x[0])


def income_events(p: FinancialProfile, days: int) -> list[tuple[date, Decimal]]:
    res = [(d, s.amount) for s in p.income_sources
           for d in _occurrences(s.next_pay_date, s.frequency, p.as_of, days)]
    return sorted(res, key=lambda x: x[0])
