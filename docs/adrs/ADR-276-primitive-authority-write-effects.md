---
adr: 276
title: Primitive Authority and Write-Effects Audit
status: accepted
implementation_status: implemented
classification_basis: 'Manifest, static auditor, dynamic smoke slice, ACC adapter, reports, and contract tests are implemented; future work is expanding dynamic coverage, not establishing the boundary.'
date: 2026-05-12
supersedes: []
superseded_by: null
extends: [ADR-126, ADR-146, ADR-150, ADR-151, ADR-189, ADR-256]
implementation_files:
  - manifests/primitive-authority.yaml
  - scripts/primitive_authority_audit.py
  - scripts/cos-primitive-authority-audit
  - docs/architecture/primitive-authority-write-effects.md
  - docs/reports/primitive-authority-latest.json
  - docs/reports/primitive-authority-latest.md
  - tests/contracts/test_primitive_authority_contract.py
  - tests/contracts/test_primitive_authority_static_audit.py
  - tests/contracts/test_primitive_authority_dynamic_smoke.py
  - tests/unit/test_primitive_authority_audit.py
  - tests/unit/test_acc_authority_adapter.py
tier: maintainer
tags: [agentic-primitives, authority, write-effects, consumer-boundary, acc]
---
# ADR-276: Primitive Authority and Write-Effects Audit

## Status

Accepted and implemented for the first ratchet.

## Context

Cognitive OS already separates several concepts:

- `SCOPE` says whether a primitive is intended for the SO, a consumer project, or both.
- Consumer availability says whether a primitive is projected or only local evidence.
- Projection profiles say which files are copied, linked, or generated into consumer workspaces.
- Protected config write guards block direct agent writes to control-plane paths.
- Consumer improvement proposal imports are `runtime_effect: none`.
- `.ai` consumer smokes prove selected generated overlays do not mutate real consumers.

These controls were necessary but not sufficient. They answered visibility and
selected write paths, but not the higher-level question:

> When a script or shared primitive runs, which roots may it read and write, and
> how do we detect obvious writes outside that authority?

Without a first-class authority layer, agents could confuse “projected” with
“allowed to mutate”, or “SO-local” with “safe to run inside a consumer project”.

## Decision

Introduce `manifests/primitive-authority.yaml` as the canonical authority
contract for primitive/script write effects.

The contract defines these modes:

- `observe-only`
- `propose-only`
- `project-local-write`
- `os-maintainer-write`
- `profile-projection-write`
- `dangerous-human-approved`

Authority can be explicit per path or derived from existing sources:

- `manifests/primitive-scope-classification.yaml`
- `manifests/primitive-consumer-availability.yaml`
- `manifests/primitive-projection-profiles.yaml`
- `manifests/shell-ci-projection.yaml`
- generated primitive readiness ledgers
- `manifests/protected-config-write-policy.yaml`

Add `scripts/primitive_authority_audit.py` and wrapper
`scripts/cos-primitive-authority-audit` to produce JSON and Markdown reports at:

- `docs/reports/primitive-authority-latest.json`
- `docs/reports/primitive-authority-latest.md`

The audit has two layers:

1. Static detection of obvious write APIs and shell write operations.
2. Dynamic filesystem-delta smokes for the initial high-risk/safe-to-run slice:
   consumer improvement export/import, Shell/CI projection, and `cos_init` Codex
   projection.

ACC consumes this report as `authority_write_effects` so primitive capability
coverage includes write-boundary evidence.

## Blocking contradictions

The first ratchet blocks only high-confidence contradictions:

- `propose-only` writing live hooks/rules/skills/scripts/templates/manifests or
  consumer source/secrets;
- `observe-only` writing live runtime/control-plane surfaces;
- project/shared primitives deriving `os-maintainer-write` by accident;
- profile projection attempting to write secrets.

The audit intentionally does not claim perfect behavior for every argument of
every script. It establishes a durable contract, catches obvious write-surface
contradictions, and creates a ratchet for expanding dynamic proof.

## Consequences

Positive:

- Scope, projection, and write authority are no longer conflated.
- Propose-only and profile-projection paths now have machine-readable guardrails.
- ACC can surface authority drift as coverage debt.
- Future dynamic write-effect smokes have a stable manifest and report shape.

Tradeoffs:

- Static detection is conservative and can miss computed paths.
- Some legitimate scripts are only classified by derived defaults until explicit
  entries are added.
- Exhaustive argument-space proof remains out of scope for this first ratchet.

## Validation

```bash
python3 scripts/primitive_authority_audit.py --project-dir . --json --fail-on-block
python3 -m pytest \
  tests/contracts/test_primitive_authority_contract.py \
  tests/contracts/test_primitive_authority_static_audit.py \
  tests/contracts/test_primitive_authority_dynamic_smoke.py \
  tests/unit/test_primitive_authority_audit.py \
  tests/unit/test_acc_authority_adapter.py -q
```
## Operational Guide

### What changes for the operator

Treat `manifests/primitive-authority.yaml` as the write-effects authority ledger for scripts and primitives. Projection, consumer availability, and scope are not enough to prove a primitive may mutate a path; the authority report is the place to check whether a write is allowed, propose-only, OS-maintainer-only, or dangerous-human-approved.

### Daily operational pattern

1. Before adding or changing a script with write behavior, classify its authority mode in `manifests/primitive-authority.yaml` or ensure the derived default is correct.
2. Run `scripts/cos-primitive-authority-audit` after changing scripts, projection code, protected config policy, or primitive scope manifests.
3. Review `docs/reports/primitive-authority-latest.{json,md}` for block findings before trusting ACC coverage.
4. Add dynamic smoke coverage only for safe-to-run representative paths; do not claim exhaustive argument-space proof.

### When sources disagree

If scope/projection metadata says a primitive is visible to consumers but authority says it is observe-only or propose-only, authority wins for write behavior. If an audit finding conflicts with intended behavior, update the manifest or script so the write boundary is explicit rather than relying on naming or convention.

### Reading guide for cold readers

Start with `docs/architecture/primitive-authority-write-effects.md`, then inspect `manifests/primitive-authority.yaml` and `scripts/primitive_authority_audit.py`. The first ratchet catches high-confidence write-boundary contradictions; broader dynamic proof is intentionally incremental.

