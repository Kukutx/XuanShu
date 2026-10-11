#!/usr/bin/env python3
"""Boot a real loopback Uvicorn process and smoke REST, static UI, and MCP.

Requires only production dependencies. Proves real socket HTTP behavior, not
remote internet, HTTPS, Docker or a third-party MCP client installation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
VERSION = '2026-07-28'
META = {'io.modelcontextprotocol/protocolVersion': VERSION,
        'io.modelcontextprotocol/clientCapabilities': {}}
OPENER = build_opener(ProxyHandler({}))
REQUEST_COUNT = 0


def request(base: str, path: str, payload: dict | None = None, headers: dict | None = None):
    global REQUEST_COUNT
    REQUEST_COUNT += 1
    data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    request_ = Request(base + path, data=data, headers={
        **({'Content-Type': 'application/json'} if data is not None else {}),
        **(headers or {})}, method='POST' if data is not None else 'GET')
    try:
        with OPENER.open(request_, timeout=5) as response:
            body = response.read()
            return response.status, json.loads(body) if 'json' in response.headers.get('Content-Type','') else body
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def main():
    with socket.socket() as available:
        available.bind(('127.0.0.1', 0))
        port = available.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    env = dict(os.environ)
    for key in ('MCP_BEARER_TOKEN', 'DEPLOYMENT_MODE', 'ASTRO_ALLOWED_HOSTS', 'MCP_ALLOWED_ORIGINS'):
        env.pop(key, None)
    args = [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
            '--port', str(port), '--log-level', 'warning', '--no-access-log']
    server = subprocess.Popen(args, cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
                              stderr=subprocess.PIPE, text=True)
    try:
        for _ in range(80):
            if server.poll() is not None:
                raise RuntimeError(f'uvicorn exited early: {server.stderr.read()}')
            try:
                status, ready = request(base, '/health')
                if status == 200:
                    break
            except (URLError, ConnectionError):
                time.sleep(.1)
        else:
            raise RuntimeError('Timed out waiting for HTTP /health')
        assert ready['status'] == 'ok' and ready['version'] == '0.1.0', ready
        assert request(base, '/')[0] == 200
        assert request(base, '/static/app.js')[0] == 200
        # Browsers served on non-default ports must work with their actual
        # same-origin headers. A different port is *not* equivalent origin.
        with_origin = {'Origin': base}
        status, same_origin = request(base, '/api/bazi',
            {'birth_datetime':'2000-08-16T04:00'}, with_origin)
        assert status == 200 and same_origin['pillars']['day']['text']=='丙午', same_origin
        # Previously non-finite JSON was accepted by Python's json parser and
        # could crash FastAPI/Pydantic response serialization with HTTP 500.
        status, rejected = request(base, '/api/bazi',
            {'birth_datetime':'2024-02-10T12:00','longitude':float('nan')})
        assert status == 400 and 'Invalid JSON' in rejected['detail'], rejected
        status, wrong_port = request(base, '/api/bazi',
            {'birth_datetime':'2000-08-16T04:00'}, {'Origin':'http://127.0.0.1:8000'})
        if base != 'http://127.0.0.1:8000':
            assert status == 403, wrong_port
        sample = {'birth_datetime': '2024-03-12T12:00', 'timezone': 'Asia/Shanghai'}
        status, normal = request(base, '/api/quality-audit', {'birth': sample})
        assert status == 200 and normal['review_needed'] is False, normal
        status, future = request(base, '/api/quality-audit', {'birth': {
            **sample, 'birth_datetime': '2057-09-28T12:00'}})
        assert status == 200 and any(f['code'] == 'published_new_moon_uncertainty' for f in future['flags']), future
        status, report = request(base, '/api/report', {'birth': sample})
        assert status == 200 and report['quality_audit']['review_needed'] is False, report
        # New traceable deep analysis from actual HTTP REST, no browser bridge.
        deep_payload={'birth': {'birth_datetime':'2024-02-07T12:00'},
                      'focus_palace':'官禄宫','lunar_year':2026}
        status, deep = request(base,'/api/deep-review',deep_payload)
        assert status==200 and deep['system']=='xuanshu-deep-evidence-review',deep
        assert deep['calendar_year_consistent'] is False and all(c['passed'] for c in deep['checks']),deep
        status, full_report = request(base, '/api/report', {'birth': sample, 'include_deep_evidence': True})
        assert status==200 and full_report['deep_evidence'] is not None,full_report
        status, denied = request(base, '/api/deep-review', {**deep_payload,'focus_palace':'invalid'})
        assert status==422,denied
        # 开发阶段 hour-Qimen: real TCP REST endpoint (not TestClient).
        qimen_payload={'moment':{'birth_datetime':'2024-06-15T14:30','timezone':'Asia/Shanghai'}}
        status,qimen=request(base,'/api/qimen',qimen_payload)
        assert status==200 and qimen['solar_term']=='芒种' and len(qimen['palaces'])==9,qimen
        # New first-class 开发阶段 calculation workflows: HTTP REST + modern MCP parity.
        sample_birth = {'birth_datetime':'2000-08-16T04:00','gender':'male'}
        dayun_payload = {'birth':sample_birth,'periods':3}
        status, dayun = request(base, '/api/dayun', dayun_payload)
        assert status == 200 and [x['pillar'] for x in dayun['periods']] == ['乙酉','丙戌','丁亥'], dayun
        status, invalid_dayun = request(base, '/api/dayun', {'birth':{'birth_datetime':'2000-08-16T04:00'}})
        assert status == 422, invalid_dayun
        boundary_payload={'birth':{'birth_datetime':'2000-08-16T00:58'},'uncertainty_minutes':8}
        status, boundaries = request(base, '/api/birth-boundaries', boundary_payload)
        assert status == 200 and len(boundaries['boundaries']) == 1, boundaries
        status, report_plus = request(base, '/api/report', {'birth':sample_birth,
            'include_dayun': True,'birth_boundary_minutes':8})
        assert status == 200 and report_plus['dayun']['periods'][0]['pillar']=='乙酉' and report_plus['birth_boundaries']['segments'], report_plus
        status, officer_days = request(base, '/api/day-officers', {'start_date':'2026-10-15','days':3})
        assert status == 200 and officer_days['days'][0]['officer'] == '建', officer_days
        status, timeline = request(base, '/api/annual-timeline', {'birth':sample,'start_lunar_year':2025,'years':3})
        assert status == 200 and len(timeline['entries']) == 3, timeline
        matrix = {'question':'选择实现方案','criteria':[{'name':'可靠性','weight':3}],
                  'options':[{'name':'方案甲','ratings':{'可靠性':4}}, {'name':'方案乙','ratings':{'可靠性':2}}]}
        status, choice = request(base, '/api/decision-matrix', matrix)
        assert status == 200 and choice['ranked_options'][0]['name'] == '方案甲', choice
        status, invalid_choice = request(base, '/api/decision-matrix', {**matrix,'question':' '})
        assert status == 422, invalid_choice
        status, invalid = request(base, '/api/quality-audit', {'birth': sample, 'boundary_window_minutes': 0})
        assert status == 422 and isinstance(invalid['detail'], list), invalid
        status, serverinfo = request(base, '/mcp', {
            'jsonrpc': '2.0', 'id': 1, 'method': 'server/discover', 'params': {'_meta': META}},
            {'MCP-Protocol-Version': VERSION, 'Mcp-Method': 'server/discover',
             'Accept': 'application/json, text/event-stream'})
        assert status == 200 and serverinfo['result']['resultType'] == 'complete', serverinfo
        status, tools = request(base, '/mcp', {
            'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {'_meta': META}},
            {'MCP-Protocol-Version': VERSION, 'Mcp-Method': 'tools/list',
             'Accept': 'application/json, text/event-stream'})
        assert status == 200 and len(tools['result']['tools']) == 27, tools
        status, rpc_choice = request(base, '/mcp', {
            'jsonrpc':'2.0','id':4,'method':'tools/call',
            'params':{'name':'decision_matrix','arguments':matrix,'_meta':META}},
            {'MCP-Protocol-Version':VERSION,'Mcp-Method':'tools/call',
             'Mcp-Name':'decision_matrix','Accept':'application/json, text/event-stream'})
        assert status == 200 and rpc_choice['result']['structuredContent'] == choice, rpc_choice
        status, rpc_dayun = request(base, '/mcp', {
            'jsonrpc':'2.0','id':5,'method':'tools/call',
            'params':{'name':'bazi_dayun','arguments':dayun_payload,'_meta':META}},
            {'MCP-Protocol-Version':VERSION,'Mcp-Method':'tools/call',
             'Mcp-Name':'bazi_dayun','Accept':'application/json, text/event-stream'})
        assert status == 200 and rpc_dayun['result']['structuredContent']==dayun, rpc_dayun
        status, rpc_qimen = request(base, '/mcp', {
            'jsonrpc':'2.0','id':6,'method':'tools/call',
            'params':{'name':'qimen_hour_chart','arguments':qimen_payload,'_meta':META}},
            {'MCP-Protocol-Version':VERSION,'Mcp-Method':'tools/call',
             'Mcp-Name':'qimen_hour_chart','Accept':'application/json, text/event-stream'})
        assert status==200 and rpc_qimen['result']['structuredContent']==qimen,rpc_qimen
        status, rpc_deep = request(base, '/mcp', {
            'jsonrpc':'2.0','id':25,'method':'tools/call',
            'params':{'name':'deep_evidence_review','arguments':deep_payload,'_meta':META}},
            {'MCP-Protocol-Version':VERSION,'Mcp-Method':'tools/call',
             'Mcp-Name':'deep_evidence_review','Accept':'application/json, text/event-stream'})
        assert status==200 and rpc_deep['result']['structuredContent']==deep,rpc_deep
        # Real executed consultation: REST and modern MCP calculate identical evidence.
        consult_payload={'question':'2027年事业发展方向', 'birth':sample_birth}
        status, consultation = request(base, '/api/consultation', consult_payload)
        assert status==200 and consultation['intent']=='career' and consultation['status']=='completed', consultation
        assert 'annual_transformations' in consultation['tool_results'] and len(consultation['tool_trace'])>=3
        status, rpc_consult = request(base, '/mcp', {
            'jsonrpc':'2.0','id':28,'method':'tools/call',
            'params':{'name':'consultation_execute','arguments':consult_payload,'_meta':META}},
            {'MCP-Protocol-Version':VERSION,'Mcp-Method':'tools/call',
             'Mcp-Name':'consultation_execute','Accept':'application/json, text/event-stream'})
        assert status==200 and rpc_consult['result']['structuredContent']==consultation,rpc_consult
        status, missing_consult = request(base, '/api/consultation', {'question':'查查我的本命'})
        assert status==200 and missing_consult['status']=='needs_input' and not missing_consult['tool_trace']
        status, bad_consult = request(base, '/api/consultation', {'question':' '})
        assert status==422, bad_consult
        # Consultation coordinator prompt is available through actual network MCP.
        status, guided = request(base, '/mcp', {
            'jsonrpc':'2.0','id':27,'method':'prompts/get',
            'params':{'name':'prepare-report', 'arguments':{'focus':'明年职业选择'}, '_meta':META}},
            {'MCP-Protocol-Version':VERSION,'Mcp-Method':'prompts/get',
             'Mcp-Name':'prepare-report','Accept':'application/json, text/event-stream'})
        assert status==200 and '问题驱动' in guided['result']['messages'][0]['content']['text'],guided
        status, rules = request(base, '/mcp', {
            'jsonrpc':'2.0','id':26,'method':'resources/read',
            'params':{'uri':'astro://rules/evidence','_meta':META}},
            {'MCP-Protocol-Version':VERSION,'Mcp-Method':'resources/read',
             'Mcp-Name':'astro://rules/evidence','Accept':'application/json, text/event-stream'})
        assert status==200 and '深度证据分析' in rules['result']['contents'][0]['text'],rules
        # Explicit professional provider: no silent substitution with the partial chart.
        status, pro = request(base, '/api/ziwei-professional',
            {'birth': {'birth_datetime':'2000-08-16T04:00', 'gender':'female'}, 'target_date':'2024-02-10'})
        assert status in (200,422) and (status == 200 or 'Optional local provider unavailable' in str(pro)), pro
        # Reference comparison audits all provided fields, no claims about fields absent.
        ref_body={'moment':{'birth_datetime':'2024-06-15T14:30'},
                  'reference_source':'independently transcribed reference fixture',
                  'reference_school':'时家拆补转盘','root_fields':{'solar_term':'芒种'}}
        status, comparison=request(base,'/api/qimen-reference-audit',ref_body)
        assert status==200 and comparison['compared']==1 and comparison['matching']==1,comparison
        # MCP skill extension is exposed over actual TCP and uses digest metadata.
        status, skills = request(base, '/mcp', {
            'jsonrpc':'2.0','id':20,'method':'skills/list','params':{'_meta':META}},
            {'MCP-Protocol-Version':VERSION,'Mcp-Method':'skills/list',
             'Accept':'application/json, text/event-stream'})
        assert status==200 and len(skills['result']['skills'])==2,skills
        uri=skills['result']['skills'][0]['uri']
        status, skill = request(base, '/mcp', {
            'jsonrpc':'2.0','id':21,'method':'skills/get','params':{'uri':uri,'_meta':META}},
            {'MCP-Protocol-Version':VERSION,'Mcp-Method':'skills/get',
             'Accept':'application/json, text/event-stream'})
        assert status==200 and skill['result']['skill']['uri']==uri,skill
        status, missing = request(base, '/mcp', {
            'jsonrpc': '2.0', 'id': 3, 'method': 'tools/list', 'params': {'_meta': {
                'io.modelcontextprotocol/protocolVersion': VERSION}}},
            {'MCP-Protocol-Version': VERSION, 'Mcp-Method': 'tools/list',
             'Accept': 'application/json, text/event-stream'})
        assert status == 400 and missing['error']['code'] == -32602, missing
        print(f'PASS: live loopback Uvicorn REST + static UI + 2026 MCP, {REQUEST_COUNT} HTTP requests including health probes at {base} (no public HTTPS)')
    finally:
        server.terminate()
        try:
            server.wait(timeout=4)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=4)


if __name__ == '__main__':
    main()
