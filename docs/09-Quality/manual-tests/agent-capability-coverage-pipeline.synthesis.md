---
type: quality-synthesis
source: docs/09-Quality/manual-tests/agent-capability-coverage-pipeline.md
provenance: "Manual test proving the Agent Capability Coverage (ACC) pipeline can regenerate its unified coverage report end-to-end without relying on chat context."
---

## What it is
A 6-step manual procedure that refreshes the ACC pipeline, inspects its compact/JSON/Markdown outputs for structural invariants, confirms adapter reports aren't silently dropped, and runs the automated ACC test suite — followed by two deeper checks on consumer projection and the harness registry.

## Key mechanics
- Step 1: `python3 scripts/acc_pipeline.py --project-dir . --refresh` regenerates the report.
- Step 2-4: inspect `docs/07-Capabilities/acc/latest-compact.md`, `latest.json`, and `latest.md`; JSON invariants checked include `schema_version == "acc.report.v1"`, non-empty `capabilities`, presence of `acc_effective` in summary, the 6 `mapping_statuses` (aligned/partial/missing/stale/overexposed/unverified) being a subset, and a `persistence` key.
- Step 5: every entry in `data['adapters']` must have `status` in `{ok, unverified, failed}` — adapters cannot fail silently.
- Step 6: runs `tests/unit/test_acc_pipeline.py` and `tests/contracts/test_acc_pipeline_contract.py`.
- Expected results: all three report files exist; local history appended to `.cognitive-os/metrics/acc-pipeline-history.jsonl`; Engram status reported honestly as unavailable unless a real bridge exists (no false-positive integration claims).
- Consumer Projection Check: after refresh, `adapters.consumer_projection.status == "ok"`, `projected_primitives > 0`, and all four harness/profile combinations (`claude/default`, `claude/full`, `codex/default`, `codex/full`) have nonzero counts; `stale_weight`, `partial_weight`, `unverified_weight` must all be 0; `consumer_availability` and `shell_ci_projection` adapters must also report `ok`, with `shell_ci` counting exactly 15 commands.
- Harness Registry Check: `manifests/harness-projection.yaml` must declare a required set of 12 harness IDs (claude, codex, cursor, devin, vscode-copilot, opencode, google-antigravity, qwen-code, kimi-code, minimax-maxclaw, deepseek-provider, shell-ci) as a subset; only `claude` and `codex` are asserted `implemented` in the ACC report, `cursor` asserted `planned`.

## Relations & where used
Drives `scripts/acc_pipeline.py`, `manifests/harness-projection.yaml`, and the ACC report files under `docs/07-Capabilities/acc/`. Companion to `docs/09-Quality/manual-tests/acc-fail-new-gate.md` (regression-gate behavior) and `docs/09-Quality/manual-tests/ai-agent-harness-landscape-review.md` (candidate landscape vs. implemented projection).

## Status / caveats
Procedural manual-test document defining a repeatable regeneration check, not a dated execution report — no run outcome is recorded here.
