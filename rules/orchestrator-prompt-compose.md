<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Orchestrator Prompt Compose — Trap Preview Before Agent Launch

## Rule (Always Active)

Before calling the Agent tool, the orchestrator MUST pipe the draft task prompt
through `scripts/compose_agent_prompt.py` when the task description mentions any
of the following trap-sensitive targets:

| Keyword / pattern | Why dangerous |
|---|---|
| `settings.json` | Generated file — never edit directly |
| `lib/*.py` | Symlinks to `packages/*/lib/*.py` — verify before touching |
| `packages/` | Symlinks from `lib/` point here — check both sides |
| `efficiency-profile` | Controlled by `scripts/apply-efficiency-profile.sh` |
| `.cognitive-os/` | OS kernel — do not mix with `.claude/` (driver) |
| `cognitive-os.yaml` | Read current value first; don't duplicate sections |
| `hooks/*.sh` (new/register) | Must be added to a profile tier, not settings.json directly |

## How to Use

```bash
# Compose then pass to Agent tool
augmented=$(echo "register new hook in settings.json" | python3 scripts/compose_agent_prompt.py)
# Use $augmented as the Agent prompt
```

The script reads traps from `templates/project-gotchas.md` at runtime.
No match → prompt passes through unchanged. Always exits 0 (advisory, never blocking).

## Why This Matters (ADR-032)

In FIRE_AND_FORGET mode, `PreToolUse:Agent` hooks inject `additionalContext` **after**
the orchestrator's prompt is assembled. If the prompt says "edit settings.json" and the
hook says "don't edit settings.json", the agent sees conflicting signals with the explicit
instruction winning. Running the script BEFORE the Agent call bakes the warning into the
prompt at the top, before any instructions, eliminating the conflict.

## Contextual Trigger

Active whenever the orchestrator is composing an Agent prompt. Self-check:
"Does my task mention settings.json, lib/*.py, packages/, or efficiency-profile?" → pipe it.
