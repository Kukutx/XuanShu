#!/usr/bin/env python3
"""Create and validate a deterministic source ZIP with per-file SHA-256 hashes.

Usage:
    python scripts/build_release.py
    python scripts/build_release.py --verify ../xuanshu-v.0.1.0.zip

Deliberately excludes secrets, caches, local environments, bytecode and Git.
"""
from __future__ import annotations

import argparse
import re
import hashlib
from pathlib import Path
import sys
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = ROOT.name
DEFAULT_ZIP = ROOT.parent / 'xuanshu-v.0.1.0.zip'
FROZEN_VERSION = '0.1.0'
DISPLAY_VERSION = 'v.0.1.0'
MANIFEST = 'RELEASE_MANIFEST.sha256'
SKIP_DIRS = {'.git', '.venv', '.artifacts', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'node_modules', 'dist', 'build', '.tox', 'xuanshu.egg-info', '.venv-py313-backup'}
SKIP_NAMES = {'.env', '.DS_Store', 'Thumbs.db', MANIFEST}
SKIP_SUFFIXES = {'.pyc', '.pyo', '.pyd', '.zip', '.log', '.tmp', '.pem', '.key', '.p12', '.pfx', '.sqlite', '.db'}
FIXED_TIMESTAMP = (2026, 10, 9, 0, 0, 0)


def validate_release_metadata(root: Path = ROOT) -> None:
    """Prevent a successful archive build when user-facing version text is stale.

    This is intentionally a stdlib-only preflight so releases can be checked
    even before runtime dependencies are installed. It does not replace tests.
    """
    version = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    if version != FROZEN_VERSION:
        raise ValueError(f'Project version is frozen at {FROZEN_VERSION}, not {version}')
    module = (root / 'app' / '__init__.py').read_text(encoding='utf-8')
    if f"__version__ = '{FROZEN_VERSION}'" not in module or f"__display_version__ = '{DISPLAY_VERSION}'" not in module:
        raise ValueError(f'Module version does not match pyproject.toml {version}')
    for relative in ('README.md', 'TEST_REPORT.md', 'CHANGELOG.md'):
        text = (root / relative).read_text(encoding='utf-8')
        if DISPLAY_VERSION not in '\n'.join(text.splitlines()[:5]):
            raise ValueError(f'Stale release metadata: {relative} is missing v{version} at its top')
    html = (root / 'static' / 'index.html').read_text(encoding='utf-8')
    if f'玄枢 · XuanShu {DISPLAY_VERSION}' not in html:
        raise ValueError('Stale Web UI version marker')
    if tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))['project']['name'] != 'xuanshu':
        raise ValueError('Unexpected project package name')
    if re.search(r'\bv\d+\.\d+\.\d+\b', html):
        raise ValueError('Stale Web UI version marker')


def is_excluded(relative: Path) -> bool:
    """Fail closed for build caches, QA artifacts and local secrets."""
    return (any(part in SKIP_DIRS for part in relative.parts)
            or relative.name in SKIP_NAMES
            or (relative.name.startswith('.env.') and relative.name != '.env.example')
            or relative.suffix in SKIP_SUFFIXES)


def eligible(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return path.is_file() and not path.is_symlink() and not is_excluded(relative)


def source_files() -> list[Path]:
    for path in ROOT.rglob('*'):
        if path.is_symlink():
            raise ValueError(f'Release refuses symbolic links: {path}')
    return sorted((p for p in ROOT.rglob('*') if eligible(p)), key=lambda p: p.relative_to(ROOT).as_posix())


def hash_content(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def construct_manifest(files: list[Path]) -> bytes:
    return ''.join(f'{hash_content(path.read_bytes())}  {path.relative_to(ROOT).as_posix()}\n'
                   for path in files).encode('utf-8')


def add_file(archive: zipfile.ZipFile, path_in_zip: str, content: bytes, executable: bool = False):
    info = zipfile.ZipInfo(path_in_zip, date_time=FIXED_TIMESTAMP)
    info.create_system = 3
    info.external_attr = ((0o100755 if executable else 0o100644) << 16)
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build(output: Path):
    validate_release_metadata(ROOT)
    files = source_files()
    if not files:
        raise ValueError('No source files found')
    manifest = construct_manifest(files)
    (ROOT / MANIFEST).write_bytes(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.is_relative_to(ROOT):
        raise ValueError('Archive must be outside source directory')
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            add_file(archive, f'{PREFIX}/{relative}', path.read_bytes(), path.suffix in {'.sh', '.py'} and path.name in {'start.sh', 'build_release.py'})
        add_file(archive, f'{PREFIX}/{MANIFEST}', manifest)
    print(f'Built {output} ({len(files) + 1} files, {output.stat().st_size:,} bytes)')
    verify(output)


def verify(path: Path):
    if not path.is_file():
        raise ValueError(f'Archive missing: {path}')
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise ValueError(f'Corrupt archive entry: {bad}')
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate file entries')
        manifest_path = f'{PREFIX}/{MANIFEST}'
        if manifest_path not in names:
            raise ValueError('Missing release manifest')
        entries = {}
        for line in archive.read(manifest_path).decode('utf-8').splitlines():
            hash_, separator, name = line.partition('  ')
            if (separator != '  ' or len(hash_) != 64 or any(c not in '0123456789abcdef' for c in hash_)
                    or not name or name.startswith('/') or '\\' in name or any(part in ('.', '..') for part in name.split('/'))):
                raise ValueError(f'Invalid manifest entry: {line}')
            if is_excluded(Path(name)):
                raise ValueError(f'Forbidden release entry: {name}')
            if name in entries:
                raise ValueError(f'Duplicate manifest entry: {name}')
            entries[name] = hash_
        expected = {f'{PREFIX}/{entry}' for entry in entries} | {manifest_path}
        if set(names) != expected:
            raise ValueError(f'Archive/manifest file mismatch: missing={expected-set(names)}, extra={set(names)-expected}')
        for name, hash_ in entries.items():
            if hash_content(archive.read(f'{PREFIX}/{name}')) != hash_:
                raise ValueError(f'Checksum mismatch: {name}')
    print(f'Verified {len(names)} files, SHA-256 manifest and ZIP CRC: {path}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_ZIP)
    parser.add_argument('--verify', type=Path, help='Verify an existing ZIP instead of packaging')
    args = parser.parse_args()
    try:
        if args.verify:
            verify(args.verify.resolve())
        else:
            build(args.output.resolve())
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        print(f'RELEASE ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
