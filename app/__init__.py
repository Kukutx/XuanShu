"""XuanShu — standalone calendar calculation and MCP tools."""
__version__ = '0.1.0'
__display_version__ = 'v.0.1.0'

# Daylight-saving rules come from the bundled tzdata package rather than the operating system's database, so every
# machine applies the same rules to the same birth time (reported by /health; see app/provenance.py).
try:
    import tzdata as _tzdata  # noqa: F401
except ImportError:
    pass
else:
    import zoneinfo as _zoneinfo
    _zoneinfo.reset_tzpath(to=())
