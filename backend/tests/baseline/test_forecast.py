from datetime import timedelta
from decimal import Decimal as D

from app.baseline.forecast import forecast, weekday_spend_profile
from app.calc.models import Account, Transaction
from tests.factories import AS_OF, UID, empty_profile, make_profile


def test_weekday_profile_means():
    # 90 days back from AS_OF; put 10 on every Monday only
    txs = [Transaction(f"m{i}", "a-chk", D("-10"), "dining", AS_OF - timedelta(days=i))
           for i in range(90) if (AS_OF - timedelta(days=i)).weekday() == 0]
    means, sigma = weekday_spend_profile(make_profile(transactions=txs))
    assert means[0] == D("10") and means[1] == D("0") and sigma > 0


def test_series_length_matches_days():
    assert len(forecast(make_profile(), 30).series) == 30


def test_band_widens_with_horizon():
    s = forecast(make_profile(transactions=[
        Transaction("x", "a-chk", D("-50"), "dining", AS_OF - timedelta(days=2))]), 30).series
    widths = [x.high - x.low for x in s]
    assert widths[-1] > widths[0]


def test_projected_low_is_minimum_point():
    f = forecast(make_profile(), 30)
    assert f.projected_low.balance == min(s.projected_balance for s in f.series)


def test_shortfall_flag_vs_safety_buffer():
    f = forecast(make_profile(), 30)
    assert f.shortfall == (f.projected_low.balance < f.safety_buffer)
    rich = make_profile(accounts=[Account("a-chk", UID, "C", "checking", D("100000"))])
    assert forecast(rich, 30).shortfall is False


def test_empty_profile_forecast_is_flat_and_no_shortfall_crash():
    f = forecast(empty_profile(), 7)
    assert f.series == [] and f.status == "abstained"
    assert f.shortfall is True  # 0 < default buffer; just must not crash


def test_overdrawn_cash_forecast_is_shortfall():
    p = make_profile(accounts=[Account("a-chk", UID, "C", "checking", D("-50"))])
    assert forecast(p, 7).shortfall is True
