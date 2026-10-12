"""Two-person Zi Wei overlay (紫微合盘宫位叠盘).

Both charts share the same twelve-branch grid, so one person's stars and
palaces can be read inside the other's palaces branch by branch. This module
reports three structural facts and nothing else:

* the palace each person has on every branch (宫位对照);
* where each person's Ming and Shen palaces land in the other chart;
* where each person's birth-year stem transformations (生年四化) fall when the
  transformed stars are looked up in the other person's chart (四化入对方盘).

It gives no compatibility score and makes no claim about the relationship.
"""
from __future__ import annotations

from .engines import BRANCHES, calculate_ziwei
from .features import PairInput
from .reference import FOUR_TRANSFORMATIONS, FOUR_TYPES, TRANSFORMATION_SCHOOL

FOCUS_PALACES = ('命宫', '夫妻宫', '福德宫', '迁移宫', '财帛宫', '官禄宫')


def _by_branch(chart: dict) -> dict[str, dict]:
    return {p['branch']: p for p in chart['palaces']}


def _summary(chart: dict) -> dict:
    return {'birth_datetime': chart['birth_datetime'], 'year_pillar': chart['year_pillar'],
            'ming_palace_branch': chart['ming_palace'], 'shen_palace_branch': chart['shen_palace'],
            'five_elements_bureau': chart['five_elements_bureau']}


def _landing(branch: str, other: dict[str, dict]) -> dict:
    palace = other[branch]
    return {'branch': branch, 'palace_in_other_chart': palace['name'], 'main_stars_there': palace['main_stars']}


def _transformations_into(source: dict, target: dict, target_palaces: dict[str, dict]) -> list[dict]:
    stem = source['year_pillar'][0]
    rows = []
    for kind, star in zip(FOUR_TYPES, FOUR_TRANSFORMATIONS[stem]):
        branch = target['star_positions'].get(star)
        rows.append({'type': kind, 'star': star, 'source_year_stem': stem,
                     'target_branch': branch,
                     'target_palace': target_palaces[branch]['name'] if branch else None})
    return rows


def ziwei_pair_overlay(request: PairInput) -> dict:
    if request.person_a_hour_unknown or request.person_b_hour_unknown:
        raise ValueError('紫微宫位叠盘需要两人的出生时辰：时辰不详时无法安命宫，也就没有宫位可以对齐。')
    a, b = calculate_ziwei(request.person_a), calculate_ziwei(request.person_b)
    pa, pb = _by_branch(a), _by_branch(b)
    grid = [{'branch': br,
             'person_a_palace': pa[br]['name'], 'person_a_main_stars': pa[br]['main_stars'],
             'person_b_palace': pb[br]['name'], 'person_b_main_stars': pb[br]['main_stars']}
            for br in BRANCHES]
    focus = []
    for name in FOCUS_PALACES:
        for owner, mine, other in (('person_a', pa, pb), ('person_b', pb, pa)):
            branch = next(br for br, p in mine.items() if p['name'] == name)
            focus.append({'owner': owner, 'palace': name, 'branch': branch,
                          'other_palace_on_same_branch': other[branch]['name'],
                          'other_main_stars_here': other[branch]['main_stars']})
    return {
        'system': 'ziwei-pair-overlay',
        'person_a': _summary(a),
        'person_b': _summary(b),
        'palace_grid': grid,
        'ming_shen_landings': {
            'person_a_ming_in_b': _landing(a['ming_palace'], pb),
            'person_a_shen_in_b': _landing(a['shen_palace'], pb),
            'person_b_ming_in_a': _landing(b['ming_palace'], pa),
            'person_b_shen_in_a': _landing(b['shen_palace'], pa),
        },
        'focus_palaces': focus,
        'transformations_a_into_b': _transformations_into(a, b, pb),
        'transformations_b_into_a': _transformations_into(b, a, pa),
        'school': TRANSFORMATION_SCHOOL,
        'method': 'same twelve-branch grid; stars and palaces read across charts by branch; '
                  'birth-year stem transformations looked up in the other chart',
        'compatibility_score': None,
        'limitations': [
            '宫位叠盘只是把两张命盘按十二地支对齐后的结构对照，不评价关系好坏，不提供匹配分数。',
            '「四化入对方盘」是合盘常见读法之一：用一方生年天干的四化星，在另一方命盘中找该星所在宫位；其他流派可能改用宫干飞化或流年四化。',
            f'四化表采用{TRANSFORMATION_SCHOOL}；钦天、北派等流派的合盘规则未实现。',
            '传统术数未经科学预测效力验证，不能替代两个人的实际沟通。',
        ],
    }
