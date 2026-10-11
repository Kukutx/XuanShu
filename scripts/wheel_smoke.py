#!/usr/bin/env python3
"""Verify the *installed wheel* works outside the source checkout.

Runs in an isolated temporary directory using the current interpreter and
preinstalled production/test dependencies (build uses --no-build-isolation).
This catches missing runtime assets that source-only pytest cannot detect.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix='xuanshu-wheel-smoke-') as folder:
        temp = Path(folder)
        dist = temp / 'dist'
        dist.mkdir()
        subprocess.run([sys.executable, '-m', 'pip', 'wheel', str(ROOT),
                        '--no-build-isolation', '--no-deps', '-w', str(dist), '-q'],
                       check=True, cwd=temp)
        wheels = list(dist.glob('xuanshu-0.1.0-*.whl'))
        if len(wheels) != 1:
            raise RuntimeError('Missing frozen-version wheel')
        installed = temp / 'installed'
        subprocess.run([sys.executable, '-m', 'pip', 'install', str(wheels[0]),
                        '--no-deps', '--target', str(installed), '-q'],
                       check=True, cwd=temp)
        external = temp / 'elsewhere'
        external.mkdir()
        env = os.environ.copy()
        env['PYTHONPATH'] = str(installed)
        env['PYTHONNOUSERSITE'] = '1'
        script = r'''
import json
from pathlib import Path
from fastapi.testclient import TestClient
import app.main as app_module
from app.main import app
from app.mcp import process_rpc
from app.asset_paths import resource_root
assert Path(app_module.__file__).is_relative_to(Path(__import__('os').environ['PYTHONPATH']))
assets = resource_root()
assert '_resources' in str(assets), assets
assert (assets/'docs/research/FEATURES_AND_REFERENCES.md').is_file()
assert (assets/'docs/research/PRODUCT_BUSINESS_AUDIT.md').is_file()
assert (assets/'docs/research/CONSULTATION_WORKFLOW_SPEC.md').is_file()
assert 'six' in (assets/'skills/structured-dossier/SKILL.md').read_text(encoding='utf-8').lower()
assert (assets/'examples/DEEP_ANALYSIS_WALKTHROUGH.md').is_file()
assert (assets/'docs/rules/consultation.md').is_file()
assert (assets/'examples/deep-evidence-reference-2024-02-07.json').is_file()
assert 'input_parameters' in json.loads((assets/'examples/deep-evidence-reference-2024-02-07.json').read_text(encoding='utf-8'))
c = TestClient(app)
for path in ('/', '/static/app.js', '/static/style.css', '/static/vault.js', '/health', '/api/capabilities'):
    resp = c.get(path)
    assert resp.status_code == 200, (path, resp.text[:300])
assert c.get('/api/capabilities').json()['counts']['agent_skills'] == 18
payload = {'jsonrpc':'2.0','id':7,'method':'resources/read','params':{'uri':'astro://rules/qimen'}}
r = c.post('/mcp', json=payload)
assert r.status_code == 200 and '时家' in r.json()['result']['contents'][0]['text']
review = c.post('/api/deep-review',json={'birth':{'birth_datetime':'2000-08-16T04:00'}})
assert review.status_code == 200 and len(review.json()['references']) == 9
ref = c.post('/mcp',json={'jsonrpc':'2.0','id':9,'method':'resources/read','params':{'uri':'astro://rules/evidence'}})
assert ref.status_code == 200 and '证据分析' in ref.json()['result']['contents'][0]['text']
qimen = c.post('/api/qimen', json={'moment':{'birth_datetime':'2026-03-21T12:00'}})
assert qimen.status_code == 200 and len(qimen.json()['palaces']) == 9
consult = c.post('/api/consultation',json={'question':'2027年职业结构','birth':{'birth_datetime':'2000-08-16T04:00'}})
assert consult.status_code==200 and 'annual_transformations' in consult.json()['tool_results']
resource = c.post('/mcp', json={'jsonrpc':'2.0','id':15,'method':'resources/read','params':{'uri':'astro://rules/consultation'}})
assert resource.status_code==200 and '六类场景' in resource.json()['result']['contents'][0]['text']
print('Installed wheel Web/REST/MCP/resources/Skills/consultation: OK')
'''
        subprocess.run([sys.executable, '-c', script], check=True, cwd=external,
                       env=env, timeout=35)
        cli = subprocess.run([sys.executable, '-m', 'app.cli', 'tools'], cwd=external,
                             env=env, text=True, capture_output=True, timeout=20, check=True)
        assert len(json.loads(cli.stdout)['tools']) == 33
        line = json.dumps({'jsonrpc': '2.0', 'method': 'tools/list', 'id': 8}) + '\n'
        stdio = subprocess.run([sys.executable, '-m', 'app.stdio'], cwd=external,
                               env=env, input=line, text=True, capture_output=True,
                               timeout=20, check=True)
        assert len(json.loads(stdio.stdout)['result']['tools']) == 33
        assert not stdio.stderr
        print('PASS: isolated wheel installation, Web, REST, MCP HTTP+stdio, CLI, 18 Skills')


if __name__ == '__main__':
    main()
