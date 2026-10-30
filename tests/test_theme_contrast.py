"""Every colour token used for text reaches WCAG AA (4.5:1) on every panel colour, in both themes.

The tokens live in static/style.css: the dark theme on :root, the light theme on :root[data-theme="light"] and again
for a light system preference. Charts colour stems, branches, transformations and labels with these tokens on any of
the panel colours, so each pair is checked rather than only the main text. The print block is checked the same way."""
import re
from pathlib import Path

CSS = (Path(__file__).resolve().parents[1] / 'static' / 'style.css').read_text(encoding='utf-8')
TEXT = 'text text2 muted faint gold gold2 green red warn wood fire earth metal water lu quan ke ji'.split()
BACKGROUNDS = 'bg panel panel2 panel3'.split()


def tokens(start: str) -> dict[str, str]:
    i = CSS.index(start)
    body = CSS[i:CSS.index('}', i)]
    found = {}
    for name, value in re.findall(r'--([\w-]+):(#[0-9a-fA-F]{3,6})\b', body):
        found[name] = value if len(value) == 7 else '#' + ''.join(c * 2 for c in value[1:])
    return found


def contrast(a: str, b: str) -> float:
    def luminance(hex_colour: str) -> float:
        channels = [int(hex_colour[k:k + 2], 16) / 255 for k in (1, 3, 5)]
        r, g, b = (c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4 for c in channels)
        return .2126 * r + .7152 * g + .0722 * b
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + .05) / (low + .05)


THEMES = {'dark': tokens(':root{'), 'light': tokens(':root[data-theme="light"]{'),
          'light (system)': tokens(':root:not([data-theme="dark"]){'),
          # Printing from the dark theme takes these (the light blocks outrank them when the light theme is on).
          'print': tokens('@media print{\n  :root{')}


def test_both_light_blocks_define_the_same_colours():
    assert THEMES['light'] == THEMES['light (system)']


def test_text_tokens_reach_aa_on_every_panel():
    failures = []
    for theme, t in THEMES.items():
        for name in TEXT:
            for background in BACKGROUNDS:
                ratio = contrast(t[name], t[background])
                if ratio < 4.5:
                    failures.append(f'{theme}: --{name} {t[name]} on --{background} {t[background]} = {ratio:.2f}')
    assert not failures, '\n'.join(failures)


def test_text_on_filled_badges_reaches_aa():
    for theme, t in THEMES.items():
        assert contrast(t['on-gold'], t['gold']) >= 4.5, theme
        for name in ('lu', 'quan', 'ke', 'ji'):
            assert contrast(t['on-hua'], t[name]) >= 4.5, (theme, name)
