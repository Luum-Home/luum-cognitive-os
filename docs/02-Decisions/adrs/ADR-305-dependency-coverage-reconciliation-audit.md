---
id: ADR-305
title: Dependency Coverage Reconciliation Audit
status: accepted
implementation_status: implemented
date: 2026-05-14
extends:
- ADR-145
- ADR-168
- ADR-208
- ADR-212
- ADR-217
- ADR-254
related:
- docs/06-Daily/reports/dependency-management-surface-review-2026-05-14.md
- docs/06-Daily/reports/dependency-installer-coverage-gap-postmortem-2026-05-14.md
tags:
- dependencies
- installation
- audit
- manifests
- tooling
implementation_files:
- lib/dependency_coverage_audit.py
- scripts/cos-deps-coverage-audit
- tests/unit/test_dependency_coverage_audit.py
adr: 305
tier: maintainer
classification_basis: dependency coverage audit library, CLI, and unit tests are implemented;
  no remaining in-scope work for this ADR
---

# ADR-305 — Dependency Coverage Reconciliation Audit

## Status

Accepted and implemented 2026-05-14.

## Context

The dependency installer coverage post-mortem and the follow-up surface review
showed that Cognitive OS already has multiple dependency-management surfaces:

- ADR-168 manifest-driven host-tool installation via `manifests/dependencies.yaml`,
  `scripts/cos-deps-install.sh`, `scripts/manifest-check.sh`, and
  `scripts/cos-doctor-tools.sh`.
- ADR-145 optional Python dependency lanes under `requirements/dependency-lanes/`.
- ADR-208 dependency-adoption evidence gates for staged dependency changes.
- ADR-254 external-tool adoption manifests and research checks.
- ADR-212 and ADR-217 license/security/adoption-truth audits.
- Legacy/tactical setup scripts such as `scripts/setup.sh`,
  `scripts/deps-update.sh`, `scripts/cos-bootstrap.sh`, and `scripts/install-*.sh`.

Those surfaces are useful, but they do not answer one operational question:

> Which dependencies and host tools are actually used or declared by the
> repository but missing from the installer contract?

Adding more install commands directly to `scripts/setup.sh` or
`manifests/dependencies.yaml` would hide the drift instead of making it
reviewable. The first corrective step must be a read-only reconciliation audit.

## Decision

Introduce `scripts/cos-deps-coverage-audit` as a read-only dependency coverage
reconciler.

The audit compares:

1. Package manifests:
   - `pyproject.toml`
   - `requirements.txt`
   - `requirements/dependency-lanes/*.txt`
   - `package.json`
   - `go.mod`
   - `Cargo.toml`
2. Runtime/tool probes in tracked scripts and Python files:
   - `command -v`
   - `shutil.which(...)`
   - `subprocess.run([...])`
   - hardcoded install calls such as `brew install`, `cargo install`,
     `go install`, `npm install -g`, and `pip install`.
3. The ADR-168 dependency manifest:
   - `manifests/dependencies.yaml`
4. External-tool adoption policy:
   - `manifests/external-tools-adoption.yaml`

The audit emits JSON schema `cos-deps-coverage-audit.v1` and human output. It
never installs tools, never reads credentials, and defaults to tracked files
when the target root is a Git repository so local caches, snapshots, and
untracked generated red-team files do not pollute the baseline.

## Output Buckets

The audit reports these buckets:

- `missing_from_manifest` — package dependencies or host tools observed in repo
  surfaces but absent from `manifests/dependencies.yaml`.
- `manifested_but_unused` — tools declared in `manifests/dependencies.yaml` but
  not observed in command probes.
- `platform_builtin` — shell/POSIX-style utilities that should not become COS
  install-profile debt by default.
- `internal_helper_false_positive` — sourced COS shell helpers that look like
  commands in defensive probes.
- `optional_lane_needed` — Python dependencies found in dependency-lane files but
  not yet represented in manifest Python groups.
- `declared_python_dependency` — Python dependency observations.
- `declared_host_tool` — host-tool observations.
- `blocked_or_removed_by_policy` — package observations whose external-tool
  adoption policy is REMOVE/REJECT or cleanup-required.
- `profile_candidate` — observed missing items suitable for later profile
  triage.

## Consequences

Positive:

- Dependency drift becomes visible before installer behavior changes.
- ADR-168 remains the install contract instead of becoming a blind dumping
  ground for every observed command.
- Python lanes, host tools, adoption policy, and license/adoption audits remain
  separate but reconcilable.
- False positives such as `safe_jsonl_append` and `cos_stash_lock_acquire` are
  explicitly classified.

Tradeoffs:

- The first implementation is conservative and pattern-based. Some command
  extraction results still require human triage.
- `manifested_but_unused` is advisory because tools can be consumed by humans,
  docs, or external harnesses without appearing in local command probes.
- The audit does not yet update `manifests/dependencies.yaml` automatically.

## Implementation

Implemented files:

- `lib/dependency_coverage_audit.py` — parser/reconciler and JSON/human report
  formatter.
- `scripts/cos-deps-coverage-audit` — shell entrypoint.
- `tests/unit/test_dependency_coverage_audit.py` — unit and CLI contract tests.

The implementation intentionally reuses existing COS helpers where practical:

- `lib.manifest_loader.load_manifest` for ADR-168 dependency manifest parsing.
- `lib.external_tool_intelligence` package parsers and normalization helpers.
- `manifests/external-tools-adoption.yaml` for REMOVE/REJECT policy signals.

## Alternatives rejected

- **Leave the behavior as implicit agent instruction only.** Rejected because this ADR records a runtime/authoring contract that needs durable tests or audits rather than conversation-only memory.

## Verification

Targeted tests:

```bash
.venv/bin/python -m pytest tests/unit/test_dependency_coverage_audit.py -q
```

Repository smoke:

```bash
scripts/cos-deps-coverage-audit --json > /tmp/deps-coverage.json
python3 - <<'PY'
import json
payload = json.load(open('/tmp/deps-coverage.json'))
assert payload['schema_version'] == 'cos-deps-coverage-audit.v1'
assert 'missing_from_manifest' in payload['summary']
PY
```

Test-efficiency plan for this slice:

```bash
scripts/cos-test-efficiency-plan --from-git --commands --include-final-laptop
```

The emitted broad derived-artifact gate was run and failed on pre-existing
hook-quality / harness-projection drift unrelated to this dependency audit
slice. The failure did not identify files introduced by ADR-305. The broad final
`make test-laptop` lane was not run as part of this focused implementation
slice.


## Follow-up

ADR-307 adds the maintenance loop above this detector: `scripts/cos-deps-triage`, `scripts/cos-deps-profile-ratchet`, lane audit integration, doctor warnings, and coverage-aware adoption-gate mode.
