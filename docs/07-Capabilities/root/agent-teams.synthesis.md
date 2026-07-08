---
type: capability-synthesis
source: docs/07-Capabilities/root/agent-teams.md
provenance: "Integration reference explaining how Cognitive OS wraps Claude Code's experimental Agent Teams feature with COS's quality, security, memory, and governance hooks."
---

## What it is
Reference documentation (updated 2026-03-29) on how Cognitive OS integrates with Claude Code's experimental Agent Teams feature (v2.1.32+, Feb 2026): collaborative multi-agent teams with a shared task list and lateral communication.

## Key mechanics
- Architecture: a Team Lead (main session) coordinates a Shared Task List consumed by Teammates, each an independent Claude Code session with its own 1M-token context; teammates auto-claim tasks with file-level locking and can message each other directly, not just through the lead. Storage: `~/.claude/teams/{team-name}/config.json` and `~/.claude/tasks/{team-name}/`.
- Subagents-vs-Agent-Teams comparison table across 11 dimensions: communication topology, context isolation, task assignment, parallelism, visibility (split-pane tmux vs cycle-view in-process), cost (1x vs 3-5x), session resume (Agent Teams: not supported), coordination overhead, quality-gate application, memory persistence path, escalation, and rate limiting.
- Enablement: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` env var or `.claude/settings.json` `env` block; display mode (`in-process` default, cycle via Shift+Down, or `tmux` split panes) set in `~/.claude.json`.
- COS integration map: `SubagentStart` hook injects the COS preamble + Engram sidecar context + phase-aware rules + prohibited-terms list into each teammate at launch; `TaskCreated` hook enforces quality gates (acceptance criteria, bounded scope, verification commands) with exit 2 blocking creation; `TaskCompleted` hook runs acceptance-criteria commands, DoD checks, Trust Report validation, and claim validation, with exit 2 rejecting completion; `TeammateIdle` prevents premature shutdown by reassigning remaining tasks.
- Full example `.claude/settings.json` config wiring all four Teams-specific hooks plus standard PreToolUse/PostToolUse security hooks.
- Decision table for "Agent Teams vs Subagents" across 9 scenario types (e.g. quick file read -> subagent; 5+ independent features -> Agent Teams; SDD pipeline sequential phases -> subagent; SDD apply with 10+ independent tasks -> Agent Teams).
- Limitations table (9 rows): no session resumption for in-process teammates, task-status lag, one team per session, fixed lead, no `/resume`/`/rewind`, no nested teams, 3-5x token cost, no built-in rate limiting (mitigated by COS rate limiter), no built-in escalation (mitigated by COS agent-escalation protocol).
- Cost table: team-size cost multipliers from 2x (lead+1, "rarely justified") up to 11x (lead+10, "exceptional cases only"); COS budget governance notes each teammate counts against `max_agent_launches_per_hour` and `daily_alert_usd`/`monthly_limit_usd`, with automatic model downgrade to sonnet under budget pressure.
- Best practices: 3-5 teammates recommended, 5-6 tasks per teammate, one file per teammate to avoid merge conflicts, independent/bounded tasks, research-phase-first, broadcasts for cross-cutting decisions, mandatory Engram saves per teammate.

## Relations & where used
Direct companion to `docs/07-Capabilities/root/agent-teams-testing.md` (testing procedure for the same three lifecycle hooks). References the COS rate limiter, WorkloadScheduler, Trust Report system, error-learning pipeline, and Engram shared memory.

## Status / caveats
Describes Agent Teams as an experimental Claude Code feature "as of March 2026" with 9 explicitly enumerated limitations (no session resume, no nested teams, higher cost, etc.) — this is a living integration doc tied to an upstream feature that may change; the limitations list should be treated as time-bound, not permanent.
