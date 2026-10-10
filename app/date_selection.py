"""Date-range candidate scan for 择日择时 with user-chosen traditional filters.

Combines the existing twelve-day officers, natal branch clash labels and
optional hour-Qimen charts. It filters and lists; it never scores luck or
ranks candidates, so the user's own criteria decide what remains.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .astronomy import chinese_lunar_date
from .engines import BirthInput, calculate_bazi
from .qimen import QimenRequest, qimen_chart
from .reference import BRANCH_CLASH
from .workflows import DayOfficerRequest, day_officer_calendar

Officer = Literal['建', '除', '满', '平', '定', '执', '破', '危', '成', '收', '开', '闭']

MAX_QIMEN_CHARTS = 40


class DateScanRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    start_date: date = Field(description='First Gregorian date (China calendar day)')
    days: int = Field(default=30, ge=1, le=93)
    include_officers: list[Officer] = Field(default_factory=list, max_length=12, description='Keep only these 建除 officers')
    exclude_officers: list[Officer] = Field(default_factory=list, max_length=12, description='Drop these 建除 officers')
    exclude_jie_boundary_days: bool = Field(default=False, description='Drop days on which a jie solar term changes the month branch')
    birth: BirthInput | None = Field(default=None, description='Optional natal chart for branch-clash labels')
    exclude_natal_clash: bool = Field(default=False, description='Drop days whose branch clashes with the natal year or day branch; requires birth')
    hours: list[str] = Field(default_factory=list, max_length=4, description='Optional local times HH:MM for hour-Qimen charts on each remaining day')
    timezone: str = Field(default='Asia/Shanghai', description='IANA timezone for the hour charts')
    max_results: int = Field(default=30, ge=1, le=60)

    @field_validator('start_date')
    @classmethod
    def supported_year(cls, value: date) -> date:
        if not 1901 <= value.year <= 2099:
            raise ValueError('Supported calendar years are 1901–2099')
        return value

    @field_validator('hours')
    @classmethod
    def valid_hours(cls, values: list[str]) -> list[str]:
        for value in values:
            if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
                raise ValueError('hours must use 24-hour HH:MM')
        if len(values) != len(set(values)):
            raise ValueError('hours cannot contain duplicates')
        return values

    @model_validator(mode='after')
    def consistent(self):
        DayOfficerRequest(start_date=self.start_date, days=self.days)  # range check up to 2099
        if set(self.include_officers) & set(self.exclude_officers):
            raise ValueError('an officer cannot be both included and excluded')
        if len(self.include_officers) != len(set(self.include_officers)) or len(self.exclude_officers) != len(set(self.exclude_officers)):
            raise ValueError('officer filters cannot contain duplicates')
        if self.exclude_natal_clash and self.birth is None:
            raise ValueError('exclude_natal_clash requires birth')
        return self


def date_candidate_scan(req: DateScanRequest) -> dict:
    calendar = day_officer_calendar(DayOfficerRequest(start_date=req.start_date, days=req.days))
    natal = None
    if req.birth is not None:
        pillars = calculate_bazi(req.birth)['pillars']
        natal = {'year': pillars['year']['branch'], 'day': pillars['day']['branch']}
    excluded = {'officer_not_included': 0, 'officer_excluded': 0, 'jie_boundary': 0, 'natal_clash': 0}
    candidates, charts, truncated = [], 0, False
    for day in calendar['days']:
        clashes = [{'with': f'natal_{key}_branch', 'natal_branch': branch, 'day_branch': day['day_branch']}
                   for key, branch in (natal or {}).items() if frozenset((branch, day['day_branch'])) in BRANCH_CLASH]
        if req.include_officers and day['officer'] not in req.include_officers:
            excluded['officer_not_included'] += 1
            continue
        if day['officer'] in req.exclude_officers:
            excluded['officer_excluded'] += 1
            continue
        if req.exclude_jie_boundary_days and day['jie_boundary_on_date']:
            excluded['jie_boundary'] += 1
            continue
        if req.exclude_natal_clash and clashes:
            excluded['natal_clash'] += 1
            continue
        if len(candidates) >= req.max_results:
            truncated = True
            break
        lunar = chinese_lunar_date(date.fromisoformat(day['date']))
        entry = {**day, 'lunar_date': {k: lunar[k] for k in ('year', 'month', 'day', 'is_leap_month')},
                 'natal_clashes': clashes, 'hour_charts': []}
        for hour in req.hours:
            if charts >= MAX_QIMEN_CHARTS:
                truncated = True
                break
            chart = qimen_chart(QimenRequest(moment=BirthInput(birth_datetime=f"{day['date']}T{hour}", timezone=req.timezone)))
            charts += 1
            entry['hour_charts'].append({key: chart[key] for key in (
                'instant', 'solar_term', 'dun', 'bureau', 'yuan', 'hour_pillar', 'zhi_fu_star', 'zhi_fu_palace',
                'zhi_shi_door', 'zhi_shi_palace', 'void_branches')} | {'local_time': hour})
        candidates.append(entry)
    return {
        'system': 'date-candidate-scan',
        'range_start': req.start_date.isoformat(),
        'requested_days': req.days,
        'criteria': {'include_officers': req.include_officers, 'exclude_officers': req.exclude_officers,
                     'exclude_jie_boundary_days': req.exclude_jie_boundary_days,
                     'exclude_natal_clash': req.exclude_natal_clash, 'natal_branches': natal,
                     'hours': req.hours, 'timezone': req.timezone},
        'candidates': candidates,
        'excluded_counts': excluded,
        'truncated': truncated,
        'order': 'chronological; no luck ranking',
        'limitations': [
            '候选日只按你选的传统标签筛选并按日期排列，没有吉凶评分，也不保证择日效果。',
            '建除值日以北京时间正午归类；交节当天前后的值日可能不同。',
            '地支六冲只对照本命年支和日支，是传统标签，不代表现实冲突。',
            f'时家奇门只覆盖时家拆补转盘一种流派，每次最多排 {MAX_QIMEN_CHARTS} 张盘。',
        ] + calendar['limitations'][2:],
    }
