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
    from importlib.util import find_spec
    try:
        return find_spec('iztro_py') is not None
    except (ModuleNotFoundError, ValueError):
        return False


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
        raise ValueError('Optional local provider unavailable: install `pip install "xuanshu[professional]"`. No approximate chart was substituted.') from exc
    normalized = normalized_dt(req.birth)
    effective, time_basis_meta = time_basis(normalized, req.birth.time_mode, req.birth.longitude)
    # iztro uses 0=early Rat (00-00:59), 1=Ox (01-02:59), ...
    # 12=late Rat (23-23:59). XuanShu's year/month/day convention stays explicit.
    hour_index = 12 if effective.hour == 23 else (effective.hour + 1)//2
    try:
        original = astro.by_solar(f'{effective.year}-{effective.month}-{effective.day}',
                                  hour_index, '男' if req.birth.gender == 'male' else '女',
                                  req.birth.leap_month_second_half_as_next, 'zh-CN')
        natal = _encode_safe(original)
        horoscope = None
        if req.target_date is not None:
            target_hour_index = 12 if req.target_hour == 23 else (req.target_hour + 1)//2
            horoscope = _encode_safe(original.horoscope(
                f'{req.target_date.year}-{req.target_date.month}-{req.target_date.day}',
                target_hour_index))
    except (ValueError, TypeError, AttributeError, RuntimeError) as exc:
        raise ValueError(f'Professional Zi Wei provider calculation failed: {exc}') from exc
    return {
        'system': 'ziwei-professional', 'provider': 'iztro-py',
        'provenance': 'https://github.com/spyfree/iztro-py',
        'license': 'MIT', 'profile': 'iztro-compatible',
        'birth_datetime': normalized.isoformat(),
        'effective_calendar_date': effective.date().isoformat(),
        'time_index': hour_index, 'time_basis': time_basis_meta,
        'natal': natal, 'horoscope': horoscope,
        'target_date': req.target_date.isoformat() if req.target_date else None,
        'notes': [
            '此结果由用户选择安装的独立 iztro-py 引擎生成，与 XuanShu 原生子集分开输出。',
            '流派版本、闰月习惯和动态盘字段以实际安装的提供方为准；未通过逐星独立认证。',
            '传统文化规则不具有已验证的现实预测效力。',
        ],
    }
