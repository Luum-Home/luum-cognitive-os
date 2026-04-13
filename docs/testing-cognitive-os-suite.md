# Cognitive OS Test Suite

Comprehensive automated testing for the Cognitive OS infrastructure, behavior, and quality.

## Architecture

The test suite follows a 3-layer pyramid:

```
        /\
       /  \        Layer 3: Quality (LLM-evaluated, promptfoo)
      /    \       - Skill trigger accuracy
     /------\      - Rule compliance
    /        \     Layer 2: Behavior (semi-deterministic)
   /          \    - Hook trigger simulation
  /            \   - Private mode gating
 /--------------\  - Phase system switching
/                \ Layer 1: Infrastructure (deterministic)
| Hooks, Skills, Rules, Config, Docker, Metrics |
\________________________________________________/
```

## Directory Structure

```
.cognitive-os/
  tests/
    infra/                          # Layer 1: deterministic bash tests
      test-hooks.sh                 # Hook existence, permissions, syntax, registration
      test-skills.sh                # SKILL.md existence, frontmatter, catalog sync
      test-rules.sh                 # Rule file existence, RULES-COMPACT.md sync
      test-config.sh                # YAML validation, required fields
      test-docker.sh                # Container status and healthchecks
      test-metrics.sh               # JSONL validation, file sizes
    behavior/                       # Layer 2: behavioral tests with mock inputs
      test-hook-triggers.sh         # Simulate tool events, verify hook output
      test-private-mode.sh          # Flag-based gating (create/remove flag)
      test-phase-system.sh          # Phase switching and rule injection
      test-resource-governor.sh     # Budget enforcement with mock cost data
    quality/                        # Layer 3: LLM-evaluated tests
      promptfoo-config.yaml         # Promptfoo test definitions
      run-quality-tests.sh          # Quality test runner
  scripts/
    test-cognitive-os.sh                # Layer 1 runner only
    test-cognitive-os-full.sh           # Full suite runner (all 3 layers)
  skills/
    cognitive-os-test/SKILL.md          # Skill to invoke via /cognitive-os-test
  metrics/
    test-results.jsonl              # Test run history (appended per run)
```

## Running Tests

### Quick (Layer 1 only)

```bash
bash .cognitive-os/scripts/test-cognitive-os.sh
```

Validates all infrastructure files are present, valid, and consistent.

### Full Suite (Layers 1+2)

```bash
bash .cognitive-os/scripts/test-cognitive-os-full.sh --skip-quality
```

Runs infrastructure checks plus behavioral simulations.

### Complete (All Layers)

```bash
bash .cognitive-os/scripts/test-cognitive-os-full.sh
```

Includes LLM-evaluated quality tests (requires promptfoo and ANTHROPIC_API_KEY).

### Via Skill

```
/cognitive-os-test
```

## Layer Details

### Layer 1: Infrastructure Tests

Fully deterministic. No external dependencies beyond bash, python3, and optionally yq.

| Test | What It Checks |
|------|----------------|
| test-hooks.sh | Files exist, are executable, have valid bash syntax. Registered hooks in settings.local.json map to real files. Detects orphan hooks (on disk, not registered) and phantom hooks (registered, file missing). |
| test-skills.sh | Each skill dir has SKILL.md with YAML frontmatter containing `name` and `description`. All disk skills appear in CATALOG.md and vice versa. |
| test-rules.sh | Each rule .md file is referenced in RULES-COMPACT.md. All RULES-COMPACT references resolve to real files. Rule files are non-empty. |
| test-config.sh | cognitive-os.yaml parses as valid YAML. Required fields exist: project.phase, resources.budget, skills.loading. Squad and customization YAMLs also parse. |
| test-docker.sh | Each service in docker-compose.cognitive-os.yml: checks container status (running/exited/not found) and healthcheck status. Non-blocking (docker failures are warnings). |
| test-metrics.sh | Metrics dir exists. Each .jsonl file has valid JSON per line. Reports line counts and sizes. |

### Layer 2: Behavior Tests

Semi-deterministic. Pipe mock JSON to hooks and verify output patterns.

| Test | What It Checks |
|------|----------------|
| test-hook-triggers.sh | inject-phase-context.sh produces PHASE and GATES for Agent tool, stays silent for Bash. error-learning.sh captures failures and ignores successes. resource-check.sh allows when no cost data. tool-loop-detector.sh runs cleanly. |
| test-private-mode.sh | private-mode-gate.sh allows engram when flag absent, denies when /tmp/claude-private-mode-active exists. metrics-gate suppresses in private mode. Cleans up flag after test. |
| test-phase-system.sh | Temporarily sets phase in cognitive-os.yaml to each of reconstruction/stabilization/production/maintenance. Verifies inject-phase-context outputs phase-appropriate rules. All phases include constitutional gates. Restores original config. |
| test-resource-governor.sh | Creates mock cost-events.jsonl at various spend levels. Verifies: empty = allow, low = allow, 80%+ = downgrade warning, 100%+ = block. Budget thresholds match cognitive-os.yaml config. Restores original cost file. |

### Layer 3: Quality Tests

LLM-evaluated via promptfoo. Requires `promptfoo` installed and `ANTHROPIC_API_KEY` set.

| Test | What It Checks |
|------|----------------|
| Go endpoint creation | Uses the project's declared framework, not non-standard alternatives |
| Handler pattern | Uses CreateHandler/ControllerInterface, not raw c.JSON() |
| DTO location | application/ not domain/dtos/ |
| Code review | Provides substantive feedback, not "looks good" |
| Phase awareness | Knows project is in reconstruction |
| Gate enforcement | Rejects deploy without tests, direct mobile-to-service calls, integrations without mocks |
| Entity patterns | Uses EntityWithID, defines TableName() |
| Cross-service comms | Uses pkg/sdks/, not internal imports |

## Test Results

Results are appended to `.cognitive-os/metrics/test-results.jsonl` with this schema:

```json
{
  "timestamp": "2025-03-22T10:00:00Z",
  "layer1": { "pass": 45, "fail": 0, "warn": 3 },
  "layer2": { "pass": 20, "fail": 1, "skip": 0 },
  "layer3": "passed",
  "total_pass": 65,
  "total_fail": 1,
  "pass_rate": 98
}
```

## Adding New Tests

### Adding an Infrastructure Test

1. Create `tests/infra/test-{name}.sh`
2. Use the standard pattern: `pass()`, `fail()`, `warn()` functions
3. Print summary: `PASS: N`, `FAIL: N`, `WARN: N`
4. Exit 1 on any failure, 0 otherwise
5. It will be auto-discovered by the runner

### Adding a Behavior Test

1. Create `tests/behavior/test-{name}.sh`
2. Use mock JSON piped to hooks via stdin
3. Always clean up temporary state (use `trap ... EXIT`)
4. Use `pass()`, `fail()`, `skip()` pattern

### Adding a Quality Test

1. Add a test case to `tests/quality/promptfoo-config.yaml`
2. Use `contains`, `not-contains`, or `contains-any` assertions
3. Keep prompts focused on one rule/skill at a time
