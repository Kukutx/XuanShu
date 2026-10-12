from datetime import date

from fastapi.testclient import TestClient

from app.chat import SPECIALISTS
from app.engines import BirthInput
from app.main import app
from app.mcp import process_rpc
from app.ziwei_horoscope import ZiweiHoroscopeRequest, ziwei_horoscope


def layers(birth: dict, target: str, time: str | None = None, **extra) -> dict:
    result = ziwei_horoscope(ZiweiHoroscopeRequest(birth=BirthInput(**birth), target_date=date.fromisoformat(target), target_time=time, **extra))
    return result


def summary(result: dict) -> dict:
    return {key: (layer['ming_branch'], layer['stem'] + layer['branch'], [t['star'] for t in layer['transformations']])
            for key, layer in result['layers'].items()}


def test_layers_match_iztro_reference():
    # Expected values from iztro-py 0.5.0 (by_solar('2000-8-16', 2, '女').horoscope('2026-10-11', 5)).
    result = layers({'birth_datetime': '2000-08-16T04:00', 'gender': 'female'}, '2026-10-11', '09:30')
    assert result['nominal_age'] == 27
    assert summary(result) == {
        'decade': ('辰', '庚辰', ['太阳', '武曲', '太阴', '天同']),
        'small_limit': ('申', '甲申', ['廉贞', '破军', '武曲', '太阳']),
        'year': ('午', '丙午', ['天同', '天机', '文昌', '廉贞']),
        'month': ('戌', '戊戌', ['贪狼', '太阴', '右弼', '天机']),
        'day': ('亥', '戊午', ['贪狼', '太阴', '右弼', '天机']),
        'hour': ('辰', '丁巳', ['太阴', '天同', '天机', '巨门']),
    }
    month = result['layers']['month']
    assert month['dou_jun_branch'] == '寅' and month['label'] == '2026年九月 · 戊戌月'
    # Each layer names the twelve palaces from its own Life palace.
    names = {p['branch']: p['name'] for p in month['palaces']}
    assert names['戌'] == '命宫' and names['酉'] == '兄弟宫' and names['亥'] == '父母宫'
    lu = month['transformations'][0]
    assert lu['type'] == '化禄' and lu['star'] == '贪狼' and lu['natal_palace'] and lu['layer_palace'] == names[lu['branch']]


def test_second_half_of_a_leap_month_counts_as_the_next_month():
    # iztro-py 0.5.0: by_solar('1988-3-5', 7, '男').horoscope('2025-8-10', 0).
    result = layers({'birth_datetime': '1988-03-05T14:00', 'gender': 'male'}, '2025-08-10', '00:15')
    assert summary(result)['month'] == ('午', '甲申', ['廉贞', '破军', '武曲', '太阳'])
    assert summary(result)['day'] == ('戌', '辛亥', ['巨门', '太阳', '文曲', '文昌'])
    assert summary(result)['hour'] == ('戌', '戊子', ['贪狼', '太阴', '右弼', '天机'])
    assert '闰六月（下半月，按七月）' in result['layers']['month']['label']
    # Stepping by month visits each half of the leap month once.
    nav = result['navigation']
    assert nav['month_segment'] == ['2025-08-09', '2025-08-22'] and nav['previous_month'] == '2025-08-08' and nav['next_month'] == '2025-08-23'
    first_half = layers({'birth_datetime': '1988-03-05T14:00', 'gender': 'male'}, '2025-08-08')
    assert '闰六月（上半月，按六月）' in first_half['layers']['month']['label']
    assert first_half['navigation']['month_segment'] == ['2025-07-25', '2025-08-08']


def test_layers_that_need_missing_facts_say_why():
    unknown_hour = layers({'birth_datetime': '2000-08-16T04:00', 'gender': 'female'}, '2026-10-11', hour_unknown=True)
    for key in ('decade', 'month', 'day', 'hour'):
        assert unknown_hour['layers'][key]['available'] is False and '时辰不详' in unknown_hour['layers'][key]['reason']
    # The small limit and year palaces follow the year branch; natal palaces and star positions follow the
    # placeholder hour and are left out, so another placeholder gives the same answer.
    other_placeholder = layers({'birth_datetime': '2000-08-16T15:00', 'gender': 'female'}, '2026-10-11', hour_unknown=True)
    assert unknown_hour['layers'] == other_placeholder['layers'] and unknown_hour['hour_unknown'] is True
    year = unknown_hour['layers']['year']
    assert year['available'] is True and year['ming_branch'] == '午' and year['ming_natal_palace'] is None
    assert [t['star'] for t in year['transformations']] == ['天同', '天机', '文昌', '廉贞']
    assert all(t['branch'] is None and t['natal_palace'] is None for t in year['transformations'])
    assert all(p['natal_palace'] is None for p in year['palaces']) and year['palaces'][6]['name'] == '命宫'
    assert unknown_hour['layers']['small_limit']['ming_branch'] == '申' and any('时辰不详' in x for x in unknown_hour['limitations'])
    no_gender = layers({'birth_datetime': '2000-08-16T04:00'}, '2026-10-11')
    assert no_gender['layers']['decade']['available'] is False and '性别' in no_gender['layers']['decade']['reason']
    assert no_gender['layers']['small_limit']['available'] is False
    assert no_gender['layers']['hour']['available'] is False and 'target_time' in no_gender['layers']['hour']['reason']
    child = layers({'birth_datetime': '2000-08-16T04:00', 'gender': 'female'}, '2001-01-01')
    assert child['layers']['decade']['available'] is False and '童限' in child['layers']['decade']['reason']


def test_target_day_boundary_follows_the_birth_rule():
    birth = {'birth_datetime': '2000-08-16T04:00', 'gender': 'female'}
    same_day = layers(birth, '2026-10-11', '23:30')
    next_day = layers(dict(birth, late_zi_day_rollover=True), '2026-10-11', '23:30')
    assert same_day['target']['calendar_day'] == '2026-10-11' and next_day['target']['calendar_day'] == '2026-10-12'
    assert next_day['target']['day']['text'] == '己未' and next_day['layers']['hour']['branch'] == '子'
    # The last supported evening still works: 2099-12-31 23:30 counts as 2100-01-01, inside lunar year 2099.
    last = layers(dict(birth, late_zi_day_rollover=True), '2099-12-31', '23:30')
    assert last['target']['calendar_day'] == '2100-01-01' and last['navigation']['next_day'] is None


def test_navigation_dates_are_target_dates_after_the_day_change():
    # 23:30 with the 23:00 day change reads the next day; stepping back must land in the previous month, not this one.
    birth = {'birth_datetime': '2000-08-16T04:00', 'gender': 'female', 'late_zi_day_rollover': True}
    here = layers(birth, '2026-10-11', '23:30')
    nav = here['navigation']
    before = layers(birth, nav['previous_month'], '23:30')
    after = layers(birth, nav['next_month'], '23:30')
    assert before['layers']['month']['label'] != here['layers']['month']['label'] != after['layers']['month']['label']
    assert before['navigation']['next_month'] == nav['month_segment'][0] and after['navigation']['previous_month'] == nav['month_segment'][1]
    # Every target_date inside month_segment reads the same month at this time.
    for value in nav['month_segment']:
        assert layers(birth, value, '23:30')['layers']['month']['label'] == here['layers']['month']['label']


def test_rest_mcp_and_chat_specialist():
    client = TestClient(app)
    body = {'birth': {'birth_datetime': '2000-08-16T04:00', 'gender': 'female'}, 'target_date': '2026-10-11'}
    reply = client.post('/api/ziwei-horoscope', json=body)
    assert reply.status_code == 200 and reply.json()['layers']['month']['ming_branch'] == '戌'
    assert client.post('/api/ziwei-horoscope', json=dict(body, target_date='1999-01-01')).status_code == 422
    assert client.post('/api/ziwei-horoscope', json=dict(body, target_time='9:30')).status_code == 422
    assert client.post('/api/ziwei-horoscope', json=dict(body, extra=1)).status_code == 422
    rpc = process_rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                       'params': {'name': 'ziwei_horoscope', 'arguments': body}})
    assert rpc['result']['structuredContent']['system'] == 'ziwei-horoscope'
    assert 'ziwei_horoscope' in SPECIALISTS['ziwei']['tools']
