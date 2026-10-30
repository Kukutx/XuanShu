"""Portable exports that contain no private birth records."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
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


def solar_terms_ics(year: int, moon: bool = False, festivals: bool = False) -> str:
    """The 24 solar terms of a year; with ``moon``, also the new, first-quarter, full and last-quarter moons; with
    ``festivals``, the traditional festivals and the first days of the fu periods and the nines as all-day events."""
    if not 1901 <= year <= 2099:
        raise ValueError('Supported years: 1901–2099')
    extras = (['月相'] if moon else []) + (['传统节令'] if festivals else [])  # 节令: the festivals, 三伏 and 数九
    name = '、'.join(['二十四节气'] + extras[:-1]) + ('与' + extras[-1] if extras else '')
    rows = [
        'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//XuanShu//Solar Terms//ZH',
        'CALSCALE:GREGORIAN', 'METHOD:PUBLISH', 'X-WR-CALNAME:' + name,
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
    if festivals:
        from .festivals import starts_of_year
        seen: dict[str, int] = {}
        for day, mark in starts_of_year(year):
            stamp = f'{day:%Y%m%d}'
            seen[stamp] = seen.get(stamp, 0) + 1
            length = f'共 {mark["length"]} 天。' if mark['kind'] == 'sanfu' and 'length' in mark else ''
            rows += [
                'BEGIN:VEVENT', f'UID:mark-{stamp}-{mark["kind"]}-{seen[stamp]}@xuanshu.local',
                'DTSTAMP:20000101T000000Z', f'DTSTART;VALUE=DATE:{stamp}',
                f'DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}',
                f'SUMMARY:{_ics_text(mark["name"])}',
                f'DESCRIPTION:{_ics_text(length + "推算规则：" + mark["rule"] + "。按中国标准时间的日期。")}',
                'TRANSP:TRANSPARENT', 'END:VEVENT',
            ]
    rows.append('END:VCALENDAR')
    # RFC 5545: CRLF line ends, long lines folded at 75 octets.
    return '\r\n'.join(part for row in rows for part in _fold(row)) + '\r\n'
