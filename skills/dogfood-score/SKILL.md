<!-- SCOPE: os-only -->
---
name: dogfood-score
description: Measure the SO's self-build maturity as a composite 0-100 score across test health, skill coverage, hook wiring, ADR discipline, harness portability, commit activity, and doc freshness. Analog to rules/trust-score.md but for the project itself, not for agents.
invoke: /dogfood-score
tag: os-only
model: haiku
audience: os-dev
effort: haiku
summary_line: "Composite 0-100 score measuring SO self-build maturity (tests, skills, hooks, ADRs, portability, activity, docs)."

version: "1.0.0"
platforms: ["claude-code"]
prerequisites: []
routing_patterns:
  - pattern: '\bdogfood[- ]?score\b'
    confidence: 0.95
  - pattern: '\bself[- ]?build\s+maturity\b'
    confidence: 0.85
  - pattern: '\bdogfood\s+(check|metric|measure)\b'
    confidence: 0.8
---

# Dogfood Maturity Score

## Purpose

Replace hand-wave "we're ~80% self-built" with a precise, auditable number.
Each subdimension is measurable from the repo today; no guessing, no network
access, no external tools. The score is deterministic: same repo state →
same number.

This is to the *project* what `rules/trust-score.md` is to an *agent*:
forcing evidence-based self-assessment instead of confident claims.

## Invocation

```bash
# Pretty breakdown
uv run python3 scripts/dogfood_score.py

# JSON for scripting
uv run python3 scripts/dogfood_score.py --json

# Persist to trend file + show delta vs previous run
uv run python3 scripts/dogfood_score.py --trend

# Fail CI if score drops below a floor
uv run python3 scripts/dogfood_score.py --fail-below 70
```

## Dimensions

Weights live at the top of `lib/dogfood_scorer.py` in `DIMENSION_WEIGHTS` —
edit them without touching code.

| Dimension | Weight | What it measures |
|---|---|---|
| test_health | 25 | Pass rate in cached `junit.xml` under `.cognitive-os/reports/test-runs/latest/`. Xfails penalized. |
| skill_coverage | 15 | Fraction of `skills/*/SKILL.md` with a behavioral test file (name-match + asserts present). |
| hook_wiring | 15 | Fraction of `hooks/*.sh` both registered in `.claude/settings.json` AND referenced by a test. |
| adr_discipline | 15 | Fraction of Proposed/Accepted ADRs whose number appears in a test or skill. |
| harness_portability | 10 | Fraction of files under `hooks/`, `scripts/`, `lib/` that do NOT reference `.claude/` or `CLAUDE_PROJECT_DIR`. |
| self_build_activity | 10 | Commit-type mix in last 30 days: healthy if test ≥25% AND docs ≥10% with ≥20 commits. |
| doc_freshness | 10 | Blend of (ADRs whose file refs still exist) and (plans/features/*.md touched in last 90d). |

## Graceful degradation

A dimension whose signal file is missing reports `null` (not `0`) and is
excluded from the weighted sum. The overall score is then marked `partial`.
This prevents false penalties on minimal repos where e.g. `.cognitive-os/plans/`
doesn't exist yet.

## Heuristic caveats

- **skill_coverage**: name-match heuristic. A test file matching the skill
  name is assumed to test that skill. Documented false-positive rate ~5-10%.
- **hook_wiring**: substring match on `settings.json` and tests/ files. A hook
  mentioned only in a comment counts as "tested". Acceptable; the alternative
  is AST parsing every shell file.
- **adr_discipline**: searches for the ADR number (e.g. `ADR-027`) in tests
  and skills. An ADR mentioned only in a docstring still counts — that's
  arguably still "evidence of awareness".

## Related

- `rules/trust-score.md` — analog for agent self-reporting
- `scripts/cos-config-audit.sh` — validates declared config vs wired reality
- `lib/dogfood_scorer.py` — implementation
- `tests/unit/test_dogfood_scorer.py` — unit tests
- `.cognitive-os/metrics/dogfood-score.jsonl` — trend history (populated via `--trend`)
