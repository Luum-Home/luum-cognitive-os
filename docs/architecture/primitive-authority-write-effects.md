# Primitive Authority and Write-Effects Boundary

> Canonical boundary for deciding which Cognitive OS agentic primitives may read or write SO state, consumer-project state, generated artifacts, and review-only proposal surfaces.

## Why this exists

Scope and projection are not the same as write authority. A primitive can be:

- documented in the SO repository;
- projected into a consumer project;
- available only through Shell/CI;
- review-only/propose-only;
- a maintainer operation that should never run as a consumer-project primitive.

Those facts answer “where is it visible?” They do not fully answer “what may it mutate?” This document joins the existing scope, projection, proposal, guard, and smoke-test surfaces into one current authority model.

## Existing sources of authority

| Source | What it governs | Current role |
|---|---|---|
| `manifests/primitive-scope-classification.yaml` | `os-only`, `project`, and `both` intent markers | Prevents SO-only primitives from being treated as consumer surfaces by default. |
| `manifests/primitive-consumer-availability.yaml` | Explicit consumer availability overrides | Keeps SO-local and maintainer-only rows from becoming consumer-project debt. |
| `manifests/primitive-projection-profiles.yaml` | Default/full projection classes and profile-driver scripts | Separates scripts copied into consumers from SO-local installer/profile drivers. |
| `manifests/shell-ci-projection.yaml` | Shell/CI command projection paths | Limits projected shell commands to canonical `.cognitive-os/scripts/cos/`, driver symlinks under `scripts/`, and generated CI workflow paths. |
| `manifests/protected-config-write-policy.yaml` | Protected control-plane write globs | Blocks agent tool writes to hooks, rules, skills, agent settings, MCP config, and sensitive manifests unless explicitly approved. |
| `manifests/primitive-coherence.yaml` | Cross-primitive ownership and write surfaces | Documents multi-writer constraints for known mutable surfaces. |
| `lib/consumer_improvement_proposals.py` | Consumer-to-SO improvement exchange | Imports consumer evidence as review artifacts with `runtime_effect: none`; it must not mutate live hooks, rules, skills, manifests, Engram, or vault state. |
| `scripts/portable_ai_real_consumer_smoke.py` | `.ai` overlay consumer smoke | Projects into temporary consumer shadows and verifies registered consumer repositories remain unchanged. |

## Authority classes

| Class | May read | May write | Must not write |
|---|---|---|---|
| `observe-only` | SO or consumer evidence declared by the command | Generated reports, metrics, or stdout only | Live hooks, rules, skills, scripts, manifests, consumer source files, credentials. |
| `propose-only` | Sanitized consumer evidence and SO review context | Review artifacts such as `.cognitive-os/improvements/proposals/` or `docs/proposals/` | Runtime state, live primitive files, policy manifests, consumer runtime files, raw vaults, credentials. |
| `profile-projection-write` | SO primitive sources and selected project metadata | Declared projection roots such as `.cognitive-os/`, harness settings files, shell/CI driver symlinks, generated workflows, and install metadata | User-global config, unrelated consumer source, SO source while running inside a consumer project. |
| `project-local-write` | Current project state | Explicit project-local generated artifacts or project-local primitive extensions | The source SO checkout, user-global config, secrets, unrelated sibling projects. |
| `os-maintainer-write` | SO repository state | SO repository files within the task scope | Consumer repositories, user-global config, credentials, unrelated worktrees. |
| `dangerous-human-approved` | Explicitly approved inputs only | Approved destructive or protected surfaces | Anything outside the reviewed command, scope, and rollback plan. |

## Current write-effect evidence

| Surface | Current proof | What is proved | What is not proved |
|---|---|---|---|
| Consumer projection | `tests/behavior/test_consumer_project_projection.py` | Default install/projection succeeds for implemented native and structural harnesses in temporary projects. | Runtime enforcement parity for structural harnesses. |
| Scope-filtered install | `tests/integration/test_install_scope.py` | `SCOPE: os-only` files are excluded from project-scope installs. | Complete script side-effect containment. |
| Settings projection | `tests/integration/test_project_settings_generation.py` | Generated settings use project-local `.cognitive-os` paths and avoid resolving hooks to the SO source checkout. | Every downstream script invoked by those hooks is side-effect audited. |
| Shell/CI projection | `tests/unit/test_project_shell_ci.py` | Command copies, symlinks, workflow, and metadata land in declared project-local paths. | Behavior of every projected command under arbitrary arguments. |
| Consumer improvement import | `tests/unit/test_consumer_improvement_proposals.py` | Invalid mutating bundles are rejected; valid imports write review artifacts only. | All future proposal-like importers unless they use the same contract. |
| Protected config writes | `tests/security/test_boundary_enforcement_p0.py` | Agent `Write`/`Edit`/`MultiEdit` attempts to protected control-plane paths are blocked, generated reports are allowed. | Mutations performed inside arbitrary Bash scripts after approval or outside the hook path. |
| `.ai` real consumer smoke | `tests/contracts/test_primitive_closure_smokes.py` | Registered real consumers are not mutated; overlay projection happens in temporary shadows. | Non-`.ai` projection paths and arbitrary scripts. |
| Readiness ledgers | `tests/contracts/test_primitive_scope_governance.py` | Regenerated ledgers account for current hooks/skills/rules/scripts/templates and valid scope markers. | Write authority of each row. |

## Implemented authority audit

ADR-276 implements the first authority ratchet:

- `manifests/primitive-authority.yaml` declares authority modes, writable surfaces, derivation rules, explicit high-risk rows, and blocking contradictions.
- `scripts/primitive_authority_audit.py` statically scans scripts for obvious Python and shell write operations, derives authority from existing scope/projection/readiness manifests, and writes `docs/reports/primitive-authority-latest.{json,md}`.
- The same auditor runs a dynamic write-effects audit with filesystem-delta smokes for the initial safe-to-run slice: consumer improvement export/import, Shell/CI projection, and Codex `cos_init` projection.
- ACC consumes the report as `authority_write_effects`.

This is a ratchet, not a claim of total argument-space proof. Computed paths and arbitrary command invocations still need future dynamic expansion.

## Required rule for future primitives

Any new shared or projected primitive that can write files must name one authority class above explicitly in `manifests/primitive-authority.yaml` or be derivable from existing scope/projection/readiness metadata. If the primitive is `propose-only`, `observe-only`, or `profile-projection-write`, tests must prove its writes stay within the declared artifact/projection roots before the row is promoted.

## Current validation bundle

Run the boundary documentation and projection slice:

```bash
python3 -m pytest \
  tests/unit/test_consumer_improvement_proposals.py \
  tests/unit/test_primitive_scope_governance.py \
  tests/contracts/test_primitive_scope_governance.py \
  tests/security/test_boundary_enforcement_p0.py \
  tests/unit/test_project_shell_ci.py -q
```

Run the full consumer projection proof:

```bash
python3 -m pytest tests/behavior/test_consumer_project_projection.py -q
```

<!-- GENERATED:documentation-truth:primitive_authority_write_effects:start -->
Generated documentation truth: primitive authority/write-effects.
Authority audit status: pass.
Scripts audited: 536; blockers: 0; dynamic smokes: 4; dynamic blocks: 0.
Contract surfaces: manifests/primitive-authority.yaml; scripts/primitive_authority_audit.py; ACC adapter authority_write_effects.
Sources: docs/reports/primitive-authority-latest.json; docs/adrs/ADR-276-primitive-authority-write-effects.md.
<!-- GENERATED:documentation-truth:primitive_authority_write_effects:end -->
