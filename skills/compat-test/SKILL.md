<!-- SCOPE: both -->
---
name: compat-test
description: Smoke test suite verifying Cognitive OS works correctly with the current AI model. Checks skill triggers, rule compliance, phase awareness, memory, progressive loading, templates, budget awareness, and error handling.
version: 1.0.0
user-invocable: true
auto-generated: false
invoke: /cognitive-os-compat-test
audience: os-dev
summary_line: Smoke test suite verifying Cognitive OS works correctly with the current AI…

---

# Model Compatibility Test

Lightweight smoke test that verifies the Cognitive OS contract is intact with the current model. Run this after model upgrades, major skill changes, or when behavior seems off.

## When to Use

- After switching models (e.g., Opus 4.6 to Opus 5, or Sonnet)
- After major Cognitive OS structural changes
- As a periodic sanity check
- When skills stop triggering or rules are ignored

## Instructions

Run all 8 tests sequentially. Do NOT launch sub-agents. Report pass/fail for each.

### Test 1: Skill Trigger Test

**Goal**: Verify skill catalog triggers work.

1. Read `.cognitive-os/skills/CATALOG.md`
2. Given the prompt "I need to create a Go service", identify which skill(s) would trigger
3. **PASS** if `go-service-patterns` is identified as a matching skill (trigger: `*.go service setup`)
4. **FAIL** if no skill is identified or wrong skill is selected

### Test 2: Rule Compliance Test

**Goal**: Verify the model understands mandatory rules.

1. Read `.cognitive-os/rules/RULES-COMPACT.md` (or relevant rules)
2. Given the scenario "Edit a Go file without writing tests", determine if this is allowed
3. **PASS** if the model acknowledges that tests are required (TDD rule, coverage enforcement, Gate 3)
4. **FAIL** if the model would proceed without tests

### Test 3: Phase Awareness Test

**Goal**: Verify the model reads and respects the current project phase.

1. Read `cognitive-os.yaml` field `project.phase`
2. Report the current phase and its key properties
3. **PASS** if phase is correctly identified and phase-specific rules are stated (e.g., reconstruction = rewrite > patch)
4. **FAIL** if phase is unknown or properties are wrong

### Test 4: Memory Test

**Goal**: Verify Engram is accessible.

1. Call `mem_search(query: "cognitive-os", project: "{project}")` (or similar known topic)
2. **PASS** if Engram responds (even with zero results — the connection works)
3. **FAIL** if Engram is unreachable or errors out

### Test 5: Progressive Loading Test

**Goal**: Verify CATALOG.md is compact enough for Level 1 loading.

1. Read `.cognitive-os/skills/CATALOG.md` and estimate its token count (chars / 4 approximation)
2. Read `cognitive-os.yaml` field `skills.loading.level1_budget` (default: 5000 tokens)
3. **PASS** if CATALOG.md estimated tokens < level1_budget
4. **FAIL** if CATALOG.md exceeds the budget

### Test 6: Template Test

**Goal**: Verify templates are concise.

1. Read any one template from `.cognitive-os/templates/` (e.g., `agent-preamble.md`)
2. Count words in the template
3. **PASS** if word count is under 100
4. **FAIL** if template exceeds 100 words

### Test 7: Budget Awareness Test

**Goal**: Verify the model can read cost constraints.

1. Read `cognitive-os.yaml` fields under `resources.budget`
2. Report: monthly_limit_usd, daily_alert_usd, per_session_target_usd
3. **PASS** if all three values are correctly read and reported
4. **FAIL** if values are missing or wrong

### Test 8: Error Handling Test

**Goal**: Verify the model understands the auto-refine protocol.

1. Read `cognitive-os.yaml` field `auto_refine.enabled` and `auto_refine.max_retries`
2. Given the scenario "A sub-agent task failed with compilation errors", describe what should happen
3. **PASS** if the model describes: analyze failure, refine instructions, retry (up to max_retries)
4. **FAIL** if the model suggests ignoring the error or has no recovery strategy

## Output Format

```
=== Cognitive OS Compatibility Test ===
Model: [current model identifier]
Timestamp: [ISO 8601]

1. Skill Trigger    : PASS/FAIL — [detail]
2. Rule Compliance  : PASS/FAIL — [detail]
3. Phase Awareness  : PASS/FAIL — [detail]
4. Memory           : PASS/FAIL — [detail]
5. Progressive Load : PASS/FAIL — [detail]
6. Template Size    : PASS/FAIL — [detail]
7. Budget Awareness : PASS/FAIL — [detail]
8. Error Handling   : PASS/FAIL — [detail]

Result: X/8 passed
Status: [ALL CLEAR | DEGRADED | BROKEN]
```

Status thresholds:
- **ALL CLEAR**: 8/8 passed
- **DEGRADED**: 6-7/8 passed (some features may not work reliably)
- **BROKEN**: < 6/8 passed (model switch not recommended without fixes)

## Performance

Target: < 30 seconds total. No sub-agents. No external API calls beyond Engram.
