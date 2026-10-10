"""Field-by-field Qimen plate comparison with explicit external evidence.

This is a tool for validating reported plates, NOT evidence that all schools
produce the same result. Only compare fields the reference actually provides.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .engines import BirthInput
from .qimen import QimenRequest, qimen_chart

ROOT_FIELDS = frozenset(('solar_term','dun','bureau','yuan','day_pillar','hour_pillar',
                         'zhi_fu_star','zhi_fu_palace','zhi_fu_origin','zhi_shi_door',
                         'zhi_shi_palace','zhi_shi_raw_palace','xun_head','xun_instrument'))
PALACE_FIELDS = frozenset(('trigram','direction','earth_stem','heaven_stem',
                           'dark_stem','star','door','deity','void','center_lodged_here'))


class QimenReferencePalace(BaseModel):
    model_config = ConfigDict(extra='forbid')
    number: int = Field(ge=1, le=9)
    earth_stem: str | None = None
    heaven_stem: str | None = None
    dark_stem: str | None = None
    star: str | None = None
    door: str | None = None
    deity: str | None = None
    void: bool | None = None
    center_lodged_here: bool | None = None
    trigram: str | None = None
    direction: str | None = None


class QimenAuditRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    moment: BirthInput
    reference_source: str = Field(min_length=4, max_length=512,
        description='Full citation or identifier of independently obtained reference chart')
    reference_school: str = Field(min_length=2, max_length=120)
    root_fields: dict[str, Any] = Field(default_factory=dict)
    palaces: list[QimenReferencePalace] = Field(default_factory=list, max_length=9)

    @model_validator(mode='after')
    def validate_audit_fields(self):
        if set(self.root_fields) - ROOT_FIELDS:
            raise ValueError('Unknown Qimen root comparison fields')
        if any(type(v) not in (str, int) for v in self.root_fields.values()):
            raise ValueError('Qimen reference root values must be strings or integers')
        if len({p.number for p in self.palaces}) != len(self.palaces):
            raise ValueError('Each reference palace must be unique')
        if not self.root_fields and not any(getattr(p, field) is not None
                                            for p in self.palaces
                                            for field in p.model_fields_set - {'number'}):
            raise ValueError('Provide at least one reference field to audit')
        return self


def qimen_reference_audit(req: QimenAuditRequest) -> dict:
    calc = qimen_chart(QimenRequest(moment=req.moment))
    ours = {p['number']: p for p in calc['palaces']}
    compared = []
    def append(path: str, local: Any, reference: Any):
        compared.append({'field': path, 'ours': local, 'reference': reference, 'match': local == reference})
    for key in sorted(req.root_fields):
        append(key, calc[key], req.root_fields[key])
    for palace in sorted(req.palaces, key=lambda x:x.number):
        for key in sorted(palace.model_fields_set - {'number'}):
            reference = getattr(palace, key)
            # Explicit JSON null cannot assert a supplied, verifiable value.
            if reference is None:
                continue
            append(f'palaces.{palace.number}.{key}', ours[palace.number][key], reference)
    mismatches = [p for p in compared if not p['match']]
    return {'system':'qimen-reference-audit','reference_source':req.reference_source,
            'reference_school':req.reference_school,
            'local_school':calc['method'], 'compared':len(compared),
            'matching':len(compared)-len(mismatches), 'mismatches':mismatches,
            'matches':not mismatches,
            'comparison_scope': sorted({p['field'].split('.')[-1] for p in compared}),
            'notes':['只校验实际给出的字段；未提供的逐宫字段不计为一致。',
                     '不同流派和节令日界可能产生合法差异；请逐字段核对。',
                     '参考来源由用户提供，工具不自动认证该来源的权威性。']}
