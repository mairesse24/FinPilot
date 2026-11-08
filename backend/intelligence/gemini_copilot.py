"""Gemini adapter over authenticated calculation tools; no direct database access."""
import json
import os
from .copilot import SYSTEM, _numbers, grounded_summary, tool_schemas
from .simulator import simulate


def gemini_chat(message, customer, spending, analysis, client=None, model=None, max_rounds=4):
    model = model or os.getenv('GEMINI_MODEL')
    if not model or (client is None and not os.getenv('GEMINI_API_KEY')):
        raise ValueError('Gemini requires GEMINI_API_KEY and GEMINI_MODEL; use provider=offline for local summaries')
    from google import genai
    from google.genai import types
    owned = client is None
    if owned:
        client = genai.Client(api_key=os.environ['GEMINI_API_KEY'],
                              http_options=types.HttpOptions(timeout=30000,
                                  retry_options=types.HttpRetryOptions(attempts=1)))
    declarations = [types.FunctionDeclaration(name=s['name'], description=s['description'],
                                              parameters_json_schema=s['parameters']) for s in tool_schemas()]
    declarations.append(types.FunctionDeclaration(name='get_dashboard',
                        description='Read current balances, income, bills and verified financial analysis.',
                        parameters_json_schema={'type': 'object', 'properties': {}, 'additionalProperties': False}))
    config = types.GenerateContentConfig(system_instruction=SYSTEM, max_output_tokens=2048,
                tools=[types.Tool(function_declarations=declarations)],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
    contents = [types.Content(role='user', parts=[types.Part.from_text(text=message)])]
    results = []
    try:
        for _ in range(max_rounds):
            response = client.models.generate_content(model=model, contents=contents, config=config)
            if not response.candidates or not response.candidates[0].content:
                break
            content = response.candidates[0].content
            # Keep the original complete model content, including thought signatures.
            contents.append(content)
            calls = [p.function_call for p in (content.parts or []) if p.function_call]
            if not calls:
                text = response.text or ''
                if not results or not text or not _numbers(text).issubset(_numbers(json.dumps(results))):
                    return {'mode': 'validated_fallback', 'answer': grounded_summary(analysis), 'tool_results': results}
                return {'mode': 'gemini', 'answer': text, 'tool_results': results,
                        'validation': 'Numeric tokens matched tool evidence; semantic claims still require review.'}
            parts = []
            for call in calls:
                try:
                    args = dict(call.args or {})
                    if call.name == 'get_analysis' and not args:
                        result = analysis
                    elif call.name == 'get_dashboard' and not args:
                        result = {'customer': customer, 'analysis': analysis}
                    elif call.name == 'simulate':
                        result = simulate(customer, spending, args, analysis['economy'].get('snapshot'))
                    else:
                        raise ValueError('Tool not allowed or invalid arguments')
                except (ValueError, TypeError, KeyError) as error:
                    result = {'error': str(error)}
                results.append({'tool': call.name, 'result': result})
                parts.append(types.Part(function_response=types.FunctionResponse(
                    name=call.name, id=call.id, response={'result': result})))
            contents.append(types.Content(role='tool', parts=parts))
        return {'mode': 'tool_limit_fallback', 'answer': grounded_summary(analysis), 'tool_results': results}
    finally:
        if owned:
            client.close()
