# Agent Capability Coverage — Compact

> Context diet entrypoint. Read this before opening `docs/acc/latest.json`.

Generated: 2026-05-06T08:02:28Z
Gate: pass (reconstruction)
ACC: 0.9320
ACC effective: 0.9631
Capabilities: 1725
Findings: 195
New debt gate: pass (0)
Primitive fitness reports: 0

## Warnings

- coverage_debt:195

## Mapping Weights

- aligned: 2990
- missing: 0
- overexposed: 0
- partial: 199
- stale: 0
- unverified: 19

## Consumer Accessibility

- lifecycle-declared-consumer-candidate: 2
- lifecycle-declared-maintainer: 1
- maintainer-only: 57
- profile-driver: 19
- projected-consumer-surface: 347
- shell-ci-candidate: 15
- so-local-only: 1284

## Top Findings

- `script:scripts/cos-key-learnings-capture` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/security-red-team` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `harness_coverage:hooks/aci-observation-capture.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/adaptive-bypass.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/adr-detector.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/adr-relevance-suggest.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/adr-section-validator.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/agent-bash-cwd-enforcer.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof

## New Debt

- none

## Context Diet Rule

- Do not open full JSON ledgers unless debugging the pipeline itself.
- Prefer this compact file, `python3 scripts/acc_pipeline.py --brief`, or targeted JSON queries.
- Subagents should receive only selected rows/findings, not complete ACC/readiness reports.
