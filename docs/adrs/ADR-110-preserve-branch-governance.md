# ADR-110 — Preserve Branch Governance

<!-- SCOPE: OS -->

**Status**: Proposed
**Date**: 2026-05-02
**Author**: Matias Nahuel Améndola + Cognitive OS
**Related**: ADR-088 (provenance markers), ADR-089 (multi-session git coordination), ADR-106 (multi-session safety primitives), ADR-108 (concurrent agent safety layer), [Preserve Branch Governance Report](../reports/preserve-branch-governance-2026-05-02.md), [Preserve Branch Lifecycle](../architecture/preserve-branch-lifecycle.md)

## Status

Proposed. Initial doctor and behavior tests are part of the first implementation slice.

## Relationship to ADR-108 and ADR-111

ADR-110 is the preserve-branch primitive under the ADR-108 Concurrent Agent Safety Layer. It is intentionally narrower than ADR-108: it governs `codex/preserve-*` branches, manifests, ancestry checks, mixed-scope detection, and deletion proof. ADR-111 controls how this primitive is projected into consumer projects through configuration. ADR-110 controls the doctor contract and preserve-branch lifecycle semantics.

## Context

Cognitive OS increasingly creates preservation branches such as `codex/preserve-*` to avoid losing WIP during concurrent sessions, validation capsules, rollback planning, and automatic cleanup. This is good as a crash-safety mechanism, but it creates a new governance problem: preserved work can remain reachable in Git while not being active in `HEAD`.

A concrete failure surfaced during concurrent-agent safety validation: a testbed commit existed as a Git object, but it was not an ancestor of `HEAD`, so the active branch did not contain the files. The fix was a deliberate cherry-pick after ancestry and file-presence checks.

## Decision

Cognitive OS adopts explicit governance for `codex/preserve-*` branches.

This is a **dual-scope primitive**:

- **OS kernel scope**: Cognitive OS owns the contract, doctor, tests, reference implementation, and lifecycle documentation.
- **Consumer-project projection**: projects that install the SO receive the same governance through configurable branch patterns, manifest directories, base refs, and phase-aware strictness.

The policy is:

> Preserve automatically; reintegrate manually and selectively; delete only after proof.

## Required Controls

### 1. Preserve Manifest

Every preserve branch SHOULD have a manifest under:

```text
.cognitive-os/preserve-manifests/<safe-branch-name>.json
```

Minimum fields:

- `branch`
- `created_at`
- `created_by`
- `source_branch`
- `source_head`
- `reason`
- `scope`
- `status`
- `files`
- `integration_commit`
- `delete_after`

Allowed statuses:

- `open`
- `partially-integrated`
- `integrated`
- `obsolete`
- `delete-approved`

### 2. Mixed-Scope Detection

A preserve branch touching unrelated product areas must be flagged as mixed scope. Mixed-scope branches are not merge candidates; they require selective restore or split cherry-picks.

### 3. Ancestry Verification

A preserved commit being present is insufficient. The doctor must report whether the preserve tip is an ancestor of `HEAD`.

### 4. Integrated Branch Detection

If a preserve branch tip is already an ancestor of `HEAD`, the branch is a delete candidate unless its manifest says otherwise.

### 5. Reintegrate By Selection

Reintegration to `main` must be one of:

- selective file restore;
- targeted cherry-pick;
- reviewed merge when the branch is single-scope and current.

Automatic reintegration is prohibited.

## Doctor

The first tool is:

```bash
bash scripts/cos-doctor-preserve.sh
```

It must be portable across the SO repository and consumer projects:

```bash
bash scripts/cos-doctor-preserve.sh --project-dir /path/to/project --branch-pattern 'codex/preserve-*' --base-ref HEAD --json
```

Required detections:

1. preserve branch without manifest;
2. preserve branch mixed-scope;
3. preserve branch already integrated;
4. commit exists but is not ancestor of `HEAD`;
5. preserve branch candidate to delete.

## Invariants

1. No preserve branch is considered resolved without ancestry or explicit integration evidence.
2. No mixed-scope preserve branch should be merged wholesale.
3. Branch deletion requires proof that the branch is integrated, obsolete, or delete-approved.
4. The doctor must be read-only.
5. Governance must be testable without manual inspection.

## Consequences

### Positive

- Preserved WIP remains recoverable without becoming invisible operational debt.
- Operators can see which preserved branches are open, mixed, integrated, or deletable.
- Future automatic preservation flows have a durable manifest contract.

### Negative

- Preservation flows must write metadata or accept doctor warnings.
- Existing preserve branches without manifests will be noisy until reconciled.

## Verification

```bash
python3 -m pytest tests/behavior/test_cos_doctor_preserve.py -v
bash scripts/cos-doctor-preserve.sh --json
```

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Delete preserve branches after push | Unsafe; preserved branches may contain work that was not integrated. |
| Keep preserve branches forever | Creates opaque operational debt. |
| Trust commit existence | The testbed incident showed commit existence does not mean active branch integration. |
| Merge preserve branches wholesale | Mixed-scope branches can include unrelated or stale work. |
