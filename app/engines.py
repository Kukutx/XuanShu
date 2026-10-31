"""Deterministic BaZi and Zi Wei Dou Shu natal chart calculations.

Scope: BaZi four pillars and surface-stem ten-gods; Zi Wei 12 palaces,
14 primary stars and an auditable collection of additional named stars,
four natal cycle labels, small-limit nominal ages, five-elements bureau,
and 10-year palace periods. No fortune telling by a language model.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .astronomy import chinese_lunar_date, from_jd, solar_term_jd, solar_month_offset, nearest_jie

from .reference import (HIDDEN_STEMS, NAYIN_NAMES, FOUR_TRANSFORMATIONS, FOUR_TYPES, TRANSFORMATION_SCHOOL, BRANCH_HARMONY, BRANCH_CLASH, BRANCH_HARM, BRANCH_PUNISH,
                        BRANCH_SEASONS, BRANCH_TRIADS, GROWTH_START, STEM_CLASHES, STEM_COMBINATIONS)
from .timebasis import time_basis
from .shensha import natal_bases, natal_shensha, rule_notes, stars_on
from .ziwei_extensions import (BRIGHTNESS, CHANGSHENG, adjunct_stars, cycle_positions, nominal_small_limit_ages,
                               LIFEMASTER_BY_BRANCH, BODYMASTER_BY_YEAR_BRANCH)

STEMS = tuple('甲乙丙丁戊己庚辛壬癸')
BRANCHES = tuple('子丑寅卯辰巳午未申酉戌亥')
ELEMENTS = tuple('木火土金水')
STEM_ELEMENT = tuple('木木火火土土金金水水')
BRANCH_ELEMENT = tuple('水土木木土火火土金金土水')
ANIMALS = tuple('鼠牛虎兔龙蛇马羊猴鸡狗猪')
PALACE_NAMES = ('命宫','兄弟宫','夫妻宫','子女宫','财帛宫','疾厄宫','迁移宫','仆役宫','官禄宫','田宅宫','福德宫','父母宫')
NAYIN_ELEMENT_30 = tuple('金火木土金火水土金木水土火木水金火木土金火水土金木水土火木水')
BUREAU_NUM = {'水': 2, '木': 3, '金': 4, '土': 5, '火': 6}
ZIWEI_STARS = (('紫微', 0), ('天机', -1), ('太阳', -3), ('武曲', -4), ('天同', -5), ('廉贞', -8))
TIANFU_STARS = (('天府', 0), ('太阴', 1), ('贪狼', 2), ('巨门', 3), ('天相', 4), ('天梁', 5), ('七杀', 6), ('破军', 10))
LUCUN_BY_STEM = (2, 3, 5, 6, 5, 6, 8, 9, 11, 0)
# 天魁, 天钺 by stem: 甲戊庚 丑未, 乙己 子申, 丙丁 亥酉, 辛 午寅, 壬癸 卯巳 (iztro's published table).
KUI_YUE_BY_STEM = ((1, 7), (0, 8), (11, 9), (11, 9), (1, 7), (0, 8), (1, 7), (6, 2), (3, 5), (3, 5))
# 天马 by branch triad: 申子辰 寅, 巳酉丑 亥, 寅午戌 申, 亥卯未 巳.
TIANMA_BY_BRANCH = tuple((2, 11, 8, 5)[branch % 4] for branch in range(12))


class BirthInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    birth_datetime: str = Field(description='ISO 8601 local birth time, e.g. 1995-06-08T14:30; for a clock time repeated or skipped by a '
                                'daylight-saving change, append the UTC offset the clock showed, e.g. 1988-09-11T01:30+09:00')
    timezone: str = Field(default='Asia/Shanghai', description='IANA timezone, e.g. Asia/Shanghai, Europe/Rome')
    gender: Literal['male', 'female', 'unspecified'] = 'unspecified'
    late_zi_day_rollover: bool = Field(default=False, description='Set true for traditional 23:00 day change')
    leap_month_second_half_as_next: bool = True
    time_mode: Literal['clock', 'mean_solar', 'apparent_solar'] = 'clock'
    longitude: float | None = Field(default=None, ge=-180, le=180, description='Birthplace longitude, east positive; mandatory for solar-time modes')
    latitude: float | None = Field(default=None, ge=-90, le=90, description='Optional birthplace latitude; metadata only')

    @model_validator(mode='after')
    def require_longitude(self):
        if self.time_mode != 'clock' and self.longitude is None:
            raise ValueError('longitude is required for solar-time modes')
        return self

    @field_validator('birth_datetime')
    @classmethod
    def valid_datetime(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError('Use ISO 8601 datetime like 1995-06-08T14:30') from exc
        return value

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f'Unknown IANA timezone: {value}') from exc
        return value


def _offset_text(delta) -> str:
    seconds = int(delta.total_seconds())
    sign, seconds = ('-' if seconds < 0 else '+'), abs(seconds)
    text = f'{sign}{seconds // 3600:02d}:{seconds % 3600 // 60:02d}'
    return text + (f':{seconds % 60:02d}' if seconds % 60 else '')


def normalized_dt(inp: BirthInput) -> datetime:
    zone = ZoneInfo(inp.timezone)
    raw = datetime.fromisoformat(inp.birth_datetime)
    result = raw.replace(tzinfo=zone) if raw.tzinfo is None else raw.astimezone(zone)
    if not 1901 <= result.year <= 2099:
        raise ValueError('Supported birth years: 1901–2099')
    # Eliminate invalid wall times during DST transitions. Both messages name the two offsets the clock could have
    # shown (before and after the change), so a client can offer them and send the chosen one with the time.
    if raw.tzinfo is None:
        offsets = f' (UTC offsets {_offset_text(result.replace(fold=0).utcoffset())} or {_offset_text(result.replace(fold=1).utcoffset())})'
        if result.astimezone(ZoneInfo('UTC')).astimezone(zone).replace(tzinfo=None) != raw:
            raise ValueError('Birth time falls in a nonexistent daylight-saving hour; specify a valid local time' + offsets)
        if result.replace(fold=0).utcoffset() != result.replace(fold=1).utcoffset():
            raise ValueError('Ambiguous daylight-saving local time; supply an explicit UTC offset' + offsets)
    return result


def _sexagenary(index: int) -> dict:
    i = index % 60
    return {'stem': STEMS[i % 10], 'branch': BRANCHES[i % 12], 'text': STEMS[i % 10]+BRANCHES[i % 12]}


def growth_stage(stem: int, branch: int) -> str:
    """Twelve growth stages of a stem at a branch: yang stems run forward from their birth branch, yin stems backward."""
    start = GROWTH_START[stem % 10]
    return CHANGSHENG[(branch - start) % 12 if stem % 2 == 0 else (start - branch) % 12]


def xun_kong(index: int) -> str:
    """The two branches left over by the ten-pillar decade a pillar belongs to (Jia-Zi decade: Xu and Hai)."""
    first = index - index % 10
    return BRANCHES[(first + 10) % 12] + BRANCHES[(first + 11) % 12]


def stem_labels(left: str, right: str) -> list[str]:
    """The five stem combinations (Yi and Geng combine into metal, ...) and the four stem clashes between two stems."""
    pair = frozenset((left, right))
    return ([STEM_COMBINATIONS[pair]] if pair in STEM_COMBINATIONS else []) + (['相冲'] if pair in STEM_CLASHES else [])


def branch_labels(left: str, right: str) -> list[str]:
    """Pair labels between two branches. Punishment (xing) belongs to the pair, whichever pillar comes first."""
    pair = frozenset((left, right))
    return ((['同支'] if left == right else []) + (['六合'] if pair in BRANCH_HARMONY else [])
            + (['六冲'] if pair in BRANCH_CLASH else []) + (['六害'] if pair in BRANCH_HARM else [])
            + (['相刑'] if (left, right) in BRANCH_PUNISH or (right, left) in BRANCH_PUNISH else []))


def natal_interactions(pillar: str, natal: dict, pillar_keys: tuple[str, ...] = ('year', 'month', 'day', 'hour')) -> dict:
    """A luck or year pillar read against the natal pillars: its growth stages, whether it falls in the
    day or year void, and the stem and branch relations it forms with each natal pillar. Labels only."""
    stem, branch = STEMS.index(pillar[0]), BRANCHES.index(pillar[1])
    master = STEMS.index(natal['day_master'])
    natal_pillars = {key: natal['pillars'][key] for key in pillar_keys}
    present = {p['branch'] for p in natal_pillars.values()}
    return {
        'pillar': pillar,
        'ten_god_of_stem': _ten_god(master, stem),
        'hidden_stems': [{'stem': hidden, 'element': STEM_ELEMENT[STEMS.index(hidden)], 'ten_god': _ten_god(master, STEMS.index(hidden))}
                         for hidden in HIDDEN_STEMS[pillar[1]]],
        'na_yin': NAYIN_NAMES[_sexagenary_by_pair(stem, branch) // 2],
        'growth_stage': growth_stage(master, branch),
        'self_stage': growth_stage(stem, branch),
        'void_of': [key for key in ('day', 'year') if key in natal_pillars and pillar[1] in natal_pillars[key]['xun_kong']],
        # Stars this pillar carries by the natal day stem, year stem, year and day branches, month branch and year Na Yin.
        'shensha': stars_on(pillar, natal_bases({key: p['text'] for key, p in natal['pillars'].items()})),
        'stem_relations': [{'pillar': key, 'stem': p['stem'], 'labels': labels}
                           for key, p in natal_pillars.items() if (labels := stem_labels(pillar[0], p['stem']))],
        'branch_relations': [{'pillar': key, 'branch': p['branch'], 'labels': labels}
                             for key, p in natal_pillars.items() if (labels := branch_labels(pillar[1], p['branch']))],
        # A three-harmony or seasonal group this branch completes with branches already in the natal chart.
        'branch_groups': [{'kind': kind, 'branches': group, 'element': element,
                           'pillars': [key for key, p in natal_pillars.items() if p['branch'] in group and p['branch'] != pillar[1]]}
                          for kind, table in (('三合', BRANCH_TRIADS), ('三会', BRANCH_SEASONS))
                          for group, element in table
                          if pillar[1] in group and all(b in present for b in group if b != pillar[1])],
    }


def _sexagenary_by_pair(stem: int, branch: int) -> int:
    return next(i for i in range(60) if i % 10 == stem and i % 12 == branch)


def hour_branch_index(hour: int) -> int:
    return ((hour + 1) // 2) % 12


def _ten_god(day_stem: int, other_stem: int) -> str:
    if day_stem == other_stem:
        return '比肩'
    mine = ELEMENTS.index(STEM_ELEMENT[day_stem])
    other = ELEMENTS.index(STEM_ELEMENT[other_stem])
    delta = (other - mine) % 5
    same_yin_yang = (day_stem % 2 == other_stem % 2)
    names = (
        ('比肩', '劫财'),
        ('食神', '伤官'),
        ('偏财', '正财'),
        ('七杀', '正官'),
        ('偏印', '正印'),
    )
    return names[delta][0 if same_yin_yang else 1]


def pillar_indices(dt: datetime, late_zi_day_rollover: bool = False, time_mode: str = 'clock',
                   longitude: float | None = None) -> tuple[tuple[int, int, int, int], datetime, dict]:
    """Sexagenary indices (0 = 甲子) of the year, month, day and hour pillars for an aware instant.

    Year and month follow the astronomical instant (立春 and the twelve jie);
    day and hour follow the effective local reading of the chosen time basis.
    """
    effective, time_meta = time_basis(dt, time_mode, longitude)
    li_chun = from_jd(solar_term_jd(dt.year, 315))
    solar_year = dt.year if dt >= li_chun else dt.year - 1
    year_idx = (solar_year - 1984) % 60
    year_stem = year_idx % 10

    # Determine the month by an actual Jie event instant (inclusive), rather
    # than flooring a floating-point Sun longitude near a 30-degree boundary.
    month_offset = solar_month_offset(dt)
    month_branch = (2 + month_offset) % 12
    month_stem = (2 + 2 * (year_stem % 5) + month_offset) % 10
    month_idx = _sexagenary_by_pair(month_stem, month_branch)

    day_date = effective.date() + (timedelta(days=1) if late_zi_day_rollover and effective.hour == 23 else timedelta())
    # Independently verified anchor: 2000-01-01 is 戊午日 (index 54).
    day_idx = (54 + (day_date - date(2000,1,1)).days) % 60
    hour_branch = hour_branch_index(effective.hour)
    hour_stem = (2 * (day_idx % 5) + hour_branch) % 10
    hour_idx = _sexagenary_by_pair(hour_stem, hour_branch)
    return (year_idx, month_idx, day_idx, hour_idx), effective, time_meta


def calculate_bazi(inp: BirthInput) -> dict:
    dt = normalized_dt(inp)
    (year_idx, month_idx, day_idx, hour_idx), effective, time_meta = pillar_indices(
        dt, inp.late_zi_day_rollover, inp.time_mode, inp.longitude)

    pillars = {
        'year': _sexagenary(year_idx),
        'month': _sexagenary(month_idx),
        'day': _sexagenary(day_idx),
        'hour': _sexagenary(hour_idx),
    }
    master_stem = day_idx % 10
    for name, pillar in pillars.items():
        pillar['stem_element'] = STEM_ELEMENT[STEMS.index(pillar['stem'])]
        pillar['branch_element'] = BRANCH_ELEMENT[BRANCHES.index(pillar['branch'])]
        pillar['ten_god_of_stem'] = '日主' if name == 'day' else _ten_god(master_stem, STEMS.index(pillar['stem']))
        pillar_idx = {'year':year_idx, 'month':month_idx, 'day':day_idx, 'hour':hour_idx}[name]
        pillar['na_yin'] = NAYIN_NAMES[pillar_idx // 2]
        # Growth stage of the day master at this branch, and of the pillar's own stem at its branch.
        pillar['growth_stage'] = growth_stage(master_stem, pillar_idx % 12)
        pillar['self_stage'] = growth_stage(pillar_idx % 10, pillar_idx % 12)
        pillar['xun_kong'] = xun_kong(pillar_idx)
        pillar['hidden_stems'] = [
            {'stem': hidden, 'element': STEM_ELEMENT[STEMS.index(hidden)],
             'ten_god': _ten_god(master_stem, STEMS.index(hidden))}
            for hidden in HIDDEN_STEMS[pillar['branch']]
        ]

    # Traditional auxiliary stars on each pillar, read from the day stem, year stem, year and day branches, month branch
    # and the year's Na Yin; the hour pillar can carry stars but is never the basis of one.
    for name, stars in natal_shensha({key: p['text'] for key, p in pillars.items()}).items():
        pillars[name]['shensha'] = stars
    shensha_names = {star['name'] for p in pillars.values() for star in p['shensha']}

    # Visible stems/branches only — NOT a seasonal strength or hidden-stem analysis.
    surface_elements = Counter({e: 0 for e in ELEMENTS})
    for pillar in pillars.values():
        surface_elements[pillar['stem_element']] += 1
        surface_elements[pillar['branch_element']] += 1

    hidden_elements = Counter({e: 0 for e in ELEMENTS})
    ten_god_counts = Counter()
    for pillar in pillars.values():
        if pillar['ten_god_of_stem'] != '日主':
            ten_god_counts[pillar['ten_god_of_stem']] += 1
        for hidden in pillar['hidden_stems']:
            hidden_elements[hidden['element']] += 1
            ten_god_counts[hidden['ten_god']] += 1
    # Which pillars' branches fall in the day pillar's and the year pillar's 旬空.
    for pillar in pillars.values():
        pillar['void_of'] = [key for key in ('day', 'year') if pillar['branch'] in pillars[key]['xun_kong']]
    relations = []
    pillar_keys = tuple(pillars)
    stem_relations = []
    for i, a in enumerate(pillar_keys):
        for b in pillar_keys[i+1:]:
            tags = stem_labels(pillars[a]['stem'], pillars[b]['stem'])
            stem_relations.append({'a': a, 'b': b, 'stems': pillars[a]['stem'] + '/' + pillars[b]['stem'], 'labels': tags})
    present = [pillars[key]['branch'] for key in pillar_keys]
    branch_groups = [{'kind': kind, 'branches': group, 'element': element,
                      'pillars': [key for key in pillar_keys if pillars[key]['branch'] in group]}
                     for kind, table in (('三合', BRANCH_TRIADS), ('三会', BRANCH_SEASONS))
                     for group, element in table if all(branch in present for branch in group)]
    for i, a in enumerate(pillar_keys):
        for b in pillar_keys[i+1:]:
            left, right = pillars[a]['branch'], pillars[b]['branch']
            relations.append({'a': a, 'b': b, 'branches': left + '/' + right, 'labels': branch_labels(left, right)})

    return {
        'system': 'bazi',
        'birth_datetime': dt.isoformat(timespec='minutes'),
        'timezone': inp.timezone,
        'pillars': pillars,
        'day_master': STEMS[master_stem],
        'day_master_element': STEM_ELEMENT[master_stem],
        'surface_five_elements': dict(surface_elements),
        'hidden_stem_elements_unweighted': dict(hidden_elements),
        'ten_god_occurrences_unweighted': dict(ten_god_counts),
        'branch_relations': relations,
        'stem_relations': stem_relations,
        'branch_groups': branch_groups,
        'shensha_rules': rule_notes(shensha_names),
        'time_basis': time_meta,
        'lunar_date': chinese_lunar_date(effective.date()),
        'jie_boundaries': nearest_jie(dt),
        'rules': {
            'year_boundary': '立春',
            'month_boundary': '十二节令',
            'day_boundary': '23:00' if inp.late_zi_day_rollover else '00:00',
            'solar_time_correction': inp.time_mode != 'clock',
            'time_mode': inp.time_mode,
            'hidden_stems': '本气、中气、余气传统顺序；不含藏干权重',
            'growth_stage': '十二长生：阳干顺行、阴干逆行；长生位甲亥、乙午、丙戊寅、丁己酉、庚巳、辛子、壬申、癸卯（火土同宫）',
            'xun_kong': '旬空：每旬十个干支余下的两个地支；标出落在日柱旬空、年柱旬空里的地支',
            'stem_relations': '天干五合（甲己、乙庚、丙辛、丁壬、戊癸）与四冲（甲庚、乙辛、丙壬、丁癸），只作标签，不判断合化成败',
            'shensha': '神煞：只收能在古籍里查到安法的二十一种，以日干、年干、年支、日支、月支和年柱纳音查四柱，时柱不作查法起点；每种附查法与出处，只作标签，不断吉凶',
        },
        'notes': ['五行计数仅包含四柱明干与地支本气，不代表旺衰或缺失判定', '传统历法模型，不构成可验证的人生预测'],
    }


def _month_stem_for_branch(lunar_year_stem: int, palace_branch: int) -> int:
    return (2 + 2 * (lunar_year_stem % 5) + (palace_branch - 2) % 12) % 10


def _bureau(ming_stem: int, ming_branch: int) -> tuple[str, int]:
    sexagenary = _sexagenary_by_pair(ming_stem, ming_branch)
    element = NAYIN_ELEMENT_30[sexagenary // 2]
    return element, BUREAU_NUM[element]


def _ziwei_branch(lunar_day: int, bureau: int) -> int:
    quotient = (lunar_day + bureau - 1) // bureau
    offset = quotient * bureau - lunar_day
    movement = offset if offset % 2 == 0 else -offset
    return (2 + quotient - 1 + movement) % 12


def _star_positions(lunar_day: int, bureau: int, adjusted_month: int,
                    hour_branch: int, year_stem: int, year_branch: int) -> dict[str, int]:
    ziwei = _ziwei_branch(lunar_day, bureau)
    ziwei_relative = (ziwei - 2) % 12
    tianfu = (2 - ziwei_relative) % 12
    stars = {name: (ziwei + delta) % 12 for name, delta in ZIWEI_STARS}
    stars.update({name: (tianfu + delta) % 12 for name, delta in TIANFU_STARS})
    stars.update({
        '左辅': (4 + adjusted_month - 1) % 12,
        '右弼': (10 - (adjusted_month - 1)) % 12,
        '文昌': (10 - hour_branch) % 12,
        '文曲': (4 + hour_branch) % 12,
        '地空': (11 - hour_branch) % 12,
        '地劫': (11 + hour_branch) % 12,
    })
    lucun = LUCUN_BY_STEM[year_stem]
    stars.update({'禄存': lucun, '擎羊': (lucun + 1) % 12, '陀罗': (lucun - 1) % 12})
    stars['天马'] = TIANMA_BY_BRANCH[year_branch]
    stars['天魁'], stars['天钺'] = KUI_YUE_BY_STEM[year_stem]
    # 红鸾 starts at 卯 for 子 year and counts backwards; 天喜 opposite.
    stars['红鸾'] = (3 - year_branch) % 12
    stars['天喜'] = (stars['红鸾'] + 6) % 12
    # 天刑 from 酉, 天姚 from 丑 at first lunar month, counting forward.
    stars['天刑'] = (9 + adjusted_month - 1) % 12
    stars['天姚'] = (1 + adjusted_month - 1) % 12
    # 龙池 from 辰 counts forward by year branch; 凤阁 from 戌 counts backward.
    stars['龙池'] = (4 + year_branch) % 12
    stars['凤阁'] = (10 - year_branch) % 12
    return stars


def calculate_ziwei(inp: BirthInput) -> dict:
    dt = normalized_dt(inp)
    effective, time_meta = time_basis(dt, inp.time_mode, inp.longitude)
    # With the 23:00 day change, 23:00-23:59 takes the next day's whole lunar date, as the
    # bazi day pillar does. (iztro's late-Zi hour adds a day but keeps the month; see docs/evals.)
    late_zi = inp.late_zi_day_rollover and effective.hour == 23
    lunar = chinese_lunar_date(effective.date() + (timedelta(days=1) if late_zi else timedelta()), allow_rollover_day=late_zi)
    month = lunar['month']
    if lunar['is_leap_month'] and inp.leap_month_second_half_as_next and lunar['day'] > 15:
        month = month % 12 + 1

    time_index = hour_branch_index(effective.hour)
    ming = (2 + (month - 1) - time_index) % 12
    shen = (2 + (month - 1) + time_index) % 12
    year_idx = (lunar['year'] - 1984) % 60
    year_stem, year_branch = year_idx % 10, year_idx % 12
    ming_stem = _month_stem_for_branch(year_stem, ming)
    bureau_el, bureau_value = _bureau(ming_stem, ming)
    stars = _star_positions(lunar['day'], bureau_value, month, time_index, year_stem, year_branch)
    # Preserve canonical insertion order across interpreter runs and hash seeds.
    # A frozenset here made auxiliary_star_groups nondeterministic in exported JSON.
    main_star_names = {name for name, _ in ZIWEI_STARS + TIANFU_STARS}
    legacy_auxiliary = tuple(name for name in stars if name not in main_star_names)
    adjectives = adjunct_stars(lunar['day'], month, time_index, year_stem,
                               year_branch, ming, shen, stars)
    stars.update(adjectives)
    cycles = cycle_positions(bureau_value, stars['禄存'], year_stem, year_branch, inp.gender)

    natal_transformations = [
        {'type': tag, 'star': star, 'palace': BRANCHES[stars[star]],
         'palace_name': PALACE_NAMES[(ming - stars[star]) % 12]}
        for tag, star in zip(FOUR_TYPES, FOUR_TRANSFORMATIONS[STEMS[year_stem]])
    ]

    starts = {}
    if inp.gender != 'unspecified':
        # Yang male / Yin female moves forward through earthly branches.
        forward = (year_stem % 2 == 0) == (inp.gender == 'male')
        step = 1 if forward else -1
        for j in range(12):
            starts[(ming + j * step) % 12] = {'start_age': bureau_value + 10*j, 'end_age': bureau_value + 10*j + 9}

    palaces = []
    for branch in range(12):
        # Palace name sequence decreases by earthly branch from 命宫.
        name_idx = (ming - branch) % 12
        stem_idx = _month_stem_for_branch(year_stem, branch)
        flying = [
            {'type': tag, 'star': star, 'target_branch': BRANCHES[stars[star]],
             'target_palace': PALACE_NAMES[(ming - stars[star]) % 12], 'self_transform': stars[star] == branch}
            for tag, star in zip(FOUR_TYPES, FOUR_TRANSFORMATIONS[STEMS[stem_idx]])
        ]
        triangle = [(branch + 4) % 12, (branch + 8) % 12]
        opposite = (branch + 6) % 12
        palaces.append({
            'three_harmonies_and_opposite': {
                'trine': [{'branch': BRANCHES[i], 'palace': PALACE_NAMES[(ming-i)%12]} for i in triangle],
                'opposite': {'branch': BRANCHES[opposite], 'palace': PALACE_NAMES[(ming-opposite)%12]},
            },
            'name': PALACE_NAMES[name_idx],
            'branch': BRANCHES[branch],
            'stem': STEMS[stem_idx],
            'is_ming': branch == ming,
            'is_shen': branch == shen,
            'main_stars': [name for name, idx in stars.items() if idx == branch and name in dict(ZIWEI_STARS + TIANFU_STARS)],
            'auxiliary_stars': [name for name, idx in stars.items() if idx == branch and name not in dict(ZIWEI_STARS + TIANFU_STARS)],
            'star_brightness': {name: BRIGHTNESS[name][branch] for name, idx in stars.items()
                                if idx == branch and name in BRIGHTNESS and BRIGHTNESS[name][branch]},
            'auxiliary_star_groups': {
                'original_selected': [name for name in legacy_auxiliary if stars[name] == branch],
                'additional_named': [name for name in adjectives if stars[name] == branch],
            },
            'natal_cycles': {key: locations[branch] for key, locations in cycles.items()},
            'small_limit_nominal_ages': nominal_small_limit_ages(year_branch, inp.gender, branch),
            'birth_year_transformations': [x for x in natal_transformations if x['palace'] == BRANCHES[branch]],
            'palace_flying_transformations': flying,
            'decade': starts.get(branch),
        })
    return {
        'system': 'ziwei',
        'birth_datetime': dt.isoformat(timespec='minutes'),
        'timezone': inp.timezone,
        'lunar_date': lunar,
        'year_pillar': _sexagenary(year_idx)['text'],
        'adjusted_lunar_month': month,
        'ming_palace': BRANCHES[ming],
        'shen_palace': BRANCHES[shen],
        'five_elements_bureau': bureau_el + '二三四五六'[bureau_value-2] + '局',
        'bureau_number': bureau_value,
        'palaces': palaces,
        'star_positions': {name: BRANCHES[branch] for name, branch in stars.items()},
        'star_counts': {'main': len(ZIWEI_STARS)+len(TIANFU_STARS),
                        'auxiliary': len(stars)-len(ZIWEI_STARS)-len(TIANFU_STARS),
                        'original_selected': len(legacy_auxiliary), 'additional_named': len(adjectives)},
        'ming_master': LIFEMASTER_BY_BRANCH[ming],
        'shen_master': BODYMASTER_BY_YEAR_BRANCH[year_branch],
        'small_limit_age_system': '传统虚岁；出生当年按一岁计算，非周岁',
        'natal_cycles_included': sorted(cycles),
        'time_basis': time_meta,
        'birth_year_transformations': natal_transformations,
        'transformation_school': TRANSFORMATION_SCHOOL,
        'rules': {
            'year_boundary': '农历正月初一',
            'late_zi_day_rollover_in_ziwei': inp.late_zi_day_rollover,
            'leap_month_second_half_as_next': inp.leap_month_second_half_as_next,
            'star_coverage': '14主星+44颗选定辅助/杂曜（其中新增26颗）；非所有流派与流曜',
            'brightness_table': '庙旺得利平不陷，十四主星与文昌、文曲、火星、铃星、擎羊、陀罗；用 iztro 公开的亮度表，其他流派的得、利、平可能不同',
            'additional_star_rules': 'iztro公开安星诀；出生年、本命宫位、农历月日和时辰推导',
            'ming_master_basis': '本命命宫地支（与公开示例相符）；其他流派可能用生年地支',
            'shen_master_basis': '出生年地支',
            'natal_cycles_are_not_annual_charts': True,
            'solar_time_correction': inp.time_mode != 'clock',
            'time_mode': inp.time_mode,
        },
        'notes': ['紫微新增选定杂曜、四组十二神与虚岁小限；运限层（大限到流时，含流曜与流年十二神）见 ziwei_horoscope；全部星曜已与 iztro 交叉核验，其他流派尚未逐宫核对', '传统时辰依据所选时基计算；太阳时转换为近似值，非精密历史历书定盘', '流派差异请使用一致的命盘规则比对'],
    }


def combined_chart(inp: BirthInput) -> dict:
    return {'bazi': calculate_bazi(inp), 'ziwei': calculate_ziwei(inp)}
