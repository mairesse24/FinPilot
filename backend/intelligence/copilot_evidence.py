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
    if name == "evaluate_purchase":
        source=result.get('funding_source','liquid')
        gift=result.get('gift_amount',0)
        opening=(f"The {result.get('item','purchase')} price is {usd(result['price'])}. "
                 f"Available {source} funds are {usd(result['available_source_funds'])}, leaving a cash funding gap of {usd(result['source_funding_gap'])}.")
        if gift:
            opening += (f" The portfolio scenario treats the {usd(gift)} gift as a down-payment contribution "
                        f"and therefore requires {usd(result['portfolio_scenario']['hypothetical_financing_needed'])} of financing.")
        facts=[opening,
               f"Current checking is {usd(result['checking'])}, savings are {usd(result['savings'])}, liabilities are {usd(result['liabilities'])}, and net worth is {usd(result['net_worth'])}."]
        portfolio=result.get('portfolio_scenario')
        if portfolio:
            facts.append(f"If the contribution is applied as a down payment, the illustrative remaining financing need is {usd(portfolio['hypothetical_financing_needed'])}. Portfolio assets would be {usd(portfolio['assets_after_purchase'])}, liabilities {usd(portfolio['liabilities_after_purchase'])}, liquid funds {usd(portfolio['liquid_after_down_payment'])}, and net worth {usd(portfolio['net_worth_after_purchase'])} before taxes, fees, depreciation, or transaction costs.")
        if result.get('gift_amount',0)>0:
            facts.append(f"The {usd(result['gift_amount'])} gift or contribution is hypothetical income until received and verified.")
        financing=result.get('financing')
        if financing:
            facts += [f"With {usd(financing['down_payment'])} down, {usd(financing['principal'])} is financed at {financing['apr_percent']:g}% APR for {financing['term_months']} months. The estimated principal-and-interest payment is {usd(financing['monthly_payment'])} per month.",
                      f"Estimated loan payments total {usd(financing['total_of_payments'])}, including {usd(financing['total_interest'])} interest. The down-payment funding gap is {usd(financing['down_payment_funding_gap'])}."]
        facts.append(result['note'])
        return facts
    if name == "get_financial_assessment":
        shown=result.get('score') if result.get('score') is not None else result.get('observed_score')
        qualifier='confirmed-input score' if result.get('score') is not None else f"automatic estimate with {result.get('observed_score_confidence','unknown')} confidence"
        facts=[f"Your FinPilot financial-health {qualifier} is {shown:g} out of 100."] if shown is not None else ["A financial-health score is unavailable because the required evidence is incomplete."]
        return facts+list(result.get('observed_score_limitations',[]))+list(result.get('withheld_reasons',[]))[:2]
    if name == "get_economic_conditions":
        return [f"Economic conditions as of {result['as_of']} are classified as {result['status']}. This is descriptive context, not a market forecast.",
                *result.get('labels',[])[:3]]
    if name == "get_economic_resilience":
        facts=[result.get('note','Economic conditions contextualize vulnerability and do not rewrite the personal score.')]
        facts += [a['cause'] for a in result.get('financial_alerts',[])[:2]]
        facts += [a['cause'] for a in result.get('alerts',[])[:2]]
        return facts
    if name == "run_economic_simulation":
        return [result.get('note','This is a deterministic hypothetical scenario, not a prediction.'),
                f"The hypothetical changes ending checking by {usd(result['ending_checking_change'])} and net worth by {usd(result['net_worth_change'])}."]
    raise ValueError("Unsupported financial evidence")
