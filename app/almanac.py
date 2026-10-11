"""Today's calendar card: pillars, lunar date, solar term, day officer and moon phase.

Every field is a calendar fact computed by the same engines as the charts. An
optional birth adds the traditional ten-god names and branch relations of the
current pillars against the natal chart, plus the decade period in force. There
is no luck score, no do-and-avoid list and no forecast.
"""
from __future__ import annotations

import math
from datetime import datetime, time, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .advanced import DayunRequest, dayun_sequence
from .astronomy import TERMS, chinese_lunar_date, from_jd, moon_data, signed_degrees, solar_term_jd, sun_data, to_jd
from .engines import ANIMALS, BRANCHES, STEMS, STEM_ELEMENT, BirthInput, _ten_god, calculate_bazi, normalized_dt, pillar_indices
from .life_path import _relations
from .workflows import DAY_OFFICERS

LUNAR_MONTHS = ('正月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '冬月', '腊月')
LUNAR_DAYS = ('初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
              '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
              '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十')
WEEKDAYS = tuple('一二三四五六日')
# Elongation of the Moon from the Sun; the four principal phases get a window of
# about half a day either side, the rest of the cycle the intermediate names.
PHASES = ((7, '新月'), (83, '蛾眉月'), (97, '上弦月'), (173, '盈凸月'), (187, '满月'),
          (263, '亏凸月'), (277, '下弦月'), (353, '残月'), (360, '新月'))
PILLAR_KEYS = ('year', 'month', 'day', 'hour')


class DailyAlmanacRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    moment: str | None = Field(default=None, description='ISO time such as 2026-10-11T09:30 read in timezone, or with an offset (2026-10-11T09:30+08:00) to pick one reading of a repeated daylight-saving hour; omit for the current time')
    timezone: str = Field(default='Asia/Shanghai', description='IANA timezone of the moment')
    birth: BirthInput | None = Field(default=None, description='Optional natal data for ten gods and branch relations; not stored')

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f'Unknown IANA timezone: {value}') from exc
        return value

    @field_validator('moment')
    @classmethod
    def valid_moment(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError('moment must be an ISO time such as 2026-10-11T09:30') from exc
        return value

    @model_validator(mode='after')
    def real_moment_and_birth_before_it(self):
        if self.moment is not None:
            raw, zone = datetime.fromisoformat(self.moment), ZoneInfo(self.timezone)
            if raw.tzinfo is None:
                # Same checks as birth times: a skipped or repeated daylight-saving reading has no single instant.
                local = raw.replace(tzinfo=zone)
                if local.astimezone(dt_timezone.utc).astimezone(zone).replace(tzinfo=None) != raw:
                    raise ValueError('moment falls in a skipped daylight-saving hour; give a time that exists in timezone')
                if local.replace(fold=0).utcoffset() != local.replace(fold=1).utcoffset():
                    raise ValueError('moment is a repeated daylight-saving hour; add its UTC offset, e.g. 2026-10-25T02:30+02:00')
            if not 1901 <= self.instant().year <= 2099:
                raise ValueError('moment must fall between 1901 and 2099')
        if self.birth is not None and normalized_dt(self.birth) > self.instant():
            raise ValueError('birth must not be after the moment')
        return self

    def instant(self) -> datetime:
        zone = ZoneInfo(self.timezone)
        if self.moment is None:
            return datetime.now(zone).replace(second=0, microsecond=0)
        raw = datetime.fromisoformat(self.moment)
        return raw.astimezone(zone) if raw.tzinfo is not None else raw.replace(tzinfo=zone)


def lunar_label(lunar: dict) -> str:
    return ('闰' if lunar['is_leap_month'] else '') + LUNAR_MONTHS[lunar['month'] - 1] + LUNAR_DAYS[lunar['day'] - 1]


def _terms_around(instant: datetime) -> tuple[tuple[str, datetime], tuple[str, datetime]]:
    events = sorted((from_jd(solar_term_jd(year, lon)), name)
                    for year in (instant.year - 1, instant.year, instant.year + 1) for name, lon, _, __ in TERMS)
    index = max(i for i, (when, _) in enumerate(events) if when <= instant)
    return (events[index][1], events[index][0]), (events[index + 1][1], events[index + 1][0])


def _day_officer(instant: datetime) -> dict:
    """Day officer (jianchu) for the local date in the card's zone: the jie month at local noon against the day branch."""
    zone, day = instant.tzinfo, instant.date()
    noon = pillar_indices(datetime.combine(day, time(12), tzinfo=zone))[0]
    start = datetime.combine(day, time(), tzinfo=zone)
    end = datetime.combine(day + timedelta(days=1), time(), tzinfo=zone) - timedelta(microseconds=1)
    return {'officer': DAY_OFFICERS[(noon[2] - noon[1]) % 12],
            # A jie instant inside this local day changes the month branch before and after it.
            'jie_boundary_on_date': pillar_indices(start)[0][1] != pillar_indices(end)[0][1]}


def _elongation(jd: float) -> tuple[float, float]:
    sun, sun_speed = sun_data(jd)
    moon, moon_speed = moon_data(jd)
    return (moon - sun) % 360, moon_speed - sun_speed


def _next_phase(jd: float, target: float) -> float:
    """First instant after ``jd`` at which the elongation equals ``target`` degrees."""
    angle, speed = _elongation(jd)
    guess = jd + ((target - angle) % 360 or 360) / speed
    for _ in range(12):
        angle, speed = _elongation(guess)
        step = signed_degrees(angle - target) / speed
        guess -= step
        if abs(step) < 1e-7:
            break
    return guess


PHASE_EVENTS = ((0, '新月'), (90, '上弦月'), (180, '满月'), (270, '下弦月'))


def moon_phases(year: int) -> list[dict]:
    """Instants of the four principal moon phases within a calendar year in China time."""
    if not 1901 <= year <= 2099:
        raise ValueError('Supported years: 1901–2099')
    china = ZoneInfo('Asia/Shanghai')
    start, end = to_jd(datetime(year, 1, 1, tzinfo=china)), to_jd(datetime(year + 1, 1, 1, tzinfo=china))
    events = []
    for target, name in PHASE_EVENTS:
        jd = start
        while (hit := _next_phase(jd, target)) < end:
            events.append({'name': name, 'elongation': target, 'instant': from_jd(hit)})
            jd = hit + 1
    return sorted(events, key=lambda e: e['instant'])


def _moon(instant: datetime) -> dict:
    jd = to_jd(instant)
    angle, _ = _elongation(jd)
    zone = instant.tzinfo
    return {
        'phase': next(name for limit, name in PHASES if angle < limit),
        'elongation_degrees': round(angle, 2),
        'illuminated_fraction': round((1 - math.cos(math.radians(angle))) / 2, 3),
        'waxing': angle < 180,
        'next_full_moon': from_jd(_next_phase(jd, 180)).astimezone(zone).isoformat(timespec='minutes'),
        'next_new_moon': from_jd(_next_phase(jd, 0)).astimezone(zone).isoformat(timespec='minutes'),
    }


def _personal(birth: BirthInput, instant: datetime, today: dict[str, str]) -> dict:
    natal = calculate_bazi(birth)
    day_master = STEMS.index(natal['pillars']['day']['stem'])
    natal_branches = {key: natal['pillars'][key]['branch'] for key in PILLAR_KEYS}
    rows = []
    for key in PILLAR_KEYS:
        pillar = today[key]
        rows.append({
            'pillar_of': key,
            'pillar': pillar,
            'stem_ten_god': _ten_god(day_master, STEMS.index(pillar[0])),
            'branch_relations': _relations(pillar[1], natal_branches),
        })
    born = normalized_dt(birth)
    result = {
        'day_master': STEMS[day_master] + STEM_ELEMENT[day_master],
        'natal_pillars': {key: natal['pillars'][key]['text'] for key in PILLAR_KEYS},
        'today_against_natal': rows,
        'nominal_age': chinese_lunar_date(instant.date())['year'] - chinese_lunar_date(born.date())['year'] + 1,
        'decade_period': None,
    }
    if birth.gender != 'unspecified':
        periods = dayun_sequence(DayunRequest(birth=birth, periods=12))['periods']
        start = datetime.fromisoformat(periods[0]['approx_start_local'])
        current = next((p for p in periods if datetime.fromisoformat(p['approx_start_local']) <= instant
                        < datetime.fromisoformat(p['approx_end_local_exclusive'])), None)
        if current:
            result['decade_period'] = {
                'pillar': current['pillar'],
                'stem_ten_god': _ten_god(day_master, STEMS.index(current['pillar'][0])),
                'approx_start_local': current['approx_start_local'],
                'approx_end_local_exclusive': current['approx_end_local_exclusive'],
            }
        elif instant < start:
            result['decade_period'] = {'pillar': None, 'note': '尚未起运', 'approx_start_local': periods[0]['approx_start_local']}
    return result


def daily_almanac(req: DailyAlmanacRequest) -> dict:
    instant = req.instant()
    indices, _, _ = pillar_indices(instant)
    pillars = {key: STEMS[i % 10] + BRANCHES[i % 12] for key, i in zip(PILLAR_KEYS, indices)}
    lunar = chinese_lunar_date(instant.date())
    (current_name, current_start), (next_name, next_start) = _terms_around(instant)
    current_local, next_local = current_start.astimezone(instant.tzinfo), next_start.astimezone(instant.tzinfo)
    span = (next_start - current_start).total_seconds()
    result = {
        'system': 'daily-almanac',
        'moment': instant.isoformat(timespec='minutes'),
        'timezone': req.timezone,
        'date': instant.date().isoformat(),
        'weekday': WEEKDAYS[instant.weekday()],
        'pillars': pillars,
        'zodiac': ANIMALS[indices[0] % 12],
        'lunar': {**lunar, 'label': lunar_label(lunar)},
        'solar_term': {
            'current': {'name': current_name, 'start': current_local.isoformat(timespec='minutes'),
                        'day_number': (instant.date() - current_local.date()).days + 1},
            'next': {'name': next_name, 'start': next_local.isoformat(timespec='minutes'),
                     'days_until': (next_local.date() - instant.date()).days},
            'progress': round((instant - current_start).total_seconds() / span, 3),
        },
        'day_officer': _day_officer(instant),
        'moon': _moon(instant),
        'personal': _personal(req.birth, instant, pillars) if req.birth else None,
        'method': ('Pillars from the bazi_chart pillar function (Lichun year, jie months, 00:00 day change, clock time); '
                   'lunar date from astronomical new moons in China time; moon phase from the geocentric elongation.'),
        'limitations': [
            '只列历法事实与传统名称，不给吉凶评分、宜忌或预测。',
            '建除值日按所在时区当天正午的节令月归类；交节当天节令前后可能不同。',
            '月相按地心黄经差计算，与当地实际所见可能相差数小时。',
        ],
    }
    if req.birth:
        result['limitations'].append('十神与六冲、六合、同支只是传统标签，不代表现实中的好坏；出生资料只用于本次计算，服务器不保存。')
    return result
