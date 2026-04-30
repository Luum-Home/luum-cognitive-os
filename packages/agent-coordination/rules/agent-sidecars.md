<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Agent Sidecars via Engram (BMAD v6 Pattern 4)

## Purpose

Each agent accumulates learnings, preferences, and frequently-used patterns across sessions. These are stored as "sidecars" in engram and injected on agent launch to provide continuity.

## Engram Topic Key Convention

```
agent/{agent-name}/sidecar
```

Examples:
- `agent/code-reviewer/sidecar`
- `agent/test-coverage-enforcer/sidecar`
- `agent/stack-validator/sidecar`
- `agent/sdd-verify/sidecar`

## Sidecar Content Structure

Each sidecar observation follows this format:

```markdown
# Agent Sidecar: {agent-name}

## Learnings
- {discovery or lesson learned from past runs}

## Preferences
- {preferred patterns, tools, or approaches this agent uses}

## Frequent Patterns
- {code patterns, file locations, or conventions this agent encounters often}

## Known Issues
- {recurring problems or edge cases this agent has encountered}

## Performance Notes
- {what makes this agent faster or slower, token usage observations}
```

## Orchestrator Responsibilities

### On Agent Launch

1. Search engram for the agent's sidecar:
   ```
   mem_search(query: "agent/{agent-name}/sidecar", project: "{project}")
   ```
2. If found, retrieve full content:
   ```
   mem_get_observation(id: {id})
   ```
3. Inject relevant sidecar content into the sub-agent's launch prompt:
   ```
   SIDECAR CONTEXT (from previous sessions):
   {sidecar content}
   ```

### Sidecar Injection Rules

- Only inject sidecar content that is relevant to the current task
- If the sidecar is too large (> 2000 tokens), summarize key points
- Never inject stale sidecars older than 30 days without flagging them
- If no sidecar exists, proceed without one (first run)

## Agent Responsibilities

### Saving to Sidecar

After completing a task, the agent MUST evaluate if it learned something worth persisting:

1. **New discovery**: A gotcha, edge case, or non-obvious behavior
2. **Pattern confirmation**: A recurring pattern that should be remembered
3. **Performance insight**: Something that affected execution speed or token usage
4. **Tool preference**: A tool or approach that worked better than alternatives

If any of the above apply, save to engram:
```
mem_save(
  title: "Sidecar update: {agent-name} - {brief description}",
  type: "pattern",
  scope: "project",
  topic_key: "agent/{agent-name}/sidecar",
  content: "{updated sidecar content}"
)
```

### Update Rules

- Use the same `topic_key` to upsert (not create duplicates)
- Merge new learnings with existing content, don't overwrite
- Remove outdated entries when the codebase has changed
- Keep sidecars concise: max 30 bullet points across all sections

## Cross-Session Persistence

Sidecars survive across sessions because they use engram persistence. The orchestrator does NOT need to manually export or import them. The engram memory system handles persistence automatically.

## Which Agents Get Sidecars

All agents that run more than once benefit from sidecars. Priority:
1. Review agents (code-reviewer, sdd-verify) -- high value, pattern recognition
2. Implementation agents (sdd-apply) -- learn codebase conventions
3. Planning agents (sdd-propose, sdd-spec) -- learn project preferences
4. Infrastructure agents (stack-validator, sre-agent) -- learn environment quirks
