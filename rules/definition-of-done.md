# Definition of Done (DoD) by Task Complexity

## Purpose

Every task has a Definition of Done proportional to its complexity. Agents MUST classify task complexity BEFORE starting work and CANNOT mark a task as done unless ALL DoD criteria for that level pass.

## Complexity Classification

Agents classify tasks at the START of work. If unsure, classify UP (safer).

### Trivial
**Signal**: Single file, < 20 lines changed, clear fix (typo, rename, config tweak).
**Examples**: Fix a typo in a comment, update a port number, rename a variable.

| Criterion | Description | Verification |
|-----------|-------------|--------------|
| `code_compiles` | Code builds without errors | `go build ./...` or `yarn build` exits 0 |
| `no_lint_errors` | No new lint violations | `golangci-lint run ./...` or `eslint` exits 0 |

### Small
**Signal**: 1-3 files, single service, well-understood change.
**Examples**: Add a DTO field, fix a bug in one use case, add a new endpoint to existing controller.

| Criterion | Description | Verification |
|-----------|-------------|--------------|
| `code_compiles` | Code builds without errors | Build command exits 0 |
| `unit_tests_pass` | Existing tests still pass | `go test ./... -short` or `yarn test` exits 0 |
| `no_lint_errors` | No new lint violations | Lint command exits 0 |

### Medium
**Signal**: Multi-file changes, single service, new feature or significant refactor.
**Examples**: New use case with controller/DTO/mapper, add Kafka consumer, new API endpoint with tests.

| Criterion | Description | Verification |
|-----------|-------------|--------------|
| `code_compiles` | Code builds without errors | Build command exits 0 |
| `unit_tests_added` | NEW tests written for new code | Verify new `*_test.go` or `*.spec.ts` files exist |
| `coverage_maintained` | Coverage not decreased | `go test -coverprofile=coverage.out` >= threshold |
| `lint_clean` | Zero lint issues | Lint command exits 0 |
| `docs_updated` | Relevant docs updated if applicable | Check for modified `.md` files |

### Large
**Signal**: Multi-service changes, new integration, cross-cutting concerns.
**Examples**: New external provider integration, cross-service feature, new SDK package.

| Criterion | Description | Verification |
|-----------|-------------|--------------|
| `readiness_check_pass` | `/readiness-check` passes | Readiness skill returns PASS |
| `code_compiles` | All affected services build | Build commands exit 0 |
| `unit_tests_80_percent` | Coverage >= 80% on new code | Coverage report shows >= 80% |
| `integration_tests` | Integration tests written and pass | `go test -tags=integration` or equivalent |
| `architecture_compliance` | No architecture violations | No non-standard framework imports, clean arch layers respected |
| `docs_updated` | Architecture docs and READMEs updated | Modified `.md` files present |
| `adversarial_review` | Adversarial review completed | Output contains BLOCKER/CONCERN/SUGGESTION labels |

### Critical
**Signal**: Security changes, payment flows, auth changes, data migrations, smart contracts.
**Examples**: Payment endpoint, auth flow change, database migration, encryption change.

| Criterion | Description | Verification |
|-----------|-------------|--------------|
| `readiness_check_pass` | `/readiness-check` passes | Readiness skill returns PASS |
| `code_compiles` | All affected services build | Build commands exit 0 |
| `unit_tests_80_percent` | Coverage >= 80% on new code | Coverage report |
| `integration_tests` | Integration tests written and pass | Integration test command |
| `architecture_compliance` | No architecture violations | Compliance check |
| `docs_updated` | Full documentation updated | Modified `.md` files |
| `adversarial_review` | Adversarial review completed | BLOCKER/CONCERN/SUGGESTION in output |
| `security_review` | Security implications reviewed | Explicit security assessment in output |
| `idempotency_verified` | Financial ops are idempotent | Transaction ID dedup tested |
| `audit_trail_present` | All ops logged with who/when/what | Audit log entries verified |
| `rollback_tested` | Rollback procedure documented and tested | Rollback steps executed successfully |

## Scale-Adaptive Intelligence Mapping

From `control-manifest.md`, the complexity classification maps directly to workflow:

| Complexity | Workflow | DoD Enforcement |
|------------|----------|-----------------|
| Trivial | Do it directly, no workflow | DoD auto-checked by hook |
| Small | Do it, consider `/plan-bug` or `/plan-feature` | DoD checked on completion |
| Medium | Plan first (`/plan-feature`), then implement | DoD checked, missing items block completion |
| Large | SDD workflow required (`/sdd-new`) | DoD checked + adversarial review required |
| Critical | SDD + security review + rollback testing | DoD checked + all gates must pass |

## Agent Protocol

1. **BEFORE starting**: Classify complexity. State it explicitly: "Complexity: [level]"
2. **DURING work**: Track which DoD criteria are being addressed
3. **BEFORE claiming done**: Run `/dod-check` or verify each criterion manually
4. **If criteria not met**: Do NOT claim done. State what is missing and fix it.

## Phase Modifiers

The project phase (from `cognitive-os.yaml`) modifies DoD enforcement:

| Phase | Behavior |
|-------|----------|
| `reconstruction` | Missing criteria = WARNING (proceed with caution) |
| `stabilization` | Missing criteria = WARNING (proceed with caution) |
| `production` | Missing criteria = BLOCK (cannot proceed) |
| `maintenance` | Missing criteria = BLOCK (cannot proceed) |

## Contextual Trigger

This rule is loaded when: task completion, "done", "complete", "finished", DoD check requested.
