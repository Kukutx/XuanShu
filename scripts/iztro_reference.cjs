// Reference charts from iztro (the original JavaScript library) for scripts/eval_crosscheck.py.
// Reads JSON lines {date: 'YYYY-M-D', hour: 0-12, gender: '男'|'女', target?: 'YYYY-M-D', target_hour?: 0-12}
// on stdin and writes one JSON line per query: every palace's stars, their brightness and twelve gods, and, with a
// target, each period layer's stem, branch and period stars (流耀). Install the pinned version with
// `npm install --prefix docs/evals`; eval_crosscheck.py points NODE_PATH at docs/evals/node_modules.
const { astro } = require('iztro');

const rows = require('fs').readFileSync(0, 'utf8').split('\n').filter(Boolean).map(line => {
  const q = JSON.parse(line);
  // fixLeap = true: the second half of a leap month counts as the next month, as XuanShu's default.
  const chart = astro.bySolar(q.date, q.hour, q.gender, true, 'zh-CN');
  const row = {palaces: chart.palaces.map(p => ({
    branch: p.earthlyBranch, stars: [...p.majorStars, ...p.minorStars, ...p.adjectiveStars].map(s => s.name),
    brightness: Object.fromEntries([...p.majorStars, ...p.minorStars].filter(s => s.brightness).map(s => [s.name, s.brightness])),
    changsheng: p.changsheng12, boshi: p.boshi12, suiqian: p.suiqian12, jiangqian: p.jiangqian12,
  }))};
  if (q.target) {
    const h = chart.horoscope(q.target, q.target_hour);
    row.horoscope = {};
    for (const key of ['decadal', 'age', 'yearly', 'monthly', 'daily', 'hourly']) {
      const item = h[key];
      // Palace index 0 is 寅; stars[i] lists the period stars of that palace.
      row.horoscope[key] = {index: item.index, name: item.name, stem: item.heavenlyStem, branch: item.earthlyBranch,
                            stars: item.stars ? item.stars.map(list => list.map(s => s.name)) : null,
                            twelve: item.yearlyDecStar || null};
    }
  }
  return JSON.stringify(row);
});
process.stdout.write(rows.join('\n') + '\n');
