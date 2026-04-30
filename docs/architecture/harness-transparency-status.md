# Harness Transparency Status

> Last updated: 2026-04-28. Scope: Claude Code, Codex, and projects that install Cognitive OS.

Cognitive OS is moving toward full cross-harness transparency: developers should
not need to understand Claude Code internals, Codex hook formats, Engram wiring,
or Cognitive OS runtime details just to get memory, safety, and recovery.

The honest state today is:

> Developers get automatic session-memory protection and fallback persistence
> across Claude Code and Codex today. Full transparent cross-harness operation
> still requires canonical hook projection, portable skill execution, and
> harness-neutral sub-agent spawning.

## Capability Matrix

| Capability | Claude Code | Codex | Consumer projects |
| --- | --- | --- | --- |
| Engram daemon auto-up | Available through the F7 launcher path | Available through the F7 launcher path | Installed through `install.sh` / `scripts/cos-init.sh` |
| Session-start protocol | Supported | Supported | Supported when projected through the active harness driver |
| Session summary protection | Supported through Stage A/B reminder + fallback | Supported through Stage A/B reminder + fallback | Installed with the OS hooks |
| Hook canonical-to-native projection with zero drift | Not complete: ADR-064 Surface 2 | Not complete: ADR-064 Surface 2 | Not complete: ADR-064 Surface 2 |
| Skills invocable outside chat-native commands | Not complete: ADR-064 Surface 3 | Not complete: ADR-064 Surface 3 | Not complete: ADR-064 Surface 3 |
| Sub-agent spawning outside Claude Code | Not complete: ADR-064 Surface 4 | Not complete: ADR-064 Surface 4 | Not complete: ADR-064 Surface 4 |

## What Is Already Transparent

### Memory startup and recovery

A fresh session can run the portable memory lifecycle without requiring the
developer to manually launch every hook. The relevant runtime pieces are:

- `hooks/engram-daemon-launcher.sh`
- `hooks/session-init.sh`
- `hooks/session-resume.sh`
- `hooks/user-prompt-capture.sh`
- `hooks/session-learning.sh`
- `hooks/git-context-capture.sh`
- `hooks/session-changelog.sh`
- `hooks/engram-crystallize-on-session-end.sh`
- `scripts/cos-doctor-memory-lifecycle.sh`
- `scripts/cos-doctor-tools.sh`

The executable proof path is:

```bash
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" \
  bash scripts/cos-doctor-memory-lifecycle.sh --harness codex --skip-engram-start
```

Expected result includes:

```text
PASS session-resume detects and recovers pending tasks
PASS session-changelog saves resumable changelog
Result: PASS
```

### Session summary protection

`hooks/session-summary-reminder.sh` protects session close in two stages:

1. Stage A reminds/blocks when the session has not produced an explicit summary.
2. Stage B can write a heuristic Engram fallback so the session does not end
   with zero persisted context.

This is intentionally described as **protection**, not as a claim that shell
hooks can call in-process MCP tools directly.

## Important Boundary: `mem_session_summary`

`mem_session_summary` is an MCP tool that the agent must call. A shell hook can:

- remind the agent to call it;
- block once to prevent accidental context loss;
- write local fallback evidence;
- call external CLIs when available.

A shell hook cannot directly invoke the in-process MCP tool inside Claude Code or
Codex. Therefore, the transparent behavior today is memory protection plus
fallback persistence, not a magic shell-level `mem_session_summary` call.

## What Still Blocks Full Transparency

The remaining work is tracked in
[`.cognitive-os/plans/architecture/adr-064-implementation-plan.md`](../../.cognitive-os/plans/architecture/adr-064-implementation-plan.md).

### Surface 2 — Canonical hook projection

Today, hook projection exists, but the system still needs a canonical source that
projects into every native harness format without manual drift.

Target outcome:

- author hook registration once;
- project it into `.claude/settings.json`, `.codex/hooks.json`, and future
  drivers;
- detect drift with a doctor/check command;
- stop treating any single harness file as the runtime source of truth.

### Surface 3 — Portable skill execution

Today, many skills are naturally chat-native. Full transparency requires a
portable `cos-skill` path so CI, Codex, Claude Code, bare CLI, and future IDEs can
invoke the same skill contract.

Target outcome:

- `cos-skill list`;
- `cos-skill describe <name>`;
- `cos-skill run <name>`;
- canonical event output for skill execution.

### Surface 4 — Harness-neutral sub-agent spawning

Claude Code has native sub-agent affordances. Other harnesses may not. Full
transparency requires a Cognitive OS-owned `cos-agent` path that does not depend
on Claude Code as the hidden execution substrate.

Target outcome:

- `cos-agent spawn --task ...`;
- transcript persistence under `.cognitive-os/agent-transcripts/`;
- canonical event emission;
- no recursive or MCP-replication scope creep.

## Product Wording

Use this wording in product or onboarding material:

> Today Cognitive OS already provides transparent session-memory protection
> across Claude Code and Codex. The remaining path to full transparency is
> canonical hook projection, portable skill execution, and harness-neutral
> sub-agent spawning.

Avoid claiming that all automation is already fully transparent. The correct
promise is:

> Simple memory and recovery by default; deeper cross-harness portability as the
> ADR-064 surfaces ship.

## Recommended Execution Order

1. Finish the no-developer-home absolute-path scanner and enforcement.
2. Ship ADR-064 Surface 2: canonical-to-native hook projection.
3. Ship ADR-064 Surface 3: portable skill execution.
4. Ship ADR-064 Surface 4: harness-neutral sub-agent spawning.

This order keeps the product real: privacy and portability first, then runtime
projection, then execution portability, then agent orchestration.
