"""Two complementary, deterministic utilities: lunar inverse and time uncertainty.

All results are calculated from the same astronomical engine as the rest of the
application. Time-window results represent *sampled* outcomes, not a guaranteed
proof that no intermediate chart differs.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field

from .astronomy import _local_date, _new_moons_between, chinese_lunar_date, to_jd
from .engines import BirthInput, calculate_bazi, calculate_ziwei, normalized_dt


class LunarToGregorianRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    lunar_year: int = Field(ge=1901, le=2099)
    lunar_month: int = Field(ge=1, le=12)
    lunar_day: int = Field(ge=1, le=30)
    is_leap_month: bool = False


@lru_cache(maxsize=256)
def lunar_month_catalog(lunar_year: int) -> tuple[tuple[int, bool, date, int], ...]:
    """Retrieve lunar month starts from independent astronomical new moon days.

    Exposes only Gregorian dates in the supported civil range 1901--2099.
    Thus lunar months crossing 2100 are intentionally not fully reversible.
    """
    if not 1901 <= lunar_year <= 2099:
        raise ValueError('Supported lunar years: 1901–2099')
    start = to_jd(datetime(lunar_year, 1, 1, tzinfo=timezone.utc))
    end = to_jd(datetime(lunar_year + 1, 3, 1, tzinfo=timezone.utc))
    months = []
    seen = set()
    for jd in _new_moons_between(start - 45, end + 5):
        civil = _local_date(jd)
        if not 1901 <= civil.year <= 2099 or civil in seen:
            continue
        seen.add(civil)
        lunar = chinese_lunar_date(civil)
        if lunar['year'] == lunar_year and lunar['day'] == 1:
            months.append((lunar['month'], lunar['is_leap_month'], civil, lunar['month_days']))
    return tuple(sorted(months, key=lambda record: record[2]))


def lunar_to_gregorian(request: LunarToGregorianRequest) -> dict:
    catalog = lunar_month_catalog(request.lunar_year)
    target = next(((month, leap, start, length) for month, leap, start, length in catalog
                   if month == request.lunar_month and leap == request.is_leap_month), None)
    if target is None:
        qualifier = 'leap ' if request.is_leap_month else ''
        raise ValueError(f'No supported Gregorian equivalent for lunar {request.lunar_year} {qualifier}month {request.lunar_month}')
    month, leap, start, length = target
    if request.lunar_day > length:
        raise ValueError(f'That lunar month has only {length} days')
    civil = start + timedelta(days=request.lunar_day - 1)
    if not 1901 <= civil.year <= 2099:
        raise ValueError('Gregorian equivalent is outside 1901–2099')
    reverse = chinese_lunar_date(civil)
    if (reverse['year'], reverse['month'], reverse['day'], reverse['is_leap_month']) != (
            request.lunar_year, month, request.lunar_day, leap):
        raise ValueError('Lunar conversion consistency check failed')
    return {
        'system': 'astronomical-lunar-inverse',
        'gregorian_date': civil.isoformat(),
        'lunar_date': reverse,
        'timezone': 'Asia/Shanghai',
        'method': reverse['method'],
        'limitations': '1929 年起按东经 120° 子午线（UTC+8），1912–1928 年按北京子午线（东经 116°25′）；1912 年以前的清代历书和地方历书可能不同。',
    }


class BirthWindowRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    uncertainty_minutes: int = Field(default=30, ge=5, le=120, description='Plus/minus interval around birth time')
    sample_every_minutes: int = Field(default=10, ge=5, le=60)


def birth_window(request: BirthWindowRequest) -> dict:
    """Sample birth instants in a bounded uncertainty window.

    Works in UTC before converting back to the stated IANA timezone to handle
    DST changes without creating nonexistent or ambiguous wall-clock times.
    """
    original = normalized_dt(request.birth)
    center = original.astimezone(timezone.utc)
    radius = request.uncertainty_minutes
    offsets = sorted(set(range(-radius, radius + 1, request.sample_every_minutes)) | {-radius, 0, radius})
    groups: dict[tuple, dict] = {}
    sample_trace = []
    for offset in offsets:
        instant = center + timedelta(minutes=offset)
        local = instant.astimezone(original.tzinfo)
        variant = request.birth.model_copy(update={'birth_datetime': local.isoformat(timespec='minutes')})
        bazi = calculate_bazi(variant)
        ziwei = calculate_ziwei(variant)
        pillars = tuple(bazi['pillars'][name]['text'] for name in ('year', 'month', 'day', 'hour'))
        signature = (pillars, ziwei['ming_palace'], ziwei['shen_palace'], ziwei['five_elements_bureau'])
        display_time = local.isoformat(timespec='minutes')
        if signature not in groups:
            groups[signature] = {
                'pillars': dict(zip(('year', 'month', 'day', 'hour'), pillars)),
                'ming_palace': ziwei['ming_palace'],
                'shen_palace': ziwei['shen_palace'],
                'five_elements_bureau': ziwei['five_elements_bureau'],
                'first_sample_local': display_time,
                'last_sample_local': display_time,
                'sample_count': 0,
            }
        group = groups[signature]
        group['last_sample_local'] = display_time
        group['sample_count'] += 1
        sample_trace.append({'offset_minutes': offset, 'local_time': display_time,
                             'variant_index': list(groups).index(signature) + 1})
    return {
        'system': 'sampled-birth-time-sensitivity',
        'center_local': original.isoformat(timespec='minutes'),
        'uncertainty_minutes': radius,
        'sample_every_minutes': request.sample_every_minutes,
        'sample_count': len(offsets),
        'variant_count': len(groups),
        'variants': list(groups.values()),
        'samples': sample_trace,
        'limitations': [
            '只比较了采样点：两个采样点之间的切换可能漏掉，这不是完整的边界检查；精确的切换时刻用 birth_boundaries。',
            '传统命盘标签的变化不代表任何现实预测。',
            '历史时区和地理太阳时校正取决于输入是否准确。',
        ],
    }
