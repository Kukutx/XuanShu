"""Terms used in XuanShu's outputs, read from docs/rules/glossary.md so the document is the single source.

Each entry says what a term is and how XuanShu computes it, with the rule document that has the details. No entry
judges anything good or bad. A row may explain several related terms together (listed with 、); true aliases follow
a ／. ``term`` is the headword as written, ``names`` the terms it explains and ``aliases`` the other names for them.
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
        if not line.startswith('|') or len(cells) != 7 or cells[0] in ('术语', '---'):
            continue
        head, *aliases = cells[0].split('／')
        entries.append({'term': head, 'names': head.split('、'), 'aliases': aliases, 'system': cells[1],
                        'definition': cells[2], 'in_xuanshu': cells[3], 'rule_doc': 'docs/rules/' + cells[4],
                        'term_en': cells[5], 'term_ja': cells[6]})
    return tuple(entries)


def terms_in(text: str) -> list[dict]:
    """The entries whose terms or aliases occur in ``text``, in glossary order."""
    return [dict(entry) for entry in glossary() if any(name in text for name in (*entry['names'], *entry['aliases']))]
