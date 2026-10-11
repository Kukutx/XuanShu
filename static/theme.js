'use strict';
// Colour theme. The page follows the system setting unless the user picks a
// theme with the header button; the choice is stored only after that click and
// is removed again when the user cycles back to "跟随系统". Loaded without
// defer so the stored theme applies before the first paint.
(function () {
  const KEY = 'xuanshu-theme';
  const ORDER = [null, 'light', 'dark'];
  const LABELS = {system: '跟随系统', light: '浅色', dark: '深色'};
  const root = document.documentElement;
  const media = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  function stored() {
    try {const value = localStorage.getItem(KEY); return value === 'light' || value === 'dark' ? value : null;}
    catch (_) {return null;}
  }
  let choice = stored();
  function apply() {
    if (choice) root.dataset.theme = choice; else delete root.dataset.theme;
    const dark = choice ? choice === 'dark' : !media || media.matches;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = dark ? '#0d1118' : '#f6f2ea';
    const button = document.getElementById('theme-toggle');
    if (!button) return;
    const mode = choice || 'system', label = LABELS[mode];
    button.querySelector('.theme-icon').dataset.mode = mode;  // drawn in CSS
    button.querySelector('.theme-label').textContent = label;
    button.title = '配色：' + label + '（点击切换）';
  }
  function cycle() {
    choice = ORDER[(ORDER.indexOf(choice) + 1) % ORDER.length];
    try {
      if (choice) localStorage.setItem(KEY, choice); else localStorage.removeItem(KEY);
    } catch (_) { /* Storage unavailable: the theme still changes for this visit. */ }
    apply();
  }
  apply();
  if (media && media.addEventListener) media.addEventListener('change', () => {if (!choice) apply();});
  function wire() {
    const button = document.getElementById('theme-toggle');
    if (!button || button.dataset.wired) return;
    button.dataset.wired = '1';
    button.addEventListener('click', cycle);
    apply();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire); else wire();
})();
