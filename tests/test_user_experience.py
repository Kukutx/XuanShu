"""UX contract tests for the question-first XuanShu console."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_function_discovery_does_not_remove_legacy_tools():
    html=(ROOT/'static/index.html').read_text(encoding='utf-8')
    js=(ROOT/'static/app.js').read_text(encoding='utf-8')
    assert html.count('data-tab=') == 29
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
    # The integration page shows the running server's counts, so no number written into the page can fall behind.
    from app.main import capabilities
    counts = capabilities()['counts']
    for key in ('mcp_tools','mcp_resources','agent_skills','mcp_prompts'):
        assert f"count('{key}'" in js and isinstance(counts[key], int) and counts[key] > 0
    assert not any(f"value:'{n} Tools'" in js for n in range(100))
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
    assert "'integration-copy'" in js
    assert "'C:\\\\path\\\\to\\\\xuanshu'" in js
    assert "navigator.clipboard.writeText(text())" in js
    assert "'/path/to/xuanshu'" in js


def test_integration_catalogue_groups_every_mcp_tool_and_links_real_pages():
    """Every tool the server lists has a purpose group, and every workbench link names an existing tab."""
    import re
    from app.mcp import TOOLS
    js=(ROOT/'static/app.js').read_text(encoding='utf-8')
    html=(ROOT/'static/index.html').read_text(encoding='utf-8')
    groups=js[js.index('const AG_GROUPS = ['):js.index('];', js.index('const AG_GROUPS = ['))]
    grouped=re.findall(r"'([a-z_]+)'", groups.split('\n', 1)[1])
    named={g for g in re.findall(r"\['([a-z]+)', '", groups)}
    tool_names=set(grouped)-named
    assert tool_names==set(TOOLS) and len(grouped)-len(named)==len(TOOLS)
    links=js[js.index('const AG_TABS = {'):js.index('};', js.index('const AG_TABS = {'))]
    pairs=dict(re.findall(r"([a-z_]+): '([a-z-]+)'", links))
    tabs=set(re.findall(r'data-tab="([a-z-]+)"', html))
    assert pairs and set(pairs)<=set(TOOLS) and set(pairs.values())<=tabs
    # Example calls never read the birth form.
    examples=js[js.index('const AG_BIRTH ='):js.index('function agExample')]
    assert 'readInput' not in examples and "$('#birth_datetime')" not in examples



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
    assert "copyBtn.id = 'consult-copy-markdown'" in js
    assert "navigator.clipboard.writeText(c.markdown)" in js


def test_professional_page_install_advice_matches_the_optional_dependency():
    """The install command the page offers is the provider pinned in pyproject, never a `xuanshu[...]` download."""
    import re
    import tomllib
    js=(ROOT/'static/app.js').read_text(encoding='utf-8')
    pinned=tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']['optional-dependencies']['professional']
    command=re.search(r"const PF_INSTALL = '([^']+)'", js).group(1)
    assert command == f'python -m pip install "{pinned[0]}"'
    assert 'xuanshu[professional]' not in js
    # The page reads the provider flag the server reports, and the guards stop a request that cannot be meaningful.
    assert 'professional_ziwei_provider_available' in js and "'professional-gender'" in js and "'professional-hour-unknown'" in js


def test_no_native_confirm_dialogs():
    """Confirmations use the page's own dialog (xsConfirm), whose text follows the interface language."""
    import re
    for name in ('app.js', 'chat.js', 'vault.js'):
        js = (ROOT / 'static' / name).read_text(encoding='utf-8')
        assert not re.search(r'(?<![\w.])(?:window\.)?confirm\(', js), name
    assert 'function xsConfirm' in (ROOT / 'static/chat.js').read_text(encoding='utf-8')
