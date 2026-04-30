<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Confidence Gate Protocol

## Purpose

Prevent low-confidence agent results from propagating through the system. When an agent reports very low trust scores, this gate blocks downstream actions in production/maintenance phases and warns in reconstruction/stabilization phases.

## Relationship to Trust Score Validator

| Hook | Purpose | Behavior |
|------|---------|----------|
| `trust-score-validator.sh` | Validates Trust Report presence, extracts and logs scores | Advisory only (never blocks) |
| `confidence-gate.sh` | Enforces minimum confidence thresholds | Blocks in production/maintenance |

The confidence gate complements the trust score validator. The validator ensures reports exist and logs them. The gate enforces minimum thresholds.

## Thresholds

| Score Range | Severity | Reconstruction/Stabilization | Production/Maintenance |
|-------------|----------|------------------------------|----------------------|
| >= 50 | Normal | Pass | Pass |
| 30-49 | Low | WARN (pass) | BLOCK (exit 2) |
| < 30 | Critical | WARN (pass) | BLOCK (exit 2) |

## Phase-Aware Behavior

| Phase | Behavior |
|-------|----------|
| `reconstruction` | Warn only — agents are expected to have lower confidence during rebuild |
| `stabilization` | Warn only — confidence improves as standards settle |
| `production` | Block on score < 50 — low confidence means human must verify |
| `maintenance` | Block on score < 50 — minimal risk tolerance |

## What Triggers the Gate

The gate activates when:
1. An Agent/task/delegate tool call completes
2. The output contains a Trust Report with an extractable score
3. The score is below 50

## Gate Messages

### Score < 30 (Critical)
```
CRITICAL: Agent has very low confidence (Score: XX/100).
Do NOT proceed without human review.
```

### Score 30-49 (Low)
```
CONFIDENCE GATE: Agent confidence is very low (XX/100).
Human review required before proceeding.
```

## Metrics

Gate activations are logged to `.cognitive-os/metrics/confidence-gates.jsonl`:

```json
{
  "timestamp": "ISO-8601",
  "agent": "agent-name",
  "score": 35,
  "severity": "critical|low",
  "action": "warn|block",
  "phase": "reconstruction|stabilization|production|maintenance"
}
```

## Integration with Quality System

The confidence gate is the last line of defense in the quality chain:

```
Agent executes task
    |
    v
Agent outputs Trust Report (mandatory per trust-score.md)
    |
    v
trust-score-validator.sh extracts and logs score
    |
    v
confidence-gate.sh enforces minimum threshold
    |
    v
dod-gate.sh checks Definition of Done
    |
    v
auto-verify.sh runs acceptance criteria
```

## Hook Details

- **Hook**: `hooks/confidence-gate.sh`
- **Type**: PostToolUse
- **Matcher**: Agent
- **Exit code**: 0 (pass/warn) or 2 (block in production/maintenance)
- **Performance**: < 200ms
