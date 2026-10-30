"""Traditional festivals, 三伏 and 数九 as calendar facts with their rules."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.astronomy import chinese_lunar_date
from app.festivals import day_marks, sanfu, starts_of_year
from app.main import app

client = TestClient(app)


def names(day):
    return [m['name'] for m in day_marks(day)]


@pytest.mark.parametrize('day,name', [
    (date(2025, 1, 28), '除夕'),  # 腊月 had 29 days that year: the eve is 廿九
    (date(2025, 1, 29), '春节'), (date(2025, 2, 12), '元宵节'), (date(2025, 5, 31), '端午节'),
    (date(2025, 8, 29), '七夕'), (date(2025, 10, 6), '中秋节'), (date(2025, 10, 29), '重阳节'),
    (date(2024, 2, 9), '除夕'), (date(2024, 6, 10), '端午节'),
    (date(2025, 1, 22), '北方小年'), (date(2025, 1, 23), '南方小年'),
])
def test_lunar_festivals_fall_on_their_lunar_days(day, name):
    assert name in names(day)


def test_a_leap_month_repeats_no_festival():
    leap = chinese_lunar_date(date(2023, 3, 23))
    assert leap['is_leap_month'] and (leap['month'], leap['day']) == (2, 2)
    assert '龙抬头' not in names(date(2023, 3, 23)) and '龙抬头' in names(date(2023, 2, 21))


@pytest.mark.parametrize('year,first,last,total', [
    (2021, date(2021, 7, 11), date(2021, 8, 10), 40),  # 夏至 was a 庚 day and counts as the first
    (2023, date(2023, 7, 11), date(2023, 8, 10), 40),
    (2024, date(2024, 7, 15), date(2024, 8, 14), 40),
    (2025, date(2025, 7, 20), date(2025, 8, 9), 30),
])
def test_sanfu_counts_geng_days_from_the_summer_solstice_and_start_of_autumn(year, first, last, total):
    fu = sanfu(year)
    assert fu['初伏'] == first and fu['末伏'] == last and (fu['出伏'] - fu['初伏']).days == total
    mid = day_marks(fu['中伏'])
    assert {'name': '中伏', 'day': 1, 'length': total - 20} == {k: mid[0][k] for k in ('name', 'day', 'length')}
    assert '出伏' in names(fu['出伏'])


def test_nines_count_from_the_winter_solstice_day():
    assert [(m['name'], m['day']) for m in day_marks(date(2024, 12, 21)) if m['kind'] == 'shujiu'] == [('一九', 1)]
    assert [(m['name'], m['day']) for m in day_marks(date(2025, 1, 9)) if m['kind'] == 'shujiu'] == [('三九', 2)]
    assert [(m['name'], m['day']) for m in day_marks(date(2025, 3, 11)) if m['kind'] == 'shujiu'] == [('九九', 9)]
    assert '出九' in names(date(2025, 3, 12)) and not [m for m in day_marks(date(2025, 3, 13)) if m['kind'] == 'shujiu']
    assert names(date(1901, 1, 1)) and names(date(2099, 12, 31))  # the edges of the range still count


def test_every_mark_names_its_rule_and_no_judgement():
    marks = [m for _, m in starts_of_year(2025)]
    assert len(marks) >= 25 and all(m['rule'] for m in marks)
    text = repr(marks)
    assert not any(word in text for word in ('吉', '凶', '宜', '忌'))


def test_calendar_almanac_and_ics_carry_the_marks():
    days = client.post('/api/calendar', json={'start_date': '2025-01-28', 'days': 2}).json()['days']
    assert [m['name'] for m in days[0]['festivals']] == ['除夕', '五九']
    assert days[1]['festivals'][0] == {'name': '春节', 'kind': 'festival', 'rule': '农历正月初一'}
    card = client.post('/api/daily-almanac', json={'moment': '2025-05-31T09:00', 'timezone': 'Asia/Shanghai'}).json()
    assert card['festivals'] == [{'name': '端午节', 'kind': 'festival', 'rule': '农历五月初五'}]
    plain = client.get('/api/solar-terms/2025.ics').text
    full = client.get('/api/solar-terms/2025.ics?festivals=true')
    assert 'VALUE=DATE' not in plain and full.headers['content-disposition'].endswith('solar-terms-festivals-2025.ics"')
    assert 'DTSTART;VALUE=DATE:20250531\r\nDTEND;VALUE=DATE:20250601\r\nSUMMARY:端午节' in full.text
    assert full.text.count('BEGIN:VEVENT') == plain.count('BEGIN:VEVENT') + len(starts_of_year(2025))
    assert 'traditional-festivals-sanfu-shujiu' in client.get('/api/capabilities').json()['features']
