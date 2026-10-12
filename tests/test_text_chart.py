"""The share dialog's text chart (static/app.js shareChartText) pastes back into the import check."""
from __future__ import annotations

from app.chart_import import TRADITIONAL, ChartImportRequest, chart_import_check, parse_chart_text
from app.engines import BirthInput

BIRTH = BirthInput(birth_datetime='2000-08-16T04:00', timezone='Asia/Shanghai', gender='female')
# Copied from the share dialog for this birth with 乾造/坤造 ticked (scripts/browser_smoke.py checks the same lines);
# the luck decades it then lists must not disturb the parser.
TEXT_CHART = """玄枢命盘 · 本地确定性计算
坤造

【四柱八字】
　　　年柱　　月柱　　日柱　　时柱
干支：庚辰　　甲申　　丙午　　庚寅
十神：偏财　　偏印　　日主　　偏财
藏干：戊乙癸　庚壬戊　丁己　　甲丙戊
纳音：白蜡金　泉中水　天河水　松柏木
星运：冠带　　病　　　帝旺　　长生
自坐：养　　　绝　　　帝旺　　绝
旬空：申酉　　午未　　寅卯　　午未
空亡：月柱申（年空），时柱寅（日空）
日主：丙火
天干关系：年月 庚甲相冲　月时 甲庚相冲
地支关系：月时 申寅六冲·相刑
大运：逆排
　起运  3　癸未　正官　星运衰　　合日
　起运 13　壬午　七杀　星运帝旺　同日　刑日
　起运 23　辛巳　正财　星运临官　合月　刑月　害时　刑时
　起运 33　庚辰　偏财　星运冠带　同年　刑年
　起运 43　己卯　伤官　星运沐浴　害年　日空
　起运 53　戊寅　食神　星运长生　冲月　刑月　同时　日空
　起运 63　丁丑　劫财　星运养　　害日
　起运 73　丙子　比肩　星运胎　　冲日
　起运 83　乙亥　正印　星运绝　　害月　合时

【紫微斗数】
命宫在壬午，身宫在官禄宫，木三局，命主破军，身主文昌
生年四化：太阳化禄　武曲化权　太阴化科　天同化忌
命宫（壬午）：紫微庙｜文曲陷 凤阁 蜚廉｜大限 3–12
兄弟宫（辛巳）：天机平｜天喜 天空 孤辰｜大限 13–22
夫妻宫（庚辰）：七杀庙｜右弼 火星陷 封诰 华盖｜大限 23–32
子女宫（己卯）：太阳庙 天梁庙｜天刑｜大限 33–42
财帛宫（戊寅）：武曲得 天相庙｜天马 月解 天巫 阴煞 天哭 天寿 三台 天厨｜大限 43–52
疾厄宫（己丑）：天同不 巨门不｜地劫 天魁 寡宿 破碎 天使｜大限 53–62
迁移宫（戊子）：贪狼旺｜铃星陷 八座｜大限 63–72
仆役宫（丁亥）：太阴庙｜红鸾 天月 恩光 天伤｜大限 73–82
官禄宫（丙戌，身宫）：廉贞利 天府庙｜左辅 天虚 天才｜大限 83–92
田宅宫（乙酉）：空宫｜地空 擎羊陷 咸池 天贵｜大限 93–102
福德宫（甲申）：破军得｜文昌得 禄存 龙池 台辅｜大限 103–112
父母宫（癸未）：空宫｜陀罗庙 天钺 天姚｜大限 113–122
注：紫微为部分排盘，含十四主星与选定的辅星、杂曜，不是全流派专业盘；四化表与亮度表因流派而异。

排盘规则：00:00 换日　闰月后半月按下月　钟表时间
传统文化符号，未经科学预测效力验证，不作医疗、投资、法律等决策依据。
XuanShu · 开源 · 确定性计算，可复现"""

# Simplified -> traditional, the inverse of the parser's table, so the traditional chart text from zh-TW parses too.
TRADITIONAL_PAIRS = tuple(''.join(chr(c) for c in pair) for pair in zip(*((v, k) for k, v in TRADITIONAL.items())))


def test_text_chart_parses_every_field():
    parsed = parse_chart_text(TEXT_CHART)
    assert parsed['pillars'] == {'year': '庚辰', 'month': '甲申', 'day': '丙午', 'hour': '庚寅'}
    assert (parsed['ming_branch'], parsed['shen_palace'], parsed['bureau']) == ('午', '官禄宫', '木三局')
    assert (parsed['ming_master'], parsed['shen_master']) == ('破军', '文昌')
    assert parsed['transformations'] == {'化禄': '太阳', '化权': '武曲', '化科': '太阴', '化忌': '天同'}
    # Auxiliary stars after the bar are not read as major stars; empty palaces say 空宫.
    assert len(parsed['palace_major_stars']) == 12 and parsed['palace_major_stars']['田宅宫'] == []
    assert parsed['palace_major_stars']['官禄宫'] == ['廉贞', '天府'] and parsed['palace_brightness']['疾厄宫'] == {'天同': '不', '巨门': '不'}


def test_text_chart_round_trip_matches_every_field():
    for text in (TEXT_CHART, TEXT_CHART.translate(str.maketrans(*TRADITIONAL_PAIRS))):
        result = chart_import_check(ChartImportRequest(birth=BIRTH, text=text))
        assert result['recognized_count'] == 35 and result['summary'] == {'matched': 35, 'mismatched': 0}


def test_hour_unknown_text_chart_compares_three_pillars():
    text = TEXT_CHART.split('【紫微斗数】')[0].replace('庚寅', '—').replace('月时 甲庚相冲', '')
    result = chart_import_check(ChartImportRequest(birth=BIRTH, text=text))
    assert [f['key'] for f in result['fields']] == ['pillar.year', 'pillar.month', 'pillar.day']


def test_share_dialog_wiring():
    from pathlib import Path
    app_js = (Path(__file__).resolve().parents[1] / 'static/app.js').read_text(encoding='utf-8')
    for marker in ("function shareChartText()", "'share-copy-text'", "'share-download-text'", "'share-system'", "['gender', '显示乾造 / 坤造']"):
        assert marker in app_js, marker
