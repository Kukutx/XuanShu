"""Confidence labels for AI chat answers.

Two independent layers, both returned with each answer:

* ``chart_confidence``: deterministic. For the profile's birth data it measures
  how far the birth moment is from each calculation boundary (hour, day, jie
  month) and compares that margin with the user's stated birth-time
  uncertainty. A pillar whose boundary lies inside the uncertainty may flip.
* a verifier sub-agent: a second, separate model call that sees only the
  question, the answer and the raw tool results, and labels each chart claim
  as tool-backed, partially backed or unsupported, with a confidence tier.
  It cannot call tools, so it cannot add new facts.
"""
from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .engines import BirthInput, calculate_bazi, calculate_ziwei, normalized_dt
from .quality import QualityAuditRequest, calculation_quality_audit

MAX_EVIDENCE_CHARS = 40000

Tier = Literal['high', 'medium', 'low']


def _facts_at(birth: BirthInput, shift_minutes: int) -> dict[str, str] | None:
    moment = normalized_dt(birth) + timedelta(minutes=shift_minutes)
    shifted = birth.model_copy(update={'birth_datetime': moment.isoformat()})
    try:
        pillars = calculate_bazi(shifted)['pillars']
        ziwei = calculate_ziwei(shifted)
    except ValueError:  # shifted outside the supported years
        return None
    return {'八字年柱': pillars['year']['text'], '八字月柱': pillars['month']['text'],
            '八字日柱': pillars['day']['text'], '八字时柱': pillars['hour']['text'],
            '紫微命宫/身宫': f"命{ziwei['ming_palace']} 身{ziwei['shen_palace']}"}


def chart_confidence(birth: BirthInput, uncertainty_minutes: int) -> dict:
    """Stability of each birth-time dependent fact under the stated uncertainty."""
    audit = calculation_quality_audit(QualityAuditRequest(birth=birth))
    snap = audit['calculation_snapshot']
    jie = min(snap['minutes_since_previous_jie'], snap['minutes_until_next_jie'])
    hour = snap['minutes_to_nearest_hour_boundary']
    day = snap['minutes_to_day_boundary']
    pillars = snap['bazi_pillars']
    items = [
        ('八字年柱', pillars['year'], jie, '立春等节令交接'),  # the year pillar can only change at 立春, a jie
        ('八字月柱', pillars['month'], jie, '节令交接'),
        ('八字日柱', pillars['day'], day, '日界'),
        ('八字时柱', pillars['hour'], hour, '时辰交界'),
        ('紫微命宫/身宫', f"命{snap['ziwei_ming']} 身{snap['ziwei_shen']}", hour, '时辰交界'),
    ]
    # Recompute at ±1× and ±2× the uncertainty: the tier says how far the value holds.
    near = [_facts_at(birth, s * uncertainty_minutes) for s in (-1, 1)]
    far = [_facts_at(birth, s * 2 * uncertainty_minutes) for s in (-1, 1)]
    facts = []
    for name, value, margin, boundary in items:
        if any(f is None or f[name] != value for f in near):
            tier: Tier = 'low'
        elif any(f is None or f[name] != value for f in far):
            tier = 'medium'
        else:
            tier = 'high'
        facts.append({'fact': name, 'value': value, 'nearest_boundary': boundary,
                      'margin_minutes': round(margin, 1), 'confidence': tier})
    return {
        'method': 'recompute at ±1× and ±2× the stated birth-time uncertainty: high = unchanged at ±2×, '
                  'medium = unchanged at ±1× only, low = changes within ±1×',
        'birth_time_uncertainty_minutes': uncertainty_minutes,
        'facts': facts,
        'review_needed': audit['review_needed'] or any(f['confidence'] == 'low' for f in facts),
        'notes': [
            '置信度只衡量出生时间误差会不会让这项排盘结果改变，不衡量传统解释是否正确。',
            '紫微命宫/身宫随时辰变化，与八字时柱共用时辰交界距离。',
        ],
    }


# --- verifier sub-agent ---------------------------------------------------------

VERIFY_TOOL = {
    'name': 'report_verification',
    'description': 'Report, for each chart claim in the answer, whether the tool results support it.',
    'schema': {
        'type': 'object', 'additionalProperties': False, 'required': ['claims', 'overall'],
        'properties': {
            'claims': {'type': 'array', 'maxItems': 12, 'items': {
                'type': 'object', 'additionalProperties': False,
                'required': ['claim', 'support', 'confidence', 'reason'],
                'properties': {
                    'claim': {'type': 'string', 'maxLength': 300},
                    'support': {'type': 'string', 'enum': ['tool_backed', 'partially_backed', 'unsupported']},
                    'confidence': {'type': 'string', 'enum': ['high', 'medium', 'low']},
                    'reason': {'type': 'string', 'maxLength': 300},
                }}},
            'overall': {'type': 'string', 'maxLength': 400},
        },
    },
}

VERIFY_PROMPT = """你是玄枢的核验员，和写回答的助手相互独立。你只能看到用户问题、助手回答和本轮工具的原始返回结果，不能调用工具。

任务：找出回答里关于命盘、干支、星曜、四化、节气、奇门等计算事实的陈述（最多 12 条，优先挑结论性陈述），逐条判断：
- tool_backed：工具结果里能直接找到。
- partially_backed：部分能找到，或回答做了工具结果没有的推断、引申。
- unsupported：工具结果里找不到，或与工具结果矛盾。
confidence 表示你对这条判断本身有多确定。reason 用回答所用的语言写一句话，指出对应的工具和字段。
不要评价传统解释是否灵验，也不要核验用户自述的现实信息。最后在 overall 里用一两句话总结。必须调用 report_verification 提交结果。"""


class VerifiedClaim(BaseModel):
    model_config = ConfigDict(extra='forbid')
    claim: str = Field(max_length=300)
    support: Literal['tool_backed', 'partially_backed', 'unsupported']
    confidence: Tier
    reason: str = Field(max_length=300)


class Verification(BaseModel):
    model_config = ConfigDict(extra='forbid')
    claims: list[VerifiedClaim] = Field(max_length=12)
    overall: str = Field(max_length=400)


def verifier_input(question: str, answer: str, evidence: list[dict]) -> str:
    """One user message for the verifier; evidence is cut to a fixed budget."""
    parts, used = [], 0
    for item in evidence:
        text = json.dumps(item, ensure_ascii=False, default=str)
        if used + len(text) > MAX_EVIDENCE_CHARS:
            parts.append(json.dumps({'tool': item['tool'], 'omitted': '超出核验输入上限'}, ensure_ascii=False))
            continue
        parts.append(text)
        used += len(text)
    return ('<question>\n' + question + '\n</question>\n<answer>\n' + answer + '\n</answer>\n<tool_results>\n'
            + ('\n'.join(parts) or '（本轮没有调用工具）') + '\n</tool_results>')


# A verify function makes one forced tool call: (config, system prompt, user text) -> raw tool input or None.
VerifyFn = Callable[[Any, str, str], Any]


def anthropic_verify(config: Any, system: str, user_text: str) -> Any:
    import anthropic

    client = anthropic.Anthropic(api_key=config.api_key) if config.api_key else anthropic.Anthropic()
    response = client.beta.messages.create(
        model=config.model, max_tokens=4000, system=system,
        tools=[{'name': VERIFY_TOOL['name'], 'description': VERIFY_TOOL['description'], 'input_schema': VERIFY_TOOL['schema']}],
        tool_choice={'type': 'tool', 'name': VERIFY_TOOL['name']},
        messages=[{'role': 'user', 'content': user_text}],
        output_config={'effort': 'low'},
        betas=['server-side-fallback-2026-07-01'], fallbacks='default',
    )
    return next((b.input for b in response.content if b.type == 'tool_use'), None)


def openai_verify(config: Any, system: str, user_text: str) -> Any:
    import openai

    kwargs = {k: v for k, v in (('api_key', config.api_key), ('base_url', config.base_url)) if v}
    response = openai.OpenAI(**kwargs).chat.completions.create(
        model=config.model,
        messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user_text}],
        tools=[{'type': 'function', 'function': {'name': VERIFY_TOOL['name'], 'description': VERIFY_TOOL['description'],
                                                 'parameters': VERIFY_TOOL['schema']}}],
        tool_choice={'type': 'function', 'function': {'name': VERIFY_TOOL['name']}},
    )
    calls = response.choices[0].message.tool_calls or []
    return json.loads(calls[0].function.arguments) if calls else None


VERIFIERS: dict[str, VerifyFn] = {'anthropic': anthropic_verify, 'openai': openai_verify}


def run_verifier(verify: VerifyFn, config: Any, question: str, answer: str, evidence: list[dict]) -> dict:
    """Never raises: a failed verification is reported, the answer stays usable."""
    try:
        raw = verify(config, VERIFY_PROMPT, verifier_input(question, answer, evidence))
        if raw is None:
            return {'status': 'failed', 'error': '核验员没有返回结果'}
        result = Verification.model_validate(raw)
    except ValidationError:
        return {'status': 'failed', 'error': '核验结果格式不符合要求'}
    except Exception as exc:  # provider or network error; keep the answer
        return {'status': 'failed', 'error': f'核验调用失败：{type(exc).__name__}'}
    counts = {key: sum(c.support == key for c in result.claims) for key in ('tool_backed', 'partially_backed', 'unsupported')}
    return {'status': 'ok', 'claims': [c.model_dump() for c in result.claims], 'overall': result.overall, 'counts': counts}
