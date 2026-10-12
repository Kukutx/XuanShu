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


def check_relation_card(page, kind: str, screenshot: Path) -> None:
    """Open a relation card, check what it draws and what it saves, and close it."""
    page.evaluate("""() => {
      window.__drawn = []; window.__saved = []; window.__fillText = CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText = function (text, ...rest) { window.__drawn.push(String(text)); return window.__fillText.call(this, text, ...rest); };
      window.__downloadBlob = downloadBlob; downloadBlob = (blob, name) => { window.__saved.push([name, blob.type, blob.size]); };
    }""")
    page.locator(f'#{kind}-card').click()
    page.locator('#relation-card-dialog[open]').wait_for(timeout=10000)
    assert page.evaluate("document.querySelector('#relation-card-canvas').width") == 1080
    data = page.evaluate(f"(() => {{ const d = relationCardData('{kind}'); return {{labels: d.people.map(p => p.label), year: d.year_view.year}}; }})()")
    # The luck timeline would give away each person's gender: it is drawn only once ticked.
    assert '大运时间轴' not in ''.join(page.evaluate('window.__drawn'))
    page.evaluate('window.__drawn = []')
    page.locator('#relation-card-luck').check()
    drawn = page.evaluate('window.__drawn')
    labels = data['labels']
    assert labels and all(label in ''.join(drawn) for label in labels), (labels, drawn)
    assert f"大运时间轴 · {data['year']}" in ''.join(drawn), drawn
    # Pairs name the direction of each ten god; group members are numbered so cut names stay apart.
    assert ('①→②' if kind == 'group' else 'A→B') in ''.join(drawn), drawn
    joined = '\n'.join(drawn)
    assert not re.search(r'\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2}|备注', joined) and '一起做项目' not in joined and '表姐' not in joined, drawn
    page.locator('#relation-card-canvas').screenshot(path=str(screenshot))
    page.locator('#relation-card-download').click()
    page.wait_for_function('() => window.__saved.length === 1', timeout=10000)
    assert page.evaluate('window.__saved[0]')[:2] == [f'xuanshu-{kind}.png', 'image/png'] and page.evaluate('window.__saved[0][2]') > 10000
    page.evaluate("() => { CanvasRenderingContext2D.prototype.fillText = window.__fillText; downloadBlob = window.__downloadBlob; }")
    page.locator('#relation-card-close').click()
    assert page.locator('#relation-card-dialog[open]').count() == 0


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
            # Growth stages and voids under each pillar; 申 (month) sits in the year void, 寅 (hour) in the day void.
            assert page.locator('.pillar-stage').count() == 8
            assert page.locator('.pillar').nth(1).locator('.void-mark').inner_text() == '年空'
            assert page.locator('.pillar').nth(3).locator('.void-mark').inner_text() == '日空'
            assert '星运帝旺自坐帝旺' in page.locator('.pillar.day-master').inner_text().replace('\n', '')
            # Relations between pillars as labelled brackets: stems above, branches below.
            assert sorted(page.locator('.pillar-links:not(.below) .pillar-link-label').all_inner_texts()) == ['庚甲相冲', '甲庚相冲']
            assert page.locator('.pillar-links.below .pillar-link-label').all_inner_texts() == ['申寅六冲·相刑']
            # 神煞 on each pillar, named by what places them (华盖 by the year branch 辰), and a table of rules and sources.
            assert [page.locator('.pillar').nth(i).locator('.shensha-tag').all_inner_texts() for i in range(4)] == [
                ['华盖'], ['驿马'], ['羊刃', '将星'], ['驿马']]
            assert page.locator('.pillar').nth(0).locator('.shensha-tag').get_attribute('title') == '查法起点：年支 辰'
            rules_rows = page.locator('#shensha-rules tbody tr')
            assert [rules_rows.nth(i).locator('td').first.inner_text() for i in range(rules_rows.count())] == ['羊刃', '驿马', '将星', '华盖']
            assert rules_rows.nth(1).locator('.shensha-where').all_inner_texts() == ['月柱甲申', '时柱庚寅']
            assert '《三命通会》卷三·论驿马' in rules_rows.nth(1).inner_text()
            # Decade and annual pillars under the BaZi chart; a year opens the Zi Wei year layer.
            page.locator('#luck-decade-0').wait_for(timeout=30000)
            assert page.locator('.luck-decade').count() == 9 and page.locator('.luck-year').count() == 10
            page.locator('#luck-decade-1').click()
            assert page.locator('#luck-decade-1').get_attribute('aria-pressed') == 'true'
            assert page.locator('#luck-year-2015').count() == 1
            # Each luck and year pillar against the natal chart: 午 is the same branch as the day pillar and punishes it.
            assert page.locator('#luck-decade-1 .luck-mark').all_inner_texts() == ['同日', '刑日']
            assert page.locator('#luck-decade-1 .luck-stage').inner_text() == '帝旺'
            natal_line = page.locator('.luck-natal').inner_text()
            assert '日柱丙：壬丙相冲' in natal_line and '日柱午：午午同支·相刑' in natal_line, natal_line
            assert natal_line.endswith('神煞 羊刃、将星、月德贵人'), natal_line
            assert page.locator('#luck-year-2015 .luck-mark').all_inner_texts() == ['合日']
            assert page.locator('#luck-year-2015').get_attribute('title').startswith('2015 乙未 · 星运 衰')
            assert '神煞 天乙贵人' in page.locator('#luck-year-2015').get_attribute('title')
            assert page.locator('#luck-decade-4 .luck-mark').all_inner_texts() == ['害年', '日空']  # 己卯
            # 五行生克: five phases, the 生 circle and the 克 star; the day master's phase is open first.
            assert page.locator('#wuxing .wx-node').count() == 5 and page.locator('#wuxing .wx-edge').count() == 10
            assert page.locator('#wuxing-fire').get_attribute('aria-checked') == 'true' and 'is-master' in page.locator('#wuxing-fire').get_attribute('class')
            assert [page.locator(f'#wuxing-{e} .wx-count').text_content() for e in ('wood', 'fire', 'earth', 'metal', 'water')] == ['2', '2', '1', '3', '0']
            detail = page.locator('#wuxing-detail').inner_text()
            assert '比劫' in detail and '日主 丙' in detail and '日干丙、日支午' in detail and '丙（时支寅）' in detail, detail
            # Each ten god of the phase with where it stands: stems other than the day stem, and hidden stems.
            flat = ' '.join(detail.split())
            assert '比肩 1 丙（时支寅）' in flat and '劫财 1 丁（日支午）' in flat, detail
            page.locator('#wuxing-water').click()
            detail = page.locator('#wuxing-detail').inner_text()
            assert page.locator('#wuxing-water').get_attribute('aria-checked') == 'true' and '官杀' in detail, detail
            assert '癸（年支辰）、壬（月支申）' in detail and page.locator('#wuxing .wx-edge.is-on').count() == 4, detail
            page.locator('#wuxing-water').focus()
            page.keyboard.press('ArrowRight')
            assert page.evaluate('document.activeElement.id') == 'wuxing-wood' and page.locator('#wuxing-wood').get_attribute('aria-checked') == 'true'
            assert '食伤' not in page.locator('#wuxing-detail').inner_text() and '印星' in page.locator('#wuxing-detail').inner_text()
            # One choice among five: a single tab stop, which End, Home and the up arrow move too.
            assert page.locator('#wuxing [role=radio][tabindex="0"]').count() == 1 and page.locator('#wuxing svg').get_attribute('role') == 'radiogroup'
            for key, phase in (('End', 'water'), ('Home', 'wood'), ('ArrowUp', 'water'), ('ArrowDown', 'wood')):
                page.keyboard.press(key)
                assert page.evaluate('document.activeElement.id') == f'wuxing-{phase}' and page.locator(f'#wuxing-{phase}').get_attribute('tabindex') == '0', key
            page.locator('#wuxing').screenshot(path=str(screenshot_dir / '46-wuxing.png'))
            page.locator('#wuxing-fire').click()
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
            page.locator('#group-extra-gender').select_option('female')
            page.locator('#group-extra-add').click()
            assert '女' in page.locator('.group-extra').inner_text()
            page.evaluate("() => { groupDraft.year = 2026; }")  # the device year would make the luck section vary
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
            # The result copies as text: pillars, the ten-god matrix and every pair, with the names as typed and no notes.
            group_text = page.locator('#group-text-text').text_content()
            assert group_text.startswith('玄枢 · 多人关系对照\n\n【四柱】\n') and '【日干十神】' in group_text, group_text
            assert group_text.split('【三合】')[0].count(' ↔ ') == 3, group_text
            labels = page.evaluate("groupResult.members.map(m => m.label)")
            assert all(label + ' ↔ ' in group_text or ' ↔ ' + label in group_text for label in labels), group_text
            assert all(n not in group_text for n in ('表姐', '一起做项目', '本人', '1992-06-06')), group_text
            matrix = group_text.split('【日干十神】')[1].split('\n')[2:5]
            assert [row.split()[0] for row in matrix] == labels and all(len(row.split()) == 4 for row in matrix), matrix
            page.evaluate('''() => {window.copiedText = null; Object.defineProperty(navigator, 'clipboard', {configurable: true,
              value: {writeText: async () => {throw new Error('denied');}}});}''')
            page.locator('#group-text-copy').click()
            page.locator('#group-text-copy', has_text='已选中文字').wait_for(timeout=10000)
            assert page.locator('#group-text details[open]').count() == 1 and page.evaluate('getSelection().toString()') == group_text
            page.evaluate("() => {navigator.clipboard.writeText = async text => {window.copiedText = text;};}")
            page.locator('#group-text-copy').click()
            page.locator('#group-text-copy', has_text='已复制').wait_for(timeout=10000)
            assert page.evaluate('window.copiedText') == group_text
            # Each member's five phases: the table matches the server's counts, and the copy lists them too.
            assert page.locator('#group-elements-matrix tbody tr').count() == 3 and page.locator('#group-elements-matrix .em-cell').count() == 15
            assert page.evaluate("groupResult.members.every(m => PHASES.split('').every(e => personElements(m)[e] === m.surface_five_elements[e]))")
            assert page.locator('#group-elements-matrix .em-master').count() == page.evaluate('groupResult.members.filter(m => m.day_master).length')
            assert '\n各人（四柱天干地支，不含藏干）：\n' in group_text, group_text
            # Luck and year pillars by year: one card per member; a member without a gender gets the year pillar only.
            year_text = group_text.split('【2026 丙午年 · 大运流年】')[1]
            assert '同事（女，34 岁）\n　大运：壬寅 劫财，2022 年交运\n　流年：正财：' in year_text, year_text
            assert '既有档案（性别未填，26 岁）\n　大运：未填性别，不排大运' in year_text, year_text
            assert '\n大运时间轴（2022–2036）：\n' in year_text and '\n　既有档案：未填性别，不排大运' in year_text, year_text
            assert '\n　同事：' in year_text and ' → ' in year_text.split('\n　同事：')[1].split('\n')[0], year_text
            cards = page.locator('.group-year-card')
            assert cards.count() == 3 and '2026 流年 丙午' in page.locator('.group-year-title').inner_text()
            coworker = cards.nth(2).inner_text()
            assert '壬寅' in coworker.replace('\n', '') and '交运年 2022' in coworker and '咸池' in coworker, coworker
            assert '未填性别，不排大运' in cards.nth(1).inner_text()
            page.locator('#group-year-next').click()
            page.wait_for_function("() => groupResult.year_view.year === 2027 && !groupYearPending", timeout=30000)
            assert '2027 流年 丁未' in page.locator('.group-year-title').inner_text()
            assert page.evaluate('document.activeElement.id') == 'group-year-next'
            assert page.evaluate("groupResult.members.length") == 3 and page.locator('.group-member').count() == 3
            page.locator('#group-year-input').fill('1800')
            page.locator('#group-year-input').dispatch_event('change')
            page.locator('#group-year .inline-msg', has_text='1901 到 2099').wait_for(timeout=10000)
            assert page.evaluate("groupResult.year_view.year") == 2027
            page.locator('#group-year').screenshot(path=str(screenshot_dir / '40-group-years.png'))
            # An unknown hour can leave two possible start years; both are shown, never "null".
            assert page.evaluate("luckText({status: 'not_started', start_year: null, start_years: [1996, 1997]})") == '未起运，1996 或 1997 年起运'
            assert page.evaluate("(() => {const box = document.createElement('div'); luckLine(box, {status: 'not_started', start_year: null, start_years: [1996, 1997]}, '大运'); return box.textContent;})()") == '大运未起运 · 起运年 1996 / 1997 （随时辰而定）'
            # Stepping to 2099 disables the 下一年 button that was used; keyboard focus moves to the year field.
            page.locator('#group-year-input').fill('2098')
            page.locator('#group-year-input').dispatch_event('change')
            page.wait_for_function("() => groupResult.year_view.year === 2098 && !groupYearPending", timeout=30000)
            page.locator('#group-year-next').click()
            page.wait_for_function("() => groupResult.year_view.year === 2099 && !groupYearPending", timeout=30000)
            assert page.locator('#group-year-next').is_disabled() and page.evaluate('document.activeElement.id') == 'group-year-input'
            # Slow replies. A year switched while 对照关系 runs asks for the run's members, not the ones shown.
            page.evaluate("() => { window.__post = postJSON; postJSON = async (...args) => { await new Promise(r => setTimeout(r, 800)); return window.__post(...args); }; }")
            page.locator('#group-current').uncheck()
            page.locator('#group-run').click()
            page.locator('#group-year-prev').click()
            page.wait_for_function("() => groupResult.year_view.year === 2098 && !groupYearPending && !groupRun", timeout=30000)
            assert page.evaluate("groupResult.members.length") == 2 and '成员已改变' not in page.locator('#result').inner_text()
            page.locator('#group-current').check()
            page.locator('#group-run').click()
            page.wait_for_function("() => !groupRun && groupResult.members.length === 3", timeout=30000)
            # Two quick steps count from the year asked for, not the one still shown.
            page.locator('#group-year-prev').click()
            page.locator('#group-year-prev').click()
            assert page.locator('#group-year-input').input_value() == '2096' and page.locator('.group-year-status').inner_text() == '正在换年…'
            page.wait_for_function("() => groupResult.year_view.year === 2096 && !groupYearPending", timeout=30000)
            # A year being typed when a reply arrives is kept, still focused, with no error.
            page.locator('#group-year-prev').click()
            page.locator('#group-year-input').fill('20')
            page.wait_for_function("() => groupResult.year_view.year === 2095 && !groupYearPending", timeout=30000)
            page.wait_for_timeout(100)
            assert page.locator('#group-year-input').input_value() == '20' and page.evaluate('document.activeElement.id') == 'group-year-input'
            assert page.locator('#group-year .inline-msg').count() == 0
            page.evaluate("() => { postJSON = window.__post; }")
            page.locator('#group-year-input').fill('2026')
            page.locator('#group-year-input').dispatch_event('change')
            page.wait_for_function("() => groupResult.year_view.year === 2026 && !groupYearPending", timeout=30000)
            # The luck timeline: a row per member over fifteen years; a year opens its cards, the arrows only move the window.
            assert page.locator('#group-timeline tbody tr').count() == 3 and page.locator('#group-timeline thead .tl-year').count() == 15
            assert page.locator('#group-timeline-year-2026').get_attribute('aria-pressed') == 'true'
            assert page.locator('#group-timeline .luck-timeline-range').inner_text() == '2022–2036'
            assert '未填性别，不排大运' in page.locator('#group-timeline tbody tr').nth(1).inner_text()
            # The arrows move the window at once, also past the open year, and the text preview lists the same years.
            timeline_range = lambda: page.locator('#group-timeline .luck-timeline-range').inner_text()
            page.locator('#group-timeline-forward').click()
            assert timeline_range() == '2027–2041' and page.evaluate('document.activeElement.id') == 'group-timeline-forward'
            assert '\n大运时间轴（2027–2041）：\n' in page.locator('#group-text-text').text_content()
            for expected in ('2022–2036', '2017–2031', '2012–2026', '2007–2021'):
                page.locator('#group-timeline-back').click()
                assert timeline_range() == expected and page.evaluate('document.activeElement.id') == 'group-timeline-back'
            for _ in range(3):
                page.locator('#group-timeline-forward').click()
            assert timeline_range() == '2022–2036'
            # With an unknown hour the twelfth period may end a year later: that year is a "?", not "已排完".
            row = "{status: 'ok', born_year: 1917, periods: [{pillar: '丁酉', start_years: [2026, 2027], end_years: [2035, 2036]}, {pillar: '戊戌', start_years: [2036, 2037], end_years: [2045, 2046]}]}"
            assert page.evaluate(f"(() => {{ const row = {row}; return [2045, 2046, 2047].map(y => luckAt(row, y).kind).concat([luckAt(row, 2046).after]); }})()") == ['period', 'maybe', 'beyond', None]
            assert page.evaluate(f"luckSpanText({row}, 2042, 2056)") == '戊戌 2036/2037–2045/2046 → 已排完（时辰不详，交运年有两种可能）'
            assert page.evaluate(f"luckSpanText({{...{row}, periods: [{{pillar: '甲子', start_years: [1990, 1991], end_years: [1999]}}, {{pillar: '乙丑', start_years: [2000], end_years: [2009]}}]}}, 2003, 2017)") == '乙丑 2000–2009 → 已排完'
            page.locator('#group-timeline-year-2030').click()
            page.wait_for_function("() => groupResult.year_view.year === 2030 && !groupYearPending", timeout=30000)
            assert page.evaluate('document.activeElement.id') == 'group-timeline-year-2030'
            assert page.locator('#group-timeline-year-2030').get_attribute('aria-pressed') == 'true' and '2030 流年 庚戌' in page.locator('.group-year-title').inner_text()
            assert page.locator('#group-timeline .luck-timeline-range').inner_text() == '2022–2036'
            page.locator('#group-timeline-forward').click()
            assert page.locator('#group-timeline .luck-timeline-range').inner_text() == '2027–2041' and page.evaluate('document.activeElement.id') == 'group-timeline-forward'
            assert page.evaluate('groupResult.year_view.year') == 2030 and page.locator('#group-timeline .tl-change').count() >= 1
            page.locator('#group-timeline').screenshot(path=str(screenshot_dir / '42-group-timeline.png'))
            # At the end of the range the pressed arrow turns off and focus moves to the other one.
            while not page.locator('#group-timeline-forward').is_disabled():
                page.locator('#group-timeline-forward').click()
            assert timeline_range() == '2085–2099' and page.evaluate('document.activeElement.id') == 'group-timeline-back'
            # Opening another year puts the window back around it.
            page.locator('#group-year-input').fill('2026')
            page.locator('#group-year-input').dispatch_event('change')
            page.wait_for_function("() => groupResult.year_view.year === 2026 && !groupYearPending", timeout=30000)
            assert timeline_range() == '2022–2036'
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
            assert '\n也请对照这一年的大运流年：2026\n' in draft and ' · 女' in draft, draft
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
            # The relation card is drawn on this device: names, pillars and labels, never notes, birth dates or times.
            check_relation_card(page, 'group', screenshot_dir / '44-group-card.png')
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
            assert page.locator('#ziwei-board path.fly:not(.in)').count() == 3
            assert page.locator('#palace-3 .fly-mark.fly-lu').inner_text() == '禄入' and page.locator('#palace-6 .fly-mark').inner_text() == '自化权'
            assert page.locator('#palace-10 .fly-mark.fly-ke').count() == 1 and page.locator('#palace-2 .fly-mark.fly-ji').count() == 1
            page.locator('#ziwei-fly-toggle').click()
            assert page.locator('#ziwei-board path.fly').count() == 0 and page.locator('.fly-mark').count() == 0
            assert page.locator('#ziwei-fly-toggle').get_attribute('aria-pressed') == 'false'
            page.locator('#ziwei-fly-toggle').click()
            assert page.locator('#ziwei-board path.fly:not(.in)').count() == 3
            # The panel lists the reverse direction too: 紫微 and 文曲 sit in 午, so 乙 (酉) sends 紫微化科,
            # 辛 (巳) sends 文曲化科 and both 己 palaces send 文曲化忌; 午's own 壬 紫微化权 is a self-transformation.
            fly_in = page.locator('.palace-panel .fly-in').inner_text()
            assert fly_in.startswith('飞入本宫：') and page.locator('.palace-panel .fly-in .fly-item').count() == 4, fly_in
            assert all(item in fly_in for item in ('田宅宫（乙干）紫微化科', '兄弟宫（辛干）文曲化科', '疾厄宫（己干）文曲化忌', '子女宫（己干）文曲化忌')), fly_in
            # Each entry brings out its own curve: the incoming ones are hidden until pointed at, a click keeps one lit.
            assert page.locator('#ziwei-board path.fly.in').count() == 4 and not page.locator('#ziwei-board path.fly.in').first.is_visible()
            page.locator('.fly-in .fly-item', has_text='田宅宫').hover()
            hot = '#ziwei-board path.fly.is-hot[data-key="in|田宅宫|紫微化科"]'
            assert page.locator(hot).is_visible() and page.locator('#ziwei-board.fly-focus').count() == 1
            assert page.locator('.palace.fly-end').evaluate_all('els => els.map(el => el.id).sort()') == ['palace-6', 'palace-9']
            page.mouse.move(5, 5)
            assert page.locator('#ziwei-board.fly-focus').count() == 0 and not page.locator('#ziwei-board path.fly.in').first.is_visible()
            page.locator('.fly-in .fly-item', has_text='田宅宫').click()
            page.mouse.move(5, 5)
            assert page.locator(hot).is_visible() and page.locator('.fly-in .fly-item[aria-pressed="true"]').count() == 1
            page.locator('#ziwei-board').screenshot(path=str(screenshot_dir / '43-ziwei-fly-highlight.png'))
            page.locator('.palace-panel').screenshot(path=str(screenshot_dir / '44-ziwei-panel-fly.png'))
            # Hiding the curves drops the kept highlight and turns the entries back into text.
            page.locator('#ziwei-fly-toggle').click()
            assert page.locator('#ziwei-board.fly-focus').count() == 0 and page.locator('.fly-item').count() == 0
            assert page.locator('.palace.fly-end').count() == 0 and '田宅宫（乙干）紫微化科' in page.locator('.palace-panel .fly-in').inner_text()
            page.locator('#ziwei-fly-toggle').click()
            assert page.locator('.fly-item[aria-pressed="true"]').count() == 0 and page.locator('#ziwei-board.fly-focus').count() == 0
            page.locator('#palace-6').focus()
            assert page.locator('#ziwei-board.fly-focus').count() == 0 and page.locator('.fly-item[aria-pressed="true"]').count() == 0
            page.locator('.fly-out .fly-item', has_text='天梁化禄').focus()
            assert page.locator('#ziwei-board path.fly.is-hot[data-key="out|天梁化禄"]').count() == 1
            page.locator('#palace-6').focus()
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
            assert page.locator('#ziwei-board path.fly:not(.layer):not(.in)').count() == 3
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
            # 2016 丙 inside the 辛 decade of a 庚 birth year: three stars carry two transformations each.
            overlap = page.locator('.hua-overlap-item').all_inner_texts()
            assert overlap == ['太阳（生年化禄、大限化权）', '天同（生年化忌、流年化禄）', '文昌（大限化忌、流年化科）'], overlap
            assert page.locator('#ziwei-board .star.hua-stack').count() == 3
            # The layer table lists the decade and small limit in force that year next to the year itself.
            heads = "[...document.querySelectorAll('#ziwei-layer-table thead th')].map(th => th.textContent)"
            assert page.evaluate(heads) == ['宫干支', '本命', '大限', '小限', '流年']
            page.screenshot(path=str(screenshot_dir / '31-ziwei-annual-layer.png'), full_page=True)
            # Month and day layers come from the engine for any date; the stack lists every layer in force that day.
            page.locator('#ziwei-layer-month').click()
            page.locator('#ziwei-layer-date').fill('2026-10-11')
            page.locator('.layer-label', has_text='2026年九月 · 戊戌月').wait_for(timeout=30000)
            assert page.locator('#palace-10.layer-anchor').count() == 1 and page.locator('#ziwei-layer-stack .layer-stack-row').count() == 5
            assert page.locator('#ziwei-board .hua.layer').count() == 4 and '流月四化（戊干）' in page.locator('.palace-panel').inner_text()
            assert page.locator('#ziwei-board .flow-star', has_text='月禄').count() == 1 and page.locator('#palace-5 .flow-star', has_text='月禄').count() == 1
            # The month stacks on the 庚 decade, the 丙 year and the 庚 birth year.
            overlap = page.locator('.hua-overlap-item').all_inner_texts()
            assert overlap == ['太阳（生年化禄、大限化禄）', '武曲（生年化权、大限化权）', '太阴（生年化科、大限化科、流月化权）',
                               '天同（生年化忌、大限化忌、流年化禄）', '天机（流年化权、流月化忌）'], overlap
            # Every layer side by side: each row one palace, each layer's 命宫 highlighted, rows pick the palace on the board.
            page.locator('#ziwei-layer-table summary').click()
            assert page.evaluate(heads) == ['宫干支', '本命', '大限', '小限', '流年', '流月', '流日']
            assert page.locator('#ziwei-layer-table td.layer-ming').count() == 6 and page.locator('.layer-table-hua').count() == 24
            assert page.locator('#ziwei-layer-table tbody tr').nth(2).locator('td.layer-ming').count() == 1  # 庚辰: the decade's 命宫
            page.locator('#layer-table-pick-3').click()
            assert page.locator('#palace-3.selected').count() == 1 and page.locator('#ziwei-layer-table[open]').count() == 1
            assert page.locator('#ziwei-layer-table tbody tr.selected th').inner_text() == '己卯'
            page.evaluate('''() => {window.copiedText = null; Object.defineProperty(navigator, 'clipboard', {configurable: true,
              value: {writeText: async text => {window.copiedText = text;}}});}''')
            page.locator('#ziwei-layer-table-copy').click()
            page.locator('#ziwei-layer-table-copy', has_text='已复制表格').wait_for(timeout=10000)
            tsv = page.evaluate('window.copiedText').split('\n')
            assert tsv[0] == '宫干支\t本命\t大限\t小限\t流年\t流月\t流日' and len(tsv) == 13
            assert '己卯\t子女宫 太阳化禄\t兄弟宫 太阳化禄\t疾厄宫 太阳化忌\t子女宫\t仆役宫\t官禄宫' in tsv, tsv
            page.screenshot(path=str(screenshot_dir / '41-ziwei-layer-table.png'), full_page=True)
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
            page.locator('#share-bazi').check()
            # Text chart: common chart notation; decade ages (which reveal gender) only with 乾造/坤造 ticked.
            page.locator('#share-view-text').click()
            assert page.locator('#share-canvas').is_hidden() and page.locator('#share-download').is_hidden()
            share_text = "document.querySelector('#share-text').textContent"
            text_chart = page.evaluate(share_text)
            assert '干支：庚辰　　甲申　　丙午　　庚寅' in text_chart and '空亡：月柱申（年空），时柱寅（日空）' in text_chart, text_chart
            assert '命宫在壬午，身宫在官禄宫，木三局，命主破军，身主文昌' in text_chart and '大限' not in text_chart and '坤造' not in text_chart
            assert '天干关系：年月 庚甲相冲　月时 甲庚相冲' in text_chart and '地支关系：月时 申寅六冲·相刑' in text_chart
            assert '\n神煞：年柱 华盖｜月柱 驿马｜日柱 羊刃、将星｜时柱 驿马\n' in text_chart, text_chart
            page.locator('#share-gender').check()
            text_chart = page.evaluate(share_text)
            assert '坤造' in text_chart and '命宫（壬午）：紫微庙｜文曲陷 凤阁 蜚廉｜大限 3–12' in text_chart
            assert '官禄宫（丙戌，身宫）：廉贞利 天府庙｜' in text_chart and '田宅宫（乙酉）：空宫｜' in text_chart
            # With the gender shown the luck decades follow, with their marks; calendar years only when the date is shown too.
            page.wait_for_function("() => document.querySelector('#share-text').textContent.includes('大运：逆排')", timeout=30000)
            text_chart = page.evaluate(share_text)
            assert '\u3000起运 13\u3000壬午\u3000七杀\u3000星运帝旺\u3000同日\u3000刑日' in text_chart and '2013–2022' not in text_chart
            page.locator('#share-date').check()
            assert '\u3000起运 13\u3000壬午\u3000七杀\u3000星运帝旺\u30002013–2022\u3000同日' in page.evaluate(share_text)
            page.locator('#share-date').uncheck()
            # The page runs from set_content (no secure origin), so the clipboard is stubbed: first refused, then allowed.
            page.evaluate('''() => {window.copiedText = null; Object.defineProperty(navigator, 'clipboard', {configurable: true,
              value: {writeText: async () => {throw new Error('denied');}}});}''')
            page.locator('#share-copy-text').click()
            page.locator('#share-copy-text', has_text='已选中文字').wait_for(timeout=10000)
            assert page.evaluate('getSelection().toString()') == text_chart
            page.evaluate("() => {navigator.clipboard.writeText = async text => {window.copiedText = text;};}")
            page.locator('#share-copy-text').click()
            page.locator('#share-copy-text', has_text='已复制文字盘').wait_for(timeout=10000)
            assert page.evaluate('window.copiedText') == text_chart
            page.locator('#share-gender').uncheck()
            assert page.locator('#share-copy-text').inner_text() == '复制文字盘'
            # A language applied while the dialog is open (its table was still loading) regenerates the text chart.
            page.evaluate("applyLoadedLanguage('zh-TW')")
            assert '命宮在壬午' in page.evaluate(share_text)
            page.evaluate("applyLoadedLanguage('zh-CN')")
            assert '命宫在壬午' in page.evaluate(share_text) and '注：紫微为部分排盘' in page.evaluate(share_text)
            page.locator('#share-close').click()
            # The system share sheet gets the prepared PNG (stubbed here; headless Linux has none).
            page.evaluate('''() => {window.sharedFiles = null; navigator.canShare = () => true;
              navigator.share = async data => {window.sharedFiles = data.files.map(f => f.name + ' ' + f.type).join();};}''')
            page.locator('#share-card').click()
            page.locator('#share-view-image').click()
            assert page.locator('#share-copy-text').is_hidden()
            page.locator('#share-system:not([disabled])').click(timeout=10000)
            page.wait_for_function("() => window.sharedFiles === 'xuanshu-card.png image/png'", timeout=10000)
            page.locator('#share-close').click()
            # The text chart pastes back into the import check: every recognized field agrees.
            page.locator('[data-tab="import-check"]').click()
            page.locator('#import-text').fill(text_chart)
            page.locator('#import-check-run').click()
            page.locator('.import-table').wait_for(timeout=30000)
            assert '识别到的字段全部一致' in page.locator('#result').inner_text() and '已识别字段 35' in page.locator('#result').inner_text()
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
            assert page.locator('#crosscheck-dialog .crosscheck-table tbody tr').count() == 41
            assert page.locator('#crosscheck-dialog h4', has_text='八字神煞对照').count() == 1
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
            # The noon placeholder carries no 神煞, and the rule table leaves it out (午 would otherwise be a 将星 there).
            assert page.locator('.pillar').nth(3).locator('.pillar-shensha').inner_text().replace('\n', '') == '神煞时辰不详'
            assert '时柱' not in page.locator('#shensha-rules').inner_text()
            # Luck and year pillars are not read against the placeholder hour pillar.
            page.locator('#luck-decade-0').wait_for(timeout=30000)
            assert page.locator('.luck-mark').count() > 0 and not any(t.endswith('时') for t in page.locator('.luck-mark').all_inner_texts())
            # The five phases count the three known pillars only; a new chart opens its own day master's phase.
            assert sum(int(page.locator(f'#wuxing-{e} .wx-count').text_content()) for e in ('wood', 'fire', 'earth', 'metal', 'water')) == 6
            assert page.locator('#wuxing-water').get_attribute('aria-checked') == 'true' and '时柱' not in page.locator('#wuxing-detail').inner_text()
            assert '时辰不详，时柱按 12:00 占位，不计入。' in page.locator('#result').inner_text()
            page.screenshot(path=str(screenshot_dir / '32-hour-unknown.png'), full_page=True)
            # Without the hour there is no decade: not as a layer, and not in the year layer's stacked transformations.
            page.locator('[data-tab="ziwei"]').click()
            page.locator('#ziwei-layer-decade').click()
            assert '时辰不详时无法确定' in page.locator('#result').inner_text() and page.locator('.palace-layer').count() == 0
            page.locator('#ziwei-layer-year').click()
            page.locator('.hua-overlap').wait_for(timeout=30000)
            assert '大限' not in page.locator('.hua-overlap').inner_text()
            assert page.locator('#ziwei-layer-table').count() == 0 and '不列各层宫位对照表' in page.locator('#result').inner_text()
            page.locator('#ziwei-layer-natal').click()
            page.locator('[data-tab="bazi"]').click()
            # 2000-02-04 has 立春 at 20:40: with the hour unknown the year and month pillars, and so the stars, are open.
            page.locator('#birth_datetime').fill('2000-02-04T12:00')
            page.locator('#run-btn').click()
            page.wait_for_function("() => document.querySelector('#result-subtitle').textContent.startsWith('2000-02-04')", timeout=30000)
            cells = [page.locator('.pillar').nth(i).locator('.pillar-shensha').inner_text().replace('\n', '') for i in range(4)]
            assert cells == ['神煞随时辰而定'] * 3 + ['神煞时辰不详'], cells
            assert page.locator('#shensha-rules').count() == 0 and '神煞也随之不同，这里不列' in page.locator('#result').inner_text()
            # The five phases count only the day pillar then; the day master is settled, so the ten gods stay.
            assert sum(int(page.locator(f'#wuxing-{e} .wx-count').text_content()) for e in ('wood', 'fire', 'earth', 'metal', 'water')) == 2
            assert page.locator('#wuxing .is-master').count() == 1 and '出生当天立春，年柱、月柱随时辰而定。这三柱都不计入。' in page.locator('#result').inner_text()
            assert '藏干元素出现次数（不加权）：木1 · 火0 · 土1 · 金0 · 水1' in page.locator('#result').inner_text()  # 戊乙癸 of 壬辰
            # With the 23:00 day change the day pillar is open as well: nothing is counted and no day master names ten gods.
            page.evaluate("document.querySelector('#late_zi_day_rollover').checked = true")
            page.locator('#run-btn').click()
            page.wait_for_function("() => document.querySelector('#wuxing') && !document.querySelector('#wuxing .is-master')", timeout=30000)
            assert page.locator('#wuxing .wx-group').count() == 0 and '比肩' not in page.locator('#wuxing-detail').inner_text()
            assert '这四柱都不计入，日主未定，也不标十神。' in page.locator('#result').inner_text()
            page.evaluate("document.querySelector('#late_zi_day_rollover').checked = false")
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
            page.evaluate("() => { pairDraft.year = 2026; }")  # the device year would make the luck section vary
            page.locator('#pair_gender').select_option('female')
            page.locator('#pair-run').click()
            page.locator('#ziwei-pair-grid tbody tr').first.wait_for(timeout=30000)
            # The same luck and year-pillar cards as the group page, for A and B, switchable by year.
            assert page.locator('#pair-year .group-year-card').count() == 2 and '2026 流年 丙午' in page.locator('#pair-year').inner_text()
            assert page.evaluate("pairResult.year_view.members[1].gender") == 'female' and '女' in page.locator('#pair-year-card-1').inner_text()
            assert page.locator('#pair-timeline tbody tr').count() == 2 and page.locator('#pair-timeline-year-2026').get_attribute('aria-pressed') == 'true'
            page.locator('#pair-year-next').click()
            page.wait_for_function("() => pairResult.year_view.year === 2027 && !pairYearPending", timeout=30000)
            assert page.evaluate('document.activeElement.id') == 'pair-year-next' and page.locator('#ziwei-pair-grid').count() == 1
            assert '【2027 丁未年 · 大运流年】' in page.locator('#pair-text-text').text_content()
            page.locator('#pair-year').screenshot(path=str(screenshot_dir / '41-pair-years.png'))
            page.locator('#pair-year-prev').click()
            page.wait_for_function("() => pairResult.year_view.year === 2026 && !pairYearPending", timeout=30000)
            # A year switched while 比较两人命盘 runs is fetched for the new pair once the run's reply arrives.
            page.evaluate("() => { window.__post = postJSON; postJSON = async (...args) => { await new Promise(r => setTimeout(r, 800)); return window.__post(...args); }; }")
            page.locator('#pair_gender').select_option('male')
            page.locator('#pair-run').click()
            page.locator('#pair-year-next').click()
            assert page.locator('#pair-year-input').input_value() == '2027' and page.locator('#pair-run').is_disabled()
            page.wait_for_function("() => pairResult.year_view.year === 2027 && !pairYearPending && !pairRunning && pairResult.year_view.members[1].gender === 'male'", timeout=30000)
            assert 'A 或 B 的资料已改变' not in page.locator('#result').inner_text() and page.locator('#ziwei-pair-grid').count() == 1
            page.evaluate("() => { postJSON = window.__post; }")
            page.locator('#pair_gender').select_option('female')
            page.locator('#pair-run').click()
            page.wait_for_function("() => !pairRunning && pairResult.year_view.members[1].gender === 'female'", timeout=30000)
            page.locator('#pair-year-prev').click()
            page.wait_for_function("() => pairResult.year_view.year === 2026 && !pairYearPending", timeout=30000)
            # A run's reply that then asks for another year does not redraw another open tab.
            page.evaluate("() => { window.__post = postJSON; postJSON = async (...args) => { await new Promise(r => setTimeout(r, 800)); return window.__post(...args); }; }")
            page.locator('#pair-run').click()
            page.locator('#pair-year-next').click()
            page.locator('[data-tab="calendar"]').click()
            page.evaluate("() => { document.querySelector('#result').firstElementChild.dataset.mark = 'kept'; }")
            page.wait_for_function("() => !pairRunning && !pairYearPending && pairResult.year_view.year === 2027", timeout=30000)
            assert page.evaluate("document.querySelector('#result').firstElementChild.dataset.mark") == 'kept'
            page.evaluate("() => { postJSON = window.__post; }")
            page.locator('[data-tab="pair"]').click()
            # A year that fails to load is not used by the next run.
            page.evaluate("() => { window.__post = postJSON; postJSON = async (url, body) => { if (url === '/api/pair' && body.year === 2028) { postJSON = window.__post; throw new Error('offline'); } return window.__post(url, body); }; }")
            page.locator('#pair-year-next').click()
            page.locator('#pair-year .inline-msg', has_text='换年失败').wait_for(timeout=10000)
            assert page.evaluate("pairDraft.year") == 2027 and page.locator('#pair-year-input').input_value() == '2027'
            # A year typed but not entered goes with the 比较两人命盘 click that follows it, and steps count from it.
            page.locator('#pair-year-input').fill('2031')
            box = page.locator('#pair-run').bounding_box()  # a slow press: the field's change runs before the release
            page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
            page.mouse.down()
            page.wait_for_timeout(150)
            page.mouse.up()
            page.wait_for_function("() => !pairRunning && !pairYearPending && pairResult.year_view.year === 2031", timeout=30000)
            assert page.locator('#pair-year-input').input_value() == '2031'
            page.locator('#pair-year-input').fill('2025')
            page.locator('#pair-year-next').click()
            page.wait_for_function("() => pairResult.year_view.year === 2026 && !pairYearPending", timeout=30000)
            # The two people can go to the AI chat as a draft, as on the group page; another year replaces that draft.
            assert page.locator('#pair-ask-ai').is_disabled() and 'AI 对话尚未启用' in page.locator('#result .group-ask').inner_text()
            page.evaluate("() => { chatStatus.enabled = true; chatDraft = ''; chatThirdPartyBirths = []; }")
            page.locator('[data-tab="calendar"]').click()
            page.locator('[data-tab="pair"]').click()
            page.locator('#pair-ask-ai:not([disabled])').click()
            page.locator('[data-tab="chat"][aria-selected="true"]').wait_for(timeout=30000)
            draft = page.locator('#chat-input').input_value()
            assert draft.startswith('请结合双人对照') and draft.count('\n- ') == 2 and '\n也请对照这一年的大运流年：2026\n- A · ' in draft, draft
            assert draft.endswith('\n- B · 2001-01-01 12:00 · Asia/Shanghai · 女'), draft
            assert page.locator('#chat-send').is_disabled() and page.locator('#chat-consent-needed').is_visible()
            page.screenshot(path=str(screenshot_dir / '43-pair-to-chat.png'), full_page=True)
            page.locator('[data-tab="pair"]').click()
            page.locator('#pair-year-next').click()
            page.wait_for_function("() => pairResult.year_view.year === 2027 && !pairYearPending", timeout=30000)
            page.locator('#pair-ask-ai:not([disabled])').click()
            page.locator('[data-tab="chat"][aria-selected="true"]').wait_for(timeout=30000)
            draft = page.locator('#chat-input').input_value()
            assert draft.count('请结合双人对照') == 1 and '大运流年：2027\n' in draft and '2026' not in draft, draft
            # Renaming B or rewriting the hour keeps the consent check: it looks for B's birth date, not the whole line.
            page.locator('#chat-input').fill(draft.replace('- B · ', '- 我女朋友 · ').replace('12:00', '约中午'))
            assert page.locator('#chat-send').is_disabled() and page.locator('#chat-consent-needed').is_visible()
            # A alone is the current chart, which the chat already uses: no consent needed for that line.
            page.locator('#chat-input').fill('\n'.join(line for line in draft.split('\n') if not line.startswith('- B · ')))
            assert page.locator('#chat-consent-needed').count() == 0 and not page.locator('#chat-send').is_disabled()
            page.locator('#chat-input').fill(draft)
            # B corrected and compared again: the new draft replaces the earlier one instead of adding a second B.
            page.locator('[data-tab="pair"]').click()
            page.locator('#pair_gender').select_option('male')
            page.locator('#pair-run').click()
            page.wait_for_function("() => !pairRunning && !pairYearPending && pairResult.year_view.members[1].gender === 'male'", timeout=30000)
            page.locator('#pair-ask-ai:not([disabled])').click()
            page.locator('[data-tab="chat"][aria-selected="true"]').wait_for(timeout=30000)
            draft = page.locator('#chat-input').input_value()
            assert draft.count('请结合双人对照') == 1 and draft.endswith('\n- B · 2001-01-01 12:00 · Asia/Shanghai · 男') and draft.count('- B · ') == 1, draft
            # While another year loads the button is off; a year typed but not entered is loaded first and the draft follows it.
            page.locator('[data-tab="pair"]').click()
            page.evaluate("() => { window.__post = postJSON; postJSON = async (url, body) => { await new Promise(r => setTimeout(r, 400)); return window.__post(url, body); }; }")
            page.locator('#pair-year-next').click()
            assert page.locator('#pair-ask-ai').is_disabled()
            assert page.locator('#pair-card').is_disabled()
            page.wait_for_function("() => pairResult.year_view.year === 2028 && !pairYearPending", timeout=30000)
            page.evaluate("() => { postJSON = window.__post; }")
            page.locator('#pair-year-input').fill('2030')
            page.locator('#pair-ask-ai:not([disabled])').click()
            page.locator('[data-tab="chat"][aria-selected="true"]').wait_for(timeout=30000)
            draft = page.locator('#chat-input').input_value()
            assert draft.count('请结合双人对照') == 1 and '大运流年：2030\n' in draft and page.evaluate('pairResult.year_view.year') == 2030, draft
            page.locator('[data-tab="pair"]').click()
            page.locator('#pair_gender').select_option('female')
            page.locator('#pair-run').click()
            page.wait_for_function("() => !pairRunning && !pairYearPending && pairResult.year_view.members[1].gender === 'female'", timeout=30000)
            page.evaluate("() => { chatStatus.enabled = false; chatDraft = ''; chatThirdPartyBirths = []; }")
            page.locator('[data-tab="pair"]').click()
            page.locator('#pair-year-input').fill('2026')
            page.locator('#pair-year-input').dispatch_event('change')
            page.wait_for_function("() => pairResult.year_view.year === 2026 && !pairYearPending", timeout=30000)
            check_relation_card(page, 'pair', screenshot_dir / '45-pair-card.png')
            # A year typed but not entered is loaded before the card opens, so the card shows the year the page shows;
            # closing returns focus to the redrawn button.
            page.locator('#pair-year-input').fill('2031')
            page.locator('#pair-card').click()
            page.locator('#relation-card-dialog[open]').wait_for(timeout=30000)
            assert page.evaluate('pairResult.year_view.year') == 2031 and page.locator('#pair-year-input').input_value() == '2031'
            page.keyboard.press('Escape')
            page.wait_for_function("() => document.activeElement && document.activeElement.id === 'pair-card'", timeout=10000)
            page.locator('#pair-year-input').fill('2026')
            page.locator('#pair-year-input').dispatch_event('change')
            page.wait_for_function("() => pairResult.year_view.year === 2026 && !pairYearPending", timeout=30000)
            # 4 pillar rows + every labelled branch link + 12 branch rows + 8 cross-chart transformations, besides the luck timeline
            # and the two rows of five phases.
            links = page.evaluate('pairResult.branch_links.length')
            assert links >= 1 and page.locator('#result tbody tr').count() - page.locator('#pair-timeline tbody tr').count() == 4 + links + 12 + 8 + 2
            assert page.locator('#pair-elements tbody tr').count() == 2 and page.locator('#pair-elements .em-master').count() == 2
            assert page.locator('#pair-elements tbody tr').first.locator('.em-master small').inner_text() == '日主 · 比劫'
            assert page.locator('.meta-tags span', has_text='A 命宫落在 B 的').count() == 1
            facts = page.locator('#pair-facts').inner_text()
            assert 'A → B：' + page.evaluate('pairResult.day_stems.a_sees_b') in facts and 'B → A：' in facts, facts
            pair_text = page.locator('#pair-text-text').text_content()
            assert pair_text.startswith('玄枢 · 双人合盘对照\n\n【四柱】\n') and '\n【紫微宫位叠盘】\n' in pair_text and '\n　A → B（' in pair_text, pair_text
            assert '\n【五行】四柱天干地支，不含藏干\n' in pair_text, pair_text
            assert pair_text.count('—') >= links and page.evaluate('pairResult.branch_links.map(linkText).join("；")') in pair_text
            assert sum(1 for line in pair_text.split('\n') if line[:1] in '子丑寅卯辰巳午未申酉戌亥' and '宫' in line) == 12, pair_text
            page.screenshot(path=str(screenshot_dir / '06-pair.png'), full_page=True)
            # B without a birth hour: no hour pillar, no Zi Wei overlay, and the text says why.
            page.locator('#pair_hour_unknown').check()
            page.locator('#pair-run').click()
            page.wait_for_function("() => !document.getElementById('ziwei-pair-grid') && pairResult.person_b.hour_unknown", timeout=30000)
            assert page.locator('#pair-pillars tbody tr').nth(3).locator('td').nth(2).inner_text() == '?'
            assert page.locator('.feature-note', has_text='紫微宫位叠盘需要两人的出生时辰').count() == 1
            pair_text = page.locator('#pair-text-text').text_content()
            assert '\n紫微宫位叠盘需要两人的出生时辰，有一方时辰不详时不列出。\n' in pair_text and '【紫微宫位叠盘】' not in pair_text, pair_text
            assert page.evaluate("pairResult.branch_links.every(l => l.b_pillar !== 'hour')")
            # Ticking it puts B on a noon placeholder; a draft that no longer matches the result is flagged after a tab visit.
            assert page.locator('#pair_datetime').input_value().endswith('T12:00')
            assert page.get_attribute('#pair-text-text', 'aria-labelledby') == 'pair-text-summary'
            page.locator('#pair_hour_unknown').uncheck()
            page.locator('[data-tab="bazi"]').click()
            page.locator('[data-tab="pair"]').click()
            assert page.locator('#pair_hour_unknown').is_checked() is False
            assert page.locator('.feature-note', has_text='A 或 B 的资料已改变').count() == 1
            page.locator('#pair-run').click()
            page.locator('#ziwei-pair-grid').wait_for(timeout=30000)
            assert page.locator('.feature-note', has_text='A 或 B 的资料已改变').count() == 0

            # 开发阶段 decade cycles and exact modeled birth-time boundaries.
            page.locator('[data-tab="dayun"]').click()
            page.locator('#dayun-run').click()
            page.get_by_text('投影起始时间',exact=False).first.wait_for(timeout=30000)
            assert page.locator('#result tbody tr').count() == 10
            assert page.locator('#result thead th').last.inner_text() == '神煞'
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
            # The board scrolls sideways on a phone; arrow keys bring the newly selected palace into view.
            in_view = '''() => {const el = document.activeElement, r = el.getBoundingClientRect(), wrap = el.closest('.ziwei-wrap').getBoundingClientRect();
              return el.classList.contains('palace') && r.left >= wrap.left - 1 && r.right <= wrap.right + 1;}'''
            page.locator('#ziwei-board .palace[tabindex="0"]').focus()
            for key in ('ArrowRight', 'ArrowLeft'):
                for _ in range(3):
                    page.keyboard.press(key)
                assert page.evaluate(in_view), key
            page.locator('#ziwei-board .palace[aria-label*="命宫"]').click()
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
            # The copied text follows 繁體 too, but a name the user typed is kept exactly as typed.
            assert page.locator('#pair-text-text').text_content().startswith('玄樞 · 雙人合盤對照')
            assert page.evaluate("finishText([asName('妈妈') + ' 对照'])") == '妈妈 對照'
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
