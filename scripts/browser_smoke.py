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


def install_professional_stand_in(birth: dict) -> None:
    """Put a stand-in for the optional iztro-py provider in sys.modules, built from XuanShu's own chart (test data
    only). Like iztro-py 0.5 it dumps internal keys (soulPalace, ziweiMaj, wuHeavenly, ziEarthly) and carries an
    i18n.t that turns them into Chinese, naming 仆役宫 交友宫 as iztro does; one star is moved to another palace, one
    major star's brightness changed and one star only the stand-in places."""
    import importlib.machinery
    import types
    from app.engines import BirthInput, calculate_ziwei
    keys = dict(zip('子丑寅卯辰巳午未申酉戌亥', ('zi', 'chou', 'yin', 'mao', 'chen', 'si', 'wu', 'wei', 'shen', 'you', 'xu', 'hai')))
    stems = dict(zip('甲乙丙丁戊己庚辛壬癸', ('jia', 'yi', 'bing', 'ding', 'wu', 'ji', 'geng', 'xin', 'ren', 'gui')))
    palace_keys = {'命宫': 'soulPalace', '兄弟宫': 'siblingsPalace', '夫妻宫': 'spousePalace', '子女宫': 'childrenPalace',
                   '财帛宫': 'wealthPalace', '疾厄宫': 'healthPalace', '迁移宫': 'surfacePalace', '仆役宫': 'friendsPalace',
                   '官禄宫': 'careerPalace', '田宅宫': 'propertyPalace', '福德宫': 'spiritPalace', '父母宫': 'parentsPalace'}
    star_keys = {'紫微': 'ziweiMaj', '天机': 'tianjiMaj', '太阳': 'taiyangMaj', '武曲': 'wuquMaj', '天同': 'tiantongMaj',
                 '廉贞': 'lianzhenMaj', '天府': 'tianfuMaj', '太阴': 'taiyinMaj', '贪狼': 'tanlangMaj', '巨门': 'jumenMaj',
                 '天相': 'tianxiangMaj', '天梁': 'tianliangMaj', '七杀': 'qishaMaj', '破军': 'pojunMaj',
                 '左辅': 'zuofuMin', '右弼': 'youbiMin', '文昌': 'wenchangMin', '文曲': 'wenquMin'}
    table = {('stars.major.' if v.endswith('Maj') else 'stars.minor.') + v: k for k, v in star_keys.items()}
    table.update({'palaces.' + v: ('交友宫' if v == 'friendsPalace' else k) for k, v in palace_keys.items()})
    table.update({'heavenlyStem.' + v + 'Heavenly': k for k, v in stems.items()})
    table.update({'earthlyBranch.' + v + 'Earthly': k for k, v in keys.items()})
    key = lambda n: star_keys.get(n, n)
    minor = set('左辅 右弼 文昌 文曲 禄存 天马 擎羊 陀罗 火星 铃星 地空 地劫 天魁 天钺'.split())
    z = calculate_ziwei(BirthInput(**birth))
    hua = {t['star']: t['type'][-1] for t in z['birth_year_transformations']}
    moved, dropped = '八座', '天贵'
    palaces = []
    for p in z['palaces']:
        star = lambda n, kind: {'name': key(n), 'type': kind, 'brightness': p['star_brightness'].get(n, ''), 'mutagen': hua.get(n, '')}
        aux = [n for n in p['auxiliary_stars'] if n not in (moved, dropped)]
        palaces.append({'index': len(palaces), 'name': palace_keys[p['name']], 'is_body_palace': p['is_shen'],
                        'heavenly_stem': stems[p['stem']] + 'Heavenly',
                        'earthly_branch': keys[p['branch']] + 'Earthly', 'major_stars': [star(n, 'major') for n in p['main_stars']],
                        'minor_stars': [star(n, 'soft') for n in aux if n in minor], 'adjective_stars': [star(n, 'adjective') for n in aux if n not in minor],
                        'decadal': {'range': [p['decade']['start_age'], p['decade']['end_age']]}})
    next(q for q in palaces if q['earthly_branch'] != keys[z['star_positions'][moved]] + 'Earthly')['adjective_stars'].append({'name': moved})
    first = next(q['major_stars'][0] for q in palaces if q['major_stars'] and q['major_stars'][0]['brightness'])
    first['brightness'] = '庙' if first['brightness'] == '平' else '平'
    palaces[0]['adjective_stars'].append({'name': '天德'})
    natal = {'solar_date': birth['birth_datetime'][:10], 'five_elements_class': z['five_elements_bureau'], 'soul': key(z['ming_master']), 'body': key(z['shen_master']),
             'earthly_branch_of_soul_palace': keys[z['ming_palace']] + 'Earthly', 'earthly_branch_of_body_palace': keys[z['shen_palace']] + 'Earthly', 'palaces': palaces}
    class Chart:
        def model_dump(self, **kw):
            return natal
        def horoscope(self, date, hour):
            return {'decadal': {'index': 3, 'heavenly_stem': 'wuHeavenly', 'earthly_branch': 'yinEarthly', 'mutagen': ['tanlangMaj', 'taiyinMaj', 'youbiMin', 'tianjiMaj']},
                    'yearly': {'index': 5, 'heavenly_stem': 'bingHeavenly', 'earthly_branch': 'wuEarthly', 'mutagen': ['tiantongMaj', 'tianjiMaj', 'wenchangMin', 'lianzhenMaj']}}
    class Astro:
        def by_solar(self, *args):
            return Chart()
    module = types.ModuleType('iztro_py')
    module.astro, module.__spec__ = Astro(), importlib.machinery.ModuleSpec('iztro_py', None)
    module.i18n = types.SimpleNamespace(t=lambda name, lang=None: table.get(name, name))
    sys.modules['iztro_py'], sys.modules['iztro_py.i18n'] = module, module.i18n


def remove_professional_stand_in() -> None:
    sys.modules.pop('iztro_py', None)
    sys.modules.pop('iztro_py.i18n', None)


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


# Text fields whose hint is wider than the field, measured in the field's own font (folded settings opened for it).
CLIPPED_HINTS = """() => {
  const folds = [...document.querySelectorAll('#connection-settings, .vault-pane')].filter(d => !d.open);
  folds.forEach(d => {d.open = true;});
  const ruler = document.createElement('canvas').getContext('2d'), out = [];
  document.querySelectorAll('input[placeholder]').forEach(el => {
    if (!el.offsetParent || el.value) return;
    const s = getComputedStyle(el); ruler.font = s.font;
    const room = el.clientWidth - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight);
    if (ruler.measureText(el.placeholder).width > room + 0.5) out.push(el.id + ': ' + el.placeholder);
  });
  folds.forEach(d => {d.open = false;});
  return out;
}"""


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
    api_js = (ROOT / 'static/api.js').read_text(encoding='utf-8')
    tips_js = (ROOT / 'static/tips.js').read_text(encoding='utf-8')
    datepicker_js = (ROOT / 'static/datepicker.js').read_text(encoding='utf-8')
    client = TestClient(app)
    counts = {'requests': 0}
    group_bodies: list[str] = []

    def call_api(path: str, data: dict, headers: dict | None = None):
        # The integration page speaks MCP to POST /mcp; its protocol headers are passed on as the browser sends them.
        if path == '/mcp' and data is not None:
            wanted = ('accept', 'content-type', 'mcp-protocol-version', 'mcp-method', 'mcp-name', 'authorization')
            response = client.post('/mcp', json=data, headers={k: v for k, v in (headers or {}).items() if k.lower() in wanted})
            counts['requests'] += 1
            return {'ok': response.is_success, 'status': response.status_code, 'data': response.json(), 'text': response.text,
                    'type': response.headers.get('content-type', '')}
        # The page also reads one static data file (the cross-check summary) with fetch.
        if not (path.startswith('/api/') or (data is None and path in ('/static/crosscheck-summary.json', '/openapi.json'))):
            raise ValueError('Only /api/ and /mcp calls can use the local browser bridge')
        if path == '/api/group-relations':
            group_bodies.append(json.dumps(data, ensure_ascii=False))
        response = client.get(path) if data is None else client.post(path, json=data)
        counts['requests'] += 1
        return {'ok': response.is_success, 'status': response.status_code, 'data': response.json(), 'text': response.text,
                'type': response.headers.get('content-type', '')}

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
                const result=await window.apiBridge(path,data,opt && opt.headers ? opt.headers : null);
                // text() is the body as the server sent it, which the Agent page measures.
                return {ok:result.ok,status:result.status,json:async()=>result.data,text:async()=>result.text};
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
            page.add_script_tag(content=tips_js)
            page.add_script_tag(content=datepicker_js)
            page.add_script_tag(content=i18n_js)
            # The full time-zone list keeps the page's default zone selected.
            assert page.locator('#timezone').input_value() == 'Asia/Shanghai'
            page.locator('#birth_city').select_option('温哥华')
            assert page.locator('#timezone').input_value() == 'America/Vancouver'
            assert page.locator('#longitude').input_value() == '-123.1207'
            page.locator('#birth_city').select_option('')
            page.locator('#timezone').select_option('Asia/Shanghai')
            page.locator('#longitude').fill('')
            # In a Windows contrast theme the token-drawn checkbox and switch still show whether they are on.
            page.emulate_media(forced_colors='active')
            # Colour transitions are switched off for the check, so the computed colours are the settled ones.
            page.evaluate("() => {const s = document.createElement('style'); s.id = 'smoke-still'; s.textContent = '#hour_unknown,#hour_unknown::before,#late_zi_day_rollover,#late_zi_day_rollover::before{transition:none!important}'; document.head.append(s);}")
            paint = "(id) => {const el = document.getElementById(id); return [getComputedStyle(el).backgroundColor, getComputedStyle(el, '::before').backgroundColor];}"
            off = [page.evaluate(paint, i) for i in ('hour_unknown', 'late_zi_day_rollover')]
            page.evaluate("() => ['hour_unknown', 'late_zi_day_rollover'].forEach(id => {document.getElementById(id).checked = true;})")
            on = [page.evaluate(paint, i) for i in ('hour_unknown', 'late_zi_day_rollover')]
            page.evaluate("() => {['hour_unknown', 'late_zi_day_rollover'].forEach(id => {document.getElementById(id).checked = false;}); document.getElementById('smoke-still').remove();}")
            page.emulate_media(forced_colors='none')
            assert off[0] != on[0] and off[1] != on[1], (off, on)
            # AI chat is the initial view; without a configured model it explains how to enable it.
            page.locator('#chat-status').get_by_text('对话服务未启用', exact=False).wait_for(timeout=30000)
            assert page.locator('#chat-send').is_disabled()
            assert page.locator('#chat-memory-panel').count() == 1
            assert page.locator('#chat-mode option').count() == 2 and page.locator('#chat-mode').input_value() == 'single'
            # A select drawn in the page's own style keeps the width of its widest option, so choosing another one moves
            # nothing beside it (the browser would otherwise size it to the chosen option).
            if page.evaluate("CSS.supports('appearance', 'base-select')"):
                if not page.locator('#chat-mode').is_visible():
                    page.locator('#chat-settings > summary').click()
                mode_width = page.locator('#chat-mode').bounding_box()['width']
                page.locator('#chat-mode').select_option('panel')
                assert abs(page.locator('#chat-mode').bounding_box()['width'] - mode_width) < 1, mode_width
                page.locator('#chat-mode').select_option('single')
                assert abs(page.locator('#chat-mode').bounding_box()['width'] - mode_width) < 1, mode_width
                page.locator('#chat-settings > summary').click()
                assert not page.locator('#chat-mode').is_visible()
            page.locator('[data-tab="date-scan"]').click()
            # An officer cannot be kept and excluded at once: ticking one side clears the other.
            page.locator('#scan-include input[value="建"]').check()
            page.locator('#scan-exclude input[value="建"]').check()
            assert not page.locator('#scan-include input[value="建"]').is_checked()
            page.locator('#scan-exclude input[value="建"]').uncheck()
            page.locator('#scan-exclude input[value="破"]').check()
            page.locator('#scan-hours').fill('23:30')
            page.locator('#scan-run').click()
            page.get_by_text('值符', exact=False).first.wait_for(timeout=30000)
            # The result is a week calendar over the whole range: candidates open their detail, dropped days say why.
            assert page.locator('#scan-grid .ds-day').count() == 30
            scan = page.evaluate("({picks: dateScanResult.candidates.map(c => c.date), out: dateScanResult.excluded_days.map(d => [d.date, d.reason])})")
            assert page.locator('#scan-grid .ds-day.is-pick').count() == len(scan['picks']) and len(scan['picks']) + len(scan['out']) == 30
            assert scan['out'] and all(reason == 'officer_excluded' for _, reason in scan['out'])
            assert '排除的值日' in page.locator('#scan-day-' + scan['out'][0][0]).inner_text()
            assert page.locator('#scan-detail h4').inner_text().startswith(scan['picks'][0])
            # Edits not yet scanned survive choosing a candidate and switching views; focus stays on the chosen day.
            page.locator('#scan-hours').fill('10:00')
            page.locator('#scan-skip-jie').check()
            page.locator('#scan-day-' + scan['picks'][2] + ' .ds-pick').click()
            assert page.evaluate("document.activeElement.id") == 'scan-pick-' + scan['picks'][2]
            assert page.locator('#scan-detail h4').inner_text().startswith(scan['picks'][2])
            assert page.locator('#scan-detail .ds-hour-card').count() == 1
            page.locator('#scan-view-list').click()
            assert page.locator('#scan-list tbody tr').count() == len(scan['picks'])
            page.locator('#scan-view-grid').click()
            assert page.locator('#scan-hours').input_value() == '10:00' and page.locator('#scan-skip-jie').is_checked()
            page.locator('#scan-hours').fill('23:30')
            page.locator('#scan-skip-jie').uncheck()
            # The lunar date follows the interface language; switching language re-renders the calendar.
            lunar_zh = page.locator('#scan-detail .cal-detail-facts p').first.inner_text()
            page.locator('#ui-language').select_option('en')
            lunar_en = page.locator('#scan-detail .cal-detail-facts p').first.inner_text()
            assert lunar_en != lunar_zh and '月' not in lunar_en and '年' not in lunar_en
            page.locator('#ui-language').select_option('zh-CN')
            # A chart opens on the Qimen page with the card's date, time, zone and 00:00 day boundary, whatever the
            # birth panel's 23:00 setting, so the page shows the same chart as the card.
            page.evaluate("$('#late_zi_day_rollover').checked = true")
            page.locator('#scan-qimen-0').click()
            page.wait_for_function("active === 'qimen' && qimenResult", timeout=30000)
            assert page.evaluate("document.activeElement.dataset.tab") == 'qimen'
            card = page.evaluate("dateScanResult.candidates.find(c => c.date === %r).hour_charts[0]" % scan['picks'][2])
            shown = page.evaluate("qimenResult")
            assert card['instant'].startswith(scan['picks'][2] + 'T23:30')
            assert all(shown[k] == v for k, v in card.items() if k != 'local_time'), (card, {k: shown.get(k) for k in card})
            page.evaluate("$('#late_zi_day_rollover').checked = false")
            page.locator('#qimen-moment').select_option('now')
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
            # What is missing comes as a card with a way to supply it, and nothing ran.
            assert page.locator('#consult-head .cw-badge').inner_text() == '需要补充输入' and page.locator('#consult-steps').count() == 0
            assert 'birth' in page.locator('#consult-need-birth').inner_text()
            page.locator('#consult-need-birth button').click()
            assert page.locator('#consult-use-birth').is_checked()
            page.locator('#consult-real-world-facts').fill('需要稳定的收入和可控的工作时间')
            page.locator('#consult-run').click()
            page.get_by_text('annual_transformations', exact=False).first.wait_for(timeout=30000)
            # The scenario and why, then each tool in order with what it came back with and the observations drawn from it.
            assert page.locator('#consult-head .cw-badge').inner_text() == '已完成' and page.locator('#consult-head .cw-intent').inner_text() == '事业/年度'
            assert '职业' in page.locator('#consult-head .cw-route').inner_text()
            assert page.locator('#consult-steps > li').count() == 4 and page.locator('#consult-step-1 code').first.inner_text() == 'chart_quality_audit'
            assert page.locator('#consult-step-3 .cw-step-fact').inner_text().startswith('2027 农历年')
            assert page.locator('#consult-step-2 .cw-ob').count() >= 3 and page.locator('#consult-step-2 .cw-ref').count() >= 1
            assert '可核验观察' in page.locator('#result').inner_text()
            assert '需要稳定的收入' in page.locator('#consult-given').inner_text() and page.locator('#consult-given .cw-type').count() == 0
            # The summary is drawn from the run (not the server's sentence), the result takes the focus, and the deep-evidence
            # count says how many of its observations are listed.
            assert page.locator('#consult-head .cw-summary').inner_text() == '4 步可复现计算已执行 · 没有缺少的必需输入'
            assert page.evaluate("document.activeElement.id") == 'consult-head'
            shown = page.locator('#consult-step-2 .cw-ob').count()
            assert f'下面列出与问题相关的 {shown} 条' in page.locator('#consult-step-2 .cw-step-fact').inner_text()
            page.screenshot(path=str(screenshot_dir / '26-consultation-desktop.png'), full_page=True)
            # The follow-up keeps the scenario: the next-year question goes into the box, still in Chinese, and a filled
            # 农历年 field moves on with it (it would otherwise override the year in the question).
            assert page.locator('#consult-next-year').inner_text() == '那2028年呢？'
            page.locator('#consult-year').fill('2027')
            page.locator('#consult-next-year').click()
            assert page.locator('#consult-question').input_value() == '那2028年呢？' and page.locator('#consult-year').input_value() == '2028'
            page.locator('#consult-run').click()
            page.get_by_text('2028 农历年', exact=False).first.wait_for(timeout=30000)
            assert page.locator('#consult-head .cw-turn').inner_text() == '对话轮次 3'  # the run that asked for the birth details counts too
            assert page.locator('#consult-next-year').inner_text() == '那2029年呢？'
            # 换个话题 rewrites the follow-up box at once and the next-year shortcut goes away.
            page.locator('#consult-intent').select_option('career')
            page.locator('#consult-fresh').click()
            assert page.locator('#consult-intent').input_value() == 'auto'  # a hand-picked scenario would override the new question
            assert page.locator('#consult-next-year').count() == 0 and page.locator('#consult-fresh').is_disabled()
            assert page.locator('#consult-next p').first.inner_text() == '下一问按新话题识别，不沿用本次场景。'
            page.locator('#consult-year').fill('')
            page.locator('[data-tab="bazi"]').click()
            # The form checks itself instead of showing the browser's validation bubble: a wrong longitude is named under
            # its field in the interface language and focused, and nothing is cast until it is fixed.
            assert page.evaluate("document.getElementById('birth-form').noValidate")
            page.locator('#longitude').fill('200')
            page.locator('#run-btn').click()
            page.locator('#longitude-problem').wait_for(timeout=5000)
            assert page.locator('#longitude-problem').inner_text() == '经度需在 -180 到 180 之间（东经为正、西经为负）'
            assert page.evaluate('document.activeElement.id') == 'longitude' and page.get_attribute('#longitude', 'aria-invalid') == 'true'
            assert 'longitude-problem' in page.get_attribute('#longitude', 'aria-describedby')
            assert page.locator('.pillar-stem').count() == 0
            page.locator('#longitude').fill('104.06675')
            assert page.locator('#longitude-problem').inner_text() == '经度最多保留 4 位小数，例如 104.0667'
            page.locator('#longitude').fill('')
            assert page.locator('#longitude-problem').count() == 0 and page.get_attribute('#longitude', 'aria-invalid') is None
            # A longitude filled in by choosing a city clears the note too, not only typing.
            page.locator('#longitude').fill('200')
            page.locator('#run-btn').click()
            page.locator('#longitude-problem').wait_for(timeout=5000)
            page.locator('#birth_city').select_option('成都')
            assert page.locator('#longitude-problem').count() == 0 and page.get_attribute('#longitude', 'aria-invalid') is None
            page.locator('#birth_city').select_option('')
            page.locator('#longitude').fill('')
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
            assert page.locator('.pillar').nth(0).locator('.shensha-tag').get_attribute('data-tip') == '查法起点：年支 辰'
            # Hints are drawn by tips.js in the project's style, not as the browser's title tooltip: hover shows one,
            # Escape closes it, and a click pins a plain label's hint until the next click.
            assert page.evaluate("document.querySelectorAll('body [title]').length") == 0
            tag = page.locator('.pillar').nth(0).locator('.shensha-tag')
            tag.hover()
            page.wait_for_function("() => {const t = document.getElementById('xs-tip'); return t && !t.hidden && t.textContent === '查法起点：年支 辰';}", timeout=3000)
            assert 'xs-tip' in (tag.get_attribute('aria-describedby') or '')
            box = page.locator('#xs-tip').bounding_box(); anchor = tag.bounding_box()
            assert box['y'] + box['height'] <= anchor['y'] or box['y'] >= anchor['y'] + anchor['height']
            page.keyboard.press('Escape')
            page.wait_for_function("() => document.getElementById('xs-tip').hidden", timeout=3000)
            assert 'xs-tip' not in (tag.get_attribute('aria-describedby') or '')
            tag.click()
            page.wait_for_function("() => !document.getElementById('xs-tip').hidden", timeout=3000)
            page.mouse.move(2, 2)
            page.wait_for_timeout(450)
            assert page.evaluate("!document.getElementById('xs-tip').hidden")
            tag.click()
            page.wait_for_function("() => document.getElementById('xs-tip').hidden", timeout=3000)
            # Screen readers have the hint as the mark's description all the time, not only while it shows.
            assert tag.get_attribute('aria-description') == '查法起点：年支 辰'
            # The pointer can move onto the hint and rest there to read it; leaving it closes the hint.
            page.mouse.move(2, 2)
            tag.hover()
            page.wait_for_function("() => !document.getElementById('xs-tip').hidden", timeout=3000)
            tip_box = page.locator('#xs-tip').bounding_box()
            page.mouse.move(tip_box['x'] + tip_box['width'] / 2, tip_box['y'] + tip_box['height'] / 2, steps=4)
            page.wait_for_timeout(500)
            assert page.evaluate("!document.getElementById('xs-tip').hidden")
            # Escape closes the hint only; the key does not reach the page behind it (an open dialog, a running reply).
            page.evaluate("() => {window.__esc = 0; document.addEventListener('keydown', e => {if (e.key === 'Escape') window.__esc += 1;});}")
            page.keyboard.press('Escape')
            page.wait_for_function("() => document.getElementById('xs-tip').hidden", timeout=3000)
            assert page.evaluate('window.__esc') == 0
            page.mouse.move(2, 2)
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
            assert page.locator('#luck-year-2015').get_attribute('data-tip').startswith('2015 乙未 · 星运 衰')
            assert '神煞 天乙贵人' in page.locator('#luck-year-2015').get_attribute('data-tip')
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
            # Only the twelve month pillars the year stem allows (五虎遁) and the twelve hours the day stem allows (五鼠遁).
            assert page.locator('#pillar-month option').count() == 12 and page.locator('#pillar-hour option').count() == 13
            assert page.locator('#pillar-year optgroup').count() == 6
            assert page.locator('.ps-col').nth(1).locator('.ps-preview small').inner_text() == '立秋 – 白露'
            assert page.locator('.ps-col').nth(3).locator('.ps-preview small').inner_text() == '03–05'
            # A new year stem moves the month stems and keeps the month branch.
            page.locator('#pillar-year').select_option('甲子')
            assert page.locator('#pillar-month').input_value() == '壬申'
            page.locator('#pillar-year').select_option('庚辰')
            assert page.locator('#pillar-month').input_value() == '甲申'
            # A new day stem re-derives the hour stems and keeps the hour branch; 不限 stays 不限.
            page.locator('#pillar-day').select_option('戊辰')
            assert page.locator('#pillar-hour').input_value() == '甲寅'
            page.locator('#pillar-hour').select_option('')
            page.locator('#pillar-day').select_option('丙午')
            assert page.locator('#pillar-hour').input_value() == ''
            # Under the 00:00 day change the 子 hour is the first and the last hour of the day.
            page.locator('#pillar-hour').select_option('戊子')
            hour_hint = page.locator('#pillar-hour-hint')
            assert page.locator('#pillar-hour').get_attribute('aria-describedby') == 'pillar-hour-hint'
            assert hour_hint.inner_text() == '00–01 · 23–24'
            page.locator('#pillar-late-zi').check()
            assert hour_hint.inner_text() == '23–01' and page.locator('#pillar-day-hint').inner_text() == '23:00 换日'
            page.locator('#pillar-late-zi').uncheck()
            page.locator('#pillar-hour').select_option('庚寅')
            # Unsearched choices and the derived text follow a language switch.
            page.locator('#pillar-from').fill('1990')
            page.locator('#ui-language').select_option('en')
            assert page.locator('#pillar-from').input_value() == '1990' and page.locator('#pillar-hour').input_value() == '庚寅'
            month_en = page.locator('#pillar-month-hint').inner_text()
            assert '立秋' not in month_en and month_en.count(' – ') == 1
            page.locator('#ui-language').select_option('zh-CN')
            assert page.locator('#pillar-month-hint').inner_text() == '立秋 – 白露'
            page.locator('#pillar-from').fill('1901')
            page.locator('#pillar-search-run').click()
            page.locator('#pillar-use-1').wait_for(timeout=30000)
            assert page.locator('#pillar-matches > li').count() == 2
            # The year pillar returns every sixty years: one mark per year on the axis, and a card per interval.
            assert page.locator('#pillar-axis .ps-mark').all_inner_texts() == ['1940', '2000']
            card = page.locator('#pillar-match-1')
            assert card.locator('.ps-date').inner_text() == '2000-08-16' and card.locator('.ps-weekday').inner_text() == '星期三'
            assert card.locator('.ps-when').inner_text().startswith('03:00:00 – 05:00:00')
            assert '庚辰 · 七月十七' in card.inner_text() and '2 小时' in card.inner_text()
            assert 'UTC+09:00' in page.locator('#pillar-match-0').inner_text()
            page.locator('#pillar-axis .ps-mark').nth(1).click()
            assert page.evaluate("document.activeElement.id") == 'pillar-match-1'
            assert page.locator('#pillar-use-1').get_attribute('aria-describedby') == 'pillar-date-1 pillar-when-1'
            page.screenshot(path=str(screenshot_dir / '33-pillar-search.png'), full_page=True)
            # A whole day across a daylight-saving switch (Shanghai, 4 May 1986): each end keeps its own offset, and the
            # line wraps at the dash instead of running out of the card.
            page.locator('#pillar-year').select_option('丙寅')
            page.locator('#pillar-month').select_option('壬辰')
            page.locator('#pillar-day').select_option('戊申')
            page.locator('#pillar-hour').select_option('')
            page.locator('#pillar-from').fill('1986')
            page.locator('#pillar-to').fill('1986')
            page.locator('#pillar-search-run').click()
            page.wait_for_function("() => document.querySelector('#pillar-match-0 .ps-date')?.textContent === '1986-05-04'", timeout=30000)
            dst = page.locator('#pillar-match-0 .ps-when')
            assert dst.inner_text().replace('\n', ' ').split() == ['00:00:00', 'UTC+08:00', '–', '1986-05-05', '00:00:00', 'UTC+09:00']
            assert page.evaluate("[...document.querySelectorAll('#pillar-matches .ps-when')].every(p => p.scrollWidth <= p.clientWidth + 1)")
            page.locator('#pillar-year').select_option('庚辰')
            page.locator('#pillar-month').select_option('甲申')
            page.locator('#pillar-day').select_option('丙午')
            page.locator('#pillar-hour').select_option('庚寅')
            page.locator('#pillar-from').fill('1901')
            page.locator('#pillar-to').fill('2099')
            page.locator('#pillar-search-run').click()
            page.wait_for_function("() => document.querySelectorAll('#pillar-matches > li').length === 2", timeout=30000)
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
            # A differing hour pillar: the same day is tried at every double hour. With the 命宫 above (the 寅 hour's)
            # no hour matches both, and the closest ones are framed; the pillars alone match at 卯, 寅 is the chart's.
            assert page.locator('#import-hours .ic-hour').count() == 13 and page.locator('.ic-hour.is-match').count() == 0
            assert page.locator('.ic-hour.is-best').count() == 2 and page.locator('.ic-hour .ic-near').count() == 2
            # The closest hours are named in the verdict, not only framed.
            closest = page.locator('.ic-verdict').inner_text()
            assert '最接近：' in closest and all(name.split('\n')[0] in closest for name in page.locator('.ic-hour.is-best .ic-name').all_inner_texts())
            # Field lists translate label by label: no Chinese left in English, separators by language.
            page.locator('#ui-language').select_option('en')
            page.wait_for_function("() => document.querySelector('#import-hour-detail').innerText.includes('Still differing')", timeout=10000)
            still = page.locator('#import-hour-detail .ic-detail-diff').inner_text()
            assert not re.search(r'[\u3400-\u9fff、]', still), still
            page.locator('#ui-language').select_option('zh-CN')
            # Birth data edited after the check: the results are marked as belonging to the old data, and the hour is not applied.
            page.locator('#gender').select_option('male')
            assert page.locator('#import-stale').is_visible()
            page.locator('#import-hour-0').click()
            page.locator('#import-hour-use').click()
            assert page.locator('#birth_datetime').input_value() == '2000-08-16T04:00' and page.locator('#import-stale').is_visible()
            page.locator('#gender').select_option('female')
            assert page.locator('#import-stale').is_hidden()
            page.locator('#import-text').fill('乾造 庚辰 甲申 丙午 辛卯')
            page.locator('#import-check-run').click()
            page.locator('.ic-hour.is-match').first.wait_for(timeout=30000)
            assert page.locator('.ic-hour.is-match').all_inner_texts() == [page.locator('#import-hour-3').inner_text()]
            assert '卯时' in page.locator('.ic-verdict').inner_text() and '寅时' in page.locator('.ic-hour.is-current').inner_text()
            assert page.locator('#import-hour-3').get_attribute('aria-pressed') == 'true'
            assert '2000-08-16 06:00' in page.locator('#import-hour-detail').inner_text()
            page.locator('#import-hour-1').click()
            assert '仍不一致' in page.locator('#import-hour-detail').inner_text() and page.locator('#import-hour-3').get_attribute('aria-pressed') == 'false'
            page.locator('#import-hour-3').click()
            page.screenshot(path=str(screenshot_dir / '34-import-check.png'), full_page=True)
            # Casting with that hour checks the pasted chart again by itself.
            page.locator('#import-hour-use').focus()
            page.keyboard.press('Enter')
            page.wait_for_function("() => document.querySelector('.import-verdict.ok') !== null", timeout=30000)
            assert page.locator('#birth_datetime').input_value() == '2000-08-16T06:00' and page.locator('#import-hours').count() == 0
            # The button pressed is gone; focus lands on the new verdict rather than the page.
            page.wait_for_function("() => document.activeElement && document.activeElement.id === 'import-verdict'", timeout=10000)
            page.locator('#birth_datetime').fill('2000-08-16T04:00')
            page.locator('#run-btn').click()
            page.wait_for_function("() => currentInput && currentInput.birth_datetime === '2000-08-16T04:00'", timeout=30000)
            # Date fields open the project's own calendar instead of the browser's picker: from the icon, Alt+Down or F4.
            # Each day carries its lunar date, and the chosen day and time reach the field as typed input would.
            picker_open = "() => document.querySelector('#xs-datepicker')?.matches(':popover-open') === true"
            page.locator('#birth_datetime').scroll_into_view_if_needed()
            field_box = page.locator('#birth_datetime').bounding_box()
            page.mouse.click(field_box['x'] + field_box['width'] - 18, field_box['y'] + field_box['height'] / 2)
            page.wait_for_function(picker_open, timeout=5000)
            assert not page.evaluate("() => document.querySelector('#birth_datetime').matches(':open')"), 'the browser picker opened too'
            page.wait_for_function("() => document.querySelector('#xs-datepicker [data-day=\"2000-08-16\"] .xs-dp-lunar')?.textContent === '十七'", timeout=30000)
            assert page.evaluate('document.activeElement.dataset.day') == '2000-08-16'
            assert page.evaluate("() => document.querySelector('#xs-datepicker td[aria-selected=true] button').dataset.day") == '2000-08-16'
            assert '七月十七' in page.evaluate("document.activeElement.getAttribute('aria-label')")
            assert page.locator('#xs-datepicker .xs-dp-shichen').text_content() == '寅时'
            page.screenshot(path=str(screenshot_dir / '48-date-picker.png'))
            page.keyboard.press('ArrowRight')
            page.keyboard.press('Enter')
            page.locator('#xs-datepicker .xs-dp-hour').select_option('05')
            assert page.locator('#xs-datepicker .xs-dp-shichen').text_content() == '卯时'
            page.locator('#xs-datepicker .xs-dp-ok').click()
            page.wait_for_function("() => !document.querySelector('#xs-datepicker').matches(':popover-open')", timeout=5000)
            assert page.locator('#birth_datetime').input_value() == '2000-08-17T05:00'
            assert page.evaluate('document.activeElement.id') == 'birth_datetime'
            assert page.evaluate("document.querySelector('#demo-birth-warning').hidden"), 'the picked time did not reach the input listeners'
            page.keyboard.press('Alt+ArrowDown')
            page.wait_for_function(picker_open, timeout=5000)
            page.keyboard.press('PageDown')
            assert page.evaluate('document.activeElement.dataset.day') == '2000-09-17'
            # Tab goes round the calendar's own controls; it never drops focus on the page behind it.
            in_picker = "() => document.querySelector('#xs-datepicker').contains(document.activeElement)"
            for key in ['Tab'] * 9 + ['Shift+Tab'] * 9:
                page.keyboard.press(key)
                assert page.evaluate(in_picker), key
            page.keyboard.press('Escape')
            page.wait_for_function("() => !document.querySelector('#xs-datepicker').matches(':popover-open')", timeout=5000)
            # At the first month of the range the pressed button turns disabled, and focus moves to the year beside it.
            page.locator('#birth_datetime').fill('1901-02-15T10:00')
            page.keyboard.press('Alt+ArrowDown')
            page.wait_for_function(picker_open, timeout=5000)
            page.locator('#xs-datepicker .xs-dp-nav.is-prev').click()
            assert page.locator('#xs-datepicker .xs-dp-nav.is-prev').is_disabled()
            assert page.evaluate("document.activeElement.classList.contains('xs-dp-year')")
            page.keyboard.press('Escape')
            page.wait_for_function("() => !document.querySelector('#xs-datepicker').matches(':popover-open')", timeout=5000)
            page.locator('#birth_datetime').fill('2000-08-17T05:00')
            page.keyboard.press('Alt+ArrowDown')
            page.wait_for_function(picker_open, timeout=5000)
            page.keyboard.press('Escape')
            page.wait_for_function("() => !document.querySelector('#xs-datepicker').matches(':popover-open')", timeout=5000)
            assert page.evaluate('document.activeElement.id') == 'birth_datetime' and page.locator('#birth_datetime').input_value() == '2000-08-17T05:00'
            page.locator('#birth_datetime').fill('2000-08-16T04:00')
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
            # One card per rule changed alone; with nothing moving there are no field cards.
            assert page.locator('#rule-singles .rm-single').count() == 2 and page.locator('#rule-singles .rm-same').count() == 2
            assert page.locator('#rule-fields').count() == 0
            page.locator('#rule-only-diff').check()
            page.wait_for_function("() => document.querySelectorAll('#rule-matrix tbody tr').length === 1", timeout=30000)
            page.locator('#rule-only-diff').uncheck()
            # A birth after 23:00 in daylight saving time, with a longitude: many fields move.
            page.evaluate("() => {window.savedInput = currentInput; currentInput = {...currentInput, birth_datetime: '1990-05-17T23:30', longitude: 116.4}; render();}")
            page.locator('#rule-fields').wait_for(timeout=30000)
            singles = page.locator('#rule-singles .rm-single')
            assert singles.count() == 5 and page.locator('#rule-singles .rm-single.has-diff').count() == 4
            late = singles.first
            assert late.locator('.rm-rule').inner_text() == '23:00 换日（早晚子时）' and '时刻不变' in late.inner_text()
            assert late.locator('.rm-change').first.inner_text().replace('\n', ' ') == '日柱 壬午 → 癸未'
            assert singles.nth(2).locator('.rm-shift').inner_text() == '−1 小时 15 分'
            assert '需手动改时间' in singles.nth(4).inner_text() and singles.nth(4).locator('button').count() == 0
            # Long changes wrap inside their card, and the card and table buttons have their own ids.
            assert page.evaluate("""() => [...document.querySelectorAll('.rm-change')].every(c => c.getBoundingClientRect().right <= c.closest('.rm-single').getBoundingClientRect().right + 1)""")
            assert page.evaluate("() => {const ids = [...document.querySelectorAll('#result [id]')].map(e => e.id); return ids.length === new Set(ids).size;}")
            # A field chip scrolls to its card, keeps #tool=rule-matrix in the address and moves focus there.
            address = page.evaluate("location.hash")
            page.locator('.rule-card a.relation-chip').first.click()
            assert page.evaluate("location.hash") == address and page.evaluate("document.activeElement.classList.contains('rm-field')")
            # Every value a field takes, the current one marked, named by the single rules that give it.
            hour = page.locator('#rm-field-pillar-hour')
            assert [t.replace('\n', ' ') for t in hour.locator('.rm-val').all_inner_texts()] == ['庚子', '壬子', '辛亥']
            assert hour.locator('.rm-value').first.locator('.rm-tag').inner_text() == '当前'
            assert hour.locator('li').nth(2).locator('.rm-combo').all_inner_texts() == ['平太阳时', '真太阳时', '扣除夏令时（按标准时）']
            assert hour.locator('li').nth(2).locator('.rm-more').inner_text() == '及另 8 种组合'
            # Picking a value highlights the combinations that give it; focus stays on the pressed value.
            hour.locator('.rm-value').nth(2).click()
            assert page.locator('#rule-matrix tr.is-lit').count() == 11 and page.locator('#rule-matrix tr.is-dim').count() == 4
            assert page.evaluate("document.activeElement.getAttribute('aria-pressed')") == 'true'
            page.screenshot(path=str(screenshot_dir / '37-rule-matrix.png'), full_page=True)
            page.locator('#rule-focus-clear').click()
            assert page.locator('#rule-matrix tr.is-dim').count() == 0
            assert page.evaluate("document.activeElement.id") == 'rm-field-pillar-hour-value-2'
            # With the hour unknown, the converted times come from the placeholder, so none is listed.
            page.evaluate("() => {currentHourUnknown = true; render();}")
            page.wait_for_function("() => ruleMatrixResult && ruleMatrixResult.hour_unknown && document.querySelector('#rule-singles')", timeout=30000)
            assert page.locator('#rule-singles .rm-shift').count() == 0 and '时辰不详，不列换算后的时刻' in page.locator('#rule-singles .rm-single').first.inner_text()
            assert page.locator('#rule-matrix .rule-time').first.inner_text() == '时辰不详'
            page.evaluate("() => {currentHourUnknown = false; render();}")
            page.wait_for_function("() => ruleMatrixResult && !ruleMatrixResult.hour_unknown", timeout=30000)
            page.evaluate("() => {currentInput = window.savedInput; render();}")
            page.wait_for_function("() => document.querySelectorAll('#rule-singles .rm-single').length === 2", timeout=30000)
            # The flying table: a row per palace in the usual order with its four transformations, 自化 marked where the star
            # sits in the same palace; the matrix puts each in its landing column, with 自化 on the diagonal.
            page.locator('[data-tab="transform"]').click()
            page.locator('#transform-table').wait_for(timeout=30000)
            assert page.locator('#transform-table tbody tr').count() == 12
            assert page.locator('#transform-table tbody th').first.inner_text().startswith('命宫')
            self_count = page.evaluate("current.ziwei.palaces.flatMap(p => p.palace_flying_transformations).filter(t => t.self_transform).length")
            assert page.locator('#transform-table td.fh-cell').count() == 48 and page.locator('#transform-table td.is-self').count() == self_count
            page.locator('#transform-pick-1').click()
            assert page.evaluate('selectedPalace') == '兄弟宫' and page.locator('.palace-panel h4').inner_text().startswith('兄弟宫')
            assert page.locator('#transform-table tr.is-focus th').inner_text().startswith('兄弟宫')
            page.locator('#transform-view-matrix').click()
            assert page.locator('#transform-matrix .fh-hua').count() == 48 and page.locator('#transform-matrix td.is-diag').count() == 12
            assert page.locator('#transform-matrix td.is-diag .fh-hua').count() == self_count
            assert page.locator('#transform-matrix td.is-focus-col').count() == 12
            page.screenshot(path=str(screenshot_dir / '47-transform-matrix.png'), full_page=True)
            # The matrix badges name the palace stem, not the birth year.
            assert page.locator('#transform-matrix .fh-hua .hua').first.get_attribute('data-tip').startswith('命宫（')
            page.locator('#transform-view-table').click()
            assert page.locator('#transform-table thead .hua[data-tip]').count() == 0
            # The board opens on the palace picked here, with the flying lines on even if they were turned off before.
            page.evaluate("showFlying = false")
            page.locator('#transform-pick-4').click()
            page.locator('#transform-to-ziwei').click()
            page.wait_for_function("active === 'ziwei'", timeout=10000)
            assert page.locator('.palace-panel h4').first.inner_text().startswith('财帛宫')
            page.locator('#ziwei-board path.fly:not(.in)').first.wait_for(state='attached', timeout=10000)
            assert page.evaluate("document.activeElement.id") == 'palace-' + str(page.evaluate("current.ziwei.palaces.findIndex(p => p.name === '财帛宫')"))
            assert page.locator('#live-status').inner_text() == '紫微盘已打开宫干飞化：财帛宫'
            page.evaluate("selectedPalace = '命宫'")
            page.locator('[data-tab="bazi"]').click()
            # As on a fresh page, today's lunar year is not known yet: the result still comes once it is.
            page.evaluate("todayLunarYear = null")
            page.locator('[data-tab="annual"]').click()
            # A tool that needs only the chart shows its result on opening, for the current lunar year by default.
            page.locator('.transform-card').first.wait_for(timeout=30000)
            assert page.locator('.transform-card').count() == 4
            assert page.locator('#annual-year').input_value() == str(page.evaluate('todayLunarYear'))
            # The automatic run leaves the keyboard on the tab that opened the page.
            assert page.evaluate('document.activeElement.dataset.tab') == 'annual'
            page.screenshot(path=str(screenshot_dir / '03-annual.png'), full_page=True)
            # The year sits on the natal board: twelve palaces, the birth-year four filled, this year's four outlined, the
            # palaces holding this year's outlined, and the palace on the year branch named.
            annual = page.evaluate('annualResult')
            assert page.locator('#annual-board .ay-cell').count() == 12
            assert page.locator('#annual-board .ay-cell .hua.layer').count() == 4 and page.locator('#annual-board .ay-cell .hua:not(.layer)').count() == 4
            assert page.locator('#annual-board .has-year').count() == len({t['natal_palace'] for t in annual['transformations']})
            assert page.locator('#annual-board .is-branch b').inner_text() == annual['year_branch_palace'].replace('宫', '')
            assert page.locator('#annual-table tbody tr').count() == 4
            assert annual['gregorian_span']['start'] in page.locator('.ay-head').inner_text()
            assert page.locator('.ay-head [aria-current="date"] .ay-now').inner_text() == '今年'
            # The year-branch palace is marked by a dashed line rather than a tint, and each board badge reads by its full name.
            branch_look = page.evaluate('''() => {const b = getComputedStyle(document.querySelector('#annual-board .is-branch'));
                const plain = [...document.querySelectorAll('#annual-board .ay-cell')].find(c => !c.classList.contains('is-branch') && !c.classList.contains('has-year'));
                return [b.outlineStyle, b.backgroundColor === getComputedStyle(plain).backgroundColor];}''')
            assert branch_look == ['dashed', True], branch_look
            assert page.locator('#annual-board').get_attribute('role') == 'list'
            assert page.locator('#annual-board .ay-star .visually-hidden').count() == 8
            assert page.locator('#annual-board .ay-star .visually-hidden', has_text='该年').count() == 4
            assert page.locator('#annual-board .ay-star .hua[aria-hidden="true"]').count() == 8
            # The arrows step a year and keep their place; the way back to this year comes with the step.
            this_year = annual['lunar_year']
            page.locator('#annual-next').click()
            page.wait_for_function(f"() => annualResult.lunar_year === {this_year + 1}", timeout=30000)
            assert page.evaluate('document.activeElement.id') == 'annual-next' and page.locator('#annual-year').input_value() == str(this_year + 1)
            assert page.locator('#live-status').inner_text() == f"{this_year + 1} {page.evaluate('annualResult.year_pillar')}"
            assert page.locator('.ay-head .ay-now').count() == 0
            page.locator('#annual-now').click()
            page.wait_for_function(f"() => annualResult.lunar_year === {this_year}", timeout=30000)
            assert page.evaluate('document.activeElement.id') == 'annual-year' and page.locator('#annual-now').count() == 0
            # A year outside the range is refused without a request.
            page.locator('#annual-year').fill('2100')
            assert page.locator('#annual-next').is_disabled() is False
            page.locator('#annual-run').click()
            assert '1901–2099' in page.locator('#result .inline-msg').inner_text() and page.evaluate('annualResult.lunar_year') == this_year
            assert page.locator('#result .inline-msg').get_attribute('role') == 'alert'
            # The arrows refuse it too, rather than stepping from the year shown.
            page.locator('#annual-prev').click()
            assert '1901–2099' in page.locator('#result .inline-msg').inner_text() and page.locator('#annual-year').input_value() == '2100'
            assert page.evaluate('annualResult.lunar_year') == this_year
            page.locator('#annual-year').fill('2099')
            assert page.locator('#annual-next').is_disabled()
            page.locator('#annual-year').fill(str(this_year))
            # The run of years opens on the year-by-year page from this year, already drawn, with the number of years chosen
            # there and all twelve palaces; the keyboard lands on that page's tab.
            page.evaluate("timelineDraft = {...timelineDraft, years: 20, focus_palace: '命宫'}")
            page.locator('#annual-timeline').click()
            page.locator('#timeline-matrix').wait_for(timeout=30000)
            assert page.locator('#timeline-start').input_value() == str(this_year) and page.locator('#timeline-matrix thead .yt-year').count() == 20
            assert page.locator('#timeline-focus').input_value() == '' and page.evaluate('document.activeElement.dataset.tab') == 'timeline'
            page.evaluate("timelineDraft = {...timelineDraft, years: 10}")
            page.locator('[data-tab="annual"]').click()
            layer_before = page.evaluate('JSON.stringify(ziweiLayer)')
            page.locator('#annual-open-year').click()
            page.wait_for_function(f"() => active === 'ziwei' && ziweiLayer.mode === 'year' && ziweiLayer.year === {this_year}", timeout=30000)
            assert page.evaluate('document.activeElement.id') == 'palace-' + str(page.evaluate(f"current.ziwei.palaces.findIndex(p => p.name === {annual['year_branch_palace']!r})"))
            page.evaluate('json => {ziweiLayer = JSON.parse(json);}', layer_before)  # later steps carry on from the layer they left
            # The reading page states the chart in two cards that open the full pages, and points on to related tools.
            page.locator('[data-tab="reading"]').click()
            page.locator('#reading-bazi').wait_for(timeout=30000)
            assert page.locator('#reading-bazi .reading-pillar').count() == 4 and page.locator('#reading-bazi .is-master').count() == 1
            assert '?' not in page.locator('#reading-bazi .reading-pillars').inner_text()
            assert page.locator('#reading-ziwei .reading-label', has_text='命宫').count() == 1
            assert page.locator('#reading-ziwei [class*="reading-hua-"]').count() == 4
            assert page.locator('#reading-ziwei [class*="reading-hua-"] small').count() == 4
            assert page.locator('.reading-link').count() == 4
            page.locator('#reading-bazi-open').click()
            assert page.locator('[data-tab="bazi"]').get_attribute('aria-selected') == 'true'
            page.locator('[data-tab="reading"]').click()
            page.locator('#reading-next-dayun').click()
            assert page.locator('[data-tab="dayun"]').get_attribute('aria-selected') == 'true'
            page.locator('[data-tab="time"]').click()
            # Without a longitude in the birth data, a city picked on the page serves this comparison only.
            assert page.locator('#time-cards').count() == 0 and page.locator('#time-city').count() == 1
            page.locator('#time-run').click()
            assert '请选择出生城市或填写经度' in page.locator('#result').inner_text()
            page.locator('#time-city').select_option('87.6168')
            assert page.locator('#time-longitude').input_value() == '87.6168'
            page.locator('#time-run').click()
            page.locator('#time-cards').wait_for(timeout=30000)
            assert page.locator('#time-cards .tb-card').count() == 3 and page.locator('#time-cards .tb-card.is-used').count() == 1
            assert page.locator('#longitude').input_value() == '' and '仅用于本页' in page.locator('#result').inner_text()
            # Urumqi's solar time runs over two hours behind Beijing time, so the hour pillar always changes;
            # the clock card itself marks nothing, and the apparent one names the equation of time.
            assert page.locator('#time-mean_solar .tb-shift').inner_text().startswith('比钟表慢')
            assert page.locator('#time-mean_solar .bt-pillar.is-changed').count() >= 1 and page.locator('#time-clock .is-changed').count() == 0
            assert '均时差' in page.locator('#time-apparent_solar .tb-parts').inner_text() and '均时差' not in page.locator('#time-mean_solar .tb-parts').inner_text()
            assert '换用太阳时会改变这些结果' in page.locator('#result').inner_text()
            # Changes are spelled out for screen readers too; the page-only longitude stays out of the JSON export.
            assert page.locator('#time-mean_solar .visually-hidden', has_text='与钟表时间不同').count() >= 1
            assert page.locator('#time-clock .visually-hidden').count() == 0
            assert page.evaluate('() => jsonData().time_audit') is None
            # A scale of two-hour periods places each reading and says how far the nearest change of period is.
            assert page.locator('#time-scale-list li').count() == 3
            audit = page.evaluate('timeResult')
            for choice in audit['choices']:
                item = page.locator('#time-scale-' + choice['mode'])
                hour = int(choice['effective_reading'][11:13])
                assert item.locator('.bt-type').inner_text() == '子丑寅卯辰巳午未申酉戌亥'[(hour + 1) % 24 // 2] + '时'
                assert item.locator('.ts-gap').inner_text().startswith(('最近交界 ', '最近日界 '))
            assert page.locator('#time-scale .bt-seg.is-birth').count() == 1
            # Under the 00:00 day rule 子时 splits at midnight, where the day pillar and the hour stem change too;
            # readings are cut to the minute like the cards, so 10:59:31 is still 巳时.
            probe = page.evaluate('''() => {
              const fake = (clock, mean) => ({original_time_mode: 'clock', choices: [
                {mode: 'clock', effective_reading: clock}, {mode: 'mean_solar', effective_reading: mean}]});
              const names = {clock: '钟表时间', mean_solar: '平太阳时'}, out = {};
              const draw = (audit, lateZi) => {const box = document.createElement('div'); result.append(box); timeScale(box, audit, names, lateZi); return box;};
              for (const [key, lateZi] of [['midnight', false], ['late', true]]) {
                const box = draw(fake('2000-08-15T23:55:00+08:00', '2000-08-16T00:00:52+08:00'), lateZi);
                out[key] = {bands: [...box.querySelectorAll('.bt-seg-num')].map(e => e.textContent),
                  gaps: [...box.querySelectorAll('.ts-gap')].map(e => e.textContent), warn: (box.querySelector('.ts-warn') || {}).textContent || ''};
                box.remove();
              }
              const box = draw(fake('2000-08-16T12:00:00+08:00', '2000-08-16T10:59:31+08:00'), false);
              out.cut = [...box.querySelectorAll('li:last-child .ts-time, li:last-child .bt-type')].map(e => e.textContent);
              box.remove();
              return out;
            }''')
            assert '晚子' in probe['midnight']['bands'] and '早子' in probe['midnight']['bands']
            assert all(g.startswith('最近日界 00:00') for g in probe['midnight']['gaps']) and '00:00 日界' in probe['midnight']['warn']
            assert '晚子' not in probe['late']['bands'] and probe['late']['warn'] == ''
            assert probe['late']['gaps'][0].startswith('最近交界 23:00') and probe['late']['gaps'][1].startswith('最近交界 01:00')
            assert probe['cut'] == ['10:59', '巳时']
            # The time systems are compared by the cards; the other rules are one click away.
            assert page.locator('#compare-rules').count() == 0
            page.locator('#time-open-rules').click()
            assert page.locator('[data-tab="rule-matrix"]').get_attribute('aria-selected') == 'true'
            assert page.evaluate("document.activeElement.id") == 'result' and '规则差异对照' in page.locator('#live-status').inner_text()
            page.locator('[data-tab="time"]').click()
            page.locator('#time-cards').wait_for(timeout=30000)
            # The sampler checks its inputs, then draws the structures it found like the boundary map does.
            page.locator('#window-radius').fill('200')
            page.locator('#window-run').click()
            assert '5–120' in page.locator('#window-msg').inner_text() and page.locator('#window-radius').get_attribute('aria-invalid') == 'true'
            assert page.evaluate("document.activeElement.id") == 'window-radius'
            page.locator('#window-radius').fill('60')
            page.locator('#window-spacing').fill('10')
            page.locator('#window-run').click()
            page.locator('#window-summary').wait_for(timeout=30000)
            assert page.evaluate("document.activeElement.id") == 'window-summary'
            sampled = page.evaluate('windowResult')
            assert sampled['uncertainty_minutes'] == 60 and sampled['sample_every_minutes'] == 10
            assert page.locator('#window-cards .bt-card').count() == sampled['variant_count'] and page.locator('#window-cards .bt-card.is-birth').count() == 1
            switches = sum(1 for a, b in zip(sampled['samples'], sampled['samples'][1:]) if a['variant_index'] != b['variant_index'])
            assert page.locator('#window-changes li').count() == switches and page.locator('#window-line .bw-dot').count() == sampled['sample_count']
            assert all('\u4e00' <= ch <= '\u9fff' for ch in sampled['limitations'][0][:2])
            assert page.locator('#window-line .bt-pin').count() == 1
            page.screenshot(path=str(screenshot_dir / '04-time-audit.png'), full_page=True)
            # The boundary map opens with the same error and finds the exact moments.
            page.locator('#window-boundaries').click()
            assert page.locator('[data-tab="boundaries"]').get_attribute('aria-selected') == 'true'
            assert page.evaluate("document.activeElement.id") == 'result' and '生时边界地图' in page.locator('#live-status').inner_text()
            page.wait_for_function('() => boundaryResult && boundaryResult.uncertainty_minutes === 60', timeout=30000)
            assert page.locator('#boundary-radius').input_value() == '60'
            assert page.evaluate('() => boundaryResult.original_birth_local.slice(0, 16) === currentInput.birth_datetime.slice(0, 16)')
            page.locator('[data-tab="time"]').click()
            page.locator('#time-cards').wait_for(timeout=30000)
            # With edits not yet cast the boundary map would read another birth than this sampling, so it opens without running.
            cast_value = page.locator('#birth_datetime').input_value()
            page.locator('#birth_datetime').fill('2000-08-16T09:30')
            page.locator('#window-boundaries').click()
            assert '尚未排盘' in page.locator('#live-status').inner_text() and page.evaluate('boundaryResult') is None
            page.locator('#birth_datetime').fill(cast_value)
            page.locator('[data-tab="time"]').click()
            page.locator('#time-cards').wait_for(timeout=30000)
            # A new chart starts without the city picked for the previous one.
            page.evaluate("() => document.getElementById('run-btn').click()")
            page.wait_for_function('() => timeResult === null && timeLongitude === ""', timeout=30000)
            page.locator('#time-city').wait_for(timeout=30000)
            assert page.locator('#time-longitude').input_value() == '' and page.locator('#time-cards').count() == 0

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
            # The day of the chart, once per double hour: its own hour shows its own moment; a click casts another
            # hour (as a custom moment in the same zone) and keeps focus there; the arrows move a day at that hour.
            assert page.locator('#qimen-hours .qh-hour').count() == 13
            own = page.locator('#qimen-hours .qh-hour.is-current')
            assert own.get_attribute('id') == 'qimen-hour-7' and '14:30' in own.inner_text() and own.get_attribute('aria-current') == 'true'
            assert page.locator('.qimen-cell .q-stem [class^="el-"]').count() == 27  # heaven, dark and earth stems coloured by element
            page.locator('#qimen-hour-10').click()
            page.wait_for_function("() => document.querySelector('#qimen-hour-10.is-current') !== null", timeout=30000)
            assert page.locator('#qimen-moment').input_value() == 'custom' and page.locator('#qimen-when').input_value() == '2024-06-15T20:00'
            assert page.evaluate('document.activeElement.id') == 'qimen-hour-10' and '时柱 丙戌' in page.locator('.meta-tags').first.inner_text()
            assert page.locator('#qimen-hour-10 .qh-tag').inner_text() == '本盘' and page.locator('.qh-date').inner_text() == '2024-06-15'
            page.locator('#qimen-next-day').click()
            page.wait_for_function("() => document.getElementById('qimen-when').value === '2024-06-16T20:00' && document.querySelector('#qimen-hour-10.is-current')", timeout=30000)
            # The arrows keep their place, and the strip names its day.
            assert page.evaluate('document.activeElement.id') == 'qimen-next-day' and page.locator('.qh-date').inner_text() == '2024-06-16'
            # Cast from the birth moment in true solar time, an hour of the strip keeps that zone and solar time, its
            # clock times are said to be clock times, and changing the birth data sends the page back to the birth moment.
            page.locator('#qimen-moment').select_option('birth')
            page.evaluate('''() => {
              document.querySelector('#time_mode').value = 'apparent_solar'; document.querySelector('#longitude').value = '87.6';
              document.querySelector('#longitude').dispatchEvent(new Event('input', {bubbles: true}));
            }''')
            page.locator('#qimen-run').click()
            page.locator('#qimen-hours').wait_for(timeout=30000)
            assert '钟表时间，按所选太阳时换算' in page.locator('.qh-help').inner_text()
            page.locator('#qimen-hour-6').click()
            page.wait_for_function("() => document.querySelector('#qimen-hour-6.is-current') !== null && qimenMoment.mode === 'custom'", timeout=30000)
            assert '沿用出生资料的真太阳时起局，时区 Asia/Shanghai' in page.locator('#result').inner_text()
            assert page.evaluate('qimenInput.time_mode') == 'apparent_solar' and page.evaluate('qimenInput.longitude') == 87.6
            page.evaluate('''() => {
              document.querySelector('#time_mode').value = 'clock'; document.querySelector('#longitude').value = '';
              document.querySelector('#longitude').dispatchEvent(new Event('input', {bubbles: true}));
            }''')
            page.locator('[data-tab="ziwei"]').click()
            page.locator('[data-tab="qimen"]').click()
            assert page.locator('#qimen-moment').input_value() == 'birth' and page.locator('.qimen-cell').count() == 0
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
            # Tools that open with a result do not run on the 12:00 placeholder, and say so.
            page.locator('[data-tab="annual"]').click()
            assert '命盘时辰不详：本页按 12:00 占位时辰计算' in page.locator('#result').inner_text()
            page.wait_for_timeout(400)
            assert page.locator('.transform-card').count() == 0
            # Run by hand, the year grid names the palaces only: their stem and branch would come from the placeholder.
            page.locator('[data-tab="timeline"]').click()
            page.locator('#timeline-run').click()
            page.locator('#timeline-matrix').wait_for(timeout=30000)
            assert page.locator('#timeline-matrix .yt-palace').count() == 12 and page.locator('#timeline-matrix .yt-branch').count() == 0
            assert '时辰不详：宫位按 12:00 占位时辰排出，落宫会随时辰变化。' in page.locator('#result').inner_text()
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
            # The reading page marks the same open pillars and lists no Zi Wei palace, only the birth-year stars.
            page.locator('[data-tab="reading"]').click()
            page.locator('#reading-bazi').wait_for(timeout=30000)
            open_cells = page.locator('#reading-bazi .reading-pillar .muted').all_inner_texts()
            assert open_cells == ['随时辰而定', '随时辰而定', '时辰不详'], open_cells
            assert page.locator('#reading-bazi .is-master').count() == 1
            assert page.locator('#reading-ziwei .reading-label').all_inner_texts() == ['生年四化', '身主']
            assert page.locator('#reading-ziwei [class*="reading-hua-"]').count() == 4
            assert page.locator('#reading-ziwei [class*="reading-hua-"] small').count() == 0
            assert page.locator('#reading-next-annual').count() == 0 and page.locator('.reading-link').count() == 3
            page.locator('[data-tab="bazi"]').click()
            # With the 23:00 day change the day pillar is open as well: nothing is counted and no day master names ten gods.
            page.evaluate("document.querySelector('#late_zi_day_rollover').checked = true")
            page.locator('#run-btn').click()
            page.wait_for_function("() => document.querySelector('#wuxing') && !document.querySelector('#wuxing .is-master')", timeout=30000)
            assert page.locator('#wuxing .wx-group').count() == 0 and '比肩' not in page.locator('#wuxing-detail').inner_text()
            assert '这四柱都不计入，日主未定，也不标十神。' in page.locator('#result').inner_text()
            page.locator('[data-tab="reading"]').click()
            page.locator('#reading-bazi').wait_for(timeout=30000)
            assert page.locator('#reading-bazi .reading-pillar .muted').count() == 4 and page.locator('#reading-bazi .is-master').count() == 0
            assert '日柱随时辰而定，日主未定，十神暂不标注。' in page.locator('#reading-bazi').inner_text()
            # 2000-02-04 is the last day of the twelfth lunar month, so a 23:00 birth would fall in the new lunar year.
            assert page.locator('#reading-ziwei [class*="reading-hua-"]').count() == 0
            assert page.locator('#reading-ziwei .reading-value').inner_text() == '随时辰而定'
            # The year stem, so every palace stem, is open too: the flying table is held back, not drawn from 12:00.
            page.locator('[data-tab="transform"]').click()
            page.get_by_text('出生当天又在农历年的交界', exact=False).wait_for(timeout=30000)
            assert page.locator('#transform-table, #transform-matrix, .transform-card').count() == 0
            # Which way the day can move decides it. 2000-02-05 is the first day of the first lunar month: the 23:00
            # change only moves the day forward, so the year (and its stars) stays; so it does in mean solar time at
            # 115°E (20 minutes behind the clock), where 23:40 the evening before is counted back to this day.
            def reading_on(day, mode='clock', longitude='', late=False):
                page.locator('[data-tab="bazi"]').click()
                page.evaluate(f"() => {{document.querySelector('#birth_datetime').value = '{day}T12:00'; document.querySelector('#time_mode').value = '{mode}';"
                              f" document.querySelector('#longitude').value = '{longitude}'; document.querySelector('#late_zi_day_rollover').checked = {str(late).lower()};}}")
                page.locator('#run-btn').click()
                page.wait_for_function(f"() => document.querySelector('#result-subtitle').textContent.startsWith('{day}')", timeout=30000)
                page.locator('[data-tab="reading"]').click()
                page.locator('#reading-bazi').wait_for(timeout=30000)
                return page.locator('#reading-ziwei [class*="reading-hua-"]').count()
            assert reading_on('2000-02-05', late=True) == 4
            assert reading_on('2000-02-05', 'mean_solar', '115', late=True) == 4 and '身主' in page.locator('#reading-ziwei').inner_text()
            # Over two hours behind the clock (87.6°E), the small hours fall on the last day of the old year.
            assert reading_on('2000-02-05', 'mean_solar', '87.6') == 0 and page.locator('#reading-ziwei .reading-value').first.inner_text() == '随时辰而定'
            page.locator('[data-tab="bazi"]').click()
            page.evaluate("() => {document.querySelector('#time_mode').value = 'clock'; document.querySelector('#longitude').value = '';}")
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
            installed = professional_provider_available()
            if not installed:
                # Without the provider the page says so, lists what the native chart already has, gives an install
                # command that names the provider package (the project is not on PyPI) and keeps the run button off.
                page.locator('#professional-status.is-missing').wait_for(timeout=30000)
                assert page.locator('#professional-run').is_disabled()
                assert page.locator('#professional-status code').first.inner_text() == 'python -m pip install "iztro-py>=0.1,<1"'
                assert 'xuanshu[professional]' not in page.locator('#result').inner_text()
                page.screenshot(path=str(screenshot_dir / '22-professional-provider-guard.png'), full_page=True)
                # Gender sets the direction of the major limits, so without it the page asks for it.
                page.locator('#gender').select_option('unspecified')
                page.locator('#professional-gender').wait_for(timeout=30000)
                page.locator('#professional-go-gender').click()
                assert page.evaluate("document.activeElement.id") == 'gender'
                page.locator('#gender').select_option('female')
                page.wait_for_function("() => !document.querySelector('#professional-gender')", timeout=30000)
                # A stand-in provider built from XuanShu's own chart, with two deliberate differences, exercises the result.
                install_professional_stand_in(page.evaluate("readInput()"))
                page.locator('#professional-recheck').click()
                page.locator('#professional-status.is-ok').wait_for(timeout=30000)
                assert page.evaluate("document.activeElement.id") == 'professional-status'
            page.locator('#professional-run').click()
            page.locator('#professional-result').wait_for(timeout=60000)
            assert 'iztro-py' in page.locator('#professional-result').inner_text()
            if not installed:
                assert page.locator('#professional-board .pf-palace').count() == 12 and page.locator('#professional-board .pf-palace.is-ming').count() == 1
                assert page.locator('#professional-compare-summary').inner_text().endswith('不同 2')
                kinds = [r.split('\t')[0] for r in page.locator('#professional-compare-table tbody tr').all_inner_texts()]
                assert kinds == ['亮度', '辅星落宫'] and page.locator('#professional-board .pf-palace.has-diff').count() == 2
                assert page.locator('#professional-horoscope-table tbody tr').count() == 2
                # The provider's keys arrive as Chinese names: 交友宫 is iztro's name for 仆役宫, not a difference.
                board_text = page.locator('#professional-board').inner_text()
                assert '交友宫' in board_text and 'soulPalace' not in board_text and 'Maj' not in board_text
                assert page.locator('#professional-board').evaluate("e => e.closest('.pf-board-wrap').getAttribute('role')") == 'region'
                hua_cells = page.locator('#professional-horoscope-table tbody tr').first.locator('td').all_inner_texts()[2:]
                assert hua_cells == ['贪狼', '太阴', '右弼', '天机'], hua_cells
                page.locator('#professional-only-diff').uncheck()
                assert page.locator('#professional-compare-table tbody tr').count() > 90
                page.locator('#professional-only-diff').check()
                page.locator('#professional-raw summary').click()
                page.locator('#professional-raw .jv-tree details').first.wait_for(timeout=30000)
            page.screenshot(path=str(screenshot_dir / '22-professional-provider-success.png'), full_page=True)
            if not installed:
                # Any birth field changed afterwards marks the result as out of date, not only gender or the hour.
                flip = "on => {const box = document.querySelector('#late_zi_day_rollover'); box.checked = on; box.dispatchEvent(new Event('change', {bubbles: true}));}"
                page.evaluate(flip, True)
                page.locator('#professional-stale').wait_for(timeout=30000)
                page.evaluate(flip, False)
                page.wait_for_function("() => !document.querySelector('#professional-stale')", timeout=30000)
                remove_professional_stand_in()
                page.evaluate("capabilities = null")
            page.locator('[data-tab="qimen-audit"]').click()
            # The reference is entered on a nine-palace form; the run button says what is missing until it can run.
            assert page.locator('#qimen-audit-board-form .qr-cell').count() == 9
            assert page.locator('#qimen-audit-run').is_disabled() and '至少' in page.locator('#qimen-audit-count').inner_text()
            page.locator('#qimen-audit-when').fill('2026-10-12T15:30')
            # A time-zone list runs to hundreds of names and is held at its longest one too.
            if page.evaluate("CSS.supports('appearance', 'base-select')"):
                zone_width = page.locator('#qimen-audit-zone').bounding_box()['width']
                page.locator('#qimen-audit-zone').select_option('America/North_Dakota/New_Salem')
                assert abs(page.locator('#qimen-audit-zone').bounding_box()['width'] - zone_width) < 1, zone_width
            page.locator('#qimen-audit-zone').select_option('Asia/Shanghai')
            if page.evaluate("CSS.supports('appearance', 'base-select')"):
                assert abs(page.locator('#qimen-audit-zone').bounding_box()['width'] - zone_width) < 1, zone_width
            page.locator('#qimen-audit-late-zi').uncheck()
            ref_chart = page.evaluate("postJSON('/api/qimen', {moment: qimenAuditMoment(qimenAuditDraft)})")
            ref_palace = {p['number']: p for p in ref_chart['palaces']}
            other_door = next(d for d in ('休门', '生门', '伤门', '杜门') if d != ref_palace[2]['door'])
            page.locator('#qimen-ref-bureau').select_option(str(ref_chart['bureau']))
            assert '将比较 1 项' in page.locator('#qimen-audit-count').inner_text()
            # Every palace select is named by its palace as well as its field.
            assert page.locator('#qimen-ref-4-star').get_attribute('aria-labelledby') == 'qimen-ref-4-legend qimen-ref-4-star-label'
            page.locator('#qimen-ref-dun').select_option(ref_chart['dun'])
            page.locator('#qimen-ref-1-star').select_option(ref_palace[1]['star'])
            page.locator('#qimen-ref-2-door').select_option(other_door)
            assert page.locator('#qimen-audit-run').is_disabled() and '参考来源' in page.locator('#qimen-audit-count').inner_text()
            page.locator('#qimen-audit-source').fill('public independent reference')
            # The school is the reference's own, so it starts empty rather than claiming XuanShu's school.
            assert page.locator('#qimen-audit-school').input_value() == '' and '参考流派' in page.locator('#qimen-audit-count').inner_text()
            page.locator('#qimen-audit-school').fill('时家拆补转盘')
            page.locator('#qimen-audit-when').fill('')
            assert page.locator('#qimen-audit-run').is_disabled() and '日期与时间' in page.locator('#qimen-audit-count').inner_text()
            page.locator('#qimen-audit-when').fill('2026-10-12T15:30')
            assert not page.locator('#qimen-audit-run').is_disabled() and '4' in page.locator('#qimen-audit-count').inner_text()
            assert page.locator('#qimen-audit-message').get_attribute('role') == 'alert'
            page.locator('#qimen-audit-run').click()
            page.locator('#qimen-audit-result').wait_for(timeout=30000)
            # The result lays XuanShu's chart for the same moment over the board and marks each compared field.
            assert page.evaluate("document.activeElement.id") == 'qimen-audit-result'
            assert page.locator('.qr-big').inner_text().replace(' ', '') == '3/4'
            # The result states the moment it describes.
            assert page.locator('.qr-moment').inner_text() == '起局时刻：2026-10-12 15:30 · Asia/Shanghai · 00:00 换日'
            assert page.evaluate("referenceAuditResult.fields.length") == 4 and page.locator('#qimen-audit-root tbody tr').count() == 2
            assert 'is-diff' in page.locator('#qimen-audit-palace-2').get_attribute('class')
            assert other_door in page.locator('#qimen-audit-palace-2 .qr-mark.is-diff').inner_text()
            assert 'is-ok' in page.locator('#qimen-audit-palace-1').get_attribute('class')
            assert 'is-none' in page.locator('#qimen-audit-palace-9').get_attribute('class')
            assert page.locator('#qimen-audit-stale').is_hidden()
            page.locator('#qimen-ref-1-star').select_option('')
            assert page.locator('#qimen-audit-stale').is_visible()
            # Pasted JSON fills the form, keeping fields the form has no select for.
            page.locator('#qimen-audit-json summary').click()
            # Values are checked before anything is filled: a yes/no field takes true or false, a palace appears once.
            for bad, says in (('{"palaces":[{"number":1,"void":"yes"}]}', '需为 true 或 false'),
                              ('{"palaces":[{"number":1,"star":"天蓬"},{"number":1,"door":"休门"}]}', '宫位重复'),
                              ('{"root_fields":{"bureau":"x"}}', '需为 1…9 的整数'), ('{"extra":1}', '不认识的字段')):
                page.locator('#qimen-audit-input').fill(bad)
                page.locator('#qimen-audit-load').click()
                assert says in page.locator('#qimen-audit-load-msg').inner_text(), bad
            page.locator('#qimen-audit-input').fill('{"moment":{"birth_datetime":"2024-02-10T10:00","timezone":"Asia/Shanghai"},"reference_source":"public independent reference","reference_school":"时家拆补转盘","root_fields":{"bureau":9,"zhi_fu_origin":3},"palaces":[{"number":1,"star":"天芮禽","trigram":"坎"},{"number":5,"deity":"值符"}]}')
            page.locator('#qimen-audit-load').click()
            page.wait_for_function("document.querySelector('#qimen-ref-bureau').value === '9'", timeout=30000)
            # The pasted moment fills step 1, a value outside the list stays visible, and the count is announced.
            assert page.locator('#qimen-audit-when').input_value() == '2024-02-10T10:00'
            assert page.locator('#qimen-ref-1-star').input_value() == '天芮禽' and page.locator('#qimen-ref-2-door').input_value() == ''
            assert '天芮禽（JSON）' in page.locator('#qimen-ref-1-star option:checked').inner_text()
            assert page.locator('#qimen-audit-load-msg').inner_text() == '已填入 5 项'
            # A finished count is not drawn as work in progress, and the JSON box keeps its own role and name.
            assert 'ok' in page.locator('#qimen-audit-load-msg').get_attribute('class').split()
            assert page.locator('#qimen-audit-input').get_attribute('role') is None and page.locator('#qimen-audit-input').get_attribute('aria-label') is None
            assert page.locator('#qimen-audit-input').input_value().startswith('{"moment"')
            assert '值符原宫 3' in page.locator('.qr-extra-root').inner_text()
            assert '值符' in page.locator('#qimen-audit-board-form .qr-cell.center .qr-extra').inner_text()
            page.locator('#qimen-audit-run').click()
            page.wait_for_function("referenceAuditResult && referenceAuditResult.fields.some(f => f.field === 'zhi_fu_origin')", timeout=30000)
            assert '值符' in page.locator('#qimen-audit-palace-5').inner_text()
            assert page.locator('.qr-moment').inner_text().startswith('起局时刻：2024-02-10 10:00')
            # A field from JSON can be removed, and a cleared board can be restored.
            page.locator('.qr-extra-root .qr-extra-remove').click()
            page.wait_for_function("!document.querySelector('.qr-extra-root')", timeout=30000)
            assert page.evaluate("!('zhi_fu_origin' in qimenAuditDraft.root)")
            page.locator('#qimen-audit-clear').click()
            page.locator('#qimen-audit-undo').wait_for(timeout=30000)
            assert page.evaluate("document.activeElement.id") == 'qimen-audit-undo' and page.locator('#qimen-ref-bureau').input_value() == ''
            page.locator('#qimen-audit-undo').click()
            page.wait_for_function("document.querySelector('#qimen-ref-bureau').value === '9'", timeout=30000)
            assert page.locator('#qimen-audit-undo').count() == 0
            assert page.evaluate("UI_EXTRA['参考盘：'][0]") == 'Reference: ' and page.evaluate("UI_EXTRA['将比较 1 项'][0]") == 'Will compare 1 item'
            page.screenshot(path=str(screenshot_dir / '23-qimen-audit.png'), full_page=True)
            page.locator('[data-tab="ziwei"]').click()
            assert page.locator('.palace-btn').count() == 12
            page.locator('.palace-btn').first.click()
            assert page.locator('.palace-btn.selected').count() == 1
            page.screenshot(path=str(screenshot_dir / '02-ziwei-desktop.png'), full_page=True)

            # Month calendar: a month at a glance with lunar dates, solar terms and day pillars; the keyboard moves the pick.
            page.locator('[data-tab="calendar"]').click()
            page.locator('#calendar-grid').wait_for(timeout=30000)
            assert page.locator('#calendar-day-' + page.evaluate('localToday()')).get_attribute('aria-current') == 'date'
            # While a month loads, its grid is already drawn (Gregorian days, hidden from screen readers), and once
            # it has come the months before and after are fetched while the page is idle.
            page.evaluate("() => {window.__postJSON = postJSON; window.__release = null; postJSON = (url, body) => url === '/api/calendar' ? new Promise(go => {window.__release = go;}).then(() => window.__postJSON(url, body)) : window.__postJSON(url, body);}")
            page.evaluate("() => showCalendarDay('1990-05-10')")
            page.locator('#calendar-loading').wait_for(timeout=5000)
            assert page.locator('.cal-skeleton[aria-hidden=true] .cal-grid .cal-day').count() == 31
            assert page.locator('.cal-skeleton .cal-title').inner_text() == '1990年5月' and page.locator('.cal-skeleton button').count() == 0
            page.evaluate("() => {postJSON = window.__postJSON; window.__release();}")
            page.locator('#calendar-day-1990-05-31').wait_for(timeout=30000)
            assert page.locator('.cal-skeleton').count() == 0
            page.wait_for_function("() => calendarMonths['1990-04'] && calendarMonths['1990-04'].days && calendarMonths['1990-06'] && calendarMonths['1990-06'].days", timeout=15000)
            page.evaluate("() => showCalendarDay('2024-02-10')")
            page.locator('#calendar-day-2024-02-29').wait_for(timeout=30000)
            # February 2024 begins on a Thursday: three blank cells before the 1st and three after the 29th.
            assert page.locator('#calendar-grid .cal-day').count() == 29 and page.locator('#calendar-grid .cal-blank').count() == 6
            assert page.locator('#calendar-title').inner_text() == '2024年2月'
            new_year = page.locator('#calendar-day-2024-02-10')
            assert new_year.locator('xpath=..').get_attribute('aria-selected') == 'true' and '甲辰' in new_year.inner_text()
            # The day label is written in the interface language when drawn, so the page translator leaves it alone.
            assert new_year.get_attribute('data-no-i18n') == '' and new_year.get_attribute('aria-label').startswith('2024-02-10 · 星期六 · 农历 正月初一')
            assert '立春' in page.locator('#calendar-day-2024-02-04').inner_text()
            assert '月柱 丙寅' in page.locator('#calendar-terms').inner_text()  # 立春 opens the 寅 month of a 甲 year
            detail = page.locator('#calendar-detail').inner_text()
            assert '农历 甲辰 · 正月初一' in detail and '日柱 甲辰' in detail and '星期六' in detail, detail
            # Festivals, 三伏 and 数九 are calendar facts too: a festival takes the cell (正月初一 shows 春节), a nine
            # shows on its first day, and the detail names each with the rule that places it.
            assert '春节' in new_year.inner_text() and 'cal-festival' in new_year.get_attribute('class')
            assert '除夕' in page.locator('#calendar-day-2024-02-09').inner_text()
            assert '六九' in page.locator('#calendar-day-2024-02-05').inner_text() and 'cal-season' in page.locator('#calendar-day-2024-02-05').get_attribute('class')
            marks = page.locator('#calendar-marks').inner_text()
            assert marks.index('除夕') < marks.index('春节 02/10') < marks.index('元宵节 02/24') and '七九 02/14' in marks, marks
            assert '节日：春节' in detail and '数九：六九 第6天（共9天）' in detail and '冬至当天起每九天为一九' in detail, detail
            # The two 小年 fall on neighbouring days and keep their region in the cell.
            assert '北方小年' in page.locator('#calendar-day-2024-02-02').inner_text() and '南方小年' in page.locator('#calendar-day-2024-02-03').inner_text()
            # The text export names each mark with a space before its day count, and lists the rules of the marks shown.
            export = page.locator('#calendar-text-text').text_content()
            assert '春节、六九 第6天（共9天）' in export and '【节令推算规则】' in export and '冬至当天起每九天为一九' in export, export[-400:]
            assert new_year.get_attribute('aria-label').endswith('春节 · 六九 第6天（共9天）')
            assert page.locator('#calendar-festival-ics').get_attribute('href') == '/api/solar-terms/2024.ics?festivals=true'
            # In English a cell takes a short everyday name (New Year, Lantern, 6th Nine) that fits two lines, and the
            # detail reads "Festival: Spring Festival", "Nine nines: Sixth Nine, day 6 of 9".
            page.locator('#ui-language').select_option('en')
            page.wait_for_function("() => document.getElementById('calendar-day-2024-02-24').textContent.includes('Lantern')", timeout=10000)
            assert 'New Year' in page.locator('#calendar-day-2024-02-10').inner_text() and '6th Nine' in page.locator('#calendar-day-2024-02-05').inner_text()
            assert 'Xiaonian (N)' in page.locator('#calendar-day-2024-02-02').inner_text()
            detail = page.locator('#calendar-detail').inner_text()
            assert 'Festival: Spring Festival' in detail and 'Sixth Nine, day 6 of 9' in detail, detail
            # No named cell is cut off: each fits its two lines.
            cut = page.evaluate("() => [...document.querySelectorAll('.cal-day .cal-lunar')].filter(el => el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1).map(el => el.textContent)")
            assert cut == [], cut
            page.locator('#ui-language').select_option('zh-CN')
            page.wait_for_function("() => document.getElementById('calendar-day-2024-02-10').textContent.includes('春节')", timeout=10000)
            new_year.focus()
            page.keyboard.press('ArrowRight')
            assert page.evaluate('document.activeElement.id') == 'calendar-day-2024-02-11'
            page.keyboard.press('ArrowUp')
            assert page.evaluate('document.activeElement.id') == 'calendar-day-2024-02-04' and page.evaluate('calendarSelected') == '2024-02-04'
            page.keyboard.press('PageDown')
            page.wait_for_function("() => document.activeElement && document.activeElement.id === 'calendar-day-2024-03-04'", timeout=30000)
            page.locator('#calendar-prev').click()
            page.locator('#calendar-day-2024-02-01').wait_for(timeout=30000)
            assert page.evaluate('document.activeElement.id') == 'calendar-prev'
            assert '2024-02-10' in page.locator('#calendar-text-text').text_content() and '正月初一' in page.locator('#calendar-text-text').text_content()
            # The same month downloads as a spreadsheet table: UTF-8 with a byte-order mark, one row a day. Blob.text()
            # would drop the mark, so the bytes are decoded with it kept.
            page.evaluate("() => {window.__csv = null; window.__keepDownload = downloadBlob; downloadBlob = (blob, name) => {blob.arrayBuffer().then(bytes => {window.__csv = [name, blob.type, new TextDecoder('utf-8', {ignoreBOM: true}).decode(bytes)];});};}")
            page.locator('#calendar-text-csv').click()
            page.wait_for_function('() => window.__csv !== null', timeout=5000)
            csv_name, csv_type, csv = page.evaluate('window.__csv')
            page.evaluate('() => {downloadBlob = window.__keepDownload;}')
            assert csv_name == 'xuanshu-calendar-2024-02.csv' and csv_type.startswith('text/csv'), (csv_name, csv_type)
            assert csv.startswith('\ufeff公历,星期,农历,日柱,节气（中国标准时间）,节令,节令推算规则,节令提醒\r\n') and csv.count('\r\n') == 30, csv[:120]
            assert '\r\n2024-02-10,' in csv and '春节' in csv.split('\r\n2024-02-10,')[1].split('\r\n')[0], csv[:400]
            assert '春节：农历正月初一' in csv.split('\r\n2024-02-10,')[1].split('\r\n')[0], csv[:400]
            # The file has no rule list at its end, so a count whose start is in doubt says so on its own row: 1951's
            # winter solstice falls 0.8 s after midnight, so the nines of January 1952 carry the warning.
            doubt = page.evaluate("() => ensureCalendarMonth(1952, 1).then(data => csvText(calendarRows(data, '节气', true)))")
            doubt_row = doubt.split('\r\n1952-01-10,')[1].split('\r\n')[0]
            assert '冬至当天起每九天为一九' in doubt_row and '数九的起算日可能相差一天' in doubt_row, doubt_row
            page.screenshot(path=str(screenshot_dir / '05-calendar.png'), full_page=True)
            # A lunar date turned into a Gregorian one is picked on the calendar.
            page.locator('#calendar-next').click()
            page.locator('#calendar-day-2024-03-01').wait_for(timeout=30000)
            page.locator('#lunar-inverse-year').fill('2024')
            page.locator('#lunar-inverse-month').select_option('1')
            # 正月 of 2024 has 29 days: the error stays on the page through the redraw.
            page.locator('#lunar-inverse-day').select_option('30')
            page.locator('#lunar-inverse-run').click()
            page.get_by_text('换算失败', exact=False).first.wait_for(timeout=30000)
            assert page.locator('#lunar-inverse-result').count() == 0
            page.locator('#lunar-inverse-day').select_option('1')
            page.locator('#lunar-inverse-run').click()
            page.get_by_text('公历 2024-02-10', exact=False).first.wait_for(timeout=30000)
            assert page.evaluate('calendarSelected') == '2024-02-10' and page.locator('#calendar-day-2024-02-10').locator('xpath=..').get_attribute('aria-selected') == 'true'
            assert '换算失败' not in page.locator('#result').inner_text()
            # The picked day opens in 今日历法, and 今日历法 opens its day on the calendar.
            page.locator('#calendar-open-day').click()
            page.locator('[data-tab="today"][aria-selected="true"]').wait_for(timeout=10000)
            page.wait_for_function("() => todayPick && todayPick.date === '2024-02-10'", timeout=10000)
            page.locator('#today-date').wait_for(timeout=30000)
            assert page.locator('#today-date').input_value() == '2024-02-10'
            # The day card names the festival and the nine with the day of it; each tag takes the focus and shows the rule
            # that places it (a festival's is its lunar date).
            page.locator('.today-mark-festival').wait_for(timeout=30000)
            assert page.locator('.today-mark-festival').inner_text() == '春节' and page.locator('.today-mark-shujiu').inner_text() == '六九 第6天（共9天）'
            assert page.locator('.today-mark-shujiu').get_attribute('data-tip').startswith('冬至当天起')
            assert page.locator('.today-mark-festival').get_attribute('data-tip') == '农历 正月初一'
            assert page.locator('.today-mark-festival').get_attribute('tabindex') == '0'
            page.locator('#today-calendar').click()
            page.wait_for_function("() => document.activeElement && document.activeElement.id === 'calendar-day-2024-02-10'", timeout=30000)
            page.evaluate("() => { todayPick = null; }")
            # The range ends: no month before January 1901 or after December 2099.
            page.evaluate("() => showCalendarDay('2099-12-15')")
            page.locator('#calendar-day-2099-12-31').wait_for(timeout=30000)
            assert page.locator('#calendar-next').is_disabled() and not page.locator('#calendar-prev').is_disabled()
            page.evaluate("() => showCalendarDay('1901-01-15')")
            page.locator('#calendar-day-1901-01-01').wait_for(timeout=30000)
            assert page.locator('#calendar-prev').is_disabled() and not page.locator('#calendar-next').is_disabled()

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
            assert page.locator('#pair-elements tbody tr').first.locator('.em-master small').all_inner_texts() == ['日主', '比劫']
            assert page.locator('#pair-elements th[scope=col]').nth(1).get_attribute('aria-label') == '木'
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
            # With a gender the decades of the chart shown are worked out on opening; the button applies a new count.
            assert page.evaluate('currentInput.gender') != 'unspecified'
            page.locator('#dayun-table').wait_for(timeout=30000)
            assert page.locator('#dayun-table tbody tr').count() == 10 and page.locator('#dayun-table tr.is-current').count() == 1
            page.locator('#dayun-periods').fill('8')
            page.locator('#dayun-run').click()
            page.wait_for_function("() => document.querySelectorAll('#dayun-table tbody tr').length === 8", timeout=30000)
            page.locator('#dayun-periods').fill('10')
            page.locator('#dayun-run').click()
            page.wait_for_function("() => document.querySelectorAll('#dayun-table tbody tr').length === 10", timeout=30000)
            # The starting age is worked out step by step; the axis has a band per decade, opens on the current one
            # and a band opens its own decade with its years, keeping the focus on the band.
            assert '÷ 3' in page.locator('.dy-start').inner_text() and page.locator('.dy-start .dy-node').count() == 2
            assert page.locator('#dayun-axis .dy-decade').count() == 10 and page.locator('#dayun-axis .dy-decade.is-now').count() == 1
            assert page.locator('#dayun-axis .dy-decade.is-now').get_attribute('aria-pressed') == 'true'
            assert page.locator('#dayun-years tbody tr').count() == 10 and page.locator('#dayun-detail .dy-hidden').count() >= 1
            page.locator('#dayun-band-5').click()
            page.wait_for_function("() => document.querySelector('#dayun-band-5').getAttribute('aria-pressed') === 'true' && document.activeElement.id === 'dayun-band-5'", timeout=30000)
            assert page.locator('#dayun-detail .dy-detail-gz').inner_text() == page.locator('#dayun-band-5 .dy-band-gz').inner_text()
            assert page.locator('#dayun-axis [aria-pressed="true"]').count() == 1
            assert any(t.count(':') == 3 for t in page.locator('.dy-start .dy-node small').all_inner_texts())  # the solar term to the second, with its offset
            assert page.locator('#result thead th').last.inner_text() == '神煞'
            page.screenshot(path=str(screenshot_dir / '17-dayun-desktop.png'), full_page=True)
            # Whole days carry into a month and months into a year, so the age never reads 30 days or 12 months.
            assert page.evaluate("JSON.stringify(startAgeParts({start_age_traditional_parts: {years: 7, months: 5, days_nominal_30_day_month: 29.6}}))") == '{"years":7,"months":6,"days":0}'
            assert page.evaluate("JSON.stringify(startAgeParts({start_age_traditional_parts: {years: 6, months: 11, days_nominal_30_day_month: 29.7}}))") == '{"years":7,"months":0,"days":0}'
            # Today is read before the decades and drawn only in the gutters; the band before the first decade shows its label.
            assert page.evaluate("[...document.querySelector('#dayun-axis').children].findIndex(c => c.classList.contains('dy-today'))") in (-1, 0)
            assert page.evaluate("document.querySelector('#dayun-axis .dy-before small').getBoundingClientRect().height") > 0
            assert page.evaluate("getComputedStyle(document.querySelector('#dayun-axis .dy-today') || document.body, '::before').height") in ('24px', 'auto')
            # Picking a decade is announced, and the detail has its own heading.
            page.locator('#dayun-band-3').click()
            page.wait_for_function("() => document.querySelector('#live-status').textContent.includes(document.querySelector('#dayun-band-3 .dy-band-gz').textContent)", timeout=30000)
            assert page.locator('#dayun-detail-title').count() == 1
            # Cast without the hour on a day a jie begins, the sequence itself depends on the hour: the page says so and
            # keeps only the placeholder table.
            birth_before = page.evaluate('currentInput.birth_datetime')
            page.locator('#birth_datetime').fill('2000-08-07T12:00')
            page.locator('#hour_unknown').check()
            page.locator('#run-btn').click()
            page.wait_for_function("() => currentHourUnknown && currentInput.birth_datetime.startsWith('2000-08-07')", timeout=30000)
            page.locator('#dayun-open').wait_for(timeout=30000)
            assert '立秋' in page.locator('#dayun-open').inner_text() and page.locator('#dayun-axis').count() == 0
            page.locator('#dayun-table').wait_for(timeout=30000)
            assert '只是其中一种可能' in page.locator('#result').inner_text() and '起运随时辰而定' in page.locator('#result').inner_text()
            page.locator('#hour_unknown').uncheck()
            page.locator('#birth_datetime').fill(birth_before)
            page.locator('#run-btn').click()
            page.wait_for_function(f"() => !currentHourUnknown && currentInput.birth_datetime === {birth_before!r}", timeout=30000)
            page.locator('#dayun-axis').wait_for(timeout=30000)
            # The data browser: a card per tool with a result, trees that fill in as they open, a filter over keys and values.
            page.locator('[data-tab="json"]').click()
            assert page.locator('#json-section-chart').count() == 1 and page.locator('#json-section-bazi_dayun').count() == 1
            assert page.locator('#json-section-chart .jv-tree > details').count() >= 3 and page.locator('#json-section-chart .jv-tree details[open]').count() == 0
            page.locator('#json-section-bazi_dayun .jv-tree > details').first.locator('summary').click()
            page.locator('#json-section-bazi_dayun .jv-tree > details').first.locator(':scope > .jv-children').wait_for(timeout=5000)  # filled as it opens
            page.locator('#json-filter').fill('natal_month_pillar')
            page.wait_for_function("() => document.querySelector('#json-filter-count').textContent.includes('处匹配')", timeout=10000)
            match = page.locator('#json-section-bazi_dayun .jv-leaf.is-match')
            assert match.count() == 1 and match.get_attribute('data-tip') == 'bazi_dayun.natal_month_pillar' and '甲申' in match.inner_text()
            assert page.locator('#json-filter-count').inner_text() == '1 处匹配'
            assert page.locator('#json-section-chart').count() == 0
            page.locator('#json-filter').fill('zzz-no-such-field')
            page.wait_for_function("() => document.querySelector('#json-filter-count').textContent.includes('没有匹配')", timeout=10000)
            page.locator('#json-filter').fill('')
            page.wait_for_function("() => document.querySelectorAll('#json-sections .jv-card').length > 1", timeout=10000)
            page.locator('#json-view-raw').click()
            assert '"bazi_dayun"' in page.locator('#json-raw').inner_text() and page.locator('#json-view-raw').get_attribute('aria-pressed') == 'true'
            page.locator('#json-view-tree').click()
            # The count is every match across the cards, against a walk of the same data; at most 400 are drawn, and a card
            # whose name contains the query (bazi_dayun for "day") is still filtered to its matches.
            page.locator('#json-filter').fill('day')
            page.wait_for_function("() => document.querySelector('#json-filter-count').textContent.includes('处匹配')", timeout=10000)
            brute = page.evaluate('''() => {let n = 0; const q = 'day';
              const walk = v => {if (!(v && typeof v === 'object')) return; for (const [k, x] of Object.entries(v)) {
                if (!Array.isArray(v) && k.toLowerCase().includes(q)) n++; else if (!(x && typeof x === 'object') && String(x).toLowerCase().includes(q)) n++;
                walk(x);}};
              Object.entries(jsonData()).forEach(([k, v]) => {if (k !== 'birth_hour_unknown' && v != null) walk(v);}); return n;}''')
            count_text = page.locator('#json-filter-count').inner_text()
            assert str(brute) in count_text and (('只显示前' in count_text) == (brute > 400)), (brute, count_text)
            assert page.locator('#json-sections .is-match').count() == min(brute, 400)
            assert page.locator('#json-section-bazi_dayun .is-match').count() > 0
            page.locator('#json-filter').fill('')
            page.wait_for_function("() => document.querySelectorAll('#json-sections .jv-card').length > 1", timeout=10000)
            # Labels are source text, so they follow a language switch; the card size is that of its download.
            assert page.locator('#json-section-chart .jv-actions button').first.get_attribute('aria-label') == '复制本节 当前命盘（八字、紫微与解读）'
            # Editing the birth data on this page withdraws the downloads at once, and reverting brings them back.
            birth_now = page.locator('#birth_datetime').input_value()
            page.locator('#birth_datetime').fill('1990-01-01T10:00')
            page.wait_for_function("() => document.getElementById('json-download').disabled", timeout=10000)
            assert '出生资料已修改' in page.locator('#result').inner_text() and page.locator('#json-section-chart .jv-actions button').nth(1).is_disabled()
            page.locator('#birth_datetime').fill(birth_now)
            page.wait_for_function("() => !document.getElementById('json-download').disabled", timeout=10000)
            page.locator('[data-tab="boundaries"]').click()
            page.locator('#boundary-radius').fill('8')
            page.locator('#boundary-run').click()
            # The opening result is for ±60 minutes; wait for the ±8 one the button asked for.
            page.get_by_text('±8分钟',exact=False).first.wait_for(timeout=30000)
            page.get_by_text('各区间代表命盘',exact=False).first.wait_for(timeout=30000)
            # The interval drawn as a line: a band per segment card, a tick per switch, one pin and one birth segment.
            cards = page.locator('.bt-card').count()
            assert cards >= 1 and page.locator('#boundary-timeline .bt-seg').count() == cards
            assert page.locator('#boundary-timeline .bt-tick').count() == page.locator('#boundary-switches li').count() == cards - 1
            assert page.locator('#boundary-timeline .bt-pin').count() == 1 and page.locator('.bt-card.is-birth').count() == 1
            # 立春 2000 falls at 20:40:23 and the hour changes at 21:00: each switch says what it changes.
            page.evaluate("""async () => {boundaryResult = await postJSON('/api/birth-boundaries',
              {birth: {...readInput(), birth_datetime: '2000-02-04T20:30', timezone: 'Asia/Shanghai', time_mode: 'clock', longitude: null, late_zi_day_rollover: false}, uncertainty_minutes: 60}); render();}""")
            page.wait_for_function("() => document.querySelectorAll('#boundary-switches li').length === 2", timeout=30000)
            first, second = page.locator('#boundary-switches li').all_inner_texts()
            assert '20:40:23' in first and '节令界 · 立春' in first and '年柱 己卯 → 庚辰' in first and '月柱 丁丑 → 戊寅' in first, first
            assert '21:00' in second and '时辰界' in second and '时柱 庚戌 → 辛亥' in second and '命宫 卯 → 寅' in second, second
            assert page.locator('#boundary-segment-1').get_attribute('class') == 'bt-card is-birth'
            assert page.locator('#boundary-segment-3 .bt-pillar.is-changed').count() == 3  # year, month and hour differ from the birth's
            assert '1 小时 10 分' in page.locator('#boundary-segment-1 .bt-card-head').inner_text()
            page.screenshot(path=str(screenshot_dir / '18-boundaries-desktop.png'), full_page=True)
            # An older reply landing after a newer run of the same tool is dropped: hold the ±60 reply back,
            # redraw (which brings back an enabled button), run ±8, then let the ±60 reply arrive.
            page.evaluate("""() => {
              const real = window.fetch; window.heldBack = null;
              window.fetch = (path, opt) => path === '/api/birth-boundaries' && JSON.parse(opt.body).uncertainty_minutes === 60
                ? new Promise(resolve => {window.heldBack = () => real(path, opt).then(resolve);}) : real(path, opt);
              window.restoreFetch = () => {window.fetch = real;};
            }""")
            page.locator('#boundary-radius').fill('60')
            page.locator('#boundary-run').click()
            page.wait_for_function('() => window.heldBack !== null')
            page.evaluate('() => render()')
            page.locator('#boundary-radius').fill('8')
            page.locator('#boundary-run').click()
            page.get_by_text('±8分钟', exact=False).first.wait_for(timeout=30000)
            page.evaluate('() => window.heldBack()')
            page.wait_for_timeout(500)
            assert '±8分钟' in page.locator('#result').inner_text() and '±60分钟' not in page.locator('#result').inner_text()
            page.evaluate('() => window.restoreFetch()')

            # All three independently implemented 开发阶段 workflows must work from visible controls.
            page.locator('[data-tab="officers"]').click()
            # The coming 30 days are laid out a week per row on opening; the button applies a new range.
            page.locator('#officer-grid .of-day').first.wait_for(timeout=30000)
            assert page.locator('#officer-grid .of-day').count() == 30
            assert page.locator('#officer-grid tbody tr').count() * 7 == page.locator('#officer-grid td').count()
            # Today fills its date and is the cell marked as the current date.
            assert page.locator('#officer-grid .of-day.is-today').count() == 1 and page.locator('#officer-grid [aria-current="date"]').count() == 1
            page.locator('#officer-days').select_option('7')
            page.locator('#officer-run').click()
            page.wait_for_function("() => document.querySelectorAll('#officer-grid .of-day').length === 7", timeout=30000)
            # 立冬 2026 falls at 17:52 Beijing time: the noon officer is still 闭 and 开 follows the term.
            page.locator('#officer-date').fill('2026-11-01')
            page.locator('#officer-days').select_option('14')
            page.locator('#officer-run').click()
            page.wait_for_function("() => document.querySelector('#officer-day-2026-11-14')", timeout=30000)
            jie_day = page.locator('#officer-day-2026-11-07')
            assert 'is-jie' in jie_day.get_attribute('class') and jie_day.locator('.of-officer').inner_text() == '闭'
            assert jie_day.locator('.of-jie-swap').inner_text() == '17:52 → 开' and jie_day.locator('.of-jie-swap b').inner_text() == '开'
            assert jie_day.locator('.of-jie .visually-hidden').text_content() == '立冬 17:52 · 节后 开'
            assert page.locator('#officer-grid .of-day.is-jie').count() == 1
            # The first row starts on Monday: 2026-11-01 is a Sunday, so six blank cells lead.
            assert page.locator('#officer-grid tbody tr').first.locator('.of-blank').count() == 6
            page.locator('#officer-mark-10').click()
            assert page.locator('#officer-mark-10').get_attribute('aria-pressed') == 'true'
            assert page.locator('#officer-grid .of-day.is-mark').count() == 2 and page.locator('#officer-grid .of-day.is-dim').count() == 12
            assert 'is-mark-jie' in jie_day.get_attribute('class') and 'is-mark-jie' not in page.locator('#officer-day-2026-11-06').get_attribute('class')
            assert '其中 1 天 只在交节前或交节后' in page.locator('.of-summary').inner_text()
            page.locator('#officer-view-list').click()
            assert page.locator('#officer-list tbody tr').count() == 14 and page.locator('#officer-list tr.is-mark').count() == 2
            assert '立冬' in page.locator('#officer-list tr.is-mark').nth(1).inner_text()
            page.locator('#officer-view-grid').click()
            # 立春 2026 falls at 04:02: noon is already 危, so the cell names 成 as the officer before the term, and 成 marks it.
            page.locator('#officer-date').fill('2026-02-01')
            page.locator('#officer-days').select_option('7')
            page.locator('#officer-run').click()
            page.wait_for_function("() => document.querySelector('#officer-day-2026-02-07')", timeout=30000)
            lichun = page.locator('#officer-day-2026-02-04')
            assert lichun.locator('.of-officer').inner_text() == '危' and lichun.locator('.of-jie-swap').inner_text() == '成 → 04:02'
            page.locator('#officer-mark-8').click()
            assert 'is-mark-jie' in lichun.get_attribute('class')
            page.locator('#officer-mark-all').click()
            assert page.locator('#officer-grid .of-day.is-dim').count() == 0
            page.locator('#officer-date').fill(page.evaluate('localToday()'))
            page.locator('#officer-days').select_option('30')
            page.locator('#officer-run').click()
            page.wait_for_function("() => document.querySelectorAll('#officer-grid .of-day').length === 30", timeout=30000)
            assert '十二值日' in page.locator('#result').inner_text()
            page.screenshot(path=str(screenshot_dir / '14-day-officers-desktop.png'), full_page=True)

            page.locator('[data-tab="timeline"]').click()
            years_shown = "() => document.querySelectorAll('#timeline-matrix thead .yt-year').length"
            # A setting picked while the opening result is still on its way stays in its field through the redraw
            # that result brings, and the button (enabled again once it lands) applies it.
            page.locator('#timeline-years').select_option('5')
            page.locator('#timeline-matrix').wait_for(timeout=30000)
            assert page.evaluate(years_shown) in (5, 10) and page.locator('#timeline-years').input_value() == '5'
            page.locator('#timeline-run').click()
            page.wait_for_function(years_shown + " === 5", timeout=30000)
            assert page.locator('#timeline-years').input_value() == '5'
            page.locator('#timeline-years').select_option('10')
            page.locator('#timeline-focus').select_option('官禄宫')
            page.locator('#timeline-run').click()
            page.wait_for_function(years_shown + " === 10 && document.querySelector('#timeline-matrix tr.is-focus')", timeout=30000)
            # The palace-by-year grid: twelve palaces, each year's four transformations once, this lunar year tinted.
            assert page.locator('#timeline-matrix tbody tr').count() == 12 and page.locator('#timeline-matrix .hua').count() == 40
            assert page.locator('#timeline-matrix tr.is-focus th').inner_text().startswith('官禄宫')
            assert page.locator('#timeline-matrix thead .is-now').count() == 1
            # This lunar year is named, not only tinted, and is the column marked as the current date.
            now_year = page.locator('#timeline-matrix thead [aria-current="date"]')
            assert now_year.count() == 1 and now_year.locator('.yt-now').inner_text() == '今年'
            assert page.locator('#timeline-matrix .yt-branch').count() == 12 and page.locator('#timeline-matrix .hua.layer').count() == 40
            # A year reached by the keyboard is scrolled out from under the sticky palace column.
            gap = page.evaluate("""() => {
                const wrap = document.querySelector('.yt-wrap'); wrap.style.maxWidth = '320px'; wrap.scrollLeft = wrap.scrollWidth;
                const year = document.querySelector('#timeline-matrix thead .yt-year'); year.focus();
                const gap = year.getBoundingClientRect().left - document.querySelector('#timeline-matrix .yt-corner').getBoundingClientRect().right;
                wrap.style.maxWidth = ''; return wrap.scrollWidth > 320 ? gap : null;
            }""")
            assert gap is not None and gap >= -1, gap
            # Print leaves the grid out (it cannot fit a page) and carries every year as the list.
            page.emulate_media(media='print')
            assert not page.locator('#timeline-matrix').is_visible() and page.locator('.yt-print-list tbody tr').count() == 10
            assert page.locator('.yt-print-list tbody tr[aria-current="date"]').count() == 1
            page.emulate_media(media='screen')
            assert not page.locator('.yt-print-list').is_visible()
            hua_total = sum(int(t[1:]) for t in page.locator('#timeline-matrix .yt-count').all_inner_texts())
            assert hua_total == 40, hua_total
            # The list by year keeps the selected palace's column; a year opens the Zi Wei year layer.
            page.locator('#timeline-view-list').click()
            assert page.locator('#timeline-list tbody tr').count() == 10 and page.locator('#timeline-list thead th').last.inner_text() == '所选宫位'
            assert page.locator('#timeline-view-list').get_attribute('aria-pressed') == 'true'
            page.locator('#timeline-view-matrix').click()
            assert '年度轨迹' in page.locator('#result').inner_text()
            page.screenshot(path=str(screenshot_dir / '15-annual-timeline-desktop.png'), full_page=True)
            first_year = page.locator('#timeline-matrix thead .yt-year').first.get_attribute('id').split('-')[-1]
            page.locator('#timeline-matrix thead .yt-year').first.click()
            page.wait_for_function("() => active === 'ziwei' && ziweiLayer.mode === 'year'", timeout=30000)
            assert page.evaluate('ziweiLayer.year') == int(first_year)
            page.locator('#ziwei-layer-natal').click()

            page.locator('[data-tab="decision"]').click()
            # Options by criteria in one grid: criteria across the header, an option per row.
            assert page.locator('#decision-grid thead .criterion-edit').count() == 2 and page.locator('#decision-grid tbody tr').count() == 2
            page.locator('#decision-add-criterion').click()
            assert page.locator('.criterion-edit').count() == 3 and page.locator('#decision-grid tbody tr').first.locator('.option-rating').count() == 3
            assert page.evaluate('document.activeElement.id') == 'decision-criterion-2'
            page.locator('.remove-criterion').last.click()
            # Focus moves to the criterion that is now last rather than falling back to the page.
            assert page.locator('.criterion-edit').count() == 2 and page.evaluate('document.activeElement.id') == 'decision-criterion-1'
            page.locator('#decision-add-option').click()
            assert page.locator('.option-edit').count() == 3 and page.evaluate('document.activeElement.id') == 'decision-option-2'
            page.locator('.remove-option').last.click()
            assert page.locator('.option-edit').count() == 2
            assert page.locator('.remove-option').first.is_disabled()
            # Each rating is named by its option and criterion as typed.
            rating_name = "(el) => el.getAttribute('aria-labelledby').split(' ').map(id => document.getElementById(id).value).join(' ')"
            assert page.locator('#decision-grid .option-rating').nth(1).evaluate(rating_name) == '方案 A 维护成本'
            # Each weight by its criterion as typed and the word 权重.
            weight_name = "(el) => el.getAttribute('aria-labelledby').split(' ').map(id => {const x = document.getElementById(id); return x.value ?? x.textContent;}).join(' ')"
            assert page.locator('#decision-grid .criterion-weight').nth(1).evaluate(weight_name) == '维护成本 权重'
            assert page.locator('#decision-criterion-0').get_attribute('class') == 'criterion-name'  # not user-text, so its aria-label is translated
            page.locator('#decision-run').click()
            page.locator('#decision-ranks > li').first.wait_for(timeout=30000)
            # Ranked cards with weighted bars: B leads on 3×40% + 5×60% = 4.2, A follows on 2.8.
            assert page.locator('#decision-ranks .dm-name').all_inner_texts() == ['方案 B', '方案 A']
            assert page.locator('#decision-ranks .dm-rank').all_inner_texts() == ['1', '2'] and page.locator('#decision-ranks .is-lead').count() == 1
            assert page.locator('#decision-ranks .dm-score').first.inner_text().replace(' ', '') == '4.2/5'
            assert page.locator('#decision-ranks > li').nth(1).locator('.dm-gap').inner_text() == '比首位低 1.4'
            assert page.locator('#decision-ranks > li').first.locator('.dm-track .dm-seg').count() == 2
            assert page.locator('.dm-legend li').all_inner_texts()[0].replace('\n', '').startswith('交付速度40%')
            # How firm the lead is: exact weights at which another option takes over, and the leader without each criterion.
            rows = page.locator('#decision-sensitivity tbody tr')
            assert rows.count() == 2
            assert rows.nth(0).locator('.dm-edge').all_inner_texts() == ['> 9 (75%) → 方案 A'] and '不变' in rows.nth(0).inner_text()
            assert rows.nth(1).locator('.dm-edge').all_inner_texts() == ['< 0.67 (25%) → 方案 A'] and '首位改变' in rows.nth(1).inner_text()
            # Once compared, an edit recomputes on its own, redrawing only the result, so the field keeps its focus.
            score = page.locator('#decision-grid .option-rating').nth(1)
            score.fill('5')
            page.wait_for_function("() => document.querySelector('#decision-status').textContent.includes('方案 A')", timeout=30000)
            assert page.evaluate("document.activeElement === document.querySelectorAll('#decision-grid .option-rating')[1]")
            assert page.locator('#decision-ranks .dm-score').first.inner_text().replace(' ', '') == '4.6/5'
            # Leaving within the recompute delay keeps the grid as typed, and the result follows it.
            score.fill('4')
            page.locator('[data-tab="officers"]').click()
            page.locator('[data-tab="decision"]').click()
            assert page.locator('.criterion-edit').count() == 2 and page.locator('.option-edit').count() == 2
            assert page.locator('#decision-question').input_value() != '' and score.input_value() == '4'
            page.wait_for_function("() => !document.querySelector('#decision-output').classList.contains('is-stale') && document.querySelector('#decision-status').textContent.includes('方案 B')", timeout=30000)
            score.fill('5')
            page.wait_for_function("() => document.querySelector('#decision-status').textContent.includes('方案 A')", timeout=30000)
            # A field left blank keeps the last result, faded and labelled as out of date.
            weight = page.locator('#decision-grid .criterion-weight').first
            weight.fill('')
            page.wait_for_function("() => document.querySelector('#decision-output').classList.contains('is-stale')", timeout=30000)
            assert '比较失败' in page.locator('#decision-msg').inner_text() and page.locator('.dm-stale-note').is_visible()
            # Another tool and back: the result is still marked out of date, with the reason.
            page.locator('[data-tab="officers"]').click()
            page.locator('[data-tab="decision"]').click()
            assert page.locator('#decision-output').evaluate("el => el.classList.contains('is-stale')") and '比较失败' in page.locator('#decision-msg').inner_text()
            assert weight.input_value() == '' and score.input_value() == '5'
            weight.fill('2')
            score.fill('2')
            page.wait_for_function("() => !document.querySelector('#decision-output').classList.contains('is-stale') && document.querySelector('#decision-status').textContent.includes('方案 B')", timeout=30000)
            assert page.locator('#decision-msg').inner_text() == ''
            page.screenshot(path=str(screenshot_dir / '16-decision-matrix-desktop.png'), full_page=True)

            page.locator('[data-tab="quality"]').click()
            assert page.locator('#quality-minutes').input_value() == '15'
            # The opening result (±15) lands first; the one for ±10 replaces it.
            page.wait_for_function("() => qualityResult", timeout=30000)
            page.evaluate("window.openingQuality = qualityResult")
            page.locator('#quality-minutes').fill('10')
            page.locator('#quality-run').click()
            page.wait_for_function("() => qualityResult && qualityResult !== window.openingQuality", timeout=30000)
            assert page.locator('#quality-minutes').input_value() == '10'
            assert '未发现当前规则已知边界问题' in page.locator('#result').inner_text()
            # Distances read as days, hours and minutes, measured from the named jie on either side.
            assert page.locator('#quality-status.is-clear').count() == 1
            term = page.locator('#quality-term').inner_text()
            assert '交节已过' in term and '距交节还有' in term and ' 天' in term, term
            assert page.locator('#quality-hour .qa-gap-value').inner_text() and page.locator('.qa-gap.is-near').count() == 0
            page.screenshot(path=str(screenshot_dir / '11-quality-desktop.png'), full_page=True)

            # Auditable deep cross-method review: real Chromium controls invoking FastAPI.
            page.locator('[data-tab="deep"]').click()
            page.locator('#deep-palace').select_option('官禄宫')
            page.locator('#deep-year').fill('2026')
            page.locator('#deep-question').fill('请只展示可计算的宫位关联')
            page.locator('#deep-run').click()
            page.get_by_text('关注 官禄宫', exact=False).first.wait_for(timeout=30000)
            page.get_by_text('内部一致性核查', exact=False).first.wait_for(timeout=30000)
            assert '三方四正' in page.locator('#result').inner_text()
            assert page.locator('#deep-download').is_visible()
            # Findings come grouped as cards, the evidence tables drawn as such, the exact fields one click away.
            groups = page.locator('.ev-group').count()
            assert groups >= 4 and page.locator('.ev-toc-link').count() == groups
            assert page.locator('.ev-card').count() == int(page.get_by_text('组可追溯观察').first.inner_text().split()[0])
            assert page.locator('#deep-bazi-pillars .ev-pillar').count() == 4 and page.locator('#deep-bazi-hidden tr').count() == 4
            assert page.locator('#deep-ziwei-four [class*="reading-hua-"]').count() == 8  # four natal and four from the focus palace stem
            # A focus-stem transformation landing back in the focus palace says 自化, as the server's text does.
            self_count = page.evaluate("() => deepResult.findings.flatMap(f => f.evidence).filter(x => /palace_flying_transformations$/.test(x.path)).flatMap(x => x.value).filter(t => t.self_transform).length")
            assert page.locator('#deep-ziwei-four .ev-self').count() == self_count
            assert page.locator('#deep-bazi-pillars .ev-basis').inner_text() == '计算时制 钟表时间'
            assert not page.locator('#deep-bazi-pillars .ev-fields').is_visible()
            page.locator('#deep-bazi-pillars summary').click()
            assert page.locator('#deep-bazi-pillars .ev-fields code', has_text='bazi.pillars').first.is_visible()
            # Printing opens the other collapsed field sections and closes them again afterwards.
            page.evaluate("() => dispatchEvent(new Event('beforeprint'))")
            assert page.locator('details.ev-more:not([open])').count() == 0
            page.evaluate("() => dispatchEvent(new Event('afterprint'))")
            assert page.locator('details.ev-more[open]').count() == 1
            # The group links move keyboard focus to the group they name.
            page.locator('.ev-toc-link').nth(1).click()
            assert page.evaluate("() => document.activeElement.id") == 'deep-group-1'
            assert page.locator('#deep-checks li.is-pass').count() == page.locator('#deep-checks li').count() == 4
            assert page.locator('a[href="https://docs.iztro.com/en_US/posts/palace"]').count() > 0
            page.screenshot(path=str(screenshot_dir / '24-deep-evidence-desktop.png'), full_page=True)
            page.locator('#deep-year').fill('2100')
            page.locator('#deep-run').click()
            assert '1901–2099' in page.locator('#result').inner_text()
            page.locator('#deep-year').fill('2026')

            page.locator('[data-tab="report"]').click()
            assert page.locator('#report-year').input_value() == ''
            assert page.locator('#report-deep').is_checked()
            # Each optional part is a card that says what it needs: without a longitude there is no solar-time audit.
            assert page.locator('#report-audit').get_attribute('aria-disabled') == 'true' and '没有经度' in page.locator('#report-module-time').inner_text()
            # The box stays focusable, so its reason is read with it, but a click does not tick it.
            assert 'report-module-time-need' in page.locator('#report-audit').get_attribute('aria-describedby')
            page.locator('#report-audit').click(force=True)
            assert not page.locator('#report-audit').is_checked()
            assert page.locator('#report-plan').inner_text() == '将运行 4 个计算步骤'
            page.locator('#report-dayun').check()
            assert page.locator('#report-plan').inner_text() == '将运行 5 个计算步骤'
            page.locator('#report-dayun').uncheck()
            page.locator('#report-run').click()
            page.get_by_text('可追溯综合报告', exact=False).first.wait_for(timeout=30000)
            page.locator('#report-download').wait_for(timeout=30000)
            assert '出生数据与排盘边界审计' in page.locator('#result').inner_text()
            assert '规则证据与跨体系差异复核' in page.locator('#result').inner_text()
            assert page.locator('#report-year').input_value() == ''
            # The report as a document: the pillars, the steps run, a contents list that moves the keyboard to its section.
            assert page.locator('.rp-pillar').count() == 4 and page.locator('#report-trace li').count() == 4
            assert page.locator('#report-toc a').count() == page.locator('.rp-section').count() == 6
            assert page.evaluate("document.activeElement.id") == 'report-doc'
            page.locator('#report-toc a').nth(4).click()
            assert page.evaluate("document.activeElement.id") == 'report-sec-4'
            assert page.evaluate("reportMarkdownSection(reportResult.markdown, '规则证据与跨体系差异复核').startsWith('## 规则证据与跨体系差异复核')")
            # The terms the report uses close it: what each is, how XuanShu computes it and the rule document, from the
            # contents list too, and copied as their own section.
            terms = page.evaluate('reportResult.glossary.length')
            assert terms >= 8 and page.locator('#report-terms .rp-term').count() == terms
            assert page.locator('#report-terms .rp-term-how').count() == terms and page.locator('#report-terms .rp-term-doc').count() == terms
            assert page.locator('#report-terms dt b', has_text='日主').count() == 1
            # The report names 木三局-style bureaus and （庙）-style brightness, so both terms are explained.
            assert {'五行局', '亮度'} <= set(page.evaluate('reportResult.glossary.map(g => g.term)'))
            # English headwords come from the glossary's own column, with the Chinese term beside them.
            page.locator('#ui-language').select_option('en')
            page.wait_for_function("document.documentElement.lang === 'en' && !!document.querySelector('#report-terms .rp-term-zh')", timeout=30000)
            assert page.locator('#report-terms dt b', has_text='Day Master').count() == 1 and page.locator('#report-terms dt b', has_text='from age').count() == 0
            page.locator('#ui-language').select_option('zh-CN')
            page.wait_for_function("document.documentElement.lang === 'zh-CN' && !document.querySelector('#report-terms .rp-term-zh')", timeout=30000)
            page.locator('#report-toc a').last.click()
            assert page.evaluate("document.activeElement.id") == 'report-glossary'
            assert page.evaluate("reportMarkdownSection(reportResult.markdown, '术语解释').startsWith('## 术语解释')")
            assert page.locator('#report-copy-glossary').count() == 1
            page.screenshot(path=str(screenshot_dir / '10-report.png'), full_page=True)
            # The contents list stays in view beside the report while it is read.
            page.evaluate("document.querySelector('#report-sec-2').scrollIntoView()")
            toc_top = page.evaluate("document.querySelector('#report-toc').getBoundingClientRect().top")
            # The header stays at the top of the window and the contents list sticks just below it, not under it.
            header_bottom = page.evaluate("document.querySelector('.header').getBoundingClientRect().bottom")
            assert page.evaluate("document.querySelector('.header').getBoundingClientRect().top") == 0
            assert header_bottom <= toc_top <= header_bottom + 20, (toc_top, header_bottom)
            # With a chart cast the introduction folds to one line; the cross-check link and today's chip stay.
            assert page.locator('.hero p').is_hidden() and page.locator('.hero .eyebrow').is_hidden()
            assert page.locator('#crosscheck-open').is_visible() and page.locator('#today-chip').is_visible()
            # Opening a tool restarts the result area's one-time fade-in.
            assert 'is-entering' in (page.locator('#result').get_attribute('class') or '')
            # On a wide screen the birth form folds to a one-line summary when asked, and the workspace takes the full width.
            narrow = page.evaluate("document.querySelector('#workspace').getBoundingClientRect().width")
            page.locator('#birth-summary-toggle').click()
            assert page.locator('#input-panel.collapsed').count() == 1 and page.locator('#birth-summary-text').is_visible()
            assert page.evaluate("document.querySelector('#workspace').getBoundingClientRect().width") > narrow + 200
            # The green dot says the chart on screen comes from this data; editing the data takes it away.
            dot = "getComputedStyle(document.querySelector('#birth-summary-text'), '::before').content"
            assert page.locator('#input-panel.is-current').count() == 1 and page.evaluate(dot) != 'none'
            saved_when = page.locator('#birth_datetime').input_value()
            page.evaluate("() => {const f = document.querySelector('#birth_datetime'); f.value = '1990-01-01T10:00'; f.dispatchEvent(new Event('input', {bubbles: true}));}")
            assert page.locator('#input-panel.is-current').count() == 0 and page.evaluate(dot) == 'none'
            assert page.locator('#birth-summary-text').inner_text().startswith('1990-01-01 10:00 · ')
            page.evaluate("(v) => {const f = document.querySelector('#birth_datetime'); f.value = v; f.dispatchEvent(new Event('input', {bubbles: true}));}", saved_when)
            assert page.locator('#input-panel.is-current').count() == 1
            page.locator('#birth-summary-toggle').click()
            assert page.locator('#input-panel.collapsed').count() == 0 and page.evaluate("document.activeElement.id") == 'birth_datetime'
            assert page.evaluate("document.querySelector('#workspace').getBoundingClientRect().width") == narrow
            # Each copy button is named by its section, and sits beside the heading rather than inside it.
            first_title = page.evaluate("reportResult.sections[0].title")
            assert page.get_by_role('button', name=first_title).count() == 1
            assert page.get_by_role('heading', name=first_title).locator('button').count() == 0
            # A chart cast without a birth hour: the report marks the hour pillar and both palaces as unknown, and the
            # copies say first that the report stands on the 12:00 placeholder.
            page.locator('#hour_unknown').check()
            page.locator('#run-btn').click()
            page.wait_for_function("() => currentHourUnknown && !reportResult", timeout=30000)
            page.locator('[data-tab="report"]').click()
            page.locator('#report-run').click()
            page.locator('#report-hour-note').wait_for(timeout=30000)
            assert page.locator('.rp-pillar').nth(3).locator('b').text_content() == '??'
            assert page.evaluate("reportMarkdown(reportResult).startsWith('> 命盘时辰不详')")
            page.locator('#hour_unknown').uncheck()
            page.locator('[data-tab="integration"]').click()
            # The counts come from the running server's capabilities.
            tools = page.evaluate("fetch('/api/capabilities').then(r => r.json()).then(d => d.counts.mcp_tools)")
            page.wait_for_function(f"() => document.querySelector('#integration-counts').textContent.includes('{tools} Tools')", timeout=30000)
            # The page checks the server itself over MCP: both protocol generations, every list, all passing.
            page.wait_for_selector('#integration-summary.is-ok', timeout=30000)
            assert page.locator('#integration-steps > li').count() == 6 and page.locator('#integration-steps > li.is-ok').count() == 6
            assert [page.locator('#integration-steps .ag-method').nth(i).inner_text() for i in range(2)] == ['server/discover', 'initialize']
            assert page.locator('#integration-consistency.ag-same').count() == 1
            assert page.locator('.ag-nav-link').count() == 6
            # The catalogue lists every tool once, grouped; search and the purpose chips narrow it in place.
            assert page.locator('#integration-catalog .ag-tool').count() == tools
            assert '只读' in page.locator('#integration-hints').inner_text()
            page.locator('#integration-search').fill('qimen_hour')
            page.wait_for_function("() => [...document.querySelectorAll('#integration-catalog .ag-tool')].filter(c => !c.hidden).length === 1", timeout=5000)
            assert page.locator('#integration-tool-qimen_hour_chart').is_visible()
            assert page.locator('#integration-tool-count').inner_text().startswith('显示 1 / ')
            page.locator('#integration-search').fill('')
            page.locator('#integration-group-calendar').click()
            page.wait_for_function("() => [...document.querySelectorAll('#integration-catalog .ag-tool')].filter(c => !c.hidden).length === 7", timeout=5000)
            assert page.locator('#integration-group-sec-chart').is_hidden()
            page.locator('#integration-group-all').click()
            # A tool page link opens the workbench page; the example and trial run use the fixed demonstration birth.
            assert page.locator('#integration-open-bazi_dayun').inner_text().endswith('大运干支')
            page.locator('#integration-example-bazi_chart summary').click()
            assert '"birth_datetime": "2000-08-16T04:00"' in page.locator('#integration-example-bazi_chart .ag-request').inner_text()
            page.locator('#integration-try-bazi_chart').focus()
            page.keyboard.press('Enter')
            page.wait_for_selector('#integration-run-bazi_chart .ag-run-head.is-ok', timeout=30000)
            assert '"pillars"' in page.locator('#integration-run-bazi_chart .ag-output').inner_text()
            # The button kept the focus through the call, and the result stays inside its card.
            assert page.evaluate("document.activeElement.id") == 'integration-try-bazi_chart'
            assert page.evaluate('''() => {const card = document.querySelector('#integration-tool-bazi_chart').getBoundingClientRect();
              return [...document.querySelectorAll('#integration-tool-bazi_chart pre')].every(p => p.getBoundingClientRect().right <= card.right + 1);}''')
            # A long description opened in full stays open through a recheck, which keeps the last results on screen.
            more = page.locator('#integration-catalog .ag-more').first
            more_id = more.get_attribute('id')
            more.click()
            page.locator('#integration-recheck').focus()
            page.keyboard.press('Enter')
            assert page.locator('#integration-catalog .ag-tool').count() == tools  # still drawn while the check runs
            page.wait_for_function("() => !agentPending", timeout=30000)
            assert page.evaluate("document.activeElement.id") == 'integration-recheck'
            assert page.locator('#' + more_id).get_attribute('aria-expanded') == 'true'
            assert page.locator('#integration-example-bazi_chart').get_attribute('open') is not None
            # Every example call is valid for its tool (the optional professional provider may be missing).
            failures = page.evaluate('''async () => {
              const bad = [];
              for (const tool of agentCatalog.tools) {
                try {
                  const out = await mcpRequest('tools/call', agCall(tool).params);
                  if (out.result.isError && tool.name !== 'ziwei_professional_chart') bad.push(tool.name + ': ' + out.result.content[0].text.slice(0, 120));
                } catch (e) {bad.push(tool.name + ': ' + e.message);}
              }
              return bad;
            }''')
            assert failures == [], failures
            # Client setup follows the typed project folder; nothing personal goes into it.
            page.locator('#integration-client-codex').click()
            page.locator('#integration-os-posix').click()
            page.locator('#integration-path').fill('/opt/xuan shu/')
            codex = page.locator('#integration-snippet').inner_text()
            assert codex.startswith('[mcp_servers.xuanshu]') and 'command = "/opt/xuan shu/.venv/bin/python"' in codex
            page.locator('#integration-client-claude-code').click()
            assert page.locator('#integration-snippet').inner_text() == "claude mcp add --transport stdio --env PYTHONPATH='/opt/xuan shu' xuanshu -- '/opt/xuan shu/.venv/bin/python' -m app.stdio"
            page.locator('#integration-client-http').click()
            assert page.locator('#integration-snippet-1').inner_text().startswith('curl -s ') and 'tools/list' in page.locator('#integration-snippet-1').inner_text()
            page.locator('#integration-client-claude-desktop').click()
            page.locator('#integration-path').fill('')
            assert '"args": [' in page.locator('#integration-snippet').inner_text() and page.locator('#integration-copy').is_visible()
            # A rule resource is read on demand through resources/read.
            page.locator('#integration-doc-evidence summary').click()
            page.wait_for_selector('#integration-doc-evidence .ag-doc-text', timeout=30000)
            assert '深度证据' in page.locator('#integration-doc-evidence .ag-doc-text').inner_text()
            # The page follows the interface language and keeps what was open.
            page.locator('#ui-language').select_option('en')
            page.wait_for_function("() => document.querySelector('#integration-summary')?.textContent.includes('Connected to')", timeout=10000)
            assert page.locator('#integration-doc-evidence').get_attribute('open') is not None
            page.locator('#ui-language').select_option('zh-CN')
            page.wait_for_function("() => document.querySelector('#integration-summary')?.textContent.includes('已连上')", timeout=10000)
            page.screenshot(path=str(screenshot_dir / '07-integration.png'), full_page=True)

            page.locator('#birth_datetime').fill('2057-09-28T12:00')
            page.locator('#run-btn').click()
            page.wait_for_function("() => document.querySelector('#result-subtitle').textContent.startsWith('2057-09-28')", timeout=30000)
            page.locator('[data-tab="quality"]').click()
            page.locator('#quality-run').click()
            page.get_by_text('published_new_moon_uncertainty', exact=False).first.wait_for(timeout=30000)
            assert page.locator('#quality-status.is-review').count() == 1 and page.locator('.qa-flag.is-review .qa-code', has_text='published_new_moon_uncertainty').count() == 1
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
            # On a phone the folded introduction keeps only today's chip; the heading is left for screen readers.
            assert page.evaluate("document.querySelector('.hero h1').getBoundingClientRect().width") <= 1
            assert page.locator('#today-chip').is_visible()
            # No page is wider than a phone screen, and no field sticks out of its label (a year field used to cover
            # the next-year button).
            for tab in ('report', 'bazi', 'ziwei', 'annual', 'dayun', 'qimen', 'officers'):
                page.locator(f'[data-tab="{tab}"]').click()
                page.wait_for_timeout(300)
                assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), tab
                assert page.evaluate('''() => [...document.querySelectorAll('#result .inline-control > label > :is(input, select)')]
                  .every(f => f.getBoundingClientRect().right <= f.parentElement.getBoundingClientRect().right + 1)'''), tab
            # The nine-palace cells keep only the stem glyphs on a phone; a line above the board names them.
            page.locator('[data-tab="qimen"]').click()
            assert page.locator('.qimen-legend').is_visible()
            assert page.evaluate("[...document.querySelectorAll('.qimen-cell')].every(c => c.scrollWidth <= c.clientWidth + 1)")
            # On a phone the long English term names (Awakening of Insects, Spring Equinox) take a third line in their
            # month-calendar cell rather than losing their end.
            page.locator('[data-tab="calendar"]').click()
            page.evaluate("() => {calendarMonth = {year: 2024, month: 3}; calendarSelected = '2024-03-05'; render();}")
            page.locator('#calendar-day-2024-03-05').wait_for(timeout=30000)
            page.locator('#ui-language').select_option('en')
            page.wait_for_function("() => document.getElementById('calendar-day-2024-03-05').textContent.includes('Awakening')", timeout=10000)
            cut = page.evaluate("() => [...document.querySelectorAll('.cal-day .cal-lunar, .cal-day .cal-also')].filter(el => el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1).map(el => el.textContent)")
            assert cut == [], cut
            page.locator('#ui-language').select_option('zh-CN')
            page.wait_for_function("() => document.getElementById('calendar-day-2024-03-05').textContent.includes('惊蛰')", timeout=10000)
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
            # Deleting a profile asks in the page's own dialog, in the interface language, with the safe answer focused;
            # Escape keeps the profile and gives the focus back to the button.
            kept = page.locator('#profiles option').count()
            page.locator('#profiles').select_option(label='既有档案')
            page.locator('#remove-profile').click()
            page.locator('#xs-confirm-no').wait_for(timeout=5000)
            assert page.evaluate("document.activeElement.id") == 'xs-confirm-no'
            assert not re.search('[\u4e00-\u9fff]', page.locator('#xs-confirm-text').inner_text()), page.locator('#xs-confirm-text').inner_text()
            page.keyboard.press('Escape')
            page.locator('#xs-confirm-no').wait_for(state='detached', timeout=5000)
            assert page.locator('#profiles option').count() == kept and page.evaluate("document.activeElement.id") == 'remove-profile'
            # The encrypted backup's question and result translate piece by piece into whole English sentences.
            pieces = page.evaluate("""() => [
              ['备份里有 ', '1', ' 份档案。', '用这些档案及其记忆、人生事件和对话替换当前浏览器里的全部内容吗？'],
              ['加密备份已恢复：', '1', ' 份档案', '、', '2', ' 条记忆', '、', '0', ' 件人生事件', '、', '1', ' 段已保存的对话', '；', '原有内容已被替换。'],
            ].map(parts => parts.map(translateText).join(''))""")
            assert pieces == ['The backup holds 1 profile(s). Replace everything in this browser with these profiles and their memory, life events and conversations?',
                              'Encrypted backup restored: 1 profile(s), 2 memory note(s), 0 life event(s), 1 saved conversation(s); the previous contents were replaced.'], pieces
            # After a restore the open conversation starts again from what was restored.
            assert page.evaluate("() => {chatMessages = [{role: 'user', content: 'before the restore'}]; restartChat(); return chatMessages.length;}") == 0
            # The memory panel starts each change from what is stored at the click: what a restore wrote while the panel
            # was open is kept, and a row drawn before it removes nothing that came from the backup.
            kept_memory = page.evaluate("""() => {
              const id = document.getElementById('profiles').value, raw = localStorage.getItem(chatMemoryKey);
              if (!id) return null;
              const host = document.createElement('div'); document.body.append(host);
              saveProfileMemory(id, {memory: ['旧的记忆'], life_events: [{date: '2018-09-01', title: '入职', note: ''}], keep_history: false});
              renderMemoryPanel(host);
              saveProfileMemory(id, {memory: ['恢复的记忆'], life_events: [{date: '2020-01-01', title: '搬家', note: ''}], keep_history: false});
              host.querySelector('#chat-memory-input').value = '新的记忆';
              host.querySelector('#chat-memory-add').click();
              [...host.querySelectorAll('.chat-memory-row')].find(row => row.textContent.includes('入职')).querySelector('button').click();
              const after = profileMemory(id);
              host.remove();
              if (raw === null) localStorage.removeItem(chatMemoryKey); else localStorage.setItem(chatMemoryKey, raw);
              return after;
            }""")
            assert kept_memory['memory'] == ['恢复的记忆', '新的记忆'] and [e['title'] for e in kept_memory['life_events']] == ['搬家'], kept_memory
            page.screenshot(path=str(screenshot_dir / '30-results-english.png'), full_page=True)
            page.locator('#ui-language').select_option('ja')
            grid = page.locator('#ziwei-pair-grid').inner_text()
            assert '命宮' in grid and '命宫' not in grid, grid[:300]
            # No hint in a text field is cut off, in Japanese or English, on a desktop or a phone.
            for lang in ('ja', 'en'):
                page.locator('#ui-language').select_option(lang)
                for width, height in ((1440, 920), (390, 844)):
                    page.set_viewport_size({'width': width, 'height': height})
                    clipped = page.evaluate(CLIPPED_HINTS)
                    assert clipped == [], (lang, width, clipped)
            page.set_viewport_size({'width': 1440, 'height': 920})
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
            assert first.get_attribute('data-tip').startswith('Brightness: ' + english[first.get_attribute('data-level')])
            panel = page.locator('.palace-panel').inner_text()
            selected_levels = page.evaluate("() => {const p = findPalace(current.ziwei, selectedPalace); return p.main_stars.map(s => p.star_brightness[s]);}")
            assert all(f'({english[x]})' in panel for x in selected_levels) and not re.search('（[庙旺得利平不陷]）', panel), panel[:300]
            assert '、' not in panel and '；' not in panel, panel[:300]
            page.screenshot(path=str(screenshot_dir / '41-ziwei-brightness-english.png'), full_page=True)
            # On a touch screen a tap on a star's mark selects the palace and also opens the mark's hint (the palace
            # redraws, so the hint is found again on the redrawn mark).
            mark_tip = page.evaluate("() => document.querySelector('#palace-3 .bright').getAttribute('data-tip')")
            page.evaluate("() => {const m = document.querySelector('#palace-3 .bright'); m.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true, pointerType: 'touch'})); m.click();}")
            page.wait_for_function("(text) => {const t = document.getElementById('xs-tip'); return t && !t.hidden && t.textContent === text;}", arg=mark_tip, timeout=3000)
            assert page.locator('#palace-3').get_attribute('aria-pressed') == 'true'
            page.mouse.click(2, 2)
            page.wait_for_function("() => document.getElementById('xs-tip').hidden", timeout=3000)
            # A board drawn while English is active keeps its Chinese source text: the tooltips follow the next switch.
            page.locator('.palace-btn').nth(1).click()
            page.wait_for_function("() => document.querySelector('#ziwei-board .bright').dataset.tip.startsWith('Brightness: ')", timeout=10000)
            page.locator('#ui-language').select_option('ja')
            page.wait_for_function("() => document.querySelector('#ziwei-board .bright').dataset.tip.startsWith('明るさ：')", timeout=10000)
            page.locator('#ui-language').select_option('zh-CN')
            page.wait_for_function("() => document.querySelector('#ziwei-board .bright').dataset.tip.startsWith('亮度：')", timeout=10000)
            page.locator('#ui-language').select_option('ja')
            page.wait_for_function(f"() => {level} === {json.dumps(' '.join(m[0] + (chr(34) + '廟' + chr(34) if m[0] == '庙' else chr(34) + '陥' + chr(34) if m[0] == '陷' else m[1:]) for m in marks))}", timeout=10000)
            page.locator('#ui-language').select_option('zh-CN')
            page.wait_for_function(f"() => {level} === {json.dumps(' '.join(marks))}", timeout=10000)
            # Windows contrast themes repaint every colour: a checked box and the selected tool keep a system-colour mark.
            page.emulate_media(forced_colors='active')
            marks = page.evaluate('''() => {
              const box = document.getElementById('late_zi_day_rollover'), was = box.checked; box.checked = true;
              const style = getComputedStyle(box), tab = getComputedStyle(document.querySelector('.tab.active'));
              const out = [style.backgroundColor, getComputedStyle(document.body).backgroundColor, tab.outlineStyle,
                           getComputedStyle(document.getElementById('run-btn')).borderTopStyle];
              box.checked = was; return out;}''')
            assert marks[0] != marks[1] and marks[2] == 'solid' and marks[3] == 'solid', marks
            page.emulate_media(forced_colors='none')
            # Every IANA zone is listed (common ones first, then by region with the UTC offset); a saved zone the list
            # lacks is added back instead of leaving the select blank.
            assert page.locator('#timezone optgroup').count() >= 5
            assert page.locator('#timezone option[value="Asia/Singapore"]').count() == 1
            assert 'UTC+8' in page.locator('#timezone option[value="Asia/Singapore"]').inner_text()
            # Chromium's old CLDR names are listed under the current IANA name.
            assert page.locator('#timezone option[value="Asia/Kolkata"]').count() == 1
            assert page.locator('#timezone option[value="Asia/Calcutta"]').count() == 0
            page.evaluate("() => setInput({birth_datetime: '1990-05-01T08:00', timezone: 'US/Pacific'})")
            assert page.locator('#timezone').input_value() == 'US/Pacific'
            # 1988-09-11 01:30 happened twice in China (daylight saving ended that night): the page asks which one,
            # then casts with the offset chosen.
            page.evaluate("() => setInput({birth_datetime: '1988-09-11T01:30', timezone: 'Asia/Shanghai', gender: 'female'})")
            page.locator('#run-btn').click()
            page.locator('#dst-choice-1').wait_for(timeout=10000)
            assert page.evaluate("document.activeElement.id") == 'dst-choice-0'
            assert '+09:00' in page.locator('#dst-choice-0').inner_text() and '+08:00' in page.locator('#dst-choice-1').inner_text()
            page.screenshot(path=str(screenshot_dir / '42-dst-choice.png'))
            page.locator('#dst-choice-1').click()
            page.wait_for_function("() => currentInput && currentInput.birth_datetime === '1988-09-11T01:30+08:00'", timeout=30000)
            assert page.locator('#dst-choice').is_hidden() and page.locator('#error').is_hidden()
            # A different clock time asks again; the chosen offset belonged to 01:30 only.
            page.locator('#birth_datetime').fill('1988-09-11T01:45')
            assert page.evaluate('readInput().birth_datetime') == '1988-09-11T01:45'
            # A skipped clock time: Samoa skipped all of 30 December 2011, so the equivalent clock reading is on
            # another day and is shown with its date. The offsets come from the server's refusal, not the browser.
            page.evaluate("() => setInput({birth_datetime: '2011-12-30T12:00', timezone: 'Pacific/Apia', gender: 'female'})")
            page.locator('#run-btn').click()
            page.locator('#dst-choice-1').wait_for(timeout=10000)
            assert '2011-12-31 12:00' in page.locator('#dst-choice-0').inner_text(), page.locator('#dst-choice').inner_text()
            assert '2011-12-29 12:00' in page.locator('#dst-choice-1').inner_text() and page.locator('#error').is_hidden()
            # Any change of the time or zone takes the question away, also a value the page sets itself (时辰不详, a lunar date).
            page.evaluate("() => {document.getElementById('birth_datetime').value = '2011-12-31T12:00'; updateStaleBirthNotice();}")
            assert page.locator('#dst-choice').is_hidden()

            # The API reference at /docs is the project's own page (Swagger's CDN scripts are blocked by the CSP):
            # groups, field tables, and a "try it" request that really runs, on a phone-width screen.
            api_html = (ROOT / 'static/api.html').read_text(encoding='utf-8')
            api_html = re.sub(r'<script\s+src="/static/.*?"(\s+defer)?></script>', '', api_html)
            api_html = re.sub(r'<link\s+rel="stylesheet"\s+href="/static/style.css"\s*/>', '', api_html)
            docs = browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=1)
            docs.on('pageerror', lambda error: errors.append('docs: ' + str(error)))
            docs.set_content(api_html)
            docs.add_style_tag(content=css)
            docs.expose_function('apiBridge', call_api)
            docs.evaluate('''() => {
              const map={};
              Object.defineProperty(window,'localStorage',{value:{getItem:k=>map[k]??null,setItem:(k,v)=>{map[k]=String(v)},removeItem:k=>{delete map[k]}},configurable:true});
              window.fetch=async(path,opt)=>{
                const data=opt && opt.body ? JSON.parse(opt.body) : null;
                const result=await window.apiBridge(path,data,opt && opt.headers ? opt.headers : null);
                return {ok:result.ok,status:result.status,json:async()=>result.data,text:async()=>result.text,
                        headers:{get:name=>name.toLowerCase()==='content-type'?result.type:null}};
              };
            }''')
            for script in (theme_js, i18n_extra_js, api_js, tips_js, i18n_js):
                docs.add_script_tag(content=script)
            docs.locator('.api-op').first.wait_for(timeout=10000)
            # The theme button's hint shows for keyboard focus too, in the page's own style.
            docs.focus('#ui-language'); docs.keyboard.press('Tab')
            docs.wait_for_function("() => {const t = document.getElementById('xs-tip'); return document.activeElement.id === 'theme-toggle' && t && !t.hidden && t.textContent.startsWith('配色：');}", timeout=3000)
            docs.keyboard.press('Escape')
            assert docs.locator('.api-group').count() == 8 and docs.locator('#api-groups a').count() == 8
            assert docs.locator('#api-groups a').first.inner_text().startswith('命盘与报告')
            op = docs.locator('#op-post-api-time-audit')
            op.locator('summary').click()
            op.locator('.api-fields').first.wait_for(timeout=10000)  # built when first opened
            assert '太阳时审计' in op.locator('summary').inner_text()
            assert json.loads(op.locator('textarea').input_value())['birth']['longitude'] == 104.07
            op.locator('.api-send').click()
            op.locator('.api-status .api-code').wait_for(timeout=30000)
            assert op.locator('.api-status .api-code').inner_text() == '200', op.locator('.api-status').inner_text()
            assert '"system": "time-basis-audit"' in op.locator('.api-out').inner_text()
            # A broken body is caught in the page, with the focus put back on it.
            op.locator('textarea').fill('{"birth": ')
            op.locator('.api-send').click()
            assert 'JSON 格式有误' in op.locator('.api-status').inner_text() and op.locator('.api-out').is_hidden()
            assert docs.evaluate('document.activeElement.tagName') == 'TEXTAREA'
            # Path parameters are filled in and sent in the URL.
            lunar = docs.locator('#op-get-api-lunar-day')
            lunar.locator('summary').click()
            lunar.locator('input').fill('2026-02-17')
            lunar.locator('.api-send').click()
            lunar.locator('.api-status .api-code').wait_for(timeout=30000)
            assert '"month": 1' in lunar.locator('.api-out').inner_text() and '"day": 1' in lunar.locator('.api-out').inner_text()
            # A field name finds its endpoint; a type name jumps to the structure and opens it.
            docs.locator('#api-filter').fill('reference_school')
            assert docs.locator('.api-op:not([hidden])').count() == 1 and docs.locator('#api-count').inner_text().startswith('1 / ')
            # Fields nested in the body count too: longitude sits inside birth.
            docs.locator('#api-filter').fill('longitude')
            assert docs.locator('#op-post-api-time-audit').is_visible()
            docs.locator('#api-filter').fill('')
            # A stray % in the address is ignored rather than breaking the page.
            docs.evaluate("() => {location.hash = '100%';}")
            docs.wait_for_timeout(200)
            op.locator('.api-op-body h4 .api-ref').click()
            docs.wait_for_function("() => document.getElementById('schema-TimeAuditRequest').open", timeout=5000)
            assert docs.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth')
            docs.locator('#ui-language').select_option('en')
            docs.wait_for_function("() => document.documentElement.lang === 'en' && document.title === 'API reference · XuanShu'", timeout=10000)
            assert 'Try it' in op.inner_text() and 'Birth-time checks' in docs.locator('#api-groups').inner_text()
            out_name = op.locator('.api-out').get_attribute('aria-labelledby')
            assert docs.locator('#' + out_name).inner_text() == 'Response body'
            # A copy button gets its own label back after "Copied", still translatable into the next language.
            curl = op.locator('.api-actions .api-ghost').first
            curl.click()
            docs.wait_for_function("(b) => b.textContent === 'Copy curl'", arg=curl.element_handle(), timeout=10000)
            docs.locator('#ui-language').select_option('ja')
            docs.wait_for_function("(b) => b.textContent !== 'Copy curl' && b.textContent.includes('curl')", arg=curl.element_handle(), timeout=10000)
            docs.locator('#ui-language').select_option('en')
            docs.wait_for_function("() => document.documentElement.lang === 'en'", timeout=10000)
            assert docs.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth')
            docs.screenshot(path=str(screenshot_dir / '43-api-docs-mobile-english.png'), full_page=True)
            docs.close()
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
