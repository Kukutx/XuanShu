"""Structural metamorphic tests across yin/yang, seasons and hour boundaries.

These test invariants of our *documented* school configuration. They do not
claim cross-school agreement or independently certify individual star rules.
"""
from __future__ import annotations

from datetime import datetime
import pytest

from app.engines import BirthInput
from app.qimen import QimenRequest, qimen_chart, BASE_DOORS, BASE_STARS, GODS, EARTH_STEMS


@pytest.mark.parametrize('day', [
    '2024-01-15', '2024-03-20', '2024-06-22', '2024-09-25',
    '2024-12-25', '2026-02-07', '2026-07-15', '2026-12-08',
    '2044-03-21', '2078-11-10',
])
@pytest.mark.parametrize('hour', [0,1,6,12,23])
def test_hour_qimen_nine_palace_bijections(day, hour):
    datetime.fromisoformat(day)
    inp = QimenRequest(moment=BirthInput(birth_datetime=f'{day}T{hour:02d}:30'))
    chart = qimen_chart(inp)
    places = chart['palaces']
    assert [p['number'] for p in places] == list(range(1, 10))
    assert set(p['earth_stem'] for p in places) == set(EARTH_STEMS)
    assert set(p['heaven_stem'] for p in places) == set(EARTH_STEMS)
    assert set(p['dark_stem'] for p in places) == set(EARTH_STEMS)
    assert sorted(p['star'] for p in places) == sorted(BASE_STARS.values())
    assert sorted(p['door'] for p in places if p['door']) == sorted(BASE_DOORS.values())
    assert sorted(p['deity'] for p in places if p['deity']) == sorted(GODS)
    center = places[4]
    assert center['star'] == '天禽'
    assert center['door'] is None and center['deity'] is None
    assert 1 <= chart['bureau'] <= 9
    assert chart['dun'] in ('阳遁','阴遁')
    assert chart['zhi_fu_palace'] in [1,2,3,4,6,7,8,9]
    assert chart['zhi_shi_palace'] in [1,2,3,4,6,7,8,9]
    assert datetime.fromisoformat(chart['solar_term_instant']) <= datetime.fromisoformat(chart['instant'])
