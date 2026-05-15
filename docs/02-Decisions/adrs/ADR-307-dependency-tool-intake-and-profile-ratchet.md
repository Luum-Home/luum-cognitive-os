---
id: ADR-307
title: Dependency Tool Intake and Profile Ratchet
status: accepted
implementation_status: implemented
date: 2026-05-14
extends:
- ADR-145
- ADR-168
- ADR-208
- ADR-305
related:
- docs/02-Decisions/adrs/ADR-305-dependency-coverage-reconciliation-audit.md
- docs/06-Daily/reports/dependency-management-surface-review-2026-05-14.md
tags:
- dependencies
- installation
- audit
- ratchet
- primitive-governance
implementation_files:
- lib/dependency_tool_intake.py
- lib/dependency_profile_ratchet.py
- scripts/cos-deps-triage
- scripts/cos-deps-profile-ratchet
- scripts/dependency-lane.sh
- scripts/cos-doctor-tools.sh
- scripts/cos-dependency-adoption-gate
- tests/unit/test_dependency_tool_intake.py
adr: 307
tier: maintainer
classification_basis: dependency tool intake, profile ratchet, CLIs, lane wiring,
  adoption gate, and tests are implemented; no remaining in-scope work for this ADR
---

# ADR-307 — Dependency Tool Intake and Profile Ratchet

## Status

Accepted and implemented 2026-05-14.

## Context

ADR-305 made dependency drift visible with `scripts/cos-deps-coverage-audit`,
but detection alone does not keep the SO dependency surface current. New tools
need a maintenance loop that separates observation from installation:

```text
observed → classified → approved → manifest/lane/profile → installed/verified
```

The unsafe alternative is:

```text
observed → auto-added → installed
```

That would turn transient command probes, platform utilities, or sourced shell
helpers into installer debt.

## Decision

Add a dependency intake and ratchet layer on top of ADR-305.

Implemented primitives:

1. `scripts/cos-deps-triage`
   - Reads an existing ADR-305 coverage JSON report or runs the audit itself.
   - Emits schema `cos-deps-triage.v1`.
   - Converts findings into safe actions such as:
     - `triage_manifest_profile`
     - `triage_python_group_or_lane`
     - `map_python_lane_to_manifest_profile`
     - `block_or_remove`
     - `keep_platform_builtin`
     - `suppress_false_positive`
     - `review_unused_manifest_entry`
2. `scripts/cos-deps-profile-ratchet`
   - Reads triage output and a baseline of accepted findings.
   - Fails with exit 2 when new actionable dependency findings appear.
   - This is suitable for future CI once the current baseline is reviewed.
3. `scripts/dependency-lane.sh audit <lane>`
   - Shows which dependencies in a lane are still missing from manifest Python
     groups/profiles.
4. `scripts/cos-doctor-tools.sh`
   - Adds a dependency coverage drift summary to the host tooling doctor.
   - It warns, rather than failing, because current drift is known and needs
     triage before enforcement.
5. `scripts/cos-dependency-adoption-gate --coverage-aware`
   - Reuses the triage report as an adoption/intake view.
   - `--strict` can fail on actionable findings when a lane is ready for
     enforcement.

## Primitive Maintenance Rule

Dependency-related SO construction primitives now have distinct roles:

| Primitive | Role |
|---|---|
| `cos-deps-coverage-audit` | read-only detector |
| `cos-deps-triage` | classifier/intake proposal |
| `cos-deps-profile-ratchet` | fail-new enforcement once baselined |
| `cos-deps-install` | installer only, never detector |
| `dependency-lane.sh` | optional Python lane executor + lane audit |
| `cos-doctor-tools.sh` | operator-facing host status and coverage warning |
| `cos-dependency-adoption-gate` | staged adoption evidence gate + coverage-aware view |
| `deps-update.sh` | version/update drift, not install coverage |
| `dependency-license-classifier` | license gate, not installer |

## Consequences

Positive:

- New tools can be added through an explicit intake loop instead of ad hoc setup
  edits.
- The installer remains conservative and does not auto-install observed tokens.
- CI can later ratchet on new dependency drift without breaking on historical
  debt.
- Optional Python lanes remain opt-in while still visible to maintenance tools.

Tradeoffs:

- Maintainers need to review triage output before enforcement.
- The ratchet needs an accepted baseline before it can become blocking in broad
  CI.
- Pattern-based command extraction still requires human judgement for some
  findings.

## Alternatives rejected

- **Leave the behavior as implicit agent instruction only.** Rejected because this ADR records a runtime/authoring contract that needs durable tests or audits rather than conversation-only memory.

## Verification

Targeted validation:

```bash
bash -n scripts/cos-deps-triage scripts/cos-deps-profile-ratchet scripts/dependency-lane.sh scripts/cos-doctor-tools.sh
.venv/bin/python -m pytest \
  tests/unit/test_dependency_tool_intake.py \
  tests/unit/test_dependency_lane_script.py \
  tests/behavior/test_dependency_adoption_gate_cli.py \
  -q
```

Smoke commands:

```bash
scripts/cos-deps-triage --json >/tmp/cos-deps-triage.json
scripts/cos-deps-profile-ratchet --triage-report /tmp/cos-deps-triage.json --baseline /tmp/empty-baseline.yaml --json || true
bash scripts/dependency-lane.sh audit semantic
scripts/cos-dependency-adoption-gate --coverage-aware --json
```
