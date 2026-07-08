---
type: concept-synthesis
source: docs/04-Concepts/architecture/primitive-authority-write-effects.md
provenance: "Scope and projection (where a primitive is visible) are not the same as write authority (what it may mutate); this doc joins existing scope/projection/proposal/guard/smoke-test surfaces into one current authority model."
---

## What it is
Canonical boundary for which Cognitive OS agentic primitives may read/write SO state, consumer-project state, generated artifacts, and review-only proposal surfaces.

## Key mechanics
- Existing authority sources: `manifests/primitive-scope-classification.yaml` (os-only/project/both), `manifests/primitive-consumer-availability.yaml` (explicit overrides), `manifests/primitive-projection-profiles.yaml` (default/full projection classes), `manifests/shell-ci-projection.yaml` (limits projected shell commands to `.cognitive-os/scripts/cos/`, driver symlinks, CI workflow paths), `manifests/protected-config-write-policy.yaml` (blocks agent writes to hooks/rules/skills/settings/MCP config/sensitive manifests), `manifests/primitive-coherence.yaml` (multi-writer ownership), `lib/consumer_improvement_proposals.py` (consumer->SO import, `runtime_effect: none`), `scripts/portable_ai_real_consumer_smoke.py` (`.ai` overlay consumer smoke, projects into temp shadows).
- Six authority classes with may-read / may-write / must-not-write columns: `observe-only` (writes reports/metrics/stdout only), `propose-only` (writes review artifacts to `.cognitive-os/improvements/proposals/` or `docs/03-PoCs/proposals/`, never runtime state), `profile-projection-write` (writes `.cognitive-os/`, harness settings, shell/CI symlinks, generated workflows, install metadata), `project-local-write` (project-local generated artifacts/extensions only), `os-maintainer-write` (SO repository files within task scope), `dangerous-human-approved` (explicitly approved inputs/surfaces only).
- ADR-276 implements the first authority ratchet: `manifests/primitive-authority.yaml` declares authority modes, writable surfaces, derivation rules, explicit high-risk rows, blocking contradictions; `scripts/primitive_authority_audit.py` statically scans scripts for Python/shell write operations, derives authority from scope/projection/readiness manifests, writes `docs/06-Daily/reports/primitive-authority-latest.{json,md}`; also runs a dynamic write-effects audit with filesystem-delta smokes for consumer improvement export/import, Shell/CI projection, and Codex `cos_init` projection. ACC consumes the report as `authority_write_effects`.
- Required rule: any new shared/projected write-capable primitive must name an authority class in `manifests/primitive-authority.yaml` (or be derivable from scope/projection/readiness metadata); `propose-only`/`observe-only`/`profile-projection-write` rows need tests proving writes stay within declared roots before promotion.
- Generated truth block: authority audit status `pass`; scripts audited 720; blockers 0; dynamic smokes 4; dynamic blocks 0.

## Relations & where used
ADR-276; `manifests/primitive-authority.yaml`; `scripts/primitive_authority_audit.py`; test bundle: `tests/unit/test_consumer_improvement_proposals.py`, `tests/unit/test_primitive_scope_governance.py`, `tests/contracts/test_primitive_scope_governance.py`, `tests/security/test_boundary_enforcement_p0.py`, `tests/unit/test_project_shell_ci.py`; full consumer projection proof `tests/behavior/test_consumer_project_projection.py`.

## Status / caveats
Ratchet, not total argument-space proof — computed paths and arbitrary command invocations still need future dynamic expansion. Write authority of readiness-ledger rows themselves is not proved by existing tests.
