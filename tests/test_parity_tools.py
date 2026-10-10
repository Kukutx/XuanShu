"""Date-range candidate scan (择日择时) and Life Path event review."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.date_selection import MAX_QIMEN_CHARTS, DateScanRequest, date_candidate_scan
from app.life_path import LifePathRequest, life_path_review
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


def test_scan_hour_charts_use_qimen_engine_and_are_capped():
    out = date_candidate_scan(DateScanRequest(start_date='2026-11-02', days=1, hours=['10:00']))
    chart = out['candidates'][0]['hour_charts'][0]
    assert (chart['dun'], chart['bureau'], chart['zhi_fu_star'], chart['zhi_shi_door']) == ('阴遁', 5, '天辅', '杜门')
    capped = date_candidate_scan(DateScanRequest(start_date='2026-01-01', days=60, hours=['09:00', '15:00'], max_results=60))
    assert sum(len(c['hour_charts']) for c in capped['candidates']) == MAX_QIMEN_CHARTS and capped['truncated']


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
