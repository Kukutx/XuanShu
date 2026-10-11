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


@pytest.fixture(autouse=True)
def no_network_verifier(monkeypatch):
    """Tests never reach a real provider; individual tests pass their own verifier."""
    def offline(config, system, user_text):
        raise RuntimeError('offline')
    monkeypatch.setattr(chat_module, 'VERIFIERS', {'anthropic': offline, 'openai': offline})


def scripted_loop(calls):
    def loop(config, system, history, tools, execute):
        loop.system, loop.history, loop.tools = system, history, tools
        loop.results = [execute(name, args) for name, args in calls]
        return '基于工具结果的回答', 'end_turn'
    return loop


def test_tool_specs_cover_every_mcp_tool_and_memory_proposal():
    names = [t['name'] for t in tool_specs()]
    assert len(names) == len(set(names)) == 32
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


def fake_verifier(output):
    def verify(config, system, user_text):
        verify.system, verify.user_text = system, user_text
        return output
    return verify


def test_verifier_sub_agent_labels_claims_from_tool_evidence():
    verdict = {'claims': [{'claim': '日柱丙午', 'support': 'tool_backed', 'confidence': 'high', 'reason': 'bazi_chart.pillars.day'},
                          {'claim': '今年必定升职', 'support': 'unsupported', 'confidence': 'high', 'reason': '工具没有此结论'}],
               'overall': '一条有依据，一条没有。'}
    verify = fake_verifier(verdict)
    req = ChatRequest(messages=[{'role': 'user', 'content': '看看八字'}], profile={'birth': BIRTH})
    out = run_chat(req, config=CONFIG, loop=scripted_loop([('bazi_chart', BIRTH)]), verify=verify)
    assert out['verification']['status'] == 'ok'
    assert out['verification']['counts'] == {'tool_backed': 1, 'partially_backed': 0, 'unsupported': 1}
    # The verifier sees the question, the answer and the raw tool result, and nothing else.
    assert '看看八字' in verify.user_text and '基于工具结果的回答' in verify.user_text and '丙午' in verify.user_text
    assert 'report_verification' in verify.system


def test_verifier_failures_never_break_the_answer():
    req = ChatRequest(messages=[{'role': 'user', 'content': '八字'}])
    bad = run_chat(req, config=CONFIG, loop=scripted_loop([]), verify=fake_verifier({'claims': 'x'}))
    assert bad['reply'] and bad['verification']['status'] == 'failed'
    crashed = run_chat(req, config=CONFIG, loop=scripted_loop([]))
    assert crashed['verification'] == {'status': 'failed', 'error': '核验调用失败：RuntimeError'}
    skipped = run_chat(ChatRequest(messages=[{'role': 'user', 'content': '八字'}], verify=False), config=CONFIG,
                       loop=scripted_loop([]), verify=fake_verifier(None))
    assert skipped['verification'] is None


def test_chart_confidence_follows_the_stated_uncertainty():
    near_hour = {**BIRTH, 'birth_datetime': '2000-08-16T04:55'}
    tight = run_chat(ChatRequest(messages=[{'role': 'user', 'content': 'x'}], verify=False,
                                 profile={'birth': near_hour, 'birth_time_uncertainty_minutes': 2}),
                     config=CONFIG, loop=scripted_loop([]))
    loose = run_chat(ChatRequest(messages=[{'role': 'user', 'content': 'x'}], verify=False,
                                 profile={'birth': near_hour, 'birth_time_uncertainty_minutes': 15}),
                     config=CONFIG, loop=scripted_loop([]))
    tiers = lambda out: {f['fact']: f['confidence'] for f in out['chart_confidence']['facts']}
    # 04:55 is 5 minutes before the 卯 hour: safe for ±2 minutes, unstable for ±15.
    assert tiers(tight)['八字时柱'] == 'high' and tiers(loose)['八字时柱'] == 'low'
    assert tiers(loose)['八字日柱'] == 'high' and loose['chart_confidence']['review_needed']
    assert run_chat(ChatRequest(messages=[{'role': 'user', 'content': 'x'}], verify=False),
                    config=CONFIG, loop=scripted_loop([]))['chart_confidence'] is None


def test_year_pillar_confidence_uses_lichun_not_any_jie():
    from app.chat_verify import chart_confidence
    from app.engines import BirthInput
    # Seven minutes from 2024 立春: year and month pillars are both unstable at ±30 minutes.
    lichun = {f['fact']: f['confidence'] for f in chart_confidence(BirthInput(birth_datetime='2024-02-04T16:20', timezone='Asia/Shanghai'), 30)['facts']}
    assert lichun['八字年柱'] == 'low' and lichun['八字月柱'] == 'low'
    # Near 白露 (a jie that is not 立春) only the month pillar moves.
    bailu = {f['fact']: f['confidence'] for f in chart_confidence(BirthInput(birth_datetime='2024-09-07T11:00', timezone='Asia/Shanghai'), 120)['facts']}
    assert bailu['八字年柱'] == 'high' and bailu['八字月柱'] == 'low'


def panel_loop(calls_by_agent):
    """Answers as whichever agent the system prompt names; the synthesizer gets no tools."""
    seen = []

    def loop(config, system, history, tools, execute):
        names = {t['name'] for t in tools}
        if not tools:
            seen.append(('synth', names, history[-1]['content']))
            return '综合回答', 'end_turn'
        agent = next(k for k, v in chat_module.SPECIALISTS.items() if v['label'] in system[0])
        seen.append((agent, names, system[1]))
        for name, args in calls_by_agent.get(agent, []):
            execute(name, args)
        return f'{agent} 报告', 'end_turn'
    loop.seen = seen
    return loop


def test_panel_mode_runs_one_specialist_per_school_then_a_tool_free_synthesizer():
    loop = panel_loop({'bazi': [('bazi_chart', BIRTH)], 'ziwei': [('ziwei_chart', BIRTH), ('bazi_chart', BIRTH)]})
    verify = fake_verifier({'claims': [], 'overall': '无计算陈述。'})
    req = ChatRequest(messages=[{'role': 'user', 'content': '今年事业如何'}], profile={'birth': BIRTH}, mode='panel')
    out = run_chat(req, config=CONFIG, loop=loop, verify=verify)
    assert out['mode'] == 'panel' and out['reply'] == '综合回答'
    assert [p['agent'] for p in out['panel']] == ['bazi', 'ziwei', 'qimen']
    assert [p['tool_calls'] for p in out['panel']] == [1, 2, 0]
    tools = {agent: names for agent, names, _ in loop.seen}
    assert 'bazi_chart' in tools['bazi'] and 'ziwei_chart' not in tools['bazi']
    assert 'qimen_hour_chart' in tools['qimen'] and 'bazi_chart' not in tools['qimen']
    assert 'propose_memory' not in tools['ziwei'] and 'solar_terms' in tools['ziwei']
    assert tools['synth'] == set()
    # A specialist cannot reach another school's tool even if it asks for one.
    trace = out['trace']
    assert [t['step'] for t in trace] == [1, 2, 3]
    assert [t['agent'] for t in trace] == ['bazi', 'ziwei', 'ziwei']
    assert trace[2]['ok'] is False and '本流派' in trace[2]['error']
    # The synthesizer reads every report; the verifier sees the evidence from all specialists.
    synth_input = next(c for a, _, c in loop.seen if a == 'synth')
    assert 'bazi 报告' in synth_input and 'qimen 报告' in synth_input and synth_input.startswith('今年事业如何')
    assert '"tool": "bazi_chart"' in verify.user_text and '"tool": "ziwei_chart"' in verify.user_text
    assert any('多流派会诊' in line for line in out['limitations'])


def test_panel_agents_can_be_narrowed_and_must_be_unique():
    loop = panel_loop({})
    req = ChatRequest(messages=[{'role': 'user', 'content': '下周哪天搬家'}], mode='panel', panel_agents=['qimen'], verify=False)
    out = run_chat(req, config=CONFIG, loop=loop)
    assert [p['agent'] for p in out['panel']] == ['qimen'] and out['verification'] is None
    with pytest.raises(ValidationError):
        ChatRequest(messages=[{'role': 'user', 'content': 'x'}], panel_agents=['bazi', 'bazi'])
    with pytest.raises(ValidationError):
        ChatRequest(messages=[{'role': 'user', 'content': 'x'}], panel_agents=[])
    single = run_chat(ChatRequest(messages=[{'role': 'user', 'content': 'x'}], verify=False), config=CONFIG,
                      loop=scripted_loop([]))
    assert single['mode'] == 'single' and single['panel'] is None


def streaming_loop(calls, text='流式回答'):
    def loop(config, system, history, tools, execute, emit=None, cancelled=None):
        loop.cancelled = cancelled
        for name, args in calls:
            execute(name, args)
        if emit:
            emit({'type': 'text', 'text': text})
        return text, 'end_turn'
    return loop


def stream_events(response):
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def test_stream_endpoint_reports_tools_charts_text_then_the_full_result(monkeypatch):
    monkeypatch.setattr(chat_module, 'chat_status', lambda: {'enabled': True})
    monkeypatch.setattr(chat_module, 'chat_config', lambda: CONFIG)
    monkeypatch.setitem(chat_module.LOOPS, 'anthropic', streaming_loop([('bazi_chart', BIRTH), ('solar_terms', {'year': 2026})]))
    response = CLIENT.post('/api/chat/stream', json={'messages': [{'role': 'user', 'content': '八字'}], 'verify': False})
    assert response.status_code == 200 and response.headers['content-type'].startswith('application/x-ndjson')
    events = stream_events(response)
    kinds = [e['type'] for e in events]
    assert kinds == ['tool_start', 'tool', 'tool_start', 'tool', 'text', 'done']
    bazi = events[1]
    assert bazi['tool'] == 'bazi_chart' and bazi['ok'] and 'arguments' not in bazi
    assert bazi['chart']['pillars']['day']['text']
    assert 'chart' not in events[3]  # only chart tools carry a chart card
    result = events[-1]['result']
    assert result['reply'] == '流式回答' and [c['tool'] for c in result['charts']] == ['bazi_chart']
    assert [t['tool'] for t in result['trace']] == ['bazi_chart', 'solar_terms']


def test_stream_endpoint_reports_errors_as_events(monkeypatch):
    monkeypatch.setattr(chat_module, 'chat_status', lambda: {'enabled': False, 'reason': '未配置'})
    events = stream_events(CLIENT.post('/api/chat/stream', json={'messages': [{'role': 'user', 'content': 'x'}]}))
    assert events == [{'type': 'error', 'status': 503, 'detail': '未配置'}]
    assert CLIENT.post('/api/chat/stream', json={'messages': []}).status_code == 422


def test_cancelled_run_stops_before_verification():
    loop = streaming_loop([])
    req = ChatRequest(messages=[{'role': 'user', 'content': 'x'}])
    with pytest.raises(chat_module.ChatCancelled):
        run_chat(req, config=CONFIG, loop=loop, cancelled=lambda: True)
    assert loop.cancelled() is True


def test_only_the_latest_chart_of_each_kind_is_kept():
    other = dict(BIRTH, birth_datetime='1990-05-17T08:30')
    out = run_chat(ChatRequest(messages=[{'role': 'user', 'content': 'x'}], verify=False), config=CONFIG,
                   loop=scripted_loop([('bazi_chart', BIRTH), ('bazi_chart', other), ('ziwei_chart', BIRTH)]))
    assert [c['tool'] for c in out['charts']] == ['bazi_chart', 'ziwei_chart']
    assert out['charts'][0]['result']['birth_datetime'].startswith('1990-05-17')


def test_echo_after_fallback_keeps_only_text_written_before_the_marker():
    class Block:
        def __init__(self, kind): self.type = kind
    text, thinking, fallback, tool = Block('text'), Block('thinking'), Block('fallback'), Block('tool_use')
    assert chat_module._echo_content([text, tool]) == [text, tool]
    assert chat_module._echo_content([thinking, text, fallback, tool]) == [text, tool]


def openai_stream_client(rounds, log):
    """Fake OpenAI client: each create(stream=True) returns the next list of chunks."""
    import types

    def chunk(content=None, calls=None, finish=None):
        delta = types.SimpleNamespace(content=content, tool_calls=calls)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(delta=delta, finish_reason=finish)])

    def part(index, id=None, name=None, arguments=None):
        return types.SimpleNamespace(index=index, id=id, function=types.SimpleNamespace(name=name, arguments=arguments))

    class Stream:
        def __init__(self, chunks): self.chunks = chunks
        def __iter__(self): return iter(self.chunks)
        def close(self): log.append('closed')

    built = iter([[chunk(*c) for c in r] for r in rounds(chunk, part)])

    def create(**kw):
        log.append(('stream' if kw.get('stream') else 'plain', len(kw['messages'])))
        return Stream(next(built))
    return types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))


def test_openai_replies_stream_text_and_assemble_tool_calls_from_pieces(monkeypatch):
    import sys
    import types
    log, events = [], []
    args = json.dumps(BIRTH)
    rounds = lambda chunk, part: [
        [(None, [part(0, 'c1', 'bazi_chart', args[:10])]), (None, [part(0, None, None, args[10:])], 'tool_calls')],
        [('先看', None), ('日柱。', None, 'stop')],
    ]
    client = openai_stream_client(rounds, log)
    monkeypatch.setitem(sys.modules, 'openai', types.SimpleNamespace(OpenAI=lambda **kw: client))
    out = run_chat(ChatRequest(messages=[{'role': 'user', 'content': '八字'}], verify=False),
                   config=ChatConfig('openai', 'm'), emit=events.append)
    assert out['reply'] == '先看日柱。'
    assert [t['tool'] for t in out['trace']] == ['bazi_chart'] and out['trace'][0]['ok']
    assert [e['text'] for e in events if e['type'] == 'text'] == ['先看', '日柱。']
    assert log == [('stream', 2), 'closed', ('stream', 4), 'closed']  # system + user, then + assistant call + tool result


def test_openai_stream_is_closed_when_the_user_stops(monkeypatch):
    import sys
    import types
    log, stop = [], []
    rounds = lambda chunk, part: [[('一', None), ('二', None), ('三', None, 'stop')]]
    client = openai_stream_client(rounds, log)
    monkeypatch.setitem(sys.modules, 'openai', types.SimpleNamespace(OpenAI=lambda **kw: client))

    def emit(event):
        if event['type'] == 'text':
            stop.append(event['text'])
    with pytest.raises(chat_module.ChatCancelled):
        run_chat(ChatRequest(messages=[{'role': 'user', 'content': 'x'}], verify=False),
                 config=ChatConfig('openai', 'm'), emit=emit, cancelled=lambda: bool(stop))
    assert stop == ['一'] and log[-1] == 'closed'


def test_unknown_birth_hour_is_flagged_to_the_model():
    flagged = ChatRequest(messages=[{'role': 'user', 'content': 'x'}], profile={'birth': BIRTH, 'birth_hour_unknown': True})
    assert '用户不知道出生时辰' in build_system(flagged)[1]
    plain = ChatRequest(messages=[{'role': 'user', 'content': 'x'}], profile={'birth': BIRTH})
    assert '用户不知道出生时辰' not in build_system(plain)[1]
