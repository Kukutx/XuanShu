"""Malformed/ambiguous JSON is rejected, never returned as an HTTP 500."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from app.json_safety import strict_json_loads
from app.main import app


@pytest.mark.parametrize('bad', [
    '{"id":NaN}', '{"id":Infinity}', '{"id":-Infinity}',
    '{"longitude":1e999}', '{"longitude":-1e999}',
    '{"id":1,"id":2}', '{"a":{"b":1,"b":2}}',
    '{"id":"\\ud800"}',
])
def test_reject_nonfinite_or_duplicate_keys(bad):
    with pytest.raises(ValueError):
        strict_json_loads(bad)


def test_valid_finite_values_and_strings_named_nan():
    assert strict_json_loads('{"a":"NaN","b":1e3,"c":null}') == {'a': 'NaN', 'b': 1000, 'c': None}


@pytest.mark.parametrize('bad', ['NaN', 'Infinity', '-Infinity', '1e999', '"NaN"'])
def test_jsonrpc_request_id_never_crashes_http(bad):
    request = '{"jsonrpc":"2.0","id":' + bad + ',"method":"tools/list"}'
    headers = {'Content-Type': 'application/json',
               'MCP-Protocol-Version': '2026-07-28', 'Mcp-Method': 'ping',
               'Accept': 'application/json, text/event-stream'}
    response = TestClient(app, raise_server_exceptions=False).post('/mcp',content=request,headers=headers)
    assert response.status_code == 400
    assert response.json()['error']['code'] in (-32700, -32020)


@pytest.mark.parametrize('body', [
    '{"birth_datetime":"2024-02-10T12:00","longitude":NaN}',
    '{"birth_datetime":"2024-02-10T12:00","longitude":1e999}',
    '{"birth_datetime":"2024-02-10T12:00","birth_datetime":"2024-02-11T12:00"}',
    '{"birth_datetime":"2024-02-10T12:00","gender":"male","gender":"female"}',
    '[' * 1100 + ']' * 1100,
    '{"birth_datetime":"\\ud800"}',
])
def test_rest_malformed_json_is_400_not_500(body):
    c = TestClient(app, raise_server_exceptions=False)
    response = c.post('/api/bazi',content=body,headers={'Content-Type':'application/json'})
    assert response.status_code == 400, response.text


def test_mcp_valid_json_is_unchanged():
    c = TestClient(app)
    result = c.post('/mcp',json={'jsonrpc':'2.0','id':1,'method':'tools/list'})
    assert result.status_code == 200
    assert len(result.json()['result']['tools']) == 28


def test_stdio_uses_same_json_rules():
    source = '\n'.join([
        '{"jsonrpc":"2.0","id":NaN,"method":"tools/list"}',
        '{"jsonrpc":"2.0","id":1,"method":"tools/list"}',
        '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"a":1,"a":2}}',
    ]) + '\n'
    result = subprocess.run([sys.executable,'-m','app.stdio'],input=source,text=True,
                            capture_output=True,check=True,timeout=15)
    responses = [json.loads(line) for line in result.stdout.splitlines()]
    assert [r.get('error',{}).get('code') for r in responses] == [-32700, None, -32700]
    assert responses[1]['id'] == 1
    assert not result.stderr
