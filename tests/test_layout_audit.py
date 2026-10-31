"""Layout fixes from the interface audit: things that overlapped, were cut off or fell back to the wrong font."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'static/style.css').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')
HTML = (ROOT / 'static/index.html').read_text(encoding='utf-8')


def test_sidebar_button_stays_on_the_panel_edge():
    assert '<div class="run-bar">' in HTML
    assert '@media(min-width:861px){.run-bar{position:sticky;bottom:-22px;' in CSS


def test_day_pillar_badge_and_english_headings():
    # The badge sits on the pillar's top edge instead of over its heading; English headings are not letter-spaced.
    assert re.search(r'\.pillar-badge\{position:absolute;top:0;left:50%;transform:translate\(-50%,-50%\)', CSS)
    assert ':lang(en) .pillar-head{letter-spacing:.02em}' in CSS
    # A narrow pillar puts the void mark under its branch.
    assert '.pillar{container:pillar / inline-size}' in CSS and '@container pillar (max-width:240px){:lang(en) .void-mark' in CSS


def test_latin_text_uses_the_sans_face():
    assert '--sans:' in CSS and 'font:14px/1.65 var(--sans)' in CSS
    assert '.void-mark{position:absolute;top:2px;right:2px;font-family:var(--sans);' in CSS
    rule = re.search(r':lang\(en\) :is\(([^)]*(?:\([^)]*\)[^)]*)*)\)\{font-family:var\(--sans\)\}', CSS)
    assert rule and all(s in rule.group(1) for s in ('.wuxing-detail h5 b', '.element-bar>b', '.transform-star', '.cal-title', '.share-text'))
    # The share card's Zi Wei rows follow the interface language too.
    assert "const rowFont = document.documentElement.lang.startsWith('en') ? sans : serif;" in APP
    # The five-phase bars share their columns, so a long English name widens the label for every row.
    assert '.element-bar{display:grid;grid-column:1 / -1;grid-template-columns:subgrid;' in CSS


def test_dayun_axis_label_and_current_dot():
    assert "append(axis, 'small', 'dy-before-label', '起运前');" in APP
    assert '.dy-before small' not in CSS and '.dy-before-label{position:absolute;left:0;bottom:3px;' in CSS
    assert ".dy-decade.is-now::after{content:'';position:absolute;top:5px;right:5px;" in CSS
    assert '.dy-band-age::after' not in CSS


def test_officers_today_and_long_term_names():
    assert '.of-day.is-today .of-gz{margin-top:18px}' in CSS
    assert '.of-jie-name{display:block;overflow-wrap:anywhere}' in CSS


def test_install_commands_and_dialog_tables_stay_inside():
    assert '.pf-steps>li{min-width:0}' in CSS and '.pf-command code{flex:1 1 0;min-width:0;' in CSS
    assert ".pf-command code';" in APP
    # The cross-check dialog marks its scrolling tables; the scrollbar gutter takes the backdrop's tone.
    draw = APP[APP.index('async function openCrosscheck()'):]
    assert 'requestAnimationFrame(markScrollAreas);' in draw[:draw.index('if (crosscheckData) draw(')]
    assert 'html:has(dialog:modal){overflow:hidden;scrollbar-gutter:stable;background:color-mix(' in CSS


def test_tab_headings_keep_to_their_first_tool():
    headings = re.findall(r'<span class="tab-group"', HTML)
    leads = re.findall(r'<span class="tab-lead"><span class="tab-group" aria-hidden="true">[^<]+</span><button class="tab', HTML)
    assert headings and len(leads) == len(headings)
    assert "document.querySelectorAll('#workspace-tabs :is(.tab-group, .tab)')" in APP and 'nextElementSibling' not in APP[:3000]


def test_header_search_box_and_footer_docs_link():
    assert '@media(max-width:1240px){.ui-lang>span{display:none}}' in CSS
    assert '@media(max-width:1080px){.brand small{display:none}}' in CSS
    assert '.tool-search-box{position:relative;flex:1;min-width:min(100%,310px);' in CSS
    # The header's API link is hidden on a phone, so the footer carries one there.
    assert '<a class="footer-link footer-docs" href="/docs" target="_blank" rel="noopener">API 文档 ↗</a>' in HTML
    assert '.footer-docs{display:inline}' in CSS


def test_taiji_emblem_is_drawn_and_centre_text_sits_on_plates():
    assert "'☯'" not in APP and '☯' not in HTML
    assert APP.count('taijiMark(') == 3 and HTML.count('<svg class="taiji"') == 1
    assert '.board-center.see-through>:not(.center-symbol){padding:0 6px;border-radius:4px;background:var(--panel)}' in CSS


def test_small_labels_are_at_least_eleven_pixels():
    # Badges and notes that stand on their own (the year marks, this chart, duty star and door, the UTC start, the
    # lunar entry hint, parameter types, the jie note in the officers month) are 11px; the phone calendar keeps its own.
    for rule in ('.ay-facts small.ay-now{margin-left:6px;font-size:11px;', 'small.yt-now{font-size:11px;', '.bt-utc{font-size:11px;',
                 '.bt-pillar small{font-size:11px;', '.qh-tag{font-size:11px;', '.qh-duty{font-size:11px;', '.ic-tag{font-size:11px;',
                 '.form-section>summary small{color:var(--muted);font-size:11px;', '.ag-param small{font-size:11px;',
                 '.of-jie{display:block;margin-top:2px;font-size:11px;'):
        assert rule in CSS, rule
    assert 'html[lang=en] .qh-name,html[lang=en] .qh-bureau,html[lang=en] .qh-duty{white-space:normal;text-align:center;line-height:1.2}' in CSS
    assert 'html[lang=en] .ic-name{white-space:normal;' in CSS
    # On a 360px phone today's mark keeps inside its day.
    assert '.of-date{top:3px;left:4px;font-size:10px}.of-day.is-today .of-date{left:2px;padding:0 3px}' in CSS


def test_more_small_labels_and_narrow_cells():
    # The rest of the labels standing on their own are 11px too: the palette kind, the pillar search axis, the deep
    # review pillars and file hashes, the group pillars, the report step numbers, the API required mark and the
    # date scan notes; the dense timeline and date picker cells keep theirs.
    for rule in ('.palette-kind{flex:none;padding:1px 6px;border:1px solid var(--border);border-radius:999px;font-size:11px;',
                 'width:18px;height:18px;border-radius:999px;background:var(--panel3);font-size:11px;', '.ps-mark small{font-size:11px;',
                 '.ps-now small{position:absolute;top:15px;left:50%;transform:translateX(-50%);font-size:11px;',
                 '.ev-self{border-left:1px solid currentColor;padding-left:4px;margin-left:2px;font-size:11px}', '.ev-pillar small{font-size:11px;',
                 '.ev-hash{font-size:11px;', '.group-pillar small{font-size:11px;', '.api-req{display:inline-block;margin-left:6px;font-size:11px;',
                 '.ds-reason{display:block;margin-top:3px;font-size:11px;', '.ds-hours{display:flex;flex-direction:column;margin-top:3px;font-size:11px;'):
        assert rule in CSS, rule
    assert 'html[lang="en"] .ds-reason{' not in CSS
    # A date scan day too narrow for its hour and bureau puts the bureau on the next line instead of over the next day.
    assert '.ds-hour-bureau{display:inline-block}' in CSS and '.ds-hour-bureau{white-space:nowrap}' not in CSS
    assert "const line = texts(append(hours, 'span'), h.local_time, ' '); append(line, 'span', 'ds-hour-bureau', chartLine(h));" in APP
    # Two group cards a row on a phone: pillar names in letters take two pillars a row, and no pillar overflows.
    assert '.group-pillars{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px}' in CSS
    assert '@container group-member (max-width:156px){html:not(:lang(zh),:lang(ja),:lang(ko)) .group-pillars{grid-template-columns:repeat(2,minmax(0,1fr))}}' in CSS


def test_palace_stars_and_rule_cards_keep_inside():
    # In letters a main star with its brightness and badge (Tian Tong High 权) outgrows a 106px palace with the side
    # panel back: the brightness and badges take the next line, the name kept whole; in Chinese and Japanese the star
    # stays on one line. A minor star moves to the next line whole, and one longer than the line wraps inside it.
    assert '.star-primary .star{white-space:nowrap}' in CSS
    assert 'html:not(:lang(zh),:lang(ja),:lang(ko)) .star-primary .star{white-space:normal}' in CSS
    assert 'html:not(:lang(zh),:lang(ja),:lang(ko)) :is(.star-primary,.star-secondary) .bright{display:inline-block;text-decoration:inherit;text-underline-offset:4px}' in CSS
    assert '.star-secondary .star{display:inline-block;white-space:normal}' in CSS
    # The rule comparison cards are at least 16em each and wrap, instead of an auto first column taking the length of
    # its English sentence and leaving the two field lists a few letters wide.
    assert '.rule-summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,16em),1fr));' in CSS
    assert 'minmax(150px,auto) minmax(0,1fr) minmax(0,1fr)' not in CSS
    # An English audit palace too narrow for a label beside its value puts the label above it.
    assert '.qr-board-result .qr-cell{display:flex;flex-direction:column;gap:6px;padding:8px 10px 10px;container:qr-cell / inline-size}' in CSS
    assert '@container qr-cell (max-width:190px){html[lang="en"] .qr-value{grid-template-columns:minmax(0,1fr);gap:0}}' in CSS
    # The browser smoke walks every page in English at 900 px for an element running out of its box.
    smoke = (ROOT / 'scripts/browser_smoke.py').read_text(encoding='utf-8')
    assert 'OVERFLOW = ' in smoke and 'assert overflow == {}, overflow' in smoke


def test_boundary_line_keeps_the_birth_label_inside_a_cut_window():
    # Cut at the supported years the window is no longer symmetric: the pin comes from the birth instant, stays on the
    # track, and the label slides to stay on the line, on a row of its own clear of the start and end times.
    js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    assert "birthAt = d.birth_utc ? Date.parse(d.birth_utc) : t0 + span / 2" in js
    assert "pin.style.left = `clamp(6px, ${birthAtPct}%, calc(100% - 6px))`" in js
    assert "birthLabel.style.transform = `translateX(-${birthAtPct}%)`" in js
    assert "'bt-axis' + (clipped.length ? ' has-birth-row' : '')" in js
    assert '.bt-axis.has-birth-row .bt-axis-birth{top:1.5em}' in CSS


def test_long_typed_names_wrap_inside_their_cards():
    # A name typed as one long run wraps anywhere; in a table cell it stays whole and the table scrolls instead.
    assert '.user-text{overflow-wrap:anywhere}' in CSS
    assert ':is(td,th).user-text,:is(td,th) .user-text{overflow-wrap:break-word}' in CSS
    # Only the tags are pills: a name or a day count inside a tag is plain text, and a wrapped tag is a rounded box.
    assert '.meta-tags span{' not in CSS and '.meta-tags>span{font-size:12px;' in CSS and 'border-radius:15px}' in CSS
    # A saved profile's name and birth time wrap as a pair, so a medium name moves the time down instead of breaking.
    assert '.group-profile-text{flex:1 1 auto;min-width:0;display:flex;flex-wrap:wrap;align-items:baseline;gap:0 8px}' in CSS
    assert '.group-profile small{margin-left:auto;font-size:11px;white-space:nowrap}' in CSS
    js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    assert "const what = append(row, 'span', 'group-profile-text');" in js
    assert '  .dm-sens .dm-sens-name{white-space:normal}' in CSS


def test_contrast_theme_keeps_a_frame_on_every_button():
    # Gold-filled run buttons and buttons that fill a heading cell keep a frame once a contrast theme drops colour.
    assert '.consult-shortcuts>button.scan-run,.qr-run .scan-run,.layer-btn,.api-send{border:1px solid ButtonText}' in CSS
    assert '  .fh-pick,.yt-year,.tl-year,.ds-pick,.qr-extra-remove{border:1px solid ButtonText}' in CSS


def test_json_tree_rows_are_tall_enough_to_tap():
    assert '.jv-node>summary{padding-block:2.5px}' in CSS


def test_contrast_theme_keeps_drop_downs_and_data_marks():
    # Gradients go in a contrast theme: the browser's own drop-down comes back, bars and pins take system colours.
    assert '  select:not([multiple]):not([size]){appearance:auto}' in CSS
    assert '  .element-fill,.element-legend i,.dm-mark,.ps-mark::after{forced-color-adjust:none;background:CanvasText}' in CSS
    assert '  .today-term-fill,.bt-pin{forced-color-adjust:none;background:Highlight}' in CSS
    assert '  .dm-seg,.dm-swatch,.ag-dot,.group-dot:not(.dot-unknown){forced-color-adjust:none}' in CSS
    # Only the chosen candidate day takes the Highlight ring; every candidate has its own frame.
    assert '.ds-day.is-selected,.dy-decade.is-picked,' in CSS and '.ds-day.is-pick,.dy-decade' not in CSS
    assert '.qr-extra-remove{min-width:24px;min-height:24px;' in CSS
    smoke = (ROOT / 'scripts/browser_smoke.py').read_text(encoding='utf-8')
    assert 'found += page.evaluate(UNFRAMED) + page.evaluate(MARKS_LOST)' in smoke


def test_wider_text_spacing_cuts_nothing_off():
    # WCAG 1.4.12: with a reader's own line, letter and word spacing, labels wrap or their box grows instead.
    assert '.dy-axis{position:relative;display:grid;grid-template-rows:auto;min-height:120px;min-width:600px;padding:18px 0 24px}' in CSS
    assert '.dy-band{position:relative;grid-row:1;' in CSS and 'axis.style.gridTemplateColumns = ' in APP
    assert '.dy-band small{max-width:100%;' in CSS
    assert '.shensha-tag{max-width:100%;padding:0 6px;border:1px solid var(--border);border-radius:11px;' in CSS
    assert '.luck-cell .luck-mark,.group-year-row .luck-mark{max-width:100%;white-space:normal}' in CSS
    assert '.group-member-head strong{min-width:0}' in CSS
    assert '.ag-method{min-width:0;' in CSS and '.ag-param code{min-width:0;font-size:11.5px;overflow-wrap:anywhere}' in CSS
    assert '.chat-panel .profile-actions button{width:auto;flex:0 1 auto;max-width:100%;' in CSS
    assert '.qr-value dd{display:flex;flex-wrap:wrap;gap:0 8px;margin:0;color:var(--text);overflow-wrap:anywhere}' in CSS
    assert 'width:max-content;margin:2px auto 0' not in CSS
    # A named day in the calendar or the date picker shows its whole name, however many lines it takes; only a tool's
    # long description folds, behind its own Show more.
    assert re.findall(r'-webkit-line-clamp:\d', CSS) == ['-webkit-line-clamp:3']
    smoke = (ROOT / 'scripts/browser_smoke.py').read_text(encoding='utf-8')
    assert 'spaced = page.add_style_tag(content=SPACING)' in smoke
