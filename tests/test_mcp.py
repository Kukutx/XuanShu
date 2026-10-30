import json
import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from app.main import app

CLIENT=TestClient(app)


def rpc(method, params=None, id_=1):
    return {'jsonrpc':'2.0','id':id_,'method':method,'params':params or {}}


def test_http_health_and_static():
    assert CLIENT.get('/health').json()['status']=='ok'
    assert CLIENT.get('/').status_code==200
    assert CLIENT.get('/static/app.js').status_code==200
    assert CLIENT.get('/static/style.css').status_code==200


def test_rest_valid_and_invalid_requests():
    valid={'birth_datetime':'2000-08-16T04:00','gender':'female'}
    for path in ['/api/bazi','/api/ziwei','/api/combined','/api/analyze']:
        response=CLIENT.post(path,json=valid)
        assert response.status_code==200,(path,response.text)
    assert CLIENT.post('/api/bazi',json={'birth_datetime':'3000-01-01T01:01'}).status_code==422
    assert CLIENT.post('/api/bazi',json={'birth_datetime':'nope'}).status_code==422
    assert CLIENT.get('/api/solar-terms/2024').json()['terms'][2]['name']=='立春'
    assert CLIENT.get('/api/solar-terms/2200').status_code==422


def test_mcp_initialize_list_and_call():
    init=CLIENT.post('/mcp',json=rpc('initialize',{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'pytest','version':'1'}}))
    assert init.status_code==200
    assert init.json()['result']['protocolVersion']=='2025-11-25'
    names={t['name'] for t in CLIENT.post('/mcp',json=rpc('tools/list')).json()['result']['tools']}
    assert names=={'bazi_chart','ziwei_chart','combined_chart','symbolic_reading','solar_terms','calendar_days','pair_comparison','palace_detail','annual_transformations','time_basis_audit','rule_comparison','structured_report','lunar_to_gregorian','birth_time_window','chart_quality_audit','day_officers','annual_timeline','decision_matrix','bazi_dayun','birth_boundary_map','qimen_hour_chart','ziwei_professional_chart','qimen_reference_audit','deep_evidence_review','consultation_execute','date_candidate_scan','life_path_review','ziwei_pair_overlay','pillars_to_dates','chart_import_check','daily_almanac','group_relations','rule_sensitivity_matrix','ziwei_horoscope'}
    a=CLIENT.post('/mcp',json=rpc('tools/call',{'name':'ziwei_chart','arguments':{'birth_datetime':'2000-08-16T04:00'}}))
    assert a.status_code==200
    assert a.json()['result']['structuredContent']['ming_palace']=='午'
    assert a.json()['result']['isError'] is False
    terms=CLIENT.post('/mcp',json=rpc('tools/call',{'name':'solar_terms','arguments':{'year':2024}}))
    assert len(terms.json()['result']['structuredContent']['terms'])==24


def test_mcp_error_notification_transport():
    assert CLIENT.post('/mcp',json=rpc('tools/call',{'name':'bazi_chart','arguments':{'birth_datetime':'invalid'}})).json()['result']['isError']
    assert CLIENT.post('/mcp',json=rpc('does-not-exist')).json()['error']['code']==-32601
    assert CLIENT.post('/mcp',json={'jsonrpc':'2.0','method':'notifications/initialized'}).status_code==202
    assert CLIENT.get('/mcp').status_code==405
    assert CLIENT.post('/mcp',content='bad',headers={'Content-Type':'application/json'}).status_code==400
    assert CLIENT.post('/mcp',json=[rpc('ping')]).status_code==400


def test_mcp_tools_are_annotated_read_only_and_errors_name_fields():
    tools=CLIENT.post('/mcp',json=rpc('tools/list')).json()['result']['tools']
    for tool in tools:
        hints=tool['annotations']
        assert hints=={'title':tool['title'],'readOnlyHint':True,'destructiveHint':False,
                       'idempotentHint':True,'openWorldHint':False}, tool['name']
    bad=CLIENT.post('/mcp',json=rpc('tools/call',{'name':'bazi_chart','arguments':{'birth_datetime':'invalid','extra':1}})).json()['result']
    assert bad['isError'] is True
    error=bad['structuredContent']['error']
    assert error['code']=='invalid_arguments'
    assert [f['path'] for f in error['fields']]==['birth_datetime','extra']
    assert [f['type'] for f in error['fields']]==['value_error','extra_forbidden']
    assert 'birth_datetime' in bad['content'][0]['text'] and 'extra' in bad['content'][0]['text']
    assert not error['fields'][0]['message'].startswith('Value error')  # the reason itself, without Pydantic's prefix
    # solar_terms names its bad fields like every other tool, rather than refusing the calculation.
    for args, path in (({}, 'year'), ({'year': '2024'}, 'year'), ({'year': 2024, 'x': 1}, 'x'), ({'year': True}, 'year'), ({'year': 1800}, 'year')):
        terms=CLIENT.post('/mcp',json=rpc('tools/call',{'name':'solar_terms','arguments':args})).json()['result']
        assert terms['structuredContent']['error']['code']=='invalid_arguments', args
        assert [f['path'] for f in terms['structuredContent']['error']['fields']]==[path], args
    refused=CLIENT.post('/mcp',json=rpc('tools/call',{'name':'bazi_chart','arguments':{'birth_datetime':'1800-01-01T00:00'}})).json()['result']
    assert refused['isError'] is True and refused['structuredContent']['error']['code']=='calculation_refused'


def test_mcp_origin_policy(monkeypatch):
    monkeypatch.delenv('MCP_ALLOWED_ORIGINS',raising=False)
    res=CLIENT.post('/mcp',json=rpc('ping'),headers={'Origin':'http://evil.example'})
    assert res.status_code==403
    ok=CLIENT.post('/mcp',json=rpc('ping'),headers={'Host':'localhost:8000','Origin':'http://localhost:8000'})
    assert ok.status_code==200
    monkeypatch.setenv('MCP_ALLOWED_ORIGINS','https://known.example')
    assert CLIENT.post('/mcp',json=rpc('ping'),headers={'Origin':'https://known.example'}).status_code==200


def test_bearer_auth_protects_both_rest_and_mcp(monkeypatch):
    monkeypatch.setenv('MCP_BEARER_TOKEN','test-secret-123')
    for path in ['/mcp','/api/bazi']:
        data=rpc('ping') if path=='/mcp' else {'birth_datetime':'2024-02-10T12:00'}
        assert CLIENT.post(path,json=data).status_code==401
        assert CLIENT.post(path,json=data,headers={'Authorization':'Bearer test-secret-123'}).status_code==200


def test_stdio_roundtrip():
    requests='\n'.join(json.dumps(rpc(method,params,id_)) for id_,(method,params) in enumerate([
        ('initialize',{'protocolVersion':'2025-11-25'}),
        ('tools/list',{}),
        ('tools/call',{'name':'bazi_chart','arguments':{'birth_datetime':'2000-08-16T04:00'}}),
    ],start=1))+'\n'
    proc=subprocess.run([sys.executable,'-m','app.stdio'],text=True,input=requests,capture_output=True,timeout=12)
    assert proc.returncode==0,proc.stderr
    assert not proc.stderr
    output=[json.loads(line) for line in proc.stdout.splitlines()]
    assert len(output)==3
    assert output[2]['result']['structuredContent']['pillars']['day']['text']=='丙午'
    # The version negotiated in initialize applies to the later calls: the result links its rule document.
    assert output[2]['result']['content'][1:]==[{'type':'resource_link','uri':'astro://rules/bazi','name':'bazi',
        'mimeType':'text/markdown','description':'XuanShu rule reference for bazi_chart'}]


def test_tool_results_link_their_rule_documents_from_2025_06_18():
    from app.mcp import RESOURCE_TEXT, TOOL_RULES, TOOLS
    # Every linked document is a listed resource, and every tool that has a rule document links it.
    assert set(TOOL_RULES) <= set(TOOLS) and set(TOOLS) - set(TOOL_RULES) == {'solar_terms', 'calendar_days'}
    assert {f'astro://rules/{doc}' for docs in TOOL_RULES.values() for doc in docs} <= set(RESOURCE_TEXT)
    call=rpc('tools/call',{'name':'day_officers','arguments':{'start_date':'2026-11-01','days':3}})
    for header, linked in ((None, False), ('2025-03-26', False), ('2025-06-18', True), ('2025-11-25', True)):
        response=CLIENT.post('/mcp',json=call,headers={'MCP-Protocol-Version':header} if header else {}).json()['result']
        assert response['content'][0]['type']=='text' and not response['isError']
        assert [c['uri'] for c in response['content'][1:]]==(['astro://rules/jianchu'] if linked else []), header
    # A 2026-07-28 request names its version in its own metadata.
    from app.mcp import process_rpc
    modern=process_rpc({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'_meta':{
        'io.modelcontextprotocol/protocolVersion':'2026-07-28','io.modelcontextprotocol/clientCapabilities':{}},
        'name':'combined_chart','arguments':{'birth_datetime':'2000-08-16T04:00'}}})
    assert [c['uri'] for c in modern['result']['content'][1:]]==['astro://rules/bazi','astro://rules/ziwei']
    # A failed call links nothing.
    bad=CLIENT.post('/mcp',json=rpc('tools/call',{'name':'bazi_chart','arguments':{}}),headers={'MCP-Protocol-Version':'2025-11-25'}).json()['result']
    assert bad['isError'] and len(bad['content'])==1


def test_resource_templates_read_computed_facts():
    templates=CLIENT.post('/mcp',json=rpc('resources/templates/list')).json()['result']['resourceTemplates']
    assert [t['uriTemplate'] for t in templates]==['astro://solar-terms/{year}','astro://lunar/{date}']
    assert all(t['mimeType']=='application/json' for t in templates)
    terms=CLIENT.post('/mcp',json=rpc('resources/read',{'uri':'astro://solar-terms/2026'})).json()['result']['contents'][0]
    data=json.loads(terms['text'])
    assert terms['uri']=='astro://solar-terms/2026' and terms['mimeType']=='application/json'
    # The same terms the tool returns.
    tool=CLIENT.post('/mcp',json=rpc('tools/call',{'name':'solar_terms','arguments':{'year':2026}})).json()['result']['structuredContent']
    assert data==tool and len(data['terms'])==24
    lunar=CLIENT.post('/mcp',json=rpc('resources/read',{'uri':'astro://lunar/2026-10-18'})).json()['result']['contents'][0]
    assert json.loads(lunar['text'])=={'date':'2026-10-18','lunar':CLIENT.get('/api/lunar/2026-10-18').json()['lunar']}
    for uri in ('astro://solar-terms/1800','astro://lunar/2026-02-30','astro://lunar/1850-01-01','astro://solar-terms/abc'):
        error=CLIENT.post('/mcp',json=rpc('resources/read',{'uri':uri})).json()['error']
        assert error['code']==-32602, uri


def test_completion_suggests_prompt_focus_and_template_years():
    init=CLIENT.post('/mcp',json=rpc('initialize',{'protocolVersion':'2025-11-25'})).json()['result']
    assert init['capabilities']['completions']=={}
    def complete(ref, name, value):
        return CLIENT.post('/mcp',json=rpc('completion/complete',{'ref':ref,'argument':{'name':name,'value':value}})).json()
    palaces=complete({'type':'ref/prompt','name':'explain-ziwei'},'focus','')['result']['completion']
    assert palaces['values'][0]=='命宫' and palaces['total']==12 and palaces['hasMore'] is False
    assert complete({'type':'ref/prompt','name':'explain-ziwei'},'focus','财')['result']['completion']['values']==['财帛宫']
    # A typed text that starts no suggestion still finds the ones containing it.
    assert complete({'type':'ref/prompt','name':'explain-bazi'},'focus','干')['result']['completion']['values']==['藏干']
    assert complete({'type':'ref/prompt','name':'prepare-report'},'focus','')['result']['completion']['values']==[]
    years=complete({'type':'ref/resource','uri':'astro://solar-terms/{year}'},'year','')['result']['completion']
    assert len(years['values'])==100 and years['values'][0]=='1901' and years['total']==199 and years['hasMore'] is True
    assert complete({'type':'ref/resource','uri':'astro://solar-terms/{year}'},'year','209')['result']['completion']['values']==[str(y) for y in range(2090,2100)]
    for ref in ({'type':'ref/prompt','name':'nope'},{'type':'ref/resource','uri':'astro://nope/{x}'},{'type':'ref/tool'}):
        assert complete(ref,'focus','')['error']['code']==-32602, ref


def test_agent_page_reads_templates_and_follows_rule_links():
    from pathlib import Path
    app_js=(Path(__file__).resolve().parents[1]/'static/app.js').read_text(encoding='utf-8')
    assert "step('resources/templates/list', false, plain('resources/templates/list')" in app_js
    assert "docRow(list, 'integration-template-' + t.name, example, t.uriTemplate, t.title || t.name);" in app_js
    # JSON contents are shown indented; a tool run lists the rule documents its result links, each opening its row.
    assert "contents.every(c => c.mimeType === 'application/json')" in app_js and "const pre = append(body, 'pre', 'ag-doc-text ag-doc-json');" in app_js
    assert "filter(c => c && c.type === 'resource_link' && typeof c.uri === 'string')" in app_js
    assert "document.getElementById('integration-doc-' + uri.split('/').pop())" in app_js
