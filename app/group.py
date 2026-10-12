"""Relations among two to eight charts: family, team or friends side by side.

Each pair gets both directions of the day-stem ten-god label (what the other
person's day stem is from this person's day master), the traditional day-stem
five combinations and every labelled branch link across the four pillars. The
group also gets complete three-harmony triads formed by different members'
year or day branches. With a year, each member's luck pillar (大运) and the
year pillar (流年) read against each chart are listed side by side, with the
labelled links between members' luck pillars. These are traditional symbolic
labels, not a judgement of the relationship: no compatibility score or ranking
is produced.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from itertools import combinations
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .advanced import DayunRequest, dayun_sequence
from .engines import (ANIMALS, BRANCH_ELEMENT, BRANCHES, ELEMENTS, STEM_ELEMENT, STEMS, BirthInput, _ten_god, calculate_bazi,
                      natal_interactions)
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
    year: int | None = Field(default=None, ge=1901, le=2099, description=(
        'Optional civil year: adds year_view, the year pillar read against every chart, each member luck pillar '
        'in that year (needs birth.gender) and the labelled links between members luck pillars'))

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


DAY_START, DAY_END = 'start', 'end'


def _day_start(zone: ZoneInfo, day: date) -> datetime:
    """The first instant of the local ``day``: a daylight-saving jump at midnight can skip local 00:00 (the day
    then begins at the later clock reading) or repeat it (the day begins at the first 00:00)."""
    found = []
    for fold in (0, 1):
        moment = datetime.combine(day, time(0), tzinfo=zone).replace(fold=fold).astimezone(timezone.utc)
        if moment.astimezone(zone).date() == day:
            found.append(moment)
    if not found:
        raise ValueError(f'{day} does not exist in {zone.key}')
    return min(found)


def _birth_at(birth: BirthInput, day: str, edge: str) -> tuple[BirthInput, dict]:
    """The birth at the first (``DAY_START``) or the last whole minute (``DAY_END``) of the local ``day``, with
    its chart. The time carries its UTC offset, so a clock reading repeated by a daylight-saving change is not
    ambiguous."""
    zone, local = ZoneInfo(birth.timezone), date.fromisoformat(day)
    if edge == DAY_START:
        moment = _day_start(zone, local)
    else:
        try:
            following = _day_start(zone, local + timedelta(days=1))
        except ValueError:  # the next date was skipped (Samoa, 30 December 2011)
            following = _day_start(zone, local + timedelta(days=2))
        moment = following - timedelta(minutes=1)
    moved = birth.model_copy(update={'birth_datetime': moment.astimezone(zone).isoformat(timespec='minutes')})
    return moved, calculate_bazi(moved)


def _at(birth: BirthInput, day: str, edge: str) -> dict:
    return _birth_at(birth, day, edge)[1]


def _member(m: GroupMember) -> dict:
    chart = calculate_bazi(m.birth)
    pillars = {key: chart['pillars'][key]['text'] for key, _ in PILLARS}
    uncertain = []
    if m.hour_unknown:
        pillars['hour'] = None
        # Any time of the day is possible: a jie boundary (or a 23:00 day change) inside the day makes the
        # year, month or day pillar differ between its first and last minute, so that pillar is unknown too.
        day = chart['birth_datetime'][:10]
        ends = (_at(m.birth, day, DAY_START), _at(m.birth, day, DAY_END))
        for key in ('year', 'month', 'day'):
            if any(end['pillars'][key]['text'] != pillars[key] for end in ends):
                pillars[key] = None
                uncertain.append(key)
    return {
        'label': m.label,
        'birth_datetime': chart['birth_datetime'],
        'timezone': m.birth.timezone,
        'hour_unknown': m.hour_unknown,
        'uncertain_pillars': uncertain,
        'pillars': pillars,
        'day_master': chart['day_master'] if pillars['day'] else None,
        'day_master_element': chart['day_master_element'] if pillars['day'] else None,
        'zodiac': ANIMALS[BRANCHES.index(pillars['year'][1])] if pillars['year'] else None,
        # Stems and branches without hidden stems; unknown pillars are left out.
        'surface_five_elements': _surface(pillars),
    }


def _branch_labels(a: str | None, b: str | None) -> list[str]:
    return _labels(a[1], b[1]) if a and b else []


def _surface(pillars: dict) -> dict[str, int]:
    counts = dict.fromkeys(ELEMENTS, 0)
    for text in pillars.values():
        if text:
            counts[STEM_ELEMENT[STEMS.index(text[0])]] += 1
            counts[BRANCH_ELEMENT[BRANCHES.index(text[1])]] += 1
    return counts


def _pair(i: int, j: int, a: dict, b: dict) -> dict:
    if a['day_master'] and b['day_master']:
        sa, sb = STEMS.index(a['day_master']), STEMS.index(b['day_master'])
        stems = {'a_sees_b': _ten_god(sa, sb), 'b_sees_a': _ten_god(sb, sa),
                 'combination': STEM_COMBINATIONS.get(frozenset((a['day_master'], b['day_master'])))}
    else:
        stems = {'a_sees_b': None, 'b_sees_a': None, 'combination': None}
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
        'day_stems': stems,
        'zodiac': {'a': a['zodiac'], 'b': b['zodiac'], 'labels': _branch_labels(a['pillars']['year'], b['pillars']['year'])},
        'day_branches': _branch_labels(a['pillars']['day'], b['pillars']['day']),
        'branch_links': links,
        'label_counts': counts,
    }


def _triads(members: list[dict]) -> list[dict]:
    found = []
    for key, label in (('year', '年支（生肖）'), ('day', '日支')):
        for branches, element in BRANCH_TRIADS:
            holders = [{'label': m['label'], 'branch': m['pillars'][key][1]}
                       for m in members if m['pillars'][key] and m['pillars'][key][1] in branches]
            if {h['branch'] for h in holders} == set(branches):
                found.append({'pillar': key, 'pillar_label': label, 'triad': branches,
                              'element': element, 'members': holders})
    return found


def _luck_case(birth: BirthInput, year: int, hour_unknown: bool) -> dict:
    """The luck period ``year`` falls in, by the same 交运年 listing as the luck page: the year a period begins
    in is listed whole under it."""
    data = dayun_sequence(DayunRequest(birth=birth, periods=12, include_years=True, hour_unknown=hour_unknown))
    for period in data['periods']:
        years = [item['year'] for item in period['years']]
        if year in years:
            return {'status': 'in_period', 'pillar': period['pillar'], 'sequence': period['sequence'], 'start_year': years[0]}
    first = data['periods'][0]['years'][0]['year']
    return {'status': 'not_started' if year < first else 'beyond', 'pillar': None, 'sequence': None,
            'start_year': first if year < first else None}


def _luck(m: GroupMember, member: dict, year: int) -> dict:
    """The member's luck pillar in ``year``. With an unknown hour the luck start moves by up to a third of a
    year within the birth day, so the period is taken at the first and the last minute of that day: when both
    give one pillar but different start years, ``start_years`` has both and ``start_year`` is None; when the
    pillars differ, both cases are listed under ``options``."""
    empty = {'status': None, 'pillar': None, 'ten_god': None, 'sequence': None, 'start_year': None, 'start_years': [],
             'changes_this_year': None, 'options': []}
    if m.birth.gender == 'unspecified':
        return {**empty, 'status': 'needs_gender'}
    if {'year', 'month'} & set(member['uncertain_pillars']):
        # The month pillar the luck pillars count from (or the year stem that sets their direction) is unknown.
        return {**empty, 'status': 'uncertain_pillars'}
    if m.hour_unknown:
        day = member['birth_datetime'][:10]
        cases = [_luck_case(_birth_at(m.birth, day, times)[0], year, True) for times in (DAY_START, DAY_END)]
    else:
        cases = [_luck_case(m.birth, year, False)]
    for case in cases:
        case['changes_this_year'] = case['start_year'] == year
    starts = sorted({case['start_year'] for case in cases if case['start_year'] is not None})
    if all((c['status'], c['pillar']) == (cases[0]['status'], cases[0]['pillar']) for c in cases):
        # One pillar either way; only the year it begins in may move with the hour.
        changes = {c['changes_this_year'] for c in cases}
        found = {**empty, **cases[0], 'start_year': starts[0] if len(starts) == 1 else None,
                 'changes_this_year': changes.pop() if len(changes) == 1 else None}
    else:
        found = {**empty, 'status': 'depends_on_hour',
                 'options': sorted(cases, key=lambda c: (c['status'] == 'in_period', c['sequence'] or 0))}
    if not found['options']:
        found['start_years'] = starts
    master = member['day_master']
    found['ten_god'] = _ten_god(STEMS.index(master), STEMS.index(found['pillar'][0])) if master and found['pillar'] else None
    for case in found['options']:
        case['ten_god'] = _ten_god(STEMS.index(master), STEMS.index(case['pillar'][0])) if master and case['pillar'] else None
    return found


def _year_view(req: GroupRequest, members: list[dict]) -> dict:
    year = req.year
    pillar = STEMS[(year - 4) % 10] + BRANCHES[(year - 4) % 12]
    rows = []
    for m, member in zip(req.members, members):
        born = int(member['birth_datetime'][:4])
        row = {'label': member['label'], 'gender': m.birth.gender, 'age': year - born, 'hour_unknown': m.hour_unknown}
        if year < born:
            rows.append({**row, 'age': None, 'status': 'not_born', 'luck': None, 'year_reading': None})
            continue
        known = tuple(key for key, _ in PILLARS if member['pillars'][key])
        # A year, month or day pillar that can change within the birth day leaves the stars and the day master
        # unknown, so the year pillar is not read against such a chart.
        reading = None if member['uncertain_pillars'] else natal_interactions(pillar, calculate_bazi(m.birth), known)
        rows.append({**row, 'status': 'born', 'luck': _luck(m, member, year), 'year_reading': reading})
    pairs = []
    for i, j in combinations(range(len(rows)), 2):
        a, b = rows[i]['luck'], rows[j]['luck']
        if not (a and b and a['pillar'] and b['pillar']):
            continue
        pa, pb = a['pillar'], b['pillar']
        pairs.append({'a': i, 'b': j, 'a_label': rows[i]['label'], 'b_label': rows[j]['label'], 'a_pillar': pa, 'b_pillar': pb,
                      'stem_combination': STEM_COMBINATIONS.get(frozenset((pa[0], pb[0]))) if pa[0] != pb[0] else None,
                      'branch_labels': _labels(pa[1], pb[1])})
    notes = [
        '流年干支是立春开始的那一年的干支，与大运页同一排法；交运当年整年记在新大运下，交运日之前的几个月实际仍属上一步大运。',
        '大运按年干阴阳与性别定顺逆，未填性别的成员只列流年。',
        '同一年的流年对每个人相同，所以成员之间只比较各自的大运：天干五合与地支同支、六合、六冲、六害、相刑。',
        '只标传统标签，不评价好坏，也不预测这一年会发生什么。',
    ]
    if any(r['hour_unknown'] for r in rows):
        notes.append('时辰不详的成员按出生当天最早与最晚的时刻各排一次大运；两者不同时并列两种可能，流年也不与时柱比较。')
    if any(r['luck'] and r['luck']['status'] == 'uncertain_pillars' for r in rows):
        notes.append('时辰不详且出生当天交节的成员，月柱可能有两种，大运无法确定；流年也不与其原局比较。')
    return {
        'year': year, 'year_pillar': pillar, 'zodiac': ANIMALS[(year - 4) % 12],
        'members': rows, 'luck_pairs': pairs,
        'rules': {'year_pillar': '立春换年，公历年对应的干支', 'luck': '与大运页相同：三日折一岁，顺逆按年干阴阳与性别',
                  'luck_links': '成员两两比较大运：天干五合，地支同支、六合、六冲、六害、相刑',
                  'year_reading': '流年与各人原局：十神、星运、空亡、干支合冲刑害、补成三合三会、神煞'},
        'notes': notes,
    }


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
    if any(m['uncertain_pillars'] for m in members):
        notes.append('时辰不详且出生当天交节（或按 23:00 换日）的成员，当天之内会变的年柱、月柱或日柱也不参与比较。')
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
        'year_view': _year_view(req, members) if req.year is not None else None,
    }
