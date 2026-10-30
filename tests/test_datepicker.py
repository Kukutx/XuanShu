"""Date fields open the project's own calendar (static/datepicker.js) instead of the browser's picker."""
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / 'static'


def test_the_calendar_script_loads_on_the_main_page_before_the_translator():
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert html.index('<script src="/static/datepicker.js" defer></script>') < html.index('/static/i18n.js')


def test_the_calendar_replaces_the_browser_picker_and_keeps_the_native_field():
    js = (STATIC / 'datepicker.js').read_text(encoding='utf-8')
    # The browser's picker opens from a click and from Alt+Down / F4; both are taken over, the field is not replaced.
    assert "input[type=date],input[type=datetime-local]" in js and 'showPicker' not in js
    assert "e.key === 'F4'" in js and "'ArrowDown'" in js and 'preventDefault' in js
    # A touch-only device keeps its own picker; typed-in values, min and max still belong to the field.
    assert '(any-pointer: fine)' in js and 'field.min' in js and 'field.max' in js
    # The chosen value reaches the page's listeners as typed input does.
    assert "new Event('input', {bubbles: true})" in js and "new Event('change', {bubbles: true})" in js
    # No native title tooltip, and every word is written in the interface language by the script itself.
    assert '.title =' not in js and "'data-no-i18n'" in js


def test_the_calendar_is_drawn_in_the_project_style():
    css = (STATIC / 'style.css').read_text(encoding='utf-8')
    for rule in ('.xs-dp{', '.xs-dp-day{', '.xs-dp-lunar{', '.xs-dp.is-sheet{', '.xs-dp-grid td[aria-selected=true] .xs-dp-day{'):
        assert rule in css, rule
    assert "the icon opens the project's own calendar" in css


def test_the_calendar_keeps_focus_and_follows_its_field():
    js = (STATIC / 'datepicker.js').read_text(encoding='utf-8')
    # A modal dialog: Tab goes round its own controls; a disabled month button hands focus to the year list.
    assert "'aria-modal', 'true'" in js and "e.key === 'Tab'" in js and "again.disabled" in js
    # A field replaced by a redraw is found again by its id; one that is gone or hidden closes the calendar.
    assert 'document.getElementById(field.id)' in js and 'getClientRects().length' in js and 'MutationObserver' in js
    # Months come through the month calendar's own loader, so one month is asked for once.
    assert 'ensureCalendarMonth(' in js and "postJSON('/api/calendar'" not in js


def test_the_hour_label_follows_the_birth_form():
    js = (STATIC / 'datepicker.js').read_text(encoding='utf-8')
    # With solar time the birth chart's hour pillar is not the clock's 时辰, so the label says it is the clock's;
    # with the hour unknown there is no label.
    assert "'hour_unknown'" in js and "mode.value !== 'clock'" in js and "t('钟表时间')" in js
    # Gregorian months are 1月…12月: 一月 would read as the lunar month named in the day cells.
    assert "m + '月'" in js


def test_the_month_loader_is_shared_and_keeps_good_data():
    app = (STATIC / 'app.js').read_text(encoding='utf-8')
    assert 'calendarPending = new Map()' in app and 'calendarPending.set(key, asked)' in app
    assert 'if (!calendarMonths[key] && !ahead) calendarMonths[key] = {error: err.message};' in app


def test_the_month_calendar_draws_its_grid_while_loading_and_fetches_neighbours():
    app = (STATIC / 'app.js').read_text(encoding='utf-8')
    css = (STATIC / 'style.css').read_text(encoding='utf-8')
    # The skeleton is the same grid, hidden from screen readers; the loading line stays the focus target.
    assert "calendarSkeleton(year, month, today);" in app and "ghost.setAttribute('aria-hidden', 'true')" in app
    assert '.cal-ghost{' in css and '@keyframes xs-shimmer' in css and '.cal-ghost{animation:none}' in css
    # The neighbouring months are fetched when idle, and a failed fetch ahead of time is not remembered as failed.
    assert 'prefetchCalendarMonths(year, month);' in app and 'ensureCalendarMonth(y, m, true)' in app
    assert '!calendarMonths[key] && !ahead' in app
