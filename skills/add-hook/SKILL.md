<!-- SCOPE: both -->
---
name: add-hook
description: Step-by-step guide for adding a new hook to the Cognitive OS
version: 0.1.0
audience: os
tags: [development, extension, hooks]
---

# Add Hook

> Procedure for creating and registering a new lifecycle hook in the Cognitive OS.

## Trigger

When you need to add a new hook to intercept Claude tool usage at a specific lifecycle point.

## Inputs

- **Hook name**: kebab-case identifier (e.g., `my-check`)
- **Event type**: `PreToolUse`, `PostToolUse`, `SessionStart`, or `Stop`
- **Matcher**: tool pattern the hook should fire on (e.g., `Agent`, `Edit|Write`, `Bash`)
- **Purpose**: what the hook does and whether it can block execution

## Steps

### 1. Create the hook script

Create `hooks/{hook-name}.sh`:

```bash
#!/usr/bin/env bash
# {EventType} hook: {Hook Name} — {short description}
# Matcher: {matcher_pattern}
# Can block: yes/no (PreToolUse only can block with exit 2)
# Must complete in <200ms

set -uo pipefail

_HOOK_NAME="{hook-name}"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

INPUT=$(cat)

# Your logic here

exit 0
```

Key conventions:
- Source `_lib/safe-jsonl.sh` and `_lib/common.sh` for shared utilities
- Read stdin JSON via `INPUT=$(cat)` — contains `tool_name`, `tool_input`, and (PostToolUse) `tool_response`
- Exit 0 = pass, exit 2 = BLOCK (PreToolUse only)
- Always complete in under 200ms for PreToolUse, under 500ms for PostToolUse

### 2. Make it executable

```bash
chmod +x hooks/{hook-name}.sh
```

### 3. Register in `.claude/settings.local.json`

Add under the appropriate trigger key:

```json
{
  "hooks": {
    "{EventType}": [
      {
        "matcher": "{matcher_pattern}",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/{hook-name}.sh\""
          }
        ]
      }
    ]
  }
}
```

If the trigger key already exists, add a new entry to the array. If a matching `matcher` block already exists, add the command to its `hooks` array.

### 4. Add to efficiency profile (if always-active)

If the hook should run in the `standard` efficiency profile, add it to `packages/efficiency-profiles/profiles/standard.json`. For the `lean` profile, add to `lean.json`. Skip this step if the hook is optional or phase-specific.

Run `bash scripts/apply-efficiency-profile.sh standard` to apply after updating.

### 5. Add a test

Create `tests/unit/test-{hook-name}.sh`:

```bash
#!/usr/bin/env bash
# Tests for hooks/{hook-name}.sh

set -euo pipefail
source "$(dirname "$0")/_lib/test-helpers.sh"

test_pass_case() {
    local input='{"tool_name":"Edit","tool_input":{}}'
    local result
    result=$(echo "$input" | bash hooks/{hook-name}.sh; echo "exit:$?")
    assert_contains "$result" "exit:0" "should pass on normal input"
}

test_pass_case
echo "PASS: {hook-name} tests"
```

Run `bash tests/run-all-tests.sh` to verify.

## Available Trigger Reference

| Trigger | When it fires | Input available | Can block? |
|---------|--------------|-----------------|------------|
| `PreToolUse` | Before a tool runs | `tool_name`, `tool_input` | Yes (exit 2) |
| `PostToolUse` | After a tool runs | `tool_name`, `tool_input`, `tool_response`, `exit_code` | No |
| `SessionStart` | At session start | `session_id` | No |
| `Stop` | At session end | `session_id` | No |

## Matcher Pattern Reference

| Pattern | Matches |
|---------|---------|
| `Agent` | Agent tool only |
| `Bash` | Bash tool only |
| `Edit\|Write` | Edit or Write tools |
| `Edit\|Write\|Bash` | Edit, Write, or Bash tools |
| `.*` | All tools |

## Output: Working Registered Hook

- `hooks/{hook-name}.sh` — executable hook script
- `.claude/settings.local.json` — updated with hook registration
- `tests/unit/test-{hook-name}.sh` — passing test
- Efficiency profile updated (if always-active)

## Success Criteria

- [ ] `bash -n hooks/{hook-name}.sh` exits 0 (syntax valid)
- [ ] Hook is listed in `.claude/settings.local.json` under the correct trigger
- [ ] `bash tests/unit/test-{hook-name}.sh` passes
- [ ] Hook fires correctly: `echo '{"tool_name":"X","tool_input":{}}' | bash hooks/{hook-name}.sh`
