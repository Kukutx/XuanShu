"""Relations among two to eight charts: family, team or friends side by side.

Each pair gets both directions of the day-stem ten-god label (what the other
person's day stem is from this person's day master), the traditional day-stem
five combinations and every labelled branch link across the four pillars. The
group also gets complete three-harmony triads formed by different members'
year or day branches. These are traditional symbolic labels, not a judgement
of the relationship: no compatibility score or ranking is produced.
"""
from __future__ import annotations

from itertools import combinations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .engines import ANIMALS, BRANCH_ELEMENT, BRANCHES, ELEMENTS, STEM_ELEMENT, STEMS, BirthInput, _ten_god, calculate_bazi
from .reference import BRANCH_CLASH, BRANCH_HARM, BRANCH_HARMONY, BRANCH_PUNISH, BRANCH_TRIADS, STEM_COMBINATIONS

PILLARS = (('year', '年柱'), ('month', '月柱'), ('day', '日柱'), ('hour', '时柱'))
LINK_TYPES = ('同支', '六合', '六冲', '六害', '相刑')


class GroupMember(BaseModel):
    model_config = ConfigDict(extra='forbid')
    label: str = Field(min_length=1, max_length=50, description='Display name chosen by the user, e.g. Mum')
    birth: BirthInput
    hour_unknown: bool = Field(default=False, description='True leaves the hour pillar out of every comparison')

    @field_validator('label')
    @classmethod
    def trimmed(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('label must not be blank')
        return value


class GroupRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    members: list[GroupMember] = Field(min_length=2, max_length=8)

    @field_validator('members')
    @classmethod
    def distinct_labels(cls, members: list[GroupMember]) -> list[GroupMember]:
        labels = [m.label for m in members]
        if len(set(labels)) != len(labels):
            raise ValueError('member labels must be distinct')
        return members


def _labels(left: str, right: str) -> list[str]:
    pair = frozenset((left, right))
    found = []
    if left == right:
        found.append('同支')
    if pair in BRANCH_HARMONY:
        found.append('六合')
    if pair in BRANCH_CLASH:
        found.append('六冲')
    if pair in BRANCH_HARM:
        found.append('六害')
    if (left, right) in BRANCH_PUNISH or (right, left) in BRANCH_PUNISH:
        found.append('相刑')
    return found


def _member(m: GroupMember) -> dict:
    chart = calculate_bazi(m.birth)
    pillars = {key: chart['pillars'][key]['text'] for key, _ in PILLARS}
    if m.hour_unknown:
        pillars['hour'] = None
    return {
        'label': m.label,
        'birth_datetime': chart['birth_datetime'],
        'timezone': m.birth.timezone,
        'hour_unknown': m.hour_unknown,
        'pillars': pillars,
        'day_master': chart['day_master'],
        'day_master_element': chart['day_master_element'],
        'zodiac': ANIMALS[BRANCHES.index(pillars['year'][1])],
        # Stems and branches without hidden stems; the hour pillar is left out when unknown.
        'surface_five_elements': _surface(pillars),
    }


def _surface(pillars: dict) -> dict[str, int]:
    counts = dict.fromkeys(ELEMENTS, 0)
    for text in pillars.values():
        if text:
            counts[STEM_ELEMENT[STEMS.index(text[0])]] += 1
            counts[BRANCH_ELEMENT[BRANCHES.index(text[1])]] += 1
    return counts


def _pair(i: int, j: int, a: dict, b: dict) -> dict:
    sa, sb = STEMS.index(a['day_master']), STEMS.index(b['day_master'])
    links = []
    for ka, la in PILLARS:
        for kb, lb in PILLARS:
            pa, pb = a['pillars'][ka], b['pillars'][kb]
            if not pa or not pb:
                continue
            found = _labels(pa[1], pb[1])
            if found:
                links.append({'a_pillar': ka, 'a_label': la, 'a_branch': pa[1],
                              'b_pillar': kb, 'b_label': lb, 'b_branch': pb[1], 'labels': found})
    counts = {name: sum(name in link['labels'] for link in links) for name in LINK_TYPES}
    return {
        'a': i, 'b': j, 'a_label': a['label'], 'b_label': b['label'],
        'day_stems': {
            'a_sees_b': _ten_god(sa, sb), 'b_sees_a': _ten_god(sb, sa),
            'combination': STEM_COMBINATIONS.get(frozenset((a['day_master'], b['day_master']))),
        },
        'zodiac': {'a': a['zodiac'], 'b': b['zodiac'], 'labels': _labels(a['pillars']['year'][1], b['pillars']['year'][1])},
        'day_branches': _labels(a['pillars']['day'][1], b['pillars']['day'][1]),
        'branch_links': links,
        'label_counts': counts,
    }


def _triads(members: list[dict]) -> list[dict]:
    found = []
    for key, label in (('year', '年支（生肖）'), ('day', '日支')):
        for branches, element in BRANCH_TRIADS:
            holders = [{'label': m['label'], 'branch': m['pillars'][key][1]}
                       for m in members if m['pillars'][key][1] in branches]
            if {h['branch'] for h in holders} == set(branches):
                found.append({'pillar': key, 'pillar_label': label, 'triad': branches,
                              'element': element, 'members': holders})
    return found


def group_relations(req: GroupRequest) -> dict:
    members = [_member(m) for m in req.members]
    pairs = [_pair(i, j, members[i], members[j]) for i, j in combinations(range(len(members)), 2)]
    day_masters = {element: [m['label'] for m in members if m['day_master_element'] == element] for element in ELEMENTS}
    totals = {element: sum(m['surface_five_elements'][element] for m in members) for element in ELEMENTS}
    notes = [
        '只并列各人的四柱并标出传统的十神、天干五合、地支六合、六冲、六害、相刑与三合标签，不评价关系好坏，也不给匹配分数或排名。',
        '十神是有方向的：A 看 B 与 B 看 A 往往不同，两者都列出。',
        '这些是传统象征标签，不能据此预测关系结果，也不能替代沟通与了解对方。',
    ]
    if any(m['hour_unknown'] for m in members):
        notes.append('出生时辰不详的成员不参与时柱的比较。')
    return {
        'system': 'group-relations',
        'members': members,
        'pairs': pairs,
        'triads': _triads(members),
        'element_overview': {'day_masters': day_masters, 'surface_totals': totals},
        'rules': {
            'ten_god': '以各自日干为我，看对方日干', 'stem_combination': '甲己、乙庚、丙辛、丁壬、戊癸五合',
            'branch_links': '四柱地支两两比较：同支、六合、六冲、六害、相刑',
            'triads': '不同成员的年支或日支凑齐申子辰、亥卯未、寅午戌、巳酉丑',
            'compatibility_score': None,
        },
        'notes': notes,
    }
