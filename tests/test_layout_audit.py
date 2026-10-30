"""Layout fixes from the interface audit: things that overlapped, were cut off or fell back to the wrong font."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'static/style.css').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')
HTML = (ROOT / 'static/index.html').read_text(encoding='utf-8')


def test_sidebar_button_stays_on_the_panel_edge():
    assert '<div class="run-bar">' in HTML
    assert '@media(min-width:861px){.run-bar{position:sticky;bottom:-22px;' in CSS


def test_day_pillar_badge_and_english_headings():
    # The badge sits on the pillar's top edge instead of over its heading; English headings are not letter-spaced.
    assert re.search(r'\.pillar-badge\{position:absolute;top:0;left:50%;transform:translate\(-50%,-50%\)', CSS)
    assert ':lang(en) .pillar-head{letter-spacing:.02em}' in CSS
    # A narrow pillar puts the void mark under its branch.
    assert '.pillar{container:pillar / inline-size}' in CSS and '@container pillar (max-width:240px){:lang(en) .void-mark' in CSS


def test_latin_text_uses_the_sans_face():
    assert '--sans:' in CSS and 'font:14px/1.65 var(--sans)' in CSS
    assert '.void-mark{position:absolute;top:2px;right:2px;font-family:var(--sans);' in CSS
    rule = re.search(r':lang\(en\) :is\(([^)]*(?:\([^)]*\)[^)]*)*)\)\{font-family:var\(--sans\)\}', CSS)
    assert rule and all(s in rule.group(1) for s in ('.wuxing-detail h5 b', '.element-bar>b', '.transform-star', '.cal-title', '.share-text'))
    # The share card's Zi Wei rows follow the interface language too.
    assert "const rowFont = document.documentElement.lang.startsWith('en') ? sans : serif;" in APP
    # The five-phase bars share their columns, so a long English name widens the label for every row.
    assert '.element-bar{display:grid;grid-column:1 / -1;grid-template-columns:subgrid;' in CSS


def test_dayun_axis_label_and_current_dot():
    assert "append(axis, 'small', 'dy-before-label', '起运前');" in APP
    assert '.dy-before small' not in CSS and '.dy-before-label{position:absolute;left:0;bottom:3px;' in CSS
    assert ".dy-decade.is-now::after{content:'';position:absolute;top:5px;right:5px;" in CSS
    assert '.dy-band-age::after' not in CSS


def test_officers_today_and_long_term_names():
    assert '.of-day.is-today .of-gz{margin-top:18px}' in CSS
    assert '.of-jie-name{display:block;overflow-wrap:anywhere}' in CSS


def test_install_commands_and_dialog_tables_stay_inside():
    assert '.pf-steps>li{min-width:0}' in CSS and '.pf-command code{flex:1 1 0;min-width:0;' in CSS
    assert ".pf-command code';" in APP
    # The cross-check dialog marks its scrolling tables; the scrollbar gutter takes the backdrop's tone.
    draw = APP[APP.index('async function openCrosscheck()'):]
    assert 'requestAnimationFrame(markScrollAreas);' in draw[:draw.index('if (crosscheckData) draw(')]
    assert 'html:has(dialog:modal){overflow:hidden;scrollbar-gutter:stable;background:color-mix(' in CSS


def test_tab_headings_keep_to_their_first_tool():
    headings = re.findall(r'<span class="tab-group"', HTML)
    leads = re.findall(r'<span class="tab-lead"><span class="tab-group" aria-hidden="true">[^<]+</span><button class="tab', HTML)
    assert headings and len(leads) == len(headings)
    assert "document.querySelectorAll('#workspace-tabs :is(.tab-group, .tab)')" in APP and 'nextElementSibling' not in APP[:3000]


def test_header_search_box_and_footer_docs_link():
    assert '@media(max-width:1240px){.ui-lang>span{display:none}}' in CSS
    assert '@media(max-width:1080px){.brand small{display:none}}' in CSS
    assert '.tool-finder input{flex:1;min-width:min(100%,310px);' in CSS
    # The header's API link is hidden on a phone, so the footer carries one there.
    assert '<a class="footer-link footer-docs" href="/docs" target="_blank" rel="noopener">API 文档 ↗</a>' in HTML
    assert '.footer-docs{display:inline}' in CSS


def test_taiji_emblem_is_drawn_and_centre_text_sits_on_plates():
    assert "'☯'" not in APP and '☯' not in HTML
    assert APP.count('taijiMark(') == 3 and HTML.count('<svg class="taiji"') == 1
    assert '.board-center.see-through>:not(.center-symbol){padding:0 6px;border-radius:4px;background:var(--panel)}' in CSS
