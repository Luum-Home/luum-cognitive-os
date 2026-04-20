<!-- SCOPE: both -->
---
name: semgrep-scan
description: >
  Run Semgrep SAST security scanning on a path or changed files.
  Reports findings in adversarial review format (BLOCKER/CONCERN/SUGGESTION).
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-27
license: Apache-2.0
metadata:
  author: cognitive-os
  tool: semgrep/semgrep
  tool-license: LGPL-2.1
  tool-ring: ADOPT
  tool-score: 8.5
audience: project
---

## Purpose

Provides on-demand static analysis security testing (SAST) using Semgrep.
Scans source code for security vulnerabilities, anti-patterns, and bugs.
Results are formatted using the adversarial review protocol.

## Invocation

`/security-scan [path]` -- Scan a specific path (default: changed files)

## Prerequisites

Semgrep must be installed:

```bash
pip install semgrep
# or
brew install semgrep
```

## Steps

### 1. Determine Scan Scope

If a path is provided, scan that path. Otherwise, scan files changed since last commit:

```bash
# Changed files
git diff --name-only HEAD

# Or specific path
semgrep scan --config auto --json <path>
```

### 2. Run Semgrep

```bash
semgrep scan --config auto --json <files>
```

### 3. Parse and Classify Results

Map Semgrep severity to adversarial review tiers:

| Semgrep Severity | Review Tier |
|-----------------|-------------|
| ERROR | BLOCKER |
| WARNING | CONCERN |
| INFO | SUGGESTION |

### 4. Report Findings

Output each finding in the adversarial review format:

```
### [TIER] check-id

**Location**: file:line
**What**: description of the issue
**Why**: security impact
**Recommendation**: how to fix
```

### 5. Log Results

Append findings to `.cognitive-os/metrics/semgrep-findings.jsonl`.

## Output Format

The skill produces a structured security report compatible with the
adversarial review protocol. BLOCKERs signal the orchestrator that
human review is required before proceeding.

## Integration

- **Hook**: `hooks/semgrep-scan.sh` runs automatically after `sdd-apply`
- **Rule**: `rules/security-scanning.md` documents the integration
- **Metrics**: `.cognitive-os/metrics/semgrep-findings.jsonl`
