"""Platform hardening: response headers, reproducible time-zone rules, and the MCP endpoint off the event loop."""
import re
import zoneinfo
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main
from app.main import app

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_every_response_denies_unused_features_and_cross_origin_sharing():
    for path in ('/', '/docs', '/static/app.js', '/health', '/openapi.json'):
        headers = client.get(path).headers
        assert 'geolocation=()' in headers['permissions-policy'] and 'camera=()' in headers['permissions-policy'], path
        assert headers['cross-origin-opener-policy'] == 'same-origin', path
        assert headers['cross-origin-resource-policy'] == 'same-origin', path


def test_time_zone_rules_come_from_the_bundled_package_and_are_reported():
    import tzdata
    assert zoneinfo.TZPATH == ()  # app/__init__.py ignores the operating system's database
    health = client.get('/health').json()
    assert health['timezone_database'] == {'source': 'tzdata package', 'version': tzdata.IANA_VERSION}
    assert health['ephemeris']['library'] == 'Swiss Ephemeris' and 'Moshier' in health['ephemeris']['mode']
    assert client.get('/api/capabilities').json()['provenance'] == {k: health[k] for k in ('ephemeris', 'timezone_database')}
    # Historic daylight saving still resolves from the bundled rules (China observed it 1986–1991).
    res = client.post('/api/bazi', json={'birth_datetime': '1988-07-01T12:00', 'timezone': 'Asia/Shanghai'})
    assert res.status_code == 200 and res.json()['birth_datetime'].endswith('+09:00')


def test_mcp_tool_calls_run_in_the_threadpool(monkeypatch):
    seen = []

    async def fake_threadpool(func, *args):
        seen.append(func.__name__)
        return func(*args)

    monkeypatch.setattr(main, 'run_in_threadpool', fake_threadpool)
    res = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})
    assert res.status_code == 200 and res.json()['result']['tools'] and seen == ['process_rpc']


def test_tool_search_placeholder_counts_the_tools_on_the_page():
    html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
    tabs = len(re.findall(r'role="tab"', html))
    assert f'等 {tabs} 项能力' in html and f'展开全部 {tabs} 项' in html
