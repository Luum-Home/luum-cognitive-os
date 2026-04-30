<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Responsiveness Protocol

## Rule: Never Appear Stuck

The orchestrator MUST communicate proactively. Silence while waiting for tools, agents, or commands is perceived as a hang by the user.

## Mandatory Behaviors

### Before Tool Calls
- Before any bash command that may take >5 seconds, state what you are running
- Use `run_in_background: true` for commands expected to take >5s
- Never chain multiple blocking tool calls without speaking between them

### While Waiting for Agents
- After launching agents, immediately tell the user what was launched
- If an agent takes >60 seconds, proactively check its status and report
- Never wait silently for an agent — continue the conversation or report status

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

Sub-agents MUST structure their output with progress markers so the orchestrator (and user) can track what happened:

1. **Start**: 1-line summary of the task
2. **During**: `PROGRESS: [step N/M] description` after each major step
3. **Files**: `FILES_CREATED:` and `FILES_MODIFIED:` lists before finishing
4. **End**: Structured result with counts (tests passed, lines changed, files created)

This is enforced via the `agent-preamble.md` template that ALL sub-agents receive.

When using ClaudeExecutor (ORCHESTRATOR_MODE=executor), progress markers are published to the Agent Bus (Valkey pub/sub) for real-time visibility.

## Anti-Patterns
- DO NOT stay silent for >10 seconds without explaining why
- DO NOT launch 50+ agents in one session (causes context exhaustion)
- DO NOT wait for a blocking command when you could run it in background
- DO NOT say "te aviso cuando termine" and then forget to check
- DO NOT launch sub-agents without the agent-preamble template (no progress markers)
- DO NOT ignore PROGRESS markers in sub-agent output — relay them to the user
