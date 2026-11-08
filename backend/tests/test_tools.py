from decimal import Decimal

import pytest

from app.calc.models import Account
from app.services.gateway import Gateway
from app.tools.registry import ToolRegistry
from tests.factories import make_profile


def reg():
    return ToolRegistry(make_profile(), Gateway("baseline"))


def test_registry_specs_are_valid_function_schemas():
    specs = reg().specs()
    assert {s["function"]["name"] for s in specs} == {
        "get_accounts_summary", "get_health_score", "get_forecast",
        "get_guardian_alerts", "run_simulation","get_economic_conditions","get_financial_assessment",
        "get_economic_resilience","run_economic_simulation","evaluate_purchase"}
    for s in specs:
        assert s["type"] == "function" and s["function"]["description"]
        assert s["function"]["parameters"]["type"] == "object"


def test_registry_rejects_unknown_tool_and_bad_args():
    r = reg()
    with pytest.raises(ValueError):
        r.call("drop_tables", {})
    with pytest.raises(ValueError):
        r.call("get_forecast", {"days": 45})
    with pytest.raises(ValueError):
        r.call("run_simulation", {"reduction_amount": -5})
    with pytest.raises(ValueError):
        r.call("get_health_score", {"bogus": 1})


def test_registry_tools_run_and_are_json_serializable():
    import json
    r = reg()
    for name, args in [("get_accounts_summary", {}), ("get_health_score", {}),
                       ("get_forecast", {"days": 7}), ("get_guardian_alerts", {}),
                       ("run_simulation", {"reduction_amount": 100})]:
        json.dumps(r.call(name, args))


def test_purchase_gift_portfolio_reconciles_assets_debt_and_net_worth():
    result = reg().call("evaluate_purchase", {
        "amount": 20000, "item": "car", "gift_amount": 2000,
    })
    scenario = result["portfolio_scenario"]
    assert result["available_source_funds"] == 3500.0
    assert result["source_funding_gap"] == 16500.0
    assert scenario == {
        "gift_amount": 2000.0,
        "assumed_down_payment": 2000.0,
        "hypothetical_financing_needed": 18000.0,
        "liquid_after_down_payment": 1500.0,
        "assets_after_purchase": 21500.0,
        "liabilities_after_purchase": 20300.0,
        "net_worth_after_purchase": 1200.0,
        "net_worth_change_before_fees_and_depreciation": 2000.0,
    }
    assert scenario["assets_after_purchase"] - scenario["liabilities_after_purchase"] == scenario["net_worth_after_purchase"]


def test_purchase_using_ninety_percent_of_savings_triggers_reserve_warning():
    profile = make_profile(accounts=[
        Account("checking", "u-test", "Checking", "checking", Decimal("1000")),
        Account("savings", "u-test", "Savings", "savings", Decimal("5000")),
    ])
    result = ToolRegistry(profile, Gateway("baseline")).call("evaluate_purchase", {
        "amount": 4500, "item": "purchase", "funding_source": "savings",
    })
    assert result["source_usage_percent"] == 90.0
    assert result["source_funds_after_purchase"] == 500.0
    assert result["reserve_warning"]["severity"] == "high"
    assert "90%" in result["reserve_warning"]["message"]
