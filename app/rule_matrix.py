"""Rule sensitivity matrix: one birth record under every common rule choice.

Programs differ on a few rules: whether the day changes at 23:00, which month
the second half of a leap month belongs to, clock versus mean or apparent solar
time, and whether daylight saving time is taken off first. This module
recomputes the chart under each choice (and each pair of choices) and shows,
field by field, what stays the same and what changes. It does not say which
rule is correct.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .almanac import lunar_label
from .chart_import import MAJOR_STARS, _variants
from .engines import BirthInput, calculate_bazi, calculate_ziwei, normalized_dt

FIELDS = (
    ('pillar.year', '年柱'), ('pillar.month', '月柱'), ('pillar.day', '日柱'), ('pillar.hour', '时柱'),
    ('lunar', '农历'), ('ming', '命宫'), ('shen', '身宫'), ('bureau', '五行局'),
    ('ming_stars', '命宫主星'), ('transformations', '生年四化'),
)
# Fields that depend on the birth hour; left out when the hour is unknown.
HOUR_FIELDS = frozenset({'pillar.hour', 'ming', 'shen', 'bureau', 'ming_stars'})


class RuleMatrixRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    hour_unknown: bool = Field(False, description='Birth hour unknown: the time is a placeholder, so hour-dependent fields are left out.')


def _values(birth: BirthInput) -> tuple[dict[str, str], str]:
    bazi, ziwei = calculate_bazi(birth), calculate_ziwei(birth)
    ming = next(p for p in ziwei['palaces'] if p['is_ming'])
    shen = next(p for p in ziwei['palaces'] if p['is_shen'])
    values = {'pillar.' + key: bazi['pillars'][key]['text'] for key in ('year', 'month', 'day', 'hour')}
    values.update({
        'lunar': ziwei['year_pillar'] + '年' + lunar_label(ziwei['lunar_date']),
        'ming': ming['branch'],
        'shen': shen['branch'] + ' · ' + shen['name'],
        'bureau': ziwei['five_elements_bureau'],
        'ming_stars': '、'.join(sorted(ming['main_stars'], key=MAJOR_STARS.index)) or '空宫',
        'transformations': ' '.join(t['star'] + t['type'][1] for t in ziwei['birth_year_transformations']),
    })
    return values, bazi['time_basis']['effective_local_reading'][:16]


def _hints(birth: BirthInput, hour_unknown: bool) -> list[str]:
    bazi = calculate_bazi(birth)
    dt = normalized_dt(birth)
    hints = []
    if hour_unknown:
        hints.append('出生时辰不详：填写的时间只是占位，时柱、命宫、身宫、五行局和命宫主星不参与对照；当天若交节，年柱或月柱也可能不同。')
    for side in ('previous', 'next'):
        jie = bazi['jie_boundaries'][side]
        hours = abs((dt - datetime.fromisoformat(jie['instant'])).total_seconds()) / 3600
        if hours < 48:
            hints.append(f'出生时刻离{jie["name"]}交节约 {hours:.1f} 小时：节气时刻或时区处理稍有不同，月柱就可能不同。')
    hour = int(bazi['time_basis']['effective_local_reading'][11:13])
    if hour == 23 and not hour_unknown:
        hints.append('出生在 23:00 之后：各家对子时是否换日（早晚子时）规则不同，日柱可能不同。')
    if bazi['lunar_date']['is_leap_month']:
        hints.append('出生在农历闰月：闰月前后半月归属哪个月，各家规则不同，紫微命盘可能不同。')
    if dt.dst():
        hints.append('出生时当地实行夏令时：有的软件会先扣除夏令时再排盘。')
    if birth.longitude is None:
        hints.append('没有填写出生地经度，表中不含平太阳时与真太阳时；在出生资料里填写经度后会一起比较。')
    return hints


def rule_matrix(req: RuleMatrixRequest) -> dict:
    fields = [(key, name) for key, name in FIELDS if not (req.hour_unknown and key in HOUR_FIELDS)]
    base = req.birth.model_dump()
    baseline, reading = _values(req.birth)
    rows = [{'label': '当前设置', 'is_baseline': True, 'changes': {}, 'settings': base,
             'effective_reading': reading, 'values': baseline, 'differs': []}]
    skipped = []
    for label, variant in _variants(req.birth):
        try:
            values, reading = _values(variant)
        except ValueError:
            # A solar-time or day-change shift can move a date at the edge of the range out of it.
            skipped.append(label)
            continue
        settings = variant.model_dump()
        rows.append({
            'label': label, 'is_baseline': False,
            'changes': {k: v for k, v in settings.items() if base.get(k) != v},
            'settings': settings, 'effective_reading': reading, 'values': values,
            'differs': [key for key, _ in fields if values[key] != baseline[key]],
        })
    sensitive = []
    for key, name in fields:
        changed_by = [row['label'] for row in rows if key in row['differs']]
        if changed_by:
            sensitive.append({'field': key, 'label': name, 'changed_by': changed_by})
    stable = [name for key, name in fields if not any(key in row['differs'] for row in rows)]
    notes = [
        '每一行把当前出生资料换成一种常见的不同规则（或两种规则的组合）重新排盘，标出与当前设置不同的格子。',
        '这只说明规则选择会改变哪些字段，不判断哪种规则正确；以出生资料和你采用的流派为准。',
        '紫微按农历正月初一换年、不按 23:00 换日；八字按立春换年，两者的年柱可能不同，这是规则本身的差别。',
    ]
    if skipped:
        notes.append('以下规则换算后超出支持的 1901–2099 年，未列出：' + '；'.join(skipped))
    return {
        'system': 'rule-sensitivity-matrix',
        'hour_unknown': req.hour_unknown,
        'fields': [{'key': key, 'label': name} for key, name in fields],
        'rows': rows,
        'summary': {'variants': len(rows) - 1, 'identical_variants': sum(not r['differs'] for r in rows[1:]),
                    'stable_fields': stable, 'sensitive_fields': sensitive},
        'hints': _hints(req.birth, req.hour_unknown),
        'notes': notes,
    }
