<!-- TIER: 0 -->
<!-- SCOPE: both -->
# Mandatory Acceptance Criteria

## Purpose

Every agent prompt MUST include measurable acceptance criteria. Without them, agents optimize for speed over completeness, producing the MINIMUM viable output instead of the MAXIMUM expected result. This rule closes the gap between "technically done" and "actually complete."

## The Problem

Agents interpret ambiguous tasks minimally:
- "Rebrand the project" → renames 3 obvious files, ignores 200 others
- "Migrate endpoints" → migrates 10 of 317 endpoints and reports "done"
- "Fix all lint errors" → fixes the 5 easiest, leaves 40 remaining

## The Rule

### Before launching ANY agent, the orchestrator MUST define:

```
ACCEPTANCE CRITERIA:
1. [Measurable check]: [expected result]
2. [Command to verify]: [expected output]
3. [Quantitative target]: [number or threshold]
```

### If the orchestrator does NOT provide acceptance criteria:

The agent MUST define them BEFORE starting work:
1. Enumerate the scope (count files, endpoints, occurrences)
2. Define measurable completion checks
3. State the verification commands
4. Proceed only after criteria are established

### Format

Acceptance criteria MUST be:
- **Measurable**: Has a number, count, or pass/fail command
- **Verifiable**: Can be checked by running a command
- **Complete**: Covers the full scope, not a sample

## Examples

### BAD (ambiguous, no verification)

```
"Rebrand the project from old-name to new-name"
```
No way to verify completeness. Agent will rename what it finds convenient.

### GOOD (exhaustive, verifiable)

```
"Rebrand old-name to new-name across the backend.

ACCEPTANCE CRITERIA:
1. Zero remaining occurrences: grep -rl 'old-name' src/ --include='*.go' --include='*.ts' | wc -l = 0
2. Zero remaining in configs: grep -rl 'old-name' . --include='*.yaml' --include='*.yml' | wc -l = 0
3. Build passes: {build_command} exits 0
4. Tests pass: {test_command} exits 0"
```

### BAD (no endpoint count)

```
"Migrate all services to the new backend"
```

### GOOD (quantified scope)

```
"Migrate user endpoints to new service.

SCOPE: 47 endpoints in legacy-service/src/routes/
Currently migrated: 12. Remaining: 35.

ACCEPTANCE CRITERIA:
1. Endpoint count: find new-service/ -name '*controller*' | wc -l >= 47
2. All compile: {build_command} exits 0
3. All tests pass: {test_command} exits 0
4. Coverage maintained: {coverage_command} >= 80%"
```

### BAD (no pattern specification)

```
"Follow the existing patterns in the codebase"
```

### GOOD (explicit patterns)

```
"Implement using the project's established patterns:
- Follow the controller/handler pattern documented in .claude/rules/
- Use the project's dependency injection conventions
- Follow the clean architecture layers

ACCEPTANCE CRITERIA:
1. No anti-pattern imports: grep -r '{anti_pattern}' src/newservice/ | wc -l = 0
2. Uses correct framework: grep -r '{framework_import}' src/newservice/ | wc -l > 0
3. Architecture layers exist: ls src/newservice/{expected_dirs} all exist"
```

## Acceptance Criteria Templates

### For rebranding/renaming tasks
```
ACCEPTANCE CRITERIA:
1. grep -rl '{old_term}' {scope} --include='{file_pattern}' | wc -l = 0
2. Build passes: {build_command} exits 0
3. Tests pass: {test_command} exits 0
```

### For migration tasks
```
ACCEPTANCE CRITERIA:
1. Source count: {count_source_items} = {N}
2. Target count: {count_target_items} >= {N}
3. All compile: {build_command} exits 0
4. All tests pass: {test_command} exits 0
```

### For new feature tasks
```
ACCEPTANCE CRITERIA:
1. Feature files exist: ls {expected_files} all present
2. Tests exist: find {scope} -name '*_test.*' | wc -l >= {N}
3. Coverage: {coverage_command} >= {threshold}%
4. Lint clean: {lint_command} exits 0
```

### For cleanup/refactor tasks
```
ACCEPTANCE CRITERIA:
1. Anti-pattern removed: grep -r '{anti_pattern}' {scope} | wc -l = 0
2. New pattern applied: grep -r '{new_pattern}' {scope} | wc -l >= {N}
3. No regressions: {test_command} exits 0
```

## Integration with Other Rules

- **Closed-Loop Prompts** [`closed-loop-prompts`]: Acceptance criteria ARE the success criteria in closed-loop prompts
- **Definition of Done** [`definition-of-done`]: DoD criteria are the MINIMUM acceptance criteria; task-specific criteria are additional
- **Auto-Verify Hook** [`hooks/auto-verify.sh`]: Extracts and runs acceptance criteria commands automatically on completion
- **Exhaustive Prompt** [`skills/exhaustive-prompt`]: Generates acceptance criteria as part of exhaustive prompt composition

## Contextual Trigger

This rule is always active. It applies to every agent launch.
