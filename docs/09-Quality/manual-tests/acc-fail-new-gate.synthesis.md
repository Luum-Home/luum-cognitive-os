---
type: quality-synthesis
source: docs/09-Quality/manual-tests/acc-fail-new-gate.md
provenance: "Manual test procedure proving the Agent Capability Coverage (ACC) fail-new gate ratchets from baseline without hiding new debt behind broad local-surface defaults or crediting planned harnesses as implemented."
---

## What it is
A 4-test manual procedure verifying the ACC (Agent Capability Coverage) `--fail-new` gate correctly blocks regressions: it must pass on the current baseline, block when the baseline file is missing, reject new "broad local default" debt as a silent escape hatch, and keep planned IDE/provider harnesses out of the implemented set.

## Key mechanics
- Preconditions: run from repo root; `docs/07-Capabilities/acc/latest.json` must exist as baseline; avoid loading the full JSON into agent context — use `--brief` or targeted `jq`/Python queries instead.
- Test 1: `python3 scripts/acc_pipeline.py --project-dir . --brief --fail-new` must exit 0 with `new_debt.status == "pass"` and `new_debt.count == 0`.
- Test 2: pointing `--baseline` at a missing file must exit 1 with `gate.status == "block"` and `gate.blocks` including `missing_fail_new_baseline`.
- Test 3: delegates to the automated unit test `tests/unit/test_acc_pipeline.py::test_fail_new_strictly_blocks_new_broad_local_default`, which proves a new row aligned only by `availability_match:pattern` becomes `unreviewed-local-default` debt under strict fail-new (i.e., broad defaults can't silently pass).
- Test 4: reads `manifests/harness-projection.yaml` and asserts only `claude` and `codex` have `status: implemented`, while `cursor`, `opencode`, `qwen-code` (and others) remain `planned`.
- Acceptance criteria consolidate the four tests: baseline passes with exit 0, missing baseline fails non-zero, unit tests prove new-debt/broad-default blocking, and planned harnesses are visible but never counted as implemented.

## Relations & where used
Exercises `scripts/acc_pipeline.py` and `manifests/harness-projection.yaml`; companion to `docs/09-Quality/manual-tests/agent-capability-coverage-pipeline.md` (the broader ACC pipeline regeneration test) and `docs/09-Quality/manual-tests/ai-agent-harness-landscape-review.md` (harness landscape vs. implemented-projection distinction).

## Status / caveats
Procedural manual-test document, not a dated point-in-time report — describes a repeatable gate check rather than a single run's results. No pass/fail outcome is recorded in the source; it defines the test, not its execution history.
