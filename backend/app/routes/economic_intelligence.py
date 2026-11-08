from fastapi import APIRouter,Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel,ConfigDict,Field
from app.calc.models import FinancialProfile
from app.deps import get_assessment_profile as get_profile
from app.services import economic_intelligence as service
from intelligence.personal_finance import FinancialFacts
from intelligence.resilience import EconomicScenario

router=APIRouter(prefix='/api',tags=['economic intelligence v2'])


def invalid_facts(exc):
    message=str(exc)
    fields={}
    for text,field in [('accessible savings','accessible_emergency_savings'),
                       ('Essential cash budget','essential_cash_expenses'),
                       ('Discretionary cash budget','discretionary_cash_expenses'),
                       ('required debt payments cannot','required_debt_payments')]:
        if text in message:fields[field]=message
    return JSONResponse(status_code=422,content={'detail':message,'field_errors':fields})


@router.get('/financial-inputs')
def financial_inputs(p:FinancialProfile=Depends(get_profile)):
    from app.calc import metrics as m
    from app.calc.categories import ESSENTIAL,DISCRETIONARY
    from decimal import Decimal,ROUND_CEILING
    # Forms accept cents. Round minimum budgets upward so the displayed minimum
    # remains sufficient for a weekly/biweekly schedule normalized to 30 days.
    floor=lambda values:float(sum(values,Decimal(0)).quantize(Decimal('.01'),rounding=ROUND_CEILING))
    return {'savings_balance':float(sum((a.balance for a in p.accounts if a.account_type=='savings'),Decimal(0))),
            'essential_bill_floor':floor(m._per_30_days(b.amount,b.frequency) for b in p.bills if b.category in ESSENTIAL and b.category!='debt_payment'),
            'discretionary_bill_floor':floor(m._per_30_days(b.amount,b.frequency) for b in p.bills if b.category in DISCRETIONARY),
            'known_required_debt':float(m.monthly_debt_payments(p)),
            'dated_debt_payments':float(sum((m._per_30_days(b.amount,b.frequency) for b in p.bills if b.category=='debt_payment'),Decimal(0))),
            'scheduled_income':float(m.monthly_income(p)),
            'bills':[{'name':b.name,'amount':float(b.amount),'category':b.category,'frequency':b.frequency,'due_date':str(b.due_date)} for b in p.bills]}


class AssessmentRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    facts:FinancialFacts=Field(default_factory=FinancialFacts)


class StressRequest(AssessmentRequest):
    scenario:EconomicScenario


@router.get('/economy')
def economy(p:FinancialProfile=Depends(get_profile)):
    return service.conditions(p.as_of)


@router.get('/financial-health')
def health(p:FinancialProfile=Depends(get_profile)):
    return service.assessment(p)


@router.post('/financial-health/assess')
def assess(req:AssessmentRequest,p:FinancialProfile=Depends(get_profile)):
    try:return service.assessment(p,req.facts)
    except ValueError as exc:return invalid_facts(exc)


@router.post('/resilience')
def contextual(req:AssessmentRequest,p:FinancialProfile=Depends(get_profile)):
    try:return service.contextual(p,req.facts)
    except ValueError as exc:return invalid_facts(exc)


@router.post('/economic-simulate')
def simulate(req:StressRequest,p:FinancialProfile=Depends(get_profile)):
    try:return service.simulate(p,req.facts,req.scenario)
    except ValueError as exc:return invalid_facts(exc)
