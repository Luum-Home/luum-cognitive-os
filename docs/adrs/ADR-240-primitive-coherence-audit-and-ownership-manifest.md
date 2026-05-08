# ADR-240: Primitive Coherence Audit and Ownership Manifest

**Status**: Accepted — Slice A implemented  
**Date**: 2026-05-08  
**Owner**: platform-safety  
**Related**: ADR-149, ADR-199, ADR-200, ADR-211, ADR-218, ADR-219, ADR-238  
**Post-mortem**: `docs/reports/primitive-coherence-drift-postmortem-2026-05-08.md`

## Context

Cognitive OS has many agentic primitives: hooks, scripts, rules, skills,
profiles, manifests, ledgers, readiness gates, and cleanup/rewrite tools. Recent
release-preparation work showed a recurring failure mode where primitives were
locally correct but globally incoherent.

Examples:

- a mutating agent snapshot can hide work if it runs before preflight blockers;
- a hook can be intentionally opt-in in one manifest while another checker calls
  it missing;
- a history sanitizer can clean content but accidentally rewrite author metadata
  if metadata boundaries are not explicit;
- several primitives can write the same state family without a declared owner or
  write protocol;
- a branch switch can be treated as non-destructive by one layer even though it
  changes where future commits land.

This ADR names the class: **primitive coherence drift**.

## Decision

Adopt a machine-readable primitive coherence manifest plus a non-mutating audit
script.

New artifacts:

- `manifests/primitive-coherence.yaml`
- `scripts/primitive-coherence-audit.py`
- `tests/unit/test_primitive_coherence_audit.py`
- `docs/reports/primitive-coherence-drift-postmortem-2026-05-08.md`

The audit detects contradictions before operators or agents attempt to repair
them. Slice A is intentionally read-only.

## Manifest model

The manifest declares surfaces, owners, writers, and ordering constraints.

```yaml
schema_version: primitive-coherence/v1

surfaces:
  - id: agent.launch_snapshot
    kind: launch-state
    owner: agent-lifecycle
    allowed_multi_writer: true
    write_protocol: lock-required
    writers:
      - hooks/pre-agent-snapshot.sh
      - hooks/post-agent-snapshot-restore.sh

ordering_constraints:
  - id: agent-prelaunch-before-snapshot
    event: PreToolUse
    matcher: Agent
    before: hooks/pre-agent-snapshot.sh
    after: hooks/agent-prelaunch.sh
    severity: block
```

## Slice A checks

1. **Ordering inversion**
   - If `before` appears before `after` in the configured event/matcher hook
     chain, the audit blocks.

2. **Registration checker / classification disagreement**
   - If the legacy hook registration checker reports an unregistered hook, but
     `manifests/hook-registration-classification.yaml` classifies it as
     intentional (`opt_in`, `manual_trigger`, `future`, `deprecated`, etc.), the
     audit emits a disagreement finding.

3. **Undeclared multi-writer surface**
   - If a manifest surface has multiple writers but does not allow multi-writer
     operation and has no write protocol, the audit blocks.

## Non-goals

- Do not auto-edit `.claude/settings.json`.
- Do not auto-register hooks.
- Do not delete or rewrite state.
- Do not rewrite git history.
- Do not modify author/committer metadata.
- Do not infer ownership from prose alone.

## Consequences

Positive:

- Gives operators a single place to see cross-primitive contradictions.
- Prevents future profile regeneration from silently reordering mutating hooks
  before blockers.
- Distinguishes intentional opt-in hooks from accidental orphan hooks.
- Creates a foundation for release-readiness and service-mode gates.

Negative:

- Introduces another manifest that must be maintained.
- Slice A only covers a narrow set of contradictions.
- Some initially noisy findings are expected until legacy checkers consume the
  same manifest.

## Acceptance criteria

- Bad hook ordering fixture blocks.
- Classified opt-in hook reported by legacy checker produces a disagreement
  finding.
- Multi-writer surface without protocol blocks.
- Current repo audit emits JSON and does not mutate files.

## Future slices

- Bypass-env conflict detection.
- Producer-without-consumer detection.
- ADR status versus implementation/test consistency.
- Static write-surface discovery over hooks/scripts.
- Integration into `scripts/cos-pre-public-risk-audit`.
