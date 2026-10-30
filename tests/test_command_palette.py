"""The tool finder as a command palette: typed words list matching tools and page actions, chosen by keyboard."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'static/style.css').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')
HTML = (ROOT / 'static/index.html').read_text(encoding='utf-8')


def test_finder_is_an_aria_combobox_with_a_listbox():
    assert ('<input id="tool-search" type="search" placeholder="搜索八字、择时、报告等 29 项能力" autocomplete="off" role="combobox" '
            'aria-autocomplete="list" aria-expanded="false" aria-controls="tool-palette" />') in HTML
    assert '<ul id="tool-palette" class="tool-palette" role="listbox" aria-label="匹配的功能与操作" hidden></ul>' in HTML
    # The chosen option is announced through aria-activedescendant while the focus stays in the box.
    assert "input.setAttribute('aria-activedescendant', option.id)" in APP and "option.setAttribute('role', 'option')" in APP
    assert "$('#tool-palette').addEventListener('pointerdown', event => event.preventDefault());" in APP


def test_keys_choose_and_run_and_typing_methods_are_respected():
    assert "if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {" in APP
    assert "} else if (event.key === 'Enter' && paletteItems.length) {" in APP
    # An IME composition's Enter confirms the characters, not a palette choice.
    assert 'if (event.isComposing) return;' in APP
    # Running a choice clears the search first, so the strip shows its usual tools again.
    assert "$('#tool-search').value = ''; hidePalette(); updateToolNavigation();" in APP


def test_actions_press_existing_buttons_and_hide_when_unavailable():
    body = APP[APP.index('const PALETTE_ACTIONS = ['):APP.index('const PALETTE_LIMIT')]
    for target in ("$('#run-btn').click()", "$('#download-json').click()", "$('#share-card').click()", "$('#print-view').click()",
                   "$('#theme-toggle').click()", "$('#shortcuts-open').click()", "$('#crosscheck-open').click()",
                   "$('#tool-toggle-all').click()", "focusBirthField('birth_datetime')"):
        assert target in body, target
    assert "ok: () => !$('#download-json').disabled" in body and "ok: () => $('#ui-language').value !== lang" in body
    # The words an action answers to are input vocabulary, kept out of the translation table.
    keys = APP.index('// # i18n: input vocabulary, not interface text\nconst PALETTE_KEYS = {')
    assert keys < APP.index('// # i18n: end of input vocabulary') < APP.index('const PALETTE_ACTIONS = [')


def test_palette_styles_and_shortcut_list():
    assert '.tool-search-box{position:relative;flex:1;' in CSS and '.tool-palette{position:absolute;z-index:35;' in CSS
    assert '.palette-opt.is-active{background:var(--accent-soft);color:var(--text)}' in CSS
    assert '  .palette-opt.is-active{outline:2px solid Highlight;outline-offset:-2px}' in CSS
    assert "['功能查找', [[['↑', '↓'], '在匹配的功能和操作之间移动'], [['Enter'], '打开功能或执行操作'], [['Esc'], '清空查找']]]" in APP
