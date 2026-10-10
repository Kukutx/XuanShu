"""Read-only runtime assets from source checkout or installed distribution.

Source checkouts use repository-level static/docs/skills. A wheel embeds the
same directories into ``app/_resources`` during its build, making installed
Web and MCP resources independent of the working directory.
"""
from __future__ import annotations

from pathlib import Path


def resource_root() -> Path:
    package_dir = Path(__file__).resolve().parent
    repository = package_dir.parent
    if ((repository / 'pyproject.toml').is_file() and
            (repository / 'static' / 'index.html').is_file() and
            (repository / 'docs' / 'rules').is_dir()):
        return repository
    embedded = package_dir / '_resources'
    if (embedded / 'static' / 'index.html').is_file() and (embedded / 'docs' / 'rules').is_dir():
        return embedded
    raise RuntimeError('XuanShu runtime assets are missing (static and docs/rules); reinstall from a complete distribution')
