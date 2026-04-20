<!-- SCOPE: both -->
# Trail of Bits Security Skills

## Overview

62 professional security audit skills from [Trail of Bits](https://github.com/trailofbits/skills), a leading security research firm. Installed as a git submodule under `.claude/plugins/trailofbits-skills/`.

## License

CC-BY-SA-4.0 -- requires attribution (see ATTRIBUTION.md). Skills are used unmodified.

## Installation

```bash
bash scripts/install-tob-skills.sh
```

## Key Skills

| Category | Skills | What they catch |
|---|---|---|
| Code Auditing | static-analysis, variant-analysis, insecure-defaults | Vulnerabilities, bug patterns, fail-open configs |
| Supply Chain | supply-chain-risk-auditor | Dependency risks, typosquatting |
| Smart Contracts | building-secure-contracts | Blockchain vulnerabilities (6 chains) |
| Prompt Security | agentic-actions-auditor | GitHub Actions injection, TOCTOU |

## Integration with Cognitive OS

These skills complement our existing security stack:
- `security-scanning.md` -- our Semgrep SAST
- `pentesting-readiness.md` -- our security test cases
- `content-policy.md` -- our content enforcement

## Graceful Degradation

If the submodule is not installed, security audits use only our built-in Semgrep scanning. Trail of Bits skills are an optional enhancement.
