# @luum/e2b-sandbox

E2B Firecracker microVM sandbox integration for Cognitive OS. Provides secure, isolated code execution for AI agents via the E2B MCP server.

## Why

Agents currently execute code directly on the host machine. This creates security risks: malicious or buggy agent-generated code can access the host filesystem, environment variables, and network. E2B sandboxes isolate execution in ephemeral Firecracker microVMs with controlled access.

## Prerequisites

1. **E2B account**: Sign up at [e2b.dev](https://e2b.dev)
2. **API key**: Set `E2B_API_KEY` environment variable
3. **Node.js**: Required for `npx` to run the MCP server

## Quick Setup

### 1. Set API Key

```bash
export E2B_API_KEY=your_api_key_here
```

Or add to your `.env` file (gitignored):

```
E2B_API_KEY=your_api_key_here
```

### 2. Register MCP Server

Add to `.claude/settings.json`:

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

### 3. Enable in Configuration (Optional)

Add to `cognitive-os.yaml`:

```yaml
sandbox:
  e2b:
    enabled: true
    default_timeout_seconds: 300
    template: "base"
    auto_sandbox_untrusted: true
```

## Available Tools

Once configured, the following MCP tools become available to agents:

| Tool | Description |
|------|-------------|
| `e2b_create_sandbox` | Create an isolated sandbox environment |
| `e2b_kill_sandbox` | Terminate a sandbox |
| `e2b_execute_code` | Execute Python code in sandbox |
| `e2b_create_code_context` | Create persistent execution context |
| `e2b_execute_in_context` | Execute code in persistent context |
| `e2b_read_file` | Read file from sandbox filesystem |
| `e2b_download_file` | Download file from sandbox |
| `e2b_watch_directory` | Monitor directory for changes |

## When to Use

- Running agent-generated code that has not been reviewed
- Executing code from untrusted external repositories (`/eval-repo`)
- Data analysis with untrusted datasets
- Testing code changes before committing to host

## When NOT to Use

- Running trusted project test suites (use host for speed)
- File reading/searching (no execution involved)
- Build commands for known project toolchains

## Graceful Degradation

If E2B is not configured, all code execution falls back to host execution. E2B is an optional security layer. No workflows are blocked by its absence.

## Cost

E2B charges per sandbox creation and execution time. Minimize costs by:
- Reusing sandbox sessions via persistent contexts
- Setting appropriate timeouts
- Using host execution for trusted operations

## Links

- [E2B Documentation](https://e2b.dev/docs)
- [E2B MCP Server (GitHub)](https://github.com/e2b-dev/mcp-server)
- [@e2b/mcp-server (npm)](https://www.npmjs.com/package/@e2b/mcp-server)
- [E2B Pricing](https://e2b.dev/pricing)

## License

Apache-2.0
