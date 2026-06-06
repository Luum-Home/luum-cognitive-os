# Agent Capability Coverage — Compact

> Context diet entrypoint. Read this before opening `docs/07-Capabilities/acc/latest.json`.

Generated: 2026-06-06T02:29:07Z
Gate: pass (reconstruction)
ACC: 0.9360
ACC effective: 0.9678
Capabilities: 3272
Findings: 180
New debt gate: pass (0)
Primitive fitness reports: 0

## Warnings

- coverage_debt:180

## Mapping Weights

- aligned: 6376
- missing: 0
- overexposed: 0
- partial: 433
- stale: 0
- unverified: 3

## Consumer Accessibility

- install-profile-managed: 19
- lifecycle-declared-consumer-candidate: 188
- lifecycle-declared-maintainer: 79
- maintainer-only: 315
- profile-driver: 19
- projected-consumer-surface: 1806
- runtime-evidence: 8
- shell-ci-candidate: 15
- skill-referenced-not-projectable: 12
- so-local-only: 811

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
