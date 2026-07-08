---
type: quality-synthesis
source: docs/09-Quality/manual-tests/durable-product-verification.md
provenance: "Manual checklist verifying that the durable-core, capability-centric product direction has real inspectable/testable components, not just descriptive documentation."
---

## What it is
A manual verification checklist for Cognitive OS's "durable AI operating system" product thesis: that kernel boundaries, capability-centric execution, explicit compatibility surfaces, and outcome-based measurement are real, inspectable code — not aspirational prose.

## Key mechanics
Five checks, each pointing reviewers at real files:
1. **Kernel contract is explicit** — `manifests/kernel-contract.yaml` + `docs/04-Concepts/root/kernel-contract.md`; verify the kernel scope is small/specific, the product promise is short, and paths point to real code.
2. **Capability-centric routing exists** — `lib/execution_profile.py` + `lib/model_router.py`; verify tasks resolve to execution profiles (required capabilities, not provider brands) first, with model choice as a second step.
3. **Compatibility layer is visible** — `lib/compatibility_layer.py`; verify provider adapters, gateway adapters, and tool/schema adaptation surfaces are explicit.
4. **Outcome metrics are provider-agnostic** — `lib/outcome_metrics.py`; verify metrics are success/latency/cost based, not tied to a specific provider brand.
5. **Automated verification exists** — `python3 -m pytest tests/contracts/test_kernel_contract.py tests/unit/test_execution_profile.py tests/unit/test_compatibility_layer.py tests/unit/test_outcome_metrics.py tests/unit/test_model_router.py -q`; verify all pass and the kernel manifest drift check fails loudly.

## Relations & where used
Directly downstream of `lib/execution_profile.py`, `lib/model_router.py`, `lib/compatibility_layer.py`, `lib/outcome_metrics.py`, and `manifests/kernel-contract.yaml`. Conceptually paired with `five-minute-demo.md`, which runs the same `test_kernel_contract.py` + `test_product_zones.py` + execution-profile/compatibility-layer/outcome-metrics test set as part of its "product-contract lane."

## Status / caveats
Self-aware epistemics: the doc explicitly states "if any of those ideas cannot be demonstrated by files and tests, the design is still aspirational and must be made more concrete" — this is a deliberate reality-check gate, not a pass/fail proof of a specific run. No dated execution log embedded.
