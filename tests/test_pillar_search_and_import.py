"""Pillars-to-dates reverse lookup, pasted-chart checks and static asset delivery."""
from __future__ import annotations

import time
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.chart_import import ChartImportRequest, chart_import_check, parse_chart_text
from app.engines import BirthInput, calculate_bazi, calculate_ziwei, pillar_indices
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


def test_jie_edges_round_to_the_correct_side_of_the_instant():
    # 寒露 2026 falls at 14:29:18.24 Beijing time, inside the 未 hour.
    p = pillars_of({'birth_datetime': '2026-10-08T14:45', 'timezone': 'Asia/Shanghai'})
    (m,) = pillars_to_dates(PillarSearchRequest(**p, start_year=2026, end_year=2026))['matches']
    start, end = datetime.fromisoformat(m['start']), datetime.fromisoformat(m['end_exclusive'])
    assert m['start'] == '2026-10-08T14:29:19+08:00'
    got = lambda t: pillar_indices(t)[0]
    assert got(start) == got(end - timedelta(seconds=1)) != got(start - timedelta(seconds=1))
    assert got(end) != got(start)


def test_suggested_reading_avoids_repeated_and_skipped_clock_times():
    zone = 'America/New_York'
    fall = pillars_of({'birth_datetime': '2021-11-07T02:30', 'timezone': zone})
    (m,) = pillars_to_dates(PillarSearchRequest(**fall, timezone=zone, start_year=2021, end_year=2021))['matches']
    assert m['duration_minutes'] == 180 and m['suggested_local'] == '2021-11-07T02:15'  # 01:00–02:00 happens twice
    assert pillars_of({'birth_datetime': m['suggested_local'], 'timezone': zone}) == fall
    spring = pillars_of({'birth_datetime': '2021-03-14T01:30', 'timezone': zone})
    (m,) = pillars_to_dates(PillarSearchRequest(**spring, timezone=zone, start_year=2021, end_year=2021))['matches']
    assert m['duration_minutes'] == 60 and m['suggested_local'] == '2021-03-14T01:30'  # 02:00–03:00 never happens


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
    assert parse_chart_text('夫妻宮：無主星\n命宮位於午')['palace_major_stars'] == {'夫妻宫': []}


def test_long_padding_neither_changes_the_parse_nor_slows_it():
    padded = parse_chart_text('年柱：' + ' ' * 40 + '庚辰\n\n\n\n月柱：甲申　日柱：丙午\t\t時柱：庚寅\n\n命宮' + ' ' * 30 + '午')
    assert padded['pillars']['year'] == '庚辰' and padded['ming_branch'] == '午'
    started = time.perf_counter()
    for text in ('命宫' + ' ' * 5990 + 'x', '身宫' + '\n' * 5990 + 'x', ('年柱：' + ' ' * 2990) * 2):
        parse_chart_text(text)
    assert time.perf_counter() - started < 0.3  # quadratic backtracking took about 0.6 s for one of these


def test_a_chart_cast_with_the_late_zi_rule_is_traced_to_that_rule():
    late = dict(BIRTH, birth_datetime='2000-08-16T23:30')
    other = dict(late, late_zi_day_rollover=True)
    out = chart_import_check(ChartImportRequest(birth=late, text=chart_text(other)))
    # Day and hour pillars, plus the Zi Wei fields that follow the next day's lunar date.
    assert out['summary']['mismatched'] > 2
    assert {f['key'] for f in out['fields'] if not f['match']} >= {'pillar.day', 'pillar.hour'}
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


def test_brightness_printed_after_a_star_is_compared_as_a_table_difference():
    parsed = parse_chart_text('命宮 紫微廟\n夫妻宫：七杀（平） 火星\n官禄宫 廉贞利 天府【庙】\n疾厄宫 天同 巨门')
    assert parsed['palace_brightness'] == {'命宫': {'紫微': '庙'}, '夫妻宫': {'七杀': '平'}, '官禄宫': {'廉贞': '利', '天府': '庙'}}
    assert parsed['palace_major_stars']['夫妻宫'] == ['七杀'] and '疾厄宫' not in parsed['palace_brightness']
    out = chart_import_check(ChartImportRequest(birth=BIRTH, text='命宫 紫微庙\n夫妻宫：七杀平\n官禄宫 廉贞利 天府庙'))
    fields = {f['key']: f for f in out['fields']}
    assert fields['ziwei.brightness.命宫']['match'] and fields['ziwei.brightness.官禄宫']['match']
    assert (fields['ziwei.brightness.夫妻宫']['theirs'], fields['ziwei.brightness.夫妻宫']['ours']) == ('七杀平', '七杀庙')
    # Only the table differs: no rule variant is offered as the cause, and the cause names the table.
    assert out['variants'] == [] and out['reproducing_variants'] == []
    assert any('亮度表' in c for c in out['possible_causes'])
    # A grade for a star that is not in that palace here is left to the star comparison.
    moved = chart_import_check(ChartImportRequest(birth=BIRTH, text='夫妻宫 紫微庙'))
    assert 'ziwei.brightness.夫妻宫' not in {f['key'] for f in moved['fields']}


def test_a_late_zi_chart_with_brightness_still_finds_its_rule():
    late = dict(BIRTH, birth_datetime='2000-08-16T23:30')
    other = calculate_ziwei(BirthInput(**dict(late, late_zi_day_rollover=True)))
    text = chart_text(dict(late, late_zi_day_rollover=True)) + '\n' + '\n'.join(
        p['name'] + ' ' + ' '.join(star + p['star_brightness'][star] for star in p['main_stars']) for p in other['palaces'] if p['main_stars'])
    out = chart_import_check(ChartImportRequest(birth=late, text=text))
    assert out['reproducing_variants'][0] == '23:00 换日（早晚子时）'
