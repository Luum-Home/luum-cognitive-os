# @luum/aguara-security

Aguara AI agent security scanner integration for Cognitive OS.

## What

Integrates [aguara](https://github.com/garagon/aguara) (189-rule deterministic security scanner) and [mcp-aguara](https://github.com/garagon/mcp-aguara) (MCP server) into the Cognitive OS security stack.

## Install

```bash
bash scripts/install-aguara.sh
```

## Components

- `hooks/aguara-scan.sh` -- PreToolUse hook scanning agent prompts before execution
- `rules/aguara-integration.md` -- Full integration documentation
- MCP server config documented in rules for optional registration

## License

Apache-2.0
