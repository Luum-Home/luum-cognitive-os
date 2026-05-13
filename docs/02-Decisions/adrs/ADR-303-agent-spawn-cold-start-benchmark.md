---
adr: 303
title: Sub-Agent Spawn Cold-Start Benchmark
status: accepted
implementation_status: implemented
date: '2026-05-13'
supersedes: []
superseded_by: null
extends:
  - ADR-028
  - ADR-298
implementation_files:
  - lib/agent_spawn_benchmark.py
  - scripts/cos-agent-spawn-benchmark
  - tests/unit/test_agent_spawn_benchmark.py
  - tests/unit/test_agent_spawn_budget.py
tier: core
tags:
  - benchmark
  - subagent
  - cold-start
  - observability
  - cost-governance
verification_level: medium
classification_basis: |
  Lands an operator-side benchmark harness for the SubagentStart hook chain
  (lib/agent_spawn_benchmark.py + scripts/cos-agent-spawn-benchmark). It
  measures wall-clock latency and token payload injected at every sub-agent
  spawn, persists records to .cognitive-os/metrics/agent-spawn-benchmark.jsonl,
  and gates regressions through tests/unit/test_agent_spawn_budget.py. No LLM
  call is made; measurement is local hook execution against synthetic stdin.
---

# ADR-303: Sub-Agent Spawn Cold-Start Benchmark

## Context

Session 2026-05-13 identified a measurement gap: orchestrator SessionStart is
benchmarked (`scripts/startup-benchmark.sh`, ADR-028 D-stream) but **sub-agent
spawn cost is not**. The orchestrator routinely fans out 4–5 sub-agents in
parallel via the Agent tool; every spawn triggers the `SubagentStart` hook
chain — chiefly `hooks/subagent-context-injector.sh` — which injects:

1. `templates/agent-preamble.md` (canonical preamble)
2. Mandatory rules (effectively `rules/RULES-COMPACT.md`)
3. The skill catalog (`skills/CATALOG-COMPACT.md`, ~170 entries)
4. Per-agent sidecar context

Two costs are paid **before the sub-agent does any productive work**:

- **Wall-clock latency** — operator perceives the agent as "slow to respond"
- **Token payload** — every spawn is billed for the injected preamble

Neither dimension is observable today, so regressions land silently and the
operator cannot reason about parallel-spawn cost.

## Decision

Land a sibling harness to ADR-298 (routing-model benchmark) and the ADR-028
SessionStart benchmark:

1. **`lib/agent_spawn_benchmark.py`** — pure-Python measurement module.
   - Parses `.claude/settings.json` `hooks.SubagentStart` group.
   - Times each registered hook with a synthetic JSON stdin payload
     (`prompt`, `session_id`, `tool_name`), 5-second per-hook timeout.
   - Measures stdout bytes emitted (= injected context) and estimates tokens
     (`bytes // 4`, matching ADR-028 convention).
   - Sizes the preamble, RULES-COMPACT.md, and CATALOG-COMPACT.md statically.
   - Computes SLO pass/breach against the wall and token budgets.

2. **`scripts/cos-agent-spawn-benchmark`** — bash wrapper.
   - `--json` emits the record to stdout.
   - `--markdown` renders a human-readable report.
   - `--output PATH` overrides the JSONL append target.
   - Defaults to appending one record to
     `.cognitive-os/metrics/agent-spawn-benchmark.jsonl`.

3. **Budget regression test** — `tests/unit/test_agent_spawn_budget.py`,
   modelled on `test_startup_budget.py`. Auto-skips on fresh clones.

4. **Default budgets** (env-overridable):
   - `AGENT_SPAWN_BUDGET_MS=3000` — 3 seconds total spawn overhead.
   - `AGENT_SPAWN_TOKEN_BUDGET=20000` — 20K tokens of injected context.

   These are **provisional baselines**, not committed SLOs. A follow-up ADR
   will propose firm SLO targets once a baseline distribution has been
   collected across machines.

### Contract

Any change to the `SubagentStart` hook chain, the agent preamble template, or
the context injector **must** be re-benchmarked. Specifically:

- Edits to `.claude/settings.json` `hooks.SubagentStart`
- Edits to `hooks/subagent-context-injector.sh`
- Edits to `templates/agent-preamble.md`
- Edits to `rules/RULES-COMPACT.md` (changes per-spawn payload)
- Edits to `skills/CATALOG-COMPACT.md` (~170-skill list)

Re-run: `bash scripts/cos-agent-spawn-benchmark`. The budget test guards CI.

## Consequences

**Positive**

- Operator gains visibility into per-spawn cost; parallel-spawn pricing is now
  a measurable quantity instead of intuition.
- Regressions in the preamble or skill catalog land with a test failure rather
  than silent token bloat.
- Symmetric with ADR-028 D-stream and ADR-298 harness — same JSONL shape,
  same fresh-clone-safe skip pattern, same env-overridable budgets.

**Negative / risks**

- Wall-clock measurement runs hooks against synthetic stdin; some hooks may
  short-circuit faster than they would for a real Agent payload, so the
  numbers are a **lower bound**. Calibration against real-Agent telemetry is
  follow-up work.
- Token estimator is `bytes // 4`. True tokenisation will diverge by ±15% per
  model family — adequate for budget gating, not for precise cost prediction.
- Provisional budgets (3 s / 20 K tokens) are not based on a measured
  baseline distribution. The first follow-up ADR will tighten or relax these
  after a week of records have been collected.

## Verification

```bash
bash scripts/cos-agent-spawn-benchmark            # appends a record
bash scripts/cos-agent-spawn-benchmark --json     # prints JSON to stdout
.venv/bin/python -m pytest tests/unit/test_agent_spawn_budget.py \
                          tests/unit/test_agent_spawn_benchmark.py -v
python3 scripts/cos-adr-implementation-audit.py --strict
```

## SLO Target

**TBD.** This ADR records the baseline measurement infrastructure only. A
follow-up ADR will propose firm wall-clock and payload SLOs against the first
N records collected from the metrics JSONL.

## References

- ADR-028 — Operations, SLO catalogue, and the SessionStart benchmark
  (`scripts/startup-benchmark.sh`).
- ADR-298 — Reproducible routing-model benchmark harness (sibling pattern).
- `scripts/startup-benchmark.sh` — direct stylistic ancestor.
- `tests/unit/test_startup_budget.py` — directly mirrored in
  `test_agent_spawn_budget.py`.
