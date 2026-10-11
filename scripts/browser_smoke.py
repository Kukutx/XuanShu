#!/usr/bin/env python3
"""Optional real Chromium DOM interaction smoke with an in-process FastAPI bridge.

Avoids network navigation: some sandboxes block localhost/about:data navigation.
The frontend runs in *real Chromium*; each REST POST reaches the real FastAPI
TestClient. This does NOT validate a public-domain deployment, network CORS,
reverse proxy, OAuth, or browser-to-HTTP transport. Playwright+Chromium optional.

Usage: python scripts/browser_smoke.py [--chromium /usr/bin/chromium]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium', type=Path, default=Path('/usr/bin/chromium'))
    parser.add_argument('--screenshots-dir', type=Path,
                        help='QA artifact directory; defaults to ignored .artifacts/browser-smoke')
    args = parser.parse_args()
    screenshot_dir = args.screenshots_dir or (ROOT / '.artifacts' / 'browser-smoke')
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit('Install optional playwright and a local Chromium binary to run this smoke test') from exc
    if not args.chromium.is_file():
        raise SystemExit(f'Chromium binary not found: {args.chromium}')

    html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
    html = re.sub(r'<script\s+src="/static/.*?"\s+defer></script>', '', html)
    html = re.sub(r'<link\s+rel="stylesheet"\s+href="/static/style.css"\s*/>', '', html)
    css = (ROOT / 'static/style.css').read_text(encoding='utf-8')
    js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    chat_js = (ROOT / 'static/chat.js').read_text(encoding='utf-8')
    cities_js = (ROOT / 'static/cities.js').read_text(encoding='utf-8')
    vault_js = (ROOT / 'static/vault.js').read_text(encoding='utf-8')
    zh_tw_js = (ROOT / 'static/zh-tw-map.js').read_text(encoding='utf-8')
    i18n_js = (ROOT / 'static/i18n.js').read_text(encoding='utf-8')
    i18n_extra_js = (ROOT / 'static/i18n-extra.js').read_text(encoding='utf-8')
    client = TestClient(app)
    counts = {'requests': 0}

    def call_api(path: str, data: dict):
        if not path.startswith('/api/'):
            raise ValueError('Only /api/ calls can use the local browser bridge')
        response = client.get(path) if data is None else client.post(path, json=data)
        counts['requests'] += 1
        return {'ok': response.is_success, 'status': response.status_code, 'data': response.json()}

    with sync_playwright() as engine:
        browser = engine.chromium.launch(executable_path=str(args.chromium), headless=True,
                                         args=['--no-sandbox', '--disable-dev-shm-usage'])
        try:
            page = browser.new_page(viewport={'width': 1440, 'height': 920}, device_scale_factor=1)
            errors: list[str] = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.set_content(html)
            page.add_style_tag(content=css)
            page.expose_function('apiBridge', call_api)
            page.evaluate('''() => {
              const map={};
              Object.defineProperty(window,'localStorage',{value:{
                getItem:k=>map[k]??null,
                setItem:(k,v)=>{map[k]=String(v)},
                removeItem:k=>{delete map[k]}
              },configurable:true});
              window.fetch=async(path,opt)=>{
                const data=opt && opt.body ? JSON.parse(opt.body) : null;
                const result=await window.apiBridge(path,data);
                return {ok:result.ok,status:result.status,json:async()=>result.data};
              };
            }''')
            # Exercise one-time profile migration when the project is rebranded.
            page.evaluate('''() => window.localStorage.setItem('oriental-astro-profiles-v2',
              JSON.stringify([{id:'legacy-1',label:'既有档案',data:{birth_datetime:'2000-08-16T04:00',timezone:'Asia/Shanghai'}}]))''')
            page.add_script_tag(content=zh_tw_js)
            page.add_script_tag(content=i18n_extra_js)
            page.add_script_tag(content=chat_js)
            page.add_script_tag(content=js)
            page.add_script_tag(content=vault_js)
            page.add_script_tag(content=cities_js)
            page.add_script_tag(content=i18n_js)
            page.locator('#birth_city').select_option('温哥华')
            assert page.locator('#timezone').input_value() == 'America/Vancouver'
            assert page.locator('#longitude').input_value() == '-123.1207'
            page.locator('#birth_city').select_option('')
            page.locator('#timezone').select_option('Asia/Shanghai')
            page.locator('#longitude').fill('')
            # AI chat is the initial view; without a configured model it explains how to enable it.
            page.locator('#chat-status').get_by_text('对话服务未启用', exact=False).wait_for(timeout=30000)
            assert page.locator('#chat-send').is_disabled()
            assert page.locator('#chat-memory-panel').count() == 1
            assert page.locator('#chat-mode option').count() == 2 and page.locator('#chat-mode').input_value() == 'single'
            page.locator('[data-tab="date-scan"]').click()
            page.locator('#scan-hours').fill('09:00')
            page.locator('#scan-run').click()
            page.get_by_text('值符', exact=False).first.wait_for(timeout=30000)
            page.locator('[data-tab="chat"]').click()
            assert page.locator('#tool-toggle-all').is_visible()
            assert page.locator('.tab:visible').count() < page.locator('.tab').count()
            page.locator('#tool-toggle-all').click()
            page.locator('[data-tab="consult"]').click()
            page.locator('#consult-advanced summary').click()
            assert page.evaluate("JSON.parse(localStorage.getItem('xuanshu-profiles-v2'))[0].id") == 'legacy-1'
            assert page.evaluate("localStorage.getItem('oriental-astro-profiles-v2') !== null")

            assert page.locator('.tab').count() == 24
            # Question-first consultation keeps its opt-in birth input.
            assert page.locator('#consult-question').count() == 1
            page.locator('#consult-question').fill('2027年职业选择')
            page.locator('#consult-run').click()
            page.get_by_text('需要补充', exact=False).first.wait_for(timeout=30000)
            assert 'birth' in page.locator('#result').inner_text()
            page.locator('#consult-use-birth').check()
            page.locator('#consult-real-world-facts').fill('需要稳定的收入和可控的工作时间')
            page.locator('#consult-run').click()
            page.get_by_text('annual_transformations', exact=False).first.wait_for(timeout=30000)
            assert '可核验观察' in page.locator('#result').inner_text()
            assert '需要稳定的收入' in page.locator('#result').inner_text()
            page.screenshot(path=str(screenshot_dir / '26-consultation-desktop.png'), full_page=True)
            page.locator('#consult-question').fill('那2028年呢？')
            page.locator('#consult-run').click()
            page.get_by_text('2028 农历年', exact=False).first.wait_for(timeout=30000)
            page.locator('[data-tab="bazi"]').click()
            page.locator('#run-btn').click()
            page.locator('.pillar-stem').first.wait_for(timeout=30000)
            assert page.locator('.pillar-stem').count() == 4
            page.screenshot(path=str(screenshot_dir / '01-bazi-desktop.png'), full_page=True)
            page.locator('[data-tab="annual"]').click()
            page.screenshot(path=str(screenshot_dir / '03-annual.png'), full_page=True)
            page.locator('[data-tab="time"]').click()
            page.screenshot(path=str(screenshot_dir / '04-time-audit.png'), full_page=True)

            # New 开发阶段 hour-Qimen page: click through real UI, verify 3x3 Lo Shu cells,
            # and ensure an edited input cannot silently reuse an old chart.
            page.locator('[data-tab="qimen"]').click()
            page.locator('#qimen-run').click()
            page.locator('.qimen-cell').first.wait_for(timeout=30000)
            assert page.locator('.qimen-cell').count() == 9
            assert '时家拆补转盘' in page.locator('#result').inner_text()
            assert '地干' in page.locator('.qimen-cell').first.inner_text()
            assert page.locator('.qimen-cell').get_by_text('暗干', exact=False).count() == 9
            page.screenshot(path=str(screenshot_dir / '19-qimen-desktop.png'), full_page=True)
            page.locator('#birth_datetime').fill('2024-06-15T14:30')
            page.locator('[data-tab="ziwei"]').click()
            page.locator('[data-tab="qimen"]').click()
            assert page.locator('.qimen-cell').count() == 0, 'Stale Qimen chart was not invalidated'
            page.locator('#qimen-run').click()
            page.locator('.qimen-cell').first.wait_for(timeout=30000)
            assert '芒种' in page.locator('#result').inner_text()
            page.locator('#birth_datetime').fill('2000-08-16T04:00')

            # Real Chromium exercise for installed or unavailable optional provider.
            from app.professional_ziwei import professional_provider_available
            page.locator('[data-tab="professional"]').click()
            page.locator('#gender').select_option('female')
            page.locator('#professional-run').click()
            if professional_provider_available():
                page.wait_for_function("() => document.querySelector('#result pre.json-code')?.textContent.includes('iztro-py')", timeout=30000)
                assert '专业紫微' in page.locator('#result').inner_text()
                page.screenshot(path=str(screenshot_dir / '22-professional-provider-success.png'), full_page=True)
            else:
                page.wait_for_function("() => document.querySelector('#result').textContent.includes('专业引擎暂不可用')", timeout=30000)
                assert 'No approximate chart was substituted' in page.locator('#result').inner_text()
                page.screenshot(path=str(screenshot_dir / '22-professional-provider-guard.png'), full_page=True)
            page.locator('[data-tab="qimen-audit"]').click()
            page.locator('#qimen-audit-input').fill('{"reference_source":"public independent reference","reference_school":"时家拆补转盘","root_fields":{"bureau":9},"palaces":[{"number":1,"star":"天蓬"}]}')
            page.locator('#qimen-audit-run').click()
            page.wait_for_function("() => document.querySelector('#result').textContent.includes('字段一致')", timeout=30000)
            page.screenshot(path=str(screenshot_dir / '23-qimen-audit.png'), full_page=True)
            page.locator('[data-tab="ziwei"]').click()
            assert page.locator('.palace-btn').count() == 12
            page.locator('.palace-btn').first.click()
            assert page.locator('.palace-btn.selected').count() == 1
            page.screenshot(path=str(screenshot_dir / '02-ziwei-desktop.png'), full_page=True)

            page.locator('[data-tab="calendar"]').click()
            page.locator('#calendar-run').click()
            page.locator('#result tbody tr').first.wait_for(timeout=30000)
            assert page.locator('#result tbody tr').count() == 14
            page.screenshot(path=str(screenshot_dir / '05-calendar.png'), full_page=True)
            page.locator('#lunar-inverse-run').click()
            page.get_by_text('公历 2024-02-10', exact=False).first.wait_for(timeout=30000)

            page.locator('[data-tab="pair"]').click()
            page.locator('#pair-run').click()
            page.locator('#ziwei-pair-grid tbody tr').first.wait_for(timeout=30000)
            # 4 pillar rows + 12 branch rows + 8 cross-chart transformations.
            assert page.locator('#result tbody tr').count() == 4 + 12 + 8
            assert page.get_by_text('A 命宫落在 B 的', exact=False).count() == 1
            page.screenshot(path=str(screenshot_dir / '06-pair.png'), full_page=True)

            # 开发阶段 decade cycles and exact modeled birth-time boundaries.
            page.locator('[data-tab="dayun"]').click()
            page.locator('#dayun-run').click()
            page.get_by_text('投影起始时间',exact=False).first.wait_for(timeout=30000)
            assert page.locator('#result tbody tr').count() == 10
            page.screenshot(path=str(screenshot_dir / '17-dayun-desktop.png'), full_page=True)
            page.locator('[data-tab="boundaries"]').click()
            page.locator('#boundary-radius').fill('8')
            page.locator('#boundary-run').click()
            page.get_by_text('各区间代表命盘',exact=False).first.wait_for(timeout=30000)
            assert page.locator('#result tbody tr').count() >= 1
            page.screenshot(path=str(screenshot_dir / '18-boundaries-desktop.png'), full_page=True)

            # All three independently implemented 开发阶段 workflows must work from visible controls.
            page.locator('[data-tab="officers"]').click()
            page.locator('#officer-run').click()
            page.locator('#result tbody tr').first.wait_for(timeout=30000)
            assert page.locator('#result tbody tr').count() == 30
            assert '十二值日' in page.locator('#result').inner_text()
            page.screenshot(path=str(screenshot_dir / '14-day-officers-desktop.png'), full_page=True)

            page.locator('[data-tab="timeline"]').click()
            page.locator('#timeline-run').click()
            page.locator('#result tbody tr').first.wait_for(timeout=30000)
            assert page.locator('#result tbody tr').count() == 10
            assert '年度轨迹' in page.locator('#result').inner_text()
            page.screenshot(path=str(screenshot_dir / '15-annual-timeline-desktop.png'), full_page=True)

            page.locator('[data-tab="decision"]').click()
            page.locator('#decision-add-criterion').click()
            assert page.locator('.criterion-edit').count() == 3
            page.locator('.remove-criterion').last.click()
            assert page.locator('.criterion-edit').count() == 2
            page.locator('#decision-add-option').click()
            assert page.locator('.option-edit').count() == 3
            page.locator('.remove-option').last.click()
            assert page.locator('.option-edit').count() == 2
            assert page.locator('.remove-option').first.is_disabled()
            page.locator('#decision-run').click()
            page.get_by_text('单指标剔除敏感性',exact=False).first.wait_for(timeout=30000)
            assert page.locator('#result tbody tr').count() == 2
            page.screenshot(path=str(screenshot_dir / '16-decision-matrix-desktop.png'), full_page=True)

            page.locator('[data-tab="quality"]').click()
            assert page.locator('#quality-minutes').input_value() == '15'
            page.locator('#quality-minutes').fill('10')
            page.locator('#quality-run').click()
            page.wait_for_function("() => document.querySelector('#result').textContent.includes('有效时间')", timeout=30000)
            assert page.locator('#quality-minutes').input_value() == '10'
            assert '未发现当前规则已知边界问题' in page.locator('#result').inner_text()
            page.screenshot(path=str(screenshot_dir / '11-quality-desktop.png'), full_page=True)

            # Auditable deep cross-method review: real Chromium controls invoking FastAPI.
            page.locator('[data-tab="deep"]').click()
            page.locator('#deep-palace').select_option('官禄宫')
            page.locator('#deep-year').fill('2026')
            page.locator('#deep-question').fill('请只展示可计算的宫位关联')
            page.locator('#deep-run').click()
            page.get_by_text('内部一致性核查', exact=False).first.wait_for(timeout=30000)
            assert '三方四正' in page.locator('#result').inner_text()
            assert page.locator('#deep-download').is_visible()
            assert page.locator('a[href="https://docs.iztro.com/en_US/posts/palace"]').count() > 0
            page.screenshot(path=str(screenshot_dir / '24-deep-evidence-desktop.png'), full_page=True)
            page.locator('#deep-year').fill('2100')
            page.locator('#deep-run').click()
            assert '1901–2099' in page.locator('#result').inner_text()
            page.locator('#deep-year').fill('2026')

            page.locator('[data-tab="report"]').click()
            assert page.locator('#report-year').input_value() == ''
            assert page.locator('#report-deep').is_checked()
            page.locator('#report-run').click()
            page.get_by_text('可追溯综合报告', exact=False).first.wait_for(timeout=30000)
            page.locator('#report-download').wait_for(timeout=30000)
            assert '出生数据与排盘边界审计' in page.locator('#result').inner_text()
            assert '规则证据与跨体系差异复核' in page.locator('#result').inner_text()
            assert page.locator('#report-year').input_value() == ''
            page.screenshot(path=str(screenshot_dir / '10-report.png'), full_page=True)
            page.locator('[data-tab="integration"]').click()
            page.screenshot(path=str(screenshot_dir / '07-integration.png'), full_page=True)

            page.locator('#birth_datetime').fill('2057-09-28T12:00')
            page.locator('#run-btn').click()
            page.wait_for_function("() => document.querySelector('#result-subtitle').textContent.startsWith('2057-09-28')", timeout=30000)
            page.locator('[data-tab="quality"]').click()
            page.locator('#quality-run').click()
            page.get_by_text('published_new_moon_uncertainty', exact=False).first.wait_for(timeout=30000)
            assert page.locator('a[href="https://www.hko.gov.hk/en/gts/time/conversion.htm"]').count() > 0
            page.screenshot(path=str(screenshot_dir / '12-quality-hko-desktop.png'), full_page=True)

            # Actual frontend response to cross-timezone New Year date clash.
            page.locator('#timezone').select_option('Europe/Rome')
            page.locator('#birth_datetime').fill('2024-02-09T20:00')
            page.locator('#quality-run').click()
            page.get_by_text('china_lunar_date_basis_disagreement', exact=False).first.wait_for(timeout=30000)
            assert '时区日界对照' in page.locator('#result').inner_text()
            assert '2024-02-10' in page.locator('#result').inner_text()
            page.screenshot(path=str(screenshot_dir / '21-quality-timezone-desktop.png'), full_page=True)
            page.locator('#timezone').select_option('Asia/Shanghai')

            page.set_viewport_size({'width': 390, 'height': 844})
            page.locator('[data-tab="qimen"]').click()
            page.locator('#qimen-run').click()
            page.locator('.qimen-cell').first.wait_for(timeout=30000)
            page.screenshot(path=str(screenshot_dir / '20-qimen-mobile.png'), full_page=True)
            page.locator('[data-tab="bazi"]').click()
            page.screenshot(path=str(screenshot_dir / '08-mobile-bazi.png'), full_page=True)
            page.locator('[data-tab="ziwei"]').click()
            page.screenshot(path=str(screenshot_dir / '09-mobile-ziwei.png'), full_page=True)
            page.locator('[data-tab="deep"]').click()
            assert page.locator('#deep-run').is_visible()
            page.screenshot(path=str(screenshot_dir / '25-deep-evidence-mobile.png'), full_page=True)
            page.locator('[data-tab="consult"]').click()
            assert page.locator('#consult-run').is_visible()
            page.screenshot(path=str(screenshot_dir / '27-consultation-mobile.png'), full_page=True)
            page.locator('[data-tab="quality"]').click()
            assert page.locator('#quality-run').is_visible()
            page.screenshot(path=str(screenshot_dir / '13-quality-mobile.png'), full_page=True)
            # Interface language: English shell, 繁體 conversion of computed text, and back.
            page.set_viewport_size({'width': 1440, 'height': 920})
            page.locator('[data-tab="pair"]').click()
            page.locator('#ui-language').select_option('en')
            assert page.locator('[data-tab="pair"]').inner_text() == 'Two-person comparison'
            assert page.locator('#run-btn span').first.inner_text() == 'Generate chart'
            assert page.locator('#profile_name').get_attribute('placeholder') == 'e.g. Test chart A'
            page.locator('[data-tab="chat"]').click()
            page.locator('#chat-send').get_by_text('Send').wait_for(timeout=10000)
            assert page.locator('#chat-language').input_value() == 'en'
            page.screenshot(path=str(screenshot_dir / '28-ui-english.png'), full_page=True)
            page.locator('#ui-language').select_option('zh-TW')
            assert page.locator('[data-tab="calendar"]').inner_text() == '曆法日曆'
            page.locator('[data-tab="pair"]').click()
            page.locator('#pair-run').click()
            page.locator('#ziwei-pair-grid tbody tr').first.wait_for(timeout=30000)
            assert page.get_by_text('紫微宮位疊盤', exact=True).count() == 1
            page.screenshot(path=str(screenshot_dir / '29-ui-traditional.png'), full_page=True)
            # Computed results follow the interface language too: palace names in the overlay grid.
            page.locator('#ui-language').select_option('en')
            grid = page.locator('#ziwei-pair-grid').inner_text()
            assert 'Life Palace' in grid and '命宫' not in grid, grid[:300]
            # Branch names and pillar values stay as characters; profile labels the user typed are never rewritten.
            assert '\n子\t' in '\n' + grid or grid.splitlines()[1].startswith('子'), grid[:300]
            assert page.locator('#profiles option').first.inner_text() == '既有档案'
            page.screenshot(path=str(screenshot_dir / '30-results-english.png'), full_page=True)
            page.locator('#ui-language').select_option('ja')
            grid = page.locator('#ziwei-pair-grid').inner_text()
            assert '命宮' in grid and '命宫' not in grid, grid[:300]
            page.locator('#ui-language').select_option('zh-CN')
            assert page.locator('[data-tab="calendar"]').inner_text() == '历法日历'
            assert page.get_by_text('紫微宫位叠盘', exact=True).count() == 1
            if errors:
                raise AssertionError(f'Chromium page errors: {errors}')
            if counts['requests'] < 15:
                raise AssertionError(f'Insufficient REST calls: {counts}')
            print(f'PASS: real Chromium {browser.version} UI interactions and {counts["requests"]} FastAPI requests; '
                  'desktop/mobile screenshots captured, no JS page errors. HTTP network navigation NOT tested.')
        finally:
            browser.close()


if __name__ == '__main__':
    main()
