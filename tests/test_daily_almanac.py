"""Today's calendar card, its personal section, and on-demand translation tables."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.almanac import DailyAlmanacRequest, daily_almanac
from app.main import app
from app.mcp import process_rpc

ROOT = Path(__file__).resolve().parents[1]
CLIENT = TestClient(app)
BIRTH = {'birth_datetime': '1990-05-17T08:30', 'timezone': 'Asia/Shanghai', 'gender': 'female'}


def test_calendar_facts_for_a_fixed_moment():
    out = daily_almanac(DailyAlmanacRequest(moment='2026-10-11T09:30'))
    assert out['pillars'] == {'year': '丙午', 'month': '戊戌', 'day': '戊午', 'hour': '丁巳'}
    assert out['weekday'] == '日' and out['zodiac'] == '马'
    assert out['lunar']['label'] == '九月初二' and out['lunar']['month_days'] == 30
    term = out['solar_term']
    assert term['current']['name'] == '寒露' and term['current']['start'] == '2026-10-08T14:29+08:00'
    assert term['current']['day_number'] == 4 and term['next']['name'] == '霜降' and term['next']['days_until'] == 12
    assert 0 < term['progress'] < 1
    assert out['day_officer'] == {'officer': '成', 'jie_boundary_on_date': False}
    assert out['moon']['phase'] == '新月' and out['moon']['waxing'] is True
    assert out['moon']['next_full_moon'].startswith('2026-10-26T12:1')
    assert out['personal'] is None and len(out['limitations']) == 3


def test_full_moon_term_day_and_another_zone():
    full = daily_almanac(DailyAlmanacRequest(moment='2026-10-26T12:30'))
    assert full['moon']['phase'] == '满月' and full['moon']['illuminated_fraction'] > 0.99
    assert full['moon']['next_full_moon'] > full['moment']  # the next one, not the current
    term_day = daily_almanac(DailyAlmanacRequest(moment='2026-10-08T20:00'))
    assert term_day['day_officer']['jie_boundary_on_date'] is True and term_day['solar_term']['current']['day_number'] == 1
    rome = daily_almanac(DailyAlmanacRequest(moment='2026-10-11T01:30', timezone='Europe/Rome'))
    assert rome['moment'].endswith('+02:00') and rome['pillars']['day'] == '戊午' and rome['pillars']['hour'][1] == '丑'
    assert rome['solar_term']['current']['start'] == '2026-10-08T08:29+02:00'


def test_offsets_pick_one_reading_and_jie_days_follow_the_card_zone():
    # A repeated autumn hour needs its offset; both readings are accepted and give different instants.
    first = daily_almanac(DailyAlmanacRequest(moment='2026-10-25T02:30+02:00', timezone='Europe/Rome'))
    second = daily_almanac(DailyAlmanacRequest(moment='2026-10-25T02:30+01:00', timezone='Europe/Rome'))
    assert first['moment'] == '2026-10-25T02:30+02:00' and second['moment'] == '2026-10-25T02:30+01:00'
    converted = daily_almanac(DailyAlmanacRequest(moment='2026-10-11T09:30+08:00', timezone='Europe/Rome'))
    assert converted['moment'] == '2026-10-11T03:30+02:00'
    # 2026 寒露 is 2026-10-07 23:29 in Los Angeles but 2026-10-08 in China: the flag follows the local date.
    eve = daily_almanac(DailyAlmanacRequest(moment='2026-10-07T20:00', timezone='America/Los_Angeles'))
    after = daily_almanac(DailyAlmanacRequest(moment='2026-10-08T09:00', timezone='America/Los_Angeles'))
    assert eve['day_officer']['jie_boundary_on_date'] is True and eve['solar_term']['next']['name'] == '寒露'
    assert after['day_officer']['jie_boundary_on_date'] is False and after['solar_term']['current']['day_number'] == 2
    assert eve['day_officer']['officer'] == after['day_officer']['officer']  # the officer repeats across a jie day


def test_personal_labels_against_the_natal_chart():
    out = daily_almanac(DailyAlmanacRequest(moment='2026-10-11T09:30', birth=BIRTH))
    me = out['personal']
    assert me['day_master'] == '壬水' and me['natal_pillars']['day'] == '壬午'
    rows = {r['pillar_of']: r for r in me['today_against_natal']}
    assert rows['day']['stem_ten_god'] == '七杀' and rows['hour']['stem_ten_god'] == '正财'
    assert {'type': '六冲', 'with': '时支', 'natal_branch': '辰'} in rows['month']['branch_relations']
    assert [x['with'] for x in rows['day']['branch_relations']] == ['年支', '日支']
    assert me['nominal_age'] == 37
    assert me['decade_period']['pillar'] == '丁丑' and me['decade_period']['stem_ten_god'] == '正财'
    unspecified = daily_almanac(DailyAlmanacRequest(moment='2026-10-11T09:30', birth=dict(BIRTH, gender='unspecified')))
    assert unspecified['personal']['decade_period'] is None
    infant = daily_almanac(DailyAlmanacRequest(moment='2026-10-11T09:30', birth=dict(BIRTH, birth_datetime='2026-09-01T08:00')))
    assert infant['personal']['decade_period']['note'] == '尚未起运' and infant['personal']['nominal_age'] == 1
    assert len(out['limitations']) == 4


def test_bad_requests_are_rejected():
    for bad in ({'moment': '2026-03-29T02:30', 'timezone': 'Europe/Rome'}, {'moment': '2026-10-25T02:30', 'timezone': 'Europe/Rome'},
                {'moment': '2100-01-01T00:00'}, {'moment': '2099-12-31T23:30-12:00'}, {'moment': 'today'},
                {'timezone': 'Mars/Olympus'}, {'moment': '2026-10-11T09:30', 'birth': dict(BIRTH, birth_datetime='2027-01-01T00:00')},
                {'moment': '2026-10-11T09:30', 'extra': 1}):
        with pytest.raises(ValidationError):
            DailyAlmanacRequest(**bad)
    assert CLIENT.post('/api/daily-almanac', json={'timezone': 'Mars/Olympus'}).status_code == 422
    now = CLIENT.post('/api/daily-almanac', json={}).json()
    assert now['system'] == 'daily-almanac' and now['personal'] is None


def test_mcp_tool_and_chat_access():
    reply = process_rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                         'params': {'name': 'daily_almanac', 'arguments': {'moment': '2026-10-11T09:30'}}})
    assert reply['result']['structuredContent']['lunar']['label'] == '九月初二'
    from app.chat import SHARED_TOOLS
    assert 'daily_almanac' in SHARED_TOOLS


def test_page_wiring_and_on_demand_translation_tables():
    html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
    assert 'data-tab="today"' in html and 'id="today-chip"' in html
    assert 'i18n-extra.js' not in html and 'zh-tw-map.js' not in html
    i18n = (ROOT / 'static/i18n.js').read_text(encoding='utf-8')
    assert re.search(r"en: \['i18n-extra\.js'", i18n) and re.search(r"'zh-TW': \['zh-tw-map\.js'", i18n)
    app_js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    assert "'/api/daily-almanac'" in app_js and "commonTabs = new Set(['chat','today'," in app_js
    assert '◐' not in html and 'data-mode="system"' in html
