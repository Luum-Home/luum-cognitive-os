# Anti-Hallucination Defense System

> Layered defense preventing agents from fabricating files, inventing test results, and claiming success when failing.
> Author: luum | Updated: 2026-03-27

## 1. The Problem

LLMs hallucinate. They invent files that do not exist, fabricate test results, claim builds succeeded when they did not, and report "done" when work is incomplete. Humans also make errors: confirmation bias, optimistic estimation, unchecked assumptions. Both failure modes are unacceptable for production systems.

The core challenge: an agent's output is text, and text can say anything. Without independent verification against ground truth, there is no way to distinguish a truthful report from a confident hallucination.

## 2. Cloud-Native Analogy

Every anti-hallucination layer maps to a well-understood cloud infrastructure pattern:

| Cloud Pattern | Agent OS Pattern | Implementation |
|---|---|---|
| ALB / Load Balancer | Multi-model verification | `lib/cross_verifier.py` |
| Health Checks | Output validation against filesystem | `lib/ground_truth.py` |
| Auto-scaling | Model escalation on low confidence | `lib/capability_levels.py` |
| Circuit Breaker | Retry exhaustion then escalate | `hooks/auto-rollback-trigger.sh` |
| Canary Deploy | Dry-run + sandbox sampling | `hooks/dry-run-preview.sh` |
| WAF | Input filtering for vague prompts | `hooks/clarification-gate.sh` |
| Multi-AZ | Multi-model consensus | `lib/planning_poker.py` |
| Chaos Engineering | Red teaming with Promptfoo | Promptfoo integration |
| Bulkhead | Blast containment per task | `hooks/scope-proportionality.sh` |
| Monitoring/Alerting | Post-mortem calibration | `lib/estimation_calibrator.py` |

## 3. The 10-Layer Defense Stack

All anti-hallucination layers (existing + new), ordered by pipeline stage:

| # | Layer | Type | What It Catches | Implementation |
|---|---|---|---|---|
| 1 | Clarification Gate | PRE -- BLOCK | Vague inputs that lead to hallucinated scope | `hooks/clarification-gate.sh` |
| 2 | Blast Radius | PRE -- WARN | Scope inflation (claiming small when large) | `hooks/blast-radius.sh` |
| 3 | Scope Proportionality | POST -- BLOCK | Fix-to-rewrite expansion | `hooks/scope-proportionality.sh` |
| 4 | Ground Truth Checker | POST -- VERIFY | Fabricated files, fake test counts | `lib/ground_truth.py` |
| 5 | Cross-Verification | POST -- VERIFY | Second model catches first model's errors | `lib/cross_verifier.py` |
| 6 | Trust Score | POST -- REPORT | Self-reported confidence tracking | `hooks/trust-score-validator.sh` |
| 7 | Confidence Gate | POST -- BLOCK | Low confidence results in production | `hooks/confidence-gate.sh` |
| 8 | Assumption Tracker | POST -- WARN | Hidden assumptions that may be wrong | `hooks/assumption-tracker.sh` |
| 9 | Estimation Calibration | LOOP -- ADJUST | Systematic bias correction over time | `lib/estimation_calibrator.py` |
| 10 | Planning Poker | LOOP -- CONSENSUS | Multi-model divergence detection | `lib/planning_poker.py` |

### Layer 4: Ground Truth Checker (NEW)

**Purpose**: Verify that claims made by agents are actually true by checking the filesystem.

**How it works**: Extracts verifiable claims from agent output using regex patterns ("Created file X", "N tests passing", "Build succeeded"), then checks each claim against reality. File claims are verified via `os.path.exists()`. Function claims are verified via grep. Count claims are flagged for manual verification.

**What it catches**: An agent that says "Created `src/auth.go`" when the file does not exist. An agent that says "15 tests passing" when only 12 tests are collected.

**What it does NOT catch**: Correct file creation with wrong content (file exists but is empty or broken). Claims about runtime behavior that cannot be verified statically.

**Output**: A hallucination score from 0.0 (all claims true) to 1.0 (all claims false), plus a markdown table of verification results.

**Configuration**: `lib/ground_truth.py` (library), `hooks/claim-validator.sh` (hook).

### Layer 5: Cross-Verification (NEW)

**Purpose**: Use a DIFFERENT model to independently verify the primary model's output. The verifier does not see the original model's self-assessment.

**How it works**: Builds a verification prompt asking the second model to check task alignment, identify suspicious claims, and rate confidence. Parses the structured response for agreement, confidence level, and specific discrepancies.

**What it catches**: Errors that the primary model is blind to. A different model may notice file paths that look implausible, test counts that seem wrong, or claims that do not match the task.

**What it does NOT catch**: Errors that all models share (common training biases). If both models believe an incorrect pattern is correct, cross-verification will not catch it.

**Cost**: Approximately $0.002 per verification using haiku. Higher-tier models available for critical tasks.

**Configuration**: `lib/cross_verifier.py` (library).

### Claim Validator Hook (NEW)

**Purpose**: PostToolUse hook on Agent that runs ground truth file checks automatically after every agent completion.

**How it works**: Extracts file creation/modification claims from agent output, checks if each claimed file exists on disk. Logs results to `metrics/hallucinations.jsonl`.

**Phase behavior**:
- Reconstruction/Stabilization: WARN on hallucination (exit 0)
- Production/Maintenance: BLOCK on hallucination (exit 2)

**Configuration**: `hooks/claim-validator.sh`, registered in `settings.json`.

## 4. When to Use What

Decision tree based on task complexity:

```
Task received
    |
    +-- Trivial (single file, <20 lines)?
    |     -> Ground truth only (claim-validator hook, automatic)
    |
    +-- Small (1-3 files, single service)?
    |     -> Ground truth (automatic)
    |     -> Trust score review
    |
    +-- Medium (multi-file, new feature)?
    |     -> Ground truth (automatic)
    |     -> Cross-verification if trust score < 70
    |
    +-- Large (multi-service, integration)?
    |     -> Ground truth (automatic)
    |     -> Cross-verification (mandatory)
    |     -> Planning poker for estimates
    |
    +-- Critical (security, payments, migration)?
          -> Ground truth (automatic)
          -> Cross-verification with sonnet (mandatory)
          -> Planning poker (mandatory)
          -> Manual human review
```

## 5. Cost Analysis

What each layer costs in tokens and money:

| Layer | Token Cost | USD Cost | Notes |
|---|---|---|---|
| Clarification Gate | 0 | $0 | Regex-based, runs in bash |
| Blast Radius | 0 | $0 | Regex-based, runs in bash |
| Scope Proportionality | 0 | $0 | Line count comparison |
| Ground Truth Checker | 0 | $0 | Filesystem checks only |
| Cross-Verification (haiku) | ~2K in + ~500 out | ~$0.002 | Cheapest model verification |
| Cross-Verification (sonnet) | ~2K in + ~500 out | ~$0.014 | For critical tasks |
| Trust Score Validator | 0 | $0 | Regex extraction from output |
| Confidence Gate | 0 | $0 | Threshold comparison |
| Assumption Tracker | 0 | $0 | Regex pattern matching |
| Estimation Calibration | 0 | $0 | Statistical computation |
| Planning Poker (3 models) | ~6K in + ~1.5K out | ~$0.01 | 3 independent estimates |

Total cost for maximum verification (all layers): approximately $0.03 per task.

## 6. Metrics

All anti-hallucination events are logged to `.cognitive-os/metrics/`:

| Layer | Metrics File |
|---|---|
| Ground Truth / Claim Validator | `hallucinations.jsonl` |
| Cross-Verification | `cross-verification.jsonl` (future) |
| Trust Score | `trust-scores.jsonl` |
| Confidence Gate | `confidence-gates.jsonl` |
| Assumption Tracker | `assumptions.jsonl` |
| Estimation Calibration | `estimation-calibrator.jsonl` |
| Planning Poker | `planning-poker.jsonl` |

### Aggregate Analysis

To assess overall hallucination rates:

```bash
# Hallucination rate over time
cat .cognitive-os/metrics/hallucinations.jsonl | \
  jq -s 'map(select(.hallucinations > 0)) | length as $h | length as $t | {hallucination_events: $h, total_events: ($t), rate: (if $t > 0 then ($h / $t * 100) else 0 end)}'

# Average hallucinations per event
cat .cognitive-os/metrics/hallucinations.jsonl | \
  jq -s '{avg_hallucinations: (map(.hallucinations) | add / length), avg_verified: (map(.verified) | add / length)}'
```

## 7. Integration with Safety Mesh

The anti-hallucination layers integrate into the existing 9-layer safety mesh, extending it to 12 layers. The claim-validator hook runs in the PostToolUse chain alongside existing hooks:

```
Agent completes
    |
    v
[existing] completion-gate.sh
    |
    v
[NEW] claim-validator.sh -- Are file claims true?
    |
    v
[existing] trust-score-validator.sh
    |
    v
[existing] confidence-gate.sh
    |
    v
... (remaining hooks)
```

The ground truth checker and cross-verifier are available as Python library functions that can be called from skills, the orchestrator, or other automation.
