"""Explicit civil/mean/apparent solar-time bases for traditional hour rules.

Do not confuse a shifted clock reading with a different astronomical instant.
The precise Sun longitude, new moons and solar terms always use the original UTC instant.
Swiss Ephemeris time_equ returns apparent minus mean solar time in DAYS.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import swisseph as swe


def time_basis(dt: datetime, mode: str = 'clock', longitude: float | None = None) -> tuple[datetime, dict]:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('An aware birth datetime is required for time correction')
    if mode not in ('clock', 'mean_solar', 'apparent_solar'):
        raise ValueError('Unsupported time calculation mode')
    if mode != 'clock' and longitude is None:
        raise ValueError('longitude is required for mean/apparent solar time')
    if longitude is not None and not -180 <= longitude <= 180:
        raise ValueError('longitude must be between -180 and 180')

    utc = dt.astimezone(timezone.utc)
    local_clock = dt.replace(tzinfo=None)
    jd = swe.julday(utc.year, utc.month, utc.day,
                    utc.hour + utc.minute / 60 + utc.second / 3600 + utc.microsecond / 3.6e9)
    eot_minutes = swe.time_equ(jd) * 1440 if mode == 'apparent_solar' else 0.0
    if mode == 'clock':
        effective = local_clock
        shift_minutes = 0.0
        meridian_delta = 0.0
    else:
        # LMT = UT + geographic longitude / 15 hours (east positive).
        # Apparent solar time = LMT + equation of time.
        effective = (utc + timedelta(minutes=longitude * 4 + eot_minutes)).replace(tzinfo=None)
        shift_minutes = (effective - local_clock).total_seconds() / 60
        meridian_delta = longitude * 4 - dt.utcoffset().total_seconds() / 60
    return effective, {
        'mode': mode,
        'civil_datetime': dt.isoformat(timespec='seconds'),
        'effective_local_reading': effective.isoformat(timespec='seconds'),
        'longitude_east_degrees': longitude,
        'civil_utc_offset_minutes': round(dt.utcoffset().total_seconds() / 60, 4),
        'longitude_vs_zone_meridian_minutes': round(meridian_delta, 4),
        'equation_of_time_minutes': round(eot_minutes, 4),
        'effective_shift_minutes': round(shift_minutes, 4),
        'method': 'UT + longitude×4min + EOT' if mode == 'apparent_solar' else (
                  'UT + longitude×4min' if mode == 'mean_solar' else 'civil wall clock'),
        'scope': 'Changes traditional day/hour/lunar-date placement only; never the astronomical instant.',
    }
