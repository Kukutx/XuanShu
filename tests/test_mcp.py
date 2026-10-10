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
    assert names=={'bazi_chart','ziwei_chart','combined_chart','symbolic_reading','solar_terms','calendar_days','pair_comparison','palace_detail','annual_transformations','time_basis_audit','rule_comparison','structured_report','lunar_to_gregorian','birth_time_window','chart_quality_audit','day_officers','annual_timeline','decision_matrix','bazi_dayun','birth_boundary_map','qimen_hour_chart','ziwei_professional_chart','qimen_reference_audit','deep_evidence_review','consultation_execute'}
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
