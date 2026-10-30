"""Rule sensitivity matrix and the moon-phase calendar export."""
from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.almanac import moon_phases
from app.exports import solar_terms_ics
from app.main import app
from app.mcp import process_rpc
from app.rule_matrix import RuleMatrixRequest, rule_matrix

ROOT = Path(__file__).resolve().parents[1]
CLIENT = TestClient(app)
CHINA = ZoneInfo('Asia/Shanghai')


def test_late_birth_with_longitude_and_daylight_saving():
    # 1990-05-17 23:30 Beijing: after 23:00, China observed daylight saving time, longitude given.
    out = rule_matrix(RuleMatrixRequest(birth={'birth_datetime': '1990-05-17T23:30', 'timezone': 'Asia/Shanghai', 'longitude': 116.4}))
    rows = {r['label']: r for r in out['rows']}
    assert out['rows'][0]['is_baseline'] and out['rows'][0]['differs'] == []
    assert out['summary']['variants'] == 14 and out['summary']['identical_variants'] == 1
    late = rows['23:00 换日（早晚子时）']
    # The 23:00 day change moves the bazi day and the Zi Wei lunar day together.
    assert late['changes'] == {'late_zi_day_rollover': True} and late['differs'] == ['pillar.day', 'pillar.hour', 'lunar', 'ming_stars']
    assert late['values']['lunar'] == '庚午年四月廿四' and out['rows'][0]['values']['lunar'] == '庚午年四月廿三'
    assert late['values']['pillar.day'] == '癸未' and out['rows'][0]['values']['pillar.day'] == '壬午'
    solar = rows['真太阳时']
    assert solar['effective_reading'] == '1990-05-17T22:19' and 'ming' in solar['differs'] and 'bureau' in solar['differs']
    # Standard time reads the same instant in a fixed UTC+8 zone; it changes the birth time, so it is not applied directly.
    dst = rows['扣除夏令时（按标准时）']
    assert dst['changes'] == {'birth_datetime': '1990-05-17T22:30', 'timezone': 'Etc/GMT-8'} and dst['applicable'] is False
    assert dst['values']['pillar.month'] == out['rows'][0]['values']['pillar.month'] and late['applicable'] is True
    assert rows['闰月整月按本月']['differs'] == []
    assert out['summary']['stable_fields'] == ['年柱', '月柱', '生年四化']
    assert any('23:00' in h for h in out['hints']) and any('夏令时' in h for h in out['hints'])
    # Each row carries complete settings that the page can apply to the birth form.
    assert solar['settings']['time_mode'] == 'apparent_solar' and solar['settings']['longitude'] == 116.4


def test_ordinary_birth_is_stable_and_missing_longitude_is_explained():
    out = rule_matrix(RuleMatrixRequest(birth={'birth_datetime': '2000-08-16T04:00', 'timezone': 'Asia/Shanghai'}))
    assert out['summary']['identical_variants'] == out['summary']['variants'] == 3
    assert out['summary']['sensitive_fields'] == [] and len(out['summary']['stable_fields']) == 10
    assert any('经度' in h for h in out['hints'])
    leap = rule_matrix(RuleMatrixRequest(birth={'birth_datetime': '2023-04-12T10:00', 'timezone': 'Asia/Shanghai'}))
    assert leap['rows'][0]['values']['lunar'] == '癸卯年闰二月廿二'
    assert '闰月整月按本月' in next(f for f in leap['summary']['sensitive_fields'] if f['field'] == 'ming')['changed_by']


def test_unknown_hour_and_range_edge():
    birth = {'birth_datetime': '1990-05-17T12:00', 'timezone': 'Asia/Shanghai', 'longitude': 116.4}
    out = rule_matrix(RuleMatrixRequest(birth=birth, hour_unknown=True))
    # The 23:00 rule moves the day at 23:59 and solar time moves the date near midnight, so the day pillar
    # and the lunar date depend on the unknown hour as well.
    assert out['hour_unknown'] and [f['key'] for f in out['fields']] == ['pillar.year', 'pillar.month', 'transformations']
    assert out['uncertain_fields'] == ['日柱', '农历']
    assert all(set(r['differs']) <= {'pillar.year', 'pillar.month', 'transformations'} for r in out['rows'])
    assert '时柱' not in out['summary']['stable_fields'] and any('时辰不详' in h for h in out['hints'])
    # Solar time moves 1901-01-01 00:10 back into 1900: that variant is skipped with its reason, not a failure.
    edge = rule_matrix(RuleMatrixRequest(birth={'birth_datetime': '1901-01-01T00:10', 'timezone': 'Asia/Shanghai', 'longitude': 75}))
    labels = [r['label'] for r in edge['rows']]
    assert '平太阳时' not in labels and any('平太阳时' in n and '1901' in n and '无法排盘' in n for n in edge['notes'])


def test_unknown_hour_drops_fields_that_change_within_the_day():
    # 2026-02-04: 立春 at 04:02 Beijing, so the year and month pillars depend on the unknown hour.
    out = rule_matrix(RuleMatrixRequest(birth={'birth_datetime': '2026-02-04T12:00', 'timezone': 'Asia/Shanghai'}, hour_unknown=True))
    keys = [f['key'] for f in out['fields']]
    assert 'pillar.year' not in keys and 'pillar.month' not in keys and out['uncertain_fields'][:2] == ['年柱', '月柱']
    # The 23:00 day-change rule makes the day pillar differ at 23:59, so it is dropped too.
    assert 'pillar.day' not in keys and '日柱' in out['uncertain_fields']
    assert any('同样不参与对照' in h and '年柱' in h for h in out['hints'])
    assert '年柱' not in out['summary']['stable_fields']


def test_dst_reading_near_a_clock_change_is_kept():
    # 03:30 on the morning Rome moves to summer time: 02:30 standard time does not exist on the wall clock,
    # but it is a valid reading in a fixed UTC+1 zone.
    out = rule_matrix(RuleMatrixRequest(birth={'birth_datetime': '2026-03-29T03:30', 'timezone': 'Europe/Rome'}))
    row = next(r for r in out['rows'] if r['label'] == '扣除夏令时（按标准时）')
    assert row['changes'] == {'birth_datetime': '2026-03-29T02:30', 'timezone': 'Etc/GMT-1'}
    assert row['effective_reading'] == '2026-03-29T02:30' and not any('无法排盘' in n for n in out['notes'])


def test_ics_lines_are_folded_at_75_octets():
    text = solar_terms_ics(2026, moon=True)
    lines = text.split('\r\n')
    assert all(len(line.encode('utf-8')) <= 75 for line in lines)
    assert any(line.startswith(' ') for line in lines)
    # Unfolding restores the original description, and no UTF-8 character is split.
    unfolded = text.replace('\r\n ', '')
    assert 'DESCRIPTION:日月地心黄经差到达 0°、90°、180° 或 270° 的时刻（UTC）。' in unfolded


def test_requests_api_and_mcp():
    with pytest.raises(ValidationError):
        RuleMatrixRequest(birth={'birth_datetime': '2000-08-16T04:00'}, extra=1)
    assert CLIENT.post('/api/rule-matrix', json={'birth': {'birth_datetime': 'soon'}}).status_code == 422
    reply = process_rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                         'params': {'name': 'rule_sensitivity_matrix', 'arguments': {'birth': {'birth_datetime': '2000-08-16T04:00'}}}})
    assert reply['result']['structuredContent']['system'] == 'rule-sensitivity-matrix'
    from app.chat import SHARED_TOOLS
    assert 'rule_sensitivity_matrix' in SHARED_TOOLS


def test_moon_phases_and_ics():
    phases = moon_phases(2026)
    assert len(phases) == 50 and [p['name'] for p in phases[:4]] == ['满月', '下弦月', '新月', '上弦月']
    full = [p['instant'].astimezone(CHINA) for p in phases if p['name'] == '满月']
    assert full[0].strftime('%m-%d %H:%M') == '01-03 18:02' and full[-1].strftime('%m-%d') == '12-24'
    assert any(p['instant'].astimezone(CHINA).strftime('%m-%d %H:%M') == '10-10 23:50' and p['name'] == '新月' for p in phases)
    with pytest.raises(ValueError):
        moon_phases(2100)
    plain, moon = solar_terms_ics(2026), solar_terms_ics(2026, moon=True)
    assert plain.count('BEGIN:VEVENT') == 24 and moon.count('BEGIN:VEVENT') == 74
    assert 'X-WR-CALNAME:二十四节气与月相' in moon and 'UID:moon-20261010-0@xuanshu.local' in moon
    reply = CLIENT.get('/api/solar-terms/2026.ics?moon=true')
    assert reply.status_code == 200 and 'solar-terms-moon-2026.ics' in reply.headers['content-disposition']
    assert CLIENT.get('/api/solar-terms/2026.ics').text.count('BEGIN:VEVENT') == 24


def test_page_wiring():
    html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
    assert 'data-tab="rule-matrix"' in html
    app_js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    assert "'/api/rule-matrix'" in app_js and "if (active === 'rule-matrix') return renderRuleMatrix();" in app_js
    assert "id = 'today-ics'" in app_js and "'moon=true'" in app_js and "'festivals=true'" in app_js
