from datetime import date, timedelta
from decimal import Decimal

from app.data.synthetic import DEMO_USER_ID, build_demo_customer, build_random_customers

AS_OF = date(2026, 11, 7)


def test_demo_customer_is_deterministic():
    assert build_demo_customer(AS_OF) == build_demo_customer(AS_OF)


def test_demo_checking_balance_is_2400():
    ds = build_demo_customer(AS_OF)
    assert ds.users[0].id == DEMO_USER_ID
    assert [a.balance for a in ds.accounts if a.account_type == "checking"] == [Decimal("2400.00")]


def test_demo_has_12_months_of_history():
    ds = build_demo_customer(AS_OF)
    assert min(t.date for t in ds.transactions) <= AS_OF - timedelta(days=330)
    assert max(t.date for t in ds.transactions) <= AS_OF
    assert any(t.category == "dining" for t in ds.transactions)


def test_random_customers_seeded_and_varied():
    a, b = build_random_customers(AS_OF, 10, 42), build_random_customers(AS_OF, 10, 42)
    assert a == b
    assert len({s.amount for s in a.income_sources}) >= 3
    for u in a.users:
        assert any(x.user_id == u.id and x.account_type == "checking" for x in a.accounts)


def test_all_amounts_are_decimal_with_two_places():
    for ds in (build_demo_customer(AS_OF), build_random_customers(AS_OF, 3)):
        for t in ds.transactions:
            assert isinstance(t.amount, Decimal) and t.amount == t.amount.quantize(Decimal("0.01"))
        for a in ds.accounts:
            assert isinstance(a.balance, Decimal) and a.balance == a.balance.quantize(Decimal("0.01"))
