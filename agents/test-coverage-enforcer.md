---
name: test-coverage-enforcer
description: Auto-checks test coverage when source files change, reports per-package coverage, suggests missing tests
triggers:
  - file_pattern: "**/*.go"
    exclude: ["*_test.go", "*/mocks/*"]
  - file_pattern: "**/*.ts"
    exclude: ["*.spec.ts", "*.test.ts", "*/mocks/*"]
---

# Test Coverage Enforcer Agent

## Trigger

This agent activates when source files (non-test) are modified.

## Behavior

### 1. Identify Affected Service

From the changed file path, extract the service name by matching against:
- `cognitive-os.yaml -> project.infrastructure.services` for service-to-path mappings
- Or detect from directory structure

### 2. Read Threshold

Read `cognitive-os.yaml` from project root:
```yaml
quality:
  coverage:
    minimum: 80        # This is the threshold
    per_package: true
    exclude:
      - "*/mocks/*"
      - "*/test/*"
      - "cmd/*"
```

If `cognitive-os.yaml` is missing, default to 80%.

### 3. Run Coverage

Detect the project language and run the appropriate coverage command:

**Go:**
```bash
go test -coverprofile=/tmp/{service}-coverage.out ./... 2>&1
go tool cover -func=/tmp/{service}-coverage.out
```

**Node.js (Jest):**
```bash
npx jest --coverage --no-cache
```

**Java (Gradle):**
```bash
./gradlew test jacocoTestReport
```

### 4. Parse Results

Extract:
- Overall service coverage (total line)
- Per-package/module coverage
- Functions/methods with 0% coverage

### 5. Apply Exclusions

Skip packages matching exclude patterns from config.

### 6. Report

#### If coverage >= threshold:
```
Coverage OK: {service} at {X}% (threshold: {threshold}%)
```

#### If coverage < threshold:
Report with three sections:

**Summary:**
```
WARNING: {service} coverage is {X}% (below {threshold}% threshold)
```

**Per-package breakdown:**
```
| Package | Coverage | Status |
|---------|----------|--------|
| {pkg}   | {X}%     | {PASS/FAIL} |
```

**Suggested tests (top 10 uncovered functions):**
```
Missing tests for {service}:
  1. Test{FunctionName} -- {package}.{FunctionName} (file:line)
  ...
```

### 7. No-Test Detection

If the service has zero test files:
```
WARNING: {service} has NO test files.
Create test files alongside source.
```

## Configuration Source

All thresholds and exclusions come from `cognitive-os.yaml`. This makes the system configurable per project. Industry presets available: fintech (80%), healthcare (90%), ecommerce (70%), startup (50%).
