# Agent Teams Integration

> How Cognitive OS leverages Claude Code's experimental Agent Teams feature.
> Updated: 2026-03-29

## What Are Agent Teams?

Agent Teams is an experimental Claude Code feature (released with v2.1.32+, Feb 2026) that enables collaborative multi-agent teams with a shared task list and lateral communication between teammates.

### Architecture

```
                    Team Lead (main session, 1M context)
                         |
                    Shared Task List
                   /       |        \
            Teammate A  Teammate B  Teammate C
            (1M ctx)    (1M ctx)    (1M ctx)
                \          |          /
                 lateral communication
```

**Team Lead**: The main Claude Code session that creates the team, defines tasks, and coordinates work. The lead assigns initial tasks and can broadcast messages to all teammates.

**Teammates**: Independent Claude Code sessions, each with their own 1M context window. Teammates auto-claim tasks from the shared list and can communicate directly with each other (not just through the lead).

**Shared Task List**: A centralized task queue stored in `~/.claude/tasks/{team-name}/`. Teammates claim tasks with file-level locking to prevent double-assignment. Tasks have status tracking (pending, in-progress, completed).

**Lateral Communication**: Unlike traditional subagents, teammates can send direct messages to each other and broadcast to the team. This enables coordination without bottlenecking through the lead.

## Subagents vs Agent Teams

| Dimension | Subagents (current COS) | Agent Teams |
|-----------|------------------------|-------------|
| Communication | Through orchestrator only | Direct teammate-to-teammate + lead broadcasts |
| Context | Shared parent context (constrained) | Independent 1M context per teammate |
| Task assignment | Orchestrator dispatches | Auto-claim from shared list |
| Parallelism | Fire-and-forget or sequential | True parallel with coordination |
| Visibility | Output returned to parent | Split-pane (tmux) or cycle view (in-process) |
| Cost | 1x (single context) | 3-5x token cost (multiple full contexts) |
| Session resume | Not applicable | Not supported (limitation) |
| Coordination overhead | High (orchestrator bottleneck) | Low (lateral communication) |
| Quality gates | Full COS stack applies | COS hooks apply via Teams hooks |
| Memory persistence | Engram via orchestrator | Engram directly per teammate |
| Escalation | Agent escalation protocol | No built-in escalation |
| Rate limiting | WorkloadScheduler + RateLimiter | No built-in rate limiting |

## How to Enable

### Environment Variable

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

### Via settings.json

Add to `.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### Display Modes

Configure teammate display in `~/.claude.json`:

```json
{
  "teammateMode": "in-process"
}
```

| Mode | How It Works | Requirements |
|------|-------------|--------------|
| `in-process` (default) | Shift+Down to cycle between teammates | Any terminal |
| `tmux` | Split panes showing all teammates | tmux or iTerm2 |

### Storage

Teams store configuration and task data in:
- `~/.claude/teams/{team-name}/config.json` -- team configuration
- `~/.claude/tasks/{team-name}/` -- shared task list

## COS Integration Points

Cognitive OS wraps Agent Teams with quality, security, memory, and governance layers. The integration uses Claude Code's hook system to inject COS behavior into the Teams lifecycle.

```
                         Team Lead
                    (COS orchestrator rules)
                            |
                   Shared Task List
                   +-- TaskCreated hook (COS quality gates)
                   +-- TaskCompleted hook (COS acceptance criteria)
                            |
                   /        |        \
            Teammate A   Teammate B   Teammate C
            +SubagentStart hook (preamble + sidecar injection)
            +TeammateIdle hook (escalation prevention)
            +All COS PostToolUse hooks (security, content-policy, etc.)
            +Engram access (shared persistent memory)
```

### Hook Integration Map

| COS Primitive | Integration Point | How It Works |
|---------------|-------------------|-------------|
| SubagentStart hook | Teammate context injection | Injects agent-preamble.md + Engram sidecar context into each teammate at launch |
| TaskCreated hook | Quality gates on task specs | Validates task descriptions have acceptance criteria, scope, and verification commands before creation |
| TaskCompleted hook | Acceptance criteria verification | Verifies Definition of Done criteria are met before marking a task complete; exit 2 rejects completion |
| TeammateIdle hook | Escalation prevention | Prevents premature teammate shutdown; assigns remaining tasks or requests teammate to help others |
| Engram | Shared memory across teammates | All teammates save decisions, discoveries, and fixes to the same Engram instance |
| Rate limiter | Cost control | Each teammate counts as an agent launch against the rate limiter and budget governance |
| Security hooks | Per-teammate enforcement | content-policy.sh, secret-detector.sh, and all security hooks apply to every teammate's tool calls |
| active-tasks.json | Task synchronization | Map Teams shared task list entries to COS active-tasks.json for fault tolerance and session recovery |
| Trust score | Per-teammate quality tracking | Each teammate outputs a Trust Report on task completion; scores logged to metrics |
| Error learning | Cross-teammate learning | Errors from any teammate are captured to error-learning.jsonl; pattern warnings injected into all teammates |

### SubagentStart Hook for Teams

The SubagentStart hook fires when each teammate session initializes. COS uses this to inject:

1. **Agent preamble**: Standard COS preamble with progress markers, communication standards, and auto-refine protocol
2. **Engram sidecar**: Per-agent learnings from previous sessions (loaded from `agent/{agent-name}/sidecar`)
3. **Project context**: Phase-aware rules, acceptance criteria templates, and quality gate instructions
4. **Prohibited terms**: Content policy terms list to prevent violations at generation time

### TaskCreated Hook for Quality Gates

When a task is added to the shared task list, the TaskCreated hook validates:

- Task description is not vague (clarification gate scoring)
- Acceptance criteria are present (mandatory per COS rules)
- Scope is bounded (file list or directory reference)
- Verification commands are included

Exit code 2 blocks task creation if validation fails, forcing the lead to improve the task specification.

### TaskCompleted Hook for Verification

When a teammate marks a task complete, the TaskCompleted hook runs:

- Acceptance criteria commands are executed
- DoD criteria for the task's complexity level are checked
- Trust Report is present in the teammate's output
- Claim validation (files claimed as created/modified actually exist)

Exit code 2 rejects the completion and returns the task to in-progress status with feedback.

## When to Use Agent Teams vs Subagents

| Scenario | Use | Why |
|----------|-----|-----|
| Quick file read or analysis | Subagent | Cheaper (1x cost), faster startup |
| Single-file bug fix | Subagent | No benefit from parallelism |
| Sequential dependent tasks | Subagent | Tasks must run in order; teams add overhead |
| Implement 5+ independent features | Agent Teams | True parallelism; teammates self-coordinate |
| Research a topic from multiple angles | Agent Teams | Different contexts enable diverse perspectives |
| Security audit + simultaneous implementation | Agent Teams | One teammate audits while another implements |
| Large refactor across many files | Agent Teams | Divide files among teammates; lateral coordination |
| SDD pipeline (propose-spec-design-tasks) | Subagent | Sequential phases with dependencies |
| SDD apply phase with 10+ independent tasks | Agent Teams | Parallel implementation of independent task items |
| Multi-service integration testing | Agent Teams | Each teammate handles one service |

## Configuration

Full `.claude/settings.json` example with Agent Teams enabled and COS hooks:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "hooks": {
    "SubagentStart": [
      {
        "command": "bash hooks/agent-preamble-inject.sh",
        "timeout": 5000
      }
    ],
    "TaskCreated": [
      {
        "command": "bash hooks/task-quality-gate.sh",
        "timeout": 3000
      }
    ],
    "TaskCompleted": [
      {
        "command": "bash hooks/task-completion-gate.sh",
        "timeout": 10000
      }
    ],
    "TeammateIdle": [
      {
        "command": "bash hooks/teammate-idle-handler.sh",
        "timeout": 3000
      }
    ],
    "PreToolUse": [
      {
        "command": "bash hooks/secret-detector.sh",
        "timeout": 1000
      },
      {
        "command": "bash hooks/rate-limiter.sh",
        "timeout": 1000
      }
    ],
    "PostToolUse": [
      {
        "command": "bash hooks/content-policy.sh",
        "timeout": 2000
      },
      {
        "command": "bash hooks/error-pipeline.sh",
        "timeout": 2000
      }
    ]
  }
}
```

## Hooks Reference

### TeammateIdle

Fires when a teammate is about to go idle (no more tasks to claim).

| Property | Value |
|----------|-------|
| When | Teammate has no more tasks and would shut down |
| Exit 0 | Allow teammate to go idle |
| Exit 2 | Keep teammate working (assign more tasks or redirect) |

COS integration: Check if there are remaining tasks in active-tasks.json that could be reassigned. If the teammate has capacity, redirect to help other teammates or pick up pending work.

### TaskCreated

Fires when a new task is added to the shared task list.

| Property | Value |
|----------|-------|
| When | Lead or teammate creates a task |
| Exit 0 | Allow task creation |
| Exit 2 | Block task creation (validation failed) |

COS integration: Run clarification gate scoring on the task description. Verify acceptance criteria are present. Check that the task scope does not exceed blast radius thresholds.

### TaskCompleted

Fires when a teammate marks a task as done.

| Property | Value |
|----------|-------|
| When | Teammate claims task completion |
| Exit 0 | Accept completion |
| Exit 2 | Reject completion (criteria not met) |

COS integration: Execute acceptance criteria verification commands. Check DoD criteria for the task complexity level. Validate the Trust Report. Run claim validation on reported file changes.

## Limitations

These are known limitations of the Agent Teams feature as of March 2026:

| Limitation | Impact | Workaround |
|------------|--------|------------|
| No session resumption with in-process teammates | If the session ends, team state is lost | Save progress to Engram frequently; use `mem_session_summary` |
| Task status can lag | Teammates sometimes fail to mark tasks complete | TaskCompleted hook validates state; periodic status reconciliation |
| One team per session | Cannot run multiple teams simultaneously | Use separate Claude Code sessions for separate teams |
| Lead is fixed | Cannot transfer leadership mid-session | Plan the lead's role carefully before starting |
| No /resume or /rewind support | Cannot resume a team after session interruption | COS crash recovery (auto-checkpoint) mitigates data loss |
| No nested teams | A teammate cannot create its own sub-team | Use subagents within a teammate for further delegation |
| Higher token cost | 3-5x cost vs subagents due to independent contexts | Use Agent Teams only when parallelism justifies the cost |
| No built-in rate limiting | Token spend can escalate quickly | COS rate limiter counts each teammate as an agent launch |
| No built-in escalation | Stuck teammates spin without asking for help | COS agent-escalation protocol applies via preamble injection |

## Cost Implications

Agent Teams multiplies token consumption because each teammate maintains an independent full context window.

| Team Size | Approximate Cost Multiplier | When Justified |
|-----------|-----------------------------|----------------|
| Lead + 1 teammate | 2x | Rarely (subagent is cheaper) |
| Lead + 2 teammates | 3x | Moderate parallelism needs |
| Lead + 3 teammates | 4x | Recommended default for parallel work |
| Lead + 5 teammates | 6x | Large independent task sets (10+ tasks) |
| Lead + 10 teammates | 11x | Exceptional cases only |

### COS Budget Governance

- Each teammate counts against `max_agent_launches_per_hour` in rate-limiter
- Total team cost counts against `daily_alert_usd` and `monthly_limit_usd`
- Model downgrade chain applies: if budget pressure detected, teammates use sonnet instead of opus
- WorkloadScheduler should plan team size based on available budget headroom

## Best Practices

### Team Sizing

- **3-5 teammates** is the recommended range for most tasks
- Assign **5-6 tasks per teammate** to keep them productive
- More teammates does not always mean faster completion (coordination overhead)

### Task Design

- **One file per teammate**: Avoid assigning the same file to multiple teammates to prevent merge conflicts
- **Independent tasks**: Tasks should be completable without waiting for other teammates
- **Clear acceptance criteria**: Every task must have verifiable completion criteria (COS enforces this via TaskCreated hook)
- **Bounded scope**: Each task should touch a known set of files

### Communication

- Start with a **research phase**: Have teammates explore different parts of the codebase before implementation
- Use **broadcasts** for decisions that affect all teammates
- Teammates should save discoveries to **Engram** so other teammates (and future sessions) benefit

### COS-Specific Practices

- **Inject preamble via SubagentStart**: Every teammate gets the COS agent preamble with progress markers and quality standards
- **Enable Engram for all teammates**: All teammates should call `mem_save` for decisions and discoveries
- **Use TaskCompleted hook for DoD**: Do not rely on teammates self-reporting completion; validate with the hook
- **Monitor cost**: Check budget dashboard mid-session when running large teams
- **Save session summary**: Before the team session ends, the lead should call `mem_session_summary` with the full team's accomplishments
- **Phase-aware team behavior**: In production/maintenance phases, prefer smaller teams with stricter quality gates
