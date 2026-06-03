<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Responsiveness Protocol

## Rule: Show Progress While Work Is Running

The orchestrator communicates proactively. Silence while waiting for tools, agents, or commands is perceived as a hang by the user.

## Mandatory Behaviors

### Before Tool Calls
- Before any bash command that may take >5 seconds, state what you are running
- Use `run_in_background: true` for commands expected to take >5s
- Add a short status update between multiple blocking tool calls

### While Waiting for Agents
- After launching agents, immediately tell the user what was launched
- If an agent takes >60 seconds, proactively check its status and report
- While waiting for an agent, continue useful work or report status

### Reporting Results
- When a background task completes, report the result immediately
- Include concrete numbers: "1466 passed, 0 failed" not "tests passed"
- If a task fails, explain what failed and what you will do about it

## Agent Batching
- Maximum 10-15 agents per "sprint" within a session
- After each sprint: commit changes, run tests, checkpoint progress
- If context feels heavy (many accumulated notifications), proactively:
  1. Save session state to disk via `lib/session_state.py`
  2. Suggest a session split to the user
  3. Save summary to Engram before it is too late

## Sub-Agent Progress Protocol

Sub-agents structure their output with progress markers so the orchestrator and user can track what happened:

1. **Start**: 1-line summary of the task
2. **During**: `PROGRESS: [step N/M] description` after each major step
3. **Files**: `FILES_CREATED:` and `FILES_MODIFIED:` lists before finishing
4. **End**: Structured result with counts (tests passed, lines changed, files created)

This is enforced via the `agent-preamble.md` template that sub-agents receive.

When using ClaudeExecutor (ORCHESTRATOR_MODE=executor), progress markers are published to the Agent Bus (Valkey pub/sub) for real-time visibility.

## Anti-Patterns
- Give a status update when silence would exceed 10 seconds
- Keep agent batches bounded; 50+ agents in one session causes context exhaustion
- Run long blocking commands in the background when possible
- If you say "te aviso cuando termine", keep checking and report back
- Launch sub-agents with the agent-preamble template so progress markers exist
- Relay relevant PROGRESS markers from sub-agent output to the user

## Contextual Trigger

- When work relates to Responsiveness Protocol.
