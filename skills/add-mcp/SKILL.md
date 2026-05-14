<!-- SCOPE: both -->
---
name: add-mcp
description: 'Use when you need this Cognitive OS skill: Step-by-step guide for integrating a new MCP server into the Cognitive
  OS; do not use when a narrower skill directly matches the task.'
version: 0.1.0
audience: os
tags:
- development
- extension
- mcp
- integrations
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \badd[- ]?mcp\b
  confidence: 0.95
- pattern: \bintegrat\w*\s+(a\s+)?mcp\s+server\b
  confidence: 0.85
- pattern: \bnew\s+mcp\s+(server|integration)\b
  confidence: 0.75
summary_line: Step-by-step guide for integrating a new MCP server into the Cognitive OS.
routing_intents:
- intent: add_mcp_request
  description: User asks to step-by-step guide for integrating a new MCP server into the Cognitive OS.
  confidence: 0.85
---

# Add MCP Server

> Procedure for integrating a new MCP server so its tools are available to agents.

## Trigger

When you need to give Claude access to a new external capability via the Model Context Protocol.

## Inputs

- **MCP server name**: identifier for the server (e.g., `my-service`)
- **Tools provided**: list of tool names the server exposes
- **Install command**: how to install the server (npm package, binary, npx, etc.)
- **Activation condition**: always-on, or opt-in via env var

## Steps

### 1. Install the MCP server

Install the server binary or package:

```bash
# npm package (global install)
npm install -g @scope/mcp-server-name

# npx (zero-install, runs on demand)
npx -y @scope/mcp-server-name

# Go binary
go install github.com/org/mcp-server@latest

# Homebrew
brew install org/tap/mcp-server
```

If no API key or credentials are needed, skip to step 2. If credentials are required:
- Store in environment variable (never hardcoded)
- Reference as `${ENV_VAR_NAME}` in the config (see step 2)
- Document the env var name in step 4

### 2. Register in `.claude/settings.json` under `mcpServers`

Add the server configuration:

```json
{
  "mcpServers": {
    "{mcp-server-name}": {
      "command": "npx",
      "args": ["-y", "@scope/mcp-server-name"],
      "env": {
        "API_KEY": "${MY_SERVICE_API_KEY}"
      }
    }
  }
}
```

For a binary (not npx):
```json
{
  "mcpServers": {
    "{mcp-server-name}": {
      "command": "mcp-server-binary",
      "args": ["--flag", "value"]
    }
  }
}
```

Note: Register in `.claude/settings.json` (project-level) for project-scoped MCP servers, or in `~/.claude/settings.json` (user-level) for servers available in all projects.

### 3. Document in `packages/ecosystem-tools/rules/ecosystem-tools.md`

Add a new entry in the "Integrated Tools" section:

```markdown
### {Service Name} — {Brief Purpose}

| Property | Value |
|----------|-------|
| Purpose | {What the MCP server does} |
| Install | `{install command}` |
| Required | No (optional, graceful skip if missing) |
| Scope | {What it operates on} |
| License | {License type} |
| Status | **ADOPT** / **EVALUATE** / **WATCH** |

**Usage examples**:
```bash
# Example invocation
```

**Tools provided**:
| Tool | Purpose |
|------|---------|
| `tool_name_1` | Description |
| `tool_name_2` | Description |
```

### 4. Add graceful degradation (if the server is optional)

If the MCP server is optional (not required for core OS function), document the fallback behavior. For hooks that use the server's tools, add a silent skip guard:

```bash
# In any hook or script that calls the MCP server
if ! command -v mcp-server-binary &>/dev/null; then
    # Server not installed — skip silently
    exit 0
fi
```

For optional servers, set `Required: No` in the ecosystem-tools.md entry.

### 5. Document required environment variables

If the server needs API keys or credentials, document them:

- Add to `docs/environment-variables.md` (if the file exists) or note in the ecosystem-tools.md entry
- Add example to `.env.example` if the project has one:
  ```bash
  # Required for {MCP server name} integration
  MY_SERVICE_API_KEY=your_key_here
  ```
- Follow `rules/credential-management.md`: never hardcode values, always use `${ENV_VAR}` references

### 6. Verify the integration

Restart Claude Code and verify the server loads:

```bash
# Check Claude Code loads the MCP server without errors
# (Restart is required for settings.json changes to take effect)
```

After restart, the tools from the MCP server should be available. Test with a simple invocation:

```
# In Claude Code: try calling one of the documented tools
```

## MCP Server Types Reference

| Type | Examples | Config notes |
|------|----------|-------------|
| Memory/knowledge | Engram, Context7 | Usually plugin-based |
| Documentation | Context7 | Per-library doc lookup |
| API connectors | GitHub, Jira, Slack | Require API credentials |
| Development tools | E2B sandbox, mcp-aguara | Require install |
| File management | Google Drive, Notion | Require OAuth setup |

## Output: Configured MCP Server

- `.claude/settings.json` — updated `mcpServers` section
- `packages/ecosystem-tools/rules/ecosystem-tools.md` — documented entry
- Graceful degradation added (if optional server)
- Environment variables documented

## Success Criteria

- [ ] Server listed in `.claude/settings.json` under `mcpServers`
- [ ] `grep "{mcp-server-name}" packages/ecosystem-tools/rules/ecosystem-tools.md` returns a match
- [ ] If credentials needed: `${ENV_VAR}` syntax used (not hardcoded values)
- [ ] After Claude Code restart: no errors about the MCP server in session start output
- [ ] If optional: graceful skip guard present in any hook that uses the server
