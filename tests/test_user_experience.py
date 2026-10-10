"""UX contract tests for the question-first XuanShu console."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_function_discovery_does_not_remove_legacy_tools():
    html=(ROOT/'static/index.html').read_text(encoding='utf-8')
    js=(ROOT/'static/app.js').read_text(encoding='utf-8')
    assert html.count('data-tab=') == 22
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
