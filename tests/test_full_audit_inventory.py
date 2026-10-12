"""Fail closed when the comprehensive REST/MCP acceptance inventory drifts."""
from app.mcp import TOOL_DEFS
from scripts.full_functional_audit import CASES


def test_all_advertised_mcp_tools_are_in_acceptance_audit():
    assert set(CASES) == {tool['name'] for tool in TOOL_DEFS}
    assert len(CASES) == 34
