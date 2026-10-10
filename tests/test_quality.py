"""Independent published-almanac anchors and boundary/MCP integration tests.

Dates below are manually transcribed from the Hong Kong Observatory *text*
calendar tables, not produced by the implementation being tested:
https://www.hko.gov.hk/en/gts/time/calendar/text/files/T2024e.txt
https://www.hko.gov.hk/en/gts/time/calendar/text/files/T2033e.txt
For the future uncertainty windows, see HKO's conversion-table remarks.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.astronomy import chinese_lunar_date, from_jd, solar_term_jd
from app.engines import BirthInput
from app.main import app
from app.mcp import MODERN_PROTOCOL, PROMPTS, RESOURCES, TOOL_DEFS, process_rpc
from app.quality import QualityAuditRequest, calculation_quality_audit

client = TestClient(app)
BASE = {'birth_datetime': '2024-03-12T12:00', 'timezone': 'Asia/Shanghai'}
META = {
    'io.modelcontextprotocol/protocolVersion': MODERN_PROTOCOL,
    'io.modelcontextprotocol/clientCapabilities': {},
}

# (Gregorian month/day, assigned lunar year, lunar month, leap?)
HKO_2024_MONTH_STARTS = [
    ('01-11', 2023, 12, False), ('02-10', 2024, 1, False),
    ('03-10', 2024, 2, False), ('04-09', 2024, 3, False),
    ('05-08', 2024, 4, False), ('06-06', 2024, 5, False),
    ('07-06', 2024, 6, False), ('08-04', 2024, 7, False),
    ('09-03', 2024, 8, False), ('10-03', 2024, 9, False),
    ('11-01', 2024, 10, False), ('12-01', 2024, 11, False),
    ('12-31', 2024, 12, False),
]
HKO_2033_MONTH_STARTS = [
    ('01-01', 2032, 12, False), ('01-31', 2033, 1, False),
    ('03-01', 2033, 2, False), ('03-31', 2033, 3, False),
    ('04-29', 2033, 4, False), ('05-28', 2033, 5, False),
    ('06-27', 2033, 6, False), ('07-26', 2033, 7, False),
    ('08-25', 2033, 8, False), ('09-23', 2033, 9, False),
    ('10-23', 2033, 10, False), ('11-22', 2033, 11, False),
    ('12-22', 2033, 11, True),
]


@pytest.mark.parametrize('day,lunar_year,month,leap', HKO_2024_MONTH_STARTS)
def test_hko_2024_published_month_starts(day, lunar_year, month, leap):
    start = date.fromisoformat('2024-' + day)
    lunar = chinese_lunar_date(start)
    assert (lunar['year'], lunar['month'], lunar['day'], lunar['is_leap_month']) == (lunar_year, month, 1, leap)
    assert chinese_lunar_date(start - timedelta(days=1))['day'] >= 29


@pytest.mark.parametrize('day,lunar_year,month,leap', HKO_2033_MONTH_STARTS)
def test_hko_2033_published_month_starts(day, lunar_year, month, leap):
    start = date.fromisoformat('2033-' + day)
    lunar = chinese_lunar_date(start)
    assert (lunar['year'], lunar['month'], lunar['day'], lunar['is_leap_month']) == (lunar_year, month, 1, leap)
    assert chinese_lunar_date(start - timedelta(days=1))['day'] >= 29


def audit(iso='2024-03-12T12:00', **changes):
    return calculation_quality_audit(QualityAuditRequest(birth=BirthInput(birth_datetime=iso, **changes)))


def codes(data):
    return {item['code'] for item in data['flags']}


def test_quality_default_no_universal_false_positive():
    # The former 60 min default flagged *every* possible clock time as near
    # an hour boundary, because traditional two-hour bins have 60-min radius.
    result = audit()
    assert not result['review_needed']
    assert 'hour_boundary' not in codes(result)
    assert QualityAuditRequest(birth=BASE).boundary_window_minutes == 15


@pytest.mark.parametrize('instant,expected', [
    ('2024-03-12T01:05', 'hour_boundary'),
    ('2024-03-12T00:05', 'day_boundary'),
    ('2024-03-12T23:05', 'hour_boundary'),
])
def test_quality_chinese_hour_and_day_boundaries(instant, expected):
    result = audit(instant)
    assert expected in codes(result)
    assert result['review_needed']


def test_quality_zi_23_day_rolling_rule_is_explicit():
    traditional = audit('2024-03-12T23:05', late_zi_day_rollover=True)
    civil = audit('2024-03-12T23:05', late_zi_day_rollover=False)
    assert 'day_boundary' in codes(traditional)
    assert 'day_boundary' not in codes(civil)
    assert 'hour_boundary' in codes(civil)


def test_quality_nearest_jie_is_detected_using_actual_astronomical_time():
    minute = from_jd(solar_term_jd(2024, 315)).astimezone(__import__('zoneinfo').ZoneInfo('Asia/Shanghai'))
    result = audit((minute + timedelta(minutes=2)).isoformat())
    assert 'jie_boundary' in codes(result)
    assert result['calculation_snapshot']['minutes_since_previous_jie'] < 3


def test_quality_solar_time_date_change_and_timezone_notice():
    altered = audit('2024-03-12T00:10', time_mode='mean_solar', longitude=70.0)
    assert 'solar_time_date_change' in codes(altered)
    assert altered['calculation_snapshot']['effective_traditional_time'].startswith('2024-03-11')
    rome = audit('2024-03-12T12:00', timezone='Europe/Rome')
    assert 'cross_timezone_calendar_convention' in codes(rome)


@pytest.mark.parametrize('instant,expected', [
    ('2057-09-28T12:00', True),
    ('2089-09-04T12:00', False),
    ('2097-08-07T12:00', True),
])
def test_hko_uncertain_new_moon_periods_are_flagged_not_corrected(instant, expected):
    result = audit(instant)
    flag = next(x for x in result['flags'] if x['code'] == 'published_new_moon_uncertainty')
    assert flag['reference'].startswith('https://www.hko.gov.hk/')
    assert '不' in flag['detail']
    assert result['review_needed']
    current = result['calculation_snapshot']['lunar_date']
    # HKO's published text calendar starts these months at the date in instant.
    # Two distinct output dates are intentional algorithm-vs-reference differences.
    assert (current['day'] != 1) is expected


@pytest.mark.parametrize('instant', ['2057-10-12T12:00', '2089-09-19T12:00', '2097-08-25T12:00'])
def test_hko_uncertainty_propagates_through_lunar_month(instant):
    assert 'published_new_moon_uncertainty' in codes(audit(instant))


def test_hko_risk_flags_do_not_spill_to_ordinary_adjacent_dates():
    for instant in ('2057-09-27T12:00', '2057-10-28T12:00', '2097-08-06T12:00', '2097-09-06T12:00'):
        assert 'published_new_moon_uncertainty' not in codes(audit(instant))


def test_quality_schema_strict_rejects_unknown_fields_and_out_of_range_threshold():
    with pytest.raises(ValidationError):
        QualityAuditRequest(birth=BASE, unexpected='no')
    for limit in (0, 1441):
        with pytest.raises(ValidationError):
            QualityAuditRequest(birth=BASE, boundary_window_minutes=limit)


def modern_payload(method, params=None, id_=1):
    return {'jsonrpc': '2.0', 'id': id_, 'method': method,
            'params': {**(params or {}), '_meta': {**META, 'io.modelcontextprotocol/clientCapabilities': {}}}}


def modern_http(method, params=None, override_headers=None, payload=None):
    params = params or {}
    headers = {
        'MCP-Protocol-Version': MODERN_PROTOCOL,
        'Mcp-Method': method,
        'Accept': 'application/json, text/event-stream',
    }
    if method in ('tools/call', 'prompts/get', 'resources/read'):
        headers['Mcp-Name'] = params.get('uri' if method == 'resources/read' else 'name', '')
    headers.update(override_headers or {})
    return client.post('/mcp', json=payload or modern_payload(method, params), headers=headers)


def test_modern_mcp_request_requires_client_capabilities_and_http_400():
    missing = modern_payload('tools/list')
    missing['params']['_meta'].pop('io.modelcontextprotocol/clientCapabilities')
    response = modern_http('tools/list', payload=missing)
    assert response.status_code == 400
    assert response.json()['error']['code'] == -32602
    assert process_rpc(missing)['error']['code'] == -32602


@pytest.mark.parametrize('bad', [None, [], 'true', 10])
def test_modern_mcp_client_capabilities_must_be_object(bad):
    request = modern_payload('tools/list')
    request['params']['_meta']['io.modelcontextprotocol/clientCapabilities'] = bad
    response = modern_http('tools/list', payload=request)
    assert response.status_code == 400
    assert response.json()['error']['code'] == -32602


@pytest.mark.parametrize('method,params', [
    ('server/discover', {}), ('tools/list', {}), ('resources/list', {}),
    ('prompts/list', {}), ('resources/read', {'uri': 'astro://rules/quality'}),
])
def test_modern_mcp_replies_have_mandatory_cache_hints(method, params):
    response = modern_http(method, params)
    assert response.status_code == 200, response.text
    data = response.json()['result']
    assert data['resultType'] == 'complete'
    assert data['ttlMs'] >= 0
    assert data['cacheScope'] in {'public', 'private'}


def test_legacy_mcp_cache_hints_not_inadvertently_added():
    response = process_rpc({'jsonrpc': '2.0', 'id': 99, 'method': 'tools/list'})
    assert 'ttlMs' not in response['result']
    assert 'cacheScope' not in response['result']


def test_mcp_quality_tool_prompt_and_resource_are_coherent():
    assert any(x['name'] == 'chart_quality_audit' for x in TOOL_DEFS)
    assert any(x['name'] == 'audit-quality' for x in PROMPTS)
    assert any(x['uri'] == 'astro://rules/quality' for x in RESOURCES)
    response = modern_http('tools/call', {'name': 'chart_quality_audit', 'arguments': {'birth': BASE}})
    assert response.status_code == 200, response.text
    payload = response.json()['result']
    assert payload['isError'] is False
    assert payload['structuredContent']['system'] == 'chart-input-and-boundary-quality-audit'
    assert payload['structuredContent']['review_needed'] is False


def test_quality_rest_requires_auth_when_configured(monkeypatch):
    monkeypatch.setenv('MCP_BEARER_TOKEN', 'this-is-a-test-token')
    unauth = client.post('/api/quality-audit', json={'birth': BASE})
    assert unauth.status_code == 401
    good = client.post('/api/quality-audit', json={'birth': BASE},
                       headers={'Authorization': 'Bearer this-is-a-test-token'})
    assert good.status_code == 200
    assert good.json()['review_needed'] is False
    assert good.headers['Cache-Control'] == 'no-store'


def test_quality_rest_rejects_illegal_threshold():
    assert client.post('/api/quality-audit', json={'birth': BASE, 'boundary_window_minutes': 0}).status_code == 422


def test_utc_dst_ambiguous_time_is_not_silently_assumed():
    ambiguous = {'birth_datetime': '2024-10-27T02:30', 'timezone': 'Europe/Rome'}
    res = client.post('/api/quality-audit', json={'birth': ambiguous})
    assert res.status_code == 422
    explicit = {**ambiguous, 'birth_datetime': '2024-10-27T02:30+01:00'}
    assert client.post('/api/quality-audit', json={'birth': explicit}).status_code == 200


def test_quality_stdio_modern_same_result_as_http():
    request = modern_payload('tools/call', {'name': 'chart_quality_audit', 'arguments': {'birth': BASE}})
    run = subprocess.run([sys.executable, '-m', 'app.stdio'], input=json.dumps(request)+'\n',
                         text=True, capture_output=True, timeout=30)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout.strip())['result']
    assert result['structuredContent']['review_needed'] is False
    assert result['structuredContent']['system'] == 'chart-input-and-boundary-quality-audit'


def test_cli_quality_audit_entrypoint():
    run = subprocess.run([sys.executable, '-m', 'app.cli', 'quality-audit', '--date', '2024-03-12T12:00'],
                         text=True, capture_output=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)['review_needed'] is False


def test_local_dns_rebinding_host_defense_and_allowed_loopback():
    assert client.get('/health', headers={'Host':'malicious-controlled.example'}).status_code == 400
    assert client.post('/api/bazi', json=BASE,
                       headers={'Host':'malicious-controlled.example'}).status_code == 400
    assert client.post('/mcp', json={'jsonrpc':'2.0','id':1,'method':'ping'},
                       headers={'Host':'malicious-controlled.example'}).status_code == 400
    assert client.get('/health', headers={'Host':'127.0.0.1:8000'}).status_code == 200
    assert client.get('/health', headers={'Host':'localhost'}).status_code == 200


def test_rest_origin_policy_is_consistent_with_mcp():
    assert client.post('/api/quality-audit', json={'birth':BASE},
                       headers={'Origin':'https://malicious-controlled.example'}).status_code == 403
    assert client.post('/api/quality-audit', json={'birth':BASE},
                       headers={'Host':'localhost:8000','Origin':'http://localhost:8000'}).status_code == 200
