# Agent Capability Coverage — Compact

> Context diet entrypoint. Read this before opening `docs/acc/latest.json`.

Generated: 2026-05-04T20:56:05Z
Gate: pass (reconstruction)
ACC: 0.5326
ACC effective: 0.5439
Capabilities: 732
Findings: 40

## Warnings

- coverage_debt:40

## Mapping Weights

- aligned: 1062
- missing: 0
- overexposed: 0
- partial: 45
- stale: 0
- unverified: 887

## Consumer Accessibility

- lifecycle-declared-maintainer: 74
- maintainer-only: 34
- profile-driver: 19
- projected-consumer-surface: 278
- repo-skill-not-projectable: 38
- shell-ci-candidate: 15
- skill-referenced-not-projectable: 2
- so-local-only: 272

## Top Findings

- `script:scripts/cos_cleanup_preserved_wip.py` [unverified/medium]: Represented locally but not proven projectable → add package/profile projection metadata
- `script:scripts/so_vs_vanilla_benchmark.py` [unverified/medium]: Represented locally but not proven projectable → add package/profile projection metadata
- `skill:skills/__contracts__/SKILL.md` [unverified/medium]: Represented locally but not proven projectable → add package/profile projection metadata
- `skill:skills/__contracts__/canonical-event-emitter/SKILL.md` [unverified/medium]: Represented locally but not proven projectable → add package/profile projection metadata
- `skill:skills/add-hook/SKILL.md` [unverified/medium]: Represented locally but not proven projectable → add package/profile projection metadata
- `skill:skills/add-mcp/SKILL.md` [unverified/medium]: Represented locally but not proven projectable → add package/profile projection metadata
- `skill:skills/add-rule/SKILL.md` [unverified/medium]: Represented locally but not proven projectable → add package/profile projection metadata
- `skill:skills/add-skill/SKILL.md` [unverified/medium]: Represented locally but not proven projectable → add package/profile projection metadata

## Context Diet Rule

- Do not open full JSON ledgers unless debugging the pipeline itself.
- Prefer this compact file, `python3 scripts/acc_pipeline.py --brief`, or targeted JSON queries.
- Subagents should receive only selected rows/findings, not complete ACC/readiness reports.
