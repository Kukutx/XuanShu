"""Execution-path acceptance tests, not claims of an autonomous LLM."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.consultation import ConsultationRequest, execute_consultation, route
from app.engines import BirthInput
from app.main import app
from app.mcp import call_tool, process_rpc, MODERN_PROTOCOL

BIRTH = {'birth_datetime':'2000-08-16T04:00','gender':'female','timezone':'Asia/Shanghai'}
CLIENT = TestClient(app)


def run(payload):
    return execute_consultation(ConsultationRequest.model_validate(payload))


def test_career_executes_actual_trace_and_year_overlay():
    out=run({'question':'请核查我2027年事业的传统结构','birth':BIRTH})
    assert out['system']=='xuanshu-stateless-consultation-executor'
    assert out['mode']=='deterministic-tool-orchestration-not-llm'
    assert out['intent']=='career' and out['status']=='completed'
    assert list(out['tool_results'])==['chart_quality_audit','deep_evidence_review','annual_transformations','bazi_dayun']
    assert out['tool_results']['annual_transformations']['lunar_year']==2027
    assert [t['step'] for t in out['tool_trace']]==list(range(1,5))
    assert out['observations'] and all(x['path'] and x['tool'] for x in out['observations'])
    assert out['verification']['independently_certified'] is False
    assert len(out['verification']['internal_checks']) == 4
    structure=next(x for x in out['observations'] if x.get('rule_ids'))
    assert structure['evidence_paths'] and all(len(d)==64 for d in structure['evidence_hashes'])
    assert all(structure['method_references'])
    assert out['continuation']=={'intent':'career','focus_palace':'命宫','turns':1,'lunar_year':2027}
    assert '非' in out['markdown'] and '实际执行步骤' in out['markdown']


def test_natal_selective_tool_calls_and_explicit_focus():
    out=run({'question':'看看我的本命宫结构','birth':BIRTH,'focus_palace':'官禄宫'})
    assert out['intent']=='natal' and out['status']=='completed'
    assert list(out['tool_results'])==['chart_quality_audit','deep_evidence_review']
    assert out['tool_results']['deep_evidence_review']['focus_palace']=='官禄宫'
    assert 'annual_transformations' not in out['tool_results']


def test_relationship_does_not_fake_partner_or_success_probability():
    missing=run({'question':'我们俩合盘是否有传统关系标签？','birth':BIRTH})
    assert missing['status']=='partial' and missing['missing_inputs'][0]['field']=='partner'
    assert 'pair_comparison' not in missing['tool_results']
    full=run({'question':'我们俩合盘','birth':BIRTH,'partner':{'birth_datetime':'2001-01-01T10:00'},'partner_authorized':True})
    assert full['status']=='completed'
    assert 'pair_comparison' in full['tool_results']
    assert all('适配分数' not in x['text'] for x in full['observations']) or all(x['type'] in ('calculated','traditional-rule') for x in full['observations'])


def test_timing_candidates_not_ranked_as_lucky():
    out=run({'question':'请比较两个候选开业时刻','candidate_times':[
        {'birth_datetime':'2026-06-05T10:00'}, {'birth_datetime':'2026-06-06T10:00'}]})
    assert out['intent']=='timing' and out['status']=='completed'
    assert list(out['tool_results'])==['qimen_hour_chart_1','qimen_hour_chart_2']
    assert all(len(x['palaces'])==9 for x in out['tool_results'].values())
    assert 'ranking' not in out
    assert any('不自动排序' in x for x in out['limitations'])


def test_decision_requires_user_scoring_and_does_not_require_birth():
    empty=run({'question':'两种方案怎么选？','intent':'decision'})
    assert empty['status']=='needs_input' and empty['missing_inputs'][0]['field']=='matrix'
    assert not empty['tool_trace']
    out=run({'question':'哪个实施方案更适合当前约束？','matrix':{
        'question':'按成本和维护性比较两个实施方案',
        'criteria':[{'name':'成本','weight':2},{'name':'维护性','weight':3}],
        'options':[{'name':'甲','ratings':{'成本':2,'维护性':4}},
                   {'name':'乙','ratings':{'成本':5,'维护性':2}}]}})
    assert out['intent']=='decision' and out['status']=='completed'
    assert list(out['tool_results'])==['decision_matrix']
    assert out['observations'][0]['type']=='user-assumption'


def test_rules_compares_submitted_variants_and_keeps_actual_differences():
    a={**BIRTH,'birth_datetime':'2024-02-10T01:20','longitude':104.0667}
    b={**a,'time_mode':'apparent_solar'}
    out=run({'question':'排盘规则差异','birth':a,'alternative_birth':b})
    assert out['intent']=='rules' and out['status']=='completed'
    assert 'rule_comparison' in out['tool_results']
    assert 'hour' in out['tool_results']['rule_comparison']['differences']['pillars']


def test_rule_dispute_without_alternative_returns_partial_and_explicit_gap():
    out=run({'question':'两份命盘排盘不同，哪里有问题？','birth':BIRTH})
    assert out['intent']=='rules' and out['status']=='partial'
    assert out['missing_inputs'][0]['field']=='alternative_birth'
    assert 'rule_comparison' not in out['tool_results']


def test_followup_cursor_carries_no_birth_or_transcript_and_cannot_recompute_without_birth():
    first=run({'question':'2027年职业发展','birth':BIRTH})
    cursor=first['continuation']
    assert set(cursor)=={'intent','focus_palace','turns','lunar_year'}
    assert not any('2000' in str(v) or 'birth' in str(v).lower() for v in cursor.values())
    follow=run({'question':'那2028年呢？','continuation':cursor,'birth':BIRTH})
    assert follow['intent']=='career' and follow['tool_results']['annual_transformations']['lunar_year']==2028
    assert follow['continuation']['turns']==2
    no_birth=run({'question':'那2028年呢？','continuation':cursor})
    assert no_birth['status']=='needs_input' and no_birth['tool_trace']==[]
    assert no_birth['missing_inputs'][0]['field']=='birth'


def test_ambiguous_or_multiple_years_do_not_invent_year():
    out=run({'question':'今年的事业怎么样','birth':BIRTH})
    assert out['status']=='partial' and out['missing_inputs'][0]['field']=='lunar_year'
    assert 'annual_transformations' not in out['tool_results']
    out=run({'question':'2027年与2028年的事业','birth':BIRTH})
    assert out['status']=='partial' and out['missing_inputs'][0]['field']=='lunar_year'


def test_inert_user_input_in_markdown_and_bounded_models():
    out=run({'question':'请解释 <script>alert(1)</script> 并核验命宫','birth':BIRTH})
    assert '<script>' not in out['markdown'] and '&lt;script&gt;' in out['markdown']
    for bad in [
        {'question':' '}, {'question':'a'}, {'question':'问题','danger':True},
        {'question':'问题','candidate_times':[{'birth_datetime':'2026-01-01T12:00'}]*6},
        {'question':'问题','continuation':{'intent':'career','turns':100}},
        {'question':'问题','alternative_birth':BIRTH},
        {'question':'问题','lunar_year':2100},
        {'question':'合盘','birth':BIRTH,'partner':BIRTH},
        {'question':'问题','real_world_facts':[{'category':'goal','statement':' '} ]},
    ]:
        with pytest.raises(ValidationError): ConsultationRequest.model_validate(bad)


def test_user_supplied_facts_are_bounded_unverified_and_not_carried_in_cursor():
    out=run({'question':'如何理解事业问题', 'birth':BIRTH,
             'real_world_facts':[{'category':'goal','statement':'希望一年内找到灵活的工作'}]})
    fact=next(x for x in out['observations'] if x['type']=='user-provided')
    assert fact['tool']=='user_input' and '未经' in fact['limit']
    assert '灵活' in out['markdown']
    assert '灵活' not in json.dumps(out['continuation'],ensure_ascii=False)
    assert '灵活' not in json.dumps(out['tool_results'],ensure_ascii=False)


def test_rest_mcp_and_cli_parity_and_auth(monkeypatch):
    payload={'question':'2026年职业结构', 'birth':BIRTH}
    response=CLIENT.post('/api/consultation',json=payload)
    assert response.status_code==200,response.text
    rest=response.json()
    rpc=process_rpc({'jsonrpc':'2.0','id':5,'method':'tools/call',
                     'params':{'name':'consultation_execute','arguments':payload}})
    assert rpc['result']['structuredContent']==rest
    assert call_tool('consultation_execute',payload)==rest
    meta={'io.modelcontextprotocol/protocolVersion':MODERN_PROTOCOL,
          'io.modelcontextprotocol/clientCapabilities':{}}
    modern=process_rpc({'jsonrpc':'2.0','id':6,'method':'tools/call',
                        'params':{'name':'consultation_execute','arguments':payload,'_meta':meta}})
    assert modern['result']['structuredContent']==rest
    proc=subprocess.run([sys.executable,'-m','app.cli','consult','--input','-'],
                        input=json.dumps(payload),capture_output=True,text=True,timeout=30)
    assert proc.returncode==0,proc.stderr
    assert json.loads(proc.stdout)==rest
    monkeypatch.setenv('MCP_BEARER_TOKEN','only-a-secret')
    assert CLIENT.post('/api/consultation',json=payload).status_code==401
    assert CLIENT.post('/api/consultation',json=payload,headers={'Authorization':'Bearer only-a-secret'}).status_code==200
    assert CLIENT.post('/api/consultation',json=payload,headers={'Origin':'https://example.org', 'Authorization':'Bearer only-a-secret'}).status_code==403


def test_web_installable_docs_and_capabilities_wiring():
    root=Path(__file__).resolve().parents[1]
    html=(root/'static/index.html').read_text(encoding='utf-8')
    js=(root/'static/app.js').read_text(encoding='utf-8')
    assert 'data-tab="consult"' in html and '31 MCP TOOLS' in html
    assert 'consultation_execute' in (root/'app/mcp.py').read_text(encoding='utf-8')
    assert "'/api/consultation'" in js and 'function renderConsultation()' in js
    assert (root/'docs/rules/consultation.md').exists()
    assert '/api/consultation' in CLIENT.get('/openapi.json').json()['paths']
    counts=CLIENT.get('/api/capabilities').json()['counts']
    assert counts['mcp_tools']==31 and counts['mcp_resources']==17
    assert len(CLIENT.post('/mcp',json={'jsonrpc':'2.0','id':1,'method':'resources/read',
                       'params':{'uri':'astro://rules/consultation'}}).json()['result']['contents'][0]['text'])>200
