"""Independent published 2026 Qimen fixtures and complete dark-stem invariants.

The MIT public repository describes five example charts. Its 6 shared top-level
fields and 9 暗干 cells are compared one by one. Other palace fields remain
unverified by this corpus. The fixture carries its citation and source scope.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.engines import BirthInput
from app.main import app
from app.mcp import call_tool, process_rpc
from app.qimen import QimenRequest, qimen_chart, _dark_stems, EARTH_STEMS

FIXTURES = json.loads((Path(__file__).parent / 'fixtures' / 'qimen_public_2026.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('case', FIXTURES['cases'], ids=[v['datetime'] for v in FIXTURES['cases']])
def test_external_chart_dark_stems_all_palaces(case):
    request = QimenRequest(moment=BirthInput(birth_datetime=case['datetime'],timezone=FIXTURES['timezone']))
    result = qimen_chart(request)
    for field in ('dun','bureau','zhi_fu_star','zhi_fu_palace','zhi_shi_door','zhi_shi_palace'):
        assert result[field] == case[field], f"{case['datetime']} field {field}"
    assert set(case['dark_stems']) == {str(x) for x in range(1,10)}
    for palace in result['palaces']:
        assert palace['dark_stem'] == case['dark_stems'][str(palace['number'])], (
            f"{case['datetime']} 第{palace['number']}宫暗干")
    assert sorted(p['dark_stem'] for p in result['palaces']) == sorted(EARTH_STEMS)
    assert len(result['palaces']) == 9


@pytest.mark.parametrize('yang', [False,True])
@pytest.mark.parametrize('raw_palace',list(range(1,10)))
@pytest.mark.parametrize('stem', list('甲乙丙丁戊己庚辛壬癸'))
def test_dark_stem_invariants_for_yin_yang_and_center(yang, raw_palace, stem):
    data, anchor = _dark_stems(stem, '庚', raw_palace, yang)
    assert set(data) == set(range(1,10))
    assert set(data.values()) == set(EARTH_STEMS)
    assert anchor == (5 if stem == '甲' else raw_palace)
    assert data[anchor] == ('庚' if stem == '甲' else stem)
    direction = 1 if yang else -1
    order = [((anchor-1 + direction*i)%9)+1 for i in range(9)]
    stems = [data[palace] for palace in order]
    assert stems == list(EARTH_STEMS[EARTH_STEMS.index(data[anchor]):] + EARTH_STEMS[:EARTH_STEMS.index(data[anchor])])


def test_dark_stem_parity_rest_legacy_mcp_and_modern_mcp():
    body = {'moment':{'birth_datetime':'2026-12-08T12:00','timezone':'Asia/Shanghai'}}
    with TestClient(app) as client:
        rest = client.post('/api/qimen',json=body)
    assert rest.status_code == 200, rest.text
    out = rest.json()
    assert out['dark_stem_anchor'] == 5  # 甲时特例；不是值使门已寄宫位 4.
    assert out['zhi_shi_palace'] == 4
    assert out == call_tool('qimen_hour_chart',body)
    for protocol in ('2025-11-25', '2026-07-28'):
        params={'name':'qimen_hour_chart','arguments':body}
        if protocol == '2026-07-28':
            params['_meta']={'io.modelcontextprotocol/protocolVersion':protocol,
                             'io.modelcontextprotocol/clientCapabilities':{}}
        response=process_rpc({'jsonrpc':'2.0','id':8,'method':'tools/call','params':params})
        assert response['result']['structuredContent'] == out
