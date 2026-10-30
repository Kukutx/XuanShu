'use strict';
// Interface language. Simplified Chinese is the source text. 繁體中文 is
// converted character by character (zh-tw-map.js, generated from OpenCC), so
// every label and computed result switches. English and 日本語 use the table
// below for the interface shell, plus UI_EXTRA (i18n-extra.js, generated from
// scripts/i18n_extra.json) for the remaining labels and the engines' result
// text. A text node that matches no entry whole has its known phrases replaced
// in place, longest first, so composed labels translate too; computed values
// such as 干支 pillars stay as characters.
// Text the user typed (.user-text: profile labels, memory, life events, option names) and
// model replies (.chat-text) are never rewritten.
const UI_LANG_KEY = 'xuanshu-ui-language';
const UI_LANGS = {'zh-CN': '简体中文', 'zh-TW': '繁體中文', 'en': 'English', 'ja': '日本語'};
// [简体中文, English, 日本語]
const UI_TEXT = [
  ['历法计算 × 传统文化 × Agent MCP', 'Calendar computation × traditional culture × Agent MCP', '暦法計算 × 伝統文化 × Agent MCP'],
  ['● 本地优先 · 数据不自动保存', '● Local-first · nothing saved automatically', '● ローカル優先 · 自動保存なし'],
  ['API 文档 ↗', 'API docs ↗', 'API ドキュメント ↗'],
  ['从你的问题出发，', 'Start from your question, ', 'あなたの問いから、'],
  ['调用可核验的术数工具。', 'and call verifiable traditional tools.', '検証できる術数ツールを呼び出す。'],
  ['时制审计与节令 · 八字藏干十神 · 农历反查 · 时刻误差采样 · 紫微三方四正与四化 · 时家奇门拆补九宫 · 双盘对照 · 建除值日 · 年度轨迹 · 大运十年干支 · 出生边界地图 · 透明决策矩阵 · 加密本地备份。所有计算结果可由 ChatGPT、Claude 与 Codex 通过 MCP 读取。',
    'Time-basis audit and solar terms · BaZi hidden stems and ten gods · lunar date lookup · birth-time uncertainty sampling · Zi Wei trines and four transformations · hour Qimen nine palaces · two-person comparison · twelve day officers · annual trajectory · decade periods · birth boundary map · transparent decision matrix · encrypted local backup. Every result can be read by ChatGPT, Claude and Codex over MCP.',
    '時制監査と節気 · 八字の蔵干と十神 · 旧暦逆引き · 出生時刻の誤差サンプリング · 紫微の三方四正と四化 · 時家奇門の九宮 · 二人の命式対照 · 建除十二直 · 年次推移 · 大運 · 出生境界マップ · 透明な意思決定マトリクス · 暗号化ローカルバックアップ。すべての計算結果は ChatGPT、Claude、Codex から MCP で読み取れます。'],
  ['出生信息', 'Birth details', '出生情報'],
  ['出生地当地钟表时间 · 可追溯计算规则', 'Local clock time at the birthplace · traceable rules', '出生地の現地時刻 · 追跡可能な計算規則'],
  ['公历出生日期与时间', 'Gregorian birth date and time', '西暦の生年月日と時刻'],
  ['示例日期为公开排盘基准；可以替换为自己的测试数据', 'The sample date is a public reference chart; replace it with your own data.', 'サンプル日付は公開の基準命式です。ご自身のデータに置き換えてください。'],
  ['当前使用演示出生资料。个人分析前请替换为实际出生时间。', 'Demo birth data in use. Replace it with a real birth time before personal analysis.', 'デモ用の出生データを使用中です。個人の分析には実際の出生時刻に置き換えてください。'],
  ['时区', 'Time zone', 'タイムゾーン'],
  ['传统顺逆方向参数（紫微大限 / 八字大运）', 'Direction parameter for Zi Wei decades / BaZi luck periods', '順逆方向パラメータ（紫微大限 / 八字大運）'],
  ['不指定', 'Unspecified', '指定しない'], ['男', 'Male', '男性'], ['女', 'Female', '女性'],
  ['23:00 子初换日', 'Day changes at 23:00 (early Zi)', '23:00 子初で日替わり'],
  ['仅影响八字日柱和时干', 'Affects only the BaZi day pillar and hour stem', '八字の日柱と時干のみに影響'],
  ['闰月后半月顺延', 'Second half of a leap month counts as next month', '閏月後半を翌月扱い'],
  ['影响紫微命盘月份', 'Affects the Zi Wei chart month', '紫微命盤の月に影響'],
  ['传统时辰计算时基', 'Time basis for traditional hours', '伝統的時辰の時刻基準'],
  ['当地钟表时间（默认）', 'Local clock time (default)', '現地時刻（既定）'],
  ['平太阳时（按经度）', 'Mean solar time (by longitude)', '平均太陽時（経度による）'],
  ['真太阳时（经度 + 均时差）', 'Apparent solar time (longitude + equation of time)', '真太陽時（経度 + 均時差）'],
  ['出生城市（选填，自动填写时区和经度）', 'Birth city (optional; fills time zone and longitude)', '出生都市（任意。タイムゾーンと経度を自動入力）'],
  ['手动填写', 'Enter manually', '手動で入力'],
  ['出生地经度（东正西负）', 'Birthplace longitude (east +, west −)', '出生地の経度（東経 +、西経 −）'],
  ['如 104.0667（成都示例）', 'e.g. 104.0667 (Chengdu)', '例：104.0667（成都）'],
  ['太阳时模式必须填写准确经度。城市坐标取市中心，内置在页面里，不联网查询、不上传位置。', 'Solar-time modes need an accurate longitude. City coordinates are city centres built into the page; nothing is looked up online or uploaded.', '太陽時モードでは正確な経度が必要です。都市座標は市中心でページに内蔵されており、オンライン検索やアップロードはしません。'],
  ['API 访问令牌（本地默认留空）', 'API access token (leave empty locally)', 'API アクセストークン（ローカルでは空欄）'],
  ['Docker/私有服务器需要填写，本机直接运行可留空', 'Required for Docker or a private server; leave empty when running locally', 'Docker や専用サーバーでは必須。ローカル実行では空欄で可'],
  ['生成命盘', 'Generate chart', '命盤を作成'],
  ['本机档案', 'Local profiles', 'ローカルプロフィール'],
  ['主动保存 · 不上传', 'Saved on request · never uploaded', '手動保存 · アップロードなし'],
  ['档案标签', 'Profile label', 'プロフィール名'],
  ['例如：测试命盘 A', 'e.g. Test chart A', '例：テスト命盤 A'],
  ['保存当前参数到此浏览器', 'Save current inputs in this browser', '現在の入力をこのブラウザに保存'],
  ['已保存的档案', 'Saved profiles', '保存済みプロフィール'],
  ['暂无本地档案', 'No local profiles', 'ローカルプロフィールなし'],
  ['载入', 'Load', '読み込む'], ['删除', 'Delete', '削除'],
  ['加密备份 · WebCrypto', 'Encrypted backup · WebCrypto', '暗号化バックアップ · WebCrypto'],
  ['备份口令（至少 12 字符，仅本次使用）', 'Backup passphrase (12+ characters, used once)', 'バックアップ用パスフレーズ（12 文字以上、今回のみ使用）'],
  ['只用于加密 / 解密备份', 'Used only to encrypt / decrypt the backup', 'バックアップの暗号化 / 復号のみに使用'],
  ['加密导出', 'Export encrypted', '暗号化して書き出し'], ['导入备份', 'Import backup', 'バックアップを読み込む'],
  ['清空全部本地档案', 'Clear all local profiles', 'ローカルプロフィールをすべて削除'],
  ['本地保存为明文；导出备份可额外加密。不要在公共电脑存储真实出生资料。', 'Local profiles are stored as plain text; exported backups can be encrypted. Do not store real birth data on a shared computer.', 'ローカル保存は平文です。書き出すバックアップは暗号化できます。共用 PC に実際の出生データを保存しないでください。'],
  ['历法与文化工具', 'Calendar and cultural tools', '暦法と文化のツール'],
  ['服务器不保留出生记录；解读为传统文化符号，不提供科学意义上的命运预测。', 'The server keeps no birth records. Readings are traditional cultural symbols, not scientific predictions.', 'サーバーは出生記録を保持しません。解釈は伝統文化の象徴であり、科学的な運命予測ではありません。'],
  ['命盘工作台', 'Chart workbench', '命盤ワークベンチ'],
  ['选择参数后开始生成', 'Choose inputs, then generate', '入力を選んでから作成'],
  ['导出 JSON ↓', 'Export JSON ↓', 'JSON を書き出す ↓'],
  ['出生参数已修改。下方旧命盘不再对应当前输入；请点击左侧「生成命盘」重新计算，才能导出。', 'Birth inputs changed. The chart below no longer matches; click “Generate chart” to recalculate before exporting.', '出生情報が変更されました。下の命盤は現在の入力と一致しません。書き出す前に「命盤を作成」で再計算してください。'],
  ['查找需要的功能', 'Find a feature', '機能を探す'],
  ['搜索八字、择时、报告等 29 项能力', 'Search 29 features: BaZi, date selection, reports…', '八字・日取り・レポートなど 29 機能を検索'],
  ['展开全部 29 项', 'Show all 29', '29 項目をすべて表示'],
  ['Ctrl+K 搜索 · ← / → 切换功能', 'Ctrl+K search · ← / → switch', 'Ctrl+K 検索 · ← / → 切替'],
  ['AI 对话', 'AI chat', 'AI チャット'], ['AI 咨询工作流', 'AI consultation workflow', 'AI 相談ワークフロー'],
  ['四柱八字', 'BaZi four pillars', '四柱推命'], ['奇门遁甲', 'Qimen Dunjia', '奇門遁甲'],
  ['紫微十二宫', 'Zi Wei twelve palaces', '紫微十二宮'], ['专业紫微（可选）', 'Professional Zi Wei (optional)', '専門紫微（任意）'],
  ['奇门逐宫核验', 'Qimen palace check', '奇門の宮ごと検証'], ['四化飞星', 'Four transformations', '四化飛星'],
  ['年干四化', 'Year-stem transformations', '年干四化'], ['太阳时审计', 'Solar time audit', '太陽時監査'],
  ['大运干支', 'Decade periods', '大運'], ['生时边界地图', 'Birth boundary map', '出生時刻境界マップ'],
  ['择日择时', 'Date & hour selection', '日取り・時取り'], ['建除值日', 'Day officers', '建除十二直'],
  ['年度轨迹', 'Annual trajectory', '年次推移'], ['方案决策', 'Decision matrix', '選択肢の比較'],
  ['历法日历', 'Calendar', '暦'], ['双人对照', 'Two-person comparison', '二人の対照'], ['多人关系', 'Group relations', '複数人の関係'], ['规则差异对照', 'Rule differences', 'ルール差の対照'],
  ['排盘质量审计', 'Chart quality audit', '命盤品質監査'], ['文化解读', 'Cultural reading', '文化的解説'],
  ['深度证据', 'Deep evidence', '詳細エビデンス'], ['四柱反查', 'Pillars to dates', '四柱逆引き'], ['今日历法', 'Today', '今日の暦'], ['命盘导入核对', 'Chart import check', '命盤インポート照合'], ['综合报告', 'Full report', '総合レポート'],
  ['Agent 集成', 'Agent integration', 'Agent 連携'], ['JSON 数据', 'JSON data', 'JSON データ'],
  ['历法可核验，规则可追溯', 'Verifiable calendar, traceable rules', '検証できる暦、追跡できる規則'],
  ['点击「生成命盘」开始计算', 'Click “Generate chart” to start', '「命盤を作成」で計算を開始'],
  ['部分紫微排盘 · 传统术数未经科学预测验证，不作医疗、金融或其他关键决策依据', 'Partial Zi Wei charting · traditional systems are not scientifically validated predictors; not a basis for medical, financial or other critical decisions', '紫微は一部のみ · 伝統術数は科学的な予測として検証されておらず、医療・金融などの重要な判断の根拠にはなりません'],
  ['界面语言', 'Interface language', '表示言語'],
  ['收起高级功能', 'Hide advanced features', '詳細機能を隠す'],
  ['出生资料已更改：旧命盘需要重新生成', 'Birth data changed: regenerate the chart', '出生データが変更されました：命盤を再作成してください'],
  ['时制 / GEO-TIME', 'Time basis / GEO-TIME', '時制 / GEO-TIME'],
  ['档案记忆与人生事件', 'Profile memory and life events', 'プロフィールの記憶と人生の出来事'],
  // Panel headings
  ['奇门遁甲 · 时家拆补转盘', 'Qimen Dunjia · hour chart (chabu, rotating)', '奇門遁甲 · 時家拆補転盤'],
  ['专业紫微 · iztro-py（可选）', 'Professional Zi Wei · iztro-py (optional)', '専門紫微 · iztro-py（任意）'],
  ['奇门外部参考盘逐宫核验', 'Check an external Qimen chart palace by palace', '外部の奇門参照盤を宮ごとに検証'],
  ['四柱命式', 'Four pillars', '四柱命式'], ['透明的文化解释', 'Transparent cultural explanation', '透明な文化的解説'],
  ['农历 · 干支日历', 'Lunar · sexagenary calendar', '旧暦 · 干支暦'], ['建除十二值日', 'Twelve day officers', '建除十二直'],
  ['连续农历年四化对照', 'Four transformations across lunar years', '連続する旧暦年の四化対照'],
  ['透明方案决策矩阵', 'Transparent decision matrix', '透明な意思決定マトリクス'],
  ['双人合盘对照', 'Two-person chart comparison', '二人の命盤対照'],
  ['指定农历年干四化', 'Four transformations of a lunar year', '指定した旧暦年の年干四化'],
  ['出生时间与经度审计', 'Birth time and longitude audit', '出生時刻と経度の監査'],
  ['规则敏感性比较', 'Rule sensitivity comparison', '規則の感度比較'],
  ['出生记录与排盘质量审计', 'Birth record and chart quality audit', '出生記録と命盤品質の監査'],
  ['深度证据 · 跨体系结构审计', 'Deep evidence · cross-system audit', '詳細エビデンス · 体系横断の監査'],
  ['可追溯综合报告', 'Traceable full report', '追跡可能な総合レポート'],
  ['八字大运十年干支', 'BaZi decade luck periods', '八字の大運（十年干支）'],
  ['出生时刻临界地图', 'Birth-time boundary map', '出生時刻の境界マップ'],
  ['Agent 接入中心', 'Agent integration hub', 'Agent 連携センター'],
  ['问题驱动咨询工作流', 'Question-driven consultation workflow', '問いから始める相談ワークフロー'],
  ['紫微宫位叠盘', 'Zi Wei palace overlay', '紫微の宮位重ね合わせ'],
  // AI chat
  ['回答语言 ', 'Answer language ', '回答言語 '], [' 附带左侧出生参数', ' Include the birth details on the left', ' 左側の出生情報を含める'],
  [' 已获对方同意使用其出生资料（双人或多人）', ' The other person or people agreed to use their birth data', ' 相手（複数可）の出生データ使用に同意を得ている'],
  ['载入本档案对话', 'Load this profile’s chat', 'このプロフィールの会話を読み込む'],
  ['正在检查对话服务…', 'Checking the chat service…', 'チャットサービスを確認中…'],
  ['直接提问即可，例如「我今年适合换工作吗？」。缺少出生时间或问题范围时，AI 会先追问。', 'Just ask, for example “Is this a good year to change jobs?”. If the birth time or scope is missing, the AI asks first.', '「今年は転職に向いている？」のように質問してください。出生時刻や範囲が足りない場合は AI が先に確認します。'],
  ['看看我的本命盘有什么特点', 'What stands out in my natal chart?', '私の命盤の特徴は？'],
  ['对照我的人生事件回溯一下大运', 'Review my life events against my decade periods', '人生の出来事を大運と照らし合わせて'],
  ['下个月哪几天适合搬家？请先问我候选日期', 'Which days next month suit a move? Ask me for candidate dates first', '来月の引っ越しに向く日は？まず候補日を聞いて'],
  ['比较一下我和伴侣的命盘（对方已同意）', 'Compare my chart with my partner’s (they agreed)', '私とパートナーの命盤を比較して（同意済み）'],
  ['输入问题，Ctrl+Enter 发送', 'Type a question, Ctrl+Enter to send', '質問を入力、Ctrl+Enter で送信'],
  ['发送', 'Send', '送信'], ['思考中…', 'Thinking…', '考え中…'],
  ['导出对话 Markdown', 'Export chat as Markdown', '会話を Markdown で書き出す'], ['清空对话', 'Clear chat', '会話を消去'],
  ['正在调用工具和模型…', 'Calling tools and the model…', 'ツールとモデルを呼び出し中…'],
  ['我', 'Me', '自分'], ['玄枢', 'XuanShu', '玄枢'],
  ['档案记忆', 'Profile memory', 'プロフィールの記憶'], ['添加记忆', 'Add memory', '記憶を追加'],
  ['人生事件（命途回溯锚点）', 'Life events (anchors for retrospective review)', '人生の出来事（振り返りの基準点）'],
  ['添加事件', 'Add event', '出来事を追加'], ['对照人生事件（不需要模型）', 'Review life events (no model needed)', '人生の出来事を照合（モデル不要）'],
  [' 在本机保存这个档案的对话（明文）', ' Keep this profile’s chats in this browser (plain text)', ' このプロフィールの会話をこのブラウザに保存（平文）'],
  ['保存', 'Save', '保存'], ['先选择档案', 'Choose a profile first', '先にプロフィールを選択'],
  ['对话由你配置的语言模型生成；命盘计算只来自本地确定性工具。服务器不保存对话、记忆或出生资料。传统术数未经科学预测效力验证。', 'Replies come from the language model you configured; chart calculations come only from local deterministic tools. The server stores no chats, memory or birth data. Traditional systems are not scientifically validated predictors.', '回答は設定した言語モデルが生成し、命盤の計算はローカルの決定的ツールのみによります。サーバーは会話・記憶・出生データを保存しません。伝統術数は科学的な予測として検証されていません。'],
  [' 独立核验回答（多一次模型调用）', ' Independently verify answers (one more model call)', ' 回答を独立に検証（モデル呼び出しが 1 回増える）'],
  ['出生时间误差 ', 'Birth-time uncertainty ', '出生時刻の誤差 '],
  ['回答方式 ', 'Answer mode ', '回答方式 '], ['单一助手', 'Single assistant', '単一アシスタント'],
  ['多流派会诊（多次模型调用）', 'Multi-school panel (several model calls)', '流派別の合議（モデル呼び出しが複数回）'],
  ['各流派专家正在分别排盘，随后综合…', 'Each school’s specialist is charting; a synthesis follows…', '各流派の専門家が個別に作盤中、その後まとめます…'],
  ['±2 分钟', '±2 min', '±2 分'], ['±15 分钟', '±15 min', '±15 分'], ['±30 分钟', '±30 min', '±30 分'],
  ['±1 小时', '±1 h', '±1 時間'], ['±2 小时', '±2 h', '±2 時間'],
  // Date selection
  ['起始日', 'Start date', '開始日'], ['扫描天数', 'Days to scan', 'スキャン日数'],
  ['候选时刻（选填，逗号分隔，如 09:00,15:00）', 'Candidate times (optional, comma-separated, e.g. 09:00,15:00)', '候補時刻（任意、カンマ区切り。例：09:00,15:00）'],
  ['只保留这些值日（不选=不限）', 'Keep only these officers (none = any)', 'これらの十二直のみ（未選択＝制限なし）'],
  ['排除这些值日', 'Exclude these officers', 'これらの十二直を除外'],
  [' 排除交节当天', ' Exclude solar-term change days', ' 節入りの日を除外'],
  [' 排除与左侧本命年支、日支相冲的日子', ' Exclude days clashing with the natal year or day branch', ' 本命の年支・日支と冲になる日を除外'],
  ['扫描候选日', 'Scan candidate days', '候補日をスキャン'],
  ['先选条件再扫描。结果只是传统标签筛选，最终取舍以现实安排为准。', 'Choose criteria, then scan. Results only filter traditional labels; real-world plans decide.', '条件を選んでからスキャンしてください。結果は伝統的なラベルによる絞り込みにすぎず、最終判断は現実の予定によります。'],
  // Two-person comparison
  ['比较两人命盘', 'Compare both charts', '二人の命盤を比較'],
  ['A 使用左侧出生信息；B 在下方单独填写。对照数据不会自动保存。', 'A uses the birth details on the left; enter B below. Nothing is saved automatically.', 'A は左側の出生情報を使い、B は下に入力します。自動保存はされません。'],
  ['B · 公历出生日期与时间', 'B · Gregorian birth date and time', 'B · 西暦の生年月日と時刻'], ['B · 时区', 'B · Time zone', 'B · タイムゾーン'],
];

let uiLang = 'zh-CN';
let uiObserver = null;
const uiIndex = {};
// One-character entries join only for the five elements, which results compose as 木 / 水.
const UI_SINGLE_TOKENS = '木火土金水';
const UI_WHOLE_ONLY = ['1 天', '1 小时', '1 岁', '1 个月', '1 个工具有结果', '1 个字段', '1 处匹配'];
let uiPhraseMap = {};  // trimmed phrase -> entry; an exact (untrimmed) key wins
let uiPhrases = [], uiPhraseRe = null;
function buildUiIndex() {
  Object.keys(uiIndex).forEach(k => {delete uiIndex[k];});
  if (typeof UI_EXTRA === 'object') Object.entries(UI_EXTRA).forEach(([zh, [en, ja]]) => {uiIndex[zh] = {en, ja};});
  UI_TEXT.forEach(([zh, en, ja]) => {uiIndex[zh] = {en, ja};});
  // Phrases of two or more characters, longest first, for in-place replacement. The singular counts match only a whole
  // text, so "21 天" never turns into "21 day".
  uiPhraseMap = {};
  Object.keys(uiIndex).forEach(k => {const t = k.trim(); if (!uiPhraseMap[t] || k === t) uiPhraseMap[t] = uiIndex[k];});
  uiPhrases = Object.keys(uiPhraseMap).filter(k => (k.length >= 2 || UI_SINGLE_TOKENS.includes(k)) && /[㐀-鿿]/.test(k) && !UI_WHOLE_ONLY.includes(k))
    .sort((a, b) => b.length - a.length);
  uiPhraseRe = uiPhrases.length
    ? new RegExp(uiPhrases.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'), 'g') : null;
}
buildUiIndex();
// The two large tables load only for the language that uses them, so 简体中文 visitors never download them.
const UI_TABLES = {
  en: ['i18n-extra.js', () => typeof UI_EXTRA === 'object'],
  ja: ['i18n-extra.js', () => typeof UI_EXTRA === 'object'],
  'zh-TW': ['zh-tw-map.js', () => typeof ZH_TW_CHARS === 'object'],
};
const uiTableLoads = {};
function loadUiTable(lang) {
  const table = UI_TABLES[lang];
  if (!table || table[1]()) return Promise.resolve();
  const file = table[0];
  if (!uiTableLoads[file]) uiTableLoads[file] = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = '/static/' + file;
    script.onload = () => {if (file === 'i18n-extra.js') buildUiIndex(); resolve();};
    script.onerror = () => {delete uiTableLoads[file]; script.remove(); reject(new Error('Could not load ' + file));};
    document.head.append(script);
  });
  return uiTableLoads[file];
}
const UI_ATTRS = ['placeholder', 'title', 'aria-label', 'label'];  // label: <optgroup> names
const uiOriginal = new WeakMap();  // text node -> source text

function toTraditional(text) {
  if (typeof ZH_TW_CHARS !== 'object') return text;
  let out = '';
  for (let i = 0; i < text.length;) {
    let hit = null;
    for (let n = 4; n >= 2 && !hit; n--) {
      const piece = text.slice(i, i + n);
      if (piece.length === n && ZH_TW_PHRASES[piece]) hit = [piece.length, ZH_TW_PHRASES[piece]];
    }
    if (hit) {out += hit[1]; i += hit[0]; continue;}
    out += ZH_TW_CHARS[text[i]] || text[i]; i += 1;
  }
  return out;
}
function translateText(source) {
  // A list separator on its own, between labels that each translate whole.
  if (uiLang === 'en' && source === '、') return ', ';
  // A colon or semicolon on its own between translated pieces reads as English punctuation.
  if (uiLang === 'en' && source === '：') return ': ';
  if (uiLang === 'en' && source === '；') return '; ';
  if (uiLang === 'zh-CN' || !/[㐀-鿿]/.test(source)) return source;
  if (uiLang === 'zh-TW') return toTraditional(source);
  const trimmed = source.trim();
  const entry = uiIndex[source] || uiIndex[trimmed];
  if (entry) return uiIndex[source] ? entry[uiLang] : source.replace(trimmed, entry[uiLang].trim());
  if (!uiPhraseRe) return source;
  // Numeric dates read as 2026-10-11 / 10/11 in English; Japanese writes them the same way as Chinese.
  if (uiLang === 'en') source = source.replace(/(\d{4})年(\d{1,2})月(\d{1,2})日/g, (_, y, m, d) => `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`)
    .replace(/(\d{1,2})月(\d{1,2})日/g, '$1/$2')
    // Counted days and ages: 19.97 日 reads 19.97 days, 6岁 7月 reads 6 yr 7 mo.
    .replace(/(\d+)岁 ?(\d+)个?月/g, '$1 yr $2 mo').replace(/(\d+)岁(?![㐀-鿿（(])/g, '$1 yr')
    .replace(/(\d+(?:\.\d+)?) ?日(?![㐀-鿿])/g, (_, n) => n + (n === '1' ? ' day' : ' days'))
    // Qimen bureaus: 阴遁5局 reads Yin Dun 5.
    .replace(/([阴阳])遁 ?(\d)局/g, (_, side, n) => (side === '阴' ? 'Yin' : 'Yang') + ' Dun ' + n);
  const gap = uiLang === 'en' ? ' ' : '';
  // Composed text: replace each known phrase; English gets spaces between replaced words and Chinese.
  const out = source.replace(uiPhraseRe, (hit, offset, whole) => {
    const target = uiPhraseMap[hit][uiLang].trim();
    const before = offset > 0 && /[^\s(（·:：,，、/]/.test(whole[offset - 1]) ? gap : '';
    const next = whole[offset + hit.length];
    const after = next && /[^\s)）·:：,，、。/]/.test(next) ? gap : '';
    return before + target + after;
  });
  // English lists read "A, B; C" rather than keeping the Chinese enumeration comma and semicolon.
  return uiLang === 'en' ? out.replace(/\s*、\s*/g, ', ').replace(/\s*；\s*/g, '; ') : out;
}
function skipNode(el) {
  return !el || el.closest('script,style,textarea,code,pre,.chat-text,.user-text,[data-no-i18n]') !== null;
}
function translateNode(root) {
  if (root.nodeType === Node.TEXT_NODE) {
    if (skipNode(root.parentElement)) return;
    if (!uiOriginal.has(root)) uiOriginal.set(root, root.data);
    const value = translateText(uiOriginal.get(root));
    if (root.data !== value) root.data = value;
    return;
  }
  if (root.nodeType !== Node.ELEMENT_NODE || skipNode(root)) return;
  translateAttrs(root);
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (node.nodeType === Node.ELEMENT_NODE) translateAttrs(node);
    else translateNode(node);
  }
}
function translateAttrs(el) {
  // A textarea's own placeholder is interface text; only its typed value is the user's.
  if (el.closest('script,style,code,pre,.chat-text,.user-text,[data-no-i18n]')) return;
  for (const attr of UI_ATTRS) {
    if (!el.hasAttribute(attr)) continue;
    const key = 'data-i18n-' + attr;
    if (!el.hasAttribute(key)) el.setAttribute(key, el.getAttribute(attr));
    const value = translateText(el.getAttribute(key));
    if (el.getAttribute(attr) !== value) el.setAttribute(attr, value);
  }
}
let uiRequested = 'zh-CN';
function applyUiLanguage(lang) {
  const wanted = UI_LANGS[lang] ? lang : 'zh-CN';
  uiRequested = wanted;
  // Without its table 繁體 cannot convert; English and 日本語 still have the interface shell above.
  loadUiTable(wanted).then(() => true, () => wanted !== 'zh-TW').then(ok => {
    if (uiRequested === wanted) applyLoadedLanguage(ok ? wanted : 'zh-CN');
  });
}
function applyLoadedLanguage(lang) {
  uiLang = lang;
  document.documentElement.lang = uiLang;
  if (uiObserver) uiObserver.disconnect();
  translateNode(document.body);
  document.title = uiLang === 'zh-TW' ? toTraditional('玄枢 · XuanShu v.0.1.0') : '玄枢 · XuanShu v.0.1.0';
  // Text the app sets later (re-rendered panels, status lines) is translated as it appears.
  uiObserver = new MutationObserver(records => {
    uiObserver.disconnect();
    for (const record of records) {
      if (record.type === 'characterData') {
        // The app replaced this text: treat the new value as source text.
        if (record.target.data !== translateText(uiOriginal.get(record.target) || '')) uiOriginal.set(record.target, record.target.data);
        translateNode(record.target);
      } else if (record.type === 'attributes') {
        // The app set a new value; our own translation of the stored source (already applied while handling the
        // element's insertion earlier in this batch) is not one.
        const key = 'data-i18n-' + record.attributeName, value = record.target.getAttribute(record.attributeName);
        if (!record.target.hasAttribute(key) || value !== translateText(record.target.getAttribute(key))) record.target.removeAttribute(key);
        translateAttrs(record.target);
      } else record.addedNodes.forEach(translateNode);
    }
    uiObserver.observe(document.body, {subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: UI_ATTRS});
  });
  uiObserver.observe(document.body, {subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: UI_ATTRS});
  // Text the translator leaves alone (canvas drawings, <pre> chart text) is regenerated by whoever owns it.
  document.dispatchEvent(new CustomEvent('xuanshu-language', {detail: uiLang}));
}
function setupUiLanguage() {
  const select = document.getElementById('ui-language');
  Object.entries(UI_LANGS).forEach(([value, label]) => {
    const op = document.createElement('option'); op.value = value; op.textContent = label; select.append(op);
  });
  select.setAttribute('data-no-i18n', '');
  let saved = null;
  try {saved = localStorage.getItem(UI_LANG_KEY);} catch (_) {}
  select.value = UI_LANGS[saved] ? saved : 'zh-CN';
  select.addEventListener('change', () => {
    // Choosing a language is a deliberate action; only the language code is stored.
    try {localStorage.setItem(UI_LANG_KEY, select.value);} catch (_) {}
    // Switching back to 简体中文 restores the stored source text, so no reload is needed.
    if (typeof chatLanguage !== 'undefined') {chatLanguage = select.value; if (active === 'chat') render();}
    applyUiLanguage(select.value);
  });
  if (typeof chatLanguage !== 'undefined') chatLanguage = select.value;
  applyUiLanguage(select.value);
}
setupUiLanguage();
