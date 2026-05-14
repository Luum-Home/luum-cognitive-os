---
name: invariant-check
description: 'Use when you need this Cognitive OS skill: Scans a target file pair
  (ADR + lib, or similar) for numeric-constant pairs, proposes invariants between
  them, and writes pytest assertions that enforce the relationship. Trigger when a
  review finds "two values look inconsistent", when landing new numeric constants
  that might drift across ADR and implementation, or when closing a decision-depth-gate
  finding of type "two values inconsistent".; do not use when a narrower skill directly
  matches the task.'
version: 1.0
audience: project
summary_line: Scans a target file pair (ADR + lib, or similar) for numeric-constant
  pairs…
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \binvariant[- ]?check\b
  confidence: 0.95
- pattern: \bcheck\s+invariants?\b
  confidence: 0.85
- pattern: \bnumeric\s+invariants?\b
  confidence: 0.75
triggers:
- invariant-check
- /invariant-check
- Scans a target file pair (ADR + lib, or similar) for numeric-constant pairs…
---
<!-- SCOPE: both -->
# invariant-check

> **Invoke**: `/invariant-check <file-a> <file-b> [--test-file <path>]`
> **Purpose**: Detect drift between ADR-declared constants and their implementation counterparts by generating pytest assertions that enforce the relationship.

## Problem

A single numeric value often appears twice:
- Once in an ADR (design source of truth)
- Once in the implementation (`lib/*.py`, config, etc.)

When one drifts without the other, nothing complains — until production. The ADR-047 case: the design declared Phase A CPU threshold at 5.0%, but an older draft had Phase A at 1.0% and Phase B at 5.0%. Phase A was under-predicting Phase B because the constants were not pinned by an invariant. Prose resolved the confusion, but the code never enforced it.

## When to Invoke

- A review (e.g., `decision-depth-gate` Q1-Q4) flags "two values that should agree but don't"
- Landing a new numeric constant in an ADR that will also live in code
- After writing an ADR that says things like "both phases use 5.0%", "X must equal Y", or "threshold is shared"
- When a surface-fix advisory (from `hooks/surface-fix-detector.sh`) suggests you're clarifying prose instead of pinning values

## How It Works

### Step 1 — Extract numeric constants from both files
The helper (`scripts/invariant_check_helper.py`) parses each file for assignments of the form `NAME = <number>` (Python-style). For ADRs, it extracts backtick-quoted constant names near numeric literals.

### Step 2 — Pair by name similarity
Constants are paired when their names share a suffix or semantic stem:
- `_CPU_IDLE_THRESHOLD_PCT` (lib) ↔ `CPU threshold` / `5.0 %` / `threshold_pct` (ADR)
- `_HEARTBEAT_STALE_THRESHOLD_S` (lib) ↔ `threshold=15min` (ADR)

### Step 3 — Propose the invariant
For each pair the helper proposes the minimal invariant:
- If values match: `assert A == B` (pin equality)
- If ADR says "A is superset of B": `assert A >= B`
- If ADR says "A is stricter than B": `assert A <= B`
- Otherwise: `assert A == B  # TODO: confirm relationship`

### Step 4 — Emit pytest assertions
The helper writes stdout in this form:

```python
def test_cpu_idle_threshold_matches_adr_047():
    """Invariant (ADR-047 §Phase A/B): Phase A and Phase B share the CPU idle threshold."""
    from lib.session_watchdog_lib import _CPU_IDLE_THRESHOLD_PCT
    ADR_047_PHASE_A_CPU_PCT = 5.0
    ADR_047_PHASE_B_CPU_PCT = 5.0
    assert _CPU_IDLE_THRESHOLD_PCT == ADR_047_PHASE_A_CPU_PCT
    assert ADR_047_PHASE_A_CPU_PCT == ADR_047_PHASE_B_CPU_PCT
```

The skill review step appends these to the appropriate test file (e.g., `tests/unit/test_session_watchdog.py`).

## Example: ADR-047 CPU Threshold

### Before
- `docs/02-Decisions/adrs/ADR-047-session-lifecycle-management.md` line 344: "both phases use 5.0 %"
- `lib/session_watchdog_lib.py` line 323: `_CPU_IDLE_THRESHOLD_PCT = 5.0`
- Nothing enforces the pairing. If a future edit drops one to 1.0 the system silently desyncs.

### Run
```bash
python3 scripts/invariant_check_helper.py \
  docs/02-Decisions/adrs/ADR-047-session-lifecycle-management.md \
  lib/session_watchdog_lib.py
```

### After
The helper emits the `test_cpu_idle_threshold_matches_adr_047` test above. Appended to `tests/unit/test_session_watchdog.py`, future drift becomes a hard CI failure.

## Output Contract

- One pytest `def test_<invariant>_matches_adr_<id>()` per detected pair
- Each test imports the implementation constant and restates the ADR value as a literal
- Comment header cites file + line of the ADR reference
- Exit code 0 on success; non-zero only if BOTH input files are unreadable

## Helper CLI

```
python3 scripts/invariant_check_helper.py <file-a> <file-b> [--min-similarity 0.5]
```

Emits assertions to stdout. The agent/human reviews them, then appends to the chosen test file.

## Relationship to Other Tools

- **`rules/decision-depth-gate.md`**: this skill is the Q4 ("pin the invariant") execution step
- **`hooks/surface-fix-detector.sh`**: nudges the human to run this skill before committing a prose-only fix
- **`rules/trust-score.md`**: tests written by this skill count as HIGH-weight verification evidence

## Limitations (be honest)

- The pairing heuristic is suffix-based; it can miss semantic pairs with wildly different names (e.g., `TIMEOUT_MS` vs `max_wait_seconds`)
- Non-Python implementations need format-specific parsers (not yet built)
- The invariant direction (`==` vs `>=` vs `<=`) is the agent's job to confirm — the helper defaults to `==` and flags it
