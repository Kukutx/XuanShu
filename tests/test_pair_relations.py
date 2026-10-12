"""Two-person comparison: the group reading of a pair, and unknown birth hours."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.engines import BirthInput
from app.features import PairComparisonInput, PairInput, compare_charts
from app.group import GroupMember, GroupRequest, group_relations
from app.main import app
from app.mcp import process_rpc
from app.ziwei_pair import ziwei_pair_overlay

A = {'birth_datetime': '2000-08-16T04:00', 'timezone': 'Asia/Shanghai'}  # 庚辰 甲申 丙午 庚寅
B = {'birth_datetime': '1998-01-05T12:00', 'timezone': 'Asia/Shanghai'}  # 丁丑 壬子 壬子 丙午; 小寒 falls that day


def test_pair_reads_both_directions_and_every_branch_link():
    data = compare_charts(PairInput(person_a=BirthInput(**A), person_b=BirthInput(**B)))
    assert data['day_stems'] == {'a_sees_b': '七杀', 'b_sees_a': '偏财', 'combination': None}
    assert data['zodiac'] == {'a': '龙', 'b': '牛', 'labels': []}
    assert [(x['a_pillar'], x['b_pillar'], x['labels']) for x in data['branch_links']] == [
        ('day', 'year', ['六害']), ('day', 'month', ['六冲']), ('day', 'day', ['六冲']), ('day', 'hour', ['同支', '相刑'])]
    assert data['label_counts'] == {'同支': 1, '六合': 0, '六冲': 2, '六害': 1, '相刑': 1}
    # The same-position table keeps its old fields and gains the full labels; A's 午 day meets B's 午 hour only across.
    assert [(r['branch_relation'], r['labels']) for r in data['comparisons']] == [
        ('未标记六合或六冲', []), ('未标记六合或六冲', []), ('六冲', ['六冲']), ('未标记六合或六冲', [])]
    assert data['person_a']['pillars'] == {'year': '庚辰', 'month': '甲申', 'day': '丙午', 'hour': '庚寅'}
    assert data['rules']['compatibility_score'] is None
    # It is exactly the group reading of the same two people.
    group = group_relations(GroupRequest(members=[GroupMember(label='A', birth=BirthInput(**A)), GroupMember(label='B', birth=BirthInput(**B))]))
    pair = group['pairs'][0]
    assert (data['day_stems'], data['zodiac'], data['branch_links']) == (pair['day_stems'], pair['zodiac'], pair['branch_links'])


def test_unknown_hour_leaves_out_what_the_day_does_not_fix():
    data = compare_charts(PairInput(person_a=BirthInput(**A), person_b=BirthInput(**B), person_b_hour_unknown=True))
    # 小寒 on the birth day: the month pillar changes during the day, so it is unknown along with the hour.
    assert data['person_b']['pillars'] == {'year': '丁丑', 'month': None, 'day': '壬子', 'hour': None}
    assert data['person_b']['uncertain_pillars'] == ['month'] and data['person_b']['hour_unknown'] is True
    assert [(r['person_b'], r['branch_relation']) for r in data['comparisons'][1::2]] == [
        (None, '不比较（当天交节或换日）'), (None, '不比较（时辰不详）')]
    assert all(x['b_pillar'] in ('year', 'day') for x in data['branch_links'])
    assert any('时柱' in n for n in data['notes']) and any('交节' in n for n in data['notes'])
    # Without A's hour the day master is still known, but nothing is read from A's hour pillar.
    blind = compare_charts(PairInput(person_a=BirthInput(**A), person_b=BirthInput(**B), person_a_hour_unknown=True))
    assert blind['person_a']['pillars']['hour'] is None and blind['day_stems']['a_sees_b'] == '七杀'
    assert all(x['a_pillar'] != 'hour' for x in blind['branch_links'])


def test_ziwei_overlay_refuses_an_unknown_hour():
    with pytest.raises(ValueError, match='出生时辰'):
        ziwei_pair_overlay(PairInput(person_a=BirthInput(**A), person_b=BirthInput(**B), person_a_hour_unknown=True))
    response = TestClient(app).post('/api/ziwei-pair', json={'person_a': A, 'person_b': B, 'person_b_hour_unknown': True})
    assert response.status_code == 422 and '出生时辰' in response.json()['detail']


def test_rest_and_mcp_agree():
    args = {'person_a': A, 'person_b': B, 'person_b_hour_unknown': True}
    rest = TestClient(app).post('/api/pair', json=args).json()
    reply = process_rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'pair_comparison', 'arguments': args}})
    assert reply['result']['structuredContent'] == rest and rest['person_b']['pillars']['hour'] is None
    tools = process_rpc({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})['result']['tools']
    pair = next(t for t in tools if t['name'] == 'pair_comparison')
    assert 'person_b_hour_unknown' in pair['inputSchema']['properties'] and 'both directions' in pair['description']


def test_a_year_adds_the_same_luck_and_year_view_as_a_group_of_two():
    a, b = BirthInput(**A, gender='male'), BirthInput(**B, gender='female')
    assert compare_charts(PairInput(person_a=a, person_b=b))['year_view'] is None
    data = compare_charts(PairComparisonInput(person_a=a, person_b=b, year=2026))
    group = group_relations(GroupRequest(members=[GroupMember(label='A', birth=a), GroupMember(label='B', birth=b)], year=2026))
    assert data['year_view'] == group['year_view'] and data['year_view']['year_pillar'] == '丙午'
    assert [m['label'] for m in data['year_view']['members']] == ['A', 'B'] and len(data['year_view']['luck_pairs']) == 1
    # B's hour unknown on a jie day: the month pillar is open, so there is no luck pillar to compare.
    open_month = compare_charts(PairComparisonInput(person_a=a, person_b=b, person_b_hour_unknown=True, year=2026))['year_view']
    assert open_month['members'][1]['luck']['status'] == 'uncertain_pillars' and open_month['luck_pairs'] == []
    for year in (1900, 2100):
        with pytest.raises(ValueError):
            PairComparisonInput(person_a=a, person_b=b, year=year)
    # The Zi Wei overlay has no year view and still refuses unknown fields.
    assert TestClient(app).post('/api/ziwei-pair', json={'person_a': A, 'person_b': B, 'year': 2026}).status_code == 422
    args = {'person_a': dict(A, gender='male'), 'person_b': dict(B, gender='female'), 'year': 2026}
    rest = TestClient(app).post('/api/pair', json=args).json()
    reply = process_rpc({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'pair_comparison', 'arguments': args}})
    assert reply['result']['structuredContent']['year_view'] == rest['year_view'] == data['year_view']
    tools = process_rpc({'jsonrpc': '2.0', 'id': 4, 'method': 'tools/list'})['result']['tools']
    pair = next(t for t in tools if t['name'] == 'pair_comparison')
    assert 'year' in pair['inputSchema']['properties'] and 'year_view' in pair['description']
    ziwei = next(t for t in tools if t['name'] == 'ziwei_pair_overlay')
    assert 'year' not in ziwei['inputSchema']['properties']
