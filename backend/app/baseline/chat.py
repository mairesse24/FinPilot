"""Keyword-routed baseline copilot. Quotes tool numbers verbatim; never invents any."""
import re
from datetime import datetime, timezone

from app.schemas.chat import ChatMessage, ChatResult, ToolCallRecord
from app.schemas.common import Meta

NOTE = "This is a prototype estimate based on simulated data, not financial advice."
HELP = ("I can help with: your financial health score, cash-flow risks and forecast, and "
        "what-if savings (for example, \"what if I cut $200?\").")


def _usd(v) -> str:
    return f"${float(v):,.2f}"


def _has(text: str, words: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{w}", text) for w in words)


def chat(messages: list[ChatMessage], tools) -> ChatResult:
    text = next((m.content for m in reversed(messages) if m.role == "user"), "").lower()
    followup=bool(re.search(r'\b(consequence|went ahead|go ahead|did it|what happens|impact)\b',text))
    purchase_text=text
    if followup:
        purchase_text=next((m.content.lower() for m in reversed(messages[:-1])
            if m.role=='user' and re.search(r'\$\s*[\d,]+',m.content) and _has(m.content.lower(),('buy','purchase','car','vehicle','house','home','tv'))),text)
    calls: list[ToolCallRecord] = []

    def use(name: str, args: dict, summary: str | None = None) -> dict:
        res = tools.call(name, args)
        calls.append(ToolCallRecord(name=name, args=args, summary=summary or f"called {name}"))
        return res

    purchase_amount=re.search(r'\$\s*([\d,]+(?:\.\d+)?)',purchase_text)
    if purchase_amount and (_has(purchase_text,("buy","purchase","car","vehicle","house","home","tv")) or followup):
        amount=float(purchase_amount.group(1).replace(',',''))
        item='car' if _has(purchase_text,("car","vehicle")) else 'home' if _has(purchase_text,("house","home")) else 'tv' if _has(purchase_text,("tv",)) else 'purchase'
        args={'amount':amount,'item':item}
        if 'saving' in purchase_text:args['funding_source']='savings'
        down=(re.search(r'(?:put|pay)\s*\$\s*([\d,]+(?:\.\d+)?)\s*down',purchase_text) or
              re.search(r'down payment(?:\s+of|\s+is)?\s*\$\s*([\d,]+(?:\.\d+)?)',purchase_text))
        apr=re.search(r'apr(?:\s+is|\s+of)?\s*(\d+(?:\.\d+)?)\s*%',purchase_text)
        term=(re.search(r'(?:term\s+is\s+)?(\d+)\s*months?',purchase_text) or re.search(r'(\d+)[ -]month',purchase_text))
        if down and apr and term:args.update(down_payment=float(down.group(1).replace(',','')),
            apr_percent=float(apr.group(1)),term_months=int(term.group(1)))
        r=use('evaluate_purchase',args,'compared proposed purchase and supplied financing terms with verified balances')
        reply=(f"The purchase price is {_usd(r['price'])}. You have {_usd(r['liquid_funds'])} in checking and savings; "
               f"current checking is {_usd(r['checking'])}, liabilities are {_usd(r['liabilities'])}, and net worth is {_usd(r['net_worth'])}. ")
        if r['funding_source']=='savings':
            reply+=f"Because you specified savings, the relevant available amount is {_usd(r['savings'])}, leaving a {_usd(r['source_funding_gap'])} gap. "
        if r['price_to_net_worth'] is not None:reply+=f"The price is {r['price_to_net_worth']:.2f} times current net worth. "
        if r['financing']:
            f=r['financing'];reply+=(f"With {_usd(f['down_payment'])} down, the financed principal is {_usd(f['principal'])}. "
                f"At {f['apr_percent']:g}% APR for {f['term_months']} months, the estimated principal-and-interest payment is {_usd(f['monthly_payment'])} per month; "
                f"total loan payments are {_usd(f['total_of_payments'])}, including {_usd(f['total_interest'])} interest. "
                f"The down payment alone exceeds known liquid funds by {_usd(f['down_payment_funding_gap'])}. ")
            if f['payment_to_scheduled_income'] is not None:reply+=f"The payment is {f['payment_to_scheduled_income']:.1%} of scheduled monthly deposits. "
            reply+="Based on the known balances, the stated down payment is not currently funded. Taxes, fees, insurance, maintenance, fuel and depreciation are excluded, so full affordability remains incomplete. "
        else:
            reply+=(f"A cash purchase leaves a funding gap of {_usd(r['source_funding_gap'])}. "
                "A financing payment needs a down payment, APR and loan term. Taxes, fees, insurance and operating costs are also unknown. ")
        if followup and r['source_funding_gap']>0:
            reply+="Going ahead cannot be funded from the stated account alone; it would require other borrowing, an overdraft, or another unmodeled source of money, and would reduce the cash available for upcoming bills and emergencies. "
        reply+="Compare the complete monthly cost with the cash-flow forecast before deciding. "+NOTE
    elif _has(text,("economy","inflation","unemployment","borrowing","market")) and not _has(text,("what if","simulate")):
        r=use('get_economic_resilience',{},'fetched dated economic observations and scoped financial assessment')
        c=r['economic_conditions']
        reply=f"Economic conditions as of {c['as_of']}: {c['status']}. "+' '.join(c['labels'])+'. '
        reply+=' '.join(a['cause'] for a in r['alerts']) if r['alerts'] else 'No personalized exposure statement is supported by the currently confirmed facts. '
        reply+=' Sources and observation dates: '+'; '.join(f"{i['id']} {i['observation_date']} ({i['source_url']})" for i in c['indicators'][:5])
        reply+=' Descriptive conditions, not a market forecast.'
    elif 'savings' in text and _has(text,('increase','increasing','transfer')):
        amount=re.search(r'\$\s*([\d,]+(?:\.\d+)?)',text)
        if amount and _has(text,('transfer','from checking')):
            try:
                r=use('run_economic_simulation',{'scenario':{'type':'savings_transfer','amount':float(amount.group(1).replace(',',''))}},'tested explicitly requested savings transfer')
                reply=f"The hypothetical transfer changes net worth by {_usd(r['net_worth_change'])}; the new v2 score is {r['after']['health']['score'] if r['after']['health']['score'] is not None else 'withheld'}. Checking liquidity also changes."
            except ValueError as exc:
                reply='The requested scenario is unavailable: '+str(exc)
        else:reply='Specify the dollar amount and whether savings come from existing checking or new income. A transfer alone does not create net worth.'
    elif _has(text,("assessment","v2","score","health")) and 'legacy' not in text:
        r=use('get_financial_assessment',{},'fetched versioned v2 components and completeness')
        reply=(f"FinPilot v2 score: {r['score']}/100. " if r['score'] is not None else
               f"Automatic observed-data estimate: {r['observed_score']}/100. The confirmed-input v2 assessment is incomplete. ")
        reply+=' '.join(r['withheld_reasons'])+' This is not the CFPB questionnaire score.'
        known=[c for c in r['components'] if c['score'] is not None]
        if known:
            worst=min(known,key=lambda c:c['score'])
            reply+=f" Lowest supported component: {worst['name']} ({worst['score']}/100). Formula: {worst['formula']}."
    elif _has(text,("paycheck","expenses rise","income reduction","emergency")):
        pct=re.search(r'(\d+(?:\.\d+)?)\s*%',text)
        amount=re.search(r'\$\s*([\d,]+(?:\.\d+)?)',text)
        scenario={'type':'missed_paycheck'} if 'paycheck' in text else ({'type':'cash_expense_increase' if 'expenses rise' in text else 'income_reduction','fraction':float(pct.group(1))/100} if pct and float(pct.group(1))<=100 else {'type':'emergency_expense','amount':float(amount.group(1).replace(',',''))} if amount else None)
        if scenario is None:
            reply='Specify an explicit percentage from 0 to 100 or a dollar amount for the hypothetical shock. No unstated amount has been assumed.'
        else:
            try:
                r=use('run_economic_simulation',{'scenario':scenario},'ran hypothetical deterministic stress')
                reply=f"Under the stated hypothetical assumptions, ending checking changes by {_usd(r['ending_checking_change'])}. {r['after']['cash_plan']['note']}"
            except ValueError as exc:reply='The requested scenario is unavailable: '+str(exc)
    elif _has(text, ("cut", "save", "reduce", "what if", "what can")):
        amount, horizon = None, 30
        for a in use("get_guardian_alerts", {}, "fetched alerts")["alerts"]:
            sc = a.get("suggested_scenario")
            if sc:
                amount, horizon = float(sc["reduction_amount"]), int(sc["horizon_days"])
                break
        mt = re.search(r"\$?\s*(\d[\d,]*(?:\.\d+)?)", text)
        if mt:
            amount = float(mt.group(1).replace(",", ""))
        if not amount or amount <= 0:
            reply = ("Tell me an amount, like \"what if I cut $200 a month?\", and I will "
                     "run the numbers.")
        else:
            r = use("run_simulation", {"reduction_amount": amount, "horizon_days": horizon},
                    f"simulated a {_usd(amount)} cut")
            b, s = r["baseline_low"], r["scenario_low"]
            if b and s:
                reply = (f"If you cut discretionary spending by {_usd(amount)} over {horizon} days, your "
                         f"lowest projected balance goes from {_usd(b['balance'])} to "
                         f"{_usd(s['balance'])} (a change of "
                         f"{_usd(r['delta'].get('low_balance_change', 0))}). ")
            else:
                reply = f"I simulated a {_usd(amount)} cut but found no projected low point. "
            reply += NOTE
    elif _has(text, ("health", "score")):
        r = use("get_health_score", {}, "fetched health score")
        reply = f"Your financial health score is {r['score']:g} out of 100. "
        if r["weaknesses"]:
            reply += f"Main weakness: {r['weaknesses'][0]} "
        if r["strengths"]:
            reply += f"Strength: {r['strengths'][0]} "
        reply += NOTE
    elif _has(text, ("risk", "alert", "guardian", "forecast", "balance", "cash", "safe")):
        acc = use("get_accounts_summary", {}, "fetched balances")
        fc = use("get_forecast", {"days": 30}, "fetched 30-day forecast")
        al = use("get_guardian_alerts", {}, "fetched alerts")["alerts"]
        reply = f"Your checking balance is {_usd(acc['cash_balance'])}. "
        if fc["projected_low"]:
            reply += (f"Over the next 30 days it is projected to dip to "
                      f"{_usd(fc['projected_low']['balance'])} on {fc['projected_low']['date']} "
                      f"(safety buffer {_usd(fc['safety_buffer'])}). ")
        if al:
            reply += f"Top alert: {al[0]['title']}. {al[0]['recommended_action']} "
        else:
            reply += "No active alerts. "
        reliability=fc.get('meta',{}).get('forecast_reliability')
        if reliability and reliability.get('validation')!='synthetic_evaluated':
            reply+='Forecast accuracy is not validated for this history; treat the figures as uncertain planning estimates. '
        reply += NOTE
    else:
        reply = HELP + " " + NOTE
    meta = Meta(source="baseline", as_of=tools.profile.as_of, generated_at=datetime.now(timezone.utc))
    return ChatResult(reply=reply, tool_calls=calls, meta=meta)
