# Architecture & roadmap

```text
Browser UI (HTML/CSS/JS)          ChatGPT/Claude/Codex
           |                             |
       REST API                     MCP JSON-RPC
           |                     HTTP POST or stdio
           +--------- FastAPI / mcp.py --+
                         |
          +--------------+--------------+
          |              |              |
     engines.py      features.py / workflows.py   report.py / quality.py    docs/rules
      BaZi/ZiWei      pair/calendar   MCP resources
          |              |
     reference.py / astronomy.py
         Lookup tables / Swiss Ephemeris
```

- Calculations are deterministic and not performed by a language model.
- `app/mcp.py` implements **18 callable tools, 11 rule resources and 11 prompt templates**, with 2025 legacy initialization and 2026-07-28 stateless metadata requests.
- Agent Skills describe how an LLM should invoke and explain those tools; skills are **not** a substitute for deterministic calculations.
- Service is stateless by design. Only browser `localStorage` may save optional named test profiles when the user clicks Save.
- REST and MCP tool outputs share the same Python service functions.

## Limits / next milestones

1. Independent external cross-library verification for larger lunar-calendar/solar-term year fixture sets; lunar-to-Gregorian inverse and sampled birth-time windows are now implemented in `app/extended.py`.
2. Solar-time correction with explicit longitude is implemented; improve external historical timezone and near-boundary oracle validation.
3. Complete Zi Wei auxiliary stars, school choices, annual and decade transformations and professional cross-library comparisons.
4. Optional opt-in encrypted multi-device profiles with authentication and deletion, *only after a separate privacy design*.
5. Production-grade HTTPS MCP deployment, OAuth integration, monitoring and load testing; user authorization required for plugin registration.

## Why no prediction engine?

The model can explain *traditional meanings*, but astrology is not experimentally established as a reliable way to predict individual health, relationship or economic outcomes. This repository intentionally reports rules and transparent labels rather than fabricating certainty.
