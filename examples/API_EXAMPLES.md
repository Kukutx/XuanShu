# API & MCP sample calls

Start: `uvicorn app.main:app --host 127.0.0.1 --port 8000`

### BaZi (hidden stems / ten gods / Na Yin)

```bash
curl -s http://127.0.0.1:8000/api/bazi -H 'Content-Type: application/json' \
  -d '{"birth_datetime":"2000-08-16T04:00","timezone":"Asia/Shanghai"}'
```

### Zi Wei + four transformations

```bash
curl -s http://127.0.0.1:8000/api/ziwei -H 'Content-Type: application/json' \
  -d '{"birth_datetime":"2000-08-16T04:00","gender":"female"}'
```

### Selected palace

```bash
curl -s http://127.0.0.1:8000/api/palace -H 'Content-Type: application/json' \
  -d '{"birth":{"birth_datetime":"2000-08-16T04:00"},"palace":"命宫"}'
```

### 14 day calendar

```bash
curl -s http://127.0.0.1:8000/api/calendar -H 'Content-Type: application/json' \
  -d '{"start_date":"2024-02-04","days":14}'
```

### Structural comparison

```bash
curl -s http://127.0.0.1:8000/api/pair -H 'Content-Type: application/json' \
  -d '{"person_a":{"birth_datetime":"2000-08-16T04:00"},"person_b":{"birth_datetime":"2001-01-01T12:00"}}'
```

### MCP list tools

```bash
curl -s http://127.0.0.1:8000/mcp -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' -H 'MCP-Protocol-Version: 2025-11-25' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
```

### MCP call a calendar tool

```bash
curl -s http://127.0.0.1:8000/mcp -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"calendar_days","arguments":{"start_date":"2024-02-10","days":7}}}'
```

### MCP rule resource

```bash
curl -s http://127.0.0.1:8000/mcp -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":4,"method":"resources/read","params":{"uri":"astro://rules/ziwei"}}'
```

To use a bearer token when set, add `-H 'Authorization: Bearer YOUR_SECRET'` to the protected requests.


## 综合计算报告（带 Markdown）

```bash
curl -sS http://127.0.0.1:8000/api/report \
  -H 'Content-Type: application/json' \
  -d '{"birth":{"birth_datetime":"2000-08-16T04:00","timezone":"Asia/Shanghai","longitude":104.0667},"lunar_year":2026,"include_time_audit":true}'
```

返回 `sections` / `tool_trace` / `markdown`，不保存到服务端。MCP 同功能调用 `structured_report`。

## 农历反查

```bash
curl http://127.0.0.1:8000/api/lunar-to-gregorian -H 'Content-Type: application/json' -d '{"lunar_year":2020,"lunar_month":4,"lunar_day":1,"is_leap_month":true}'
```

## 出生时间不确定性区间

```bash
curl http://127.0.0.1:8000/api/birth-window -H 'Content-Type: application/json' -d '{"birth":{"birth_datetime":"2024-02-10T01:20","timezone":"Asia/Shanghai"},"uncertainty_minutes":30,"sample_every_minutes":5}'
```

## MCP 2026-07-28

详见 `docs/MCP_INTEGRATION.md` 中的 `server/discover` 和 `tools/call` 示例，必须同时发送 `MCP-Protocol-Version`、`Mcp-Method` 和必要的 `Mcp-Name` 头。
