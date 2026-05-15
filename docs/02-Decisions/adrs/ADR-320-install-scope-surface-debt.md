---
adr: 320
title: Install Scope Surface Debt and Protected Config Boundary
status: accepted
implementation_status: implemented
date: '2026-05-15'
supersedes: []
superseded_by: null
implementation_files:
- install.sh
- scripts/cos_init.py
- scripts/generate-project-settings.sh
- scripts/cos_install_projection_audit.py
- scripts/cos-install-projection-audit
- tests/behavior/test_cos_init_parity_2_2.py
- tests/integration/test_install_projection_audit.py
- tests/integration/test_project_settings_generation.py
- tests/red_team/portability/test_protected-config-write-guard.py
- docs/06-Daily/reports/cos-install-scope-dev-smoke-latest.md
tier: project
authority: install-scope smoke, installer source, protected-config policy, and manual hook probe
classification_basis: project and both install scopes are aliases; all is a maintainer superset; protected-config guard protects control-plane files, not .env secrets
---

# ADR-320 — Install Scope Surface Debt and Protected Config Boundary

## Context

Primitive SCOPE classification has three semantic values:

- `os-only` — primitives for building or operating Cognitive OS itself.
- `project` — primitives intended only for adopter projects.
- `both` — primitives shared by Cognitive OS maintenance and adopter projects.

The installer exposes three names through `COS_INSTALL_SCOPE` and `--scope`:

- `project`
- `both`
- `all`

Manual review and the latest install-scope smoke showed that these names do not
currently map to three distinct installed surfaces. `project` and `both` are
aliases. `all` installs more files, including maintainer-only and `os-only`
primitives, but the smoke does not prove a better developer outcome.

A second confusion surfaced while interpreting safety probes. The
`protected-config-write-guard` blocks agent control-plane configuration paths
such as `.claude/settings.json`, `.codex/**`, rules, hooks, and selected
manifests. The current policy does **not** include `.env`. A `.env` write probe
therefore does not test protected-config behavior; it tests an expectation that
is not encoded in that guard.

## Decision

Cognitive OS will treat the current installer as having **two real installed
surfaces** until a future ADR gives `project` and `both` separate executable
semantics:

1. **Consumer filtered install** — `project` and `both` are equivalent aliases.
   They install `SCOPE: project` and `SCOPE: both` primitives and exclude top-level
   `SCOPE: os-only` primitives.
2. **Maintainer/self-hosting install** — `all` installs the full surface,
   including `SCOPE: os-only`, and is not a default recommendation for adopter
   projects.

The three-value primitive taxonomy remains valid for classification and review.
The debt is specifically in install-scope projection: the installer has three
labels but only two effective surfaces.

`both` remains the default install-scope alias for backward compatibility, but
new documentation and tests must describe it as equivalent to `project`, not as a
separate tier.

Protected-config safety claims must stay scoped to control-plane files. COS must
not claim that `protected-config-write-guard` blocks `.env` writes unless a later
ADR adds `.env`/`.env*` to `manifests/protected-config-write-policy.yaml` and
adds passing tests for that policy.


## Projection Consistency Guardrail

SCOPE filtering is necessary but not sufficient. A generated harness projection is
valid only when every registered hook command points at a hook file that the same
filtered install actually copied into the target project. The invariant is:

> settings hook reference ⊆ installed hook files ∩ SCOPE-allowed hook files

`scripts/cos-install-projection-audit` enforces this invariant by creating
temporary fixture projects across install scope, harness, and install mode, then
reading the generated `.codex/hooks.json` or `.claude/settings.json`. It fails on
source-layout hook paths, registered hooks that are missing from
`.cognitive-os/hooks/cos/`, or hooks whose source `SCOPE` is excluded by the
current install scope.

Default-mode projection must also stay aligned with
`scripts/cos_init.py::DEFAULT_HOOKS`; `all` broadens SCOPE eligibility but does
not mean default installs copy every hook. Full mode may project the larger
maintainer surface because it also installs that larger surface.

## Non-Goals

- Do not remove the semantic `project`/`both` distinction from primitive
  metadata. It remains necessary to decide whether a primitive is adopter-only or
  shared with OS maintenance.
- Do not promote `all` as a better project install merely because it installs
  more primitives.
- Do not silently expand protected-config policy to `.env`; that is a separate
  secret-write policy decision with compatibility risk.

## Consequences

- Product language must say there are currently two installed surfaces, not
  three operational tiers.
- Classifier work can continue using `os-only`, `project`, and `both`, but install
  smoke/reporting must not imply `project` and `both` differ at runtime.
- `all` remains useful for COS self-hosting and maintainer debugging, but it
  should lose any implicit "more is better" framing.
- `.env` write protection must be attributed to a secret/confidentiality control
  only if that control is actually wired and tested for writes.

## Debt Register

1. **Install-scope alias debt**: `project` and `both` are equivalent in
   `scripts/cos_init.py::scope_allows()` and `skill_scope_allows()`.
2. **Naming debt**: `both` is a default alias, not a separate install tier.
3. **Outcome debt**: `all` has not demonstrated better developer results; it has
   demonstrated a larger surface.
4. **Safety-claim debt**: protected-config claims must not include `.env` until
   policy and tests say so.

## Acceptance Criteria

```bash
.venv/bin/python -m pytest tests/behavior/test_cos_init_parity_2_2.py tests/red_team/portability/test_protected-config-write-guard.py -q
python3 scripts/primitive_scope_classifier.py --project-dir . --fail-contradictions
python3 scripts/primitive_parse_inventory.py --project-dir . --output /tmp/primitive_inventory.json
scripts/cos-install-projection-audit --json
.venv/bin/python -m pytest tests/integration/test_install_projection_audit.py -q
```

The tests must prove that:

- `project` and `both` produce the same allow/block decisions for file SCOPE
  markers.
- `project` and `both` produce the same allow/block decisions for skill audience
  metadata.
- `protected-config-write-guard` blocks `.claude/settings.json`.
- `protected-config-write-guard` does not block `.env` under the current policy.
- Generated Codex and Claude hook settings never reference hooks missing from the
  filtered install output.
- Generated hook settings never register `SCOPE: os-only` hooks under consumer
  `project`/`both` installs.

## Future Options

A future ADR may choose one of these paths:

1. **Keep two install surfaces** and deprecate the `both` CLI spelling in favor
   of `project` plus `all`.
2. **Make three surfaces real** by defining project-only, shared, and maintainer
   install outputs with separate tests and user-facing docs.
3. **Add secret write protection** by extending policy to `.env`/`.env*` and
   documenting migration risks for projects that intentionally edit env files via
   agents.
