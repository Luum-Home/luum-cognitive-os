# Memory Lifecycle

> How Cognitive OS saves, protects, retrieves, and verifies cross-session
> memory for Codex, Claude Code, and future harness drivers.

## Product Contract

Cognitive OS must not rely on one chat window or one vendor harness as the
place where project memory lives.

For developers, memory should be transparent by default: installing the OS
should make session continuity, prompt capture, task recovery, and shutdown
evidence happen through harness hooks and local artifacts without requiring
developers to understand Engram internals.

The durable memory contract is:

1. capture important user intent while the session is active;
2. protect content before it is written to persistent memory;
3. flush structured context before compaction;
4. record session outcomes at shutdown;
5. recover pending work and prior context at the next session start;
6. verify the whole loop with an executable doctor, not only documentation.

## What "Automatic" Means

The memory lifecycle has two automation layers:

1. **Hook automation** — shell hooks run automatically at harness lifecycle
   events and write local evidence under `.cognitive-os/`.
2. **Agent-tool automation** — when Engram MCP tools are available in the
   current agent host, the agent is expected to call `mem_session_summary`,
   `mem_save`, or related MCP tools at the correct lifecycle points.

Shell hooks cannot directly call the in-process MCP tool named
`mem_session_summary` on behalf of Codex or Claude Code. They can run CLI
commands, write local artifacts, launch daemons, and emit instructions. That is
why the OS keeps local evidence even if a model fails to call the MCP tool, and
why `hooks/pre-compaction-flush.sh` explicitly instructs the agent to call
`mem_session_summary` and `mem_save`.

The intended developer experience is:

- developers do not manually run memory hooks during normal work;
- new sessions automatically get session initialization, host diagnostics,
  Engram startup, and pending-task recovery;
- normal prompts and session shutdown automatically leave local evidence;
- compaction and session closure still require the agent to obey the durable
  memory protocol when MCP tools are available;
- the doctor command proves whether the host can support that lifecycle.

## Quick Verification

Run the full host doctor:

```bash
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" bash scripts/cos-doctor-tools.sh
```

Expected evidence includes:

```text
PASS memory lifecycle doctor passed
```

Run only the memory lifecycle proof:

```bash
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" bash scripts/cos-doctor-memory-lifecycle.sh --harness codex
```

That doctor creates an isolated scratch project and proves:

- Engram launcher can run for a new Codex session;
- pending tasks can be detected and recovered;
- actionable prompts can be captured;
- session-learning metrics are written;
- git context is captured;
- a resumable changelog is generated;
- session-end crystallization writes an event;
- the pre-compaction hook emits mandatory `mem_session_summary` / `mem_save`
  reminders.

## Save Surfaces

| Purpose | Component | Output / Effect |
|---|---|---|
| Capture actionable user prompts | `hooks/user-prompt-capture.sh` | `.cognitive-os/metrics/prompt-captures.jsonl` and downstream user-message processing |
| Flush before compaction | `hooks/pre-compaction-flush.sh` | anchored summary attempt plus explicit `mem_session_summary` / `mem_save` reminder |
| Capture session outcomes | `hooks/session-learning.sh` | `.cognitive-os/metrics/session-learnings.jsonl` |
| Capture git context | `hooks/git-context-capture.sh` | `.cognitive-os/sessions/{session_id}/git-context.json` and session audit metrics |
| Generate resumable changelog | `hooks/session-changelog.sh` | `.cognitive-os/changelogs/{session_id}.md` |
| Crystallize repeated topics | `hooks/engram-crystallize-on-session-end.sh` | `.cognitive-os/metrics/crystallization-events.jsonl` and Engram digest observations when candidates exist |

## Recovery Surfaces

| Purpose | Component | Output / Effect |
|---|---|---|
| Start Engram daemon when available | `hooks/engram-daemon-launcher.sh` | best-effort Engram HTTP daemon startup and runtime log |
| Bootstrap project profile draft | `hooks/session-init.sh` + `hooks/_lib/session_init_helper.py` + `lib/project_profile_bootstrap.py` | during the first three sessions, writes `.cognitive-os/project-profile/draft.json` and `draft.md` with source-linked, sanitized signals |
| Resume incomplete tasks | `hooks/session-resume.sh` | marks verified tasks complete or tells the agent what needs relaunch |
| Retrieve memory programmatically | `lib/memory_retriever.py` | hybrid ranked retrieval over Engram memory |
| Talk to Engram from Python | `lib/engram_client.py` | machine-readable Engram CLI wrapper |

## Protection Surfaces

| Purpose | Component | Contract |
|---|---|---|
| Scan before user-facing saves | `lib/safe_engram.py` | blocks suspicious content before invoking Engram writes |
| Detect memory threats | `lib/memory_scanner.py` | classifies prompt-injection, credential, and unsafe-memory patterns |
| Build compact durable summaries | `lib/anchored_summarizer.py` | extracts decisions, files, task state, and next steps before compaction |

## Harness Behavior

Memory hooks use canonical project/session env precedence:

```text
Project: COGNITIVE_OS_PROJECT_DIR -> CODEX_PROJECT_DIR -> CLAUDE_PROJECT_DIR -> cwd
Session: COGNITIVE_OS_SESSION_ID -> CODEX_SESSION_ID -> CLAUDE_SESSION_ID
```

Codex currently projects the portable lifecycle on supported events:

- `SessionStart`
- `UserPromptSubmit`
- `Stop`

On a new Codex session, the projected SessionStart chain runs:

- `hooks/self-install.sh`
- `hooks/session-init.sh`
- `hooks/host-tool-doctor.sh`
- `hooks/engram-daemon-launcher.sh`
- `hooks/session-resume.sh`

During the session, Codex projects `hooks/user-prompt-capture.sh` on
`UserPromptSubmit`. At shutdown, Codex projects `hooks/session-learning.sh`,
`hooks/git-context-capture.sh`, `hooks/session-changelog.sh`, and
`hooks/engram-crystallize-on-session-end.sh` on `Stop`.

Claude Code currently has richer event coverage:

- `PreCompact` for `pre-compaction-flush.sh`
- `PostToolUse` for `engram-reinforce-on-access.sh`

On a new Claude Code session, the same SessionStart memory chain runs through
`.claude/settings.json`. Claude additionally gets the compaction reminder and
Engram-access reinforcement hooks because those event surfaces exist in its
driver projection today.

That is an explicit driver capability difference, not hidden Claude lock-in.
Codex should only receive equivalent projections when equivalent event semantics
are proven.

## Project Profile Bootstrap

Memory bootstrap starts locally before it becomes durable memory. During the
first three valid sessions, `session-init.sh` calls the consolidated
`session_init_helper.py`, which invokes `lib/project_profile_bootstrap.py`. The
module writes:

- `.cognitive-os/project-profile/draft.json`
- `.cognitive-os/project-profile/draft.md`

The draft is advisory and editable. It uses small deterministic signals only:
stack markers such as `go.mod`, `pyproject.toml`, `package.json`, Docker files,
session metadata count, and prompt-capture categories. It does not scan the full
repo, does not call Engram/MCP from a shell hook, and does not promote entries
automatically. Promotion is explicit and writes a local active profile to
`.cognitive-os/project-profile/profile.json`; it does not write to Engram or
mutate agent behavior. Every entry has a source object and the writer sanitizes
developer-specific home paths before persisting.

Manual commands:

```bash
python3 scripts/cos_profile_bootstrap.py generate
python3 scripts/cos_profile_bootstrap.py inspect
python3 scripts/cos_profile_bootstrap.py promote --approved-by <reviewer>
python3 scripts/cos_profile_bootstrap.py wipe
```


## Tests That Enforce This

| Test | What it proves |
|---|---|
| `tests/contracts/test_memory_lifecycle_portability.py` | Codex and Claude projections contain the expected memory lifecycle hooks and Codex env works without `CLAUDE_PROJECT_DIR` |
| `tests/behavior/test_cos_doctor_tools.py` | host doctor and memory lifecycle doctor execute real checks |
| `tests/behavior/test_engram_reinforce_hook.py` | reinforcement metrics can write under Codex project env |
| `tests/contracts/test_session_start_tooling_contract.py` | SessionStart host doctor includes memory lifecycle proof and does not run pytest |
| `tests/unit/test_project_profile_bootstrap.py` | project profile drafts are source-linked, conflict-aware, sanitized, and fail-open on corrupt session metadata |
| `tests/behavior/test_profile_bootstrap_cli.py` | manual generate/inspect/promote/wipe profile bootstrap commands work without leaking absolute project paths |

## Related Documents

- [Bootstrap Portability](bootstrap-portability.md)
- [Harness Driver Parity](harness-driver-parity.md)
- [Codex Host Tooling Verification](../manual-tests/codex-host-tooling-verification.md)
- [Testing Guide](../testing.md)
- [ADR-071: Engram Lifecycle Evolution](../adrs/ADR-071-engram-lifecycle-evolution.md)
