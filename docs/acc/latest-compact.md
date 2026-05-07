# Agent Capability Coverage — Compact

> Context diet entrypoint. Read this before opening `docs/acc/latest.json`.

Generated: 2026-05-07T15:11:43Z
Gate: pass (reconstruction)
ACC: 0.9744
ACC effective: 0.9844
Capabilities: 1843
Findings: 65
New debt gate: pass (0)
Primitive fitness reports: 0

## Warnings

- coverage_debt:65

## Mapping Weights

- aligned: 3352
- missing: 0
- overexposed: 0
- partial: 69
- stale: 0
- unverified: 19

## Consumer Accessibility

- lifecycle-declared-consumer-candidate: 2
- lifecycle-declared-maintainer: 1
- maintainer-only: 57
- profile-driver: 19
- projected-consumer-surface: 917
- shell-ci-candidate: 15
- so-local-only: 832

## Top Findings

- `script:scripts/cos-key-learnings-capture` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/security-red-team` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `harness_coverage:hooks/agent-control-inbound-guard.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/agent-launch-confirmed.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/context-watchdog.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/contextual-rule-loader.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/cosd-auth-guard.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof
- `harness_coverage:hooks/doc-sync-detector.sh` [partial/medium]: Harness implementation coverage gap → classify the gap policy or add the missing harness projection/proof

## New Debt

- none

## Context Diet Rule

- Do not open full JSON ledgers unless debugging the pipeline itself.
- Prefer this compact file, `python3 scripts/acc_pipeline.py --brief`, or targeted JSON queries.
- Subagents should receive only selected rows/findings, not complete ACC/readiness reports.
