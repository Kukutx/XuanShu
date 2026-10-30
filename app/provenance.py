"""Where the numbers come from: the ephemeris and the time-zone rules this process applies.

app/__init__.py points zoneinfo at the bundled tzdata package (a declared dependency) instead of the operating
system's database, so two machines give the same daylight-saving answer for the same birth time. Without the
package installed the system database is used and reported as such.
"""
from __future__ import annotations

import zoneinfo
from pathlib import Path

import swisseph as swe


def timezone_database() -> dict:
    if not zoneinfo.TZPATH:
        try:
            import tzdata
            return {'source': 'tzdata package', 'version': tzdata.IANA_VERSION}
        except ImportError:
            return {'source': 'unavailable', 'version': None}
    for base in map(Path, zoneinfo.TZPATH):
        if (base / 'Asia' / 'Shanghai').is_file():
            version = None
            index = base / 'tzdata.zi'
            if index.is_file():
                with index.open(encoding='utf-8', errors='replace') as handle:
                    first = handle.readline().strip()
                if first.startswith('# version '):
                    version = first[len('# version '):]
            return {'source': 'system', 'version': version}
    return {'source': 'unavailable', 'version': None}


def runtime_provenance() -> dict:
    return {
        'ephemeris': {'library': 'Swiss Ephemeris', 'version': swe.version,
                      'mode': 'Moshier analytical theory (no ephemeris files)'},
        'timezone_database': timezone_database(),
    }
