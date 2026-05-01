<!-- SCOPE: os-only -->
# Edit-Conflict Response Template (ADR-098)

When a sub-agent's `Edit` or `Write` is blocked by an active edit lock from
another session, paste this template into the agent's prompt or response so it
follows the standard 4-option protocol instead of guessing.

## Context the agent receives (from the PreToolUse hook)

```
EDIT-LOCK CONFLICT on <path>
  Held by:    session=<id>
  Intent:     <exclusive-edit | shared-read | append-only>
  Since:      <ISO8601>   (heartbeat: <ISO8601>)
  Purpose:    <free-form string from holder>
```

## Decision tree

```
                      ┌─────────────────────────────┐
                      │  Is the lock STALE?         │
                      │  (heartbeat >30min OR PID   │
                      │   dead per scripts/edit-    │
                      │   coop.sh check)            │
                      └──────┬─────────────────┬────┘
                             │ yes             │ no
                             ▼                 ▼
                      ┌─────────────┐   ┌─────────────────┐
                      │ Take over:  │   │ Is your work    │
                      │ acquire     │   │ urgent?         │
                      │ proceeds &  │   └──┬──────────┬───┘
                      │ logs audit  │      │ no       │ yes
                      └─────────────┘      ▼          ▼
                                     ┌──────────┐  ┌──────────────┐
                                     │ PARK     │  │ NEGOTIATE    │
                                     │ option   │  │ (or          │
                                     │ #1       │  │  ESCALATE if │
                                     └──────────┘  │  critical)   │
                                                   └──────────────┘
```

## Option 1 — PARK (default for non-urgent)

Save the planned edit as a JSON sidecar; switch to non-conflicting work.

```bash
SESSION="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}"
mkdir -p .cognitive-os/runtime/parked-edits/$SESSION
SAFE_PATH=$(printf '%s' "<path>" | sed 's|/|--|g')
cat > .cognitive-os/runtime/parked-edits/$SESSION/$SAFE_PATH.json <<EOF
{
  "target_file": "<path>",
  "intended_change_summary": "<one line>",
  "diff_or_pseudo": "<paste your planned diff>",
  "blocked_on_session": "<holder-session-id>",
  "blocked_since": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "agent": "${COS_AGENT_ID:-unknown}"
}
EOF
echo "Parked. Continuing with non-conflicting work."
```

Then continue with files NOT in the conflict.

## Option 2 — READ-ONLY

Use the file's content to inform other work, but edit elsewhere. Often valid
when the conflict is on a config or schema file you only need to consult.

```bash
# Read but do not Edit/Write
cat <path>
# Then make your edit on a DIFFERENT file
```

## Option 3 — NEGOTIATE

Write a request to the holder's negotiations dir. They read on each heartbeat.

```bash
HOLDER_SESSION="<id-from-conflict-message>"
SESSION="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}"
mkdir -p .cognitive-os/runtime/edit-negotiations/$HOLDER_SESSION
cat > .cognitive-os/runtime/edit-negotiations/$HOLDER_SESSION/$SESSION.yaml <<EOF
from_session: "$SESSION"
target_file: "<path>"
need_lines: [<start>, <end>]      # only the lines you need
duration_estimate_seconds: <N>
purpose: "<why your edit is necessary>"
ask: "yield region [start-end] for <N>s, or signal when free"
EOF
```

## Option 4 — ESCALATE (critical bugfix only)

Only when your priority is `critical-bugfix` (security incident, data
corruption fix, broken-main hotfix). Set the bypass and proceed; the audit
trail is automatic.

```bash
export COS_BYPASS_EDIT_LOCK=1
echo "ESCALATION: bypassing edit lock on <path>" \
  >> .cognitive-os/runtime/edit-locks-audit.jsonl
# Now Edit/Write proceeds normally
```

This is logged to `.cognitive-os/runtime/edit-locks-audit.jsonl`. Inappropriate
escalation is grounds for review.

## Anti-patterns

- ❌ **Retry in a tight loop** — the lock is real, not transient
- ❌ **`rm -rf` the lock dir manually** — breaks audit + may abort the holder mid-edit
- ❌ **Copy file out, edit copy, paste back** — defeats the protocol; equivalent to ESCALATE without the audit log
- ❌ **Pick a different file with the same content (skill/hook duplicate) and edit that** — creates divergent state

## Related

- `scripts/edit-coop.sh` — the lock primitive
- `hooks/edit-lock-pre-tool.sh` — PreToolUse enforcement
- `skills/coordination-status/SKILL.md` — introspection
- ADR-098 — full design rationale
- ADR-089 — sibling for git-index coordination
