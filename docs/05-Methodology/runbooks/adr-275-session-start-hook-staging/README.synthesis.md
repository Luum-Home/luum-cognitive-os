---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/adr-275-session-start-hook-staging/README.md
provenance: "Preserves the historical staging artifact for ADR-275's SessionStart hook wiring, now marked deployed, and documents the three per-harness registration patches plus their verification and rollback procedure."
---

## What it is

A runbook (now historical) for wiring the ADR-275 session-start projector (`scripts/cos-session-start-projector`) into all three harness `SessionStart` hook registries. The doc header states the wiring was DEPLOYED on 2026-05-18 and verified across all three harnesses; the runbook body is kept as the staging artifact.

## Key mechanics

- **Verification of current state** is a single grep: `grep cos-session-start-projector .claude/settings.json .codex/hooks.json .cognitive-os/cos-runner-hooks.json`.
- **What the projector does**: writes a human-readable summary to stderr (not stdout, so it doesn't pollute pipelines), exits 0 always, is read-only (never mutates state), and has a 60s cache TTL to prevent thrashing on rapid session restarts.
- **Three separate per-harness patches** (not one unified diff) because each harness has its own hook schema: Claude Code uses `hooks.SessionStart[]` with `command`+`description`; Codex uses a flatter `hooks.session_start` structure; cos-runner uses an ADR-008-aligned entry pattern. JSON-merge, not `git apply`, since schemas differ. The projector script itself is the single source of truth — harness adapters just wire it in.
- **Why staged/gated**: all three target files (`.claude/settings.json`, `.codex/hooks.json`, `.cognitive-os/cos-runner-hooks.json`) are protected by `protected-config-write-guard`; per ADR-117 (reversibility) and ADR-008 (cross-harness portability), hook registrations must be auditable and operator-reviewed, requiring `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` for the applying session.
- **Post-deployment verification**: check `.cognitive-os/runtime/session-start-projection.cache.json` mtime is within 60s of a session restart; force a cache miss with `COS_PROJECTOR_NOCACHE=1`; run the portability probe suite `tests/red_team/portability/test_cos-session-start-projector.py` (expects 7 passed).

## Relations & where used

Points to three sibling instruction files in the same directory for the exact JSON snippets: `claude-settings-entry.md`, `codex-hooks-entry.md`, and a `cos-runner-hooks-entry.md` (referenced but not included in this synthesis batch). Same staging/gating discipline as `adr-273-slice-c-staging/` and `adr-274-validator-extension-staging/`.

## Status / caveats

Explicitly a historical staging artifact superseded by a deployed state — the doc itself instructs readers to re-verify via the grep command rather than trust the narrative below the status line, since the runbook body still describes the pre-deployment staging process. No internal inconsistencies found beyond this intentional "kept for history" framing.
