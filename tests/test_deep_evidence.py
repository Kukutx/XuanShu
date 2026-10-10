"""Regressions for evidence-based analysis and the four public entry points."""
import json
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.evidence import DeepReviewRequest, RULE_SOURCES, deep_evidence_review
from app.engines import BirthInput, PALACE_NAMES
from app.main import app
from app.mcp import process_rpc
from app.report import ReportRequest, structured_report

BASE = {'birth_datetime':'2000-08-16T04:00', 'timezone':'Asia/Shanghai','gender':'female'}
CLIENT = TestClient(app)


def review(day='2000-08-16T04:00', **kwargs):
    return deep_evidence_review(DeepReviewRequest(birth=BirthInput(**{**BASE, 'birth_datetime':day}), **kwargs))


def test_rules_are_unique_with_trust_scopes_and_references():
    assert len(RULE_SOURCES) == 10
    assert all(x['reference'].startswith(('https://','docs/')) and x['scope'] and x['implementation'] for x in RULE_SOURCES.values())
    assert any('not_independent' in k for k in RULE_SOURCES)


@pytest.mark.parametrize('when',[
    '2000-08-16T04:00','2024-02-07T12:00','2024-02-10T01:20',
    '2026-06-21T23:55','2033-12-22T10:30','2057-09-28T12:00',
])
def test_deep_review_internal_invariants_across_dates(when):
    result=review(when)
    assert result['system']=='xuanshu-deep-evidence-review'
    assert len(result['findings'])==9
    assert len(result['references'])==9
    assert len(set(f['id'] for f in result['findings']))==9
    assert len(result['checks'])==4 and all(c['passed'] for c in result['checks'])
    assert len(result['overview']['pillars'].split(' / '))==4
    assert result['independent_professional_verification'] is False
    for finding in result['findings']:
        assert finding['evidence'] and finding['rule_ids'] and finding['limit']
        for field in finding['evidence']:
            assert field['path'] and 'value' in field
        assert all(key in RULE_SOURCES for key in finding['rule_ids'])
    assert '不算外部独立验证' in result['markdown'] or '不能算独立复验' in result['markdown'] or '不算外部验证' in result['markdown']
    assert len(result['markdown']) > 1500


def test_lunar_new_year_and_lichun_cutoffs_are_not_collapsed():
    result=review('2024-02-07T12:00')
    assert result['calendar_year_consistent'] is False
    assert '甲辰' in next(f for f in result['findings'] if f['title']=='两套年柱口径差异核对')['observation']
    assert '癸卯' in next(f for f in result['findings'] if f['title']=='两套年柱口径差异核对')['observation']
    assert review('2024-02-20T12:00')['calendar_year_consistent'] is True


@pytest.mark.parametrize('palace',list(PALACE_NAMES))
def test_each_palace_has_valid_trine_and_flying(palace):
    result=review(focus_palace=palace, include_quality=False)
    assert len(result['findings'])==8
    assert len(result['references'])==8
    trine=next(f for f in result['findings'] if f['id']=='ziwei-surround')
    assert trine['title']==f'{palace}的三方四正'
    assert len(trine['evidence'][0]['value']['trine'])==2
    flying=next(f for f in result['findings'] if f['id']=='ziwei-four')['evidence'][1]['value']
    assert len(flying)==4
    assert len({t['type'] for t in flying})==4


@pytest.mark.parametrize('year',[1901,2000,2026,2099])
def test_optional_year_is_explicitly_an_overlay(year):
    r=review(lunar_year=year, include_quality=False)
    assert len(r['findings'])==9
    assert r['annual_overlay']['year_pillar']
    assert len(r['annual_overlay']['transformations'])==4
    assert '流年全盘' in next(f for f in r['findings'] if f['id']=='ziwei-annual')['limit']


def test_optional_question_not_executed_and_not_overwritten():
    r=review(question='比较这个宫位和四柱的传统结构',include_quality=False)
    assert r['question']=='比较这个宫位和四柱的传统结构'
    assert r['markdown'].count('研究问题')==1


@pytest.mark.parametrize('payload',[
    {'focus_palace':'不存在的宫位'}, {'lunar_year':2100}, {'lunar_year':1800},
    {'question':'a'*201}, {'unexpected':'x'},
])
def test_invalid_inputs_fail_closed(payload):
    with pytest.raises(ValidationError):
        DeepReviewRequest(birth=BirthInput(**BASE),**payload)


def test_no_ml_or_online_fetch_and_scopes_say_method_reference():
    r=review()
    assert all(x['scope'] for x in r['references'])
    assert any(x['reference'].startswith('https://docs.iztro.com') for x in r['references'])
    assert '未经' not in r['system']
    assert '不用于医疗' in ' '.join(r['limitations'])


def test_rest_and_old_mcp_and_modern_mcp_results_identical():
    args={'birth':BASE,'focus_palace':'官禄宫','lunar_year':2026}
    rest=CLIENT.post('/api/deep-review',json=args)
    assert rest.status_code==200,rest.text
    old=process_rpc({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'deep_evidence_review','arguments':args}})
    assert old['result']['structuredContent']==rest.json()
    meta={ 'io.modelcontextprotocol/protocolVersion':'2026-07-28',
           'io.modelcontextprotocol/clientCapabilities':{}}
    modern=process_rpc({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{
        '_meta':meta,'name':'deep_evidence_review','arguments':args}})
    assert modern['result']['structuredContent']==rest.json()
    assert modern['result']['resultType']=='complete'


def test_rules_resource_and_prompt_resolve_through_mcp():
    x=process_rpc({'jsonrpc':'2.0','id':3,'method':'resources/read','params':{'uri':'astro://rules/evidence'}})
    assert '外部参考及证据等级' in x['result']['contents'][0]['text']
    p=process_rpc({'jsonrpc':'2.0','id':4,'method':'prompts/get','params':{'name':'deep-evidence-review','arguments':{'focus':'官禄宫'}}})
    assert 'deep_evidence_review' in p['result']['messages'][0]['content']['text']


def test_report_can_opt_in_deep_review_without_changing_old_default():
    basic=structured_report(ReportRequest(birth=BirthInput(**BASE)))
    assert basic['deep_evidence'] is None and all(x['id']!='deep_evidence' for x in basic['sections'])
    full=structured_report(ReportRequest(birth=BirthInput(**BASE),include_deep_evidence=True))
    assert len(full['deep_evidence']['findings'])==8
    assert full['sections'][-1]['id']=='deep_evidence'
    assert '方法参考文档' in full['markdown']
    assert any(x['tool']=='deep_evidence_review' for x in full['tool_trace'])


def test_cli_deep_review_json_and_invalid_palace():
    p=subprocess.run([sys.executable,'-m','app.cli','deep-review','--date',BASE['birth_datetime'],
        '--palace','官禄宫','--year','2026'],capture_output=True,text=True,timeout=15)
    assert p.returncode==0,p.stderr
    assert json.loads(p.stdout)['focus_palace']=='官禄宫'
    invalid=subprocess.run([sys.executable,'-m','app.cli','deep-review','--date',BASE['birth_datetime'],
        '--palace','不存在'],capture_output=True,text=True,timeout=15)
    assert invalid.returncode!=0


def test_web_declares_new_workbench_and_safe_response_rendering():
    from app.asset_paths import resource_root
    root=resource_root()
    html=(root/'static/index.html').read_text(encoding='utf-8')
    js=(root/'static/app.js').read_text(encoding='utf-8')
    assert html.count('data-tab=') == 23
    assert 'data-tab="deep"' in html
    assert "'/api/deep-review'" in js
    assert "append(panel,'p','feature-note',f.observation)" in js
    assert "append(panel,'p','feature-note',f.observation)" in js and 'innerHTML' not in js
    assert 'report-deep' in js


def test_all_evidence_hashes_recompute_and_match_public_chart_hashes():
    from app.evidence import _digest
    from app.engines import calculate_bazi, calculate_ziwei
    birth=BirthInput(**BASE)
    result=deep_evidence_review(DeepReviewRequest(birth=birth,lunar_year=2026))
    assert result['calculation_hashes']['bazi_chart']==_digest(calculate_bazi(birth))
    assert result['calculation_hashes']['ziwei_chart']==_digest(calculate_ziwei(birth))
    for finding in result['findings']:
        for x in finding['evidence']:
            assert len(x['sha256'])==64 and x['sha256']==_digest(x['value'])


def test_sanitized_user_question_stays_inert_in_markdown():
    s='<script>alert(1)</script>\n# dangerous [link](javascript:alert(1))'
    result=review(question=s,include_quality=False)
    assert result['question']==s
    assert '<script>' not in result['markdown']
    assert '\n# dangerous' not in result['markdown']
    assert '&lt;script&gt;' in result['markdown']


def test_calculation_hash_stable_for_repeated_identical_births():
    a=review('2024-02-07T12:00',include_quality=False)
    b=review('2024-02-07T12:00',include_quality=False)
    assert a['calculation_hashes']==b['calculation_hashes']
    assert a['markdown']==b['markdown']


def test_published_reference_fixture_is_reproducible_and_explicitly_not_independent():
    from app.asset_paths import resource_root
    from pathlib import Path
    root=resource_root()
    fixture=json.loads((root/'examples/deep-evidence-reference-2024-02-07.json').read_text(encoding='utf-8'))
    assert fixture['input_parameters']['birth']['gender']=='unspecified'
    result=deep_evidence_review(DeepReviewRequest.model_validate(fixture['input_parameters']))
    assert fixture['input_parameters']==result['input_parameters']
    assert fixture['calculation_hashes']==result['calculation_hashes']
    assert fixture['overview']==result['overview']
    assert fixture['calendar_year_consistent'] is False
    assert fixture['independent_professional_verification'] is False
    assert all(x['rule_ids'] for x in fixture['findings'])


def test_birth_gender_option_is_part_of_reference_identity():
    female=review('2024-02-07T12:00', focus_palace='官禄宫', lunar_year=2026)
    unspecified=deep_evidence_review(DeepReviewRequest(
        birth=BirthInput(birth_datetime='2024-02-07T12:00',timezone='Asia/Shanghai',gender='unspecified'),
        focus_palace='官禄宫',lunar_year=2026))
    assert female['input_parameters']['birth']['gender']=='female'
    assert unspecified['input_parameters']['birth']['gender']=='unspecified'
    assert female['calculation_hashes']['bazi_chart']==unspecified['calculation_hashes']['bazi_chart']
    assert female['calculation_hashes']['ziwei_chart']!=unspecified['calculation_hashes']['ziwei_chart']
