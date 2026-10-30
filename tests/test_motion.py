"""Motion on switches: the tab pill slides between tools and a theme change spreads from its button."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'static/style.css').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')
THEME = (ROOT / 'static/theme.js').read_text(encoding='utf-8')


def test_tab_pill_slides_from_the_previous_tool():
    assert 'function slideTabPill(from, to)' in APP and 'slideTabPill(previous, tab);' in APP
    # Nothing slides on the first activation at load, with reduced motion, or from a hidden tab.
    assert 'const previous = tabsShown ? tabs.find(other => other.classList.contains(\'active\')) : null;' in APP
    assert "matchMedia('(prefers-reduced-motion: reduce)').matches || typeof to.animate !== 'function') return;" in APP
    assert 'if (!a.width || !b.width) return;' in APP
    # The pill is decorative, lies under the tab labels, and goes when the slide lands or is cut short.
    assert "pill.setAttribute('aria-hidden', 'true');" in APP and 'slide.onfinish = land; slide.oncancel = land;' in APP
    assert '.tabbar{position:relative;isolation:isolate}' in CSS and '.tab-pill{position:absolute;z-index:-1;' in CSS
    assert '.tab.active.pill-arriving{background:transparent;box-shadow:none;' in CSS
    assert '  .tab-pill{display:none}' in CSS  # forced colours keep the outline on the active tab instead


def test_theme_change_spreads_from_the_button():
    assert 'function reveal(button)' in THEME and 'document.startViewTransition(apply)' in THEME
    # Only a change of colours animates; without view transitions or with reduced motion the theme applies at once.
    assert 'if (isDark(choice) !== before) reveal(event && event.currentTarget); else apply();' in THEME
    assert "typeof document.startViewTransition !== 'function'" in THEME and "prefers-reduced-motion: reduce" in THEME
    assert "pseudoElement: '::view-transition-new(root)'" in THEME
    # The reveal replaces the default cross-fade only while it runs.
    assert 'html.theme-reveal::view-transition-old(root),html.theme-reveal::view-transition-new(root){animation:none;' in CSS
    assert "transition.finished.finally(() => root.classList.remove('theme-reveal'));" in THEME


def test_dialogs_fade_out_as_they_close():
    assert '.share-dialog{transition:opacity .16s var(--ease),transform .16s var(--ease),overlay .16s allow-discrete,display .16s allow-discrete}' in CSS
    # While it fades it stays drawn on top, so clicks must pass through it to the page.
    assert '.share-dialog:not([open]){opacity:0;transform:translateY(6px) scale(.985);pointer-events:none}' in CSS
    assert '.share-dialog:not([open])::backdrop{opacity:0;pointer-events:none}' in CSS
    assert '@starting-style{.share-dialog[open]::backdrop{opacity:0}}' in CSS
    assert '@media (prefers-reduced-motion:reduce){.share-dialog::backdrop{transition:none}}' in CSS
