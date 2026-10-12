"""Terms used in XuanShu's outputs, read from docs/rules/glossary.md so the document is the single source.

Each entry says what a term is and how XuanShu computes it, with the rule document that has the details. No entry
judges anything good or bad.
"""
from __future__ import annotations

from functools import lru_cache

from .asset_paths import resource_root

GLOSSARY_DOC = 'docs/rules/glossary.md'


@lru_cache(maxsize=1)
def glossary() -> tuple[dict, ...]:
    entries = []
    for line in (resource_root() / GLOSSARY_DOC).read_text(encoding='utf-8').splitlines():
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if not line.startswith('|') or len(cells) != 5 or cells[0] in ('术语', '---'):
            continue
        names = cells[0].split('／')
        entries.append({'term': names[0], 'aliases': names[1:], 'system': cells[1], 'definition': cells[2],
                        'in_xuanshu': cells[3], 'rule_doc': 'docs/rules/' + cells[4]})
    return tuple(entries)


def terms_in(text: str) -> list[dict]:
    """The entries whose term or an alias occurs in ``text``, in glossary order."""
    return [dict(entry) for entry in glossary() if any(name in text for name in (entry['term'], *entry['aliases']))]
