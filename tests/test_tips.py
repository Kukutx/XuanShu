"""Hints are drawn by static/tips.js in the project's style, never as the browser's native title tooltip."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'static'


def test_no_native_title_tooltips_in_the_interface():
    for path in STATIC.glob('*.js'):
        if path.name in ('i18n-extra.js', 'zh-tw-map.js'):
            continue
        text = path.read_text(encoding='utf-8')
        assert not re.search(r"(?<!document)\.title = ", text), path.name
        assert "setAttribute('title'" not in text, path.name
    for path in STATIC.glob('*.html'):
        assert not re.search(r'<(?!title\b)[a-z][^>]*\stitle="', path.read_text(encoding='utf-8')), path.name


def test_every_page_loads_the_hint_layer_and_translates_hints():
    for page in ('index.html', 'api.html'):
        assert '<script src="/static/tips.js" defer></script>' in (STATIC / page).read_text(encoding='utf-8'), page
    assert "'data-tip'" in re.search(r'const UI_ATTRS = \[[^\]]*\]', (STATIC / 'i18n.js').read_text(encoding='utf-8')).group(0)
    tips = (STATIC / 'tips.js').read_text(encoding='utf-8')
    assert 'innerHTML' not in tips and 'Storage' not in tips and 'localStorage' not in tips
    assert "role', 'tooltip'" in tips and 'aria-describedby' in tips and "'Escape'" in tips
