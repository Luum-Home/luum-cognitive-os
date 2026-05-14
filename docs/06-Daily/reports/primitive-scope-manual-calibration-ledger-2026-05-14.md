# Primitive Scope Manual Calibration Ledger — 2026-05-14

## Goal

Resolve ADR-314 `SCOPE` taxonomy debt manually in bounded batches, using evidence from file content, lifecycle/distribution metadata, consumer availability, and primitive contract registry entries.

## Guardrails

- Do not mass-edit markers from grep output.
- Prefer adding missing lifecycle/consumer evidence when a marker is manually confirmed.
- Change `SCOPE` only when file content and distribution evidence contradict the marker.
- Each batch must record sample evidence, files changed, validation commands, and remaining triage count.

## Current baseline before semantic batches

After structural standardization:

```json
{
  "total_unknown": 562,
  "by_bucket": {
    "declared-both-needs-proof-and-metadata": 364,
    "declared-both-os-internal-heavy": 81,
    "insufficient-metadata": 65,
    "conflicting-metadata": 32,
    "os-only-semantic-candidate": 19,
    "both-semantic-candidate": 1
  }
}
```

## Batch 001 — Confirm obvious os-only rows

### Hypothesis

Rows already declared `os-only` and summarized as COS daemons, COS metrics, COS task bridge, COS install/repair/synthesis, or OS rule roadmap should be resolved by adding maintainer-only lifecycle/consumer metadata, not by changing markers.

### Candidate paths

- `hooks/cognitive-os-health.sh`
- `hooks/cos-executor-heartbeat.sh`
- `hooks/cosd-intent-submit.sh`
- `hooks/metrics-calibrator-trigger.sh`
- `hooks/reaper-heartbeat.sh`
- `hooks/recap-sync.sh`
- `hooks/session-hygiene.sh`
- `hooks/session-knowledge-extractor.sh`
- `hooks/session-state-save.sh`
- `hooks/sync-to-repo.sh`
- `hooks/task-bridge-notify.sh`
- `hooks/telemetry-budget-violator-detect.sh`
- `hooks/usage-health-check.sh`
- `packages/agent-lifecycle/skills/review-output/SKILL.md`
- `rules/research-first-protocol.md`
- `rules/ROADMAP.md`
- `skills/cos-install-operations/SKILL.md`
- `skills/hook-timing/SKILL.md`
- `skills/repair-skill/SKILL.md`
- `skills/synthesize-skill/SKILL.md`

### Manual review notes

- Reviewed each candidate header/content sample.
- Confirmed COS-specific runtime/internal dependence: `.cognitive-os` metrics/state, cosd/cos-executor/reaper daemons, Claude recap/task bridge adapters, telemetry SLO aggregation, COS install/repair/synthesis queues, and OS rule-maintenance roadmap.
- No marker changes were needed; existing `SCOPE: os-only` markers were correct.
- Corrected stale skill `audience` metadata for:
  - `packages/agent-lifecycle/skills/review-output/SKILL.md`
  - `skills/repair-skill/SKILL.md`
  - `skills/synthesize-skill/SKILL.md`
- Added maintainer-only consumer availability and lifecycle metadata for all 20 candidate paths.

### Result

Resolved the `os-only-semantic-candidate` bucket and the single false `both-semantic-candidate` row by adding evidence metadata.

Before batch 001:

```json
{
  "total_unknown": 562,
  "os-only-semantic-candidate": 19,
  "both-semantic-candidate": 1
}
```

After batch 001:

```json
{
  "total_unknown": 542,
  "by_bucket": {
    "conflicting-metadata": 32,
    "declared-both-needs-proof-and-metadata": 364,
    "declared-both-os-internal-heavy": 81,
    "insufficient-metadata": 65
  }
}
```

Validation:

```bash
bash scripts/cos-registry-lock --project-dir . --write
.venv/bin/python -m pytest tests/unit/test_primitive_parser.py tests/unit/test_primitive_scope_classifier.py tests/unit/test_primitive_scope_unknown_triage.py -q
# 28 passed
bash scripts/cos-registry-lock --project-dir . --audit
# status: pass
```

## Batch 002 — Recommended next target

### Hypothesis

`conflicting-metadata` is the next best bucket because each row already has contradictory durable metadata. Fixing it should produce clear signal without requiring broad proof work.

### Candidate count

- `conflicting-metadata`: 32

### Initial examples

- `hooks/bash-hot-path-dispatcher.sh`
- `hooks/subagent-budget-enforcer.sh`
- `scripts/cos-key-learnings-capture`
- `scripts/cos_primitive_harvester.py`
- `scripts/cos_session_backlog.py`
- `scripts/cos_work_inventory.py`
- `scripts/cos_worktree_triage.py`

### Manual review notes

Split the 32 rows into three decisions:

- Shared `both` surfaces (14): runtime/project governance tools valid in COS and consumer repositories with COS installed.
- Project-only surfaces (9): downstream project writers/scaffolders/report writers that should not be treated as COS self-construction primitives.
- Maintainer-only/os-only surfaces (9): COS harvester, catalog generator, live smoke/red-team and provider fallback probes, statusline/local harness internals.

### Changes

- Added classifier support for `shared-surface` consumer availability and `lifecycle-declared-shared-surface` lifecycle accessibility.
- Reconciled consumer availability and lifecycle metadata for all 32 rows.
- Changed `SCOPE` markers where manual review found stale declarations:
  - `both` → `project` for downstream project writers/scaffolders.
  - `both` → `os-only` for maintainer-only COS/internal/smoke primitives.
- Kept `both` for shared runtime/project governance surfaces.

### Result

Before batch 002:

```json
{
  "total_unknown": 542,
  "conflicting-metadata": 32
}
```

After batch 002:

```json
{
  "total_unknown": 510,
  "by_bucket": {
    "declared-both-needs-proof-and-metadata": 364,
    "declared-both-os-internal-heavy": 81,
    "insufficient-metadata": 65
  }
}
```

Validation:

```bash
bash scripts/cos-registry-lock --project-dir . --write
.venv/bin/python -m pytest tests/unit/test_primitive_parser.py tests/unit/test_primitive_scope_classifier.py tests/unit/test_primitive_scope_unknown_triage.py -q
# 28 passed
bash scripts/cos-registry-lock --project-dir . --audit
# status: pass
.venv/bin/python scripts/primitive_parse_inventory.py --project-dir .
# structural_findings: {}
```

## Batch 003 — Recommended next target

### Hypothesis

`declared-both-os-internal-heavy` (81) is the next highest-risk bucket because markers say `both` while content is dominated by COS internals. This is closest to the original failure mode, so review must be row-by-row with explicit downgrade/split/proof decisions.

### Candidate count

- `declared-both-os-internal-heavy`: 81

### Status

Pending.
