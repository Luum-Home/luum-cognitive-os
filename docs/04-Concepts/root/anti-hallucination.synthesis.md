---
type: concept-synthesis
source: docs/04-Concepts/root/anti-hallucination.md
provenance: "LLMs and humans both fabricate files, invent test results, and claim success when failing; without independent verification against ground truth there is no way to distinguish truthful reports from confident hallucination."
---

## What it is

A 10-layer, pipeline-ordered defense stack preventing agents from fabricating files, faking test results, or claiming success when work is incomplete — each layer mapped to a cloud-infrastructure analogy (e.g. Ground Truth Checker = Health Checks, Cross-Verification = Multi-AZ consensus).

## Key mechanics

**10 layers** (# | type | catches | file): 1 Clarification Gate (PRE-BLOCK, vague input) `hooks/clarification-gate.sh`; 2 Blast Radius (PRE-WARN, scope inflation) `hooks/blast-radius.sh`; 3 Scope Proportionality (POST-BLOCK, fix-to-rewrite expansion) `hooks/scope-proportionality.sh`; 4 Ground Truth Checker (POST-VERIFY, fabricated files/fake counts) `lib/ground_truth.py`; 5 Cross-Verification (POST-VERIFY, second-model catch) `lib/cross_verifier.py`; 6 Trust Score (POST-REPORT) `hooks/trust-score-validator.sh`; 7 Confidence Gate (POST-BLOCK, low confidence in production) `hooks/confidence-gate.sh`; 8 Assumption Tracker (POST-WARN) `hooks/assumption-tracker.sh`; 9 Estimation Calibration (LOOP-ADJUST) `lib/estimation_calibrator.py`; 10 Planning Poker (LOOP-CONSENSUS) `lib/planning_poker.py`.

**Ground Truth Checker (Layer 4)**: extracts claims via regex ("Created file X", "N tests passing", "Build succeeded"), verifies files via `os.path.exists()`, functions via grep, counts flagged for manual check. Outputs a hallucination score 0.0 (all true) to 1.0 (all false). Does NOT catch correct-creation-wrong-content or unverifiable runtime claims. Hook: `hooks/claim-validator.sh`, logs to `metrics/hallucinations.jsonl`; reconstruction/stabilization = WARN, production/maintenance = BLOCK (exit 2).

**Cross-Verification (Layer 5)**: different model checks task alignment/suspicious claims/confidence without seeing original self-assessment. ~$0.002/verification on haiku. Does not catch shared training biases across models.

**Decision tree by task size**: trivial → ground truth only (automatic); small → +trust score review; medium → +cross-verification if trust score <70; large → +mandatory cross-verification, planning poker; critical (security/payments/migration) → +sonnet cross-verification mandatory, planning poker mandatory, manual human review.

**Cost table**: most layers are $0 (regex/filesystem/statistical); cross-verification haiku ~$0.002, sonnet ~$0.014; planning poker (3 models) ~$0.01. Maximum verification (all layers): ~$0.03/task.

**Metrics files**: hallucinations.jsonl, cross-verification.jsonl (future), trust-scores.jsonl, confidence-gates.jsonl, assumptions.jsonl, estimation-calibrator.jsonl, planning-poker.jsonl — all under `.cognitive-os/metrics/`.

**Pipeline position**: claim-validator.sh runs in PostToolUse chain right after completion-gate.sh, before trust-score-validator.sh and confidence-gate.sh — extending the existing 9-layer safety mesh to 12 layers.

## Relations & where used

`lib/capability_levels.py` (model-escalation on low confidence), `hooks/auto-rollback-trigger.sh` (circuit breaker), `hooks/dry-run-preview.sh` (canary), `hooks/clarification-gate.sh` (WAF), `hooks/scope-proportionality.sh` (bulkhead), `lib/estimation_calibrator.py` (post-mortem calibration). Aggregate hallucination-rate analysis via `jq` over `hallucinations.jsonl`.

## Status / caveats

Updated 2026-03-27. Ground truth and cross-verification are marked "(NEW)" in the source, i.e. recent additions to a pre-existing 9-layer mesh. Ground truth checking cannot verify runtime-behavior claims statically.
