---
name: cognitive-os-test
description: Run the Cognitive OS automated test suite (infra, behavior, quality)
invoke: /cognitive-os-test
version: 1.0.0
---

# Cognitive OS Test Suite

Run the comprehensive automated test suite for the Cognitive OS.

## What It Does

Executes a 3-layer test pyramid:

1. **Layer 1 — Infrastructure** (deterministic, bash): Validates hooks, skills, rules, config, docker, and metrics files exist and are properly configured.
2. **Layer 2 — Behavior** (semi-deterministic): Simulates hook triggers, private mode, phase system, and resource governor with mock inputs.
3. **Layer 3 — Quality** (LLM-evaluated, optional): Runs promptfoo evals to test skill trigger accuracy, rule compliance, and phase awareness.

## Usage

```
/cognitive-os-test              # Full suite (skips quality if promptfoo unavailable)
/cognitive-os-test --infra-only # Layer 1 only
/cognitive-os-test --skip-quality # Layers 1+2 only
```

## Instructions

When invoked, run the appropriate test script:

### Full suite (default):
```bash
bash "$CLAUDE_PROJECT_DIR/.cognitive-os/scripts/test-cognitive-os-full.sh"
```

### Infra only:
```bash
bash "$CLAUDE_PROJECT_DIR/.cognitive-os/scripts/test-cognitive-os.sh"
```

### Skip quality:
```bash
bash "$CLAUDE_PROJECT_DIR/.cognitive-os/scripts/test-cognitive-os-full.sh" --skip-quality
```

After running, report the summary to the user with:
- Pass rate per layer
- Any failures with details
- Recommendations for fixing failures

## Output

Results are saved to `.cognitive-os/metrics/test-results.jsonl` for trend tracking.
