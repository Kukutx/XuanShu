"""Interface language assets: script order, dictionary shape, 繁體 table guards."""
from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def _tables():
    source = (ROOT / 'static/zh-tw-map.js').read_text(encoding='utf-8')
    chars = json.loads(re.search(r'ZH_TW_CHARS = (\{.*?\});', source).group(1))
    phrases = json.loads(re.search(r'ZH_TW_PHRASES = (\{.*?\});', source).group(1))
    return chars, phrases


def test_scripts_load_in_dependency_order():
    html = TestClient(app).get('/').text
    order = re.findall(r'<script src="/static/([\w.-]+)" defer>', html)
    assert order == ['markdown.js', 'chat.js', 'app.js', 'vault.js', 'cities.js', 'tips.js', 'i18n.js']
    assert 'id="ui-language"' in html
    assert TestClient(app).get('/static/i18n.js').status_code == 200


def test_traditional_table_keeps_domain_terms():
    chars, phrases = _tables()
    # Stems, branches and star names must survive: never 幹/醜/鬥/臺/鹹/兇/佔.
    assert not set('干丑斗台咸凶占') & set(chars)
    assert not any(set(k) & set('干丑斗台咸凶占') for k in phrases)
    assert chars['冲'] == '沖' and chars['钟'] == '鐘'
    assert '合中' not in phrases  # 三合中位 stays 三合, not 閤
    assert '换发' not in phrases  # 切换发生 stays 切換發生, not 髮
    assert phrases['历日'] == '曆日' and phrases['合历'] == '合曆'  # calendar words from the glossary
    assert chars['宫'] == '宮' and chars['历'] == '歷' and phrases['农历'] == '農曆' and phrases['日历'] == '日曆'


def test_traditional_table_covers_interface_text():
    chars, _ = _tables()
    # Spot-check characters from the new interface strings and computed labels.
    for simplified in '双盘叠宫语档对话择时禄贪杀阴':
        assert simplified in chars, simplified


def test_dictionary_entries_are_complete_and_unique():
    source = (ROOT / 'static/i18n.js').read_text(encoding='utf-8')
    body = source[source.index('const UI_TEXT = ['):source.index('];\n\nlet uiLang')]
    rows = re.findall(r"\[('(?:[^'\\]|\\.)*'), ('(?:[^'\\]|\\.)*'), ('(?:[^'\\]|\\.)*')\]", body)
    assert len(rows) >= 150
    zh = [r[0] for r in rows]
    assert len(zh) == len(set(zh))
    assert all(len(cell) > 2 for row in rows for cell in row)
    html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
    for tab in re.findall(r'role="tab" aria-selected="\w+">([^<]+)</button>', html):
        assert f"'{tab}'" in zh, tab


def test_extra_table_is_generated_and_covers_every_source_string():
    import importlib.util
    spec = importlib.util.spec_from_file_location('build_i18n_extra', ROOT / 'scripts/build_i18n_extra.py')
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    data = build.load()
    assert (ROOT / 'static/i18n-extra.js').read_text(encoding='utf-8') == build.render(data)
    # New Chinese text in static/ or app/ needs an English and Japanese entry.
    assert build.missing() == []
    assert data['命宫'][0] == 'Life Palace' and data['命宫'][1] == '命宮'
