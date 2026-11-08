import pytest
from pydantic import ValidationError

from app.schemas.common import SpendingCut


@pytest.mark.parametrize("kw", [{"reduction_amount": 0}, {"reduction_amount": -5},
                                {"reduction_amount": 10, "horizon_days": 0},
                                {"reduction_amount": 10, "horizon_days": 91}])
def test_spending_cut_rejects_bad_values(kw):
    with pytest.raises(ValidationError):
        SpendingCut(**kw)


def test_spending_cut_defaults_and_json_number():
    c = SpendingCut(reduction_amount=200)
    assert c.horizon_days == 30 and c.model_dump(mode="json")["reduction_amount"] == 200.0
