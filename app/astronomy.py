"""Astronomical dates for the Chinese calendar, using Swiss Ephemeris (AGPL).

Chinese lunar calendar: new moon *local date* in Asia/Shanghai starts a month;
winter solstice lies in month 11; the first month without a principal solar
term in a 13-month sui is leap. Supports Gregorian 1901–2099.

This computes dates dynamically, not using the Korean lunar-calendar tables.
Event dates use the 120°E meridian (UTC+08), as the Chinese calendar has since
1929. From 1912 to 1928 the calendar was computed for the Beijing meridian,
116°25'E (local mean time UTC+07:45:40), so those years use it. The Qing
calendar (1901-1911) used older astronomy that is not reproduced here.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
import math
import swisseph as swe

CHINA = timezone(timedelta(hours=8))
UTC = timezone.utc
# Before 1929 the calendar was computed for the Beijing meridian, 116°25'E
# (Aslaksen, "The Mathematics of the Chinese Calendar", sections 4.2 and 4.6).
# Applied from 1912, the first Republican calendar year.
BEIJING_MEAN = timezone(timedelta(hours=7, minutes=45, seconds=40))
BEIJING_MERIDIAN_START = datetime(1912, 1, 1, tzinfo=BEIJING_MEAN)
BEIJING_MERIDIAN_END = datetime(1929, 1, 1, tzinfo=CHINA)
FLAG = swe.FLG_MOSEPH | swe.FLG_SPEED

# Actual 24 solar terms with tropical geocentric solar longitudes.
TERMS = (
    ("小寒", 285, 1, 5), ("大寒", 300, 1, 20),
    ("立春", 315, 2, 4), ("雨水", 330, 2, 19),
    ("惊蛰", 345, 3, 5), ("春分", 0, 3, 20),
    ("清明", 15, 4, 4), ("谷雨", 30, 4, 20),
    ("立夏", 45, 5, 5), ("小满", 60, 5, 21),
    ("芒种", 75, 6, 5), ("夏至", 90, 6, 21),
    ("小暑", 105, 7, 7), ("大暑", 120, 7, 23),
    ("立秋", 135, 8, 7), ("处暑", 150, 8, 23),
    ("白露", 165, 9, 7), ("秋分", 180, 9, 23),
    ("寒露", 195, 10, 8), ("霜降", 210, 10, 23),
    ("立冬", 225, 11, 7), ("小雪", 240, 11, 22),
    ("大雪", 255, 12, 7), ("冬至", 270, 12, 21),
)


def to_jd(value: datetime) -> float:
    dt = value.astimezone(UTC)
    hours = dt.hour + dt.minute / 60 + dt.second / 3600 + dt.microsecond / 3600000000
    return swe.julday(dt.year, dt.month, dt.day, hours)


def from_jd(jd: float) -> datetime:
    year, month, day, hours = swe.revjul(jd)
    return datetime(year, month, day, tzinfo=UTC) + timedelta(hours=hours)


def signed_degrees(degrees: float) -> float:
    return (degrees + 180) % 360 - 180


def sun_data(jd: float) -> tuple[float, float]:
    info, _ = swe.calc_ut(jd, swe.SUN, FLAG)
    return info[0], info[3]


def moon_data(jd: float) -> tuple[float, float]:
    info, _ = swe.calc_ut(jd, swe.MOON, FLAG)
    return info[0], info[3]


def sun_longitude(value: datetime) -> float:
    return sun_data(to_jd(value))[0]


@lru_cache(maxsize=512)
def solar_term_jd(year: int, longitude: int) -> float:
    rough = next((x for x in TERMS if x[1] == longitude), None)
    if rough is None:
        raise ValueError("Solar term longitude must be a multiple of 15 degrees")
    jd = to_jd(datetime(year, rough[2], rough[3], 12, tzinfo=UTC))
    for _ in range(12):
        solar, speed = sun_data(jd)
        step = signed_degrees(solar - longitude) / speed
        jd -= step
        if abs(step) < 1e-10:
            break
    return jd


def get_solar_terms(year: int) -> list[dict]:
    return [
        {"name": name, "longitude": lon, "time_china": from_jd(solar_term_jd(year, lon)).astimezone(CHINA).isoformat(timespec="seconds")}
        for name, lon, _, __ in TERMS
    ]


@lru_cache(maxsize=4096)
def new_moon_jd(k: int) -> float:
    jd = 2451550.09765 + k * 29.530588853  # Mean new moon, J2000 epoch
    for _ in range(16):
        sun, sun_speed = sun_data(jd)
        moon, moon_speed = moon_data(jd)
        step = signed_degrees(moon - sun) / (moon_speed - sun_speed)
        jd -= step
        if abs(step) < 1e-9:
            break
    return jd


def calendar_zone(moment: datetime) -> timezone:
    """The time zone whose dates the Chinese calendar used at an instant."""
    return BEIJING_MEAN if BEIJING_MERIDIAN_START <= moment < BEIJING_MERIDIAN_END else CHINA


def _local_date(jd: float) -> date:
    moment = from_jd(jd)
    return moment.astimezone(calendar_zone(moment)).date()


def _new_moons_between(jd_start: float, jd_end: float) -> list[float]:
    k0 = math.floor((jd_start - 2451550.09765) / 29.530588853) - 2
    k1 = math.ceil((jd_end - 2451550.09765) / 29.530588853) + 2
    return [new_moon_jd(k) for k in range(k0, k1 + 1)]


def _find_month_index(moons: list[date], day: date) -> int:
    for i in range(len(moons) - 1):
        if moons[i] <= day < moons[i + 1]:
            return i
    raise ValueError(f"Could not assign date to lunar month: {day}")


@lru_cache(maxsize=512)
def chinese_lunar_date(solar_date: date) -> dict:
    """Computes modern Chinese lunar day/month/year, including leap month."""
    if not 1901 <= solar_date.year <= 2099:
        raise ValueError("Supported Gregorian years: 1901–2099")
    solstice_this_year = _local_date(solar_term_jd(solar_date.year, 270))
    prior_year = solar_date.year if solar_date >= solstice_this_year else solar_date.year - 1
    solstice_prev = solar_term_jd(prior_year, 270)
    solstice_next = solar_term_jd(prior_year + 1, 270)
    moons = _new_moons_between(solstice_prev - 40, solstice_next + 65)
    days = [_local_date(jd) for jd in moons]
    start = _find_month_index(days, _local_date(solstice_prev))
    end = _find_month_index(days, _local_date(solstice_next))
    target = _find_month_index(days, solar_date)
    if not start <= target <= end:
        raise ValueError("Lunar calendar assignment failed at winter-solstice boundary")

    # Twelve principal solar terms, starting with winter solstice, are within
    # month 11 to (but not including) the next winter-solstice month 11.
    principal_dates = []
    for year in (prior_year, prior_year + 1):
        for longitude in range(0, 360, 30):
            event = solar_term_jd(year, longitude)
            if solstice_prev <= event < solstice_next:
                principal_dates.append(_local_date(event))
    principal_dates.append(_local_date(solstice_prev))

    leap_index = None
    if end - start == 13:
        for i in range(start + 1, end):
            has_principal = any(days[i] <= x < days[i + 1] for x in principal_dates)
            if not has_principal:
                leap_index = i
                break
        if leap_index is None:
            raise ValueError("Intercalary lunar month not found for 13-month lunar year")
    elif end - start != 12:
        raise ValueError("Unexpected lunar months between solstices")

    month = 11
    is_leap = False
    for i in range(start + 1, target + 1):
        if i == end:
            month, is_leap = 11, False
        elif i == leap_index:
            is_leap = True
        else:
            month = month % 12 + 1
            is_leap = False
    lunar_year = prior_year + (1 if month < 11 else 0)
    if target == end:
        lunar_year = prior_year + 1
    return {
        "year": lunar_year,
        "month": month,
        "day": (solar_date - days[target]).days + 1,
        "is_leap_month": is_leap,
        "month_days": (days[target + 1] - days[target]).days,
        "method": "astronomical-new-moon-beijing-116e25" if 1912 <= solar_date.year <= 1928 else "astronomical-new-moon-china-utc8",
    }


@lru_cache(maxsize=1024)
def _jie_around_year(year: int) -> tuple[tuple[str, datetime], ...]:
    """The 12 solar-term month boundaries (jie), as UTC-aware instants."""
    return tuple(
        (name, from_jd(solar_term_jd(year, longitude)))
        for name, longitude, _month, _day in TERMS if longitude % 30 == 15
    )


def jie_neighbors(instant: datetime) -> tuple[tuple[str, datetime], tuple[str, datetime]]:
    """Find the previous/current and next 12-jie boundaries by UTC instant.

    The previous term is inclusive. Comparing against event times rather than
    flooring a rounded solar longitude avoids a wrong month at the exact jie.
    """
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError('An aware datetime is required for jie comparison')
    events = sorted(
        ((name, event) for year in (instant.year - 1, instant.year, instant.year + 1)
         for name, event in _jie_around_year(year)),
        key=lambda item: item[1],
    )
    previous = next(((name, event) for name, event in reversed(events) if event <= instant), None)
    following = next(((name, event) for name, event in events if event > instant), None)
    if previous is None or following is None:
        raise ValueError('Cannot determine solar-term month boundary')
    return previous, following


def solar_month_offset(instant: datetime) -> int:
    """Zero-based Jie month since 立春; exact term instant belongs to new month."""
    previous, _ = jie_neighbors(instant)
    longitude_by_name = {name: longitude for name, longitude, _, _ in TERMS}
    return ((longitude_by_name[previous[0]] - 315) % 360) // 30


def nearest_jie(birth_time: datetime) -> dict:
    """Adjacent jie boundaries; useful for auditing a BaZi month pillar."""
    previous, following = jie_neighbors(birth_time)
    return {
        'previous': {'name': previous[0], 'instant': previous[1].astimezone(birth_time.tzinfo).isoformat(timespec='seconds')},
        'next': {'name': following[0], 'instant': following[1].astimezone(birth_time.tzinfo).isoformat(timespec='seconds')},
    }
