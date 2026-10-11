"""Agent-ready deterministic dossier: trace, optional flows and parity on all transports."""
import json
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.engines import BirthInput
from app.report import ReportRequest, structured_report
from app.mcp import TOOL_DEFS, RESOURCES, PROMPTS, process_rpc

BASE = {'birth_datetime': '2000-08-16T04:00', 'timezone': 'Asia/Shanghai'}
CLIENT = TestClient(app)


def test_report_is_deterministic_and_traceable():
    req=ReportRequest(birth=BirthInput(**BASE))
    a,b=structured_report(req),structured_report(req)
    assert a==b
    assert a['overview']['pillars']==['庚辰','甲申','丙午','庚寅']
    assert a['overview']['star_counts']=={'main':14,'auxiliary':44,'original_selected':18,'additional_named':26}
    assert [x['id'] for x in a['sections']]==['method','bazi','ziwei','quality']
    assert [x['tool'] for x in a['tool_trace']]==['bazi_chart','ziwei_chart','chart_quality_audit']
    assert len(a['markdown'])>100 and '## 四柱与藏干统计' in a['markdown']
    assert a['annual'] is None and a['time_audit'] is None
    assert '科学' in a['markdown']


def test_report_with_year_and_time_audit():
    req=ReportRequest(birth=BirthInput(**BASE,longitude=104.0667),lunar_year=2026,include_time_audit=True)
    data=structured_report(req)
    assert len(data['sections'])==6
    assert len(data['tool_trace'])==5
    assert len(data['annual']['transformations'])==4
    assert len(data['time_audit']['choices'])==3
    assert data['sections'][-1]['id']=='time_audit'
    assert '2026 农历年干四化叠加' in data['markdown']


def test_report_non_optional_time_audit_requires_longitude():
    with pytest.raises(ValidationError,match='longitude'):
        ReportRequest(birth=BirthInput(**BASE),include_time_audit=True)


@pytest.mark.parametrize('bad_year',[0,1900,2100,3000])
def test_report_invalid_year(bad_year):
    with pytest.raises(ValidationError):
        ReportRequest(birth=BirthInput(**BASE),lunar_year=bad_year)


def test_report_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ReportRequest(birth=BirthInput(**BASE),arbitrary='ignored')


def test_report_rest_and_auth(monkeypatch):
    request={'birth':BASE,'lunar_year':2026}
    r=CLIENT.post('/api/report',json=request)
    assert r.status_code==200,r.text
    assert r.json()['system']=='deterministic-multitool-dossier'
    assert r.headers['cache-control']=='no-store'
    bad=CLIENT.post('/api/report',json={'birth':BASE,'include_time_audit':True})
    assert bad.status_code==422
    monkeypatch.setenv('MCP_BEARER_TOKEN','secret')
    assert CLIENT.post('/api/report',json=request).status_code==401
    assert CLIENT.post('/api/report',json=request,headers={'Authorization':'Bearer secret'}).status_code==200


def test_report_mcp_and_prompt():
    assert len(TOOL_DEFS)==28
    assert len(RESOURCES)==17
    assert len(PROMPTS)==15
    resp=process_rpc({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{
        'name':'structured_report','arguments':{'birth':BASE,'lunar_year':2026}}})
    assert resp['result']['isError'] is False
    assert resp['result']['structuredContent']['system']=='deterministic-multitool-dossier'
    prompt=process_rpc({'jsonrpc':'2.0','id':2,'method':'prompts/get','params':{'name':'prepare-report'}})
    assert 'structured_report' in prompt['result']['messages'][0]['content']['text']


def test_report_cli_json_output():
    command=[sys.executable,'-m','app.cli','report','--date','2000-08-16T04:00',
             '--longitude','104.0667','--year','2026','--audit-time']
    proc=subprocess.run(command,text=True,capture_output=True,timeout=20)
    assert proc.returncode==0,proc.stderr
    result=json.loads(proc.stdout)
    assert len(result['sections'])==6
    assert len(result['tool_trace'])==5


def test_report_frontend_skill_wiring():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    assert (root/'static/index.html').read_text(encoding='utf-8').count('data-tab=') == 24
    assert "'/api/report'" in (root/'static/app.js').read_text(encoding='utf-8')
    skill=(root/'skills/structured-dossier/SKILL.md').read_text(encoding='utf-8')
    assert 'structured_report' in skill and 'provenance' in skill
    assert CLIENT.get('/api/capabilities').json()['counts']=={
        'mcp_tools':28,'mcp_resources':17,'mcp_prompts':15,'agent_skills':18}
