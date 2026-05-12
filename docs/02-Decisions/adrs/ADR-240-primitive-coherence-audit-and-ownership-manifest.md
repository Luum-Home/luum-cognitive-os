---
adr: 240
title: Primitive Coherence Audit and Ownership Manifest
status: accepted
implementation_status: implemented
date: '2026-05-08'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit accepted/implemented status
---

# ADR-240: Primitive Coherence Audit and Ownership Manifest

status: accepted

## Status

Accepted — Slice A implemented.

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

## Detection-before-repair rule

ADR-240 must first detect live contradictions before any agent “cleans them up.”
A green audit is not valuable if it was achieved by manually correcting the
primitives before the detector learned the failure shape. Slice A is therefore
read-only and may legitimately report current warnings or blockers. Remediation
commits must be separate from detector commits and should reference the finding
code they resolve.


## Boundary: future primitives are safe only after registration

This audit is a meta-system, not magic. It prevents regressions for primitive
classes and mutable surfaces that are declared in manifests. A brand-new skill,
hook, rule, script, daemon, repair command, or audit can still destabilize COS if
it introduces an undeclared write surface, lifecycle, bypass, ordering edge, or
external tool boundary.

Therefore every new or promoted agentic primitive must have a machine-readable
registration contract before it is treated as governed:

```yaml
primitive:
  id: example
  kind: hook | skill | rule | script | daemon | audit | repair
  owner: platform-safety
  lifecycle: active | manual_trigger | opt_in | deprecated
  mutates: true | false
  reads:
    - path/or/surface
  writes:
    - path/or/surface
  surfaces:
    - existing.surface.id
  bypasses:
    - optional-bypass-id
  ordering:
    before: []
    after: []
  external_tools: []
  tests:
    - tests/unit/test_example.py
```

The current implementation enforces several registration slices already:

- active hooks must be projected into settings;
- manual/future/deprecated/demoted hooks must not be auto-registered;
- multi-writer surfaces need an owner, allowance, and protocol;
- declared ordering constraints must match the actual hook chain;
- declared primitive invocation cycles need an explicit recursion boundary;
- external tool boundaries need owner, SPDX license, adapter, callers, and
  failure policy.

What it does **not** guarantee is safety for an undeclared new primitive. The
operational rule is: if an incident reveals a new class, add it to a manifest,
make it emit a stable finding, add metrics through ADR-248, and only then decide
whether a safe-class auto-fix is allowed.

## Slice B — recursion and third-party tool boundaries

Primitive coherence also covers recursive control-plane loops. A primitive may
invoke another primitive, a script may wrap a hook, and a hook may call a
third-party tool that eventually re-enters COS. That is safe only when the edge
has an explicit recursion boundary.

ADR-240 therefore treats external tools as adapter boundaries, not as implicit
new primitives. This lets COS adopt market tools such as `git`, `git-filter-repo`,
`trivy`, `syft`, or `gitleaks` without reinventing them, while still requiring:

- an owner;
- SPDX license;
- adapter name;
- allowed callers;
- failure policy;
- recursion boundary.

The audit blocks declared primitive invocation cycles unless the manifest marks
that edge as explicitly recursion-safe. It also blocks incomplete external tool
boundaries, because consuming a third-party CLI without a boundary recreates the
same producer-without-consumer problem at the tool layer.

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

## Alternatives rejected

- **Continue with independent per-primitive checkers only** — rejected because the incident class is cross-primitive contradiction, not local primitive absence. Independent checkers can each be green while their combined guidance is unsafe.
- **Auto-repair contradictions immediately** — rejected because repair before detection hides the failure shape and can mutate state incorrectly. Slice A must stay read-only and make contradictions observable first.
- **Encode ownership only in prose ADRs** — rejected because agents and scripts need machine-readable ownership, writers, and ordering constraints to catch drift before runtime.

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
- Static discovery of undeclared third-party CLI usage once the declared boundary model is stable.

## Verification

```bash
python3 -m pytest tests/unit/test_primitive_coherence_audit.py tests/audit/test_adr_contracts.py -q
```
