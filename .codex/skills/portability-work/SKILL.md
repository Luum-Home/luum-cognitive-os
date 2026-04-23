---
name: portability-work
description: Working guide for cross-harness and cross-provider changes in Cognitive OS. Use when touching bootstrap, runtime env resolution, provider normalization, or settings projection.
version: 1.0.0
audience: both
tags: [portability, harness, providers, bootstrap]
---

# Portability Work

## Trigger

Use when changing anything related to:

- `COGNITIVE_OS_PROJECT_DIR`
- `CODEX_PROJECT_DIR`
- `CLAUDE_PROJECT_DIR`
- settings or hook projection
- provider adapters
- harness behavior

## Canonical Runtime Precedence

Project:

`COGNITIVE_OS_PROJECT_DIR -> CODEX_PROJECT_DIR -> CLAUDE_PROJECT_DIR -> cwd`

Session:

`COGNITIVE_OS_SESSION_ID -> CODEX_SESSION_ID -> CLAUDE_SESSION_ID`

## Portability Taxonomy

- `core-agnostic`
- `driver-projected`
- `claude-advantaged`
- `claude-only`

Do not call a surface portable unless it is either:

- implemented through stable internal contracts, or
- explicitly projected via a harness driver and tested that way

## Primary Files

- `lib/paths.py`
- `lib/config_loader.py`
- `lib/dispatch.py`
- `lib/record_completion.py`
- `hooks/session-init.sh`
- `hooks/self-install.sh`
- `scripts/generate-project-settings.sh`
- `scripts/cos-init.sh`
- `cmd/cos/internal/installer/`

## Required Validation

```bash
python3 -m pytest tests/behavior/test_self_install.py tests/integration/test_project_settings_generation.py -q
(cd cmd/cos && go test ./internal/installer/... ./internal/cli/... ./internal/wizard/... -count=1)
```

## Documentation Rule

Any meaningful portability conclusion should update:

- `docs/architecture/bootstrap-portability.md`
- and, if product-significant, `docs/business/master-plan-checklist.md`
