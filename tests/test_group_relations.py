"""Relations among two to eight charts: labels in both directions, triads, no score."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.advanced import DayunRequest, dayun_sequence
from app.engines import BirthInput, calculate_bazi, natal_interactions
from app.group import GroupRequest, group_relations
from app.main import app
from app.mcp import process_rpc

ROOT = Path(__file__).resolve().parents[1]
CLIENT = TestClient(app)


def member(label, when, **extra):
    return {'label': label, 'birth': {'birth_datetime': when, 'timezone': 'Asia/Shanghai'}, **extra}


FAMILY = [member('我', '1990-05-17T08:30'), member('妈妈', '1964-03-02T06:00'),
          member('爸爸', '1962-11-20T21:00', hour_unknown=True), member('弟弟', '1996-08-08T12:00')]


def test_members_and_directional_day_stem_labels():
    out = group_relations(GroupRequest(members=FAMILY))
    assert [m['pillars']['day'] for m in out['members']] == ['壬午', '庚戌', '壬戌', '丁丑']
    assert out['members'][2]['pillars']['hour'] is None and out['members'][0]['zodiac'] == '马'
    assert len(out['pairs']) == 6
    me_brother = next(p for p in out['pairs'] if (p['a_label'], p['b_label']) == ('我', '弟弟'))
    # 壬 sees 丁 as 正财; 丁 sees 壬 as 正官; the two day stems form 丁壬合木.
    assert me_brother['day_stems'] == {'a_sees_b': '正财', 'b_sees_a': '正官', 'combination': '丁壬合木'}
    assert me_brother['zodiac']['labels'] == ['六冲']  # 午 and 子
    me_mum = next(p for p in out['pairs'] if (p['a_label'], p['b_label']) == ('我', '妈妈'))
    month = next(link for link in me_mum['branch_links'] if link['a_pillar'] == link['b_pillar'] == 'month')
    assert month['labels'] == ['六害', '相刑']  # 巳 and 寅
    assert {'a_pillar': 'hour', 'a_label': '时柱', 'a_branch': '辰', 'b_pillar': 'year', 'b_label': '年柱',
            'b_branch': '辰', 'labels': ['同支', '相刑']} in me_mum['branch_links']
    assert me_mum['label_counts'] == {'同支': 1, '六合': 0, '六冲': 1, '六害': 2, '相刑': 2}
    assert out['rules']['compatibility_score'] is None
    assert out['element_overview']['day_masters']['水'] == ['我', '爸爸']


def test_unknown_hour_is_left_out_of_every_comparison():
    out = group_relations(GroupRequest(members=FAMILY))
    for p in out['pairs']:
        if '爸爸' in (p['a_label'], p['b_label']):
            side = 'a_pillar' if p['a_label'] == '爸爸' else 'b_pillar'
            assert all(link[side] != 'hour' for link in p['branch_links'])
    assert any('时辰不详' in n for n in out['notes'])
    assert sum(out['members'][2]['surface_five_elements'].values()) == 6


def test_unknown_hour_on_a_boundary_day_leaves_the_changing_pillars_out():
    # 2026 立春 falls at 04:02 China time on 2026-02-04: with the hour unknown, the year and month are unknown.
    lichun = member('立春', '2026-02-04T12:00', hour_unknown=True)
    late = {'label': '晚子', 'birth': {'birth_datetime': '1996-08-08T12:00', 'timezone': 'Asia/Shanghai',
                                     'late_zi_day_rollover': True}, 'hour_unknown': True}
    out = group_relations(GroupRequest(members=[lichun, FAMILY[0], late]))
    first, _, third = out['members']
    assert first['pillars'] == {'year': None, 'month': None, 'day': '己酉', 'hour': None}
    assert first['uncertain_pillars'] == ['year', 'month'] and first['zodiac'] is None and first['day_master'] == '己'
    # With the 23:00 day change the last hour belongs to the next day, so the day pillar (and day master) is unknown.
    assert third['uncertain_pillars'] == ['day'] and third['day_master'] is None and third['pillars']['year'] == '丙子'
    pairs = {(p['a_label'], p['b_label']): p for p in out['pairs']}
    assert pairs[('立春', '我')]['zodiac']['labels'] == [] and pairs[('立春', '我')]['day_stems']['a_sees_b'] == '正财'
    assert pairs[('我', '晚子')]['day_stems'] == {'a_sees_b': None, 'b_sees_a': None, 'combination': None}
    assert all(link['a_pillar'] not in ('year', 'month', 'hour') for link in pairs[('立春', '我')]['branch_links'])
    assert sum(first['surface_five_elements'].values()) == 2 and any('交节' in n for n in out['notes'])
    ordinary = group_relations(GroupRequest(members=FAMILY))
    assert all(m['uncertain_pillars'] == [] for m in ordinary['members'])


def test_three_harmony_needs_different_members_covering_all_three_branches():
    trio = [member('申', '1992-06-06T09:00'), member('子', '1996-08-08T12:00'), member('辰', '2000-08-16T04:00')]
    out = group_relations(GroupRequest(members=trio))
    year = [t for t in out['triads'] if t['pillar'] == 'year']
    assert year == [{'pillar': 'year', 'pillar_label': '年支（生肖）', 'triad': '申子辰', 'element': '水',
                     'members': [{'label': '申', 'branch': '申'}, {'label': '子', 'branch': '子'}, {'label': '辰', 'branch': '辰'}]}]
    two = group_relations(GroupRequest(members=trio[:2]))
    assert not [t for t in two['triads'] if t['pillar'] == 'year']


def test_bad_groups_are_rejected():
    for bad in ([FAMILY[0]], FAMILY * 3, [FAMILY[0], dict(FAMILY[1], label='我')], [FAMILY[0], dict(FAMILY[1], label='  ')],
                [FAMILY[0], dict(FAMILY[1], extra=1)]):
        with pytest.raises(ValidationError):
            GroupRequest(members=bad)
    assert CLIENT.post('/api/group-relations', json={'members': [FAMILY[0]]}).status_code == 422
    ok = CLIENT.post('/api/group-relations', json={'members': FAMILY[:2]})
    assert ok.status_code == 200 and ok.json()['system'] == 'group-relations'


def gendered(label, when, gender, **extra):
    m = member(label, when, **extra)
    m['birth']['gender'] = gender
    return m


YEAR_FAMILY = [gendered('我', '1990-05-17T08:30', 'male'), gendered('妈妈', '1964-03-02T06:00', 'female'),
               gendered('爸爸', '1962-11-20T21:00', 'male', hour_unknown=True), member('弟弟', '1996-08-08T12:00'),
               gendered('侄子', '2020-06-01T10:00', 'male')]


def test_year_view_lists_each_luck_pillar_and_the_year_pillar_against_each_chart():
    assert group_relations(GroupRequest(members=FAMILY))['year_view'] is None
    view = group_relations(GroupRequest(members=YEAR_FAMILY, year=2026))['year_view']
    assert (view['year'], view['year_pillar'], view['zodiac']) == (2026, '丙午', '马')
    rows = {m['label']: m for m in view['members']}
    assert [rows[k]['age'] for k in ('我', '妈妈', '爸爸', '弟弟', '侄子')] == [36, 62, 64, 30, 6]
    me = rows['我']['luck']
    assert (me['status'], me['pillar'], me['ten_god'], me['start_year'], me['changes_this_year']) == ('in_period', '甲申', '食神', 2017, False)
    # The same period and year listing as the luck page.
    dayun = dayun_sequence(DayunRequest(birth=BirthInput(**YEAR_FAMILY[0]['birth']), periods=12, include_years=True))
    period = next(p for p in dayun['periods'] if 2026 in [y['year'] for y in p['years']])
    assert period['pillar'] == me['pillar'] and period['natal_interactions']['ten_god_of_stem'] == me['ten_god']
    assert rows['我']['year_reading'] == natal_interactions('丙午', calculate_bazi(BirthInput(**YEAR_FAMILY[0]['birth'])))
    # No gender: no luck pillar, but the year pillar is still read against the chart.
    assert rows['弟弟']['luck']['status'] == 'needs_gender' and rows['弟弟']['luck']['pillar'] is None
    assert rows['弟弟']['year_reading']['ten_god_of_stem'] == '劫财'
    # An unknown hour leaves the hour pillar out of the year reading.
    assert all(r['pillar'] != 'hour' for r in rows['爸爸']['year_reading']['branch_relations'] + rows['爸爸']['year_reading']['stem_relations'])
    pairs = {(p['a_label'], p['b_label']): p for p in view['luck_pairs']}
    assert len(pairs) == 6 and not any('弟弟' in key for key in pairs)
    assert pairs[('我', '妈妈')]['branch_labels'] == ['同支']  # 甲申 and 庚申
    assert pairs[('我', '爸爸')]['branch_labels'] == ['六合', '相刑']  # 申 and 巳
    assert pairs[('爸爸', '侄子')]['stem_combination'] == '丁壬合木' and pairs[('爸爸', '侄子')]['branch_labels'] == []
    assert any('不预测' in n for n in view['notes']) and any('时辰不详' in n for n in view['notes'])


def test_year_view_before_birth_and_before_the_first_luck_period():
    view = group_relations(GroupRequest(members=YEAR_FAMILY, year=2015))['year_view']
    nephew = view['members'][4]
    assert (nephew['status'], nephew['age'], nephew['luck'], nephew['year_reading']) == ('not_born', None, None, None)
    assert all(p['b_label'] != '侄子' for p in view['luck_pairs'])
    young = group_relations(GroupRequest(members=YEAR_FAMILY, year=2020))['year_view']['members'][4]['luck']
    assert (young['status'], young['pillar'], young['start_year']) == ('not_started', None, 2021)


def test_year_view_with_an_unknown_hour_takes_both_ends_of_the_birth_day():
    me = YEAR_FAMILY[0]
    # The luck start moves with the hour: one pillar either way, but it may begin in 1996 or 1997.
    view = group_relations(GroupRequest(members=[gendered('甲', '1985-07-03T12:00', 'female', hour_unknown=True), me], year=2001))
    luck = view['year_view']['members'][0]['luck']
    assert (luck['status'], luck['pillar'], luck['start_year'], luck['start_years']) == ('in_period', '甲申', None, [1996, 1997])
    assert len(view['year_view']['luck_pairs']) == 1
    # Here the two ends fall in different periods: both are listed and no pillar is compared.
    view = group_relations(GroupRequest(members=[gendered('乙', '1985-09-19T12:00', 'female', hour_unknown=True), me], year=2001))
    luck = view['year_view']['members'][0]['luck']
    assert luck['status'] == 'depends_on_hour' and luck['pillar'] is None
    assert [(o['pillar'], o['start_year'], o['changes_this_year'], o['ten_god']) for o in luck['options']] == [
        ('丙戌', 1992, False, '正官'), ('丁亥', 2001, True, '七杀')]
    for option, clock in zip(luck['options'], ('00:00', '23:59')):
        birth = BirthInput(birth_datetime='1985-09-19T' + clock, timezone='Asia/Shanghai', gender='female')
        periods = dayun_sequence(DayunRequest(birth=birth, periods=12, include_years=True))['periods']
        assert option['pillar'] in [p['pillar'] for p in periods if 2001 in [y['year'] for y in p['years']]]
    assert view['year_view']['luck_pairs'] == []
    # Born on the 立春 day with the hour unknown: the month pillar itself is unknown.
    view = group_relations(GroupRequest(members=[gendered('丙', '2026-02-04T12:00', 'female', hour_unknown=True), me], year=2030))
    row = view['year_view']['members'][0]
    assert row['luck']['status'] == 'uncertain_pillars' and row['year_reading'] is None
    assert any('交节' in n for n in view['year_view']['notes'])


def test_unknown_hour_on_a_midnight_daylight_saving_change_uses_the_real_ends_of_the_day():
    def zoned(label, when, zone):
        return {'label': label, 'birth': {'birth_datetime': when, 'timezone': zone, 'gender': 'male'}, 'hour_unknown': True}
    # Sao Paulo, 28 January 1989: clocks fell back at midnight, so 23:00-23:59 came twice and the day ended at
    # the second 23:59 (UTC-3). Both ends count: the later one begins the second luck period in 2000.
    view = group_relations(GroupRequest(members=[zoned('甲', '1989-01-28T12:00', 'America/Sao_Paulo'),
                                                 zoned('乙', '1990-05-17T12:00', 'Asia/Shanghai')], year=2000))
    luck = view['year_view']['members'][0]['luck']
    assert luck['status'] == 'depends_on_hour'
    assert [(o['pillar'], o['start_year']) for o in luck['options']] == [('丙寅', 1991), ('丁卯', 2000)]
    late = BirthInput(birth_datetime='1989-01-28T23:59-03:00', timezone='America/Sao_Paulo', gender='male')
    periods = dayun_sequence(DayunRequest(birth=late, periods=12, include_years=True))['periods']
    assert [p['pillar'] for p in periods if 2000 in [y['year'] for y in p['years']]] == ['丁卯']
    # One pillar, two possible start years: start_year is None and start_years has both.
    early = group_relations(GroupRequest(members=[zoned('乙', '1990-05-17T12:00', 'Asia/Shanghai'),
                                                  zoned('丙', '1991-01-01T12:00', 'Asia/Shanghai')], year=1992))
    luck = early['year_view']['members'][0]['luck']
    assert (luck['status'], luck['start_year'], luck['start_years']) == ('not_started', None, [1996, 1997])
    # Havana, 7 October 1972: clocks also fell back at midnight, and the 寒露 jie came in the day's last two
    # hours (the clock read 23:00-23:59 twice), so the month pillar is unknown.
    view = group_relations(GroupRequest(members=[zoned('丁', '1972-10-07T12:00', 'America/Havana'),
                                                 zoned('乙', '1990-05-17T12:00', 'Asia/Shanghai')]))
    assert view['members'][0]['uncertain_pillars'] == ['month']


def test_year_is_validated_and_reaches_rest_and_mcp():
    for year in (1900, 2100, 'next'):
        with pytest.raises(ValidationError):
            GroupRequest(members=FAMILY[:2], year=year)
    rest = CLIENT.post('/api/group-relations', json={'members': YEAR_FAMILY[:2], 'year': 2026}).json()
    reply = process_rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                         'params': {'name': 'group_relations', 'arguments': {'members': YEAR_FAMILY[:2], 'year': 2026}}})
    assert reply['result']['structuredContent']['year_view'] == rest['year_view'] and rest['year_view']['year_pillar'] == '丙午'
    tools = process_rpc({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})['result']['tools']
    assert 'year_view' in next(t for t in tools if t['name'] == 'group_relations')['description']


def test_mcp_tool_chat_access_and_page_wiring():
    reply = process_rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                         'params': {'name': 'group_relations', 'arguments': {'members': FAMILY[:2]}}})
    assert reply['result']['structuredContent']['pairs'][0]['day_stems']['a_sees_b'] == '偏印'
    from app.chat import SPECIALISTS
    assert 'group_relations' in SPECIALISTS['bazi']['tools']
    html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
    assert 'data-tab="group"' in html
    app_js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    assert "'/api/group-relations'" in app_js and "if (active === 'group') return renderGroup();" in app_js
    assert "id = 'today-date'" in app_js and 'function pickRequest()' in app_js
