---
id: ADR-304
title: Telemetry Aggregator + Feedback Loop
status: accepted
implementation_status: implemented
date: 2026-05-13
extends: [ADR-028, ADR-031, ADR-247, ADR-275]
related: [ADR-049, ADR-297, ADR-303]
tags: [observability, telemetry, slo, control-plane, feedback-loop]
---

# ADR-304 — Telemetry Aggregator + Feedback Loop

## Status

Accepted, implemented 2026-05-13.

## Context

COS writes telemetry to ~7 JSONL streams under `.cognitive-os/metrics/` and
`.cognitive-os/audit/`. Until this ADR, **none of them had a periodic
consumer** — the OS was operating an observability data lake without
subscribers. Concretely:

- `hook-timing.jsonl` (~73 k records, every hook duration)
- `llm-dispatch.jsonl` (ADR-049 dispatches)
- `llm-routing.jsonl` (ADR-297 dispatches)
- `skill-enrichment.jsonl`, `skill-routing.jsonl`
- `startup-benchmark.jsonl`
- `closure-trail.jsonl` (the one stream with an existing consumer per ADR-275)

The failure mode is documented in detail at
`docs/06-Daily/reports/postmortem-observability-data-lake-without-consumers-2026-05-13.md`
(HIGH severity). The incident that surfaced it: during ADR-303 work, the
operator asked whether sub-agent spawn performance had been measured. The
orchestrator extracted 38 samples already on disk and found p95 = 55.6 s,
p99 = 90.9 s — silent regressions that had been writing to disk for >24 h
without alerting. The SessionStart SLO (ADR-028, target < 2000 ms) was
similarly breaching (measured 2496–9703 ms) without any alert firing.

The control-plane already has the right infrastructure to act on aggregated
findings: `scripts/cos-control-plane-audit` runs `hourly`/`pre-public` lanes
and emits findings into `.cognitive-os/tasks/control-plane-remediation.jsonl`
(ADR-247, ADR-275). The aggregator fits into that contract.

## Decision

Introduce a periodic telemetry aggregator that:

1. Reads SLO declarations from a single manifest
   (`manifests/observability-slo.yaml`).
2. Evaluates each declared metric against its target.
3. Emits one finding per breach into the existing control-plane remediation
   queue (idempotent on `stable_id`).
4. Surfaces top findings on SessionStart (banner).
5. Proposes (never auto-applies) self-tuning when the same hook breaches the
   same SLO across ≥3 consecutive windows AND emits zero stdout.

Three implementation slices, each independently testable.

## Slice 1 — Telemetry Aggregator

**Files**

- `manifests/observability-slo.yaml` — SLO declarations, single source of truth.
- `lib/telemetry_aggregator.py` — pure-Python evaluation engine.
- `scripts/cos-telemetry-aggregate` — CLI wrapper.
- `hooks/telemetry-budget-violator-detect.sh` — hourly lane hook.
- `manifests/control-plane-audits.yaml` — registers `telemetry-aggregator`
  under the `hourly` lane.

**Schema** (`observability-slo/v1`):

```yaml
slos:
  - id: <stable-id>
    source_stream: .cognitive-os/metrics/<name>.jsonl
    metric: percentile(duration_ms, 0.95) | success_ratio
            | cache_hit_ratio | latest.<dotted.path>
    filter: <field> == "<value>" [or|and ...]    # optional
    window: last_N_records                       # optional
    target_lt: <num>    # or target_gte
    severity_on_breach: warn | block | info
    rationale: <text>
```

Guarantees:

- Missing/empty streams emit `telemetry-stream-missing` at `info` (never crash).
- `stable_id = sha256(slo_id|hour_bucket|rounded_value)[:16]` — idempotent
  across re-runs in the same hour with the same value.
- Strict mode (`--strict`) exits 2 on any breach (for CI gating).

**Independent test command**

```
.venv/bin/python -m pytest tests/unit/test_telemetry_aggregator.py -v
```

## Slice 2 — SessionStart Banner

**Files**

- `lib/telemetry_banner.py` — pure renderer (snapshot YAML → banner text).
- `hooks/session-init.sh` — invokes the renderer if the latest snapshot is
  ≤ 2 h old.

Banner format (top 3 highest-severity findings, info-only `stream_missing`
suppressed):

```
⚠️ Performance findings (latest hourly aggregation):
  1. session-start-blocking-total: 2496 ms (target < 2000 ms, breach 25%)
  2. subagent-spawn-p95: 55620 ms over last 100 spawns (target < 5000 ms)
Run `scripts/cos-telemetry-aggregate --snapshot` for full report.
```

Silent on: missing snapshot, snapshot older than 2 h, zero actionable findings.

**Independent test command**

```
.venv/bin/python -m pytest tests/unit/test_session_start_banner_telemetry.py -v
```

## Slice 3 — Self-Tuning Proposer

**File** — `lib/telemetry_aggregator.py::_propose_self_tuning`

Proposes (does **not** auto-apply) flipping a hook to async when ALL hold:

1. Same `slo_id` breached across ≥ 3 distinct hourly windows
   (read from the existing remediation queue history).
2. The breaching SLO sources `hook-timing.jsonl`.
3. The offending hook (inferred from the filter expression's
   `hook == "..."`) emits zero stdout bytes across recent records.

Critical gate: if `stdout_bytes` field is absent from `hook-timing.jsonl`
(current schema does not yet emit it), proposals of this class are
**skipped silently** — no false positives. When `hook-timing-wrapper.sh`
later begins emitting `stdout_bytes`, proposals will activate without code
changes.

Proposal output (in the remediation queue, code
`telemetry-self-tuning-proposal`):

```json
{
  "code": "telemetry-self-tuning-proposal",
  "severity": "warn",
  "stable_id": "telemetry-self-tune/<hook>",
  "window_summary": {
    "proposed_change": {
      "file": "scripts/_lib/settings-driver-claude-code.sh",
      "hook": "<hook>.sh",
      "from": "false",
      "to": "true"
    },
    "manual_application_command":
      "Run: bash scripts/apply-efficiency-profile.sh standard ..."
  }
}
```

Never auto-applied. Operator triages the queue and decides.

**Independent test command**

```
.venv/bin/python -m pytest tests/unit/test_telemetry_self_tuning_proposer.py -v
```

## Consequences

### Positive

- The data lake now has consumers. Every emitter under
  `.cognitive-os/metrics/` is eligible for an SLO budget.
- Adding a new SLO is one YAML entry. No code change required.
- All findings flow through the existing ADR-247/275 remediation queue, so
  triage, dedupe, and operator workflows are unchanged.
- SessionStart banner closes the visibility loop without forcing the operator
  to remember to inspect a report.

### Risks accepted

- Aggregator windows are applied **after** any declared filter. This is
  required for sparse events such as `SubagentStart` inside global streams
  like `hook-timing.jsonl`; tailing first can erase the signal and incorrectly
  report `no_data`. Large streams may require retention/rollup work as SLO
  coverage expands.
- Self-tuning proposer is gated on a schema field (`stdout_bytes`) not yet
  emitted by `hook-timing-wrapper.sh`. Until that field is added, this slice
  is dormant by design. The graceful-skip is verified by
  `test_no_proposal_when_stdout_bytes_field_missing`.

### Negative / cost

- One additional hook in the hourly control-plane lane (~50 ms typical).
- A new manifest to maintain.

## Alternatives rejected

- **Leave the behavior as implicit agent instruction only.** Rejected because this ADR records a runtime/authoring contract that needs durable tests or audits rather than conversation-only memory.

## Verification

End-to-end on real repo, 2026-05-13:

```
$ .venv/bin/python scripts/cos-telemetry-aggregate \
    --snapshot /tmp/real-snap.yaml --findings /tmp/real-findings.jsonl
[telemetry-aggregate] evaluations=5 breaches=3 proposals=0
                      stream_missing=0 appended=3 deduped=0
$ # re-run — dedupe verified
[telemetry-aggregate] evaluations=5 breaches=3 proposals=0
                      stream_missing=0 appended=0 deduped=3
```

Test summary:

```
tests/unit/test_telemetry_aggregator.py          9 passed
tests/unit/test_session_start_banner_telemetry.py 5 passed
tests/unit/test_telemetry_self_tuning_proposer.py 6 passed
```


```bash
python3 -m pytest tests/unit -q
```
## References

- Postmortem:
  `docs/06-Daily/reports/postmortem-observability-data-lake-without-consumers-2026-05-13.md`
- ADR-028 — SLO catalogue + error budget
- ADR-031 — Continuous audit doctrine
- ADR-247 — Postmortem regression detection
- ADR-275 — Closure & projection (existing single consumer)
