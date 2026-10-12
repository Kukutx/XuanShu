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


def test_a_switch_exactly_on_a_whole_second_is_not_reported_a_second_late():
    # Mean solar time at 87.6°E runs 2 h 9 min 36 s behind the clock, so the 丑 hour opens at 03:09:36 exactly.
    out = pillars_to_dates(PillarSearchRequest(year='庚辰', month='甲申', day='丙午', hour='己丑', time_mode='mean_solar',
                                               longitude=87.6, start_year=2000, end_year=2000))
    (m,) = out['matches']
    assert m['start'] == '2000-08-16T03:09:36+08:00' and m['end_exclusive'] == '2000-08-16T05:09:36+08:00'
    assert m['effective_start'] == '2000-08-16T01:00:00'
    got = lambda t: pillar_indices(t, False, 'mean_solar', 87.6)[0]
    start = datetime.fromisoformat(m['start'])
    assert got(start)[3] != got(start - timedelta(seconds=1))[3]


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


def test_the_same_day_is_tried_at_every_double_hour():
    # Cast at 04:00 (寅), checked against the 12:00 placeholder a chart without the hour stands on.
    out = chart_import_check(ChartImportRequest(birth=dict(BIRTH, birth_datetime='2000-08-16T12:00'), text=chart_text(BIRTH)))
    hours = out['hour_alternatives']
    assert [h['label'] for h in hours] == ['早子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥', '晚子']
    assert [h['birth_datetime'][11:] for h in hours[:3]] == ['00:30', '02:00', '04:00'] and hours[-1]['birth_datetime'][11:] == '23:30'
    assert all(h['hour_pillar'][1] == h['branch'] for h in hours)
    assert out['reproducing_hours'] == ['寅'] and [h['label'] for h in hours if h['current']] == ['午']
    assert next(h for h in hours if h['label'] == '寅')['mismatched_fields'] == []


def tiger_hour(birth: dict) -> str:
    """The 寅 hour pillar of the birth's effective day (五鼠遁), so some hour of the day reproduces it."""
    stems, day = '甲乙丙丁戊己庚辛壬癸', pillars_of(birth)['day']
    return '时柱 ' + stems[(stems.index(day[0]) % 5 * 2 + 2) % 10] + '寅'


def test_hour_alternatives_land_in_their_hour_under_solar_time_and_daylight_saving():
    slot = lambda reading: 0 if reading[11:13] == '00' else 12 if reading[11:13] == '23' else (int(reading[11:13]) + 1) // 2
    cases = [dict(birth_datetime='1990-05-17T00:10', timezone='Asia/Shanghai', longitude=75.99, time_mode='apparent_solar'),
             dict(birth_datetime='2024-03-10T01:30', timezone='America/New_York', longitude=-74.0, time_mode='apparent_solar'),
             dict(birth_datetime='2024-03-10T12:00', timezone='America/New_York')]
    for birth in cases:
        hours = chart_import_check(ChartImportRequest(birth=birth, text=tiger_hour(birth)))['hour_alternatives']
        assert len(hours) == 13 and sum(h['current'] for h in hours) == 1
        days = set()
        for i, h in enumerate(hours):
            reading = calculate_bazi(BirthInput(**dict(birth, birth_datetime=h['birth_datetime'])))['time_basis']['effective_local_reading']
            assert slot(reading) == i, (birth, h, reading)
            days.add(reading[:10])
        assert len(days) == 1  # every hour of the same (effective) day
    # 2024-03-10 02:00 does not exist in New York: 丑 is tried in the middle of what is left of it, before the gap.
    assert hours[1]['birth_datetime'] == '2024-03-10T01:30'
    # The chart's own hour is its own moment, not the middle of the hour.
    late_noon = dict(BIRTH, birth_datetime='2000-08-16T12:50')
    own = chart_import_check(ChartImportRequest(birth=late_noon, text=tiger_hour(late_noon)))['hour_alternatives']
    assert [h['birth_datetime'] for h in own if h['current']] == ['2000-08-16T12:50']


def test_daylight_saving_days_keep_every_hour_that_exists_and_name_the_ones_that_do_not():
    slot = lambda reading: 0 if reading[11:13] == '00' else 12 if reading[11:13] == '23' else (int(reading[11:13]) + 1) // 2
    # Fall-back days with solar time, where the repeated hour sits next to 早子 and 丑, and London's spring-forward day.
    cases = [dict(birth_datetime='2024-11-03T12:00', timezone='America/New_York', longitude=-74.0, time_mode='apparent_solar'),
             dict(birth_datetime='2018-11-04T12:00', timezone='America/New_York', longitude=-74.0, time_mode='apparent_solar'),
             dict(birth_datetime='2024-03-31T12:00', timezone='Europe/London', longitude=-3.0, time_mode='apparent_solar'),
             dict(birth_datetime='2024-10-27T12:00', timezone='Europe/London', longitude=1.5, time_mode='mean_solar'),
             dict(birth_datetime='2024-10-27T12:00', timezone='Europe/London', longitude=1.5, time_mode='apparent_solar')]
    for birth in cases:
        out = chart_import_check(ChartImportRequest(birth=birth, text=tiger_hour(birth)))
        hours = out['hour_alternatives']
        assert len(hours) == 13 and out['missing_hours'] == [] and out['reproducing_hours'] == ['寅'], birth
        for i, h in enumerate(hours):
            reading = calculate_bazi(BirthInput(**dict(birth, birth_datetime=h['birth_datetime'])))['time_basis']['effective_local_reading']
            assert slot(reading) == i and reading[:10] == birth['birth_datetime'][:10] and h['effective_reading'] == reading[:16], (birth, h)
    # São Paulo skipped 00:00–00:59 on 2018-11-04 and repeated 23:00–23:59 on 2019-02-16: those halves of 子 have no clock time.
    for day, gone in (('2018-11-04', '早子'), ('2019-02-16', '晚子')):
        birth = dict(birth_datetime=day + 'T12:00', timezone='America/Sao_Paulo')
        out = chart_import_check(ChartImportRequest(birth=birth, text=tiger_hour(birth)))
        assert out['missing_hours'] == [gone] and len(out['hour_alternatives']) == 12
        assert gone not in [h['label'] for h in out['hour_alternatives']]


def test_a_day_pillar_difference_tries_the_hours_only_with_the_late_zi_day_change():
    # Another hour of the same day keeps the day pillar, except 晚子 when 23:00 starts the next day.
    late = dict(BIRTH, late_zi_day_rollover=True)
    next_day = pillars_of(dict(late, birth_datetime='2000-08-16T23:30'))['day']
    assert next_day != pillars_of(BIRTH)['day']
    plain = chart_import_check(ChartImportRequest(birth=BIRTH, text='日柱 ' + next_day))
    assert plain['summary']['mismatched'] == 1 and plain['hour_alternatives'] == [] and plain['missing_hours'] == []
    out = chart_import_check(ChartImportRequest(birth=late, text='日柱 ' + next_day))
    assert out['reproducing_hours'] == ['晚子'] and all(h['mismatched'] == 1 for h in out['hour_alternatives'][:-1])


def test_no_row_of_hours_when_every_hour_differs_by_as_much():
    # An hour pillar no hour of the day has: all thirteen hours would show the same single difference.
    noon = dict(BIRTH, birth_datetime='2000-08-16T12:00')
    every = {h['hour_pillar'] for h in chart_import_check(ChartImportRequest(birth=noon, text=tiger_hour(noon)))['hour_alternatives']}
    assert len(every) >= 12
    stems, branches = '甲乙丙丁戊己庚辛壬癸', '子丑寅卯辰巳午未申酉戌亥'
    impossible = next(stems[i % 10] + branches[i % 12] for i in range(60) if stems[i % 10] + branches[i % 12] not in every)
    out = chart_import_check(ChartImportRequest(birth=BIRTH, text='时柱 ' + impossible))
    assert out['summary']['mismatched'] == 1 and out['hour_alternatives'] == [] and out['reproducing_hours'] == []


def test_hours_are_not_tried_when_only_year_based_fields_differ():
    z = calculate_ziwei(BirthInput(**BIRTH))
    wrong = next(s for s in ('太阳', '武曲') if s != z['birth_year_transformations'][0]['star'])
    out = chart_import_check(ChartImportRequest(birth=BIRTH, text=f'年柱 {pillars_of(BIRTH)["year"]} {wrong}化禄'))
    assert out['summary']['mismatched'] == 1 and out['hour_alternatives'] == [] and out['reproducing_hours'] == []
