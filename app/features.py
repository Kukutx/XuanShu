"""Auditable cultural comparison, calendar exploration, and palace lookup.

No luck scores, compatibility rankings, or predictions are produced.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .astronomy import CHINA, from_jd, solar_term_jd, TERMS, chinese_lunar_date
from .engines import BirthInput, calculate_bazi, calculate_ziwei, STEMS, BRANCHES
from .festivals import day_marks, lunar_or_rollover
from .reference import BRANCH_HARMONY, BRANCH_CLASH, PALACE_TOPICS


class CalendarRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    start_date: date = Field(description='Gregorian date YYYY-MM-DD, interpreted in China standard time')
    days: int = Field(default=14, ge=1, le=31, description='Number of consecutive days (1 to 31)')

    @field_validator('start_date')
    @classmethod
    def supported_day(cls, value: date) -> date:
        if not 1901 <= value.year <= 2099:
            raise ValueError('Gregorian date must be between 1901 and 2099')
        return value


class PairInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    person_a: BirthInput
    person_b: BirthInput
    person_a_hour_unknown: bool = Field(default=False, description="Person A's birth hour is unknown: the hour pillar is left out, and the Zi Wei overlay is refused")
    person_b_hour_unknown: bool = Field(default=False, description="Person B's birth hour is unknown: the hour pillar is left out, and the Zi Wei overlay is refused")


class PairComparisonInput(PairInput):
    year: int | None = Field(default=None, ge=1901, le=2099, description=(
        'Optional civil year: adds year_view, the year pillar read against both charts, each person luck pillar in '
        'that year (needs gender) and the labels between the two luck pillars'))


class PalaceRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    palace: Literal[
        '命宫', '兄弟宫', '夫妻宫', '子女宫', '财帛宫', '疾厄宫',
        '迁移宫', '仆役宫', '官禄宫', '田宅宫', '福德宫', '父母宫',
    ]


def _day_pillar(day: date) -> str:
    i = (54 + (day - date(2000, 1, 1)).days) % 60
    return STEMS[i % 10] + BRANCHES[i % 12]


def calendar_days(request: CalendarRequest) -> dict:
    last = request.start_date + timedelta(days=request.days - 1)
    if last.year > 2099:
        raise ValueError('Date range cannot extend beyond 2099-12-31')
    events_by_day: dict[date, list[dict]] = {}
    for year in range(request.start_date.year, last.year + 1):
        for name, longitude, _month, _day in TERMS:
            moment = from_jd(solar_term_jd(year, longitude)).astimezone(CHINA)
            events_by_day.setdefault(moment.date(), []).append({
                'name': name, 'time_china': moment.isoformat(timespec='minutes')
            })
    days = []
    # One lunar date past the range tells whether its last day is 除夕.
    lunars = [lunar_or_rollover(request.start_date + timedelta(days=offset)) for offset in range(request.days + 1)]
    for offset in range(request.days):
        current = request.start_date + timedelta(days=offset)
        days.append({
            'date': current.isoformat(),
            'weekday': '一二三四五六日'[current.weekday()],
            'lunar': lunars[offset],
            'day_pillar': _day_pillar(current),
            'solar_terms': events_by_day.get(current, []),
            'festivals': day_marks(current, lunars[offset], lunars[offset + 1]),
        })
    return {
        'timezone': 'Asia/Shanghai', 'start_date': request.start_date.isoformat(),
        'days': days, 'method': 'astronomical-lunar-with-day-cycle',
        'notes': ['此接口只提供农历、日干支、节气与传统节日、三伏、数九的日期；不提供黄历宜忌或吉凶择日结论。',
                  '传统节日按农历日期（闰月不重复过节），三伏按夏至、立秋起数庚日，数九从冬至当天起数；每项都附推算规则。'],
    }


def _branch_relation(left: str, right: str) -> str:
    if left == right:
        return '同支'
    pair = frozenset((left, right))
    if pair in BRANCH_HARMONY:
        return '六合'
    if pair in BRANCH_CLASH:
        return '六冲'
    return '未标记六合或六冲'


def compare_charts(request: PairInput) -> dict:
    # The group reading of two people: ten gods both ways, the day-stem combination and every branch link,
    # and with a year the same luck and year-pillar view as a group of two.
    from .group import GroupMember, GroupRequest, _member, _pair, _year_view
    people = [GroupMember(label=label, birth=birth, hour_unknown=unknown) for label, birth, unknown in
              (('A', request.person_a, request.person_a_hour_unknown), ('B', request.person_b, request.person_b_hour_unknown))]
    a, b = (_member(m) for m in people)
    year = getattr(request, 'year', None)
    relation = _pair(0, 1, a, b)
    parallels = []
    for key, label in (('year', '年柱'), ('month', '月柱'), ('day', '日柱'), ('hour', '时柱')):
        pa, pb = a['pillars'][key], b['pillars'][key]
        known = bool(pa and pb)
        parallels.append({
            'pillar': key, 'label': label,
            'person_a': pa, 'person_b': pb,
            'branch_relation': _branch_relation(pa[1], pb[1]) if known else '不比较（时辰不详）' if key == 'hour' else '不比较（当天交节或换日）',
            'labels': next((x['labels'] for x in relation['branch_links'] if x['a_pillar'] == x['b_pillar'] == key), []),
            'same_stem': known and pa[0] == pb[0],
        })
    notes = [
        '仅对两组四柱做结构化对照，不评价关系好坏，不提供匹配分数。',
        '六合、六冲、六害、相刑与天干五合是传统象征标签，不能据此预测关系结果或替代实际沟通。',
        '十神是有方向的：A 看 B 与 B 看 A 往往不同，两者都列出。',
    ]
    if a['hour_unknown'] or b['hour_unknown']:
        notes.append('出生时辰不详的一方不参与时柱的比较。')
    if a['uncertain_pillars'] or b['uncertain_pillars']:
        notes.append('时辰不详且出生当天交节（或按 23:00 换日）的一方，当天之内会变的年柱、月柱或日柱也不参与比较。')
    person = lambda m: {'birth_datetime': m['birth_datetime'], 'hour_unknown': m['hour_unknown'], 'uncertain_pillars': m['uncertain_pillars'],
                        'pillars': m['pillars'], 'day_master': m['day_master'], 'day_master_element': m['day_master_element'],
                        'zodiac': m['zodiac']}
    return {
        'system': 'pair-comparison',
        'person_a': person(a),
        'person_b': person(b),
        'comparisons': parallels,
        'day_stems': relation['day_stems'],
        'zodiac': relation['zodiac'],
        'branch_links': relation['branch_links'],
        'label_counts': relation['label_counts'],
        'rules': {'branches': '传统六合 / 六冲 / 同支标签', 'ten_god': '以各自日干为我，看对方日干',
                  'stem_combination': '甲己、乙庚、丙辛、丁壬、戊癸五合',
                  'branch_links': '四柱地支两两比较：同支、六合、六冲、六害、相刑', 'compatibility_score': None},
        'notes': notes,
        'year_view': _year_view(GroupRequest(members=people, year=year), [a, b]) if year is not None else None,
    }


def palace_detail(request: PalaceRequest) -> dict:
    chart = calculate_ziwei(request.birth)
    found = next(p for p in chart['palaces'] if p['name'] == request.palace)
    return {
        'system': 'ziwei-palace-detail',
        'palace': found,
        'topic': PALACE_TOPICS[request.palace],
        'year_transformations_here': found['birth_year_transformations'],
        'school': chart['transformation_school'],
        'follow_up_questions': [
            f'{request.palace}在传统命盘中通常关联什么话题？',
            '宫内主星、辅星与四化分别按照哪些计算规则安置？',
            '不同紫微流派会怎样处理同一张命盘？',
        ],
        'limitations': '该信息属于传统命盘符号解释，非事实预测；星曜覆盖未完成。',
    }

class AnnualRequest(BaseModel):
    """Lunar year stem four-transformation overlay, not a predictive transit."""
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    lunar_year: int = Field(ge=1901, le=2099, description='Named Chinese lunar year (starts at Chinese New Year)')


class TimeAuditRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput


class RuleComparisonRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    original: BirthInput
    alternative: BirthInput


def _lunar_year_span(lunar_year: int) -> dict:
    """Gregorian first and last day of a named lunar year (China calendar); the last day is None past 2099."""
    from .extended import lunar_month_catalog
    start = lunar_month_catalog(lunar_year)[0][2]
    end = lunar_month_catalog(lunar_year + 1)[0][2] - timedelta(days=1) if lunar_year < 2099 else None
    return {'start': start.isoformat(), 'end': end.isoformat() if end else None}


def annual_transformations(request: AnnualRequest) -> dict:
    """Four-transformations for the given *named lunar year* mapped onto natal palaces.

    Year-branch / flow-palace, annual stars, traditional timing and interpretation
    are NOT implied by these labels.
    """
    from .engines import PALACE_NAMES
    from .reference import FOUR_TRANSFORMATIONS, FOUR_TYPES, TRANSFORMATION_SCHOOL
    chart = calculate_ziwei(request.birth)
    stem_idx = (request.lunar_year - 1984) % 10
    stem = STEMS[stem_idx]
    year_branch = BRANCHES[(request.lunar_year - 1984) % 12]
    natal_ming_branch_idx = BRANCHES.index(chart['ming_palace'])
    palace_at = lambda branch: PALACE_NAMES[(natal_ming_branch_idx - BRANCHES.index(branch)) % 12]
    natal = {t['star']: t['type'] for t in chart['birth_year_transformations']}
    overlays = []
    for tag, star in zip(FOUR_TYPES, FOUR_TRANSFORMATIONS[stem]):
        target_branch = chart['star_positions'][star]
        overlays.append({
            'type': tag, 'star': star, 'natal_branch': target_branch,
            'natal_palace': palace_at(target_branch), 'natal_type': natal.get(star),
        })
    return {
        'system': 'annual-stem-four-transformations', 'lunar_year': request.lunar_year,
        'year_pillar': stem+year_branch, 'natal_ming_palace': chart['ming_palace'],
        'gregorian_span': _lunar_year_span(request.lunar_year),
        'year_branch_palace': palace_at(year_branch),
        'transformations': overlays,
        'natal_transformations': [{'type': t['type'], 'star': t['star'], 'natal_branch': t['palace'],
                                   'natal_palace': t['palace_name']} for t in chart['birth_year_transformations']],
        'school': TRANSFORMATION_SCHOOL,
        'limitations': [
            '农历年干四化叠加至本命盘，非完整流年盘，不包含流年命宫、限运、流曜。',
            '年支所在的本命宫位只是位置对照；完整的流年命宫与流曜见紫微盘的流年层。',
            '仅展示传统规则及位置，不预测个人当年的事件或结果。',
        ],
    }


def time_audit(request: TimeAuditRequest) -> dict:
    """Compare clock / mean / apparent solar time for one birth record."""
    from .engines import normalized_dt
    from .timebasis import time_basis
    inp = request.birth
    dt = normalized_dt(inp)
    if inp.longitude is None:
        raise ValueError('time_audit requires birthplace longitude')
    choices = []
    for mode in ('clock', 'mean_solar', 'apparent_solar'):
        variant = inp.model_copy(update={'time_mode': mode})
        b = calculate_bazi(variant)
        z = calculate_ziwei(variant)
        effective, meta = time_basis(dt, mode, inp.longitude)
        choices.append({
            'mode': mode, 'effective_reading': effective.isoformat(timespec='seconds'),
            'shift_minutes': meta['effective_shift_minutes'],
            'equation_of_time_minutes': meta['equation_of_time_minutes'],
            'pillars': {k: v['text'] for k, v in b['pillars'].items()},
            'ming_palace': z['ming_palace'], 'shen_palace': z['shen_palace'],
            'lunar_date': z['lunar_date'],
        })
    # The solar shifts are the longitude against the zone's standard meridian, minus any daylight saving.
    dst = (dt.dst() or timedelta(0)).total_seconds() / 60
    standard = dt.utcoffset().total_seconds() / 60 - dst
    return {
        'system': 'time-basis-audit', 'original_time_mode': inp.time_mode,
        'longitude': inp.longitude, 'choices': choices,
        'dst_minutes': round(dst, 4), 'standard_utc_offset_minutes': round(standard, 4),
        'longitude_vs_standard_meridian_minutes': round(inp.longitude * 4 - standard, 4),
        'warnings': ['地理经度必须准确；历史时区与流派对时辰起止仍可能有差异。',
                     '这只是时制敏感性对照，不判断哪个时间体系具有预测效力。'],
    }


def rule_comparison(request: RuleComparisonRequest) -> dict:
    a_b, b_b = calculate_bazi(request.original), calculate_bazi(request.alternative)
    a_z, b_z = calculate_ziwei(request.original), calculate_ziwei(request.alternative)
    return {
        'system': 'rule-sensitivity',
        'a': {'bazi': {k: v['text'] for k,v in a_b['pillars'].items()},
              'ming': a_z['ming_palace'], 'shen': a_z['shen_palace'],
              'bureau': a_z['five_elements_bureau'], 'time_basis': a_b['time_basis']},
        'b': {'bazi': {k: v['text'] for k,v in b_b['pillars'].items()},
              'ming': b_z['ming_palace'], 'shen': b_z['shen_palace'],
              'bureau': b_z['five_elements_bureau'], 'time_basis': b_b['time_basis']},
        'differences': {
            'pillars': [k for k in a_b['pillars'] if a_b['pillars'][k]['text'] != b_b['pillars'][k]['text']],
            'ming': a_z['ming_palace'] != b_z['ming_palace'],
            'shen': a_z['shen_palace'] != b_z['shen_palace'],
            'bureau': a_z['five_elements_bureau'] != b_z['five_elements_bureau'],
        },
        'notes': ['只展示两个参数方案之间的计算差异；不评价命盘孰优孰劣。'],
    }
