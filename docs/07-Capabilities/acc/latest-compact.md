# Agent Capability Coverage — Compact

> Context diet entrypoint. Read this before opening `docs/07-Capabilities/acc/latest.json`.

Generated: 2026-06-17T23:58:22Z
Gate: pass (reconstruction)
ACC: 0.9186
ACC effective: 0.9190
Capabilities: 3683
Findings: 288
New debt gate: not_evaluated (0)
Primitive fitness reports: 0

## Warnings

- coverage_debt:181

## Mapping Weights

- aligned: 7351
- missing: 0
- overexposed: 0
- partial: 434
- stale: 214
- unverified: 3

## Consumer Accessibility

- install-profile-managed: 19
- lifecycle-declared-consumer-candidate: 296
- lifecycle-declared-maintainer: 213
- maintainer-only: 315
- profile-driver: 19
- projected-consumer-surface: 1945
- runtime-evidence: 9
- shell-ci-candidate: 15
- skill-referenced-not-projectable: 3
- so-local-only: 849

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
