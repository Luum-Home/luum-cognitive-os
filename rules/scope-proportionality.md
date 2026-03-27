# Scope Proportionality Check

## Purpose

Prevents AI coding agents from producing disproportionate responses to simple tasks. A well-documented failure mode in agent-assisted development is scope creep: a task described as "fix a bug" triggers sweeping file deletions, rewrites across dozens of files, or architectural changes that far exceed the original intent.

This rule ensures that **changes are proportional to the task**.

## Motivation

In agent-assisted coding, a recurring failure pattern is:
1. User requests a simple bug fix
2. Agent interprets the fix broadly and rewrites the entire module
3. Files are deleted, APIs are changed, tests are broken
4. The "fix" introduces more problems than it solves

The proportionality check catches this pattern by comparing the task type (fix, refactor, feature) against the scope of changes (files created, modified, deleted).

## The Three Rules

### Rule 1: Fix tasks must not delete files

A bug fix patches existing behavior. Deleting files during a fix is almost always a sign that the agent has exceeded its scope.

| Phase | Behavior |
|-------|----------|
| `reconstruction` | WARN -- agent is rebuilding, some structural changes during fixes are expected |
| `stabilization` | WARN -- structural changes should be separate from fixes |
| `production` | BLOCK -- fix tasks must NOT delete files; use a separate refactor task |
| `maintenance` | BLOCK -- minimal changes only; deletions require a dedicated task |

### Rule 2: Fix tasks touching >20 files are disproportionate

A bug fix that touches more than 20 files is almost certainly doing more than fixing a bug. This triggers a WARNING in all phases.

Exceptions where this may be legitimate:
- A single-line change propagated via automated tooling (e.g., import path rename)
- A test fix that requires updating many test fixtures

In these cases, the warning is advisory and can be acknowledged.

### Rule 3: Any task deleting >5 files needs justification

Regardless of task type, deleting more than 5 files in a single agent run is unusual and deserves attention. This triggers a WARNING in all phases.

## Integration with Other Rules

| Rule | Relationship |
|------|-------------|
| Blast Radius (`blast-radius`) | Blast radius estimates scope BEFORE execution. Proportionality checks AFTER. Complementary. |
| Acceptance Criteria (`acceptance-criteria`) | Well-defined acceptance criteria naturally constrain scope. |
| Sandbox Sampling (`sandbox-sampling`) | Large-scope tasks should be sampled first, which prevents proportionality violations. |
| HALT Protocol (`closed-loop-prompts`) | HALT triggers fire BEFORE execution for risky tasks. Proportionality fires AFTER for disproportionate results. |
| Agent Quality (`agent-quality`) | Proportionality is a quality dimension: agents should do what was asked, not more. |

## Metrics

Events are logged to `.cognitive-os/metrics/scope-proportionality.jsonl`:

```json
{
  "timestamp": "ISO-8601",
  "task_type": "fix",
  "severity": "BLOCK",
  "files_created": 0,
  "files_modified": 3,
  "files_deleted": 2,
  "total_files": 5,
  "phase": "production",
  "message": "Fix task deleted files in production phase",
  "task": "first 100 chars of task description..."
}
```

## Hook Details

- **Hook**: `hooks/scope-proportionality.sh`
- **Type**: PostToolUse
- **Matcher**: Agent
- **Exit code**: 0 (pass/warn) or 2 (block in production/maintenance for rule 1)
- **Performance**: < 200ms

## Contextual Trigger

This rule is always active. It applies to every agent completion via the PostToolUse hook.
