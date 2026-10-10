"""Regression for malformed MCP requests, exact local origin, and Docker ingress.

All sample IP addresses are documentation or private gateway ranges; none
represent an actual publicly reachable service.
"""
from __future__ import annotations

import os
import re
import stat
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.mcp import process_rpc
from scripts.init_docker_local import initialize

ROOT = Path(__file__).resolve().parents[1]


def _rpc(method, params=None):
    return {'jsonrpc': '2.0', 'id': 18, 'method': method, 'params': params or {}}


@pytest.mark.parametrize('payload,code', [
    (_rpc('tools/list', {'_meta': {'io.modelcontextprotocol/protocolVersion': []}}), -32602),
    (_rpc('server/discover', {'_meta': {'io.modelcontextprotocol/protocolVersion': {'nested': 1}}}), -32602),
    (_rpc('initialize', {'protocolVersion': []}), -32602),
    (_rpc('initialize', {'protocolVersion': {'foo': 'bar'}}), -32602),
    (_rpc('resources/read', {'uri': {}}), -32602),
    (_rpc('ping', {'_meta': []}), -32602),
    ({'jsonrpc': '2.0', 'id': ['invalid'], 'method': 'tools/list'}, -32600),
])
def test_malformed_mcp_request_never_crashes(payload, code):
    result = process_rpc(payload)
    assert result['error']['code'] == code
    response = TestClient(app).post('/mcp', json=payload)
    assert response.status_code != 500
    assert response.json()['error']['code'] == code


@pytest.mark.parametrize('bad', [[], [3], 'not-an-object', False, 123])
def test_mcp_params_must_be_object(bad):
    payload = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list', 'params': bad}
    result = process_rpc(payload)
    assert result['error']['code'] == -32602
    assert TestClient(app).post('/mcp', json=payload).json()['error']['code'] == -32602


def test_mcp_rejects_modern_unhashable_version_over_http():
    payload = _rpc('tools/list', {'_meta': {'io.modelcontextprotocol/protocolVersion': []}})
    result = TestClient(app).post('/mcp', json=payload, headers={
        'MCP-Protocol-Version': '2026-07-28',
        'Mcp-Method': 'tools/list',
        'Accept': 'application/json, text/event-stream',
    })
    assert result.status_code == 400
    assert 'error' in result.json()


def test_local_same_origin_port_is_not_hard_coded(monkeypatch):
    monkeypatch.delenv('DEPLOYMENT_MODE', raising=False)
    monkeypatch.delenv('MCP_ALLOWED_ORIGINS', raising=False)
    c = TestClient(app, base_url='http://127.0.0.1:8769', client=('127.0.0.1', 56123))
    headers = {'Origin': 'http://127.0.0.1:8769'}
    assert c.post('/api/bazi', headers=headers, json={'birth_datetime': '2000-08-16T04:00'}).status_code == 200
    assert c.post('/mcp', headers=headers, json=_rpc('ping')).status_code == 200
    for different_origin in ('http://127.0.0.1:8000', 'http://localhost:8769',
                             'https://127.0.0.1:8769', 'http://evil.example',
                             'http://127.0.0.1:8769.attacker.example'):
        assert c.post('/api/bazi', headers={'Origin': different_origin},
                      json={'birth_datetime': '2000-08-16T04:00'}).status_code == 403
        assert c.post('/mcp', headers={'Origin': different_origin}, json=_rpc('ping')).status_code == 403


def test_docker_bridge_peer_requires_auth_and_known_host(monkeypatch):
    monkeypatch.setenv('DEPLOYMENT_MODE', 'public')
    monkeypatch.setenv('MCP_BEARER_TOKEN', 'fixture-only-random-very-long-docker-secret')
    monkeypatch.setenv('ASTRO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
    monkeypatch.setenv('MCP_ALLOWED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000')
    for key in ('ASTRO_OAUTH_ISSUER','ASTRO_OAUTH_JWKS_URL','ASTRO_OAUTH_AUDIENCE','ASTRO_PUBLIC_BASE_URL'):
        monkeypatch.delenv(key, raising=False)
    bridge = TestClient(app, base_url='http://127.0.0.1:8000', client=('172.18.0.1', 50000))
    payload = {'birth_datetime': '2000-08-16T04:00'}
    assert bridge.post('/api/bazi', json=payload).status_code == 401
    assert bridge.post('/api/bazi', json=payload, headers={'Authorization': 'Bearer wrong'}).status_code == 401
    assert bridge.post('/api/bazi', json=payload, headers={
        'Authorization': 'Bearer fixture-only-random-very-long-docker-secret',
        'Origin': 'http://127.0.0.1:8000'}).status_code == 200
    assert bridge.post('/api/bazi', json=payload, headers={
        'Authorization': 'Bearer fixture-only-random-very-long-docker-secret',
        'Origin': 'https://evil.example'}).status_code == 403
    assert bridge.get('/health', headers={'Host': 'forged.example.com'}).status_code == 400


def test_docker_local_bootstrap_is_exclusive_and_private(tmp_path):
    filename = initialize(tmp_path)
    assert filename.name == '.env'
    data = filename.read_text(encoding='utf-8')
    found = re.search(r'^MCP_BEARER_TOKEN=(\S+)$', data, re.MULTILINE)
    assert found and len(found.group(1)) >= 48
    if os.name == 'posix':
        assert stat.S_IMODE(filename.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        initialize(tmp_path)
    assert data == filename.read_text(encoding='utf-8')


def test_docker_compose_never_anonymously_exposes_bridge():
    compose = (ROOT / 'compose.yaml').read_text(encoding='utf-8')
    assert '127.0.0.1:8000:8000' in compose
    assert 'DEPLOYMENT_MODE: public' in compose
    assert 'MCP_BEARER_TOKEN: ${MCP_BEARER_TOKEN:?' in compose
    assert 'ASTRO_ALLOWED_HOSTS: localhost,127.0.0.1' in compose
    assert 'env_file:' not in compose
