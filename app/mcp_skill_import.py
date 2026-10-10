"""Bounded MCP skills catalogue compatible with OpenAI's SEP-2640 subset.

The remote importer limits one scan to five skills. The distributable plugin
contains all project skills, while this endpoint deliberately exposes five
high-value, read-only workflow instructions. Resource digests always derive
from the exact UTF-8 response text, never from a stale manifest.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .asset_paths import resource_root

IMPORTABLE = (
    'bazi-analysis',
    'ziwei-analysis',
    'qimen-hour-chabu',
    'calculation-quality-audit',
    'structured-dossier',
)
PAGE_SIZE = 2
BASE = resource_root() / 'skills'


def _text_and_frontmatter(name: str) -> tuple[str, dict[str, str]]:
    if name not in IMPORTABLE:
        raise ValueError('Unknown importable skill')
    source = BASE / name / 'SKILL.md'
    if not source.is_file() or source.is_symlink():
        raise ValueError('Skill resource unavailable')
    text = source.read_text(encoding='utf-8')
    parts = text.split('---', 2)
    if len(parts) != 3 or parts[0] != '':
        raise ValueError('Invalid skill frontmatter')
    fm: dict[str, str] = {}
    for line in parts[1].splitlines():
        if not line.strip():
            continue
        if ':' not in line:
            raise ValueError('Unsupported skill frontmatter')
        k, v = line.split(':', 1)
        k = k.strip()
        if k in fm:
            raise ValueError('Duplicate skill frontmatter field')
        fm[k] = v.strip().strip('"\'')
    if fm.get('name') != name or not fm.get('description'):
        raise ValueError('Skill name and description are mandatory')
    return text, fm


def skill_entry(name: str) -> dict:
    contents, frontmatter = _text_and_frontmatter(name)
    uri = f'skill://xuanshu/{name}/SKILL.md'
    digest = hashlib.sha256(contents.encode('utf-8')).hexdigest()
    return {'uri': uri, 'frontmatter': frontmatter,
            'resources': [{'uri': uri, 'digest': 'sha256:' + digest}]}


def list_importable_skills(cursor: str | None = None) -> dict:
    if cursor is None:
        position = 0
    elif cursor in ('2', '4'):
        position = int(cursor)
    else:
        raise ValueError('Invalid skills/list cursor')
    entries = [skill_entry(name) for name in IMPORTABLE[position:position+PAGE_SIZE]]
    result = {'skills': entries}
    if position + PAGE_SIZE < len(IMPORTABLE):
        result['nextCursor'] = str(position + PAGE_SIZE)
    return result


def get_importable_skill(uri: str) -> dict:
    for name in IMPORTABLE:
        entry = skill_entry(name)
        if entry['uri'] == uri:
            return {'skill': entry}
    raise ValueError('Unknown skill URI')


def get_skill_resource(uri: str) -> dict | None:
    for name in IMPORTABLE:
        entry = skill_entry(name)
        if entry['uri'] == uri:
            text, _ = _text_and_frontmatter(name)
            return {'contents': [{'uri': uri, 'mimeType': 'text/markdown', 'text': text}]}
    return None
