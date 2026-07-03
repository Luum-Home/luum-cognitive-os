---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-174b-prevention-followup.md
adr: ADR-174b
status: accepted
reality_level: REAL
provenance: The 2026-05-05 audit-of-audits found 108 skills on disk without `routing_patterns:` frontmatter — a two-part gap where `packages/consequence-system/hooks/auto-skill-generator.sh` produced new SKILL.md files without `routing_patterns:` at all (the generation gap), and the existing `hooks/skill-md-routing-validator.sh` was only advisory and could not block future writes (the enforcement gap).
---

## Decision
Part A: when `auto-skill-generator.sh` fires, it now calls `lib/routing_pattern_deriver.py` to derive 2–3 routing patterns (skill-name match, hyphen-collapsed variant, Spanish action verb, two-word keyword combo — generic words like "create"/"fix"/"test" excluded) and injects `routing_patterns:`, `lifecycle_state: sandbox`, and `distribution: lab` into the generated frontmatter; if the deriver fails, the hook falls back gracefully and still writes the SKILL.md (never blocks). Part B: a propose-only soak evaluator (`lib/validator_soak_evaluator.py`), wired into a weekly `hooks/validator-soak-weekly.sh` SessionStart hook, throttled to one run per 7 days, reads the last 30 days of `.cognitive-os/metrics/skill-md-routing-validator.jsonl`, and — if false-positive rate < 5% and total_entries > 30 — emits a human-reviewable promotion proposal Markdown file. The actual advisory-to-blocking promotion is NOT decided here; it is deferred to ADR-174c pending operator approval.

## Why
ADR-174 had wired the routing validator as advisory-only, which caught the symptom but not the source. The audit traced the 108-skill gap to the auto-generator itself never emitting `routing_patterns:`, meaning every new auto-generated skill kept adding to the backlog. Closing only the enforcement side (blocking) without closing the generation side would have kept producing non-compliant skills faster than validation could flag them.

## Consequences
Positive: new auto-generated skills immediately carry `routing_patterns:`, eliminating the primary source of future coverage decay; the soak evaluator makes advisory-to-blocking promotion data-driven rather than ad hoc; all components are fail-open (deriver failure, hook errors) so no session is ever blocked. Negative/risks: the false-positive heuristic is imperfect — it assumes an unchanged SKILL.md after a warning means false positive, but the skill may have been accepted via explicit operator override; the 30-day/5% thresholds are conventional, not calibrated against COS-specific data (both are CLI-flag adjustable); the deriver's pattern quality may need iteration after the first generation cohort.

## Status & current state
Accepted and implemented. Rollback path: set `VALIDATOR_BLOCKING=0` to revert the validator to advisory mode without code changes. Verification: `python3 -m pytest tests/audit/test_adr_contracts.py -q` plus the listed unit/contract tests for the deriver, auto-skill-generator routing, and validator promotion trigger.

## Key links
ADR-133 (auto-skill-generation — same "declare in artifact, derive at runtime" pattern), ADR-134 (propose-only self-improvement artifacts), ADR-174 (parent — auto-derived primitive routing), ADR-174c (owns the future advisory→blocking promotion decision). Files: `lib/routing_pattern_deriver.py`, `lib/validator_soak_evaluator.py`, `packages/consequence-system/hooks/auto-skill-generator.sh`, `hooks/validator-soak-weekly.sh`.
