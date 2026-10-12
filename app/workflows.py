"""Independent, reproducible cultural-date and decision-support workflows.

These modules are deliberately not a clone or client of any third-party service.
They do not assert auspiciousness, compatibility or real-world predictive power.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .astronomy import CHINA, jie_neighbors, solar_month_offset
from .engines import BRANCHES, STEMS, PALACE_NAMES, BirthInput, calculate_ziwei
from .features import _day_pillar
from .reference import FOUR_TRANSFORMATIONS, FOUR_TYPES, TRANSFORMATION_SCHOOL


DAY_OFFICERS = tuple('建除满平定执破危成收开闭')


class DayOfficerRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    start_date: date = Field(description='Gregorian date in Asia/Shanghai, 1901–2099')
    days: int = Field(default=14, ge=1, le=93)
    filter_officers: list[Literal['建','除','满','平','定','执','破','危','成','收','开','闭']] = Field(default_factory=list, max_length=12)

    @field_validator('start_date')
    @classmethod
    def supported_year(cls, value: date) -> date:
        if value.year < 1901 or value.year > 2099:
            raise ValueError('Supported calendar years are 1901–2099')
        return value

    @model_validator(mode='after')
    def check_range(self):
        if (self.start_date + timedelta(days=self.days - 1)).year > 2099:
            raise ValueError('Date range cannot extend past 2099-12-31')
        if len(self.filter_officers) != len(set(self.filter_officers)):
            raise ValueError('filter_officers cannot contain duplicates')
        return self


@lru_cache(maxsize=256)
def _solar_month_branch(day: date, hour: int) -> int:
    """Solar-term month boundary based on exact modeled jie event instants.

    The 12 jie start at solar longitude 315° (立春 / 寅 month).
    The boundary hour is explicitly sampled; month changes can split a date.
    """
    moment = datetime.combine(day, time(hour=hour), tzinfo=CHINA)
    month_offset = solar_month_offset(moment)
    return (2 + month_offset) % 12


def _jie_boundary_on(day: date) -> bool:
    """True when a jie instant falls anywhere in [00:00, 24:00) China time."""
    start = datetime.combine(day, time(), tzinfo=CHINA)
    end = start + timedelta(days=1) - timedelta(microseconds=1)
    return solar_month_offset(start) != solar_month_offset(end)


def _jie_on(day: date, day_branch: str) -> dict | None:
    """The jie falling on a China date, and the month branch and officer on either side of it."""
    start = datetime.combine(day, time(), tzinfo=CHINA)
    end = start + timedelta(days=1) - timedelta(microseconds=1)
    if solar_month_offset(start) == solar_month_offset(end):
        return None
    _, (name, instant) = jie_neighbors(start)
    before, after = (2 + solar_month_offset(start)) % 12, (2 + solar_month_offset(end)) % 12
    officer = lambda month: DAY_OFFICERS[(BRANCHES.index(day_branch) - month) % 12]
    return {'name': name, 'time_china': instant.astimezone(CHINA).isoformat(timespec='minutes'),
            'month_branch_before': BRANCHES[before], 'officer_before': officer(before),
            'month_branch_after': BRANCHES[after], 'officer_after': officer(after)}


def day_officer_calendar(request: DayOfficerRequest) -> dict:
    """Label dates by 建除十二值日 without claiming luck or offering 宜忌."""
    days = []
    for i in range(request.days):
        current = request.start_date + timedelta(days=i)
        noon_month = _solar_month_branch(current, 12)
        day_pillar = _day_pillar(current)
        day_branch = day_pillar[-1]
        officer = DAY_OFFICERS[(BRANCHES.index(day_branch) - noon_month) % 12]
        if request.filter_officers and officer not in request.filter_officers:
            continue
        days.append({
            'date': current.isoformat(),
            'day_pillar': day_pillar,
            'month_branch_at_noon': BRANCHES[noon_month],
            'day_branch': day_branch,
            'officer': officer,
            'jie_boundary_on_date': _jie_boundary_on(current),
            # On a jie day: the term, its China time, and the officer before and after it (the noon one is listed above).
            'jie_on_date': _jie_on(current, day_branch),
        })
    return {
        'system': 'jianchu-twelve-day-officers',
        'timezone': 'Asia/Shanghai',
        'range_start': request.start_date.isoformat(),
        'requested_days': request.days,
        'filter_officers': request.filter_officers,
        'days': days,
        'method': 'twelve-jie-month-branch + sexagenary-day-branch at China noon',
        'limitations': [
            '十二值日是传统历法标签，不构成吉凶评分、黄历宜忌或择日保证。',
            '交节当天节令切换前后的值日不同：本表按北京时间正午归类，交节当天另给出交节时刻和节后的值日；精确活动时间要对照交节时刻。',
            '本模型不声称为任何特定流派的完整黄历择日法。',
        ],
    }


class TimelineRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    start_lunar_year: int = Field(ge=1901, le=2099)
    years: int = Field(default=10, ge=1, le=30)
    focus_palace: str | None = None

    @model_validator(mode='after')
    def valid_range(self):
        if self.start_lunar_year + self.years - 1 > 2099:
            raise ValueError('Annual sequence exceeds 2099')
        if self.focus_palace is not None and self.focus_palace not in PALACE_NAMES:
            raise ValueError('focus_palace must be one of the 12 Zi Wei palace names')
        return self


def annual_timeline(request: TimelineRequest) -> dict:
    """Reuse one natal chart across consecutive *named lunar years*."""
    chart = calculate_ziwei(request.birth)
    ming_idx = BRANCHES.index(chart['ming_palace'])
    occurrence_count = {name: 0 for name in PALACE_NAMES}
    entries = []
    for year in range(request.start_lunar_year, request.start_lunar_year + request.years):
        stem = STEMS[(year - 1984) % 10]
        branch = BRANCHES[(year - 1984) % 12]
        overlays = []
        for label, star in zip(FOUR_TYPES, FOUR_TRANSFORMATIONS[stem]):
            target_branch = chart['star_positions'][star]
            palace = PALACE_NAMES[(ming_idx - BRANCHES.index(target_branch)) % 12]
            occurrence_count[palace] += 1
            overlays.append({'type': label, 'star': star, 'natal_palace': palace,
                             'natal_branch': target_branch})
        entries.append({'lunar_year': year, 'year_pillar': stem + branch,
                        'transformations': overlays,
                        'focus_hits': [t for t in overlays if t['natal_palace'] == request.focus_palace]
                        if request.focus_palace else []})
    return {
        'system': 'annual-four-transformations-timeline',
        'start_lunar_year': request.start_lunar_year,
        'years': request.years,
        'focus_palace': request.focus_palace,
        'natal_ming_palace': chart['ming_palace'],
        'school': TRANSFORMATION_SCHOOL,
        'entries': entries,
        'natal_palace_label_counts': occurrence_count,
        'limitations': [
            '年份按农历命名年，不从公历一月一日开始；春节、节令附近须核对时间归属。',
            '只对照每年天干四化星到本命宫的映射，不含真正的流年命宫、限运、流月或流曜。',
            '各宫出现次数不是吉凶评分或事件发生概率，不预测现实变化。',
        ],
    }


class DecisionCriterion(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=40)
    weight: float = Field(gt=0, le=100)

    @field_validator('weight', mode='before')
    @classmethod
    def reject_boolean_weight(cls, value):
        if isinstance(value, bool):
            raise ValueError('weight cannot be a boolean')
        return value

    @field_validator('name')
    @classmethod
    def no_blank(cls, v):
        if not v.strip():
            raise ValueError('criterion name cannot be blank')
        return v.strip()


class DecisionOption(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=80)
    ratings: dict[str, float] = Field(description='0–5 user ratings keyed by criterion name')

    @field_validator('ratings', mode='before')
    @classmethod
    def reject_boolean_ratings(cls, value):
        if not isinstance(value, dict) or any(isinstance(v, bool) for v in value.values()):
            raise ValueError('ratings must be numeric values, not booleans')
        return value

    @field_validator('name')
    @classmethod
    def no_blank(cls, v):
        if not v.strip():
            raise ValueError('option name cannot be blank')
        return v.strip()


class DecisionMatrixRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=3, max_length=300)
    criteria: list[DecisionCriterion] = Field(min_length=1, max_length=8)
    options: list[DecisionOption] = Field(min_length=2, max_length=8)

    @field_validator('question')
    @classmethod
    def non_blank_question(cls, value):
        if not value.strip():
            raise ValueError('question cannot be blank')
        return value.strip()

    @model_validator(mode='after')
    def valid_matrix(self):
        criterion_names = [c.name for c in self.criteria]
        option_names = [o.name for o in self.options]
        if len(set(n.casefold() for n in criterion_names)) != len(criterion_names):
            raise ValueError('Criterion names must be unique')
        if len(set(n.casefold() for n in option_names)) != len(option_names):
            raise ValueError('Option names must be unique')
        for opt in self.options:
            if set(opt.ratings) != set(criterion_names):
                raise ValueError(f'{opt.name}: rating keys must match criteria exactly')
            if any(isinstance(v, bool) or not 0 <= v <= 5 for v in opt.ratings.values()):
                raise ValueError(f'{opt.name}: each rating must be from 0 to 5')
        return self


def decision_matrix(request: DecisionMatrixRequest) -> dict:
    """Transparent, user-specified weighted scoring; never occult prediction."""
    total = sum(c.weight for c in request.criteria)
    weights = {c.name: c.weight / total for c in request.criteria}
    computed = []
    for position, option in enumerate(request.options):
        contributions = [
            {'criterion': c.name, 'rating': option.ratings[c.name],
             'normalized_weight': round(weights[c.name], 8),
             'weighted_contribution': round(weights[c.name] * option.ratings[c.name], 8)}
            for c in request.criteria
        ]
        score = sum(x['rating'] * weights[x['criterion']] for x in contributions)
        computed.append({'name': option.name, 'score': round(score, 6), 'contributions': contributions,
                         '_raw_score': score, '_position': position})
    computed.sort(key=lambda r: (-r['_raw_score'], r['_position']))
    top_score = computed[0]['_raw_score']
    leaders = [r['name'] for r in computed if abs(r['_raw_score'] - top_score) < 1e-9]
    # Leave-one-criterion-out checks whether the score leader depends on one criterion.
    sensitivity = []
    if len(request.criteria) > 1:
        for omitted in request.criteria:
            remaining = [c for c in request.criteria if c.name != omitted.name]
            sum_remaining = sum(c.weight for c in remaining)
            rank = sorted(((sum(c.weight * o.ratings[c.name] for c in remaining) / sum_remaining, o.name)
                           for o in request.options), reverse=True)
            first_score = rank[0][0]
            winners = sorted(name for score, name in rank if abs(score - first_score) < 1e-9)
            sensitivity.append({'omitted_criterion': omitted.name,
                                'leaders_without_it': winners,
                                'leader_changed': set(winners) != set(leaders)})
    for row in computed:
        del row['_raw_score'], row['_position']
    return {
        'system': 'transparent-decision-matrix',
        'question': request.question,
        'criteria': [{'name': c.name, 'raw_weight': c.weight,
                      'normalized_weight': round(weights[c.name], 8)} for c in request.criteria],
        'ranked_options': computed,
        'joint_leaders': sorted(leaders),
        'leave_one_out_sensitivity': sensitivity,
        'limitations': [
            '所有数值来自用户输入的主观评分与权重；排序不是客观真理、概率或现实结果预测。',
            '方案结果不引用命理术数；现实重大决策应另行核对事实、成本、法律、安全与专业意见。',
        ],
    }
