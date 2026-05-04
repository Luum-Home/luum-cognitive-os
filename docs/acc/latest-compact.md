# Agent Capability Coverage — Compact

> Context diet entrypoint. Read this before opening `docs/acc/latest.json`.

Generated: 2026-05-04T20:46:31Z
Gate: pass (reconstruction)
ACC: 0.4814
ACC effective: 0.5183
Capabilities: 732
Findings: 89

## Warnings

- coverage_debt:89
- acc_below_threshold:0.4814<0.5

## Mapping Weights

- aligned: 960
- missing: 0
- overexposed: 0
- partial: 147
- stale: 0
- unverified: 887

## Consumer Accessibility

- lifecycle-declared-consumer-candidate: 49
- lifecycle-declared-maintainer: 74
- projected-consumer-surface: 297
- repo-skill-not-projectable: 38
- skill-referenced-not-projectable: 2
- so-local-only: 272

## Top Findings

- `script:scripts/aspirational_audit.py` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/check_mcp_servers.py` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/cos` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/cos-coordination-status.sh` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/cos-release-check.sh` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/cos-smoke.sh` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/cos-status.sh` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/cos-usage-report.sh` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion

## Context Diet Rule

- Do not open full JSON ledgers unless debugging the pipeline itself.
- Prefer this compact file, `python3 scripts/acc_pipeline.py --brief`, or targeted JSON queries.
- Subagents should receive only selected rows/findings, not complete ACC/readiness reports.
