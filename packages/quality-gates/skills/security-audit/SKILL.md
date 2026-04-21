<!-- SCOPE: both -->
---
name: security-audit
description: >
  Comprehensive security audit of Cognitive OS configuration, secrets, hooks,
  permissions, and infrastructure. Reports findings with severity levels.
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-27
license: Apache-2.0
metadata:
  author: luum
  category: security
audience: os-dev
summary_line: "Comprehensive security audit of Cognitive OS configuration, secrets, hooks…"

---

## Purpose

Scan the Cognitive OS installation and project configuration for security issues:
exposed secrets, over-privileged agents, unregistered hooks, hardcoded URLs, and
exposed Docker ports. Generates a structured report with CRITICAL/HIGH/MEDIUM/LOW findings.

## Invocation

`/security-audit` -- Full security audit of the current project

## Steps

### Step 1: Scan for Exposed Secrets

Search source files for patterns that look like API keys, tokens, and passwords:
- `grep -rn "(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}" --include="*.py" --include="*.ts" --include="*.go" --include="*.yaml" --include="*.json" .`
- Exclude `.env` files, `node_modules/`, `__pycache__/`, `.git/`
- Each match is a CRITICAL finding

### Step 2: Check .env.example Coverage

- List all env vars referenced in source code (`grep -roh '\$\{[A-Z_]*\}' --include="*.yaml" --include="*.py"`)
- Check if each appears in `.env.example`
- Missing entries are HIGH findings

### Step 3: Verify Hook Registration

- List all `.sh` files in `hooks/`
- Check each is registered in `.claude/settings.json` or `settings.local.json`
- Unregistered hooks are MEDIUM findings (potential backdoor or dead code)

### Step 4: Check for Unregistered Hooks

- Look for executable scripts in `.claude/hooks/` or other directories that are NOT in the official hooks/ directory
- Unknown hooks are HIGH findings

### Step 5: Review Agent Permission Grants

- Check if `lib/agent_permissions.py` is used in agent launch flows
- Verify ALWAYS_BLOCKED paths list is comprehensive
- Check for any hardcoded permission escalation patterns
- Over-privileged patterns are HIGH findings

### Step 6: Scan for Hardcoded URLs and IPs

- `grep -rn "http://\|https://" --include="*.py" --include="*.go" --include="*.ts" .`
- Filter out localhost, test URLs, and documentation
- Hardcoded production URLs are MEDIUM findings

### Step 7: Check Docker Service Exposure

- Read `docker-compose*.yml` for port mappings
- Identify services with ports exposed to `0.0.0.0` (all interfaces)
- Services without authentication on exposed ports are HIGH findings

### Step 8: Review Always-Blocked Paths

- Verify the ALWAYS_BLOCKED list in `lib/agent_permissions.py` covers:
  `.env`, `*.key`, `*.pem`, `*.p12`, `secrets/*`, `**/credentials*`, `**/password*`, `.git/config`
- Missing patterns are HIGH findings

### Step 9: Generate Security Report

Output a structured markdown report:

```markdown
# Security Audit Report

**Date**: {ISO timestamp}
**Scope**: {project path}

## Summary
- CRITICAL: {count}
- HIGH: {count}
- MEDIUM: {count}
- LOW: {count}

## Findings

### [CRITICAL] {title}
**Location**: {file:line}
**What**: {description}
**Why**: {security impact}
**Recommendation**: {fix}

### [HIGH] {title}
...
```

## Success Criteria

- All 8 scan steps executed
- Report generated with severity classifications
- Zero false positives on `.env.example` references
- All findings include location and recommendation

## Notes

- This skill is READ-ONLY — it does not modify any files
- Use the `security_audit` permission profile when running
- Findings should be tracked and addressed before production deployment
