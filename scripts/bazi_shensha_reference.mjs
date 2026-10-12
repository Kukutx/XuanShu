// Reference 神煞 from @soul-atelier/bazi for scripts/eval_crosscheck.py.
// Reads JSON lines {pillars: {year, month, day, hour}, fortune: '甲子'} (each pillar a 干支 such as '庚午') on stdin and
// writes one JSON line per query: {natal: {star: [pillar, ...]}, fortune: [star, ...]}, the stars of the four pillars
// and of one luck or year pillar read against them. Install the pinned version with `npm install --prefix docs/evals`;
// eval_crosscheck.py points NODE_PATH at docs/evals/node_modules. The package is ES-module only, so it is imported
// from that folder by path.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const entry = join(process.env.NODE_PATH, '@soul-atelier', 'bazi', 'dist', 'index.mjs');
const { calculateShenSha, calculateFortuneShenSha } = await import(pathToFileURL(entry).href);

const ganzhi = text => ({ stem: { name: text[0] }, branch: { name: text[1] }, sixtyCycleName: text });
const rows = readFileSync(0, 'utf8').split('\n').filter(Boolean).map(line => {
  const q = JSON.parse(line);
  const chart = Object.fromEntries(['year', 'month', 'day', 'hour'].map(key => [key, ganzhi(q.pillars[key])]));
  // Gender only decides between 阴差 and 阳错, which XuanShu does not list.
  const natal = Object.fromEntries(calculateShenSha(chart, 'male').map(item => [item.name, item.pillars]));
  const fortune = calculateFortuneShenSha(chart, ganzhi(q.fortune)).map(item => item.name);
  return JSON.stringify({ natal, fortune });
});
process.stdout.write(rows.join('\n') + '\n');
