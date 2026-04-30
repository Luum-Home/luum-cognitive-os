<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Security Scanning — Semgrep SAST Integration

## Overview

Semgrep provides Static Application Security Testing (SAST) integrated into the SDD pipeline.
After `sdd-apply` produces code changes, Semgrep automatically scans for security vulnerabilities,
coding anti-patterns, and potential bugs.

## Activation

Security scanning is **OFF by default**. Enable it by setting:

```bash
export SEMGREP_ENABLED=true
```

Or add to your `.env`:

```
SEMGREP_ENABLED=true
```

## Requirements

Install Semgrep:

```bash
pip install semgrep
# or
brew install semgrep
```

## How It Works

### Automatic Scanning (PostToolUse Hook)

The `hooks/semgrep-scan.sh` hook fires after any Agent tool use that contains
`sdd-apply` in its output. It:

1. Identifies changed files from `git diff`
2. Filters to source code files (.go, .ts, .py, .java, etc.)
3. Runs `semgrep scan --config auto --config p/ai-best-practices --json` on changed files
4. Classifies findings using the adversarial review format:

| Semgrep Severity | Adversarial Review Tier | Action |
|-----------------|------------------------|--------|
| ERROR | BLOCKER | Must fix before proceeding |
| WARNING | CONCERN | Should fix, requires justification to skip |
| INFO/NOTE | SUGGESTION | Fix if time allows |

5. Logs findings to `.cognitive-os/metrics/semgrep-findings.jsonl`
6. Signals the orchestrator if BLOCKER-level findings are detected

### Manual Scanning (Skill)

Use `/security-scan [path]` for on-demand scanning of any path.

## Graceful Degradation

- If `semgrep` is not installed, the hook silently exits (no error)
- If no source files are changed, the hook skips scanning
- If Semgrep returns no findings, no output is produced

## Findings Log Format

Each finding is logged to `.cognitive-os/metrics/semgrep-findings.jsonl`:

```json
{
  "timestamp": "2026-03-27T12:00:00Z",
  "tier": "BLOCKER",
  "check_id": "python.lang.security.audit.exec-detected",
  "message": "Detected use of exec()...",
  "file": "src/handler.py",
  "line": 42,
  "severity": "ERROR"
}
```

## Integration with SDD Pipeline

```
sdd-apply completes
    |
    v
semgrep-scan.sh (PostToolUse) — scans changed files
    |
    v
Findings classified as BLOCKER/CONCERN/SUGGESTION
    |
    v
sdd-verify (includes security findings in review)
    |
    v
Orchestrator acts on BLOCKERs
```

## Configuration

In `cognitive-os.yaml` (optional):

```yaml
security:
  semgrep:
    enabled: false              # Set to true to activate
    config: "auto,p/ai-best-practices"  # Semgrep rulesets (auto + AI security rules)
    max_files: 50               # Max files to scan per run
    severity_threshold: WARNING # Minimum severity to report
```

## AI Best Practices Ruleset

The `p/ai-best-practices` ruleset (58 rules) is included alongside the default `auto` config.
It detects AI/ML-specific security issues:

| Category | Examples |
|----------|---------|
| Hardcoded API keys | OpenAI, Anthropic, Cohere, HuggingFace keys in source |
| Prompt injection | Unsanitized user input passed to LLM prompts |
| MCP security | Insecure MCP server configurations and tool definitions |
| Model configuration | Insecure model loading, pickle deserialization |
| Data leakage | Sensitive data in LLM context or logging |

This ruleset is particularly relevant for Cognitive OS development where agent prompts,
MCP configurations, and LLM API calls are common patterns.

## Custom Rules

Add project-specific Semgrep rules in `.semgrep/` directory at the project root.
Semgrep will automatically include these alongside the community rules.
