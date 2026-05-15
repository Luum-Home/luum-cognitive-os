---
adr: 316
title: Agentic Literacy Before OS Abstraction
status: accepted
implementation_status: implemented
date: '2026-05-15'
extends:
- ADR-057
- ADR-064
- ADR-123
- ADR-258
- ADR-312
supersedes: []
superseded_by: null
implementation_files:
- docs/08-References/business/promise-compliance-audit-2026-05-15.md
- docs/04-Concepts/architecture/harness-engineering.md
- docs/08-References/business/developer-confidence.md
- docs/03-PoCs/research/minimal-context-principle.md
tier: core
tags:
- product-boundary
- developer-experience
- harness-engineering
- portability
- education
classification_basis: accepted product and architecture boundary implemented as documentation
  doctrine; no remaining in-scope work for this ADR, and future education or harness
  material is separate/out-of-scope follow-up.
verification:
  level: medium
  commands:
  - .venv/bin/python -m pytest tests/contracts/test_harness_engineering_docs.py tests/contracts/test_product_zones.py
    -q
  - scripts/cos-public-claim-gate --json
  - bash scripts/cos measure harness-profiles --json
  proves:
  - harness doctrine and product zones remain linked and executable
  - public autonomous/self-improvement claims remain bounded
  - minimal and full harness surfaces remain measurable
---

# ADR-316 — Agentic Literacy Before OS Abstraction

## Status

Accepted and implemented as documentation doctrine — 2026-05-15.

<!-- SCOPE: both -->

## Context

The operator raised a strategic concern on 2026-05-15: building a full Cognitive OS may be less valuable than letting developers learn PI / prompt-injection defense, Claude Code, OpenCode, Goose, Codex, harness engineering, and SDD directly.

The repository already contains strong supporting doctrine:

- `docs/04-Concepts/architecture/harness-engineering.md` says a stronger harness is not necessarily larger and should prefer simple file-system/shell primitives first.
- `docs/04-Concepts/root/kernel-contract.md` keeps the kernel intentionally narrow.
- `docs/04-Concepts/root/product-zones.md` says core should stay small and extensions should not crowd the product story.
- `docs/08-References/business/developer-confidence.md` says Cognitive OS should accompany a project, not invade it.
- `docs/03-PoCs/research/minimal-context-principle.md` says context and governance overhead can reduce task success for simple work.

However, the missing explicit rule is pedagogical and architectural: Cognitive OS must not become a substitute for developer competence in the underlying agentic tools and workflows.

## Decision

Cognitive OS is an operational discipline layer, not an agentic literacy replacement.

It may provide:

- durable memory;
- governance and safety gates;
- evidence-backed verification;
- harness projection drivers;
- SDD playbooks and fast paths;
- reusable skills, rules, hooks, and manifests.

It must not hide or replace:

- direct developer understanding of the active harness;
- prompt-injection and tool-permission threat models;
- native Claude Code, Codex, OpenCode, Goose, Cursor, or other host capabilities;
- SDD as a reasoning discipline;
- shell, git, filesystem, and test fundamentals;
- the difference between native runtime enforcement, governed-wrapper enforcement, structural projection, and planned support.

## Product Rule

Every new default-facing COS primitive must answer:

1. What underlying developer skill does this reinforce?
2. What harness/runtime surface does it rely on?
3. Does it teach or expose that surface, or hide it behind magic?
4. Can a user bypass COS and still understand the manual workflow?
5. Is this default-core, team, maintainer, lab, or purely experimental?

If a primitive mainly hides a simple operation without reducing measurable risk, it should not be default-core.

## Documentation Rule

Product and onboarding docs must distinguish these levels:

| Level | Meaning |
|---|---|
| `native-lifecycle` | Host runtime emits lifecycle events and COS projection is tested. |
| `runtime-smoke` | A signed smoke proves runtime behavior for the host/slice. |
| `governed-wrapper-enforced` | COS wrapper enforces behavior around a host that lacks full native parity. |
| `structural` | Files/configs/instructions are generated; runtime enforcement is not claimed. |
| `planned` | Product direction exists, but implementation/proof is absent. |
| `unsupported` | Intentionally out of scope. |

Docs must not collapse these into a single “supported” or “REAL” label.

## Consequences

### Positive

- Developers learn the actual harnesses instead of only learning COS ceremony.
- COS remains valuable as a portable guardrail layer rather than a heavy framework.
- Public claims become easier to defend because support levels are explicit.
- Skills become more useful as teaching playbooks, not just command wrappers.

### Negative / Trade-offs

- Some “magic” UX will be slower to promote because it must expose its underlying surface.
- Public docs may look less impressive after splitting native, wrapper, structural, and planned support.
- Default-core will shrink; some existing primitives may move to team, maintainer, lab, or experimental profiles.

## Acceptance Criteria

- The promise compliance audit exists and names the missing agentic literacy boundary.
- First-contact docs link to the audit or this ADR.
- Future feature claims use proof-level vocabulary for harness support.
- Default profile changes prefer teaching, verification, and risk reduction over abstraction volume.
