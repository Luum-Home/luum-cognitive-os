# ADR-235 — Detached Agent Daemon

<!-- SCOPE: OS -->

**Status**: Accepted — Slice A implemented (2026-05-07)  
**Date**: 2026-05-07  
**Related**: ADR-223 (worktree-per-write-agent), ADR-225 (branch-per-task), ADR-228 (retry/budget), ADR-233 (agent-team file IPC)  
**Source**: [`docs/research/orchestration-gaps/background-agent-patterns.md`](../research/orchestration-gaps/background-agent-patterns.md)

---

## Context

Long-running local agent work currently either blocks the orchestrator or escapes into ad-hoc background shell commands with no task state, completion sentinel, cost envelope, or worktree ownership. Cloud competitors solve this with remote VMs; COS needs a local-first equivalent that does not make Redis, Postgres, Docker, or a resident daemon mandatory.

## Decision

Build an **opt-in detached local agent lane** with three primitives:

1. A file-backed queue/state directory under `.cognitive-os/agent-daemon/`.
2. `tmux` as the optional process runtime for detached visibility and attachability.
3. ADR-223 worktree-per-write-agent integration via explicit `--prepare-worktree`, never via auto-stashing the operator worktree.

Slice A intentionally does **not** install launchd/systemd units and does **not** run forever by default. It ships the queue, state machine, run script, tmux launcher, completion sentinel, and CLI. A later slice can wrap `cos agent daemon run-once` in launchd/systemd.

## State model

```text
queued -> running -> completed | failed
```

Per task:

- `tasks/<task-id>/state.json` — source of truth.
- `tasks/<task-id>/run.sh` — generated launcher script.
- `tasks/<task-id>/heartbeat.json` — written before command execution.
- `tasks/<task-id>/done.json` — written after command exit.
- `results.jsonl` — append-only completion ledger after `reap`.

## Implementation status (2026-05-07)

Implemented Slice A:

- `packages/agent-lifecycle/lib/agent_daemon.py` with `AgentDaemon`, `DetachedAgentTask`, queue/state management, tmux launch, and done-sentinel reap.
- `scripts/cos-agent-daemon` plus `cos agent daemon ...` routes for `enqueue`, `list`, `run-once`, and `reap`.
- Optional `--prepare-worktree` delegates to ADR-223 `prepare_agent_worktree` before queueing.
- Manifest policy at `manifests/detached-agent-daemon.yaml`.
- Unit and behavior tests cover queueing, generated launch script, dry-run launch, CLI flow, and fake-tmux launch.

Implemented additional slices:

- Watchdog `reap_stale` marks stale/missing-heartbeat running tasks failed with `done.json` receipts.
- ADR-228 budget gate checks estimated cost before enqueue and records estimate on completion.
- `enqueue-team-next` claims the next ADR-233 team task and queues a detached command template.
- `service-plan` prints launchd/systemd definitions without installing them.

Not implemented yet:

- launchd/systemd installer that mutates user service directories.
- Process kill escalation beyond state/done receipts.

## Hard rules

- Detached mode is opt-in.
- No command runs in the operator worktree unless the operator explicitly passes that path.
- Write-capable detached tasks should use ADR-223 worktrees.
- No secrets are injected by the daemon; callers must pass an explicit environment through the command if needed.
- `tmux` is a runtime assumption, not a bundled dependency.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_agent_daemon.py tests/behavior/test_cos_agent_daemon_cli.py -q
python3 -m py_compile scripts/cos-agent-daemon && bash -n scripts/cos
```

