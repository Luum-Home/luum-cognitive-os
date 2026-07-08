---
type: quality-synthesis
source: docs/09-Quality/manual-tests/hook-enforced-rule-projection.md
provenance: "Manual test proving rule context diet and hook enforcement close together for self-hosted COS and downstream harness projection (Claude and Codex)."
---

## What it is
A manual test that verifies the high-ROI enforcement hooks (e.g. skill-router bash gate, scope-proportionality, consequence-evaluator) are actually wired into projected harness settings — not just documented — for both Claude Code and Codex, and that the bash-gate blocks unsafe direct dependency upgrades unless explicitly overridden.

## Key mechanics
- Preconditions: run from repo root; requires `jq`, `python3`, `bash`.
- Step 1: regenerate all harness projections via `bash scripts/apply-efficiency-profile.sh maintainer --harness=all`.
- Step 2: confirm 10 named hooks (skill-router-bash-gate.sh, prompt-quality-llm.sh, token-budget-monitor.sh, adaptive-bypass.sh, assumption-tracker.sh, scope-proportionality.sh, scope-creep-detector.sh, consequence-evaluator.sh, auto-skill-generator.sh, release-guard.sh) are present in `.claude/settings.json` via grep loop.
- Step 3: confirm Codex receives the Bash-supported bypass gate (`skill-router-bash-gate.sh` present in `.codex/hooks.json`).
- Step 4: prove the direct dependency-upgrade bypass blocks — feeding a `brew upgrade gentleman-programming/tap/engram` Bash command through `hooks/skill-router-bash-gate.sh` must exit 2.
- Step 5: prove the explicit operator override works — prefixing the same command with `COS_ALLOW_SKILL_BYPASS=1` must exit 0.
- Step 6: run the automated audit contract (`tests/audit/test_hook_enforced_exclusions.py`, `tests/behavior/test_skill_router_bash_gate.py`).
- Expected result requires all four conditions together: no projection drift, every listed hook present in Claude settings, the bash-gate hook present in Codex hooks.json, and the exit-code contract (2 blocked / 0 overridden) holding.

## Relations & where used
Exercises `scripts/apply-efficiency-profile.sh`, `hooks/skill-router-bash-gate.sh`, `.claude/settings.json`, `.codex/hooks.json`, and the audit/behavior test pair. Directly tied to the rate-limiting/rule-enforcement hook family described in `rules/RULES-COMPACT.md` (`[skill-invocation-mandatory]`, hook-enforced rule exclusions).

## Status / caveats
Straightforward, fully automatable manual test (no planned/future scaffolding); no dated snapshot or inconsistency found in the source.
