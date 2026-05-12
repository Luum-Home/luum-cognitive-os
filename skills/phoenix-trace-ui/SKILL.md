<!-- SCOPE: both -->
---
name: phoenix-trace-ui
description: "Use when you need this Cognitive OS skill: Start the Arize Phoenix LLM-native trace UI locally (pip-based, no Docker); do not use when a narrower skill directly matches the task."
triggers: ["/phoenix-trace-ui", "/phoenix", "/trace-ui"]
audience: project
version: "1.0.0"
platforms: ["claude-code"]
prerequisites: []
routing_patterns:
  - pattern: '\bphoenix[- ]?trace[- ]?ui\b'
    confidence: 0.95
  - pattern: '\barize\s+phoenix\b'
    confidence: 0.9
  - pattern: '\bphoenix\s+(ui|trace|llm)\b'
    confidence: 0.8
---

# /phoenix-trace-ui

> Boot the Phoenix UI (http://localhost:6006) to inspect OTel spans emitted
> by `lib/record_completion.py` and other instrumented code paths.

## Context

Per ADR-058 (2026-04-24) the former observability docker stack (6 containers)
was retired. LLM trace visualisation is now provided by **Arize Phoenix** —
a pip package with a local UI server and an OTel collector on a single port.
The Phoenix server package (`arize-phoenix`) is licensed under Elastic License
2.0 (ELv2), so COS treats it as an operator-installed local runtime, not a
bundled dependency or hosted managed service. The OTel bridge package is
Apache-2.0.

This skill is available to any project that adopts the Cognitive OS, not
just the OS repo itself (`SCOPE: both`, `audience: project`). It does not
assume any SO-specific paths — it only relies on:

- the `arize-phoenix` pip package being explicitly installed from
  `requirements/dependency-lanes/observability.txt` via
  `bash scripts/dependency-lane.sh install observability`;
- a free port 6006 on the local machine.

## Instructions

### Start the UI

Run this command from the project root (or any directory — Phoenix does not
care about CWD):

```bash
uv run phoenix serve
```

Alternative invocations, all equivalent:

```bash
# If the virtualenv is already activated
phoenix serve

# Explicit module invocation (useful when `phoenix` CLI is not on PATH)
uv run python -m phoenix.server.main serve
```

The UI is then reachable at **http://localhost:6006**. The same port also
hosts the OTel HTTP collector at `http://localhost:6006/v1/traces`, which
is what `lib/record_completion.py` writes to.

### Stop the UI

Press **Ctrl+C** in the terminal running Phoenix. Phoenix is a local pip
process, not a Docker container — there is no `docker compose down`
equivalent, and nothing is running in the background after Ctrl+C.

### Viewing traces

1. Open http://localhost:6006 in a browser.
2. Select the project `cognitive-os` in the top-left selector (created
   automatically on the first trace by `_send_otel_trace` in
   `lib/record_completion.py`).
3. Filter by attribute. The spans emitted by the OS carry:
   - `skill.name` — skill/agent name
   - `task.type` — implementation / review / debugging / …
   - `task.id` — Claude Code tool-call id
   - `trust.score` — 0-100
   - `trust.score_normalized` — 0.0-1.0
   - `tokens.used`, `tokens.input_estimate`, `tokens.output_estimate`
   - `completion.success` — bool

### Overriding the collector endpoint

Phoenix defaults to `http://localhost:6006/v1/traces`. To point traces at
a different host (e.g. a shared team Phoenix instance), set in `.env`:

```
PHOENIX_COLLECTOR_ENDPOINT=http://phoenix.internal.example.com/v1/traces
```

`phoenix.otel.register(...)` reads this variable automatically.

## Acceptance checks

- `command -v uv` exits 0, AND
- `uv run python -c "import phoenix; print(phoenix.__version__)"` prints a
  version ≥ 4.0, AND
- After `uv run phoenix serve &`, `curl -sSf http://localhost:6006/ -o
  /dev/null` returns exit code 0 within 30 seconds.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: phoenix` | Observability dependency lane not installed | `bash scripts/dependency-lane.sh install observability` |
| Port 6006 already in use | Previous Phoenix or another service holds it | `lsof -iTCP:6006 -sTCP:LISTEN` then kill the PID |
| Traces not showing | Collector endpoint mismatch | Set `PHOENIX_COLLECTOR_ENDPOINT` OR start Phoenix before the traced code runs |

## Related

- ADR-058 — `docs/02-Decisions/adrs/ADR-058-observability-migration-*.md`
- `lib/record_completion.py` — `_send_otel_trace()` is the primary emitter
- `requirements/dependency-lanes/observability.txt` — explicit heavy lane for
  `arize-phoenix` / `arize-phoenix-otel`
