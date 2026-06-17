---
name: epistemic-review
version: 1.0.0
description: Use when a task needs model-agnostic skeptical review, claim verification, interested-witness detection, evidence ranking, or benchmark-gaming audits before trusting a conclusion.
audience: both
platforms:
  - codex
  - claude-code
  - opencode
  - generic-cli
platform_support:
  generic-cli:
    support_level: executable
    evidence:
      - scripts/cos-claim-audit
      - scripts/cos-evidence-rank
      - scripts/cos-benchmark-gaming-audit
      - tests/red_team/portability/test_cos_epistemic_review_primitives.py
routing_patterns:
  - pattern: (/epistemic-review|/claim-audit|/benchmark-gaming-audit|\b(epistemic review|claim audit|interested witness|self[- ]authored benchmark|benchmark gaming|verify claim|refute claim|skeptical audit|humo)\b)
    confidence: 0.93
  - pattern: \b(audita honestamente|verifica claims?|refuta claims?|testigo interesado|afirmacion interesada|auditoria esceptica|auditoria cetica|verificar afirmacao|refutar afirmacao)\b
    confidence: 0.92
routing_intents:
  - intent: epistemic_review_request
    description: User asks the agent to audit a claim honestly, distrust self-interested sources, refute a conclusion, or verify benchmark/productivity claims.
    confidence: 0.92
triggers:
  - /epistemic-review
  - /claim-audit
  - /benchmark-gaming-audit
  - audit honestly
  - verify claim
  - refute claim
  - interested witness
  - benchmark gaming
  - audita honestamente
  - verifica claim
  - refuta claim
  - testigo interesado
  - auditoría escéptica
  - auditoria cética
  - verificar afirmação
---
<!-- SCOPE: both -->
# Epistemic Review

Use this skill when a model must behave skeptically regardless of its native
personality: treat claims as hypotheses, identify interested witnesses, require
stronger evidence for self-authored claims, and record receipts.

## Procedure

1. State the claim as a falsifiable hypothesis.
2. Mark the claim source:
   - `self-authored`, `self-reported`, `project-authored`, or `vendor` means interested witness.
   - `external` or `neutral` can still be wrong, but starts with less incentive bias.
3. Rank evidence before trusting the claim:

   ```bash
   scripts/cos-evidence-rank \
     --evidence "pytest output exit 0" \
     --evidence "self-reported benchmark improvement" \
     --json
   ```

4. Audit the claim with explicit evidence and a bounded verification command:

   ```bash
   scripts/cos-claim-audit \
     --claim "The benchmark proves a real improvement" \
     --source "project benchmark report" \
     --source-interest self-authored \
     --evidence "benchmark report" \
     --verification-command "python3 -m pytest tests/unit -q" \
     --json
   ```

5. For performance/productivity claims, scan for benchmark-gaming signals:

   ```bash
   scripts/cos-benchmark-gaming-audit --path . --json
   ```

6. Final answer rule: separate what was verified now, what is only supported by
   lower-tier evidence, and what remains an open refutation question.

## Evidence hierarchy

1. Source inspection plus tests/build run now.
2. Reproducible command output with exit code and receipt.
3. Commit/diff history that links the change to the claim.
4. Implementation-linked docs or ADRs.
5. Self-reported benchmark or metric.
6. Marketing, aspiration, or unverified narrative.

## Rules

- Do not repeat self-authored audits, benchmarks, or product claims as fact until
  independent verification exists.
- If the source benefits from the claim being true, call it an interested witness
  and lower confidence.
- A failing or missing verification command means the claim is not fully
  supported, even when the prose sounds convincing.
- Benchmark improvements are not quality improvements unless correctness gates
  and source inspection also support the claim.

## Contextual Trigger

Use when the user asks for an honest audit, asks whether something is valuable,
mentions smoke/humo/benchmark gaming, asks whether a claim came from the OS or
model baseline, or wants the same skeptical behavior across Claude, Codex,
OpenCode, and generic CLI/IDE harnesses.
