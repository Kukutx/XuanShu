'use strict';
// Date and date-time fields open the project's own calendar in place of the browser's picker, which ignores the
// colour theme, cannot show lunar dates and looks different in every browser. The field stays a native date input:
// typing, the form value, validation and min/max work as before. The calendar icon, Alt+↓ and F4 open this calendar
// instead. A touch-only device keeps the browser's own picker, the one people expect there.
// Each day shows what the month calendar shows (lunar day, solar term, festival), from the same /api/calendar months.
(() => {
  const FIELD = 'input[type=date],input[type=datetime-local]';
  const MIN = '1901-01-01', MAX = '2099-12-31';
  const ICON_ZONE = 22;  // px at the field's end where the calendar icon sits (its size is set in style.css)
  let box = null, field = null, view = null, picked = '', cursor = '', time = null, frame = 0, downWhileOpen = false, watch = null;

  const lang = () => typeof calLang === 'function' ? calLang() : 'zh-CN';
  const t = text => typeof calT === 'function' ? calT(text) : text;
  const pad = n => String(n).padStart(2, '0');
  const iso = (y, m, d) => {const day = new Date(Date.UTC(y, m - 1, d)); return day.getUTCFullYear() + '-' + pad(day.getUTCMonth() + 1) + '-' + pad(day.getUTCDate());};
  const parts = day => [Number(day.slice(0, 4)), Number(day.slice(5, 7)), Number(day.slice(8, 10))];
  const shift = (day, days) => {const [y, m, d] = parts(day); return iso(y, m, d + days);};
  const utc = day => {const [y, m, d] = parts(day); return new Date(Date.UTC(y, m - 1, d));};
  const daysIn = (y, m) => new Date(Date.UTC(y, m, 0)).getUTCDate();
  const today = () => typeof localToday === 'function' ? localToday() : new Date().toISOString().slice(0, 10);
  const isDay = value => /^\d{4}-\d{2}-\d{2}$/.test(value);
  const bounds = () => {
    const lo = (field.min || '').slice(0, 10), hi = (field.max || '').slice(0, 10);
    return [isDay(lo) && lo > MIN ? lo : MIN, isDay(hi) && hi < MAX ? hi : MAX];
  };
  const clamp = day => {const [lo, hi] = bounds(); return day < lo ? lo : day > hi ? hi : day;};
  const withTime = () => field.type === 'datetime-local';
  const fmt = (day, options) => utc(day).toLocaleDateString(lang(), {...options, timeZone: 'UTC'});
  // 子时 runs 23:00–00:59, 丑时 01:00–02:59 and so on.
  const SHICHEN = ['子时', '丑时', '寅时', '卯时', '辰时', '巳时', '午时', '未时', '申时', '酉时', '戌时', '亥时'];
  const shichen = hour => t(SHICHEN[Math.floor((hour + 1) / 2) % 12]);
  // The birth time is read as solar time when the birth form says so, and the hour pillar follows that; the label
  // here names the clock's 时辰 and says so. With the hour unknown there is none to name.
  const hourName = hour => {
    if (field.id !== 'birth_datetime') return shichen(hour);
    const unknown = document.getElementById('hour_unknown'), mode = document.getElementById('time_mode');
    if (unknown && unknown.checked) return '';
    return shichen(hour) + (mode && mode.value !== 'clock' ? ' · ' + t('钟表时间') : '');
  };
  // Where a select's list is open, Escape and Enter belong to the list (a browser without :open has no such list).
  const listOpen = node => {try {return node.matches(':open');} catch (err) {return false;}};
  // A redraw of the page may have replaced the field meanwhile; the new one carries the same id.
  const current = () => {
    if (field && !field.isConnected && field.id) field = document.getElementById(field.id) || field;
    return field && field.isConnected ? field : null;
  };
  // 2024年 / 2024: two hundred of these per drawing, so each language's names are made once.
  const yearNames = {};
  const yearName = y => ((yearNames[lang()] = yearNames[lang()] || {})[y] = yearNames[lang()][y] || fmt(iso(y, 1, 1), {year: 'numeric'}));

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function ensureBox() {
    if (box) return box;
    box = el('div', 'xs-dp');
    box.id = 'xs-datepicker';
    box.setAttribute('role', 'dialog');
    // Modal while open: Tab goes round its own controls, and Escape or a choice hands focus back to the field.
    box.setAttribute('aria-modal', 'true');
    // Every word in it is written in the interface language here, so the page translator leaves it alone.
    box.setAttribute('data-no-i18n', '');
    if (typeof box.showPopover === 'function') box.popover = 'auto';
    // A light dismiss (a click elsewhere, Escape) closes the popover without passing through close().
    box.addEventListener('toggle', e => {if (e.newState === 'closed' && !box.matches(':popover-open')) cleanUp();});
    box.addEventListener('keydown', onKey);
    box.addEventListener('click', onClick);
    box.addEventListener('change', onChange);
    return box;
  }

  function open(input) {
    if (input.disabled || input.readOnly) return;
    field = input;
    const value = input.value, day = value.slice(0, 10);
    picked = isDay(day) ? day : '';
    cursor = clamp(picked || today());
    // A value outside the allowed range is not shown, so it is not what 确定 would keep either.
    if (picked && picked !== cursor) picked = '';
    if (withTime() && !picked) picked = cursor;
    time = withTime() ? (/^\d{2}:\d{2}/.test(value.slice(11)) ? value.slice(11, 16) : '12:00') : null;
    view = {year: parts(cursor)[0], month: parts(cursor)[1]};
    ensureBox();
    // Inside an open modal dialog the calendar has to sit in it: the rest of the page is inert meanwhile.
    const host = input.closest('dialog[open]') || document.body;
    if (box.parentElement !== host) host.append(box);
    box.setAttribute('aria-label', t(withTime() ? '选择日期和时间' : '选择日期'));
    draw();
    if (box.popover) box.showPopover(); else box.hidden = false;
    box.classList.add('is-open');
    place();
    // A sheet along the bottom of a narrow window would cover a field low on the page, so the page moves it up.
    if (box.classList.contains('is-sheet')) {
      const r = input.getBoundingClientRect(), room = innerHeight - box.offsetHeight - 8;
      if (r.bottom > room) scrollBy(0, r.bottom - room);
    }
    focusCursor();
    addEventListener('scroll', onMove, true);
    addEventListener('resize', onMove);
    // The page may redraw under it: the calendar follows its field, grows with the lunar lines, and closes when the
    // field is gone or hidden (another tool was opened).
    watch = watch || new MutationObserver(onMove);
    watch.observe(document.body, {childList: true, subtree: true});
  }
  function close(refocus = false) {
    if (!box || !box.classList.contains('is-open')) return;
    const from = current();
    if (box.popover && box.matches(':popover-open')) box.hidePopover();
    cleanUp();
    if (refocus && from) from.focus();
  }
  function cleanUp() {
    if (!box.classList.contains('is-open')) return;
    box.classList.remove('is-open');
    if (!box.popover) box.hidden = true;
    removeEventListener('scroll', onMove, true);
    removeEventListener('resize', onMove);
    if (watch) watch.disconnect();
  }
  function commit(day) {
    const target = current();
    const value = withTime() ? day + 'T' + time : day;
    close(true);
    if (!target || target.value === value) return;
    target.value = value;
    target.dispatchEvent(new Event('input', {bubbles: true}));
    target.dispatchEvent(new Event('change', {bubbles: true}));
    if (document.activeElement !== target) target.focus();
  }

  // Below the field, else above it, else beside it, so the field stays in view; a narrow window gets a sheet along
  // the bottom edge.
  function place() {
    const input = current();
    if (!input || !input.getClientRects().length) {close(); return;}
    const sheet = innerWidth < 480;
    box.classList.toggle('is-sheet', sheet);
    if (sheet) {box.style.left = box.style.top = ''; return;}
    const r = input.getBoundingClientRect(), w = box.offsetWidth, h = box.offsetHeight, gap = 6, edge = 8;
    const fitTop = y => Math.min(Math.max(edge, y), innerHeight - h - edge);
    let left = Math.min(Math.max(edge, r.left), innerWidth - w - edge), top;
    if (r.bottom + gap + h <= innerHeight - edge) top = r.bottom + gap;
    else if (r.top - gap - h >= edge) top = r.top - gap - h;
    else if (r.right + gap + w <= innerWidth - edge) {left = r.right + gap; top = fitTop(r.top - h / 3);}
    else if (r.left - gap - w >= edge) {left = r.left - gap - w; top = fitTop(r.top - h / 3);}
    else top = fitTop(r.bottom + gap);
    box.style.left = Math.round(left) + 'px';
    box.style.top = Math.round(top) + 'px';
  }
  function onMove() {
    if (frame) return;
    frame = requestAnimationFrame(() => {frame = 0; if (box.classList.contains('is-open')) place();});
  }

  function draw() {
    const [lo, hi] = bounds(), now = today(), {year, month} = view, locale = lang();
    box.replaceChildren();
    const head = box.appendChild(el('div', 'xs-dp-head'));
    const nav = (step, label) => {
      const b = el('button', 'xs-dp-nav ' + (step < 0 ? 'is-prev' : 'is-next'));
      b.type = 'button'; b.dataset.step = String(step); b.setAttribute('aria-label', t(label));
      const edge = step < 0 ? iso(year, month, 0) < lo : iso(year, month + 1, 1) > hi;
      b.disabled = edge;
      return b;
    };
    head.append(nav(-1, '上个月'));
    const years = el('select', 'xs-dp-year'), months = el('select', 'xs-dp-month');
    years.setAttribute('aria-label', t('公历年份')); months.setAttribute('aria-label', t('公历月份'));
    for (let y = Number(lo.slice(0, 4)); y <= Number(hi.slice(0, 4)); y++) {
      const option = el('option', null, yearName(y)); option.value = String(y); years.append(option);
    }
    for (let m = 1; m <= 12; m++) {
      // 1月, not 一月: a Chinese month name would read as the lunar month written in the day cells.
      const option = el('option', null, locale === 'en' ? fmt(iso(2000, m, 1), {month: 'short'}) : m + '月'); option.value = String(m);
      option.disabled = iso(year, m + 1, 0) < lo || iso(year, m, 1) > hi;
      months.append(option);
    }
    years.value = String(year); months.value = String(month);
    head.append(years, months, nav(1, '下个月'));

    const table = box.appendChild(el('table', 'xs-dp-grid'));
    table.setAttribute('role', 'grid');
    table.setAttribute('aria-label', fmt(iso(year, month, 1), {year: 'numeric', month: 'long'}));
    const headRow = table.appendChild(el('thead')).appendChild(el('tr'));
    const short = locale === 'en' ? CAL_WEEKDAYS_EN : (CAL_WEEKDAYS[locale] || CAL_WEEKDAYS['zh-CN']);
    short.forEach((name, i) => {
      const th = headRow.appendChild(el('th', i > 4 ? 'is-weekend' : null, name));
      th.scope = 'col';
      th.setAttribute('aria-label', fmt(iso(2024, 1, 1 + i), {weekday: 'long'}));  // 2024-01-01 was a Monday
    });
    const body = table.appendChild(el('tbody'));
    const first = iso(year, month, 1), lead = (utc(first).getUTCDay() + 6) % 7;
    let day = shift(first, -lead);
    // Always six weeks, so the calendar keeps its size from month to month.
    for (let week = 0; week < 6; week++) {
      const row = body.appendChild(el('tr'));
      for (let i = 0; i < 7; i++, day = shift(day, 1)) {
        const cell = row.appendChild(el('td'));
        cell.setAttribute('role', 'gridcell');
        const button = cell.appendChild(el('button', 'xs-dp-day'));
        button.type = 'button'; button.dataset.day = day; button.tabIndex = day === cursor ? 0 : -1;
        button.append(el('span', 'xs-dp-num', String(parts(day)[2])));
        if (i > 4) button.classList.add('is-weekend');
        if (parts(day)[1] !== month) button.classList.add('is-outside');
        if (day === now) {button.classList.add('is-today'); button.setAttribute('aria-current', 'date');}
        cell.setAttribute('aria-selected', String(day === picked));
        button.disabled = day < lo || day > hi;
        label(button, day, null);
      }
    }
    if (withTime()) {
      const row = box.appendChild(el('div', 'xs-dp-time'));
      const [hour, minute] = time.split(':').map(Number);
      const hours = el('select', 'xs-dp-hour'), minutes = el('select', 'xs-dp-minute');
      hours.setAttribute('aria-label', t('小时')); minutes.setAttribute('aria-label', t('分钟（时间）'));
      for (let h = 0; h < 24; h++) {const o = el('option', null, pad(h)); o.value = pad(h); hours.append(o);}
      for (let m = 0; m < 60; m++) {const o = el('option', null, pad(m)); o.value = pad(m); minutes.append(o);}
      hours.value = pad(hour); minutes.value = pad(minute);
      const zone = el('span', 'xs-dp-shichen', hourName(hour));
      zone.setAttribute('aria-live', 'polite');
      zone.hidden = !zone.textContent;
      row.append(el('span', 'xs-dp-time-label', t('时间')), hours, el('span', 'xs-dp-colon', ':'), minutes, zone);
    }
    const foot = box.appendChild(el('div', 'xs-dp-foot'));
    const go = el('button', 'tiny-button xs-dp-today', t('今天')); go.type = 'button';
    go.disabled = now < lo || now > hi;
    foot.append(go);
    if (withTime()) {
      const actions = foot.appendChild(el('span', 'xs-dp-actions'));
      const cancel = el('button', 'tiny-button xs-dp-cancel', t('取消')); cancel.type = 'button';
      const ok = el('button', 'tiny-button xs-dp-ok', t('确定')); ok.type = 'button';
      actions.append(cancel, ok);
    }
    fillLunar();
  }
  // The lunar line of each day, once its month has come from the server (months the month calendar already loaded
  // are not asked for again). Without it the calendar still works, with Gregorian days only.
  function fillLunar() {
    if (typeof calendarMonths === 'undefined' || typeof ensureCalendarMonth !== 'function') return;
    const key = view.year + '-' + pad(view.month);
    const known = () => {
      box.querySelectorAll('.xs-dp-day').forEach(button => {
        const data = calendarMonths[button.dataset.day.slice(0, 7)];
        const d = data && data.days && data.days[parts(button.dataset.day)[2] - 1];
        if (d && !button.querySelector('.xs-dp-lunar')) label(button, button.dataset.day, d);
      });
    };
    known();
    if (calendarMonths[key] && calendarMonths[key].days) return;
    // The month calendar's own loader: a month on its way for either is asked for once.
    ensureCalendarMonth(view.year, view.month).then(() => {
      if (box.classList.contains('is-open') && view.year + '-' + pad(view.month) === key) known();
    });
  }
  // The day's full name for a screen reader: the date, then its lunar date, festivals and solar term.
  function label(button, day, d) {
    const sep = {en: ', ', ja: '、'}[lang()] || '，';
    let words = '';
    if (d && typeof calendarCellText === 'function') {
      const cell = calendarCellText(d);
      button.appendChild(el('span', 'xs-dp-lunar', cell.text));
      button.classList.add('xs-dp-k-' + cell.kind);
      words = [...new Set([lunarDateText(d.lunar), ...marksOf(d).map(m => t(m.name)), ...d.solar_terms.map(term => t(term.name))])].join(sep);
    }
    button.setAttribute('aria-label', fmt(day, {year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'}) + (words ? sep + words : ''));
  }

  function focusCursor() {
    const button = box.querySelector('.xs-dp-day[data-day="' + cursor + '"]');
    if (button) button.focus({preventScroll: true});
  }
  // Moves the keyboard focus to another day, turning the month when that day is outside it.
  function moveTo(day) {
    day = clamp(day);
    cursor = day;
    const [y, m] = parts(day);
    if (y !== view.year || m !== view.month) {view = {year: y, month: m}; draw();}
    else box.querySelectorAll('.xs-dp-day').forEach(b => {b.tabIndex = b.dataset.day === day ? 0 : -1;});
    focusCursor();
  }
  function turnMonth(step) {
    const [y, m, d] = parts(cursor);
    const target = new Date(Date.UTC(y, m - 1 + step, 1));
    const ty = target.getUTCFullYear(), tm = target.getUTCMonth() + 1;
    return iso(ty, tm, Math.min(d, daysIn(ty, tm)));
  }
  function pick(day) {
    if (!withTime()) {commit(day); return;}
    picked = day; cursor = day;
    const [y, m] = parts(day);
    if (y !== view.year || m !== view.month) {view = {year: y, month: m}; draw();}
    else box.querySelectorAll('.xs-dp-day').forEach(b => {
      b.tabIndex = b.dataset.day === day ? 0 : -1;
      b.parentElement.setAttribute('aria-selected', String(b.dataset.day === day));
    });
    focusCursor();
  }

  function onClick(e) {
    const button = e.target.closest('button');
    if (!button || button.disabled) return;
    if (button.classList.contains('xs-dp-day')) pick(button.dataset.day);
    else if (button.classList.contains('xs-dp-nav')) {
      cursor = clamp(turnMonth(Number(button.dataset.step)));
      view = {year: parts(cursor)[0], month: parts(cursor)[1]};
      draw();
      // At the end of the range the pressed button is now disabled, and focus moves to the year beside it.
      const again = box.querySelector('.xs-dp-nav.' + (button.classList.contains('is-prev') ? 'is-prev' : 'is-next'));
      (again.disabled ? box.querySelector('.xs-dp-year') : again).focus();
    } else if (button.classList.contains('xs-dp-today')) pick(clamp(today()));
    else if (button.classList.contains('xs-dp-ok')) commit(picked || cursor);
    else if (button.classList.contains('xs-dp-cancel')) close(true);
  }
  function onChange(e) {
    const target = e.target;
    if (target.matches('.xs-dp-year, .xs-dp-month')) {
      const y = Number(box.querySelector('.xs-dp-year').value), m = Number(box.querySelector('.xs-dp-month').value);
      cursor = clamp(iso(y, m, Math.min(parts(cursor)[2], daysIn(y, m))));
      view = {year: parts(cursor)[0], month: parts(cursor)[1]};
      const which = target.classList.contains('xs-dp-year') ? '.xs-dp-year' : '.xs-dp-month';
      draw();
      box.querySelector(which).focus();
    } else if (target.matches('.xs-dp-hour, .xs-dp-minute')) {
      time = box.querySelector('.xs-dp-hour').value + ':' + box.querySelector('.xs-dp-minute').value;
      const zone = box.querySelector('.xs-dp-shichen');
      zone.textContent = hourName(Number(time.slice(0, 2)));
      zone.hidden = !zone.textContent;
    }
  }
  function onKey(e) {
    if (e.key === 'Escape') {
      // Escape in an open year, month or time list closes that list only.
      const list = e.target.closest && e.target.closest('select');
      if (list && listOpen(list)) return;
      e.preventDefault(); e.stopPropagation(); close(true); return;
    }
    if (e.key === 'Tab') {
      // The days are one stop (arrow keys move among them), so the ring is the controls that take Tab.
      const stops = [...box.querySelectorAll('button, select')].filter(x => !x.disabled && x.tabIndex >= 0);
      const at = (e.target.closest && e.target.closest('select')) || e.target;
      if (!stops.length) return;
      if (e.shiftKey && at === stops[0]) {e.preventDefault(); stops[stops.length - 1].focus();}
      else if (!e.shiftKey && at === stops[stops.length - 1]) {e.preventDefault(); stops[0].focus();}
      return;
    }
    const day = e.target.closest && e.target.closest('.xs-dp-day');
    if (!day) {
      if (e.key === 'Enter' && withTime() && e.target.matches('.xs-dp-hour, .xs-dp-minute') && !listOpen(e.target)) {e.preventDefault(); commit(picked || cursor);}
      return;
    }
    // Alt+← is the browser's Back, Ctrl/⌘ with an arrow its own shortcuts: those are left alone.
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    const steps = {ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7};
    const weekday = (utc(cursor).getUTCDay() + 6) % 7;
    let next = null;
    if (e.key in steps) next = shift(cursor, steps[e.key]);
    else if (e.key === 'Home') next = shift(cursor, -weekday);
    else if (e.key === 'End') next = shift(cursor, 6 - weekday);
    else if (e.key === 'PageUp' || e.key === 'PageDown') next = turnMonth((e.key === 'PageUp' ? -1 : 1) * (e.shiftKey ? 12 : 1));
    if (next === null) return;
    e.preventDefault();
    moveTo(next);
  }

  // The browser's picker would open from a click on the icon (and, in some browsers, anywhere on the field) or from
  // Alt+↓ / F4; those open this calendar instead. Clicks on the date and time segments still place the caret there.
  const fine = () => typeof matchMedia !== 'function' || matchMedia('(any-pointer: fine)').matches;
  document.addEventListener('click', e => {
    const input = e.target instanceof Element && e.target.closest(FIELD);
    if (!input || !fine()) return;
    e.preventDefault();
    const r = input.getBoundingClientRect(), cs = getComputedStyle(input);
    const end = r.right - parseFloat(cs.borderRightWidth) - parseFloat(cs.paddingRight);
    const onIcon = e.clientX >= end - ICON_ZONE && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom;
    // A click on the field while its calendar is open closes the calendar (the press outside it already began to);
    // it does not open it again.
    if (downWhileOpen) {downWhileOpen = false; close(true); return;}
    if (onIcon) open(input);
  }, true);
  document.addEventListener('pointerdown', e => {
    downWhileOpen = !!(box && box.classList.contains('is-open') && field && e.target === field);
  }, true);
  // Focus that moves anywhere outside the calendar (Tab, a click on another field) closes it.
  document.addEventListener('focusin', e => {
    if (box && box.classList.contains('is-open') && e.target instanceof Node && !box.contains(e.target)) close();
  });
  document.addEventListener('keydown', e => {
    const input = e.target instanceof Element && e.target.matches(FIELD) ? e.target : null;
    if (!input || !((e.altKey && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) || e.key === 'F4')) return;
    e.preventDefault();
    open(input);
  }, true);
  // The shortcut is announced on the field itself, set the first time it is reached.
  document.addEventListener('focusin', e => {
    const input = e.target instanceof Element && e.target.matches(FIELD) ? e.target : null;
    if (input && !input.hasAttribute('aria-keyshortcuts')) input.setAttribute('aria-keyshortcuts', 'Alt+ArrowDown');
  });
  document.addEventListener('xuanshu-language', () => close());
})();
