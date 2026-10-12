"""Calendar meridian before 1929, and the committed cross-check report."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.astronomy import chinese_lunar_date
from app.extended import LunarToGregorianRequest, lunar_to_gregorian

ROOT = Path(__file__).resolve().parents[1]


def lunar(day: date) -> tuple:
    value = chinese_lunar_date(day)
    return value['year'], value['month'], value['day'], value['is_leap_month']


def test_republican_calendar_uses_the_beijing_meridian():
    # New moons a few minutes after midnight at UTC+8 fall before midnight at 116°25'E.
    # sxtwl, lunar_python and lunardate all start these months a day earlier.
    assert lunar(date(1914, 11, 17)) == (1914, 10, 1, False)
    assert lunar(date(1916, 2, 3)) == (1916, 1, 1, False)
    assert lunar(date(1920, 11, 10)) == (1920, 10, 1, False)
    assert chinese_lunar_date(date(1920, 11, 10))['method'] == 'astronomical-new-moon-beijing-116e25'
    # The Qing calendar and every year since 1929 keep UTC+8.
    assert lunar(date(1906, 4, 24)) == (1906, 4, 1, False)
    assert chinese_lunar_date(date(1929, 1, 1))['method'] == 'astronomical-new-moon-china-utc8'
    assert lunar(date(2057, 9, 29)) == (2057, 9, 1, False)
    inverse = lunar_to_gregorian(LunarToGregorianRequest(lunar_year=1914, lunar_month=10, lunar_day=1))
    assert inverse['gregorian_date'] == '1914-11-17' and inverse['method'] == 'astronomical-new-moon-beijing-116e25'


def test_committed_report_matches_its_data():
    data = json.loads((ROOT / 'docs/evals/crosscheck.json').read_text(encoding='utf-8'))
    readme = (ROOT / 'docs/evals/README.md').read_text(encoding='utf-8')
    assert data['system'] == 'xuanshu-crosscheck' and data['quick'] is False and data['years'] == [1901, 2099]
    days = data['days']
    assert days['pillars_at_noon']['sxtwl.day']['mismatches'] == 0
    for key in ('sxtwl', 'lunar_python', 'lunardate'):
        item = days['lunar_dates'][key]
        assert f"| 农历日期 vs {key} | {item['checked']:,} | {item['mismatches']:,} |" in readme
    for item in data['ziwei']['results'].values():
        assert item['checked'] == 3000
    # With the 23:00 day change XuanShu matches iztro's late Zi except where iztro keeps the month.
    late = data['ziwei']['late_zi']
    assert all(item['mismatches'] == 0 for item in late['rollover_vs_iztro_late_zi'].values())
    assert late['rollover_vs_iztro_late_zi']['stars']['checked'] + late['iztro_keeps_month']['births'] == late['births']
    assert set(data['references']) == {'sxtwl', 'lunar_python', 'lunardate', 'ephem', 'iztro_py', 'pyswisseph', 'iztro'}
    # Every other star and the four twelve-god cycles agree with iztro itself.
    assert data['ziwei']['results']['other_stars']['mismatches'] == 0 and data['ziwei']['results']['cycles']['mismatches'] == 0
    assert data['ziwei']['other_stars'] == {'star_count': 44, 'mismatching_stars': {}}
    # The page summary is written from the same run.
    page = json.loads((ROOT / 'static/crosscheck-summary.json').read_text(encoding='utf-8'))
    assert page['generated'] == data['generated'] and page['references'] == data['references']
    lunar_rows = {row['reference']: row for row in page['daily'] if row['field'] == 'lunar'}
    assert {k: (v['checked'], v['mismatches']) for k, v in lunar_rows.items()} == {
        k: (v['checked'], v['mismatches']) for k, v in days['lunar_dates'].items()}
    assert [d['first'] for d in page['differences']] == [d['first'] for d in days['lunar_month_differences']]
    assert all(d['cause'] in {'forecast', 'old_almanac', 'table'} for d in page['differences'])
    assert [fix['cause'] for fix in page['fixes']] == ['beijing_meridian', 'ziwei_star_tables']
    assert len(page['daily']) + len(page['ziwei']['rows']) == 18
    assert page['ziwei']['late_zi_month_kept'] == late['iztro_keeps_month']['births']
    # Period layers: every difference from iztro falls in a month where lunar_python's calendar differs.
    horoscope = data['horoscope']
    layers = {'decade', 'small_limit', 'year', 'month', 'day', 'hour'}
    flows = {'flow_decade', 'flow_year', 'flow_month', 'flow_day', 'flow_hour', 'year_twelve'}
    assert horoscope['sample']['pairs'] == 1000 and set(horoscope['results']) == layers | flows
    # Period stars depend only on each layer's stem and branch: no difference at all, not even in the calendar months.
    assert all(horoscope['results'][key]['mismatches'] == 0 for key in flows)
    assert set(horoscope['lunar_python_calendar_differs']) <= {'day', 'hour'}
    mismatches = sum(item['mismatches'] for item in horoscope['results'].values())
    assert mismatches == sum(horoscope['lunar_python_calendar_differs'].values())
    assert page['horoscope']['unexplained'] == 0 and page['horoscope']['calendar_differs'] == mismatches
    assert [(row['field'], row['mismatches']) for row in page['horoscope']['rows']] == [
        (key, horoscope['results'][key]['mismatches']) for key in ('decade', 'small_limit', 'year', 'month', 'day', 'hour')]
    assert [row['field'] for row in page['horoscope']['flow_rows']] == ['flow_decade', 'flow_year', 'flow_month', 'flow_day', 'flow_hour', 'year_twelve']
    assert '## 紫微运限对照 iztro' in readme and '| 流年流曜（流魁至流喜、年解） | 1,000 | 0 |' in readme
    app_js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    assert "fetch('/static/crosscheck-summary.json')" in app_js and 'id="crosscheck-open"' in (ROOT / 'static/index.html').read_text(encoding='utf-8')
    pins = (ROOT / 'docs/evals/requirements.txt').read_text(encoding='utf-8')
    assert json.loads((ROOT / 'docs/evals/package.json').read_text(encoding='utf-8'))['dependencies'] == {'iztro': data['references']['iztro']}
    for name, version in data['references'].items():
        if name not in ('pyswisseph', 'iztro'):
            assert f"{name.replace('_', '-') if name == 'iztro_py' else name}=={version}" in pins
