"""System display preferences beyond light and dark, and the way back to the tool tabs from far down a page."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'static/style.css').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')
HTML = (ROOT / 'static/index.html').read_text(encoding='utf-8')
TIPS = (ROOT / 'static/tips.js').read_text(encoding='utf-8')


def test_more_contrast_strengthens_borders_and_secondary_text_in_both_themes():
    dark = re.search(r'@media \(prefers-contrast:more\)\{\n  :root\{([^}]*)\}\n  :root\[data-theme="light"\]\{([^}]*)\}', CSS)
    system_light = re.search(r'@media \(prefers-contrast:more\) and \(prefers-color-scheme:light\)\{\n  :root:not\(\[data-theme="dark"\]\)\{([^}]*)\}', CSS)
    assert dark and system_light
    # The chosen light theme and the system's light theme get the same values.
    assert dark.group(2) == system_light.group(1)
    for block in (dark.group(1), dark.group(2)):
        assert all(f'--{name}:' in block for name in ('border', 'text2', 'muted', 'faint', 'accent-line', 'ring', 'glass'))
    # After the theme blocks, so it overrides them; before the base rules.
    assert CSS.index('@media (prefers-color-scheme:light){') < CSS.index('@media (prefers-contrast:more){') < CSS.index('/* ---- base ---- */')


def test_less_transparency_also_drops_the_dialog_blur():
    block = CSS[CSS.index('@media (prefers-reduced-transparency:reduce){'):]
    block = block[:block.index('\n}') + 2]
    assert '.share-dialog::backdrop{background:rgba(4,6,10,.74);-webkit-backdrop-filter:none;backdrop-filter:none}' in block


def test_back_to_the_tool_tabs():
    assert '<button id="to-top" class="to-top" type="button" aria-label="回到功能标签" data-tip="回到功能标签"></button>' in HTML
    # Shown a screen past the tabs; hidden by visibility so it takes no focus while out of sight.
    assert "toTop.classList.toggle('is-shown', $('#workspace-tabs').getBoundingClientRect().bottom < -innerHeight);" in APP
    assert "{toTopFrame ||= requestAnimationFrame(placeToTop);}, {passive: true}" in APP
    assert "tab.focus({preventScroll: true});" in APP[APP.index("toTop.addEventListener('click'"):]
    assert '.to-top{position:fixed;' in CSS and 'visibility:hidden;opacity:0;' in CSS and '.to-top.is-shown{visibility:visible;' in CSS
    assert '@media print{.to-top{display:none!important}}' in CSS and '@media (forced-colors:active){.to-top{border-color:ButtonText}' in CSS
    # A hint that repeats an icon button's name is not read twice.
    assert "if (text && text !== el.getAttribute('aria-label'))" in TIPS and "attributeFilter: ['data-tip', 'aria-label']" in TIPS
