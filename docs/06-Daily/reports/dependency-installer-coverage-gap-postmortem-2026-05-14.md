# Post-Mortem — Dependency Installer Coverage Gap — 2026-05-14

## Summary

Cognitive OS announced and used dependencies that were not fully represented in
`manifests/dependencies.yaml`, the manifest consumed by the ADR-168 installer
and doctor flow. The gap became visible while adding the Rust transpiler lab
profile: Depyler could be added cleanly to the manifest, but a broader scan
showed many Python dependencies, host CLIs, service tools, harness tools, and
platform utilities used elsewhere without installer-profile coverage.

## Impact

A maintainer could run the documented installer and still miss tools needed by
hooks, tests, optional lanes, local services, or lab workflows. This weakens the
cross-device bootstrap promise and makes setup drift hard to review.

## Findings

### Python dependencies used but not modeled as installable lanes

High-signal direct dependencies found in `pyproject.toml`, `requirements.txt`,
or `requirements/dependency-lanes/*` but not fully modeled in the installer
manifest included:

- `arize-phoenix`
- `arize-phoenix-otel`
- `browser-use`
- `claude-agent-sdk`
- `deepeval`
- `fastembed`
- `mlflow`
- `mlflow-skinny`
- `numpy`
- `openai`
- `pytest-rerunfailures`
- `ragas`
- `rich`
- `sentence-transformers`
- `testcontainers`

Some are opt-in or heavy, but they should still map to explicit lanes/profiles
when Cognitive OS advertises them.

### CLIs and host tools invoked or checked but not consistently manifested

High-signal categories:

- Toolchains: `go`, `cargo`, `node`, `npm`, `npx`, `pip`, `pytest`.
- Quality/CI: `shellcheck`, `gofmt`, `golangci-lint`, `codespell`, `vale`,
  `lychee`, `yq`, `rg`.
- Security/SBOM: `syft`, `grype`, `trivy`.
- Local services/integration: `redis-cli`, `redis-server`, `valkey-server`,
  `pg_ctl`, `orb`, `tmux`.
- Harness/agent tooling: `claude`, `opencode`, `fastmcp`, `obsidian`, `bwrap`,
  `sandbox-exec`.
- Platform utilities: `bc`, `uuidgen`, `shasum`, `sha256sum`, `md5`, `md5sum`,
  `flock`, `pgrep`, `timeout`, `tput`, `curl`.

False positives also appeared. Examples include shell helpers such as
`safe_jsonl_append`, `cache_hit`, `cache_update`, `cos_stash_lock_acquire`,
`cos_stash_lock_release`, `portable_epoch_now`, and `file_exists_strict`.

## Root Cause

The repository had several partial sources of dependency truth but no read-only
reconciler across them:

- `manifests/dependencies.yaml` for host-tool installer metadata.
- `pyproject.toml` and `requirements/dependency-lanes/*.txt` for Python deps.
- `package.json`, `go.mod`, and `Cargo.toml` for other ecosystems.
- `command -v`, `shutil.which`, and `subprocess.run` probes in scripts/hooks.
- External-tool adoption and license/security manifests.

Without a coverage audit, drift could accumulate silently.

## Corrective Action

ADR-305 implements `scripts/cos-deps-coverage-audit` as a read-only
reconciliation primitive. It reports buckets such as `missing_from_manifest`,
`manifested_but_unused`, `platform_builtin`, `internal_helper_false_positive`,
and `optional_lane_needed` before any installer behavior changes.

## Follow-up

Use audit output to triage additions to `manifests/dependencies.yaml` by profile
instead of bulk-adding every observed tool. Heavy/optional Python stacks should
remain lane-based until their install contract is explicitly reviewed.
