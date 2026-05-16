# Agent Capability Coverage — Compact

> Context diet entrypoint. Read this before opening `docs/07-Capabilities/acc/latest.json`.

Generated: 2026-05-16T00:42:49Z
Gate: pass (reconstruction)
ACC: 0.9322
ACC effective: 0.9661
Capabilities: 3138
Findings: 184
New debt gate: pass (0)
Primitive fitness reports: 0

## Warnings

- coverage_debt:184

## Mapping Weights

- aligned: 6094
- missing: 0
- overexposed: 0
- partial: 443
- stale: 0
- unverified: 0

## Consumer Accessibility

- install-profile-managed: 19
- lifecycle-declared-consumer-candidate: 193
- lifecycle-declared-maintainer: 76
- maintainer-only: 315
- profile-driver: 19
- projected-consumer-surface: 1751
- runtime-evidence: 4
- shell-ci-candidate: 15
- skill-referenced-not-projectable: 12
- so-local-only: 734

## Top Findings

- `script:scripts/adr_implementation_ledger.py` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/adr_tombstone.py` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/agent_work_ledger.py` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/approval_ledger.py` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/check_absolute_paths.py` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/check_test_quality.py` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/check_test_ratchet.py` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/claim_task.py` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion

## New Debt

- none

## Context Diet Rule

- Do not open full JSON ledgers unless debugging the pipeline itself.
- Prefer this compact file, `python3 scripts/acc_pipeline.py --brief`, or targeted JSON queries.
- Subagents should receive only selected rows/findings, not complete ACC/readiness reports.
