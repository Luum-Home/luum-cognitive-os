# Primitive Scope Classifier — Iteration 010: Paired-proof key fix + hook/UI batch

Date: 2026-05-14

## Goal

Continue manual SCOPE calibration without a global rewrite. This iteration targeted the `declared-both-os-internal-heavy` bucket and checked whether it was real classification debt or classifier/triage debt.

## Finding 1 — triage false positive

`primitive_scope_unknown_triage.py` was checking `paired_proof`, but `primitive_scope_classifier.py` emits `paired_portability_test`. That made rows with real paired proofs look like `declared-both-missing-paired-proof`.

### Fix

- Accept `paired_portability_test` first, with `paired_proof` as legacy fallback.
- Added a unit test using `hooks/_lib/bypass-resolver.sh` shape.

### Effect

Before the fix, the triage bucket `declared-both-os-internal-heavy` had 81 rows. After the fix it dropped to 1 row. Most of that bucket was not scope debt; it was triage schema drift.

## Manual review batch

| Primitive | Decision | Evidence |
|---|---|---|
| `hooks/agent-bus-monitor.sh` | keep `both` | Symlink to package hook; paired portability proof exists; useful as shared adopter surface when agent bus is enabled. |
| `hooks/contextual-rule-loader.sh` | keep `both` | Symlink to package hook; paired portability proof exists; contextual rule projection surface for adopters. |
| `hooks/agent-quota-advisor.sh` | change to `os-only` | Claude Agent quota advisory reads COS metrics and recommends COS orchestrator routing. |
| `hooks/notify.sh` | change to `os-only` | PostToolUse Agent hook detects COS SDD phases and calls COS notifications. |
| `hooks/task-panel-sync.sh` | change to `os-only` | Claude native task panel adapter over COS task state. |
| `hooks/_lib/task_panel_adapter.py` | change to `os-only` | Helper for Claude native task panel integration. |
| `hooks/_lib/recap_adapter.py` | change to `os-only` | Helper for Claude `/recap` integration over COS session state. |
| `packages/skill-governance/skills/self-improve/SKILL.md` | change to `os-only` | META skill orchestrates COS analyze/apply improvement loop, hooks, config, and governance. |

## Classifier result after iteration

```json
{
  "by_suggested_scope": {
    "both": 71,
    "os-only": 529,
    "project": 86,
    "unknown": 502
  },
  "contradictions": 233,
  "low_confidence": 564
}
```

## Triage result after iteration

```json
{
  "total_unknown": 502,
  "by_bucket": {
    "both-semantic-candidate": 36,
    "declared-both-needs-proof-and-metadata": 70,
    "insufficient-metadata": 344,
    "os-only-semantic-candidate": 41,
    "project-only-semantic-candidate": 11
  }
}
```

## Next iteration

Recommended next target: manually review the 11 `project-only-semantic-candidate` rows because they are small enough to review one by one and likely clarify what `project` really means.
