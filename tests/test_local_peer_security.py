"""Local mode must be actually loopback-only, not just Host-header-only."""
from fastapi.testclient import TestClient

from app.main import app


def test_remote_peer_must_not_access_unauthenticated_local_api(monkeypatch):
    monkeypatch.delenv('DEPLOYMENT_MODE',raising=False)
    monkeypatch.delenv('MCP_BEARER_TOKEN',raising=False)
    for name in ('ASTRO_OAUTH_ISSUER','ASTRO_OAUTH_JWKS_URL','ASTRO_OAUTH_AUDIENCE','ASTRO_PUBLIC_BASE_URL'):
        monkeypatch.delenv(name,raising=False)
    # A remote client can forge the Host header as localhost; the ASGI socket
    # peer remains non-loopback, so middleware must reject every entrypoint.
    remote=TestClient(app,base_url='http://127.0.0.1:8000',client=('198.51.100.7',60001))
    for path in ('/health','/','/static/app.js'):
        response=remote.get(path,headers={'Host':'127.0.0.1:8000'})
        assert response.status_code == 403, (path,response.text)
    for path,payload in (
        ('/api/bazi', {'birth_datetime':'2000-08-16T04:00'}),
        ('/api/qimen', {'moment':{'birth_datetime':'2000-08-16T04:00'}}),
        ('/mcp', {'jsonrpc':'2.0','id':1,'method':'tools/list'}),
    ):
        response=remote.post(path,json=payload,headers={'Host':'127.0.0.1:8000'})
        assert response.status_code == 403, (path,response.text)


def test_loopback_ipv4_ipv6_and_test_client_still_work(monkeypatch):
    monkeypatch.delenv('DEPLOYMENT_MODE',raising=False)
    for peer in ('127.0.0.1','::1','testclient'):
        c=TestClient(app,base_url='http://127.0.0.1:8000',client=(peer,50000))
        r=c.get('/health')
        assert r.status_code == 200, (peer,r.text)


def test_public_mode_allows_remote_peer_only_with_configured_auth(monkeypatch):
    monkeypatch.setenv('DEPLOYMENT_MODE','public')
    monkeypatch.setenv('ASTRO_ALLOWED_HOSTS','astro.example.com')
    monkeypatch.setenv('MCP_BEARER_TOKEN','test-token-with-adequate-length-0123456789')
    for name in ('ASTRO_OAUTH_ISSUER','ASTRO_OAUTH_JWKS_URL','ASTRO_OAUTH_AUDIENCE','ASTRO_PUBLIC_BASE_URL'):
        monkeypatch.delenv(name,raising=False)
    c=TestClient(app,base_url='https://astro.example.com',client=('198.51.100.7',60001))
    assert c.get('/health').status_code==200
    assert c.post('/api/qimen',json={'moment':{'birth_datetime':'2000-08-16T04:00'}}).status_code==401
    assert c.post('/api/qimen',json={'moment':{'birth_datetime':'2000-08-16T04:00'}},
                  headers={'Authorization':'Bearer test-token-with-adequate-length-0123456789'}).status_code==200
