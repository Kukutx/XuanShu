"""Stateless, question-first consultation orchestrator for XuanShu.

Unlike MCP prompt templates, this module *executes* existing calculation
functions. It deliberately does not call an LLM, infer life outcomes, or store
birth data. Conversation continuity consists of a minimal, client-carried
context with no names, birth times, transcripts, or actual chart values.
"""
from __future__ import annotations

import html
import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import __version__
from .advanced import DayunRequest, dayun_sequence, BirthBoundaryRequest, birth_boundary_map
from .engines import BirthInput, PALACE_NAMES
from .evidence import DeepReviewRequest, deep_evidence_review
from .features import (AnnualRequest, PairInput, RuleComparisonRequest,
                       annual_transformations, compare_charts, rule_comparison)
from .qimen import QimenRequest, qimen_chart
from .quality import QualityAuditRequest, calculation_quality_audit
from .report import ReportRequest, structured_report
from .workflows import DecisionMatrixRequest, decision_matrix

Intent = Literal['auto', 'natal', 'career', 'relationship', 'timing', 'decision', 'rules']
ResolvedIntent = Literal['natal', 'career', 'relationship', 'timing', 'decision', 'rules']

# An explicit classification vocabulary: deterministic, locally testable and
# inspected by users. NOT a general semantic LLM classifier.
SIGNALS = {
    'rules': ('排盘不同', '流派', '规则差异', '时差', '校时', '真太阳时', '子初', '不一致', '交节', '为什么不同'),
    'timing': ('择日', '择时', '选日子', '开业时间', '时间窗口', '哪天', '几点', '候选时刻', '起卦'),
    'relationship': ('婚恋', '感情', '合盘', '婚姻', '情侣', '伴侣', '我们两', '合作关系', '两个人'),
    'decision': ('决策矩阵', '方案比较', '权重', '评分', '两个方案', '怎么选', '哪个好', '选哪个'),
    'career': ('事业', '工作', '职业', '职场', '财运', '转职', '跳槽', '升职', '流年', '大运', '发展方向', '年度'),
    'natal': ('本命', '八字', '命宫', '紫微', '命盘', '四柱', '藏干', '星曜'),
}
INTENT_LABELS = {'natal': '本命分析', 'career': '事业/年度', 'relationship': '双人关系', 'timing': '多时刻查询',
                 'decision': '方案比较', 'rules': '规则分歧'}
STATUS_LABELS = {'completed': '已完成', 'partial': '部分完成，还缺输入', 'needs_input': '需要补充输入'}
FOLLOWUP_CUES = ('那', '那么', '再看', '然后', '继续', '也', '呢', '刚才', '之前', '接着')
YEAR_PATTERN = re.compile(r'(?<!\d)(19\d{2}|20\d{2})(?=年|\b)')


class Continuation(BaseModel):
    """Client-transported topic cursor, never an authentication token."""
    model_config = ConfigDict(extra='forbid')
    intent: ResolvedIntent
    focus_palace: Literal[tuple(PALACE_NAMES)] = '命宫'
    turns: int = Field(default=1, ge=1, le=12)
    # A named lunar year is sufficient to continue a *topic*, not recover a chart.
    lunar_year: int | None = Field(default=None, ge=1901, le=2099)


class RealWorldFact(BaseModel):
    """Optional first-person context for this request only, never a verified fact."""
    model_config = ConfigDict(extra='forbid')
    category: Literal['experience', 'goal', 'constraint']
    statement: str = Field(min_length=2, max_length=220)

    @field_validator('statement')
    @classmethod
    def nonblank_statement(cls, value: str) -> str:
        value = ' '.join(value.split())
        if len(value) < 2:
            raise ValueError('statement must not be blank')
        return value


class ConsultationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=2, max_length=600)
    intent: Intent = 'auto'
    birth: BirthInput | None = None
    partner: BirthInput | None = None
    partner_authorized: bool = False
    real_world_facts: list[RealWorldFact] = Field(default_factory=list, max_length=8)
    alternative_birth: BirthInput | None = None
    lunar_year: int | None = Field(default=None, ge=1901, le=2099)
    focus_palace: Literal[tuple(PALACE_NAMES)] | None = None
    candidate_times: list[BirthInput] = Field(default_factory=list, max_length=5)
    matrix: DecisionMatrixRequest | None = None
    include_full_report: bool = False
    uncertainty_minutes: int | None = Field(default=None, ge=1, le=120)
    dayun_direction_override: Literal['forward', 'reverse'] | None = None
    # Browser or agent must send this field again. We never retain it server-side.
    continuation: Continuation | None = None

    @field_validator('question')
    @classmethod
    def validate_question(cls, value: str) -> str:
        text = ' '.join(value.split())
        if len(text) < 2:
            raise ValueError('question must not be blank')
        return text

    @model_validator(mode='after')
    def validate_intent_args(self):
        if self.alternative_birth is not None and self.birth is None:
            raise ValueError('alternative_birth requires birth')
        if self.partner is not None and not self.partner_authorized:
            raise ValueError('partner requires explicit confirmation of permitted use')
        if self.partner is not None and self.birth is None:
            raise ValueError('partner requires birth')
        if self.birth is None and self.include_full_report:
            raise ValueError('include_full_report requires birth')
        return self


def route(question: str, *, chosen: Intent = 'auto', continuation: Continuation | None = None,
          has_matrix: bool = False, has_candidates: bool = False) -> tuple[ResolvedIntent, list[str]]:
    if chosen != 'auto':
        return chosen, ['intent selected explicitly']
    if has_matrix:
        return 'decision', ['matrix supplied']
    if has_candidates:
        return 'timing', ['candidate_times supplied']
    matched = {key: [word for word in words if word in question] for key, words in SIGNALS.items()}
    for key in ('rules', 'timing', 'relationship', 'decision', 'career', 'natal'):
        if matched[key]:
            return key, [f'question mentions: {word}' for word in matched[key][:3]]
    if continuation and any(question.startswith(cue) for cue in FOLLOWUP_CUES):
        return continuation.intent, ['no domain keywords; inherited client-provided topic cursor']
    return 'natal', ['no domain keywords; default to natal structural review']


def _year_from_question(question: str) -> int | None:
    matches = [int(m.group(1)) for m in YEAR_PATTERN.finditer(question)]
    matches = [x for x in matches if 1901 <= x <= 2099]
    return matches[0] if len(set(matches)) == 1 else None


def _safe_markdown(value: str) -> str:
    value = html.escape(value, quote=True)
    return re.sub(r'([\\`*_{}\[\]()#+.!|>~-])', r'\\\1', value)


def execute_consultation(req: ConsultationRequest) -> dict:
    """Plan + run only necessary engines; return trace, evidence and next inputs.

    No global state, model calls, network requests or persistence. All chart
    computations derive only from *this request's* BirthInput(s). The previous
    topic cursor is user-controlled and never treated as authenticated evidence.
    """
    intent, route_evidence = route(req.question, chosen=req.intent,
                                   continuation=req.continuation,
                                   has_matrix=req.matrix is not None,
                                   has_candidates=bool(req.candidate_times))
    focus = req.focus_palace or (req.continuation.focus_palace if req.continuation else '命宫')
    year = req.lunar_year if req.lunar_year is not None else _year_from_question(req.question)
    # Do not carry an old year forward when this question explicitly gives a
    # different one. A bare 'then?' may retain the last topic's lunar year.
    if year is None and req.continuation and any(req.question.startswith(x) for x in FOLLOWUP_CUES):
        year = req.continuation.lunar_year

    missing: list[dict[str, str]] = []
    trace: list[dict] = []
    results: dict[str, object] = {}
    observations: list[dict] = []
    checks: list[dict] = []
    needs_human_review = False
    caveats = [
        '传统命理符号是文化解释框架，尚无可靠科学证据支持个人命运预测。',
        '计算结构、传统解释与现实事实必须分开；本执行器没有调用 LLM、不会自动查询现实事件。',
        '结果依赖选定流派；不同流派、时区和临界出生时刻可能产生差异。',
        '服务器不保存会话或出生资料；续问需要客户端重新提交必需信息。',
    ]

    def need(field: str, why: str) -> None:
        if field not in [item['field'] for item in missing]:
            missing.append({'field': field, 'reason': why})

    def call(tool: str, func, request_model, *, purpose: str, keys: list[str] | None = None) -> dict:
        result = func(request_model)
        results[tool] = result
        trace.append({'step': len(trace) + 1, 'tool': tool, 'status': 'computed',
                      'purpose': purpose, 'field_paths': keys or []})
        return result

    # Separate user-supplied experience from computed material and external
    # evidence. Never use the text as an instruction or treat it as verified.
    for i, fact in enumerate(req.real_world_facts):
        observations.append({'type': 'user-provided', 'text': fact.statement,
                             'tool': 'user_input', 'path': f'real_world_facts[{i}].statement',
                             'category': fact.category,
                             'limit': '由使用者提供，未经本工具独立核实；不得当作命理推断或第三方已证实的事实。'})

    if intent in ('natal', 'career', 'relationship', 'rules') and req.birth is None:
        need('birth', '需要出生公历时间、出生地时区与所选排盘口径；不在后台猜测或恢复出生资料')
    if intent == 'rules' and req.alternative_birth is None:
        need('alternative_birth', '规则差异对照需要第二套明确的出生时基或流派选项；本模块不会虚构另一套排盘结果')

    if req.birth is not None and intent in ('natal', 'career', 'relationship', 'rules'):
        q = call('chart_quality_audit', calculation_quality_audit,
                 QualityAuditRequest(birth=req.birth), purpose='核对临界时刻和历法/时区歧义',
                 keys=['flags', 'details'])
        if q['review_needed']:
            needs_human_review = True
            caveats.append('出生时间和历法质量审计标记需要复核，请先确认警告后解释命盘。')
        observations.append({'type': 'calculated', 'text': f"出生资料质量提示：{len(q['flags'])} 项。",
                             'tool': 'chart_quality_audit', 'path': 'flags'})

    if intent in ('natal', 'career', 'relationship', 'rules') and req.birth is not None:
        if intent == 'rules' and req.alternative_birth is not None:
            comparison = call('rule_comparison', rule_comparison,
                              RuleComparisonRequest(original=req.birth, alternative=req.alternative_birth),
                              purpose='同一命盘两套明确输入/时制口径比较', keys=['differences'])
            observations.append({'type': 'calculated', 'text': '两套参数差异已列入 comparison.differences；变化不等于某套规则绝对正确。',
                                 'tool': 'rule_comparison', 'path': 'differences'})
        # Relationship calculations are only a two-person *symbol* comparison.
        if intent == 'relationship' and req.partner is not None:
            p = call('pair_comparison', compare_charts, PairInput(person_a=req.birth, person_b=req.partner),
                     purpose='两人四柱结构与传统合冲标签', keys=['person_a', 'person_b'])
            observations.append({'type': 'calculated', 'text': '已计算双方结构对照；无婚恋适配分数或关系成功率。',
                                 'tool': 'pair_comparison', 'path': 'person_a'})
        if intent == 'relationship' and req.partner is None:
            need('partner', '关系合盘需要对方明确提供或授权使用的出生信息')
        review = call('deep_evidence_review', deep_evidence_review,
                      DeepReviewRequest(birth=req.birth, focus_palace='夫妻宫' if intent == 'relationship' and req.focus_palace is None else focus,
                                        lunar_year=year if intent == 'career' else None,
                                        include_quality=False, question=req.question[:200]),
                      purpose='按规则链提取八字、紫微结构证据', keys=['findings', 'references', 'checks'])
        # Prioritize evidence relevant to the question, rather than mechanically
        # reporting the same first four chart facts for every domain.
        interests = {
            'natal': ['bazi-pillars', 'bazi-hidden', 'ziwei-natal', 'ziwei-surround', 'ziwei-four'],
            'career': ['bazi-pillars', 'ziwei-natal', 'ziwei-four', 'calendar-year_boundaries'],
            'relationship': ['bazi-relations', 'ziwei-natal', 'ziwei-surround', 'ziwei-four'],
            'rules': ['calendar-year_boundaries', 'cross-not_independent', 'bazi-pillars', 'ziwei-four'],
        }
        by_id = {f['id']: f for f in review['findings']}
        relevant = [by_id[k] for k in interests.get(intent, []) if k in by_id]
        checks.extend(review['checks'])
        if not all(check['passed'] for check in review['checks']):
            needs_human_review = True
            caveats.append('深度证据的内部一致性检查未全部通过；请勿据此断言计算完全准确。')
        ref_by_id = {r['id']: r for r in review['references']}
        for finding in relevant:
            observations.append({'type': 'traditional-rule', 'text': finding['observation'],
                                 'tool': 'deep_evidence_review', 'path': f"findings.{finding['id']}",
                                 'rule_ids': finding['rule_ids'], 'limit': finding['limit'],
                                 'evidence_paths': [e['path'] for e in finding['evidence']],
                                 'evidence_hashes': [e['sha256'] for e in finding['evidence']],
                                 'method_references': [ref_by_id[id_]['reference'] for id_ in finding['rule_ids'] if id_ in ref_by_id]})

    if intent == 'career':
        if req.birth is not None:
            if year is None:
                need('lunar_year', '年度四化需要明确指定农历命名年，不能默认把公历1月1日视为年界')
            else:
                annual = call('annual_transformations', annual_transformations,
                              AnnualRequest(birth=req.birth, lunar_year=year),
                              purpose='指定农历年四化到本命宫的规则映射', keys=['year_pillar', 'transformations'])
                observations.append({'type': 'traditional-rule', 'text': f"{year} 农历年年干支为 {annual['year_pillar']}；所列四化只是静态映射。",
                                     'tool': 'annual_transformations', 'path': 'year_pillar'})
            if req.birth.gender != 'unspecified' or req.dayun_direction_override:
                d = call('bazi_dayun', dayun_sequence, DayunRequest(birth=req.birth,
                         direction_override=req.dayun_direction_override),
                         purpose='可选传统十年运序列', keys=['periods', 'direction'])
                observations.append({'type': 'traditional-rule', 'text': '已按所选规则列出名义大运干支序列（非事件预测）。',
                                     'tool': 'bazi_dayun', 'path': 'periods'})
            elif '大运' in req.question:
                need('dayun_direction_override', '性别选项未指定时必须明确大运顺逆方向，不能自动推断')

    if intent == 'timing':
        if not req.candidate_times:
            need('candidate_times', '请提供至少一个明确的候选日期、时刻和当地时区')
        else:
            for index, birth in enumerate(req.candidate_times):
                data = call(f'qimen_hour_chart_{index + 1}', qimen_chart, QimenRequest(moment=birth),
                            purpose=f'候选时刻 {index + 1} 的时家拆补转盘（独立计算）',
                            keys=['solar_term', 'bureau', 'palaces'])
                observations.append({'type': 'traditional-rule',
                                     'text': f"候选{index + 1}：{data['solar_term']}、{data['dun']}{data['bureau']}局、{data['yuan']}。",
                                     'tool': f'qimen_hour_chart_{index + 1}', 'path': 'bureau'})
            caveats.append('候选时刻只是逐一计算比较；不自动排序吉凶、不保证择时效果。')

    if intent == 'decision':
        if req.matrix is None:
            need('matrix', '请提供至少两个方案、可验证的评价指标、指标权重和0至5的用户评分')
        else:
            matrix = call('decision_matrix', decision_matrix, req.matrix,
                          purpose='基于用户评分的加权比较与敏感性审计', keys=['ranked_options', 'sensitivity'])
            observations.append({'type': 'user-assumption', 'text': '方案排序完全来自用户提供的评分和权重，不来自命盘。',
                                 'tool': 'decision_matrix', 'path': 'ranked_options'})

    if req.uncertainty_minutes is not None and req.birth is not None and intent in ('natal', 'career', 'relationship', 'rules'):
        call('birth_boundary_map', birth_boundary_map,
             BirthBoundaryRequest(birth=req.birth, uncertainty_minutes=req.uncertainty_minutes),
             purpose='出生时刻不确定性下的交节/时辰边界', keys=['boundaries', 'segments'])

    if req.include_full_report and req.birth is not None:
        call('structured_report', structured_report,
             ReportRequest(birth=req.birth, lunar_year=year if intent == 'career' else None,
                           include_deep_evidence=True, include_dayun=False),
             purpose='导出多工具结构化报告', keys=['sections', 'markdown'])

    if req.real_world_facts:
        caveats.append('现实经历、目标和限制条件由用户在本次请求中提供；未作外部核查，不会自动留存供未来会话使用。')
    status = 'needs_input' if missing and not trace else ('partial' if missing else 'completed')
    cursor = Continuation(intent=intent, focus_palace=focus,
                          turns=min(12, (req.continuation.turns + 1 if req.continuation else 1)),
                          lunar_year=year)
    # In user-facing text, a fixed explanation is preferable to invented
    # psychological claims. The steps and raw evidence are available separately.
    plain_summary = ('需要补齐输入后才能进行指定计算。' if not trace else
                     f"已根据问题执行 {len(trace)} 步可复现计算，{'另有未补齐输入' if missing else '没有需要补齐的必需输入'}。")
    followups = ([f"请补充 {item['field']}：{item['reason']}" for item in missing] or
                 ['可指定某项规则或宫位继续追问；续问时请重新发送需要的出生资料。'])
    lines = ['# XuanShu · 问题驱动的可核验咨询工作流', '',
             '问题：' + _safe_markdown(req.question),
             f'咨询场景：{INTENT_LABELS[intent]}（{intent}）', f'状态：{STATUS_LABELS[status]}（{status}）', '', plain_summary, '',
             '## 实际执行步骤', '']
    lines.extend(f"- {x['step']}. `{x['tool']}`：{x['purpose']}" for x in trace)
    lines.extend(['', '## 可核对观察', ''])
    lines.extend('- ' + _safe_markdown(o['text']) + '（' + o['tool'] + '）' for o in observations)
    lines.extend(['', '## 必须补充', ''])
    lines.extend('- ' + _safe_markdown(x['reason']) for x in missing)
    lines.extend(['', '## 限制与隐私', ''])
    lines.extend('- ' + _safe_markdown(x) for x in caveats)
    return {
        'system': 'xuanshu-stateless-consultation-executor', 'version': __version__,
        'mode': 'deterministic-tool-orchestration-not-llm',
        'intent': intent, 'routing_evidence': route_evidence,
        'status': status, 'summary': plain_summary,
        'verification': {'internal_checks': checks,
                         'internal_checks_passed': all(c['passed'] for c in checks),
                         'needs_human_review': needs_human_review,
                         'independently_certified': False},
        'missing_inputs': missing, 'tool_trace': trace, 'observations': observations,
        'tool_results': results, 'limitations': caveats, 'next_questions': followups,
        'continuation': cursor.model_dump(mode='json'), 'persistence': 'none',
        'markdown': '\n'.join(lines) + '\n',
    }
