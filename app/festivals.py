"""Traditional festivals, the three fu periods (三伏) and the nine nines (数九) as calendar facts.

Every mark carries the rule that places it, so a reader can check it against an almanac. Nothing here says a day is
good or bad, and no festival custom is prescribed.
"""
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

from .astronomy import CHINA, TERMS, chinese_lunar_date, from_jd, solar_term_jd
from .engines import STEMS

# Lunar month and day of each festival. A leap month repeats the month's number but not its festivals: 闰五月初五 is
# not 端午. 小年 differs by region, so both customary days are named.
LUNAR_FESTIVALS = {
    (1, 1): '春节', (1, 15): '元宵节', (2, 2): '龙抬头', (3, 3): '上巳节', (5, 5): '端午节',
    (7, 7): '七夕', (7, 15): '中元节', (8, 15): '中秋节', (9, 9): '重阳节', (10, 1): '寒衣节',
    (10, 15): '下元节', (12, 8): '腊八节', (12, 23): '北方小年', (12, 24): '南方小年',
}
MONTH_NAMES = ('正月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '冬月', '腊月')
DAY_NAMES = ('初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
             '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
             '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十')
NINES = ('一九', '二九', '三九', '四九', '五九', '六九', '七九', '八九', '九九')
SANFU_RULES = {
    '初伏': '夏至当天起数第三个庚日（夏至逢庚当天算第一个），初伏十天',
    '中伏': '第四个庚日起，到立秋当天起第一个庚日之前，十天或二十天',
    '末伏': '立秋当天起第一个庚日（立秋逢庚当天算），末伏十天',
    '出伏': '末伏十天之后的第一天',
}
SHUJIU_RULE = '冬至当天起每九天为一九，九个九共八十一天'
SHUJIU_END_RULE = '九九八十一天之后的第一天'
EVE_RULE = '农历腊月的最后一天（春节前一天）'
_LONGITUDE = {name: longitude for name, longitude, _month, _day in TERMS}


def _stem(day: date) -> str:
    return STEMS[(54 + (day - date(2000, 1, 1)).days) % 60 % 10]  # 2000-01-01 was a 戊午 day


@lru_cache(maxsize=512)
def _term_day(year: int, name: str) -> date:
    """The China-time calendar day of a solar term."""
    return from_jd(solar_term_jd(year, _LONGITUDE[name])).astimezone(CHINA).date()


def _geng_from(day: date, n: int) -> date:
    """The n-th geng-stem day counting from ``day`` itself."""
    while _stem(day) != '庚':
        day += timedelta(days=1)
    return day + timedelta(days=10 * (n - 1))


@lru_cache(maxsize=256)
def sanfu(year: int) -> dict[str, date]:
    """The first days of the first, middle and last fu periods, and the day after the last fu day."""
    first = _geng_from(_term_day(year, '夏至'), 3)
    last = _geng_from(_term_day(year, '立秋'), 1)
    return {'初伏': first, '中伏': first + timedelta(days=10), '末伏': last, '出伏': last + timedelta(days=10)}


def _shujiu_offset(day: date) -> int:
    """Days since the winter solstice that began the current or most recent counting of nines."""
    start = _term_day(day.year, '冬至')
    if day < start:
        start = _term_day(day.year - 1, '冬至')
    return (day - start).days


def day_marks(day: date, lunar: dict | None = None, next_lunar: dict | None = None) -> list[dict]:
    """The festivals, fu and nine marks of one China-time calendar day, each with its rule."""
    lunar = lunar or chinese_lunar_date(day)
    marks = []
    if not lunar['is_leap_month']:
        name = LUNAR_FESTIVALS.get((lunar['month'], lunar['day']))
        if name:
            marks.append({'name': name, 'kind': 'festival',
                          'rule': '农历' + MONTH_NAMES[lunar['month'] - 1] + DAY_NAMES[lunar['day'] - 1]})
    if next_lunar is None:
        try:
            next_lunar = chinese_lunar_date(day + timedelta(days=1), allow_rollover_day=True)
        except ValueError:
            next_lunar = None
    if next_lunar and next_lunar['month'] == 1 and next_lunar['day'] == 1 and not next_lunar['is_leap_month']:
        marks.append({'name': '除夕', 'kind': 'festival', 'rule': EVE_RULE})
    fu = sanfu(day.year)
    if fu['初伏'] <= day < fu['出伏']:
        period = '初伏' if day < fu['中伏'] else '中伏' if day < fu['末伏'] else '末伏'
        following = {'初伏': '中伏', '中伏': '末伏', '末伏': '出伏'}[period]
        marks.append({'name': period, 'kind': 'sanfu', 'day': (day - fu[period]).days + 1,
                      'length': (fu[following] - fu[period]).days, 'rule': SANFU_RULES[period]})
    elif day == fu['出伏']:
        marks.append({'name': '出伏', 'kind': 'sanfu', 'rule': SANFU_RULES['出伏']})
    n = _shujiu_offset(day)
    if n < 81:
        marks.append({'name': NINES[n // 9], 'kind': 'shujiu', 'day': n % 9 + 1, 'length': 9, 'rule': SHUJIU_RULE})
    elif n == 81:
        marks.append({'name': '出九', 'kind': 'shujiu', 'rule': SHUJIU_END_RULE})
    return marks


def starts_of_year(year: int) -> list[tuple[date, dict]]:
    """The days in a civil year where a festival falls or a fu period or nine begins, for a calendar file."""
    day, end = date(year, 1, 1), date(year, 12, 31)
    lunar = chinese_lunar_date(day)
    out = []
    while day <= end:
        try:
            following = chinese_lunar_date(day + timedelta(days=1), allow_rollover_day=True)
        except ValueError:
            following = None
        for mark in day_marks(day, lunar, following):
            if mark['kind'] == 'festival' or mark.get('day', 1) == 1:
                out.append((day, mark))
        day, lunar = day + timedelta(days=1), following
    return out
