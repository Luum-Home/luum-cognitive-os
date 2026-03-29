# Cognitive OS MCP Server

Exposes Cognitive OS knowledge (Engram memory, task state, rules, metrics, quality checks) as MCP tools. This makes COS accessible from **any MCP-compatible editor** — VS Code, Cursor, Windsurf, and others — not just Claude Code.

## Requirements

- Python 3.10+
- `fastmcp` (`pip install fastmcp`)
- Optional: `PyYAML` for full cognitive-os.yaml parsing
- Optional: `engram` for memory search/save functionality

## Installation

```bash
pip install fastmcp pyyaml
```

## Configuration

Add to your editor's MCP configuration. For Claude Code, add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "cos": {
      "command": "python",
      "args": ["mcp-server/cos_mcp.py"],
      "cwd": "/path/to/luum-agent-os"
    }
  }
}
```

For VS Code (with an MCP extension), Cursor, or Windsurf, use the equivalent MCP server configuration format with the same command and args.

## Exposed Tools

| Tool | Description |
|------|-------------|
| `cos_search_memory` | Search Engram for past decisions, discoveries, bugs, patterns |
| `cos_get_tasks` | Get current tasks from active-tasks.json with status filtering |
| `cos_get_rules` | Find relevant COS rules by context (uses contextual triggers) |
| `cos_check_quality` | Run quality checks: prohibited terms, credential leaks, TODOs, stubs |
| `cos_get_metrics` | Get session metrics: trust scores, error rates, cost, KPIs |
| `cos_suggest_skill` | Suggest the best COS skill for a given task description |
| `cos_save_memory` | Save an observation to Engram persistent memory |
| `cos_status` | Get COS installation status: phase, rules, hooks, skills, packages |

## Tool Details

### cos_search_memory

Search past decisions, bug fixes, and discoveries stored in Engram.

```
cos_search_memory(query="JWT authentication", project="my-project", limit=5)
```

### cos_get_tasks

View current task state. Filter by status: `all`, `pending`, `in_progress`, `completed`, `failed`.

```
cos_get_tasks(status="in_progress")
```

### cos_get_rules

Find relevant COS rules for your current work context. Uses the contextual trigger system from `cognitive-os.yaml`.

```
cos_get_rules(context="security audit credentials")
```

### cos_check_quality

Run quality gates on code before committing. Checks content policy, credential leaks, TODO comments, stub implementations, and dead code blocks.

```
cos_check_quality(code="api_key = 'sk-abc123...'", file_path="config.py")
```

Returns findings with severity levels: BLOCKER, CONCERN, SUGGESTION.

### cos_get_metrics

Access COS metrics. Filter by type: `all`, `errors`, `trust`, `cost`, `kpis`, `skills`.

```
cos_get_metrics(metric_type="errors")
```

### cos_suggest_skill

Get skill recommendations for a task. Uses the skill routing table from `lib/skill_router.py`.

```
cos_suggest_skill(message="investigate this GitHub repo for security issues")
```

### cos_save_memory

Persist important decisions and discoveries to Engram for future sessions.

```
cos_save_memory(
    title="Switched from REST to GraphQL",
    content="**What**: Migrated user API to GraphQL\n**Why**: Reduce over-fetching on mobile",
    type="decision",
    project="my-project"
)
```

### cos_status

Get a snapshot of the COS installation: project phase, component counts, active tasks, and metrics summary.

```
cos_status()
```

## Graceful Degradation

The server works even when optional dependencies are missing:

- **Without Engram**: `cos_search_memory` and `cos_save_memory` return informative error messages
- **Without PyYAML**: `cos_get_rules` and `cos_status` have reduced functionality
- **Without lib/skill_router.py**: `cos_suggest_skill` falls back to keyword matching against CATALOG.md
- **Without metrics files**: `cos_get_metrics` reports which files are available

## Architecture

```
mcp-server/cos_mcp.py
    |
    +-- FastMCP server (stdio transport)
    |
    +-- lib/skill_router.py (skill suggestions)
    +-- lib/prompt_classifier.py (prompt classification)
    +-- .cognitive-os/content-policy.yaml (quality checks)
    +-- .cognitive-os/metrics/*.jsonl (metrics data)
    +-- .cognitive-os/tasks/active-tasks.json (task state)
    +-- cognitive-os.yaml (config, phase, contextual triggers)
    +-- Engram CLI/API (persistent memory)
```

## Running Standalone

For testing:

```bash
cd /path/to/luum-agent-os
python mcp-server/cos_mcp.py
```

The server communicates via stdio (standard MCP transport).
