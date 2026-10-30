"""The self-hosted API reference at /docs and the OpenAPI additions behind it."""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.api_docs import ROUTES, TAGS
from app.main import app

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)
# Optional engines answer with a clear refusal when they are not installed or configured.
OPTIONAL = {'/api/chat': {200, 503}, '/api/ziwei-professional': {200, 422}}


def test_docs_page_is_self_hosted_and_passes_the_csp():
    res = client.get('/docs')
    assert res.status_code == 200 and 'text/html' in res.headers['content-type']
    assert res.headers['cache-control'] == 'no-cache'  # revalidated like the workbench, so an upgrade shows at once
    assert "script-src 'self'" in res.headers['content-security-policy']
    html = res.text
    assert re.findall(r'<script\b[^>]*>', html) and all('src="/static/' in tag for tag in re.findall(r'<script\b[^>]*>', html))
    assert not any(body.strip() for body in re.findall(r'<script\b[^>]*>(.*?)</script>', html, re.S))  # no inline scripts
    assert not re.search(r'(?:src|href)="(?:https?:)?//', html)  # nothing from another origin
    assert ' style=' not in html and 'id="ui-language"' in html and 'id="theme-toggle"' in html
    assert client.get('/redoc').status_code == 404


def test_docs_script_builds_nodes_without_html_parsing_and_never_stores_the_token():
    js = (ROOT / 'static/api.js').read_text(encoding='utf-8')
    assert 'innerHTML' not in js and 'insertAdjacentHTML' not in js and 'outerHTML' not in js
    assert 'localStorage' not in js and 'sessionStorage' not in js
    assert '$MCP_BEARER_TOKEN' in js  # copied commands carry a placeholder, not the token


def test_every_route_has_a_group_and_a_title():
    schema = client.get('/openapi.json').json()
    names = [name for name, _, _ in TAGS]
    assert [t['name'] for t in schema['tags']] == names and all(t['x-title'] for t in schema['tags'])
    assert '/' not in schema['paths'] and '/docs' not in schema['paths']
    assert set(schema['paths']) == set(ROUTES)
    for path, operations in schema['paths'].items():
        for operation in operations.values():
            assert operation['tags'][0] in names, path
            assert operation['x-title'], path


def test_every_request_example_runs():
    schema = client.get('/openapi.json').json()
    posted = 0
    for path, operations in schema['paths'].items():
        operation = operations.get('post')
        if not operation:
            continue
        example = operation['requestBody']['content']['application/json']['example']
        res = client.post(path, json=example)
        assert res.status_code in OPTIONAL.get(path, {200}), (path, res.status_code, res.text[:300])
        posted += 1
    assert posted >= 36
    # The MCP example is a JSON-RPC message, not a schema-derived body.
    assert schema['paths']['/mcp']['post']['requestBody']['content']['application/json']['example']['method'] == 'tools/list'
    assert 'requestBody' not in schema['paths']['/mcp']['get']
