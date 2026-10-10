"""The one fixed-version consultation skill must route real questions to existing tools.

These tests validate a user-facing *workflow contract*, not a live LLM Agent.
"""
from pathlib import Path

from app.mcp import TOOLS, process_rpc

ROOT = Path(__file__).resolve().parents[1]


SCENARIOS = {
    '本命分析': ('chart_quality_audit', 'deep_evidence_review', 'palace_detail'),
    '事业、年度规划': ('bazi_chart', 'bazi_dayun', 'annual_transformations'),
    '婚恋、关系、合作': ('pair_comparison', 'palace_detail'),
    '多时间窗口、择时': ('qimen_hour_chart', 'day_officers', 'solar_terms'),
    '人生经历 / 多选择方案': ('decision_matrix', 'annual_timeline'),
    '盘不同 / 流派争议': ('rule_comparison', 'time_basis_audit', 'birth_boundary_map'),
}


def test_all_six_business_scenarios_map_to_real_mcp_tools():
    text = (ROOT / 'skills/structured-dossier/SKILL.md').read_text(encoding='utf-8')
    for scenario, tools in SCENARIOS.items():
        assert scenario in text
        for name in tools:
            assert f'`{name}`' in text, (scenario, name)
            assert name in TOOLS, (scenario, name)
    assert 'no server' in text.lower() or 'server-side persistent memory' in text.lower()
    assert 'provenance' in text
    assert 'structured_report' in text


def test_prepare_report_prompt_is_problem_oriented_not_fake_agent():
    rpc = process_rpc({'jsonrpc':'2.0', 'id':1, 'method':'prompts/get',
                       'params':{'name':'prepare-report', 'arguments':{'focus':'考虑转职'}}})
    assert 'error' not in rpc
    message = rpc['result']['messages'][0]['content']['text']
    for expected in ('问题驱动', 'deep_evidence_review', 'structured_report',
                     'provenance', '长期记忆', '不输出科学预测'):
        assert expected in message


def test_business_audit_is_grounded_in_code_and_explicitly_scoped():
    audit = (ROOT / 'docs/research/PRODUCT_BUSINESS_AUDIT.md').read_text(encoding='utf-8')
    workflow = (ROOT / 'docs/research/CONSULTATION_WORKFLOW_SPEC.md').read_text(encoding='utf-8')
    for required in ('app/evidence.py', 'app/analysis.py', 'app/report.py', '公开', 'P0', '隐私'):
        assert required in audit
    for stage in ('Clarify', 'Compute', 'Verify', 'Interpret', 'Follow-up'):
        assert stage in workflow
    assert '6/6' in workflow
    assert 'v.0.1.0' in audit and 'v.0.1.0' in workflow
