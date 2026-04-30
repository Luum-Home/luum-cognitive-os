<!-- SCOPE: both -->
---
name: exhaustive-prompt
description: Generate exhaustive agent prompts with scope enumeration and acceptance criteria
audience: project
version: "1.0.0"
platforms: ["claude-code"]
prerequisites: []
---

# Exhaustive Prompt Generator

> **Invoke**: `/exhaustive-prompt`
> **Purpose**: Transform a high-level task into an exhaustive, verifiable agent prompt with complete scope enumeration and measurable acceptance criteria.

## Problem

Agents do the MINIMUM when given vague instructions. "Rebrand old-name to new-name" becomes "renamed 3 files." The fix: never give agents vague instructions. This skill generates the exhaustive prompt BEFORE the agent is launched.

## When to Use

- BEFORE launching any agent for a medium/large/critical task
- When the task involves processing multiple files, endpoints, or items
- When "all" or "every" or "complete" appears in the task description
- When the orchestrator detects a completeness risk (see `/completeness-check`)

## Process

### Step 1: Scope Enumeration

Run discovery commands to enumerate the EXACT scope:

```
For rebranding tasks:
  grep -rl '{old_term}' {scope} --include='{pattern}' | sort

For migration tasks:
  find {source} -name '{pattern}' | wc -l
  List each item explicitly

For feature tasks:
  ls {expected_directories}
  Count expected files

For cleanup tasks:
  grep -rn '{anti_pattern}' {scope} | wc -l
  List each occurrence
```

### Step 2: Generate File-Level Detail

For EACH file in scope, specify:
- File path (absolute or relative to project root)
- Line number(s) where changes are needed
- What the current content is
- What it should become
- Why this change is needed

Example output:
```
FILES TO PROCESS (37 files, exhaustive):
1. apps/api/config/config.go -- line 15: 'old_user' -> 'new_user' (DB credential)
2. apps/api/config/config.go -- line 23: 'old_db' -> 'new_db' (DB name)
3. apps/service/internal/domain/entities/entity.go -- line 8: OldTag -> NewTag (struct field)
[... every single file ...]
37. pkg/sdks/auth/client.go -- line 5: 'old-auth' -> 'new-auth' (service name)
```

### Step 3: Generate Acceptance Criteria

Based on the enumerated scope, create verifiable criteria:

```
ACCEPTANCE CRITERIA:
1. Zero remaining occurrences: `grep -rl '{old}' {scope} --include='{pattern}' | wc -l` = 0
2. Build passes: `{build_command}` exits 0
3. Tests pass: `{test_command}` exits 0
4. [Additional task-specific criteria]
```

### Step 4: Generate Verification Commands

Separate section listing exact commands to run after completion:

```
VERIFICATION (run ALL, ALL must pass):
1. grep -rl 'old-name'' ${SERVICES_ROOT}/ --include='*.go' | wc -l
   Expected: 0
2. go build ./...
   Expected: exit code 0
3. go test ./... -short
   Expected: exit code 0
```

### Step 5: Define Complexity-Appropriate DoD

Map the task to the correct Definition of Done level and include ALL required criteria.

## Output Format

The skill produces a complete agent prompt ready to be passed to a sub-agent:

```markdown
# Task: [Clear, specific title]

## Context
[Why this task exists, what problem it solves]

## Scope
[EXHAUSTIVE list of items to process]
Total: [N] items

## FILES TO PROCESS ([N] files, exhaustive):
1. [path] — line [N]: '[old]' -> '[new]' ([reason])
2. [path] — line [N]: '[old]' -> '[new]' ([reason])
...

## Instructions
1. [Specific step 1]
2. [Specific step 2]
...

## Patterns to Follow
- [Exact pattern 1 with example]
- [Exact pattern 2 with example]

## ACCEPTANCE CRITERIA:
1. [Measurable check]: `[command]` = [expected]
2. [Measurable check]: `[command]` exits 0
3. [Measurable check]: `[command]` >= [threshold]

## VERIFICATION:
Run ALL commands. ALL must pass.
1. `[command]` — Expected: [result]
2. `[command]` — Expected: [result]

## Definition of Done: [complexity level]
- [ ] [criterion 1]
- [ ] [criterion 2]
...
```

## Examples

### Input: "Rebrand old-name to new-name"

The skill would:
1. Run `grep -rl 'old-name'' . --include='*.go' --include='*.yaml' --include='*.json'`
2. For each file, extract line numbers with `grep -rl 'old-name'' {file}`
3. Generate the exhaustive file list with line-level detail
4. Create acceptance criteria based on zero remaining occurrences
5. Add build and test verification

### Input: "Migrate wallet endpoints to Go"

The skill would:
1. Run `find payments/src/routes/wallet -name '*.ts'` to enumerate source endpoints
2. Run `grep -r 'router\.\(get\|post\|put\|delete\)' payments/src/routes/wallet/` to count
3. Check existing Go endpoints with `find ${SERVICES_ROOT}/wallet -name '*_controller.go'`
4. Calculate delta: remaining = source - existing
5. Generate per-endpoint migration instructions
6. Create acceptance criteria based on endpoint count parity

### Input: "Fix all lint errors"

The skill would:
1. Run `golangci-lint run ./... 2>&1 | grep -c 'Error'` to count errors
2. Categorize errors by type
3. List each error with file:line
4. Create acceptance criteria: `golangci-lint run ./... 2>&1 | grep -c 'Error'` = 0

## Anti-Patterns (DO NOT)

- Do NOT generate prompts that say "all files" without listing them
- Do NOT say "follow existing patterns" without specifying WHICH patterns
- Do NOT set acceptance criteria that only check a sample
- Do NOT skip the discovery step — always run commands to enumerate scope
- Do NOT guess counts — always verify with actual commands

## Integration

- **Pre-launch**: Run before ANY medium/large/critical agent launch
- **Completeness Check**: `hooks/completeness-check.sh` suggests this skill when prompts are vague
- **Auto-Verify**: `hooks/auto-verify.sh` uses the acceptance criteria from this skill's output
- **Acceptance Criteria**: `rules/acceptance-criteria.md` defines the format this skill produces
