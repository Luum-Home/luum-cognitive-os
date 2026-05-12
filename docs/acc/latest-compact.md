# Agent Capability Coverage — Compact

> Context diet entrypoint. Read this before opening `docs/acc/latest.json`.

Generated: 2026-05-12T17:37:47Z
Gate: block (reconstruction)
ACC: 0.9833
ACC effective: 0.9899
Capabilities: 2954
Findings: 74
New debt gate: block (14)
Primitive fitness reports: 0

## Warnings

- coverage_debt:74

## Mapping Weights

- aligned: 6077
- missing: 0
- overexposed: 0
- partial: 81
- stale: 0
- unverified: 22

## Consumer Accessibility

- install-profile-managed: 19
- lifecycle-declared-consumer-candidate: 65
- lifecycle-declared-maintainer: 58
- maintainer-only: 59
- profile-driver: 19
- projected-consumer-surface: 1355
- runtime-evidence: 8
- shell-ci-candidate: 15
- skill-referenced-not-projectable: 2
- so-local-only: 1354

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

- `script:scripts/cos-documentation-truth-audit` [unreviewed-local-default]: new capability matched a broad local-surface default instead of an explicit row or projection proof
- `script:scripts/cos-portable-ai-consumer-package-smoke` [unreviewed-local-default]: new capability matched a broad local-surface default instead of an explicit row or projection proof
- `script:scripts/documentation_truth_audit.py` [unreviewed-local-default]: new capability matched a broad local-surface default instead of an explicit row or projection proof
- `script:scripts/portable_ai_consumer_package.py` [unreviewed-local-default]: new capability matched a broad local-surface default instead of an explicit row or projection proof
- `rule:rules/session-close-doc-truth.md` [unreviewed-local-default]: new capability matched a broad local-surface default instead of an explicit row or projection proof
- `template:templates/counsel-outreach/clean-room-permission.md` [unverified]: new mapping debt
- `template:templates/counsel-outreach/license-clarification.md` [unverified]: new mapping debt
- `template:templates/counsel-outreach/review-request.md` [unverified]: new mapping debt

## Context Diet Rule

- Do not open full JSON ledgers unless debugging the pipeline itself.
- Prefer this compact file, `python3 scripts/acc_pipeline.py --brief`, or targeted JSON queries.
- Subagents should receive only selected rows/findings, not complete ACC/readiness reports.
