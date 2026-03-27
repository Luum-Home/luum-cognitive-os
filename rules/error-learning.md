# Error Learning Protocol

## Automatic Error Capture

Every test, lint, and build failure is automatically captured by the `error-learning.sh` PostToolUse hook.
Errors are stored in `.claude/metrics/error-learning.jsonl` as one JSON object per line.

### Captured Commands

| Category | Commands Detected |
|----------|-------------------|
| Test | jest, vitest, go test, gradlew test, pytest, yarn test, npm test |
| Lint | eslint, golangci-lint, tsc --noEmit, go vet |
| Build | go build, gradlew build, yarn build, npm run build, tsc |

### Error Types

- **TEST_FAILURE**: Unit/integration test failures (assertion errors, timeouts, missing mocks)
- **LINT_ERROR**: Linting violations (eslint, golangci-lint, go vet, tsc type checking)
- **BUILD_ERROR**: Build/compilation failures (missing modules, config errors)
- **COMPILATION_ERROR**: Subset of build errors with syntax/type errors detected
- **RUNTIME_ERROR**: Runtime crashes or panics (future — not yet auto-captured)
- **INTEGRATION_ERROR**: Service-to-service communication failures (future — not yet auto-captured)

## Pattern Detection

Before launching sub-agents, the `error-pattern-detector.sh` PreToolUse hook checks for repeated failures
and injects warnings into the agent's context. This happens automatically and requires no user action.

### Warning Threshold

A warning is injected when a service has **3 or more errors of the same type** within the last 24 hours.

### Warning Format

Warnings appear at the start of sub-agent context as:
```
WARNING: KNOWN ERROR PATTERN: {service} has had {N} {TYPE} errors in the last 24h.
  Common cause: {detected context}
  Recommended: {action to take}
```

## Skill Improvement Trigger

When a pattern has 3+ occurrences:
1. The orchestrator should suggest running `/error-analyzer`
2. The analyzer groups patterns by service, type, and root cause
3. It proposes skill updates based on error patterns
4. After user approval, skills are updated to prevent the error class

## Self-Healing Flow

```
Error detected (non-zero exit from test/lint/build)
    |
    v
error-learning.sh captures to JSONL (deduped within 60s)
    |
    v
error-pattern-detector.sh checks on next Agent launch
    |
    v (if 3+ same type in 24h)
Warning injected into sub-agent context
    |
    v (user runs /error-analyzer)
Patterns analyzed -> skill updates proposed
    |
    v (user approves with --apply)
Skills updated -> error class prevented in future
```

## Deduplication

- Errors with the same type + service + fingerprint within 60 seconds are not re-logged
- The fingerprint is an MD5 of the first 100 characters of the error message
- This prevents flooding the log when retrying the same failing command

## Mistake Documentation Template (PDCA)

When an error recurs 3+ times (same type + service pattern), the agent MUST create a formal mistake report
using the Plan-Do-Check-Act template below. This goes beyond the automatic JSONL capture — it forces
root cause analysis and prevention planning.

### When to Create a Mistake Report

- Error pattern detected 3+ times in `error-learning.jsonl` (same `type` + `service`)
- The error-pattern-detector has already injected a warning for this pattern
- The agent (or orchestrator) has context on what caused the recurrence

### Template

```
### Mistake Report: {title}

**What Happened**: {description of the error — what failed, which command, what output}
**Root Cause**: {why it actually happened, not just symptoms — dig past "test failed" to why the test failed}
**Why Missed**: {what check/gate/test should have caught this earlier — was there a missing unit test, a gap in acceptance criteria, a skill that didn't cover this case?}
**Fix Applied**: {what was done to fix it — code change, config update, skill modification}
**Prevention Checklist**:
- [ ] {concrete action to prevent recurrence — e.g., "Add unit test for null input to UserService"}
- [ ] {test or gate to add — e.g., "Add acceptance criterion: grep -c 'nil pointer' = 0"}
- [ ] {skill or rule update — e.g., "Update go-service-patterns to include nil guard pattern"}
**Lesson Learned**: {one sentence takeaway — the most important thing to remember}
```

### Persistence

Save mistake reports to Engram using the bugfix prefix:

```
mem_save(
  title: "Mistake Report: {title}",
  topic_key: "bugfix/{service}/{issue-slug}",
  type: "bugfix",
  scope: "project",
  content: "{full mistake report using template above}"
)
```

### Integration with Error Pattern Detector

The error-pattern-detector hook already warns when 3+ errors of the same type occur in 24 hours.
When an agent sees this warning AND has context to fill in the template, it MUST:

1. Create the mistake report using the template above
2. Save to Engram under `bugfix/{service}/{issue-slug}`
3. Include at least one item in the Prevention Checklist
4. If the prevention action is a test, create the test in the same session

### PDCA Cycle Mapping

| PDCA Phase | Mistake Report Field |
|------------|---------------------|
| **Plan** | Root Cause + Why Missed (understand the problem) |
| **Do** | Fix Applied (implement the fix) |
| **Check** | Prevention Checklist (verify the fix prevents recurrence) |
| **Act** | Lesson Learned (standardize the learning for future sessions) |

## Metrics File Location

`.claude/metrics/error-learning.jsonl` — append-only, one JSON object per line.

To inspect recent errors manually:
```bash
# Last 10 errors
tail -10 .claude/metrics/error-learning.jsonl | jq .

# Errors by service
cat .claude/metrics/error-learning.jsonl | jq -s 'group_by(.service) | map({service: .[0].service, count: length})'

# Errors in last 24 hours
cat .claude/metrics/error-learning.jsonl | jq --argjson cutoff $(date -v-24H +%s) 'select(.timestamp_epoch > $cutoff)'
```
