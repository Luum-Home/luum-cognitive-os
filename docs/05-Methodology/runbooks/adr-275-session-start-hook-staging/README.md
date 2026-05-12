# ADR-275 — SessionStart hook wiring (staged)

**Status**: STAGED, not yet deployed.

The session-start projector (`scripts/cos-session-start-projector`) is
operational. What's staged here are the per-harness `SessionStart` hook
registrations across the three IDE/runtime entries:

- `.claude/settings.json`
- `.codex/hooks.json`
- `.cognitive-os/cos-runner-hooks.json`

All three are protected by `protected-config-write-guard` (control-plane
paths). The operator applies them after review, same discipline as
ADR-273 Slice C and the ADR-274 validator extension.

## What the patches do

Each patch adds a `SessionStart` hook entry that invokes:

```
python3 "$CLAUDE_PROJECT_DIR/scripts/cos-session-start-projector"
```

The projector writes a human-readable summary to stderr (so it surfaces
in the IDE/console without polluting stdout pipelines) and exits 0. It is
read-only — never mutates state. Cache TTL of 60s prevents thrashing on
rapid session restarts.

## How to deploy

Three per-harness entry instructions are in this directory:

- `claude-settings-entry.md` — append to `.claude/settings.json`
- `codex-hooks-entry.md` — append to `.codex/hooks.json` (or create)
- `cos-runner-hooks-entry.md` — append to `.cognitive-os/cos-runner-hooks.json`

Each contains the exact JSON snippet to insert. Operator must set
`COS_ALLOW_PROTECTED_CONFIG_WRITE=1` for the session that applies the
edits. JSON-merge (not git-apply) — schemas differ slightly per harness
so a unified diff would not apply cleanly.

After deployment, smoke-test by opening a new session in each harness;
expect the projection block on stderr.

## Rollback

Remove the appended entries (or restore the prior version from git).

## Why staged

`protected-config-write-guard` blocks direct agent writes to:
- `.claude/settings.json`
- `.codex/hooks.json`
- `.cognitive-os/cos-runner-hooks.json`

Per ADR-117 reversibility and ADR-008 cross-harness portability, hook
registrations must be auditable and operator-reviewed. The patches here
are the auditable artifact.

## Why three patches instead of one

Each harness has its own JSON schema for hooks:
- Claude Code uses `hooks.SessionStart[]` with `command` + `description`
- Codex uses a flatter structure under `hooks.session_start`
- cos-runner uses an entry pattern aligned with ADR-008 hook registry

Three patches keep diffs small + reviewable. The projector script is
the SINGLE source of truth — the harness adapters just wire it in.

## Verification after deployment

```bash
# Force a session restart in any harness, then:
ls -la .cognitive-os/runtime/session-start-projection.cache.json
# expect: file present, mtime within last 60s

# Test cache miss:
COS_PROJECTOR_NOCACHE=1 python3 scripts/cos-session-start-projector | head -5
# expect: same projection regardless of cache

# Test portability probes (no operator deploy needed):
python3 -m pytest tests/red_team/portability/test_cos-session-start-projector.py -q
# expect: 7 passed
```
