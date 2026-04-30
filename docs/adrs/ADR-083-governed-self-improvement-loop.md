# ADR-083 — Governed Self-Improvement Loop

<!-- SCOPE: OS -->

**Status**: Proposed (retroactive backfill 2026-04-30)
**Date**: 2026-04-29
**Author**: Matias Nahuel Améndola
**Related**: ADR-074 (Tier-0 learning loop closure), ADR-075 (stage-2 selective expansion)
**Implementation-plan**: .cognitive-os/plans/architecture/governed-self-improvement-roadmap.md

---

## Status

Proposed (retroactive backfill 2026-04-30).

---

## Context

ADR-074 closed the Tier-0 learning loop by recording error signals and successful
workflows. It did not decide what the system is allowed to do with those signals.
The open question: should Cognitive OS be allowed to modify its own runtime
behavior automatically, and if so, under what constraints?

The competitive context (OpenClaw, Hermes Agent) shows self-improvement as a
differentiating feature. Both systems allow autonomous promotion of learned
behaviors. The risk is uncontrolled self-modification: a system that edits its
own rules or skills without evidence or approval can diverge silently from its
intended behavior.

---

## Decision

Self-improvement is governed by an explicit approval gate. The system may detect
and draft improvements automatically; it may not promote them into runtime
behavior without a human approval step unless a project explicitly opts into
`auto_promote`.

The governed loop has exactly these stages:

```
detect pattern -> propose improvement -> create draft -> verify -> approve -> promote -> reuse -> measure outcome
```

The implementation boundary is:

- **Drafts only** under `.cognitive-os/improvements/drafts/`. The draft stage
  includes `improvement.json` and a `SKILL.md` candidate.
- **Promotion only** under `.cognitive-os/skills/cos/`. No other path in the
  repository is a valid promotion target.
- **Live rules and root skills are not auto-edited.** Promotion is scoped to
  skills, not to the rules surface.
- The Go CLI exposes the loop as `cos skill suggest | draft | inspect | promote`
  and delegates to the canonical Python implementation so CLI and runtime behavior
  share one contract.

A parallel workstream bootstraps a local project profile from the first three
sessions. Profile entries are source-linked, conflict-checkable, exportable, and
wipeable. Secrets and developer-specific absolute paths are never persisted.

---

## Consequences

### Positive

- The learning loop from ADR-074 produces actionable improvement candidates
  rather than raw signal records.
- The approval gate prevents silent runtime drift while still surfacing
  improvement signals.
- Shared CLI/Python contract ensures the improvement loop behaves identically
  inside the harness and in headless mode.
- `auto_promote` opt-in gives projects that trust their test coverage a faster
  loop without exposing all projects to the risk.

### Negative / Trade-offs

- Improvements that are correct but not yet approved are inert. Teams that do not
  review the draft queue regularly will see signal accumulate without benefit.
- The draft-only scope means the system cannot fix recurring hook failures
  automatically; a human must promote the fix.
- Project profile bootstrap runs for three sessions before producing a draft,
  which delays the first memory artifact for new projects.

### Risks

- `auto_promote` projects skip the approval gate entirely. A misconfigured
  `auto_promote` flag in a shared repository could promote a bad improvement
  silently. Mitigation: the flag must be set explicitly per-project and should be
  documented in `.cognitive-os/config.yaml`.

---

## Alternatives rejected

- **Fully autonomous promotion**: Rejected because self-modification without
  evidence or approval creates an unbounded feedback loop. The system could
  promote an improvement that degrades behavior, then learn from the degraded
  behavior and promote further changes.
- **No self-improvement at all (read-only learning loop)**: Rejected because ADR-074
  already committed to closing the loop. Recording signals without acting on them
  provides no operational benefit.
- **Promotion into `.claude/rules/` directly**: Rejected because rules are the
  governance surface; allowing learned improvements to overwrite rules removes
  the human check on the most sensitive part of the system.

---

## Open questions

1. What evidence threshold is required to surface a draft? The current
   implementation uses repeated failures or successful workflows as signals,
   but the minimum repetition count is not yet codified.
2. How should the approval UI work in headless mode where there is no interactive
   harness? The `cos skill inspect` command provides read access but a headless
   approval flow is not yet specified.

---

## Cross-references

- ADR-074: Tier-0 Learning Loop Closure
- ADR-075: Stage-2 Selective Expansion
- `lib/governed_self_improvement.py`
- `lib/project_profile_bootstrap.py`
- `cmd/cos/internal/cli/skill.go`
- `cmd/cos/internal/cli/profile.go`

## Verification

```bash
python3 -m pytest tests/unit/test_governed_self_improvement.py -q --tb=short
python3 -m pytest tests/behavior/test_governed_self_improvement_cli.py -q --tb=short
python3 -m pytest tests/unit/test_project_profile_bootstrap.py -q --tb=short
```
