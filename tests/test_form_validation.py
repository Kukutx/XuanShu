"""The birth form checks itself in the interface's style and language instead of the browser's validation bubble."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')


def test_the_browser_bubble_is_switched_off_and_the_form_checks_itself_first():
    assert 'form.noValidate = true;' in APP
    # The check is a capture listener on the form, so it runs before the casting handler and can stop it.
    check = APP.index("form.addEventListener('submit', event => {")
    assert check < APP.index("form.addEventListener('submit', async event => {")
    assert 'event.stopImmediatePropagation();' in APP[check:check + 1400] and '}, true);' in APP[check:check + 1400]
    # The lunar converter has its own button; its fields never hold back the birth form.
    assert "!el.closest('#lunar-entry')" in APP


def test_each_problem_has_a_written_reason_in_every_language():
    extra = json.loads((ROOT / 'scripts/i18n_extra.json').read_text(encoding='utf-8'))
    block = APP[APP.index('const FIELD_PROBLEMS = {'):APP.index('const checkedFields')]
    reasons = set(re.findall(r"'([^']*[一-鿿][^']*)'", block))
    assert len(reasons) >= 12
    for reason in reasons:
        assert reason in extra and all(extra[reason]), reason


def test_a_marked_field_is_announced_and_styled():
    assert "el.setAttribute('aria-invalid', 'true')" in APP and "'-problem'" in APP
    css = (ROOT / 'static/style.css').read_text(encoding='utf-8')
    assert ':is(input,select,textarea)[aria-invalid=true]{border-color:var(--red)!important}' in css
    assert '.field-problem{' in css


def test_marked_fields_follow_every_change_of_the_birth_data():
    # Not only the typed field: a city choice, the lunar converter and a loaded profile change fields from code.
    assert "form.querySelectorAll('[aria-invalid=true]')" in APP
    stale = APP.index('function updateStaleBirthNotice() {')
    assert 'recheckFieldProblems();' in APP[stale:stale + 80]
    # A half-typed date is named as half-typed, not as missing.
    generic = APP[APP.index('const GENERIC_PROBLEMS'):]
    assert generic.index('badInput') < generic.index('valueMissing')
    # Enter in the lunar fields converts the lunar date instead of casting from the Gregorian one.
    assert "$('#lunar-entry').addEventListener('keydown'" in APP and "$('#lunar-fill').click();" in APP


def test_contrast_themes_tell_a_field_to_fix_from_the_focused_one():
    css = (ROOT / 'static/style.css').read_text(encoding='utf-8')
    assert ':is(input,select,textarea)[aria-invalid=true]{border:2px dashed CanvasText!important}' in css
    assert ":is(input,select,textarea)[aria-invalid=true]:focus{border-style:solid!important;border-color:Highlight!important}" in css
    # The badge is drawn, not read: screen readers read only the reason.
    assert ".field-problem::before{content:'!' / '';" in css
