#!/usr/bin/env python3
"""Strict XuanShu functional contract audit (all published MCP Tools vs REST).

Exit nonzero if even one tool's HTTP invocation does not match its REST API.
Does not claim independent academic/astronomical validation, an OAuth login,
or third-party compatibility. Run from project root or an installed wheel.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.main import app
from app.mcp import TOOL_DEFS

BIRTH = {'birth_datetime': '2000-08-16T04:00', 'timezone': 'Asia/Shanghai', 'gender': 'male'}
MOMENT = {'birth_datetime': '2024-06-15T14:30', 'timezone': 'Asia/Shanghai'}
MATRIX = {
    'question': '比较两种方案', 'criteria': [{'name': '成本', 'weight': 2}],
    'options': [{'name': '方案甲', 'ratings': {'成本': 4}},
                {'name': '方案乙', 'ratings': {'成本': 2}}],
}

# Every advertised tool MUST appear here. Do not silently skip newly added tools.
CASES = OrderedDict([
    ('consultation_execute', ('/api/consultation', {'question': '2027年事业', 'birth': BIRTH})),
    ('deep_evidence_review', ('/api/deep-review', {'birth': BIRTH, 'lunar_year': 2026})),
    ('ziwei_professional_chart', ('/api/ziwei-professional', {'birth': BIRTH})),
    ('qimen_reference_audit', ('/api/qimen-reference-audit', {
        'moment': MOMENT, 'reference_source': 'local comparative fixture',
        'reference_school': '时家拆补转盘', 'root_fields': {'solar_term': '芒种'}})),
    ('qimen_hour_chart', ('/api/qimen', {'moment': MOMENT})),
    ('bazi_chart', ('/api/bazi', BIRTH)),
    ('ziwei_chart', ('/api/ziwei', BIRTH)),
    ('combined_chart', ('/api/combined', BIRTH)),
    ('symbolic_reading', ('/api/analyze', BIRTH)),
    ('solar_terms', ('/api/solar-terms/2026', {'year': 2026})),
    ('calendar_days', ('/api/calendar', {'start_date': '2024-02-10', 'days': 3})),
    ('pair_comparison', ('/api/pair', {'person_a': BIRTH, 'person_b': MOMENT})),
    ('ziwei_pair_overlay', ('/api/ziwei-pair', {'person_a': BIRTH, 'person_b': MOMENT})),
    ('annual_transformations', ('/api/annual', {'birth': BIRTH, 'lunar_year': 2026})),
    ('time_basis_audit', ('/api/time-audit', {'birth': {**BIRTH, 'longitude': 116.4}})),
    ('rule_comparison', ('/api/rules-compare', {'original': BIRTH, 'alternative': BIRTH})),
    ('structured_report', ('/api/report', {'birth': BIRTH})),
    ('lunar_to_gregorian', ('/api/lunar-to-gregorian', {'lunar_year': 2024, 'lunar_month': 1, 'lunar_day': 1})),
    ('birth_time_window', ('/api/birth-window', {'birth': BIRTH, 'uncertainty_minutes': 5, 'sample_every_minutes': 5})),
    ('chart_quality_audit', ('/api/quality-audit', {'birth': BIRTH})),
    ('day_officers', ('/api/day-officers', {'start_date': '2026-10-15', 'days': 3})),
    ('date_candidate_scan', ('/api/date-scan', {'start_date': '2026-10-15', 'days': 10, 'include_officers': ['成', '开'], 'hours': ['09:00']})),
    ('life_path_review', ('/api/life-path', {'birth': BIRTH, 'events': [{'date': '2020-03-01', 'title': '换工作'}]})),
    ('annual_timeline', ('/api/annual-timeline', {'birth': BIRTH, 'start_lunar_year': 2025, 'years': 3})),
    ('decision_matrix', ('/api/decision-matrix', MATRIX)),
    ('bazi_dayun', ('/api/dayun', {'birth': BIRTH, 'periods': 3})),
    ('birth_boundary_map', ('/api/birth-boundaries', {'birth': BIRTH, 'uncertainty_minutes': 3})),
    ('palace_detail', ('/api/palace', {'birth': BIRTH, 'palace': '命宫'})),
])

VERSION = '2026-07-28'
META = {'io.modelcontextprotocol/protocolVersion': VERSION,
        'io.modelcontextprotocol/clientCapabilities': {}}
HEADERS = {'MCP-Protocol-Version': VERSION, 'Accept': 'application/json, text/event-stream'}


def invoke(client: TestClient, name: str, args: dict):
    payload = {'jsonrpc': '2.0', 'id': 21, 'method': 'tools/call',
               'params': {'name': name, 'arguments': args, '_meta': META}}
    resp = client.post('/mcp', json=payload,
                       headers={**HEADERS, 'Mcp-Method': 'tools/call', 'Mcp-Name': name})
    return resp.status_code, resp.json()


def test_all():
    advertised = {d['name'] for d in TOOL_DEFS}
    if advertised != set(CASES):
        raise AssertionError(f'Tool inventory drift. Missing: {advertised - set(CASES)}; stale: {set(CASES) - advertised}')
    results = []
    client = TestClient(app)
    for name, (endpoint, payload) in CASES.items():
        try:
            if name == 'solar_terms':
                rest = client.get(endpoint)
            else:
                rest = client.post(endpoint, json=payload)
            status, rpc = invoke(client, name, payload)
            if name == 'ziwei_professional_chart' and rest.status_code == 422 and not app_professional_available():
                if status != 200 or not rpc.get('result', {}).get('isError', False):
                    raise AssertionError(f'Expected explicit optional-provider error: REST {rest.status_code}, MCP {rpc}')
                results.append((name, 'OPTIONAL_DEPENDENCY_NOT_INSTALLED'))
                continue
            if status != 200 or rest.status_code != 200:
                raise AssertionError(f'HTTP failure: REST {rest.status_code} {rest.text[:300]}, MCP {status} {str(rpc)[:300]}')
            structure = rpc['result']['structuredContent']
            expected = rest.json()
            if structure != expected:
                # Show only differing high-level keys, avoid user birth-record logging.
                keys = sorted(set(structure) ^ set(expected)) if isinstance(structure, dict) and isinstance(expected, dict) else []
                raise AssertionError(f'REST/MCP output mismatch (keys symmetric diff={keys})')
            results.append((name, 'PASS'))
        except Exception as exc:
            results.append((name, f'FAIL: {exc}'))
    return results


def app_professional_available():
    from app.professional_ziwei import professional_provider_available
    return professional_provider_available()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='Emit concise machine-readable result')
    args = parser.parse_args()
    results = test_all()
    failures = [(n, status) for n, status in results if status.startswith('FAIL')]
    output = {'tools': len(results), 'passed': sum(s == 'PASS' for _, s in results),
              'dependency_unavailable': sum(s.startswith('OPTIONAL_') for _, s in results),
              'failed': len(failures), 'results': results}
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        for name, status in results:
            print(f'{status}: {name}')
        print(f"TOTAL {output['tools']} tools, {output['passed']} REST/MCP matches, {output['dependency_unavailable']} optional unavailable, {output['failed']} failures")
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
