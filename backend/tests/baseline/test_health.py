from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D

import pytest

from app.baseline.health import compute_health_score
from app.calc.models import Account, Bill, IncomeSource, Transaction
from tests.factories import AS_OF, UID, empty_profile, make_profile


def comp(r, key):
    return next(c for c in r.components if c.key == key)


def debt_profile(debt, income=1000):
    return empty_profile().__class__(
        user=empty_profile().user, as_of=AS_OF,
        accounts=[Account("c", UID, "Card", "credit_card", D("100"), min_payment=D(str(debt)))],
        income_sources=[IncomeSource("i", UID, "Pay", D(str(income)), "monthly", AS_OF)])


def test_weights_sum_to_100_and_five_components():
    r = compute_health_score(make_profile())
    assert len(r.components) == 5
    assert sum(c.weight for c in r.components) == 100


def test_total_is_weighted_sum():
    r = compute_health_score(make_profile())
    assert r.score == pytest.approx(sum(c.weight * c.score for c in r.components) / 100, abs=0.1)
    assert all(c.explanation for c in r.components)


def test_strong_profile_scores_high():
    p = make_profile(accounts=[Account("a-chk", UID, "Checking", "checking", D("5000")),
                               Account("a-sav", UID, "Savings", "savings", D("20000"))],
                     bills=[])
    r = compute_health_score(p)
    assert comp(r, "emergency").score == 100
    assert comp(r, "debt").score == 100
    assert r.score >= 75
    assert r.strengths


@pytest.mark.parametrize("debt,expected", [(100, 100), (500, 0), (300, 50)])
def test_debt_anchor_points(debt, expected):
    assert comp(compute_health_score(debt_profile(debt)), "debt").score == pytest.approx(expected)


def test_empty_profile_is_in_range_and_no_exception():
    r = compute_health_score(empty_profile())
    assert 0 <= r.score <= 100
    assert all(0 <= c.score <= 100 for c in r.components)


def test_overdrawn_checking_scores_readiness_zero():
    p = make_profile(accounts=[Account("a-chk", UID, "Checking", "checking", D("-200"))])
    assert comp(compute_health_score(p), "readiness").score == 0


def test_liabilities_only_profile_in_range():
    p = empty_profile()
    p = p.__class__(user=p.user, as_of=AS_OF, accounts=[
        Account("l", UID, "Loan", "loan", D("9000"), min_payment=D("300"))])
    r = compute_health_score(p)
    assert 0 <= r.score <= 100
    assert comp(r, "debt").score == 0
