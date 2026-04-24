<!-- SCOPE: both -->
# Repomix Integration — Repository Context Packing

## Purpose

Repomix packs entire repositories into single AI-friendly files with tree-sitter compression (~70% token reduction). Integrated as an optional tool for repo analysis, deep research, and repo-scout tasks.

## Installation

```bash
npm install -g repomix
# or
npx repomix
```

## Usage

### As CLI Tool
```bash
# Pack current repo for AI consumption
repomix

# Pack with compression (signatures only, no implementations)
repomix --compress

# Pack specific paths
repomix --include "src/**/*.ts" --exclude "node_modules"

# Output token count tree
repomix --token-count-tree
```

### As MCP Server
```bash
repomix --mcp
```

Add to `.claude/settings.json`:
```json
{
  "mcpServers": {
    "repomix": {
      "command": "npx",
      "args": ["-y", "repomix", "--mcp"]
    }
  }
}
```

## Integration with Cognitive OS

| Skill | How Repomix Helps |
|---|---|
| `/repo-scout` | Pack external repos for analysis without cloning |
| `/deep-research` | Compress large codebases into digestible context |
| `/sdd-explore` | Quick project overview via token count tree |
| Context optimization | Tree-sitter compression reduces context window usage |

## Configuration

In `cognitive-os.yaml`:
```yaml
tools:
  repomix:
    enabled: true
    default_compress: true  # Use tree-sitter compression by default
    max_tokens: 50000       # Limit output size
```

## Graceful Degradation

If Repomix is not installed, skills fall back to our existing file reading patterns (Glob + Read with targeted paths). Repomix is an optimization, not a requirement.
