"""Render financial statements from registry results, never from model-authored prose.

Gemini selects statements and their order. The server owns each statement's values,
units, and baseline/scenario relationship; matching a numeric allowlist is not enough.
"""


def usd(value) -> str:
    return f"${float(value):,.2f}"


def statements(name: str, args: dict, result: dict) -> list[str]:
    if name == "get_accounts_summary":
        return [
            f"Your checking balance is {usd(result['cash_balance'])}. "
            f"Your net worth is {usd(result['net_worth'])}, with assets of "
            f"{usd(result['assets'])} and liabilities of {usd(result['liabilities'])}.",
            *[f"{a['name']} ({a['account_type']}): {usd(a['balance'])}."
              for a in result["accounts"]],
        ]
    if name == "get_health_score":
        return [
            f"Your financial health score is {result['score']:g} out of 100.",
            *[f"{c['name']}: {c['score']:g}/100. {c.get('explanation', '')}".strip()
              for c in result["components"]],
            *result["strengths"], *result["weaknesses"],
        ]
    if name == "get_forecast":
        low = result["projected_low"]
        facts = [f"The {result['days']}-day forecast (data as of {result.get('as_of', 'the current snapshot')}) uses a safety buffer of "
                 f"{usd(result['safety_buffer'])}."]
        if low:
            facts.append(f"Over the next {result['days']} days, your lowest projected checking "
                         f"balance is {usd(low['balance'])} on {low['date']}. "
                         + ("This is below your safety buffer." if result["shortfall"]
                            else "This is not below your safety buffer."))
        interval = result.get("low_point_interval")
        if interval:
            facts.append(f"The approximate uncertainty range at that low point is "
                         f"{usd(interval['low'])} to {usd(interval['high'])}.")
        return facts + result["assumptions"]
    if name == "get_guardian_alerts":
        if not result["alerts"]:
            return ["Guardian currently reports no active alerts. This does not guarantee future safety."]
        return [f"Guardian ({a['severity']} priority, {result.get('forecast_days', 30)}-day outlook, "
                f"data as of {result.get('as_of', 'the current snapshot')}): {a['title']}. {a['cause']} "
                f"Action to explore: {a['recommended_action']}"
                for a in result["alerts"]]
    if name == "run_simulation":
        base, scenario = result["baseline_low"], result["scenario_low"]
        facts = [f"I tested a total discretionary spending cut of {usd(args['reduction_amount'])} "
                 f"over {args.get('horizon_days', 30)} days. This is a preview; no accounts were changed."]
        if base and scenario:
            facts.append(f"Your lowest projected balance changes from {usd(base['balance'])} "
                         f"on {base['date']} to {usd(scenario['balance'])} on {scenario['date']}, "
                         f"a change of {usd(result['delta']['low_balance_change'])}.")
        facts.append(f"The baseline has {result['baseline_alerts']} active Guardian alerts; "
                     f"the scenario has {result['scenario_alerts']}. Other risks may remain.")
        if "scenario_health_score" in result:
            facts.append(f"The simulated health score changes from "
                         f"{result['baseline_health_score']:g} to {result['scenario_health_score']:g}.")
        if "scenario_end_balance" in result:
            facts.append(f"The projected ending balance changes from "
                         f"{usd(result['baseline_end_balance'])} to {usd(result['scenario_end_balance'])}.")
        return facts
    raise ValueError("Unsupported financial evidence")
