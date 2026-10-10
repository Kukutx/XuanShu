#!/usr/bin/env python3
"""Smoke real browser-to-HTTP requests without a FastAPI in-process bridge."""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import ProxyHandler, build_opener
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--chromium', type=Path, required=True)
    args = p.parse_args()
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    env = os.environ.copy()
    for name in ('MCP_BEARER_TOKEN', 'DEPLOYMENT_MODE', 'ASTRO_ALLOWED_HOSTS', 'MCP_ALLOWED_ORIGINS'):
        env.pop(name, None)
    server = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
         '--port', str(port), '--log-level', 'warning'],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        opener = build_opener(ProxyHandler({}))
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError('Uvicorn quit before ready')
            try:
                with opener.open(url + '/health', timeout=2) as r:
                    if r.status == 200:
                        break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError('Uvicorn did not become ready')
        errors, responses = [], []
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=str(args.chromium), headless=True)
            try:
                desktop = browser.new_page(viewport={'width': 1440, 'height': 900})
                desktop.on('pageerror', lambda e: errors.append(str(e)))
                desktop.on('requestfailed', lambda r: errors.append(r.url))
                desktop.on('response', lambda r: responses.append((r.status, r.url))
                           if '/api/' in r.url else None)
                desktop.goto(url + '/', wait_until='networkidle')
                assert desktop.locator('.tab').count() == 22
                assert desktop.locator('.tab:visible').count() < 22
                # Ctrl+K and synonyms make the workbench discoverable.
                desktop.keyboard.press('Control+k')
                assert desktop.locator('#tool-search').evaluate('(el) => document.activeElement === el')
                desktop.locator('#tool-search').fill('MCP')
                assert desktop.locator('[data-tab="integration"]').is_visible()
                desktop.locator('[data-tab="integration"]').click()
                assert desktop.evaluate('location.hash') == '#tool=integration'
                desktop.reload(wait_until='networkidle')
                assert desktop.locator('[data-tab="integration"]').get_attribute('aria-selected') == 'true'
                desktop.locator('#tool-search').fill('')
                desktop.locator('#tool-toggle-all').click()
                desktop.locator('[data-tab="consult"]').click()
                desktop.locator('[data-tab="consult"]').focus()
                desktop.keyboard.press('End')
                assert desktop.locator('[data-tab="json"]').get_attribute('aria-selected') == 'true'
                desktop.keyboard.press('Home')
                assert desktop.locator('[data-tab="consult"]').get_attribute('aria-selected') == 'true'
                # Reset expanded navigation to preserve existing test assumptions.
                desktop.locator('#tool-toggle-all').click()
                desktop.locator('#tool-search').fill('四化')
                assert desktop.locator('[data-tab="transform"]').is_visible()
                desktop.locator('#tool-search').press('Escape')
                assert desktop.locator('#tool-search').input_value() == ''
                desktop.locator('#tool-toggle-all').click()
                assert desktop.locator('.tab:visible').count() == 22
                desktop.get_by_role('button',name='年度事业',exact=True).click()
                assert '事业' in desktop.locator('#consult-question').input_value()
                desktop.locator('#consult-question').fill('2027年职业选择')
                desktop.locator('#consult-run').click()
                desktop.get_by_text('需要补充', exact=False).first.wait_for()
                desktop.locator('#consult-use-birth').check()
                desktop.locator('#consult-run').click()
                desktop.get_by_text('annual_transformations', exact=False).first.wait_for()
                assert desktop.locator('#consult-copy-markdown').is_visible()
                desktop.context.grant_permissions(['clipboard-read','clipboard-write'], origin=url)
                desktop.locator('#consult-copy-markdown').click()
                assert desktop.locator('#consult-copy-markdown').text_content() == '已复制报告'
                assert len(desktop.evaluate('navigator.clipboard.readText()')) > 80
                desktop.locator('[data-tab="bazi"]').click()
                desktop.locator('#run-btn').click()
                desktop.locator('.pillar-stem').first.wait_for()
                assert desktop.locator('.pillar-stem').count() == 4
                assert desktop.locator('#stale-birth-warning').is_hidden()
                original_date=desktop.locator('#birth_datetime').input_value()
                desktop.locator('#birth_datetime').fill('2000-08-16T04:01')
                assert desktop.locator('#stale-birth-warning').is_visible()
                assert desktop.locator('#download-json').is_disabled()
                desktop.locator('#birth_datetime').fill(original_date)
                assert desktop.locator('#stale-birth-warning').is_hidden()
                assert desktop.locator('#download-json').is_enabled()
                desktop.locator('[data-tab="qimen"]').click()
                desktop.locator('#qimen-run').click()
                desktop.locator('.qimen-cell').first.wait_for()
                assert desktop.locator('.qimen-cell').count() == 9
                desktop.locator('[data-tab="professional"]').click()
                desktop.locator('#gender').select_option('female')
                desktop.locator('#professional-run').click()
                desktop.wait_for_function(
                    "() => document.querySelector('#result')?.textContent.includes('iztro-py')",
                    timeout=30000)
                desktop.locator('[data-tab="calendar"]').click()
                desktop.locator('#calendar-run').click()
                desktop.locator('#result tbody tr').first.wait_for()
                assert desktop.locator('#result tbody tr').count() == 14
                desktop.locator('[data-tab="integration"]').click()
                assert desktop.locator('#integration-copy').is_visible()
                assert any('mcpServers' in v for v in desktop.locator('#result pre').all_text_contents())
                mobile = browser.new_page(viewport={'width': 390, 'height': 844},
                                          is_mobile=True, has_touch=True)
                mobile.on('pageerror', lambda e: errors.append(str(e)))
                mobile.goto(url + '/', wait_until='networkidle')
                assert mobile.locator('#consult-question').is_visible()
                assert mobile.locator('#tool-search').is_visible()
                assert mobile.locator('.consult-shortcuts button').count() == 5
                # Qimen is usable without first generating the natal chart.
                # Its own result must also be marked stale if birth inputs change.
                standalone=browser.new_page(viewport={'width':1024,'height':768})
                standalone.on('pageerror', lambda e: errors.append(str(e)))
                standalone.goto(url + '/#tool=qimen', wait_until='networkidle')
                assert standalone.locator('[data-tab="qimen"]').get_attribute('aria-selected') == 'true'
                standalone.locator('#qimen-run').click()
                standalone.locator('.qimen-cell').first.wait_for()
                assert standalone.locator('#stale-birth-warning').is_hidden()
                standalone.locator('#birth_datetime').fill('2000-08-16T04:01')
                assert standalone.locator('#stale-birth-warning').is_visible()
                standalone.locator('#birth_datetime').fill('2000-08-16T04:00')
                assert standalone.locator('#stale-birth-warning').is_hidden()
            finally:
                browser.close()
        assert not errors, errors
        assert len(responses) >= 6, responses
        assert all(code == 200 for code, _ in responses), responses
        print(f'PASS: real Chrome-to-Uvicorn HTTP, {len(responses)} API requests, desktop/mobile')
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


if __name__ == '__main__':
    main()
