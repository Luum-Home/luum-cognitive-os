# Agent Capability Coverage — Compact

> Context diet entrypoint. Read this before opening `docs/acc/latest.json`.

Generated: 2026-05-05T17:39:13Z
Gate: pass (reconstruction)
ACC: 0.9973
ACC effective: 0.9986
Capabilities: 802
Findings: 2
New debt gate: pass (0)

## Warnings

- coverage_debt:2

## Mapping Weights

- aligned: 2190
- missing: 0
- overexposed: 0
- partial: 6
- stale: 0
- unverified: 0

## Consumer Accessibility

- lifecycle-declared-consumer-candidate: 2
- lifecycle-declared-maintainer: 1
- maintainer-only: 57
- profile-driver: 19
- shell-ci-candidate: 15
- so-local-only: 708

## Top Findings

- `script:scripts/cos-key-learnings-capture` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/security-red-team` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion

## New Debt

- none

## Context Diet Rule

- Do not open full JSON ledgers unless debugging the pipeline itself.
- Prefer this compact file, `python3 scripts/acc_pipeline.py --brief`, or targeted JSON queries.
- Subagents should receive only selected rows/findings, not complete ACC/readiness reports.
