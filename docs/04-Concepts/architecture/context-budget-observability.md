# Context Budget Observability — JSONL First, OTel/Phoenix Optional

ADR-186 enforcement is local and file-backed. The source of truth is:

```text
.cognitive-os/metrics/context-budget.jsonl
```

## What solves calibration?

Calibration is solved by reading the JSONL and computing the ADR-186 SLOs:

- 90% PASS
- ≤8% WARN
- ≤2% BLOCK
- override usage <5%
- `context-budget-meter` p99 <30 ms

The concrete operator command is:

```bash
scripts/cos-context-budget-report --json
```

## Does OTel solve it?

Partially. OTel is the right export format when COS needs to ship these metrics
to a collector or correlate them with spans. It does **not** replace local
JSONL because enforcement must work with no daemon, no network, and no external
collector.

Recommended layering:

1. JSONL metric is authoritative and always-on.
2. `cos-context-budget-report` computes calibration from JSONL.
3. Optional future OTel exporter reads the same JSONL or receives the same event
   at write-time.

## Does Phoenix solve it?

Phoenix is useful for visualizing LLM traces and debugging high-context turns.
It is not the enforcement plane. Phoenix can show context-budget events as trace
annotations if OTel export is added, but the pass/warn/block decision remains in
`lib/context_budget.py` and the hooks.

## Practical interpretation

- Need local gating? Use ADR-186 hooks and JSONL.
- Need trend/calibration? Use `scripts/cos-context-budget-report`.
- Need trace correlation? Export to OTel and inspect in Phoenix.
- Need dashboarding over many sessions? Add an OTel/metrics backend later, but
  keep JSONL as the portable fallback.
