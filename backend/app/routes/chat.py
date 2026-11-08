from fastapi import APIRouter, Depends

from app.baseline.chat import chat as baseline_chat
from app.calc.models import FinancialProfile
from app.deps import get_gateway, get_profile
from app.schemas.chat import ChatRequest, ChatResult
from app.services.gateway import Gateway, make_meta
from app.tools.registry import ToolRegistry

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResult)
def chat_route(req: ChatRequest, p: FinancialProfile = Depends(get_profile),
               gateway: Gateway = Depends(get_gateway)):
    tools = ToolRegistry(p, gateway)
    out = gateway.run("copilot", "chat", baseline_chat, req.messages, tools, expect=ChatResult)
    return out.value.model_copy(update={"meta": make_meta(out, p.as_of)})
