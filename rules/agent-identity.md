<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Agent Identity Protocol

## Agent Identification

Every agent (sub-agent, skill, hook) must be identifiable:

- **Agent name**: from description or skill name
- **Agent type**: executor, coordinator, validator, SRE
- **Session ID**: from active-tasks.json
- **Parent agent**: who spawned it

## Audit Trail

Every agent action is logged with:

- **WHO**: agent name + type
- **WHAT**: tool used + args summary
- **WHEN**: timestamp
- **WHERE**: service/file affected
- **WHY**: task description

## Credential Rules

- Agents NEVER see real API keys (future: OneCLI vault)
- Each agent has scoped permissions (future: Cerbos policies)
- Credential rotation tracked in Engram
- Placeholder tokens used in config; real values injected at runtime

## Trust Levels

| Level | Name | Description | Access |
|-------|------|-------------|--------|
| 0 | Untrusted | New/unknown agent | No write access |
| 1 | Basic | Orchestrator-spawned | Read + write with approval |
| 2 | Trusted | Known skill with history | Auto-approve safe actions |
| 3 | Verified | Cryptographically signed | Full autonomy within scope |

## Delegation Rules

- Sub-agents inherit AT MOST the permissions of their parent (monotonic attenuation)
- Permissions can only narrow when delegated, never expand
- The orchestrator defines the maximum permission boundary for any session
- Future: Agent Passport DCTs enforce this cryptographically

## Identity in Sub-Agent Prompts

When the orchestrator spawns a sub-agent, the launch prompt SHOULD include:

```
Identity: {agent-name} ({agent-type})
Parent: {parent-agent-name}
Session: {session-id}
Trust Level: {0-3}
Allowed Tools: {list of MCP tools this agent may use}
```

## Future Integration Points

| Tool | Purpose | Phase |
|------|---------|-------|
| AIM (OpenA2A) | Cryptographic identity (Ed25519 + post-quantum) | Phase 3 |
| OneCLI | Runtime credential injection | Phase 2 |
| Cerbos | YAML-based permission policies | Phase 2 |
| A2A Agent Cards | Cross-agent discovery via /.well-known/agent.json | Phase 3 |
| Agent Passport | Delegation Capability Tokens (DCTs) | Phase 2 |
| SPIFFE/SPIRE | Infrastructure workload identity (X.509 SVIDs) | Phase 3 |

See `docs/cognitive-os/identity-stack.md` for full architecture details.

## Contextual Trigger

- When work relates to Agent Identity Protocol.
