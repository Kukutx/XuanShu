"""Pillars-to-dates reverse lookup, pasted-chart checks and static asset delivery."""
from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.chart_import import ChartImportRequest, chart_import_check, parse_chart_text
from app.engines import BirthInput, calculate_bazi, calculate_ziwei
from app.main import app
from app.pillar_search import PillarSearchRequest, pillars_to_dates

CLIENT = TestClient(app)
BIRTH = {'birth_datetime': '2000-08-16T04:00', 'timezone': 'Asia/Shanghai', 'gender': 'female'}


def pillars_of(birth: dict) -> dict:
    return {k: v['text'] for k, v in calculate_bazi(BirthInput(**birth))['pillars'].items()}


def test_every_match_reproduces_the_pillars_and_contains_the_birth():
    p = pillars_of(BIRTH)
    out = pillars_to_dates(PillarSearchRequest(**p))
    assert out['count'] == 2 and not out['impossible_combination']
    spans = [(m['start'], m['end_exclusive']) for m in out['matches']]
    assert ('2000-08-16T03:00:00+08:00', '2000-08-16T05:00:00+08:00') in spans
    for m in out['matches']:
        inside = datetime.fromisoformat(m['suggested_local']).isoformat(timespec='minutes')
        assert pillars_of(dict(BIRTH, birth_datetime=inside)) == p
        assert datetime.fromisoformat(m['start']) < datetime.fromisoformat(m['end_exclusive'])


def test_whole_days_without_an_hour_and_both_zi_hour_rules():
    days = pillars_to_dates(PillarSearchRequest(year='庚辰', month='甲申', day='丙午'))
    assert all(m['duration_minutes'] == 1440 for m in days['matches'])
    split = pillars_to_dates(PillarSearchRequest(year='庚辰', month='甲申', day='壬午', hour='庚子'))
    assert [(m['start'][11:16], m['end_exclusive'][11:16]) for m in split['matches']] == [('00:00', '01:00'), ('23:00', '00:00')]
    joined = pillars_to_dates(PillarSearchRequest(year='庚辰', month='甲申', day='壬午', hour='庚子', late_zi_day_rollover=True))
    assert [(m['start'][5:16], m['end_exclusive'][5:16]) for m in joined['matches']] == [('09-05T23:00', '09-06T01:00')]


def test_solar_time_shifts_the_clock_interval():
    out = pillars_to_dates(PillarSearchRequest(year='庚辰', month='甲申', day='壬午', hour='壬寅',
                                               time_mode='apparent_solar', longitude=87.6))
    (m,) = out['matches']
    assert m['start'].startswith('2060-09-06T05:07') and m['effective_start'] == '2060-09-06T03:00:00'


def test_impossible_stems_are_explained_and_bad_pairs_rejected():
    out = pillars_to_dates(PillarSearchRequest(year='庚辰', month='丙申', day='壬午', hour='丙辰'))
    assert out['count'] == 0 and len(out['impossible_combination']) == 2
    assert '五虎遁' in out['impossible_combination'][0] and '五鼠遁' in out['impossible_combination'][1]
    for bad in ({'year': '庚丑', 'month': '甲申', 'day': '壬午'}, {'year': '庚辰', 'month': '甲申', 'day': '壬午', 'start_year': 2000, 'end_year': 1990},
                {'year': '庚辰', 'month': '甲申', 'day': '壬午', 'time_mode': 'mean_solar'}):
        with pytest.raises(ValidationError):
            PillarSearchRequest(**bad)
    assert CLIENT.post('/api/pillars-to-dates', json={'year': '庚丑', 'month': '甲申', 'day': '壬午'}).status_code == 422


def test_the_year_range_limits_results():
    p = pillars_of(BIRTH)
    out = pillars_to_dates(PillarSearchRequest(**p, start_year=1990, end_year=2010))
    assert [m['start'][:4] for m in out['matches']] == ['2000']


def chart_text(birth: dict) -> str:
    b, z = calculate_bazi(BirthInput(**birth)), calculate_ziwei(BirthInput(**birth))
    shen = next(p for p in z['palaces'] if p['is_shen'])
    lines = ['乾造 ' + ' '.join(b['pillars'][k]['text'] for k in ('year', 'month', 'day', 'hour')),
             f"命宫在{z['ming_palace']}，身宫在{shen['name'][:2]}，{z['five_elements_bureau']}，命主：{z['ming_master']} 身主：{z['shen_master']}"]
    lines += [f"{p['name']}：{' '.join(p['main_stars']) or '空宫'}" for p in z['palaces']]
    lines.append(' '.join(t['star'] + t['type'] for t in z['birth_year_transformations']))
    return '\n'.join(lines)


def test_a_matching_chart_agrees_on_every_recognized_field():
    out = chart_import_check(ChartImportRequest(birth=BIRTH, text=chart_text(BIRTH)))
    assert out['recognized_count'] == 4 + 5 + 12 + 4 and out['summary']['mismatched'] == 0
    assert out['variants'] == [] and out['possible_causes'] == []


def test_traditional_text_and_labelled_pillars_parse():
    parsed = parse_chart_text('年柱：庚辰 月柱：甲申 日柱：丙午 時柱：庚寅\n命宮(午) 紫微\n官祿宮 廉貞 天府\n命主武曲 身主天相')
    assert parsed['pillars'] == {'year': '庚辰', 'month': '甲申', 'day': '丙午', 'hour': '庚寅'}
    assert parsed['ming_branch'] == '午' and parsed['palace_major_stars'] == {'命宫': ['紫微'], '官禄宫': ['廉贞', '天府']}
    assert parse_chart_text('子女宫：太阳 天梁\n身宫在子女')['shen_palace'] == '子女宫'
    assert 'ming_branch' not in parse_chart_text('命宫 子女宫 天机')


def test_a_chart_cast_with_the_late_zi_rule_is_traced_to_that_rule():
    late = dict(BIRTH, birth_datetime='2000-08-16T23:30')
    other = dict(late, late_zi_day_rollover=True)
    out = chart_import_check(ChartImportRequest(birth=late, text=chart_text(other)))
    assert out['summary']['mismatched'] == 2  # day and hour pillars; Zi Wei ignores the rule
    assert out['reproducing_variants'][0] == '23:00 换日（早晚子时）'
    assert out['variants'][0]['settings']['late_zi_day_rollover'] is True
    assert any('23:00' in c for c in out['possible_causes'])


def test_unrecognized_text_lists_accepted_formats():
    out = CLIENT.post('/api/chart-import-check', json={'birth': BIRTH, 'text': 'hello'}).json()
    assert out['recognized_count'] == 0 and len(out['accepted_formats']) == 4
    assert CLIENT.post('/api/chart-import-check', json={'birth': BIRTH, 'text': 'x' * 6001}).status_code == 422


def test_static_assets_are_compressed_and_revalidated_but_api_is_not():
    js = CLIENT.get('/static/i18n-extra.js', headers={'Accept-Encoding': 'gzip'})
    assert js.headers['content-encoding'] == 'gzip' and js.headers['cache-control'] == 'no-cache'
    assert CLIENT.get('/static/i18n-extra.js', headers={'If-None-Match': js.headers['etag']}).status_code == 304
    api = CLIENT.post('/api/bazi', json=BIRTH, headers={'Accept-Encoding': 'gzip'})
    assert 'content-encoding' not in api.headers and api.headers['cache-control'] == 'no-store'
