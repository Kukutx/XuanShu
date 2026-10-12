"""MCP JSON-RPC core shared by stdio and stateless Streamable HTTP.

Supports the 2026-07-28 stateless request-metadata dialect and older
2025 initialize-handshake revisions. No server-initiated SSE or sessions.
"""
from __future__ import annotations

import json
from pathlib import Path
from .asset_paths import resource_root
from .mcp_skill_import import list_importable_skills, get_importable_skill, get_skill_resource
from typing import Any

from pydantic import ValidationError

from . import __version__
from .analysis import symbolic_reading
from .evidence import DeepReviewRequest, deep_evidence_review
from .consultation import ConsultationRequest, execute_consultation
from .qimen import QimenRequest, qimen_chart
from .date_selection import DateScanRequest, date_candidate_scan
from .life_path import LifePathRequest, life_path_review
from .ziwei_pair import ziwei_pair_overlay
from .pillar_search import PillarSearchRequest, pillars_to_dates
from .chart_import import ChartImportRequest, chart_import_check
from .almanac import DailyAlmanacRequest, daily_almanac
from .group import GroupRequest, group_relations
from .rule_matrix import RuleMatrixRequest, rule_matrix
from .ziwei_horoscope import ZiweiHoroscopeRequest, ziwei_horoscope
from .professional_ziwei import ProfessionalZiweiRequest, professional_ziwei_chart
from .chart_audit import QimenAuditRequest, qimen_reference_audit
from .extended import LunarToGregorianRequest, BirthWindowRequest, lunar_to_gregorian, birth_window
from .astronomy import get_solar_terms
from .report import ReportRequest, structured_report
from .quality import QualityAuditRequest, calculation_quality_audit
from .advanced import DayunRequest, BirthBoundaryRequest, dayun_sequence, birth_boundary_map
from .workflows import (DayOfficerRequest, TimelineRequest, DecisionMatrixRequest,
                        day_officer_calendar, annual_timeline, decision_matrix)
from .engines import BirthInput, calculate_bazi, calculate_ziwei, combined_chart
from .features import CalendarRequest, PairComparisonInput, PairInput, PalaceRequest, AnnualRequest, TimeAuditRequest, RuleComparisonRequest, calendar_days, compare_charts, palace_detail, annual_transformations, time_audit, rule_comparison

PROTOCOL = '2025-11-25'  # legacy initialization fallback
MODERN_PROTOCOL = '2026-07-28'
SUPPORTED_PROTOCOLS = {'2025-03-26', '2025-06-18', '2025-11-25', MODERN_PROTOCOL}
ROOT = resource_root()

TOOL_DEFS = [
    {'name': 'consultation_execute', 'title': '真实问题驱动的可执行咨询工作流', 'description': 'Execute a stateless, deterministic plan over existing tools; return missing inputs, trace, rule-backed observations, safe continuation cursor and markdown. No model inference or personal data persistence.', 'inputSchema': ConsultationRequest.model_json_schema()},
    {'name': 'deep_evidence_review', 'title': '有规则引用的八字紫微跨体系深度分析', 'description': 'Evidence-backed structural review with exact source-field pointers, rule references, trines/opposition, natal/annual transformations, boundary audit and explicit non-independent cross-method checks. No predictions.', 'inputSchema': DeepReviewRequest.model_json_schema()},
    {'name': 'ziwei_professional_chart', 'title': '可选专业紫微星盘与运限', 'description': 'Local iztro-py provider for an extended natal chart and optional horoscope overlay. Requires optional installed provider; no silent fallback.', 'inputSchema': ProfessionalZiweiRequest.model_json_schema()},
    {'name': 'qimen_reference_audit', 'title': '奇门全盘逐字段核对', 'description': 'Compare documented external reference fields including any supplied nine-palace star/door/deity/stems, report all mismatches, never assume unprovided fields agree.', 'inputSchema': QimenAuditRequest.model_json_schema()},
    {'name': 'qimen_hour_chart', 'title': '时家奇门拆补转盘', 'description': 'Specified hour-chabu rotating Qimen: 24 solar terms, three yuan bureaus, nine palaces, three wonders/six instruments, eight doors, nine stars and eight deities. Unverified school variants omitted.', 'inputSchema': QimenRequest.model_json_schema()},
    {'name': 'bazi_chart', 'title': '八字排盘与藏干', 'description': 'BaZi four pillars, hidden stems with ten gods, Na Yin, twelve growth stages (day master per branch and each stem on its own branch), void branches (xun kong, with branches in the day or year void marked), stem combinations and clashes, branch pair labels and three-harmony or seasonal groups, sixteen traditional auxiliary stars (shensha) per pillar with the natal values that place them and the rule and source of each star (shensha_rules: a San Ming Tong Hui chapter, or the Zi Wei placement table for Hong Luan and Tian Xi), and adjacent jie solar terms; labels only, no good-or-bad reading and no life predictions.', 'inputSchema': BirthInput.model_json_schema()},
    {'name': 'ziwei_chart', 'title': '紫微排盘与四化', 'description': 'Partial Zi Wei chart with 12 palaces, 14 major stars, 44 selected auxiliary and minor stars, star brightness (庙旺得利平不陷, from iztro\'s published table) for the major stars and 文昌, 文曲, 火星, 铃星, 擎羊, 陀罗, natal transformations and palace flying mappings. School-specific; brightness is not a luck score.', 'inputSchema': BirthInput.model_json_schema()},
    {'name': 'combined_chart', 'title': '八字紫微联合排盘', 'description': 'Calculate both BaZi and partial Zi Wei charts, preserving method metadata.', 'inputSchema': BirthInput.model_json_schema()},
    {'name': 'symbolic_reading', 'title': '文化规则说明', 'description': 'Explain fields and traditional symbolic labels without inventing predictions.', 'inputSchema': BirthInput.model_json_schema()},
    {'name': 'solar_terms', 'title': '二十四节气', 'description': 'Get China-time instants of 24 solar terms in one Gregorian year.', 'inputSchema': {'type': 'object', 'properties': {'year': {'type': 'integer', 'minimum': 1901, 'maximum': 2099}}, 'required': ['year'], 'additionalProperties': False}},
    {'name': 'calendar_days', 'title': '连续农历日历', 'description': 'List 1–31 days with lunar dates, day stems/branches and solar-term occurrences; no auspicious-day claims.', 'inputSchema': CalendarRequest.model_json_schema()},
    {'name': 'pair_comparison', 'title': '双人四柱对照', 'description': 'Compare two sets of pillars: the day-stem ten god in both directions, the day-stem five combination, the zodiac labels and every labelled branch link across the four pillars (same branch, six harmony, six clash, six harm, punishment), plus the same-position table. person_a_hour_unknown / person_b_hour_unknown leave that hour pillar out (and any pillar that changes during an unknown-hour birth day). With year, year_view lists the year pillar read against both charts, each person\'s luck pillar in that year (needs gender; with an unknown hour both possibilities when they differ) and the labels between the two luck pillars, with luck_timeline, as in group_relations. No compatibility score.', 'inputSchema': PairComparisonInput.model_json_schema()},
    {'name': 'ziwei_pair_overlay', 'title': '双人紫微宫位叠盘', 'description': 'Overlay two Zi Wei charts on the shared twelve-branch grid: palace-by-palace comparison, where each Ming/Shen palace lands in the other chart, and each birth-year stem four-transformation looked up in the other chart. Both birth hours are required: an hour_unknown flag is refused. No compatibility score.', 'inputSchema': PairInput.model_json_schema()},
    {'name': 'annual_transformations', 'title': '指定农历年干四化', 'description': 'Map a named lunar year stem four-transformations to natal star positions (not a complete annual chart).', 'inputSchema': AnnualRequest.model_json_schema()},
    {'name': 'time_basis_audit', 'title': '时制敏感性分析', 'description': 'Compare clock, longitude-based mean solar and apparent solar time for a birth with longitude. Each mode returns its effective reading, shift and equation of time, pillars, Life/Body palaces and lunar date; dst_minutes and longitude_vs_standard_meridian_minutes split the solar shift into daylight saving and the longitude offset from the zone standard meridian.', 'inputSchema': TimeAuditRequest.model_json_schema()},
    {'name': 'rule_comparison', 'title': '两套排盘规则对照', 'description': 'Compare BaZi pillars and Zi Wei major natal indices using two parameter configurations.', 'inputSchema': RuleComparisonRequest.model_json_schema()},
    {'name': 'structured_report', 'title': '跨工具可追溯综合报告', 'description': 'Reproducible BaZi + partial Zi Wei dossier with optional named-year and solar-time audit; tool provenance and downloadable Markdown, no predictions.', 'inputSchema': ReportRequest.model_json_schema()},
    {'name': 'lunar_to_gregorian', 'title': '农历反查公历', 'description': 'Convert a modern China lunar year/month/day with leap-month flag back to Gregorian date; reject invalid leap dates.', 'inputSchema': LunarToGregorianRequest.model_json_schema()},
    {'name': 'birth_time_window', 'title': '出生时间误差区间', 'description': 'Sample BaZi and partial Zi Wei charts across a time uncertainty range, listing distinct observed structures and sampling limitations.', 'inputSchema': BirthWindowRequest.model_json_schema()},
    {'name': 'chart_quality_audit', 'title': '排盘输入与边界审计', 'description': 'Audit birth-time and solar-term boundaries (with the names and instants of the adjacent jie), time-zone assumptions, and published lunar uncertainties without silently changing astronomical data.', 'inputSchema': QualityAuditRequest.model_json_schema()},
    {'name': 'day_officers', 'title': '建除十二值日查询', 'description': 'Traditional twelve-day-officer calendar derived from solar-term month branch and sexagenary day branch; on a jie day, jie_on_date names the term, its China time, and the month branch and officer before and after it. Explicitly not auspicious-day advice.', 'inputSchema': DayOfficerRequest.model_json_schema()},
    {'name': 'annual_timeline', 'title': '连续农历年四化轨迹', 'description': 'Consecutive named lunar-year stem four-transformations mapped to one natal chart; no annual fate forecast.', 'inputSchema': TimelineRequest.model_json_schema()},
    {'name': 'decision_matrix', 'title': '透明多方案决策矩阵', 'description': 'Compare user-scored options with transparent normalized weights and leave-one-out sensitivity; entirely non-astrological.', 'inputSchema': DecisionMatrixRequest.model_json_schema()},
    {'name': 'bazi_dayun', 'title': '八字大运十年干支', 'description': 'Traditional direction, adjacent jie, nominal age and 10-year pillars, each read against the natal chart (natal_interactions: ten god, Na Yin, growth stages, day/year void, stem and branch relations with each natal pillar, three-harmony or seasonal groups it completes, the auxiliary stars it carries by the natal bases); shensha_rules gives the rule and source of each star; include_years adds every civil year of each period read the same way; hour_unknown leaves out the hour pillar. Cultural labels without predictions.', 'inputSchema': DayunRequest.model_json_schema()},
    {'name': 'birth_boundary_map', 'title': '出生时间边界地图', 'description': 'Locate modeled hour, day, solar-term and DST transitions across a birth uncertainty interval; each segment gives its UTC and birth-zone local start and end, its four pillars and its Zi Wei Life/Body palaces, bureau and lunar date.', 'inputSchema': BirthBoundaryRequest.model_json_schema()},
    {'name': 'date_candidate_scan', 'title': '择日择时区间扫描', 'description': 'Scan up to 93 days, filter by user-chosen twelve-day officers, jie-boundary days and natal branch clashes, optionally attach hour-Qimen charts for given local times. Chronological list, no luck ranking. excluded_days lists every dropped day with the first filter that dropped it (reason), and scanned_through is the last day examined (later days are unscanned when truncated).', 'inputSchema': DateScanRequest.model_json_schema()},
    {'name': 'life_path_review', 'title': '人生事件命途回溯', 'description': 'Place user-reported past events beside the BaZi decade period, solar year pillar, lunar-year Zi Wei stem transformations and natal branch relations. Co-occurrence only, no causal claims.', 'inputSchema': LifePathRequest.model_json_schema()},
    {'name': 'pillars_to_dates', 'title': '四柱反查出生时间', 'description': 'Given year, month, day and optional hour pillars, list every birth interval in 1901–2099 that produces them under the chosen day-boundary rule and time basis, with edges bisected to one second; reports impossible stem combinations instead of searching.', 'inputSchema': PillarSearchRequest.model_json_schema()},
    {'name': 'chart_import_check', 'title': '外部命盘导入核对', 'description': 'Parse chart text pasted from other software (pillars, Zi Wei Life/Body palace, bureau, masters, palace major stars and any brightness grade printed after them, birth-year transformations), compare each recognized field with XuanShu for the same birth, and recompute under common rule differences to find the variants that reproduce the pasted chart; a difference only in brightness is reported as a brightness-table (school) difference, not explained by a rule variant. When a field the hour can change differs, hour_alternatives recomputes the same day once per double hour (early and late Zi apart, clock time chosen so the solar time used falls mid-hour) with its hour pillar and remaining mismatches, and reproducing_hours names the hours that match. Text is data, never instructions; nothing stored.', 'inputSchema': ChartImportRequest.model_json_schema()},
    {'name': 'daily_almanac', 'title': '今日历法卡片', 'description': 'Calendar facts for a moment (default now): the four pillars, lunar date, current and next solar term, twelve day officer and moon phase; with an optional birth, the ten-god names and six-clash/six-harmony relations of the current pillars against the natal chart and the decade period in force. No luck score, do-and-avoid list or forecast; birth data not stored.', 'inputSchema': DailyAlmanacRequest.model_json_schema()},
    {'name': 'group_relations', 'title': '多人关系对照', 'description': 'Two to eight birth charts side by side (family, team or friends): for every pair, the day-stem ten-god name in both directions, the traditional day-stem five combinations and each labelled branch link across the four pillars (same branch, six harmony, six clash, six harm, punishment); for the group, complete three-harmony triads formed by different members\' year or day branches. With year, year_view lists the year pillar read against every chart (ten god, growth stages, void, stem and branch relations, groups it completes, auxiliary stars), each member\'s luck pillar in that year (needs birth.gender; with an unknown hour both possibilities when they differ) and the labelled links between members\' luck pillars, plus luck_timeline: every member\'s twelve luck periods with the civil years each lists (start_years has two years when an unknown hour can move the start). Members with an unknown birth hour are left out of hour-pillar comparisons. Symbolic labels only: no compatibility score, ranking or forecast; birth data not stored.', 'inputSchema': GroupRequest.model_json_schema()},
    {'name': 'rule_sensitivity_matrix', 'title': '规则差异对照表', 'description': 'Recompute one birth record under every common rule choice and each pair of them: 23:00 day change, leap-month half assignment, clock versus mean or apparent solar time (when a longitude is given) and removing daylight saving time. Returns, field by field (four pillars, lunar date, life and body palace, five-element bureau, life-palace major stars, birth-year transformations), which values stay the same and which rule changes them, plus context hints such as a nearby jie boundary. Does not say which rule is correct; birth data not stored.', 'inputSchema': RuleMatrixRequest.model_json_schema()},
    {'name': 'ziwei_horoscope', 'title': '紫微运限（大限到流时）', 'description': 'Zi Wei period layers for one date: decade, small limit, year, month (斗君 rule), day and, with a clock time, hour. For each layer: the palace serving as that period\'s Life palace, the names it gives the twelve palaces, the four transformations of the period\'s stem placed on the natal stars, and the layer\'s ten period stars (流曜: 魁钺昌曲禄羊陀马鸾喜 from the layer\'s own stem and branch, named 运/流/月/日/时; none for the small limit), each with its natal and layer palace; the year also gets 年解 and that year\'s 岁前 and 将前 twelve gods. The decade, month, day and hour layers depend on the birth hour and are left out when it is unknown. Traditional symbolic labels only: no event forecast; birth data not stored.', 'inputSchema': ZiweiHoroscopeRequest.model_json_schema()},
    {'name': 'palace_detail', 'title': '十二宫重点查看', 'description': 'Get a selected palace, included stars, natal transformation markers, flying mappings and traditional topic.', 'inputSchema': PalaceRequest.model_json_schema()},
]
TOOLS = {item['name']: item for item in TOOL_DEFS}
RESOURCE_TEXT = {
    'astro://rules/consultation': 'docs/rules/consultation.md',
    'astro://rules/evidence': 'docs/rules/evidence.md',
    'astro://rules/qimen': 'docs/rules/qimen.md',
    'astro://rules/oauth': 'docs/rules/oauth.md',
    'astro://rules/bazi': 'docs/rules/bazi.md',
    'astro://rules/ziwei': 'docs/rules/ziwei.md',
    'astro://rules/privacy': 'docs/rules/privacy.md',
    'astro://rules/solar-time': 'docs/rules/solar-time.md',
    'astro://rules/limitations': 'docs/rules/limitations.md',
    'astro://rules/lunar-inverse': 'docs/rules/lunar-inverse.md',
    'astro://rules/birth-window': 'docs/rules/birth-window.md',
    'astro://rules/quality': 'docs/rules/quality.md',
    'astro://rules/jianchu': 'docs/rules/jianchu.md',
    'astro://rules/timeline': 'docs/rules/timeline.md',
    'astro://rules/decision': 'docs/rules/decision.md',
    'astro://rules/dayun': 'docs/rules/dayun.md',
    'astro://rules/boundary-map': 'docs/rules/boundary-map.md',
}
RESOURCES = [
    {'uri': uri, 'name': file.rsplit('/', 1)[-1].removesuffix('.md'), 'description': f'XuanShu rule reference: {uri}', 'mimeType': 'text/markdown'}
    for uri, file in RESOURCE_TEXT.items()
]
PROMPTS = [
    {'name': 'deep-evidence-review', 'title': '有来源的结构推演与反证', 'description': 'Use computed BaZi and Zi Wei to trace each conclusion to rule and field evidence.', 'arguments': [{'name': 'focus', 'description': 'Selected palace or specific question', 'required': False}]},
    {'name':'explain-qimen', 'title':'奇门九宫结构解读', 'description':'Explain the specified rotating school labels without predicting outcomes.', 'arguments':[{'name':'focus','description':'Optional palace or rule','required':False}]},
    {'name': 'explain-bazi', 'title': '八字结构解释', 'description': 'Explain stems, branches, hidden stems and rules from a computed BaZi chart.', 'arguments': [{'name': 'focus', 'description': 'Optional focus, e.g. 藏干 / 节气', 'required': False}]},
    {'name': 'explain-ziwei', 'title': '紫微重点宫位说明', 'description': 'Use a computed palace and four-transformation data to describe traditional symbols.', 'arguments': [{'name': 'focus', 'description': 'Optional palace name or question', 'required': False}]},
    {'name': 'audit-solar-time', 'title': '经度与时制核对', 'description': 'Compare clock / mean / apparent solar time rules.', 'arguments': [{'name': 'focus', 'description': 'Longitude or time-sensitive concern', 'required': False}]},
    {'name': 'prepare-report', 'title': '编排计算报告', 'description': 'Build an auditable cultural dossier from computed tools.', 'arguments': [{'name': 'focus', 'description': 'Optional audit concern', 'required': False}]},
    {'name': 'audit-birth-window', 'title': '时刻误差采样', 'description': 'Sample plausible birth times around an uncertain minute.', 'arguments': [{'name': 'focus', 'description': 'Time uncertainty concern', 'required': False}]},
    {'name': 'convert-lunar', 'title': '农历日期反查', 'description': 'Convert a lunar date with an explicit leap-month option.', 'arguments': [{'name': 'focus', 'description': 'Lunar month/date to check', 'required': False}]},
    {'name': 'audit-quality', 'title': '排盘数据质量与日界核验', 'description': 'Review astronomical boundaries and HKO-published future lunar uncertainties.', 'arguments': [{'name': 'focus', 'description': 'Boundary concern, e.g. 2057 lunar leap date', 'required': False}]},
    {'name': 'explore-day-officers', 'title': '建除十二值日', 'description': 'Review twelve officer tags, solar term month rules and boundary flags.', 'arguments': [{'name': 'focus', 'description': 'Optional date selection focus', 'required': False}]},
    {'name': 'explore-annual-timeline', 'title': '连续农历年份的四化标签', 'description': 'Trace named lunar-year stem transformations on the same natal chart.', 'arguments': [{'name': 'focus', 'description': 'Optional palace or period of interest', 'required': False}]},
    {'name': 'compare-options', 'title': '透明决策方案对照', 'description': 'Compare factual options using explicit user criteria and ratings.', 'arguments': [{'name': 'focus', 'description': 'Optional decision question', 'required': False}]},
    {'name': 'explain-dayun', 'title': '大运干支排法', 'description': 'Verify direction, month pillar and adjacent jie without forecasts.', 'arguments': [{'name':'focus','description':'Optional school rule','required':False}]},
    {'name': 'audit-birth-boundaries', 'title': '生时误差临界时刻核查', 'description': 'Locate modeled switches across uncertain birth times.', 'arguments': [{'name':'focus','description':'Optional birth-time concern','required':False}]},
    {'name': 'compare-charts', 'title': '双人盘文化对照', 'description': 'Ask for two birth records and show only structural comparisons.', 'arguments': [{'name': 'focus', 'description': 'Optional comparison focus', 'required': False}]},
]


def call_tool(name: str, args: dict) -> Any:
    if name not in TOOLS:
        raise ValueError(f'Unknown MCP tool: {name}')
    if name == 'solar_terms':
        if set(args) != {'year'} or type(args.get('year')) is not int or not (1901 <= args['year'] <= 2099):
            raise ValueError('solar_terms requires integer year between 1901 and 2099')
        return {'year': args['year'], 'timezone': 'Asia/Shanghai', 'terms': get_solar_terms(args['year'])}
    mapping = {
        'consultation_execute': (ConsultationRequest, execute_consultation),
        'deep_evidence_review': (DeepReviewRequest, deep_evidence_review),
        'ziwei_professional_chart': (ProfessionalZiweiRequest, professional_ziwei_chart),
        'qimen_reference_audit': (QimenAuditRequest, qimen_reference_audit),
        'qimen_hour_chart': (QimenRequest, qimen_chart),
        'bazi_chart': (BirthInput, calculate_bazi),
        'ziwei_chart': (BirthInput, calculate_ziwei),
        'combined_chart': (BirthInput, combined_chart),
        'symbolic_reading': (BirthInput, symbolic_reading),
        'calendar_days': (CalendarRequest, calendar_days),
        'pair_comparison': (PairComparisonInput, compare_charts),
        'ziwei_pair_overlay': (PairInput, ziwei_pair_overlay),
        'palace_detail': (PalaceRequest, palace_detail),
        'annual_transformations': (AnnualRequest, annual_transformations),
        'time_basis_audit': (TimeAuditRequest, time_audit),
        'rule_comparison': (RuleComparisonRequest, rule_comparison),
        'structured_report': (ReportRequest, structured_report),
        'lunar_to_gregorian': (LunarToGregorianRequest, lunar_to_gregorian),
        'birth_time_window': (BirthWindowRequest, birth_window),
        'chart_quality_audit': (QualityAuditRequest, calculation_quality_audit),
        'day_officers': (DayOfficerRequest, day_officer_calendar),
        'annual_timeline': (TimelineRequest, annual_timeline),
        'decision_matrix': (DecisionMatrixRequest, decision_matrix),
        'bazi_dayun': (DayunRequest, dayun_sequence),
        'birth_boundary_map': (BirthBoundaryRequest, birth_boundary_map),
        'date_candidate_scan': (DateScanRequest, date_candidate_scan),
        'life_path_review': (LifePathRequest, life_path_review),
        'pillars_to_dates': (PillarSearchRequest, pillars_to_dates),
        'chart_import_check': (ChartImportRequest, chart_import_check),
        'daily_almanac': (DailyAlmanacRequest, daily_almanac),
        'group_relations': (GroupRequest, group_relations),
        'rule_sensitivity_matrix': (RuleMatrixRequest, rule_matrix),
        'ziwei_horoscope': (ZiweiHoroscopeRequest, ziwei_horoscope),
    }
    model, function = mapping[name]
    return function(model.model_validate(args))


def error_response(id_: Any, code: int, message: str, data: dict | None = None) -> dict:
    err = {'code': code, 'message': message}
    if data is not None:
        err['data'] = data
    return {'jsonrpc': '2.0', 'id': id_, 'error': err}


def unsupported_version(id_: Any, version: str | None) -> dict:
    return error_response(id_, -32022, 'Unsupported protocol version',
                          {'supported': sorted(SUPPORTED_PROTOCOLS, reverse=True), 'requested': version})


def _prompt_get(params: dict) -> dict:
    name = params.get('name')
    prompt = next((item for item in PROMPTS if item['name'] == name), None)
    if not prompt:
        raise ValueError(f'Unknown prompt: {name}')
    args = params.get('arguments', {})
    if not isinstance(args, dict):
        raise ValueError('Prompt arguments must be an object')
    focus = args.get('focus', '无特定方向')
    if not isinstance(focus, str) or len(focus) > 200:
        raise ValueError('focus must be text no longer than 200 characters')
    prompts = {
        'deep-evidence-review': '先调用 deep_evidence_review，选择关注宫位，逐条展示 observation、evidence.path、rule_ids、对应公开规则及 limit。对照八字立春年界与紫微农历年界，明示同源数据不算外部验证。可调用 structured_report(include_deep_evidence=true) 导出 Markdown。所有引用是方法参考，不要冒充权威逐盘验算或推断人生。',
        'explain-qimen': '先调用 qimen_hour_chart，只解释节气、阴阳遁、三元局数、九宫、八门、九星及八神的传统排布。说明本实现只涵盖时家拆补转盘配置，不含置闰或其他流派，不作现实吉凶预测。',
        'explain-bazi': '请先调用 bazi_chart 工具，用出生地当地时间核对四柱和节令，再解释藏干、纳音及十神的计算含义。',
        'explain-ziwei': '请先调用 ziwei_chart，必要时调用 palace_detail；区分生年四化和宫干飞化，注明流派及未实现的星曜。',
        'prepare-report': '这是问题驱动的执行流程。优先调用 consultation_execute 来执行真实的 Clarify/Compute/Verify 工作流（不要仅凭提示编造工具调用）；工具会返回 intent/status/missing_inputs/tool_trace/observations/continuation 与限制。若 status=needs_input 或 partial，先请用户确认所需输入；可用 continuation 跨次承接主题，但出生参数仍须重新提供。需要 LLM 表达时只据返回的证据分析，不得冒充执行器调用了语言模型。此前的指引仍适用：先明确用户实际问题、时间范围及必要出生输入，再判断是本命、年度职业、关系合盘、多候选择时、方案比较还是流派争议。先检查需要的出生数据质量；按需求选择 bazi_chart、ziwei_chart、deep_evidence_review、pair_comparison、annual_transformations、qimen_hour_chart、decision_matrix 等真实工具，不要每次全部调用。需要报告时调用 structured_report(include_deep_evidence=true)，有经度才启用 include_time_audit，完整保留 tool_trace、provenance、limitations。将计算事实、传统解释、用户提供的现实事实和推测分层陈述；检查流派差异与不完整紫微运限，不输出科学预测、无来源现实信息或虚构成功率。当前没有服务器长期记忆、真人账户及在线自主 Agent，不得假装已保存人生事件或完成真实联网核验。',
        'audit-birth-window': '请确认估计的出生时间、时区及误差分钟，再调用 birth_time_window，并明确指出这是离散采样、可能漏掉采样点之间的边界。',
        'convert-lunar': '请确认农历年月日及是否闰月，再调用 lunar_to_gregorian；不存在的闰月或农历三十日应明确报错。',
        'explore-day-officers': '先调用 day_officers，并明确选择的时区为北京时间、节令日可能存在日内变化。只讲建除十二值日的传统名称，不输出吉凶结论或宜忌保证。',
        'explore-annual-timeline': '先调用 annual_timeline 查看连续农历年四化映射，列出年份范围与关注宫位；四化次数不是命运概率或年份好坏。',
        'compare-options': '先让使用者定义方案、核验过的评价维度、权重和0至5评分，再调用 decision_matrix。解释评分主观性与剔除单一指标敏感性，不引用出生数据来决定现实结果。',
        'explain-dayun': '先确认出生信息和大运顺逆（性别未指定时要求显式方向），调用 bazi_dayun，核对本命月柱、十二节交接、三日一岁折算，清楚标明公历投影仅为近似，不能预测事件。',
        'audit-birth-boundaries': '先调用 birth_boundary_map 按模型边界分段，说明1秒定位精度仅是算法数值，不等于实际出生时刻已知；对每段比较八字和部分紫微，禁止作命运预测。',
        'compare-charts': '请先分别确认两个人的出生资料，再调用 pair_comparison（八字四柱）和 ziwei_pair_overlay（紫微宫位叠盘），只呈现结构对照和传统关系标签，不给匹配分数。',
        'audit-solar-time': '先确认出生时区及出生地经度，再调用 time_basis_audit 比较三种时制的有效时间与四柱/命宫差异。',
        'audit-quality': '先核对出生信息、时区及流派配置，再调用 chart_quality_audit；如位于香港天文台发布的远期不确定新月区间，必须披露差异，禁止未经证实地调整日期。',
    }
    body = prompts[name] + f'\n关注点：{focus}\n严格区分算法结果、传统象征和未经证实的推断；不预测现实人生结果。'
    return {'description': prompt['description'], 'messages': [{'role': 'user', 'content': {'type': 'text', 'text': body}}]}


def process_rpc(payload: Any) -> dict | None:
    if not isinstance(payload, dict) or payload.get('jsonrpc') != '2.0' or not isinstance(payload.get('method'), str):
        return error_response(payload.get('id') if isinstance(payload, dict) else None, -32600, 'Invalid JSON-RPC request')
    method, id_ = payload['method'], payload.get('id')
    if 'id' in payload and (isinstance(id_, bool) or not isinstance(id_, (str, int))):
        return error_response(None, -32600, 'Invalid JSON-RPC id')
    raw_params = payload.get('params')
    if raw_params is not None and not isinstance(raw_params, dict):
        return error_response(id_, -32602, 'params must be an object')
    raw_params = raw_params or {}
    meta = raw_params.get('_meta')
    if meta is not None and not isinstance(meta, dict):
        return error_response(id_, -32602, 'params._meta must be an object')
    declared_version = meta.get('io.modelcontextprotocol/protocolVersion') if meta else None
    if declared_version is not None and not isinstance(declared_version, str):
        return error_response(id_, -32602, 'protocolVersion must be a string')
    if declared_version is not None and declared_version not in SUPPORTED_PROTOCOLS:
        return unsupported_version(id_, declared_version)
    modern = declared_version == MODERN_PROTOCOL
    if modern and (not isinstance(meta, dict) or not isinstance(meta.get('io.modelcontextprotocol/clientCapabilities'), dict)):
        return error_response(id_, -32602, '2026-07-28 requests require object clientCapabilities in params._meta')
    if 'id' not in payload:
        return None  # notifications are one-way
    params = raw_params
    if modern and method in ('initialize', 'ping', 'resources/subscribe', 'resources/unsubscribe'):
        return error_response(id_, -32601, f'Method retired in {MODERN_PROTOCOL}: {method}')
    if method == 'server/discover':
        result = {
            'supportedVersions': sorted(SUPPORTED_PROTOCOLS, reverse=True),
            'capabilities': {'tools': {}, 'resources': {}, 'prompts': {}, 'extensions': {'io.modelcontextprotocol/skills': {}}},
            'instructions': 'Deterministic cultural calculations; Zi Wei is partial and all prediction claims are unverified.',
            'ttlMs': 300000, 'cacheScope': 'public',
        }
    elif method == 'initialize':
        desired = params.get('protocolVersion')
        if desired is not None and not isinstance(desired, str):
            return error_response(id_, -32602, 'initialize.protocolVersion must be a string')
        negotiated = desired if desired in SUPPORTED_PROTOCOLS - {MODERN_PROTOCOL} else PROTOCOL
        result = {
            'protocolVersion': negotiated,
            'capabilities': {'tools': {'listChanged': False}, 'resources': {'subscribe': False, 'listChanged': False}, 'prompts': {'listChanged': False}, 'extensions': {'io.modelcontextprotocol/skills': {}}},
            'serverInfo': {'name': 'xuanshu', 'version': __version__},
            'instructions': 'Traditional calendar algorithms and symbolic labels; Zi Wei is partial and school-specific. No scientifically verified fortune predictions.',
        }
    elif method == 'ping':
        result = {}
    elif method == 'tools/list':
        result = {'tools': TOOL_DEFS}
        if modern:
            result.update({'ttlMs': 300000, 'cacheScope': 'public'})
    elif method == 'resources/list':
        result = {'resources': RESOURCES}
        if modern:
            result.update({'ttlMs': 300000, 'cacheScope': 'public'})
    elif method == 'skills/list':
        try:
            cursor = params.get('cursor')
            if cursor is not None and not isinstance(cursor, str):
                raise ValueError('skills/list cursor must be a string')
            result = list_importable_skills(cursor)
        except ValueError as exc:
            return error_response(id_, -32602, str(exc))
    elif method == 'skills/get':
        try:
            if not isinstance(params.get('uri'), str):
                raise ValueError('skills/get uri must be a string')
            result = get_importable_skill(params['uri'])
        except ValueError as exc:
            return error_response(id_, -32602, str(exc))
    elif method == 'resources/read':
        uri = params.get('uri')
        if not isinstance(uri, str):
            return error_response(id_, -32602, 'Unknown resource URI')
        if uri in RESOURCE_TEXT:
            result = {'contents': [{'uri': uri, 'mimeType': 'text/markdown', 'text': (ROOT / RESOURCE_TEXT[uri]).read_text(encoding='utf-8')}]}
        else:
            result = get_skill_resource(uri)
            if result is None:
                return error_response(id_, -32602, 'Unknown resource URI')
        if modern:
            result.update({'ttlMs': 300000, 'cacheScope': 'public'})
    elif method == 'prompts/list':
        result = {'prompts': PROMPTS}
        if modern:
            result.update({'ttlMs': 300000, 'cacheScope': 'public'})
    elif method == 'prompts/get':
        try:
            result = _prompt_get(params)
        except ValueError as exc:
            return error_response(id_, -32602, str(exc))
    elif method == 'tools/call':
        name, args = params.get('name'), params.get('arguments', {})
        if not isinstance(name, str) or not isinstance(args, dict):
            return error_response(id_, -32602, 'tools/call requires name and object arguments')
        if name not in TOOLS:
            return error_response(id_, -32602, f'Unknown tool: {name}')
        try:
            data = call_tool(name, args)
            result = {
                'content': [{'type': 'text', 'text': json.dumps(data, ensure_ascii=False)}],
                'structuredContent': data,
                'isError': False,
            }
        except (ValueError, ValidationError) as exc:
            result = {'content': [{'type': 'text', 'text': str(exc)}], 'isError': True}
    else:
        return error_response(id_, -32601, f'Method not found: {method}')
    if modern:
        result = {'resultType': 'complete', **result, '_meta': {
            'io.modelcontextprotocol/serverInfo': {'name': 'xuanshu', 'version': __version__}}}
    return {'jsonrpc': '2.0', 'id': id_, 'result': result}
