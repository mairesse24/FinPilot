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

    if _has(text, ("cut", "save", "reduce", "what if", "what can")):
        amount, horizon = None, 30
        for a in use("get_guardian_alerts", {}, "fetched alerts")["alerts"]:
            sc = a.get("suggested_scenario")
            if sc:
                amount, horizon = float(sc["reduction_amount"]), int(sc["horizon_days"])
                break
        mt = re.search(r"\$?\s*(\d[\d,]*(?:\.\d+)?)", text)
        if mt:
            amount = float(mt.group(1).replace(",", ""))
        if not amount or amount <= 0 or amount > 100000:
            reply = ("Tell me a positive amount up to $100,000, like \"what if I cut $200?\", and I will "
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
        reply += NOTE
    else:
        reply = HELP + " " + NOTE
    meta = Meta(source="baseline", as_of=tools.profile.as_of, generated_at=datetime.now(timezone.utc))
    return ChatResult(reply=reply, tool_calls=calls, meta=meta)
