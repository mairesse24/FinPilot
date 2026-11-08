from datetime import date, timedelta
from decimal import Decimal as D

from app.calc import metrics as m
from app.calc.models import Bill, IncomeSource, Transaction
from tests.factories import AS_OF, UID, empty_profile, make_profile


def test_net_worth_subtracts_liabilities():
    assert m.net_worth(make_profile()) == D("-800")


def test_monthly_income_normalizes_frequency():
    def inc(amt, freq):
        return m.monthly_income(make_profile(income_sources=[
            IncomeSource("i", UID, "x", D(amt), freq, AS_OF)]))
    assert inc("1400", "biweekly") == D("3000.00")
    assert inc("700", "weekly") == D("3000.00")
    assert inc("3000", "monthly") == D("3000.00")


def test_bill_occurrences_repeat_by_frequency():
    mk = lambda f, d: make_profile(bills=[Bill("b", UID, "B", D("10"), "rent", f, d)])
    monthly = m.bill_occurrences(mk("monthly", date(2026, 11, 10)), 90)
    assert len(monthly) == 3
    weekly = m.bill_occurrences(mk("weekly", date(2026, 11, 8)), 30)
    assert len(weekly) in (4, 5)
    assert all(AS_OF < d <= AS_OF + timedelta(days=30) for d, _ in weekly)


def test_spend_by_category_ignores_income_and_outside_window():
    p = make_profile(transactions=[
        Transaction("1", "a", D("-10"), "dining", AS_OF),
        Transaction("2", "a", D("500"), "income", AS_OF),
        Transaction("3", "a", D("-99"), "dining", AS_OF - timedelta(days=40)),
    ])
    assert m.spend_by_category(p, 30) == {"dining": D("10")}


def test_empty_profile_metrics_are_zero():
    p = empty_profile()
    assert m.net_worth(p) == m.cash_balance(p) == m.liquid_balance(p) == 0
    assert m.window_inflow(p, 30) == m.window_outflow(p, 30) == 0
    assert m.monthly_income(p) == m.monthly_debt_payments(p) == 0
    assert m.spend_by_category(p, 30) == {}
    assert m.bill_occurrences(p, 30) == [] and m.income_events(p, 30) == []
