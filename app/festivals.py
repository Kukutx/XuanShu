"""Traditional festivals, the three fu periods (三伏) and the nine nines (数九) as calendar facts.

Every mark carries the rule that places it, so a reader can check it against an almanac. Nothing here says a day is
good or bad, and no festival custom is prescribed.
"""
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

from .astronomy import CHINA, ROLLOVER_DAY_AFTER_RANGE, TERMS, chinese_lunar_date, from_jd, solar_term_jd
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
# A term this close to midnight cannot be put on one side of it with confidence: the terms agree with sxtwl and
# PyEphem to a few seconds. The count that starts from it may then start a day earlier or later (1951's winter
# solstice falls 0.8 s after midnight; 2021's, 42 s before it, is clear of the margin).
NEAR_MIDNIGHT_SECONDS = 30
CAUTIONS = {
    '冬至': '冬至时刻距午夜不到半分钟，天文推算分不清是哪一天，数九的起算日可能相差一天',
    '夏至': '夏至时刻距午夜不到半分钟，天文推算分不清是哪一天，入伏的日子可能不同',
    '立秋': '立秋时刻距午夜不到半分钟，天文推算分不清是哪一天，末伏的日子可能不同',
}
_LONGITUDE = {name: longitude for name, longitude, _month, _day in TERMS}


def _stem(day: date) -> str:
    return STEMS[(54 + (day - date(2000, 1, 1)).days) % 60 % 10]  # 2000-01-01 was a 戊午 day


@lru_cache(maxsize=512)
def _term_moment(year: int, name: str):
    return from_jd(solar_term_jd(year, _LONGITUDE[name])).astimezone(CHINA)


def _term_day(year: int, name: str) -> date:
    """The China-time calendar day of a solar term."""
    return _term_moment(year, name).date()


def _caution(year: int, name: str) -> str | None:
    moment = _term_moment(year, name)
    seconds = moment.hour * 3600 + moment.minute * 60 + moment.second + moment.microsecond / 1e6
    return CAUTIONS[name] if min(seconds, 86400 - seconds) < NEAR_MIDNIGHT_SECONDS else None


def lunar_or_rollover(day: date) -> dict:
    """The lunar date, also for 2100-01-01 just past the range, so 2099-12-31 can still be told as New Year's Eve."""
    return chinese_lunar_date(day, allow_rollover_day=day == ROLLOVER_DAY_AFTER_RANGE)


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


def _shujiu_start(day: date) -> tuple[int, date]:
    """The year and day of the winter solstice that began the current or most recent counting of nines."""
    year = day.year if day >= _term_day(day.year, '冬至') else day.year - 1
    return year, _term_day(year, '冬至')


def day_marks(day: date, lunar: dict | None = None, next_lunar: dict | None = None) -> list[dict]:
    """The festivals, fu and nine marks of one China-time calendar day, each with its rule."""
    lunar = lunar or lunar_or_rollover(day)
    marks = []
    if not lunar['is_leap_month']:
        name = LUNAR_FESTIVALS.get((lunar['month'], lunar['day']))
        if name:
            marks.append({'name': name, 'kind': 'festival',
                          'rule': '农历' + MONTH_NAMES[lunar['month'] - 1] + DAY_NAMES[lunar['day'] - 1]})
    if next_lunar is None:
        try:
            next_lunar = lunar_or_rollover(day + timedelta(days=1))
        except ValueError:
            next_lunar = None
    if next_lunar and next_lunar['month'] == 1 and next_lunar['day'] == 1 and not next_lunar['is_leap_month']:
        marks.append({'name': '除夕', 'kind': 'festival', 'rule': EVE_RULE})
    fu = sanfu(day.year)
    if fu['初伏'] <= day <= fu['出伏']:
        if day == fu['出伏']:
            mark = {'name': '出伏', 'kind': 'sanfu', 'rule': SANFU_RULES['出伏']}
        else:
            period = '初伏' if day < fu['中伏'] else '中伏' if day < fu['末伏'] else '末伏'
            following = {'初伏': '中伏', '中伏': '末伏', '末伏': '出伏'}[period]
            mark = {'name': period, 'kind': 'sanfu', 'day': (day - fu[period]).days + 1,
                    'length': (fu[following] - fu[period]).days, 'rule': SANFU_RULES[period]}
        # 初伏 and 中伏 count from 夏至; 末伏 and 出伏 from 立秋.
        caution = _caution(day.year, '夏至' if mark['name'] in ('初伏', '中伏') else '立秋')
        if caution:
            mark['caution'] = caution
        marks.append(mark)
    year, start = _shujiu_start(day)
    n = (day - start).days
    if n <= 81:
        mark = ({'name': NINES[n // 9], 'kind': 'shujiu', 'day': n % 9 + 1, 'length': 9, 'rule': SHUJIU_RULE} if n < 81
                else {'name': '出九', 'kind': 'shujiu', 'rule': SHUJIU_END_RULE})
        caution = _caution(year, '冬至')
        if caution:
            mark['caution'] = caution
        marks.append(mark)
    return marks


@lru_cache(maxsize=8)
def starts_of_year(year: int) -> tuple[tuple[date, dict], ...]:
    """The days in a civil year where a festival falls or a fu period or nine begins, for a calendar file."""
    day, end = date(year, 1, 1), date(year, 12, 31)
    lunar = lunar_or_rollover(day)
    out = []
    while day <= end:
        following = lunar_or_rollover(day + timedelta(days=1))
        for mark in day_marks(day, lunar, following):
            if mark['kind'] == 'festival' or mark.get('day', 1) == 1:
                out.append((day, mark))
        day, lunar = day + timedelta(days=1), following
    return tuple(out)
