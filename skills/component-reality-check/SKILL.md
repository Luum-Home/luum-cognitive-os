---
name: component-reality-check
description: 'Use when you need this Cognitive OS skill: Measure declared-but-unwired
  vs real agentic primitives of the SO using the audit classifier script. Reports
  REAL / DORMANT / UNWIRED / METADATA counts + worst offenders + trend. SO-only.;
  do not use when a narrower skill directly matches the task.'
invoke: /component-reality-check
version: 1.0.0
last-updated: 2026-04-24
audience: os-dev
tags:
- audit
- dogfooding
- metrics
- wiring
summary_line: Classify every SO agentic primitive into REAL / DORMANT / UNWIRED /
  METADATA — catch drift between declarations and observable runtime.
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bcomponent[- ]?reality[- ]?check\b
  confidence: 0.95
- pattern: \b(real|dormant|unwired)\s+(vs\.?\s+)?(dormant|unwired|declared)\b
  confidence: 0.85
- pattern: \b(agentic\s+)?primitives?\s+(audit|reality|classification|classify)\b
  confidence: 0.8
routing_intents:
- intent: component_reality_check_request
  description: User asks to measure declared-but-unwired vs real agentic primitives
    of the SO using the audit classifier script. Reports REAL / DORMANT / UNWIRED
    / METADATA counts + worst offenders + trend. SO-only.
  confidence: 0.85
triggers:
- component-reality-check
- /component-reality-check
- Agentic Primitive Reality Check
- Classify every SO agentic primitive into REAL / DORMANT / UNWIRED / METADATA — catch
  drift between declarations and obse
---
<!-- SCOPE: os-only -->
# Agentic Primitive Reality Check

Run the SO against itself: how many declared agentic primitives (hooks, lib,
scripts, skills) actually FIRE at runtime, vs how many are declared
but unused?

Not the same as the dogfood-score (composite across 7 dimensions). This
skill is the drill-down into dimension 3 (hook wiring) + extends to
lib, scripts, and skills directories. Use when you want the raw number, not the composite.

Today (2026-04-24 baseline): **27.7% REAL / 64.5% Dormant+Unwired**.

## Invocation

```
/component-reality-check                 # full run, default --dry-run (no persistence)
/component-reality-check --persist       # write JSONL record to .cognitive-os/metrics/aspirational-audit.jsonl for trend
/component-reality-check --strict        # exit 1 if dormant_aspirational_ratio > 0.40
/component-reality-check --worst N       # show top N worst offenders (default 10)
/component-reality-check --trend         # compare against last persisted run
```

## What it measures

The classifier `scripts/aspirational_audit.py` scans every hook, lib
module, script, and skill and assigns one of four labels:

| Label | Criterion |
|---|---|
| **REAL** | Observable runtime use in 7-30d window: JSONL output, caller references, hook firing events, or test invocation |
| **DORMANT** | Code exists and parses; no observable use in the window |
| **`ASPIRATIONAL`** | References missing dependencies OR explicitly marked `FUTURE` / `TODO` |
| **METADATA** | Intentional non-behavioural artifact (shim, lib helper, deprecated stub) |

## Instructions

When invoked:

1. Run:
   ```bash
   uv run python3 scripts/aspirational_audit.py --dry-run --json
   ```
   (omit `--dry-run` if user passed `--persist`).

2. Parse the JSON output and present:
   - **Header**: total agentic primitives, measurement window
   - **Counts table**: each label with count + percentage
   - **Ratio**: `dormant_aspirational_ratio` — critical metric (target <0.40 per ADR-XX if defined)
   - **Worst offenders**: top N (default 10) with path, type, and reason (e.g., "no JSONL output in 30d", "references missing module X")
   - **Recent cold-start note**: any agentic primitive with mtime < 7d is expected to be DORMANT; flag those separately so they don't skew the verdict

3. **If `--trend`**: read previous record from `.cognitive-os/metrics/aspirational-audit.jsonl` and report delta (REAL +N, Dormant -N). Flag any newly-DORMANT agentic primitive.

4. **If `--strict` and ratio > 0.40**: exit with non-zero code so CI can gate on it.

5. **Next steps section** (always include): suggest actions per category:
   - DORMANT >180 days: candidate for `docs/99-Archive/archive/` or promotion with behavioral test.
   - `ASPIRATIONAL`: either implement the missing dependency OR remove the reference.
   - Newly added (<7d): give it time; re-check next week.

## Example output

```
Agentic Primitive Reality Check — 2026-04-24
Measurement window: 7-30 days

| Label        | Count | %      |
|--------------|-------|--------|
| REAL         |   160 |  27.7% |
| DORMANT      |   305 |  52.8% |
| ASPIRATIONAL |    68 |  11.8% |
| METADATA     |    45 |   7.8% |
| Total        |   578 |        |

Dormant+Aspirational ratio: 0.645 (target <0.400)
Status: 🔴 ABOVE TARGET

Worst offenders (top 10):
  1. hooks/adr-detector.sh       DORMANT  no events 30d
  2. hooks/agent-bus-monitor.sh  DORMANT  no events 30d
  ... (8 more)

Cold-start (added <7d, DORMANT expected):
  - hooks/agent-quota-advisor.sh (age: 3d, ADR-056 L1)
  - hooks/agent-quota-redirect.sh (age: 3d, ADR-056 L2)

Delta vs last run (2026-04-17):
  REAL: +12   DORMANT: -8   ASPIRATIONAL: +3   Total: +7

Next steps:
  - DORMANT >180d: 47 candidates for archive/promotion (see --worst 50)
  - ASPIRATIONAL: 68 to resolve (implement deps OR remove refs)
  - Cold-start: 2 hooks acceptable, re-check 2026-05-01
```

## Artifacts

- `.cognitive-os/metrics/aspirational-audit.jsonl` — trend record (append-only, `--persist`)
- `.cognitive-os/reports/component-reality-<ts>.md` — human-readable snapshot (optional, `--report`)

## Related

- `scripts/aspirational_audit.py` — underlying classifier (SCOPE: os-only)
- `scripts/weekly-aspirational-audit.sh` — cron wrapper for automatic weekly run
- `skills/dogfood-score` (in progress) — composite metric; this skill is a drill-down
- ADR-031 / ADR-041 — continuous classifier design (supersedes one-shot `dead-weight-audit` plan)
- Engram: `audit/aspirational-real` — historical trend

## Contextual Trigger

SO-only. Use after adding/removing agentic primitives, or on a weekly cadence
via `weekly-aspirational-audit.sh`. Adopting projects use their own
`/dod-check` or `/readiness-check`, not this skill.
