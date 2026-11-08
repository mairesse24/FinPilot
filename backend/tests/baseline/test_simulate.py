from datetime import timedelta
from decimal import Decimal as D

from app.baseline.forecast import forecast
from app.baseline.simulate import apply_spending_cut, simulate
from app.calc.models import Account, Transaction
from app.schemas.common import SpendingCut
from tests.factories import AS_OF, UID, empty_profile, make_profile


def rich_spender(chk="1000.00"):
    txs = [Transaction(f"d{i}", "a-chk", D("-40.00"), "dining", AS_OF - timedelta(days=i))
           for i in range(90)]
    return make_profile(transactions=txs,
                        accounts=[Account("a-chk", UID, "C", "checking", D(chk))])


def test_cut_raises_projected_low_by_about_reduction():
    p = rich_spender()
    f = forecast(p, 30)
    h = max(1, (f.projected_low.date - AS_OF).days)
    r = simulate(p, SpendingCut(reduction_amount=D("100"), horizon_days=h))
    assert abs(r.delta["low_balance_change"] - 100) <= 1.0


def test_cut_is_capped_at_available_spending():
    p = rich_spender()
    r = simulate(p, SpendingCut(reduction_amount=D("99999"), horizon_days=5))
    assert r.delta["end_balance_change"] <= 5 * 40 + 0.01


def test_cut_never_lowers_balance_or_health():
    r = simulate(rich_spender(), SpendingCut(reduction_amount=D("150"), horizon_days=10))
    assert r.delta["low_balance_change"] >= 0 and r.delta["end_balance_change"] >= 0
    assert r.delta["health_score_change"] >= 0


def test_delta_matches_outcomes():
    r = simulate(rich_spender(), SpendingCut(reduction_amount=D("100"), horizon_days=10))
    assert r.delta["end_balance_change"] == round(
        float(r.scenario.end_balance - r.baseline.end_balance), 2)


def test_cut_only_touches_discretionary():
    p = make_profile()  # groceries only
    assert apply_spending_cut(p, SpendingCut(reduction_amount=D("100"))) == p
    q = apply_spending_cut(rich_spender(), SpendingCut(reduction_amount=D("100"), horizon_days=30))
    cut = sum(-t.amount for t in rich_spender().transactions if t.date > AS_OF - timedelta(days=30)) \
        - sum(-t.amount for t in q.transactions if t.date > AS_OF - timedelta(days=30))
    assert abs(cut - 100) <= D("0.5")


def test_empty_profile_simulation_is_zero_delta():
    r = simulate(empty_profile(), SpendingCut(reduction_amount=D("100")))
    assert set(r.delta.values()) == {0.0}
