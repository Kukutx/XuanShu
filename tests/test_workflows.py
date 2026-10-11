"""Regression and negative tests for independently implemented workflows."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.engines import BirthInput
from app.features import AnnualRequest, annual_transformations
from app.main import app
from app.mcp import process_rpc
from app.workflows import (DayOfficerRequest, TimelineRequest, DecisionMatrixRequest,
                           DAY_OFFICERS, day_officer_calendar, annual_timeline, decision_matrix)

client = TestClient(app)
BIRTH = {'birth_datetime':'2000-08-16T04:00','timezone':'Asia/Shanghai'}


def valid_matrix():
    return {'question':'评估两套开发方案',
            'criteria':[{'name':'成本','weight':3},{'name':'维护性','weight':2}],
            'options':[{'name':'A','ratings':{'成本':4,'维护性':2}},
                       {'name':'B','ratings':{'成本':3,'维护性':5}}]}


def test_officers_reference_public_calendar_2026_10_15():
    out=day_officer_calendar(DayOfficerRequest(start_date='2026-10-15',days=1))
    assert out['days']==[{'date':'2026-10-15','day_pillar':'壬戌',
         'month_branch_at_noon':'戌','day_branch':'戌','officer':'建','jie_boundary_on_date':False}]
    assert '吉凶' in out['limitations'][0]


def test_officer_sequence_and_jie_split_2024_lichun():
    data=day_officer_calendar(DayOfficerRequest(start_date='2024-02-03',days=6))['days']
    assert [d['officer'] for d in data]==['成','收','收','开','闭','建']
    assert data[1]['jie_boundary_on_date'] is True
    assert all(not d['jie_boundary_on_date'] for i,d in enumerate(data) if i != 1)
    assert set(d['officer'] for d in data) <= set(DAY_OFFICERS)


def test_officers_filters_return_only_requested_labels():
    data=day_officer_calendar(DayOfficerRequest(start_date='2024-02-01',days=31,filter_officers=['建','开']))
    assert data['requested_days']==31
    assert len(data['days'])>0
    assert all(d['officer'] in {'建','开'} for d in data['days'])


@pytest.mark.parametrize('options',[
    {'start_date':'2024-01-01','days':0},
    {'start_date':'2024-01-01','days':94},
    {'start_date':'1900-12-31','days':1},
    {'start_date':'2099-12-30','days':3},
    {'start_date':'2024-01-01','days':1,'filter_officers':['吉']},
    {'start_date':'2024-01-01','days':1,'filter_officers':['建','建']},
    {'start_date':'2024-01-01','days':1,'unexpected':True},
])
def test_officer_inputs_fail_closed(options):
    with pytest.raises(ValidationError): DayOfficerRequest(**options)


def test_annual_sequence_matches_existing_year_overlay_exactly():
    request=TimelineRequest(birth=BirthInput(**BIRTH),start_lunar_year=2024,years=6,focus_palace='命宫')
    timeline=annual_timeline(request)
    assert len(timeline['entries'])==6
    for entry in timeline['entries']:
        old=annual_transformations(AnnualRequest(birth=request.birth,lunar_year=entry['lunar_year']))
        assert old['year_pillar']==entry['year_pillar']
        assert old['transformations']==entry['transformations']
        assert all(hit['natal_palace']=='命宫' for hit in entry['focus_hits'])
    assert sum(timeline['natal_palace_label_counts'].values())==24


@pytest.mark.parametrize('kw',[
    {'start_lunar_year':2099,'years':2},
    {'start_lunar_year':1900,'years':1},
    {'start_lunar_year':2026,'years':31},
    {'start_lunar_year':2026,'years':1,'focus_palace':'不存在'},
])
def test_timeline_rejects_invalid_ranges(kw):
    with pytest.raises(ValidationError):TimelineRequest(birth=BirthInput(**BIRTH),**kw)


def test_decision_weight_normalization_and_sensitivity():
    d=decision_matrix(DecisionMatrixRequest(**valid_matrix()))
    assert d['ranked_options'][0]['name']=='B'
    assert d['ranked_options'][0]['score']==3.8
    assert sum(x['normalized_weight'] for x in d['criteria'])==pytest.approx(1)
    assert len(d['leave_one_out_sensitivity'])==2
    assert any(e['leader_changed'] for e in d['leave_one_out_sensitivity'])
    assert '主观' in d['limitations'][0]


def test_decision_scale_is_weight_invariant_and_ties_are_stable():
    input=valid_matrix()
    a=decision_matrix(DecisionMatrixRequest(**input))
    input['criteria'][0]['weight']*=10
    input['criteria'][1]['weight']*=10
    b=decision_matrix(DecisionMatrixRequest(**input))
    assert a['ranked_options']==b['ranked_options']
    input['criteria']=[{'name':'唯一','weight':1}]
    input['options']=[{'name':'A','ratings':{'唯一':3}},{'name':'B','ratings':{'唯一':3}}]
    ties=decision_matrix(DecisionMatrixRequest(**input))
    assert ties['joint_leaders']==['A','B'] and ties['ranked_options'][0]['name']=='A'
    assert ties['leave_one_out_sensitivity']==[]


@pytest.mark.parametrize('bad',[
    {'criteria':[{'name':'重复','weight':1},{'name':'重复','weight':1}]},
    {'criteria':[{'name':'A','weight':0}]},
    {'options':[{'name':'A','ratings':{'成本':4,'维护性':2}}, {'name':'A','ratings':{'成本':4,'维护性':2}}]},
    {'options':[{'name':'A','ratings':{'成本':4}}, {'name':'B','ratings':{'成本':2,'维护性':1}}]},
    {'options':[{'name':'A','ratings':{'成本':6,'维护性':2}}, {'name':'B','ratings':{'成本':1,'维护性':2}}]},
    {'options':[{'name':'A','ratings':{'成本':float('nan'),'维护性':2}}, {'name':'B','ratings':{'成本':1,'维护性':2}}]},
    {'options':[{'name':'A','ratings':{'成本':True,'维护性':2}}, {'name':'B','ratings':{'成本':1,'维护性':2}}]},
    {'criteria':[{'name':'成本','weight':True},{'name':'维护性','weight':1}]},
    {'question':'      '},
])
def test_decision_rejects_invalid_data(bad):
    d=valid_matrix();d.update(bad)
    with pytest.raises(ValidationError):DecisionMatrixRequest(**d)


def test_endpoints_mcp_and_rest_parity():
    requests=[
        ('day_officers','/api/day-officers',{'start_date':'2026-10-15','days':5}),
        ('annual_timeline','/api/annual-timeline',{'birth':BIRTH,'start_lunar_year':2024,'years':3}),
        ('decision_matrix','/api/decision-matrix',valid_matrix()),
    ]
    for name,path,payload in requests:
        response=client.post(path,json=payload)
        assert response.status_code==200,(path,response.text)
        rpc=process_rpc({'jsonrpc':'2.0','id':9,'method':'tools/call','params':{'name':name,'arguments':payload}})
        assert rpc['result']['structuredContent']==response.json()
        assert rpc['result']['isError'] is False
    counts=client.get('/api/capabilities').json()['counts']
    assert counts=={'mcp_tools':28,'mcp_resources':17,'mcp_prompts':15,'agent_skills':18}


def test_bad_decision_rest_and_mcp_rejected():
    bad=valid_matrix();bad['options'][1]['ratings']['维护性']=99
    assert client.post('/api/decision-matrix',json=bad).status_code==422
    rpc=process_rpc({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'decision_matrix','arguments':bad}})
    assert rpc['result']['isError'] is True

@pytest.mark.parametrize('path,payload', [
    ('/api/day-officers', {'start_date': '2026-10-15', 'days': 5}),
    ('/api/annual-timeline', {'birth': BIRTH, 'start_lunar_year': 2025, 'years': 3}),
    ('/api/decision-matrix', valid_matrix()),
])
def test_new_workflows_respect_shared_auth_and_browser_origin(monkeypatch, path, payload):
    monkeypatch.setenv('MCP_BEARER_TOKEN', 'testing-secret')
    assert client.post(path, json=payload).status_code == 401
    assert client.post(path, json=payload, headers={'Authorization': 'Bearer testing-secret'}).status_code == 200
    assert client.post(path, json=payload, headers={
        'Authorization': 'Bearer testing-secret', 'Origin': 'https://evil.example'}).status_code == 403


@pytest.mark.parametrize('uri,prompt_name,rule_marker,tool_marker', [
    ('astro://rules/jianchu', 'explore-day-officers', '十二值日', 'day_officers'),
    ('astro://rules/timeline', 'explore-annual-timeline', '年干四化', 'annual_timeline'),
    ('astro://rules/decision', 'compare-options', '主观', 'decision_matrix'),
])
def test_new_mcp_resources_and_prompts_return_real_content(uri, prompt_name, rule_marker, tool_marker):
    resource = process_rpc({'jsonrpc':'2.0','id':11,'method':'resources/read','params':{'uri':uri}})
    assert rule_marker in resource['result']['contents'][0]['text']
    prompt = process_rpc({'jsonrpc':'2.0','id':12,'method':'prompts/get', 'params':{'name':prompt_name}})
    assert tool_marker in prompt['result']['messages'][0]['content']['text']


def test_default_officer_year_range_not_capped_to_31_days():
    result = day_officer_calendar(DayOfficerRequest(start_date='2026-01-01', days=93))
    assert len(result['days']) == 93
    assert len(set(d['officer'] for d in result['days'])) == 12


def test_new_cli_workflows_match_rest(tmp_path):
    import json, subprocess, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    scenarios = [
        (['officers', '--date', '2026-10-15', '--days', '2'],
         day_officer_calendar(DayOfficerRequest(start_date='2026-10-15', days=2))),
        (['timeline', '--date', BIRTH['birth_datetime'], '--year', '2024', '--years', '2'],
         annual_timeline(TimelineRequest(birth=BirthInput(**BIRTH), start_lunar_year=2024, years=2))),
    ]
    p = tmp_path / 'decision.json'
    p.write_text(json.dumps(valid_matrix(), ensure_ascii=False), encoding='utf-8')
    scenarios.append((['decide', '--input', str(p)], decision_matrix(DecisionMatrixRequest(**valid_matrix()))))
    for args, expected in scenarios:
        run = subprocess.run([sys.executable, '-m', 'app.cli', *args], cwd=root,
                             text=True, capture_output=True, timeout=20)
        assert run.returncode == 0, run.stderr
        assert json.loads(run.stdout) == expected


def test_cli_decision_stdin_and_invalid_input():
    import json, subprocess, sys
    valid=subprocess.run([sys.executable,'-m','app.cli','decide','--input','-'],
        input=json.dumps(valid_matrix(),ensure_ascii=False),text=True,capture_output=True,timeout=20)
    assert valid.returncode == 0
    invalid=subprocess.run([sys.executable,'-m','app.cli','officers','--date','2026-10-15','--days','100'],
        text=True,capture_output=True,timeout=20)
    assert invalid.returncode == 2 and 'Error:' in invalid.stderr
