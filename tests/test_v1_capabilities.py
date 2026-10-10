"""开发阶段 deterministic features, API shape, and honest feature boundaries."""
import json
import subprocess
import sys
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.astronomy import chinese_lunar_date, get_solar_terms
from app.engines import BirthInput, calculate_bazi, calculate_ziwei
from app.exports import solar_terms_ics
from app.features import (AnnualRequest, TimeAuditRequest, RuleComparisonRequest,
                          annual_transformations, time_audit, rule_comparison)
from app.main import app
from app.mcp import process_rpc, TOOL_DEFS, RESOURCES, PROMPTS
from app.timebasis import time_basis
from app.engines import normalized_dt

client=TestClient(app)
BASE={'birth_datetime':'2000-08-16T04:00','timezone':'Asia/Shanghai','gender':'female'}


@pytest.mark.parametrize('longitude',[-181,181,361])
def test_invalid_longitudes(longitude):
    with pytest.raises(ValidationError):
        BirthInput(**BASE,longitude=longitude)


@pytest.mark.parametrize('latitude',[-91,91])
def test_invalid_latitude(latitude):
    with pytest.raises(ValidationError):
        BirthInput(**BASE,latitude=latitude)


def test_solar_modes_require_geographic_longitude():
    for mode in ('mean_solar','apparent_solar'):
        with pytest.raises(ValidationError,match='longitude'):
            BirthInput(**BASE,time_mode=mode)


def test_true_solar_time_formula_and_utc_invariance():
    dt=normalized_dt(BirthInput(**BASE))
    clock,m0=time_basis(dt,'clock')
    mean,m1=time_basis(dt,'mean_solar',120)
    apparent,m2=time_basis(dt,'apparent_solar',120)
    assert clock==mean  # 120E is UTC+8 reference meridian
    assert m1['effective_shift_minutes']==pytest.approx(0,abs=1e-9)
    assert -20<m2['equation_of_time_minutes']<20
    assert abs((apparent-mean).total_seconds()/60-m2['equation_of_time_minutes'])<1e-4
    assert m2['method']=='UT + longitude×4min + EOT'


def test_chengdu_solar_time_changes_hour_not_astronomical_year():
    base=BirthInput(birth_datetime='2024-02-10T01:20',timezone='Asia/Shanghai',longitude=104.0667)
    clock=calculate_bazi(base)
    solar=calculate_bazi(base.model_copy(update={'time_mode':'apparent_solar'}))
    assert clock['pillars']['year']==solar['pillars']['year']
    assert clock['pillars']['month']==solar['pillars']['month']
    assert clock['pillars']['hour']['branch']!=solar['pillars']['hour']['branch']
    assert solar['time_basis']['effective_shift_minutes'] < -60
    assert solar['time_basis']['longitude_east_degrees']==104.0667


def test_clock_mode_is_backwards_compatible_without_longitude():
    a=calculate_bazi(BirthInput(**BASE))
    b=calculate_bazi(BirthInput(**BASE,longitude=104.0667))
    assert a['pillars']==b['pillars']
    assert b['time_basis']['effective_shift_minutes']==0


def test_dst_fold_requires_explicit_offset():
    with pytest.raises(ValueError,match='Ambiguous'):
        calculate_bazi(BirthInput(birth_datetime='2024-10-27T02:30',timezone='Europe/Rome'))
    result=calculate_bazi(BirthInput(birth_datetime='2024-10-27T02:30+02:00',timezone='Europe/Rome'))
    assert result['timezone']=='Europe/Rome'


def test_dst_spring_gap_still_rejected():
    with pytest.raises(ValueError,match='nonexistent'):
        calculate_bazi(BirthInput(birth_datetime='2024-03-31T02:30',timezone='Europe/Rome'))


def test_bazi_structure_extends_without_removing_existing_data():
    b=calculate_bazi(BirthInput(**BASE))
    assert len(b['pillars'])==4
    assert len(b['branch_relations'])==6
    assert sum(b['surface_five_elements'].values())==8
    assert sum(b['hidden_stem_elements_unweighted'].values())==sum(len(x['hidden_stems']) for x in b['pillars'].values())
    assert sum(b['ten_god_occurrences_unweighted'].values())==3+sum(len(x['hidden_stems']) for x in b['pillars'].values())
    assert '六冲' in next(x for x in b['branch_relations'] if x['a']=='month' and x['b']=='hour')['labels']


def test_ziwei_stars_unique_and_trine_opposite_symmetric():
    z=calculate_ziwei(BirthInput(**BASE))
    assert z['star_counts']=={'main':14,'auxiliary':44,'original_selected':18,'additional_named':26}
    stars=[name for palace in z['palaces'] for name in palace['main_stars']+palace['auxiliary_stars']]
    assert len(stars)==len(set(stars))==58
    for palace in z['palaces']:
        net=palace['three_harmonies_and_opposite']
        assert len(net['trine'])==2
        assert len({palace['branch'],net['trine'][0]['branch'],net['trine'][1]['branch'],net['opposite']['branch']})==4
        opposite=next(p for p in z['palaces'] if p['branch']==net['opposite']['branch'])
        assert opposite['three_harmonies_and_opposite']['opposite']['branch']==palace['branch']


@pytest.mark.parametrize('year', [1901,1949,2000,2024,2033,2044,2099])
def test_annual_overlay_preserves_four_transformations(year):
    z=calculate_ziwei(BirthInput(**BASE))
    annual=annual_transformations(AnnualRequest(birth=BirthInput(**BASE),lunar_year=year))
    assert len(annual['transformations'])==4
    assert annual['natal_ming_palace']==z['ming_palace']
    assert {item['type'] for item in annual['transformations']}=={'化禄','化权','化科','化忌'}
    for item in annual['transformations']:
        assert z['star_positions'][item['star']]==item['natal_branch']
        assert item['natal_palace'] in {x['name'] for x in z['palaces']}


def test_time_audit_has_three_comparable_results():
    inp=BirthInput(**BASE,longitude=104.0667)
    a=time_audit(TimeAuditRequest(birth=inp))
    assert [x['mode'] for x in a['choices']]==['clock','mean_solar','apparent_solar']
    assert a['choices'][0]['pillars']['day']=='丙午'
    assert a['choices'][0]['shift_minutes']==0
    assert a['choices'][1]['shift_minutes']==pytest.approx((104.0667-120)*4,abs=1)
    assert a['choices'][2]['equation_of_time_minutes']!=0


def test_time_audit_requires_longitude_even_clock():
    with pytest.raises(ValueError,match='longitude'):
        time_audit(TimeAuditRequest(birth=BirthInput(**BASE)))


def test_rule_sensitivity_delta_between_modes():
    basic=BirthInput(birth_datetime='2024-02-10T01:20',longitude=104.0667)
    adjusted=basic.model_copy(update={'time_mode':'apparent_solar'})
    comp=rule_comparison(RuleComparisonRequest(original=basic,alternative=adjusted))
    assert 'hour' in comp['differences']['pillars']
    assert 'year' not in comp['differences']['pillars']
    assert comp['a']['time_basis']['mode']=='clock'
    assert comp['b']['time_basis']['mode']=='apparent_solar'


def test_export_ics_contains_24_unambiguous_utc_events():
    output=solar_terms_ics(2024)
    assert output.startswith('BEGIN:VCALENDAR\r\n')
    assert output.count('BEGIN:VEVENT')==24
    assert output.count('DTSTART:')==24
    assert output.count('END:VEVENT')==24
    assert 'SUMMARY:立春' in output
    assert output.endswith('END:VCALENDAR\r\n')


def test_public_calendar_and_ics_routes():
    assert client.get('/api/lunar/2024-02-10').json()['lunar']['day']==1
    assert client.get('/api/lunar/2099-12-31').status_code==200
    assert client.get('/api/lunar/2100-01-01').status_code==422
    assert client.get('/api/lunar/not-a-date').status_code==422
    ics=client.get('/api/solar-terms/2024.ics')
    assert ics.status_code==200
    assert 'text/calendar' in ics.headers['content-type']
    assert ics.text.count('BEGIN:VEVENT')==24
    assert client.get('/api/solar-terms/2100.ics').status_code==422


@pytest.mark.parametrize('endpoint,body,expected',[
    ('/api/annual',{'birth':BASE,'lunar_year':2026},'transformations'),
    ('/api/time-audit',{'birth':{**BASE,'longitude':104.0667}},'choices'),
    ('/api/rules-compare',{'original':BASE,'alternative':BASE},'differences'),
])
def test_new_rest_endpoints(endpoint,body,expected):
    response=client.post(endpoint,json=body)
    assert response.status_code==200,response.text
    assert expected in response.json()
    assert response.headers['cache-control']=='no-store'


def test_security_headers_and_public_mode_fail_closed(monkeypatch):
    res=client.get('/')
    assert res.headers['x-content-type-options']=='nosniff'
    assert res.headers['x-frame-options']=='DENY'
    assert 'frame-ancestors' in res.headers['content-security-policy']
    monkeypatch.setenv('DEPLOYMENT_MODE','public')
    monkeypatch.delenv('MCP_BEARER_TOKEN',raising=False)
    assert client.get('/health').status_code==503
    assert client.post('/mcp',json={'jsonrpc':'2.0','id':1,'method':'ping'}).status_code==503
    monkeypatch.setenv('MCP_BEARER_TOKEN','example-safe-test-token-12345678901234567890')
    monkeypatch.setenv('ASTRO_ALLOWED_HOSTS','testserver')
    assert client.get('/health').status_code==200
    assert client.post('/api/bazi',json=BASE).status_code==401


def test_oversized_request_rejected():
    payload=b'{' + b' ' * (70*1024) + b'}'
    res=client.post('/api/bazi',content=payload,headers={'Content-Type':'application/json'})
    assert res.status_code==413


def test_mcp_all_tools_and_resources_and_prompts_resolve():
    assert len(TOOL_DEFS)==27
    assert len(RESOURCES)==17
    assert len(PROMPTS)==15
    for resource in RESOURCES:
        response=process_rpc({'jsonrpc':'2.0','id':1,'method':'resources/read','params':{'uri':resource['uri']}})
        assert response['result']['contents'][0]['text']
    for prompt in PROMPTS:
        response=process_rpc({'jsonrpc':'2.0','id':1,'method':'prompts/get','params':{'name':prompt['name']}})
        assert response['result']['messages'][0]['content']['text']
    for name,args in [
        ('annual_transformations',{'birth':BASE,'lunar_year':2026}),
        ('time_basis_audit',{'birth':{**BASE,'longitude':104.0667}}),
        ('rule_comparison',{'original':BASE,'alternative':BASE}),
    ]:
        response=process_rpc({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':name,'arguments':args}})
        assert not response['result']['isError'],response
        assert response['result']['structuredContent']['system']


def test_cli_bazi_success_and_error():
    ok=subprocess.run([sys.executable,'-m','app.cli','bazi','--date','2000-08-16T04:00'],text=True,capture_output=True,timeout=10)
    assert ok.returncode==0
    assert json.loads(ok.stdout)['pillars']['day']['text']=='丙午'
    bad=subprocess.run([sys.executable,'-m','app.cli','bazi','--date','2000-08-16T04:00','--time-mode','apparent_solar'],text=True,capture_output=True,timeout=10)
    assert bad.returncode==2
    assert 'longitude' in bad.stderr


@pytest.mark.parametrize('year',[1902,1912,1950,1980,2000,2020,2033,2050,2070,2090,2099])
def test_lunar_month_rollover_never_skips_day(year):
    # Covers winter solstice, leap years and year boundaries.
    for month,day in ((1,5),(2,10),(5,10),(7,23),(12,10)):
        d=date(year,month,day)
        a=chinese_lunar_date(d)
        b=chinese_lunar_date(d+timedelta(days=1))
        if a['month']==b['month'] and a['is_leap_month']==b['is_leap_month'] and a['year']==b['year']:
            assert b['day']==a['day']+1
        else:
            assert b['day']==1


def test_plugin_metadata_and_web_vault_have_no_external_analytics():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    html=(root/'static/index.html').read_text(encoding='utf-8')
    vault=(root/'static/vault.js').read_text(encoding='utf-8')
    assert html.count('data-tab=') == 24
    assert '/static/vault.js' in html
    assert 'PBKDF2' in vault and 'AES-GCM' in vault and 'subtle.decrypt' in vault
    assert 'fetch(' not in vault
    assert 'googletagmanager' not in html.lower()
