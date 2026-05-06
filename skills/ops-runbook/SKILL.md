<!-- SCOPE: both -->
---
name: ops-runbook
version: 1.0.0
description: Scaffold operations.md + admin-processes.md + monitoring.md under docs/06-backoffice/ (deploy/rollback/on-call/SLOs/alerting). Idempotent.
invocation: /ops-runbook --project-dir <path> [--overwrite]
user-invocable: true
last-updated: 2026-04-21
audience: project
triggers:
  - operations runbook
  - rollback procedure
  - on-call runbook
  - SLO dashboard
  - admin processes
summary_line: Scaffold deploy/rollback/on-call/monitoring runbooks idempotently under 06-backoffice.
model: haiku
platforms: ["claude-code"]
prerequisites: []
routing_patterns:
  - pattern: '\bops[- ]?runbook\b'
    confidence: 0.95
  - pattern: '\bscaffold\s+ops\b'
    confidence: 0.85
  - pattern: '\boperations\.md\b'
    confidence: 0.8
---

# Ops Runbook Scaffolder

Emits three structured runbook templates under `docs/06-backoffice/`:

| File | Covers |
|---|---|
| `operations.md` | Deploy preconditions + steps + verification, rollback triggers + steps, on-call rotation, common-incidents table |
| `admin-processes.md` | User management, data corrections, configuration change procedures |
| `monitoring.md` | SLO table, dashboards, alert routing, log aggregation |

## Invocation

```
uv run python3 scripts/ops_runbook.py \
  --project-dir /path/to/adopter-project \
  [--project-name "Human Name"]
```

## Idempotency contract

Each of the three files has its own `<!-- ops-runbook:autogen-header -->` … `<!-- ops-runbook:autogen-footer -->` pair.

- First run: creates all three.
- Re-run (no `--overwrite`): for each file with markers, replace only the autogen block; preserve content below footer. If a file exists without markers, skip it (don't destroy).
- `--overwrite`: replace all three in full.

## NOT in scope

- Filling actual deploy commands / thresholds / SLO targets (project-specific; human fill-in).
- Generating incident taxonomy (operator-specific).

## Integration

- Pairs with `/project-scaffold` which emits stubs for these files; this skill replaces those stubs with a fuller, opinionated template when markers are absent (no — it respects the "skip without markers" contract, so stub-only files are left alone unless `--overwrite`).
- Pairs with `/monitoring` skills and SRE dashboards to populate SLO links.

## Verification

```bash
uv run python3 scripts/ops_runbook.py --project-dir /tmp/test-ops
ls /tmp/test-ops/docs/06-backoffice/  # operations.md admin-processes.md monitoring.md
grep -q "Rollback" /tmp/test-ops/docs/06-backoffice/operations.md
grep -q "SLOs" /tmp/test-ops/docs/06-backoffice/monitoring.md
```
