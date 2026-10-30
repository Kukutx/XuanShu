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
