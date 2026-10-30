'use strict';
// API reference at /docs. FastAPI's Swagger UI needs CDN scripts and an inline script that the
// Content-Security-Policy blocks, so this page reads /openapi.json itself. Every node is built with
// DOM methods; nothing from the schema is parsed as HTML. Bodies typed into "试一试" stay in the page.
(function () {
  const list = document.getElementById('api-list');
  const filter = document.getElementById('api-filter');
  const count = document.getElementById('api-count');
  const groupsNav = document.getElementById('api-groups');
  const schemaSection = document.querySelector('.api-schemas');
  const schemaBox = document.getElementById('api-schemas-list');
  const tokenInput = document.getElementById('api-token');  // never stored
  const METHODS = ['get', 'post', 'put', 'patch', 'delete'];
  // A long-lived event stream and a session close: an MCP client is the right tool for both.
  const NO_TRY = new Set(['get /mcp', 'delete /mcp']);
  const MAX_SHOWN = 200000;
  let components = {};
  const cards = [];

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }
  function refName(schema) {return schema && schema.$ref ? schema.$ref.split('/').pop() : '';}
  function resolve(schema) {
    let s = schema || {}, guard = 0;
    while (s.$ref && guard++ < 20) s = components[refName(s)] || {};
    return s;
  }
  function schemaLink(name) {
    const a = el('a', 'api-ref', name);
    a.href = '#schema-' + name;
    return a;
  }
  function typeNode(schema) {
    const box = el('code', 'api-type');
    (function walk(s, into) {
      if (!s || !Object.keys(s).length) {into.append('any'); return;}
      if (s.$ref) {into.append(schemaLink(refName(s))); return;}
      const union = s.anyOf || s.oneOf;
      if (union) {
        const parts = union.filter(x => x.type !== 'null');
        parts.forEach((p, i) => {if (i) into.append(' | '); walk(p, into);});
        if (parts.length < union.length) into.append(' | null');
        return;
      }
      if (s.allOf && s.allOf.length === 1) {walk(s.allOf[0], into); return;}
      if (s.type === 'array') {walk(s.items, into); into.append('[]'); return;}
      if (s.type === 'object' && s.additionalProperties && typeof s.additionalProperties === 'object') {
        into.append('object<string, '); walk(s.additionalProperties, into); into.append('>'); return;
      }
      into.append((s.type || 'any') + (s.format ? ' (' + s.format + ')' : ''));
    })(schema, box);
    return box;
  }
  function rule(label, value) {
    const span = el('span', 'api-rule');
    span.append(el('span', '', label), el('code', '', value));
    return span;
  }
  function between(low, high) {
    if (low !== undefined && high !== undefined) return low + '–' + high;
    return low !== undefined ? '≥ ' + low : '≤ ' + high;
  }
  function rules(schema) {
    const out = [];
    const options = schema.anyOf ? schema.anyOf.filter(x => x.type !== 'null') : [schema];
    options.forEach(o => {
      if (o.minLength !== undefined || o.maxLength !== undefined) out.push(rule('长度', between(o.minLength, o.maxLength)));
      const low = o.minimum !== undefined ? o.minimum : o.exclusiveMinimum, high = o.maximum !== undefined ? o.maximum : o.exclusiveMaximum;
      if (low !== undefined || high !== undefined) {
        const text = o.exclusiveMinimum !== undefined && o.minimum === undefined
          ? '> ' + o.exclusiveMinimum + (high !== undefined ? ', ≤ ' + high : '') : between(low, high);
        out.push(rule('范围', text));
      }
      if (o.minItems !== undefined || o.maxItems !== undefined) out.push(rule('条数', between(o.minItems, o.maxItems)));
      if (o.enum) out.push(rule('可选值', o.enum.join(' / ')));
    });
    if ('default' in schema) out.push(rule('默认值', JSON.stringify(schema.default)));
    return out;
  }
  function fieldTable(schema) {
    const s = resolve(schema);
    const props = s.properties || {};
    const names = Object.keys(props);
    if (!names.length) return el('p', 'api-note', '没有固定字段。');
    const required = new Set(s.required || []);
    const table = el('table', 'api-fields');
    const head = table.createTHead().insertRow();
    ['字段', '类型', '说明'].forEach(text => {const th = el('th', '', text); th.scope = 'col'; head.append(th);});
    const body = table.createTBody();
    names.forEach(name => {
      const prop = props[name];
      const row = body.insertRow();
      const nameCell = row.insertCell();
      nameCell.className = 'api-name';
      nameCell.append(el('code', 'api-field', name));
      if (required.has(name)) nameCell.append(el('span', 'api-req', '必填'));
      const typeCell = row.insertCell();
      typeCell.className = 'api-type-cell';
      typeCell.append(typeNode(prop));
      const desc = row.insertCell();
      desc.className = 'api-desc-cell';
      if (prop.description) desc.append(el('span', 'api-desc-text', prop.description));
      rules(prop).forEach(r => desc.append(r));
      if (!desc.childNodes.length) desc.append(el('span', 'api-muted', '—'));
    });
    return table;
  }
  function responseList(op) {
    const ul = el('ul', 'api-responses');
    Object.entries(op.responses || {}).forEach(([code, response]) => {
      const li = el('li');
      li.append(el('span', 'api-code ' + (code[0] === '2' ? 'is-ok' : 'is-err'), code));
      li.append(el('span', '', code === '422' ? '字段校验失败' : code[0] === '2' ? '成功' : response.description || ''));
      const types = Object.keys(response.content || {});
      if (types.length) li.append(el('code', 'api-ctype', types.join(', ')));
      const name = types.length ? refName(response.content[types[0]].schema) : '';
      if (name) li.append(schemaLink(name));
      ul.append(li);
    });
    return ul;
  }

  function copyText(text, button) {
    const label = button.dataset.label || button.textContent;
    button.dataset.label = label;
    const done = ok => {
      button.textContent = ok ? '已复制' : '复制失败';
      setTimeout(() => {button.textContent = label;}, 1600);
    };
    if (navigator.clipboard && window.isSecureContext) {navigator.clipboard.writeText(text).then(() => done(true), () => done(false)); return;}
    // Plain-HTTP pages on another machine have no Clipboard API.
    const scratch = el('textarea');
    scratch.value = text;
    scratch.setAttribute('readonly', '');
    scratch.className = 'visually-hidden';
    document.body.append(scratch);
    scratch.select();
    let ok = false;
    try {ok = document.execCommand('copy');} catch (_) {ok = false;}
    scratch.remove();
    button.focus();
    done(ok);
  }
  const shellQuote = text => "'" + text.replace(/'/g, "'\\''") + "'";
  function paramExample(param) {
    const schema = param.schema || {};
    if (param.example !== undefined) return String(param.example);
    if (schema.default !== undefined) return String(schema.default);
    const now = new Date();
    if (schema.format === 'date') return [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-');
    if (param.name === 'year') return String(now.getFullYear());
    return '';
  }

  function tryPanel(entry, id) {
    const {method, path, op} = entry;
    const box = el('div', 'api-try');
    box.append(el('h4', '', '试一试'));
    if (NO_TRY.has(method + ' ' + path)) {
      box.append(el('p', 'api-note', '这个端点保持长连接或结束会话，请用 MCP 客户端连接。'));
      return box;
    }
    const inputs = [];
    (op.parameters || []).forEach((param, i) => {
      const label = el('label', 'api-param');
      const input = el('input');
      input.type = 'text';
      input.id = id + '-p' + i;
      input.value = paramExample(param);
      input.spellcheck = false;
      label.htmlFor = input.id;
      label.append(el('code', '', param.name), el('span', 'api-muted', param.in === 'path' ? '路径参数' : '查询参数'));
      if (param.required) label.append(el('span', 'api-req', '必填'));
      box.append(label, input);
      inputs.push({param, input});
    });
    const json = op.requestBody && op.requestBody.content && op.requestBody.content['application/json'];
    let textarea = null, sample = '';
    if (json) {
      sample = JSON.stringify(json.example !== undefined ? json.example : {}, null, 2);
      const label = el('label', 'api-label', '请求体（JSON，可修改）');
      textarea = el('textarea', 'api-body');
      textarea.id = id + '-body';
      textarea.spellcheck = false;
      textarea.value = sample;
      textarea.rows = Math.min(16, sample.split('\n').length + 1);
      label.htmlFor = textarea.id;
      box.append(label, textarea);
    }
    const actions = el('div', 'api-actions');
    const send = el('button', 'api-send', '发送请求');
    send.type = 'button';
    const curl = el('button', 'api-ghost', '复制 curl');
    curl.type = 'button';
    actions.append(send, curl);
    if (textarea) {
      const reset = el('button', 'api-ghost', '恢复示例');
      reset.type = 'button';
      reset.addEventListener('click', () => {textarea.value = sample; textarea.focus();});
      actions.append(reset);
    }
    const result = el('div', 'api-response');
    result.hidden = true;
    const status = el('p', 'api-status');
    status.setAttribute('role', 'status');
    const pre = el('pre', 'api-out');
    pre.tabIndex = 0;
    pre.setAttribute('aria-label', '响应内容');
    const copyOut = el('button', 'api-ghost api-copy-out', '复制响应');
    copyOut.type = 'button';
    copyOut.addEventListener('click', () => copyText(pre.textContent, copyOut));
    result.append(status, pre, copyOut);
    box.append(actions, result);

    function target() {
      let url = path;
      const query = new URLSearchParams();
      inputs.forEach(({param, input}) => {
        const value = input.value.trim();
        if (param.in === 'path') url = url.replace('{' + param.name + '}', encodeURIComponent(value));
        else if (value) query.set(param.name, value);
      });
      const q = query.toString();
      return url + (q ? '?' + q : '');
    }
    function show(ok, parts, body) {
      result.hidden = false;
      status.className = 'api-status ' + (ok ? 'is-ok' : 'is-err');
      status.replaceChildren(...parts);
      pre.hidden = !body;
      copyOut.hidden = !body;
      pre.textContent = body || '';
    }
    function readBody() {
      if (!textarea) return {body: undefined};
      try {return {body: JSON.stringify(JSON.parse(textarea.value))};}
      catch (err) {return {error: err.message};}
    }
    curl.addEventListener('click', () => {
      const parts = ['curl', '-sS'];
      if (method !== 'get') parts.push('-X', method.toUpperCase());
      parts.push(shellQuote(location.origin + target()));
      // The token itself never goes to the clipboard.
      if (tokenInput.value.trim()) parts.push('-H', '"Authorization: Bearer $MCP_BEARER_TOKEN"');
      if (textarea) {
        const read = readBody();
        parts.push('-H', shellQuote('Content-Type: application/json'), '-d', shellQuote(read.body || textarea.value.trim()));
      }
      copyText(parts.join(' '), curl);
    });
    send.addEventListener('click', async () => {
      if (send.getAttribute('aria-disabled') === 'true') return;
      const read = readBody();
      if (read.error) {
        show(false, [el('b', '', 'JSON 格式有误：'), el('span', '', read.error)], '');
        textarea.focus();
        return;
      }
      const missing = inputs.find(x => x.param.required && !x.input.value.trim());
      if (missing) {
        show(false, [el('b', '', '请先填写：'), el('code', '', missing.param.name)], '');
        missing.input.focus();
        return;
      }
      send.setAttribute('aria-disabled', 'true');
      send.textContent = '发送中…';
      const started = performance.now();
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 120000);
      try {
        const options = {method: method.toUpperCase(), signal: controller.signal, headers: {}};
        if (read.body !== undefined) {options.headers['Content-Type'] = 'application/json'; options.body = read.body;}
        if (tokenInput.value.trim()) options.headers.Authorization = 'Bearer ' + tokenInput.value.trim();
        const response = await fetch(target(), options);
        const text = await response.text();
        const ms = Math.round(performance.now() - started);
        let shown = text;
        if ((response.headers.get('content-type') || '').includes('json')) {
          try {shown = JSON.stringify(JSON.parse(text), null, 2);} catch (_) { /* show it as sent */ }
        }
        const parts = [el('b', 'api-code ' + (response.ok ? 'is-ok' : 'is-err'), String(response.status)),
          el('span', '', response.ok ? '成功' : '失败'), el('span', 'api-muted', ms + ' ms'),
          el('span', 'api-muted', (new Blob([text]).size / 1024).toFixed(1) + ' KB')];
        if (shown.length > MAX_SHOWN) {
          shown = shown.slice(0, MAX_SHOWN);
          parts.push(el('span', 'api-muted', '只显示前 200,000 个字符'));
        }
        show(response.ok, parts, shown || ' ');
      } catch (err) {
        show(false, [el('b', '', err.name === 'AbortError' ? '超过 120 秒没有响应，已停止。' : '请求没有发出：'),
          el('span', '', err.name === 'AbortError' ? '' : err.message)], '');
      } finally {
        clearTimeout(timer);
        send.removeAttribute('aria-disabled');
        send.textContent = '发送请求';
      }
    });
    return box;
  }

  function opBody(entry, id) {
    const {op} = entry;
    const body = el('div', 'api-op-body');
    if (op.description) body.append(el('p', 'api-desc', op.description));
    if ((op.parameters || []).length) {
      body.append(el('h4', '', '参数'));
      const table = fieldTable({
        type: 'object',
        properties: Object.fromEntries(op.parameters.map(p => [p.name, Object.assign({}, p.schema, p.description ? {description: p.description} : {})])),
        required: op.parameters.filter(p => p.required).map(p => p.name),
      });
      body.append(table);
    }
    const json = op.requestBody && op.requestBody.content && op.requestBody.content['application/json'];
    if (json) {
      const head = el('h4', '', '请求体');
      const name = refName(json.schema);
      if (name) {head.append(el('span', 'api-muted', ' · ')); head.append(schemaLink(name));}
      body.append(head);
      body.append(json.schema ? fieldTable(json.schema) : el('p', 'api-note', 'JSON-RPC 2.0 消息，见下方示例。'));
    }
    body.append(el('h4', '', '响应'), responseList(op), tryPanel(entry, id));
    return body;
  }

  function card(entry) {
    const {method, path, op} = entry;
    const id = 'op-' + method + path.replace(/[^A-Za-z0-9]+/g, '-').replace(/-+$/, '');
    const details = el('details', 'api-op');
    details.id = id;
    const summary = el('summary');
    summary.append(el('span', 'api-method m-' + method, method.toUpperCase()), el('code', 'api-path', path),
      el('span', 'api-title', op['x-title'] || op.summary || ''));
    details.append(summary);
    details.addEventListener('toggle', () => {
      if (!details.open) return;
      if (!details.dataset.built) {details.dataset.built = '1'; details.append(opBody(entry, id));}
      if (location.hash !== '#' + id) history.replaceState(null, '', '#' + id);
    });
    const schema = resolve(op.requestBody && op.requestBody.content && op.requestBody.content['application/json']
      && op.requestBody.content['application/json'].schema);
    const fields = Object.keys(schema.properties || {}).concat((op.parameters || []).map(p => p.name));
    cards.push({node: details, summary, hay: [method, path, op['x-title'] || '', op.summary || '', op.description || ''].concat(fields).join(' ').toLowerCase()});
    return details;
  }

  function applyFilter() {
    const q = filter.value.trim().toLowerCase();
    let shown = 0;
    cards.forEach(c => {
      const hit = !q || c.hay.includes(q) || c.summary.textContent.toLowerCase().includes(q);
      c.node.hidden = !hit;
      if (hit) shown += 1;
    });
    list.querySelectorAll('.api-group').forEach(group => {
      const visible = !!group.querySelector('.api-op:not([hidden])');
      group.hidden = !visible;
      const chip = groupsNav.querySelector('a[href="#' + group.id + '"]');
      if (chip) chip.hidden = !visible;
    });
    count.replaceChildren();
    if (!shown) {count.append(el('span', '', '没有匹配的接口。')); return;}
    count.append(el('b', '', q ? shown + ' / ' + cards.length : String(cards.length)), el('span', '', '个接口'));
  }

  function openHash() {
    const id = decodeURIComponent(location.hash.slice(1));
    const node = id && document.getElementById(id);
    if (!node || !node.closest('.api-list, .api-schemas')) return;
    if (node.closest('[hidden]') && filter.value) {filter.value = ''; applyFilter();}
    const details = node.matches('details') ? node : node.closest('details');
    if (details) details.open = true;
    node.scrollIntoView({block: 'start'});
    const summary = details && details.querySelector('summary');
    if (summary) summary.focus({preventScroll: true});
  }

  function render(spec) {
    components = (spec.components && spec.components.schemas) || {};
    const groups = new Map((spec.tags || []).map(tag => [tag.name, {tag, ops: []}]));
    Object.entries(spec.paths || {}).forEach(([path, item]) => {
      METHODS.forEach(method => {
        const op = item[method];
        if (!op) return;
        const name = (op.tags && op.tags[0]) || 'other';
        if (!groups.has(name)) groups.set(name, {tag: {name}, ops: []});
        groups.get(name).ops.push({method, path, op});
      });
    });
    list.replaceChildren();
    groupsNav.replaceChildren();
    groups.forEach(({tag, ops}) => {
      if (!ops.length) return;
      const title = tag['x-title'] || tag.name;
      const section = el('section', 'api-group');
      section.id = 'group-' + tag.name;
      const heading = el('h2', 'api-group-title');
      heading.id = section.id + '-h';
      heading.append(el('span', '', title), el('small', 'api-group-count', String(ops.length)));
      section.setAttribute('aria-labelledby', heading.id);
      section.append(heading);
      ops.forEach(entry => section.append(card(entry)));
      list.append(section);
      const chip = el('a', 'api-chip');
      chip.href = '#' + section.id;
      chip.append(el('span', '', title), el('b', '', String(ops.length)));
      groupsNav.append(chip);
    });
    schemaBox.replaceChildren();
    Object.keys(components).sort().forEach(name => {
      const details = el('details', 'api-schema');
      details.id = 'schema-' + name;
      const summary = el('summary');
      const n = Object.keys(components[name].properties || {}).length;
      summary.append(el('code', '', name), el('span', 'api-schema-n', String(n)), el('small', '', '个字段'));
      details.append(summary);
      details.addEventListener('toggle', () => {
        if (!details.open || details.dataset.built) return;
        details.dataset.built = '1';
        if (components[name].description) details.append(el('p', 'api-desc', components[name].description));
        details.append(fieldTable(components[name]));
      });
      schemaBox.append(details);
    });
    schemaSection.hidden = !schemaBox.childElementCount;
    list.setAttribute('aria-busy', 'false');
    filter.disabled = false;
    applyFilter();
    openHash();
  }

  function load() {
    list.setAttribute('aria-busy', 'true');
    fetch('/openapi.json', {headers: {Accept: 'application/json'}})
      .then(response => {if (!response.ok) throw new Error('HTTP ' + response.status); return response.json();})
      .then(render)
      .catch(err => {
        list.setAttribute('aria-busy', 'false');
        const box = el('div', 'api-error');
        box.setAttribute('role', 'alert');
        box.append(el('b', '', '接口说明读取失败：'), el('span', '', err.message));
        const retry = el('button', 'api-ghost', '重试');
        retry.type = 'button';
        retry.addEventListener('click', load);
        box.append(retry);
        list.replaceChildren(box);
      });
  }

  filter.addEventListener('input', applyFilter);
  window.addEventListener('hashchange', openHash);
  // A link to the structure already in the address bar fires no hashchange; open it anyway (it may have been closed).
  document.addEventListener('click', event => {
    const link = event.target.closest('a.api-ref');
    if (link && link.getAttribute('href') === location.hash) {event.preventDefault(); openHash();}
  });
  load();
})();
