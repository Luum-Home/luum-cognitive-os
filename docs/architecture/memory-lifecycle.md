# Memory Lifecycle

> How Cognitive OS saves, protects, retrieves, and verifies cross-session
> memory for Codex, Claude Code, and future harness drivers.

## Product Contract

Cognitive OS must not rely on one chat window or one vendor harness as the
place where project memory lives.

The durable memory contract is:

1. capture important user intent while the session is active;
2. protect content before it is written to persistent memory;
3. flush structured context before compaction;
4. record session outcomes at shutdown;
5. recover pending work and prior context at the next session start;
6. verify the whole loop with an executable doctor, not only documentation.

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

Claude Code currently has richer event coverage:

- `PreCompact` for `pre-compaction-flush.sh`
- `PostToolUse` for `engram-reinforce-on-access.sh`

That is an explicit driver capability difference, not hidden Claude lock-in.
Codex should only receive equivalent projections when equivalent event semantics
are proven.

## Tests That Enforce This

| Test | What it proves |
|---|---|
| `tests/contracts/test_memory_lifecycle_portability.py` | Codex and Claude projections contain the expected memory lifecycle hooks and Codex env works without `CLAUDE_PROJECT_DIR` |
| `tests/behavior/test_cos_doctor_tools.py` | host doctor and memory lifecycle doctor execute real checks |
| `tests/behavior/test_engram_reinforce_hook.py` | reinforcement metrics can write under Codex project env |
| `tests/contracts/test_session_start_tooling_contract.py` | SessionStart host doctor includes memory lifecycle proof and does not run pytest |

## Related Documents

- [Bootstrap Portability](bootstrap-portability.md)
- [Harness Driver Parity](harness-driver-parity.md)
- [Codex Host Tooling Verification](../manual-tests/codex-host-tooling-verification.md)
- [Testing Guide](../testing.md)
- [ADR-071: Engram Lifecycle Evolution](../adrs/ADR-071-engram-lifecycle-evolution.md)
