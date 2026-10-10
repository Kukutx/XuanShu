"""Bundle required runtime assets into the installable Python distribution.

The source ZIP/Docker layout keeps top-level ``static``, ``docs/rules``, and
``skills`` as the only editable sources. Packaging copies them into the wheel's
``app/_resources`` at build time, without creating a second editable source.
"""
from pathlib import Path
from shutil import copytree, rmtree

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithAssets(build_py):
    def run(self):
        super().run()
        root = Path(__file__).resolve().parent
        out = Path(self.build_lib) / 'app' / '_resources'
        if out.exists():
            rmtree(out)
        for relative in (Path('static'), Path('docs/rules'), Path('docs/research'), Path('examples'), Path('skills')):
            source = root / relative
            if not source.is_dir():
                raise RuntimeError(f'Missing required build assets: {relative}')
            copytree(source, out / relative, dirs_exist_ok=True, ignore=None)


setup(cmdclass={'build_py': BuildWithAssets})
