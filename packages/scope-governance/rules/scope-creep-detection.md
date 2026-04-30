<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Scope Creep Detection

## Purpose

Detects when agents edit files outside the approved task scope. When an active task in `.cognitive-os/tasks/active-tasks.json` defines `scope`, `expectedFiles`, or `expectedOutputs`, edits to files not matching those paths trigger a warning or block.

## How It Works

The `scope-creep-detector.sh` PostToolUse hook fires on every Edit and Write tool use:

1. Reads the edited file path from stdin JSON
2. Checks `.cognitive-os/tasks/active-tasks.json` for an `in_progress` task with scope metadata
3. If the task has `scope`, `expectedFiles`, or `expectedOutputs` arrays, compares the edited file against those paths
4. Matching uses exact match, prefix match, and substring match to support both file paths and directory scopes
5. If the file is outside scope, emits a warning or block depending on phase

## Phase Behavior

| Phase | Out-of-Scope Edit | Exit Code |
|-------|-------------------|-----------|
| `reconstruction` | WARNING (advisory) | 0 |
| `stabilization` | WARNING (advisory) | 0 |
| `production` | BLOCK | 2 |
| `maintenance` | BLOCK | 2 |

## When It Skips (Silent Exit)

- No active tasks file exists
- No `in_progress` task has scope/expectedFiles/expectedOutputs defined
- The edited file matches an approved path
- Private mode is active
- Capability level disables this component

## Task Scope Format

Tasks in `active-tasks.json` can define scope using any of these fields:

```json
{
  "id": "implement-user-endpoint",
  "status": "in_progress",
  "scope": ["internal/users/", "tests/unit/test_user"],
  "expectedFiles": ["internal/users/handler.go", "internal/users/dto.go"],
  "expectedOutputs": ["internal/users/handler.go"]
}
```

All three fields are merged when checking scope. Any match (exact, prefix, or substring) allows the edit.

## Metrics

Detections are logged to `.cognitive-os/metrics/scope-creep.jsonl`:

```json
{
  "timestamp": "ISO-8601",
  "file": "path/to/edited/file",
  "task": "task description",
  "phase": "reconstruction",
  "action": "warn"
}
```

## Hook Details

- **Hook**: `hooks/scope-creep-detector.sh`
- **Type**: PostToolUse
- **Matcher**: Edit|Write
- **Exit code**: 0 (pass/warn) or 2 (block in production/maintenance)
- **Performance**: < 100ms

## Integration

| Rule | Relationship |
|------|-------------|
| Scope Proportionality | Proportionality checks response SIZE. Scope creep checks file LOCATION. Complementary. |
| Blast Radius | Blast radius estimates scope BEFORE execution. Scope creep detects violations DURING execution. |
| Fault Tolerance | Task registration in active-tasks.json provides the scope metadata this hook reads. |

## Contextual Trigger

This rule is always active. It applies to every Edit and Write tool use via the PostToolUse hook.
