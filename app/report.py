"""Composed, reproducible multi-tool dossier; no generative model or fortune claims.

The report makes provenance explicit. It is an agent-ready orchestration *artifact*,
not a claim of autonomous reasoning or scientific prediction.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal
from .advanced import DayunRequest, BirthBoundaryRequest, dayun_sequence, birth_boundary_map

from . import __version__
from .engines import BirthInput, calculate_bazi, calculate_ziwei
from .features import AnnualRequest, TimeAuditRequest, annual_transformations, time_audit
from .quality import QualityAuditRequest, calculation_quality_audit
from .evidence import DeepReviewRequest, deep_evidence_review
from .glossary import GLOSSARY_DOC, terms_in


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    lunar_year: int | None = Field(default=None, ge=1901, le=2099,
                                    description='Optional named lunar year for a four-transformations overlay')
    include_time_audit: bool = False
    include_dayun: bool = False
    include_deep_evidence: bool = False
    dayun_direction_override: Literal['forward', 'reverse'] | None = None
    birth_boundary_minutes: int | None = Field(default=None, ge=1, le=120)

    @model_validator(mode='after')
    def check_audit_longitude(self):
        if self.include_time_audit and self.birth.longitude is None:
            raise ValueError('include_time_audit requires birthplace longitude')
        if self.include_dayun and self.birth.gender == 'unspecified' and not self.dayun_direction_override:
            raise ValueError('include_dayun requires male/female gender or explicit dayun_direction_override')
        return self


# Time systems by their names in the text, so a reader (and the glossary) sees 平太阳时 rather than mean_solar.
TIME_MODE_NAMES = {'clock': '钟表时间', 'mean_solar': '平太阳时', 'apparent_solar': '真太阳时'}


def structured_report(request: ReportRequest) -> dict:
    bazi = calculate_bazi(request.birth)
    ziwei = calculate_ziwei(request.birth)
    palace = next(p for p in ziwei['palaces'] if p['is_ming'])
    four = [f"{x['star']}{x['type']}（{x['palace_name']}）" for x in ziwei['birth_year_transformations']]
    pillars = [p['text'] for p in bazi['pillars'].values()]
    trace = [
        {'step': 1, 'tool': 'bazi_chart', 'engine': 'calculate_bazi', 'status': 'computed'},
        {'step': 2, 'tool': 'ziwei_chart', 'engine': 'calculate_ziwei', 'status': 'computed'},
    ]
    sections = [
        {'id': 'method', 'title': '时制与节令方法', 'facts': [
            '出生日时基：' + TIME_MODE_NAMES.get(bazi['time_basis']['mode'], bazi['time_basis']['mode']),
            '有效传统钟点：' + bazi['time_basis']['effective_local_reading'],
            '23:00 换日：' + ('已选，23:00–23:59 出生按次日排日柱' if request.birth.late_zi_day_rollover else '未选，按 00:00 换日'),
            '年柱以立春为界，月柱以节令为界；其他流派可能存在差异。',
        ], 'provenance': 'BirthInput / app.timebasis / app.astronomy'},
        {'id': 'bazi', 'title': '四柱与藏干统计', 'facts': [
            '年/月/日/时：' + ' / '.join(pillars),
            f"日主：{bazi['day_master']}（{bazi['day_master_element']}）",
            '未加权藏干五行：' + '、'.join(f'{k}{v}' for k,v in bazi['hidden_stem_elements_unweighted'].items()),
        ], 'provenance': 'app.engines.calculate_bazi / app.reference'},
        {'id': 'ziwei', 'title': '紫微十二宫与四化', 'facts': [
            f"命宫{ziwei['ming_palace']}、身宫{ziwei['shen_palace']}；五行局：{ziwei['five_elements_bureau']}",
            ('命宫主星（括号内为亮度）：' if any(star in palace['star_brightness'] for star in palace['main_stars']) else '命宫主星：')
            + ('、'.join(star + (f"（{palace['star_brightness'][star]}）" if star in palace['star_brightness'] else '')
                        for star in palace['main_stars']) or '空宫'),
            '生年四化：' + '、'.join(four),
            f"星曜覆盖：{ziwei['star_counts']['main']} 主星 + {ziwei['star_counts']['auxiliary']} 颗已实现的辅星与杂曜，非完整专业盘。",
        ], 'provenance': 'app.engines.calculate_ziwei / app.reference'},
    ]
    quality = calculation_quality_audit(QualityAuditRequest(birth=request.birth))
    sections.append({'id':'quality', 'title':'出生数据与排盘边界审计',
                     'facts': [x['detail'] for x in quality['flags']] or ['未发现已知边界提示；不代表排盘获得权威认证。'],
                     'provenance':'app.quality.calculation_quality_audit / HKO published uncertainty note'})
    trace.append({'step': len(trace)+1, 'tool':'chart_quality_audit',
                  'engine':'calculation_quality_audit', 'status':'computed'})
    annual = None
    if request.lunar_year is not None:
        annual = annual_transformations(AnnualRequest(birth=request.birth, lunar_year=request.lunar_year))
        sections.append({'id': 'annual', 'title': f"{request.lunar_year} 农历年干四化叠加", 'facts': [
            f"年干支：{annual['year_pillar']}",
            ' / '.join(f"{x['star']}{x['type']}：{x['natal_palace']}" for x in annual['transformations']),
            '不是完整流年运盘，不代表事件预测。',
        ], 'provenance': 'app.features.annual_transformations'})
        trace.append({'step': len(trace)+1, 'tool': 'annual_transformations', 'engine': 'annual_transformations', 'status': 'computed'})
    audit = None
    if request.include_time_audit:
        audit = time_audit(TimeAuditRequest(birth=request.birth))
        sections.append({'id': 'time_audit', 'title': '三套时制审计', 'facts': [
            f"{TIME_MODE_NAMES.get(v['mode'], v['mode'])}：{v['effective_reading']}，命宫{v['ming_palace']}，四柱{'/'.join(v['pillars'].values())}"
            + (f"，均时差 {v['equation_of_time_minutes']:+.1f} 分钟" if v['mode'] == 'apparent_solar' and v.get('equation_of_time_minutes') is not None else '')
            for v in audit['choices']
        ], 'provenance': 'app.features.time_audit / app.timebasis'})
        trace.append({'step': len(trace)+1, 'tool': 'time_basis_audit', 'engine': 'time_audit', 'status': 'computed'})
    dayun = None
    if request.include_dayun:
        dayun = dayun_sequence(DayunRequest(birth=request.birth, direction_override=request.dayun_direction_override))
        sections.append({'id': 'dayun', 'title': '十年干支大运（非预测）', 'facts': [
            '顺逆方向：' + dayun['direction'],
            '所取节令：' + dayun['nearest_jie_used']['name'] + ' ' + dayun['nearest_jie_used']['instant'],
            f"名义起运年龄：{dayun['start_age_years_nominal']}岁（约）",
            '前六个干支：' + ' / '.join(x['pillar'] for x in dayun['periods'][:6]),
            '公历交运时间仅为均值年投影，不能当作精确流派交运日。',
        ], 'provenance': 'app.advanced.dayun_sequence / app.astronomy.nearest_jie'})
        trace.append({'step': len(trace)+1, 'tool': 'bazi_dayun', 'engine': 'dayun_sequence', 'status': 'computed'})
    boundaries = None
    if request.birth_boundary_minutes is not None:
        boundaries = birth_boundary_map(BirthBoundaryRequest(birth=request.birth,
            uncertainty_minutes=request.birth_boundary_minutes))
        sections.append({'id': 'birth_boundaries', 'title': '出生时刻模型边界地图', 'facts': [
            f"检查前后 {request.birth_boundary_minutes} 分钟，检出 {len(boundaries['boundaries'])} 个边界、{len(boundaries['segments'])} 段代表盘。",
            *[b['local'] + ' ' + '/'.join(b['types']) for b in boundaries['boundaries']],
            '数值定位精度不等于真实出生记录精度；仅覆盖当前实现的流派规则。',
        ], 'provenance': 'app.advanced.birth_boundary_map / app.timebasis / app.astronomy'})
        trace.append({'step': len(trace)+1, 'tool': 'birth_boundary_map', 'engine': 'birth_boundary_map', 'status': 'computed'})
    deep_review = None
    if request.include_deep_evidence:
        deep_review = deep_evidence_review(DeepReviewRequest(birth=request.birth, include_quality=False, lunar_year=request.lunar_year))
        sections.append({'id': 'deep_evidence', 'title': '规则证据与跨体系差异复核',
                         'facts': [finding['title'] + '：' + finding['observation'] for finding in deep_review['findings']],
                         'provenance': 'app.evidence.deep_evidence_review / docs/rules/evidence.md / references listed in deep_evidence_review'})
        trace.append({'step': len(trace)+1, 'tool': 'deep_evidence_review',
                      'engine': 'deep_evidence_review', 'status': 'computed'})
    warnings = [
        '传统术数未有可靠科学证据支持对个人命运的预测，不应用于重要现实决策。',
        '紫微星曜和四化按选定公开流派规则，仅部分实现；不同流派可能不一致。',
        '这是一份确定性多工具计算报告，未运行外部大语言模型，不是自主推理结果。',
        '出生记录不保存到服务器；报告由请求即时生成。',
    ]
    lines = ['# 传统历法与命盘 · 可核验计算报告', '', f"引擎版本：{__version__}",
             f"时区：{request.birth.timezone}", '']
    for section in sections:
        lines += ['## ' + section['title'], '']
        lines += ['- ' + fact for fact in section['facts']]
        lines += ['', '计算来源：`' + section['provenance'] + '`', '']
    if deep_review is not None:
        lines += ['## 深度证据资料与独立验证限制', '']
        lines += ['- ' + x['title'] + '：' + x['reference'] + '（' + x['scope'] + '）' for x in deep_review['references']]
        lines += ['', '注：方法参考文档不能替代该命盘的第三方逐盘认证。', '']
    # The terms this report uses, explained; matched against the report's own text before this section.
    glossary = terms_in('\n'.join(lines))
    if glossary:
        lines += ['## 术语解释', '']
        lines += [f"- **{x['term']}**（{x['system']}）：{x['definition']}玄枢：{x['in_xuanshu']}" for x in glossary]
        lines += ['', '来源：`' + GLOSSARY_DOC + '`', '']
    lines += ['## 适用边界', ''] + ['- ' + item for item in warnings] + ['']
    return {
        'system': 'deterministic-multitool-dossier', 'version': __version__,
        'overview': {'pillars': pillars, 'day_master': bazi['day_master'],
                     'ming_palace': ziwei['ming_palace'], 'shen_palace': ziwei['shen_palace'],
                     'star_counts': ziwei['star_counts']},
        'sections': sections, 'tool_trace': trace,
        'annual': annual, 'time_audit': audit, 'quality_audit': quality,
        'dayun': dayun, 'birth_boundaries': boundaries, 'deep_evidence': deep_review, 'glossary': glossary,
        'limitations': warnings, 'markdown': '\n'.join(lines),
    }
