# Agent Capability Coverage — Compact

> Context diet entrypoint. Read this before opening `docs/acc/latest.json`.

Generated: 2026-05-04T20:17:19Z
Gate: pass (reconstruction)
ACC: 0.2655
ACC effective: 0.3169
Capabilities: 729
Findings: 153

## Warnings

- coverage_debt:153
- acc_below_threshold:0.2655<0.5
- acc_effective_below_threshold:0.3169<0.4

## Mapping Weights

- aligned: 527
- missing: 0
- overexposed: 0
- partial: 204
- stale: 0
- unverified: 1254

## Consumer Accessibility

- install-profile-managed: 19
- lifecycle-declared-consumer-candidate: 49
- lifecycle-declared-maintainer: 119
- projected-consumer-surface: 62
- repo-skill-not-projectable: 83
- skill-referenced-not-projectable: 2
- so-local-only: 395

## Top Findings

- `script:scripts/apply-efficiency-profile.sh` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/aspirational_audit.py` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/check_mcp_servers.py` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/cos` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/cos-bootstrap.sh` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/cos-config-audit.sh` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/cos-coordination-status.sh` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion
- `script:scripts/cos-core-skills-check.sh` [partial/medium]: Candidate/projectable surface needs consumer projection proof → add harness projection proof before promotion

## Context Diet Rule

- Do not open full JSON ledgers unless debugging the pipeline itself.
- Prefer this compact file, `python3 scripts/acc_pipeline.py --brief`, or targeted JSON queries.
- Subagents should receive only selected rows/findings, not complete ACC/readiness reports.
