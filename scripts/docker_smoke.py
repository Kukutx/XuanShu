#!/usr/bin/env python3
"""Verify authenticated Docker bridge traffic through host-loopback publishing.

Run AFTER docker compose up -d. This script does not create a container,
modify secrets, or contact remote services. It does not replace Docker engine
and TLS/proxy acceptance testing in a production deployment.
"""
from __future__ import annotations

import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
OPENER = build_opener(ProxyHandler({}))
BASE = 'http://127.0.0.1:8000'


def bearer_from_env():
    path = ROOT / '.env'
    if not path.is_file():
        raise RuntimeError('Run python scripts/init_docker_local.py first')
    tokens = [line.partition('=')[2].strip() for line in path.read_text(encoding='utf-8').splitlines()
              if line.startswith('MCP_BEARER_TOKEN=')]
    if len(tokens) != 1 or len(tokens[0]) < 32:
        raise RuntimeError('.env must contain one strong MCP_BEARER_TOKEN')
    return tokens[0]


def request(path: str, payload: dict | None = None, headers: dict | None = None):
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
    headers = {'Content-Type': 'application/json', **(headers or {})}
    outgoing = Request(BASE + path, data=data, headers=headers,
                       method='POST' if payload is not None else 'GET')
    try:
        with OPENER.open(outgoing, timeout=4) as response:
            content = response.read()
            return response.status, json.loads(content) if content and 'json' in response.headers.get('Content-Type', '') else content
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def main():
    secret = bearer_from_env()
    for _ in range(60):
        try:
            if request('/health')[0] == 200:
                break
        except (URLError, ConnectionError, TimeoutError):
            time.sleep(1)
    else:
        raise RuntimeError('Container did not become healthy on host 127.0.0.1:8000')
    birth = {'birth_datetime': '2000-08-16T04:00', 'timezone': 'Asia/Shanghai'}
    token = {'Authorization': 'Bearer ' + secret}
    assert request('/api/bazi', birth)[0] == 401
    assert request('/api/bazi', birth, {'Authorization': 'Bearer invalid'})[0] == 401
    status, bazi = request('/api/bazi', birth, {**token, 'Origin': BASE})
    assert status == 200 and bazi['pillars']['day']['text'] == '丙午'
    assert request('/api/bazi', birth, {**token, 'Origin': 'https://untrusted.example'})[0] == 403
    assert request('/api/bazi', birth, {**token, 'Host': 'fake.example'})[0] == 400
    assert request('/mcp', {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})[0] == 401
    status, mcp = request('/mcp', {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}, token)
    assert status == 200 and 'tools' in mcp['result']
    print('PASS: Docker loopback port, bridge auth, REST, MCP, Host/Origin denials (no remote HTTPS claims).')


if __name__ == '__main__':
    main()
