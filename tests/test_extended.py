"""Release tests for new tools, dual-era MCP compatibility and hardened HTTP."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.astronomy import chinese_lunar_date
from app.engines import BirthInput
from app.extended import (BirthWindowRequest, LunarToGregorianRequest, birth_window,
                          lunar_month_catalog, lunar_to_gregorian)
from app.main import app
from app.mcp import MODERN_PROTOCOL, process_rpc, TOOL_DEFS, RESOURCES, PROMPTS

client = TestClient(app)
BASE = {'birth_datetime':'2024-02-10T01:20','timezone':'Asia/Shanghai','gender':'female'}
META = {'io.modelcontextprotocol/protocolVersion':MODERN_PROTOCOL,
        'io.modelcontextprotocol/clientInfo':{'name':'pytest','version':'1.0'},
        'io.modelcontextprotocol/clientCapabilities':{}}


def modern(method, params=None, id_=1, override=None):
    body = {'jsonrpc':'2.0','id':id_,'method':method,'params':{'_meta':META,**(params or {})}}
    headers={'MCP-Protocol-Version':MODERN_PROTOCOL,'Mcp-Method':method,
             'Accept':'application/json, text/event-stream'}
    if method in ('tools/call','prompts/get','resources/read'):
        headers['Mcp-Name'] = params['uri'] if method=='resources/read' else params['name']
    headers.update(override or {})
    return client.post('/mcp',json=body,headers=headers)


@pytest.mark.parametrize('lunar,expected',[((2024,1,1,False),'2024-02-10'),
    ((2020,4,1,True),'2020-05-23'),((2033,11,1,True),'2033-12-22'),
    ((1901,1,1,False),'1901-02-19')])
def test_lunar_inverse_reference(lunar, expected):
    y,m,d,leap=lunar
    result=lunar_to_gregorian(LunarToGregorianRequest(lunar_year=y,lunar_month=m,lunar_day=d,is_leap_month=leap))
    assert result['gregorian_date']==expected
    assert result['lunar_date']['month']==m
    assert result['lunar_date']['is_leap_month']==leap


def test_lunar_catalog_has_distinct_month_starts_and_roundtrips():
    for year in (1901, 2020, 2024, 2033, 2099):
        catalog=lunar_month_catalog(year)
        assert len(catalog)>=11
        assert len({(m,leap) for m,leap,_,_ in catalog})==len(catalog)
        assert all(length in (29,30) for _,_,_,length in catalog)
        for month,leap,start,length in catalog:
            day=min(length,15)
            greg=lunar_to_gregorian(LunarToGregorianRequest(lunar_year=year,lunar_month=month,lunar_day=day,is_leap_month=leap))
            assert greg['gregorian_date']==(start+timedelta(days=day-1)).isoformat()
            assert chinese_lunar_date(start)['day']==1


def test_lunar_inverse_rejects_invalid_leaps_and_month_lengths():
    with pytest.raises(ValueError,match='No supported'):
        lunar_to_gregorian(LunarToGregorianRequest(lunar_year=2024,lunar_month=1,lunar_day=1,is_leap_month=True))
    first=next(x for x in lunar_month_catalog(2024) if x[3]==29)
    with pytest.raises(ValueError,match='only 29'):
        lunar_to_gregorian(LunarToGregorianRequest(lunar_year=2024,lunar_month=first[0],lunar_day=30,is_leap_month=first[1]))


def test_birth_window_has_sample_trace_no_false_exhaustive_claim():
    out=birth_window(BirthWindowRequest(birth=BirthInput(**BASE),uncertainty_minutes=50,sample_every_minutes=5))
    assert out['sample_count']==21
    assert sum(item['sample_count'] for item in out['variants'])==out['sample_count']
    assert 1<=out['variant_count']<=out['sample_count']
    assert [x['offset_minutes'] for x in out['samples']]==list(range(-50,51,5))
    assert any('not an exhaustive' in x for x in out['limitations'])
    assert all(1<=row['variant_index']<=out['variant_count'] for row in out['samples'])


def test_birth_window_crosses_hour_boundary_and_dst_fold_safely():
    out=birth_window(BirthWindowRequest(birth=BirthInput(**BASE),uncertainty_minutes=30,sample_every_minutes=5))
    assert out['variant_count']>=2
    # The ambiguous 02:30 clocks are represented with explicit correct offsets.
    rome=BirthInput(birth_datetime='2024-10-27T02:30+02:00',timezone='Europe/Rome')
    fold=birth_window(BirthWindowRequest(birth=rome,uncertainty_minutes=60,sample_every_minutes=15))
    assert fold['sample_count']>=8
    assert any('+01:00' in s['local_time'] for s in fold['samples'])
    assert any('+02:00' in s['local_time'] for s in fold['samples'])


def test_new_http_endpoints_success_and_reject_bad_calendar_dates():
    r=client.post('/api/lunar-to-gregorian',json={'lunar_year':2024,'lunar_month':1,'lunar_day':1})
    assert r.status_code==200 and r.json()['gregorian_date']=='2024-02-10'
    assert r.headers['cache-control']=='no-store'
    assert client.post('/api/lunar-to-gregorian',json={'lunar_year':2024,'lunar_month':1,'lunar_day':31}).status_code==422
    r=client.post('/api/birth-window',json={'birth':BASE,'uncertainty_minutes':30,'sample_every_minutes':15})
    assert r.status_code==200 and r.json()['sample_count']>=5
    assert client.post('/api/birth-window',json={'birth':BASE,'uncertainty_minutes':200}).status_code==422


def test_modern_discovery_list_and_tool_with_real_response():
    discovery=modern('server/discover')
    assert discovery.status_code==200
    assert MODERN_PROTOCOL in discovery.json()['result']['supportedVersions']
    assert discovery.json()['result']['resultType']=='complete'
    tools=modern('tools/list')
    assert tools.status_code==200 and len(tools.json()['result']['tools'])==25
    args={'lunar_year':2024,'lunar_month':1,'lunar_day':1}
    call=modern('tools/call',{'name':'lunar_to_gregorian','arguments':args})
    assert call.status_code==200 and call.json()['result']['structuredContent']['gregorian_date']=='2024-02-10'
    assert call.json()['result']['resultType']=='complete'
    assert 'io.modelcontextprotocol/serverInfo' in call.json()['result']['_meta']
    assert len(RESOURCES)==17 and len(PROMPTS)==15
    # Modern stdio shares the exact same core and does not need initialize.
    core=process_rpc({'jsonrpc':'2.0','id':1,'method':'tools/list','params':{'_meta':META}})
    assert core['result']['resultType']=='complete'


def test_modern_header_validation_unknown_method_and_legacy_fallback():
    x=modern('tools/list',override={'Mcp-Method':'ping'})
    assert x.status_code==400 and x.json()['error']['code']==-32020
    x=modern('tools/call',{'name':'lunar_to_gregorian','arguments':{}},override={'Mcp-Name':'other'})
    assert x.status_code==400 and x.json()['error']['code']==-32020
    x=modern('server/discover',override={'MCP-Protocol-Version':'1900-01-01'})
    assert x.status_code==400 and x.json()['error']['code']==-32022
    assert MODERN_PROTOCOL in x.json()['error']['data']['supported']
    x=modern('unknown/method')
    assert x.status_code==404 and x.json()['error']['code']==-32601
    old=client.post('/mcp',json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25'}})
    assert old.status_code==200 and old.json()['result']['protocolVersion']=='2025-11-25'


def test_public_mode_requires_strong_token_and_allowed_hosts(monkeypatch):
    monkeypatch.setenv('DEPLOYMENT_MODE','public')
    monkeypatch.setenv('MCP_BEARER_TOKEN','short')
    assert client.get('/health').status_code==503
    monkeypatch.setenv('MCP_BEARER_TOKEN','a-long-test-token-12345678901234567890')
    assert client.get('/health').status_code==503
    monkeypatch.setenv('ASTRO_ALLOWED_HOSTS','testserver')
    assert client.get('/health').status_code==200
    assert client.get('/api/lunar/2024-02-10').status_code==401
    assert client.get('/api/lunar/2024-02-10',headers={'Authorization':'Bearer a-long-test-token-12345678901234567890'}).status_code==200
    assert client.get('/health',headers={'Host':'evil.example'}).status_code==400
    assert client.post('/mcp',json={'jsonrpc':'2.0','id':1,'method':'ping'},headers={'Origin':'https://evil.example','Authorization':'Bearer a-long-test-token-12345678901234567890'}).status_code==403


def test_streamed_request_cannot_bypass_body_limit():
    chunks=(b' ' * 10000 for _ in range(8))
    r=client.post('/api/combined',content=chunks,headers={'Content-Type':'application/json'})
    assert r.status_code==413, r.text


def test_cli_new_commands():
    for argv,expected in [(['gregorian','--year','2024','--month','1','--day','1'],'gregorian_date'),
                          (['birth-window','--date',BASE['birth_datetime'],'--radius','10','--step','5'],'variant_count')]:
        run=subprocess.run([sys.executable,'-m','app.cli',*argv],text=True,capture_output=True,timeout=20)
        assert run.returncode==0,run.stderr
        assert expected in json.loads(run.stdout)


def test_release_ui_and_skills_wired():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    js=(root/'static/app.js').read_text(encoding='utf-8')
    assert "'/api/lunar-to-gregorian'" in js and "'/api/birth-window'" in js
    assert '25 MCP TOOLS' in (root/'static/index.html').read_text(encoding='utf-8')
    assert len(list((root/'skills').glob('*/SKILL.md')))==18
