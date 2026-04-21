<!-- SCOPE: both -->
---
name: self-improve
description: META skill — orchestrates analyze-improvements → (human reviews) → apply-improvements. The closing piece of the self-improvement loop.
version: 2.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-04-10
audience: both
tags: [self-improvement, meta, kpis]
summary_line: META skill — orchestrates analyze-improvements → (human reviews) →…

---

# Self-Improve Skill (META)

Thin orchestration wrapper around two atomic skills:

```
/analyze-improvements  →  [HUMAN REVIEWS PROPOSALS]  →  /apply-improvements
```

**The human gate between analysis and application is intentional and non-negotiable.** This skill does not bypass it.

## When to Use

- Weekly (recommended), or after `/agent-kpis` shows degraded metrics
- After 3+ failed tasks in a single session
- When `/error-analyzer` keeps finding the same patterns
- When `kpi-trigger.sh` fires the `.self-improve-recommended` flag
- Manually: `/self-improve`

## Self-improvement Loop

```
Execution → Verification → Error Capture → Pattern Detection → Self-Improve → Better Rules/Skills → Better Next Execution
```

## Instructions

This skill is a META wrapper. Execute the two atomic skills in sequence with an explicit human pause between them.

### Phase 1: Analyze (read-only)

Invoke `/analyze-improvements` with any flags passed to this skill.

Equivalent to loading `skills/analyze-improvements/SKILL.md` and following its instructions.

Available flags forwarded:
- `--since YYYY-MM-DD`
- `--focus TYPE`

At the end of Phase 1, the analysis report is produced. **Stop here and present the full report to the user.**

### HUMAN GATE (mandatory pause)

After Phase 1 completes, output:

```
=== HUMAN REVIEW REQUIRED ===

The analysis above identified {N} improvement proposals:
  Auto-applicable: {N} — safe to apply without further review
  Requires approval: {N} — you will be asked about each before it is applied

Review the PROPOSAL BLOCK above.

To apply changes, invoke:
  /apply-improvements   (auto proposals only)
  /apply-improvements --include-manual   (auto + manual, with per-proposal confirmation)

Or run /self-improve --apply to continue automatically (auto proposals only).
```

**Do NOT proceed to Phase 2 unless the user explicitly says to continue or the `--apply` flag was passed.**

### Phase 2: Apply (file-modifying)

Only reached when:
- The `--apply` flag was passed to `/self-improve`, OR
- The user explicitly confirms after reviewing Phase 1 output

Invoke `/apply-improvements` with the PROPOSAL BLOCK from Phase 1 as input.

Equivalent to loading `skills/apply-improvements/SKILL.md` and following its instructions.

## Flags

| Flag | Phase 1 | Human Gate | Phase 2 |
|------|---------|------------|---------|
| (none) | Runs fully | Shows gate message, stops | NOT invoked |
| `--apply` | Runs fully | Shows proposals, auto-continues for AUTO | Invoked for AUTO proposals |
| `--apply --include-manual` | Runs fully | Shows proposals, auto-continues | Invoked for AUTO + asks per HUMAN-APPROVAL |
| `--since YYYY-MM-DD` | Forwarded to analyze | — | — |
| `--focus TYPE` | Forwarded to analyze | — | — |

## Integration Points

| Component | Role |
|-----------|------|
| `hooks/error-learning.sh` | Captures raw error data (feeds analyze) |
| `hooks/auto-refine.sh` | Captures iteration data (feeds analyze) |
| `hooks/session-learning.sh` | Captures session-level learnings (feeds analyze) |
| `hooks/kpi-trigger.sh` | Detects when self-improve should run |
| `skills/analyze-improvements/` | Phase 1 — read-only analysis |
| `skills/apply-improvements/` | Phase 2 — file-modifying application |
| `skills/error-analyzer/` | Detailed error pattern analysis |
| `skills/agent-kpis/` | KPI dashboard data |
| `skills/model-optimizer/` | Model routing recommendations |
| `rules/self-improvement-protocol.md` | Governance rules |
| `lib/self_improvement.py` | Pre-built analysis utilities |

## Configuration

Controlled by `self_improvement` section in `cognitive-os.yaml`:

```yaml
self_improvement:
  enabled: true
  auto_apply: false          # require human approval by default
  trigger_threshold:
    first_pass_success: 0.70
    iteration_count: 3
  schedule: session_end
  max_auto_improvements: 5
```
