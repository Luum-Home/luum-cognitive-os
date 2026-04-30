<!-- TIER: 2 -->
<!-- SCOPE: both -->
# E2B Sandbox -- Secure Agent Code Execution

## Overview

E2B provides Firecracker microVM sandboxes for safe code execution by AI agents. Instead of running agent-generated code directly on the host machine, E2B isolates execution in ephemeral sandboxes with controlled filesystem access, network egress filtering, and automatic cleanup.

The E2B MCP server (`@e2b/mcp-server`) exposes sandbox capabilities as MCP tools that agents can invoke for code execution, file operations, and sandbox lifecycle management.

## Installation

```bash
# E2B MCP server (runs via npx, no global install needed)
npx -y @e2b/mcp-server

# Or install globally
npm install -g @e2b/mcp-server
```

An E2B API key is required. Sign up at [e2b.dev](https://e2b.dev) and set the environment variable:

```bash
export E2B_API_KEY=your_api_key_here
```

## MCP Server Configuration

Add to `.claude/settings.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "e2b": {
      "command": "npx",
      "args": ["-y", "@e2b/mcp-server"],
      "env": {
        "E2B_API_KEY": "${E2B_API_KEY}"
      }
    }
  }
}
```

## Available MCP Tools

The E2B MCP server provides approximately 15 tools across three categories:

### Sandbox Lifecycle

| Tool | Purpose |
|------|---------|
| `e2b_create_sandbox` | Create a new sandbox with configurable timeout and template |
| `e2b_kill_sandbox` | Terminate a running sandbox |
| Pause/Resume/List | Manage sandbox lifecycle across sessions |

### Code Execution

| Tool | Purpose |
|------|---------|
| `e2b_execute_code` | Execute Python code in an isolated sandbox |
| `e2b_create_code_context` | Create a persistent execution context (shared variables) |
| `e2b_execute_in_context` | Execute code within a persistent context |

### File Operations

| Tool | Purpose |
|------|---------|
| `e2b_read_file` | Read file content from sandbox filesystem |
| `e2b_download_file` | Download file from sandbox to local or return content |
| `e2b_watch_directory` | Monitor directory for filesystem events |

## Integration with Cognitive OS

### When to Use E2B Sandboxes

| Scenario | Use E2B? | Why |
|----------|----------|-----|
| Running agent-generated code | Yes | Prevents host compromise from malicious or buggy code |
| Data analysis with untrusted data | Yes | Isolates data processing from host filesystem |
| Testing code changes before commit | Yes | Validates behavior without polluting host environment |
| Running trusted project tests | No | Use host execution (faster, no API cost) |
| Simple file edits | No | No execution involved |
| Reading/searching code | No | Read-only operations are safe on host |
| Running build commands for known projects | No | Trusted toolchain on host is faster |

### SDD Pipeline Integration

E2B sandboxes can be used in the `sdd-apply` and `sdd-verify` phases:

1. **sdd-apply**: When generating code that needs runtime validation, execute in sandbox first
2. **sdd-verify**: Run generated tests in sandbox to verify correctness before committing
3. **Eval tasks**: Use sandboxes for `/repo-scout` when evaluating untrusted external repositories

### Security Model

| Threat | E2B Mitigation |
|--------|----------------|
| Agent runs `rm -rf /` | Sandbox filesystem only; host unaffected |
| Agent exfiltrates secrets via code | Sandbox has no access to host env vars or `.env` files |
| Agent installs malicious packages | Sandbox is ephemeral; destroyed after use |
| Agent opens reverse shell | Network egress can be filtered per sandbox template |
| Agent consumes excessive resources | Sandbox timeout and resource limits enforced by E2B |

### Credential Handling

The `E2B_API_KEY` must be set as an environment variable. It is passed to the MCP server via the `env` field in `settings.json`. The key is never exposed to sub-agents or written to files.

Follow `rules/credential-management.md`: never hardcode the API key in source files or commit it to version control.

## Configuration

In `cognitive-os.yaml` (optional):

```yaml
sandbox:
  e2b:
    enabled: false              # Set to true after configuring E2B_API_KEY
    default_timeout_seconds: 300 # Sandbox auto-termination
    template: "base"            # Default sandbox template
    auto_sandbox_untrusted: true # Auto-use sandbox for untrusted code execution
```

## Graceful Degradation

If E2B is not configured or `E2B_API_KEY` is not set, code execution falls back to host execution (current behavior). E2B sandboxing is an optional security enhancement, not a requirement.

When the MCP server is unavailable:
- Agent-generated code runs on host as before
- A warning is logged if `auto_sandbox_untrusted` is enabled but E2B is unreachable
- No workflow is blocked

## Cost Considerations

E2B sandbox usage incurs API costs. Each sandbox creation and execution time is billed. For cost-sensitive workflows:
- Reuse sandbox sessions (create once, execute multiple times via contexts)
- Set appropriate timeouts to avoid idle sandbox charges
- Use host execution for trusted operations (project builds, linting)

## Comparison with Other Sandboxing Approaches

| Approach | Isolation Level | Speed | Cost | Setup |
|----------|----------------|-------|------|-------|
| E2B (Firecracker microVM) | High (VM-level) | ~2-5s startup | Per-use API | API key only |
| Docker containers | Medium (container-level) | ~1-3s startup | Self-hosted | Docker required |
| Host execution | None | Instant | Free | None |
| Jupyter sandbox | Low (process-level) | ~1s | Self-hosted | Jupyter required |

E2B provides the strongest isolation with the simplest setup (no Docker or infrastructure required).

## Contextual Trigger

This rule is loaded when: e2b, sandbox, safe execution, isolated execution, code sandbox, microvm, firecracker, untrusted code.
