'use strict';
// Hover, focus and tap hints in the project's own style, replacing the browser's title tooltips: those ignore the
// colour theme, wait about a second, never appear for keyboard focus and cannot be opened on a touch screen.
// An element carries its hint in data-tip, which i18n.js translates like any other interface attribute.
(() => {
  const SHOW_DELAY = 350;  // ms of hovering before a hint appears
  const WARM_MS = 500;     // moving straight on to the next hint shows it at once
  // A tap on these does something else, so a tap never pins their hint (hover and focus still show it).
  const INTERACTIVE = 'a[href],button,input,select,textarea,summary,label,[role="button"],[role="tab"],[role="option"],[contenteditable]';
  let box = null, target = null, pending = null, timer = 0, lastHide = 0, pinned = false, watcher = null, frame = 0;

  function ensureBox() {
    if (box) return box;
    box = document.createElement('div');
    box.id = 'xs-tip'; box.className = 'xs-tip'; box.setAttribute('role', 'tooltip'); box.hidden = true;
    box.setAttribute('data-no-i18n', '');  // its text is copied from a data-tip that is already translated
    // In the top layer where supported, so a hint inside an open dialog is not drawn underneath it.
    if (typeof box.showPopover === 'function') box.popover = 'manual';
    document.body.append(box);
    return box;
  }
  function place(el) {
    const r = el.getBoundingClientRect(), gap = 8, edge = 8;
    const vw = document.documentElement.clientWidth, vh = document.documentElement.clientHeight;
    box.style.left = '0px'; box.style.top = '0px';
    const w = box.offsetWidth, h = box.offsetHeight;
    // Above the element when there is room, otherwise below; kept inside the window.
    let top = r.top - h - gap, side = 'above';
    if (top < edge && r.bottom + gap + h <= vh - edge) {top = r.bottom + gap; side = 'below';}
    top = Math.min(Math.max(edge, top), vh - h - edge);
    const left = Math.min(Math.max(edge, r.left + r.width / 2 - w / 2), vw - w - edge);
    box.style.left = Math.round(left) + 'px'; box.style.top = Math.round(top) + 'px';
    box.dataset.side = side;
  }
  function describe(el, on) {
    // While the hint shows, screen readers read it as the element's description.
    const ids = (el.getAttribute('aria-describedby') || '').split(/\s+/).filter(id => id && id !== 'xs-tip');
    if (on) ids.push('xs-tip');
    if (ids.length) el.setAttribute('aria-describedby', ids.join(' ')); else el.removeAttribute('aria-describedby');
  }
  function show(el, pin = false) {
    clearTimeout(timer); pending = null;
    const text = el.getAttribute('data-tip');
    if (!text || !el.isConnected) return;
    if (target && target !== el) describe(target, false);
    ensureBox();
    target = el; pinned = pin;
    box.textContent = text;
    box.hidden = false;
    if (box.popover) {  // re-shown each time, so it also lands above a dialog opened since the last hint
      try {box.hidePopover();} catch (_) {}
      try {box.showPopover();} catch (_) {}
    }
    place(el);
    describe(el, true);
    // A re-render can remove the element under the hint; the hint goes with it.
    if (!watcher) watcher = new MutationObserver(() => {if (target && !target.isConnected) hide();});
    watcher.observe(document.body, {childList: true, subtree: true});
  }
  function hide() {
    clearTimeout(timer); pending = null;
    if (watcher) watcher.disconnect();
    if (!target) return;
    if (target.isConnected) describe(target, false);
    if (box.popover) {try {box.hidePopover();} catch (_) {}}
    box.hidden = true; target = null; pinned = false; lastHide = Date.now();
  }
  const tipOf = node => node instanceof Element ? node.closest('[data-tip]') : null;

  document.addEventListener('pointerover', e => {
    if (e.pointerType === 'touch') return;
    const el = tipOf(e.target);
    if (!el || el === target || el === pending || pinned) return;
    clearTimeout(timer);
    const warm = target !== null || Date.now() - lastHide < WARM_MS;
    if (target) hide();
    pending = el;
    timer = setTimeout(() => show(el), warm ? 0 : SHOW_DELAY);
  });
  document.addEventListener('pointerout', e => {
    if (e.pointerType === 'touch' || pinned) return;
    const el = tipOf(e.target);
    if (!el || (e.relatedTarget instanceof Node && el.contains(e.relatedTarget))) return;
    if (el === pending) {clearTimeout(timer); pending = null;}
    if (el === target) hide();
  });
  document.addEventListener('focusin', e => {
    const el = e.target;
    if (!(el instanceof Element) || !el.hasAttribute('data-tip')) return;
    let keyboard = true;
    try {keyboard = el.matches(':focus-visible');} catch (_) {}
    if (keyboard) show(el);
  });
  document.addEventListener('focusout', e => {if (e.target === target && !pinned) hide();});
  document.addEventListener('pointerdown', e => {if (target && tipOf(e.target) !== target) hide();}, true);
  document.addEventListener('click', e => {
    const el = tipOf(e.target);
    if (!el) return;
    // Pressing a button that has a hint acts on it; the hint goes away.
    if (e.target.closest(INTERACTIVE)) {if (target) hide(); return;}
    // A plain label, mark or cell opens its hint on a tap or click, and closes it on the next one.
    if (el === target && pinned) hide(); else show(el, true);
  });
  document.addEventListener('keydown', e => {if (e.key === 'Escape' && target) hide();}, true);
  // Scrolling (including the scroll that brings a newly focused field into view) moves the hint with its element.
  window.addEventListener('scroll', () => {
    if (!target || frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      if (!target) return;
      const r = target.getBoundingClientRect();
      if (r.bottom < 0 || r.top > document.documentElement.clientHeight) hide(); else place(target);
    });
  }, {capture: true, passive: true});
  window.addEventListener('resize', () => {if (target) hide();});
  document.addEventListener('xuanshu-language', () => {if (target) hide();});
})();
