"""Professional adapter and evidence-aware audit integration, no external network required."""
import sys
import types

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.engines import BirthInput
from app.professional_ziwei import (ProfessionalZiweiRequest, professional_ziwei_chart,
                                     professional_provider_available)
from app.chart_audit import QimenAuditRequest, qimen_reference_audit
from app.main import app
from app.mcp import call_tool, process_rpc
from app.qimen import qimen_chart, QimenRequest

BIRTH = {'birth_datetime':'2000-08-16T04:00','gender':'female'}


def test_missing_professional_package_fails_explicitly():
    # Real isolated environment deliberately has no optional iztro-py installed.
    if professional_provider_available():
        pytest.skip('Professional dependency installed; tested via provider fixture below')
    req = ProfessionalZiweiRequest(birth=BirthInput(**BIRTH))
    with pytest.raises(ValueError, match='Optional local provider unavailable'):
        professional_ziwei_chart(req)
    with TestClient(app) as client:
        r=client.post('/api/ziwei-professional',json={'birth':BIRTH})
    assert r.status_code == 422 and 'install' in r.text
    # The advice names the provider package; the project itself is not on PyPI.
    assert 'iztro-py>=0.1,<1' in r.text and 'xuanshu[professional]' not in r.text


def test_vendor_adaptor_maps_time_and_preserves_dynamic_output(monkeypatch):
    calls=[]
    class FakeChart:
        def model_dump(self, **kw):
            return {'palaces': [{'name':'命宫','major_stars':[{'name':'紫微'}]}], 'mutagen':['化禄']}
        def horoscope(self, date_str, hour):
            calls.append(('horoscope',date_str,hour))
            return {'yearly': {'name':'甲辰'}, 'daily': {'name':'戊午'}}
    class FakeAstro:
        def by_solar(self,*args):
            calls.append(('by_solar',)+args)
            return FakeChart()
    monkeypatch.setitem(sys.modules,'iztro_py',types.SimpleNamespace(astro=FakeAstro()))
    req=ProfessionalZiweiRequest(birth=BirthInput(**BIRTH),target_date='2024-02-10',target_hour=23)
    result=professional_ziwei_chart(req)
    assert calls[0][1:4] == ('2000-8-16', 2, '女')
    # 23:00 without the 23:00 day change stays on the same day: iztro's early Zi (0), not late Zi (12).
    assert calls[1] == ('horoscope','2024-2-10',0)
    assert result['late_zi_rule'] == 'same_day' and result['target_time_index'] == 0
    assert result['natal']['palaces'][0]['name']=='命宫'
    assert result['horoscope']['yearly']['name']=='甲辰'
    assert result['target_date']=='2024-02-10' and result['target_hour']==23
    assert result['provider']=='iztro-py'
    with TestClient(app) as client:
        body={'birth':BIRTH,'target_date':'2024-02-10','target_hour':23}
        rest=client.post('/api/ziwei-professional',json=body)
        assert rest.status_code == 200
        assert rest.json() == call_tool('ziwei_professional_chart',body)
        params={'name':'ziwei_professional_chart','arguments':body}
        assert process_rpc({'jsonrpc':'2.0','id':1,'method':'tools/call','params':params})['result']['structuredContent']==rest.json()


def test_late_zi_follows_the_birth_day_change_setting(monkeypatch):
    calls=[]
    class FakeChart:
        def model_dump(self, **kw):
            return {'palaces': []}
        def horoscope(self, date_str, hour):
            calls.append(hour)
            return {}
    class FakeAstro:
        def by_solar(self,*args):
            calls.append(args[1])
            return FakeChart()
    monkeypatch.setitem(sys.modules,'iztro_py',types.SimpleNamespace(astro=FakeAstro()))
    for rollover, index in ((False, 0), (True, 12)):
        calls.clear()
        birth=BirthInput(birth_datetime='2000-08-16T23:30',gender='female',late_zi_day_rollover=rollover)
        out=professional_ziwei_chart(ProfessionalZiweiRequest(birth=birth,target_date='2024-02-10',target_hour=23))
        assert calls == [index, index] and out['time_index'] == index
        assert out['late_zi_rule'] == ('next_day' if rollover else 'same_day')


def test_provider_keys_become_chinese_with_the_providers_own_locale(monkeypatch):
    # iztro-py 0.5 dumps names as internal keys; the adapter translates them with the provider's i18n.t (here a
    # stand-in holding only the keys this test uses) and leaves values it has no translation for untouched.
    table={'stars.major.ziweiMaj':'紫微','stars.minor.zuofuMin':'左辅','palaces.soulPalace':'命宫',
           'heavenlyStem.renHeavenly':'壬','earthlyBranch.wuEarthly':'午','hongluan':'红鸾','stars.major.pojunMaj':'破军'}
    i18n=types.SimpleNamespace(t=lambda key, lang=None: table.get(key, key))
    class FakeChart:
        def model_dump(self, **kw):
            return {'soul':'pojunMaj','earthly_branch_of_soul_palace':'wuEarthly','time':'寅时','gender':'女',
                    'palaces':[{'name':'soulPalace','heavenly_stem':'renHeavenly','earthly_branch':'wuEarthly',
                                'major_stars':[{'name':'ziweiMaj','type':'major','scope':'origin','brightness':'庙','mutagen':'科'}],
                                'minor_stars':[{'name':'zuofuMin','type':'soft','scope':'origin'}],
                                'adjective_stars':[{'name':'hongluan','type':'flower','scope':'origin'},{'name':'unknownKey','type':'adjective','scope':'origin'}],
                                'changsheng12':'长生'}]}
        def horoscope(self, date_str, hour):
            return {'yearly':{'name':'流年','heavenly_stem':'renHeavenly','earthly_branch':'wuEarthly',
                              'palace_names':['soulPalace'],'mutagen':['ziweiMaj','zuofuMin']}}
    class FakeAstro:
        def by_solar(self,*args):
            return FakeChart()
    monkeypatch.setitem(sys.modules,'iztro_py',types.SimpleNamespace(astro=FakeAstro(),i18n=i18n))
    monkeypatch.setitem(sys.modules,'iztro_py.i18n',i18n)
    out=professional_ziwei_chart(ProfessionalZiweiRequest(birth=BirthInput(**BIRTH),target_date='2024-02-10'))
    natal, palace=out['natal'], out['natal']['palaces'][0]
    assert (natal['soul'], natal['earthly_branch_of_soul_palace'], natal['time']) == ('破军', '午', '寅时')
    assert (palace['name'], palace['heavenly_stem'], palace['earthly_branch']) == ('命宫', '壬', '午')
    assert palace['major_stars'][0] == {'name':'紫微','type':'major','scope':'origin','brightness':'庙','mutagen':'科'}
    assert palace['minor_stars'][0]['name'] == '左辅'
    assert [s['name'] for s in palace['adjective_stars']] == ['红鸾', 'unknownKey']
    yearly=out['horoscope']['yearly']
    assert yearly == {'name':'流年','heavenly_stem':'壬','earthly_branch':'午','palace_names':['命宫'],'mutagen':['紫微','左辅']}


def test_real_provider_gives_chinese_names_that_match_the_native_chart():
    # Runs where iztro-py is installed (the CI compatibility job pins 0.5.0); skipped elsewhere.
    pytest.importorskip('iztro_py')
    from app.engines import calculate_ziwei
    birth=BirthInput(**BIRTH)
    out=professional_ziwei_chart(ProfessionalZiweiRequest(birth=birth,target_date='2024-02-10',target_hour=10))
    native=calculate_ziwei(birth)
    cjk=lambda v: isinstance(v, str) and v and all('\u4e00' <= ch <= '\u9fff' for ch in v)
    palaces=out['natal']['palaces']
    assert len(palaces) == 12
    for p in palaces:
        assert cjk(p['name']) and p['name'].endswith('宫') and cjk(p['heavenly_stem']) and cjk(p['earthly_branch'])
        for kind in ('major_stars','minor_stars','adjective_stars'):
            assert all(cjk(s['name']) for s in p.get(kind, [])), (kind, p.get(kind))
    theirs={s['name']: p['earthly_branch'] for p in palaces for s in p.get('major_stars', [])}
    ours={star: p['branch'] for p in native['palaces'] for star in p['main_stars']}
    assert theirs == ours and len(ours) == 14
    assert out['natal']['earthly_branch_of_soul_palace'] == native['ming_palace']
    assert cjk(out['natal']['soul']) and cjk(out['natal']['body'])
    for layer in ('decadal','yearly','monthly','daily','hourly'):
        item=out['horoscope'][layer]
        assert cjk(item['earthly_branch']) and all(cjk(n) for n in item['mutagen']) and all(cjk(n) for n in item['palace_names'])


def test_gender_and_future_target_refused():
    with pytest.raises(ValidationError):
        ProfessionalZiweiRequest(birth=BirthInput(birth_datetime='2000-08-16T04:00'))
    with pytest.raises(ValidationError):
        ProfessionalZiweiRequest(birth=BirthInput(**BIRTH),target_date='2200-01-01')


def test_qimen_comparison_every_available_palace_field():
    moment=BirthInput(birth_datetime='2026-09-23T12:00',gender='female')
    generated=qimen_chart(QimenRequest(moment=moment))
    fields=('earth_stem','heaven_stem','dark_stem','star','door','deity','void','center_lodged_here')
    body={'moment':moment.model_dump(),'reference_source':'manual independently transcribed chart',
          'reference_school':'时家拆补转盘',
          'root_fields':{'bureau':generated['bureau'],'dun':generated['dun']},
          'palaces':[{'number':p['number'],**{k:p[k] for k in fields if p[k] is not None}} for p in generated['palaces']]}
    req=QimenAuditRequest.model_validate(body)
    out=qimen_reference_audit(req)
    assert out['compared']==2+sum(len(p)-1 for p in body['palaces']) and out['matches']
    assert out['matching']==out['compared']
    body['palaces'][0]['earth_stem']='X'
    changed=qimen_reference_audit(QimenAuditRequest.model_validate(body))
    assert not changed['matches'] and len(changed['mismatches'])==1
    assert changed['mismatches'][0]['field']=='palaces.1.earth_stem'
    # fields lists every comparison, root fields first, so a client can mark matches as well as differences.
    assert len(changed['fields'])==changed['compared'] and [f['field'] for f in changed['fields'][:2]]==['bureau','dun']
    assert [f for f in changed['fields'] if not f['match']]==changed['mismatches']
    assert {'field':'palaces.1.earth_stem','ours':generated['palaces'][0]['earth_stem'],'reference':'X','match':False} in changed['fields']
    # The result names the moment it was raised for, so a saved copy says what it describes.
    assert changed['moment']=={'birth_datetime':'2026-09-23T12:00','timezone':'Asia/Shanghai','time_mode':'clock','longitude':None,'late_zi_day_rollover':False}
    assert changed['instant']==generated['instant']
    with TestClient(app) as client:
        r=client.post('/api/qimen-reference-audit',json=body)
    assert r.status_code==200 and r.json()==call_tool('qimen_reference_audit',body)


@pytest.mark.parametrize('bad',[
    {'moment':BIRTH,'reference_source':'ref a','reference_school':'s','root_fields':{}},
    {'moment':BIRTH,'reference_source':'ref a','reference_school':'流派一','root_fields':{'madeup':'x'}},
    {'moment':BIRTH,'reference_source':'ref a','reference_school':'流派一','palaces':[{'number':1,'star':'天蓬'},{'number':1,'star':'天英'}]},
    {'moment':BIRTH,'reference_source':'ref a','reference_school':'流派一','root_fields':{'bureau':[3]}},
    {'moment':BIRTH,'reference_source':'ref a','reference_school':'流派一','palaces':[{'number':1,'star':None}]},
])
def test_invalid_reference_cannot_claim_verified(bad):
    with pytest.raises(ValidationError):
        QimenAuditRequest.model_validate(bad)

@pytest.mark.parametrize('case', __import__('json').loads((__import__('pathlib').Path(__file__).parent/'fixtures/qimen_public_2026.json').read_text(encoding='utf-8'))['cases'], ids=lambda c:c['datetime'])
def test_external_qimen_fixture_integrated_audit_tool(case):
    """Public source 5 charts: 6 top-level fields + 9 separate palace dark stems."""
    req=QimenAuditRequest.model_validate({
        'moment':{'birth_datetime':case['datetime'],'timezone':'Asia/Shanghai'},
        'reference_source':'https://github.com/qfdk/qimen/blob/main/test/paipan.test.js',
        'reference_school':'MIT public reference hour-board',
        'root_fields':{field:case[field] for field in ('dun','bureau','zhi_fu_star','zhi_fu_palace','zhi_shi_door','zhi_shi_palace')},
        'palaces':[{'number':int(number),'dark_stem':value}
                    for number,value in case['dark_stems'].items()]})
    compared=qimen_reference_audit(req)
    assert compared['matching']==compared['compared']==15
    assert compared['mismatches']==[]
    assert set(compared['comparison_scope'])=={'dun','bureau','zhi_fu_star','zhi_fu_palace','zhi_shi_door','zhi_shi_palace','dark_stem'}
