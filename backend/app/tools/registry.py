"""Read-only tools the copilot may call. Results are JSON-serializable dicts."""
from decimal import Decimal

from pydantic import ValidationError

from app.calc import metrics as m
from app.calc.models import FinancialProfile
from app.config import Settings
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
    def __init__(self, profile: FinancialProfile, gateway: Gateway,
                 settings: Settings | None = None, facts=None):
        self.profile = profile
        self.gateway = gateway
        self.facts = facts
        self.settings = settings
        self._tools = {
            "get_accounts_summary": self._accounts,
            "get_health_score": self._health,
            "get_forecast": self._forecast,
            "get_guardian_alerts": self._guardian,
            "run_simulation": self._simulate,
            "get_economic_conditions": self._economy,
            "get_financial_assessment": self._assessment,
            "get_economic_resilience": self._resilience,
            "run_economic_simulation": self._economic_simulation,
            "evaluate_purchase": self._purchase,
        }

    def specs(self) -> list[dict]:
        return [
            _spec("get_accounts_summary", "Account balances, assets, liabilities and net worth."),
            _spec("get_health_score", "Legacy v1 financial score; use get_financial_assessment for the explicitly versioned v2 assessment."),
            _spec("get_economic_conditions", "Cached actual economic observations, source dates and descriptive labels; no predictions."),
            _spec("get_financial_assessment", "FinPilot v2 score, completeness and formulas; missing score means withheld, not zero."),
            _spec("evaluate_purchase", "Evaluate a proposed purchase against current finances. Pass every financing term the user supplies; payments remain unknown only when terms are missing.",
                  {"amount":{"type":"number","exclusiveMinimum":0},"item":{"type":"string"},
                   "funding_source":{"type":"string","enum":["liquid","savings"]},
                   "gift_amount":{"type":"number","minimum":0},
                   "down_payment":{"type":"number","minimum":0},
                   "apr_percent":{"type":"number","minimum":0,"maximum":100},
                   "term_months":{"type":"integer","minimum":1,"maximum":480}},["amount"]),
            _spec("get_economic_resilience", "Personal exposure grounded in supplied financial facts and dated economic observations."),
            _spec("run_economic_simulation", "Deterministic hypothetical stress; no bank writes. Requires confirmed facts for a complete budget.",
                  {"scenario":{"type":"object","properties":{"type":{"type":"string","enum":["essential_cost_increase","cash_expense_increase","income_reduction","income_interruption","missed_paycheck","emergency_expense","variable_rate_payment","delayed_paycheck","fixed_bill_increase","debt_repayment","savings_transfer"]},
                      "fraction":{"type":"number","minimum":0,"maximum":1},"amount":{"type":"number","minimum":0},"delay_days":{"type":"integer","minimum":1,"maximum":90},"liability_account_id":{"type":"string"}},"required":["type"],"additionalProperties":False}},["scenario"]),
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
                "components": [c.model_dump(mode="json") for c in r.components],
                'meta':r.meta.model_dump(mode='json'),'forecast_dependency':'none; score uses recorded history and schedules'}

    def _forecast(self, days: int) -> dict:
        if days not in (7, 30, 90):
            raise ValueError("days must be 7, 30 or 90")
        r = get_forecast(self.profile, self.gateway, days)
        d = r.model_dump(mode="json")
        low_point = next((p for p in d["series"]
                          if d["projected_low"] and p["date"] == d["projected_low"]["date"]), None)
        return {"days": days, "as_of": self.profile.as_of.isoformat(), "status":d["status"],
                "warning":d["meta"].get("warning"), 'meta':d['meta'], "projected_low": d["projected_low"],
                "safety_buffer": d["safety_buffer"], "shortfall": d["shortfall"],
                "assumptions": d["assumptions"],
                "low_point_interval": {"low": low_point["low"], "high": low_point["high"]}
                if low_point else None}

    def _guardian(self) -> dict:
        result=get_guardian(self.profile,self.gateway)
        return {"as_of": self.profile.as_of.isoformat(), "forecast_days": 30,
                "alerts": [a.model_dump(mode="json")
                           for a in result.alerts], 'meta':result.meta.model_dump(mode='json')}

    def _simulate(self, reduction_amount: float, horizon_days: int = 30) -> dict:
        cut = SpendingCut(reduction_amount=Decimal(str(reduction_amount)),
                          horizon_days=horizon_days)
        r = run_simulation(self.profile, self.gateway, cut)
        d = r.model_dump(mode="json")
        return {"baseline_low": d["baseline"]["projected_low"],
                "scenario_low": d["scenario"]["projected_low"], "delta": d["delta"],
                "baseline_end_balance": d["baseline"]["end_balance"],
                "scenario_end_balance": d["scenario"]["end_balance"],
                "baseline_health_score": d["baseline"]["health_score"],
                "scenario_health_score": d["scenario"]["health_score"],
                "baseline_alerts": len(d["baseline"]["alerts"]),
                "scenario_alerts": len(d["scenario"]["alerts"]),'meta':d['meta']}

    def _economy(self):
        from app.services.economic_intelligence import conditions
        return conditions(self.profile.as_of)

    def _assessment(self):
        from app.services.economic_intelligence import assessment
        return assessment(self.profile,self.facts)

    def _resilience(self):
        from app.services.economic_intelligence import contextual
        return contextual(self.profile,self.facts)

    def _economic_simulation(self,scenario):
        from app.services.economic_intelligence import simulate
        from intelligence.resilience import EconomicScenario
        from intelligence.personal_finance import FinancialFacts
        return simulate(self.profile,self.facts or FinancialFacts(),EconomicScenario.model_validate(scenario))

    def _purchase(self,amount:float,item:str='purchase',funding_source:str='liquid',gift_amount:float=0,
                  down_payment:float|None=None,
                  apr_percent:float|None=None,term_months:int|None=None):
        if amount<=0:raise ValueError('purchase amount must be greater than zero')
        price=Decimal(str(amount));gift=Decimal(str(gift_amount));liquid=m.liquid_balance(self.profile)
        if gift<0:raise ValueError('gift amount must not be negative')
        checking=m.cash_balance(self.profile);net=m.net_worth(self.profile);debt=m.liabilities(self.profile)
        savings=sum((a.balance for a in self.profile.accounts if a.account_type=='savings'),Decimal(0))
        if funding_source not in ('liquid','savings'):raise ValueError('funding source must be liquid or savings')
        source_funds=(savings if funding_source=='savings' else liquid)+gift
        source_after=source_funds-price
        usage_percent=round(float(price/source_funds*100),1) if source_funds>0 else None
        safety=self.profile.user.safety_buffer
        max_cash=max(Decimal(0),source_funds-safety)
        warning=None
        if price>source_funds:
            warning={'severity':'high','code':'purchase_exceeds_available_funds',
                'message':f'This cash purchase is not funded: it exceeds available {funding_source} funds by ${price-source_funds:,.2f}. Do not treat credit or overdraft as available cash.'}
        elif usage_percent is not None and usage_percent>=80:
            warning={'severity':'high','code':'large_reserve_purchase',
                'message':f'This purchase would use {usage_percent:g}% of available {funding_source} funds and leave ${max(Decimal(0),source_after):,.2f}. Preserve emergency cash and upcoming bill coverage before buying.'}
        elif source_after<safety:
            warning={'severity':'medium','code':'below_safety_buffer',
                'message':f'This purchase would leave available {funding_source} funds below the ${safety:,.2f} safety buffer.'}
        supplied=[down_payment is not None,apr_percent is not None,term_months is not None]
        if any(supplied) and not all(supplied):raise ValueError('down payment, APR and term months are all required for financing calculations')
        financing=None
        if all(supplied):
            down=Decimal(str(down_payment));apr=Decimal(str(apr_percent));months=int(term_months)
            if down<0 or down>price:raise ValueError('down payment must be between zero and purchase price')
            if apr<0 or apr>100:raise ValueError('APR percent must be between zero and 100')
            if months<1 or months>480:raise ValueError('loan term must be between 1 and 480 months')
            principal=price-down;rate=apr/Decimal(1200)
            payment=principal/Decimal(months) if rate==0 else principal*rate/(Decimal(1)-(Decimal(1)+rate)**(-months))
            total=payment*months;income=m.monthly_income(self.profile)
            financing={'down_payment':float(down),'principal':float(principal),'apr_percent':float(apr),
                'term_months':months,'monthly_payment':round(float(payment),2),
                'total_of_payments':round(float(total),2),'total_interest':round(float(total-principal),2),
                'down_payment_funding_gap':float(max(Decimal(0),down-(liquid+gift))),
                'liquid_after_down_payment':float(liquid+gift-down),'scheduled_monthly_income':float(income),
                'payment_to_scheduled_income':round(float(payment/income),4) if income>0 else None}
        portfolio=None
        if gift>0 or all(supplied):
            assumed_down=Decimal(str(down_payment)) if down_payment is not None else min(gift,price)
            assumed_principal=price-assumed_down
            assets_after=m.assets(self.profile)+gift-assumed_down+price
            liabilities_after=debt+assumed_principal
            portfolio={'gift_amount':float(gift),'assumed_down_payment':float(assumed_down),
                'hypothetical_financing_needed':float(assumed_principal),
                'liquid_after_down_payment':float(liquid+gift-assumed_down),
                'assets_after_purchase':float(assets_after),'liabilities_after_purchase':float(liabilities_after),
                'net_worth_after_purchase':float(assets_after-liabilities_after),
                'net_worth_change_before_fees_and_depreciation':float((assets_after-liabilities_after)-net)}
        return {'item':item,'price':float(price),'checking':float(checking),'savings':float(savings),'liquid_funds':float(liquid),
                'gift_amount':float(gift),
                'funding_source':funding_source,'available_source_funds':float(source_funds),
                'source_funding_gap':float(max(Decimal(0),price-source_funds)),
                'source_usage_percent':usage_percent,
                'source_funds_after_purchase':float(source_after),
                'recommended_max_cash_purchase':float(max_cash),
                'safety_buffer':float(safety),'reserve_warning':warning,
                'liabilities':float(debt),'net_worth':float(net),'cash_purchase_supported':price<=liquid,
                'liquid_funding_gap':float(max(Decimal(0),price-liquid)),
                'liquid_after_cash_purchase':float(liquid-price),
                'price_to_net_worth':round(float(price/net),2) if net>0 else None,
                'financing':financing,'portfolio_scenario':portfolio,
                'financing_inputs_needed':([] if financing else ['down payment','APR','loan term'])+
                    ['taxes and fees','insurance and operating costs'],
                'note':'Loan math excludes taxes, fees, insurance, maintenance and depreciation. This read-only comparison does not approve or execute a purchase.'}
