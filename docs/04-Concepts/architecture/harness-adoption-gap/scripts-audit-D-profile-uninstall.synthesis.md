---
type: concept-synthesis
source: docs/04-Concepts/architecture/harness-adoption-gap/scripts-audit-D-profile-uninstall.md
provenance: "Cluster D follow-up to ADR-001: audit apply-efficiency-profile.sh (settings.json generator) and uninstall.sh for correctness/completeness after the skills-sync-path fix landed."
---

## What it is
Audit of the profile generator and uninstaller. Profile generator's hook wiring is correct post-ADR-001 (LOW cosmetic issues only). Uninstaller had a HIGH finding — it never removed `.claude/skills/`, the new ADR-001 driver path — fixed in this session.

## Key mechanics
- `apply-efficiency-profile.sh`: LOW risk, no fix needed for wiring. Dead code at lines 303-311 ("restore from backup on `full`") is unreachable because the `full` branch already exits at line 94 — backup mechanism is write-only, never read. Summary block (lines 289-300) has drifted from actual `build_settings` hook count (lists 7 PreToolUse Agent hooks, code wires 10) — cosmetic, not fixed.
- `uninstall.sh` HIGH finding: 6-stage cleanup never touched `.claude/skills/` (126 symlinks from `self-install.sh` survive uninstall, harness still sees them — the "Cognitive OS has been uninstalled" message becomes false). Fix applied: new stage 6 removes `.claude/skills/` (counts symlinks first, only removes if directory exists, never touches source `skills/`); "Remove install metadata" renumbered to stage 7.
- Profile-coverage matrix for the 9 ADR-001 ghost skills: none are blocked by profile choice (skill exposure via `.claude/skills/` is orthogonal to hook wiring in `.claude/settings.json`) — but `verification-before-completion`, `exhaustive-prompt`, `plan-feature`, `session-backlog` have degraded *automatic* behavior under `lean` because companion hooks aren't wired at that tier (by design).
- Pre-existing bugs surfaced but out of scope: `auto-refine` skill references a non-existent `auto-refine.sh` hook; `resource-governor`'s `resource-check.sh` hook is wired in no profile tier.
- Uninstall completeness checklist: `.claude/skills/` removal now fixed; two secondary gaps NOT fixed — `settings.json` scrub pattern is stale (targets `.cognitive-os/hooks/` but generator now emits `$CLAUDE_PROJECT_DIR/hooks/`, MEDIUM risk); `.githooks`/`core.hooksPath` git config not reverted.

## Relations & where used
Completes the ADR-001 cluster alongside `diagnosis.md`, `scripts-audit-B-init-bootstrap.md`, `scripts-audit-C-updaters.md`, `scripts-audit.md`. References `templates/project-gotchas.md` ("48/93 hooks intentionally not wired").

## Status / caveats
1 HIGH fix applied and verified (`uninstall.sh` stage 6, `.claude/skills/` removal). 2 MEDIUM/LOW secondary gaps logged as follow-up tickets, not fixed (settings.json scrub pattern staleness, dead-code restore-from-backup path, `auto-refine.sh` missing hook).
