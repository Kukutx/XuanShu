"""Check a chart pasted from other software against XuanShu, field by field.

The pasted text is parsed for what charts commonly print: the four pillars, the
Zi Wei Life and Body palaces, the five-elements bureau, the Life and Body
masters, the major stars of each palace (with their brightness when printed)
and the birth-year transformations.
Each recognized field is compared with XuanShu's chart for the same birth data.
When fields differ, the same birth is recomputed under the rule choices that
commonly differ between programs, and every variant that reproduces the pasted
chart is reported. Nothing is stored; the text is data, never instructions.
"""
from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .engines import BRANCHES, STEMS, BirthInput, calculate_bazi, calculate_ziwei, normalized_dt
from .reference import FOUR_TYPES
from .ziwei_extensions import BODYMASTER_BY_YEAR_BRANCH, BRIGHTNESS_LEVELS, LIFEMASTER_BY_BRANCH

MAJOR_STARS = ('紫微', '天机', '太阳', '武曲', '天同', '廉贞', '天府', '太阴', '贪狼', '巨门', '天相', '天梁', '七杀', '破军')
TRANSFORMING_STARS = MAJOR_STARS + ('文昌', '文曲', '左辅', '右弼')
MASTER_STARS = frozenset(LIFEMASTER_BY_BRANCH + BODYMASTER_BY_YEAR_BRANCH)
# Pasted name -> XuanShu palace name. 交友/奴仆 and 事业 are common alternative names.
PALACE_ALIASES = {
    '命宫': '命宫', '兄弟': '兄弟宫', '夫妻': '夫妻宫', '子女': '子女宫', '财帛': '财帛宫', '疾厄': '疾厄宫',
    '迁移': '迁移宫', '仆役': '仆役宫', '交友': '仆役宫', '奴仆': '仆役宫', '官禄': '官禄宫', '事业': '官禄宫',
    '田宅': '田宅宫', '福德': '福德宫', '父母': '父母宫',
}
# Traditional characters that appear in chart terms, so charts from Taiwan and Hong Kong parse too.
TRADITIONAL = str.maketrans('宮財遷僕祿機陽貞貪門軍權時殺陰輔羅鈴鉞業體帛無於廟', '宫财迁仆禄机阳贞贪门军权时杀阴辅罗铃钺业体帛无于庙')
STEM_CLASS, BRANCH_CLASS = '[' + ''.join(STEMS) + ']', '[' + ''.join(BRANCHES) + ']'
PALACE_PATTERN = re.compile('(' + '|'.join(sorted(PALACE_ALIASES, key=len, reverse=True)) + r')\s*宫?')
PILLAR_NAMES = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}
TYPE_NAMES = {t: '生年' + t for t in FOUR_TYPES}
# A brightness grade printed right after a star name: 紫微庙, 七杀(平), 天府【得】.
BRIGHTNESS_AFTER = r'\s*[（(【\[]?\s*([' + BRIGHTNESS_LEVELS + '])'


class ChartImportRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    text: str = Field(min_length=1, max_length=6000, description='Chart text copied from other software')


def _valid_pair(stem: str, branch: str) -> bool:
    return STEMS.index(stem) % 2 == BRANCHES.index(branch) % 2


def parse_chart_text(text: str) -> dict:
    """Fields recognized in pasted chart text; absent fields are left out."""
    # One character per whitespace run keeps the optional-separator patterns below linear on long padding.
    text = re.sub(r'\s+', lambda m: '\n' if '\n' in m.group() else ' ', text.translate(TRADITIONAL))
    parsed: dict = {}
    pillars = {}
    for key, label in PILLAR_NAMES.items():
        m = re.search(label + r'\s*[：:]?\s*(' + STEM_CLASS + ')(' + BRANCH_CLASS + ')', text)
        if m and _valid_pair(*m.groups()):
            pillars[key] = m.group(1) + m.group(2)
    if len(pillars) < 3:
        # Unlabelled: the first run of three or four stem-branch pairs separated only by spaces or punctuation.
        tokens = [(m.start(), m.group()) for m in re.finditer(STEM_CLASS + BRANCH_CLASS, text) if _valid_pair(*m.group())]
        run: list[tuple[int, str]] = []
        for pos, pair in tokens:
            if run and (pos - run[-1][0] > 5 or re.search(r'[一-鿿\n]', text[run[-1][0] + 2:pos])):
                if len(run) >= 3:
                    break
                run = []
            run.append((pos, pair))
            if len(run) == 4:
                break
        if len(run) >= 3:
            pillars = dict(zip(('year', 'month', 'day', 'hour'), (pair for _, pair in run)))
    if pillars:
        parsed['pillars'] = pillars

    m = re.search(r'([水木金土火])\s*([二三四五六23456])\s*局', text)
    if m:
        number = m.group(2) if m.group(2) in '二三四五六' else '二三四五六'[int(m.group(2)) - 2]
        parsed['bureau'] = m.group(1) + number + '局'
    for key, label in (('ming_master', '命主'), ('shen_master', '身主')):
        m = re.search(label + r'\s*[：:]?\s*([一-鿿]{2})', text)
        if m and m.group(1) in MASTER_STARS:
            parsed[key] = m.group(1)
    connector = r'\s*(?:在|位于|落|[：:（(【\[])?\s*'
    m = re.search('命宫' + connector + STEM_CLASS + '?(' + BRANCH_CLASS + r')(?!\s*女)', text)
    if m:
        parsed['ming_branch'] = m.group(1)
    m = re.search('身宫' + connector + '(' + '|'.join(sorted(PALACE_ALIASES, key=len, reverse=True)) + ')', text)
    if m:
        parsed['shen_palace'] = PALACE_ALIASES[m.group(1)]
    else:
        m = re.search('身宫' + connector + STEM_CLASS + '?(' + BRANCH_CLASS + r')(?!\s*女)', text)
        if m:
            parsed['shen_branch'] = m.group(1)

    transformations = {}
    for m in re.finditer('(' + '|'.join(TRANSFORMING_STARS) + r')\s*化\s*([禄权科忌])', text):
        transformations.setdefault('化' + m.group(2), m.group(1))
    if transformations:
        parsed['transformations'] = transformations

    # Major stars per palace: the text after a palace name up to the next palace name or line break.
    # Life/Body master mentions are blanked first so a master star is not read as a star of the palace.
    body = re.sub(r'[命身]主\s*[：:]?\s*[一-鿿]{2}', lambda m: ' ' * len(m.group()), text)
    body = re.sub(r'[命身]宫\s*(?:在|位于|落)', lambda m: ' ' * len(m.group()), body)
    palaces, brightness = {}, {}
    for line in body.splitlines():
        found = list(PALACE_PATTERN.finditer(line))
        for i, m in enumerate(found):
            segment = line[m.end(): found[i + 1].start() if i + 1 < len(found) else len(line)]
            stars = [s for s in MAJOR_STARS if s in segment]
            name = PALACE_ALIASES[m.group(1)]
            if stars or re.search(r'空宫|无\s*主星', segment):
                palaces.setdefault(name, sorted(stars, key=MAJOR_STARS.index))
            levels = {s: g.group(1) for s in stars if (g := re.search(s + BRIGHTNESS_AFTER, segment))}
            if levels and name not in brightness:
                brightness[name] = levels
    if palaces:
        parsed['palace_major_stars'] = palaces
    if brightness:
        parsed['palace_brightness'] = brightness
    return parsed


def _compare(parsed: dict, bazi: dict, ziwei: dict) -> list[dict]:
    fields = []

    def add(key: str, label: str, theirs, ours):
        fields.append({'key': key, 'label': label, 'theirs': theirs, 'ours': ours, 'match': theirs == ours})

    for key, pair in parsed.get('pillars', {}).items():
        add('pillar.' + key, PILLAR_NAMES[key], pair, bazi['pillars'][key]['text'])
    by_name = {p['name']: p for p in ziwei['palaces']}
    shen = next(p for p in ziwei['palaces'] if p['is_shen'])
    if 'ming_branch' in parsed:
        add('ziwei.ming_branch', '命宫地支', parsed['ming_branch'], ziwei['ming_palace'])
    if 'shen_branch' in parsed:
        add('ziwei.shen_branch', '身宫地支', parsed['shen_branch'], ziwei['shen_palace'])
    if 'shen_palace' in parsed:
        add('ziwei.shen_palace', '身宫所在宫', parsed['shen_palace'], shen['name'])
    if 'bureau' in parsed:
        add('ziwei.bureau', '五行局', parsed['bureau'], ziwei['five_elements_bureau'])
    if 'ming_master' in parsed:
        add('ziwei.ming_master', '命主', parsed['ming_master'], ziwei['ming_master'])
    if 'shen_master' in parsed:
        add('ziwei.shen_master', '身主', parsed['shen_master'], ziwei['shen_master'])
    for name, stars in parsed.get('palace_major_stars', {}).items():
        ours = sorted(by_name[name]['main_stars'], key=MAJOR_STARS.index)
        add('ziwei.palace.' + name, name + '主星', '、'.join(stars) or '空宫', '、'.join(ours) or '空宫')
    # Brightness is compared only for stars that sit in the same palace on both charts.
    for name, levels in parsed.get('palace_brightness', {}).items():
        mine = by_name[name]['star_brightness']
        shared = [star for star in levels if star in mine]
        if shared:
            add('ziwei.brightness.' + name, name + '主星亮度', '、'.join(star + levels[star] for star in shared),
                '、'.join(star + mine[star] for star in shared))
    ours_hua = {t['type']: t['star'] for t in ziwei['birth_year_transformations']}
    for kind, star in parsed.get('transformations', {}).items():
        add('ziwei.transformation.' + kind, TYPE_NAMES[kind], star, ours_hua.get(kind))
    return fields


def _variants(birth: BirthInput) -> list[tuple[str, BirthInput]]:
    """Rule choices that commonly differ between programs, as alternative inputs."""
    base = birth.model_dump()
    options = [('23:00 换日（早晚子时）' if not birth.late_zi_day_rollover else '00:00 换日',
                {'late_zi_day_rollover': not birth.late_zi_day_rollover}),
               ('闰月整月按本月' if birth.leap_month_second_half_as_next else '闰月后半月按下月',
                {'leap_month_second_half_as_next': not birth.leap_month_second_half_as_next})]
    if birth.longitude is not None:
        modes = {'clock': '钟表时间', 'mean_solar': '平太阳时', 'apparent_solar': '真太阳时'}
        options += [(modes[mode], {'time_mode': mode}) for mode in modes if mode != birth.time_mode]
    dt = normalized_dt(birth)
    if dt.dst():
        standard = (dt - dt.dst()).replace(tzinfo=None).isoformat(timespec='minutes')
        # Read the same instant on standard time: a fixed-offset zone keeps the instant and avoids
        # nonexistent wall times. Etc/GMT zones exist for whole hours only (their sign is inverted).
        hours, rest = divmod(int((dt.utcoffset() - dt.dst()).total_seconds()), 3600)
        change = {'birth_datetime': standard}
        if not rest:
            change['timezone'] = f'Etc/GMT{-hours:+d}' if hours else 'Etc/GMT'
        options.append(('扣除夏令时（按标准时）', change))
    singles = [(label, BirthInput(**{**base, **change})) for label, change in options]
    # Pairs of changes too: programs often differ in more than one rule at once.
    pairs = []
    for i, (label_a, change_a) in enumerate(options):
        for label_b, change_b in options[i + 1:]:
            if set(change_a) & set(change_b):
                continue
            pairs.append((label_a + ' + ' + label_b, BirthInput(**{**base, **change_a, **change_b})))
    return singles + pairs


def _causes(birth: BirthInput, fields: list[dict], bazi: dict, ziwei: dict) -> list[str]:
    wrong = {f['key'] for f in fields if not f['match']}
    causes = []
    dt = normalized_dt(birth)
    if 'pillar.year' in wrong and bazi['pillars']['year']['text'] != ziwei['year_pillar']:
        causes.append('出生在立春与春节之间：玄枢八字以立春换年，对方可能以春节（正月初一）换年。')
    if 'pillar.month' in wrong or 'pillar.year' in wrong:
        for side in ('previous', 'next'):
            jie = bazi['jie_boundaries'][side]
            hours = abs((dt - datetime.fromisoformat(jie['instant'])).total_seconds()) / 3600
            if hours < 48:
                causes.append(f'出生时刻离{jie["name"]}交节只有约 {hours:.1f} 小时：对方的节气时刻、时区或夏令时处理可能不同。')
    effective_hour = int(bazi['time_basis']['effective_local_reading'][11:13])
    if wrong & {'pillar.day', 'pillar.hour'} and effective_hour == 23:
        causes.append('出生在 23:00 之后：各家对子时是否换日（早晚子时）规则不同。')
    if dt.dst():
        causes.append('出生时当地实行夏令时：有的软件会先扣除夏令时再排盘。')
    if birth.time_mode == 'clock' and wrong & {'pillar.hour', 'ziwei.ming_branch', 'ziwei.shen_branch'}:
        causes.append('对方可能按真太阳时排盘：在出生资料里填写经度后可以一起比较。' if birth.longitude is None
                      else '对方可能按平太阳时或真太阳时排盘。')
    if ziwei['lunar_date']['is_leap_month'] and any(k.startswith('ziwei.') for k in wrong):
        causes.append('出生在农历闰月：闰月前后半月归属哪个月，各家规则不同。')
    if 'pillar.hour' in wrong and any(k.startswith('ziwei.') for k in wrong):
        causes.append('时辰不同会连带改变命宫、身宫和星曜位置，先核对出生时间。')
    if any(k.startswith('ziwei.transformation') for k in wrong):
        causes.append('四化表因流派而异（例如庚、壬年的化科化忌），玄枢使用《紫微斗数全书》表。')
    if any(k.startswith('ziwei.brightness') for k in wrong):
        causes.append('星曜亮度表因流派而异（得、利、平的判定尤其不同），玄枢使用 iztro 公开的亮度表；星曜落宫一致时，亮度不同只是表不同。')
    return causes


def chart_import_check(req: ChartImportRequest) -> dict:
    parsed = parse_chart_text(req.text)
    bazi, ziwei = calculate_bazi(req.birth), calculate_ziwei(req.birth)
    fields = _compare(parsed, bazi, ziwei)
    mismatched = [f for f in fields if not f['match']]
    variants = []
    # Rule variants move stars; when only brightness grades differ there is nothing for them to explain.
    if any(not f['key'].startswith('ziwei.brightness') for f in mismatched):
        for label, alternative in _variants(req.birth):
            try:
                alt_fields = _compare(parsed, calculate_bazi(alternative), calculate_ziwei(alternative))
            except ValueError:
                continue
            # A brightness table is a school choice no rule variant changes, so it does not count against one.
            wrong = [f['label'] for f in alt_fields if not f['match'] and not f['key'].startswith('ziwei.brightness')]
            variants.append({'label': label, 'settings': alternative.model_dump(exclude_none=True),
                             'mismatched': len(wrong), 'mismatched_fields': wrong})
        variants.sort(key=lambda v: (v['mismatched'], v['label'].count('+')))
    reproducing = [v for v in variants if v['mismatched'] == 0]
    return {
        'system': 'chart-import-check',
        'recognized': parsed,
        'recognized_count': len(fields),
        'fields': fields,
        'summary': {'matched': len(fields) - len(mismatched), 'mismatched': len(mismatched)},
        'variants': variants[:12],
        'reproducing_variants': [v['label'] for v in reproducing],
        'possible_causes': _causes(req.birth, fields, bazi, ziwei) if mismatched else [],
        'accepted_formats': [
            '四柱：「年柱 庚辰 月柱 甲申 日柱 丙午 时柱 庚寅」或连续的「庚辰 甲申 丙午 庚寅」',
            '紫微：「命宫在寅」「身宫：夫妻」「水二局」「命主：破军」「身主：天相」',
            '宫位主星：每行一个宫名，后接该宫主星，例如「夫妻宫：天机 太阴」；空宫写「空宫」；星名后紧跟庙旺得利平不陷时一并核对亮度，如「紫微庙」「七杀（平）」',
            '生年四化：「廉贞化禄」「破军化权」等',
        ],
        'limitations': [
            '只核对识别到的字段；没识别到的字段不代表一致。',
            '规则对照只覆盖常见差异（换日、闰月、时制、夏令时），不能证明对方使用的就是这套规则。',
            '粘贴的内容只用于本次比对，服务器不保存。',
        ],
    }
