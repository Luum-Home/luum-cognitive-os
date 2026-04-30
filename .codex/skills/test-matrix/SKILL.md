---
name: test-matrix
description: Targeted validation matrix for Cognitive OS maintainer changes. Use to pick the smallest trustworthy test set for building this SO without over-running local machines.
version: 1.0.0
audience: cognitive-os-maintainers
tags: [testing, validation, workflow]
---

# Test Matrix

## Trigger

Use when choosing verification scope after a change.

## Scope

This skill is for building and maintaining Cognitive OS itself. Do not present
these commands as default guidance for projects that merely consume the SO.

## Fast Lanes

### Runtime path/config changes

```bash
python3 -m pytest tests/unit/test_paths.py tests/unit/test_config_loader.py tests/unit/test_dispatch.py tests/unit/test_record_completion.py -q
```

### Self-hosting and bootstrap changes

```bash
python3 -m pytest tests/behavior/test_self_install.py tests/integration/test_project_settings_generation.py -q
```

### Installer and package-manager changes

```bash
(cd cmd/cos && go test ./internal/installer/... ./internal/cli/... ./internal/wizard/... -count=1)
```

### Provider/kernel changes

```bash
go test ./internal/provider/... ./internal/validator/... ./pkg/hook/... -count=1
```

### Laptop-friendly broad validation

Use this for normal local confidence after multi-file Cognitive OS changes. It
caps parallel workers and skips integration, e2e, chaos, Docker, and
cost-bearing lanes.

```bash
make test-laptop
```

### Integration lane changes

`./cos-test cluster --lane integration --ci` is not a lightweight laptop lane. It
is explicit, optional, stateful, serial, and SO-maintainer-only. It runs the full
non-Docker integration directory through `pytest-with-summary.sh` with
`--workers 0`, a 900s timeout, Docker forbidden, and cost-bearing tests blocked.

Use it before merge/release or after touching installation, hooks, memory,
harness drivers, provider/runtime behavior, or session lifecycle code. For local
work, prefer lower priority:

```bash
make test-laptop-integration
```

Use `make test-release` only for release preparation; it chains CI default,
non-Docker integration, and Docker/e2e checks.

For one suspected surface, run the specific integration file instead:

```bash
bash scripts/pytest-with-summary.sh --workers 0 --lane integration -- tests/integration/test_name.py
```

Future split target: integration-memory, integration-installer,
integration-hooks, integration-provider, and integration-runtime.

### Infrastructure contract changes

Use this when touching service classification, compose/reference stacks, or
local health semantics.

```bash
python3 -m pytest tests/integration/test_service_health.py tests/integration/test_e2e_flows.py -q -ra
```

Interpretation:

- `test_service_health.py` proves compose/runtime contract and opt-in localhost probes.
- `test_e2e_flows.py` is the isolated `testcontainers` lane for real stack boot.

### Documentation/product-claim changes

Verify links and claims manually against:

- `README.md`
- `docs/README.md`
- `docs/business/`
- `docs/architecture/`

## Rule

Pick the smallest lane that still matches the changed surface. Do not jump to `integration --ci`, `test-ci-default`, or `test-release` as a reflex on a laptop.

If a claim changes, docs-only validation is not enough when code behavior is implied.
