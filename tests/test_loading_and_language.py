"""Loading placeholders and the interface-language gaps the audit found: words that stayed Chinese in English or Japanese."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'static/style.css').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')
I18N = (ROOT / 'static/i18n.js').read_text(encoding='utf-8')
EXTRA = json.loads((ROOT / 'scripts/i18n_extra.json').read_text(encoding='utf-8'))


def test_pages_draw_a_placeholder_while_their_first_result_computes():
    assert 'function loadingGhost(parent, ...shapes)' in APP and "box.setAttribute('aria-hidden', 'true');" in APP
    shapes = set(re.search(r'const GHOST_COUNT = \{([^}]*)\}', APP).group(1).replace(' ', '').split(','))
    assert {s.split(':')[0] for s in shapes} == {'strip', 'cards', 'table', 'month'}
    # Every page that opens with an automatic run has a shape, and the placeholder goes once the button is enabled again.
    auto_open = set(re.findall(r'^  (\w+): \[\'[\w-]+-run\'', APP, re.M))
    auto_ghost = set(re.findall(r'(\w+): \[', re.search(r'const AUTO_GHOST = \{([^}]*)\}', APP).group(1)))
    assert auto_open and auto_open == auto_ghost
    assert "watch.observe(run, {attributes: true, attributeFilter: ['disabled']});" in APP
    # Pages that compute on their own draw it while their request is out.
    assert 'if(!officerResult){if(officerPending)loadingGhost(result,\'month\');return;}' in APP
    assert "if (dayunPending) loadingGhost(result, 'strip', 'table');" in APP
    assert "'正在按各种规则重新排盘…'); loadingGhost(result, 'table');" in APP
    assert APP.count("loadingGhost(result, 'cards');") >= 2
    # The blocks shimmer like the calendar's placeholder, stand still with reduced motion and show in forced colours.
    assert '.xs-ghost>span{display:block;' in CSS and 'animation:xs-shimmer' in CSS
    assert re.search(r'prefers-reduced-motion:reduce\)\{[^}]*\.xs-ghost>span', CSS) or '.xs-ghost>span{animation:none}' in CSS
    assert re.search(r'forced-colors:active\)\{[^@]*\.xs-ghost>span', CSS)


def test_one_character_words_are_drawn_as_their_own_text():
    # Phrase replacement skips single characters, so counts, growth stages and badge glyphs are separate texts.
    assert "texts(append(row, 'small'), primary[name] || 0, ' 个'," in APP
    assert "names.forEach(([name, cls], i) => {if (i) line.append(' · '); append(line, 'span', cls, name);});" in APP
    assert "append(badge, 'span', 'hua-layer-mark', LAYER_NAMES[layer].slice(-1));" in APP and "badge.append(type.replace('化', ''));" in APP
    assert ':lang(en) .hua-layer-mark{display:none}' in CSS
    for zh, en, ja in (('我', 'Me', '自分'), ('权', '权', '権'), ('自坐 死', 'Self seat Death (Si)', '自坐 死')):
        assert EXTRA[zh] == [en, ja]
    assert all(f'星运 {s}' in EXTRA and f'自坐 {s}' in EXTRA for s in '养死病衰墓绝胎')


def test_examples_and_default_names_follow_the_interface_language():
    # The decision example and the current chart's default name translate until the user changes them.
    assert 'const DECISION_EXAMPLE = {' in APP
    assert "decisionDraft = JSON.parse(JSON.stringify(DECISION_EXAMPLE), (key, value) => typeof value === 'string' ? calT(value) : value);" in APP
    assert "if (groupDraft.currentLabel === groupLabelShown) groupDraft.currentLabel = groupLabelShown = calT('我');" in APP
    assert "groupDraft.currentLabel.trim() || calT('我')" in APP
    # A text field the user fills still gets its hint and accessible name translated, but only from a whole entry.
    assert "const field = el.matches('input.user-text,textarea.user-text');" in I18N
    assert 'if (field && !uiIndex[source] && !uiIndex[source.trim()]) continue;' in I18N


def test_english_punctuation_ages_and_the_calendar_export():
    assert ".replace(/（([甲乙丙丁戊己庚辛壬癸])干）/g, '（$1 stem）')" in I18N
    for rule in (r"replace(/\s*、\s*/g, ', ')", r"replace(/\s*；\s*/g, '; ')", r"replace(/\s*：\s*/g, ': ')", r"replace(/(\S) {2,}(?=\S)/g, '$1 ')"):
        assert rule in I18N
    # Japanese ages: a bare 10月 would read as October.
    assert "if (uiLang === 'ja') source = source.replace(/(\\d+) ?岁 ?(\\d+) ?个?月/g, '$1歳 $2か月')" in I18N
    assert '`起运约 ${parts.years}岁 ${parts.months}个月`' in APP
    # The month calendar's text and CSV exports use the interface's words; day pillars stay as characters.
    assert "const WEEKDAY_WORDS = {en: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']" in APP
    assert "lines.push(...textColumns(calendarExportRows(calendarRows(data)), exportLang() === 'en'));" in APP
    assert "() => calendarExportRows(calendarRows(data, '节气（中国标准时间）', true))" in APP
    assert "function textColumns(rows, plain = false)" in APP
