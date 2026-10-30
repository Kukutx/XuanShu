"""Opt-in expert Zi Wei provider adapter with explicit provenance.

Uses the independent MIT-licensed ``iztro-py`` package instead of silently
claiming that XuanShu's bounded natal formulas are a complete school chart.
The dependency is optional: there is no network call, hosted AI, or key.
"""
from __future__ import annotations

from datetime import date
from importlib import import_module
from typing import Any

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .engines import BirthInput, normalized_dt
from .timebasis import time_basis


class ProfessionalZiweiRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    target_date: date | None = Field(default=None, description='Optional Gregorian day for annual/monthly/daily horoscope overlays')
    target_hour: int = Field(default=12, ge=0, le=23, description='Optional local clock hour (0–23) for hourly horoscope')

    @model_validator(mode='after')
    def validate_target(self):
        if self.target_date is not None and not (1901 <= self.target_date.year <= 2099):
            raise ValueError('target_date must be between 1901 and 2099')
        if self.birth.gender not in ('male', 'female'):
            raise ValueError('Professional school requires gender (male/female) for traditional major-cycle direction')
        return self


def professional_provider_available() -> bool:
    """True only when the provider imports, so an installed but broken copy is not reported as ready."""
    from importlib.util import find_spec
    try:
        if find_spec('iztro_py') is None:
            return False
        import_module('iztro_py')
    except Exception:  # any failure while importing a third-party package means it is not usable
        return False
    return True


# Where iztro-py keeps each kind of internal key in its own locale tables (``iztro_py.i18n``).
_KEY_SECTIONS = ('stars.major.', 'stars.minor.', 'palaces.', 'heavenlyStem.', 'earthlyBranch.', '')
# Fields that carry one internal key, and fields that carry a list of them, in iztro-py's dumps (snake or camel case).
_NAME_FIELDS = frozenset({'name', 'soul', 'body', 'heavenly_stem', 'earthly_branch', 'heavenlyStem', 'earthlyBranch',
                          'earthly_branch_of_soul_palace', 'earthly_branch_of_body_palace', 'earthlyBranchOfSoulPalace',
                          'earthlyBranchOfBodyPalace', 'year_stem', 'year_branch', 'month_stem', 'month_branch', 'day_stem',
                          'day_branch', 'time_stem', 'time_branch'})
_NAME_LIST_FIELDS = frozenset({'palace_names', 'palaceNames', 'mutagen'})


def _provider_names():
    """The provider's own zh-CN translator for its internal keys (ziweiMaj, soulPalace, ziEarthly, ...).

    iztro-py 0.5 dumps names as keys and translates them only through its own locale; XuanShu uses that locale rather
    than a table of its own, and leaves a value untouched when the installed version has no translation for it."""
    try:
        translate = import_module('iztro_py.i18n').t
    except (ImportError, AttributeError):
        return lambda value: value

    def name(value: Any) -> Any:
        if not isinstance(value, str) or not value.isascii() or not value:
            return value
        for section in _KEY_SECTIONS:
            try:
                found = translate(section + value, 'zh-CN')
            except (KeyError, ValueError, TypeError):
                continue
            if isinstance(found, str) and found and found != section + value:
                return found
        return value
    return name


def _chinese_names(data: Any, name) -> Any:
    """Translate the name, stem and branch fields of a dumped chart or horoscope, keeping everything else as given."""
    if isinstance(data, list):
        return [_chinese_names(item, name) for item in data]
    if not isinstance(data, dict):
        return data
    out = {}
    for key, value in data.items():
        if key in _NAME_FIELDS and isinstance(value, str):
            out[key] = name(value)
        elif key in _NAME_LIST_FIELDS and isinstance(value, list):
            out[key] = [name(item) for item in value]
        else:
            out[key] = _chinese_names(value, name)
    return out


def _time_index(hour: int, rollover: bool) -> int:
    """iztro's time index for a clock hour: 0 early Zi (00:00–00:59), 1 丑 … 11 亥, 12 late Zi (23:00–23:59).

    23:00–23:59 follows the birth's own day-change setting: without the 23:00 day change XuanShu keeps that
    calendar day, which is iztro's early Zi (0); with it the next day, iztro's late Zi (12). docs/evals/README.md
    records both pairings against iztro."""
    if hour == 23:
        return 12 if rollover else 0
    return (hour + 1) // 2


def _encode_safe(obj: Any) -> Any:
    """Convert package Pydantic/data classes to protocol-safe plain JSON."""
    if hasattr(obj, 'model_dump') and callable(obj.model_dump):
        obj = obj.model_dump(mode='json', exclude_none=True)
    return jsonable_encoder(obj, exclude_none=True)


def professional_ziwei_chart(req: ProfessionalZiweiRequest) -> dict:
    """Full vendor-generated structure, never silently substituted by natal subset."""
    try:
        astro = import_module('iztro_py').astro
    except ImportError as exc:
        # The project is not published on PyPI, so the advice names the provider package itself (or the
        # project's own extra from a source checkout), never a `xuanshu[...]` download someone else could own.
        raise ValueError('Optional local provider unavailable: install it into the Python environment that runs XuanShu with '
                         '`python -m pip install "iztro-py>=0.1,<1"` (or `python -m pip install ".[professional]"` in the source folder). '
                         'No approximate chart was substituted.') from exc
    normalized = normalized_dt(req.birth)
    effective, time_basis_meta = time_basis(normalized, req.birth.time_mode, req.birth.longitude)
    rollover = req.birth.late_zi_day_rollover
    hour_index = _time_index(effective.hour, rollover)
    name = _provider_names()
    try:
        original = astro.by_solar(f'{effective.year}-{effective.month}-{effective.day}',
                                  hour_index, '男' if req.birth.gender == 'male' else '女',
                                  req.birth.leap_month_second_half_as_next, 'zh-CN')
        natal = _chinese_names(_encode_safe(original), name)
        horoscope = None
        target_hour_index = None
        if req.target_date is not None:
            target_hour_index = _time_index(req.target_hour, rollover)
            horoscope = _chinese_names(_encode_safe(original.horoscope(
                f'{req.target_date.year}-{req.target_date.month}-{req.target_date.day}',
                target_hour_index)), name)
    except (ValueError, TypeError, AttributeError, RuntimeError) as exc:
        raise ValueError(f'Professional Zi Wei provider calculation failed: {exc}') from exc
    return {
        'system': 'ziwei-professional', 'provider': 'iztro-py',
        'provenance': 'https://github.com/spyfree/iztro-py',
        'license': 'MIT', 'profile': 'iztro-compatible',
        'birth_datetime': normalized.isoformat(),
        'effective_calendar_date': effective.date().isoformat(),
        'time_index': hour_index, 'time_basis': time_basis_meta,
        'late_zi_rule': 'next_day' if rollover else 'same_day',
        'target_time_index': target_hour_index,
        'natal': natal, 'horoscope': horoscope,
        'target_date': req.target_date.isoformat() if req.target_date else None,
        'target_hour': req.target_hour if req.target_date else None,
        'notes': [
            '此结果由用户选择安装的独立 iztro-py 引擎生成，与 XuanShu 原生子集分开输出。',
            '流派版本、闰月习惯和动态盘字段以实际安装的提供方为准；未通过逐星独立认证。',
            '星名、宫名和干支按提供方自带的简体中文语言表从内部键名转成中文，其余字段保持提供方原样。',
            '23:00–23:59 按出生资料的「23:00 换日」设置：换日用 iztro 的晚子时（序号 12），不换日用早子时（序号 0）。',
            '传统文化规则不具有已验证的现实预测效力。',
        ],
    }
