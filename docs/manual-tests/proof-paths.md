# Product Proof Paths

> Product claims mapped to inspectable artifacts, tests, and manual verification paths.

## Purpose

Cognitive OS should not age as a pile of aspirational subsystems. Every major claim should have a proof path that a maintainer can run, inspect, or improve.

## Claim: Easy To Adopt

Promise: a real team can install the core without reading deep architecture docs.

Evidence:

- installer entry point: `install.sh`
- onboarding status command: `scripts/cos-status.sh`
- executable first-run proof: `scripts/demo-first-run-onboarding.sh`
- fresh-install tests: `tests/integration/test_installer.py`
- first-run budget tests: `tests/integration/test_first_run_onboarding.py`
- install manifest tests: `tests/integration/test_install_manifest_integration.py`
- manual proof: `docs/manual-tests/first-run-onboarding.md`
- manual demo: `docs/manual-tests/five-minute-demo.md`

Verification:

```bash
bash scripts/demo-first-run-onboarding.sh
python3 -m pytest \
  tests/integration/test_first_run_onboarding.py \
  tests/integration/test_installer.py \
  tests/integration/test_install_manifest_integration.py -q
```

## Claim: Serious To Trust

Promise: the system is governed by contracts, not just documentation.

Evidence:

- kernel boundary: `manifests/kernel-contract.yaml`
- product zone boundary: `manifests/product-zones.yaml`
- policy/runtime contracts: `internal/validator/`, `pkg/hook/`
- outcome metrics: `lib/outcome_metrics.py`
- capability profiles: `lib/execution_profile.py`

Verification:

```bash
python3 -m pytest \
  tests/contracts/test_kernel_contract.py \
  tests/contracts/test_product_zones.py \
  tests/unit/test_execution_profile.py \
  tests/unit/test_outcome_metrics.py -q
```

## Claim: Portable Across Ecosystem Churn

Promise: vendors, models, IDEs, and harnesses can change without rewriting the core product philosophy.

Evidence:

- provider adapters: `internal/provider/`
- compatibility inventory: `lib/compatibility_layer.py`
- harness-aware settings projection: `scripts/generate-project-settings.sh`
- executable portability demo: `scripts/demo-portability-proof.sh`
- settings-driver helpers: `scripts/_lib/settings-driver.sh`
- bootstrap portability analysis: `docs/architecture/bootstrap-portability.md`
- cross-harness authoring guide: `docs/architecture/cross-harness-authoring.md`

Verification:

```bash
bash scripts/demo-portability-proof.sh
go test ./internal/provider/... ./internal/validator/... ./pkg/hook/... -count=1
python3 -m pytest \
  tests/unit/test_compatibility_layer.py \
  tests/integration/test_project_settings_generation.py \
  tests/integration/test_installer.py \
  tests/integration/test_portability_demo.py -q
```

## Claim: Capability-Centric, Not Model-Centric

Promise: runtime decisions start from execution intent and required capabilities before choosing a provider or model.

Evidence:

- capability profile contract: `lib/execution_profile.py`
- dispatch integration: `lib/dispatch.py`
- gateway selection: `lib/gateway_selector.py`
- skill routing: `lib/skill_routing.py`
- runtime enforcement doc: `docs/architecture/capability-centric-runtime-enforcement.md`

Verification:

```bash
python3 -m pytest \
  tests/unit/test_execution_profile.py \
  tests/unit/test_model_router.py \
  tests/unit/test_dispatch.py \
  tests/unit/test_skill_routing.py -q
```

## Claim: Simple Outside, Rigorous Inside

Promise: first-contact docs stay focused, while advanced systems remain available as extensions or experiments.

Evidence:

- product messaging: `docs/business/product-messaging.md`
- durable master plan: `docs/business/durable-product-master-plan.md`
- product taxonomy: `docs/product-zones.md`
- machine-readable taxonomy: `manifests/product-zones.yaml`
- master checklist: `docs/business/master-plan-checklist.md`

Verification:

```bash
python3 -m pytest tests/contracts/test_product_zones.py -q
```

Manual review:

- `README.md` should lead with governance, verification, and portability.
- `docs/README.md` should label squads, dashboards, and control-plane material as optional or future architecture.
- New product claims should be added to this file before they are promoted in the README.
