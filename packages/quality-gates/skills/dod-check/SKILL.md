---
name: dod-check
command: /dod-check
description: Verify Definition of Done criteria for a task at a given complexity level
trigger: Manual invocation or before claiming task completion
inputs:
  - task_description (optional): What was done
  - complexity (optional): trivial | small | medium | large | critical. Auto-classified if omitted.
outputs:
  - verdict: PASS | PARTIAL | FAIL
  - criteria_results: per-criterion pass/fail with evidence
  - missing_items: what needs to be done to pass
audience: project
---

# Definition of Done Check

## Purpose

Verify that all DoD criteria for a task's complexity level are met before marking it complete. Can auto-classify complexity if not provided.

## When to Run

- **Before claiming done**: Agent runs this to verify completion criteria
- **Manual**: User invokes `/dod-check [description]`
- **Post-completion audit**: Verify a recently completed task meets standards

## Auto-Classification

If complexity is not provided, classify based on these signals:

| Signal | Complexity |
|--------|-----------|
| Single file, < 20 lines, typo/rename/config | `trivial` |
| 1-3 files, single service, bug fix | `small` |
| Multi-file, single service, new feature | `medium` |
| Multi-service, new integration, SDK work | `large` |
| Security, payments, auth, data migration | `critical` |

When unsure, classify UP (safer).

## Verification Procedure

### Step 1: Classify Complexity

State the complexity level explicitly:
```
Complexity: [level]
Rationale: [why this level]
```

### Step 2: Run Verification Commands

For each criterion at the classified level, run the appropriate verification command.

#### code_compiles
```bash
# Go services
cd [service-dir] && go build ./...

# NestJS services
cd [service-dir] && yarn build

# Spring Boot services
cd [service-dir] && ./gradlew compileJava

# Express services
cd [service-dir] && yarn build
```
**PASS if**: Exit code 0, no compilation errors.

#### unit_tests_pass / unit_tests_added
```bash
# Go
go test ./... -short -v

# NestJS / Express
yarn test

# Spring Boot
make utest
```
**PASS if**: All tests pass (0 failures). For `unit_tests_added`: new test files exist for new code.

#### unit_tests_80_percent
```bash
# Go
go test ./... -coverprofile=coverage.out
go tool cover -func=coverage.out | grep total

# NestJS
yarn test:cov
```
**PASS if**: Total coverage >= 80%.

#### coverage_maintained
Compare current coverage with baseline. Coverage must not decrease.

#### lint_clean / no_lint_errors
```bash
# Go
golangci-lint run ./...

# TypeScript
yarn lint
```
**PASS if**: Zero issues reported.

#### docs_updated
Check if any `.md` files were modified in the changeset:
```bash
git diff --name-only HEAD | grep -E '\.md$'
```
**PASS if**: At least one doc file updated (for medium+), OR no docs needed (trivial/small).

#### architecture_compliance
```bash
# Check for forbidden imports
grep -r "chi\|huma\|echo\|fiber" --include="*.go" [changed-files]

# Check clean arch violations
grep -r "internal/infrastructure" --include="*.go" [domain-files]
```
**PASS if**: No forbidden imports, no layer violations.

#### integration_tests
```bash
# Go
go test ./... -tags=integration

# NestJS
yarn test:e2e

# Spring Boot
make itest
```
**PASS if**: Integration tests exist and pass.

#### adversarial_review
Check that an adversarial review was performed with findings labeled as BLOCKER, CONCERN, or SUGGESTION.
**PASS if**: Review output exists with labeled findings, all BLOCKERs resolved.

#### readiness_check_pass
Run `/readiness-check` skill.
**PASS if**: Verdict is PASS.

#### security_review
Check for explicit security assessment in the work output.
**PASS if**: Security implications documented, no unmitigated vulnerabilities.

#### idempotency_verified
Check that financial operations use transaction IDs and handle duplicates.
**PASS if**: Transaction ID deduplication tested.

#### audit_trail_present
Check that operations log who, when, what, and amount.
**PASS if**: Audit log entries verified in test output.

#### rollback_tested
Check that rollback procedure is documented and tested.
**PASS if**: Rollback steps documented and executed successfully.

### Step 3: Report Results

Format the report as:

```
## DoD Check: [PASS | PARTIAL | FAIL]
Complexity: [level]
Phase: [current phase]
Enforcement: [WARN | BLOCK]

### Criteria Results
| Criterion | Status | Evidence |
|-----------|--------|----------|
| ... | PASS/FAIL | [what was checked] |

### Missing Items (if any)
- [criterion]: [what needs to be done]

### Verdict
[PASS]: All criteria met. Task is done.
[PARTIAL]: N/M criteria met. Address missing items.
[FAIL]: Critical criteria missing. Cannot mark as done.
```

## Phase Enforcement

| Phase | Missing Criteria |
|-------|-----------------|
| `reconstruction` | WARNING — proceed with caution |
| `stabilization` | WARNING — proceed with caution |
| `production` | BLOCK — must fix before done |
| `maintenance` | BLOCK — must fix before done |
