---
type: concept-synthesis
source: docs/04-Concepts/architecture/cross-runtime-portability.md
provenance: "COS needs to run on AI coding tools beyond Claude Code; this doc quantifies the current 80 percent portable kernel versus the 20 percent Claude Code-specific surface and defines the adapter architecture to close the gap."
---

## What it is
Architecture for making Cognitive OS portable across multiple AI coding tools via a "kernel + driver" model: a vendor-neutral kernel plus thin per-tool driver adapters that generate tool-specific config.

## Key mechanics
- Portable today (80%): rules (94 .md files, zero coupling), skills (103 SKILL.md, low coupling, 16+ tools support), cognitive-os.yaml, SDD pipeline (8 phases), Engram/MCP, Python lib/ (20+ modules), pre-commit gate (registers as git hook not Claude hook).
- Claude Code-specific (20%): `.claude/settings.json` (proprietary hook registration), hook event names (PreToolUse/PostToolUse/Stop/SessionStart etc.), tool name matchers (Bash/Agent/Edit/Write/Read/Glob/Grep), exit-code protocol (0=allow/2=block, already shared with Cursor), `CLAUDE_PROJECT_DIR` (common.sh has fallback chain), `.claude/rules/` auto-loading, stdin JSON schema.
- Adapter pattern: canonical hooks live as tool-agnostic POSIX shell in `.cognitive-os/hooks/` (JSON stdin/stdout, exit code); each tool gets a thin adapter translating hook registration format, event names, tool names, and injecting the project-dir env var.
- Event name mapping (COS -> Claude Code/Cursor/Devin/Gemini): before_tool -> PreToolUse/pre_tool/pre_hook/PreToolUse; after_tool -> PostToolUse/post_tool/post_hook/PostToolUse; session_end -> Stop only for Claude+Gemini; session_start -> SessionStart only (Claude); subagent_end -> SubagentStop only (Claude); context_compact -> PreCompact only (Claude); user_input -> UserPromptSubmit only (Claude).
- Tool name mapping: shell->Bash/terminal, agent->Agent/none, file_edit->Edit/edit, file_write->Write/write, file_read->Read/read, search_files->Glob/none, search_content->Grep/none.
- `ide-bridge.sh` already generates configs for 15 IDEs (Cursor, Devin, Aider, Gemini, Copilot, Codex/OpenCode, Trae, Roo, Continue.dev, Augment, Warp, Cline, Zed) via per-file-copy or single-concatenated-file strategies.
- `common.sh` project-dir fallback chain: `$CLAUDE_PROJECT_DIR` -> `$COGNITIVE_OS_PROJECT_DIR` -> `git rev-parse --show-toplevel` -> `pwd`.
- 5-phase rollout: (1) AGENTS.md generation from RULES-COMPACT.md, 1-2 days, Tier 3 for 9+ tools; (2) Cursor+Devin hook adapters, 3-4 days; (3) MCP config templates, 1-2 days; (4) tool-agnostic pipeline runner (external Python CLI), 5-7 days; (5) cross-tool test suite (Cursor+OpenCode), 2-3 days.
- Git submodules in worktrees break because relative `gitdir:` paths assume the wrong filesystem depth (known upstream limitation, anthropics/claude-code#27201 closed without fix); fixed automatically by `hooks/worktree-submodule-fix.sh` (SessionStart) rewriting submodule `.git` files to absolute paths.
- What cannot be ported: Agent Teams multi-agent orchestration (falls back to sequential), SubagentStart/Stop hooks (no equivalent, governance skipped), PreCompact (no equivalent, manual checkpointing), UserPromptSubmit (only Claude Code + Cursor), auto-chain SDD pipeline (use external pipeline-runner instead), CronCreate scheduling (session-only, in-memory, no persistence).
- Scheduling alternatives ranked by durability: CronCreate (session-only, no persistence, no reboot survival) < Scheduled Tasks MCP (files persist, no auto-resume without Claude Code running) < `singularity.py daemon` (persists as OS process, harness-independent) < system crontab / launchd / systemd (persists and survives reboot and harness-independent).
- 3 ADRs: ADR-001 AGENTS.md as universal format (must stay under 4KB per ETH Zurich finding that large instruction files reduce success); ADR-002 adapter pattern over abstraction layer (hook scripts stay identical, only configs differ); ADR-003 pipeline runner as portability escape hatch (external subprocess orchestration is universal, internal Agent-tool orchestration is not).

## Relations & where used
`hooks/worktree-submodule-fix.sh`, `scripts/_lib/settings-driver-codex.sh` (see cross-tool-task-recovery-research doc), `docs/04-Concepts/root/singularity.md#scheduling-options`.

## Status / caveats
80/20 split is a snapshot claim from this doc; Phase 1-5 rollout plan status not stated here (see cross-tool-task-recovery-research-2026-05.md for a related, more current portability status on the memory/backlog side).
