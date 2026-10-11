"""Regression checks for prior release capabilities."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.astronomy import CHINA, TERMS, from_jd, solar_term_jd
from app.engines import BirthInput, calculate_bazi, calculate_ziwei
from app.features import (
    CalendarRequest, PairInput, PalaceRequest, _branch_relation,
    calendar_days, compare_charts, palace_detail,
)
from app.main import app
from app.mcp import process_rpc, PROTOCOL
from app.reference import FOUR_TRANSFORMATIONS, FOUR_TYPES, NAYIN_NAMES, HIDDEN_STEMS

client = TestClient(app)


def birth(date_time='2000-08-16T04:00', **kwargs):
    return BirthInput(birth_datetime=date_time, **kwargs)


def rpc(method, params=None):
    return {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}}


def test_twelve_hidden_stems_are_complete():
    assert len(HIDDEN_STEMS) == 12
    assert sum(map(len, HIDDEN_STEMS.values())) == 28
    for branch, hidden in HIDDEN_STEMS.items():
        assert len(hidden) == len(set(hidden)), branch


def test_bazi_hidden_stems_and_nayin_anchor():
    b = calculate_bazi(birth())
    assert [b['pillars'][key]['na_yin'] for key in ('year','month','day','hour')] == [
        '白蜡金', '泉中水', '天河水', '松柏木',
    ]
    assert [x['stem'] for x in b['pillars']['day']['hidden_stems']] == ['丁','己']
    assert [x['ten_god'] for x in b['pillars']['day']['hidden_stems']] == ['劫财', '伤官']
    assert next(x for x in b['pillars']['hour']['hidden_stems'] if x['stem'] == '丙')['ten_god'] == '比肩'
    assert b['jie_boundaries']['previous']['name'] == '立秋'
    assert b['jie_boundaries']['next']['name'] == '白露'
    assert len(NAYIN_NAMES) == 30


def test_jie_temporal_boundaries_and_month_pillars():
    for year in (1979, 2000, 2024, 2050):
        for name, longitude, _month, _day in TERMS:
            if longitude % 30 != 15:
                continue
            moment = from_jd(solar_term_jd(year, longitude)).astimezone(CHINA)
            before = calculate_bazi(birth((moment - timedelta(minutes=5)).isoformat(), timezone='Asia/Shanghai'))
            after = calculate_bazi(birth((moment + timedelta(minutes=5)).isoformat(), timezone='Asia/Shanghai'))
            assert before['pillars']['month']['text'] != after['pillars']['month']['text'], (year, name)
            assert before['jie_boundaries']['next']['name'] == name
            assert after['jie_boundaries']['previous']['name'] == name


def test_four_transformations_complete_each_year_stem():
    assert len(FOUR_TRANSFORMATIONS) == 10
    assert all(len(FOUR_TRANSFORMATIONS[stem]) == 4 for stem in FOUR_TRANSFORMATIONS)
    for year in range(2010, 2020):
        z = calculate_ziwei(birth(f'{year}-08-16T04:00'))
        stem = z['year_pillar'][0]
        transformations = z['birth_year_transformations']
        assert len(transformations) == 4
        assert tuple(t['star'] for t in transformations) == FOUR_TRANSFORMATIONS[stem]
        assert tuple(t['type'] for t in transformations) == FOUR_TYPES
        assert all(t['star'] in z['star_positions'] for t in transformations)
        assert sorted(t['star'] for p in z['palaces'] for t in p['birth_year_transformations']) == sorted(FOUR_TRANSFORMATIONS[stem])
        assert all(len(p['palace_flying_transformations']) == 4 for p in z['palaces'])


def test_ziwei_transformations_reference_2000():
    z = calculate_ziwei(birth())
    assert [(t['star'], t['type']) for t in z['birth_year_transformations']] == [
        ('太阳','化禄'), ('武曲','化权'), ('太阴','化科'), ('天同','化忌'),
    ]
    assert [t['palace'] for t in z['birth_year_transformations']] == ['卯','寅','亥','丑']
    assert any(t['self_transform'] for p in z['palaces'] for t in p['palace_flying_transformations'])


def test_palace_detail_by_name_and_topic():
    info = palace_detail(PalaceRequest(birth=birth(), palace='命宫'))
    assert info['palace']['branch'] == '午'
    assert info['topic']
    assert len(info['palace']['palace_flying_transformations']) == 4
    with pytest.raises(ValidationError):
        PalaceRequest(birth=birth(), palace='不存在的宫位')


@pytest.mark.parametrize('relation,left,right', [
    ('六合','子','丑'),('六合','寅','亥'),('六合','午','未'),
    ('六冲','子','午'),('六冲','辰','戌'),('同支','酉','酉'),
    ('未标记六合或六冲','子','卯'),
])
def test_branch_relations_symmetrical(relation, left, right):
    assert _branch_relation(left, right) == relation
    assert _branch_relation(right, left) == relation


def test_pair_comparison_does_not_claim_compatibility():
    data = compare_charts(PairInput(person_a=birth(), person_b=birth('2001-01-01T12:00')))
    assert len(data['comparisons']) == 4
    assert data['comparisons'][2]['branch_relation'] == '六冲'
    assert data['rules']['compatibility_score'] is None
    assert 'notes' in data
    reverse = compare_charts(PairInput(person_a=birth('2001-01-01T12:00'), person_b=birth()))
    assert [r['branch_relation'] for r in data['comparisons']] == [r['branch_relation'] for r in reverse['comparisons']]


def test_calendar_known_lunar_festival_and_terms():
    out = calendar_days(CalendarRequest(start_date='2024-02-03', days=9))
    assert len(out['days']) == 9
    feb10 = next(x for x in out['days'] if x['date'] == '2024-02-10')
    assert (feb10['lunar']['year'],feb10['lunar']['month'],feb10['lunar']['day']) == (2024,1,1)
    feb4 = next(x for x in out['days'] if x['date'] == '2024-02-04')
    assert [t['name'] for t in feb4['solar_terms']] == ['立春']
    assert all(len(x['day_pillar']) == 2 for x in out['days'])


def test_calendar_crosses_year_and_range_rejects_overrun():
    out = calendar_days(CalendarRequest(start_date='2023-12-29', days=7))
    assert out['days'][-1]['date'] == '2024-01-04'
    with pytest.raises(ValueError, match='Date range'):
        calendar_days(CalendarRequest(start_date='2099-12-30', days=3))
    with pytest.raises(ValidationError):
        CalendarRequest(start_date='2024-02-01',days=32)
    with pytest.raises(ValidationError):
        CalendarRequest(start_date='2100-01-01', days=1)


def test_new_rest_endpoints():
    valid = {'birth_datetime': '2000-08-16T04:00'}
    for url, payload in [
        ('/api/calendar', {'start_date':'2024-02-04','days':7}),
        ('/api/pair', {'person_a':valid, 'person_b':valid}),
        ('/api/palace', {'birth':valid, 'palace':'命宫'}),
    ]:
        response = client.post(url, json=payload)
        assert response.status_code == 200, (url, response.text)
    assert len(client.get('/api/capabilities').json()['features']) >= 10
    assert client.post('/api/calendar', json={'start_date':'2024-01-01','days':999}).status_code == 422
    assert client.post('/api/pair', json={'person_a':valid}).status_code == 422


def test_new_mcp_tools_and_resources_prompts():
    init = process_rpc(rpc('initialize', {'protocolVersion':PROTOCOL}))['result']
    assert set(init['capabilities']) == {'tools','prompts','resources','extensions'}
    result = process_rpc(rpc('tools/list'))['result']['tools']
    assert len(result) == 27
    for name, args, field in [
        ('calendar_days', {'start_date':'2024-02-10','days':1}, 'days'),
        ('pair_comparison', {'person_a':{'birth_datetime':'2000-08-16T04:00'},'person_b':{'birth_datetime':'2001-01-01T12:00'}},'comparisons'),
        ('palace_detail', {'birth':{'birth_datetime':'2000-08-16T04:00'},'palace':'命宫'},'palace'),
    ]:
        response = process_rpc(rpc('tools/call',{'name':name,'arguments':args}))
        assert response['result']['isError'] is False, (name,response)
        assert field in response['result']['structuredContent']
    resources = process_rpc(rpc('resources/list'))['result']['resources']
    assert len(resources) == 17
    for res in resources:
        data = process_rpc(rpc('resources/read', {'uri':res['uri']}))['result']['contents'][0]
        assert data['mimeType'] == 'text/markdown'
        assert len(data['text']) > 80
    prompts = process_rpc(rpc('prompts/list'))['result']['prompts']
    assert len(prompts) == 15
    for prompt in prompts:
        msg = process_rpc(rpc('prompts/get',{'name':prompt['name'],'arguments':{'focus':'命宫'}}))['result']['messages'][0]
        assert msg['content']['type'] == 'text'
        assert '命宫' in msg['content']['text']


def test_mcp_invalid_protocol_and_resource_error():
    assert client.post('/mcp', json=rpc('ping'), headers={'MCP-Protocol-Version':'2030-01-01'}).status_code == 400
    assert client.post('/mcp', json=rpc('ping'), headers={'MCP-Protocol-Version':PROTOCOL}).status_code == 200
    assert process_rpc(rpc('resources/read',{'uri':'astro://rules/secret'}))['error']['code'] == -32602
    assert process_rpc(rpc('prompts/get',{'name':'wrong'}))['error']['code'] == -32602
    assert process_rpc(rpc('ping',{}))['result'] == {}
    assert process_rpc({'jsonrpc':'2.0','method':'ping','id':True})['error']['code'] == -32600


def test_reject_unknown_fields_and_guard_private_endpoint(monkeypatch):
    with pytest.raises(ValidationError):
        BirthInput(birth_datetime='2000-08-16T04:00', injected='not allowed')
    monkeypatch.setenv('MCP_BEARER_TOKEN','new-secret')
    assert client.post('/api/pair',json={'person_a':{'birth_datetime':'2000-08-16T04:00'},'person_b':{'birth_datetime':'2000-08-16T04:00'}}).status_code == 401
    assert client.get('/mcp').status_code == 401
    assert client.post('/api/calendar',json={'start_date':'2024-02-04'},headers={'Authorization':'Bearer new-secret'}).status_code == 200
