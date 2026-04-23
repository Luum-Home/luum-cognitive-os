---
name: test-matrix
description: Targeted validation matrix for Cognitive OS changes. Use to pick the smallest trustworthy test set for a given edit.
version: 1.0.0
audience: both
tags: [testing, validation, workflow]
---

# Test Matrix

## Trigger

Use when choosing verification scope after a change.

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

### Documentation/product-claim changes

Verify links and claims manually against:

- `README.md`
- `docs/README.md`
- `docs/business/`
- `docs/architecture/`

## Rule

Pick the smallest lane that still matches the changed surface.

If a claim changes, docs-only validation is not enough when code behavior is implied.
