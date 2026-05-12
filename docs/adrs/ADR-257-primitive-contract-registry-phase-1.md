---
adr: 257
title: Primitive Contract Registry Phase 1
status: accepted
implementation_status: partial
date: '2026-05-09'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted/implemented text with explicit partial/deferred scope
---

# ADR-257 — Primitive Contract Registry Phase 1

## Status

Accepted — implemented

**Date:** 2026-05-09  
**Owner:** platform-safety  
**Tier:** core  
**Related:** ADR-057, ADR-064, ADR-126, ADR-146, ADR-147, ADR-150, ADR-154, ADR-189, ADR-190, ADR-205, ADR-256

## Context

Cognitive OS already had the architecture direction for IDE-agnostic primitives:

```text
canonical behavior
  -> harness-specific projection
  -> proof/fidelity boundaries
  -> observable evidence
```

The deep review in
`docs/reports/primitive-contract-cross-ide-premise-investigation-2026-05-09.md`
confirmed that this was contemplated across multiple ADRs:

- ADR-057 says to author behavior once and project through harness drivers.
- ADR-064 abstracts harness integration surfaces.
- ADR-126 records primitive lifecycle metadata.
- ADR-146 and ADR-147 provide readiness and ACC ledgers.
- ADR-150, ADR-154, ADR-159, and ADR-160 provide projection profiles and broad
  structural harness projection.
- ADR-189 reports implementation coverage across surfaces.
- ADR-190 and ADR-205 provide action receipts and trace joining.
- ADR-256 names the missing root contract: primitive contract registry plus
  runtime intervention evidence.

The remaining gap was implementation, not concept:

```text
primitive-lifecycle/readiness metadata
+ primitive source files
  -> manifests/primitive-contracts.yaml
  -> projection/fidelity report
  -> primitive-interventions.jsonl
  -> codebase-itinerary.jsonl
  -> trace_joiner
```

Before this ADR, `manifests/primitive-contracts.yaml` did not exist.
`scripts/cos_init.py` projected to many IDEs/harnesses, but projection was driven
by installer/profile logic rather than a per-primitive portable contract row.

## Decision

Implement ADR-256 Phase 1 by adding `manifests/primitive-contracts.yaml` as the
first canonical primitive contract registry.

The initial registry contains five existing high-value primitives:

1. `destructive-git-blocker`
2. `destructive-rm-blocker`
3. `reinvention-check`
4. `large-file-advisor`
5. `skill-router`

Each contract row declares:

- `id`, `family`, `source`, and optional implementation refs;
- portable `intent`;
- portable `trigger` shape;
- required capabilities, including `emit_intervention` for ADR-256 compatibility;
- preferred/fallback actions and reason codes;
- evidence sinks, including future
  `.cognitive-os/metrics/primitive-interventions.jsonl`;
- proof tests;
- projection fidelity for Claude, Codex, OpenCode, Cursor, VS Code Copilot, and
  Shell/CI;
- downstream impact metadata.

OpenCode is deliberately modeled as `host-plugin-lifecycle-capable`, not as
structural-only forever and not as runtime-enforced today. OpenCode enforcement
must use native OpenCode permissions and plugin lifecycle events such as
`tool.execute.before` / `tool.execute.after` before COS invents any parallel
OpenCode enforcement layer.

Cursor and VS Code Copilot remain `structural-advisory` for these primitives
until a real runtime adapter/smoke exists.

## Consequences

### Positive

- ADR-256 now has a concrete Phase 1 source of truth.
- The first five primitives have portable contracts instead of only lifecycle and
  hook metadata.
- Future projection/fidelity reporting can consume a deterministic registry.
- Structural-only IDEs cannot accidentally inherit enforcement claims from
  Claude/Codex/OpenCode.
- OpenCode's plugin-capable runtime surface is represented without overclaiming
  signed enforcement.

### Negative

- The registry initially duplicates some facts from `manifests/primitive-lifecycle.yaml`.
  This is accepted for Phase 1 because the contract adds fields lifecycle rows do
  not carry: required capabilities, portable triggers, reason codes, and
  per-harness fidelity.
- The registry is not yet consumed by `scripts/cos_init.py`; projection remains
  profile/driver-driven until a later ADR-256 phase.
- Runtime ledgers are still future work: this ADR does not implement
  `primitive-interventions.jsonl`, `codebase-itinerary.jsonl`, or trace joiner
  integration.

## Alternatives rejected

| Alternative | Rejection rationale |
|---|---|
| Add more IDE adapters first | Rejected because it would expand projection surface while the primitive source-of-truth gap remains. |
| Treat `primitive-lifecycle.yaml` as sufficient | Rejected because lifecycle rows do not declare portable triggers, required capabilities, reason codes, or per-harness fidelity. |
| Generate OpenCode enforcement through a COS-only wrapper first | Rejected because OpenCode already has native permissions/plugins; COS should adapt to them before inventing a parallel layer. |
| Implement all ADR-256 phases at once | Rejected because the correct reconstruction slice is the minimal registry plus contract tests before runtime ledger wiring. |

## Verification

```bash
python3 -m pytest tests/contracts/test_primitive_contract_registry.py -q
python3 -m pytest tests/contracts/test_harness_implementation_phases.py -q
python3 - <<'PY'
import yaml
for path in [
    'manifests/primitive-contracts.yaml',
    'manifests/harness-projection.yaml',
    'manifests/harness-driver-capabilities.yaml',
    'manifests/ai-agent-harness-landscape.yaml',
]:
    yaml.safe_load(open(path))
    print(path, 'ok')
PY
```

Acceptance criteria:

```text
1. `manifests/primitive-contracts.yaml` exists.
2. It contains the five initial contracts from ADR-256 Phase 1.
3. Each contract declares source, family, intent, trigger, required capabilities,
   actions/reason codes, evidence sinks, and projection fidelity for Claude,
   Codex, OpenCode, Cursor, VS Code Copilot, and Shell/CI.
4. Contract tests validate schema and source/proof paths.
5. Contract tests prevent structural-only IDE harnesses from claiming enforcement.
```
