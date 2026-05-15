# Primitive SCOPE classifier — Iteration 022 hooks/_lib batch 002

Date: 2026-05-15

## Goal

Continue the post-orthogonality recalibration after fixing the classifier bug where `distribution` tier was treated as SCOPE evidence.

This batch reviews the remaining `hooks/_lib` primitives that still appeared as `unknown` only because they lacked explicit consumer-availability and lifecycle metadata.

## Manual classification decision

Classify the following 13 hook support primitives as `SCOPE: os-only`:

- `hooks/_lib/register-bg.sh`
- `hooks/_lib/remediation.sh`
- `hooks/_lib/resolve-main-worktree.sh`
- `hooks/_lib/safe-jsonl.sh`
- `hooks/_lib/semantic-search.sh`
- `hooks/_lib/session-fs-reap.sh`
- `hooks/_lib/session_init_helper.py`
- `hooks/_lib/singularity-suggestion.sh`
- `hooks/_lib/stash-lock.sh`
- `hooks/_lib/task-identity.sh`
- `hooks/_lib/task_bridge.py`
- `hooks/_lib/timing.sh`
- `hooks/_lib/tuning.sh`

## Evidence

These files are not standalone repository-agnostic construction guidance. They are libraries/helpers for COS hook runtime behavior:

- `.cognitive-os/metrics`, `.cognitive-os/sessions`, `.cognitive-os/runtime`, and `.cognitive-os/tasks` state management.
- COS session-init support, hook timing/tuning, remediation registry, auto-repair matching, and task identity/bridge wiring.
- Hook runtime coordination such as process registry, stash locking, safe JSONL writes, and main-worktree resolution.

They may be copied with projected hooks as implementation support, but they are not consumer-facing primitives by themselves.

## Metadata added

For each file:

- `primitive-consumer-availability.yaml`: `status: maintainer-only` with a concrete rationale.
- `primitive-lifecycle.yaml`: `consumer_accessibility: lifecycle-declared-maintainer`, `distribution: maintainer`, `governance_class: hook-runtime-support`, and explicit behavior evidence.

## Before / after

Before this batch, post-orthogonality triage showed:

```json
{
  "total_unknown": 426,
  "by_prefix": {"hooks": 185, "rules": 83, "scripts": 158}
}
```

After this batch:

```json
{
  "total_unknown": 413,
  "by_prefix": {"hooks": 172, "rules": 83, "scripts": 158},
  "by_bucket": {
    "conflicting-metadata": 4,
    "insufficient-metadata": 322,
    "os-only-semantic-candidate": 83,
    "project-only-semantic-candidate": 4
  }
}
```

## Acceptance criteria

- `python3 scripts/primitive_scope_classifier.py --project-dir .` reports `unknown: 413`.
- `python3 scripts/primitive_scope_unknown_triage.py --project-dir . ...` reports hooks unknown reduced from 185 to 172.
- Registry lock regenerates and audits cleanly.
- Primitive parser/classifier/triage/portability unit and red-team tests pass.
- Primitive inventory remains structurally clean.
