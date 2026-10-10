"""Check OpenAI static skill import integrity without claiming live plugin install."""
import hashlib
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.mcp import process_rpc


def rpc(method, params=None):
    return process_rpc({'jsonrpc':'2.0','id':1,'method':method,'params': params or {}})


def test_advertises_skills_in_both_protocols():
    init = rpc('initialize', {'protocolVersion':'2025-11-25'})['result']
    assert 'io.modelcontextprotocol/skills' in init['capabilities']['extensions']
    caps = {'io.modelcontextprotocol/protocolVersion':'2026-07-28',
            'io.modelcontextprotocol/clientCapabilities':{}}
    discovery = rpc('server/discover', {'_meta':caps})['result']
    assert 'io.modelcontextprotocol/skills' in discovery['capabilities']['extensions']


def test_paginated_catalog_sha256_and_exact_frontmatter():
    cursor = None
    discovered=[]
    for page in range(3):
        result=rpc('skills/list', {} if cursor is None else {'cursor':cursor})['result']
        discovered.extend(result['skills'])
        cursor=result.get('nextCursor')
        assert len(result['skills']) <= 2
    assert cursor is None and len(discovered)==5
    assert len({d['uri'] for d in discovered}) == 5
    for entry in discovered:
        front=entry['frontmatter']
        assert front['name'] == entry['uri'].split('/')[-2]
        assert front['description']
        details=rpc('skills/get', {'uri':entry['uri']})['result']['skill']
        assert details == entry
        for resource in entry['resources']:
            body=rpc('resources/read',{'uri':resource['uri']})['result']['contents']
            assert len(body)==1 and body[0]['uri']==resource['uri']
            digest=hashlib.sha256(body[0]['text'].encode('utf-8')).hexdigest()
            assert resource['digest'] == 'sha256:'+digest

@pytest.mark.parametrize('method,params',[('skills/list',{'cursor':'bogus'}),
    ('skills/list',{'cursor':1}),('skills/get',{}),
    ('skills/get',{'uri':'skill://xuanshu/../private/SKILL.md'}),
    ('resources/read',{'uri':'skill://xuanshu/nonexistent/SKILL.md'})])
def test_no_path_traversal_or_invalid_cursor(method,params):
    assert rpc(method,params)['error']['code']==-32602


def test_skill_extension_real_http():
    with TestClient(app) as client:
        r=client.post('/mcp',json={'jsonrpc':'2.0','id':1,'method':'skills/list','params':{}})
    assert r.status_code==200 and len(r.json()['result']['skills'])==2
