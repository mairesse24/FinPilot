"""Provider chat over backend-mvp's scoped read-only ToolRegistry.

Provider errors become sanitized status metadata and explicit local responses.
No database access or cross-user tool selection is introduced here.
"""
import json
import re
from .copilot import SYSTEM, _numbers
from .provider_config import load_config,safe_failure


_CASUAL_PATTERNS = (
    r'(?:hi|hello|hey)(?: there)?[!.?]*',
    r'how are you(?: doing)?[!.?]*',
    r'(?:thank you|thanks|thx)[!.?]*',
    r'who are you[!.?]*',
    r'what can you do[!.?]*',
)


def _is_casual_message(messages):
    """Allow only narrowly social prompts to receive a tool-free live reply."""
    text=next((m.content.strip().lower() for m in reversed(messages) if m.role=='user'),'')
    return any(re.fullmatch(pattern,text) for pattern in _CASUAL_PATTERNS)


def _finish_response(messages,tools,provider,model,evidence,records,text):
    from app.schemas.chat import ChatResult, ChatDelivery
    from app.baseline.chat import chat as baseline_chat
    from .backend_adapter import _meta
    if _is_casual_message(messages) and not evidence and text and not _numbers(text):
        return ChatResult(reply=text,tool_calls=[],meta=_meta(tools.profile),
            delivery=ChatDelivery(mode='live',provider=provider,model=model,
                message='Live AI response; no financial calculation was requested.'))
    if not evidence or not text or not _numbers(text).issubset(_numbers(json.dumps(evidence))):
        fallback = baseline_chat(messages, tools)
        return fallback.model_copy(update={'meta': _meta(tools.profile, 'baseline',
            'Provider narration failed numeric evidence check; deterministic backend narration used.'),
            'delivery':ChatDelivery(mode='fallback',provider=provider,model=model,code='grounding_check',
                message='The AI explanation could not be verified. Showing a calculation-based response instead.')})
    return ChatResult(reply=text, tool_calls=records, meta=_meta(tools.profile),
        delivery=ChatDelivery(mode='live',provider=provider,model=model,message='Live AI response grounded in financial tools.'))


def chat_messages(messages, tools):
    from app.schemas.chat import ChatDelivery
    from app.baseline.chat import chat as baseline_chat
    config=load_config()
    try:return _chat_messages(messages,tools,config)
    except Exception as exc:
        code,message=safe_failure(exc)
        provider=config.get('COPILOT_PROVIDER','offline').lower()
        result=baseline_chat(messages,tools)
        return result.model_copy(update={'delivery':ChatDelivery(mode='fallback',provider=provider,
            model=config.get(provider.upper()+'_MODEL'),code=code,message=message)})


def _chat_messages(messages,tools,config):
    from app.schemas.chat import ToolCallRecord, ChatDelivery
    from app.baseline.chat import chat as baseline_chat
    from .backend_adapter import _meta
    provider = config.get('COPILOT_PROVIDER', 'offline').lower()
    if provider == 'offline':
        return baseline_chat(messages, tools)
    if provider not in ('gemini', 'openai'):
        raise ValueError('Unsupported COPILOT_PROVIDER')
    prefix = 'GEMINI' if provider == 'gemini' else 'OPENAI'
    key, model = config.get(prefix+'_API_KEY'), config.get(prefix+'_MODEL')
    if not key or not model:
        raise ValueError(f'{prefix} key/model not configured; backend baseline remains available')
    specs = [s['function'] for s in tools.specs()]
    system=SYSTEM+' You may answer greetings and brief social questions naturally without calling a tool. Use get_financial_assessment for FinPilot v2; get_health_score is legacy v1. A withheld score is unknown, never zero. Economic indicators require source observation and knowledge dates. Do not present descriptive regimes or stress assumptions as market forecasts or event probabilities. User-confirmed facts are not independently verified bank evidence.'
    allowed = {s['name'] for s in specs}
    records, evidence = [], []

    def execute(name, args):
        if name not in allowed or not isinstance(args, dict):
            raise ValueError('Unsupported backend tool or arguments')
        value = tools.call(name, args)
        evidence.append({'tool': name, 'result': value})
        records.append(ToolCallRecord(name=name, args=args, summary=f'Executed verified {name} calculation'))
        return value

    def finish(text):
        return _finish_response(messages,tools,provider,model,evidence,records,text)

    if provider == 'openai':
        from openai import OpenAI
        context = [{'role': m.role, 'content': m.content} for m in messages]
        with OpenAI(api_key=key, timeout=30, max_retries=0) as client:
            for _ in range(4):
                response = client.responses.create(model=model, instructions=system, input=context,
                    tools=[{'type': 'function', **s, 'strict': False} for s in specs], store=False, max_output_tokens=2048)
                context.extend(response.output)
                calls = [item for item in response.output if item.type == 'function_call']
                if not calls:
                    return finish(response.output_text)
                for call in calls:
                    value = execute(call.name, json.loads(call.arguments))
                    context.append({'type': 'function_call_output', 'call_id': call.call_id,
                                    'output': json.dumps(value, allow_nan=False)})
    else:
        from google import genai
        from google.genai import types
        context = [types.Content(role='user' if m.role == 'user' else 'model',
                   parts=[types.Part.from_text(text=m.content)]) for m in messages]
        settings = types.GenerateContentConfig(system_instruction=system, max_output_tokens=2048,
            tools=[types.Tool(function_declarations=[types.FunctionDeclaration(name=s['name'],
                description=s['description'], parameters_json_schema=s['parameters']) for s in specs])],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
        with genai.Client(api_key=key, http_options=types.HttpOptions(timeout=30000,
                         retry_options=types.HttpRetryOptions(attempts=1))) as client:
            for _ in range(4):
                response = client.models.generate_content(model=model, contents=context, config=settings)
                if not response.candidates or not response.candidates[0].content:
                    break
                content = response.candidates[0].content
                context.append(content)
                calls = [part.function_call for part in (content.parts or []) if part.function_call]
                if not calls:
                    return finish(response.text or '')
                parts = [types.Part(function_response=types.FunctionResponse(name=call.name, id=call.id,
                         response={'result': execute(call.name, dict(call.args or {}))})) for call in calls]
                context.append(types.Content(role='tool', parts=parts))
    fallback = baseline_chat(messages, tools)
    return fallback.model_copy(update={'meta': _meta(tools.profile, 'baseline', 'Provider tool-round limit reached.'),
        'delivery':ChatDelivery(mode='fallback',provider=provider,model=model,code='tool_limit',message='The AI reached its tool-call limit. Showing a calculation-based response instead.')})
