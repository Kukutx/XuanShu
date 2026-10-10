"""Guard against shipping resources without skills/Docker support."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def test_agent_skills_metadata_and_count():
    paths = sorted((ROOT/'skills').glob('*/SKILL.md'))
    assert len(paths) == 18
    for path in paths:
        text = path.read_text(encoding='utf-8')
        assert text.startswith('---\n')
        frontmatter = text.split('---',2)[1]
        assert f'name: {path.parent.name}' in frontmatter
        assert re.search(r'(?m)^description: .{40,}$', frontmatter)
        assert len(text) > 400


def test_mcp_resource_files_shipped_in_docker():
    docker = (ROOT/'Dockerfile').read_text(encoding='utf-8')
    assert 'COPY docs ./docs' in docker
    for name in ('bazi','ziwei','privacy'):
        assert (ROOT/'docs/rules'/f'{name}.md').is_file()


def test_ui_feature_count_in_html_and_js():
    html = (ROOT/'static/index.html').read_text(encoding='utf-8')
    js = (ROOT/'static/app.js').read_text(encoding='utf-8')
    assert html.count('data-tab=') == 24
    assert '18 AGENT SKILLS' in html
    assert '27 MCP TOOLS' in html and '15 PROMPTS' in html and '17 RESOURCES' in html
    for endpoint in ('/api/combined','/api/analyze','/api/calendar','/api/pair'):
        assert endpoint in js


def test_readme_matches_version():
    from app import __version__
    readme = (ROOT/'README.md').read_text(encoding='utf-8')
    assert __version__ == '0.1.0'
    assert 'v.0.1.0' in readme


def test_build_release_preflight_metadata():
    from scripts.build_release import validate_release_metadata
    validate_release_metadata(ROOT)


def test_build_release_fails_closed_on_stale_metadata(tmp_path):
    from scripts.build_release import validate_release_metadata
    paths = ['pyproject.toml', 'app/__init__.py', 'README.md', 'TEST_REPORT.md', 'CHANGELOG.md', 'static/index.html']
    for name in paths:
        source = ROOT/name
        target = tmp_path/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    old_report = tmp_path/'TEST_REPORT.md'
    old_report.write_text('# XuanShu stale-test-marker · broken release\n', encoding='utf-8')
    import pytest
    with pytest.raises(ValueError, match='TEST_REPORT.md'):
        validate_release_metadata(tmp_path)


def test_reject_any_future_package_version_without_explicit_release_decision(tmp_path):
    from scripts.build_release import validate_release_metadata
    import pytest
    paths = ['pyproject.toml','app/__init__.py','README.md','TEST_REPORT.md','CHANGELOG.md','static/index.html']
    for name in paths:
        dest = tmp_path/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT/name).read_bytes())
    pyproject = tmp_path/'pyproject.toml'
    pyproject.write_text(pyproject.read_text(encoding='utf-8').replace('version = "0.1.0"','version = "0.2.0"'), encoding='utf-8')
    with pytest.raises(ValueError,match='frozen'):
        validate_release_metadata(tmp_path)

def test_internal_and_public_versions_remain_in_sync():
    import tomllib
    from app import __version__, __display_version__
    assert __version__ == '0.1.0'
    assert __display_version__ == 'v.0.1.0'
    assert tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']['version'] == __version__
    assert __display_version__ in (ROOT/'static/index.html').read_text(encoding='utf-8')
    assert __display_version__ in (ROOT/'README.md').read_text(encoding='utf-8')


def test_xuanshu_brand_is_consistent():
    import tomllib
    config=tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))
    assert config['project']['name']=='xuanshu'
    assert 'xuanshu' in config['project']['scripts']
    assert config['project']['version']=='0.1.0'
    ui=(ROOT/'static/index.html').read_text(encoding='utf-8')
    assert '<title>玄枢 · XuanShu v.0.1.0</title>' in ui
    assert 'ENGINE 1.4' not in ui
    assert 'ORIENTAL ASTRO AGENT' not in ui
    from scripts.build_release import DEFAULT_ZIP
    assert DEFAULT_ZIP.name=='xuanshu-v.0.1.0.zip'


def test_web_preserves_pre_rename_profiles_and_backup_compatibility():
    client=(ROOT/'static/app.js').read_text(encoding='utf-8')
    archive=(ROOT/'static/vault.js').read_text(encoding='utf-8')
    assert "const profileKey = 'xuanshu-profiles-v2'" in client
    assert 'legacyProfileKey' in client and "'oriental-astro-profiles-v2'" in client
    assert "'xuanshu-aes256gcm-v1'" in archive
    assert "'oriental-astro-aes256gcm-v1'" in archive
    assert 'const expectedSchema = legacy' in archive


def test_wheel_includes_research_and_reproducible_examples():
    setup=(ROOT/'setup.py').read_text(encoding='utf-8')
    manifest=(ROOT/'MANIFEST.in').read_text(encoding='utf-8')
    for path in ("docs/research", "examples"):
        assert f"Path('{path}')" in setup
        assert f'recursive-include {path}' in manifest
    import json
    fixture=json.loads((ROOT/'examples/deep-evidence-reference-2024-02-07.json').read_text(encoding='utf-8'))
    assert fixture['input_parameters']['birth']['gender']=='unspecified'


def test_release_excludes_local_secrets_and_browser_artifacts():
    from scripts.build_release import is_excluded, source_files
    for filename in (
        '.artifacts/browser-smoke/01-bazi-desktop.png',
        '.env.local', '.env.production', 'credentials.pem',
        'private.key', 'secrets.p12', 'local.sqlite',
    ):
        assert is_excluded(Path(filename)), filename
    assert not is_excluded(Path('.env.example'))
    assert not is_excluded(Path('app/main.py'))
    assert all('.artifacts' not in p.relative_to(ROOT).parts for p in source_files())


def test_release_verification_rejects_hashed_secret_file(tmp_path):
    import hashlib
    import zipfile
    import pytest
    from scripts.build_release import PREFIX, MANIFEST, verify
    content = b'example-only-no-secret'
    digest = hashlib.sha256(content).hexdigest()
    path = tmp_path / 'invalid-secret.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr(f'{PREFIX}/.env.local', content)
        archive.writestr(f'{PREFIX}/{MANIFEST}',
                         f'{digest}  .env.local\n'.encode('utf-8'))
    with pytest.raises(ValueError, match='Forbidden release entry'):
        verify(path)



def test_ignored_virtualenv_symlinks_do_not_block_release(tmp_path, monkeypatch):
    # Python 3.15 uv venv creates a POSIX .venv/lib64 -> lib link.
    import pytest
    from scripts import build_release
    ignored = tmp_path / '.venv'
    ignored.mkdir()
    link = ignored / 'lib64'
    try:
        link.symlink_to(ignored, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip('Host does not permit creating symbolic links')
    source = tmp_path / 'README.md'
    source.write_text('example', encoding='utf-8')
    monkeypatch.setattr(build_release, 'ROOT', tmp_path)
    assert build_release.source_files() == [source]

    # Unexcluded source symlinks remain forbidden (no data exfiltration).
    untrusted = tmp_path / 'untrusted'
    untrusted.symlink_to(source)
    with pytest.raises(ValueError, match='refuses symbolic links'):
        build_release.source_files()
