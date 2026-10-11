"""Independent public traditional-rule fixtures, civil-time boundaries and interface parity."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.advanced import DayunRequest, BirthBoundaryRequest, dayun_sequence, birth_boundary_map
from app.astronomy import from_jd, solar_term_jd
from app.engines import BirthInput, calculate_bazi, calculate_ziwei
from app.main import app
from app.mcp import call_tool, process_rpc, MODERN_PROTOCOL, TOOL_DEFS
from app.report import ReportRequest, structured_report

CLIENT = TestClient(app)
BASE = {'birth_datetime': '2000-08-16T04:00', 'timezone': 'Asia/Shanghai', 'gender': 'male'}


def birth(**overrides):
    return BirthInput.model_validate({**BASE, **overrides})


@pytest.mark.parametrize('gender,direction,first', [
    ('male', 'forward', ['癸未','甲申','乙酉','丙戌']),
    ('female','reverse',['辛巳','庚辰','己卯','戊寅']),
])
def test_public_1990_dayun_sequence_fixture(gender, direction, first):
    # Independently published example: yilibazi.com/baike/dayun.html, checked 2026-10-09.
    result = dayun_sequence(DayunRequest(birth=birth(birth_datetime='1990-06-15T06:30',gender=gender),periods=4))
    assert result['natal_year_pillar']=='庚午'
    assert result['natal_month_pillar']=='壬午'
    assert result['direction']==direction
    assert [x['pillar'] for x in result['periods']]==first
    assert (result['nearest_jie_used']['name']=='小暑') == (direction=='forward')


@pytest.mark.parametrize('gender,direction',[('male','reverse'),('female','forward')])
def test_yin_birth_year_direction(gender, direction):
    out=dayun_sequence(DayunRequest(birth=birth(birth_datetime='1991-06-15T06:30',gender=gender)))
    assert out['natal_year_pillar']=='辛未' and out['direction']==direction


@pytest.mark.parametrize('gender,expected',[('male','forward'),('female','reverse')])
def test_2000_birth_year_gender(gender,expected):
    data=dayun_sequence(DayunRequest(birth=birth(gender=gender),periods=2))
    assert data['direction']==expected
    assert data['periods'][0]['pillar']==('乙酉' if gender=='male' else '癸未')
    assert data['method']['civil_projection'].startswith('365.2425')
    assert '科学' not in json.dumps(data['periods'],ensure_ascii=False)


def test_dayun_nominal_age_ratio_and_period_monotonicity():
    out=dayun_sequence(DayunRequest(birth=birth(),periods=12))
    assert out['start_age_years_nominal']==pytest.approx(out['birth_to_jie_days']/3,abs=1e-6)
    assert len(set(x['pillar'] for x in out['periods']))==12
    assert all(b['approx_start_age_years']-a['approx_start_age_years']==pytest.approx(10)
               for a,b in zip(out['periods'],out['periods'][1:]))
    assert all(datetime.fromisoformat(b['approx_start_local'])>datetime.fromisoformat(a['approx_start_local'])
               for a,b in zip(out['periods'],out['periods'][1:]))


def test_dayun_unspecified_is_not_inferred():
    with pytest.raises(ValidationError,match='direction'):
        DayunRequest(birth=birth(gender='unspecified'))
    out=dayun_sequence(DayunRequest(birth=birth(gender='unspecified'),direction_override='reverse'))
    assert out['direction']=='reverse' and out['direction_source']=='explicit_override'


def test_explicit_override_wins():
    out=dayun_sequence(DayunRequest(birth=birth(gender='male'),direction_override='reverse'))
    assert out['direction']=='reverse'
    assert out['nearest_jie_used']['name']=='立秋'


@pytest.mark.parametrize('count',[0,13,-1,100])
def test_dayun_rejects_invalid_period_counts(count):
    with pytest.raises(ValidationError):DayunRequest(birth=birth(),periods=count)


def test_dayun_rejects_extra_fields_and_invalid_gender():
    with pytest.raises(ValidationError):DayunRequest(birth=birth(),unknown=True)
    with pytest.raises(ValidationError):DayunRequest(birth={'birth_datetime':'2000-08-16T04:00','gender':'test'})


def test_bazi_year_uses_lichun_near_utc_jie():
    instant=from_jd(solar_term_jd(2000,315))
    before=(instant-timedelta(minutes=5)).astimezone(timezone(timedelta(hours=8)))
    after=(instant+timedelta(minutes=5)).astimezone(timezone(timedelta(hours=8)))
    a=dayun_sequence(DayunRequest(birth=birth(birth_datetime=before.isoformat())))
    b=dayun_sequence(DayunRequest(birth=birth(birth_datetime=after.isoformat())))
    assert a['natal_year_pillar']!='庚辰' and b['natal_year_pillar']=='庚辰'
    assert a['direction']!=b['direction']


def test_boundary_map_odd_hour_exact_transition():
    out=birth_boundary_map(BirthBoundaryRequest(birth=birth(birth_datetime='2000-08-16T00:58'),uncertainty_minutes=8))
    assert len(out['boundaries'])==1 and len(out['segments'])==2
    assert out['boundaries'][0]['local'].startswith('2000-08-16T01:00:00')
    assert '时辰界' in out['boundaries'][0]['types']
    assert out['segments'][0]['bazi_pillars']['hour']!=out['segments'][1]['bazi_pillars']['hour']


def test_boundary_map_zi_day_boundary():
    out=birth_boundary_map(BirthBoundaryRequest(birth=birth(birth_datetime='2024-02-10T22:59',late_zi_day_rollover=True),uncertainty_minutes=8))
    assert len(out['boundaries'])==1
    assert '日柱日期界' in out['boundaries'][0]['types']
    assert out['segments'][0]['bazi_pillars']['day']!=out['segments'][1]['bazi_pillars']['day']


def test_boundary_map_midnight_without_zi_day_boundary():
    out=birth_boundary_map(BirthBoundaryRequest(birth=birth(birth_datetime='2024-02-10T23:58'),uncertainty_minutes=5))
    assert len(out['boundaries'])==1
    assert '有效历日界' in out['boundaries'][0]['types']
    assert '日柱日期界' in out['boundaries'][0]['types']
    assert out['segments'][0]['bazi_pillars']['day']!=out['segments'][1]['bazi_pillars']['day']


def test_boundary_map_jiestart_astro_second_precision():
    instant=from_jd(solar_term_jd(2000,165)).astimezone(timezone(timedelta(hours=8)))
    out=birth_boundary_map(BirthBoundaryRequest(birth=birth(birth_datetime=instant.isoformat()),uncertainty_minutes=10))
    found=[b for b in out['boundaries'] if any('白露' in t for t in b['types'])]
    assert len(found)==1
    actual=datetime.fromisoformat(found[0]['utc'])
    assert abs((actual-instant.astimezone(timezone.utc)).total_seconds())<=1.1
    a,b=out['segments'][0],out['segments'][-1]
    assert a['bazi_pillars']['month']!=b['bazi_pillars']['month']


def test_boundary_map_dst_spring_in_rome():
    out=birth_boundary_map(BirthBoundaryRequest(birth=birth(birth_datetime='2024-03-31T01:58',timezone='Europe/Rome'),uncertainty_minutes=60))
    assert any('时区夏令时/历史UTC偏移界' in b['types'] for b in out['boundaries'])
    assert any('2024-03-31T03:00:00+02:00' == b['local'] for b in out['boundaries'])


@pytest.mark.parametrize('offset',['+01:00','+02:00'])
def test_boundary_map_dst_fall_requires_explicit_offset(offset):
    out=birth_boundary_map(BirthBoundaryRequest(birth=birth(birth_datetime='2024-10-27T02:10'+offset,timezone='Europe/Rome'),uncertainty_minutes=60))
    assert out['segments'] and '时区夏令时/历史UTC偏移界' in [x for b in out['boundaries'] for x in b['types']]


def test_boundary_map_dst_ambiguous_without_offset_rejected():
    with pytest.raises(ValueError,match='Ambiguous daylight-saving'):
        birth_boundary_map(BirthBoundaryRequest(birth=birth(birth_datetime='2024-10-27T02:10',timezone='Europe/Rome')))


def test_boundary_map_finds_apparent_solar_hour_transition():
    out=birth_boundary_map(BirthBoundaryRequest(birth=birth(birth_datetime='2000-08-16T00:58',time_mode='apparent_solar',longitude=116.4),uncertainty_minutes=60))
    assert any('时辰界' in b['types'] for b in out['boundaries'])


@pytest.mark.parametrize('radius',[0,121,-5])
def test_boundary_map_rejects_bad_radius(radius):
    with pytest.raises(ValidationError): BirthBoundaryRequest(birth=birth(),uncertainty_minutes=radius)


def test_boundary_map_near_1901_boundary_is_rejected():
    with pytest.raises(ValueError,match='1901'):
        birth_boundary_map(BirthBoundaryRequest(birth=birth(birth_datetime='1901-01-01T00:10'),uncertainty_minutes=60))


def test_boundary_map_no_events_is_single_segment():
    result=birth_boundary_map(BirthBoundaryRequest(birth=birth(birth_datetime='2000-08-16T14:00'),uncertainty_minutes=1))
    assert result['boundaries']==[] and len(result['segments'])==1


def test_boundary_segments_recompute_from_original_engine():
    out=birth_boundary_map(BirthBoundaryRequest(birth=birth(birth_datetime='2000-08-16T00:58'),uncertainty_minutes=120))
    for segment in out['segments']:
        sample=segment['sample_local']
        calc=calculate_bazi(birth(birth_datetime=sample))
        ziwei=calculate_ziwei(birth(birth_datetime=sample))
        assert segment['bazi_pillars']=={k:x['text'] for k,x in calc['pillars'].items()}
        assert segment['ziwei_ming_palace']==ziwei['ming_palace']


def test_advanced_rest_matches_functions():
    for endpoint, name, payload in [
        ('/api/dayun','bazi_dayun',{'birth':BASE,'periods':2}),
        ('/api/birth-boundaries','birth_boundary_map',{'birth':BASE,'uncertainty_minutes':8}),
    ]:
        response=CLIENT.post(endpoint,json=payload)
        assert response.status_code==200,response.text
        assert response.json()==call_tool(name,payload)
        assert response.headers['cache-control']=='no-store'


def test_advanced_rest_validation_and_origin(monkeypatch):
    assert CLIENT.post('/api/dayun',json={'birth':{**BASE,'gender':'unspecified'}}).status_code==422
    assert CLIENT.post('/api/birth-boundaries',json={'birth':BASE,'uncertainty_minutes':121}).status_code==422
    assert CLIENT.post('/api/dayun',json={'birth':BASE,'extra':'x'}).status_code==422
    assert CLIENT.post('/api/dayun',json={'birth':BASE},headers={'Origin':'https://unknown.example'}).status_code==403
    monkeypatch.setenv('MCP_BEARER_TOKEN','test-advanced-token')
    assert CLIENT.post('/api/dayun',json={'birth':BASE}).status_code==401
    assert CLIENT.post('/api/dayun',json={'birth':BASE},headers={'Authorization':'Bearer test-advanced-token'}).status_code==200


def test_advanced_mcp_legacy_parity_and_resources():
    for name,payload in [('bazi_dayun',{'birth':BASE,'periods':2}),('birth_boundary_map',{'birth':BASE,'uncertainty_minutes':8})]:
        resp=process_rpc({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':name,'arguments':payload}})
        assert resp['result']['structuredContent']==call_tool(name,payload)
    for uri in ['astro://rules/dayun','astro://rules/boundary-map']:
        resp=process_rpc({'jsonrpc':'2.0','id':5,'method':'resources/read','params':{'uri':uri}})
        assert len(resp['result']['contents'][0]['text'])>160
    for name in ['explain-dayun','audit-birth-boundaries']:
        resp=process_rpc({'jsonrpc':'2.0','id':6,'method':'prompts/get','params':{'name':name}})
        assert resp['result']['messages']


def test_mcp_2026_version_metadata_and_headers():
    body={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{
        'name':'bazi_dayun','arguments':{'birth':BASE,'periods':2}, '_meta':{
        'io.modelcontextprotocol/protocolVersion':MODERN_PROTOCOL,
        'io.modelcontextprotocol/clientCapabilities':{}}}}
    headers={'MCP-Protocol-Version':MODERN_PROTOCOL,'Mcp-Method':'tools/call','Mcp-Name':'bazi_dayun',
             'Accept':'application/json, text/event-stream'}
    res=CLIENT.post('/mcp',json=body,headers=headers)
    assert res.status_code==200,res.text
    assert res.json()['result']['structuredContent']['periods'][0]['pillar']=='乙酉'
    headers['Mcp-Name']='wrong'
    assert CLIENT.post('/mcp',json=body,headers=headers).status_code==400


def test_advanced_stdio_cli_parity():
    args={'birth':BASE,'periods':2}
    payload=json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'bazi_dayun','arguments':args}})+'\n'
    proc=subprocess.run([sys.executable,'-m','app.stdio'],input=payload,text=True,capture_output=True,timeout=15)
    assert proc.returncode==0,proc.stderr
    stdio=json.loads(proc.stdout)['result']['structuredContent']
    cli=subprocess.run([sys.executable,'-m','app.cli','dayun','--date','2000-08-16T04:00','--tz','Asia/Shanghai','--gender','male','--periods','2'],text=True,capture_output=True,timeout=15)
    assert cli.returncode==0,cli.stderr
    assert json.loads(cli.stdout)==stdio
    cli2=subprocess.run([sys.executable,'-m','app.cli','birth-boundaries','--date','2000-08-16T00:58','--radius','8'],text=True,capture_output=True,timeout=20)
    assert cli2.returncode==0,cli2.stderr
    assert len(json.loads(cli2.stdout)['boundaries'])==1


def test_report_opt_in_advanced_sections():
    req=ReportRequest(birth=birth(),include_dayun=True,birth_boundary_minutes=8)
    dossier=structured_report(req)
    assert [x['tool'] for x in dossier['tool_trace']][-2:]==['bazi_dayun','birth_boundary_map']
    assert '十年干支大运' in dossier['markdown']
    assert dossier['dayun']['system']=='bazi-traditional-dayun-sequence'
    assert dossier['birth_boundaries']['system']=='birth-chart-modeled-boundary-map'
    assert len(dossier['sections'])==6
    response=CLIENT.post('/api/report',json={'birth':BASE,'include_dayun':True,'birth_boundary_minutes':8})
    assert response.status_code==200 and response.json()==dossier


def test_report_default_unchanged_and_no_implied_direction():
    report=structured_report(ReportRequest(birth=birth(gender='unspecified')))
    assert report['dayun'] is None and report['birth_boundaries'] is None
    with pytest.raises(ValidationError,match='direction'):
        ReportRequest(birth=birth(gender='unspecified'),include_dayun=True)
    allowed=ReportRequest(birth=birth(gender='unspecified'),include_dayun=True,dayun_direction_override='reverse')
    assert structured_report(allowed)['dayun']['direction']=='reverse'


def test_advanced_openapi_endpoint_and_counts():
    schema=CLIENT.get('/openapi.json').json()
    assert '/api/dayun' in schema['paths'] and '/api/birth-boundaries' in schema['paths']
    counts=CLIENT.get('/api/capabilities').json()['counts']
    assert counts=={'mcp_tools':32,'mcp_resources':17,'mcp_prompts':15,'agent_skills':18}
    assert {'bazi_dayun','birth_boundary_map'}<=set(x['name'] for x in TOOL_DEFS)
