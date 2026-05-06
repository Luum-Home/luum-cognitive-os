---
adr: "174-bis"
title: Routing-Pattern Prevention Followup — Auto-Generation and Soak-Driven Promotion
status:
  part_a: accepted
  part_b: proposed
date: 2026-05-05
authors: [luum-agent-os]
supersedes: []
cross_references:
  - ADR-133   # auto-skill-generation — same "declare in artifact, derive at runtime" pattern
  - ADR-134   # propose-only self-improvement artifacts
  - ADR-174   # auto-derived primitive routing (parent)
implementation_files:
  - lib/routing_pattern_deriver.py
  - lib/validator_soak_evaluator.py
  - packages/consequence-system/hooks/auto-skill-generator.sh
  - hooks/validator-soak-weekly.sh
  - tests/unit/test_routing_pattern_deriver.py
  - tests/unit/test_auto_skill_generator_routing.py
  - tests/contracts/test_validator_promotion_trigger.py
---

# ADR-174-bis — Routing-Pattern Prevention Followup

## Status

- **Part A**: Accepted
- **Part B**: Proposed (requires soak data before operator approval)

## Context

ADR-174 wired `hooks/skill-md-routing-validator.sh` as an **advisory**
PostToolUse Write hook.  It emits warnings to stderr when a SKILL.md is
written without `routing_patterns:` frontmatter, but does not block the write.

The audit-of-audits (2026-05-05) found 108 skills on disk without
`routing_patterns:`, meaning the prevention was incomplete in two ways:

1. **Generation gap**: `packages/consequence-system/hooks/auto-skill-generator.sh`
   produced SKILL.md files without `routing_patterns:` at all — the very source
   of the problem.
2. **Enforcement gap**: the advisory validator cannot block future writes.

ADR-174-bis closes both gaps.

---

## Part A — Auto-Generation Includes `routing_patterns:`

### Decision

When `auto-skill-generator.sh` fires and templates a new SKILL.md, it now:

1. Calls `python3 -m lib.routing_pattern_deriver --skill-name <slug> --description <desc>`
   to derive 2–3 routing patterns from the skill name and task description.
2. Injects the resulting `routing_patterns:` YAML block into the frontmatter.
3. Also adds `lifecycle_state: sandbox` and `distribution: lab` to the
   generated frontmatter (previously absent).

The deriver (`lib/routing_pattern_deriver.py`) is standard-library-only and
runs in < 200 ms.  If the deriver fails for any reason, the hook falls back
gracefully — the SKILL.md is still written without `routing_patterns:`
(existing behaviour), so the session is never blocked.

### Routing Pattern Heuristics

| Rule | Pattern | Confidence |
|------|---------|-----------|
| 1 | `\b<skill-name>\b` | 0.95 |
| 2 | Hyphen-collapsed variant | 0.85 |
| 3 | Spanish action verb present in description | 0.80 |
| 4 | Two-word keyword combo from description | 0.75 |

Generic words (`create`, `fix`, `test`, `run`, …) are excluded from
consideration as standalone patterns.  Patterns are capped at 3 per skill.

### Latency Budget

The full hook budget is < 5 s (inherited from ADR-133).  The deriver
call adds < 200 ms (measured: cold-start Python module import ≈ 80–120 ms
on target hardware).

---

## Part B — Metric-Driven Advisory → Blocking Promotion (Deferred)

### Decision

A propose-only soak evaluator (`lib/validator_soak_evaluator.py`) is
introduced.  It is wired into a weekly SessionStart hook
(`hooks/validator-soak-weekly.sh`) that:

1. Throttles to at most one evaluation per 7 days (marker file gating).
2. Reads `.cognitive-os/metrics/skill-md-routing-validator.jsonl`.
3. Filters entries within the last 30 days.
4. Computes a false-positive rate (FP: warned but skill was accepted
   unchanged or with override).
5. If `fp_rate < 5%` AND `total_entries > 30`, emits a human-reviewable
   Markdown proposal at
   `docs/reports/promotion-proposals/<date>/validator-advisory-to-blocking.md`.
6. Appends an evaluation log entry to
   `.cognitive-os/metrics/validator-promotion-evaluations.jsonl`.

**The actual promotion to blocking mode requires operator approval.**
No runtime behavior changes automatically.

### Wire-up: SessionStart hook (not self-improvement loop)

The evaluator is wired as a standalone `hooks/validator-soak-weekly.sh`
rather than into `lib/self_improvement_loop.py`.  Rationale:

- The self-improvement loop runs synchronously in a hot path; a file I/O
  scan over potentially large JSONL is better isolated in a session-boundary
  hook where latency expectations are lower.
- Idempotency is trivially achieved with a marker file (same pattern as
  `hooks/aspirational-audit-weekly.sh` and `hooks/promotion-proposer-weekly.sh`).
- The hook is fail-open: any error exits 0, so it never blocks a session.

### Rollback Path

Set env var `VALIDATOR_BLOCKING=0` to revert the validator to advisory mode
without any code change.  The flag is read at the top of the hook.

---

## Consequences

### Positive

- New auto-generated skills immediately carry `routing_patterns:` frontmatter,
  eliminating the primary source of future coverage decay.
- The soak evaluator makes the advisory → blocking promotion data-driven and
  auditable rather than ad-hoc.
- All components are fail-open; no session is blocked by this ADR.

### Negative / Risks

- The FP heuristic is imperfect (see Uncertainty section below).
- The deriver patterns may need refinement after the first generation cohort;
  a second pass via `/optimize-skill` is recommended.

---

## Uncertainty and Known Gaps

1. **FP-rate detection is heuristic** — assumes an unchanged SKILL.md after a
   warning is a false positive, but the skill may have been accepted with an
   explicit operator override.  Real soak data will calibrate.

2. **The 30-day soak threshold and 5 % FP cutoff are conventional**, not
   validated against COS-specific data.  These can be adjusted via CLI flags
   without code changes.

3. **The deriver's pattern quality may need iteration** after the first
   generation cohort.  A future micro-ADR can tighten confidence thresholds
   once empirical trigger accuracy is measured.

---

## Related Work

- `lib/routing_pattern_deriver.py` — new, standard-library-only deriver
- `lib/validator_soak_evaluator.py` — new, propose-only soak evaluator
- `packages/consequence-system/hooks/auto-skill-generator.sh` — modified
- `hooks/validator-soak-weekly.sh` — new, SessionStart, fail-open, throttled
