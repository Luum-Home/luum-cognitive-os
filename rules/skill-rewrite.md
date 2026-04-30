<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Skill Rewrite Protocol

## Purpose

Automatically surface rewrite suggestions when a skill fails repeatedly, closing
the Act → Learn → Reuse cycle (see `rules/auto-skill-generation.md`).  Persistent
failure patterns indicate that the current skill definition is wrong, incomplete,
or no longer matches reality.

## Trigger Threshold

A skill MUST be suggested for rewrite when it has accumulated **3 or more failures**
(``success=False`` performance records) within a rolling **24-hour window**.

Detection runs via `ConsequenceEngine.get_skills_needing_rewrite()` in
`lib/consequence_engine.py` after every agent completion (PostToolUse via
`completion-gate.sh`).

## Phase-Aware Behavior

| Phase | Output label | Action required |
|-------|-------------|-----------------|
| `reconstruction` | `AUTO-REWRITE SUGGESTED` | Orchestrator SHOULD invoke `/optimize-skill {name}` immediately |
| `stabilization` | `AUTO-REWRITE SUGGESTED` | Orchestrator SHOULD invoke `/optimize-skill {name}` immediately |
| `production` | `REWRITE SUGGESTED` | Human approval REQUIRED before running `/optimize-skill` |
| `maintenance` | `REWRITE SUGGESTED` | Human approval REQUIRED before running `/optimize-skill` |

## Output Format

Suggestions appear on stderr via the `completion-gate.sh` hook:

```
=== COMPLETION-GATE: SKILL REWRITE RECOMMENDATIONS ===
AUTO-REWRITE SUGGESTED: sdd-apply has 4 failures in 24h
  Last error context: build_error
  Run: /optimize-skill sdd-apply
=== END SKILL REWRITE RECOMMENDATIONS ===
```

## What Counts as a Failure

A performance record is counted as a failure when the ``success`` field is
``False`` in `.cognitive-os/metrics/consequence-history.jsonl`.  These records
are written by `lib/record_completion.py` (called from `completion-gate.sh`
after every agent completion).

## How to Act on a Suggestion

1. Run `/optimize-skill {skill_name}` — the skill reads failure history and
   rewrites or patches the SKILL.md to address root causes.
2. In production/maintenance phases, present the suggestion to the user first
   and wait for explicit approval before invoking `/optimize-skill`.
3. After the skill is rewritten, call `ConsequenceEngine.re_enable_skill(name)`
   if the skill was also disabled.

## Integration Points

| Primitive | Role |
|-----------|------|
| `lib/consequence_engine.py` | `get_skills_needing_rewrite()` counts recent failures |
| `packages/quality-gates/hooks/completion-gate.sh` | Calls the method after every Agent completion |
| `lib/record_completion.py` | Writes performance records (success/failure) |
| `packages/skill-governance/skills/optimize-skill/SKILL.md` | Performs the actual rewrite |
| `rules/skill-management.md` | Broader skill adaptation protocol |
| `rules/auto-skill-generation.md` | Act → Learn → Reuse cycle |

## Contextual Trigger

This rule is loaded when: skill rewrite, optimize-skill, skill failing, rewrite
suggestion, 3 failures, skill degradation.
