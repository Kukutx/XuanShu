"""Luck and year pillars read against the natal chart."""
from __future__ import annotations

from datetime import datetime, timedelta

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
    # The stems hidden in the luck pillar's branch, main qi first, each with its ten god against the day master 丙.
    assert [(h['stem'], h['element'], h['ten_god']) for h in si['hidden_stems']] == [('丙', '火', '比肩'), ('戊', '土', '食神'), ('庚', '金', '偏财')]
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
    args = {'birth': BIRTH, 'periods': 2, 'include_years': True, 'month_year': 2026}
    rest = TestClient(app).post('/api/dayun', json=args).json()
    reply = process_rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'bazi_dayun', 'arguments': args}})
    mcp = reply['result']['structuredContent']
    assert rest['periods'] == mcp['periods'] and len(rest['periods'][1]['years']) == 10
    assert rest['flow_months'] == mcp['flow_months'] and len(mcp['flow_months']['months']) == 12


def test_month_pillars_of_a_year():
    reply = dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=1, month_year=2026))
    flow = reply['flow_months']
    months = flow['months']
    assert (flow['year'], flow['year_pillar']) == (2026, '丙午') and [m['month'] for m in months] == list(range(1, 13))
    # 丙辛之岁寻庚上: the 寅 month of a 丙 year is 庚寅, and the months run on through the cycle to 辛丑.
    assert [m['pillar'] for m in months] == ['庚寅', '辛卯', '壬辰', '癸巳', '甲午', '乙未', '丙申', '丁酉', '戊戌', '己亥', '庚子', '辛丑']
    assert [m['jie'] for m in months] == ['立春', '惊蛰', '清明', '立夏', '芒种', '小暑', '立秋', '白露', '寒露', '立冬', '大雪', '小寒']
    # Each month ends where the next begins, at the exact jie, and the twelfth ends at the next 立春.
    assert all(a['end_local_exclusive'] == b['start_local'] for a, b in zip(months, months[1:]))
    assert months[0]['start_local'].startswith('2026-02-04') and months[-1]['end_local_exclusive'].startswith('2027-02-04')
    # A chart cast two days into each month has that month pillar.
    for m in months:
        inside = (datetime.fromisoformat(m['start_local']) + timedelta(days=2)).replace(tzinfo=None).isoformat(timespec='minutes')
        assert calculate_bazi(BirthInput(birth_datetime=inside, timezone='Asia/Shanghai'))['pillars']['month']['text'] == m['pillar']
    # Read against the natal chart like the years, without the hidden stems; their stars have rules too.
    assert months[4]['branch_relations'] == [{'pillar': 'day', 'branch': '午', 'labels': ['同支', '相刑']}] and 'hidden_stems' not in months[0]
    assert {s['name'] for m in months for s in m['shensha']} <= {r['name'] for r in reply['shensha_rules']}
    assert 'flow_months' not in dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=1))


def test_month_stems_follow_the_year_stem():
    # 甲己之年丙作首, 乙庚之岁戊为头, 丙辛之岁寻庚上, 丁壬壬寅顺水流, 若问戊癸何处起, 甲寅之上好追求.
    firsts = {year: dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=1, month_year=year))['flow_months']['months'][0]['pillar']
              for year in (2024, 2025, 2026, 2027, 2028, 2029, 2030)}
    assert firsts == {2024: '丙寅', 2025: '戊寅', 2026: '庚寅', 2027: '壬寅', 2028: '甲寅', 2029: '丙寅', 2030: '戊寅'}
    # The last supported year still ends at the following 立春.
    last = dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=1, month_year=2099))['flow_months']['months']
    assert last[-1]['end_local_exclusive'].startswith('2100-02-0')
    assert TestClient(app).post('/api/dayun', json={'birth': BIRTH, 'month_year': 1900}).status_code == 422


def test_luck_page_years_open_their_months():
    script = open('static/app.js', encoding='utf-8').read()
    # Each year of the picked decade is a button that fetches and toggles its month pillars below the table.
    assert "open.setAttribute('aria-expanded'" in script and 'month_year: year' in script and "panel.id = 'dayun-months'" in script
    assert '.dy-year-toggle[aria-expanded="true"]' in open('static/style.css', encoding='utf-8').read()
