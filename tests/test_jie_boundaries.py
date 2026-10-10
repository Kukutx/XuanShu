"""Precision regression for the astronomical Jie boundary and Dayun starting instant.

Events come from the same deterministic Swiss Ephemeris solver; these checks
assert consistency and exact boundary membership, not independent ephemeris
certification or universal agreement between traditional schools.
"""
from datetime import timedelta, timezone

import pytest

from app.astronomy import TERMS, from_jd, jie_neighbors, solar_month_offset, solar_term_jd
from app.advanced import DayunRequest, dayun_sequence
from app.engines import BRANCHES, BirthInput, calculate_bazi


@pytest.mark.parametrize('year', [2000, 2024, 2033])
@pytest.mark.parametrize('name,longitude', [(name, lon) for name, lon, _, _ in TERMS if lon % 30 == 15])
def test_all_12_jie_bazi_month_switch_exact_instant(year, name, longitude):
    event = from_jd(solar_term_jd(year, longitude))
    offset_before = solar_month_offset(event - timedelta(microseconds=1))
    offset_at = solar_month_offset(event)
    offset_after = solar_month_offset(event + timedelta(microseconds=1))
    assert offset_at == offset_after == ((longitude - 315) % 360) // 30, (year, name)
    assert offset_before == (offset_at - 1) % 12, (year, name)
    for delta, expected_offset in [(timedelta(seconds=-1), offset_before), (timedelta(), offset_at), (timedelta(seconds=1), offset_at)]:
        instant = (event + delta).astimezone(timezone(timedelta(hours=8)))
        chart = calculate_bazi(BirthInput(birth_datetime=instant.isoformat(), gender='male'))
        assert chart['pillars']['month']['branch'] == BRANCHES[(2 + expected_offset) % 12], (year, name, delta)
        if delta >= timedelta():
            assert chart['jie_boundaries']['previous']['name'] == name
        else:
            assert chart['jie_boundaries']['previous']['name'] != name


def test_exact_lichun_membership_and_zero_dayun_age():
    instant = from_jd(solar_term_jd(2000, 315))
    b = BirthInput(birth_datetime=instant.astimezone(timezone(timedelta(hours=8))).isoformat(), gender='male')
    result = dayun_sequence(DayunRequest(birth=b, periods=1))
    assert result['natal_year_pillar'] == '庚辰'
    assert result['natal_month_pillar'] == '戊寅'
    assert result['direction'] == 'forward'
    assert result['nearest_jie_used']['name'] == '立春'
    assert result['birth_to_jie_days'] == 0
    assert result['start_age_years_nominal'] == 0
    assert result['start_age_traditional_parts'] == {'years': 0, 'months': 0, 'days_nominal_30_day_month': 0.0}
    assert result['periods'][0]['pillar'] == '己卯'


def test_exact_lichun_neighbor_selection_and_gender_rule_change():
    instant = from_jd(solar_term_jd(2000, 315))
    before = (instant - timedelta(microseconds=10)).isoformat()
    at = instant.isoformat()
    p = jie_neighbors(instant)
    assert p[0][0] == '立春' and p[0][1] == instant
    assert p[1][0] == '惊蛰'
    before_chart = calculate_bazi(BirthInput(birth_datetime=before, gender='male'))
    at_chart = calculate_bazi(BirthInput(birth_datetime=at, gender='male'))
    assert before_chart['pillars']['year']['text'] == '己卯'
    assert before_chart['pillars']['month']['text'] == '丁丑'
    assert at_chart['pillars']['year']['text'] == '庚辰'
    assert at_chart['pillars']['month']['text'] == '戊寅'


def test_naive_jie_query_is_rejected():
    instant = from_jd(solar_term_jd(2000, 315)).replace(tzinfo=None)
    with pytest.raises(ValueError, match='aware datetime'):
        solar_month_offset(instant)
