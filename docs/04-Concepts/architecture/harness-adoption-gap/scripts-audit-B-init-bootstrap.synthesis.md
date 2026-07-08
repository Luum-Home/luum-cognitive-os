---
type: concept-synthesis
source: docs/04-Concepts/architecture/harness-adoption-gap/scripts-audit-B-init-bootstrap.md
provenance: "Cluster B follow-up to ADR-001: verify whether the skills-sync-path bug also affects init/bootstrap scripts (cos-init.sh, cos-init-global.sh, cos-bootstrap.sh) beyond self-install.sh."
---

## What it is
Audit of 3 init/bootstrap scripts for the ADR-001 bug class (skills installed to `.cognitive-os/skills/` but never to harness-readable `.claude/skills/`). Bug found and fixed in exactly 1 of 3: `cos-init.sh`.

## Key mechanics
- `cos-init.sh` (MEDIUM, FIX APPLIED): was installing skills to `.cognitive-os/skills/cos/` only; fix adds `SKILL_DESTS=(".cognitive-os/skills/cos" ".claude/skills/cos")` array loop around lines 218-252, +31/-25 net +6 lines; `skills_installed` counter increments only on the driver-path pass. Verified via `bash -n` (SYNTAX_OK) and `grep -c 'SKILL_DESTS'` → 2.
- `cos-init-global.sh` (LOW, no bug): rules-only scope, writes to `~/.claude/rules/cos/` — correct user-level path, does not touch skills/hooks.
- `cos-bootstrap.sh` (LOW, no bug): delegates skill sync to `hooks/self-install.sh` at Step 7 (already fixed under ADR-001), so the fix cascades automatically.
- Fixing `cos-init.sh` transitively resolves cluster A's prior HIGH finding for `auto-update-projects.sh` (which calls `cos-init.sh`) — no change needed there.
- Blast radius of the pre-fix bug: every project installed via `install.sh` or re-installed by `auto-update-projects.sh` had zero COS skills visible to the harness.

## Relations & where used
Part of the ADR-001 cluster with `diagnosis.md`, `scripts-audit.md`, `scripts-audit-C-updaters.md`, `scripts-audit-D-profile-uninstall.md`.

## Status / caveats
Unsure/flagged: `cp -r` is not strictly idempotent (would create nested `name/name` dir if destination already exists as a directory) — pre-existing behavior, not improved, flagged for follow-up (cluster D or separate idempotency pass). Not run end-to-end against a throwaway project (syntax/grep checks only — ceiling of this audit). Open structural concern: `cos-init.sh` uses `cos/`-namespaced subdir under `.claude/skills/` while `self-install.sh` creates flat symlinks — whether the harness recurses into `cos/` subdirs was not confirmed; flagged as an ADR-002 candidate. Human should verify by running `cos-init.sh --standard` in a throwaway dir and inspecting a fresh session's skill list.
