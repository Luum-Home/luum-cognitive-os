---
type: capability-synthesis
source: docs/07-Capabilities/root/agent-teams-testing.md
provenance: "How-to/runbook for testing the three COS hooks (TeammateIdle, TaskCreated, TaskCompleted) that integrate with Claude Code's experimental Agent Teams feature."
---

## What it is
A testing runbook for the three COS hooks that integrate with Claude Code's experimental Agent Teams feature: `TeammateIdle`, `TaskCreated`, `TaskCompleted`.

## Key mechanics
- Prerequisites: Claude Code v2.1.32+, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, all three hooks registered in `.claude/settings.json`, `jq` installed.
- Provides a Python one-liner to verify hook registration by reading `.claude/settings.json`.
- Automated validation: `python3 -m pytest tests/hooks/test_agent_teams_hooks.py -v` covers 28 scenarios (4 settings-registration tests, 7 TeammateIdle tests, 8 TaskCreated tests, 9 TaskCompleted tests).
- Gives manual mock-stdin `bash hooks/*.sh` invocations for each hook with expected exit codes (e.g. `TaskCreated` with a 3-char description should exit 2; a substantive `TaskCompleted` output should exit 0).
- Manual end-to-end procedure: start Claude Code with the env var, create a 3-teammate team via a natural-language prompt, observe hook behavior (TaskCreated blocks short/production-phase-noncompliant tasks; TeammateIdle keeps a teammate active via exit 2 when work remains; TaskCompleted rejects trivial or (in production phase) Trust-Report-less completions), then verify metrics files (`.cognitive-os/metrics/{teammate-idle,task-created,task-completed}.jsonl`) and `active-tasks.json` updates.
- Phase-aware behavior table: reconstruction/stabilization only block short descriptions/output; production/maintenance additionally block missing acceptance criteria (TaskCreated) and missing Trust Report (TaskCompleted).
- Graceful degradation contract: empty stdin, malformed JSON, missing fields, private mode, or missing `active-tasks.json` all cause exit 0 (allow).
- Known limitations: Agent Teams is experimental so the stdin JSON shape may change between Claude Code versions (hooks extract fields defensively); event dispatch cannot be tested in CI, only mock-input hook behavior; `SubagentStart` hook for automatic preamble injection into teammates is "not yet integrated."
- Troubleshooting notes: hooks not firing requires a Claude Code restart after `settings.json` changes; a previously-seen "exit code 5 on malformed JSON" bug is described as fixed via `|| true` guards on `jq` pipelines.

## Relations & where used
Companion document to `docs/07-Capabilities/root/agent-teams.md` (the broader Agent Teams integration/architecture doc); references `tests/hooks/test_agent_teams_hooks.py`, `hooks/teammate-idle.sh`, `hooks/task-created.sh`, `hooks/task-completed.sh`, and `.claude/tasks/active-tasks.json`.

## Status / caveats
Explicitly documents that Agent Teams "cannot be tested via subprocess or CI" — it requires an interactive session, so the automated pytest suite validates hook logic in isolation, not the full Claude Code dispatch pipeline. The doc self-identifies the stdin JSON contract as unstable ("may change between Claude Code versions") and flags `SubagentStart` integration as an open gap, not yet implemented.
