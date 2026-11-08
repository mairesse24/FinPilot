import httpx
import pytest
import openai
from app.services.gateway import Gateway
from app.tools.registry import ToolRegistry
from app.schemas.chat import ChatMessage
from tests.factories import make_profile


@pytest.mark.parametrize('status,code,expected',[(429,'credit_balance_exhausted','quota_exhausted'),
                                               (401,'invalid_api_key','authentication_failed'),
                                               (404,'model_not_found','model_unavailable')])
def test_provider_failure_is_visible_and_redacted(monkeypatch,status,code,expected):
    from intelligence import registry_copilot as module
    monkeypatch.setattr(module,'load_config',lambda:{'COPILOT_PROVIDER':'openai','OPENAI_API_KEY':'test-only','OPENAI_MODEL':'gpt-4.1-mini'})
    sdk_client=openai.OpenAI(api_key='test-only',max_retries=0,http_client=httpx.Client(
        transport=httpx.MockTransport(lambda request:httpx.Response(status,json={
            'error':{'message':'SECRET-MUST-NOT-APPEAR','type':'insufficient_quota' if status==429 else 'invalid_request_error','code':code}}))))
    monkeypatch.setattr(openai,'OpenAI',lambda **kwargs:sdk_client)
    result=module.chat_messages([ChatMessage(role='user',content='Explain my health score')],
        ToolRegistry(make_profile(),Gateway('baseline')))
    assert result.delivery.mode=='fallback' and result.delivery.code==expected
    assert result.delivery.provider=='openai'
    assert 'SECRET-MUST-NOT-APPEAR' not in result.model_dump_json()
    assert 'Automatic observed-data estimate' in result.reply


def test_explicit_offline_mode_is_not_mislabeled_as_api_failure(client):
    r=client.post('/api/chat',json={'messages':[{'role':'user','content':'Explain my health score'}]}).json()
    assert r['delivery']['mode']=='offline'
    assert r['delivery']['code'] is None


@pytest.mark.parametrize('message',["How are you?","hello","Thanks!","Who are you?"])
def test_only_narrow_social_messages_can_skip_financial_tools(message):
    from intelligence.registry_copilot import _is_casual_message
    assert _is_casual_message([ChatMessage(role='user',content=message)])


@pytest.mark.parametrize('message',[
    "How is my financial health?",
    "Hello, what will my balance be?",
    "Thanks, should I pay my loan faster?",
])
def test_financial_messages_still_require_verified_tools(message):
    from intelligence.registry_copilot import _is_casual_message
    assert not _is_casual_message([ChatMessage(role='user',content=message)])


def test_casual_provider_reply_is_live_without_financial_tool_call():
    from intelligence.registry_copilot import _finish_response
    tools=ToolRegistry(make_profile(),Gateway('baseline'))
    result=_finish_response([ChatMessage(role='user',content='How are you?')],tools,
                            'gemini','test-model',[],[],'Doing well—how can I help?')
    assert result.reply=='Doing well—how can I help?'
    assert result.tool_calls==[]
    assert result.delivery.mode=='live'


def test_financial_provider_reply_without_evidence_still_falls_back():
    from intelligence.registry_copilot import _finish_response
    tools=ToolRegistry(make_profile(),Gateway('baseline'))
    result=_finish_response([ChatMessage(role='user',content='What is my balance?')],tools,
                            'gemini','test-model',[],[],'Your balance is $9,999.')
    assert result.delivery.mode=='fallback'
    assert result.delivery.code=='grounding_check'
    assert '$9,999' not in result.reply
