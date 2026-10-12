"""Auditable, deterministic cross-chart evidence review.

The output separates calculated facts, local rule choices and external method
references. No external site is queried at runtime; references document
methods, not independent verification of a particular generated chart.
"""
from __future__ import annotations

from typing import Literal
from hashlib import sha256
import html
import json
import re

from pydantic import BaseModel, ConfigDict, Field

from . import __version__
from .engines import BirthInput, PALACE_NAMES, calculate_bazi, calculate_ziwei
from .features import AnnualRequest, annual_transformations
from .quality import QualityAuditRequest, calculation_quality_audit
from .reference import PALACE_TOPICS

TIME_MODE_LABELS = {'clock': '钟表时间', 'mean_solar': '平太阳时', 'apparent_solar': '真太阳时'}

# External links describe public conventions or developer interfaces, rather
# than claiming an independent correctness certificate for this implementation.
RULE_SOURCES = {
    'calendar.year_boundaries': {
        'title': '干支年界与传统农历年的不同语义',
        'implementation': 'app.engines.calculate_bazi / calculate_ziwei',
        'reference': 'https://www.weather.gov.hk/en/gts/time/conversion.htm',
        'scope': '日历概念参考；不是两套算法的交叉认证',
    },
    'bazi.pillars': {
        'title': '四柱与十二节令界定',
        'implementation': 'app.engines.calculate_bazi / app.astronomy.solar_month_offset',
        'reference': 'https://www.weather.gov.hk/en/gts/astronomy/Solar_Term.htm',
        'scope': '节令的天文定义；八字日界/流派另依本项目规则',
    },
    'bazi.hidden': {
        'title': '地支藏干、十神与未加权计数',
        'implementation': 'app.engines._ten_god / app.reference.HIDDEN_STEMS',
        'reference': 'docs/rules/bazi.md',
        'scope': '本项目明示的规则表；无科学个人属性证明',
    },
    'bazi.relations': {
        'title': '传统地支合冲刑害的结构标记',
        'implementation': 'app.reference.BRANCH_HARMONY / BRANCH_CLASH / BRANCH_HARM / BRANCH_PUNISH',
        'reference': 'docs/rules/bazi.md',
        'scope': '仅识别规则中存在的符号配对，不判现实吉凶',
    },
    'ziwei.natal': {
        'title': '十二宫、命身宫和星曜定位',
        'implementation': 'app.engines.calculate_ziwei',
        'reference': 'https://docs.iztro.com/en_US/posts/astrolabe',
        'scope': '开源排盘的数据模型参考；本项目只实现选定星曜',
    },
    'ziwei.surround': {
        'title': '三方四正（本宫、两三合宫及对宫）',
        'implementation': 'app.engines.calculate_ziwei / palaces[].three_harmonies_and_opposite',
        'reference': 'https://docs.iztro.com/en_US/posts/palace',
        'scope': '宫位关系与查询接口参考，不是个体事件推断',
    },
    'ziwei.four': {
        'title': '全书系十干四化、宫干飞化',
        'implementation': 'app.reference.FOUR_TRANSFORMATIONS / app.engines.calculate_ziwei',
        'reference': 'https://docs.iztro.com/en_US/posts/config-n-plugin',
        'scope': '不同流派的四化配置有差异；此处是固定规则表',
    },
    'ziwei.annual': {
        'title': '指定农历年干四化静态投影',
        'implementation': 'app.features.annual_transformations',
        'reference': 'https://docs.iztro.com/en_US/posts/horoscope',
        'scope': '只对照年干和本命宫位，不是完整流年盘或预测',
    },
    'quality.boundaries': {
        'title': '日期与时制临界的已知限制',
        'implementation': 'app.quality.calculation_quality_audit',
        'reference': 'https://www.weather.gov.hk/en/gts/time/conversion.htm',
        'scope': '提示输入/历法敏感性；无提示不代表专业认证',
    },
    'cross.not_independent': {
        'title': '两体系共用生日、历法库和时制，不能以重合证明正确',
        'implementation': 'app.engines.calculate_bazi / calculate_ziwei',
        'reference': 'docs/research/FEATURES_AND_REFERENCES.md',
        'scope': '质量控制原则，不宣称跨学科因果或成功概率',
    },
}


def _digest(value: object) -> str:
    """Reproducible checksum of a rule result (not an authentication signature)."""
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return sha256(data.encode('utf-8')).hexdigest()


def _markdown_literal(value: str) -> str:
    """Keep user-submitted focus notes inert in exported Markdown."""
    return re.sub(r'([\\`*_{}\[\]()#+.!|>~-])', r'\\\1', html.escape(' '.join(value.split()), quote=True))


class DeepReviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    focus_palace: Literal[tuple(PALACE_NAMES)] = '命宫'
    lunar_year: int | None = Field(default=None, ge=1901, le=2099)
    include_quality: bool = True
    question: str | None = Field(default=None, max_length=200)


def deep_evidence_review(request: DeepReviewRequest) -> dict:
    """Build a rule-linked, non-predictive explanation from the computed charts."""
    bazi = calculate_bazi(request.birth)
    ziwei = calculate_ziwei(request.birth)
    by_palace = {p['name']: (i, p) for i, p in enumerate(ziwei['palaces'])}
    focus_index, focus = by_palace[request.focus_palace]
    named = {p['branch']: p for p in ziwei['palaces']}
    findings: list[dict] = []

    def add(key: str, group: str, title: str, observation: str,
            evidence: list[dict], caveat: str) -> None:
        for field in evidence:
            field['sha256'] = _digest(field['value'])
        findings.append({
            'id': key.replace('.', '-'), 'group': group, 'title': title,
            'observation': observation, 'evidence': evidence,
            'rule_ids': [key], 'limit': caveat, 'claim_level': 'calculated-structure',
        })

    four_pillars = ' / '.join(bazi['pillars'][k]['text'] for k in ('year','month','day','hour'))
    add('bazi.pillars', '八字', '四柱与时基',
        f'{four_pillars}；计算时制：{TIME_MODE_LABELS.get(bazi["time_basis"]["mode"], bazi["time_basis"]["mode"])}。',
        [{'path': 'bazi.pillars', 'value': {k:p['text'] for k,p in bazi['pillars'].items()}},
         {'path': 'bazi.time_basis', 'value': bazi['time_basis']['mode']}],
        '年界按立春、月界按节令，日界和太阳时按输入选项；不是现实性格推断。')

    hidden_ten = []
    for key, pillar in bazi['pillars'].items():
        hidden_ten.append(f"{key}:{pillar['branch']}→" + '/'.join(
            f"{s['stem']}({s['ten_god']})" for s in pillar['hidden_stems']))
    add('bazi.hidden', '八字', '藏干与十神（仅做映射）',
        '；'.join(hidden_ten),
        [{'path': 'bazi.pillars', 'value': {key: value['hidden_stems'] for key,value in bazi['pillars'].items()}},
         {'path': 'bazi.hidden_stem_elements_unweighted', 'value': bazi['hidden_stem_elements_unweighted']}],
        '藏干顺序是传统表；出现次数未加权，不能直接当旺衰或职业倾向。')
    active_relations = [r for r in bazi['branch_relations'] if r['labels']]
    add('bazi.relations', '八字', '地支关系标记',
        '；'.join(f"{r['a']}/{r['b']} {r['branches']}：{'、'.join(r['labels'])}" for r in active_relations) if active_relations else '所列四支两两配对未命中当前实现的合冲刑害表。',
        [{'path': 'bazi.branch_relations', 'value': active_relations}],
        '关系可能叠加，标记不带强弱权重，也不等于个人关系或事件的吉凶。')

    add('ziwei.natal', '紫微', f"{request.focus_palace}（{focus['branch']}）结构", 
        f"命宫{ziwei['ming_palace']}、身宫{ziwei['shen_palace']}；{request.focus_palace}主星：{'、'.join(focus['main_stars']) or '无'}；"
        f"已实现辅/杂曜：{'、'.join(focus['auxiliary_stars']) or '无'}。",
        [{'path': 'ziwei.ming_palace', 'value': ziwei['ming_palace']},
         {'path': 'ziwei.shen_palace', 'value': ziwei['shen_palace']},
         {'path': f'ziwei.palaces[{focus_index}].main_stars', 'value': focus['main_stars']},
         {'path': f'ziwei.palaces[{focus_index}].auxiliary_stars', 'value': focus['auxiliary_stars']}],
        '此为原生有限星曜集合；不能将空宫或未排出的星曜当成不存在。')
    surround = focus['three_harmonies_and_opposite']
    others = [named[x['branch']] for x in surround['trine']]
    opposite = named[surround['opposite']['branch']]
    add('ziwei.surround', '紫微', f'{request.focus_palace}的三方四正',
        f"三合：{'、'.join(p['name']+'('+p['branch']+')' for p in others)}；"
        f"对宫：{opposite['name']}({opposite['branch']})；主题：{PALACE_TOPICS[request.focus_palace]}。",
        [{'path': f'ziwei.palaces[{focus_index}].three_harmonies_and_opposite', 'value': surround}],
        '这里仅列宫位拓扑关系，不把星曜词汇直接推断为人生结果。')
    natal_four = ziwei['birth_year_transformations']
    flying = focus['palace_flying_transformations']
    add('ziwei.four', '紫微', '生年四化与焦点宫飞化（分别展示）',
        '生年：' + '、'.join(f"{t['star']}{t['type']}→{t['palace_name']}" for t in natal_four) + '；焦点宫宫干飞化：' +
        '、'.join(f"{f['star']}{f['type']}→{f['target_palace']}" + ('（自化）' if f['self_transform'] else '') for f in flying),
        [{'path': 'ziwei.birth_year_transformations', 'value': natal_four},
         {'path': f'ziwei.palaces[{focus_index}].palace_flying_transformations', 'value': flying}],
        '仅固定全书系四化和选定安星规则，其他流派、亮度、格局不能混用。')

    bazi_year = bazi['pillars']['year']['text']
    ziwei_year = ziwei['year_pillar']
    same_year = bazi_year == ziwei_year
    add('calendar.year_boundaries', '对照', '两套年柱口径差异核对',
        (f'当前干支年相同：{bazi_year}，但两者使用共同出生输入与历法依赖，不能算独立复验。'
         if same_year else f'八字立春年柱为 {bazi_year}，紫微农历年干支为 {ziwei_year}；这可能是立春与农历年首口径不同，不应强制统一。'),
        [{'path': 'bazi.pillars.year.text', 'value': bazi_year},
         {'path': 'ziwei.year_pillar', 'value': ziwei_year}],
        '同一历法依赖意味着两者相同不构成算法独立认证；不同时要核对临界时刻。')
    add('cross.not_independent', '方法', '跨体系关联能说明什么',
        f"两图使用同一出生时刻与时基，不能根据‘四柱里有{bazi['day_master']}’和‘{request.focus_palace}有某星’推出因果关系。",
        [{'path': 'bazi.time_basis.mode', 'value': bazi['time_basis']['mode']},
         {'path': 'ziwei.time_basis.mode', 'value': ziwei['time_basis']['mode']}],
        '跨体系只能对照输入口径与符号结构；没有科学证据支持命运预测或统计概率。')

    annual = None
    if request.lunar_year is not None:
        annual = annual_transformations(AnnualRequest(birth=request.birth, lunar_year=request.lunar_year))
        add('ziwei.annual', '年度', f'{request.lunar_year} 农历年干四化叠加',
            f"年干支 {annual['year_pillar']}；" + '、'.join(
                f"{x['star']}{x['type']}→{x['natal_palace']}" for x in annual['transformations']),
            [{'path': 'annual.transformations', 'value': annual['transformations']}],
            '仅是固定四化与原生命宫映射，不是流年全盘或事件预测。')

    quality = None
    if request.include_quality:
        quality = calculation_quality_audit(QualityAuditRequest(birth=request.birth))
        flags = quality['flags']
        add('quality.boundaries', '质量', '出生时间与历法适用性',
            f'检测到 {len(flags)} 项已知边界提示。' if flags else '目前未触发已知敏感边界提示。',
            [{'path': 'quality.flags', 'value': flags}],
            '没有质量提示并不代表源数据准确或经过专业流派认证。')

    checks = [
        {'id': 'unique-12-palaces', 'passed': len(ziwei['palaces']) == 12 and len(set(p['branch'] for p in ziwei['palaces'])) == 12, 'meaning': '十二宫地支结构无重复'},
        {'id': 'natal-four-locations', 'passed': len(natal_four) == 4 and all(ziwei['star_positions'].get(t['star']) == t['palace'] for t in natal_four), 'meaning': '生年四化星曜位置一致'},
        {'id': 'trine-and-opposite', 'passed': len(set([focus['branch']] + [p['branch'] for p in others] + [opposite['branch']])) == 4, 'meaning': '三方四正四宫互异'},
        {'id': 'shared-time-basis', 'passed': bazi['time_basis']['mode'] == ziwei['time_basis']['mode'], 'meaning': '八字与紫微计算使用相同的时间选项'},
    ]
    used_ids = list(dict.fromkeys(id_ for f in findings for id_ in f['rule_ids']))
    refs = [{'id': id_, **RULE_SOURCES[id_]} for id_ in used_ids]
    base = [
        '# 玄枢 · 有证据的跨体系结构研究', '',
        '版本：v.' + __version__,
        f'关注宫位：{request.focus_palace}',
        f'时区：{request.birth.timezone}',
        f'出生资料：{request.birth.birth_datetime}；性别选项：{request.birth.gender}；时间模式：{request.birth.time_mode}',
        '', '此报告展示传统文化规则下的可计算事实、公开方法参考和局限；不预测个体命运。',
    ]
    if request.question:
        base.extend(['', '用户研究问题：' + _markdown_literal(request.question)])
    for f in findings:
        base.extend(['', '## ' + f['title'], '', f['observation'], '',
                     '对应规则：' + ', '.join(f['rule_ids']),
                     '证据字段：' + ', '.join(e['path'] for e in f['evidence']),
                     '局限：' + f['limit']])
    base.extend(['', '## 结构校验（仅限内部一致性）', ''])
    base.extend('- ' + ('通过' if c['passed'] else '失败') + '：' + c['meaning'] for c in checks)
    base.extend(['', '## 方法和参考资料（非专业认证）', ''])
    for r in refs:
        base.extend(['- ' + r['title'] + '｜' + r['reference'] + '｜' + r['scope']])
    base.extend(['', '## 总体限制', '',
                 '- 未调用 LLM；传统术数的所谓推演不具有经验证的人生预测效力。',
                 '- 相同输入、相同历法依赖造成的重合不算外部独立验证。',
                 '- 仅计算已实现的有限规则；流派差异和星曜缺失均可能影响表现。', ''])
    return {
        'system': 'xuanshu-deep-evidence-review', 'version': __version__,
        'focus_palace': request.focus_palace, 'question': request.question,
        'input_parameters': request.model_dump(mode='json'),
        'calendar_year_consistent': same_year,
        'overview': {'pillars': four_pillars, 'day_master': bazi['day_master'],
                     'ming_palace': ziwei['ming_palace'], 'shen_palace': ziwei['shen_palace'],
                     'natal_star_counts': ziwei['star_counts']},
        'findings': findings, 'checks': checks, 'references': refs,
        'quality_audit': quality, 'annual_overlay': annual,
        'independent_professional_verification': False,
        'calculation_hashes': {
            'bazi_chart': _digest(bazi), 'ziwei_chart': _digest(ziwei),
            **({'annual_transformations': _digest(annual)} if annual is not None else {}),
        },
        'limitations': [
            '参考文档只支持方法描述，不意味着 XuanShu 的逐盘算法通过独立认证。',
            '传统术数缺乏可靠科学依据，不用于医疗、投资、法律或重大决策。',
            '两套计算共用输入和天文历法依赖，不能将一致字段计为独立证据。',
        ],
        'markdown': '\n'.join(base),
    }
