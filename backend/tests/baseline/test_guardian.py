from datetime import timedelta
from decimal import Decimal as D

from app.baseline.forecast import forecast
from app.baseline.guardian import evaluate
from app.calc.models import Account, Bill, Transaction
from tests.factories import AS_OF, UID, empty_profile, make_profile


def alerts(p):
    return {a.rule: a for a in evaluate(p, forecast(p, 30))}


def low_profile(**kw):
    accts = [Account("a-chk", UID, "C", "checking", D("1000.00")),
             Account("a-sav", UID, "S", "savings", D("20000.00"))]
    return make_profile(accounts=accts, **kw)


def test_low_balance_alert_fires_with_numbers():
    a = alerts(low_profile())["low_projected_balance"]
    assert a.numbers["current"] == 1000.0 and a.numbers["safety_buffer"] == 500.0
    assert a.suggested_scenario.reduction_amount % 50 == 0 and a.suggested_scenario.reduction_amount >= 50


def test_low_balance_alert_absent_when_projection_above_buffer():
    p = make_profile(accounts=[Account("a-chk", UID, "C", "checking", D("100000"))])
    assert "low_projected_balance" not in alerts(p)


def test_suggested_scenario_horizon_matches_low_date():
    p = low_profile()
    f = forecast(p, 30)
    a = [x for x in evaluate(p, f) if x.rule == "low_projected_balance"][0]
    assert a.suggested_scenario.horizon_days == max(1, (f.projected_low.date - AS_OF).days)


def test_overdrawn_profile_is_high_severity():
    p = make_profile(accounts=[Account("a-chk", UID, "C", "checking", D("-50"))])
    assert alerts(p)["low_projected_balance"].severity == "high"


def test_debt_burden_threshold_036():
    # income 1400 biweekly -> ~3000/mo; card 25 + loan 100 = 125 -> ok
    assert "high_debt_burden" not in alerts(make_profile())
    p = make_profile(accounts=[Account("a-chk", UID, "C", "checking", D("1000")),
                               Account("a-l", UID, "L", "loan", D("9000"), min_payment=D("1700"))])
    assert alerts(p)["high_debt_burden"].severity == "high"


def test_emergency_savings_severity_levels():
    def sav(x):
        return make_profile(accounts=[Account("a-chk", UID, "C", "checking", D("100")),
                                      Account("a-sav", UID, "S", "savings", D(x))])
    # essentials ~ 20/day groceries = ~600/mo
    assert alerts(sav("100"))["low_emergency_savings"].severity == "high"
    assert alerts(sav("800"))["low_emergency_savings"].severity == "medium"
    assert "low_emergency_savings" not in alerts(sav("5000"))


def test_every_alert_has_cause_numbers_action_and_severity():
    for a in evaluate(low_profile(), forecast(low_profile(), 30)):
        assert a.cause and a.numbers and a.recommended_action and a.severity in ("low", "medium", "high")


def test_sorted_high_first():
    p = make_profile(accounts=[Account("a-chk", UID, "C", "checking", D("-50"))])
    sev = [a.severity for a in evaluate(p, forecast(p, 30))]
    assert sev == sorted(sev, key=["high", "medium", "low"].index)


def test_empty_profile_returns_no_emergency_alert_and_no_crash():
    p = empty_profile()
    assert "low_emergency_savings" not in alerts(p)
    assert "high_debt_burden" not in alerts(p)
