---
type: quality-synthesis
source: docs/09-Quality/manual-tests/ai-agent-harness-landscape-review.md
provenance: "Manual test verifying the broad AI coding IDE/CLI/hosted-agent landscape manifest stays useful for tracking candidates without ever claiming unsupported runtime compatibility."
---

## What it is
A 5-step manual procedure validating that `manifests/ai-agent-harness-landscape.yaml` (the backlog of candidate harnesses) is kept strictly separate from `manifests/harness-projection.yaml` (the implemented-projection source of truth), and that no stale "full/high compatibility" marketing claims survive in the docs.

## Key mechanics
- Preconditions: run from repo root; network access optional for spot-checking source URLs; no paid IDE/CLI accounts required.
- Step 1: loads the candidate manifest and prints the count plus IDs of every candidate with status in `{candidate, hosted-candidate, provider-candidate}`.
- Step 2: runs `tests/contracts/test_ai_agent_harness_landscape.py` to confirm implemented projection is sourced only from `harness-projection.yaml`, never from the landscape backlog.
- Step 3: manually spot-checks 5 official source URLs, one from each category (CLI candidate, IDE candidate, hosted-agent candidate, provider/tooling candidate, implemented structural harness).
- Step 4: greps `docs/04-Concepts/root/ide-compatibility.md` to assert the absence of stale compatibility language: `FULL COMPATIBILITY`, `HIGH COMPATIBILITY`, `COS Coverage`, `70-90%`, `100%`.
- Step 5: runs the ACC ratchet (`scripts/acc_pipeline.py --refresh --fail-new`).
- Expected result: the landscape manifest may list many candidates, but only the projection manifest declares implementation; every candidate carries a proof level and availability boundary; no doc claims universal runtime support; ACC fail-new still passes.
- Governance note: if an official source URL disappears or changes semantics, the candidate must be downgraded to `research-candidate` or removed — no candidate may be promoted to implemented without tests.

## Relations & where used
Governs `manifests/ai-agent-harness-landscape.yaml` vs. `manifests/harness-projection.yaml`; enforced by `tests/contracts/test_ai_agent_harness_landscape.py`; references `docs/04-Concepts/root/ide-compatibility.md`. Companion to `docs/09-Quality/manual-tests/agents-md-native-structural-projection.md` (structural proof for 6 specific harnesses) and `docs/09-Quality/manual-tests/acc-fail-new-gate.md` (implemented-set gating).

## Status / caveats
Procedural manual-test document, not a dated execution report — defines a repeatable review process and pass criteria rather than recording one run's results.
