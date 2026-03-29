# Ecosystem Tools — External Tool Integrations

## Purpose

Documents all external tools integrated into Cognitive OS, their configuration, installation, and which hooks use them. All ecosystem tools follow the graceful degradation pattern: if a tool is not installed, the corresponding hook silently exits without blocking.

## Integrated Tools

### agnix — Agent Configuration Linter

| Property | Value |
|----------|-------|
| Purpose | Lints agent configuration files (SKILL.md, rules, agent definitions) for best practices |
| Config | `.agnix.toml` at project root |
| Hook | `hooks/agnix-lint.sh` (PostToolUse on Edit\|Write) |
| Install | `npm install -g @agent-sh/agnix` or `brew install agent-sh/tap/agnix` |
| Required | No (optional dependency, graceful skip if missing) |
| Scope | `.claude/`, `rules/`, `skills/`, `agents/` files only |

**Phase behavior**:
- reconstruction/stabilization: warnings only (exit 0)
- production/maintenance: errors block writes (exit 2)

**Metrics**: Findings logged to `.cognitive-os/metrics/agnix-findings.jsonl`

### semgrep — Static Application Security Testing

| Property | Value |
|----------|-------|
| Purpose | Scans code changes for security vulnerabilities and anti-patterns |
| Config | `.semgrep/` directory for custom rules (optional) |
| Hook | `hooks/semgrep-scan.sh` (PostToolUse on Agent) |
| Install | `pip install semgrep` or `brew install semgrep` |
| Required | No (OFF by default, enable with `SEMGREP_ENABLED=true`) |
| Scope | Source code files (.go, .ts, .py, .java, etc.) after sdd-apply |

**Metrics**: Findings logged to `.cognitive-os/metrics/semgrep-findings.jsonl`

### parry-guard — Prompt Injection Scanner

| Property | Value |
|----------|-------|
| Purpose | Scans agent prompts for prompt injection attempts |
| Config | `cognitive-os.yaml` under `security.parry` |
| Hook | `hooks/parry-scan.sh` (PreToolUse on Agent) |
| Install | `npm install -g parry-guard` |
| Required | No (optional dependency) |
| Scope | Agent prompts before execution |

### recall — Conversation Search

| Property | Value |
|----------|-------|
| Purpose | Searches past conversation transcripts for context |
| Config | None (reads from Claude conversation history) |
| Skill | `skills/recall-search/SKILL.md` |
| Install | `npm install -g @anthropic/recall` |
| Required | No (optional dependency) |
| Scope | Conversation history search |

### aguara — AI Agent Security Scanner

| Property | Value |
|----------|-------|
| Purpose | Deterministic security scanner for AI agent skills and MCP servers. 189 rules across 14 threat categories (prompt injection, data exfiltration, supply chain attacks). No LLM required. |
| Config | `cognitive-os.yaml` under `security.aguara` |
| Hook | `hooks/aguara-scan.sh` (PreToolUse on Agent) |
| Install | `go install github.com/garagon/aguara@latest` or `bash scripts/install-aguara.sh` |
| Required | No (optional dependency, graceful skip if missing) |
| Scope | Agent prompts before execution |

**Phase behavior**:
- All phases: CRITICAL findings block agent launch (exit 2), all others advisory (exit 0)

**Metrics**: Findings logged to `.cognitive-os/metrics/aguara-findings.jsonl`

**MCP Server**: `mcp-aguara` available as optional MCP server (`go install github.com/garagon/mcp-aguara@latest`). Provides 5 tools: `scan_content`, `check_mcp_config`, `list_rules`, `explain_rule`, `discover_mcp`. See `packages/aguara-security/rules/aguara-integration.md` for registration instructions.

### hcom — Cross-Terminal Communication

| Property | Value |
|----------|-------|
| Purpose | Enables communication between concurrent Claude Code sessions |
| Config | `cognitive-os.yaml` under `sessions.hcom` |
| Hook | N/A (used by session management) |
| Install | `npm install -g hcom` |
| Required | No (optional dependency) |
| Scope | Multi-session coordination |

## Graceful Degradation Pattern

All ecosystem tool hooks follow this pattern:

```bash
# Check if tool is installed — skip silently if not
if ! command -v tool-name &>/dev/null; then
  exit 0
fi
```

This ensures:
1. The Cognitive OS works without any external tools installed
2. Tools are additive enhancements, not requirements
3. CI/CD pipelines do not break due to missing optional tools
4. New team members can onboard without installing every tool upfront

## Adding New Ecosystem Tools

When integrating a new external tool:

1. Create a hook in `hooks/` following the graceful degradation pattern
2. Add configuration (if needed) to `.{tool}.toml` or `cognitive-os.yaml`
3. Add integration tests to `tests/integration/test_ecosystem_tools.py`
4. Add unit tests for hook logic to `tests/unit/test_{tool}_integration.py`
5. Document the tool in this file
6. Update `RULES-COMPACT.md` if the tool adds a new always-active rule

## Installation Status Check

Run the following to check which ecosystem tools are available:

```bash
for tool in agnix semgrep parry-guard aguara mcp-aguara recall hcom; do
  if command -v "$tool" &>/dev/null; then
    echo "[installed] $tool: $($tool --version 2>/dev/null | head -1)"
  else
    echo "[missing]   $tool"
  fi
done
```

## Contextual Trigger

This rule is loaded when: ecosystem tools, external tools, agnix, semgrep, parry, aguara, recall, hcom, tool integration.
