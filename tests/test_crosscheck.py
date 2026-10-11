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
    assert set(data['references']) == {'sxtwl', 'lunar_python', 'lunardate', 'ephem', 'iztro_py', 'pyswisseph'}
    # The page summary is written from the same run.
    page = json.loads((ROOT / 'static/crosscheck-summary.json').read_text(encoding='utf-8'))
    assert page['generated'] == data['generated'] and page['references'] == data['references']
    lunar_rows = {row['reference']: row for row in page['daily'] if row['field'] == 'lunar'}
    assert {k: (v['checked'], v['mismatches']) for k, v in lunar_rows.items()} == {
        k: (v['checked'], v['mismatches']) for k, v in days['lunar_dates'].items()}
    assert [d['first'] for d in page['differences']] == [d['first'] for d in days['lunar_month_differences']]
    assert all(d['cause'] in {'forecast', 'old_almanac', 'table'} for d in page['differences'])
    assert page['fixes'][0]['cause'] == 'beijing_meridian' and len(page['daily']) + len(page['ziwei']['rows']) == 16
    app_js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    assert "fetch('/static/crosscheck-summary.json')" in app_js and 'id="crosscheck-open"' in (ROOT / 'static/index.html').read_text(encoding='utf-8')
    pins = (ROOT / 'docs/evals/requirements.txt').read_text(encoding='utf-8')
    for name, version in data['references'].items():
        if name != 'pyswisseph':
            assert f"{name.replace('_', '-') if name == 'iztro_py' else name}=={version}" in pins
