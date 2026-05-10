<!-- SCOPE: both -->
---
name: risk-register
version: 1.0.0
description: "Use when you need this Cognitive OS skill: Scaffold STRIDE-based risk-register.md under docs/03-dominio-riesgo/ with impact/likelihood matrix and 6 seed rows (one per STRIDE category). Idempotent.; do not use when a narrower skill directly matches the task."
invocation: /risk-register --project-dir <path> [--assets "<brief>"] [--overwrite]
user-invocable: true
last-updated: 2026-04-21
audience: project
triggers:
  - risk register
  - STRIDE
  - threat categories
  - impact likelihood
  - risk-register.md
summary_line: Scaffold STRIDE risk register with impact/likelihood matrix idempotently.
model: haiku
platforms: ["claude-code"]
prerequisites: []
routing_patterns:
  - pattern: '\brisk[- ]?register\b'
    confidence: 0.95
  - pattern: '\bstride\s+risk\b'
    confidence: 0.85
  - pattern: '\bscaffold\s+risk\b'
    confidence: 0.75
---

# Risk Register Scaffolder

Scaffolds `docs/03-dominio-riesgo/risk-register.md` with a STRIDE-organized table and an impact × likelihood matrix legend. This is a **template scaffolder**, not a threat-modeling engine — it seeds one row per STRIDE category and expects human/agent fill-in.

## Scope

- Creates or extends ONE file: `<project>/docs/03-dominio-riesgo/risk-register.md`
- Seeds 6 rows (one per STRIDE category) with placeholder IDs `R-01` through `R-06`
- Idempotent via autogen markers (same contract as `/domain-model`)

## Invocation

```
uv run python3 scripts/risk_register.py \
  --project-dir /path/to/adopter-project \
  --assets "user database, API keys, payment processor credentials"
```

## STRIDE categories seeded

1. Spoofing
2. Tampering
3. Repudiation
4. Information Disclosure
5. Denial of Service
6. Elevation of Privilege

## Outputs

- Assets section (verbatim insertion of `--assets`)
- Likelihood / Impact legend (L/M/H)
- Impact × Likelihood classification matrix
- STRIDE threats table (ID, Category, Threat, Likelihood, Impact, Mitigation, Owner, Status)
- Residual risks section

## Idempotency contract

Same as `/domain-model`:
1. First run creates.
2. Re-run replaces autogen block only, preserves content below footer.
3. `--overwrite` replaces everything.
4. Pre-existing file without markers → skipped.

## NOT in scope

- Generating actual threats from asset descriptions (LLM-domain; scaffolder only).
- Scoring risks (L/M/H values are placeholders — human judgement required).

## Verification

```bash
uv run python3 scripts/risk_register.py --project-dir /tmp/test-rr --assets "user db, API keys"
grep -q "STRIDE threats" /tmp/test-rr/docs/03-dominio-riesgo/risk-register.md
grep -cE '^\| R-0[1-6]' /tmp/test-rr/docs/03-dominio-riesgo/risk-register.md   # expect 6
```
