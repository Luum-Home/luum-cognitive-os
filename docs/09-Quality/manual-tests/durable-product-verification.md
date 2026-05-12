# Durable Product Verification

> Manual verification checklist for the durable-core, capability-centric product direction.

## Goal

Verify that the repo does not only *describe* a durable AI operating system,
but contains real, inspectable, testable components for:

- kernel boundaries
- capability-centric execution
- explicit compatibility surfaces
- outcome-based measurement

## Manual Checks

### 1. Kernel Contract Is Explicit

Open:

- `manifests/kernel-contract.yaml`
- `docs/04-Concepts/root/kernel-contract.md`

Verify:

- the kernel scope is small and specific
- the product promise is short and product-facing
- the kernel paths point to real code

### 2. Capability-Centric Routing Exists

Open:

- `lib/execution_profile.py`
- `lib/model_router.py`

Verify:

- tasks resolve to execution profiles first
- execution profiles describe required capabilities, not provider brands
- model choice is a second step that satisfies the profile

### 3. Compatibility Layer Is Visible

Open:

- `lib/compatibility_layer.py`

Verify:

- provider adapters are listed explicitly
- gateway adapters are listed explicitly
- tool/schema adaptation surfaces are visible

### 4. Outcome Metrics Are Provider-Agnostic

Open:

- `lib/outcome_metrics.py`

Verify:

- metrics are based on success, latency, and cost outcomes
- metrics do not require a specific provider brand to remain meaningful

### 5. Automated Verification Exists

Run:

```bash
python3 -m pytest \
  tests/contracts/test_kernel_contract.py \
  tests/unit/test_execution_profile.py \
  tests/unit/test_compatibility_layer.py \
  tests/unit/test_outcome_metrics.py \
  tests/unit/test_model_router.py -q
```

Verify:

- all tests pass
- the system fails loudly if the kernel manifest drifts
- the execution-profile layer remains intact

## Expected Outcome

After these checks, a reviewer should be able to point to real files and real
tests demonstrating that Cognitive OS is moving toward:

- a smaller durable kernel
- capability-centric orchestration
- explicit compatibility boundaries
- outcome-based evaluation

If any of those ideas cannot be demonstrated by files and tests, the design is
still aspirational and must be made more concrete.
