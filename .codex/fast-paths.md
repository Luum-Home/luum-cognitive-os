# Cognitive OS — Fast Paths

> Fast verification and navigation commands for common work areas.

## Repo Navigation

```bash
rg --files hooks lib cmd/cos internal/provider pkg/hook docs/08-References/business docs/04-Concepts/architecture
rg -n "COGNITIVE_OS_PROJECT_DIR|CODEX_PROJECT_DIR|CLAUDE_PROJECT_DIR" hooks lib scripts cmd/cos
rg -n "settings.json|hooks.json|COGNITIVE_OS_HARNESS" scripts cmd/cos hooks tests docs
```

## Fast Validation

```bash
bash -n hooks/*.sh scripts/*.sh
python3 -m pytest tests/unit/test_paths.py tests/unit/test_config_loader.py tests/unit/test_dispatch.py tests/unit/test_record_completion.py -q
python3 -m pytest tests/behavior/test_self_install.py -q
go test ./internal/provider/... ./internal/validator/... ./pkg/hook/... -count=1
```

## Portability Slice

```bash
python3 -m pytest tests/integration/test_project_settings_generation.py tests/behavior/test_self_install.py -q
(cd cmd/cos && go test ./internal/installer/... ./internal/cli/... ./internal/wizard/... -count=1)
```

## Product/Docs Slice

```bash
rg -n "governable|verifiable|portable|easy to adopt|hard to outgrow" README.md docs
rg -n "squad|organization|control plane|dashboard" README.md docs/08-References/business docs/00-MOCs/entrypoints/README.md
```

## Safe Search Targets By Theme

- bootstrap: `scripts/cos-init.sh`, `install.sh`, `hooks/self-install.sh`
- portability: `lib/paths.py`, `lib/config_loader.py`, `lib/dispatch.py`, `lib/record_completion.py`, `cmd/cos/internal/installer/`
- provider core: `internal/provider/`, `pkg/hook/context.go`
- product wedge: `README.md`, `docs/08-References/business/`, `docs/00-MOCs/entrypoints/README.md`
- runtime contracts: `manifests/kernel-contract.yaml`, `docs/04-Concepts/root/kernel-contract.md`
