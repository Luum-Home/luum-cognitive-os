# Agent Capability Coverage — Compact

> Context diet entrypoint. Read this before opening `docs/acc/latest.json`.

Generated: 2026-05-12T18:44:49Z
Gate: pass (reconstruction)
ACC: 0.9839
ACC effective: 0.9902
Capabilities: 2962
Findings: 71
New debt gate: pass (0)
Primitive fitness reports: 0

## Warnings

- coverage_debt:71

## Mapping Weights

- aligned: 6101
- missing: 0
- overexposed: 0
- partial: 78
- stale: 0
- unverified: 22

## Consumer Accessibility

- install-profile-managed: 19
- lifecycle-declared-consumer-candidate: 65
- lifecycle-declared-maintainer: 58
- maintainer-only: 60
- profile-driver: 19
- projected-consumer-surface: 1356
- runtime-evidence: 8
- shell-ci-candidate: 15
- skill-referenced-not-projectable: 12
- so-local-only: 1350

## Top Findings

- `script:scripts/cos-key-learnings-capture` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/security-red-team` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `harness_coverage:hooks/agent-control-inbound-guard.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/agent-launch-confirmed.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/ai-provider-identity-guard.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/contextual-rule-loader.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/cosd-auth-guard.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/doc-sync-detector.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof

## New Debt

- none

## Context Diet Rule

- Do not open full JSON ledgers unless debugging the pipeline itself.
- Prefer this compact file, `python3 scripts/acc_pipeline.py --brief`, or targeted JSON queries.
- Subagents should receive only selected rows/findings, not complete ACC/readiness reports.
