"""BaZi auxiliary stars (神煞): tables, placement on the pillars, luck and year pillars, and agreement with the
Zi Wei tables that share a rule."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.advanced import DayunRequest, dayun_sequence
from app.engines import BRANCHES, KUI_YUE_BY_STEM, LUCUN_BY_STEM, STEMS, TIANMA_BY_BRANCH, BirthInput, _star_positions, calculate_bazi
from app.main import app
from app.mcp import process_rpc
from app.shensha import RULE_BY_NAME, RULES, natal_bases, natal_shensha, nayin_phase, stars_on
from app.ziwei_extensions import year_branch_cycles

ROOT = Path(__file__).resolve().parents[1]
BIRTH = {'birth_datetime': '1990-05-17T08:30', 'timezone': 'Asia/Shanghai'}


def names(stars):
    return [star['name'] for star in stars]


def test_every_rule_has_a_full_table_a_rule_and_a_source():
    assert len(RULES) == len(RULE_BY_NAME) == 21
    for rule in RULES:
        assert rule['rule'] and rule['source'], rule['name']
        keys = set(rule['table'])
        if rule['name'] == '羊刃':
            assert keys == set(STEMS[::2])  # the five yang stems only
        elif rule['name'] == '魁罡':
            assert keys == {'庚辰', '壬辰', '戊戌', '庚戌'}
        elif rule['bases'] == ('year_nayin',):
            assert keys == set('金木水火土'), rule['name']
        elif rule['bases'][0].endswith('stem'):
            assert keys == set(STEMS), rule['name']
        else:
            assert keys == set(BRANCHES), rule['name']


def test_a_known_chart():
    # 庚午 辛巳 壬午 甲辰: day stem 壬 (天乙 卯巳, 太极 申巳, 红艳 巳), month 巳 (天德 辛, 月德 庚), year and day 午 (寅午戌
    # group), year 午 (巳午未); the year's 纳音 路旁土 puts 学堂 and 词馆 on 戊申 and 丁亥, which the chart does not have.
    b = calculate_bazi(BirthInput(**BIRTH))
    assert [b['pillars'][k]['text'] for k in ('year', 'month', 'day', 'hour')] == ['庚午', '辛巳', '壬午', '甲辰']
    assert {k: names(p['shensha']) for k, p in b['pillars'].items()} == {
        'year': ['将星', '月德贵人'], 'month': ['天乙贵人', '亡神', '天德贵人', '太极贵人', '红艳'], 'day': ['将星'], 'hour': ['寡宿']}
    assert b['pillars']['month']['shensha'][0]['by'] == [{'basis': 'day_stem', 'value': '壬'}]
    assert b['pillars']['year']['shensha'][0]['by'] == [{'basis': 'year_branch', 'value': '午'}, {'basis': 'day_branch', 'value': '午'}]
    # The rules listed are those of the stars shown, in table order.
    assert names(b['shensha_rules']) == ['天乙贵人', '将星', '亡神', '寡宿', '天德贵人', '月德贵人', '太极贵人', '红艳']
    assert b['shensha_rules'][0]['source'] == '《三命通会》卷三·论天乙贵人'
    assert '不断吉凶' in b['rules']['shensha']


def test_the_hour_pillar_is_never_a_basis():
    morning = calculate_bazi(BirthInput(birth_datetime='1990-05-17T08:30', timezone='Asia/Shanghai'))
    evening = calculate_bazi(BirthInput(birth_datetime='1990-05-17T20:30', timezone='Asia/Shanghai'))
    assert morning['pillars']['hour']['text'] != evening['pillars']['hour']['text']
    for key in ('year', 'month', 'day'):
        assert morning['pillars'][key]['shensha'] == evening['pillars'][key]['shensha']


def test_yang_ren_only_for_yang_day_stems_and_kui_gang_only_on_the_day_pillar():
    pillars = {'year': '甲子', 'month': '丙寅', 'day': '乙卯', 'hour': '庚辰'}
    assert '羊刃' not in [n for stars in natal_shensha(pillars).values() for n in names(stars)]
    pillars = {'year': '庚辰', 'month': '戊寅', 'day': '庚辰', 'hour': '丙子'}
    found = natal_shensha(pillars)
    assert '魁罡' in names(found['day']) and '魁罡' not in names(found['year'])
    assert '魁罡' not in names(stars_on('庚辰', natal_bases(pillars)))  # luck and year pillars do not carry it


def test_tables_shared_with_zi_wei_agree():
    for i, branch in enumerate(BRANCHES):
        cycle = {name: BRANCHES[pos] for pos, name in year_branch_cycles(i)['jiangqian'].items()}
        for name in ('将星', '华盖', '劫煞', '咸池', '亡神'):
            assert RULE_BY_NAME[name]['table'][branch] == cycle[name], (name, branch)
        assert RULE_BY_NAME['驿马']['table'][branch] == BRANCHES[TIANMA_BY_BRANCH[i]]
        # The Zi Wei engine's own placement (day, bureau, month, hour and stem do not move these two).
        ziwei = _star_positions(1, 2, 1, 0, 0, i)
        assert RULE_BY_NAME['红鸾']['table'][branch] == BRANCHES[ziwei['红鸾']]
        assert RULE_BY_NAME['天喜']['table'][branch] == BRANCHES[ziwei['天喜']]
    for i, stem in enumerate(STEMS):
        assert RULE_BY_NAME['禄神']['table'][stem] == BRANCHES[LUCUN_BY_STEM[i]]  # 禄存
        if i % 2 == 0:
            assert RULE_BY_NAME['羊刃']['table'][stem] == BRANCHES[(LUCUN_BY_STEM[i] + 1) % 12]  # 擎羊
        # 天乙贵人 sits where Zi Wei puts 天魁 and 天钺.
        assert set(RULE_BY_NAME['天乙贵人']['table'][stem]) == {BRANCHES[pos] for pos in KUI_YUE_BY_STEM[i]}


def test_luck_and_year_pillars_carry_stars_by_the_natal_bases():
    data = dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH, gender='male'), periods=9, include_years=True))
    natal = calculate_bazi(BirthInput(**BIRTH, gender='male'))
    bases = natal_bases({k: p['text'] for k, p in natal['pillars'].items()})
    shown = set()
    for period in data['periods']:
        for item in [period['natal_interactions'], *period['years']]:
            assert item['shensha'] == stars_on(item['pillar'], bases)
            shown |= set(names(item['shensha']))
    assert '魁罡' not in shown and shown
    assert names(data['shensha_rules']) == [rule['name'] for rule in RULES if rule['name'] in shown]
    assert any('神煞' in line for line in data['limitations'])


def test_rest_and_mcp_return_the_same_stars():
    rest = TestClient(app).post('/api/bazi', json=BIRTH).json()
    reply = process_rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'bazi_chart', 'arguments': BIRTH}})
    mcp = reply['result']['structuredContent']
    assert mcp['shensha_rules'] == rest['shensha_rules'] and {k: p['shensha'] for k, p in mcp['pillars'].items()} == {
        k: p['shensha'] for k, p in rest['pillars'].items()}
    tools = process_rpc({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})['result']['tools']
    assert 'shensha' in next(t for t in tools if t['name'] == 'bazi_chart')['description']


def test_stars_from_the_san_ming_tong_hui_follow_its_own_text():
    for i, stem in enumerate(STEMS):
        assert RULE_BY_NAME['金舆']['table'][stem] == BRANCHES[(LUCUN_BY_STEM[i] + 2) % 12]  # 禄前二辰
    # 红艳 as the book lists it (甲乙逢午……壬巳), not the 乙申、戊辰、壬子 of the 星学大成 and the common table.
    assert ''.join(RULE_BY_NAME['红艳']['table'][s] for s in STEMS) == '午午寅未子辰戌酉巳申'
    # 太极: each stem has a beginning and an end; 戊己 喜生乎申，得辰戌丑未为正库, so 申 as well as the four stores.
    assert [RULE_BY_NAME['太极贵人']['table'][s] for s in STEMS] == ['子午', '子午', '卯酉', '卯酉', '申辰戌丑未', '申辰戌丑未', '寅亥', '寅亥',
                                                                 '申巳', '申巳']


def test_the_page_names_every_basis_a_rule_reads():
    app_js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    line = next(line for line in app_js.splitlines() if line.startswith('const SHENSHA_BASIS = {'))
    assert {basis for rule in RULES for basis in rule['bases']} == set(re.findall(r'(\w+): \'', line))


def test_xue_tang_and_ci_guan_are_the_true_seats_of_the_years_na_yin():
    # 金命见辛巳 (学堂) and 壬申 (词馆) are the book's own examples; the others follow 余以类推.
    assert RULE_BY_NAME['学堂']['table'] == {'金': '辛巳', '木': '己亥', '水': '甲申', '火': '丙寅', '土': '戊申'}
    assert RULE_BY_NAME['词馆']['table'] == {'金': '壬申', '木': '庚寅', '水': '癸亥', '火': '乙巳', '土': '丁亥'}
    born, office = {'金': '巳', '木': '亥', '水': '申', '火': '寅', '土': '申'}, {'金': '申', '木': '寅', '水': '亥', '火': '巳', '土': '亥'}
    for phase in '金木水火土':
        for name, place in (('学堂', born), ('词馆', office)):
            pillar = RULE_BY_NAME[name]['table'][phase]
            assert pillar[1] == place[phase] and nayin_phase(pillar) == phase
    # 辛巳 is 白蜡金: on the day pillar it is the year's 学堂, but the year pillar is not its own.
    pillars = {'year': '辛巳', 'month': '壬申', 'day': '辛巳', 'hour': '丙寅'}
    found = natal_shensha(pillars)
    assert '学堂' in names(found['day']) and '词馆' in names(found['month']) and not {'学堂', '词馆'} & set(names(found['year']))
    assert found['day'][[n['name'] for n in found['day']].index('学堂')]['by'] == [{'basis': 'year_nayin', 'value': '金'}]
    bases = natal_bases(pillars)
    assert '学堂' in names(stars_on('辛巳', bases)) and '词馆' in names(stars_on('壬申', bases))  # a luck or year pillar can carry them
    assert not {'学堂', '词馆'} & set(names(stars_on('丁巳', bases)))  # 丁巳 is on 巳 but its 纳音 is 沙中土
