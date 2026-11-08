"""Deterministic latency budgets: simulated network delay, real financial tools.

No flaky wall-clock thresholds or live provider calls. These fail if redundant
model rounds or repeated calculation executions are reintroduced.
"""
from dataclasses import replace
from decimal import Decimal

import pytest

from intelligence import copilot
from tests.test_copilot_intelligence import (
    Provider, ask, install, response, settings, repo, tools,
)


@pytest.mark.parametrize("question,calls", [
    ("Explain my biggest risk", [("get_guardian_alerts", {})]),
    ("How was my health score calculated?", [("get_health_score", {})]),
    ("What if I cut $200 over 10 days?", [("run_simulation", {"reduction_amount": 200, "horizon_days": 10})]),
])
def test_common_questions_require_one_network_round(monkeypatch, tools, question, calls):
    clock = [0.0]
    monkeypatch.setattr(copilot.time, "monotonic", lambda: clock[0])
    provider = Provider([response(*calls)])
    generate = provider.generate_content
    def simulated_network(**kwargs):
        clock[0] += 1.0
        return generate(**kwargs)
    provider.generate_content = simulated_network
    original = tools.call
    def simulated_tools(name, args):
        clock[0] += 0.01
        return original(name, args)
    monkeypatch.setattr(tools, "call", simulated_tools)
    install(monkeypatch, provider)
    result = copilot.chat(ask(question), tools)
    assert result.meta.source == "model"
    assert len(provider.requests) == 1
    assert clock[0] <= 1.03
    assert len(result.reply) < 1400
    assert "prototype estimate" in result.reply


def test_duplicate_tool_requests_reuse_verified_evidence(monkeypatch, tools):
    executions = []
    original = tools.call
    def counted(name, args):
        executions.append((name, args))
        return original(name, args)
    monkeypatch.setattr(tools, "call", counted)
    install(monkeypatch, Provider([response(
        ("get_guardian_alerts", {}), ("get_guardian_alerts", {}),
        ("get_health_score", {}), ("get_health_score", {}),
    )]))
    result = copilot.chat(ask("Explain my risk and score"), tools)
    assert [name for name, _ in executions] == ["get_guardian_alerts", "get_health_score"]
    assert len(result.tool_calls) == 2


def test_cache_never_survives_a_new_chat_request(monkeypatch, tools):
    provider = install(monkeypatch, Provider([
        response(("get_accounts_summary", {})), response(("get_accounts_summary", {})),
    ]))
    first = copilot.chat(ask("What is my balance?"), tools)
    account = replace(tools.profile.accounts[0], balance=Decimal("9999"))
    tools.profile = replace(tools.profile, accounts=[account, *tools.profile.accounts[1:]])
    second = copilot.chat(ask("What is my balance now?"), tools)
    assert "$2,400.00" in first.reply and "$9,999.00" in second.reply
    assert len(second.tool_calls) == 2
    assert len(provider.requests) == 2


def test_cache_keys_include_scenario_arguments(monkeypatch, tools):
    install(monkeypatch, Provider([response(
        ("run_simulation", {"reduction_amount": 200, "horizon_days": 10}),
        ("run_simulation", {"reduction_amount": 250, "horizon_days": 10}),
    )]))
    result = copilot.chat(ask("Compare $200 and $250 cuts over 10 days"), tools)
    simulations = [call for call in result.tool_calls if call.name == "run_simulation"]
    assert len(simulations) == 2
    assert "$200.00" in result.reply and "$250.00" in result.reply


def test_invalid_argument_repairs_remain_bounded(monkeypatch, tools):
    tools.settings = tools.settings.model_copy(update={"copilot_max_rounds": 2})
    provider = install(monkeypatch, Provider([
        response(("get_forecast", {"days": 45})), response(("get_forecast", {"days": 45})),
    ]))
    with pytest.raises(copilot.CopilotUnavailable, match="round budget"):
        copilot.chat(ask("Explain my forecast"), tools)
    assert len(provider.requests) == 2


def test_component_focus_does_not_require_another_model_or_calculation(monkeypatch, tools):
    executed = []
    original = tools.call
    def counted(name, args):
        executed.append((name, args))
        return original(name, args)
    monkeypatch.setattr(tools, "call", counted)
    provider = install(monkeypatch, Provider([response(
        ("get_health_score", {"component": "debt"}),
        ("get_health_score", {"component": "readiness"}),
    )]))
    result = copilot.chat(ask("Explain debt and bill readiness"), tools)
    assert len(provider.requests) == 1
    assert executed.count(("get_health_score", {})) == 1
    assert "Debt burden" in result.reply and "Bill readiness" in result.reply
    assert result.tool_calls[-1].args == {}


def test_truncated_tool_selection_falls_back_without_extra_rounds(monkeypatch, tools):
    truncated = response(("run_simulation", {"reduction_amount": 200, "horizon_days": 10}))
    truncated.candidates[0].finish_reason = "MAX_TOKENS"
    provider = install(monkeypatch, Provider([truncated]))
    with pytest.raises(copilot.CopilotUnavailable, match="incomplete"):
        copilot.chat(ask("What if I cut $200?"), tools)
    assert len(provider.requests) == 1
