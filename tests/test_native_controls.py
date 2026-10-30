"""The browser's own control parts are drawn in the project's style: scrollbars, selects, the text-box grip, hints."""
from pathlib import Path

CSS = (Path(__file__).resolve().parents[1] / 'static/style.css').read_text(encoding='utf-8')


def test_scrollbars_and_selects_follow_the_theme():
    assert '::-webkit-scrollbar-thumb{' in CSS and '::-webkit-scrollbar-button{display:none' in CSS
    assert 'appearance:base-select' in CSS


def test_the_text_box_grip_and_field_hints_follow_the_theme():
    # The resize grip is drawn with the theme's border and accent colours, not the browser's grey hatching.
    assert '::-webkit-resizer{' in CSS and '::-webkit-resizer:hover{' in CSS and 'var(--border-strong) 40% 47%' in CSS
    # Placeholder text uses the theme's quiet colour at full opacity (Firefox would halve it).
    assert '::placeholder{color:var(--faint);opacity:1}' in CSS


def test_selects_keep_their_arrow_and_clip_long_labels():
    # Chromium's own picker icon is pushed out by a long label, so it is hidden and the theme's chevron drawn instead.
    assert 'select::picker-icon{display:none}' in CSS
    assert 'select:not([multiple]):not([size]){white-space:nowrap;overflow:hidden}' in CSS


def test_buttons_share_one_hover_and_disabled_look():
    assert 'button:disabled{cursor:not-allowed}' in CSS
    assert ':hover:not(:disabled){background:var(--gold2)' in CSS
    # Code, keys and samples use one monospace stack instead of the browser's default Courier.
    assert '--mono:ui-monospace' in CSS and 'code,kbd,samp,pre{font-family:var(--mono)}' in CSS
    assert 'ui-monospace,SFMono-Regular,Menlo,Consolas,monospace' not in CSS
    # Every focus ring uses the brighter accent (selection outlines keep the plain gold).
    import re
    focus = [rule for rule in re.findall(r'[^{}]*:focus-visible[^{}]*\{[^}]*\}', CSS) if 'outline:2px solid' in rule]
    assert focus and not any(re.search(r'outline:2px solid var\(--gold\)[;}]', rule) for rule in focus)


def test_phone_tab_strip_and_profile_buttons():
    app = (Path(__file__).resolve().parents[1] / 'static/app.js').read_text(encoding='utf-8')
    # The tab strip scrolls the opened tab into view on narrow screens.
    assert "strip.scrollTo({left:" in app
    # The load and delete buttons are greyed out while nothing is saved.
    assert "$('#load-profile').disabled = $('#remove-profile').disabled = !list.length;" in app
    # A date and time, or a time zone, takes the whole row on a phone.
    assert ".inline-control>label:has(>input[type=datetime-local],>select.zone-select){flex:1 1 100%}" in CSS
    assert "select.classList.add('zone-select');" in app
