from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from app.calc.models import FinancialProfile
from app.deps import get_assessment_profile as get_profile
from app.services import economic_intelligence as service
from intelligence.personal_finance import FinancialFacts
from intelligence.resilience import EconomicScenario

router=APIRouter(prefix='/api',tags=['economic intelligence v2'])


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
    except ValueError as exc:raise HTTPException(422,str(exc)) from None


@router.post('/resilience')
def contextual(req:AssessmentRequest,p:FinancialProfile=Depends(get_profile)):
    try:return service.contextual(p,req.facts)
    except ValueError as exc:raise HTTPException(422,str(exc)) from None


@router.post('/economic-simulate')
def simulate(req:StressRequest,p:FinancialProfile=Depends(get_profile)):
    try:return service.simulate(p,req.facts,req.scenario)
    except ValueError as exc:raise HTTPException(422,str(exc)) from None
