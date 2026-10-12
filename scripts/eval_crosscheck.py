"""Cross-check XuanShu's calendar and chart engines against independent open-source libraries.

Every day from 1901 to 2099 is compared for the lunar date and the four pillars;
every solar term and principal moon phase is compared for its instant; a fixed
random sample of births is compared for the Zi Wei Dou Shu chart and its
period layers. A full run
writes docs/evals/crosscheck.json, docs/evals/README.md and the page summary
static/crosscheck-summary.json together; a quick run writes only to
build/evals-quick/ so it never replaces the committed report.

The reference libraries are not XuanShu dependencies. Install the pinned set in
a separate environment, then run the script:

    pip install -r requirements.txt -r docs/evals/requirements.txt
    npm install --prefix docs/evals              # iztro, the original JavaScript library
    python scripts/eval_crosscheck.py            # full run
    python scripts/eval_crosscheck.py --quick    # every tenth year, smaller Zi Wei sample, build/evals-quick/

References: sxtwl (寿星天文历 by 许剑伟), lunar_python (6tail), lunardate
(table based), PyEphem (libastro, VSOP87), iztro-py (port of iztro) and iztro
itself, run through Node.js (scripts/iztro_reference.cjs) for the stars and
period stars iztro-py does not provide.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ephem  # noqa: E402
import lunardate  # noqa: E402
import swisseph as swe  # noqa: E402
import sxtwl  # noqa: E402
from iztro_py import astro  # noqa: E402
from lunar_python import Solar  # noqa: E402

from app.almanac import moon_phases  # noqa: E402
from app.astronomy import TERMS, _new_moons_between, calendar_zone, chinese_lunar_date, from_jd, solar_term_jd, to_jd  # noqa: E402
from app.engines import ZIWEI_STARS, TIANFU_STARS, BirthInput, calculate_ziwei, pillar_indices  # noqa: E402
from app.ziwei_horoscope import ZiweiHoroscopeRequest, ziwei_horoscope  # noqa: E402

UTC = timezone.utc
CHINA = timezone(timedelta(hours=8))
STEMS, BRANCHES = '甲乙丙丁戊己庚辛壬癸', '子丑寅卯辰巳午未申酉戌亥'
LAST_OBSERVED_DELTA_T_YEAR = 2025  # later years rest on Delta T forecasts
EXAMPLES = 20
# Engine corrections this evaluation led to; kept in the report.
FIXES = [{'months': ['1914-11-17', '1916-02-03', '1920-11-10'], 'cause': 'beijing_meridian',
          'text': '1914、1916、1920 年各有一个月，玄枢原来一律按北京时间（东经 120°）编历，初一比三家参考都晚一天；'
                  '这三个月的朔在北京时间午夜后几分钟，按 1912–1928 年实际使用的北京地方平时（东经 116°25′）则在午夜前。'
                  '已改为这些年份按北京地方平时编历，重跑后三个月全部一致。'},
         {'cause': 'ziwei_star_tables',
          'text': '紫微辅星对照 iztro 时查出两张安星表与所引规则不符：辛年天魁、天钺互换（应为天魁在午、天钺在寅，“辛年午寅”），'
                  '封诰逆行（应从寅宫起子时顺数到生时）。辛年出生约占一成，封诰只有子时、午时出生原来恰好对。已改正，重跑后全部辅星一致。'}]


def gz(index: int) -> str:
    return STEMS[index % 10] + BRANCHES[index % 12]


def all_days(years):
    for year in years:
        day = date(year, 1, 1)
        while day.year == year:
            yield day
            day += timedelta(days=1)


def seconds_stats(deltas: list[float]) -> dict:
    absolute = sorted(abs(x) for x in deltas)
    if not absolute:
        return {'count': 0}
    return {
        'count': len(absolute),
        'mean_abs_seconds': round(statistics.fmean(absolute), 2),
        'p95_abs_seconds': round(absolute[int(0.95 * (len(absolute) - 1))], 2),
        'max_abs_seconds': round(absolute[-1], 2),
        'within_60s': sum(x <= 60 for x in absolute),
    }


def split_stats(rows: list[dict], key: str) -> dict:
    observed = [r[key] for r in rows if r['year'] <= LAST_OBSERVED_DELTA_T_YEAR]
    forecast = [r[key] for r in rows if r['year'] > LAST_OBSERVED_DELTA_T_YEAR]
    return {'all': seconds_stats([r[key] for r in rows]),
            f'through_{LAST_OBSERVED_DELTA_T_YEAR}': seconds_stats(observed),
            f'after_{LAST_OBSERVED_DELTA_T_YEAR}': seconds_stats(forecast)}


class Tally:
    """Mismatch counter with a few examples, per reference and field."""

    def __init__(self):
        self.checked = Counter()
        self.mismatch = Counter()
        self.examples: dict[str, list] = {}

    def check(self, key: str, ours, theirs, example: dict) -> None:
        self.checked[key] += 1
        if ours != theirs:
            self.mismatch[key] += 1
            bucket = self.examples.setdefault(key, [])
            if len(bucket) < EXAMPLES:
                bucket.append({**example, 'xuanshu': ours, 'reference': theirs})

    def report(self) -> dict:
        return {key: {'checked': self.checked[key], 'mismatches': self.mismatch[key],
                      'examples': self.examples.get(key, [])} for key in sorted(self.checked)}


# ---------------------------------------------------------------- calendar

def sxtwl_lunar(day: date):
    d = sxtwl.fromSolar(day.year, day.month, day.day)
    return d.getLunarYear(), d.getLunarMonth(), d.getLunarDay(), bool(d.isLunarLeap()), gz(_sx_index(d.getDayGZ()))


def _sx_index(value) -> int:
    return next(i for i in range(60) if i % 10 == value.tg and i % 12 == value.dz)


def lunar_python_values(moment: datetime):
    lunar = Solar.fromYmdHms(moment.year, moment.month, moment.day, moment.hour, moment.minute, moment.second).getLunar()
    month = lunar.getMonth()
    return ((lunar.getYear(), abs(month), lunar.getDay(), month < 0),
            (lunar.getYearInGanZhiExact(), lunar.getMonthInGanZhiExact(), lunar.getDayInGanZhi(), lunar.getTimeInGanZhi()))


def lunardate_values(day: date):
    try:
        value = lunardate.LunarDate.from_solar_date(day.year, day.month, day.day)
    except ValueError:
        return None
    return value.year, value.month, value.day, bool(value.isLeapMonth)


def _new_moon_near(day: date) -> datetime:
    midnight = datetime(day.year, day.month, day.day, tzinfo=CHINA)
    moons = [from_jd(jd) for jd in _new_moons_between(to_jd(midnight) - 3, to_jd(midnight) + 3)]
    moment = min(moons, key=lambda t: abs((t - midnight).total_seconds()))
    return moment.astimezone(calendar_zone(moment))


def _minutes_from_midnight(local: datetime) -> float:
    minutes = local.hour * 60 + local.minute + local.second / 60
    return round(min(minutes, 1440 - minutes), 1)


def compare_days(years) -> dict:
    lunar, pillars = Tally(), Tally()
    runs: list[dict] = []  # consecutive days on which some reference gives another lunar date
    for day in all_days(years):
        ours = chinese_lunar_date(day)
        xs = (ours['year'], ours['month'], ours['day'], ours['is_leap_month'])
        noon = datetime(day.year, day.month, day.day, 12, tzinfo=CHINA)
        (y, m, d, h), _, _ = pillar_indices(noon)
        ours_pillars = (gz(y), gz(m), gz(d), gz(h))
        example = {'date': day.isoformat()}
        sx = sxtwl_lunar(day)
        lunar.check('sxtwl', xs, sx[:4], example)
        lp_lunar, lp_pillars = lunar_python_values(noon)
        lunar.check('lunar_python', xs, lp_lunar, example)
        ld = lunardate_values(day)
        if ld is not None:
            lunar.check('lunardate', xs, ld, example)
        pillars.check('sxtwl.day', ours_pillars[2], sx[4], example)
        for name, ours_value, theirs in zip(('year', 'month', 'day', 'hour'), ours_pillars, lp_pillars):
            pillars.check('lunar_python.' + name, ours_value, theirs, {'moment': noon.isoformat()})
        differing = [name for name, value in (('sxtwl', sx[:4]), ('lunar_python', lp_lunar), ('lunardate', ld))
                     if value is not None and value != xs]
        if differing:
            if runs and runs[-1]['references'] == differing and (day - date.fromisoformat(runs[-1]['last'])).days == 1:
                runs[-1]['last'], runs[-1]['days'] = day.isoformat(), runs[-1]['days'] + 1
            else:
                new_moon = _new_moon_near(day)
                runs.append({'first': day.isoformat(), 'last': day.isoformat(), 'days': 1, 'references': differing,
                             'xuanshu': xs, 'sxtwl': sx[:4], 'lunar_python': lp_lunar, 'lunardate': ld,
                             'new_moon_calendar_time': new_moon.isoformat(timespec='seconds'),
                             'minutes_from_midnight': _minutes_from_midnight(new_moon)})
    return {'lunar_dates': lunar.report(), 'lunar_month_differences': runs, 'pillars_at_noon': pillars.report()}


def compare_jie_boundaries(years, offset_seconds: int = 120) -> dict:
    """Month pillar just before and just after each of the twelve jie, versus lunar_python."""
    tally = Tally()
    for year in years:
        for name, longitude, _, _ in TERMS:
            if longitude % 30 != 15:
                continue
            instant = from_jd(solar_term_jd(year, longitude))
            for side, delta in (('before', -offset_seconds), ('after', offset_seconds)):
                moment = (instant + timedelta(seconds=delta)).astimezone(CHINA)
                (y, m, _, _), _, _ = pillar_indices(moment)
                _, lp = lunar_python_values(moment)
                example = {'term': name, 'side': side, 'moment': moment.isoformat(timespec='seconds')}
                tally.check('month', gz(m), lp[1], example)
                if longitude == 315:
                    tally.check('year', gz(y), lp[0], example)
    return {'offset_seconds': offset_seconds, 'results': tally.report()}


# ---------------------------------------------------------------- instants

def _ephem_sun_longitude(moment: datetime) -> float:
    when = ephem.Date(moment.astimezone(UTC).replace(tzinfo=None))
    sun = ephem.Sun()
    sun.compute(when)
    return math.degrees(ephem.Ecliptic(ephem.Equatorial(sun.g_ra, sun.g_dec, epoch=when), epoch=when).lon)


def ephem_term(longitude: int, guess: datetime) -> datetime:
    moment = guess
    for _ in range(8):
        diff = (_ephem_sun_longitude(moment) - longitude + 180) % 360 - 180
        moment -= timedelta(days=diff / 0.98565)
        if abs(diff) < 1e-7:
            break
    return moment


def sxtwl_terms(years) -> dict[int, list[datetime]]:
    found: dict[int, list[datetime]] = {}
    for year in range(min(years) - 1, max(years) + 2):
        for item in sxtwl.getJieQiByYear(year):
            t = sxtwl.JD2DD(item.jd - 8 / 24)  # sxtwl works in Beijing time
            moment = datetime(int(t.Y), int(t.M), int(t.D), int(t.h), int(t.m), tzinfo=UTC) + timedelta(seconds=t.s)
            found.setdefault((270 + 15 * item.jqIndex) % 360, []).append(moment)
    return found


def compare_solar_terms(years) -> dict:
    reference = sxtwl_terms(years)
    rows, china_dates = [], []
    for year in years:
        for name, longitude, _, _ in TERMS:
            ours = from_jd(solar_term_jd(year, longitude))
            sx = min(reference[longitude], key=lambda t: abs((t - ours).total_seconds()))
            ep = ephem_term(longitude, ours)
            row = {'year': year, 'term': name, 'xuanshu_utc': ours.isoformat(timespec='seconds'),
                   'sxtwl': (sx - ours).total_seconds(), 'ephem': (ep - ours).total_seconds()}
            rows.append(row)
            if sx.astimezone(CHINA).date() != ours.astimezone(CHINA).date():
                china_dates.append({'year': year, 'term': name,
                                    'xuanshu_china': ours.astimezone(CHINA).isoformat(timespec='seconds'),
                                    'sxtwl_china': sx.astimezone(CHINA).isoformat(timespec='seconds')})
    worst = sorted(rows, key=lambda r: -abs(r['sxtwl']))[:EXAMPLES]
    return {'events': len(rows), 'sxtwl': split_stats(rows, 'sxtwl'), 'ephem': split_stats(rows, 'ephem'),
            'china_date_differs_from_sxtwl': china_dates,
            'worst_vs_sxtwl': [{**r, 'sxtwl': round(r['sxtwl'], 1), 'ephem': round(r['ephem'], 1)} for r in worst]}


EPHEM_PHASES = {0: ephem.next_new_moon, 90: ephem.next_first_quarter_moon,
                180: ephem.next_full_moon, 270: ephem.next_last_quarter_moon}


def compare_moon_phases(years, near_midnight_minutes: int = 10) -> dict:
    rows, near_midnight = [], []
    for year in years:
        for phase in moon_phases(year):
            ours = phase['instant'].astimezone(UTC)
            start = ephem.Date((ours - timedelta(days=2)).replace(tzinfo=None))
            theirs = EPHEM_PHASES[phase['elongation']](start).datetime().replace(tzinfo=UTC)
            rows.append({'year': year, 'ephem': (theirs - ours).total_seconds()})
            if phase['elongation'] == 0:
                local = ours.astimezone(calendar_zone(ours))
                gap = _minutes_from_midnight(local)
                if gap < near_midnight_minutes:
                    near_midnight.append({'new_moon_calendar_time': local.isoformat(timespec='seconds'),
                                          'minutes_from_midnight': gap})
    return {'events': len(rows), 'ephem': split_stats(rows, 'ephem'),
            'near_midnight_minutes': near_midnight_minutes, 'new_moons_near_china_midnight': near_midnight}


def delta_t_table() -> dict:
    return {str(year): round(swe.deltat(to_jd(datetime(year, 7, 1, tzinfo=UTC))) * 86400, 1)
            for year in (1901, 1950, 2000, 2025, 2026, 2050, 2075, 2099)}


# ---------------------------------------------------------------- Zi Wei

STAR_KEYS = {'ziweiMaj': '紫微', 'tianjiMaj': '天机', 'taiyangMaj': '太阳', 'wuquMaj': '武曲', 'tiantongMaj': '天同',
             'lianzhenMaj': '廉贞', 'tianfuMaj': '天府', 'taiyinMaj': '太阴', 'tanlangMaj': '贪狼', 'jumenMaj': '巨门',
             'tianxiangMaj': '天相', 'tianliangMaj': '天梁', 'qishaMaj': '七杀', 'pojunMaj': '破军'}
TRANSFORMED_MINOR = {'zuofuMin': '左辅', 'youbiMin': '右弼', 'wenchangMin': '文昌', 'wenquMin': '文曲'}
BRANCH_KEYS = {key + 'Earthly': BRANCHES[i] for i, key in
               enumerate(('zi', 'chou', 'yin', 'mao', 'chen', 'si', 'wu', 'wei', 'shen', 'you', 'xu', 'hai'))}


def _iztro_values(birth: datetime, gender: str, hour_index: int | None = None) -> dict:
    if hour_index is None:
        hour_index = 12 if birth.hour == 23 else (birth.hour + 1) // 2
    # fix_leap=True matches XuanShu's default: the second half of a leap month counts as the next month.
    chart = astro.by_solar(f'{birth.year}-{birth.month}-{birth.day}', hour_index, '男' if gender == 'male' else '女',
                           True, 'zh-CN').model_dump(mode='json', exclude_none=True)
    stars, transformations = {}, {}
    for palace in chart['palaces']:
        for star in palace.get('major_stars', []) + palace.get('minor_stars', []):
            name = STAR_KEYS.get(star['name']) or TRANSFORMED_MINOR.get(star['name'], star['name'])
            if star['name'] in STAR_KEYS:
                stars[name] = BRANCH_KEYS[palace['earthly_branch']]
            if star.get('mutagen'):
                transformations[name] = star['mutagen']
    lunar = chart['raw_lunar_date']
    return {'lunar': (lunar['year'], lunar['month'], lunar['day'], lunar['is_leap_month']),
            'ming': BRANCH_KEYS[chart['earthly_branch_of_soul_palace']],
            'shen': BRANCH_KEYS[chart['earthly_branch_of_body_palace']],
            'bureau': chart['five_elements_class'], 'stars': stars,
            'transformations': dict(sorted(transformations.items()))}


def _xuanshu_values(birth: datetime, gender: str, rollover: bool = False) -> dict:
    chart = calculate_ziwei(BirthInput(birth_datetime=birth.isoformat(timespec='minutes'), timezone='Asia/Shanghai',
                                       gender=gender, late_zi_day_rollover=rollover))
    stars = {}
    for palace in chart['palaces']:
        for star in palace['main_stars']:
            stars[star] = palace['branch']
    lunar = chart['lunar_date']
    return {'lunar': (lunar['year'], lunar['month'], lunar['day'], lunar['is_leap_month']),
            'ming': next(p['branch'] for p in chart['palaces'] if p['is_ming']),
            'shen': next(p['branch'] for p in chart['palaces'] if p['is_shen']),
            'bureau': chart['five_elements_bureau'], 'stars': stars,
            'transformations': dict(sorted((t['star'], t['type'][1]) for t in chart['birth_year_transformations']))}


IZTRO_NODE_MODULES = ROOT / 'docs' / 'evals' / 'node_modules'
MAIN_STARS = {name for name, _ in ZIWEI_STARS + TIANFU_STARS}
IZTRO_ALIASES = {'解神': '月解'}  # iztro's 解神 is the month-based 月解; its 年解 is separate
CYCLE_KEYS = (('changsheng', 'changsheng'), ('boshi', 'boshi'), ('natal_suiqian', 'suiqian'), ('natal_jiangqian', 'jiangqian'))


def iztro_js(queries: list[dict]) -> list[dict]:
    """Charts from iztro (JavaScript) for a batch of queries; see scripts/iztro_reference.cjs."""
    run = subprocess.run(['node', str(ROOT / 'scripts' / 'iztro_reference.cjs')], input='\n'.join(map(json.dumps, queries)),
                         capture_output=True, text=True, check=True, env=dict(os.environ, NODE_PATH=str(IZTRO_NODE_MODULES)))
    return [json.loads(line) for line in run.stdout.splitlines()]


def _iztro_query(birth: datetime, gender: str) -> dict:
    return {'date': f'{birth.year}-{birth.month}-{birth.day}', 'hour': 12 if birth.hour == 23 else (birth.hour + 1) // 2,
            'gender': '男' if gender == 'male' else '女'}


def _iztro_js_values(row: dict, names) -> dict:
    """Branch of each named star, and the four twelve-god cycles per branch, from one iztro (JavaScript) chart."""
    where = {IZTRO_ALIASES.get(star, star): palace['branch'] for palace in row['palaces'] for star in palace['stars']}
    return {'other_stars': {name: where.get(name) for name in names},
            'cycles': {palace['branch']: [palace[key] for _, key in CYCLE_KEYS] for palace in row['palaces']}}


def _xuanshu_other_values(birth: datetime, gender: str) -> dict:
    chart = calculate_ziwei(BirthInput(birth_datetime=birth.isoformat(timespec='minutes'), timezone='Asia/Shanghai', gender=gender))
    return {'other_stars': {name: branch for name, branch in chart['star_positions'].items() if name not in MAIN_STARS},
            'cycles': {p['branch']: [p['natal_cycles'].get(key) for key, _ in CYCLE_KEYS] for p in chart['palaces']}}


def _sample_births(count: int, seed: int, late: bool) -> list[tuple[datetime, str]]:
    rng = random.Random(seed)
    births = []
    while len(births) < count:
        day = date(1930, 1, 1) + timedelta(days=rng.randrange((date(2049, 12, 31) - date(1930, 1, 1)).days))
        hour = 23 if late else rng.randrange(23)
        births.append((datetime(day.year, day.month, day.day, hour, rng.randrange(60)), rng.choice(('male', 'female'))))
    return births


def _iztro_keeps_month(birth: datetime) -> bool:
    """True when iztro's late-Zi index 12 and XuanShu's 23:00 rollover use different lunar months.

    iztro adds one to the day number but keeps the birth day's lunar month and skips the leap-month fix at
    index 12 (``fix_lunar_month_index`` and ``fix_lunar_day_index``); XuanShu takes the whole next lunar date.
    The two only part ways at the end of a month and in the second half of a leap month.
    """
    today, following = chinese_lunar_date(birth.date()), chinese_lunar_date(birth.date() + timedelta(days=1))
    ours = following['month'] + (1 if following['is_leap_month'] and following['day'] > 15 else 0)
    return ours != today['month']


ZIWEI_KEYS = ('lunar', 'ming', 'shen', 'bureau', 'stars', 'transformations')


def compare_ziwei(count: int, late_count: int) -> dict:
    def run(births, hour_index: int | None = None, rollover: bool = False, keys=ZIWEI_KEYS) -> dict:
        tally = Tally()
        for birth, gender in births:
            ours, theirs = _xuanshu_values(birth, gender, rollover), _iztro_values(birth, gender, hour_index)
            example = {'birth': birth.isoformat(timespec='minutes'), 'gender': gender}
            for key in keys:
                tally.check(key, ours[key], theirs[key], example)
        return tally.report()
    def run_other(births) -> tuple[dict, dict]:
        # Every other star and the four twelve-god cycles, against iztro itself (iztro-py lacks some of them).
        tally, stars = Tally(), Counter()
        for (birth, gender), row in zip(births, iztro_js([_iztro_query(*item) for item in births])):
            ours = _xuanshu_other_values(birth, gender)
            theirs = _iztro_js_values(row, ours['other_stars'])
            example = {'birth': birth.isoformat(timespec='minutes'), 'gender': gender}
            for key in ('other_stars', 'cycles'):
                # Only the entries that differ go into the examples.
                differ = [k for k in ours[key] if ours[key][k] != theirs[key][k]]
                tally.check(key, {k: ours[key][k] for k in differ}, {k: theirs[key][k] for k in differ}, example)
            stars.update(name for name, branch in ours['other_stars'].items() if theirs['other_stars'][name] != branch)
        return tally.report(), {'star_count': len(ours['other_stars']), 'mismatching_stars': dict(stars.most_common())}
    main = _sample_births(count, 20261011, late=False)
    other, other_detail = run_other(main)
    late = _sample_births(late_count, 1123, late=True)
    kept = [item for item in late if _iztro_keeps_month(item[0])]
    # iztro reports the birth day's lunar date while placing stars by the next day, so the date is not compared.
    next_day_keys = tuple(key for key in ZIWEI_KEYS if key != 'lunar')
    return {
        'sample': {'births': count, 'years': '1930–2049', 'hours': '00:00–22:59', 'seed': 20261011,
                   'rules': 'clock time; second half of a leap month as the next month'},
        'results': {**run(main), **other},
        'other_stars': other_detail,
        'late_zi': {'births': late_count,
                    'note': "By default XuanShu keeps the same lunar day for 23:00-23:59 (iztro's early-Zi index 0); "
                            "with late_zi_day_rollover it takes the next day's whole lunar date. iztro's late-Zi "
                            "index 12 adds one to the day but keeps the month, so births on the last day of a month "
                            "or in the second half of a leap month are counted separately.",
                    'default_vs_iztro_same_day_zi': run(late, 0),
                    'rollover_vs_iztro_late_zi': run([item for item in late if item not in kept], 12, rollover=True,
                                                     keys=next_day_keys),
                    'iztro_keeps_month': {'births': len(kept),
                                          'examples': [item[0].isoformat(timespec='minutes') for item in kept[:EXAMPLES]],
                                          'comparison': run(kept, 12, rollover=True, keys=next_day_keys)},
                    'default_vs_iztro_late_zi': run(late, 12, keys=next_day_keys)},
    }


HOROSCOPE_LAYERS = {'decade': 'decadal', 'small_limit': 'age', 'year': 'yearly', 'month': 'monthly', 'day': 'daily', 'hour': 'hourly'}
STEM_KEYS = {key + 'Heavenly': STEMS[i] for i, key in enumerate(('jia', 'yi', 'bing', 'ding', 'wu', 'ji', 'geng', 'xin', 'ren', 'gui'))}


def _one_palace_shift(value, reference) -> bool:
    """The mismatch a one-day lunar date difference makes: the same stem and stars, the palace one step away."""
    return (value is not None and reference is not None and value[1:] == reference[1:]
            and (BRANCHES.index(value[0]) - BRANCHES.index(reference[0])) % 12 in (1, 11))


FLOW_LAYERS = ('decade', 'year', 'month', 'day', 'hour')


def _iztro_flow(item: dict) -> dict:
    """Period stars of one iztro layer by name, and the year's twelve gods by branch; palace index 0 is 寅."""
    stars = {star: BRANCHES[(i + 2) % 12] for i, names in enumerate(item['stars'] or []) for star in names}
    twelve = item['twelve'] and {BRANCHES[(i + 2) % 12]: [item['twelve']['suiqian12'][i], item['twelve']['jiangqian12'][i]]
                                 for i in range(12)}
    return {'stars': stars, 'twelve': twelve}


def compare_horoscope(count: int) -> dict:
    """Period layers (decade to hour) for random birth and target pairs: Life palace, stem, the four stars and the period stars."""
    rng = random.Random(20261012)
    tally, explained = Tally(), Counter()
    samples = []
    while len(samples) < count:
        day = date(1930, 1, 1) + timedelta(days=rng.randrange((date(2049, 12, 31) - date(1930, 1, 1)).days))
        birth = datetime(day.year, day.month, day.day, rng.randrange(23), rng.randrange(60))
        gender = rng.choice(('male', 'female'))
        target = day + timedelta(days=rng.randrange(1, 100 * 365))
        hour = rng.randrange(23)
        if target.year <= 2099:
            samples.append((birth, gender, target, hour))
    # Period stars come from iztro itself: iztro-py 0.5.0 leaves them out.
    flows = iztro_js([{**_iztro_query(birth, gender), 'target': f'{target.year}-{target.month}-{target.day}',
                       'target_hour': (hour + 1) // 2} for birth, gender, target, hour in samples])
    for (birth, gender, target, hour), flow in zip(samples, flows):
        chart = astro.by_solar(f'{birth.year}-{birth.month}-{birth.day}', (birth.hour + 1) // 2, '男' if gender == 'male' else '女',
                               True, 'zh-CN')
        theirs = chart.horoscope(f'{target.year}-{target.month}-{target.day}', (hour + 1) // 2).model_dump(mode='json')
        ours = ziwei_horoscope(ZiweiHoroscopeRequest(birth=BirthInput(birth_datetime=birth.isoformat(timespec='minutes'), gender=gender),
                                                     target_date=target, target_time=f'{hour:02d}:30'))
        # iztro takes its lunar dates from lunar_python; in the months where that calendar differs, the day and hour
        # palaces move one step and nothing else changes. Only that exact shape counts as explained.
        lunar = chinese_lunar_date(target)
        calendar_differs = lunar_python_values(datetime(target.year, target.month, target.day, 12))[0] != (
            lunar['year'], lunar['month'], lunar['day'], lunar['is_leap_month'])
        example = {'birth': birth.isoformat(timespec='minutes'), 'gender': gender, 'target': f'{target.isoformat()}T{hour:02d}:30'}
        for key, name in HOROSCOPE_LAYERS.items():
            item, layer = theirs[name], ours['layers'][key]
            # iztro's index -1 means no palace; XuanShu lists no childhood limit (童限) either.
            reference = None if item['index'] == -1 or item['name'] == '童限' else (
                BRANCHES[(item['index'] + 2) % 12], STEM_KEYS[item['heavenly_stem']],
                [STAR_KEYS.get(star) or TRANSFORMED_MINOR.get(star, star) for star in item['mutagen']])
            value = (layer['ming_branch'], layer['stem'], [t['star'] for t in layer['transformations']]) if layer['available'] else None
            tally.check(key, value, reference, example)
            if key in ('day', 'hour') and calendar_differs and _one_palace_shift(value, reference):
                explained[key] += 1
            if key in FLOW_LAYERS and layer['available'] and reference is not None:
                theirs_flow = _iztro_flow(flow['horoscope'][name])
                ours_flow = {star['name']: star['branch'] for star in layer['stars']}
                tally.check('flow_' + key, ours_flow, theirs_flow['stars'], example)
                if key == 'year':
                    tally.check('year_twelve', {p['branch']: [p['suiqian'], p['jiangqian']] for p in layer['palaces']},
                                theirs_flow['twelve'], example)
    return {'sample': {'pairs': count, 'birth_years': '1930–2049', 'targets': 'up to 100 years after birth, through 2099',
                       'hours': '00:00–22:59', 'seed': 20261012},
            'results': tally.report(), 'lunar_python_calendar_differs': dict(explained)}


# ---------------------------------------------------------------- report

def references() -> dict:
    names = {'sxtwl': 'sxtwl', 'lunar_python': 'lunar_python', 'lunardate': 'lunardate', 'ephem': 'ephem',
             'iztro_py': 'iztro-py', 'pyswisseph': 'pyswisseph'}
    found = {key: version(dist) for key, dist in names.items()}
    found['iztro'] = json.loads((IZTRO_NODE_MODULES / 'iztro' / 'package.json').read_text(encoding='utf-8'))['version']
    return found


HOROSCOPE_LABELS = {'decade': '大限', 'small_limit': '小限', 'year': '流年', 'month': '流月（斗君）', 'day': '流日', 'hour': '流时'}
FLOW_LABELS = {'flow_decade': '大限流曜（运魁至运喜）', 'flow_year': '流年流曜（流魁至流喜、年解）', 'flow_month': '流月流曜',
               'flow_day': '流日流曜', 'flow_hour': '流时流曜', 'year_twelve': '流年岁前、将前十二神'}


def horoscope_note(horoscope: dict) -> str:
    mismatches = sum(item['mismatches'] for item in horoscope['results'].values())
    explained = sum(horoscope['lunar_python_calendar_differs'].values())
    if not mismatches:
        return '各层全部一致。'
    text = (f'共 {mismatches} 处不一致，其中 {explained} 处的目标日期落在玄枢与 lunar_python 农历日期不同的月份'
            '（iztro 的农历取自 lunar_python，见上文“逐日对照”），流日、流时随农历日数相差一宫')
    return text + ('；没有其他不一致。' if explained == mismatches else f'；另有 {mismatches - explained} 处尚未解释，清单见 JSON。')


def total(section: dict, key: str) -> tuple[int, int]:
    item = section[key]
    return item['mismatches'], item['checked']


def write_markdown(result: dict, path: Path) -> None:
    days, jie, terms, moons, ziwei = (result['days'], result['jie_boundaries'], result['solar_terms'],
                                      result['moon_phases'], result['ziwei'])
    horoscope = result['horoscope']
    observed, forecast = f'through_{LAST_OBSERVED_DELTA_T_YEAR}', f'after_{LAST_OBSERVED_DELTA_T_YEAR}'

    def agree(section, key):
        return f"{section[key]['checked'] - section[key]['mismatches']}/{section[key]['checked']}"

    def late_agreement(section):
        names = {'ming': '命宫', 'shen': '身宫', 'bureau': '五行局', 'stars': '十四主星', 'transformations': '生年四化'}
        if not any(section[key]['mismatches'] for key in names):
            return f"{'、'.join(names.values())}全部一致（{agree(section, 'stars')}）"
        return '，'.join(f'{label}一致 {agree(section, key)}' for key, label in names.items())

    def row(label, mismatches_checked):
        mismatches, checked = mismatches_checked
        return f'| {label} | {checked:,} | {mismatches:,} | {100 * (checked - mismatches) / checked:.3f}% |'

    def instant_row(label, stats):
        return (f"| {label} | {stats['count']:,} | {stats['mean_abs_seconds']} | {stats['p95_abs_seconds']} | "
                f"{stats['max_abs_seconds']} | {stats['within_60s']:,} |")

    lunar, pillars = days['lunar_dates'], days['pillars_at_noon']
    zr = ziwei['results']
    lines = [
        '# 玄枢计算交叉核验评测',
        '',
        f"这份报告由 `scripts/eval_crosscheck.py` 生成（{result['generated']}，年份 {result['years'][0]}–{result['years'][1]}"
        f"{'，快速模式' if result['quick'] else ''}）。脚本把玄枢的历法和排盘结果与几个独立的开源库逐项对照，"
        '原始数据在 [crosscheck.json](crosscheck.json)。任何人装上 [requirements.txt](requirements.txt) 里固定版本的参考库，都能重跑并得到相同结果。',
        '',
        '参考库：' + '，'.join(f'{k} {v}' for k, v in result['references'].items()) + '。'
        '玄枢自己用 Swiss Ephemeris（Moshier 星历）计算天象，sxtwl 和 lunar_python 源自许剑伟的寿星天文历，'
        'PyEphem 基于 libastro，lunardate 是查表实现，iztro-py 是 iztro 的 Python 移植；iztro-py 没有的辅星、杂曜、十二神和流曜'
        '直接对照 iztro 原版（JavaScript，经 Node.js 运行 `scripts/iztro_reference.cjs`）。',
        '',
        '这只核验“算得对不对”，不评价命理解读是否应验；玄枢不对吉凶、预测准确率做任何声明。',
        '',
        '编历规则：1929 年起按东经 120°（北京时间）；1912–1928 年按北京地方平时（东经 116°25′）编历'
        '（Aslaksen, *The Mathematics of the Chinese Calendar*, 4.2、4.6 节）；1901–1911 年清朝时宪历用的是旧天文法，'
        '玄枢按现代天文与北京时间计算，不复现旧法。',
        '',
        '## 逐日对照：农历日期与四柱',
        '',
        '| 对照项 | 核对数 | 不一致 | 一致率 |',
        '| --- | ---: | ---: | ---: |',
        row('农历日期 vs sxtwl', total(lunar, 'sxtwl')),
        row('农历日期 vs lunar_python', total(lunar, 'lunar_python')),
        row('农历日期 vs lunardate', total(lunar, 'lunardate')),
        row('日柱 vs sxtwl', total(pillars, 'sxtwl.day')),
        row('年柱（正午，按立春） vs lunar_python', total(pillars, 'lunar_python.year')),
        row('月柱（正午，按节） vs lunar_python', total(pillars, 'lunar_python.month')),
        row('日柱 vs lunar_python', total(pillars, 'lunar_python.day')),
        row('时柱（正午） vs lunar_python', total(pillars, 'lunar_python.hour')),
        '',
        f"交节前后 {jie['offset_seconds']} 秒的月柱与年柱（立春）对照 lunar_python：",
        '',
        '| 对照项 | 核对数 | 不一致 | 一致率 |',
        '| --- | ---: | ---: | ---: |',
        row('交节前后月柱', total(jie['results'], 'month')),
        row('立春前后年柱', total(jie['results'], 'year')),
        '',
        '## 节气与月相时刻',
        '',
        '时刻差以秒计（参考库减玄枢）。'
        f'{LAST_OBSERVED_DELTA_T_YEAR} 年以前地球自转差 ΔT 已有观测值；之后各库用各自的 ΔT 预报，差距随年份变大。'
        '玄枢所用 Swiss Ephemeris 的 ΔT：' + '，'.join(f'{y} 年 {v} 秒' for y, v in result['delta_t_seconds'].items()) + '。',
        '',
        '| 对照项 | 事件数 | 平均差 | 95% 分位 | 最大差 | 60 秒以内 |',
        '| --- | ---: | ---: | ---: | ---: | ---: |',
        instant_row(f'节气 vs sxtwl（{result["years"][0]}–{LAST_OBSERVED_DELTA_T_YEAR}）', terms['sxtwl'][observed]),
        instant_row(f'节气 vs sxtwl（{LAST_OBSERVED_DELTA_T_YEAR + 1}–{result["years"][1]}）', terms['sxtwl'][forecast]),
        instant_row(f'节气 vs PyEphem（{result["years"][0]}–{LAST_OBSERVED_DELTA_T_YEAR}）', terms['ephem'][observed]),
        instant_row(f'节气 vs PyEphem（{LAST_OBSERVED_DELTA_T_YEAR + 1}–{result["years"][1]}）', terms['ephem'][forecast]),
        instant_row(f'月相 vs PyEphem（{result["years"][0]}–{LAST_OBSERVED_DELTA_T_YEAR}）', moons['ephem'][observed]),
        instant_row(f'月相 vs PyEphem（{LAST_OBSERVED_DELTA_T_YEAR + 1}–{result["years"][1]}）', moons['ephem'][forecast]),
        '',
        f"与 sxtwl 相比，节气落在北京时间不同日期的有 {len(terms['china_date_differs_from_sxtwl'])} 个"
        f"；朔离编历所用午夜不到 {moons['near_midnight_minutes']} 分钟的有 {len(moons['new_moons_near_china_midnight'])} 个，"
        '这些月份的初一在不同软件里容易差一天，清单见 JSON。',
        '',
        '## 紫微斗数对照 iztro',
        '',
        f"随机抽取 {ziwei['sample']['births']:,} 个出生时刻（{ziwei['sample']['years']}，{ziwei['sample']['hours']}，"
        f"种子 {ziwei['sample']['seed']}），默认规则（钟表时间，闰月后半月按下月；iztro 设 fix_leap=True）。",
        '',
        '| 对照项 | 核对数 | 不一致 | 一致率 |',
        '| --- | ---: | ---: | ---: |',
        row('农历日期', total(zr, 'lunar')),
        row('命宫', total(zr, 'ming')),
        row('身宫', total(zr, 'shen')),
        row('五行局', total(zr, 'bureau')),
        row('十四主星落宫', total(zr, 'stars')),
        row('生年四化', total(zr, 'transformations')),
        row(f"其余 {ziwei['other_stars']['star_count']} 颗辅星、杂曜落宫（iztro）", total(zr, 'other_stars')),
        row('长生、博士、岁前、将前十二神（iztro）', total(zr, 'cycles')),
        '',
        '前六项对照 iztro-py；辅星、杂曜与十二神对照 iztro 原版，每个出生的全部星曜或全部十二神都相同才算一致'
        + ('。' if not ziwei['other_stars']['mismatching_stars'] else
           '；不一致的星：' + '、'.join(f'{k} {v}' for k, v in ziwei['other_stars']['mismatching_stars'].items()) + '。'),
        '',
        f"23:00–23:59 出生另抽 {ziwei['late_zi']['births']} 个。玄枢默认 23:00 不换日，用当天的农历日，"
        f"与 iztro 的“早子时”（时辰序号 0）对照，十四主星一致 {agree(ziwei['late_zi']['default_vs_iztro_same_day_zi'], 'stars')}；"
        f"选择「23:00 换日」后按次日的农历日期排，与 iztro 的“晚子时”（序号 12）对照，{late_agreement(ziwei['late_zi']['rollover_vs_iztro_late_zi'])}。"
        f"另有 {ziwei['late_zi']['iztro_keeps_month']['births']} 个出生在月末最后一天或闰月后半月：iztro 晚子时只把日数加一、"
        '不进月，也不按闰月后半月进位（源码 `fix_lunar_month_index`、`fix_lunar_day_index`），玄枢按次日完整的农历日期排，'
        f"这些出生里命宫不同的有 {ziwei['late_zi']['iztro_keeps_month']['comparison']['ming']['mismatches']} 个。"
        '晚子时算当日还是次日是流派规则的不同，两种规则玄枢都支持。',
        '',
        '## 紫微运限对照 iztro',
        '',
        f"随机抽取 {horoscope['sample']['pairs']:,} 组出生时刻与目标时刻（出生 {horoscope['sample']['birth_years']}，"
        f"目标在出生后 100 年内且不晚于 2099 年，时刻 {horoscope['sample']['hours']}，种子 {horoscope['sample']['seed']}），"
        '逐层比较运限命宫所在地支、运限天干和四化星（对照 iztro-py），以及各层的流曜和流年十二神（对照 iztro 原版，iztro-py 没有流曜）。'
        '样本都选了性别（大限、小限的顺逆取决于性别）；未到第一个大限的童限两边都不列，所以大限流曜的核对数少一些。',
        '',
        '| 运限层 | 核对数 | 不一致 | 一致率 |',
        '| --- | ---: | ---: | ---: |',
    ] + [row(label, total(horoscope['results'], key)) for key, label in HOROSCOPE_LABELS.items()] + [
        row(label, total(horoscope['results'], key)) for key, label in FLOW_LABELS.items()] + [
        '',
        horoscope_note(horoscope),
        '',
        '## 不一致的原因',
        '',
    ]
    lines += result['findings'] or ['- 没有发现不一致。']
    lines += ['', '## 评测带来的修正', ''] + ['- ' + fix['text'] for fix in FIXES]
    lines += ['', '## 重跑', '', '```', 'pip install -r requirements.txt -r docs/evals/requirements.txt',
              'npm install --prefix docs/evals', 'python scripts/eval_crosscheck.py', '```', '']
    path.write_text('\n'.join(lines), encoding='utf-8')


def findings(result: dict) -> list[str]:
    """Plain-language causes for the mismatches, filled in from the data."""
    out = []
    terms = result['solar_terms']
    observed, forecast = terms['sxtwl'][f'through_{LAST_OBSERVED_DELTA_T_YEAR}'], terms['sxtwl'][f'after_{LAST_OBSERVED_DELTA_T_YEAR}']
    if observed.get('count'):
        out.append(f"- 节气时刻：{LAST_OBSERVED_DELTA_T_YEAR} 年以前与寿星天文历最大相差 {observed['max_abs_seconds']} 秒。"
                   f"之后最大相差 {forecast.get('max_abs_seconds', 0)} 秒，来自两边对未来 ΔT 的预报不同"
                   f"（Swiss Ephemeris 预报 2026 年 ΔT 为 {result['delta_t_seconds'].get('2026')} 秒）。"
                   '只有出生或事件离交节只差这么几分钟时，月柱才可能因此不同。')
    for run in result['days']['lunar_month_differences']:
        year = int(run['first'][:4])
        span = f"{run['first']} 至 {run['last']}（{run['days']} 天）"
        moon = f"朔在 {run['new_moon_calendar_time'].replace('T', ' ')}，离午夜 {run['minutes_from_midnight']} 分钟"
        who = '、'.join(run['references'])
        if year > LAST_OBSERVED_DELTA_T_YEAR:
            out.append(f'- {span}：{moon}，{who} 与玄枢差一天。离午夜太近，要看 ΔT 预报，现在无法确定哪边对。')
        elif run['references'] == ['lunardate'] and run['minutes_from_midnight'] < 15:
            out.append(f'- {span}：{moon}。只有 lunardate 不同，sxtwl 和 lunar_python 都与玄枢一致。'
                       '旧算法容易把这样的朔算到午夜另一侧（Aslaksen 记载 1978 年以前香港、台湾历书仍沿用 1908 年的旧历法）。')
        elif run['references'] == ['lunardate']:
            out.append(f'- {span}：{moon}，按天象这一天就是初一。只有 lunardate 不同，sxtwl 和 lunar_python 都与玄枢一致，'
                       '是这份表的月份长度与天象不符。')
        else:
            out.append(f'- {span}：{moon}，{who} 与玄枢不同，尚未解释。')
    month = result['days']['pillars_at_noon'].get('lunar_python.month', {})
    for example in month.get('examples', []):
        if int(example['moment'][:4]) > LAST_OBSERVED_DELTA_T_YEAR:
            out.append(f"- {example['moment'][:10]} 正午的月柱（玄枢 {example['xuanshu']}，lunar_python {example['reference']}）："
                       '这天正午前后交节，两边的 ΔT 预报差一两分钟。')
    for item in result['solar_terms']['china_date_differs_from_sxtwl']:
        out.append(f"- {item['year']} 年{item['term']}：玄枢 {item['xuanshu_china'][:19].replace('T', ' ')}，"
                   f"sxtwl {item['sxtwl_china'][:19].replace('T', ' ')}，落在午夜两侧，同样是 ΔT 预报不同。")
    return out


def _cause(run: dict) -> str:
    if int(run['first'][:4]) > LAST_OBSERVED_DELTA_T_YEAR:
        return 'forecast'
    if run['references'] == ['lunardate']:
        return 'old_almanac' if run['minutes_from_midnight'] < 15 else 'table'
    return 'unexplained'


def summary(result: dict) -> dict:
    """Compact, label-free summary for the web page (static/crosscheck-summary.json)."""
    days, jie, ziwei = result['days'], result['jie_boundaries']['results'], result['ziwei']
    observed, forecast = f'through_{LAST_OBSERVED_DELTA_T_YEAR}', f'after_{LAST_OBSERVED_DELTA_T_YEAR}'

    def counts(item):
        return {'checked': item['checked'], 'mismatches': item['mismatches']}

    def instants(section, reference):
        return [{'field': section, 'reference': reference, 'period': period,
                 **{k: stats[k] for k in ('count', 'mean_abs_seconds', 'p95_abs_seconds', 'max_abs_seconds')}}
                for period, stats in ((f"{result['years'][0]}–{LAST_OBSERVED_DELTA_T_YEAR}", result[section][reference][observed]),
                                      (f"{LAST_OBSERVED_DELTA_T_YEAR + 1}–{result['years'][1]}", result[section][reference][forecast]))]
    late = ziwei['late_zi']
    return {
        'generated': result['generated'], 'years': result['years'], 'references': result['references'],
        'delta_t_2026': result['delta_t_seconds'].get('2026'),
        'daily': [{'field': 'lunar', 'reference': key, **counts(days['lunar_dates'][key])} for key in ('sxtwl', 'lunar_python', 'lunardate')]
        + [{'field': 'day', 'reference': 'sxtwl', **counts(days['pillars_at_noon']['sxtwl.day'])}]
        + [{'field': name, 'reference': 'lunar_python', **counts(days['pillars_at_noon']['lunar_python.' + name])} for name in ('year', 'month', 'day', 'hour')]
        + [{'field': 'jie_month', 'reference': 'lunar_python', **counts(jie['month'])},
           {'field': 'jie_year', 'reference': 'lunar_python', **counts(jie['year'])}],
        'instants': instants('solar_terms', 'sxtwl') + instants('solar_terms', 'ephem') + instants('moon_phases', 'ephem'),
        'ziwei': {'births': ziwei['sample']['births'],
                  'rows': [{'field': key, 'reference': 'iztro_py', **counts(ziwei['results'][key])}
                           for key in ('lunar', 'ming', 'shen', 'bureau', 'stars', 'transformations')]
                  + [{'field': key, 'reference': 'iztro', **counts(ziwei['results'][key])} for key in ('other_stars', 'cycles')],
                  'other_star_count': ziwei['other_stars']['star_count'],
                  'late_zi_births': late['births'],
                  'late_zi_same_day': counts(late['default_vs_iztro_same_day_zi']['stars']),
                  'late_zi_next_day': counts(late['rollover_vs_iztro_late_zi']['stars']),
                  'late_zi_month_kept': late['iztro_keeps_month']['births']},
        'horoscope': {'pairs': result['horoscope']['sample']['pairs'],
                      'rows': [{'field': key, **counts(result['horoscope']['results'][key])} for key in HOROSCOPE_LAYERS],
                      'flow_rows': [{'field': key, **counts(result['horoscope']['results'][key])} for key in FLOW_LABELS],
                      'calendar_differs': sum(result['horoscope']['lunar_python_calendar_differs'].values()),
                      'unexplained': sum(item['mismatches'] for item in result['horoscope']['results'].values())
                      - sum(result['horoscope']['lunar_python_calendar_differs'].values())},
        'differences': [{'first': run['first'], 'last': run['last'], 'references': run['references'],
                         'minutes_from_midnight': run['minutes_from_midnight'], 'cause': _cause(run)}
                        for run in days['lunar_month_differences']],
        'fixes': [{'months': fix.get('months', []), 'cause': fix['cause']} for fix in FIXES],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--quick', action='store_true', help='every tenth year and a smaller Zi Wei sample')
    parser.add_argument('--output', type=Path, help='default: docs/evals, or build/evals-quick with --quick')
    args = parser.parse_args()
    committed = ROOT / 'docs' / 'evals'
    output = args.output or (ROOT / 'build' / 'evals-quick' if args.quick else committed)
    years = list(range(1901, 2100, 10)) + [2099] if args.quick else list(range(1901, 2100))
    result = {
        'system': 'xuanshu-crosscheck', 'generated': date.today().isoformat(), 'quick': args.quick,
        'years': [1901, 2099], 'references': references(), 'delta_t_seconds': delta_t_table(),
    }
    print('days…', flush=True)
    result['days'] = compare_days(years)
    print('jie boundaries…', flush=True)
    result['jie_boundaries'] = compare_jie_boundaries(years)
    print('solar terms…', flush=True)
    result['solar_terms'] = compare_solar_terms(years)
    print('moon phases…', flush=True)
    result['moon_phases'] = compare_moon_phases(years)
    print('zi wei…', flush=True)
    result['ziwei'] = compare_ziwei(300 if args.quick else 3000, 50 if args.quick else 300)
    print('zi wei periods…', flush=True)
    result['horoscope'] = compare_horoscope(100 if args.quick else 1000)
    result['findings'] = findings(result)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'crosscheck.json').write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    write_markdown(result, output / 'README.md')
    # The page summary must stay in step with the committed report, so only a full run into docs/evals writes it.
    if not args.quick and output.resolve() == committed.resolve():
        (ROOT / 'static' / 'crosscheck-summary.json').write_text(
            json.dumps(summary(result), ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print('wrote', output / 'crosscheck.json')


if __name__ == '__main__':
    main()
