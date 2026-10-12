"""Zi Wei period layers for one date: decade, small limit, year, month, day and hour.

Each layer is a palace that serves as the period's Life palace, plus the four
transformations of the period's heavenly stem, placed on the natal stars. The
rules are the public traditional ones, as implemented by iztro:

- decade (大限): the natal palace whose age range holds the nominal age;
  transformations from that palace's stem.
- small limit (小限): the natal palace listing the nominal age; its stem.
- year (流年): the palace on the lunar year's branch; the year stem.
- month (流月): 斗君 -- from the year palace count back to the birth month,
  then forward to the birth hour; that palace is the first month and each
  month moves one palace forward. The month stem follows 五虎遁 from the lunar
  year stem.
- day (流日): from the month palace, the first day of the lunar month, one
  palace per day; the day pillar's stem.
- hour (流时): from the day palace, the Zi hour, one palace per double hour;
  the hour pillar's stem.

Each layer except the small limit also places its own ten period stars (流曜)
from the layer's stem and branch, with the natal tables: 魁钺 and 昌曲 by stem,
禄存 by stem with 擎羊 and 陀罗 beside it, 天马 by branch triad, 红鸾 and 天喜
by branch. Their names carry the layer: 运 (decade), 流 (year), 月, 日, 时. The year
layer adds 年解 and the year branch's 岁前 and 将前 twelve gods.

The lunar year is counted from the lunar new year. With the leap-month option
on, the second half of a leap month counts as the next month for the month
layer, as it does for the natal chart. Nothing is stored and nothing is
forecast: a layer only says which palace, transformations and stars apply.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from .almanac import LUNAR_DAYS, LUNAR_MONTHS
from .astronomy import chinese_lunar_date
from .engines import (BRANCHES, KUI_YUE_BY_STEM, LUCUN_BY_STEM, PALACE_NAMES, STEMS, TIANMA_BY_BRANCH, BirthInput, calculate_ziwei,
                      hour_branch_index, normalized_dt)
from .reference import FOUR_TRANSFORMATIONS, FOUR_TYPES
from .timebasis import time_basis
from .ziwei_extensions import year_branch_cycles

LAYER_KEYS = ('decade', 'small_limit', 'year', 'month', 'day', 'hour')
HOUR_LAYERS = ('month', 'day', 'hour')
# 文昌, 文曲 of a period by its stem (the natal pair goes by birth hour instead).
CHANG_QU_BY_STEM = ((5, 9), (6, 8), (8, 6), (9, 5), (8, 6), (9, 5), (11, 3), (0, 2), (2, 0), (3, 11))
# Period stars in the order 魁钺昌曲禄羊陀马鸾喜, named with each layer's prefix as iztro does.
FLOW_STAR_NAMES = {
    'decade': ('运魁', '运钺', '运昌', '运曲', '运禄', '运羊', '运陀', '运马', '运鸾', '运喜'),
    'year': ('流魁', '流钺', '流昌', '流曲', '流禄', '流羊', '流陀', '流马', '流鸾', '流喜'),
    'month': ('月魁', '月钺', '月昌', '月曲', '月禄', '月羊', '月陀', '月马', '月鸾', '月喜'),
    'day': ('日魁', '日钺', '日昌', '日曲', '日禄', '日羊', '日陀', '日马', '日鸾', '日喜'),
    'hour': ('时魁', '时钺', '时昌', '时曲', '时禄', '时羊', '时陀', '时马', '时鸾', '时喜'),
}


class ZiweiHoroscopeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    target_date: date | None = Field(default=None, description='Gregorian date to read the periods for (YYYY-MM-DD, 1901-02-19 to 2099-12-31); default today in the birth time zone')
    target_time: str | None = Field(default=None, pattern=r'^([01]\d|2[0-3]):[0-5]\d$',
                                    description='Optional clock time HH:MM for the hour layer; with the 23:00 day change, 23:00-23:59 counts as the next day')
    hour_unknown: bool = Field(default=False, description='Birth hour unknown: the decade, month, day and hour layers depend on it and are '
                               'left out; the small limit and year keep their palace branch, stem and transformed stars but not natal positions')


def _ganzhi(stem: int, branch: int) -> dict:
    return {'stem': STEMS[stem % 10], 'branch': BRANCHES[branch % 12], 'text': STEMS[stem % 10] + BRANCHES[branch % 12]}


def flow_star_positions(stem: int, branch: int, scope: str) -> list[tuple[str, int]]:
    """Period stars of one layer as (name, branch index) pairs, in the order of FLOW_STAR_NAMES; the year adds Nian Jie."""
    lu = LUCUN_BY_STEM[stem]
    luan = (3 - branch) % 12
    places = (*KUI_YUE_BY_STEM[stem], *CHANG_QU_BY_STEM[stem], lu, (lu + 1) % 12, (lu - 1) % 12,
              TIANMA_BY_BRANCH[branch], luan, (luan + 6) % 12)
    stars = list(zip(FLOW_STAR_NAMES[scope], places))
    if scope == 'year':
        stars.append(('年解', (10 - branch) % 12))  # 子年在戌，逆行
    return stars


def _layer(name: str, label: str, ming: int, stem: str, branch: str, chart: dict, scope: str | None = None, **extra) -> dict:
    """One period: its Life palace, the names it gives the twelve palaces, its stem's transformations and its stars."""
    natal = {p['branch']: p['name'] for p in chart['palaces']}
    transformations = []
    for kind, star in zip(FOUR_TYPES, FOUR_TRANSFORMATIONS[stem]):
        where = chart['star_positions'].get(star)
        index = BRANCHES.index(where) if where else None
        transformations.append({'type': kind, 'star': star, 'branch': where,
                                'natal_palace': natal.get(where), 'layer_palace': None if index is None else PALACE_NAMES[(ming - index) % 12]})
    stars = [] if scope is None else [
        {'name': star, 'branch': BRANCHES[at], 'natal_palace': natal[BRANCHES[at]], 'layer_palace': PALACE_NAMES[(ming - at) % 12]}
        for star, at in flow_star_positions(STEMS.index(stem), BRANCHES.index(branch), scope)]
    palaces = [{'branch': BRANCHES[i], 'natal_palace': natal[BRANCHES[i]], 'name': PALACE_NAMES[(ming - i) % 12]} for i in range(12)]
    if scope == 'year':
        cycles = year_branch_cycles(BRANCHES.index(branch))
        for i, palace in enumerate(palaces):
            palace.update(suiqian=cycles['suiqian'][i], jiangqian=cycles['jiangqian'][i])
    return {'name': name, 'available': True, 'label': label, 'ming_branch': BRANCHES[ming], 'ming_natal_palace': natal[BRANCHES[ming]],
            'stem': stem, 'branch': branch, 'palaces': palaces, 'transformations': transformations, 'stars': stars, **extra}


def _unavailable(name: str, reason: str) -> dict:
    return {'name': name, 'available': False, 'reason': reason}


def _without_natal_positions(layer: dict) -> dict:
    """Drop what depends on the natal chart's placeholder hour: natal palace names and where the stars sit."""
    layer['ming_natal_palace'] = None
    for palace in layer['palaces']:
        palace['natal_palace'] = None
    for item in layer['transformations']:
        item.update(branch=None, natal_palace=None, layer_palace=None)
    for star in layer['stars']:  # period stars sit by the layer's own stem and branch; only the natal name goes
        star['natal_palace'] = None
    return layer


def _in_range(day: date) -> str | None:
    try:
        chinese_lunar_date(day)
    except ValueError:
        return None
    return day.isoformat()


def ziwei_horoscope(req: ZiweiHoroscopeRequest) -> dict:
    birth = req.birth
    chart = calculate_ziwei(birth)
    dt = normalized_dt(birth)
    effective, _ = time_basis(dt, birth.time_mode, birth.longitude)
    birth_hour = hour_branch_index(effective.hour)
    target = req.target_date or datetime.now(ZoneInfo(birth.timezone)).date()
    if target < dt.date():
        raise ValueError('target_date is before the birth date')
    hour = int(req.target_time[:2]) if req.target_time else None
    # The day boundary follows the birth record's own rule, as the natal chart does.
    day = target + timedelta(days=1) if hour == 23 and birth.late_zi_day_rollover else target
    lunar = chinese_lunar_date(day, allow_rollover_day=day != target)

    birth_lunar = chart['lunar_date']
    age = lunar['year'] - birth_lunar['year'] + 1
    year_idx = (lunar['year'] - 1984) % 60
    year_stem, year_branch = year_idx % 10, year_idx % 12
    leap_next = lunar['is_leap_month'] and birth.leap_month_second_half_as_next and lunar['day'] > 15
    month_number = lunar['month'] + (1 if leap_next else 0)  # 13 for the second half of a leap twelfth month
    month_stem, month_branch = (2 * (year_stem % 5) + 2 + month_number - 1) % 10, (2 + month_number - 1) % 12
    day_idx = (54 + (day - date(2000, 1, 1)).days) % 60  # 2000-01-01 is 戊午
    hour_branch = hour_branch_index(hour) if hour is not None else None
    hour_stem = (2 * (day_idx % 5) + hour_branch) % 10 if hour is not None else None

    layers: dict[str, dict] = {}
    decades = [p for p in chart['palaces'] if p['decade']]
    holder = next((p for p in decades if p['decade']['start_age'] <= age <= p['decade']['end_age']), None)
    if req.hour_unknown:
        layers['decade'] = _unavailable('大限', '大限的起运岁数和所在宫位取决于五行局与命宫，时辰不详时无法确定。')
    elif not decades:
        layers['decade'] = _unavailable('大限', '大限顺行或逆行取决于性别；出生资料未选性别。')
    elif holder is None:
        first = min(p['decade']['start_age'] for p in decades)
        layers['decade'] = _unavailable('大限', f'虚岁 {age} 还没到第一个大限（{first} 岁起），童限未列出。' if age < first
                                        else f'虚岁 {age} 超出十二个大限。')
    else:
        layers['decade'] = _layer('大限', f"大限 {holder['decade']['start_age']}–{holder['decade']['end_age']} 岁 · {holder['stem']}{holder['branch']}",
                                  BRANCHES.index(holder['branch']), holder['stem'], holder['branch'], chart, 'decade',
                                  start_age=holder['decade']['start_age'], end_age=holder['decade']['end_age'])
    small = next((p for p in chart['palaces'] if age in (p['small_limit_nominal_ages'] or [])), None)
    layers['small_limit'] = (_layer('小限', f"小限 · {small['stem']}{small['branch']}", BRANCHES.index(small['branch']),
                                    small['stem'], small['branch'], chart) if small
                             else _unavailable('小限', '小限顺行或逆行取决于性别；出生资料未选性别。' if birth.gender == 'unspecified'
                                               else f'虚岁 {age} 不在小限表内。'))
    layers['year'] = _layer('流年', f"{lunar['year']} {STEMS[year_stem]}{BRANCHES[year_branch]}年 · 虚岁 {age}", year_branch,
                            STEMS[year_stem], BRANCHES[year_branch], chart, 'year')
    if req.hour_unknown:
        # The small limit and year palaces follow the year branch alone; the natal palaces and star positions follow the hour.
        for key in ('small_limit', 'year'):
            if layers[key]['available']:
                _without_natal_positions(layers[key])
        for key, name in zip(HOUR_LAYERS, ('流月', '流日', '流时')):
            layers[key] = _unavailable(name, '流月、流日、流时按出生时辰定斗君；时辰不详时无法确定。')
    else:
        dou_jun = (year_branch - (chart['adjusted_lunar_month'] - 1) + birth_hour) % 12
        month_palace = (dou_jun + month_number - 1) % 12
        month_name = ('闰' if lunar['is_leap_month'] else '') + LUNAR_MONTHS[lunar['month'] - 1]
        half = ''
        if lunar['is_leap_month'] and birth.leap_month_second_half_as_next:
            half = ('（下半月，按' if leap_next else '（上半月，按') + LUNAR_MONTHS[(month_number - 1) % 12] + '）'
        layers['month'] = _layer('流月', f"{lunar['year']}年{month_name}{half} · {STEMS[month_stem]}{BRANCHES[month_branch]}月",
                                 month_palace, STEMS[month_stem], BRANCHES[month_branch], chart, 'month', dou_jun_branch=BRANCHES[dou_jun])
        day_palace = (month_palace + lunar['day'] - 1) % 12
        layers['day'] = _layer('流日', f"{day.isoformat()} · {month_name}{LUNAR_DAYS[lunar['day'] - 1]} · {STEMS[day_idx % 10]}{BRANCHES[day_idx % 12]}日",
                               day_palace, STEMS[day_idx % 10], BRANCHES[day_idx % 12], chart, 'day')
        if hour is None:
            layers['hour'] = _unavailable('流时', '没有填写时刻（target_time），不列流时。')
        else:
            layers['hour'] = _layer('流时', f"{req.target_time} · {STEMS[hour_stem]}{BRANCHES[hour_branch]}时",
                                    (day_palace + hour_branch) % 12, STEMS[hour_stem], BRANCHES[hour_branch], chart, 'hour')

    start = day - timedelta(days=lunar['day'] - 1)
    end = start + timedelta(days=lunar['month_days'] - 1)
    segment = (start, end)
    if lunar['is_leap_month'] and birth.leap_month_second_half_as_next:
        segment = (start + timedelta(days=15), end) if leap_next else (start, start + timedelta(days=14))
    # Navigation is given as target_date values for the same target_time, so undo the 23:00 day change.
    shift = day - target
    segment = (segment[0] - shift, segment[1] - shift)
    return {
        'system': 'ziwei-horoscope',
        'birth_datetime': chart['birth_datetime'], 'timezone': birth.timezone,
        'target': {'date': target.isoformat(), 'time': req.target_time, 'calendar_day': day.isoformat(), 'lunar_date': lunar,
                   'year': _ganzhi(year_stem, year_branch), 'month': _ganzhi(month_stem, month_branch),
                   'day': _ganzhi(day_idx, day_idx), 'hour': _ganzhi(hour_stem, hour_branch) if hour is not None else None},
        'nominal_age': age,
        'hour_unknown': req.hour_unknown,
        'layers': {key: layers[key] for key in LAYER_KEYS},
        'navigation': {'month_segment': [segment[0].isoformat(), segment[1].isoformat()],
                       'previous_month': _in_range(segment[0] - timedelta(days=1)), 'next_month': _in_range(segment[1] + timedelta(days=1)),
                       'previous_day': _in_range(target - timedelta(days=1)), 'next_day': _in_range(target + timedelta(days=1))},
        'rules': {
            'year_boundary': '农历正月初一',
            'day_boundary': '23:00' if birth.late_zi_day_rollover else '00:00',
            'leap_month_second_half_as_next': birth.leap_month_second_half_as_next,
            'decade': '本命宫位的大限年龄区间；四化取该宫宫干',
            'small_limit': '本命宫位所列小限虚岁；四化取该宫宫干',
            'year': '流年地支所在宫为流年命宫；四化取年干',
            'month': '斗君：从流年命宫逆数到生月，再顺数到生时为正月，每月顺行一宫；四化取月干（五虎遁）',
            'day': '从流月命宫起初一，每日顺行一宫；四化取日干',
            'hour': '从流日命宫起子时，每个时辰顺行一宫；四化取时干',
            'flow_stars': '大限、流年、流月、流日、流时各按本层干支安魁钺昌曲禄羊陀马鸾喜，字头分别为运、流、月、日、时；流年另安年解与岁前、将前十二神；小限不安流曜',
            'nominal_age': '传统虚岁：目标农历年减出生农历年再加一',
            'transformation_school': chart['transformation_school'],
        },
        'limitations': [
            '只标出各层的命宫、四化落在哪颗本命星上和本层流曜，不预测具体事件。',
            '流曜只有魁钺昌曲禄羊陀马鸾喜十颗（流年另有年解），与 iztro 一致；流火、流铃等其他流派的流曜不安。',
            '流月的起法各派不同；这里用斗君，与 iztro 一致。',
            '流时按所填钟表时间取时辰，不做太阳时换算。',
            '前后翻页的日期是 target_date，配合同一个 target_time 使用；选了 23:00 换日时已扣回提前的一天。',
        ] + (['时辰不详：本命宫位和星曜位置随时辰变化，小限、流年只列命宫地支、天干、四化星名和本层流曜，不列它们落在哪个本命宫。'] if req.hour_unknown else []),
    }
