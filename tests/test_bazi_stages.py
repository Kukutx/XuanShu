"""Twelve growth stages, voids and pillar relations in the BaZi chart."""
from __future__ import annotations

from app.engines import BRANCHES, STEMS, BirthInput, calculate_bazi, growth_stage, xun_kong


def chart(moment: str) -> dict:
    return calculate_bazi(BirthInput(birth_datetime=moment, timezone='Asia/Shanghai'))


def test_reference_chart_matches_lunar_python():
    # lunar_python 1.4 EightChar: getXxxDiShi 冠带 病 帝旺 长生, getXxxXunKong 申酉 午未 寅卯 午未.
    b = chart('2000-08-16T04:00')
    pillars = [b['pillars'][k] for k in ('year', 'month', 'day', 'hour')]
    assert [p['growth_stage'] for p in pillars] == ['冠带', '病', '帝旺', '长生']
    assert [p['xun_kong'] for p in pillars] == ['申酉', '午未', '寅卯', '午未']
    assert [p['self_stage'] for p in pillars] == ['养', '绝', '帝旺', '绝']
    # 申 (month) is in the year pillar's void, 寅 (hour) in the day pillar's.
    assert [p['void_of'] for p in pillars] == [[], ['year'], [], ['day']]
    assert [r['labels'] for r in b['stem_relations'] if r['labels']] == [['相冲'], ['相冲']]  # 庚甲 twice
    assert b['branch_groups'] == []


def test_yin_day_master_runs_backward_and_relations_are_listed():
    b = chart('1990-05-10T13:00')  # 庚午 辛巳 乙亥 癸未
    pillars = [b['pillars'][k] for k in ('year', 'month', 'day', 'hour')]
    assert [p['text'] for p in pillars] == ['庚午', '辛巳', '乙亥', '癸未']
    assert [p['growth_stage'] for p in pillars] == ['长生', '沐浴', '死', '养']
    assert [p['self_stage'] for p in pillars] == ['沐浴', '死', '死', '墓']
    assert [p['xun_kong'] for p in pillars] == ['戌亥', '申酉', '申酉', '申酉']
    assert pillars[2]['void_of'] == ['year']
    labels = {(r['a'], r['b']): r['labels'] for r in b['stem_relations'] if r['labels']}
    assert labels == {('year', 'day'): ['乙庚合金'], ('month', 'day'): ['相冲']}
    assert b['branch_groups'] == [{'kind': '三会', 'branches': '巳午未', 'element': '火', 'pillars': ['year', 'month', 'hour']}]
    assert '火土同宫' in b['rules']['growth_stage']


def test_growth_stage_table():
    # 帝旺 of each stem, from the traditional table: 甲卯 乙寅 丙午 丁巳 戊午 己巳 庚酉 辛申 壬子 癸亥.
    peaks = '卯寅午巳午巳酉申子亥'
    for stem, branch in zip(STEMS, peaks):
        assert growth_stage(STEMS.index(stem), BRANCHES.index(branch)) == '帝旺', stem
    for stem in range(10):
        assert len({growth_stage(stem, branch) for branch in range(12)}) == 12


def test_void_branches_of_the_six_decades():
    assert [xun_kong(first) for first in range(0, 60, 10)] == ['戌亥', '申酉', '午未', '辰巳', '寅卯', '子丑']
    assert all(xun_kong(first + k) == xun_kong(first) for first in range(0, 60, 10) for k in range(10))


def test_rest_and_mcp_return_the_new_fields():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.mcp import process_rpc

    birth = {'birth_datetime': '1990-05-10T13:00', 'timezone': 'Asia/Shanghai'}
    rest = TestClient(app).post('/api/bazi', json=birth).json()
    reply = process_rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'bazi_chart', 'arguments': birth}})
    mcp = reply['result']['structuredContent']
    fields = ('growth_stage', 'self_stage', 'xun_kong', 'void_of')
    for result in (rest, mcp):
        assert [result['pillars'][k]['growth_stage'] for k in ('year', 'month', 'day', 'hour')] == ['长生', '沐浴', '死', '养']
        assert result['pillars']['day']['void_of'] == ['year'] and result['pillars']['day']['xun_kong'] == '申酉'
        assert ['乙庚合金'] in [r['labels'] for r in result['stem_relations']]
        assert [(g['kind'], g['branches'], g['element']) for g in result['branch_groups']] == [('三会', '巳午未', '火')]
    assert {k: [rest['pillars'][p][k] for p in rest['pillars']] for k in fields} == {k: [mcp['pillars'][p][k] for p in mcp['pillars']] for k in fields}
    assert rest['stem_relations'] == mcp['stem_relations'] and rest['branch_groups'] == mcp['branch_groups']
