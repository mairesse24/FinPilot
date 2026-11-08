from fastapi import APIRouter, Depends

from app.baseline.chat import chat as baseline_chat
from app.calc.models import FinancialProfile
from app.config import Settings
from app.deps import get_gateway, get_assessment_profile as get_profile, get_settings_dep
from app.schemas.chat import ChatRequest, ChatResult
from app.schemas.chat import ChatDelivery
from app.services.gateway import Gateway, make_meta
from app.tools.registry import ToolRegistry

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResult)
def chat_route(req: ChatRequest, p: FinancialProfile = Depends(get_profile),
               gateway: Gateway = Depends(get_gateway),
               settings: Settings = Depends(get_settings_dep)):
    tools = ToolRegistry(p, gateway, settings=settings, facts=req.financial_facts)
    out = gateway.run("copilot", "chat", baseline_chat, req.messages, tools, expect=ChatResult)
    result=out.value
    if out.warning:
        result=result.model_copy(update={'delivery':ChatDelivery(mode='fallback',provider='gemini',
            model=settings.gemini_model,code='provider_unavailable',message=out.warning)})
    return result.model_copy(update={"meta": make_meta(out, p.as_of)})
