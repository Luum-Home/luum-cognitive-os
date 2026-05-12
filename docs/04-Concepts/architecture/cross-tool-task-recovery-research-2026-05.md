# Cross-Tool Task Recovery Research — 2026-05-02

> Research question: how should Cognitive OS recover solved work and pending work
> from past sessions when Codex, Claude Code, and future development harnesses do
> not share the same session files, hook surfaces, or memory mechanics?

## Executive Summary

The correct source of truth is not Codex chat history, Claude transcripts, or
Engram alone. The durable recovery model should be a layered ledger:

1. **Repository artifacts** for finished decisions and plans.
2. **Local runtime evidence** under `.cognitive-os/` for prompts, task state,
   session git context, changelogs, and fallback summaries.
3. **Engram observations** for semantic recall across sessions and tools.
4. **Harness transcripts** as forensic input, never as the primary API.
5. **Git state** for actual shipped work, unresolved branches, stashes, and dirty
   worktrees.

The repository already has most of this loop: memory lifecycle docs, Codex and
Claude settings drivers, session-resume, prompt capture, session changelogs,
Engram startup, fallback stop reminders, and a doctor that proves the loop under
Codex without Claude env vars. The main gap is that the backlog inventory path
is still partly Claude-shaped and not yet promoted to a first-class portable
command that reconciles all ledgers into one canonical `session/backlog/latest`.

## External Evidence

### Claude Code

Claude Code exposes a rich hook lifecycle. Its official hook reference documents
session, turn, tool, subagent, compaction, worktree, and session-end events. This
matters because Claude can automatically run `PreCompact`, `PostToolUse`,
`SubagentStart`, `SubagentStop`, and `SessionEnd` style recovery logic that Codex
may not expose with equivalent semantics.

Important properties from the public docs:

- hooks receive JSON event context on stdin or via HTTP;
- `SessionStart` fires when a session begins or resumes;
- `UserPromptSubmit` fires before Claude processes the prompt;
- `PreToolUse` and `PostToolUse` surround tool execution;
- `Stop` fires when Claude finishes responding;
- `PreCompact` and `PostCompact` exist around compaction;
- MCP tools can be invoked from hooks after the MCP server is connected.

Source: <https://code.claude.com/docs/en/hooks>

### Codex

OpenAI positions `AGENTS.md` as repo guidance for Codex, but not as a dynamic
memory store. The official Codex launch material says AGENTS.md files are like
README files that tell Codex how to navigate a codebase, run tests, and follow
project practices. OpenAI's harness engineering guidance is even more direct:
use AGENTS.md as a map/table of contents, and keep structured repo docs as the
system of record instead of one giant instruction blob.

Codex CLI configuration also supports MCP servers through `~/.codex/config.toml`,
which makes Engram-style memory transport plausible across harnesses, but only
when the MCP is configured and available in that host.

Sources:

- <https://openai.com/index/introducing-codex/>
- <https://openai.com/index/harness-engineering/>
- <https://github.com/openai/codex/blob/main/docs/config.md>

## Local Evidence in This Repository

### Existing product contract

`docs/04-Concepts/architecture/memory-lifecycle.md` already states the right durable memory
contract: do not rely on one chat window or one vendor harness; capture user
intent, protect content, flush before compaction, record shutdown outcomes,
recover pending work at next start, and verify the loop with an executable
doctor.

It also makes a key implementation distinction: shell hooks cannot directly call
an in-process MCP tool such as `mem_session_summary`; hooks can write local
artifacts, run CLIs, launch daemons, and emit reminders. Therefore local evidence
is required even when Engram exists.

### Current save and recovery surfaces

| Surface | What it recovers | Current location |
|---|---|---|
| Active task ledger | Pending, failed, in-progress, and auto-completed tasks | `.cognitive-os/tasks/active-tasks.json` |
| Prompt capture metrics | Actionable prompt classes and safety-screened prompt signals | `.cognitive-os/metrics/prompt-captures.jsonl` |
| User request queue | User messages received while orchestrator is busy | `.cognitive-os/sessions/{session_id}/user-requests.jsonl` |
| Session learning | Session outcome metrics | `.cognitive-os/metrics/session-learnings.jsonl` |
| Git context | Start/end commit and dirty context | `.cognitive-os/sessions/{session_id}/git-context.json` |
| Changelog | Resumable session-level change narrative | `.cognitive-os/changelogs/{session_id}.md` |
| Fallback summary | Stop-hook reminder/fallback when MCP summary is not called | `.cognitive-os/metrics/session-summary-fallback.jsonl` |
| Engram | Semantic project memory and session summaries | MCP memory store |
| Handoffs | Human-readable historical closeout | `docs/SESSION-HANDOFF-*.md` |
| Git | Actual committed work and unresolved branches/stashes | repository history |

### Codex driver capabilities today

`scripts/_lib/settings-driver-codex.sh` is explicit that Codex projection is not
Claude-equivalent. Today it emits only supported lifecycle surfaces:

- `SessionStart`
- `UserPromptSubmit`
- `Stop`
- `PreToolUse:Bash`
- `PostToolUse:Bash`

It deliberately omits unsupported or unproven surfaces such as `SubagentStart`,
`PreCompact`, non-Bash Pre/PostToolUse, `TeammateIdle`, `TaskCreated`, and
`TaskCompleted`.

That is the right discipline: do not fake portability by projecting hooks onto
non-equivalent events. Instead, keep the canonical ledgers in `.cognitive-os/`
and let each driver contribute whatever lifecycle events it actually supports.

### Claude driver capabilities today

The Claude driver projects the same memory-critical SessionStart,
UserPromptSubmit, and Stop hooks, plus richer Claude-only coverage such as
`PreCompact` and Engram access reinforcement on `PostToolUse`. This is useful,
but should remain a driver advantage, not the system source of truth.

### Executable proof

`bash scripts/cos-doctor-memory-lifecycle.sh --harness codex` proves, in an
isolated scratch project, that a Codex-shaped session can:

- verify memory hooks are projected for supported events;
- start the profile bootstrap without Claude env vars;
- recover pending tasks;
- capture user prompts;
- write session-learning metrics;
- write git context;
- write a resumable changelog;
- record session-end crystallization;
- emit `mem_session_summary` reminders and fallback persistence;
- emit the pre-compaction memory-save reminder.

A local run on 2026-05-02 passed with `--skip-engram-start`; the only warning was
that Engram startup was intentionally skipped.

## Current Backlog Snapshot

A direct read of `.cognitive-os/tasks/active-tasks.json` on 2026-05-02 found:

| Status | Count |
|---|---:|
| completed | 144 |
| pending | 28 |
| cancelled-stale | 15 |
| cancelled | 2 |

The highest-signal pending items currently include:

1. Fix inject-phase-context latency.
2. so-existential Phase 1 reality-check.
3. hook-architecture-v2 Phase 4+5.
4. decision-triage critical-only re-run.
5. so-existential batch 2 baseline runs and punch list.
6. Pre-agent-snapshot root fix and border tests.
7. 87 soft decisions triage close-as-obvious.
8. Fix SessionStart hook latency violations.
9. so-existential Phase 1 prune triage.
10. Phase 3 review-agent pattern implementation.
11. Root-cause 3-spawn session startup.
12. Update `SESSION-HANDOFF-2026-05-01` with multi-spawn issue.
13. Batch 1+2 DELETE + IMPLEMENT hooks wiring.
14. Batch 3 IMPLEMENT skills wiring.
15. Batch 4 DEFER markers on 8 hooks.
16. Investigate audit/contract serial reversal.
17. Vocabulary migration separate pass and audit test.
18. Coordination Phase D: drain, negotiate, audit, spawn.
19. CI matrix dynamic lane registry.
20. Live validation: broad + unit stability.
21. Port Hermes rate_limit_tracker.
22. Build `bin/cos-skill` CLI.
23. `cos-agent spawn` plus bare_cli adapter.
24. canonical-event-emitter contract skill.
25. Port Hermes batch_runner + cron.
26. Automated tier_filter validation harness.
27. CATALOG-COMPACT lazy-load + telemetry.
28. Port Hermes error_classifier + insights.

This is a useful raw inventory, but it is not enough: some pending tasks may have
been completed later and not marked; some stale/cancelled tasks may still encode
valid next work; and Engram session summaries may include newer next steps than
the active task ledger.

## Gap Analysis

### Gap 1 — `/session-backlog` still has Claude-shaped assumptions

The `session-backlog` skill exists in both `.claude/skills/session-backlog` and
`skills/session-backlog`, and its header says `SCOPE: both`, but its frontmatter
still says `platforms: ["claude-code"]` and Step 1 resolves the project root as
`CLAUDE_PROJECT_DIR -> pwd` instead of the canonical precedence
`COGNITIVE_OS_PROJECT_DIR -> CODEX_PROJECT_DIR -> CLAUDE_PROJECT_DIR -> cwd`.

Impact: the best existing inventory procedure is conceptually portable but not
fully harness-portable in its own instructions.

### Gap 2 — no single reconciliation command owns `session/backlog/latest`

The repository has ledgers, but no one command is visibly responsible for
merging:

- active task statuses;
- plan checkboxes;
- session summaries and next steps;
- prompt/user request queues;
- handoff docs;
- git branches/stashes/dirty state;
- Engram observations;
- tests/doctor status.

The result is exactly the user's concern: solved work and pending work can exist
in multiple places, and each harness sees a different subset unless an agent
performs a manual audit.

### Gap 3 — Codex has fewer automatic interception points

Codex's projected hooks currently cannot cover every Claude event. In practice:

- no Codex `PreCompact` equivalent means compaction memory safety must be
  handled through Stop reminders, local summaries, and explicit agent protocol;
- no non-Bash Pre/PostToolUse means file-edit reinforcement cannot be assumed;
- no subagent lifecycle event means subagent task tracking needs a portable
  runner or local task ledger rather than Claude-only subagent hooks.

### Gap 4 — Engram is necessary but insufficient

Engram is excellent for semantic recall, but it should not be the only source of
truth because:

- MCP may be unavailable in a given host;
- shell hooks cannot call in-process MCP tools directly;
- memory writes can fail silently or be skipped by the agent;
- task state often needs deterministic evidence such as files, checks, commits,
  and statuses, not only semantic summaries.

### Gap 5 — transcripts are forensic, not canonical

Claude and Codex store conversation/session histories differently and change
those internals over time. A transcript importer is valuable for recovery, but
should normalize into `.cognitive-os/` ledgers and Engram observations instead
of making either vendor transcript layout a permanent dependency.

## Recommended Architecture

### 1. Canonical task ledger

Promote `.cognitive-os/tasks/active-tasks.json` from hook helper to explicit
product primitive. Define a versioned schema with:

- stable `id`;
- `description`;
- `status` enum: `pending`, `queued`, `in_progress`, `blocked`, `completed`,
  `cancelled`, `cancelled-stale`;
- `source` enum: `user`, `agent`, `plan`, `engram`, `git`, `doctor`, `imported`;
- `harness` and `session_id`;
- `created_at`, `updated_at`, `completed_at`;
- `expected_outputs`;
- `check_command`;
- `evidence`: commits, files, test commands, Engram observation IDs;
- `supersedes` and `superseded_by` for stale/cancelled reconciliation.

### 2. Portable backlog reconciler

Add a command such as:

```bash
cos session backlog --write --sync-engram
```

or a script first:

```bash
python3 scripts/cos_session_backlog.py --write --sync-engram
```

It should scan all ledgers, reconcile duplicates, validate completed tasks by
`check_command` / `expected_outputs`, mark stale items explicitly, write:

- `.cognitive-os/sessions/{session_id}/backlog.md`
- `.cognitive-os/tasks/active-tasks.json`
- `.cognitive-os/metrics/backlog-reconciliation.jsonl`

and upsert Engram:

- `session/backlog/latest`
- `session/backlog/{YYYY-MM-DD}`

### 3. Transcript importers as adapters

Build importer adapters, not direct dependencies:

```text
Claude transcript(s) ┐
Codex session logs   ├─> normalized events -> task ledger + changelog + Engram
Git / plans / docs   ┘
```

Importer output should use the same schema as live hooks. Unknown transcript
fields should be retained in `raw_ref`, not spread into core logic.

### 4. Stop-time enforcement and fallback

Keep `session-summary-reminder.sh` as the cross-harness stop safety net. Improve
it so the second-stop fallback writes enough structured information to seed the
backlog reconciler even if the agent never calls Engram.

### 5. Startup recovery protocol

On SessionStart, keep the current chain but make its output less advisory and
more actionable:

1. run fast backlog reconciliation in read-only mode;
2. print the top 3 pending user-owned items;
3. print unresolved dirty git/stash/branch risks;
4. indicate whether `session/backlog/latest` was updated recently;
5. tell the agent the exact command to refresh the full backlog.

### 6. Cross-harness capability matrix

Keep `manifests/harness-driver-capabilities.yaml` and `scripts/harness_parity_audit.py`
as the enforcement layer. Add memory/task recovery rows for:

- prompt capture;
- Stop summary reminder;
- pending task recovery;
- compaction flush;
- subagent task lifecycle;
- non-Bash tool reinforcement;
- MCP availability check;
- transcript import support.

## Concrete Implementation Plan

### P0 — Repair the existing portable backlog procedure

Acceptance criteria:

1. `skills/session-backlog/SKILL.md` uses canonical project/session precedence.
2. The skill frontmatter no longer claims Claude-only if it is supported by
   canonical instructions.
3. The procedure writes/upserts `session/backlog/latest` when Engram tools are
   available and writes local fallback when not.
4. Tests or docs cite the exact local fallback path.

### P1 — Add `scripts/cos_session_backlog.py`

Acceptance criteria:

1. Reads `.cognitive-os/tasks/active-tasks.json`.
2. Reads `.cognitive-os/plans/**/*.md` checkboxes.
3. Reads current-session `user-requests.jsonl`.
4. Reads recent `.cognitive-os/changelogs/*.md`.
5. Reads `git status`, `git stash list`, and non-merged branches.
6. Produces deterministic Markdown and JSON outputs.
7. Unit tests cover duplicate merging, stale completed detection, and missing
   Engram behavior.

### P2 — Add Engram sync wrapper

Acceptance criteria:

1. If Engram MCP is available in-agent, agent protocol saves
   `session/backlog/latest`.
2. If only Engram CLI/HTTP is available, the script can best-effort write a
   sanitized digest.
3. If Engram is unavailable, the command exits 0 and records local fallback.

### P3 — Add transcript importer adapters

Acceptance criteria:

1. Claude importer reads configured transcript files when available and emits
   normalized task events.
2. Codex importer reads known local session/log surfaces when available and
   emits the same normalized task events.
3. Unknown/missing transcript paths are warnings, not failures.
4. Imported tasks are tagged `source: imported` and require evidence before
   being marked complete.

### P4 — Enforce with doctor and contracts

Acceptance criteria:

1. `scripts/cos-doctor-memory-lifecycle.sh` verifies backlog reconciliation.
2. A contract test proves Codex can generate the backlog without Claude env vars.
3. A contract test proves Claude can generate the same schema with richer event
   coverage.
4. A docs contract keeps this research linked from `docs/00-MOCs/entrypoints/README.md`.

## Implementation Update — 2026-05-02

P0/P1 are now represented by a portable command:

```bash
python3 scripts/cos_session_backlog.py --write --sync-engram
```

The command uses canonical project/session precedence, reconciles active tasks,
plan checkboxes, user request queues, recent changelogs, handoff docs, ADR
implementation status, git status/stashes/unmerged branches, and optional Engram
observations, then writes:

- `.cognitive-os/sessions/{session_id}/backlog.md`
- `.cognitive-os/metrics/backlog-reconciliation.jsonl`
- `.cognitive-os/metrics/adr-implementation-latest.json`
- `.cognitive-os/sessions/{session_id}/adr-implementation-ledger.md`
- Engram `session/backlog/latest` and `session/backlog/{YYYY-MM-DD}` when the
  local Engram CLI wrapper is available.

The remaining P0/P1 governance gap is now enforceable rather than advisory:
`tests/contracts/test_primitive_scope_classification.py` fails any new agentic
primitive that lacks a valid `SCOPE`, any skill without `audience`, any
user-invocable skill without `platforms`, any skill-referenced script without
`SCOPE`, or any primitive root without a product-zone guardrail. The install
scope proof remains anchored in `tests/integration/test_install_scope.py`, which
covers project omission of `os-only` surfaces plus `scope=all` inclusion.

ADR implementation state is now a startup-readable ledger, not just scattered
ADR prose. `scripts/adr_implementation_ledger.py` classifies each ADR as
implemented, partial, pending, pending-evidence, blocked, superseded, or unknown
with reasons and evidence. The session startup hook only reads the cached latest
ledger to stay fast, while `/session-backlog` refreshes the ledger during full
reconciliation.

The `/session-backlog` skill now points users to this command first and documents
`COGNITIVE_OS_PROJECT_DIR -> CODEX_PROJECT_DIR -> CLAUDE_PROJECT_DIR -> cwd` plus
`COGNITIVE_OS_SESSION_ID -> CODEX_SESSION_ID -> CLAUDE_SESSION_ID -> default` as
mandatory cross-harness precedence.

## Operational Playbook for the Next Session

Run these commands before attacking new work:

```bash
# 1. prove portable memory lifecycle under Codex
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" \
  bash scripts/cos-doctor-memory-lifecycle.sh --harness codex

# 2. inspect raw pending tasks
jq -r '.tasks[] | select(.status != "completed") | [.status,.id,.description] | @tsv' \
  .cognitive-os/tasks/active-tasks.json

# 3. inspect task status counts
jq -r '.tasks[].status' .cognitive-os/tasks/active-tasks.json | sort | uniq -c

# 4. inspect git risks
git status --porcelain
git stash list
git branch --no-merged HEAD
```

Until `cos_session_backlog.py` exists, run `/session-backlog` manually but apply
canonical env precedence yourself when using Codex.

## Decision

Adopt a **ledger-first, Engram-synchronized, transcript-importable** recovery
model.

Do not make Codex or Claude session internals the source of truth. Do not treat
Engram as sufficient by itself. The canonical durable state should live in repo
artifacts and `.cognitive-os/` ledgers, with Engram as semantic index and
harness transcripts as best-effort recovery inputs.
