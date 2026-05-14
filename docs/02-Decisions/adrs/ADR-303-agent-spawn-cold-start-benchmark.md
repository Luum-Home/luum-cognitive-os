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
  persists records to .cognitive-os/metrics/agent-spawn-benchmark.jsonl.
  As of ADR-304, synthetic wall-clock is smoke/lower-bound only; real
  latency budget authority lives in manifests/observability-slo.yaml over
  production hook-timing telemetry. No LLM call is made by this harness.
---

# ADR-303: Sub-Agent Spawn Cold-Start Benchmark

## Status

Accepted


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
   - Computes synthetic smoke status and payload budget status; real wall-clock
     SLO authority is delegated to ADR-304 telemetry aggregation.

2. **`scripts/cos-agent-spawn-benchmark`** — bash wrapper.
   - `--json` emits the record to stdout.
   - `--markdown` renders a human-readable report.
   - `--output PATH` overrides the JSONL append target.
   - Defaults to appending one record to
     `.cognitive-os/metrics/agent-spawn-benchmark.jsonl`.

3. **Budget regression test** — `tests/unit/test_agent_spawn_budget.py`.
   Payload checks still use the ADR-303 record. Real latency checks read the
   ADR-304 SLO manifest and evaluate production `hook-timing.jsonl` telemetry.
   Auto-skips real latency on fresh clones without production telemetry.

4. **Default budgets** (env-overridable):
   - `AGENT_SPAWN_BUDGET_MS=3000` — 3 seconds total spawn overhead.
   - `AGENT_SPAWN_TOKEN_BUDGET=20000` — 20K tokens of injected context.

   The wall budget is a synthetic smoke threshold, not the committed real
   latency SLO. ADR-304 owns the real `subagent-spawn-p95` /
   `subagent-spawn-p99` budgets in `manifests/observability-slo.yaml`. The
   payload budget remains a static ADR-303 guard.

### Contract

Any change to the `SubagentStart` hook chain, the agent preamble template, or
the context injector **must** be re-benchmarked. Specifically:

- Edits to `.claude/settings.json` `hooks.SubagentStart`
- Edits to `hooks/subagent-context-injector.sh`
- Edits to `templates/agent-preamble.md`
- Edits to `rules/RULES-COMPACT.md` (changes per-spawn payload)
- Edits to `skills/CATALOG-COMPACT.md` (~170-skill list)

Re-run: `bash scripts/cos-agent-spawn-benchmark` for payload/smoke data and
`scripts/cos status --observability` for authoritative real latency status.

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
  numbers are a **lower bound**. ADR-304 production telemetry is the calibrated
  authority for latency.
- Token estimator is `bytes // 4`. True tokenisation will diverge by ±15% per
  model family — adequate for budget gating, not for precise cost prediction.
- The 3 s synthetic wall threshold must not be cited as evidence that real
  sub-agent spawn is healthy. Use ADR-304's `subagent-spawn-p95` and
  `subagent-spawn-p99` evaluations instead.

## Alternatives rejected

- **Leave the behavior as implicit agent instruction only.** Rejected because this ADR records a runtime/authoring contract that needs durable tests or audits rather than conversation-only memory.

## Verification

```bash
bash scripts/cos-agent-spawn-benchmark            # appends a record
bash scripts/cos-agent-spawn-benchmark --json     # prints JSON to stdout
.venv/bin/python -m pytest tests/unit/test_agent_spawn_budget.py \
                          tests/unit/test_agent_spawn_benchmark.py -v
python3 scripts/cos-adr-implementation-audit.py --strict
```

## SLO Target

Latency SLO authority moved to ADR-304. The executable targets are declared in
`manifests/observability-slo.yaml` as `subagent-spawn-p95` and
`subagent-spawn-p99` over `.cognitive-os/metrics/hook-timing.jsonl`. This ADR
keeps the synthetic harness as a smoke/lower-bound check and owns the static
per-spawn payload budget.

## References

- ADR-028 — Operations, SLO catalogue, and the SessionStart benchmark
  (`scripts/startup-benchmark.sh`).
- ADR-298 — Reproducible routing-model benchmark harness (sibling pattern).
- `scripts/startup-benchmark.sh` — direct stylistic ancestor.
- `tests/unit/test_startup_budget.py` — directly mirrored in
  `test_agent_spawn_budget.py`.

## Evidence

Tier claim evidence is maintained through the boring-reliability control-plane lane:

```bash
scripts/cos-boring-reliability --json
scripts/cos-tier-claim-audit --json
```

This ADR remains `tier: core` because it affects default routing, observability,
or primitive-governance behavior that is part of the core operator control
plane. The tier claim is re-audited by `scripts/cos-tier-claim-audit`.
