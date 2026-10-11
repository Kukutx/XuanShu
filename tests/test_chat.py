"""AI chat layer: deterministic tool execution, request limits and REST wiring.

No network: a fake provider loop drives tool calls the way a model would.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import chat as chat_module
from app.chat import ChatConfig, ChatRequest, build_system, chat_config, chat_status, run_chat, tool_specs
from app.main import app

CLIENT = TestClient(app)
BIRTH = {'birth_datetime': '2000-08-16T04:00', 'timezone': 'Asia/Shanghai', 'gender': 'female'}
CONFIG = ChatConfig('anthropic', 'test-model')


def scripted_loop(calls):
    def loop(config, system, history, tools, execute):
        loop.system, loop.history, loop.tools = system, history, tools
        loop.results = [execute(name, args) for name, args in calls]
        return '基于工具结果的回答', 'end_turn'
    return loop


def test_tool_specs_cover_every_mcp_tool_and_memory_proposal():
    names = [t['name'] for t in tool_specs()]
    assert len(names) == len(set(names)) == 29
    assert 'bazi_chart' in names and 'propose_memory' in names


def test_tool_calls_run_real_engines_and_are_traced():
    loop = scripted_loop([('bazi_chart', BIRTH), ('bazi_chart', {'birth_datetime': 'bad'}), ('no_such_tool', {})])
    req = ChatRequest(messages=[{'role': 'user', 'content': '看看我的八字'}], profile={'birth': BIRTH})
    out = run_chat(req, config=CONFIG, loop=loop)
    assert out['reply'] == '基于工具结果的回答'
    ok, bad, unknown = out['trace']
    assert ok['ok'] and len(ok['result_sha256']) == 64 and '"pillars"' in loop.results[0][0]
    assert not bad['ok'] and bad['error'].startswith('参数校验失败') and loop.results[1][1] is True
    assert not unknown['ok'] and 'Unknown MCP tool' in unknown['error']


def test_memory_proposals_are_returned_not_stored():
    loop = scripted_loop([('propose_memory', {'items': ['正在考虑转行', '正在考虑转行']}),
                          ('propose_memory', {'items': []})])
    out = run_chat(ChatRequest(messages=[{'role': 'user', 'content': '我想转行'}]), config=CONFIG, loop=loop)
    assert out['memory_suggestions'] == ['正在考虑转行']
    assert out['trace'][1]['ok'] is False


def test_long_tool_results_stay_valid_json_and_keep_limitations(monkeypatch):
    monkeypatch.setattr(chat_module, 'MAX_TOOL_RESULT_CHARS', 8000)
    loop = scripted_loop([('date_candidate_scan', {'start_date': '2026-01-01', 'days': 93, 'hours': ['09:00', '15:00']})])
    run_chat(ChatRequest(messages=[{'role': 'user', 'content': '择日'}]), config=CONFIG, loop=loop)
    text = loop.results[0][0]
    assert len(text) <= chat_module.MAX_TOOL_RESULT_CHARS
    data = json.loads(text)
    full = chat_module.call_tool('date_candidate_scan', {'start_date': '2026-01-01', 'days': 93, 'hours': ['09:00', '15:00']})
    assert data['limitations'] == full['limitations'] and data['criteria'] == full['criteria']
    assert 0 < len(data['candidates']) < len(full['candidates'])
    assert data['candidates'] == full['candidates'][:len(data['candidates'])]
    assert any(f.startswith('candidates') for f in data['_truncated']['fields'])


def test_partner_tools_need_the_users_consent_tick():
    pair = {'person_a': BIRTH, 'person_b': {**BIRTH, 'birth_datetime': '1999-03-02T10:00'}}
    message = [{'role': 'user', 'content': '合盘'}]
    denied = run_chat(ChatRequest(messages=message), config=CONFIG, loop=scripted_loop([('pair_comparison', pair)]))
    assert not denied['trace'][0]['ok'] and '已获对方同意' in denied['trace'][0]['error']
    consult = {'question': '我们适合合作吗', 'birth': BIRTH, 'partner': pair['person_b'], 'partner_authorized': True}
    denied = run_chat(ChatRequest(messages=message), config=CONFIG, loop=scripted_loop([('consultation_execute', consult)]))
    assert not denied['trace'][0]['ok']
    allowed = run_chat(ChatRequest(messages=message, partner_authorized=True), config=CONFIG,
                       loop=scripted_loop([('pair_comparison', pair)]))
    assert allowed['trace'][0]['ok']


def test_malformed_openai_arguments_are_traced(monkeypatch):
    import sys
    import types

    def reply(calls, content=None):
        message = types.SimpleNamespace(content=content, tool_calls=calls)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message, finish_reason='stop')])

    bad = types.SimpleNamespace(id='c1', function=types.SimpleNamespace(name='bazi_chart', arguments='{not json'))
    responses = iter([reply([bad]), reply(None, '好的')])
    client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **kw: next(responses))))
    monkeypatch.setitem(sys.modules, 'openai', types.SimpleNamespace(OpenAI=lambda **kw: client))
    out = run_chat(ChatRequest(messages=[{'role': 'user', 'content': '八字'}]), config=ChatConfig('openai', 'm'))
    assert out['reply'] == '好的'
    assert out['trace'] == [{'step': 1, 'tool': 'bazi_chart', 'arguments': '{not json', 'ok': False,
                             'error': 'arguments must be a valid JSON object'}]


def test_today_comes_from_the_browser_within_a_day():
    from datetime import datetime, timedelta, timezone
    today = datetime.now(timezone.utc).date()
    req = ChatRequest(messages=[{'role': 'user', 'content': '今天'}], today=today + timedelta(days=1))
    assert f'{(today + timedelta(days=1)).isoformat()}（用户本地日期）' in build_system(req)[1]
    with pytest.raises(ValidationError):
        ChatRequest(messages=[{'role': 'user', 'content': '今天'}], today=today + timedelta(days=3))


def test_system_context_carries_profile_as_unverified_data_and_language():
    req = ChatRequest(messages=[{'role': 'user', 'content': 'hello'}], language='en',
                      profile={'label': 'A', 'birth': BIRTH, 'memory': ['  设计师  '],
                               'life_events': [{'date': '2020-03-01', 'title': '换工作', 'note': '去了新公司'}]})
    stable, context = build_system(req)
    assert '只能来自本轮工具返回的结果' in stable and 'English' in context
    assert '设计师' in context and '2020-03-01 换工作：去了新公司' in context and '未核实' in context
    assert '2000-08-16T04:00' in context


@pytest.mark.parametrize('payload', [
    {'messages': []},
    {'messages': [{'role': 'assistant', 'content': 'hi'}]},
    {'messages': [{'role': 'user', 'content': 'a'}, {'role': 'assistant', 'content': 'b'}]},
    {'messages': [{'role': 'user', 'content': 'x' * 4001}]},
    {'messages': [{'role': 'user', 'content': 'x'}], 'language': 'fr'},
    {'messages': [{'role': 'user', 'content': 'x'}], 'extra': 1},
    {'messages': [{'role': 'user', 'content': 'x'}], 'profile': {'memory': ['   ']}},
])
def test_request_validation_is_strict(payload):
    with pytest.raises(ValidationError):
        ChatRequest.model_validate(payload)


def test_config_from_environment(monkeypatch):
    for name in ('XUANSHU_LLM_PROVIDER', 'XUANSHU_LLM_MODEL', 'XUANSHU_LLM_API_KEY', 'XUANSHU_LLM_BASE_URL',
                 'XUANSHU_LLM_EFFORT', 'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'OPENAI_API_KEY'):
        monkeypatch.delenv(name, raising=False)
    assert chat_config() is None and chat_status()['enabled'] is False
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'k')
    assert chat_config().model == 'claude-opus-5-5' and chat_config().effort == 'medium'
    monkeypatch.setenv('XUANSHU_LLM_PROVIDER', 'openai')
    with pytest.raises(ValueError):
        chat_config()
    monkeypatch.setenv('XUANSHU_LLM_MODEL', 'deepseek-chat')
    monkeypatch.setenv('XUANSHU_LLM_BASE_URL', 'https://api.example.com/v1')
    cfg = chat_config()
    assert (cfg.provider, cfg.model, cfg.base_url) == ('openai', 'deepseek-chat', 'https://api.example.com/v1')
    monkeypatch.setenv('XUANSHU_LLM_PROVIDER', 'other')
    assert chat_status() == {'enabled': False, 'reason': 'XUANSHU_LLM_PROVIDER must be anthropic or openai'}


def test_rest_endpoints(monkeypatch):
    monkeypatch.delenv('XUANSHU_LLM_PROVIDER', raising=False)
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    monkeypatch.delenv('ANTHROPIC_AUTH_TOKEN', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    assert CLIENT.get('/api/chat/status').json()['enabled'] is False
    body = {'messages': [{'role': 'user', 'content': '你好'}]}
    assert CLIENT.post('/api/chat', json=body).status_code == 503
    assert CLIENT.post('/api/chat', json={'messages': []}).status_code == 422

    loop = scripted_loop([('solar_terms', {'year': 2026})])
    monkeypatch.setattr(chat_module, 'chat_status', lambda: {'enabled': True})
    monkeypatch.setattr(chat_module, 'chat_config', lambda: CONFIG)
    monkeypatch.setitem(chat_module.LOOPS, 'anthropic', loop)
    data = CLIENT.post('/api/chat', json=body).json()
    assert data['trace'][0]['tool'] == 'solar_terms' and data['trace'][0]['ok']
    assert data['provider'] == 'anthropic' and data['limitations']
