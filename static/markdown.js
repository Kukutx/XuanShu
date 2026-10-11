'use strict';
// Minimal Markdown renderer for model answers. It builds DOM nodes directly
// (never innerHTML), so text from the model can only ever become text.
// Supported: headings, paragraphs, bullet / numbered lists (two levels),
// block quotes, fenced code, pipe tables, horizontal rules, **bold**, *italic*,
// `code` and http(s) links.
(function () {
  const INLINE = /(\*\*([^*]+?)\*\*|__([^_]+?)__|`([^`]+?)`|\[([^\]]+?)\]\((https?:\/\/[^\s)]+)\)|(?<![\w*])\*([^*\s][^*]*?)\*(?![\w*])|(?<![\w_])_([^_\s][^_]*?)_(?![\w_]))/;

  function inline(parent, text) {
    let rest = text;
    while (rest) {
      const match = INLINE.exec(rest);
      if (!match) {parent.append(rest); break;}
      if (match.index) parent.append(rest.slice(0, match.index));
      if (match[2] || match[3]) {
        const strong = document.createElement('strong');
        inline(strong, match[2] || match[3]);
        parent.append(strong);
      } else if (match[4]) {
        const code = document.createElement('code');
        code.textContent = match[4];
        parent.append(code);
      } else if (match[5]) {
        const link = document.createElement('a');
        link.href = match[6]; link.target = '_blank'; link.rel = 'noopener noreferrer nofollow';
        link.textContent = match[5];
        parent.append(link);
      } else {
        const em = document.createElement('em');
        inline(em, match[7] || match[8]);
        parent.append(em);
      }
      rest = rest.slice(match.index + match[0].length);
    }
  }

  const isTableRow = line => /^\s*\|.*\|\s*$/.test(line);
  const isTableRule = line => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(line);
  const cells = line => line.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
  const listItem = line => /^(\s*)([-*+]|\d{1,3}[.)])\s+(.*)$/.exec(line);

  function render(source, container) {
    const root = container || document.createElement('div');
    root.replaceChildren();
    const lines = String(source || '').replace(/\r\n?/g, '\n').split('\n');
    let i = 0;
    let paragraph = [];
    const flush = () => {
      if (!paragraph.length) return;
      const p = document.createElement('p');
      paragraph.forEach((line, n) => {if (n) p.append(document.createElement('br')); inline(p, line);});
      root.append(p); paragraph = [];
    };
    while (i < lines.length) {
      const line = lines[i];
      const fence = /^\s*(```|~~~)(.*)$/.exec(line);
      if (fence) {
        flush();
        const body = [];
        i++;
        while (i < lines.length && !lines[i].trim().startsWith(fence[1])) body.push(lines[i++]);
        i++;
        const pre = document.createElement('pre'); const code = document.createElement('code');
        code.textContent = body.join('\n'); pre.append(code); root.append(pre);
        continue;
      }
      if (!line.trim()) {flush(); i++; continue;}
      const heading = /^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$/.exec(line);
      if (heading) {
        flush();
        const h = document.createElement('h' + Math.min(4, heading[1].length + 1));
        inline(h, heading[2]); root.append(h); i++; continue;
      }
      if (/^\s{0,3}([-*_])(\s*\1){2,}\s*$/.test(line)) {flush(); root.append(document.createElement('hr')); i++; continue;}
      if (isTableRow(line) && i + 1 < lines.length && isTableRule(lines[i + 1])) {
        flush();
        const table = document.createElement('table');
        const head = table.createTHead().insertRow();
        cells(line).forEach(c => {const th = document.createElement('th'); inline(th, c); head.append(th);});
        const body = table.createTBody();
        i += 2;
        while (i < lines.length && isTableRow(lines[i])) {
          const row = body.insertRow();
          cells(lines[i]).forEach(c => inline(row.insertCell(), c));
          i++;
        }
        root.append(table); continue;
      }
      if (/^\s{0,3}>/.test(line)) {
        flush();
        const quote = [];
        while (i < lines.length && /^\s{0,3}>/.test(lines[i])) quote.push(lines[i++].replace(/^\s{0,3}>\s?/, ''));
        const block = document.createElement('blockquote');
        render(quote.join('\n'), block);
        root.append(block); continue;
      }
      const item = listItem(line);
      if (item) {
        flush();
        const stack = [];
        while (i < lines.length) {
          const current = listItem(lines[i]);
          if (!current) {
            // A wrapped continuation line belongs to the previous item.
            if (lines[i].trim() && /^\s+/.test(lines[i]) && stack.length) {
              const last = stack[stack.length - 1].list.lastElementChild;
              last.append(' '); inline(last, lines[i].trim()); i++; continue;
            }
            break;
          }
          const depth = current[1].replace(/\t/g, '    ').length >= 2 && stack.length ? 1 : 0;
          const ordered = /\d/.test(current[2]);
          while (stack.length > depth + 1) stack.pop();
          if (stack.length === depth) {
            const list = document.createElement(ordered ? 'ol' : 'ul');
            if (ordered && parseInt(current[2], 10) > 1) list.start = parseInt(current[2], 10);
            if (depth && stack[0].list.lastElementChild) stack[0].list.lastElementChild.append(list); else root.append(list);
            stack.push({list});
          }
          const li = document.createElement('li');
          inline(li, current[3]);
          stack[depth].list.append(li);
          i++;
        }
        continue;
      }
      paragraph.push(line.trim());
      i++;
    }
    flush();
    return root;
  }

  // Plain text for clipboard and exports.
  window.XuanShuMarkdown = {render};
})();
