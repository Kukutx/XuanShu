"""Specified 時家奇門 (hour-based 拆補/轉盤) school profile.

Independent implementation of public traditional tables; *not* the proprietary
implementation of a third-party platform. We expose every rule assumption,
including center-palace lodging, so alternative schools are never implicit.
"""
from __future__ import annotations

from datetime import timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .astronomy import TERMS, from_jd, solar_term_jd
from .engines import (BirthInput, BRANCHES, STEMS, _sexagenary_by_pair,
                      calculate_bazi, normalized_dt)

# The 24 terms each have an upper/middle/lower bureau. Table values are the
# standard published 時家拆補三元局数 table. Grouping is a convention, not astronomy.
BUREAU_TABLE = {
    '冬至': ('阳', (1,7,4)), '小寒': ('阳',(2,8,5)), '大寒':('阳',(3,9,6)),
    '立春': ('阳',(8,5,2)), '雨水':('阳',(9,6,3)), '惊蛰':('阳',(1,7,4)),
    '春分':('阳',(3,9,6)), '清明':('阳',(4,1,7)), '谷雨':('阳',(5,2,8)),
    '立夏':('阳',(4,1,7)), '小满':('阳',(5,2,8)), '芒种':('阳',(6,3,9)),
    '夏至':('阴',(9,3,6)), '小暑':('阴',(8,2,5)), '大暑':('阴',(7,1,4)),
    '立秋':('阴',(2,5,8)), '处暑':('阴',(1,4,7)), '白露':('阴',(9,3,6)),
    '秋分':('阴',(7,1,4)), '寒露':('阴',(6,9,3)), '霜降':('阴',(5,8,2)),
    '立冬':('阴',(6,9,3)), '小雪':('阴',(5,8,2)), '大雪':('阴',(4,7,1)),
}
# The loop of outer palaces is clockwise in the Luoshu layout.
RING = (1, 8, 3, 4, 9, 2, 7, 6)
EARTH_STEMS = tuple('戊己庚辛壬癸丁丙乙')
BASE_STARS = {1:'天蓬', 8:'天任', 3:'天冲', 4:'天辅',
              9:'天英', 2:'天芮', 7:'天柱', 6:'天心', 5:'天禽'}
BASE_DOORS = {1:'休门', 8:'生门', 3:'伤门', 4:'杜门',
              9:'景门', 2:'死门', 7:'惊门', 6:'开门'}
DOOR_RING = tuple(BASE_DOORS[p] for p in RING)
GODS = ('值符','腾蛇','太阴','六合','白虎','玄武','九地','九天')
XUN_INSTRUMENTS = ('戊','己','庚','辛','壬','癸')
PALACE_NAMES = {1: ('坎','北'), 2:('坤','西南'), 3:('震','东'),
                4:('巽','东南'),5:('中','中'),6:('乾','西北'),
                7:('兑','西'),8:('艮','东北'),9:('离','南')}
BRANCH_PALACES = (1,8,8,3,4,4,9,2,2,7,6,6)


class QimenRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    moment: BirthInput
    system: Literal['hour-qimen-chabu-rotating'] = 'hour-qimen-chabu-rotating'


def _term_at(instant):
    events = [
        (from_jd(solar_term_jd(year, lon)), name)
        for year in (instant.year - 1, instant.year, instant.year + 1)
        for name, lon, _, _ in TERMS
    ]
    earlier = [(time, name) for time, name in events if time <= instant]
    if not earlier:
        raise ValueError('No previous solar term')
    return max(earlier, key=lambda item: item[0])


def _ground(bureau: int, yang: bool) -> dict[int, str]:
    return {((bureau-1 + (i if yang else -i)) % 9)+1: stem
            for i, stem in enumerate(EARTH_STEMS)}


def _host(palace: int) -> int:
    return 2 if palace == 5 else palace


def _dark_stems(hour_stem: str, xun_instrument: str, raw_door_palace: int,
                yang: bool) -> tuple[dict[int, str], int]:
    """Place 九宫暗干 by the explicitly selected hour-chart convention.

    The raw (before center-lodging) 值使宫 is the anchor except for 甲时,
    which begins at 中五宫 with its 旬首六仪. Assign the complete nine-stem
    sequence by numeric palace order, clockwise for 阳遁 and reverse for 阴遁.
    This is a *school-specific* rule, not a claim of universal agreement.
    """
    if hour_stem not in STEMS or xun_instrument not in XUN_INSTRUMENTS:
        raise ValueError('Unsupported Qimen stem / xun instrument')
    if not 1 <= raw_door_palace <= 9:
        raise ValueError('Invalid raw door palace')
    start_stem = xun_instrument if hour_stem == '甲' else hour_stem
    anchor = 5 if hour_stem == '甲' else raw_door_palace
    offset = EARTH_STEMS.index(start_stem)
    result = {((anchor - 1 + (i if yang else -i)) % 9) + 1:
              EARTH_STEMS[(offset + i) % 9] for i in range(9)}
    return result, anchor


def qimen_chart(req: QimenRequest) -> dict:
    """Hour-based decomposed 3-yuan rotating plate with explicit uncertainty."""
    instant = normalized_dt(req.moment)
    bazi = calculate_bazi(req.moment)
    day = bazi['pillars']['day']; hour = bazi['pillars']['hour']
    day_index = _sexagenary_by_pair(STEMS.index(day['stem']), BRANCHES.index(day['branch']))
    hour_index = _sexagenary_by_pair(STEMS.index(hour['stem']), BRANCHES.index(hour['branch']))
    term_time, term = _term_at(instant.astimezone(timezone.utc))
    # The symbolic head of each 5-day group is 甲 or 己. Its earthly branch
    # determines the upper/middle/lower grouping.
    preceding_in_group = day_index % 5
    head_branch = BRANCHES[(BRANCHES.index(day['branch'])-preceding_in_group)%12]
    yuan_index = {0:0, 2:1, 1:2}[BRANCHES.index(head_branch)%3]
    yuan = ('上元','中元','下元')[yuan_index]
    dun, bureau_numbers = BUREAU_TABLE[term]
    bureau = bureau_numbers[yuan_index]
    earth = _ground(bureau, dun=='阳')
    xun_index = hour_index // 10
    xun_branch = BRANCHES[(xun_index*10)%12]
    xun = '甲'+xun_branch
    instrument = XUN_INSTRUMENTS[xun_index]
    original_raw = next(g for g, stem in earth.items() if stem == instrument)
    original = _host(original_raw)
    active_stem = instrument if hour['stem'] == '甲' else hour['stem']
    destination_raw = next(g for g, stem in earth.items() if stem == active_stem)
    destination = _host(destination_raw)

    # Rotate outer-ring star positions from the original xun-head stem palace
    # to the current hour stem palace. Heavenly stems move *with* the stars.
    delta = (RING.index(destination)-RING.index(original))%8
    stars, heaven = {}, {}
    for original_palace in RING:
        target_palace = RING[(RING.index(original_palace)+delta)%8]
        stars[target_palace] = BASE_STARS[original_palace]
        heaven[target_palace] = earth[original_palace]
    stars[5] = '天禽'
    heaven[5] = earth[5]
    zhi_fu_star = BASE_STARS[original]

    # Door messenger flies through 1...9 numerical palaces by hour offset,
    # lodges center in Kun(2), then eight doors rotate around outer ring.
    offset = hour_index % 10
    door_raw = ((original_raw - 1 + (offset if dun=='阳' else -offset))%9)+1
    door_target = _host(door_raw)
    dark_stems, dark_stem_anchor = _dark_stems(hour['stem'], instrument, door_raw,
                                               dun == '阳')
    zhi_shi = BASE_DOORS[original]
    door_shift = (RING.index(door_target)-DOOR_RING.index(zhi_shi))%8
    doors = {RING[(i+door_shift)%8]: name for i, name in enumerate(DOOR_RING)}
    gods = {RING[(RING.index(destination)+(i if dun=='阳' else -i))%8]: name
            for i, name in enumerate(GODS)}
    void_branches = [BRANCHES[(BRANCHES.index(xun_branch)+i)%12] for i in (10,11)]
    void_palaces = sorted(set(BRANCH_PALACES[BRANCHES.index(x)] for x in void_branches))

    palaces = []
    for index in range(1,10):
        trigram, direction = PALACE_NAMES[index]
        palaces.append({'number':index, 'trigram':trigram,'direction':direction,
                        'earth_stem':earth[index],'heaven_stem':heaven[index],
                        'dark_stem':dark_stems[index],
                        'star':stars[index], 'door':doors.get(index),
                        'deity':gods.get(index),'void':index in void_palaces,
                        'center_lodged_here':index==2 and (original_raw==5 or destination_raw==5 or door_raw==5)})
    return {
        'system':'hour-qimen-chabu-rotating', 'method':'时家拆补 · 转盘外环 · 中五寄二',
        'instant':instant.isoformat(), 'time_basis':bazi['time_basis'],
        'solar_term':term, 'solar_term_instant':term_time.isoformat(),
        'dun':dun+'遁', 'bureau':bureau, 'yuan':yuan,
        'day_pillar':day['text'], 'hour_pillar':hour['text'],
        'fu_tou_branch':head_branch, 'xun_head':xun, 'xun_instrument':instrument,
        'zhi_fu_star':zhi_fu_star, 'zhi_fu_origin':original, 'zhi_fu_palace':destination,
        'zhi_shi_door':zhi_shi, 'zhi_shi_palace':door_target,
        'zhi_shi_raw_palace':door_raw,
        'dark_stem_anchor':dark_stem_anchor,
        'dark_stem_rule':'时干甲寄中五并取旬首六仪；其余以值使原始落宫起局，阴逆阳顺按1–9宫数排九干',
        'void_branches':void_branches, 'void_palaces':void_palaces,
        'palaces':palaces,
        'limitations':[
            '仅实现明确列出的时家拆补转盘配置，不涵盖置闰、茅山、飞盘、鸣法、刻家等流派。',
            '中五宫寄二宫是可争议的传统规则，外环星、门、神和天盘干按本项目固定旋转方式推导。',
            '五组公开样本已核对关键局数及九宫暗干；天盘、门星神与其他日期仍缺完整异源逐宫验收。',
            '九宫和星门神只是传统文化标签，没有经过科学证实的预测力，不提供吉凶或现实择时建议。',
        ],
    }
