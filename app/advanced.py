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

from .astronomy import TERMS, from_jd, solar_term_jd, jie_neighbors
from .engines import (BirthInput, BRANCHES, STEMS, normalized_dt, calculate_bazi,
                      calculate_ziwei, hour_branch_index, natal_interactions)
from .timebasis import time_basis


class DayunRequest(BaseModel):
    """Traditional three-days-to-one-year method, with explicit direction policy."""
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    periods: int = Field(default=10, ge=1, le=12)
    direction_override: Literal['forward', 'reverse'] | None = None
    include_years: bool = Field(default=False, description='Also list each civil year of every period with its pillar read against the natal chart')
    hour_unknown: bool = Field(default=False, description='Birth hour unknown: relations with the hour pillar are left out')

    @model_validator(mode='after')
    def require_direction(self):
        if self.birth.gender == 'unspecified' and self.direction_override is None:
            raise ValueError('Specify male/female in birth.gender or an explicit direction_override; direction is never guessed')
        return self


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
            periods[-1]['years'] = [{'year': y, **natal_interactions(STEMS[(y - 4) % 10] + BRANCHES[(y - 4) % 12], natal, keys)}
                                    for y in range(first, last)]
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
        'method': {'direction': 'year stem yin/yang + gender, or explicit override',
                   'jie': '12 month-boundary jie, not 24 solar terms',
                   'age_conversion': 'three exact elapsed days per nominal traditional year',
                   'civil_projection': '365.2425 days per nominal age-year; approximate, not a calendar school standard',
                   'annual_pillars': 'with include_years: the civil years from the one each period begins in to the one the next begins in; the year of a change is listed under the new period'},
        'limitations': [
            '大运是传统十年干支标签，本工具不据此预测真实事件、吉凶、健康、财运或关系。',
            '起运年龄按三日折一岁；起始公历时间采用365.2425日近似年投影，非各流派统一精确交运日。',
            '顺逆规则参考立春年柱阴阳；自选 direction_override 优先。不同流派可按不同起运和顺逆规则排盘。',
            '时制模式用于出生时辰；交节间隔始终按实际UTC瞬间计算，不能把钟表偏移伪装为时间流逝。',
            '与原局的星运、空亡和合冲刑害只是传统标签，不判断合化成败，也不据此断吉凶。',
            '流年按常见排法从交运那一年列起：交运当年整年记在新大运下，交运日之前的几个月实际仍属上一步大运。',
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
    candidate = _instant_ceil_second(hi)
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
