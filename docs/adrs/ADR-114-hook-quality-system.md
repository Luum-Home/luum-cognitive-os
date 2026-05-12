---
adr: 114
title: Hook Quality System
status: accepted
implementation_status: implemented
date: '2026-05-02'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: 'hook-quality manifest, audit script, and contract tests implement the hook quality system'
---

# ADR-114 — Hook Quality System

<!-- SCOPE: OS -->

## Status

Accepted — 2026-05-02.

## Context

Cognitive OS hooks are not helper scripts. They are automatic runtime
primitives executed by IDEs, CLIs, and governed runners before or after agent
actions. A broken hook can silently remove security, quality, concurrency, or
memory guarantees from every project using the OS.

The risk increases with portability. Claude Code, Codex, and future IDEs do not
share the same native hook surface. The same hook may run as:

- a native projected hook in one harness,
- a governed-runner hook in another,
- a COS-owned runtime step in a bare CLI, or
- an unsupported surface with no guarantee.

Therefore script quality cannot be asserted by `bash -n` alone. Quality must be
attached to the **hook primitive contract**: script, event, matcher, criticality,
blocking behavior, degradation behavior, harness tier, tests, and performance
budget.

## Decision

Introduce a **Hook Quality System** with a generated/audited manifest:

```text
manifests/hook-quality.yaml
```

and an enforcement command:

```bash
python3 scripts/hook_quality_audit.py --sync
python3 scripts/hook_quality_audit.py --check
```

The manifest is generated from the canonical hook registry in
`cognitive-os.yaml > harness.hooks`. It records one quality contract per hook
primitive:

- script path
- canonical event
- matcher
- scope
- criticality
- runtime budget
- safe degradation policy
- harness tiers for Claude and Codex
- discovered behavior/contract/chaos tests

The audit fails when:

- `manifests/hook-quality.yaml` drifts from `cognitive-os.yaml`,
- a registered hook script is missing,
- a hook script fails `bash -n`,
- a hook lacks a valid `SCOPE` header,
- a harness tier is not one of `native`, `governed`, `cos_owned`, or
  `unsupported`, or
- a required critical hook lacks behavior coverage.

## Primitive Creation and Update Rule

Any new or changed hook primitive must follow this sequence:

1. Add/update the hook script under `hooks/` with a valid `SCOPE` header.
2. Register/update it in `cognitive-os.yaml > harness.hooks`.
3. Run `python3 scripts/hook_quality_audit.py --sync`.
4. Add behavior, contract, or chaos coverage if the hook is critical.
5. Run `python3 scripts/hook_quality_audit.py --check`.

This makes primitive updates explicit and prevents the repo from accumulating
silent automatic hooks that are wired but unproven.

## Harness Tier Semantics

| Tier | Meaning |
|---|---|
| `native` | The harness emits the event and the settings driver projects the hook. |
| `governed` | COS wraps the action and executes the canonical hook chain. |
| `cos_owned` | COS owns the runtime action or scheduler directly. |
| `unsupported` | No portability guarantee exists for that surface. |

The product promise is not equal hook counts across IDEs. The promise is that
each automatic hook surface has an explicit tier and evidence.

## Consequences

- Hook quality becomes machine-auditable instead of relying on manual review.
- New automatic hooks cannot be added without appearing in the quality manifest.
- Codex and future IDE gaps remain honest: governed is distinct from native.
- Critical hooks must carry behavior evidence, reducing the chance that a hook
  creates more operational problems than product value.
- The manifest can later feed `cos doctor hooks`, release gates, and generated
  primitive documentation.

## Acceptance Criteria

- `python3 scripts/hook_quality_audit.py --sync` creates/updates
  `manifests/hook-quality.yaml` from `cognitive-os.yaml`.
- `python3 scripts/hook_quality_audit.py --check` passes on the committed repo.
- `tests/contracts/test_hook_quality_system.py` proves manifest sync, script
  existence/syntax, tier validity, and required critical-hook behavior coverage.

## Related

- [ADR-064 — Harness-Agnostic Cognitive OS](ADR-064-harness-agnostic-cognitive-os.md)
- [ADR-112 — Codex Governed Tool Layer](ADR-112-codex-governed-tool-layer.md)
- [Hook Quality System](../architecture/hook-quality-system.md)


## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep relying on `bash -n` only | Syntax checks do not prove hook criticality, matcher coverage, degradation behavior, or harness parity. |
| Maintain hook quality only in prose docs | Prose drifts from the canonical hook registry and cannot gate CI. |
| Make each harness own separate quality checks | Splits one hook primitive contract into incompatible harness-specific interpretations. |


## Verification

```bash
python3 scripts/hook_quality_audit.py --check
python3 -m pytest tests/contracts/test_hook_quality_system.py -q
```
