"""Read-only tools the copilot may call. Results are JSON-serializable dicts."""
from decimal import Decimal

from pydantic import ValidationError

from app.calc import metrics as m
from app.calc.models import FinancialProfile
from app.schemas.common import SpendingCut
from app.services.forecast import get_forecast
from app.services.gateway import Gateway
from app.services.guardian import get_guardian
from app.services.health import get_health
from app.services.simulate import run_simulation


def _spec(name: str, description: str, properties: dict | None = None,
          required: list[str] | None = None) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties or {},
                       "required": required or []}}}


class ToolRegistry:
    def __init__(self, profile: FinancialProfile, gateway: Gateway):
        self.profile = profile
        self.gateway = gateway
        self._tools = {
            "get_accounts_summary": self._accounts,
            "get_health_score": self._health,
            "get_forecast": self._forecast,
            "get_guardian_alerts": self._guardian,
            "run_simulation": self._simulate,
        }

    def specs(self) -> list[dict]:
        return [
            _spec("get_accounts_summary", "Account balances, assets, liabilities and net worth."),
            _spec("get_health_score", "Financial health score (0-100) with components."),
            _spec("get_forecast", "Projected checking balance for the next 7, 30 or 90 days.",
                  {"days": {"type": "integer", "enum": [7, 30, 90]}}, ["days"]),
            _spec("get_guardian_alerts", "Active risk alerts with causes and suggested actions."),
            _spec("run_simulation", "What-if: cut discretionary spending by an amount.",
                  {"reduction_amount": {"type": "number", "exclusiveMinimum": 0},
                   "horizon_days": {"type": "integer", "minimum": 1, "maximum": 90,
                                    "default": 30}}, ["reduction_amount"]),
        ]

    def call(self, name: str, args: dict | None = None) -> dict:
        fn = self._tools.get(name)
        if fn is None:
            raise ValueError(f"unknown tool '{name}'")
        try:
            return fn(**(args or {}))
        except (TypeError, ValidationError) as exc:
            raise ValueError(f"bad arguments for {name}: {exc}") from exc

    def _accounts(self) -> dict:
        p = self.profile
        return {"accounts": [{"name": a.name, "account_type": a.account_type,
                              "balance": float(a.balance)} for a in p.accounts],
                "cash_balance": float(m.cash_balance(p)), "net_worth": float(m.net_worth(p)),
                "assets": float(m.assets(p)), "liabilities": float(m.liabilities(p))}

    def _health(self) -> dict:
        r = get_health(self.profile, self.gateway)
        return {"score": round(r.score, 1), "strengths": r.strengths,
                "weaknesses": r.weaknesses,
                "components": [{"name": c.name, "score": c.score} for c in r.components]}

    def _forecast(self, days: int) -> dict:
        if days not in (7, 30, 90):
            raise ValueError("days must be 7, 30 or 90")
        r = get_forecast(self.profile, self.gateway, days)
        d = r.model_dump(mode="json")
        return {"days": days, "projected_low": d["projected_low"],
                "safety_buffer": d["safety_buffer"], "shortfall": d["shortfall"],
                "assumptions": d["assumptions"]}

    def _guardian(self) -> dict:
        return {"alerts": [a.model_dump(mode="json")
                           for a in get_guardian(self.profile, self.gateway).alerts]}

    def _simulate(self, reduction_amount: float, horizon_days: int = 30) -> dict:
        cut = SpendingCut(reduction_amount=Decimal(str(reduction_amount)),
                          horizon_days=horizon_days)
        r = run_simulation(self.profile, self.gateway, cut)
        d = r.model_dump(mode="json")
        return {"baseline_low": d["baseline"]["projected_low"],
                "scenario_low": d["scenario"]["projected_low"], "delta": d["delta"],
                "baseline_alerts": len(d["baseline"]["alerts"]),
                "scenario_alerts": len(d["scenario"]["alerts"])}
