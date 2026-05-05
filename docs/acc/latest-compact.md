# Agent Capability Coverage — Compact

> Context diet entrypoint. Read this before opening `docs/acc/latest.json`.

Generated: 2026-05-05T17:00:01Z
Gate: block (reconstruction)
ACC: 1.0000
ACC effective: 1.0000
Capabilities: 776
Findings: 0
New debt gate: block (2)

## Warnings

- none

## Mapping Weights

- aligned: 2119
- missing: 0
- overexposed: 0
- partial: 0
- stale: 0
- unverified: 0

## Consumer Accessibility

- maintainer-only: 57
- profile-driver: 19
- shell-ci-candidate: 15
- so-local-only: 685

## Top Findings

- none

## New Debt

- `script:scripts/cos-deps-install.sh` [unreviewed-local-default]: new capability matched a broad local-surface default instead of an explicit row or projection proof
- `script:scripts/cos_deps_install.py` [unreviewed-local-default]: new capability matched a broad local-surface default instead of an explicit row or projection proof

## Context Diet Rule

- Do not open full JSON ledgers unless debugging the pipeline itself.
- Prefer this compact file, `python3 scripts/acc_pipeline.py --brief`, or targeted JSON queries.
- Subagents should receive only selected rows/findings, not complete ACC/readiness reports.
