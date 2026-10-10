#!/usr/bin/env python3
"""Initialize an authenticated *local-only* Docker configuration, once.

Refuse to modify an existing .env: credentials and OAuth settings must not
be silently replaced. Token remains in .env (ignored by Git), never printed.
"""
from __future__ import annotations

import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]

def initialize(root: Path = ROOT) -> Path:
    target = root / '.env'
    secret = secrets.token_urlsafe(48)
    content = ('# Docker loopback-only development token; protect this file.\n'
               f'MCP_BEARER_TOKEN={secret}\n')
    # Exclusive create avoids overwriting a user's preexisting secrets.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    handle = os.open(target, flags, 0o600)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as file:
            file.write(content)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target

def main() -> int:
    try:
        path = initialize()
    except FileExistsError:
        print('Existing .env was not modified. Verify MCP_BEARER_TOKEN is 32+ random characters.', file=sys.stderr)
        return 1
    print(f'Created {path.name} with a strong token (not printed).')
    print('Run docker compose up --build; enter MCP_BEARER_TOKEN from .env into the Web API token field.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
