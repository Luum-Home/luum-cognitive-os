<!-- TIER: 2 -->
<!-- SCOPE: both -->
# Aguara -- AI Agent Security Scanner

## Overview

Aguara is a deterministic, rule-based security scanner for AI agent skills and MCP servers. It detects prompt injection, data exfiltration, supply chain attacks, and other threats using 189 rules across 14 threat categories. No LLM required -- all analysis is local and offline.

## Installation

```bash
# Install aguara CLI
go install github.com/garagon/aguara@latest

# Install mcp-aguara (MCP server, optional)
go install github.com/garagon/mcp-aguara@latest

# Or use the install helper
bash scripts/install-aguara.sh
```

## Configuration

Enable in `cognitive-os.yaml`:
```yaml
security:
  aguara:
    enabled: false  # Set to true after installing aguara
```

## Hook: aguara-scan.sh

| Property | Value |
|----------|-------|
| Type | PreToolUse |
| Matcher | Agent |
| Purpose | Scans agent prompts for security threats before execution |
| Exit codes | 0 (clean or advisory), 2 (BLOCK on CRITICAL findings) |

### Behavior

1. Graceful skip if `aguara` CLI is not installed
2. Reads agent prompt from stdin JSON (`tool_input.prompt`)
3. Pipes prompt through `aguara scan --stdin --format json`
4. Classifies findings using adversarial review format:

| Aguara Severity | Review Tier | Action |
|----------------|-------------|--------|
| CRITICAL / ERROR / HIGH | BLOCKER | Blocks agent launch (exit 2) |
| WARNING / MEDIUM | CONCERN | Advisory warning (exit 0) |
| INFO / LOW | SUGGESTION | Logged only (exit 0) |

### Metrics

Findings logged to `.cognitive-os/metrics/aguara-findings.jsonl`:

```json
{
  "timestamp": "2026-03-28T12:00:00Z",
  "tier": "BLOCKER",
  "rule_id": "PI-001",
  "message": "Detected prompt injection pattern...",
  "category": "prompt-injection",
  "severity": "CRITICAL"
}
```

## MCP Server: mcp-aguara

mcp-aguara exposes aguara's security scanning as 5 MCP tools for agent-time scanning:

| Tool | Purpose |
|------|---------|
| `scan_content` | Scan arbitrary content for security threats |
| `check_mcp_config` | Validate MCP server configurations |
| `list_rules` | List all 189 available security rules |
| `explain_rule` | Get detailed explanation of a specific rule |
| `discover_mcp` | Auto-discover MCP configs on the machine |

### MCP Server Registration

To enable mcp-aguara as an MCP server, add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "aguara": {
      "command": "mcp-aguara",
      "args": []
    }
  }
}
```

This is optional and separate from the hook. The hook provides automated pre-execution scanning; the MCP server provides on-demand scanning tools for agents.

## Comparison with Parry

| Feature | Parry | Aguara |
|---------|-------|--------|
| Detection method | ML (DeBERTa transformers) | Deterministic (189 rules) |
| Language | Rust | Go |
| Requires model download | Yes (HuggingFace) | No |
| Threat categories | Prompt injection | 14 categories (injection, exfiltration, supply chain, etc.) |
| CI integration | No | Yes (SARIF output, GitHub Action) |
| MCP server | No | Yes (mcp-aguara) |
| False positive rate | Lower (ML confidence) | Higher (pattern matching) |
| Speed | Slower (model inference) | Faster (regex + NLP) |

Aguara and parry are complementary: aguara provides broad deterministic coverage, parry provides deep ML-based injection detection. Running both provides defense in depth.

## Integration with Existing Security Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Content policy | `hooks/content-policy.sh` | Prohibited terms and patterns |
| Secret detection | `hooks/secret-detector.sh` | Credential leak prevention |
| Agent prompt scanning | `aguara` (deterministic) | 189-rule security analysis |
| Prompt injection ML | `parry-guard` (optional) | ML-based injection detection |
| SAST scanning | `semgrep` (optional) | Static code vulnerability analysis |
| Supply chain | `cos audit` | Package integrity verification |

## Graceful Degradation

If aguara is not installed, the hook silently exits (exit 0). The system continues with existing security hooks (content-policy, secret-detector). Aguara is an additional security layer, not a replacement.

## Contextual Trigger

This rule is loaded when: aguara, agent security scanning, prompt injection, security scanner, mcp-aguara.
