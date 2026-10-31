"""Luck and year pillars read against the natal chart."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.advanced import DayunRequest, dayun_sequence
from app.engines import BirthInput, branch_labels, calculate_bazi, natal_interactions
from app.main import app
from app.mcp import process_rpc

BIRTH = {'birth_datetime': '2000-08-16T04:00', 'timezone': 'Asia/Shanghai', 'gender': 'female'}  # 庚辰 甲申 丙午 庚寅


def test_punishment_belongs_to_the_pair_in_either_order():
    assert branch_labels('巳', '寅') == branch_labels('寅', '巳') == ['六害', '相刑']
    assert branch_labels('戌', '丑') == ['相刑'] and branch_labels('午', '午') == ['同支', '相刑']
    # 己巳 丙寅: the year branch comes first, which the old ordered lookup missed.
    b = calculate_bazi(BirthInput(birth_datetime='1989-02-10T10:00', timezone='Asia/Shanghai'))
    assert [r['labels'] for r in b['branch_relations'] if (r['a'], r['b']) == ('year', 'month')] == [['六害', '相刑']]


def test_luck_pillar_against_the_natal_chart():
    natal = calculate_bazi(BirthInput(**BIRTH))
    xu = natal_interactions('丙戌', natal)
    assert (xu['ten_god_of_stem'], xu['na_yin'], xu['growth_stage'], xu['self_stage']) == ('比肩', '屋上土', '墓', '墓')
    assert xu['branch_relations'] == [{'pillar': 'year', 'branch': '辰', 'labels': ['六冲']}]
    assert xu['branch_groups'] == [{'kind': '三合', 'branches': '寅午戌', 'element': '火', 'pillars': ['day', 'hour']}]
    si = natal_interactions('辛巳', natal)
    assert si['stem_relations'] == [{'pillar': 'day', 'stem': '丙', 'labels': ['丙辛合水']}]
    assert [(r['pillar'], r['labels']) for r in si['branch_relations']] == [('month', ['六合', '相刑']), ('hour', ['六害', '相刑'])]
    # The stems hidden in the luck pillar's branch, main qi first, each with its ten god against the day master 丙.
    assert [(h['stem'], h['element'], h['ten_god']) for h in si['hidden_stems']] == [('丙', '火', '比肩'), ('戊', '土', '食神'), ('庚', '金', '偏财')]
    # 卯 is in the day pillar's void (丙午 belongs to the 甲辰 decade: 寅卯).
    assert natal_interactions('己卯', natal)['void_of'] == ['day']
    # Without the hour, nothing is read against the placeholder hour pillar.
    assert [r['pillar'] for r in natal_interactions('辛巳', natal, ('year', 'month', 'day'))['branch_relations']] == ['month']


def test_dayun_periods_and_years():
    plain = dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=3))
    assert [p['pillar'] for p in plain['periods']] == ['癸未', '壬午', '辛巳'] and 'years' not in plain['periods'][0]
    assert plain['periods'][0]['natal_interactions']['branch_relations'] == [{'pillar': 'day', 'branch': '午', 'labels': ['六合']}]
    full = dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=3, include_years=True, hour_unknown=True))
    years = full['periods'][2]['years']
    assert [y['year'] for y in years] == list(range(2023, 2033)) and years[3]['pillar'] == '丙午'
    assert years[3]['branch_relations'] == [{'pillar': 'day', 'branch': '午', 'labels': ['同支', '相刑']}]
    assert all(r['pillar'] != 'hour' for p in full['periods'] for item in [p['natal_interactions'], *p['years']] for r in item['branch_relations'])
    # The 辛巳 period begins in July 2023: 2023 is its first year and 2033, when 庚辰 begins, is the next period's.
    assert full['periods'][2]['approx_start_local'].startswith('2023-07') and full['periods'][2]['approx_end_local_exclusive'].startswith('2033-07')
    listed = [y['year'] for p in full['periods'] for y in p['years']]
    assert listed == list(range(2003, 2033))
    # The page labels each period from its start year to the year before the next start: the same years.
    assert all([y['year'] for y in p['years']] == list(range(int(p['approx_start_local'][:4]), int(p['approx_end_local_exclusive'][:4])))
               for p in full['periods'])


def test_rest_and_mcp_agree():
    args = {'birth': BIRTH, 'periods': 2, 'include_years': True, 'month_year': 2026, 'hour_date': '2026-10-30'}
    rest = TestClient(app).post('/api/dayun', json=args).json()
    reply = process_rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'bazi_dayun', 'arguments': args}})
    mcp = reply['result']['structuredContent']
    assert rest['periods'] == mcp['periods'] and len(rest['periods'][1]['years']) == 10
    assert rest['flow_months'] == mcp['flow_months'] and len(mcp['flow_months']['months']) == 12
    assert rest['flow_hours'] == mcp['flow_hours'] and len(mcp['flow_hours']['hours']) == 13


def test_month_pillars_of_a_year():
    reply = dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=1, month_year=2026))
    flow = reply['flow_months']
    months = flow['months']
    assert (flow['year'], flow['year_pillar']) == (2026, '丙午') and [m['month'] for m in months] == list(range(1, 13))
    # 丙辛之岁寻庚上: the 寅 month of a 丙 year is 庚寅, and the months run on through the cycle to 辛丑.
    assert [m['pillar'] for m in months] == ['庚寅', '辛卯', '壬辰', '癸巳', '甲午', '乙未', '丙申', '丁酉', '戊戌', '己亥', '庚子', '辛丑']
    assert [m['jie'] for m in months] == ['立春', '惊蛰', '清明', '立夏', '芒种', '小暑', '立秋', '白露', '寒露', '立冬', '大雪', '小寒']
    # Each month ends where the next begins, at the exact jie, and the twelfth ends at the next 立春.
    assert all(a['end_local_exclusive'] == b['start_local'] for a, b in zip(months, months[1:]))
    assert months[0]['start_local'].startswith('2026-02-04') and months[-1]['end_local_exclusive'].startswith('2027-02-04')
    # A chart cast two days into each month has that month pillar.
    for m in months:
        inside = (datetime.fromisoformat(m['start_local']) + timedelta(days=2)).replace(tzinfo=None).isoformat(timespec='minutes')
        assert calculate_bazi(BirthInput(birth_datetime=inside, timezone='Asia/Shanghai'))['pillars']['month']['text'] == m['pillar']
    # Read against the natal chart like the years, without the hidden stems; their stars have rules too.
    assert months[4]['branch_relations'] == [{'pillar': 'day', 'branch': '午', 'labels': ['同支', '相刑']}] and 'hidden_stems' not in months[0]
    assert {s['name'] for m in months for s in m['shensha']} <= {r['name'] for r in reply['shensha_rules']}
    assert 'flow_months' not in dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=1))


def test_month_stems_follow_the_year_stem():
    # 甲己之年丙作首, 乙庚之岁戊为头, 丙辛之岁寻庚上, 丁壬壬寅顺水流, 若问戊癸何处起, 甲寅之上好追求.
    firsts = {year: dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=1, month_year=year))['flow_months']['months'][0]['pillar']
              for year in (2024, 2025, 2026, 2027, 2028, 2029, 2030)}
    assert firsts == {2024: '丙寅', 2025: '戊寅', 2026: '庚寅', 2027: '壬寅', 2028: '甲寅', 2029: '丙寅', 2030: '戊寅'}
    # The last supported year still ends at the following 立春.
    last = dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=1, month_year=2099))['flow_months']['months']
    assert last[-1]['end_local_exclusive'].startswith('2100-02-0')
    assert TestClient(app).post('/api/dayun', json={'birth': BIRTH, 'month_year': 1900}).status_code == 422


def test_luck_page_years_open_their_months():
    script = open('static/app.js', encoding='utf-8').read()
    # Each year of the picked decade is a button that fetches and toggles its month pillars below the table.
    assert "open.setAttribute('aria-expanded'" in script and 'month_year: year' in script and "panel.id = 'dayun-months'" in script
    # Years past the supported range (the decades run on beyond 2099) stay plain; the request is matched by identity,
    # so a reply for an earlier year or chart is dropped, and a failure belongs to its chart and year.
    assert 'const FLOW_MONTH_LAST_YEAR = 2099;' in script and 'if (y.year > FLOW_MONTH_LAST_YEAR) first.textContent' in script
    assert 'if (dayunMonthsLoad === load && dayunKey === key)' in script and "dayunMonthsError.key === dayunKey && inDecade(dayunMonthsError.year)" in script
    assert 'if (dayunDaysLoad !== load || dayunKey !== key) return;' in script and 'if (same(dayunDaysLoad)) return;' in script
    # Opening another year drops the days' error and request; a failure names its month; nothing is expanded during a load.
    assert 'dayunMonthsError = dayunDaysError = dayunDaysLoad = dayunHoursError = dayunHoursLoad = null;' in script and "m.months[failed.month - 1].jie, ' ', '流日计算失败：'" in script
    assert 'const expanded = !loading && !!days && days.month === month.month;' in script and "range.dataset.noI18n = '';" in script
    # A day opens its hours the same way; one card holds the Tab stop; 展开今天 opens the chain down to today.
    assert "hour_date: date" in script and "panel.id = 'dayun-hours'" in script and 'if (same(dayunHoursLoad)) return;' in script
    assert "open.tabIndex = day.date === stop ? 0 : -1;" in script and "jump.id = 'dayun-today'" in script
    assert "ask({month_year: load.year, day_month: month.month, hour_date: today})" in script
    # Today and the hour now are read on the birth zone's clock; the year and month by today's date there.
    assert "JSON.parse(dayunKey).birth.timezone" in script and "today >= data.flow_months.months[0].start_local.slice(0, 10)" in script
    assert '      dayunPick = decade.sequence;' in script and 'event.altKey || event.ctrlKey || event.metaKey' in script
    # A month's days export as an iCalendar file made in the page, lines folded by octets, no birth data, tagged per chart.
    assert "save.id = 'dayun-days-ics'" in script and "'DTSTART;VALUE=DATE:' + compact(e.start)" in script and 'size(part + ch) > (parts.length ? 74 : 75)' in script
    assert "'@xuanshu.local', 'SEQUENCE:' + sequence" in script and 'chartTag(dayunKey)' not in script
    # A year's months export the same way, each from its jie day up to the day before the next jie.
    assert "save.id = 'dayun-months-ics'" in script and "start: from.slice(0, 10), end: to.slice(0, 10)," in script
    # Day UIDs keep the format files imported before carry; month UIDs are keyed on the flow year and month.
    assert "d.pillar, 'day', d.days.map(day => {" in script and "m.pillar, 'month', m.months.map((month, i) => {" in script
    assert "'UID:flow-' + kind + '-' + (e.key || compact(e.start)) + '-' + tag" in script and "key: m.year + String(month.month).padStart(2, '0')" in script
    # The two buttons have their own names; the jie moments carry the birth zone's UTC offset.
    assert "save.setAttribute('aria-label', '导出流日日历');" in script and "save.setAttribute('aria-label', '导出流月日历');" in script
    # The tag is made from the settled natal pillars the notes show, never from the request holding the birth minute.
    assert "const tag = chartTag(['year', 'month', 'day', 'hour'].map(k => o.open.has(k) ? '' : current.bazi.pillars[k].text).join(' '));" in script
    assert "calendarWords('神煞') + ' ' + calendarWords('随时辰而定')" in script and 'calendarWords(TEXT_FOOTER[0])' in script
    # Today's flow year before the first decade says so; 2100 days open no hours; the day's relations head its hours.
    assert "if (!decade) throw new Error('今天所在的流年早于第一步大运" in script and "dayunMonthsError = {key, year: start, text:" in script
    assert "const closed = day.date > FLOW_HOUR_LAST_DATE;" in script and "append(item, closed ? 'div' : 'button'" in script and "if (!closed) open.addEventListener('click'" in script
    assert "texts(append(panel, 'p', 'field-help dy-hour-day'), '当日', '：', natalText(settledInteractions(day, o)))" in script
    assert 'const expanded = !loading && !!hours && hours.date === day.date;' in script and "failed.date.slice(5).replace('-', '/'), ' ', '流时计算失败：'" in script
    assert '.dy-year-toggle[aria-expanded="true"]' in open('static/style.css', encoding='utf-8').read()
    # At phone width the four tables stack each row; the roles keep them tables to screen readers, a cell label only
    # where a stacked cell needs it, hidden from them.
    style = open('static/style.css', encoding='utf-8').read()
    # The four luck tables, the 神煞 rules, today's pillars and the year's four transformations.
    assert script.count('  stackTable(table);') == 7 and "table.querySelectorAll('td').forEach(cell => cell.setAttribute('role', 'cell'));" in script
    assert "label.setAttribute('aria-hidden', 'true');" in script and "stackLabel(append(tr, 'td'), '虚龄')" in script and "stackLabel(append(tr,'td'),'起运')" in script
    # A ten god or growth stage spelled out in letters keeps about two lines' width in the four luck tables, so the
    # stars wrap instead, and a table that then overflows stacks; in Chinese and Japanese the two characters need none.
    assert script.count("'dy-short'") == 8
    assert 'html:not(:lang(zh),:lang(ja),:lang(ko)) .dy-stack:not(.is-stacked) td.dy-short{min-width:11.5em}' in style
    # They stack only when their columns overflow the wrapper, measured as a table at each redraw, resize and translation.
    assert "table.classList.toggle('is-stacked', narrow || table.offsetWidth > table.parentElement.clientWidth + 1);" in script
    assert "cell.getBoundingClientRect().width < parseFloat(table.dataset.fitEm || '7.5') * parseFloat(getComputedStyle(cell).fontSize)" in script
    assert '  renderView();\n  fitStacks();' in script and 'requestAnimationFrame(() => {fitStacks(); markScrollAreas();});' in script
    assert '.dy-stack.is-stacked thead{position:absolute;' in style and '.dy-stack-label{display:none}' in style
    # Print keeps the year and jie toggles, so those cells are not blank on paper.
    assert ':not(.dy-decade):not(.dy-year-toggle){display:none!important}' in style
    # Each month in turn opens its days as cards.
    assert 'day_month: month' in script and "box.id = 'dayun-days'" in script and "list.id = 'dayun-day-grid'" in script


def test_day_pillars_of_a_month():
    reply = dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=1, month_year=2026, day_month=9))
    months = reply['flow_months']['months']
    days = months[8]['days']
    # 寒露 2026 falls on 10-08 and 立冬 on 11-07: the days from the one to the day before the other.
    assert (days[0]['date'], days[-1]['date'], len(days)) == ('2026-10-08', '2026-11-06', 30)
    assert days[0]['jie_day'] and not any(d['jie_day'] for d in days[1:]) and all('days' not in m for i, m in enumerate(months) if i != 8)
    # The day pillar of each date is the one a chart cast at its noon has.
    for d in days[::7] + days[-1:]:
        assert calculate_bazi(BirthInput(birth_datetime=d['date'] + 'T12:00', timezone='Asia/Shanghai'))['pillars']['day']['text'] == d['pillar']
    assert days[2]['pillar'] == '丁巳' and [(r['pillar'], r['labels']) for r in days[2]['branch_relations']] == [('month', ['六合', '相刑']), ('hour', ['六害', '相刑'])]
    assert 'hidden_stems' not in days[0] and {s['name'] for d in days for s in d['shensha']} <= {r['name'] for r in reply['shensha_rules']}
    # The twelfth month runs into the next year; a day needs a month of a year.
    late = dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=1, month_year=2099, day_month=12))['flow_months']['months'][11]['days']
    assert late[0]['date'].startswith('2100-01-') and late[-1]['date'].startswith('2100-02-0')
    # Samoa skipped 30 December 2011: the date is not listed.
    apia = BirthInput(**{**BIRTH, 'timezone': 'Pacific/Apia'})
    skipped = [d['date'] for d in dayun_sequence(DayunRequest(birth=apia, periods=1, month_year=2011, day_month=11))['flow_months']['months'][10]['days']]
    assert '2011-12-29' in skipped and '2011-12-31' in skipped and '2011-12-30' not in skipped
    client = TestClient(app)
    assert client.post('/api/dayun', json={'birth': BIRTH, 'day_month': 3}).status_code == 422
    assert client.post('/api/dayun', json={'birth': BIRTH, 'month_year': 2026, 'day_month': 13}).status_code == 422


def test_hour_pillars_of_a_day():
    reply = dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH), periods=1, hour_date='2026-10-30'))
    hours = reply['flow_hours']
    assert (hours['date'], hours['day_pillar'], hours['day_boundary']) == ('2026-10-30', '丁丑', '00:00')
    rows = hours['hours']
    # Zi at both ends of the civil day, a branch every two hours between them.
    assert [(h['start'], h['end']) for h in rows[:2] + rows[-2:]] == [('00:00', '01:00'), ('01:00', '03:00'), ('21:00', '23:00'), ('23:00', '24:00')]
    assert ''.join(h['branch'] for h in rows) == '子丑寅卯辰巳午未申酉戌亥子'
    # 丁壬庚子居: a 丁 day's hours start from 庚子; each matches a chart cast inside that hour.
    assert rows[0]['pillar'] == '庚子' and rows[6]['pillar'] == '丙午' and rows[12]['pillar'] == '庚子'
    for h in rows:
        moment = '2026-10-30T' + ('23:30' if h['start'] == '23:00' else h['start'][:2] + ':30')
        assert calculate_bazi(BirthInput(birth_datetime=moment, timezone='Asia/Shanghai'))['pillars']['hour']['text'] == h['pillar']
    assert 'hidden_stems' not in rows[0] and {s['name'] for h in rows for s in h['shensha']} <= {r['name'] for r in reply['shensha_rules']}
    # With the 23:00 day change the last Zi already belongs to the next day: 戊寅, whose hours start from 壬子.
    late = dayun_sequence(DayunRequest(birth=BirthInput(**BIRTH, late_zi_day_rollover=True), periods=1, hour_date='2026-10-30'))['flow_hours']
    assert late['day_boundary'] == '23:00' and (late['hours'][0]['pillar'], late['hours'][-1]['pillar'], late['hours'][-1]['day_pillar']) == ('庚子', '壬子', '戊寅')
    # A double-hour the clock jumps over is not listed: Havana went from 00:00 to 01:00 on 2026-03-08; Samoa skipped a day.
    havana = dayun_sequence(DayunRequest(birth=BirthInput(**{**BIRTH, 'timezone': 'America/Havana'}), periods=1, hour_date='2026-03-08'))['flow_hours']['hours']
    assert len(havana) == 12 and havana[0]['start'] == '01:00'
    assert dayun_sequence(DayunRequest(birth=BirthInput(**{**BIRTH, 'timezone': 'Pacific/Apia'}), periods=1, hour_date='2011-12-30'))['flow_hours']['hours'] == []
    new_york = dayun_sequence(DayunRequest(birth=BirthInput(**{**BIRTH, 'timezone': 'America/New_York'}), periods=1, hour_date='2026-03-08'))['flow_hours']['hours']
    assert len(new_york) == 13 and new_york[1]['branch'] == '丑'  # 01:00-02:00 still happened
    client = TestClient(app)
    for bad in ('1900-12-31', '2100-01-01', '2026-02-30'):
        assert client.post('/api/dayun', json={'birth': BIRTH, 'hour_date': bad}).status_code == 422
