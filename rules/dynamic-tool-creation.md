<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Dynamic Tool Creation -- Mid-Task Tool Generation

## Purpose

Agents can create lightweight tools DURING execution when they encounter capability gaps or repetitive patterns. Unlike auto-skill-generation (post-hoc, after task completion), dynamic tool creation happens mid-task so the agent can use the tool immediately.

Inspired by Agent Zero's mid-conversation plugin creation pattern.

## When Agents Should Create Dynamic Tools

| Signal | Threshold | Action |
|--------|-----------|--------|
| Repetitive pattern | Same bash command or code pattern executed 3+ times | Create a bash or python tool that encapsulates the pattern |
| Capability gap | Agent needs a tool that does not exist | Create a minimal tool that fills the gap |
| Complex pipeline | Multi-step process that will be repeated | Wrap in a single-invocation tool |
| Data transformation | Same data format conversion applied to multiple files | Create a transformation tool |

## When NOT to Create Dynamic Tools

| Situation | Why Not |
|-----------|---------|
| One-time operation | Not worth the overhead of tool creation |
| Security-sensitive operation | Dynamic tools bypass the normal skill review process |
| Existing skill covers the need | Use the existing skill instead |
| Trivial command (< 5 chars) | Direct execution is simpler |

## Tool Types

| Type | Extension | Use Case | Invocation |
|------|-----------|----------|------------|
| `bash` | `.sh` | Shell commands, file operations, git workflows | `bash .cognitive-os/dynamic-tools/{name}.sh` |
| `python` | `.py` | Data processing, API calls, complex logic | `python .cognitive-os/dynamic-tools/{name}.py` |
| `skill` | `SKILL.md` | Reusable multi-step procedures for other agents | Load as skill context |

## Tool Lifecycle

```
Agent detects pattern/gap
    |
    v
Agent calls DynamicToolCreator.create_tool()
    |
    v
Tool saved to .cognitive-os/dynamic-tools/{slug}.{ext}
    |
    v
Agent uses tool immediately in current task
    |
    v
Tool usage tracked in registry.json
    |
    v (session end)
cleanup_session_tools() removes ephemeral tools
    |
    v (if valuable)
promote_to_skill() copies to skills/auto-generated/
```

## Directory Structure

```
.cognitive-os/dynamic-tools/
    registry.json           # Tool metadata and usage tracking
    json-validator.sh       # Bash tool example
    csv-transformer.py      # Python tool example
    api-health-check/       # Skill tool example
        SKILL.md
```

The `dynamic-tools/` directory is gitignored (session-scoped). Tools that prove valuable are promoted to `skills/auto-generated/` which is also gitignored but more persistent.

## Agent Protocol

### Creating a Tool

When an agent detects a repetitive pattern (3+ occurrences) or a capability gap:

1. Check if a dynamic tool already exists: `creator.get_tool(name)`
2. If not, create it: `creator.create_tool(name, description, implementation, type)`
3. Use the tool immediately via Bash or Python execution
4. Record usage: `creator.record_usage(name)` after each use

### Using a Dynamic Tool

```python
from lib.dynamic_tool_creator import DynamicToolCreator

creator = DynamicToolCreator(project_root=".")

# Check available tools
tools = creator.list_dynamic_tools()

# Create a tool when a gap is detected
result = creator.create_tool(
    name="validate-json-schema",
    description="Validate JSON files against a schema",
    implementation='python3 -c "import json, sys; json.load(open(sys.argv[1]))" "$@"',
    tool_type="bash"
)

# Use it
# bash .cognitive-os/dynamic-tools/validate-json-schema.sh myfile.json
```

### Promoting a Tool

If a dynamic tool was used 3+ times and proved valuable:

```python
skill_path = creator.promote_to_skill("validate-json-schema")
# Tool is now at skills/auto-generated/validate-json-schema/SKILL.md
```

## Safety Boundaries

Dynamic tools MUST NOT:

| Prohibited | Why |
|------------|-----|
| Access `.env`, `*.key`, `*.pem`, `secrets/*` | Credential safety (per agent-security.md) |
| Modify hooks, rules, or core OS files | Integrity of the safety mesh |
| Execute network requests without user awareness | Data exfiltration risk |
| Self-modify or create recursive tool chains | Unbounded execution risk |
| Bypass any existing security hooks | Security hooks remain active on all tool calls |

## Integration with Existing Systems

| System | Integration |
|--------|-------------|
| Auto-Skill Generation (`auto-skill-generation.md`) | Post-hoc generation remains for complex tasks. Dynamic tools are lighter and mid-task. Promoted dynamic tools go to the same `skills/auto-generated/` directory. |
| Skill Router (`lib/skill_router.py`) | Dynamic tools are NOT routed by the skill router. They are invoked directly by the agent that created them. |
| Agent Security (`agent-security.md`) | Dynamic tool execution goes through normal Bash/Python tool calls, so all PreToolUse/PostToolUse hooks still apply. |
| Error Learning (`error-learning.md`) | Failures in dynamic tools are captured by the error-learning pipeline like any other command. |
| Session Concurrency (`session-concurrency.md`) | Dynamic tools are session-scoped. Each session has its own tools directory contents. The registry.json prevents conflicts. |

## Metrics

Tool creation and usage events are logged to `.cognitive-os/dynamic-tools/registry.json` with:
- Tool name, type, description
- Creation timestamp and session ID
- Usage count and last-used timestamp
- Promotion status

At session end, a summary can be logged to `.cognitive-os/metrics/dynamic-tools.jsonl`:

```json
{
  "timestamp": "ISO-8601",
  "session_id": "session-123",
  "tools_created": 3,
  "tools_used": 2,
  "total_usages": 7,
  "tools_promoted": 1,
  "tools_cleaned": 2
}
```

## Relationship to Auto-Skill Generation

| Aspect | Auto-Skill Generation | Dynamic Tool Creation |
|--------|----------------------|----------------------|
| When | After task completes | During task execution |
| Trigger | Complex task (10+ tool uses) | Repetitive pattern or capability gap |
| Output | Full SKILL.md | Lightweight script or stub |
| Persistence | Session-scoped (gitignored) | Session-scoped (gitignored) |
| Promotion | Already a skill | Can be promoted to skill |
| Availability | Next session | Immediately |

## Contextual Trigger

This rule is loaded when: dynamic tool, mid-task tool creation, create tool on the fly, capability gap, repetitive pattern detection.
