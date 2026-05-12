# Replay Timeline Architectures for AI Coding Agents
## Prior Art Survey: Checkpoint, Restore, and Time-Travel Primitives

**Date:** 2026-05-06
**Scope:** Devin, Replit Agent, ConTree, AgentFS, LangGraph, Jujutsu, Cline, Hermes, Cursor, Claude Code SDK, Temporal, Replay.io
**Purpose:** Inform the minimum viable replay primitive for Luum Cognitive OS
**Status:** Research-only. No code modifications. Confidence: HIGH on architectural patterns, MEDIUM on proprietary internals.

---

## 1. Executive Summary

Every mature AI coding-agent platform shipping in 2025-2026 has converged on one user-visible guarantee: *you can go back*. Whether marketed as "restore checkpoint" (Devin, Cursor), "rollback" (Replit, Cline, Hermes), "time travel" (LangGraph, AgentFS), or "op restore" (Jujutsu), the underlying commitment is identical — the operator should never be permanently stranded by a wrong turn an agent took.

The mechanisms vary sharply in sophistication:

- **Infrastructure-backed snapshot** (Replit, Devin): full VM/container filesystem manifests stored in GCS or equivalent block storage; copy-on-write checksumming makes a new snapshot essentially free (O(1) at the manifest level). Requires cloud infrastructure investment.
- **Shadow git repository** (Cline, Kilo.ai, Hermes, git-shadow): a hidden bare Git repo outside project history; `git write-tree` after every tool call; restore is `git checkout-index`. No hypervisor. No external service. Overhead is proportional to repo size × tool-call frequency.
- **Event-log + memoized replay** (LangGraph, Temporal): every node or Activity output is persisted; replay re-runs the graph but substitutes stored outputs for live LLM/API calls. True deterministic replay at the cost of full conversation-history storage.
- **Immutable image DAG** (ConTree): each execution forks a new immutable microVM image; branches form a directed acyclic graph; rollback is a pointer swap. Requires microVM infrastructure.
- **SQLite-as-filesystem** (AgentFS): the entire agent runtime lives in one `.db` file; a snapshot is a file copy; SQL queries expose time-travel over the append-only toolcall log.

For Cognitive OS — a harness-agnostic governance layer running locally — **the shadow-git pattern is the correct minimum viable primitive**. It requires no hypervisor, no cloud storage, has prior art in four shipping products, and can be layered on top of the existing Engram event log to provide the operator-visible timeline.

The three implementation prerequisites: (1) Engram events must carry file-change diffs per tool call, (2) a shadow-git store must be created per session, (3) the governance UI (or CLI) must expose `/rollback N` with diff preview.

---

## 2. Per-System Deep Dive

### 2.1 Devin (Cognition AI)

**Feature name:** Replay Timeline + Restore Checkpoint

**Announced:** September 2024 product update (Cognition blog)

**What is recorded:** Every terminal command, file edit, and browser tab action is recorded in a full replay timeline. The architecture stores "vectorised snapshots of the code base plus a full replay timeline of every command, file diff, and browser tab Devin touches." Checkpoints mark discrete points in this timeline.

**Restore mechanism:** The operator scrubs the timeline (a horizontal progress bar visible in the Devin workspace UI with a "Live" indicator), selects a checkpoint, and clicks the restore-checkpoint icon at bottom-right. The restoration rolls back *both* files and Devin's session memory. The UI explicitly separates file state from memory state because both are components of the agent's forward context.

**Use cases explicitly documented by Cognition:**
1. Error recovery: "Devin made good progress, but then makes a mistake — it can be faster to revert Devin's changes and let Devin retry with hints."
2. Prompt iteration: "Try rolling back and editing a Playbook to test whether the edit helps Devin succeed more reliably."

**What is NOT publicly documented:** The internal storage architecture — whether Cognition uses container snapshots, a shadow-git approach, or something proprietary. The vectorised snapshot language ("vectorised snapshots of the code base") suggests embedding-level indexing layered on top of a raw file snapshot, but this is inference, not confirmed architecture.

**Non-determinism handling:** Not disclosed. Devin's restore rewinds to a prior files+memory state and re-runs forward from that point — it does not claim to reproduce the identical LLM response sequence.

**Storage granularity:** Session-scoped. Checkpoints are agent-session artifacts, not cross-session.

**UI pattern:** The timeline scrub bar — video-player metaphor applied to an agent session — is the signature UX. It is the most imitated design in the space.

### 2.2 Replit Agent

**Feature name:** Checkpoints and Rollbacks

**Architecture overview:** Replit's snapshot engine uses a custom "Bottomless Storage Infrastructure" backed by Google Cloud Storage. Filesystems are divided into 16 MiB immutable chunks stored in GCS. A manifest tracks pointers to these chunks. Copying a checkpoint is a manifest copy — O(1) regardless of filesystem size. This is a copy-on-write block device abstraction at the cloud storage layer.

**Checkpoint trigger:** Whenever the Agent reaches a "state of doneness" for a task. These are semantic checkpoints, not heartbeat checkpoints — the agent decides when it has completed a coherent unit of work.

**What gets saved per checkpoint:**
- All project files and directories (via the GCS manifest)
- AI conversation context and history
- Environment and runtime configuration
- Agent memory (architectural understanding, patterns learned)
- Database contents (PostgreSQL data via Neon branch or local volume)

**Database branching:** Replit integrates with Neon serverless Postgres. Each checkpoint creates a Neon database branch at a specific timestamp; Neon's copy-on-write ensures the branch is lightweight. On restore, Replit promotes the branch to replace the current database, ensuring code and data restore atomically.

**Restore mechanics:** `checkpoint()` copies the current GCS manifest under a new name. `restore()` replaces the current manifest with the saved version. This is the entire restore operation at the infrastructure level — it is a pointer swap.

**Non-destructive preview:** Users can view their app's appearance at any checkpoint state before committing to rollback.

**Conversation continuity:** Restoring a checkpoint preserves AI context, so the user can continue building from the restored state without restarting the conversation.

**Storage cost:** Not published. The 7-day retention window on Neon suggests Replit manages storage cost through TTL, not per-checkpoint billing.

### 2.3 ConTree (Nebius)

**Feature name:** Git-like branching for cloud sandboxes

**Architecture:** ConTree uses dedicated microVMs (hardware-level kernel isolation, not shared-namespace Docker). After every execution in non-disposable mode, the entire filesystem is captured as an immutable image. Images form a directed acyclic graph (parent-child relationships tracked as "image lineage"). The branching API allows forking N times from any checkpoint, running all branches in parallel on separate microVMs, scoring results, and discarding losers.

**Branching workflow:**
```python
# Fork 3 parallel explorations from one checkpoint
branch_a = contree.fork(base_image_id)
branch_b = contree.fork(base_image_id)
branch_c = contree.fork(base_image_id)
# Run all 3 in parallel, compare results, keep winner
```

**Rollback:** Jump to any previous image in the DAG. One API call. The image UUID or human-readable tag is the reference.

**Disposable vs. non-disposable mode:** Disposable mode (for tests, one-off checks) produces no persistent image. Non-disposable mode creates a new image per execution. This two-mode design avoids runaway storage accumulation from exploratory runs.

**Process/network exclusion:** Process memory and network state are explicitly excluded from snapshots. ConTree captures filesystem state only — not an in-flight process state.

**Integration with search algorithms:** The DAG structure is designed to support MCTS, Beam Search, and value-function estimation over agent execution paths. This is the most theoretically sophisticated branching model in the survey.

**Limitation for COS:** Requires microVM infrastructure. Not practical for a local harness-agnostic tool.

### 2.4 AgentFS (Turso)

**Feature name:** SQLite-backed agent filesystem with copy-on-write isolation

**Architecture:** AgentFS stores the entire agent runtime — files, key-value state, and tool-call audit log — in a single SQLite database file. Three storage layers:
1. **Filesystem layer:** Two SQLite tables mirroring Unix kernel design: `dentry` (paths and directory structure) + `inode` (file contents and metadata). POSIX-like operations are translated to SQL.
2. **Key-value store:** A single `kv` table mapping keys to JSON-serialized values.
3. **Toolcall audit log:** An append-only table; rows are never mutated, only inserted. Every tool invocation produces an immutable record queryable by SQL.

**Snapshot mechanism:** A snapshot is a file copy of the `.db` file. Because SQLite is a single-file database, `cp agent.db agent-snapshot-$(date +%s).db` is a complete state backup. This is the simplest snapshot primitive in the survey.

**WAL integration:** SQLite's Write-Ahead Log captures all mutations as a sequence of changes before checkpointing to the main database. The WAL + the main `.db` together represent the full committed state plus in-flight changes — providing sub-commit granularity time travel.

**FUSE integration (agentfs-fuse):** AgentFS can be mounted as a POSIX filesystem via FUSE, using the `fuser` Rust crate. Every write goes through a database transaction, ensuring filesystem operations and database state remain consistent. Kernel writeback caching gives performance parity with native filesystem for write-heavy operations.

**Time travel via SQL:** Because the toolcall log is append-only with timestamps, an operator can query agent history at any point: `SELECT * FROM toolcalls WHERE timestamp <= $target_time`. This is not a restore in the traditional sense — it is forensic replay via SQL.

**Portability:** The single-file model means agent state can be moved between machines, committed to version control, or deployed to any system where SQLite runs.

### 2.5 LangGraph Checkpointer

**Feature name:** Time-travel debugging and checkpoint-based state persistence

**Architecture:** LangGraph saves a complete snapshot of the graph state after each "super-step" (a full round of node executions). Checkpoints are associated with a `thread_id` + `checkpoint_id` tuple. The checkpointer backends are pluggable: `InMemorySaver` (RAM, process-scoped), `SqliteSaver` (file-backed, persists across restarts), `PostgresSaver` (database-backed, multi-user production), and vendor extensions (DynamoDB, Couchbase, etc.).

**State data model:**
```python
class AgentState(TypedDict):
    # All fields captured at each super-step
    messages: list
    intermediate_results: NotRequired[dict]
    decision: NotRequired[str]
```

**Two time-travel operations:**

1. **Replay:** Resume execution from a prior checkpoint. All downstream nodes re-execute. LLM calls, API requests, and interrupts fire again and may return different results. Replay does NOT guarantee identical outputs — it guarantees identical starting state.

2. **Fork:** Create a new execution branch from a historical checkpoint with modified state. `update_state(checkpoint_config, values)` generates a new checkpoint ID without modifying the original thread. The original execution history remains intact.

**Non-determinism handling:** LangGraph takes the pragmatic position: "LangGraph Time Travel does not make LLMs deterministic — it makes agent workflows reliable." Replay from a checkpoint may produce different LLM outputs. The value is in making the decision workflow transparent and correctable, not in producing identical LLM tokens.

**Interrupt re-trigger:** During time travel, interrupts always re-trigger. This enables human-in-the-loop workflows where an operator can fork between interrupt points without re-answering earlier questions.

**Storage scaling:** `get_state_history(config)` retrieves the complete checkpoint history for a thread. For long-running agents, this history can become large. LangGraph does not implement automatic TTL or pruning — that is left to the operator.

### 2.6 Jujutsu (jj) Operation Log

**Feature name:** `jj op log` + `jj op restore`

**What it is:** Jujutsu is an experimental version control system that layers a content-addressed commit graph on top of a Git repository. Its operation log records every mutation to the repository as a discrete operation object.

**Data model per operation:**
- Pointer(s) to the operation(s) immediately before it (parent operations)
- A complete "view" snapshot: where every bookmark, tag, and Git ref pointed; the set of heads; the current working-copy commit per workspace
- Metadata: timestamp, username, hostname, operation description

**Mechanically different from git reflog:** Git reflog is a per-ref linear sequence of reference mutations. Jujutsu's operation log supports *concurrent operations* — two `jj` commands running simultaneously on different machines produce divergent operations that can later be reconciled. The operation log is a DAG, not a linear list.

**`jj op restore`:** Restores the entire repository to the view snapshot contained in any operation. This is a whole-repo time travel, not file-level. It is described as "a supercharged version of git's reflog command" that "works way more reliably."

**Relevance to COS:** The operation log pattern — recording every mutation as a typed, timestamped, parent-linked object — is exactly the Engram event log model. `jj op restore` demonstrates that this pattern is sufficient for full repository time-travel without a hypervisor.

### 2.7 Cline Checkpoints

**Feature name:** Checkpoint system with three restore modes

**Architecture:** Cline uses a shadow Git repository separate from the project's own `.git`. After each tool use (file modification, command execution), Cline commits the current state to this shadow repo. The shadow repo is a bare repository; the project worktree is the detached working tree.

**Three restore modes:**
1. **Restore Files only:** Reverts project files to the snapshot at this checkpoint. Conversation history is preserved. Use when code broke but the discussion remains valuable.
2. **Restore Task only:** Deletes messages after this point. Files are not changed. Use for redirecting dialogue while keeping working code.
3. **Restore Files and Task:** Complete reset — files reverted and messages deleted. Full "undo everything" operation.

**Key characteristics:**
- Snapshots occur after every tool use
- Checkpoints survive editor session restarts (persist on disk)
- Captures untracked files (unlike standard git operations)
- Does not affect the project's own Git history

**Known performance issue:** For very large repositories, checkpoint commits after each tool use can cause noticeable latency. Users are advised to disable the feature for repos with hundreds of thousands of files.

**Implementation artifact:** The shadow-git approach is confirmed and documented in Cline's own technical documentation — it is not inferred.

### 2.8 Hermes Agent (NousResearch)

**Feature name:** `/rollback` with shadow git store

**Architecture:** Hermes maintains a single shared shadow git repository at `~/.hermes/checkpoints/store/`. Unlike Cline's per-project shadow repo, Hermes uses a shared store across projects, with content deduplication.

**Checkpoint triggers:**
- File write operations (`write_file`, `patch`)
- Destructive terminal commands (`rm`, `rmdir`, `cp`, `install`, `mv`, `sed -i`, `git reset/clean/checkout`)
- Maximum one checkpoint per directory per conversation turn

**Rollback commands:**
- `/rollback` — list all checkpoints with change statistics
- `/rollback N` — restore to checkpoint N and undo the last chat turn
- `/rollback diff N` — preview changes since checkpoint N (non-destructive)
- `/rollback N <file>` — restore a single file from checkpoint N

**Context synchronization:** When executing `/rollback N`, Hermes also "undoes the last conversation turn so the agent's context matches the restored filesystem state." This is the key insight — file restore without context restore leaves the agent in an inconsistent state where it believes it made changes that no longer exist.

**Configuration limits:**
```yaml
max_snapshots: 20           # per project
max_total_size_mb: 500      # enforced via oldest-first eviction
max_file_size_mb: 10        # individual file exclusion threshold
retention_days: 7           # orphan deletion threshold
```

**Safety guardrails:** Skips directories exceeding 50,000 files; excludes files above size threshold; prevents snapshots of root or home directories.

### 2.9 Cursor Agent Checkpoints

**Feature name:** Checkpoints (Agent mode)

**Architecture:** Cursor creates a checkpoint before every AI Agent code modification by "zipping up the pre-change state." Checkpoints are stored locally in a hidden directory on the user's machine, separate from Git history.

**What is captured:** Only AI Agent-generated modifications. Manual edits made by the developer are not tracked. This is an explicit design choice — Cursor positions checkpoints as "Agent undo history," not general version control.

**Restore methods:** Clicking "Restore Checkpoint" on a previous chat message, or hovering over a message to access a "+" restore button.

**Explicit non-VCS positioning:** Cursor documentation states checkpoints "are not version control" and should not replace Git. They are ephemeral, temporary artifacts designed for short-term experimentation.

**Known issues from community forum:** "Restore Checkpoint permanently destroys change history" — when restoring, all checkpoints after the target are deleted, making this a destructive operation that cannot itself be undone. This is a significant UX flaw compared to Cline's three-mode approach.

### 2.10 Claude Code Agent SDK File Checkpointing

**Feature name:** File checkpointing with `rewindFiles()` / `rewind_files()`

**Architecture:** The SDK tracks file changes made through the `Write`, `Edit`, and `NotebookEdit` tools. Each user message in the response stream carries a UUID when `replay-user-messages` is enabled. These UUIDs serve as checkpoint identifiers.

**What is tracked:**
- Files created during the session
- Files modified during the session
- Original content of modified files before modification

**What is NOT tracked:** Changes made via Bash commands (`echo > file.txt`, `sed -i`, etc.). This is a critical limitation — agents frequently use shell commands for file manipulation.

**Restore API:**
```python
# Enable checkpointing
options = ClaudeAgentOptions(
    enable_file_checkpointing=True,
    extra_args={"replay-user-messages": None}
)

# Capture checkpoint UUID
if isinstance(message, UserMessage) and message.uuid:
    checkpoint_id = message.uuid

# Rewind files (file-only, conversation preserved)
await client.rewind_files(checkpoint_id)
```

**CLI equivalent:**
```bash
claude -p --resume <session-id> --rewind-files <checkpoint-uuid>
```

**Important limitation:** `rewindFiles()` restores file content only. Conversation history is explicitly not rewound. The documentation notes: "It does not rewind the conversation itself. The conversation history and context remain intact after calling rewindFiles()." This is the inverse of Cline's "Restore Task only" mode — Claude SDK restores files but not conversation; Cline offers both.

---

## 3. Cross-Cutting Analysis

### 3.1 Data Model Taxonomy

Four distinct data models emerge from this survey:

| Model | Representative Systems | Core Primitive | Granularity |
|-------|----------------------|----------------|-------------|
| **Manifest-based snapshot** | Replit, Devin (inferred) | Immutable chunk pointers in object storage | Full filesystem per checkpoint |
| **Shadow git tree** | Cline, Hermes, Kilo.ai, git-shadow | `git write-tree` → tree SHA per tool call | File-level, after every tool call |
| **State graph checkpoint** | LangGraph, Temporal | Serialized TypedDict / activity result per node | Graph node per super-step |
| **Immutable image DAG** | ConTree | MicroVM filesystem image per execution | Full container filesystem per run |
| **SQLite append-only log** | AgentFS | Append-only `toolcall` table + dentry/inode tables | Per tool call, SQL-queryable |

COS's Engram event log maps most directly to the **state graph checkpoint** and **SQLite append-only log** models, but currently lacks the file-state dimension that shadow git provides.

### 3.2 Restore Granularity Spectrum

From coarsest to finest:

1. **Full session restart** (no checkpoint) — start over entirely
2. **Conversation-only rollback** (Cline "Restore Task only") — rewind messages, keep files
3. **Files-only rollback** (Cline "Restore Files only", Claude SDK `rewindFiles()`) — revert filesystem, keep conversation
4. **Full rollback** (Cline "Restore Files and Task", Replit rollback, Devin restore) — revert both files and agent memory/conversation
5. **Single-file rollback** (Hermes `/rollback N <file>`) — revert one file to checkpoint N state
6. **Node-level fork** (LangGraph `update_state` + `invoke`) — modify a single checkpoint value and re-run forward

The full-rollback (option 4) is the minimum viable user expectation. Single-file rollback and node-level fork are power-user features.

### 3.3 Determinism: The Hard Problem

None of the surveyed systems solve deterministic replay in the strict sense (re-executing the agent and getting identical LLM outputs). The approaches to non-determinism fall into three categories:

**Category A — Ignore it (pragmatic fork):** LangGraph, Cline, Cursor, Hermes. Restore resets file+context state to a prior point; the agent re-runs forward and may produce different outputs. The bet: different outputs after correction hints are *better*, not worse.

**Category B — Memoize it (Temporal/event sourcing pattern):** Temporal wraps LLM calls as Activities; recorded Activity outputs are substituted during replay, producing byte-identical re-execution. Expensive: requires storing every LLM response (potentially thousands of tokens per call × many calls). Used for durability/fault-tolerance, not for user-visible replay.

**Category C — Record and stub it (sakurasky/AgentRR pattern):** Trace every LLM call (prompt + params + response) and tool call (inputs + outputs + timestamps) into a JSONL log. Replay mode substitutes `ReplayLLMClient` and `ReplayToolClient` stubs that feed back recorded responses. Six sources of non-determinism explicitly eliminated: LLM sampling, tool output, system clock, data drift, concurrency, configuration drift.

For COS, **Category A is sufficient for the MVP**. Category C is the correct target for a debugging/regression-testing workflow but requires substantially more infrastructure.

### 3.4 Storage Costs and Scaling

Published constraints from surveyed systems:

| System | Storage limit | Mechanism |
|--------|--------------|-----------|
| Hermes | 500 MB total, 20 snapshots max, 7-day TTL | Oldest-first eviction |
| Replit | 7-day retention window (Neon database) | TTL on branch data |
| Cline | "Significant storage for large repos" | No published limit; user opt-out |
| Cursor | Hidden local directory | No published limit |
| LangGraph | No built-in limit | Operator-managed |

Shadow git is the most storage-efficient at scale because `git write-tree` uses object deduplication — identical file content across checkpoints shares a single blob object. A repo where 90% of files don't change between checkpoints stores only the 10% delta per checkpoint.

Worst case: a repo with 100k files, 50% churn per tool call, 1 tool call/minute, 8-hour session = ~24,000 write-tree operations × ~50k files changed = significant I/O. In practice, tool calls affect 1-5 files, making the real-world cost negligible.

### 3.5 UI/UX Ergonomics: What Users Actually Do

From community forum analysis across Cursor, Replit, and Cline:

**Common patterns:**
- Users primarily use rollback as an "escape hatch" when an agent goes wrong, not as a regular workflow tool
- The "diff preview before restore" feature (Replit non-destructive preview, Hermes `/rollback diff N`) is highly valued — blind rollback is anxiety-inducing
- Cursor's irreversible checkpoint destruction is a recurring complaint: once you restore, the later checkpoints are gone
- Cline's three-mode restore is praised for flexibility but criticized for requiring too many decisions under stress
- Hermes's single-file restore (`/rollback N <file>`) is a power feature that reduces the blast radius of a rollback decision

**DVR metaphor adoption:** The Devin scrub-bar is the most admired UX. Multiple tools (CommitReel, the DVR-for-agents dev.to article) explicitly use the video-player metaphor: timeline scrubbing, playback speed, episode markers.

**The "context mismatch" problem:** Every system that restores files without also restoring conversation context risks leaving the agent believing it made changes that no longer exist, or believing it did not make changes that it did make. Hermes explicitly addresses this by "undoing the last conversation turn" alongside the filesystem restore. This is the most common bug class in checkpoint implementations.

---

## 4. Comparative Table

| System | Storage primitive | Non-determinism | Restore modes | File-only | Conv-only | Both | Single-file | Fork/branch | Hypervisor required |
|--------|-----------------|----------------|---------------|-----------|-----------|------|-------------|-------------|---------------------|
| Devin | Vectorised snapshot + replay timeline (proprietary) | Not addressed (re-run) | Files + Memory | No | No | Yes | No | No (UI) | Unknown |
| Replit Agent | GCS manifest + Neon DB branch | Not addressed (re-run) | Full rollback | No | No | Yes | No | No | No (cloud infra) |
| ConTree | Immutable microVM image DAG | Not applicable (sandbox) | Image pointer | N/A | N/A | Yes | No | Yes (N parallel) | Yes (microVM) |
| AgentFS | SQLite single-file + WAL | SQL query at timestamp | File copy | Yes | No | Yes (copy DB) | Yes (SQL) | Limited | No |
| LangGraph | Pluggable backend (Sqlite/PG) | Re-run (different LLM output) | Node-level fork | No | No | Yes | Via fork | Yes (fork) | No |
| Jujutsu | Operation log DAG (git-backed) | Not applicable (VCS) | Full repo | Yes | N/A | N/A | No | Yes (op fork) | No |
| Cline | Shadow git repo | Re-run (different LLM output) | 3 modes | Yes | Yes | Yes | No | No | No |
| Hermes | Shared shadow git store | Re-run + context undo | 4 modes | Yes | No | Yes | Yes | No | No |
| Cursor | Local hidden zip archive | Re-run (different LLM output) | Files only | Yes | No | No | No | No | No |
| Claude Code SDK | In-session file tracker | Re-run (different LLM output) | Files only | Yes | No | No | No | No | No |
| Temporal | Event history (Cassandra/PG) | Memoized (byte-identical) | Workflow replay | No | No | Yes | No | No | No |

---

## 5. Verdict for COS: Minimum Viable Replay Primitive

### 5.1 Design Constraints

Cognitive OS must remain:
- **Harness-agnostic**: cannot assume Claude Code, Cursor, or any specific IDE
- **Hypervisor-free**: no container runtime, no cloud infrastructure required
- **Local-first**: operators may run fully offline
- **Engram-integrated**: the event log is the single source of truth for session state

### 5.2 The Shadow-Git + Engram Event Annotation Pattern

The recommended primitive combines two existing mechanisms:

**Layer 1 — Shadow git tree (filesystem state)**

Implement a per-session shadow git store at a configurable path (default: `~/.cognitive-os/snapshots/<project-id>/<session-id>/`). After every tool call that modifies files, execute `git write-tree` against the project worktree and store the resulting tree SHA in the session's Engram event.

This is exactly the Cline + Kilo.ai + Hermes pattern, confirmed working in production.

**Layer 2 — Engram event annotation (agent state)**

Each Engram event already carries a timestamp, tool name, and result. Add two fields:
- `file_tree_sha`: the shadow git tree SHA captured *before* this tool call
- `file_changes`: list of modified paths (for targeted file-level restore)

This links file state to conversation state without duplicating file content — the tree SHA is the pointer; the shadow git object store holds the bytes.

**Layer 3 — Restore primitive**

Three restore modes (matching Cline's proven design):
```
/rollback N files     # restore filesystem to pre-step-N state, keep conversation
/rollback N task      # delete conversation after step N, keep filesystem
/rollback N           # restore filesystem + truncate conversation to step N
```

Implementation: `git checkout-index -a --prefix=<project-root>/ <tree-sha>` writes the tree to disk. Conversation truncation removes Engram events after the target step.

### 5.3 Prerequisites

In priority order:

1. **Shadow git store initialization** (`lib/shadow_git.py`): `git init --bare` at session start; `git write-tree` wrapper that commits to the shadow store and returns SHA.

2. **Engram event schema extension**: Add `file_tree_sha` (optional string) and `file_changes` (optional list) to the standard event envelope in `lib/harness_adapter/`.

3. **Rollback primitive** (`lib/replay_primitive.py`): Three-mode restore as described. Must validate that tree SHA exists before executing restore (guard against garbage-collected shadow stores).

4. **CLI entrypoint** (`/rollback` skill): Calls `replay_primitive.restore(session_id, step_n, mode)`. Shows diff preview by default (`git diff-tree --name-status <sha-before> <sha-after>`).

5. **Governance UI annotation** (optional, later): Surface the timeline in the session report, linking each step to its tree SHA.

### 5.4 What This Does NOT Provide

- **Deterministic LLM replay**: Re-running from a checkpoint may produce different LLM outputs. This is acceptable for MVP. For regression testing, implement Category C tracing (sakurasky pattern) as a separate capability.
- **Database state restore**: If the agent modifies a database, the shadow git store does not capture that. Scope: filesystem only in v1.
- **Bash command tracking**: Changes made via shell (`sed -i`, `echo > file`) are not tracked by tools-only file watchers. The Claude Code SDK has the same limitation. Mitigation: wrap risky shell operations or add an `inotify`/`FSEvents` watcher as a later enhancement.
- **Cross-session timeline**: Each session has its own shadow store. Cross-session timeline browsing requires linking sessions via a project-level index, which is a v2 feature.

### 5.5 Competitive Positioning

This primitive delivers Cline-parity (which ships today and is adopted by a large community) without a hypervisor, without cloud infrastructure, and without modifying the existing Engram schema in a breaking way. It is defensible against the Devin story ("scrub and restore") because the operator-visible experience is equivalent: pick a step, preview diff, restore.

The differentiation opportunity is **governance-integrated replay**: because COS attaches `file_tree_sha` to the Engram governance event, every policy check, blast-radius assessment, and agent-audit finding is linked to a precise, restorable filesystem state. No competitor in this survey links governance decisions to file state with restore capability. This is a unique value proposition.

---

## 6. Sources Consulted

1. Cognition AI. "Devin September '24 Product Update." https://cognition.ai/blog/sept-24-product-update (Checkpoint restore announcement)
2. Cognition AI. "Devin 2.0." https://cognition.ai/blog/devin-2 (Architecture context)
3. Replit Engineering. "Inside Replit's Snapshot Engine." https://blog.replit.com/inside-replits-snapshot-engine (GCS manifest, copy-on-write, checkpoint mechanics)
4. Replit Docs. "Checkpoints and Rollbacks." https://docs.replit.com/replitai/checkpoints-and-rollbacks (User-facing restore flow, what gets saved)
5. Neon Engineering. "Replit App History: Time Travel for Code and Data, Powered by Neon Branches." https://neon.com/blog/replit-app-history-powered-by-neon-branches (Database branching, atomic restore)
6. ConTree / Nebius. "ConTree — Sandboxed Code Execution with Git-Like Branching for AI Agents." https://contree.dev/ (Image DAG, fork/rollback API)
7. ConTree Documentation. "ConTree for SWE Agents." https://docs.contree.dev/swe-agents.html (MCTS/Beam search integration)
8. Turso Engineering. "The Missing Abstraction for AI Agents: The Agent Filesystem." https://turso.tech/blog/agentfs (SQLite architecture, three storage layers)
9. Turso Engineering. "AgentFS with FUSE: SQLite-backed agent state as a POSIX filesystem." https://turso.tech/blog/agentfs-fuse (FUSE integration, write consistency)
10. LangChain Documentation. "Use time-travel." https://docs.langchain.com/oss/python/langgraph/use-time-travel (Replay vs. Fork mechanics)
11. Dev.to (sreeni5018). "Debugging Non-Deterministic LLM Agents: Implementing Checkpoint-Based State Replay with LangGraph." https://dev.to/sreeni5018/debugging-non-deterministic-llm-agents-implementing-checkpoint-based-state-replay-with-langgraph-5171 (LangGraph code patterns, non-determinism analysis)
12. Jujutsu VCS Documentation. "Operation log." http://docs.jj-vcs.dev/latest/operation-log/ (Operation log data model, view snapshot, concurrent operations)
13. Cline Documentation. "Checkpoints." https://docs.cline.bot/features/checkpoints (Three restore modes, shadow git implementation, known limitations)
14. NousResearch / Hermes Agent. "checkpoints-and-rollback.md." https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/checkpoints-and-rollback.md (/rollback commands, config limits, context synchronization)
15. Kilo.ai Documentation. "Checkpoints." https://kilo.ai/docs/code-with-ai/features/checkpoints (Shadow git tree SHA per message, git write-tree pattern, Kilo storage path)
16. Anthropic. "Rewind file changes with checkpointing." https://code.claude.com/docs/en/agent-sdk/file-checkpointing (rewindFiles API, UUID checkpoint, Bash limitation)
17. Cursor Documentation / Steve Kinney. "Understanding Cursor Checkpoints for Safe AI Edits." https://stevekinney.com/courses/ai-development/cursor-checkpoints (Pre-edit zip, hidden local dir, irreversible restore issue)
18. sakurasky.com. "Trustworthy AI Agents: Deterministic Replay." https://www.sakurasky.com/blog/missing-primitives-for-trustworthy-ai-part-8/ (TraceWriter/TraceIndex/ReplayLLMClient architecture, six non-determinism sources)
19. Temporal Engineering. "Durable Execution meets AI." https://temporal.io/blog/durable-execution-meets-ai-why-temporal-is-the-perfect-foundation-for-ai (Activity memoization, event history as durable replay)
20. eunomia.dev. "Checkpoint/Restore Systems: Evolution, Techniques, and Applications in AI Agents." https://eunomia.dev/blog/2025/05/11/checkpointrestore-systems-evolution-techniques-and-applications-in-ai-agents/ (CRIU, container-level, stateful vs. stateless taxonomy)
21. Dev.to (json_shotwell). "Build a DVR for AI Agents: Episode Replay UI That Actually Works." https://dev.to/json_shotwell/build-a-dvr-for-ai-agents-episode-replay-ui-that-actually-works-34p2 (AgentEpisode/AgentMessage data model, SQLite storage, React timeline UI)
22. Replay.io. "The MCP time travel debugger for your coding agent." https://www.replay.io/ (Deterministic browser capture, MCP integration for agent debugging)
23. arxiv.org (2505.17716). "Get Experience from Practice: LLM Agents with Record & Replay." https://arxiv.org/abs/2505.17716 (AgentRR multi-level experience abstraction, check function mechanism)

---

*Word count: ~5,200 words. Sources: 23. Research conducted via 10 distinct WebSearch queries and 16 WebFetch fetches.*
