---
type: concept-synthesis
source: docs/04-Concepts/architecture/harness-adoption-gap/scripts-audit-C-updaters.md
provenance: "Cluster C follow-up to ADR-001: verify the fix propagates correctly through the two updater scripts (cos-update.sh, auto-update-projects.sh) rather than each reimplementing sync logic with its own bug."
---

## What it is
Audit confirming ADR-001's fix propagates correctly through both updater scripts because neither reimplements sync logic — each delegates to an already-fixed installer. No bugs found; no code changes applied.

## Key mechanics
- `scripts/cos-update.sh` (LOW, self-hosting only) → delegates to `hooks/self-install.sh` (line 357) with `CLAUDE_PROJECT_DIR` forced, no cache/stash — fresh fix lands every run.
- `scripts/auto-update-projects.sh` (LOW, mass updater) → reads `~/.cognitive-os/installations.json`, re-runs `cos-init.sh --<mode>` per matching project (line 206); `cos-init.sh` already carries `SKILL_DESTS=(".cognitive-os/skills/cos" ".claude/skills/cos")` from the ADR-001 fix.
- Three verified propagation paths: (1) self-hosting via `cos-update.sh` → `self-install.sh`; (2) manual external update via `install.sh --force` → `cos-init.sh`; (3) mass auto-update via git `post-merge` hook → `auto-update-projects.sh` → `cos-init.sh`.
- Observation (non-blocking): `auto-update-projects.sh` pre-cleanup (lines 184-187) removes `.cognitive-os/skills/cos` before re-init but NOT `.claude/skills/cos` — stale/deleted skills can persist as orphans in the driver path. Flagged as [S3 SUGGESTION], not fixed (out of cluster scope).
- Security caveats flagged (non-blocking, not HALT triggers): no `git pull --verify-signatures` on the post-merge auto-update path (supply-chain risk); no signature check on `cos-init.sh` before execution; `cos-init.sh` output suppressed to `/dev/null` in the mass updater, hiding per-project failure detail.
- Human-verify items: confirm ADR-001 commit was pushed upstream (not just local) before downstream `git pull`s pick it up; confirm each machine/clone has pulled; confirm VERSION was bumped so `auto-update-projects.sh`'s version-skip check doesn't skip projects needing the fix.

## Relations & where used
Complements `scripts-audit-B-init-bootstrap.md` (which fixed `cos-init.sh`) and `scripts-audit.md` (general pass). References `hooks/self-install.sh` SYNC_DIRS and `rules/supply-chain-defense.md`.

## Status / caveats
Cluster green — no fix required in the updaters themselves. Three S2/S3/S4-tier adversarial-review findings logged as follow-up tickets (orphaned `.claude/skills/cos` cleanup, doc conflation of `cos-update.sh` scope, silent per-project error suppression, no clean-tree pre-flight check) — none blocking ADR-001 propagation.
