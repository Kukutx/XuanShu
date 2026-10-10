"""Static plugin package acceptance; a private install is a separate action."""
import json
from pathlib import Path
from scripts.build_plugin import MANIFEST, ROOT, build


def test_manifest_is_explicit_about_unhosted_mcp():
    assert MANIFEST['name']=='xuanshu' and MANIFEST['version']=='0.1.0'
    assert MANIFEST['$schema'].startswith('https://agent-plugins.org/')
    assert 'mcp.json' not in MANIFEST and 'MCP endpoint' in MANIFEST['description']


def test_plugin_build_skills_zip(tmp_path):
    import zipfile
    result=build(tmp_path/'plugin.zip')
    with zipfile.ZipFile(result) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == 19
        assert len([n for n in archive.namelist() if n.endswith('/SKILL.md')]) == 18
        for entry in archive.namelist():
            assert entry=='plugin.json' or entry.startswith('skills/')
            assert '..' not in entry
        assert json.loads(archive.read('plugin.json'))['name']=='xuanshu'
