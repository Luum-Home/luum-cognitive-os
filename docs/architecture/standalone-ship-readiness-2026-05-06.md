# Standalone Ship Readiness — 2026-05-06

## Purpose

Record the current standalone-readiness state for the CLI/TUI/daemon/release
workstream, after closing the large gaps identified in the CLI/TUI/Standalone
audit.

This document is an execution snapshot, not a replacement for the ADRs. The
canonical decisions are:

- [ADR-191: COS Binary Release Pipeline](../adrs/ADR-191-cos-binary-release-pipeline.md)
- [ADR-192: Surface 5 Bubble Tea Adoption](../adrs/ADR-192-surface-5-adopt-bubbletea.md)
- [ADR-193: cosd Local Network API](../adrs/ADR-193-cosd-local-network-api.md)

## Readiness Matrix

| Gap | Status | What exists now | Remaining work for absolute green |
|---|---:|---|---|
| Release pipeline binario real | 🟢/🟡 | `.goreleaser.yaml`, GitHub Actions workflow, checksums, GoReleaser install script, snapshot smoke, and non-placeholder in-repo HEAD Homebrew formula. GoReleaser now generates a Homebrew cask for the external tap. | Create the real `luum-home/homebrew-tap` repository, add `HOMEBREW_TAP_GITHUB_TOKEN`, tag `v0.1.0`, and run a real GitHub release. |
| TUI adoption ADR + Bubble Tea real | 🟢 | `ADR-192-surface-5-adopt-bubbletea.md`, ADR-187 proof pack, direct Bubble Tea dependency, and compile-tested package at `cmd/cos/internal/tui`. | Expand the proof model into a full operator TUI if/when richer UX is required. |
| API local/remota para `cosd` | 🟢 | `scripts/cosd serve` exposes HTTP TCP. `scripts/cosd serve-unix` exposes HTTP over a Unix domain socket. Both transports support `/healthz`, `/status`, `/submit-intent`, and `/process-once`; tests cover both. | For truly remote operation, add authentication, TLS/reverse-proxy guidance, or another secure transport. Current scope is local-first. |
| Abstraer repo root / install root | 🟢 | `scripts/cos-root` resolves project/install roots without requiring Git. Product-facing scripts no longer call `git rev-parse --show-toplevel` directly. `tests/contracts/test_script_root_portability.py` prevents regression. | Keep new scripts on `scripts/cos-root` and add explicit exceptions only for Git-specific internals if a future need appears. |

## Evidence

### Release pipeline

Files:

- `.goreleaser.yaml`
- `.github/workflows/cos-binary-release.yml`
- `scripts/install-goreleaser.sh`
- `Formula/cognitive-os.rb`
- `manifests/dependencies.yaml`
- `tests/contracts/test_standalone_distribution_contract.py`
- `tests/contracts/test_script_root_portability.py`

Validated commands:

```bash
bash scripts/install-goreleaser.sh --install --snapshot-smoke
bash scripts/install-goreleaser.sh --check --snapshot-smoke
```

Observed result:

- GoReleaser installed through Homebrew at `/opt/homebrew/bin/goreleaser`.
- `goreleaser check` validated `.goreleaser.yaml`.
- Snapshot release built `darwin_amd64`, `darwin_arm64`, `linux_amd64`, and
  `linux_arm64` archives.
- `checksums.txt` was generated.
- Homebrew cask output was generated under ignored `dist/` artifacts.

### Surface 5 / Bubble Tea

Files:

- `docs/adrs/ADR-192-surface-5-adopt-bubbletea.md`
- `cmd/cos/internal/tui/proof.go`
- `cmd/cos/internal/tui/proof_test.go`
- `cmd/cos/go.mod`

Validated command:

```bash
cd cmd/cos && go test ./...
```

### cosd local network API

Files:

- `docs/adrs/ADR-193-cosd-local-network-api.md`
- `scripts/cosd`
- `scripts/cos_daemon.py`
- `tests/integration/test_cosd_daemon.py`

Validated commands:

```bash
python3 -m py_compile scripts/cos_daemon.py
bash -n scripts/cosd
python3 -m pytest tests/integration/test_cosd_daemon.py -q
```

Transport contract:

```bash
bash scripts/cosd --project-dir /path/to/project serve --host 127.0.0.1 --port 8765
bash scripts/cosd --project-dir /path/to/project serve-unix --socket /tmp/cosd.sock
```

### Root/install portability

Files:

- `scripts/cos-root`
- `scripts/cos`
- `scripts/cos-headless-pipeline`
- `tests/contracts/test_standalone_distribution_contract.py`
- `tests/contracts/test_script_root_portability.py`

Current resolver precedence:

1. `COGNITIVE_OS_PROJECT_DIR`
2. `CODEX_PROJECT_DIR`
3. `CLAUDE_PROJECT_DIR`
4. current directory if it looks like a COS project
5. install root derived from the script location

## Validation Snapshot

Last focused validation performed in this workstream:

```text
bash -n scripts/install-goreleaser.sh scripts/cosd scripts/cos-root scripts/cos-headless-pipeline
python3 -m py_compile scripts/cos_daemon.py scripts/cos_deps_install.py
cd cmd/cos && go test ./...
python3 -m pytest tests/contracts/test_standalone_distribution_contract.py tests/unit/test_manifest_loader.py tests/integration/test_cosd_daemon.py -q
bash scripts/install-goreleaser.sh --check
bash scripts/install-goreleaser.sh --check --snapshot-smoke
```

Observed result:

```text
go test ./cmd/cos/... OK
44 pytest passed
goreleaser check OK
goreleaser snapshot smoke OK
```

## Next Actions

1. Create and wire the external Homebrew tap repository.
2. Add `HOMEBREW_TAP_GITHUB_TOKEN` to release secrets.
3. Cut a real release tag and verify the GitHub Release artifacts.
4. Decide whether Surface 5 needs a full-screen operator TUI now or whether the
   proof model is enough for the current product phase.
5. Add auth/secure-transport design before exposing `cosd` beyond localhost or a
   local Unix socket.
6. Keep the root-portability contract green as scripts are added or promoted.
