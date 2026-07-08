---
type: concept-synthesis
source: docs/04-Concepts/architecture/cross-tool-task-recovery-research-2026-05.md
provenance: "Codex, Claude Code, and future harnesses do not share session files, hook surfaces, or memory mechanics, so solved and pending work can silently exist in different places per harness; this research asks how COS should recover it reliably."
---

## What it is
Research (2026-05-02) establishing a layered, ledger-first recovery model for pending/solved work across harnesses, rather than trusting any single chat transcript or Engram alone.

## Key mechanics
- Layered source-of-truth order: (1) repository artifacts for finished decisions/plans, (2) local `.cognitive-os/` runtime evidence, (3) Engram observations for semantic recall, (4) harness transcripts as forensic input only, (5) git state for actual shipped/unresolved work.
- Existing local surfaces: active task ledger `.cognitive-os/tasks/active-tasks.json`; prompt captures `.cognitive-os/metrics/prompt-captures.jsonl`; user request queue `.cognitive-os/sessions/{session_id}/user-requests.jsonl`; session learning `.cognitive-os/metrics/session-learnings.jsonl`; git context `.cognitive-os/sessions/{session_id}/git-context.json`; changelog `.cognitive-os/changelogs/{session_id}.md`; fallback summary `.cognitive-os/metrics/session-summary-fallback.jsonl`; Engram; handoff docs `docs/SESSION-HANDOFF-*.md`; git history.
- Codex driver (`scripts/_lib/settings-driver-codex.sh`) only projects SessionStart, UserPromptSubmit, Stop, PreToolUse:Bash, PostToolUse:Bash - deliberately omits SubagentStart, PreCompact, non-Bash Pre/PostToolUse, TeammateIdle, TaskCreated, TaskCompleted rather than faking equivalence. Claude driver additionally has PreCompact and Engram-access reinforcement on PostToolUse.
- `bash scripts/cos-doctor-memory-lifecycle.sh --harness codex` proves the loop end-to-end without Claude env vars (verified 2026-05-02, passed with `--skip-engram-start`).
- Backlog snapshot on 2026-05-02: 144 completed, 28 pending, 15 cancelled-stale, 2 cancelled tasks in `active-tasks.json` (top pending items include inject-phase-context latency fix, so-existential Phase 1 reality-check, hook-architecture-v2 Phase 4+5).
- 5 gaps identified: (1) `session-backlog` skill still Claude-shaped (`platforms: ["claude-code"]`, resolves root via `CLAUDE_PROJECT_DIR -> pwd` instead of canonical precedence); (2) no single command reconciles all ledgers into `session/backlog/latest`; (3) Codex has fewer interception points (no PreCompact/non-Bash/subagent-lifecycle equivalents); (4) Engram alone is insufficient (MCP may be unavailable, hooks can't call in-process MCP tools, writes can fail silently); (5) transcripts are forensic only, not canonical.
- Recommended architecture: (1) promote `active-tasks.json` to a versioned schema (id, description, status enum, source enum, harness, session_id, timestamps, expected_outputs, check_command, evidence, supersedes/superseded_by); (2) portable reconciler `cos session backlog --write --sync-engram` / `python3 scripts/cos_session_backlog.py --write --sync-engram` writing `.cognitive-os/sessions/{id}/backlog.md`, `active-tasks.json`, `backlog-reconciliation.jsonl`, and upserting Engram `session/backlog/latest` + `session/backlog/{date}`; (3) transcript importer adapters (Claude/Codex/git-plans-docs) normalizing into the same schema, tagged `source: imported`; (4) Stop-time fallback via `session-summary-reminder.sh`; (5) SessionStart prints top-3 pending items plus git risk plus backlog freshness; (6) `manifests/harness-driver-capabilities.yaml` plus `scripts/harness_parity_audit.py` extended with memory/task-recovery capability rows.
- P0-P4 implementation plan with acceptance criteria per phase.
- 2026-05-02 update: P0/P1 shipped as `python3 scripts/cos_session_backlog.py --write --sync-engram`, using canonical precedence `COGNITIVE_OS_PROJECT_DIR -> CODEX_PROJECT_DIR -> CLAUDE_PROJECT_DIR -> cwd` and `COGNITIVE_OS_SESSION_ID -> CODEX_SESSION_ID -> CLAUDE_SESSION_ID -> default`; reconciles active tasks, plan checkboxes, request queues, changelogs, handoffs, ADR status, git state, Engram; writes `.cognitive-os/metrics/adr-implementation-latest.json` and per-session `adr-implementation-ledger.md` via `scripts/adr_implementation_ledger.py`. `tests/contracts/test_primitive_scope_classification.py` now enforces SCOPE/audience/platforms on all primitives; `tests/integration/test_install_scope.py` anchors install-scope proof.

## Relations & where used
`docs/04-Concepts/architecture/memory-lifecycle.md` (durable memory contract this research extends), `skills/session-backlog`, `.claude/skills/session-backlog`, `docs/00-MOCs/entrypoints/README.md`.

## Status / caveats
P0/P1 shipped as of the 2026-05-02 update note; P2 (Engram sync wrapper), P3 (transcript importer adapters), and P4 (doctor/contract enforcement) acceptance criteria are listed but not confirmed complete in this doc.
