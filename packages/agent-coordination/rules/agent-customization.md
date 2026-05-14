<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Agent Customization via Override Files (BMAD v6 Pattern 9)

## Purpose

Allow per-agent behavioral overrides without modifying base agent definitions. Customizations are isolated in `.cognitive-os/customizations/` and survive Cognitive OS updates.

## Override Mechanism

### File Location

```
.cognitive-os/customizations/{agent-name}.yaml
```

Where `{agent-name}` matches the agent definition filename in `.cognitive-os/agents/`.

### Override Fields

| Field | Type | Description |
|-------|------|-------------|
| `model` | string | Override the model used for this agent (`opus`, `sonnet`, `haiku`) |
| `temperature` | float | Override temperature (0.0 - 1.0) |
| `max_tokens` | int | Override max output tokens |
| `tools_allowed` | list | Restrict which tools this agent can use |
| `tools_blocked` | list | Block specific tools for this agent |
| `skills_loaded` | list | Skills to pre-load when this agent launches |
| `phase_behavior` | map | Override phase-specific behavior |
| `halt_triggers` | list | Additional HALT triggers specific to this agent |
| `max_retries` | int | Override closed-loop retry limit |
| `budget_limit_usd` | float | Per-invocation budget cap for this agent |
| `context_priority` | list | Engram topic prefixes to pre-load for this agent |
| `custom_instructions` | string | Additional instructions appended to agent prompt |

### Deep Merge Semantics

Customizations overlay on top of the base agent definition using deep merge:

1. **Scalar fields** (model, temperature, max_tokens, max_retries, budget_limit_usd): override replaces base value
2. **List fields** (tools_allowed, skills_loaded, halt_triggers, context_priority): customization list REPLACES base list (not appended)
3. **Map fields** (phase_behavior): keys in customization override matching keys in base; non-matching keys from base are preserved
4. **tools_blocked**: always appended to any existing blocks (additive, never removed)

### Merge Order

```
Base Agent Definition (agents/{agent-name}.yaml)
  └── + Customization Override (customizations/{agent-name}.yaml)
       └── + Phase Override (from phase_behavior matching current phase)
            └── = Final Agent Configuration
```

## Tool Group References

The `tools_allowed` and `tools_blocked` fields support a `group:` prefix that expands to tool groups defined in `cognitive-os.yaml` under `tool_groups`:

```yaml
# In cognitive-os.yaml:
tool_groups:
  fs: [Read, Write, Edit, Glob, Grep]
  runtime: [Bash, Agent]
  web: [WebSearch, WebFetch]
  git: [Bash]
  readonly: [Read, Glob, Grep, WebSearch, WebFetch]
  minimal: [Read, Glob, Grep]
  coding: [Read, Write, Edit, Glob, Grep, Bash, Agent]
  full: [Read, Write, Edit, Glob, Grep, Bash, Agent, WebSearch, WebFetch]
```

```yaml
# In customizations/my-agent.yaml:
tools_allowed: ["group:coding"]     # Expands to all tools in the coding group
tools_blocked: ["group:web"]        # Blocks all web tools
```

### Group Expansion Rules

1. Entries with `group:` prefix are expanded at load time by replacing the entry with all tools in the named group
2. Non-prefixed entries are kept as-is (individual tool names)
3. Mixed lists are supported: `["group:fs", "Bash"]` expands to `[Read, Write, Edit, Glob, Grep, Bash]`
4. Unknown group names log a warning and are silently dropped
5. Duplicates from expansion are deduplicated (preserving order)

## Rules

### Customizations Are Optional

If no customization file exists for an agent, the base definition is used as-is. No error.

### Customizations Survive Updates

The `customizations/` directory is NOT part of the generated Cognitive OS. It persists across:
- Cognitive OS version upgrades
- Agent definition regeneration
- Skill catalog rebuilds

### Validation

When a customization file is loaded:
1. Verify all referenced tools exist
2. Verify all referenced skills exist in CATALOG.md
3. Verify model name is valid (`opus`, `sonnet`, `haiku`, or full model ID)
4. Verify budget_limit_usd does not exceed per_agent_max_usd from cognitive-os.yaml
5. Log a warning for unknown fields (future-proofing, not an error)

### Loading

The orchestrator loads customizations at agent launch time:
1. Read base agent definition from `agents/{agent-name}.yaml`
2. Check for `customizations/{agent-name}.yaml`
3. If exists: deep merge customization onto base
4. Apply phase-specific overrides from merged config
5. Launch agent with final configuration

## Configuration

In `cognitive-os.yaml`, add under a new `customization` key:

```yaml
customization:
  enabled: true
  directory: customizations    # relative to .cognitive-os/
  validate_on_load: true       # validate overrides at agent launch
  warn_unknown_fields: true    # log warning for unrecognized fields
```

## Contextual Trigger

- When work relates to Agent Customization via Override Files (BMAD v6 Pattern 9).
