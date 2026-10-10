"""Life Path retrospective: user-reported events beside traditional time labels.

Each past event is placed next to the BaZi decade period (大运), the solar
year pillar (流年, 立春 boundary), the named lunar year's Zi Wei stem
transformations and the traditional branch relations with the natal chart.
This shows structural co-occurrence only; it does not validate the system or
imply that the labels caused the events.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .advanced import DayunRequest, dayun_sequence
from .astronomy import chinese_lunar_date
from .engines import BirthInput, calculate_bazi
from .features import AnnualRequest, annual_transformations
from .reference import BRANCH_CLASH, BRANCH_HARMONY

class LifeEvent(BaseModel):
    """A user-reported past event used as an anchor for retrospective review."""
    model_config = ConfigDict(extra='forbid')
    date: date
    title: str = Field(min_length=1, max_length=80)
    note: str = Field(default='', max_length=300)


PILLAR_NAMES = {'year': '年支', 'month': '月支', 'day': '日支', 'hour': '时支'}


class LifePathRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    events: list[LifeEvent] = Field(min_length=1, max_length=30)
    dayun_direction_override: Literal['forward', 'reverse'] | None = None

    @model_validator(mode='after')
    def events_after_birth(self):
        born = datetime.fromisoformat(self.birth.birth_datetime).date()
        for event in self.events:
            if event.date < born or event.date.year > 2099:
                raise ValueError('event dates must fall between the birth date and 2099-12-31')
        return self


def _relations(branch: str, natal: dict[str, str]) -> list[dict]:
    found = []
    for key, natal_branch in natal.items():
        pair = frozenset((branch, natal_branch))
        if branch == natal_branch:
            found.append({'type': '同支', 'with': PILLAR_NAMES[key], 'natal_branch': natal_branch})
        elif pair in BRANCH_CLASH:
            found.append({'type': '六冲', 'with': PILLAR_NAMES[key], 'natal_branch': natal_branch})
        elif pair in BRANCH_HARMONY:
            found.append({'type': '六合', 'with': PILLAR_NAMES[key], 'natal_branch': natal_branch})
    return found


def life_path_review(req: LifePathRequest) -> dict:
    natal_chart = calculate_bazi(req.birth)
    natal = {key: natal_chart['pillars'][key]['branch'] for key in PILLAR_NAMES}
    notes = []
    periods = None
    if req.birth.gender != 'unspecified' or req.dayun_direction_override:
        periods = dayun_sequence(DayunRequest(birth=req.birth, periods=12,
                                              direction_override=req.dayun_direction_override))['periods']
    else:
        notes.append('未指定性别或大运顺逆，省略大运对照（方向不会被猜测）。')
    born = datetime.fromisoformat(req.birth.birth_datetime).date()
    rows = []
    for event in sorted(req.events, key=lambda e: e.date):
        noon = BirthInput(birth_datetime=f'{event.date.isoformat()}T12:00', timezone=req.birth.timezone)
        year_pillar = calculate_bazi(noon)['pillars']['year']['text']
        lunar_year = chinese_lunar_date(event.date)['year']
        annual = annual_transformations(AnnualRequest(birth=req.birth, lunar_year=lunar_year))
        dayun = None
        if periods is not None:
            moment = event.date.isoformat()
            period = next((p for p in periods if p['approx_start_local'][:10] <= moment < p['approx_end_local_exclusive'][:10]), None)
            if period is not None:
                dayun = {'sequence': period['sequence'], 'pillar': period['pillar'],
                         'approx_start_local': period['approx_start_local'], 'branch_relations': _relations(period['pillar'][-1], natal)}
            elif moment < periods[0]['approx_start_local'][:10]:
                dayun = {'sequence': 0, 'pillar': '起运前', 'approx_start_local': None, 'branch_relations': []}
        rows.append({
            'date': event.date.isoformat(), 'title': event.title, 'note': event.note,
            'age_years_civil': round((event.date - born).days / 365.2425, 2),
            'nominal_age_xusui': lunar_year - chinese_lunar_date(born)['year'] + 1,
            'solar_year_pillar': year_pillar,
            'solar_year_branch_relations': _relations(year_pillar[-1], natal),
            'lunar_year': lunar_year,
            'annual_transformations': annual['transformations'],
            'dayun': dayun,
        })
    return {
        'system': 'life-path-event-review',
        'natal_pillars': {key: natal_chart['pillars'][key]['text'] for key in PILLAR_NAMES},
        'events': rows,
        'notes': notes,
        'limitations': [
            '人生事件由用户提供，未经核实；本工具只把事件日期与传统时间标签并列，不声称因果，也不验证命理的预测效力。',
            '流年干支以立春为界、按事件当日正午计算；紫微年度四化按农历命名年，两者年界不同。',
            '大运区间是名义起运年龄的公历近似投影，交运日前后的事件归属可能有误差。',
            '紫微四化采用全书系十干四化映射，不是完整流年命盘。',
        ],
    }
