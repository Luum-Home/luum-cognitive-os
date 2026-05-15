# Primitive SCOPE classifier — Iteration 028 hook contradiction closure

Date: 2026-05-15

## Goal

Close the 6 remaining hook contradictions before continuing with hook unknowns.

## Manual review decision

The classifier evidence was not uniformly wrong or uniformly right. Manual review split the 6 hook contradictions into two groups.

### Reclassified to `os-only`

These 4 were declared `both` but are COS-local support/operator surfaces:

- `hooks/_lib/agent-context.sh` — COS agent-context helper for destructive-operation blockers.
- `hooks/_lib/task-event.sh` — COS task-event JSONL helper, not standalone shared capability.
- `hooks/dangerous-env-flag-detector.sh` — detects dangerous COS override flags.
- `hooks/engram-obsidian-export-on-stop.sh` — optional COS/Engram operator export hook tied to COS memory/export scripts and vault env.

### Kept as `both`; evidence corrected

These 2 were declared `both` and manual review confirmed they are shared runtime safety surfaces when projected with policy:

- `hooks/network-egress-guard.sh` — generic exfiltration-shaped network command blocking.
- `hooks/protected-config-write-guard.sh` — generic protected agent control-plane config write blocking for COS and adopter-project projected primitives.

Their prior `so-local-only` consumer-availability rows were stale and contradicted projection/harness evidence.

## Classifier robustness update

Added exact semantic patterns for this repeated family:

- shared: `network-egress-guard`, `protected-config-write-guard`;
- COS/operator-only: `dangerous-env-flag-detector`, `engram-obsidian-export-on-stop`.

This keeps broad prefixes avoided and preserves the rule that `distribution` is not scope evidence.

## Before / after

Before:

```json
{
  "hook_contradictions": 6,
  "classifier_contradictions": 36,
  "unknown": 320
}
```

After:

```json
{
  "hook_contradictions": 0,
  "classifier_contradictions": 30,
  "unknown": 320,
  "by_prefix": {"hooks": 79, "rules": 83, "scripts": 158}
}
```

Unknown count is unchanged because these were contradiction rows, not unknown rows.
