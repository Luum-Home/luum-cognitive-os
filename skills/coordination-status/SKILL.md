---
name: coordination-status
description: 'Use when you need this Cognitive OS skill: Inspect active multi-session
  edit locks and decide how to respond when a target file is held by another agent.
  Read-only introspection for sub-agents.; do not use when a narrower skill directly
  matches the task.'
invoke: /coordination-status
tag: os-only
model: haiku
audience: os-dev
effort: haiku
summary_line: List who is editing what across concurrent COS sessions.
version: 1.0.0
platforms:
- claude-code
- codex
prerequisites: []
routing_patterns:
- pattern: \bcoordination[- ]?status\b
  confidence: 0.95
- pattern: \bactive\s+(edit\s+)?locks?\b
  confidence: 0.8
- pattern: \bmulti[- ]?session\s+lock\b
  confidence: 0.75
triggers:
- coordination-status
- /coordination-status
- Coordination Status
- List who is editing what across concurrent COS sessions
---
<!-- SCOPE: os-only -->
# Coordination Status

## Purpose

Use this skill BEFORE starting work on any file in a session where another
Claude/Codex window may be active on the same repo. It answers:

- Which files are currently held by another session?
- Who holds the lock, since when, and for what purpose?
- What does the holder allow (concurrent reads? edits below line N?)?
- How should I respond if my work conflicts (park / negotiate / escalate)?

This skill is **read-only** — it inspects the lock registry, never acquires
or releases. Use `scripts/edit-coop.sh acquire/release` for those.

## When to invoke

- Starting a new sub-agent task in a multi-session repo
- Before editing any file you suspect another agent might be touching
- When a previous Edit/Write call exited with `EDIT-LOCK CONFLICT`
- During post-mortem of a "my changes got reverted" incident

## How

```bash
bash scripts/cos-coordination-status.sh
# machine-readable:
bash scripts/cos-coordination-status.sh --json | python3 -m json.tool
```

For file-lock-only detail, keep using:

```bash
bash scripts/edit-coop.sh status | python3 -m json.tool
```

The unified status includes active sessions, task claims, edit locks, stashes, orphan commits, worktrees, pending tasks, and race risks. If a specific linked worktree needs cleanup or porting, switch to `/worktree-triage` and run `scripts/cos-worktree-triage.sh` before deleting it. The file-lock-only command returns JSON like:

```json
{
  "locks": [
    {
      "target": "tests/conftest.py",
      "session": "1777505505-10911",
      "agent": "claude-opus-4-7",
      "intent": "exclusive-edit",
      "since": "2026-04-30T10:15Z",
      "heartbeat": "2026-04-30T10:23Z",
      "purpose": "ADR-098 quarantine mechanism — Pass 2",
      "status": "active"
    }
  ]
}
```

To check a specific file:

```bash
bash scripts/edit-coop.sh check tests/conftest.py
```

Exit codes: 0 = lockable (free or own), 2 = held by another session.

## Decision matrix

| Holder state | Your work | Response |
|---|---|---|
| Free (no lock) | any | acquire and proceed |
| Own (your session) | any | proceed (lock auto-refreshes) |
| Other session, intent=exclusive-edit | edit | **PARK** to `.cognitive-os/runtime/parked-edits/`, do other work |
| Other session, intent=shared-read | read | proceed read-only |
| Other session, intent=append-only | append at end | proceed (separate region) |
| Other session, stale (heartbeat >30min, PID dead) | any | call `acquire` — auto-clears + takes over |
| Heartbeat live, expires_at >30min away | edit | NEGOTIATE via `.cognitive-os/runtime/edit-negotiations/` |
| Critical bugfix priority | edit | ESCALATE: set `COS_BYPASS_EDIT_LOCK=1`, audit-log proceed |

## Park protocol

If you decide to PARK:

```bash
mkdir -p .cognitive-os/runtime/parked-edits/$YOUR_SESSION
cat > .cognitive-os/runtime/parked-edits/$YOUR_SESSION/conftest.py.json <<EOF
{
  "target_file": "tests/conftest.py",
  "intended_change_summary": "Add quarantine pass to pytest_collection_modifyitems",
  "diff": "...",
  "blocked_on": "session=1777505505",
  "since": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
```

Then move to non-conflicting work. A future hook can drain this queue when
the lock releases.

## Negotiate protocol

If you need partial access (e.g., they're editing line 200, you need line 50):

```bash
mkdir -p .cognitive-os/runtime/edit-negotiations/$THEIR_SESSION
cat > .cognitive-os/runtime/edit-negotiations/$THEIR_SESSION/$YOUR_SESSION.yaml <<EOF
from_session: "$YOUR_SESSION"
target_file: tests/conftest.py
need_lines: [45, 60]
duration_estimate_seconds: 120
purpose: "..."
ask: "yield region 45-60 for 2 minutes"
EOF
```

The holder reads `.cognitive-os/runtime/edit-negotiations/$OWN_SESSION/`
on every heartbeat (every 5min by default).

## Limits

- This skill **does not** automatically apply parked edits. That requires a
  separate drain hook (deferred until volume justifies it).
- Negotiations are **advisory** — the holder decides. No enforced mediation.
- `COS_BYPASS_EDIT_LOCK=1` works regardless of skill; this skill cannot
  prevent it (only audit-log it).

## Related

- ADR-098 — Multi-Agent File Coordination (this skill is its introspection layer)
- ADR-089 — Multi-Session Git Coordination (sibling layer for git index)
- `scripts/edit-coop.sh` — the command-line primitive
- `hooks/edit-lock-pre-tool.sh` — PreToolUse[Edit|Write] enforcement
- `templates/edit-conflict-response.md` — boilerplate for sub-agents on conflict
