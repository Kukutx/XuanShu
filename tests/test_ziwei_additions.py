"""Structural Zi Wei extension checks; not an external professional chart certification."""
from app.engines import LUCUN_BY_STEM, BirthInput, calculate_ziwei
from app.ziwei_extensions import BOSHI, BRIGHTNESS, BRIGHTNESS_LEVELS, CHANGSHENG, JIANGQIAN, SUIQIAN, adjunct_stars


def test_named_stars_and_natal_cycles_complete():
    chart = calculate_ziwei(BirthInput(birth_datetime='2000-08-16T04:00',gender='female'))
    stars = chart['star_positions']
    assert len(stars) == 58 == len(set(stars))
    assert chart['star_counts']['original_selected']==18
    assert chart['star_counts']['additional_named']==26
    for p in chart['palaces']:
        assert set(p['auxiliary_stars']) == set(p['auxiliary_star_groups']['original_selected'] + p['auxiliary_star_groups']['additional_named'])
        assert set(p['natal_cycles'])=={'changsheng','boshi','natal_jiangqian','natal_suiqian'}
        assert all(age in range(1,121) for age in p['small_limit_nominal_ages'])
    for typ, names in (('changsheng', CHANGSHENG),('boshi', BOSHI),('natal_jiangqian',JIANGQIAN),('natal_suiqian',SUIQIAN)):
        assert sorted(p['natal_cycles'][typ] for p in chart['palaces']) == sorted(names)
    for nominal in range(1,121):
        assert sum(nominal in p['small_limit_nominal_ages'] for p in chart['palaces']) == 1


def test_unspecified_gender_never_invents_gender_direction():
    chart=calculate_ziwei(BirthInput(birth_datetime='2024-02-10T12:00',gender='unspecified'))
    assert 'changsheng' not in chart['natal_cycles_included']
    assert 'boshi' not in chart['natal_cycles_included']
    assert all(p['decade'] is None and not p['small_limit_nominal_ages'] for p in chart['palaces'])
    assert all(set(p['natal_cycles']) == {'natal_jiangqian','natal_suiqian'} for p in chart['palaces'])


def test_new_placements_do_not_mutate_original_star_mapping():
    from app.engines import _star_positions
    original = _star_positions(17,3,7,2,6,4)
    backup=dict(original)
    extra=adjunct_stars(17,7,2,6,4,6,10,original)
    assert original==backup
    assert len(extra)==26
    assert not set(original).intersection(extra)
    assert all(isinstance(branch,int) and 0<=branch<12 for branch in extra.values())


def test_ziwei_reference_deterministic_across_python_hash_seeds():
    """Stable cross-process outputs are essential for audit records and MCP cacheability."""
    import os
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    code = ("import json; from app.engines import BirthInput,calculate_ziwei; "
            "print(json.dumps(calculate_ziwei(BirthInput(birth_datetime='2000-08-16T04:00', "
            "gender='female'))['palaces'],ensure_ascii=False,sort_keys=True))")
    outputs=[]
    for seed in ("3", "12345"):
        env={**os.environ, "PYTHONHASHSEED":seed}
        run=subprocess.run([sys.executable, '-c', code],cwd=root,env=env,capture_output=True,text=True,check=True,timeout=30)
        outputs.append(run.stdout)
    assert outputs[0] == outputs[1]


def test_late_zi_rollover_takes_the_next_lunar_date():
    # 2026-03-18 is lunar 1-30. With the 23:00 day change, 23:27 counts as 2-1, the same day as the bazi day pillar.
    birth = dict(birth_datetime='2026-03-18T23:27', gender='female')
    same_day = calculate_ziwei(BirthInput(**birth))
    next_day = calculate_ziwei(BirthInput(**birth, late_zi_day_rollover=True))
    assert (same_day['lunar_date']['month'], same_day['lunar_date']['day']) == (1, 30)
    assert (next_day['lunar_date']['month'], next_day['lunar_date']['day']) == (2, 1)
    assert next_day['rules']['late_zi_day_rollover_in_ziwei'] is True
    ming = [next(p['branch'] for p in chart['palaces'] if p['is_ming']) for chart in (same_day, next_day)]
    assert ming == ['寅', '卯']
    # Only 23:00-23:59 changes day.
    before = calculate_ziwei(BirthInput(birth_datetime='2026-03-18T22:59', gender='female', late_zi_day_rollover=True))
    assert before['lunar_date']['day'] == 30


def test_late_zi_rollover_on_the_last_supported_day():
    import pytest
    from datetime import date
    from app.astronomy import chinese_lunar_date
    # 2099-12-31 23:30 with the 23:00 day change reads 2100-01-01, still inside lunar year 2099.
    chart = calculate_ziwei(BirthInput(birth_datetime='2099-12-31T23:30', gender='male', late_zi_day_rollover=True))
    assert (chart['lunar_date']['year'], chart['lunar_date']['month'], chart['lunar_date']['day']) == (2099, 11, 21)
    with pytest.raises(ValueError):
        chinese_lunar_date(date(2100, 1, 1))


def test_star_tables_found_by_the_iztro_crosscheck():
    # iztro 2.6.1: a 辛 year puts 天魁 in 午 and 天钺 in 寅 ("辛年午寅"); 封诰 counts forward from 寅 at the Zi hour.
    xin = calculate_ziwei(BirthInput(birth_datetime='1981-12-18T13:09', gender='male'))['star_positions']
    assert (xin['天魁'], xin['天钺']) == ('午', '寅')
    yin_hour = calculate_ziwei(BirthInput(birth_datetime='1988-02-08T04:25', gender='male'))['star_positions']
    assert yin_hour['封诰'] == '辰' and yin_hour['台辅'] == '申'


def brightness(chart: dict) -> dict:
    return {p['branch']: p['star_brightness'] for p in chart['palaces'] if p['star_brightness']}


def test_star_brightness_matches_iztro_reference():
    # iztro 2.6.1 (JavaScript): astro.bySolar('2000-8-16', 2, '女') and astro.bySolar('1981-12-18', 7, '男').
    chart = calculate_ziwei(BirthInput(birth_datetime='2000-08-16T04:00', gender='female'))
    assert brightness(chart) == {
        '子': {'贪狼': '旺', '铃星': '陷'}, '丑': {'天同': '不', '巨门': '不'}, '寅': {'武曲': '得', '天相': '庙'},
        '卯': {'太阳': '庙', '天梁': '庙'}, '辰': {'七杀': '庙', '火星': '陷'}, '巳': {'天机': '平'},
        '午': {'紫微': '庙', '文曲': '陷'}, '未': {'陀罗': '庙'}, '申': {'破军': '得', '文昌': '得'},
        '酉': {'擎羊': '陷'}, '戌': {'廉贞': '利', '天府': '庙'}, '亥': {'太阴': '庙'}}
    other = calculate_ziwei(BirthInput(birth_datetime='1981-12-18T13:09', gender='male'))
    assert brightness(other)['子'] == {'紫微': '平'} and brightness(other)['戌'] == {'七杀': '庙', '擎羊': '庙', '火星': '庙'}
    # Every main star has a level wherever it sits; stars without a published table have none.
    for palace in chart['palaces']:
        assert set(palace['main_stars']) <= set(palace['star_brightness'])
        assert set(palace['star_brightness']) <= set(BRIGHTNESS)
    assert '左辅' not in {star for p in chart['palaces'] for star in p['star_brightness']}


def test_brightness_table_covers_every_branch_a_star_can_take():
    assert all(len(levels) == 12 for levels in BRIGHTNESS.values())
    assert {level for levels in BRIGHTNESS.values() for level in levels} == set(BRIGHTNESS_LEVELS) | {None}
    # 擎羊 and 陀罗 sit beside 禄存, which never takes 辰戌丑未, so each of them misses four branches.
    yang = {(lucun + 1) % 12 for lucun in LUCUN_BY_STEM}
    tuo = {(lucun - 1) % 12 for lucun in LUCUN_BY_STEM}
    assert {b for b in range(12) if BRIGHTNESS['擎羊'][b]} == yang and {b for b in range(12) if BRIGHTNESS['陀罗'][b]} == tuo
    assert all(None not in levels for star, levels in BRIGHTNESS.items() if star not in ('擎羊', '陀罗'))
