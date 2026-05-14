# Dependency Management Surface Review — 2026-05-14

## Purpose

This review records the pre-ADR inventory requested after the dependency-installer coverage post-mortem. The goal is to understand what Cognitive OS already has for dependency management before creating a new ADR or implementing a coverage solution.

## Executive Summary

Cognitive OS already has many dependency-management primitives and scripts, but they cover adjacent concerns rather than one unified contract. The right next step is not another installer. The right next step is a read-only reconciliation audit that compares package manifests, script/tool probes, installer manifests, adoption evidence, and license/security policy before changing installer behavior.

Recommended future primitive:

```bash
scripts/cos-deps-coverage-audit --json
```

It should report explicit buckets such as `missing_from_manifest`, `manifested_but_unused`, `platform_builtin`, `internal_helper_false_positive`, and `optional_lane_needed`.

## Existing Surfaces

### 1. Cross-device dependency install contract

Primary files:

- `manifests/dependencies.yaml`
- `lib/manifest_loader.py`
- `scripts/cos-deps-install.sh`
- `scripts/cos_deps_install.py`
- `scripts/manifest-check.sh`
- `scripts/cos-doctor-tools.sh`
- `docs/02-Decisions/adrs/ADR-168-cross-device-dependency-installation.md`

What exists:

- Manifest-backed host-tool inventory.
- Profile support for `default`, `full`, and `rust-transpiler-lab`.
- Dry-run and apply modes.
- JSON output with buckets for `already_present`, `installable`, `manual`, `auth_bound`, `unsupported_platform`, `installed`, and `failed`.
- Credential-safe metadata such as `auth_bound`, `syncable`, `never_copy`, and `post_install`.

Gaps:

- The installer currently handles tools, not Python dependency groups.
- Tool presence is checked with `shutil.which(tool.name)`, not the manifest `check` command.
- Minimum versions are declared but not enforced.
- Valid profiles are partly hardcoded in `lib/manifest_loader.py` and `scripts/cos_deps_install.py`.
- The manifest is not reconciled against `pyproject.toml`, `requirements*.txt`, `package.json`, `go.mod`, `Cargo.toml`, or script command probes.
- MCP server registration is reported/checkable but not fully installed/configured by the dependency installer.

### 2. Optional Python dependency lanes

Primary files:

- `requirements/dependency-lanes/*.txt`
- `scripts/dependency-lane.sh`
- `docs/02-Decisions/adrs/ADR-145-dependency-lane-split.md`

What exists:

- Explicit opt-in requirement files for heavy optional stacks such as observability, memory, guardrails, crawling, Jupyter, LLM, and semantic routing.
- A small helper to list, show, locate, and install lanes.

Gaps:

- `scripts/dependency-lane.sh install` assumes `uv` is available.
- Lanes are not driven by `manifests/dependencies.yaml` profiles.
- There is no audit proving each advertised lane is represented in the install contract.

### 3. Dependency adoption evidence gate

Primary files:

- `lib/dependency_adoption_gate.py`
- `scripts/cos-dependency-adoption-gate`
- `manifests/dependency-adoption-evidence.yaml`
- `docs/02-Decisions/adrs/ADR-208-imported-pattern-closure-contract.md`

What exists:

- A staged-change gate that blocks new dependency additions unless accompanying adoption evidence is staged.
- Detection of dependency manifest files such as `pyproject.toml`, `package.json`, `requirements*.txt`, and nested package manifests.

Gaps:

- It is staged-diff oriented, not a whole-repository coverage audit.
- It does not verify that existing dependencies are installable through a profile.
- It does not reconcile CLI/tool command probes with `manifests/dependencies.yaml`.

### 4. External Tool Intelligence Plane

Primary files:

- `lib/external_tool_intelligence.py`
- `scripts/cos-tool-inventory`
- `scripts/cos-tool-adoption-audit`
- `scripts/cos-tool-radar-render`
- `scripts/cos-tool-research-check`
- `manifests/external-tools-adoption.yaml`
- `docs/04-Concepts/architecture/external-tool-intelligence-plane.md`
- `docs/04-Concepts/architecture/external-tool-adoption-doctrine.md`

What exists:

- A machine-readable adoption ledger for external tools.
- Adoption verdicts such as ADOPT, INTEGRATE, DEFER, REJECT, REMOVE, and related evidence.
- Dependency inventory helpers for root package manifests.
- Tool adoption audit and radar rendering.

Gaps:

- It governs adoption posture, not installability.
- It does not emit installer profiles.
- Existing dependency parsing is narrower than the full repository surface; dependency lanes and nested project manifests are not the complete focus.

### 5. License, security, and adoption-truth audits

Primary files:

- `lib/cross_stack_license_audit.py`
- `lib/cross_stack_adoption_truth.py`
- `lib/license_guard.py`
- `scripts/cos-cross-stack-license-audit`
- `scripts/cos-cross-stack-adoption-truth`
- `manifests/cross-stack-license-audit.yaml`
- `manifests/cross-stack-adoption-truth.yaml`
- `manifests/external-tool-licenses.yaml`
- `docs/02-Decisions/adrs/ADR-212-cross-stack-license-audit-toolchain.md`
- `docs/02-Decisions/adrs/ADR-217-cross-stack-adoption-truth-audit.md`

What exists:

- License policy enforcement and scanner posture checks.
- Adoption-truth reconciliation across lockfiles, NOTICE, docs, and inventories.
- Guardrails for blocked/caution licenses.

Gaps:

- These audits should inform dependency coverage, but they do not answer whether a required local CLI is installable through `cos-deps-install`.

### 6. Legacy and tactical setup/install scripts

Primary files:

- `scripts/setup.sh`
- `scripts/cos-bootstrap.sh`
- `scripts/ci-setup.sh`
- `scripts/deps-update.sh`
- `scripts/install-*.sh`

What exists:

- Practical installers for tools such as semgrep, mcp-scan, promptfoo, garak, GoReleaser, Syft/Grype, Trivy, Obsidian, and others.
- Bootstrap for optional Docker services.
- Dependency update/audit support for Python packages, Engram, plugins, and Docker images.

Gaps:

- Installation logic is scattered and imperative.
- Some commands are hardcoded in scripts but absent from `manifests/dependencies.yaml`.
- ADR-168 already identifies this as an incremental convergence area: one-off installers should become helpers delegated from the manifest-driven contract, not independent sources of truth.

### 7. Agentic primitives related to dependency management

Observed primitive metadata under `.ai/primitives/` includes:

- `script-dependency-lane`
- `script-deps-update`
- `script-cos-doctor-tools`
- `hook-dependency-license-classifier`
- `host-tool-doctor`
- `self-install`

Implication:

- A new coverage audit should be registered and proven like other agentic primitives rather than introduced as an invisible maintenance script.

## Dependency Truth Sources to Reconcile

A complete solution should compare at least these sources:

1. Package manifests:
   - `pyproject.toml`
   - `requirements.txt`
   - `requirements/dependency-lanes/*.txt`
   - `package.json`
   - `go.mod`
   - `Cargo.toml`
2. Runtime command usage:
   - `command -v`
   - `shutil.which`
   - `subprocess.run`
   - hardcoded `brew install`, `pip install`, `uv pip`, `cargo install`, `go install`, `npm install`, and `npx` calls.
3. Installer contract:
   - `manifests/dependencies.yaml`
4. Adoption and evidence:
   - `manifests/external-tools-adoption.yaml`
   - `manifests/dependency-adoption-evidence.yaml`
5. License and security policy:
   - `manifests/external-tool-licenses.yaml`
   - `manifests/cross-stack-license-audit.yaml`
   - `manifests/cross-stack-adoption-truth.yaml`

## Proposed Pre-ADR Direction

Create a read-only coverage audit before modifying installer behavior.

Candidate interface:

```bash
scripts/cos-deps-coverage-audit --json
scripts/cos-deps-coverage-audit --format human
```

Candidate output buckets:

- `missing_from_manifest`
- `manifested_but_unused`
- `platform_builtin`
- `internal_helper_false_positive`
- `optional_lane_needed`
- `declared_python_dependency`
- `declared_host_tool`
- `blocked_or_removed_by_policy`
- `auth_bound_manual`
- `profile_candidate`

The audit should be conservative. It should not install anything. Its first job is to make drift visible and reviewable.

## Design Recommendation

Use `manifests/dependencies.yaml` as the install contract, but do not overload it as the only evidence source. Instead:

1. Keep `manifests/dependencies.yaml` as the installer/doctor source of truth for host tools and profile membership.
2. Keep `requirements/dependency-lanes/*.txt` as the Python heavy-lane package source of truth until profiles can safely drive lane installation.
3. Keep `manifests/external-tools-adoption.yaml` as the adoption and policy posture ledger.
4. Add `scripts/cos-deps-coverage-audit` as a read-only reconciler across those layers.
5. After audit output is stable, update ADR-168 or create a successor ADR for dependency coverage convergence.
6. Only then migrate `setup.sh` and `install-*.sh` toward manifest-delegated helper roles.

## Acceptance Criteria for the Future ADR Slice

1. A read-only audit can run without installing tools or reading credentials.
2. The audit compares package manifests, command probes, installer manifest entries, adoption manifests, and license policy.
3. False positives for internal shell helpers are classified instead of reported as missing external tools.
4. Optional heavy Python dependencies are reported as lane candidates, not forced into core install.
5. Existing installer behavior remains unchanged until the audit output is reviewed.
