import pytest

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
        "get_economic_resilience","run_economic_simulation"}
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
