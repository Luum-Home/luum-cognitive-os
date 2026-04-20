# ADR-032 — Orchestrator-side trap awareness before Agent launch

**Status**: Accepted
**Date**: 2026-04-20
**Related**: ADR-030 (auto-trigger), ADR-031 (aspirational audit), templates/project-gotchas.md

## Context

The COS currently operates in FIRE_AND_FORGET mode (banner: "Valkey ✅, Executor ❌"). In this mode:

1. **No mid-flight injection**: once the orchestrator calls the Agent tool, there is no channel to push new context to the running sub-agent. If the orchestrator later discovers a trap — e.g., "that file is a symlink" or "don't edit settings.json directly" — the agent has already received its full prompt and is executing.

2. **PreToolUse:Agent path works, but too late**: `hooks/agent-prelaunch-*.sh` hooks inject `additionalContext` (including known traps from `templates/project-gotchas.md`) at the point the Agent tool fires. This is **after** the orchestrator has composed the prompt. The hook fires, but the original prompt instruction may already contradict the trap — the agent sees conflicting signals.

3. **Concrete failure observed**: in the 2026-04-20 session the orchestrator's prompt said "register in `.claude/settings.json`" while the trap says "never edit `settings.json` directly — use `scripts/apply-efficiency-profile.sh`". The agent received both and chose the one in the explicit task description, not the trap warning appended later.

4. **Root cause**: the orchestrator composes the Agent prompt without querying the trap database. By the time hooks inject traps, the conflicting instruction is already baked in.

**Scope**: this ADR addresses only the orchestrator-side gap in FIRE_AND_FORGET mode. Bringing up the Executor for bidirectional mid-flight context injection is an alternative considered and rejected below.

## Decision

Add a lightweight CLI helper `scripts/compose-agent-prompt.py` that the orchestrator calls **before** invoking the Agent tool. The script:

1. Reads a draft task description from stdin (or a file).
2. Scans for keyword matches against the traps defined in `templates/project-gotchas.md`.
3. If matches found, prepends a `⚠ PROJECT TRAPS DETECTED:` section listing the matched trap lines verbatim at the top of the prompt.
4. Outputs the augmented prompt to stdout. No match → output unchanged.

The orchestrator rule (`rules/orchestrator-prompt-compose.md`) mandates that when a task description mentions trap-sensitive files or patterns (`settings.json`, `lib/*.py` symlinks, `packages/*`, `efficiency-profile`, `.cognitive-os/`, `cognitive-os.yaml`), the orchestrator MUST pipe the draft prompt through this script before calling Agent.

This approach is:
- **Stateless**: no daemon, no IPC, no infrastructure.
- **Deterministic**: same input always produces same output.
- **Composable**: works with any prompt composition strategy.
- **Zero-risk to add**: adding a warning section to a prompt cannot break a working task; it can only prevent broken ones.

## Consequences

**Positive**:
- Orchestrator's prompt and the hook's `additionalContext` no longer conflict; they say the same thing.
- Trap warnings appear at the TOP of the prompt (highest attention), not appended as a footnote after hundreds of tokens.
- Works today in FIRE_AND_FORGET mode without any infrastructure change.
- Script is trivially testable: `echo "edit settings.json" | python3 scripts/compose-agent-prompt.py`.

**Negative**:
- Requires the orchestrator to consciously route draft prompts through the script. It is a behavioural mandate (`rules/orchestrator-prompt-compose.md`), not an automated gate. Violation is possible if the orchestrator skips the step.
- Trap list is static (read from `templates/project-gotchas.md`). Adding a new trap requires updating that file; the script picks it up automatically on the next run, but there is no real-time sync.
- Adds one CLI invocation to the prompt-composition path. Cost: ~100ms, negligible.

**Neutral**:
- The existing `hooks/agent-prelaunch-*.sh` hook continues to fire and inject `additionalContext`. With this ADR, the hook and the prompt are now consistent rather than conflicting. Neither replaces the other.

## Alternatives considered

### A1 — Bring Executor up for full bidirectional mid-flight injection

The Executor (ClaudeExecutor) provides a pub/sub channel (Valkey) for mid-flight context injection. This would be the architecturally correct solution: the orchestrator discovers a conflict and pushes a correction to the running agent.

**Rejected**: Executor requires Valkey, a running executor daemon, and `ORCHESTRATOR_MODE=executor`. Currently disabled. Getting it to STABLE requires resolving several open issues unrelated to this problem. This ADR addresses the immediate bug with a proportional fix; Executor enablement is a separate workstream.

### A2 — Encode trap checks in hooks/agent-prelaunch-*.sh more aggressively

We could scan the Agent tool's `prompt` argument in the PreToolUse hook and emit a stronger warning. This is already partially done.

**Rejected**: the problem is not warning loudness — it is prompt ordering. The hook's `additionalContext` appends AFTER the orchestrator's prompt. Task description says X; appended context says ¬X. LLM attention is biased toward the start of the prompt. The fix must put the warning BEFORE the task description, which requires orchestrator-side intervention.

### A3 — Rewrite the trap into the prompt automatically, replacing the conflicting instruction

Replace "edit settings.json" with "run apply-efficiency-profile.sh" inline in the prompt.

**Rejected**: requires semantic understanding of intent. The script cannot reliably rewrite arbitrary instructions without hallucinating. Prepending a warning is safe; rewriting an instruction is not.

## Implementation plan

1. `scripts/compose-agent-prompt.py` — CLI implementation (this ADR's primary deliverable).
2. `rules/orchestrator-prompt-compose.md` — mandates usage, lists trigger keywords.
3. Entry in `rules/RULES-COMPACT.md` under "Prompt Engineering".

The script reads traps from `templates/project-gotchas.md` at runtime. No hardcoded trap list in the script — the single source of truth stays in the gotchas file.

## Verification

```bash
# AC1: ADR file exists
test -f docs/adrs/ADR-032-orchestrator-trap-preview.md

# AC2: script exists and is executable
test -x scripts/compose-agent-prompt.py

# AC3: trap match produces warning
echo "edit .claude/settings.json" | python3 scripts/compose-agent-prompt.py | grep -q "apply-efficiency-profile"

# AC4: no match passes through unchanged
output=$(echo "refactor user.go" | python3 scripts/compose-agent-prompt.py)
echo "$output" | grep -qv "TRAPS DETECTED"

# AC5: RULES-COMPACT entry exists
grep -l 'orchestrator-prompt-compose' rules/RULES-COMPACT.md
```

## Rollback

Remove `rules/orchestrator-prompt-compose.md`. The orchestrator stops being mandated to call the script. The script can remain on disk (it is side-effect-free). The `additionalContext` injection from `agent-prelaunch-*.sh` continues providing partial protection as before.
