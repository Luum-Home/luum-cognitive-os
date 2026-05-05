# Agent Capability Coverage — Compact

> Context diet entrypoint. Read this before opening `docs/acc/latest.json`.

Generated: 2026-05-05T16:47:00Z
Gate: pass (reconstruction)
ACC: 1.0000
ACC effective: 1.0000
Capabilities: 770
Findings: 0
New debt gate: pass (0)

## Warnings

- none

## Mapping Weights

- aligned: 2102
- missing: 0
- overexposed: 0
- partial: 0
- stale: 0
- unverified: 0

## Consumer Accessibility

- maintainer-only: 57
- profile-driver: 19
- shell-ci-candidate: 15
- so-local-only: 679

## Top Findings

- none

## New Debt

- none

## Context Diet Rule

- Do not open full JSON ledgers unless debugging the pipeline itself.
- Prefer this compact file, `python3 scripts/acc_pipeline.py --brief`, or targeted JSON queries.
- Subagents should receive only selected rows/findings, not complete ACC/readiness reports.
