---
type: concept-synthesis
source: docs/04-Concepts/architecture/harness-adoption-gap/scripts-audit.md
provenance: "General install/update script audit for ADR-001: the self-hosting sync (self-install.sh) was already fixed, but does the same skills-invisible-to-harness bug exist in the external-project installer path?"
---

## What it is
General audit of 9 install/update scripts. Finds the ADR-001 bug is contained to self-hosting (already fixed), but the external installer (`cos-init.sh`) and its mass-updater (`auto-update-projects.sh`) still install skills only to the harness-invisible kernel path in client projects — 1 HIGH, 1 MEDIUM finding.

## Key mechanics
- MEDIUM: `scripts/cos-init.sh` installs skills to `.cognitive-os/skills/cos/` only (line 221); never populates `.claude/skills/`; rules correctly go to `.claude/rules/cos/` (inconsistent convention). Client projects have no `self-install.sh` SessionStart hook to bridge the gap (that script is self-hosting-only). Proposed fix: mirror to `.claude/skills/cos/` after the kernel install, branching on `$MODE` (`--full` vs standard `STANDARD_SKILLS` list).
- HIGH: `scripts/auto-update-projects.sh` inherits the `cos-init.sh` bug at mass scale — every registered project re-synced via this script ends up with skills invisible to the harness. No independent fix needed once `cos-init.sh` is fixed (cascades automatically).
- LOW/no-action rows: `install.sh` (delegates entirely to `cos-init.sh`), `install-cos.sh` (CLI binary only), `cos-init-global.sh` (rules-only, correct), `cos-update.sh`/`cos-bootstrap.sh` (call `self-install.sh` directly, cascade correctly), `apply-efficiency-profile.sh` (settings.json only, correct), `uninstall.sh` (removal target doesn't yet exist — needs matching removal once `cos-init.sh` is fixed), `install-pre-commit.sh`/`install-aguara.sh`/`install-garak.sh`/`install-promptfoo.sh`/`install-mcp-scan.sh`/`install-tob-skills.sh` (external binaries/plugins, not harness paths).
- Recommended commit/dependency order: (1) fix `cos-init.sh` first, (2) fix `uninstall.sh` to match (depends on 1), (3) re-run `auto-update-projects.sh` to backfill client projects (cascades automatically, no code change).
- Explicitly not audited: `generate-project-settings.sh`, `merge-settings.sh`, `cos-registry.sh`, `setup-langfuse.sh` (no skill/rule sync surface).

## Relations & where used
Parent/general audit for the ADR-001 cluster; superseded in detail by cluster-specific audits `scripts-audit-B-init-bootstrap.md` (applies the `cos-init.sh` fix), `scripts-audit-C-updaters.md` (verifies updater propagation), `scripts-audit-D-profile-uninstall.md` (applies the `uninstall.sh` fix).

## Status / caveats
This document records findings and a recommended fix, not the fix itself — the actual `cos-init.sh` and `uninstall.sh` changes were applied in the later cluster B/D audits.
