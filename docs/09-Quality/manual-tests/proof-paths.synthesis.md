---
type: quality-synthesis
source: docs/09-Quality/manual-tests/proof-paths.md
provenance: "Maps every major Cognitive OS product claim to an inspectable artifact, automated test, and manual verification path so claims cannot age into unverifiable aspirations."
---

## What it is
A registry ("Product Proof Paths") mapping each major Cognitive OS product claim to concrete evidence — installer entry points, contract files, code modules, and verification commands — so that claims stay inspectable and runnable rather than aspirational.

## Key mechanics
Six claims, each with evidence + a runnable verification block:
- **Easy To Adopt**: `install.sh`, `scripts/cos-status.sh`, `scripts/demo-first-run-onboarding.sh`; verified via `tests/integration/test_first_run_onboarding.py`, `test_installer.py`, `test_install_manifest_integration.py`.
- **Serious To Trust**: `manifests/kernel-contract.yaml`, `manifests/product-zones.yaml`, `internal/validator/`, `pkg/hook/`, `lib/outcome_metrics.py`, `lib/execution_profile.py`; verified via contract/unit tests for kernel contract, product zones, execution profile, outcome metrics.
- **Portable Across Ecosystem Churn**: `internal/provider/`, `lib/compatibility_layer.py`, `scripts/generate-project-settings.sh`, `scripts/demo-portability-proof.sh`; verified via `go test ./internal/provider/... ./internal/validator/... ./pkg/hook/...` plus Python tests for compatibility layer, project-settings generation, installer, and portability demo.
- **Capability-Centric, Not Model-Centric**: `lib/execution_profile.py`, `lib/dispatch.py`, `lib/gateway_selector.py`, `lib/skill_routing.py`; verified via unit tests for execution profile, model router, dispatch, and skill routing.
- **Consumer SDD Happy Path**: local CLI lane `cos sdd next|approve|apply|review|status`, `scripts/demo-consumer-sdd-lane.sh`; verified via `cmd/cos/internal/cli/sdd_test.go` (`TestE2E_SDD`).
- **Simple Outside, Rigorous Inside**: product messaging, master plan, and product-taxonomy docs plus `manifests/product-zones.yaml`; verified via `tests/contracts/test_product_zones.py` and manual review of `README.md` / `docs/00-MOCs/entrypoints/README.md`.

## Relations & where used
Acts as the canonical index tying README/product-messaging claims to their proof. New product claims are required to be added here before promotion to the README. Cross-references manual tests (`first-run-onboarding.md`, `five-minute-demo.md`, `consumer-sdd-lane.md`) and architecture docs (`bootstrap-portability.md`, `cross-harness-authoring.md`, `capability-centric-runtime-enforcement.md`).

## Status / caveats
Living reference document (not a dated snapshot); accuracy depends on the linked files/tests continuing to exist and pass. No execution evidence is embedded here — each verification block must be run independently to confirm current state.
