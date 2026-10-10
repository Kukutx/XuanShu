from datetime import date, datetime, timedelta
import pytest

from app.astronomy import chinese_lunar_date, get_solar_terms
from app.engines import BirthInput, calculate_bazi, calculate_ziwei, combined_chart


def birth(d: str, **kw) -> BirthInput:
    return BirthInput(birth_datetime=d, **kw)


@pytest.mark.parametrize('day,expected', [
    (date(2024,2,10), (2024,1,1,False)),
    (date(2024,2,9), (2023,12,30,False)),
    (date(2020,5,23), (2020,4,1,True)),
    (date(2023,3,22), (2023,2,1,True)),
    (date(2000,8,16), (2000,7,17,False)),
    (date(2034,1,1), (2033,11,11,True)),
])
def test_known_chinese_lunar_dates(day, expected):
    val=chinese_lunar_date(day)
    assert (val['year'],val['month'],val['day'],val['is_leap_month']) == expected
    assert val['month_days'] in (29,30)


def test_official_iztro_reference_bazi_and_ziwei():
    # https://docs.iztro.com/quick-start
    inp=birth('2000-08-16T04:00', gender='female')
    b=calculate_bazi(inp)
    z=calculate_ziwei(inp)
    assert [x['text'] for x in b['pillars'].values()]==['庚辰','甲申','丙午','庚寅']
    assert z['lunar_date']['year']==2000
    assert (z['ming_palace'],z['shen_palace'],z['five_elements_bureau'])==('午','戌','木三局')
    assert z['star_positions']['武曲']=='寅'
    assert z['star_positions']['天相']=='寅'
    assert z['star_positions']['太阳']=='卯'
    assert z['star_positions']['天梁']=='卯'
    assert z['star_positions']['右弼']=='辰'
    assert z['star_positions']['七杀']=='辰'
    assert z['star_positions']['紫微']=='午'


def test_calendar_ganzhi_anchor():
    b=calculate_bazi(birth('2000-01-01T00:00'))
    assert [x['text'] for x in b['pillars'].values()]==['己卯','丙子','戊午','壬子']


def test_lichun_exact_hour_year_boundary():
    before=calculate_bazi(birth('2024-02-04T16:20'))
    after=calculate_bazi(birth('2024-02-04T16:40'))
    assert before['pillars']['year']['text']=='癸卯'
    assert after['pillars']['year']['text']=='甲辰'
    assert before['pillars']['month']['branch']=='丑'
    assert after['pillars']['month']['branch']=='寅'


def test_zi_hour_rollover_changes_day_and_hour_pillar():
    normal=calculate_bazi(birth('2024-02-10T23:30'))
    advance=calculate_bazi(birth('2024-02-10T23:30',late_zi_day_rollover=True))
    assert normal['pillars']['year']['text']==advance['pillars']['year']['text']
    assert normal['pillars']['day']['text']!=advance['pillars']['day']['text']
    assert normal['pillars']['hour']['text']!=advance['pillars']['hour']['text']
    assert normal['pillars']['hour']['branch']=='子'


def test_timezone_conversion_and_dst_invalid_hour():
    a=calculate_bazi(birth('2024-02-10T12:00',timezone='Asia/Shanghai'))
    b=calculate_bazi(birth('2024-02-10T04:00+00:00',timezone='Asia/Shanghai'))
    assert a['pillars']==b['pillars']
    with pytest.raises(ValueError,match='nonexistent'):
        calculate_bazi(birth('2024-03-31T02:30',timezone='Europe/Rome'))


def test_ziwei_structure_and_decade_properties():
    z=calculate_ziwei(birth('2024-02-10T12:00', gender='male'))
    assert len(z['palaces'])==12
    assert len(set(v['name'] for v in z['palaces']))==12
    assert sum(len(v['main_stars']) for v in z['palaces'])==14
    assert sum(len(v['auxiliary_stars']) for v in z['palaces'])==44
    assert z['star_counts']=={'main':14,'auxiliary':44,'original_selected':18,'additional_named':26}
    assert sorted(x['decade']['start_age'] for x in z['palaces'])==[z['bureau_number']+10*i for i in range(12)]
    assert sum(bool(x['is_ming']) for x in z['palaces']) == 1


def test_ziwei_leap_second_half_configuration_changes_month():
    a=calculate_ziwei(birth('2020-06-10T12:00',leap_month_second_half_as_next=False))
    b=calculate_ziwei(birth('2020-06-10T12:00',leap_month_second_half_as_next=True))
    assert a['lunar_date']['is_leap_month']
    assert a['lunar_date']['day']>15
    assert a['adjusted_lunar_month']==4
    assert b['adjusted_lunar_month']==5


def test_solar_terms_have_24_sorted_and_lichun():
    items=get_solar_terms(2024)
    assert len(items)==24
    assert [item['name'] for item in items][:4]==['小寒','大寒','立春','雨水']
    timestamps=[datetime.fromisoformat(item['time_china']) for item in items]
    assert timestamps==sorted(timestamps)
    assert timestamps[2].date()==date(2024,2,4)


def test_calendar_broad_period_no_crashes():
    for year in range(1902, 2100, 7):
        for month in (1,3,6,9,12):
            d=chinese_lunar_date(date(year,month,15))
            assert 1 <= d['month'] <= 12
            assert 1 <= d['day'] <= d['month_days']


def test_invalid_birth_data():
    with pytest.raises(Exception):
        BirthInput(birth_datetime='nope')
    with pytest.raises(Exception):
        BirthInput(birth_datetime='2024-02-10T12:00',timezone='Mars/Phobos')
    with pytest.raises(ValueError):
        calculate_bazi(birth('2100-02-10T12:00'))
