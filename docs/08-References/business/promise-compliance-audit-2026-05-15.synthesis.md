---
type: reference-synthesis
source: docs/08-References/business/promise-compliance-audit-2026-05-15.md
provenance: "Captures a 2026-05-15 repository audit of public/product promises against actual evidence, so maturity claims stay honest and drift is caught before it reaches external docs."
---

## What it is

A point-in-time compliance audit that checks whether Cognitive OS's public-facing claims (features.md, README, business docs) match the repository's actual evidence. It uses repository-local automated checks (claim gates, aspirational audit, tier-claim audits, contract tests) rather than external validation, and produces a verdict plus a prioritized remediation list.

## Key mechanics

- **Four maturity levels** that public docs must not blur together: (1) core verified runtime behavior, (2) driver-projected behavior with harness limits, (3) maintainer/dogfood-only behavior, (4) aspirational/dormant/structurally-projected surfaces.
- **Automated evidence commands**: `cos-public-claim-gate`, `claim_proof_audit.py`, `aspirational_audit.py`, `cos-tier-claim-audit`, `cos-manifest-tier-claim-audit`, and contract tests — run and their results tabulated.
- At audit time: aspirational audit showed 1163 total components (201 REAL, 626 ON_DEMAND, 203 DORMANT, 68 ASPIRATIONAL, 65 METADATA; DORMANT+ASPIRATIONAL ratio 23.3%). Manifest tier claim audit returned 790 findings (474 warnings).
- **Remediation pass** (same date) fixed the highest-risk public fronts: SDD phase-count consistency (8 core phases), multi-IDE proof-level vocabulary, Developer Experience counts, Automation Workflows DORMANT labeling, Observability stack wording (JSONL/OTel/MCP replacing Langfuse/LiteLLM), and manifest-governance "every primitive" overclaim removal.
- **Agentic literacy boundary** proposed as a first-class product rule: COS must not replace developer literacy in the underlying harnesses (Claude Code, Codex, OpenCode, Goose), PI/prompt-injection defense, and SDD — it should teach, not hide, the underlying operation.
- Produces three compliance tables: promises that **comply**, promises that **partially complied** at audit time (with risk notes), and promises that **did not comply/overpromised** (with required corrections), plus a full feature-by-feature compliance matrix.

## Relations & where used

References `ADR-316` (proposed as the agentic literacy boundary decision), `manifests/harness-projection.yaml`, `manifests/harness-driver-capabilities.yaml`, `tests/contracts/test_product_zones.py`, `docs/06-Daily/reports/manifest-tier-warning-backlog-2026-05-15.md`, and `features.md` (the primary remediation target). Establishes the proof-level vocabulary (`native-lifecycle`, `runtime-smoke`, `governed-wrapper-enforced`, `structural`, `planned`, `unsupported`) referenced by adjacent portability/adoption docs.

## Status / caveats

This is a **dated point-in-time snapshot** (2026-05-15) — static counts (hooks, skills, rules, scripts) and audit findings will drift as the repo evolves; treat figures as accurate only at the stated timestamp. The document explicitly frames itself as reporting proof-corpus/lexical mapping, not semantic runtime truth (e.g., "505 mapped claims, 0 weak/unmapped" is a proof-signal count, not a correctness guarantee). Acceptance criteria for closing the audit are listed but the source doc does not confirm whether they were later met — no closure status is recorded here.
