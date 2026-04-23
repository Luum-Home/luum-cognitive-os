# Skills and Rules Canonicalization Workplan

This workplan exists to make the migration followable across sessions.

It is intentionally strict:

- step-by-step
- additive first
- no direct path migration before contracts are explicit

## Goal

Move skills and rules from a `.claude`-centered model toward a canonical
`.cognitive-os` contract without breaking current harness behavior.

## Migration Rule

Do not start by moving files.

Start by making contracts, invariants, and resolvers explicit.

## Phase 1 — Freeze Current Behavior

Purpose: understand exactly what the current system guarantees and preserve that
behavior while the canonical contract is introduced.

### Invariants

- Claude must keep discovering the skills and rules it discovers today.
- Codex must not regress in bootstrap/runtime portability.
- Installer output for current harness users must remain unchanged.
- Status and health tooling must continue to describe current state honestly.
- Existing project installs must not need manual migration.

### Deliverables

- [x] Portability gap documented
- [x] Canonicalization risk documented
- [x] Historical root-cause analysis documented
- [x] Characterization tests for skill lookup precedence
- [x] Characterization tests for rule directory precedence
- [x] Characterization tests for installer/export targets
- [x] Contract notes added to the main migration checklist

## Phase 2 — Introduce the Canonical Contract

Purpose: define the future contract in code without changing the visible
artifact layout yet.

### Deliverables

- [x] Canonical path helper surface in Python
- [x] Canonical path helper surface in Go installer code
- [x] Runtime readers use the new helpers where safe
- [x] Status/diagnostic tooling can reason about canonical-first paths
- [x] Contract docs explain source-of-truth vs projection clearly

### Required Behavior

- Keep `.claude/...` as the active Claude projection
- Add `.cognitive-os/...` as the canonical contract surface
- Prefer canonical-first lookup only when it does not change override semantics
- Avoid changing install destinations in this phase

## Phase 3 — Dual Read / Dual Write

Purpose: make the system work from canonical state while still projecting to
Claude.

### Deliverables

- [x] Installer writes canonical artifacts plus driver projection
- [x] Runtime can read canonical artifacts even if Claude projection is absent
- [ ] Tests prove canonical artifacts are sufficient as source-of-truth

### Current evidence

- `cos list skills` and `cos list rules` work from canonical artifacts when the
  Claude projection is absent.
- `cos-status --json` can describe a canonical-only project without
  `.claude/skills` or `.claude/rules`.
- `uninstall.sh` works for a canonical-only project and still deregisters the
  installation correctly.
- `cos-update.sh` now invokes `self-install` through the canonical project env
  instead of relying on the Claude-specific project env.
- `cos-release-check.sh` now invokes rate-limiter checks through the canonical
  project env instead of relying on the Claude-specific project env.
- `upgrade.sh` now re-runs `cos-init.sh` through the detected harness instead
  of implicitly assuming the Claude projection.
- `cognitive-os doctor` and `cognitive-os list hooks` now report the active
  settings driver honestly for Codex-first and Claude-first projects.
- `cos-status --json` now reports hook wiring through the active settings
  driver, including Codex-first projects that only ship `.codex/hooks.json`.
- `uninstall.sh` now removes COS hook registrations from the active settings
  driver, including Codex-first projects that wire hooks through
  `.codex/hooks.json`.

## Phase 4 — Tooling and Validation Migration

Purpose: update the wider ecosystem around the new contract.

### Deliverables

- [x] `cos-status` understands canonical-first artifact layout
- [x] health checks understand canonical-first artifact layout
- [x] release checks understand canonical-first artifact layout
- [x] audit and wiring tools stop assuming `.claude/...` is the only source

## Phase 5 — Demote `.claude/` From Center to Driver

Purpose: make `.claude/` a clear projection layer instead of the implicit
center of the system.

### Deliverables

- [ ] Claude remains fully supported through projection
- [ ] Canonical artifact contract is the documented source-of-truth
- [ ] Product messaging no longer depends on Claude-centric artifact language

## Session Rule

At the end of each session:

1. Update this checklist.
2. Update any contract docs that changed.
3. Record what is now safe to do next and what remains dangerous.

Current safe next step: keep expanding canonical-only characterization coverage
around upgrade, release, and uninstall consumers so the canonical artifact
contract is provably sufficient before any path demotion begins.

Still dangerous: changing install destinations or removing `.claude/...`
projection paths before dual-write lands.

## References

- `docs/architecture/skills-rules-portability-gap.md`
- `docs/architecture/skills-rules-canonicalization-risk-analysis.md`
- `docs/architecture/why-skills-and-rules-became-claude-centered.md`
