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
    calls: list[ToolCallRecord] = []

    def use(name: str, args: dict, summary: str | None = None) -> dict:
        res = tools.call(name, args)
        calls.append(ToolCallRecord(name=name, args=args, summary=summary or f"called {name}"))
        return res

    if _has(text,("economy","inflation","unemployment","borrowing","market")) and not _has(text,("what if","simulate")):
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
        reply=(f"FinPilot v2 score: {r['score']}/100. " if r['score'] is not None else 'FinPilot v2 score is withheld until required inputs are confirmed. ')
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
