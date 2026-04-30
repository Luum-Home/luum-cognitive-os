<!-- SCOPE: both -->
---
name: error-analyzer
description: Analyze accumulated errors from test/lint/build runs and propose skill improvements. Use when error patterns repeat.
version: 1.0.0
user-invocable: true
auto-generated: false
audience: project
summary_line: Analyze accumulated errors from test/lint/build runs and propose skill…

platforms: ["claude-code"]
prerequisites: []
---

# Error Analyzer Skill

Analyze accumulated error patterns from `.claude/metrics/error-learning.jsonl` and propose skill improvements.

## When to Use

- After repeated test/lint/build failures
- When the orchestrator suggests running `/error-analyzer` due to 3+ pattern occurrences
- Periodically to review error trends and improve development workflow

## Instructions

### Step 1: Load Error Data

Read `.claude/metrics/error-learning.jsonl`. Each line is a JSON object with:
- `timestamp`: ISO timestamp
- `timestamp_epoch`: Unix epoch seconds
- `type`: TEST_FAILURE | LINT_ERROR | BUILD_ERROR | COMPILATION_ERROR | RUNTIME_ERROR
- `service`: Service name (<consumer-codename-b>, <consumer-codename-a>, onboarding, etc.)
- `framework`: Testing/build framework used
- `error`: Error message text
- `command`: The command that failed
- `context`: Auto-detected context hint
- `fingerprint`: MD5 of first 100 chars for dedup

### Step 2: Group and Cluster Errors

Group errors by:
1. **Service** (<consumer-codename-b>, onboarding, <consumer-codename-a>, payments-service, etc.)
2. **Type** (TEST_FAILURE, LINT_ERROR, BUILD_ERROR, COMPILATION_ERROR)
3. **Pattern**: Cluster similar error messages together. Look for:
   - Same error code (e.g., TS2345, TS7006)
   - Same function/file name in error
   - Same root cause pattern (missing import, type mismatch, connection refused)

### Step 3: Analyze Each Pattern (3+ occurrences)

For each pattern with 3 or more occurrences:

1. **Identify the root cause**: What keeps causing this error?
   - Missing dependency resolution step?
   - Incorrect mock configuration?
   - Type definition drift?
   - Service not running?
   - Missing environment variable?

2. **Check existing skills**: Look in `.claude/skills/` for a skill that should prevent this.
   - `nestjs-patterns/` for NestJS-related errors
   - `typescript-patterns/` for TypeScript errors
   - `testing-patterns/` for test framework errors
   - `clean-arch-patterns/` for architecture violations

3. **Propose action**:
   - If a skill exists: propose adding a section about preventing this error class
   - If no skill exists: propose creating a new skill or adding a rule
   - If it's a workflow issue: propose adding a pre-step to hooks

4. **Save to Engram**: Call `mem_save` with:
   - `title`: "Error pattern: {brief description}"
   - `type`: "discovery"
   - `project`: "{project}"
   - `topic_key`: "error-patterns/{service}"
   - `content`: Structured analysis with What/Why/Where/Learned format

### Step 4: Generate Report

Output a structured report:

```
## Error Pattern Analysis

**Period**: {earliest timestamp} to {latest timestamp}
**Total errors captured**: {count}
**Unique patterns (3+ occurrences)**: {count}

### Pattern 1: {Brief description} ({service})
- **Type**: {ERROR_TYPE}
- **Occurrences**: {count}
- **Framework**: {framework}
- **Root cause**: {analysis}
- **Common error**: {representative error message, truncated}
- **Affected skill**: {skill name or "none"}
- **Recommendation**: {what to do}
- **Proposed change**:
  ```
  {specific text to add to skill or rule}
  ```

### Pattern 2: ...
```

### Step 5: Apply Changes (if --apply flag)

If the user invoked with `--apply`:

1. For each proposed skill update:
   - Read the target skill file
   - Add the proposed section (typically under a "## Common Pitfalls" or "## Error Prevention" heading)
   - Save the updated skill

2. For each proposed new rule:
   - Create the rule file in `.claude/rules/`

3. After all changes:
   - Run `/skill-registry` to update the index (if available)
   - Save a summary to Engram: "Updated skills based on error pattern analysis"

4. Do NOT apply changes without `--apply` — only propose them in the report.

## Output Format

Always end the report with:

```
## Summary
- Patterns analyzed: {N}
- Skills to update: {N}
- New skills/rules proposed: {N}
- Action: {Run `/error-analyzer --apply` to apply changes | Changes applied successfully}
```

## Error Type Reference

| Type | Source | Examples |
|------|--------|----------|
| TEST_FAILURE | jest, vitest, go test, junit, pytest | Assertion failures, timeout, missing mock |
| LINT_ERROR | eslint, golangci-lint, tsc --noEmit, go vet | Style violations, unused vars, type errors |
| BUILD_ERROR | go build, gradlew build, yarn build, tsc | Missing modules, config errors |
| COMPILATION_ERROR | Any compiler | Syntax errors, type mismatches, undefined symbols |
| RUNTIME_ERROR | Process crash | Panics, unhandled exceptions, OOM |
| INTEGRATION_ERROR | Service calls | Connection refused, timeout, 5xx responses |
