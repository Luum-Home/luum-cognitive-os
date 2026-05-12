---
adr: 272
title: Structural Rule Backend Boundary
status: accepted
implementation_status: not-applicable
date: '2026-05-12'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: 'policy-only: boundary decision constraining future structural
  backend integrations; no runtime implementation is claimed'
verification:
  level: not-applicable
  commands:
  - python3 -m pytest tests/contracts/test_structural_rule_backend_boundary.py -q
  proves:
  - decision_state
  - contract_test
---

# ADR-272: Structural Rule Backend Boundary

Status: Accepted
Date: 2026-05-12

## Status

Accepted.

## Context

Cognitive OS now has two separate projection layers:

1. a generated maintainer `.ai/` overlay that records primitive contracts,
   lifecycle metadata, per-harness fidelity, and runtime-evidence boundaries; and
2. governed harness projection drivers invoked by `lib/adapter_compile.py`,
   `scripts/cos-adapter-compile`, and `cos adapters compile` to emit native
   consumer files such as `AGENTS.md`, `.cursor/rules/*.mdc`, and
   `.github/copilot-instructions.md`.

External tools such as `rulesync` validate the single-source/multi-target rule
compiler pattern. They can be useful for producing structural instruction files,
but they do not own COS-specific runtime evidence, primitive lifecycle state,
intervention ledgers, or per-harness enforcement claims.

## Decision

COS keeps the first-party adapter compiler as the default projection authority.
A `rulesync`-style backend may be added later only as an optional
`structural-advisory` file emitter behind the existing COS compiler contract.

The external backend must not own or rewrite:

- `manifests/primitive-contracts.yaml`;
- `manifests/primitive-lifecycle.yaml`;
- `manifests/harness-projection.yaml`;
- `.ai/profiles/*.json` fidelity claims;
- runtime evidence streams such as `primitive-interventions.jsonl`; or
- any claim that a host enforces runtime hooks, blocking gates, MCP wiring, or
  CI behavior.

COS-owned code must filter all projection through declared fidelity first. If a
primitive is `structural-advisory`, an optional backend may emit instructions,
rules, or Markdown. It must not upgrade that primitive into runtime enforcement.

## Acceptance Criteria

- The first-party adapter compiler remains the public entry point for native
  projection.
- Optional third-party rule backends are limited to structural advisory files.
- Fidelity summaries in compile receipts continue to come from generated COS
  profiles/manifests, not from external backend output.
- Any future backend integration requires license/clean-room review and a parity
  test proving it cannot overclaim runtime enforcement.

## Consequences

Positive:

- COS keeps its unique fidelity matrix and runtime-evidence model.
- Future generated rule-file support can reuse an external backend without
  surrendering primitive governance.
- Consumer projections remain honest about what a host can actually enforce.

Negative:

- COS still maintains harness projection code for now.
- A future backend adapter needs explicit mapping, licensing review, and parity
  tests before use.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Defer the decision indefinitely | Leaves the gap surfaced in this ADR's §Context unaddressed and risks accumulating cost without bounds. |
| Implement only a subset of §Decision | Already attempted in prior iterations; left behind unverified claims that this ADR exists to close. |

## Verification

```bash
python3 -m pytest tests/contracts/test_structural_rule_backend_boundary.py -q
```

