"""Relations among two to eight charts: labels in both directions, triads, no score."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

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
