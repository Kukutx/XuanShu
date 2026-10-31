"""Auditable BaZi decade sequences and event-driven birth-time boundary mapping.

Independent traditional calculation conventions, NOT predictions or guaranteed
school-neutral charts. The boundary map inventories discontinuities in the
*currently implemented* BaZi / partial Zi Wei algorithms, not unknown schools.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from math import floor, ceil
from zoneinfo import ZoneInfo
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .astronomy import TERMS, from_jd, solar_term_jd, jie_months, jie_neighbors
from .engines import (BirthInput, BRANCHES, STEMS, normalized_dt, calculate_bazi,
                      calculate_ziwei, hour_branch_index, natal_interactions, pillar_indices)
from .features import _day_pillar
from .shensha import rule_notes
from .timebasis import time_basis


class DayunRequest(BaseModel):
    """Traditional three-days-to-one-year method, with explicit direction policy."""
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    periods: int = Field(default=10, ge=1, le=12)
    direction_override: Literal['forward', 'reverse'] | None = None
    include_years: bool = Field(default=False, description='Also list each civil year of every period with its pillar read against the natal chart')
    hour_unknown: bool = Field(default=False, description='Birth hour unknown: relations with the hour pillar are left out')
    month_year: int | None = Field(default=None, ge=1901, le=2099, description='Also list the twelve month pillars of this year, counted from Lichun, each from the jie that opens it to the next, read against the natal chart')
    day_month: int | None = Field(default=None, ge=1, le=12, description='With month_year: also list every civil day of this month of that year (1 is the Yin month that opens at Lichun) with its day pillar read against the natal chart')
    hour_date: date | None = Field(default=None, ge=date(1901, 1, 1), le=date(2099, 12, 31), description='Also list the thirteen double-hours of this civil day by the clock in the birth time zone (Zi from midnight and again from 23:00), each hour pillar read against the natal chart')

    @model_validator(mode='after')
    def require_direction(self):
        if self.birth.gender == 'unspecified' and self.direction_override is None:
            raise ValueError('Specify male/female in birth.gender or an explicit direction_override; direction is never guessed')
        if self.day_month is not None and self.month_year is None:
            raise ValueError('day_month needs month_year: it picks a month of that year')
        return self


def month_pillars(year: int, natal: dict, keys: tuple[str, ...], zone, day_month: int | None = None) -> dict:
    """The twelve month pillars of a 立春 year: the 寅 month opens at 立春 and each month runs to the next jie. The
    stems follow from the year stem by the five-tiger rule (五虎遁): 甲己之年丙作首, so 寅 takes 丙 in a 甲 or 己 year."""
    year_stem = (year - 4) % 10
    first = (year_stem % 5 * 2 + 2) % 10
    jie = jie_months(year)
    months = []
    for i in range(12):
        pillar = STEMS[(first + i) % 10] + BRANCHES[(2 + i) % 12]
        months.append({'month': i + 1, 'jie': jie[i][0],
                       'start_local': jie[i][1].astimezone(zone).isoformat(timespec='minutes'),
                       'end_local_exclusive': jie[i + 1][1].astimezone(zone).isoformat(timespec='minutes'),
                       # As with the years, the hidden stems stay with the decade.
                       **{k: v for k, v in natal_interactions(pillar, natal, keys).items() if k != 'hidden_stems'}})
    if day_month is not None:
        # The civil days from the one the jie falls on to the one before the next jie: the jie's day is listed under
        # the new month, though before the jie's moment it still belongs to the one before. Days change at midnight.
        month = months[day_month - 1]
        first_day = jie[day_month - 1][1].astimezone(zone).date()
        count = (jie[day_month][1].astimezone(zone).date() - first_day).days
        # A date the zone skipped (Samoa went from 29 to 31 December 2011) has no day to list.
        exists = lambda day: datetime(day.year, day.month, day.day, 12, tzinfo=zone).astimezone(timezone.utc).astimezone(zone).date() == day
        month['days'] = [{'date': day.isoformat(), 'jie_day': n == 0,
                          **{k: v for k, v in natal_interactions(_day_pillar(day), natal, keys).items() if k != 'hidden_stems'}}
                         for n in range(count) if exists(day := first_day + timedelta(days=n))]
    return {'year': year, 'year_pillar': STEMS[year_stem] + BRANCHES[(year - 4) % 12], 'months': months}


def hour_pillars(day: date, natal: dict, keys: tuple[str, ...], zone, late_zi: bool) -> dict:
    """The double-hours of a civil day by the clock in the chart's zone: 子 from midnight to 01:00, a branch every two
    hours after it, and 子 again from 23:00. Each pillar comes from the natal engine's own rule, the stem from the day
    stem by the five-rat rule (五鼠遁); with the 23:00 day change the last 子 already belongs to the next day."""
    def wall(minutes: int) -> datetime:
        return datetime(day.year, day.month, day.day, tzinfo=zone) + timedelta(minutes=minutes)

    def exists(moment: datetime) -> bool:  # not inside a clock jump (a DST gap or a skipped day)
        return moment.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == moment.replace(tzinfo=None)

    hours = []
    for n in range(13):
        start, end = (0, 1) if n == 0 else (2 * n - 1, min(2 * n + 1, 24))
        # A double-hour the clock jumps over entirely is not listed; otherwise any minute of it that happened will do.
        moment = next((m for m in (wall((start + end) * 30), wall(start * 60), wall(end * 60 - 1)) if exists(m)), None)
        if moment is None:
            continue
        (_, _, day_index, hour_index), _, _ = pillar_indices(moment, late_zi)
        pillar = STEMS[hour_index % 10] + BRANCHES[hour_index % 12]
        hours.append({'branch': pillar[1], 'start': f'{start:02d}:00', 'end': f'{end:02d}:00', 'pillar': pillar,
                      'day_pillar': STEMS[day_index % 10] + BRANCHES[day_index % 12],
                      **{k: v for k, v in natal_interactions(pillar, natal, keys).items() if k != 'hidden_stems'}})
    return {'date': day.isoformat(), 'day_pillar': _day_pillar(day), 'day_boundary': '23:00' if late_zi else '00:00',
            'hours': hours}


def dayun_sequence(request: DayunRequest) -> dict:
    """Build the month-pillar 60-cycle sequence and an explicitly approximate timeline.

    Three actual solar-term interval days == one *nominal* traditional year.
    A tropical-year duration is used ONLY to project approximate Gregorian
    starting instants; this isn't a historical calendrical or fortune claim.
    """
    natal = calculate_bazi(request.birth)
    birthday = normalized_dt(request.birth)
    stem = natal['pillars']['year']['stem']
    yang = STEMS.index(stem) % 2 == 0
    direction = request.direction_override or (
        'forward' if yang == (request.birth.gender == 'male') else 'reverse'
    )
    previous_jie, next_jie = jie_neighbors(birthday)
    # On the *exact* astronomical jie, forward birth-to-jie distance is zero.
    # nearest_jie() deliberately returns strictly-next for display, so its
    # rounded-to-second field must not be used for exact age calculations.
    selected = (previous_jie if direction == 'reverse' or previous_jie[1] == birthday else next_jie)
    target = selected[1]
    boundary = {'name': selected[0],
                'instant': target.astimezone(birthday.tzinfo).isoformat(timespec='microseconds')}
    distance_seconds = abs((target - birthday).total_seconds())
    traditional_years = distance_seconds / (3 * 86400)
    # Not calendrical precision: numeric year age is an idealized 365.2425 days.
    start_utc = birthday.astimezone(timezone.utc) + timedelta(days=traditional_years * 365.2425)
    month_pillar = natal['pillars']['month']['text']
    index = next(i for i in range(60) if STEMS[i % 10] + BRANCHES[i % 12] == month_pillar)
    sign = 1 if direction == 'forward' else -1
    keys = ('year', 'month', 'day') if request.hour_unknown else ('year', 'month', 'day', 'hour')
    periods = []
    for i in range(request.periods):
        from_age = traditional_years + i * 10
        begin = start_utc + timedelta(days=i * 10 * 365.2425)
        finish = start_utc + timedelta(days=(i + 1) * 10 * 365.2425)
        cycle = (index + sign * (i + 1)) % 60
        periods.append({
            'sequence': i + 1,
            'pillar': STEMS[cycle % 10] + BRANCHES[cycle % 12],
            'approx_start_age_years': round(from_age, 4),
            'approx_end_age_years': round(from_age + 10, 4),
            'approx_start_local': begin.astimezone(birthday.tzinfo).isoformat(timespec='minutes'),
            'approx_end_local_exclusive': finish.astimezone(birthday.tzinfo).isoformat(timespec='minutes'),
            'natal_interactions': natal_interactions(STEMS[cycle % 10] + BRANCHES[cycle % 12], natal, keys),
        })
        if request.include_years:
            # The common 交运年 listing: from the civil year the period begins in up to the year the next one
            # begins in. The year that straddles a change is listed whole under the new period, so consecutive
            # periods share no year and skip none; the pillar is the one that 立春 opens in that year.
            first, last = begin.astimezone(birthday.tzinfo).year, finish.astimezone(birthday.tzinfo).year
            # The hidden stems stay with the decade: per year they would add a quarter to the reply for nothing shown.
            periods[-1]['years'] = [{'year': y, **{k: v for k, v in natal_interactions(STEMS[(y - 4) % 10] + BRANCHES[(y - 4) % 12], natal, keys).items()
                                                   if k != 'hidden_stems'}}
                                    for y in range(first, last)]
    flow_months = (month_pillars(request.month_year, natal, keys, birthday.tzinfo, request.day_month)
                   if request.month_year is not None else None)
    flow_hours = (hour_pillars(request.hour_date, natal, keys, birthday.tzinfo, request.birth.late_zi_day_rollover)
                  if request.hour_date is not None else None)
    months_float = traditional_years * 12
    months_whole = floor(months_float)
    nominal_days = round((months_float - months_whole) * 30, 1)
    if nominal_days >= 30:
        months_whole += 1
        nominal_days = 0.0
    return {
        'system': 'bazi-traditional-dayun-sequence',
        'birth_datetime': birthday.isoformat(timespec='minutes'),
        'natal_year_pillar': natal['pillars']['year']['text'],
        'natal_month_pillar': month_pillar,
        'direction': direction,
        'direction_source': 'explicit_override' if request.direction_override else 'year_stem_yinyang_and_gender',
        'nearest_jie_used': boundary,
        'birth_to_jie_days': round(distance_seconds / 86400, 7),
        'start_age_years_nominal': round(traditional_years, 6),
        'start_age_traditional_parts': {'years': months_whole // 12, 'months': months_whole % 12,
                                        'days_nominal_30_day_month': nominal_days},
        'approx_first_start_local': start_utc.astimezone(birthday.tzinfo).isoformat(timespec='minutes'),
        'periods': periods,
        **({'flow_months': flow_months} if flow_months else {}),
        **({'flow_hours': flow_hours} if flow_hours else {}),
        'shensha_rules': rule_notes({star['name'] for period in periods
                                     for item in [period['natal_interactions'], *period.get('years', [])]
                                     for star in item['shensha']}
                                    | {star['name'] for month in (flow_months or {}).get('months', [])
                                       for item in [month, *month.get('days', [])] for star in item['shensha']}
                                    | {star['name'] for hour in (flow_hours or {}).get('hours', []) for star in hour['shensha']}),
        'method': {'direction': 'year stem yin/yang + gender, or explicit override',
                   'jie': '12 month-boundary jie, not 24 solar terms',
                   'age_conversion': 'three exact elapsed days per nominal traditional year',
                   'civil_projection': '365.2425 days per nominal age-year; approximate, not a calendar school standard',
                   'annual_pillars': 'with include_years: the civil years from the one each period begins in to the one the next begins in; the year of a change is listed under the new period',
                   'month_pillars': 'with month_year: the twelve months of that year from Lichun, the Yin month first, each from its jie to the next; stems from the year stem by the five-tiger rule',
                   'day_pillars': 'with day_month: the civil days of that month, from the day its jie falls on to the day before the next jie; the day pillar changes at midnight',
                   'hour_pillars': 'with hour_date: the thirteen double-hours of that civil day by the clock in the birth time zone, Zi at both ends; stems from the day stem by the five-rat rule, with the natal chart\'s choice of day change at 23:00 or midnight',
                   'shensha': 'stars on each luck or year pillar, read from the natal day stem, year stem, year and day branches and month branch (Kui Gang belongs to the natal day pillar only)'},
        'limitations': [
            '大运是传统十年干支标签，本工具不据此预测真实事件、吉凶、健康、财运或关系。',
            '起运年龄按三日折一岁；起始公历时间采用365.2425日近似年投影，非各流派统一精确交运日。',
            '顺逆规则参考立春年柱阴阳；自选 direction_override 优先。不同流派可按不同起运和顺逆规则排盘。',
            '时制模式用于出生时辰；交节间隔始终按实际UTC瞬间计算，不能把钟表偏移伪装为时间流逝。',
            '与原局的星运、空亡和合冲刑害只是传统标签，不判断合化成败，也不据此断吉凶。',
            '大运流年的神煞按原局日干、年干、年支、日支、月支查，只列名称与查法出处，不断吉凶。',
            '流年按常见排法从交运那一年列起：交运当年整年记在新大运下，交运日之前的几个月实际仍属上一步大运。',
            '流月以十二节交接换月、立春起寅月，月干按五虎遁从年干起；与流年一样只读出关系标签，不断吉凶。',
            '流日按公历日列出，日柱在午夜换日；交节那天整天列在新月下，交节时刻之前其实仍属上个月。',
            '流时按出生时区的钟表时间分时辰，不做真太阳时修正，时钟跳过的时辰不列出；23:00 起的子时是否换日跟随出生盘的子时设置。',
        ],
    }


class BirthBoundaryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    uncertainty_minutes: int = Field(default=60, ge=1, le=120)


def _wall_state(instant_utc: datetime, birth: BirthInput) -> tuple:
    local = instant_utc.astimezone(ZoneInfo(birth.timezone))
    effective, _ = time_basis(local, birth.time_mode, birth.longitude)
    date_roll = effective.date() + (timedelta(days=1) if birth.late_zi_day_rollover and effective.hour == 23 else timedelta())
    return (effective.date(), date_roll, hour_branch_index(effective.hour), int(local.utcoffset().total_seconds()))


def _instant_ceil_second(value: datetime) -> datetime:
    return value.replace(microsecond=0) + (timedelta(seconds=1) if value.microsecond else timedelta())


def _find_first_changed_second(start: datetime, end: datetime, state, reference: tuple) -> datetime:
    """Find first whole UTC second with changed wall/chart-placement keys."""
    lo, hi = start, end
    for _ in range(25):
        if (hi - lo).total_seconds() <= .75:
            break
        mid = lo + (hi - lo) / 2
        if state(mid) == reference:
            lo = mid
        else:
            hi = mid
    # The change lies in (lo, hi] with hi - lo under a second: the first changed whole second is floor(hi) when the
    # change falls at or before it, else the second after.
    candidate = hi.replace(microsecond=0)
    if candidate <= lo or state(candidate) == reference:
        candidate += timedelta(seconds=1)
    # Floating point edge rounding can land before exact transition.
    for _ in range(3):
        if state(candidate) != reference:
            break
        candidate += timedelta(seconds=1)
    return candidate


def birth_boundary_map(request: BirthBoundaryRequest) -> dict:
    """Partition a UTC birth interval at every modeled discontinuity.

    Minute-wide detection bins with sub-second bisection, plus exact jie
    crossing instants (even if two lie in one detection bin). This is a
    deterministic numerical inventory for implemented rules only.
    """
    original = normalized_dt(request.birth)
    midpoint = original.astimezone(timezone.utc)
    start = midpoint - timedelta(minutes=request.uncertainty_minutes)
    end = midpoint + timedelta(minutes=request.uncertainty_minutes)
    if start.astimezone(original.tzinfo).year < 1901 or end.astimezone(original.tzinfo).year > 2099:
        raise ValueError('Uncertainty interval must stay within supported 1901–2099 birth years')
    state = lambda moment: _wall_state(moment, request.birth)
    raw_events: dict[datetime, set[str]] = {}
    previous = start
    prev_state = state(previous)
    for index in range(1, request.uncertainty_minutes * 2 + 1):
        now = start + timedelta(minutes=index)
        next_state = state(now)
        if next_state != prev_state:
            candidate = _find_first_changed_second(previous, now, state, prev_state)
            if start < candidate < end:
                before = state(candidate - timedelta(seconds=1))
                after = state(candidate)
                names = set()
                if before[2] != after[2]: names.add('时辰界')
                if before[0] != after[0]: names.add('有效历日界')
                if before[1] != after[1]: names.add('日柱日期界')
                if before[3] != after[3]: names.add('时区夏令时/历史UTC偏移界')
                raw_events.setdefault(candidate, set()).update(names or {'时制规则界'})
        previous, prev_state = now, next_state
    # Solar jie is an independent possible boundary even when wall reading
    # remains identical; take its exact UTC astronomical instant.
    for year in range(start.year - 1, end.year + 2):
        for name, longitude, _, __ in TERMS:
            if longitude % 30 != 15:
                continue
            instant = from_jd(solar_term_jd(year, longitude))
            if start < instant < end:
                moment = _instant_ceil_second(instant)
                raw_events.setdefault(moment, set()).add('节令界:' + name)
    boundaries = sorted(event for event in raw_events if start < event < end)
    times = [start, *boundaries, end]
    segments = []
    for i, (begin, finish) in enumerate(zip(times[:-1], times[1:]), 1):
        instant = begin + (finish - begin) / 2
        local = instant.astimezone(original.tzinfo)
        variant = request.birth.model_copy(update={'birth_datetime': local.isoformat(timespec='microseconds')})
        bazi = calculate_bazi(variant)
        ziwei = calculate_ziwei(variant)
        segments.append({
            'index': i,
            'start_utc_inclusive': begin.isoformat(timespec='seconds'),
            'end_utc_exclusive': finish.isoformat(timespec='seconds'),
            'start_local_inclusive': begin.astimezone(original.tzinfo).isoformat(timespec='seconds'),
            'end_local_exclusive': finish.astimezone(original.tzinfo).isoformat(timespec='seconds'),
            'sample_local': local.isoformat(timespec='seconds'),
            'bazi_pillars': {key: bazi['pillars'][key]['text'] for key in ('year', 'month', 'day', 'hour')},
            'ziwei_ming_palace': ziwei['ming_palace'],
            'ziwei_shen_palace': ziwei['shen_palace'],
            'ziwei_bureau': ziwei['five_elements_bureau'],
            'ziwei_lunar_date': {k: ziwei['lunar_date'][k] for k in ('year', 'month', 'day', 'is_leap_month')},
        })
    return {
        'system': 'birth-chart-modeled-boundary-map',
        'original_birth_local': original.isoformat(timespec='minutes'),
        'uncertainty_minutes': request.uncertainty_minutes,
        'start_utc': start.isoformat(timespec='seconds'),
        'end_utc': end.isoformat(timespec='seconds'),
        'boundary_resolution_seconds': 1,
        'boundaries': [
            {'utc': instant.isoformat(timespec='seconds'),
             'local': instant.astimezone(original.tzinfo).isoformat(timespec='seconds'),
             'types': sorted(raw_events[instant])}
            for instant in boundaries
        ],
        'segments': segments,
        'method': 'UTC-ordered minute detection + second-bisection for clock/solar reading transitions; exact computed jie added',
        'limitations': [
            '边界仅覆盖当前八字及部分紫微实现的日、时辰、十二节令、时区转变；不保证覆盖未实现的流派或星曜规则。',
            '边界时间已量化到1秒，天文学数值存在求根误差；不应据此声称秒级出生时间的真实准确性。',
            '每段按中点计算代表盘，边界端点附近应使用原始出生记录重新核对。',
        ],
    }
