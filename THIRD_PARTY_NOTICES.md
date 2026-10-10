# Third-party notices

## Swiss Ephemeris / pyswisseph

Dependency: `pyswisseph==2.10.3.2` (Python distribution) incorporating the Swiss Ephemeris by Dieter Koch and Alois Treindl (Astrodienst AG); Python bindings by Stanislas Marquis and contributors.

Licensing: GNU Affero General Public License, version 3 (AGPL-3.0), or separate Swiss Ephemeris Professional Edition license for commercial/proprietary usage. The dependency is **not vendored** in this project's source archive; users install it from PyPI by running `pip install -r requirements.txt`. A copy of the AGPL-3.0 text is provided in `LICENSE`. See https://www.astro.com/swisseph/ and https://github.com/astrorigin/pyswisseph.

## FastAPI / Uvicorn / Pydantic / tzdata

The project depends on these independently distributed Python packages. They are not vendored. Consult their respective license files and package metadata upon installation.

## iztro

This repository does **not** package or import the iztro JavaScript library; its publicly documented expected outputs are used only as a comparator for tests. Source: https://docs.iztro.com/quick-start.

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
