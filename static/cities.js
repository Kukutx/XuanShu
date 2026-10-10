'use strict';
// Offline birthplace presets: city-centre coordinates and IANA time zones.
// Selecting one fills the form locally; nothing is looked up or uploaded.
// Mainland China uses Asia/Shanghai (legal clock time), including Urumqi and Lhasa.
const CITY_PRESETS = [
  ['中国', [
    ['北京','Asia/Shanghai',116.4074,39.9042],['上海','Asia/Shanghai',121.4737,31.2304],['广州','Asia/Shanghai',113.2644,23.1291],
    ['深圳','Asia/Shanghai',114.0579,22.5431],['成都','Asia/Shanghai',104.0665,30.5728],['重庆','Asia/Shanghai',106.5516,29.5630],
    ['杭州','Asia/Shanghai',120.1551,30.2741],['南京','Asia/Shanghai',118.7969,32.0603],['武汉','Asia/Shanghai',114.3054,30.5931],
    ['西安','Asia/Shanghai',108.9398,34.3416],['天津','Asia/Shanghai',117.2010,39.0842],['沈阳','Asia/Shanghai',123.4315,41.8057],
    ['哈尔滨','Asia/Shanghai',126.5350,45.8038],['长春','Asia/Shanghai',125.3235,43.8171],['济南','Asia/Shanghai',117.1201,36.6512],
    ['青岛','Asia/Shanghai',120.3826,36.0671],['郑州','Asia/Shanghai',113.6254,34.7466],['长沙','Asia/Shanghai',112.9388,28.2282],
    ['福州','Asia/Shanghai',119.2965,26.0745],['厦门','Asia/Shanghai',118.0894,24.4798],['南昌','Asia/Shanghai',115.8579,28.6820],
    ['合肥','Asia/Shanghai',117.2272,31.8206],['昆明','Asia/Shanghai',102.8329,24.8801],['贵阳','Asia/Shanghai',106.6302,26.6477],
    ['南宁','Asia/Shanghai',108.3669,22.8170],['海口','Asia/Shanghai',110.3312,20.0319],['兰州','Asia/Shanghai',103.8343,36.0611],
    ['西宁','Asia/Shanghai',101.7782,36.6171],['银川','Asia/Shanghai',106.2309,38.4872],['乌鲁木齐','Asia/Shanghai',87.6168,43.8256],
    ['拉萨','Asia/Shanghai',91.1409,29.6456],['呼和浩特','Asia/Shanghai',111.7492,40.8426],['石家庄','Asia/Shanghai',114.5149,38.0428],
    ['太原','Asia/Shanghai',112.5489,37.8706],['香港','Asia/Hong_Kong',114.1694,22.3193],['澳门','Asia/Macau',113.5439,22.1987],
    ['台北','Asia/Taipei',121.5654,25.0330],['高雄','Asia/Taipei',120.3014,22.6273],
  ]],
  ['亚太', [
    ['新加坡','Asia/Singapore',103.8198,1.3521],['吉隆坡','Asia/Kuala_Lumpur',101.6869,3.1390],['曼谷','Asia/Bangkok',100.5018,13.7563],
    ['东京','Asia/Tokyo',139.6917,35.6895],['大阪','Asia/Tokyo',135.5023,34.6937],['首尔','Asia/Seoul',126.9780,37.5665],
    ['悉尼','Australia/Sydney',151.2093,-33.8688],['墨尔本','Australia/Melbourne',144.9631,-37.8136],['奥克兰','Pacific/Auckland',174.7633,-36.8485],
    ['迪拜','Asia/Dubai',55.2708,25.2048],
  ]],
  ['欧洲', [
    ['伦敦','Europe/London',-0.1276,51.5072],['巴黎','Europe/Paris',2.3522,48.8566],['柏林','Europe/Berlin',13.4050,52.5200],
    ['罗马','Europe/Rome',12.4964,41.9028],['米兰','Europe/Rome',9.1900,45.4642],['马德里','Europe/Madrid',-3.7038,40.4168],
    ['阿姆斯特丹','Europe/Amsterdam',4.9041,52.3676],['莫斯科','Europe/Moscow',37.6173,55.7558],
  ]],
  ['美洲', [
    ['纽约','America/New_York',-74.0060,40.7128],['洛杉矶','America/Los_Angeles',-118.2437,34.0522],['旧金山','America/Los_Angeles',-122.4194,37.7749],
    ['西雅图','America/Los_Angeles',-122.3321,47.6062],['芝加哥','America/Chicago',-87.6298,41.8781],['休斯顿','America/Chicago',-95.3698,29.7604],
    ['多伦多','America/Toronto',-79.3832,43.6532],['温哥华','America/Vancouver',-123.1207,49.2827],['圣保罗','America/Sao_Paulo',-46.6333,-23.5505],
  ]],
];
function setupCityPresets() {
  const select = document.querySelector('#birth_city');
  if (!select) return;
  CITY_PRESETS.forEach(([region, cities]) => {
    const group = document.createElement('optgroup'); group.label = region;
    cities.forEach(([name]) => {const op = document.createElement('option'); op.value = name; op.textContent = name; group.append(op);});
    select.append(group);
  });
  select.addEventListener('change', () => {
    const city = CITY_PRESETS.flatMap(([, list]) => list).find(([name]) => name === select.value);
    if (!city) return;
    const [, timezone, longitude, latitude] = city;
    const tz = document.querySelector('#timezone');
    if (![...tz.options].some(op => op.value === timezone)) {
      const op = document.createElement('option'); op.value = timezone; op.textContent = timezone; tz.append(op);
    }
    tz.value = timezone;
    document.querySelector('#longitude').value = String(longitude);
    const latitudeInput = document.querySelector('#latitude');
    if (latitudeInput) latitudeInput.value = String(latitude);
    // Let app.js refresh stale-result markers like any manual edit.
    document.querySelector('#birth-form').dispatchEvent(new Event('change', {bubbles: true}));
  });
}
setupCityPresets();
