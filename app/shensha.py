"""Traditional auxiliary stars (神煞) of a BaZi chart, each with the rule that places it and where it comes from.

Only stars whose placement could be read in a classical text are included; ``source`` names the chapter of
the 三命通会 (Ming dynasty, 万民英). 红鸾 and 天喜 use the Zi Wei Dou Shu table the Zi Wei chart here already
applies. Stars with competing tables (文昌, 太极, 福星, 国印, 学堂 and 词馆 by day stem, ...) are left out until
one table can be cited. These are traditional labels only: no good-or-bad reading and no score.
"""
from __future__ import annotations

TRIADS = ('申子辰', '寅午戌', '巳酉丑', '亥卯未')
SEASONS = ('寅卯辰', '巳午未', '申酉戌', '亥子丑')
BRANCH_ORDER = '子丑寅卯辰巳午未申酉戌亥'
KUIGANG = ('庚辰', '壬辰', '戊戌', '庚戌')


def _by_group(groups: tuple[str, ...], targets: str) -> dict[str, str]:
    """Each branch of a group mapped to that group's target."""
    return {branch: target for group, target in zip(groups, targets) for branch in group}


# looks_at: which part of each pillar is compared with the table entry: its branch, its stem, either, or (for
# 魁罡) the whole day pillar. bases: the natal values the table is read from, in the order they are tried.
RULES = (
    {'name': '天乙贵人', 'bases': ('day_stem', 'year_stem'), 'looks_at': 'branch',
     'table': {'甲': '丑未', '戊': '丑未', '庚': '丑未', '乙': '子申', '己': '子申', '丙': '亥酉', '丁': '亥酉',
               '辛': '寅午', '壬': '卯巳', '癸': '卯巳'},
     'rule': '甲戊庚见丑未，乙己见子申，丙丁见亥酉，辛见寅午，壬癸见卯巳；以日干、年干查四柱地支',
     'source': '《三命通会》卷三·论天乙贵人'},
    {'name': '禄神', 'bases': ('day_stem',), 'looks_at': 'branch',
     'table': {'甲': '寅', '乙': '卯', '丙': '巳', '丁': '午', '戊': '巳', '己': '午', '庚': '申', '辛': '酉', '壬': '亥', '癸': '子'},
     'rule': '甲禄寅，乙禄卯，丙戊禄巳，丁己禄午，庚禄申，辛禄酉，壬禄亥，癸禄子；以日干查',
     'source': '《三命通会》卷三·论十干禄'},
    {'name': '羊刃', 'bases': ('day_stem',), 'looks_at': 'branch',
     'table': {'甲': '卯', '丙': '午', '戊': '午', '庚': '酉', '壬': '子'},
     'rule': '五阳干有刃，在禄前一位：甲卯，丙戊午，庚酉，壬子；阴干不取；以日干查',
     'source': '《三命通会》卷三·论羊刃'},
    {'name': '驿马', 'bases': ('year_branch', 'day_branch'), 'looks_at': 'branch', 'table': _by_group(TRIADS, '寅申亥巳'),
     'rule': '申子辰马在寅，寅午戌马在申，巳酉丑马在亥，亥卯未马在巳；以年支、日支查',
     'source': '《三命通会》卷三·论驿马'},
    {'name': '咸池', 'bases': ('year_branch', 'day_branch'), 'looks_at': 'branch', 'table': _by_group(TRIADS, '酉卯午子'),
     'rule': '三合长生后一位（沐浴）：申子辰见酉，寅午戌见卯，巳酉丑见午，亥卯未见子，俗称桃花；以年支、日支查',
     'source': '《三命通会》卷二·论咸池'},
    {'name': '将星', 'bases': ('year_branch', 'day_branch'), 'looks_at': 'branch', 'table': _by_group(TRIADS, '子午酉卯'),
     'rule': '三合中位：申子辰见子，寅午戌见午，巳酉丑见酉，亥卯未见卯；以年支、日支查',
     'source': '《三命通会》卷二·论将星华盖'},
    {'name': '华盖', 'bases': ('year_branch', 'day_branch'), 'looks_at': 'branch', 'table': _by_group(TRIADS, '辰戌丑未'),
     'rule': '三合之库：申子辰见辰，寅午戌见戌，巳酉丑见丑，亥卯未见未；以年支、日支查',
     'source': '《三命通会》卷二·论将星华盖'},
    {'name': '劫煞', 'bases': ('year_branch', 'day_branch'), 'looks_at': 'branch', 'table': _by_group(TRIADS, '巳亥寅申'),
     'rule': '申子辰以巳，寅午戌以亥，巳酉丑以寅，亥卯未以申为劫煞；以年支、日支查',
     'source': '《三命通会》卷三·论劫煞亡神'},
    {'name': '亡神', 'bases': ('year_branch', 'day_branch'), 'looks_at': 'branch', 'table': _by_group(TRIADS, '亥巳申寅'),
     'rule': '申子辰以亥，寅午戌以巳，巳酉丑以申，亥卯未以寅为亡神；以年支、日支查',
     'source': '《三命通会》卷三·论劫煞亡神'},
    {'name': '孤辰', 'bases': ('year_branch',), 'looks_at': 'branch', 'table': _by_group(SEASONS, '巳申亥寅'),
     'rule': '寅卯辰见巳，巳午未见申，申酉戌见亥，亥子丑见寅；以年支查',
     'source': '《三命通会》卷三·论孤辰寡宿'},
    {'name': '寡宿', 'bases': ('year_branch',), 'looks_at': 'branch', 'table': _by_group(SEASONS, '丑辰未戌'),
     'rule': '寅卯辰见丑，巳午未见辰，申酉戌见未，亥子丑见戌；以年支查',
     'source': '《三命通会》卷三·论孤辰寡宿'},
    {'name': '天德贵人', 'bases': ('month_branch',), 'looks_at': 'stem_or_branch',
     'table': {'寅': '丁', '卯': '申', '辰': '壬', '巳': '辛', '午': '亥', '未': '甲', '申': '癸', '酉': '寅', '戌': '丙',
               '亥': '乙', '子': '巳', '丑': '庚'},
     # One literal: the interface translates whole strings.
     'rule': '正月丁，二月坤，三月壬，四月辛，五月乾，六月甲，七月癸，八月艮，九月丙，十月乙，十一月巽，十二月庚；坤乾艮巽按通行做法取申亥寅巳；以月支查四柱干支',
     'source': '《三命通会》卷三·论天月德（原文举正月丁、二月坤、三月壬、四月辛，其余各月按通行表）'},
    {'name': '月德贵人', 'bases': ('month_branch',), 'looks_at': 'stem', 'table': _by_group(TRIADS, '壬丙庚甲'),
     'rule': '寅午戌月丙，申子辰月壬，亥卯未月甲，巳酉丑月庚；以月支查四柱天干',
     'source': '《三命通会》卷三·论天月德'},
    {'name': '红鸾', 'bases': ('year_branch',), 'looks_at': 'branch',
     'table': {b: BRANCH_ORDER[(3 - i) % 12] for i, b in enumerate(BRANCH_ORDER)},
     'rule': '子年在卯，逆行十二支（丑年在寅，寅年在丑……亥年在辰）；以年支查',
     'source': '紫微斗数安星法，与本站紫微盘同表（已逐盘对照 iztro）'},
    {'name': '天喜', 'bases': ('year_branch',), 'looks_at': 'branch',
     'table': {b: BRANCH_ORDER[(9 - i) % 12] for i, b in enumerate(BRANCH_ORDER)},
     'rule': '红鸾对宫：子年在酉，逆行十二支；以年支查',
     'source': '紫微斗数安星法，与本站紫微盘同表（已逐盘对照 iztro）'},
    {'name': '魁罡', 'bases': ('day_pillar',), 'looks_at': 'pillar', 'table': {p: p for p in KUIGANG},
     'rule': '日柱为庚辰、壬辰、戊戌、庚戌',
     'source': '《三命通会》卷六·魁罡'},
)
RULE_BY_NAME = {rule['name']: rule for rule in RULES}
BASIS_KEYS = ('day_stem', 'year_stem', 'day_branch', 'year_branch', 'month_branch', 'day_pillar')


def natal_bases(pillars: dict[str, str]) -> dict[str, str]:
    """The natal values the tables are read from, keyed like ``RULES[...]['bases']``."""
    return {'day_stem': pillars['day'][0], 'year_stem': pillars['year'][0], 'day_branch': pillars['day'][1],
            'year_branch': pillars['year'][1], 'month_branch': pillars['month'][1], 'day_pillar': pillars['day']}


def stars_on(pillar: str, bases: dict[str, str], day_pillar: bool = False) -> list[dict]:
    """The stars a pillar (natal, luck or year) carries, each with the natal values that place it there.

    魁罡 belongs to the day pillar itself, so it is only checked when ``day_pillar`` is true.
    """
    found = []
    for rule in RULES:
        if rule['looks_at'] == 'pillar':
            if day_pillar and pillar in rule['table']:
                found.append({'name': rule['name'], 'by': [{'basis': 'day_pillar', 'value': pillar}]})
            continue
        parts = {'branch': pillar[1], 'stem': pillar[0], 'stem_or_branch': pillar}[rule['looks_at']]
        by = [{'basis': basis, 'value': bases[basis]} for basis in rule['bases']
              if (target := rule['table'].get(bases[basis])) and any(part in target for part in parts)]
        if by:
            found.append({'name': rule['name'], 'by': by})
    return found


def natal_shensha(pillars: dict[str, str]) -> dict[str, list[dict]]:
    """Stars on each of the four natal pillars."""
    bases = natal_bases(pillars)
    return {key: stars_on(text, bases, key == 'day') for key, text in pillars.items()}


def rule_notes(names) -> list[dict]:
    """How each named star is placed and where the rule comes from, in table order."""
    wanted = set(names)
    return [{'name': rule['name'], 'rule': rule['rule'], 'source': rule['source']} for rule in RULES if rule['name'] in wanted]
