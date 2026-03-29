# @luum/mantis-security

Mantis HTTP security toolkit integration for Cognitive OS.

## What

Integrates [mantis](https://github.com/garagon/mantis) into the Cognitive OS security workflow. Mantis provides automated HTTP security scanning with OWASP coverage, header analysis, TLS verification, and common vulnerability detection.

## Install

```bash
go install github.com/garagon/mantis@latest
```

## When to Use

- Scanning HTTP endpoints for security misconfigurations
- Verifying security headers (HSTS, CSP, X-Frame-Options, etc.)
- TLS certificate and configuration validation
- OWASP Top 10 basic coverage for web services
- Pre-deployment security checks in CI/CD

## Usage

```bash
# Basic security scan
mantis scan --url http://localhost:3000

# Header analysis
mantis headers --url http://localhost:3000/api/health

# TLS check
mantis tls --url https://api.example.com
```

## Integration with Security Stack

| Tool | Scope | Mantis Complement |
|------|-------|-------------------|
| Semgrep | Source code (SAST) | Mantis scans running services (DAST) |
| Garak | LLM behavior | Mantis scans HTTP layer |
| Aguara | Skill definitions | Mantis scans deployed endpoints |
| Tero | HTTP testing + chaos | Mantis adds security-specific checks |

## Status

WATCH -- Evaluated and documented. No hook implementation yet. Use directly via CLI.

## Graceful Degradation

If mantis is not installed, security scanning falls back to Semgrep (SAST) and manual HTTP inspection. Mantis is an enhancement for DAST coverage, not a requirement.

## License

Apache-2.0
