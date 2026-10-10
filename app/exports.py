"""Portable exports that contain no private birth records."""
from __future__ import annotations
from datetime import datetime, timezone
from .astronomy import get_solar_terms


def _ics_text(value: str) -> str:
    return value.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def solar_terms_ics(year: int) -> str:
    if not 1901 <= year <= 2099:
        raise ValueError('Supported years: 1901–2099')
    rows = [
        'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//XuanShu//Solar Terms//ZH',
        'CALSCALE:GREGORIAN', 'METHOD:PUBLISH', 'X-WR-CALNAME:二十四节气',
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
    rows.append('END:VCALENDAR')
    # RFC 5545 mandates CRLF. UTF-8 octet line folding can be added later,
    # all current property value lines comfortably fit typical length limits.
    return '\r\n'.join(rows) + '\r\n'
