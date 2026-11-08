from datetime import timedelta
from decimal import Decimal as D

from app.calc.models import Account, Bill, IncomeSource
from app.calc.projection import project_balance
from tests.factories import AS_OF, UID, empty_profile, make_profile


def _p(cash="1000"):
    return make_profile(
        accounts=[Account("c", UID, "C", "checking", D(cash))],
        bills=[Bill("b", UID, "B", D("300"), "rent", "monthly", AS_OF + timedelta(days=2))],
        income_sources=[IncomeSource("i", UID, "P", D("500"), "monthly", AS_OF + timedelta(days=3))])


def test_projection_applies_income_bills_and_spend():
    pts = project_balance(_p(), 3, lambda d: D("10"))
    assert [x.balance for x in pts] == [D("990"), D("680"), D("1170")]


def test_projection_length_and_dates():
    pts = project_balance(_p(), 7, lambda d: D("0"))
    assert len(pts) == 7 and pts[0].date == AS_OF + timedelta(days=1)


def test_projection_on_empty_profile_is_flat_zero():
    assert {x.balance for x in project_balance(empty_profile(), 5, lambda d: D("0"))} == {D("0")}


def test_projection_can_go_negative():
    pts = project_balance(make_profile(accounts=[Account("c", UID, "C", "checking", D("-50"))],
                                       bills=[], income_sources=[]), 2, lambda d: D("5"))
    assert pts[-1].balance == D("-60")
