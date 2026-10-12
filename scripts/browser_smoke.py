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
import json
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
    html = re.sub(r'<script\s+src="/static/.*?"(\s+defer)?></script>', '', html)
    html = re.sub(r'<link\s+rel="stylesheet"\s+href="/static/style.css"\s*/>', '', html)
    css = (ROOT / 'static/style.css').read_text(encoding='utf-8')
    js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    chat_js = (ROOT / 'static/chat.js').read_text(encoding='utf-8')
    theme_js = (ROOT / 'static/theme.js').read_text(encoding='utf-8')
    markdown_js = (ROOT / 'static/markdown.js').read_text(encoding='utf-8')
    cities_js = (ROOT / 'static/cities.js').read_text(encoding='utf-8')
    vault_js = (ROOT / 'static/vault.js').read_text(encoding='utf-8')
    zh_tw_js = (ROOT / 'static/zh-tw-map.js').read_text(encoding='utf-8')
    i18n_js = (ROOT / 'static/i18n.js').read_text(encoding='utf-8')
    i18n_extra_js = (ROOT / 'static/i18n-extra.js').read_text(encoding='utf-8')
    client = TestClient(app)
    counts = {'requests': 0}
    group_bodies: list[str] = []

    def call_api(path: str, data: dict):
        # The page also reads one static data file (the cross-check summary) with fetch.
        if not (path.startswith('/api/') or (data is None and path == '/static/crosscheck-summary.json')):
            raise ValueError('Only /api/ calls can use the local browser bridge')
        if path == '/api/group-relations':
            group_bodies.append(json.dumps(data, ensure_ascii=False))
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
            page.add_script_tag(content=theme_js)
            page.add_script_tag(content=zh_tw_js)
            page.add_script_tag(content=i18n_extra_js)
            page.add_script_tag(content=markdown_js)
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

            assert page.locator('.tab').count() == 29
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
            # Decade and annual pillars under the BaZi chart; a year opens the Zi Wei year layer.
            page.locator('#luck-decade-0').wait_for(timeout=30000)
            assert page.locator('.luck-decade').count() == 9 and page.locator('.luck-year').count() == 10
            page.locator('#luck-decade-1').click()
            assert page.locator('#luck-decade-1').get_attribute('aria-pressed') == 'true'
            assert page.locator('#luck-year-2015').count() == 1
            page.screenshot(path=str(screenshot_dir / '01-bazi-desktop.png'), full_page=True)
            page.locator('#luck-year-2015').click()
            page.locator('#ziwei-board').wait_for(timeout=30000)
            assert 'active' in page.locator('#ziwei-layer-year').get_attribute('class')
            assert '2015' in page.locator('.layer-bar').inner_text()
            page.locator('#ziwei-layer-natal').click()

            # Pillars to dates: prefilled from the chart, every interval listed, one click casts it.
            page.locator('[data-tab="pillar-search"]').click()
            assert page.locator('#pillar-year').input_value() == '庚辰' and page.locator('#pillar-hour').input_value() == '庚寅'
            page.locator('#pillar-search-run').click()
            page.locator('#pillar-use-1').wait_for(timeout=30000)
            assert page.locator('#result tbody tr').count() == 2
            assert '2000-08-16 03:00:00' in page.locator('#result').inner_text()
            page.screenshot(path=str(screenshot_dir / '33-pillar-search.png'), full_page=True)
            page.locator('#pillar-use-1').click()
            assert page.locator('#birth_datetime').input_value() == '2000-08-16T04:00'
            page.locator('.pillar-stem').first.wait_for(timeout=30000)

            # Pasted chart check: matching fields, then a differing hour pillar.
            page.locator('[data-tab="import-check"]').click()
            page.locator('#import-text').fill('乾造 庚辰 甲申 丙午 庚寅\n命宫在午，木三局，命主：破军')
            page.locator('#import-check-run').click()
            page.locator('.import-table').wait_for(timeout=30000)
            assert '识别到的字段全部一致' in page.locator('#result').inner_text()
            page.locator('#import-text').fill('乾造 庚辰 甲申 丙午 辛卯\n命宫在午')
            page.locator('#import-check-run').click()
            page.wait_for_function("() => document.querySelectorAll('.import-table tr.mismatch').length === 1", timeout=30000)
            assert '可能的原因' in page.locator('#result').inner_text()
            page.screenshot(path=str(screenshot_dir / '34-import-check.png'), full_page=True)
            # Brightness printed after a star is compared too; a different grade is a table difference, not a rule.
            page.locator('#import-text').fill('命宫 紫微庙\n夫妻宫：七杀（平）')
            page.locator('#import-check-run').click()
            page.wait_for_function("() => document.querySelectorAll('.import-table tr.mismatch').length === 1", timeout=30000)
            assert '夫妻宫主星亮度\t七杀平\t七杀庙' in page.locator('.import-table').inner_text()
            assert '亮度表' in page.locator('#result').inner_text() and page.locator('.import-verdict').count() == 0

            # Today card from the header chip: calendar facts for the device clock and labels against the chart.
            assert page.locator('#today-chip').is_visible()
            page.locator('#today-chip').click()
            page.locator('.today-table').wait_for(timeout=30000)
            assert page.locator('.today-pillar').count() == 4 and page.locator('.today-table tbody tr').count() == 4
            assert page.locator('.moon-icon').count() == 2  # the card and the header chip
            assert '日主 丙火' in page.locator('#result').inner_text()
            page.screenshot(path=str(screenshot_dir / '35-today.png'), full_page=True)
            assert page.locator('#today-ics').get_attribute('href').endswith('.ics?moon=true')
            # Pick another day on the card, then return to the device clock.
            page.locator('#today-next').click()
            page.locator('#today-now').wait_for(timeout=30000)
            page.locator('.today-hero').wait_for(timeout=30000)
            assert '所选时刻' in page.locator('.result-intro').inner_text()
            page.locator('#today-now').click()
            page.wait_for_function("() => !document.getElementById('today-now') && document.querySelector('.today-hero')", timeout=30000)

            # Group relations: the current chart, the migrated local profile and one member added on the page.
            page.locator('[data-tab="group"]').click()
            page.locator('#group-run').wait_for(timeout=30000)
            page.locator('#group-profile-legacy-1').check()
            page.locator('#group-extra-label').fill('同事')
            page.locator('#group-extra-datetime').fill('1992-06-06T09:00')
            page.locator('#group-extra-add').click()
            # Member notes: a temporary member's stays on the page; a profile's is stored only on 保存到档案.
            page.locator('#group-extra-note-0').fill('一起做项目')
            page.locator('#group-note-legacy-1').fill('表姐')
            page.locator('#group-current-note').fill('本人')
            # Another current chart starts with an empty note; the first chart's note comes back with it.
            page.evaluate("() => { window.__chart = currentInput; currentInput = {...currentInput, birth_datetime: '2001-01-01T10:00'}; render(); }")
            assert page.locator('#group-current-note').input_value() == ''
            page.evaluate("() => { currentInput = window.__chart; render(); }")
            assert page.locator('#group-current-note').input_value() == '本人'
            assert page.evaluate("loadProfiles().find(x => x.id === 'legacy-1').note") is None
            page.locator('#group-note-save-legacy-1').click()
            assert page.evaluate("loadProfiles().find(x => x.id === 'legacy-1').note") == '表姐'
            page.locator('#group-run').click()
            page.locator('#group-graph').wait_for(timeout=30000)
            assert page.locator('.group-member').count() == 3 and page.locator('.group-edge').count() == 3
            assert page.locator('.group-note-text').all_inner_texts() == ['本人', '表姐', '一起做项目']
            assert group_bodies and all('表姐' not in r and '一起做项目' not in r and '本人' not in r for r in group_bodies), 'Notes must not reach the server'
            # A selection changed while the request runs does not move the notes onto other members.
            page.evaluate("""() => { window.__post = postJSON; postJSON = async (...args) => {
              const reply = await window.__post(...args); groupDraft.useCurrent = false; postJSON = window.__post; return reply; }; }""")
            page.locator('#group-run').click()
            page.locator('#group-current:not(:checked)').wait_for(timeout=30000)
            assert '成员已改变' in page.locator('#result').inner_text()
            assert page.locator('.group-note-text').all_inner_texts() == ['本人', '表姐', '一起做项目']
            page.locator('#group-current').check()
            page.locator('#group-run').click()
            page.wait_for_function("() => ![...document.querySelectorAll('.feature-note')].some(n => n.textContent.includes('成员已改变'))", timeout=30000)
            assert page.locator('#group-matrix tbody tr').count() == 3 and page.locator('.group-pair').count() == 3
            page.locator('[data-filter="六冲"]').click()
            page.locator('#group-node-0').focus()
            page.keyboard.press('Enter')
            page.wait_for_function("() => document.querySelectorAll('.group-node.is-focus').length === 1 && document.activeElement.id === 'group-node-0'", timeout=30000)
            page.screenshot(path=str(screenshot_dir / '36-group.png'), full_page=True)
            # The members can go to the AI chat as a draft; without a configured model the button says why it is off.
            assert page.locator('#group-ask-ai').is_disabled() and 'AI 对话尚未启用' in page.locator('.group-ask').inner_text()
            page.evaluate("() => { chatStatus.enabled = true; chatDraft = '先前没发的问题'; }")
            for _ in range(2):  # an unsent question is kept and a second click does not add the members twice
                page.locator('[data-tab="group"]').click()
                page.locator('#group-ask-ai:not([disabled])').click()
                page.locator('[data-tab="chat"][aria-selected="true"]').wait_for(timeout=30000)
            draft = page.locator('#chat-input').input_value()
            assert draft.startswith('先前没发的问题\n\n请结合多人关系对照') and draft.count('\n- ') == 3, draft
            assert '- 同事 · 1992-06-06 09:00 · ' in draft and ' · 备注：一起做项目' in draft and ' · 备注：表姐' in draft, draft
            # An edited note replaces the group's earlier block instead of adding the members again.
            page.locator('[data-tab="group"]').click()
            page.locator('#group-extra-note-0').fill('一起做项目两年')
            page.locator('#group-ask-ai:not([disabled])').click()
            page.locator('[data-tab="chat"][aria-selected="true"]').wait_for(timeout=30000)
            draft = page.locator('#chat-input').input_value()
            assert draft.startswith('先前没发的问题\n\n请结合多人关系对照') and draft.count('\n- ') == 3, draft
            assert ' · 备注：一起做项目两年' in draft and '备注：一起做项目\n' not in draft and not draft.endswith('备注：一起做项目'), draft
            # Other people's birth data is not sent until the consent box is ticked.
            assert page.locator('#chat-send').is_disabled() and page.locator('#chat-consent-needed').is_visible()
            page.evaluate("() => { chatPartnerOK = true; render(); }")
            assert not page.locator('#chat-send').is_disabled() and page.locator('#chat-consent-needed').count() == 0
            page.evaluate("() => { chatPartnerOK = false; render(); }")
            page.screenshot(path=str(screenshot_dir / '39-group-to-chat.png'), full_page=True)
            page.evaluate("() => { chatStatus.enabled = false; chatDraft = ''; }")
            page.locator('[data-tab="group"]').click()
            page.locator('#group-note-clear-legacy-1').click()
            page.wait_for_function("() => loadProfiles().find(x => x.id === 'legacy-1').note === undefined && !document.getElementById('group-note-clear-legacy-1')", timeout=10000)

            # Rule differences: the chart recomputed under each common rule choice.
            page.locator('[data-tab="rule-matrix"]').click()
            page.locator('#rule-matrix').wait_for(timeout=30000)
            assert page.locator('#rule-matrix tbody tr').count() == 4 and page.locator('.rule-big').inner_text() == '3 / 3'
            page.locator('#rule-only-diff').check()
            page.wait_for_function("() => document.querySelectorAll('#rule-matrix tbody tr').length === 1", timeout=30000)
            page.screenshot(path=str(screenshot_dir / '37-rule-matrix.png'), full_page=True)
            page.locator('[data-tab="bazi"]').click()
            page.locator('[data-tab="annual"]').click()
            page.screenshot(path=str(screenshot_dir / '03-annual.png'), full_page=True)
            page.locator('[data-tab="time"]').click()
            page.screenshot(path=str(screenshot_dir / '04-time-audit.png'), full_page=True)

            # New 开发阶段 hour-Qimen page: click through real UI, verify 3x3 Lo Shu cells,
            # and ensure an edited input cannot silently reuse an old chart.
            page.locator('[data-tab="qimen"]').click()
            assert page.locator('#qimen-moment').input_value() == 'now'
            page.locator('#qimen-moment').select_option('birth')
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
            # A chart cast for another moment is discarded when the moment changes.
            page.locator('#qimen-moment').select_option('now')
            assert page.locator('.qimen-cell').count() == 0, 'Qimen chart survived a change of moment'
            page.locator('#qimen-moment').select_option('birth')
            page.locator('#birth_datetime').fill('2000-08-16T04:00')

            # Zi Wei time layers relabel the board; focus stays on the control that was used.
            page.locator('[data-tab="ziwei"]').click()
            assert page.locator('.palace-layer').count() == 0
            # Star brightness: one mark per star the engine grades, 紫微 庙 in 午, and the palace panel repeats it.
            bright = page.evaluate('''() => ({
              shown: [...document.querySelectorAll('#ziwei-board .bright')].map(el => el.parentElement.firstChild.data + el.dataset.level + '@' + el.closest('.palace').id).sort(),
              api: current.ziwei.palaces.flatMap((p, i) => Object.entries(p.star_brightness).map(([star, level]) => star + level + '@palace-' + i)).sort()})''')
            assert bright['shown'] == bright['api'] and len(bright['api']) >= 14, bright
            assert '紫微庙@palace-6' in bright['shown'] and '主星：紫微（庙）' in page.locator('.palace-panel').inner_text()
            # Flying transformations of the selected Life palace (午, 壬 stem): 天梁 禄 to 卯, 紫微 权 stays (自化),
            # 左辅 科 to 戌, 武曲 忌 to 寅. One curve per palace it flies into, one badge in each palace.
            assert page.locator('#ziwei-board path.fly').count() == 3
            assert page.locator('#palace-3 .fly-mark.fly-lu').inner_text() == '禄入' and page.locator('#palace-6 .fly-mark').inner_text() == '自化权'
            assert page.locator('#palace-10 .fly-mark.fly-ke').count() == 1 and page.locator('#palace-2 .fly-mark.fly-ji').count() == 1
            page.locator('#ziwei-fly-toggle').click()
            assert page.locator('#ziwei-board path.fly').count() == 0 and page.locator('.fly-mark').count() == 0
            assert page.locator('#ziwei-fly-toggle').get_attribute('aria-pressed') == 'false'
            page.locator('#ziwei-fly-toggle').click()
            assert page.locator('#ziwei-board path.fly').count() == 3
            # The panel lists the reverse direction too: 紫微 and 文曲 sit in 午, so 乙 (酉) sends 紫微化科,
            # 辛 (巳) sends 文曲化科 and both 己 palaces send 文曲化忌; 午's own 壬 紫微化权 is a self-transformation.
            fly_in = page.locator('.palace-panel .fly-in').inner_text()
            assert fly_in.startswith('飞入本宫：') and fly_in.count('；') == 3, fly_in
            assert all(item in fly_in for item in ('田宅宫（乙干）紫微化科', '兄弟宫（辛干）文曲化科', '疾厄宫（己干）文曲化忌', '子女宫（己干）文曲化忌')), fly_in
            # Arrow keys move between palaces in board order and jump the empty middle; the board is one tab stop.
            assert page.locator('#ziwei-board .palace[tabindex="0"]').count() == 1 and page.locator('#palace-6').get_attribute('tabindex') == '0'
            page.locator('#palace-6').focus()
            for key, expected in (('ArrowRight', 'palace-7'), ('ArrowDown', 'palace-0'), ('ArrowLeft', 'palace-1'), ('ArrowUp', 'palace-6')):
                page.keyboard.press(key)
                page.wait_for_function(f"() => document.activeElement.id === '{expected}' && document.activeElement.getAttribute('aria-pressed') === 'true' && document.activeElement.tabIndex === 0", timeout=10000)
            page.locator('#palace-5').focus()
            page.keyboard.press('ArrowLeft')  # the edge of the board: nothing moves
            assert page.evaluate('document.activeElement.id') == 'palace-5' and page.locator('#palace-6').get_attribute('aria-pressed') == 'true'
            page.locator('#ziwei-layer-decade').click()
            assert page.locator('.palace-layer').count() == 12
            assert page.locator('.palace.layer-anchor').count() == 1
            assert page.locator('#ziwei-board .hua.layer').count() == 4
            # The layer starts on its own Life palace, whose stem is the decade stem: its curves are the layer's, drawn once.
            assert page.locator('#ziwei-board path.fly.layer').count() == 0 and '点线' not in page.locator('.hua-legend').inner_text()
            # Another palace keeps the layer's four transformations as dotted curves from the layer's Life palace.
            page.locator('#palace-6').click()
            layer_curves = page.evaluate('''() => {const z = current.ziwei, info = ziweiLayerInfo(z);
              return info.anchor === 6 ? -1 : info.hua.filter(t => t.target_palace !== z.palaces[info.anchor].name).length;}''')
            assert layer_curves >= 1 and page.locator('#ziwei-board path.fly.layer').count() == layer_curves, layer_curves
            assert page.locator('#ziwei-board path.fly:not(.layer)').count() == 3
            assert '点线：大限四化飞入的宫位' in page.locator('.hua-legend').inner_text(), page.locator('.hua-legend').inner_text()
            page.locator('#ziwei-board').screenshot(path=str(screenshot_dir / '42-ziwei-layer-flying.png'))
            # The decade and year layers draw their 流曜 in the browser; they must match the engine's.
            flow_check = '''async key => {
              // 1 July always falls inside the lunar year of the same number.
              const z = current.ziwei, info = ziweiLayerInfo(z);
              const year = key === 'year' ? info.year : z.lunar_date.year + z.palaces[info.anchor].decade.start_age - 1;
              const target = year + '-07-01';
              const h = await postJSON('/api/ziwei-horoscope', {birth: currentInput, target_date: target});
              const at = branch => 'palace-' + '子丑寅卯辰巳午未申酉戌亥'.indexOf(branch);
              const shown = [...document.querySelectorAll('#ziwei-board .flow-star')].map(el => el.textContent + '@' + el.closest('.palace').id).sort();
              const expected = h.layers[key].stars.map(s => s.name + '@' + at(s.branch)).sort();
              const cycles = [...document.querySelectorAll('#ziwei-board .layer-cycle')].map(el => el.textContent + '@' + el.closest('.palace').id).sort();
              const yearly = key === 'year' ? h.layers.year.palaces.map(p => p.suiqian + '@' + at(p.branch)).sort() : [];
              return JSON.stringify([shown, cycles]) === JSON.stringify([expected, yearly]) ? '' : JSON.stringify({shown, expected, cycles, yearly});
            }'''
            assert page.locator('#ziwei-board .flow-star').count() == 10
            decade_check = page.evaluate(flow_check, 'decade')
            assert decade_check == '', decade_check
            page.locator('#ziwei-layer-year').click()
            page.locator('#ziwei-layer-next').click()
            assert page.evaluate('document.activeElement.id') == 'ziwei-layer-next'
            assert '流年四化' in page.locator('.palace-panel').inner_text() and '流年流曜' in page.locator('.palace-panel').inner_text()
            assert page.locator('#ziwei-board .flow-star').count() == 11 and page.locator('#ziwei-board .layer-cycle').count() == 12
            assert page.evaluate(flow_check, 'year') == ''
            page.screenshot(path=str(screenshot_dir / '31-ziwei-annual-layer.png'), full_page=True)
            # Month and day layers come from the engine for any date; the stack lists every layer in force that day.
            page.locator('#ziwei-layer-month').click()
            page.locator('#ziwei-layer-date').fill('2026-10-11')
            page.locator('.layer-label', has_text='2026年九月 · 戊戌月').wait_for(timeout=30000)
            assert page.locator('#palace-10.layer-anchor').count() == 1 and page.locator('#ziwei-layer-stack .layer-stack-row').count() == 5
            assert page.locator('#ziwei-board .hua.layer').count() == 4 and '流月四化（戊干）' in page.locator('.palace-panel').inner_text()
            assert page.locator('#ziwei-board .flow-star', has_text='月禄').count() == 1 and page.locator('#palace-5 .flow-star', has_text='月禄').count() == 1
            page.locator('#ziwei-layer-next').click()
            page.locator('.layer-label', has_text='十月').wait_for(timeout=30000)
            assert page.evaluate('document.activeElement.id') == 'ziwei-layer-next'
            page.locator('#ziwei-layer-day').click()
            page.locator('#ziwei-layer-prev').click()
            page.locator('.layer-label', has_text='2026-11-08 · 九月三十').wait_for(timeout=30000)
            assert page.locator('#ziwei-layer-date').input_value() == '2026-11-08'
            page.screenshot(path=str(screenshot_dir / '40-ziwei-day-layer.png'), full_page=True)
            page.locator('#ziwei-layer-natal').click()

            # Share card: drawn locally; birth date and time stay off unless ticked.
            page.locator('#share-card').click()
            assert page.locator('#share-dialog').is_visible()
            assert not page.locator('#share-date').is_checked() and not page.locator('#share-time').is_checked()
            full = page.evaluate("document.querySelector('#share-canvas').height")
            page.locator('#share-bazi').uncheck()
            assert page.evaluate("document.querySelector('#share-canvas').height") < full
            page.locator('#share-close').click()
            # Without a gender there is no 长生 or 博士, but the year's own 岁前 still marks every palace.
            page.locator('#gender').select_option('unspecified')
            page.locator('#run-btn').click()
            page.wait_for_function("() => current && current.ziwei && current.ziwei.palaces.every(p => !p.natal_cycles.changsheng)", timeout=30000)
            page.locator('[data-tab="ziwei"]').click()
            page.locator('#ziwei-layer-year').click()
            assert page.locator('#ziwei-board .layer-cycle').count() == 12
            page.locator('#ziwei-layer-natal').click()
            assert page.locator('#ziwei-board .palace-cycles').count() == 12
            page.locator('#gender').select_option('female')
            page.locator('#run-btn').click()
            page.wait_for_function("() => current && current.ziwei && current.ziwei.palaces.some(p => p.natal_cycles.changsheng)", timeout=30000)

            # Calculation cross-check: the committed evaluation summary in a dialog.
            page.locator('#crosscheck-open').click()
            page.locator('#crosscheck-differences li').first.wait_for(timeout=30000)
            assert page.locator('#crosscheck-dialog .crosscheck-table tbody tr').count() == 37
            assert '100.000%' in page.locator('#crosscheck-dialog').inner_text()
            page.locator('#crosscheck-dialog').screenshot(path=str(screenshot_dir / '38-crosscheck.png'))
            page.locator('#crosscheck-close').click()
            assert not page.locator('#crosscheck-dialog').is_visible()

            # Lunar birthday entry fills the Gregorian field; an unknown hour gets a twelve-hour comparison.
            page.locator('#lunar-entry summary').click()
            page.locator('#lunar_year').fill('1990')
            page.locator('#lunar_month').select_option('4')
            page.locator('#lunar_day').select_option('23')
            page.locator('#lunar_hour').select_option('')
            page.locator('#lunar-fill').click()
            page.wait_for_function("() => document.querySelector('#birth_datetime').value === '1990-05-17T12:00'", timeout=30000)
            assert page.locator('#hour_unknown').is_checked()
            page.locator('#run-btn').click()
            page.wait_for_function("() => document.querySelector('#result-subtitle').textContent.startsWith('1990-05-17')", timeout=30000)
            page.locator('[data-tab="bazi"]').click()
            page.locator('#hour-compare').click()
            page.locator('.hour-unknown tbody tr').first.wait_for(timeout=30000)
            assert page.locator('.hour-unknown tbody tr').count() == 13
            assert '日柱 壬午 · 全天不变' in page.locator('.stable-list').inner_text()
            page.screenshot(path=str(screenshot_dir / '32-hour-unknown.png'), full_page=True)
            page.locator('#hour_unknown').uncheck()
            page.locator('#lunar-entry summary').click()
            page.locator('#birth_datetime').fill('2000-08-16T04:00')
            page.locator('#run-btn').click()
            page.wait_for_function("() => document.querySelector('#result-subtitle').textContent.startsWith('2000-08-16')", timeout=30000)
            assert page.locator('.hour-unknown').count() == 0

            # Theme toggle cycles system → light → dark → system and stores only an explicit choice.
            page.locator('#theme-toggle').click()
            assert page.evaluate('document.documentElement.dataset.theme') == 'light'
            page.locator('#theme-toggle').click()
            page.locator('#theme-toggle').click()
            assert page.evaluate("document.documentElement.dataset.theme === undefined && localStorage.getItem('xuanshu-theme') === null")

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
            # Each language draws its own short brightness form; the tooltip explains it.
            page.locator('[data-tab="ziwei"]').click()
            page.locator('#ziwei-board .bright').first.wait_for(timeout=30000)
            level = "[...document.querySelectorAll('#ziwei-board .bright')].map(el => el.dataset.level + getComputedStyle(el, '::after').content).join(' ')"
            english = {'庙': 'Peak', '旺': 'High', '得': 'Good', '利': 'Fair', '平': 'Even', '不': 'Low', '陷': 'Fall'}
            marks = page.evaluate(level).split(' ')
            assert all(mark[1:] == f'"{mark[0]}"' for mark in marks), marks
            page.locator('#ui-language').select_option('en')
            expected = ' '.join(f'{mark[0]}"{english[mark[0]]}"' for mark in marks)
            page.wait_for_function(f"() => {level} === {json.dumps(expected)}", timeout=10000)
            first = page.locator('#ziwei-board .bright').first
            assert first.get_attribute('title').startswith('Brightness: ' + english[first.get_attribute('data-level')])
            panel = page.locator('.palace-panel').inner_text()
            selected_levels = page.evaluate("() => {const p = findPalace(current.ziwei, selectedPalace); return p.main_stars.map(s => p.star_brightness[s]);}")
            assert all(f'({english[x]})' in panel for x in selected_levels) and not re.search('（[庙旺得利平不陷]）', panel), panel[:300]
            assert '、' not in panel and '；' not in panel, panel[:300]
            page.screenshot(path=str(screenshot_dir / '41-ziwei-brightness-english.png'), full_page=True)
            # A board drawn while English is active keeps its Chinese source text: the tooltips follow the next switch.
            page.locator('.palace-btn').nth(1).click()
            page.wait_for_function("() => document.querySelector('#ziwei-board .bright').title.startsWith('Brightness: ')", timeout=10000)
            page.locator('#ui-language').select_option('ja')
            page.wait_for_function("() => document.querySelector('#ziwei-board .bright').title.startsWith('明るさ：')", timeout=10000)
            page.locator('#ui-language').select_option('zh-CN')
            page.wait_for_function("() => document.querySelector('#ziwei-board .bright').title.startsWith('亮度：')", timeout=10000)
            page.locator('#ui-language').select_option('ja')
            page.wait_for_function(f"() => {level} === {json.dumps(' '.join(m[0] + (chr(34) + '廟' + chr(34) if m[0] == '庙' else chr(34) + '陥' + chr(34) if m[0] == '陷' else m[1:]) for m in marks))}", timeout=10000)
            page.locator('#ui-language').select_option('zh-CN')
            page.wait_for_function(f"() => {level} === {json.dumps(' '.join(marks))}", timeout=10000)
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
