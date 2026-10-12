"""Date-range candidate scan (择日择时) and Life Path event review."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.date_selection import MAX_QIMEN_CHARTS, DateScanRequest, date_candidate_scan
from app.life_path import LifePathRequest, life_path_review
from app.engines import BirthInput
from app.main import app
from app.workflows import DayOfficerRequest, day_officer_calendar

CLIENT = TestClient(app)
BIRTH = {'birth_datetime': '2000-08-16T04:00', 'timezone': 'Asia/Shanghai', 'gender': 'female'}


def test_scan_filters_match_the_officer_calendar():
    out = date_candidate_scan(DateScanRequest(start_date='2026-11-01', days=30, include_officers=['成', '开']))
    expected = [d['date'] for d in day_officer_calendar(DayOfficerRequest(start_date='2026-11-01', days=30))['days']
                if d['officer'] in ('成', '开')]
    assert [c['date'] for c in out['candidates']] == expected
    assert out['excluded_counts']['officer_not_included'] == 30 - len(expected)
    # Every scanned day is either a candidate or an excluded day with its reason, so a calendar can show the whole range.
    assert sorted([c['date'] for c in out['candidates']] + [d['date'] for d in out['excluded_days']]) == [
        d['date'] for d in day_officer_calendar(DayOfficerRequest(start_date='2026-11-01', days=30))['days']]
    assert {d['reason'] for d in out['excluded_days']} == {'officer_not_included'} and out['scanned_through'] == '2026-11-30'
    assert set(out['excluded_days'][0]) == {'date', 'day_pillar', 'officer', 'jie_on_date', 'reason', 'natal_clashes'}
    assert out['order'].startswith('chronological')
    assert all('score' not in c for c in out['candidates'])


def test_scan_natal_clash_labels_and_exclusion():
    labelled = date_candidate_scan(DateScanRequest(start_date='2026-11-01', days=24, birth=BIRTH))
    # Natal year branch 辰 and day branch 午 clash with 戌 and 子 days.
    clashing = {c['date'] for c in labelled['candidates'] if c['natal_clashes']}
    assert clashing and all(c['day_branch'] in ('戌', '子') for c in labelled['candidates'] if c['natal_clashes'])
    filtered = date_candidate_scan(DateScanRequest(start_date='2026-11-01', days=24, birth=BIRTH, exclude_natal_clash=True))
    assert not clashing & {c['date'] for c in filtered['candidates']}
    assert filtered['excluded_counts']['natal_clash'] == len(clashing)
    assert {d['date'] for d in filtered['excluded_days'] if d['reason'] == 'natal_clash'} == clashing
    assert all(d['natal_clashes'] for d in filtered['excluded_days'])


def test_scan_hour_charts_use_qimen_engine_and_are_capped():
    out = date_candidate_scan(DateScanRequest(start_date='2026-11-02', days=1, hours=['10:00']))
    chart = out['candidates'][0]['hour_charts'][0]
    assert (chart['dun'], chart['bureau'], chart['zhi_fu_star'], chart['zhi_shi_door']) == ('阴遁', 5, '天辅', '杜门')
    capped = date_candidate_scan(DateScanRequest(start_date='2026-01-01', days=60, hours=['09:00', '15:00'], max_results=60))
    assert sum(len(c['hour_charts']) for c in capped['candidates']) == MAX_QIMEN_CHARTS and capped['truncated']
    # Every emitted candidate carries all requested charts; none is left half-computed.
    assert all(len(c['hour_charts']) == 2 for c in capped['candidates'])
    # The scan stops on the first day it cannot chart: days up to it are listed, later ones are not scanned.
    scanned = sorted([c['date'] for c in capped['candidates']] + [d['date'] for d in capped['excluded_days']])
    assert scanned[0] == '2026-01-01' and scanned[-1] == capped['scanned_through'] == '2026-01-20' and len(scanned) == 20
    odd = date_candidate_scan(DateScanRequest(start_date='2026-01-01', days=60, hours=['09:00', '12:00', '15:00']))
    assert all(len(c['hour_charts']) == 3 for c in odd['candidates']) and len(odd['candidates']) == MAX_QIMEN_CHARTS // 3


def test_jie_boundary_found_when_the_jie_falls_after_23_00():
    # 2006 立夏 falls between 23:00 and midnight Beijing time on 2006-05-05.
    days = {d['date']: d for d in day_officer_calendar(DayOfficerRequest(start_date='2006-05-04', days=3))['days']}
    assert [days[k]['jie_boundary_on_date'] for k in sorted(days)] == [False, True, False]
    out = date_candidate_scan(DateScanRequest(start_date='2006-05-04', days=3, exclude_jie_boundary_days=True))
    assert '2006-05-05' not in {c['date'] for c in out['candidates']} and out['excluded_counts']['jie_boundary'] == 1
    assert [(d['date'], d['reason'], d['jie_on_date']['name']) for d in out['excluded_days']] == [('2006-05-05', 'jie_boundary', '立夏')]


@pytest.mark.parametrize('payload', [
    {'start_date': '2026-01-01', 'include_officers': ['成'], 'exclude_officers': ['成']},
    {'start_date': '2026-01-01', 'exclude_natal_clash': True},
    {'start_date': '2026-01-01', 'hours': ['25:00']},
    {'start_date': '2099-12-30', 'days': 5},
    {'start_date': '2026-01-01', 'days': 94},
])
def test_scan_rejects_invalid_requests(payload):
    with pytest.raises(ValidationError):
        DateScanRequest.model_validate(payload)


def test_life_path_places_events_on_traditional_labels():
    out = life_path_review(LifePathRequest(birth=BIRTH, events=[
        {'date': '2022-07-01', 'title': '毕业'}, {'date': '2001-02-01', 'title': '立春前'}]))
    early, graduation = out['events']
    # 2001-02-01 is before 立春, so the solar year pillar is still 庚辰, while the lunar year is 2001.
    assert early['solar_year_pillar'] == '庚辰' and early['lunar_year'] == 2001
    assert early['dayun']['pillar'] == '起运前'
    assert graduation['solar_year_pillar'] == '壬寅'
    assert {'type': '六冲', 'with': '月支', 'natal_branch': '申'} in graduation['solar_year_branch_relations']
    assert graduation['dayun']['pillar'] == '壬午' and len(graduation['annual_transformations']) == 4
    assert out['natal_pillars']['day'] == '丙午'


def test_life_path_never_guesses_dayun_direction():
    out = life_path_review(LifePathRequest(birth={**BIRTH, 'gender': 'unspecified'}, events=[{'date': '2020-01-01', 'title': 'x'}]))
    assert out['events'][0]['dayun'] is None and out['notes']
    with pytest.raises(ValidationError):
        LifePathRequest(birth=BIRTH, events=[{'date': '1999-01-01', 'title': '出生前'}])


def test_life_path_uses_the_birth_date_in_the_stated_zone():
    # 2000-08-15T20:00Z is 2000-08-16 04:00 in Shanghai, so 2000-08-15 is before the local birth date.
    aware = {**BIRTH, 'birth_datetime': '2000-08-15T20:00:00+00:00'}
    with pytest.raises(ValidationError):
        LifePathRequest(birth=aware, events=[{'date': '2000-08-15', 'title': '出生前'}])
    same = life_path_review(LifePathRequest(birth=aware, events=[{'date': '2022-07-01', 'title': '毕业'}]))
    naive = life_path_review(LifePathRequest(birth=BIRTH, events=[{'date': '2022-07-01', 'title': '毕业'}]))
    assert same['events'] == naive['events']


def test_rest_and_mcp_parity():
    body = {'birth': BIRTH, 'events': [{'date': '2020-03-01', 'title': '换工作'}]}
    rest = CLIENT.post('/api/life-path', json=body).json()
    mcp = CLIENT.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                                    'params': {'name': 'life_path_review', 'arguments': body}}).json()
    assert mcp['result']['structuredContent'] == rest
    assert CLIENT.post('/api/date-scan', json={'start_date': '2026-01-01', 'days': 3}).status_code == 200
    assert CLIENT.post('/api/date-scan', json={'start_date': '2026-01-01', 'bogus': 1}).status_code == 422


def test_city_presets_use_valid_zones_and_coordinates():
    import re
    from pathlib import Path
    from zoneinfo import ZoneInfo
    source = (Path(__file__).resolve().parents[1] / 'static/cities.js').read_text(encoding='utf-8')
    cities = re.findall(r"\['([^']+)','([A-Za-z_/]+)',(-?[\d.]+),(-?[\d.]+)\]", source)
    assert len(cities) >= 60 and len({c[0] for c in cities}) == len(cities)
    for name, zone, lon, lat in cities:
        ZoneInfo(zone)
        assert -180 <= float(lon) <= 180 and -90 <= float(lat) <= 90, name
    assert ('北京', 'Asia/Shanghai', '116.4074', '39.9042') in cities


def test_installable_web_app_manifest():
    html = CLIENT.get('/').text
    assert 'rel="manifest" href="/static/manifest.json"' in html and 'id="birth_city"' in html
    manifest = CLIENT.get('/static/manifest.json').json()
    assert manifest['display'] == 'standalone' and manifest['start_url'] == '/'
    assert CLIENT.get(manifest['icons'][0]['src']).status_code == 200


def test_ziwei_pair_overlay_reads_charts_across_the_branch_grid():
    from app.engines import calculate_ziwei
    from app.features import PairInput
    from app.ziwei_pair import ziwei_pair_overlay
    partner = {'birth_datetime': '1999-03-02T10:00', 'timezone': 'Asia/Shanghai'}
    out = ziwei_pair_overlay(PairInput(person_a=BIRTH, person_b=partner))
    a, b = calculate_ziwei(BirthInput(**BIRTH)), calculate_ziwei(BirthInput(**partner))
    assert len(out['palace_grid']) == 12 and out['compatibility_score'] is None
    by_branch_b = {p['branch']: p['name'] for p in b['palaces']}
    assert all(row['person_b_palace'] == by_branch_b[row['branch']] for row in out['palace_grid'])
    # A (庚辰) 命宫午 sits in B's 子女宫; B (己卯) 化忌文曲 falls in A's 命宫.
    assert out['ming_shen_landings']['person_a_ming_in_b']['palace_in_other_chart'] == '子女宫'
    assert {'type': '化忌', 'star': '文曲', 'source_year_stem': '己', 'target_branch': '午', 'target_palace': '命宫'} \
        in out['transformations_b_into_a']
    assert len(out['focus_palaces']) == 12
    # Against one's own chart the overlay reproduces the chart's own birth-year transformations.
    self_pair = ziwei_pair_overlay(PairInput(person_a=BIRTH, person_b=BIRTH))
    assert [(t['type'], t['star'], t['target_palace']) for t in self_pair['transformations_a_into_b']] == \
        [(t['type'], t['star'], t['palace_name']) for t in a['birth_year_transformations']]


def test_ziwei_pair_rest_mcp_parity():
    body = {'person_a': BIRTH, 'person_b': {'birth_datetime': '1999-03-02T10:00', 'timezone': 'Asia/Shanghai'}}
    rest = CLIENT.post('/api/ziwei-pair', json=body).json()
    mcp = CLIENT.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                                    'params': {'name': 'ziwei_pair_overlay', 'arguments': body}}).json()
    assert mcp['result']['structuredContent'] == rest
