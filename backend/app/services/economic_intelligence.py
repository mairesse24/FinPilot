"""Profile-scoped orchestration. HTTP handlers read cached data, never refresh it."""
from intelligence.economic_data import cached
from intelligence.regimes import classify
from intelligence.personal_finance import assess,FinancialFacts
from intelligence.resilience import resilience,simulate_economic,EconomicScenario
from app.services.notices import notices_for


def provenance(result,profile):
    # These calculations consume confirmed budgets and dated schedules, not the
    # ML cash forecast. Do not invent or borrow a forecast confidence label.
    return {**result,'forecast_dependency':'none; deterministic assessment or confirmed-assumption cash plan',
            'data_notices':[n.model_dump() for n in notices_for(profile.data_warnings,'bank_data')]}


def conditions(as_of):
    return classify(cached(),str(as_of))


def assessment(profile,facts=None):
    return provenance(assess(profile,facts or FinancialFacts()),profile)


def contextual(profile,facts=None):
    return provenance(resilience(profile,facts or FinancialFacts(),conditions(profile.as_of)),profile)


def simulate(profile,facts,scenario):
    return provenance(simulate_economic(profile,facts,scenario),profile)
