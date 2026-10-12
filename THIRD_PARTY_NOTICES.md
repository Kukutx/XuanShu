# Third-party notices

## Swiss Ephemeris / pyswisseph

Dependency: `pyswisseph==2.10.3.2` (Python distribution) incorporating the Swiss Ephemeris by Dieter Koch and Alois Treindl (Astrodienst AG); Python bindings by Stanislas Marquis and contributors.

Licensing: GNU Affero General Public License, version 3 (AGPL-3.0), or separate Swiss Ephemeris Professional Edition license for commercial/proprietary usage. The dependency is **not vendored** in this project's source archive; users install it from PyPI by running `pip install -r requirements.txt`. A copy of the AGPL-3.0 text is provided in `LICENSE`. See https://www.astro.com/swisseph/ and https://github.com/astrorigin/pyswisseph.

## FastAPI / Uvicorn / Pydantic / tzdata

The project depends on these independently distributed Python packages. They are not vendored. Consult their respective license files and package metadata upon installation.

## iztro

Source: https://github.com/SylarLong/iztro · MIT License · documentation https://docs.iztro.com/quick-start.

The application does **not** import or depend on the iztro JavaScript library. It does include one table derived from iztro: the star brightness grades (庙旺得利平不陷) in `app/ziwei_extensions.py` (`BRIGHTNESS`), taken from iztro's `src/data/stars.ts` (`STARS_INFO`) and re-indexed by palace branch. That table is distributed under iztro's MIT License, reproduced below.

The evaluation script `scripts/iztro_reference.cjs` (run by `scripts/eval_crosscheck.py`) loads iztro 2.6.1 through Node.js to compare XuanShu's Zi Wei charts with it; the version is pinned in `docs/evals/package.json` and installed only on request with `npm install --prefix docs/evals`. `docs/evals/node_modules` is ignored by Git and left out of the release archive. Expected values copied from iztro's output into tests are used only as a comparator.

```text
MIT License

Copyright (c) 2023 All Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## External platform interfaces

No private APIs, accounts, credentials, code, or branding assets from tianfu-ai.com are included.

## PyJWT / cryptography (OAuth resource validation)

For optional external OAuth JWT verification, PyJWT is MIT-licensed and the
cryptography library is licensed Apache-2.0 OR BSD-3-Clause. Dependencies are
installed separately; this archive does not bundle their source or keys.

## Public traditional Qimen bureau tables

The Qimen term/bureau and nine-palace tables were cross-checked against
public traditional references including MIT-licensed
https://github.com/AbelardZ/QiMen . Our Qimen module is independently
written; it does not incorporate or invoke that repository's code.
There is no claim that the resulting full chart matches every school.

## iztro-py (optional independent expert Zi Wei provider)

Source: https://github.com/spyfree/iztro-py · MIT License.
The XuanShu source distribution **does not vendor** the package and will not install it by default. Users may choose the optional `professional` extra. This provider has not yet been run in the isolated acceptance environment; mock adapter tests cannot establish astrological accuracy or complete school coverage.
