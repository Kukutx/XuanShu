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
  const isDark = value => value ? value === 'dark' : !media || media.matches;
  function apply() {
    if (choice) root.dataset.theme = choice; else delete root.dataset.theme;
    const dark = isDark(choice);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = dark ? '#0d1118' : '#f6f2ea';
    const button = document.getElementById('theme-toggle');
    if (!button) return;
    const mode = choice || 'system', label = LABELS[mode];
    button.querySelector('.theme-icon').dataset.mode = mode;  // drawn in CSS
    button.querySelector('.theme-label').textContent = label;
    button.setAttribute('data-tip', '配色：' + label + '（点击切换）');
  }
  function cycle(event) {
    const before = isDark(choice);
    choice = ORDER[(ORDER.indexOf(choice) + 1) % ORDER.length];
    try {
      if (choice) localStorage.setItem(KEY, choice); else localStorage.removeItem(KEY);
    } catch (_) { /* Storage unavailable: the theme still changes for this visit. */ }
    if (isDark(choice) !== before) reveal(event && event.currentTarget); else apply();
  }
  // When the colours actually change, the new theme spreads in a circle from the button over a still picture of the
  // old one. The browser takes that picture first and then runs apply, so the page switches a frame later.
  function reveal(button) {
    if (!button || typeof document.startViewTransition !== 'function' || document.hidden
        || (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches)) {apply(); return;}
    const box = button.getBoundingClientRect(), x = box.left + box.width / 2, y = box.top + box.height / 2;
    const radius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
    root.classList.add('theme-reveal');
    const transition = document.startViewTransition(apply);
    transition.ready.then(() => root.animate({clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`]},
      {duration: 480, easing: 'cubic-bezier(.2, .7, .2, 1)', pseudoElement: '::view-transition-new(root)'})).catch(() => {});
    transition.finished.finally(() => root.classList.remove('theme-reveal'));
  }
  apply();
  if (media && media.addEventListener) media.addEventListener('change', () => {if (!choice) apply();});
  // The header wraps to a second line in some languages and widths; sticky offsets and scroll padding follow its
  // measured height instead of the nominal one.
  function measureHeader() {
    const header = document.querySelector('.header');
    if (!header || header.dataset.measured || typeof ResizeObserver !== 'function') return;
    header.dataset.measured = '1';
    new ResizeObserver(() => root.style.setProperty('--header-h', Math.ceil(header.getBoundingClientRect().height) + 'px')).observe(header);
  }
  function wire() {
    measureHeader();
    const button = document.getElementById('theme-toggle');
    if (!button || button.dataset.wired) return;
    button.dataset.wired = '1';
    button.addEventListener('click', cycle);
    apply();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire); else wire();
})();
