# Primitive SCOPE classifier — Iteration 030 hooks agent/orchestration runtime

Date: 2026-05-15

## Goal

Reduce hook unknowns by reviewing shared multi-agent, subagent, orchestrator, and team-task runtime hooks.

## Manual classification decision

Kept 19 hooks as `SCOPE: both` and added shared-surface evidence:

- `hooks/agent-bash-cwd-enforcer.sh`
- `hooks/agent-checkpoint.sh`
- `hooks/agent-control-inbound-guard.sh`
- `hooks/agent-launch-confirmed.sh`
- `hooks/agent-message-inbox-context.sh`
- `hooks/agent-message-inbox-guard.sh`
- `hooks/agent-output-verifier.sh`
- `hooks/agent-prelaunch.sh`
- `hooks/agent-qwen-bridge.sh`
- `hooks/agent-working-dir-inject.sh`
- `hooks/orchestrator-claim-gate.sh`
- `hooks/orchestrator-decision-trace.sh`
- `hooks/orchestrator-mode-detect.sh`
- `hooks/orchestrator-skill-invocation-gate.sh`
- `hooks/subagent-capability-preflight.sh`
- `hooks/subagent-context-injector.sh`
- `hooks/task-completed.sh`
- `hooks/task-created.sh`
- `hooks/teammate-idle.sh`

## Evidence

These hooks implement reusable multi-agent runtime behavior:

- correct subagent working directory and task lifecycle tracking;
- agent output/launch safety and capability preflight;
- agent message inbox and inbound control-plane behavior;
- orchestrator claim/skill/decision governance;
- shared task creation/completion/idle coordination.

They are not COS-source-only doctrine: the same runtime behavior applies when COS runs in adopter repositories.

## Classifier robustness update

Added exact semantic patterns for reviewed agent/orchestrator/team hook names so repeated batches do not return to `unknown`.

## Before / after

Before:

```json
{"total_unknown": 303, "hooks_unknown": 62}
```

After:

```json
{"total_unknown": 284, "hooks_unknown": 43, "rules_unknown": 83, "scripts_unknown": 158}
```
