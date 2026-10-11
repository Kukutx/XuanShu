"""UX contract tests for the question-first XuanShu console."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_function_discovery_does_not_remove_legacy_tools():
    html=(ROOT/'static/index.html').read_text(encoding='utf-8')
    js=(ROOT/'static/app.js').read_text(encoding='utf-8')
    assert html.count('data-tab=') == 26
    assert 'id="tool-search"' in html
    assert 'id="tool-toggle-all"' in html
    assert 'id="tool-visible-count"' in html
    assert 'function updateToolNavigation()' in js
    for tab in ('consult','bazi','qimen','ziwei','professional','calendar','pair','decision','report'):
        assert f"'{tab}'" in js

def test_consultation_shortcuts_and_advanced_inputs():
    js=(ROOT/'static/app.js').read_text(encoding='utf-8')
    assert 'consult-shortcuts' in js
    assert 'consult-advanced' in js
    assert "['auto','自动识别']" in js
    for t in ('natal','career','relationship','timing','decision'):
        assert f"'{t}'" in js
    assert 'payload.partner_authorized=true' in js
    assert 'const preserveDraft=()=>{' in js
    assert 'control.addEventListener(\'input\',preserveDraft)' in js
    assert 'if(birthCheck.checked)payload.birth=readInput()' in js

def test_accurate_integration_labels_and_default_dates():
    js=(ROOT/'static/app.js').read_text(encoding='utf-8')
    for count in ('25 Tools','17 Resources','18 Skills','15 Prompts'):
        assert f"value:'{count}'" in js
    assert 'start_date: localToday()' in js
    assert "question:''" in js

def test_demo_birth_warning_and_api_errors():
    html=(ROOT/'static/index.html').read_text(encoding='utf-8')
    js=(ROOT/'static/app.js').read_text(encoding='utf-8')
    assert 'id="demo-birth-warning"' in html
    assert 'function updateDemoBirthWarning()' in js
    assert '请检查 API 访问令牌' in js


def test_python315_acceptance_includes_packaging():
    windows=(ROOT/'scripts/windows_acceptance.ps1').read_text(encoding='utf-8')
    github=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert 'scripts/wheel_smoke.py' in windows
    assert 'pip setuptools wheel' in windows
    assert 'python_latest:' in github
    assert 'uv python install 3.15' in github
    assert '.venv/bin/python scripts/wheel_smoke.py' in github


def test_mcp_onboarding_snippet_is_copyable_and_portable():
    js=(ROOT/'static/app.js').read_text(encoding='utf-8')
    assert "copy.id='integration-copy'" in js
    assert "'C:\\\\path\\\\to\\\\xuanshu'" in js
    assert "navigator.clipboard.writeText(snippet)" in js
    assert "'/path/to/xuanshu'" in js



def test_workbench_is_keyboard_accessible_and_shareable_without_birth_data():
    html=(ROOT/'static/index.html').read_text(encoding='utf-8')
    js=(ROOT/'static/app.js').read_text(encoding='utf-8')
    assert "function tabFromHash()" in js
    assert "history.replaceState(null, '', '#tool=' + active)" in js
    assert "function activateTab(tab, updateUrl = true)" in js
    assert "'ArrowRight','ArrowLeft','Home','End'" in js
    assert "event.key.toLowerCase() === 'k'" in js
    assert "const toolKeywords" in js
    assert "integration:'mcp" in js
    assert 'Ctrl+K' in html
    assert 'role="tablist"' in html


def test_editing_birth_disables_old_chart_export_without_discarding_it():
    html=(ROOT/'static/index.html').read_text(encoding='utf-8')
    js=(ROOT/'static/app.js').read_text(encoding='utf-8')
    assert 'id="stale-birth-warning"' in html
    assert "function updateStaleBirthNotice()" in js
    assert "JSON.stringify(readInput()) !== JSON.stringify(currentInput)" in js
    assert "$('#download-json').disabled = true" in js
    assert "updateStaleBirthNotice();" in js
    assert "const outdatedQimen=" in js
    assert "fingerprint !== qimenFingerprint" in js


def test_report_markdown_can_be_copied_without_downloading():
    js=(ROOT/'static/app.js').read_text(encoding='utf-8')
    assert "copyBtn.id='consult-copy-markdown'" in js
    assert "navigator.clipboard.writeText(consultResult.markdown)" in js
