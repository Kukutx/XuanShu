"""Auditable Zi Wei star/cycle placement extensions for one published school.

These are independent calculations of traditional, publicly documented
placement rules (https://docs.iztro.com/learn/setup). They express conventional
symbolic placements, not empirical predictions. Cycle labels derived from the
birth year must not be confused with a complete chart for a queried future year.

Indices use 子=0 ... 亥=11. Keep every rule explicit and testable.
"""
from __future__ import annotations

from .reference import FOUR_TYPES

LIFEMASTER_BY_BRANCH = ('贪狼','巨门','禄存','文曲','廉贞','武曲',
                        '破军','武曲','廉贞','文曲','禄存','巨门')
BODYMASTER_BY_YEAR_BRANCH = ('火星','天相','天梁','天同','文昌','天机',
                             '火星','天相','天梁','天同','文昌','天机')
CHANGSHENG = ('长生','沐浴','冠带','临官','帝旺','衰','病','死','墓','绝','胎','养')
BOSHI = ('博士','力士','青龙','小耗','将军','奏书','飞廉','喜神','病符','大耗','伏兵','官府')
SUIQIAN = ('岁建','晦气','丧门','贯索','官符','小耗','大耗','龙德','白虎','天德','吊客','病符')
JIANGQIAN = ('将星','攀鞍','岁驿','息神','华盖','劫煞','灾煞','天煞','指背','咸池','月煞','亡神')
CHANGSHENG_START_BY_BUREAU = {2: 8, 3: 11, 4: 5, 5: 8, 6: 2}
TIANCHU_BY_STEM = (5, 6, 0, 5, 6, 8, 2, 6, 9, 11)
TIANYUE_BY_MONTH = (10, 5, 4, 2, 7, 3, 11, 7, 2, 6, 10, 2)
YINSHA_BY_MONTH = (2, 0, 10, 8, 6, 4)
TIANWU_BY_MONTH = (5, 8, 2, 11)
FEILIAN_BY_BRANCH = (8, 9, 10, 5, 6, 7, 2, 3, 4, 11, 0, 1)
# Brightness by palace branch, 子 to 亥, as indexes into BRIGHTNESS_LEVELS (0 strongest, 6 weakest): the
# table iztro publishes (data/stars.ts) for the 14 main stars and six minor ones. A dot marks a branch the
# star never occupies. Schools grade 得, 利 and 平 differently; this is one published table, not the only one.
# iztro is MIT-licensed (Copyright (c) 2023 All Contributors); its notice is in THIRD_PARTY_NOTICES.md.
BRIGHTNESS_LEVELS = '庙旺得利平不陷'
_BRIGHTNESS_CODES = {
    '紫微': '401121001121',
    '天机': '062134062134',
    '太阳': '651011122456',
    '武曲': '102304102304',
    '天同': '153440651440',
    '廉贞': '430436430436',
    '天府': '000202102102',
    '太阴': '001666553110',
    '贪狼': '104306104306',
    '巨门': '150061150061',
    '天相': '000622020622',
    '天梁': '010006016206',
    '七杀': '100104100104',
    '破军': '012614012614',
    '文昌': '206320632063',
    '文曲': '204120612061',
    '火星': '620362036203',
    '铃星': '620362036203',
    '擎羊': '60.60.60.60.',
    '陀罗': '.06.06.06.06',
}
BRIGHTNESS = {star: tuple(None if code == '.' else BRIGHTNESS_LEVELS[int(code)] for code in codes)
              for star, codes in _BRIGHTNESS_CODES.items()}


def _horse_group(year_branch: int) -> int:
    """In which four branch-trine groups the birth branch resides."""
    if year_branch in (8, 0, 4):  # 申子辰
        return 0
    if year_branch in (1, 5, 9):  # 巳酉丑
        return 1
    if year_branch in (2, 6, 10):  # 寅午戌
        return 2
    return 3  # 亥卯未


def adjunct_stars(lunar_day: int, month: int, hour_branch: int,
                  year_stem: int, year_branch: int, ming: int,
                  shen: int, base: dict[str, int]) -> dict[str, int]:
    """26 additional named placements, never overwriting earlier natal stars."""
    assert 1 <= lunar_day <= 30 and 1 <= month <= 12
    group = _horse_group(year_branch)
    fire_bell = ((2, 10), (3, 10), (1, 3), (9, 10))[group]
    # Year-branch groups by contiguous season: 寅卯辰、巳午未、申酉戌、亥子丑.
    seasonal = ((5, 1), (8, 4), (11, 7), (2, 10))[((year_branch - 2) % 12)//3]
    # 辰/丑/戌/未 and 酉/午/卯/子 in traditional 三合 groups.
    huagai = (4, 1, 10, 7)[group]
    xianchi = (9, 6, 3, 0)[group]
    result = {
        '火星': (fire_bell[0] + hour_branch) % 12,
        '铃星': (fire_bell[1] + hour_branch) % 12,
        # 台辅 from 午 and 封诰 from 寅 at the Zi hour, both counting forward to the birth hour.
        '台辅': (6 + hour_branch) % 12,
        '封诰': (2 + hour_branch) % 12,
        '月解': (8 + 2 * ((month-1)//2)) % 12,
        '天巫': TIANWU_BY_MONTH[(month-1) % 4],
        '天月': TIANYUE_BY_MONTH[month-1],
        '阴煞': YINSHA_BY_MONTH[(month-1) % 6],
        '天空': (year_branch + 1) % 12,
        '天哭': (6 - year_branch) % 12,
        '天虚': (6 + year_branch) % 12,
        '孤辰': seasonal[0],
        '寡宿': seasonal[1],
        '蜚廉': FEILIAN_BY_BRANCH[year_branch],
        '破碎': 5 if year_branch in (0, 3, 6, 9) else (9 if year_branch in (2, 5, 8, 11) else 1),
        '华盖': huagai,
        '咸池': xianchi,
        '天才': (ming + year_branch) % 12,
        '天寿': (shen + year_branch) % 12,
        '三台': (base['左辅'] + lunar_day - 1) % 12,
        '八座': (base['右弼'] - (lunar_day - 1)) % 12,
        '恩光': (base['文昌'] + lunar_day - 2) % 12,
        '天贵': (base['文曲'] + lunar_day - 2) % 12,
        '天厨': TIANCHU_BY_STEM[year_stem],
        '天伤': (ming - 7) % 12,  # 仆役宫
        '天使': (ming - 5) % 12,  # 疾厄宫
    }
    if base.keys() & result.keys():
        raise ValueError('Zi Wei star groups overlap')
    return result


def year_branch_cycles(year_branch: int) -> dict[str, dict[int, str]]:
    """Sui-qian and jiang-qian cycles of one year branch, for the birth year or for a year layer."""
    jiangxing_start = (0, 9, 6, 3)[_horse_group(year_branch)]  # 申子辰→子、巳酉丑→酉、寅午戌→午、亥卯未→卯
    return {
        'suiqian': {(year_branch + i) % 12: name for i, name in enumerate(SUIQIAN)},
        'jiangqian': {(jiangxing_start + i) % 12: name for i, name in enumerate(JIANGQIAN)},
    }


def cycle_positions(bureau: int, lucun: int, year_stem: int,
                    year_branch: int, gender: str) -> dict[str, dict[int, str]]:
    """Four 12-position named cycles; gender-dependent cycles may be absent."""
    yearly = year_branch_cycles(year_branch)
    data = {'natal_suiqian': yearly['suiqian'], 'natal_jiangqian': yearly['jiangqian']}
    if gender in ('male', 'female'):
        forward = (year_stem % 2 == 0) == (gender == 'male')
        step = 1 if forward else -1
        data['changsheng'] = {(CHANGSHENG_START_BY_BUREAU[bureau]+i*step) % 12: name
                              for i, name in enumerate(CHANGSHENG)}
        data['boshi'] = {(lucun+i*step) % 12: name for i, name in enumerate(BOSHI)}
    return data


def nominal_small_limit_ages(year_branch: int, gender: str, branch: int,
                              through_age: int = 120) -> list[int]:
    """Traditional nominal (虚岁) ages per natal palace; not birthday-to-birthday ages."""
    if gender == 'unspecified':
        return []
    start = (10, 7, 4, 1)[_horse_group(year_branch)]
    step = 1 if gender == 'male' else -1
    return [age for age in range(1, through_age + 1)
            if (start + (age - 1)*step) % 12 == branch]
