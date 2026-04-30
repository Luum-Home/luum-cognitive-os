<!-- TIER: 2 -->
<!-- SCOPE: both -->
# Parry -- Prompt Injection Scanner

## Overview
Parry (parry-guard) is an optional ML-based prompt injection scanner for Claude Code hooks. It uses DeBERTa transformers in Rust to detect injection attempts in tool inputs, outputs, and user prompts.

## Installation
```bash
# macOS (recommended)
brew install vaporif/tap/parry-guard
# or download binary from https://github.com/vaporif/parry/releases

# Requires HuggingFace token for model download
export HF_TOKEN=your_token_here
```

## Configuration
Enable in `cognitive-os.yaml`:
```yaml
security:
  parry:
    enabled: false  # Set to true after installing parry-guard
    threshold: 0.7  # Detection confidence threshold
```

## Hook Registration
When enabled, parry runs as additional Claude Code hooks alongside our existing security hooks. Register in `.claude/settings.local.json`:
```json
{
  "hooks": {
    "PreToolUse": [{"command": "parry-guard hook", "timeout": 1000}],
    "PostToolUse": [{"command": "parry-guard hook", "timeout": 5000}]
  }
}
```

## Graceful Degradation
If parry-guard is not installed, the system continues with our existing content-policy.sh and secret-detector.sh hooks. Parry is an additional security layer, not a replacement.

## Integration with Existing Security

| Layer | Tool | Purpose |
|-------|------|---------|
| Content policy | `hooks/content-policy.sh` | Prohibited terms and patterns |
| Secret detection | `hooks/secret-detector.sh` | Credential leak prevention |
| Prompt injection | `parry-guard` (optional) | ML-based injection detection |
| SAST scanning | `semgrep` (optional) | Static code vulnerability analysis |

## Contextual Trigger

This rule is loaded when: parry, prompt injection, injection scanner, parry-guard.
