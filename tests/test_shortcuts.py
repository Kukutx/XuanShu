"""Every keyboard shortcut is listed in one dialog, opened with ? or from the hint beside the feature search."""
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / 'static'


def test_the_hint_opens_the_shortcut_list():
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert re.search(r'<button id="shortcuts-open" type="button" class="tool-keyboard-hint" aria-haspopup="dialog"', html)
    app = (STATIC / 'app.js').read_text(encoding='utf-8')
    assert "$('#shortcuts-open').addEventListener('click', openShortcuts);" in app


def test_question_mark_opens_it_except_while_typing():
    app = (STATIC / 'app.js').read_text(encoding='utf-8')
    assert "event.key === '?'" in app and "closest('input,textarea,select,[contenteditable]" in app
    assert "!document.querySelector('dialog[open]')" in app and 'dialog.showModal()' in app


def test_the_list_names_the_shortcuts_the_page_has():
    app = (STATIC / 'app.js').read_text(encoding='utf-8')
    body = app[app.index('const SHORTCUTS = ['):app.index('function openShortcuts()')]
    for group in ('任何地方', '功能标签', '日期框和日历', '历法日历', '命盘', 'AI 对话'):
        assert f"'{group}'" in body, group
    # The keys it names are the ones the handlers listen for.
    assert "['Ctrl', 'K']" in body and "['Alt', '↓']" in body and "['Shift', 'Enter']" in body
    datepicker = (STATIC / 'datepicker.js').read_text(encoding='utf-8')
    assert "e.key === 'F4'" in datepicker and "e.key === 'PageUp'" in datepicker
    css = (STATIC / 'style.css').read_text(encoding='utf-8')
    assert 'kbd{display:inline-block' in css and '.share-dialog.shortcuts-dialog{' in css
