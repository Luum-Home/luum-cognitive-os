<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Anti-Hallucination Rule

## Purpose

Prevent agents from fabricating files, inventing test results, and claiming success when failing. All agent completions are subject to automated claim validation.

## Always Active

### Automatic Claim Validation

The `claim-validator.sh` PostToolUse hook runs on every Agent completion:
- Extracts file creation/modification claims from output
- Verifies each claimed file exists on the filesystem
- Flags test count claims for manual verification
- Logs results to `metrics/hallucinations.jsonl`

### Phase Behavior

| Phase | Hallucination Detected | Action |
|-------|----------------------|--------|
| reconstruction | WARN (exit 0) | Log warning, agent proceeds |
| stabilization | WARN (exit 0) | Log warning, agent proceeds |
| production | BLOCK (exit 2) | Block agent result, require human review |
| maintenance | BLOCK (exit 2) | Block agent result, require human review |

### Cross-Verification

For large/critical tasks, a second model independently verifies the primary model's output via `lib/cross_verifier.py`. The verifier does NOT see the original model's trust score.

| Task Complexity | Cross-Verification Required? |
|----------------|----------------------------|
| trivial/small | No |
| medium | If trust score < 70 |
| large | Yes (mandatory) |
| critical | Yes (mandatory, use sonnet) |

### Ground Truth Library

`lib/ground_truth.py` provides programmatic claim extraction and verification:
- `extract_claims(output)` -- find verifiable claims in text
- `verify_all_claims(output, project_root)` -- check claims against filesystem
- `format_verification_report(results)` -- markdown report with hallucination score

### Metrics

Logged to `.cognitive-os/metrics/hallucinations.jsonl`:
```json
{"timestamp":"ISO","hallucinations":1,"verified":5,"agent":"task description..."}
```

### Integration

- **Trust Score** [`trust-score`]: Ground truth results feed into verification evidence scoring
- **Confidence Gate** [`confidence-gate`]: High hallucination score should lower confidence
- **Completion Gate** [`completion-gate`]: Claim validation runs in the same PostToolUse chain
- **Safety Mesh** [`safety-mesh`]: Layers 4-5 in the 10-layer defense stack

## Contextual Trigger

This rule is always active. The claim-validator hook fires on every Agent completion.
