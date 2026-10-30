"""OpenAPI additions for the self-hosted API page at /docs.

FastAPI's bundled Swagger UI loads its scripts from a CDN and starts them with an inline
script; the page's Content-Security-Policy (script-src 'self') blocks both, so /docs used to
open blank. static/api.html reads /openapi.json instead. This module adds what that page and
any other OpenAPI client need: a group tag and a short title for every route, and a request
example for every JSON body. tests/test_api_docs.py posts each example and expects it to run.
"""
from __future__ import annotations

import re
from typing import Any

# Group order on the page; the titles are interface text (translated with the rest of the UI).
TAGS = [
    ('charts', '命盘与报告', 'Natal charts, reports and chart checks.'),
    ('periods', '运限与回溯', 'Luck pillars, annual periods and life-event review.'),
    ('calendar', '历法与日课', 'Calendar conversion, solar terms, almanac and day selection.'),
    ('birth-time', '出生时间核对', 'Solar time, birth-time windows and rule comparisons.'),
    ('qimen', '时家奇门', 'Bounded hour-Qimen charts and reference audits.'),
    ('relations', '多人对照', 'Two-person and group comparisons.'),
    ('consult', '咨询与 AI 对话', 'Consultation workflow, decision matrix and optional AI chat.'),
    ('system', '系统与 MCP', 'Health, capabilities, OAuth resource metadata and the MCP endpoint.'),
]

# path -> (tag, title). Every route in the schema needs an entry; tests fail on a missing one.
ROUTES: dict[str, tuple[str, str]] = {
    '/api/bazi': ('charts', '八字排盘'),
    '/api/ziwei': ('charts', '紫微斗数排盘'),
    '/api/combined': ('charts', '八字与紫微合盘'),
    '/api/analyze': ('charts', '结构分析'),
    '/api/report': ('charts', '综合报告'),
    '/api/palace': ('charts', '紫微单宫详解'),
    '/api/quality-audit': ('charts', '排盘质量审计'),
    '/api/deep-review': ('charts', '深度证据审阅'),
    '/api/ziwei-professional': ('charts', '专业紫微（可选引擎）'),
    '/api/chart-import-check': ('charts', '外部命盘导入核对'),
    '/api/dayun': ('periods', '八字大运'),
    '/api/annual': ('periods', '流年'),
    '/api/annual-timeline': ('periods', '流年时间线'),
    '/api/ziwei-horoscope': ('periods', '紫微运限'),
    '/api/life-path': ('periods', '人生事件回溯'),
    '/api/calendar': ('calendar', '万年历'),
    '/api/lunar/{day}': ('calendar', '公历转农历'),
    '/api/lunar-to-gregorian': ('calendar', '农历转公历'),
    '/api/pillars-to-dates': ('calendar', '四柱反查日期'),
    '/api/solar-terms/{year}': ('calendar', '二十四节气'),
    '/api/solar-terms/{year}.ics': ('calendar', '节气日历文件（ICS）'),
    '/api/daily-almanac': ('calendar', '每日宜忌参考'),
    '/api/day-officers': ('calendar', '建除十二值日'),
    '/api/date-scan': ('calendar', '择日扫描'),
    '/api/time-audit': ('birth-time', '太阳时审计'),
    '/api/birth-window': ('birth-time', '出生时间误差'),
    '/api/birth-boundaries': ('birth-time', '生时边界地图'),
    '/api/rules-compare': ('birth-time', '规则对比'),
    '/api/rule-matrix': ('birth-time', '规则差异对照'),
    '/api/qimen': ('qimen', '时家奇门排盘'),
    '/api/qimen-reference-audit': ('qimen', '奇门参考盘核验'),
    '/api/pair': ('relations', '双人八字对照'),
    '/api/ziwei-pair': ('relations', '双人紫微对照'),
    '/api/group-relations': ('relations', '多人关系'),
    '/api/consultation': ('consult', 'AI 咨询工作流'),
    '/api/decision-matrix': ('consult', '决策矩阵'),
    '/api/chat/status': ('consult', 'AI 对话状态'),
    '/api/chat': ('consult', 'AI 对话'),
    '/api/chat/stream': ('consult', 'AI 对话（流式）'),
    '/health': ('system', '健康检查'),
    '/api/capabilities': ('system', '能力清单'),
    '/.well-known/oauth-protected-resource': ('system', 'OAuth 资源元数据'),
    '/.well-known/oauth-protected-resource/mcp': ('system', 'OAuth 资源元数据（MCP）'),
    '/mcp': ('system', 'MCP 端点（JSON-RPC）'),
}

_BIRTH = {'birth_datetime': '1995-06-08T14:30', 'timezone': 'Asia/Shanghai', 'gender': 'female'}
_BIRTH_B = {'birth_datetime': '1993-11-20T08:15', 'timezone': 'Asia/Shanghai', 'gender': 'male'}

# Bodies the schema alone cannot fill in (dates, minimum lengths, cross-field rules). The rest
# are built from each schema's required fields, defaults and "e.g." hints.
EXAMPLES: dict[str, dict[str, Any]] = {
    '/api/bazi': _BIRTH,
    '/api/consultation': {'question': '今年适合换工作吗？', 'birth': _BIRTH},
    '/api/chat': {'messages': [{'role': 'user', 'content': '我的日主是什么？'}], 'profile': {'birth': _BIRTH}},
    '/api/chat/stream': {'messages': [{'role': 'user', 'content': '我的日主是什么？'}], 'profile': {'birth': _BIRTH}},
    '/api/date-scan': {'start_date': '2026-11-01', 'days': 14},
    '/api/life-path': {'birth': _BIRTH, 'events': [{'date': '2018-09-01', 'title': '入职'}]},
    '/api/ziwei-professional': {'birth': _BIRTH},
    '/api/qimen-reference-audit': {'moment': _BIRTH, 'reference_source': 'Printed chart, page 12',
                                   'reference_school': 'chaibu', 'root_fields': {'dun': '阳遁', 'bureau': 3}},
    '/api/calendar': {'start_date': '2026-11-01', 'days': 7},
    '/api/time-audit': {'birth': {**_BIRTH, 'longitude': 104.07}},
    '/api/pillars-to-dates': {'year': '乙亥', 'month': '壬午', 'day': '甲子', 'start_year': 1990, 'end_year': 2000},
    '/api/chart-import-check': {'birth': _BIRTH, 'text': '年柱 乙亥 月柱 壬午'},
    '/api/group-relations': {'members': [{'label': 'A', 'birth': _BIRTH}, {'label': 'B', 'birth': _BIRTH_B}]},
    '/api/dayun': {'birth': _BIRTH},
    '/api/day-officers': {'start_date': '2026-11-01', 'days': 7},
    '/api/decision-matrix': {'question': '选哪份工作？', 'criteria': [{'name': '收入', 'weight': 3}, {'name': '通勤', 'weight': 2}],
                             'options': [{'name': '甲公司', 'ratings': {'收入': 4, '通勤': 2}},
                                         {'name': '乙公司', 'ratings': {'收入': 3, '通勤': 5}}]},
    '/api/pair': {'person_a': _BIRTH, 'person_b': _BIRTH_B},
    '/api/ziwei-pair': {'person_a': _BIRTH, 'person_b': _BIRTH_B},
    '/mcp': {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'},
}


def _resolve(schema: dict, components: dict) -> dict:
    while '$ref' in schema:
        schema = components[schema['$ref'].rsplit('/', 1)[-1]]
    return schema


def example_from_schema(schema: dict, components: dict, depth: int = 0) -> Any:
    """A minimal body: required fields only, using defaults, enums and "e.g." hints."""
    schema = _resolve(schema, components)
    if depth > 6:
        return None
    for key in ('example', 'default', 'const'):
        if key in schema:
            return schema[key]
    if schema.get('examples'):
        return schema['examples'][0]
    if 'anyOf' in schema:
        options = [x for x in schema['anyOf'] if x.get('type') != 'null']
        return example_from_schema(options[0], components, depth + 1) if options else None
    if 'allOf' in schema:
        return example_from_schema(schema['allOf'][0], components, depth + 1)
    if 'enum' in schema:
        return schema['enum'][0]
    kind = schema.get('type')
    if kind == 'object':
        required = schema.get('required', [])
        return {name: example_from_schema(sub, components, depth + 1)
                for name, sub in schema.get('properties', {}).items() if name in required}
    if kind == 'array':
        return [example_from_schema(schema.get('items', {}), components, depth + 1) for _ in range(schema.get('minItems', 0))]
    if kind == 'string':
        hint = re.search(r'e\.g\.\s*([^\s,;)]+)', schema.get('description', ''))
        return hint.group(1) if hint else ''
    if kind in ('integer', 'number'):
        return schema.get('minimum', 0)
    if kind == 'boolean':
        return False
    return None


def enrich_openapi(schema: dict) -> dict:
    """Add tags, titles and request examples to a generated OpenAPI document in place."""
    components = schema.get('components', {}).get('schemas', {})
    schema['tags'] = [{'name': name, 'description': text, 'x-title': title} for name, title, text in TAGS]
    # Paths in the order of ROUTES, so each group reads from the everyday endpoints to the specialist ones.
    order = {path: i for i, path in enumerate(ROUTES)}
    schema['paths'] = dict(sorted(schema.get('paths', {}).items(), key=lambda item: order.get(item[0], len(order))))
    for path, operations in schema.get('paths', {}).items():
        tag, title = ROUTES.get(path, ('other', ''))
        for method, operation in operations.items():
            operation['tags'] = [tag]
            if title:
                operation['x-title'] = title
            body = operation.get('requestBody', {}).get('content', {}).get('application/json')
            if body is not None:
                body['example'] = EXAMPLES.get(path) or example_from_schema(body.get('schema', {}), components)
            elif method == 'post' and path in EXAMPLES:
                operation['requestBody'] = {'content': {'application/json': {'example': EXAMPLES[path]}}}
    return schema
