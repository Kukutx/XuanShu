"""Solar-term, bureau, transport parity and OAuth verification regression."""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.astronomy import from_jd, solar_term_jd
from app.engines import BirthInput
from app.main import app
from app.mcp import call_tool, process_rpc
from app.oauth_resource import config, token_ok, jwks_client
from app.qimen import QimenRequest, qimen_chart, RING, EARTH_STEMS, BUREAU_TABLE, GODS, BASE_STARS, BASE_DOORS

client=TestClient(app)


def _req(time: str, tz='Asia/Shanghai'):
    return QimenRequest(moment=BirthInput(birth_datetime=time,timezone=tz))


@pytest.mark.parametrize('time,term,dun,bureau,yuan,day,hour', [
    ('2024-06-15T14:30','芒种','阳遁',6,'上元','庚戌','癸未'),
    ('2024-12-22T14:30','冬至','阳遁',4,'下元','庚申','癸未'),
    ('2000-08-16T04:00','立秋','阴遁',8,'下元','丙午','庚寅'),
])
def test_qimen_reproducible_rule_fixtures(time,term,dun,bureau,yuan,day,hour):
    r=qimen_chart(_req(time))
    assert [r[x] for x in ('solar_term','dun','bureau','yuan','day_pillar','hour_pillar')]==[term,dun,bureau,yuan,day,hour]
    assert r['method'].startswith('时家拆补')
    assert r['system'] == _req(time).system
    assert len(r['palaces'])==9
    assert set(p['earth_stem'] for p in r['palaces'])==set(EARTH_STEMS)
    assert set(p['heaven_stem'] for p in r['palaces'])==set(EARTH_STEMS)
    assert {p['star'] for p in r['palaces']}==set(BASE_STARS.values())
    assert {p['door'] for p in r['palaces'] if p['door']}==set(BASE_DOORS.values())
    assert {p['deity'] for p in r['palaces'] if p['deity']}==set(GODS)
    assert r['zhi_fu_star']==r['palaces'][r['zhi_fu_palace']-1]['star']
    assert r['zhi_shi_door']==r['palaces'][r['zhi_shi_palace']-1]['door']


# Independent public cross-check (MIT repo qfdk/qimen, test/paipan.test.js,
# 2026 multi-chart fixtures): compare the six fields that both engines expose.
# These are public *project benchmarks*, not certified astronomical ephemerides,
# and the legacy app uses a different solar-term-at-day boundary convention.
@pytest.mark.parametrize('time,dun,bureau,star,zhi_fu,door,zhi_shi', [
    ('2026-03-21T12:00','阳遁',3,'天冲',2,'伤门',9),
    ('2026-06-09T12:00','阳遁',3,'天冲',2,'伤门',9),
    ('2026-07-15T12:00','阴遁',5,'天辅',1,'杜门',2),
    ('2026-09-23T12:00','阴遁',1,'天英',6,'景门',1),
    ('2026-12-08T12:00','阴遁',7,'天辅',4,'杜门',4),
])
def test_qimen_independent_public_chart_reference(time,dun,bureau,star,zhi_fu,door,zhi_shi):
    r=qimen_chart(_req(time))
    assert (r['dun'],r['bureau'],r['zhi_fu_star'],r['zhi_fu_palace'],
            r['zhi_shi_door'],r['zhi_shi_palace']) == (dun,bureau,star,zhi_fu,door,zhi_shi)


def test_qimen_real_jie_instant_not_whole_calendar_day():
    # Public benchmark labels 2026-06-05 16:52 as 芒种 because its software
    # uses the entire date; astronomical 芒种 occurs at roughly 23:48 UTC+8.
    # This project intentionally uses the *actual astronomical instant*.
    x=qimen_chart(_req('2026-06-05T16:52'))
    y=qimen_chart(_req('2026-06-06T00:00'))
    assert x['solar_term']=='小满' and y['solar_term']=='芒种'


@pytest.mark.parametrize('name,table',list(BUREAU_TABLE.items()))
def test_every_solar_term_has_a_valid_bureau(name,table):
    dun,nums=table
    assert dun in ('阳','阴') and len(nums)==3 and set(nums).issubset(set(range(1,10)))


def test_qimen_bureau_switches_at_solar_instant():
    boundary=from_jd(solar_term_jd(2024,90))
    left=qimen_chart(_req((boundary-timedelta(seconds=2)).astimezone(timezone(timedelta(hours=8))).isoformat()))
    right=qimen_chart(_req((boundary+timedelta(seconds=2)).astimezone(timezone(timedelta(hours=8))).isoformat()))
    assert left['solar_term']=='芒种' and right['solar_term']=='夏至'
    assert left['dun']=='阳遁' and right['dun']=='阴遁'


def test_qimen_parity_mcp_rest_cli():
    body={'moment':{'birth_datetime':'2024-06-15T14:30'}}
    r=client.post('/api/qimen',json=body)
    assert r.status_code==200, r.text
    assert r.json()==call_tool('qimen_hour_chart',body)
    rpc=process_rpc({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'qimen_hour_chart','arguments':body}})
    assert rpc['result']['structuredContent']==r.json()
    assert client.post('/api/qimen',json={'moment':{'birth_datetime':'invalid'}}).status_code==422
    assert client.post('/api/qimen',json={**body, 'method':'unknown'}).status_code==422


def _oauth_environment(monkeypatch):
    monkeypatch.setenv('DEPLOYMENT_MODE','public')
    monkeypatch.setenv('ASTRO_ALLOWED_HOSTS','astro.example.com')
    monkeypatch.setenv('ASTRO_PUBLIC_BASE_URL','https://astro.example.com')
    monkeypatch.setenv('ASTRO_OAUTH_ISSUER','https://login.example.com')
    monkeypatch.setenv('ASTRO_OAUTH_JWKS_URL','https://login.example.com/keys')
    monkeypatch.setenv('ASTRO_OAUTH_AUDIENCE','https://astro.example.com/mcp')
    monkeypatch.delenv('MCP_BEARER_TOKEN',raising=False)
    monkeypatch.delenv('MCP_ALLOWED_ORIGINS',raising=False)


def _jwk(private):
    numbers=private.public_key().public_numbers()
    def urlsafe(integer):
        data=integer.to_bytes((integer.bit_length()+7)//8,'big')
        return base64.urlsafe_b64encode(data).decode().rstrip('=')
    return {'kty':'RSA','kid':'k1','use':'sig','alg':'RS256','n':urlsafe(numbers.n),'e':urlsafe(numbers.e)}


def test_oauth_discovery_jwks_and_unauthorized(monkeypatch):
    from app import oauth_resource
    _oauth_environment(monkeypatch)
    private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    jwk=_jwk(private)
    oauth_resource.jwks_client.cache_clear()
    # Real PyJWT JWKS selection + RSA signature validation, with offline mock of the public issuer's HTTPS JWKS.
    monkeypatch.setattr(jwt.PyJWKClient,'fetch_data',lambda self:{'keys':[jwk]})
    monkeypatch.setenv('MCP_BEARER_TOKEN','dev-only-should-not-bypass-oauth')
    protected=TestClient(app,base_url='https://astro.example.com')
    discovery=protected.get('/.well-known/oauth-protected-resource/mcp')
    assert discovery.status_code==200
    assert discovery.json()['authorization_servers']==['https://login.example.com']
    assert discovery.json()['resource']=='https://astro.example.com/mcp'
    assert protected.get('/.well-known/oauth-protected-resource').status_code==200
    for path,data in [('/mcp',{'jsonrpc':'2.0','id':1,'method':'tools/list'}),('/api/qimen',{'moment':{'birth_datetime':'2000-08-16T04:00'}})]:
        response=protected.post(path,json=data)
        assert response.status_code==401
        assert 'resource_metadata="https://astro.example.com/.well-known/oauth-protected-resource/mcp"' in response.headers['WWW-Authenticate']
    assert protected.post('/mcp',json={'jsonrpc':'2.0','id':1,'method':'ping'},
                          headers={'Authorization':'Bearer dev-only-should-not-bypass-oauth'}).status_code==401

    now=int(datetime.now(tz=timezone.utc).timestamp())
    standard={'iss':'https://login.example.com','aud':'https://astro.example.com/mcp',
              'sub':'user-test','exp':now+3600,'scope':'astro:read'}
    def make(**changes):
        return jwt.encode({**standard,**changes},private,algorithm='RS256',headers={'kid':'k1'})
    valid=make()
    assert token_ok(valid)
    assert protected.post('/api/qimen',json={'moment':{'birth_datetime':'2000-08-16T04:00'}},
                          headers={'Authorization':'Bearer '+valid}).status_code==200
    assert protected.post('/mcp',json={'jsonrpc':'2.0','id':1,'method':'tools/list'},
                          headers={'Authorization':'Bearer '+valid}).status_code==200
    cases=[
        make(iss='https://untrusted.example.com'),make(aud='https://another.example.com/mcp'),
        make(exp=now-180),make(scope='other:read'),make(sub=''),
        jwt.encode(standard,rsa.generate_private_key(public_exponent=65537,key_size=2048),algorithm='RS256',headers={'kid':'k1'}),
        'bad-token',
    ]
    for token in cases:
        assert not token_ok(token)
        assert protected.post('/mcp',json={'jsonrpc':'2.0','id':1,'method':'ping'},
                              headers={'Authorization':'Bearer '+token}).status_code==401
    oauth_resource.jwks_client.cache_clear()


@pytest.mark.parametrize('key,value', [
    ('ASTRO_OAUTH_ISSUER','http://login.example.com'),
    ('ASTRO_OAUTH_JWKS_URL','https://evil.example/keys'),
    ('ASTRO_OAUTH_AUDIENCE','https://other.example.com/mcp'),
    ('ASTRO_PUBLIC_BASE_URL','https://astro.example.com/foo'),
    ('ASTRO_OAUTH_JWKS_URL','https://login.example.com:bad/keys'),
    ('ASTRO_OAUTH_JWKS_URL','https://login.example.com:8443/keys'),
])
def test_oauth_config_fail_closed(monkeypatch,key,value):
    _oauth_environment(monkeypatch)
    monkeypatch.setenv(key,value)
    with pytest.raises(ValueError):
        config()
    res=TestClient(app,base_url='https://astro.example.com').get('/health')
    assert res.status_code==503


def test_oauth_not_enabled_by_default(monkeypatch):
    for key in ('ASTRO_OAUTH_ISSUER','ASTRO_OAUTH_JWKS_URL','ASTRO_OAUTH_AUDIENCE','ASTRO_PUBLIC_BASE_URL'):
        monkeypatch.delenv(key,raising=False)
    assert client.get('/.well-known/oauth-protected-resource').status_code==404
