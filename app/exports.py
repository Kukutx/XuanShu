"""Portable exports that contain no private birth records."""
from __future__ import annotations
from datetime import datetime, timezone
from .astronomy import get_solar_terms


def _fold(line: str) -> list[str]:
    """RFC 5545 line folding: at most 75 octets per line, never splitting a UTF-8 character."""
    parts, current, size = [], '', 0
    for char in line:
        width = len(char.encode('utf-8'))
        if size + width > (75 if not parts else 74):
            parts.append(current)
            current, size = '', 0
        current += char
        size += width
    parts.append(current)
    return [parts[0]] + [' ' + part for part in parts[1:]]


def _ics_text(value: str) -> str:
    return value.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def solar_terms_ics(year: int, moon: bool = False) -> str:
    """The 24 solar terms of a year; with ``moon``, also the new, first-quarter, full and last-quarter moons."""
    if not 1901 <= year <= 2099:
        raise ValueError('Supported years: 1901–2099')
    rows = [
        'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//XuanShu//Solar Terms//ZH',
        'CALSCALE:GREGORIAN', 'METHOD:PUBLISH', 'X-WR-CALNAME:' + ('二十四节气与月相' if moon else '二十四节气'),
    ]
    for term in get_solar_terms(year):
        china_time = datetime.fromisoformat(term['time_china'])
        instant = china_time.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        rows += [
            'BEGIN:VEVENT', f'UID:jieqi-{year}-{term["longitude"]}@xuanshu.local',
            'DTSTAMP:20000101T000000Z', f'DTSTART:{instant}',
            f'SUMMARY:{_ics_text(term["name"])}',
            'DESCRIPTION:天文节气到达时间，中国标准时转换为 UTC。',
            'END:VEVENT',
        ]
    if moon:
        from .almanac import moon_phases
        for phase in moon_phases(year):
            instant = phase['instant'].astimezone(timezone.utc)
            rows += [
                'BEGIN:VEVENT', f'UID:moon-{instant:%Y%m%d}-{phase["elongation"]}@xuanshu.local',
                'DTSTAMP:20000101T000000Z', f'DTSTART:{instant:%Y%m%dT%H%M%SZ}',
                f'SUMMARY:{_ics_text(phase["name"])}',
                'DESCRIPTION:日月地心黄经差到达 0°、90°、180° 或 270° 的时刻（UTC）。',
                'END:VEVENT',
            ]
    rows.append('END:VCALENDAR')
    # RFC 5545: CRLF line ends, long lines folded at 75 octets.
    return '\r\n'.join(part for row in rows for part in _fold(row)) + '\r\n'
