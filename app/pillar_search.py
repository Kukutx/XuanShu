"""Reverse lookup: every birth interval in 1901–2099 whose BaZi pillars match.

The search uses the same ``pillar_indices`` function as the chart engine, so a
match here is exactly what ``bazi_chart`` would print for any instant inside it.
Candidate days come from the sexagenary day cycle; each candidate is sampled
every 15 minutes (plus the jie instants that open and close the month) and the
edges of every matching run are bisected to the second.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .astronomy import chinese_lunar_date, from_jd, solar_term_jd
from .engines import BRANCHES, STEMS, pillar_indices

STEP = timedelta(minutes=15)
MAX_MATCHES = 40
UTC = timezone.utc


def sexagenary_index(text: str) -> int:
    """Sexagenary index (0 = jia-zi) of a two-character stem-branch pair; ValueError if impossible."""
    if len(text) != 2 or text[0] not in STEMS or text[1] not in BRANCHES:
        raise ValueError(f'{text!r} is not a heavenly stem followed by an earthly branch')
    stem, branch = STEMS.index(text[0]), BRANCHES.index(text[1])
    if stem % 2 != branch % 2:
        raise ValueError(f'{text} never occurs: a yang stem pairs only with a yang branch')
    return next(i for i in range(60) if i % 10 == stem and i % 12 == branch)


def pillar_text(index: int) -> str:
    return STEMS[index % 10] + BRANCHES[index % 12]


class PillarSearchRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    year: str = Field(description='Year pillar: a heavenly stem followed by an earthly branch, two Chinese characters')
    month: str = Field(description='Month pillar, same form')
    day: str = Field(description='Day pillar, same form')
    hour: str | None = Field(default=None, description='Hour pillar, same form; omit to match whole days')
    timezone: str = Field(default='Asia/Shanghai', description='IANA timezone the results are shown in')
    late_zi_day_rollover: bool = Field(default=False, description='Set true for traditional 23:00 day change')
    time_mode: Literal['clock', 'mean_solar', 'apparent_solar'] = 'clock'
    longitude: float | None = Field(default=None, ge=-180, le=180, description='Birthplace longitude, east positive; required for solar-time modes')
    start_year: int = Field(default=1901, ge=1901, le=2099)
    end_year: int = Field(default=2099, ge=1901, le=2099)

    @field_validator('year', 'month', 'day', 'hour')
    @classmethod
    def valid_pillar(cls, value: str | None) -> str | None:
        if value is not None:
            sexagenary_index(value.strip())
            return value.strip()
        return value

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f'Unknown IANA timezone: {value}') from exc
        return value

    @model_validator(mode='after')
    def consistent(self):
        if self.time_mode != 'clock' and self.longitude is None:
            raise ValueError('longitude is required for solar-time modes')
        if self.start_year > self.end_year:
            raise ValueError('start_year must not be after end_year')
        return self


def _consistency(year: int, month: int, day: int, hour: int | None) -> list[str]:
    """Stem rules that make a combination impossible before any search is done."""
    problems = []
    offset = (month % 12 - 2) % 12
    month_stem = (2 + 2 * (year % 10 % 5) + offset) % 10
    if month % 10 != month_stem:
        problems.append(f'月柱天干与年干不合五虎遁：{pillar_text(year)}年的{BRANCHES[month % 12]}月是'
                        f'{STEMS[month_stem]}{BRANCHES[month % 12]}，不会是{pillar_text(month)}。')
    if hour is not None:
        hour_stem = (2 * (day % 5) + hour % 12) % 10
        if hour % 10 != hour_stem:
            problems.append(f'时柱天干与日干不合五鼠遁：{pillar_text(day)}日的{BRANCHES[hour % 12]}时是'
                            f'{STEMS[hour_stem]}{BRANCHES[hour % 12]}，不会是{pillar_text(hour)}。')
    return problems


def _month_window(solar_year: int, offset: int) -> tuple[datetime, datetime]:
    """Jie instants opening and closing month ``offset`` (0 = the yin month) of the solar year that starts at lichun."""
    def jie(k: int) -> datetime:
        longitude = (315 + 30 * k) % 360
        year = solar_year + (1 if k >= 11 else 0)  # 小寒 and the next 立春 fall in January/February
        return from_jd(solar_term_jd(year, longitude))
    return jie(offset), jie(offset + 1)


def _ceil_second(instant: datetime) -> datetime:
    return instant if not instant.microsecond else instant.replace(microsecond=0) + timedelta(seconds=1)


def _form_reading(start: datetime, end: datetime, zone: ZoneInfo) -> str | None:
    """A minute-resolution clock reading inside [start, end) that names exactly one instant.

    Readings repeated by a daylight-saving fall-back, or skipped by a spring-forward, are refused by the
    chart engines, so the midpoint is tried first and other points of the interval after it."""
    for fraction in (0.5, 0.25, 0.75, 0.1, 0.9, 0.02, 0.98):
        reading = (start + (end - start) * fraction).astimezone(zone).replace(second=0, microsecond=0, tzinfo=None, fold=0)
        first, second = reading.replace(tzinfo=zone), reading.replace(tzinfo=zone, fold=1)
        exists = first.astimezone(UTC).astimezone(zone).replace(tzinfo=None) == reading
        if exists and first.utcoffset() == second.utcoffset() and start <= first < end:
            return reading.isoformat(timespec='minutes')
    return None


def pillars_to_dates(req: PillarSearchRequest) -> dict:
    zone = ZoneInfo(req.timezone)
    year, month, day = (sexagenary_index(x) for x in (req.year, req.month, req.day))
    hour = sexagenary_index(req.hour) if req.hour else None
    target = (year, month, day, hour)
    problems = _consistency(year, month, day, hour)
    lower = datetime(req.start_year, 1, 1, tzinfo=zone).astimezone(UTC)
    upper = datetime(req.end_year + 1, 1, 1, tzinfo=zone).astimezone(UTC) if req.end_year < 2099 else \
        datetime(2099, 12, 31, 23, 59, 59, tzinfo=zone).astimezone(UTC)

    def matches(instant: datetime) -> bool:
        local = instant.astimezone(zone)
        if not 1901 <= local.year <= 2099:
            return False
        got, _, _ = pillar_indices(local, req.late_zi_day_rollover, req.time_mode, req.longitude)
        return got[:3] == target[:3] and (hour is None or got[3] == hour)

    def edge(inside: datetime, outside: datetime) -> datetime:
        """Whole second where a run starts (first matching) or ends (first non-matching), by bisection.

        Bisecting to a millisecond and then rounding up keeps both readings on the correct side of a jie
        instant that falls between two whole seconds."""
        while abs((outside - inside).total_seconds()) > 0.001:
            middle = inside + (outside - inside) / 2
            if matches(middle):
                inside = middle
            else:
                outside = middle
        return _ceil_second(outside if outside > inside else inside)

    runs: list[tuple[datetime, datetime]] = []
    if not problems:
        offset = (month % 12 - 2) % 12
        for solar_year in range(req.start_year - 1, req.end_year + 1):
            if (solar_year - 1984) % 60 != year:
                continue
            opens, closes = _month_window(solar_year, offset)
            if closes <= lower or opens >= upper:
                continue
            first, last = (opens - timedelta(days=2)).date(), (closes + timedelta(days=2)).date()
            candidate = first + timedelta(days=(day - (54 + (first - date(2000, 1, 1)).days)) % 60)
            while candidate <= last:
                # Sample the effective day widely: solar time can move a clock reading by several hours.
                begin = datetime.combine(candidate - timedelta(days=1), datetime.min.time(), zone).astimezone(UTC)
                points = [begin + STEP * k for k in range(int(timedelta(days=3) / STEP))]
                points += [opens, closes - timedelta(seconds=1)]
                points = sorted(p for p in set(points) if max(opens, lower) - STEP <= p <= min(closes, upper) + STEP)
                flags = [matches(p) for p in points]
                for i, ok in enumerate(flags):
                    if not ok or (i and flags[i - 1]):
                        continue
                    j = i
                    while j + 1 < len(flags) and flags[j + 1]:
                        j += 1
                    start = edge(points[i], points[i - 1]) if i else points[i]
                    end = edge(points[j], points[j + 1]) if j + 1 < len(points) else points[j]
                    start, end = max(start, lower), min(end, upper)
                    if start < end:
                        runs.append((start, end))
                candidate += timedelta(days=60)
    unique = sorted(set(runs))[:MAX_MATCHES]

    results = []
    for start, end in unique:
        local_start, local_end = start.astimezone(zone), end.astimezone(zone)
        _, effective, _ = pillar_indices(local_start, req.late_zi_day_rollover, req.time_mode, req.longitude)
        record = {
            'start': local_start.isoformat(timespec='seconds'),
            'end_exclusive': local_end.isoformat(timespec='seconds'),
            'duration_minutes': round((end - start).total_seconds() / 60, 1),
            # A clock reading safely inside the interval, ready for the birth form; None if no reading is unambiguous.
            'suggested_local': _form_reading(start, end, zone),
            'lunar_date': chinese_lunar_date(effective.date()),
        }
        if req.time_mode != 'clock':
            record['effective_start'] = effective.isoformat(timespec='seconds')
        results.append(record)

    pillars = {'year': req.year, 'month': req.month, 'day': req.day, 'hour': req.hour}
    return {
        'system': 'bazi-pillar-reverse-lookup',
        'pillars': pillars,
        'timezone': req.timezone,
        'range': {'start_year': req.start_year, 'end_year': req.end_year},
        'count': len(results),
        'truncated': len(set(runs)) > MAX_MATCHES,
        'matches': results,
        'impossible_combination': problems,
        'rules': {
            'year_boundary': '立春',
            'month_boundary': '十二节令（交节时刻起算）',
            'day_boundary': '23:00' if req.late_zi_day_rollover else '00:00',
            'time_mode': req.time_mode,
            'longitude_east_degrees': req.longitude,
        },
        'method': ('Candidate days from the 60-day cycle inside each matching jie month; 15-minute sampling plus '
                   'the jie instants, then bisection of each edge to one second with the same pillar function as bazi_chart.'),
        'limitations': [
            '起止时刻是这套规则下的计算边界，精确到秒只代表算法数值，不代表出生时刻能这样确定。',
            '其他流派（例如以春节换年、23:00 换日）会得到不同的区间，可切换换日规则或时制重新反查。',
            '只给出符合四柱的时间，不据此判断吉凶或推断人物身份。',
        ],
    }
