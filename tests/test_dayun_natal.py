"""Luck and year pillars read against the natal chart."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.advanced import DayunRequest, dayun_sequence
from app.engines import BirthInput, branch_labels, calculate_bazi, natal_interactions
from app.main import app
from app.mcp import process_rpc

BIRTH = {'birth_datetime': '2000-08-16T04:00', 'timezone': 'Asia/Shanghai', 'gender': 'female'}  # 庚辰 甲申 丙午 庚寅


def test_punishment_belongs_to_the_pair_in_either_order():
    assert branch_labels('巳', '寅') == branch_labels('寅', '巳') == ['六害', '相刑']
    assert branch_labels('戌', '丑') == ['相刑'] and branch_labels('午', '午') == ['同支', '相刑']
    # 己巳 丙寅: the year branch comes first, which the old ordered lookup missed.
    b = calculate_bazi(BirthInput(birth_datetime='1989-02-10T10:00', timezone='Asia/Shanghai'))
    assert [r['labels'] for r in b['branch_relations'] if (r['a'], r['b']) == ('year', 'month')] == [['六害', '相刑']]


def test_luck_pillar_against_the_natal_chart():
    natal = calculate_bazi(BirthInput(**BIRTH))
    xu = natal_interactions('丙戌', natal)
    assert (xu['ten_god_of_stem'], xu['na_yin'], xu['growth_stage'], xu['self_stage']) == ('比肩', '屋上土', '墓', '墓')
    assert xu['branch_relations'] == [{'pillar': 'year', 'branch': '辰', 'labels': ['六冲']}]
    assert xu['branch_groups'] == [{'kind': '三合', 'branches': '寅午戌', 'element': '火', 'pillars': ['day', 'hour']}]
    si = natal_interactions('辛巳', natal)
    assert si['stem_relations'] == [{'pillar': 'day', 'stem': '丙', 'labels': ['丙辛合水']}]
    assert [(r['pillar'], r['labels']) for r in si['branch_relations']] == [('month', ['六合', '相刑']), ('hour', ['六害', '相刑'])]
    # 卯 is in the day pillar's void (丙午 belongs to the 甲辰 decade: 寅卯).
    assert natal_interactions('己卯', natal)['void_of'] == ['day']
    # Without the hour, nothing is read against the placeholder hour pillar.
    assert [r['pillar'] for r in natal_interactions('辛巳', natal, ('year', 'month', 'day'))['branch_relations']] == ['month']


def test_dayun_periods_and_years():
    plain = dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=3))
    assert [p['pillar'] for p in plain['periods']] == ['癸未', '壬午', '辛巳'] and 'years' not in plain['periods'][0]
    assert plain['periods'][0]['natal_interactions']['branch_relations'] == [{'pillar': 'day', 'branch': '午', 'labels': ['六合']}]
    full = dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=3, include_years=True, hour_unknown=True))
    years = full['periods'][2]['years']
    assert [y['year'] for y in years] == list(range(2023, 2033)) and years[3]['pillar'] == '丙午'
    assert years[3]['branch_relations'] == [{'pillar': 'day', 'branch': '午', 'labels': ['同支', '相刑']}]
    assert all(r['pillar'] != 'hour' for p in full['periods'] for item in [p['natal_interactions'], *p['years']] for r in item['branch_relations'])
    # The 辛巳 period begins in July 2023: 2023 is its first year and 2033, when 庚辰 begins, is the next period's.
    assert full['periods'][2]['approx_start_local'].startswith('2023-07') and full['periods'][2]['approx_end_local_exclusive'].startswith('2033-07')
    listed = [y['year'] for p in full['periods'] for y in p['years']]
    assert listed == list(range(2003, 2033))
    # The page labels each period from its start year to the year before the next start: the same years.
    assert all([y['year'] for y in p['years']] == list(range(int(p['approx_start_local'][:4]), int(p['approx_end_local_exclusive'][:4])))
               for p in full['periods'])


def test_rest_and_mcp_agree():
    args = {'birth': BIRTH, 'periods': 2, 'include_years': True}
    rest = TestClient(app).post('/api/dayun', json=args).json()
    reply = process_rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'bazi_dayun', 'arguments': args}})
    mcp = reply['result']['structuredContent']
    assert rest['periods'] == mcp['periods'] and len(rest['periods'][1]['years']) == 10
