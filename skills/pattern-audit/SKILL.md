---
name: pattern-audit
description: 'Use when you need this Cognitive OS skill: Pattern/regex audit of a
  codebase with MANDATORY sample verification before publishing counts as severity.
  Prevents alarmist "N occurrences = problem" conclusions based on unverified regex
  hits.; do not use when a narrower skill directly matches the task.'
version: 1.0.0
user-invocable: true
disable-model-invocation: false
auto-generated: false
last-updated: 2026-04-21
license: MIT
metadata:
  author: luum
audience: both
summary_line: Grep/regex audit with mandatory sampling — forbids unverified severity
  counts.
triggers:
- audit
- grep
- pattern
- how many
- N occurrences
- fragility
- find all
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bpattern[- ]?audit\b
  confidence: 0.95
- pattern: \baudit\s+patterns?\b
  confidence: 0.85
---
<!-- SCOPE: both -->
## Purpose

When asked to audit a codebase for a pattern (fragile tests, TODOs, hardcoded
values, deprecated APIs, etc.), **raw regex hit counts are not evidence**.
A regex can match unintended syntactic forms and produce alarmist numbers.

This skill codifies a rule that agents in any codebase can violate: **never publish "N occurrences of problem X" without sampling
first**. It forces a 3-step protocol that turns grep into real findings.

## Invocation

`/pattern-audit` — or invoked implicitly when the user asks for an audit
that involves regex/grep across a codebase.

## Protocol (mandatory — ZERO exceptions)

### Step 1 — Run the search, but DO NOT report yet

Run the grep/regex. Get the raw count per file. Store but do not label as
"high severity" / "fragile" / "problematic" at this point.

Bad first-pass output (prohibited):
```
Found 33 hardcoded paths in test_skill_router.py — high severity ❌
```

Good first-pass output (required):
```
Raw hits: 33 in test_skill_router.py, 12 in test_smart_truncator.py, ...
SEVERITY: not assigned — sampling required.
```

### Step 2 — Sample 3-5 matches per pattern, READ the source

For each pattern category with >0 hits:
1. Read at least 3 matches (prefer different files if hits are spread).
2. Read enough lines of context (`-C 3` or via Read tool) to understand
   what the match actually represents.
3. Classify each sampled hit into:
   - **confirmed**: match is what the regex intended (true positive)
   - **rejected**: match is syntactically similar but semantically different (false positive)
   - **unknown**: needs more context to decide

### Step 3 — Report with sample evidence

Only now publish severity. Format:

```
### Pattern: <name>
Raw hits: <N>
Sampled: <M> matches (read from: <files>)
Classification: <confirmed>/<rejected>/<unknown>
Confirmed rate: <confirmed/sampled> = <pct>%
Estimated real count: <N * confirmed_rate>
Severity: <🟩 low | 🟨 medium | 🟥 high> — reasoning: <why>
```

If confirmed rate is <50%, **downgrade severity** and explain why the regex
was misleading.

### Step 4 — Lessons (optional, recommended)

If any pattern had confirmed rate <50%, add a note:
```
Regex issue: <original> matched <false-positive-shape>.
Better regex: <refined>
```

## Examples

### Good (follows protocol)

> "Running audit... Raw hits for `assert.+/word`: 65 across 12 files.
> Sampling 4: test_skill_router.py:38 shows `assert match.invoke_command ==
> '/plan-bug'` — **rejected** (slash-command, not path).
> test_confidentiality_scanner.py:30 shows an absolute-path string used as
> test INPUT for the scanner — **rejected** (fixture, not assertion).
> Confirmed rate: 0/4 = 0%. Severity: 🟩 nulo. Original regex was too broad."

### Bad (violates protocol — DO NOT DO THIS)

> "Found 65 hardcoded paths in 12 files — high-severity fragility, needs
> immediate migration to tmp_path fixtures." ❌
>
> (Skipped sampling, published severity on raw grep output, over-indexed
> on count.)

## When to invoke

Invoke `/pattern-audit` automatically (self-check) whenever you are about
to write any of:

- "I found N occurrences of X"
- "N files have the pattern Y"
- "Severity: high because N matches"
- "Audit shows Z is fragile/broken/at-risk"

If you're tempted to report a count as evidence and the count came from a
regex/grep/find, run this protocol first.

## Related

- `rules/trust-score.md` — sampled evidence weighs higher than raw counts
- `rules/acceptance-criteria.md` — "measurable" doesn't mean unverified
- `skills/scout-pattern` — related pre-implementation recon skill
- Engram: `feedback/audit-regex-verification` — the incident that motivated this skill

## Contextual Trigger

Active whenever the user asks for a codebase-wide audit, or the orchestrator
is about to publish a count-based severity claim.
