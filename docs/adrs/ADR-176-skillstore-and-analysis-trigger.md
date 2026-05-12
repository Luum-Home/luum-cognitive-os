---

adr: 176
title: SkillStore SQLite Schema Adoption + Post-Execution Analysis Trigger (Discipline-Gated)
status: accepted
implementation_status: implemented
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - lib/skill_store.py
  - scripts/migrate_skill_archive_to_store.py
  - hooks/skill-post-execution-analysis.sh
  - scripts/_lib/settings-driver-claude-code.sh
  - hooks/_lib/registration-allowlist.txt
  - templates/security-profiles/minimal.json
  - templates/security-profiles/standard.json
  - templates/security-profiles/paranoid.json
tier: maintainer
tags: [skill-store, sqlite, observability, post-execution-analysis, discipline-gate, openspace-adoption]
---
# ADR-176: SkillStore SQLite Schema Adoption + Post-Execution Analysis Trigger (Discipline-Gated)

## Status

Accepted.

## Context

### OpenSpace Opus Audit Verdict

The `docs/reports/openspace-opus-deep-audit-2026-05-05.md` Opus-level audit of
`github.com/HKUDS/OpenSpace` @ commit `d1e367d0ed4722d67f1f3b95d816ba4a959288d2`
identified **two HIGH-confidence adoptions** from a pattern-only verdict:

1. **Post-execution analysis trigger** — OpenSpace's `analyzer.py:ExecutionAnalyzer`
   reads conversation logs and tool errors after each Agent task and emits
   `EvolutionSuggestion` per skill. The signal source is live execution data, which
   is richer than COS's current periodic-audit approach.

2. **SQLite SkillStore schema (verbatim)** — OpenSpace's `skill_engine/store.py`
   (57,602 bytes; 1,495 LOC) defines a 6-table SQLite schema that provides queryable
   skill lineage, execution history, judgments, tool dependency tracking, and tagging.
   COS's current `lib/skill_archive.py` uses flat JSONL (`.cognitive-os/metrics/skill-archive.jsonl`)
   with no cross-record querying, no lineage graph, and no content-addressable versioning
   beyond per-snapshot SHA-256 hashes.

The audit also confirmed a **single REJECT**: OpenSpace's auto-apply semantics in
`evolver.py:_apply_with_retry` contain zero occurrences of `approval`, `human`,
`backup`, or `rollback`. This is incompatible with COS's propose-only doctrine
(ADR-133, ADR-134).

### Propose-Only Doctrine (ADR-133 / ADR-134)

ADR-134 mandates a human-gate on every loop closure:

```
audit → propose → human review → apply
```

ADR-133 establishes the expansion-without-monsterization constraint: COS adds
observability primitives only when they are tightly bounded and do not carry
implicit auto-apply contracts.

Any analysis trigger that would automatically rewrite a `SKILL.md` is forbidden
under both ADRs. This ADR adopts the signal-collection half of OpenSpace's loop
and **explicitly excludes** the apply half.


ADR-171 codified the pattern: adopt schema not behavior. The SkillStore adoption
follows the same discipline — we take the well-designed 6-table schema verbatim,
adapt column names to COS namespace where needed, and do not import OpenSpace's
evolver or analyzer logic.

## Decision

### 1. Adopt the 6-table SQLite schema verbatim

Port `openspace/skill_engine/store.py` schema to `lib/skill_store.py` with these
COS-namespace adjustments:

| OpenSpace column | COS adjustment | Reason |
|---|---|---|
| `creator_id` | retained as TEXT DEFAULT '' | OpenSpace uses user IDs; COS uses agent session IDs |
| `lineage_origin` | retained as TEXT DEFAULT 'imported' | Same semantics |
| `analyzed_by` | maps to `analyzer` (TEXT) in `record_analysis` API | COS uses model-name not user-id |
| `skill_applied` (INTEGER) | retained | Maps to COS's `status` boolean |

All CREATE TABLE, index, and foreign key definitions are ported verbatim. Standard
library only (`sqlite3`, `dataclasses`, `typing`, `hashlib`). No new pip dependencies.

Storage path: `.cognitive-os/skill_store.db` (sibling to existing JSONL metrics).

### 2. Adopt the post-execution analysis trigger — route through discipline gate

A new hook `hooks/skill-post-execution-analysis.sh` fires on `PostToolUse Agent`.
When an Agent tool completes:

1. Extract `skill_name`, `tool_count`, `duration_ms`, `status` from `tool_response`.
2. Write execution record to SkillStore (`skill_records` + `execution_analyses`).
3. If the execution meets the "candidate for evolution" heuristic (3+ tool issues
   OR `status=error` AND `duration_ms > 30000`):
   - Write a **propose-only** artifact to
     `docs/reports/skill-analysis-proposals/<YYYY-MM-DD>/<skill_name>.md`.
   - The artifact contains observations and suggested changes but **never modifies**
     the live `SKILL.md`.
   - The discipline gate is enforced: the hook has no write path to `packages/*/SKILL.md`
     or `.claude/skills/`.
4. Total latency budget: <200ms (SQLite write is O(1), file write is bounded by
   proposal template size ~2KB).

Killswitch: `DISABLE_HOOK_SKILL_POST_EXECUTION_ANALYSIS=1`.
Hook is async (`"async": true` in driver) — never blocks the main session.

### 3. Migrate existing skill-archive.jsonl

Script `scripts/migrate_skill_archive_to_store.py` reads the existing flat JSONL
and maps each entry into `skill_records` + `execution_analyses`. The migration is
idempotent via PRIMARY KEY constraints. Default mode is `--dry-run`; `--apply` writes.

## Source

OpenSpace schema source:
- URL: `https://github.com/HKUDS/OpenSpace/blob/d1e367d0ed4722d67f1f3b95d816ba4a959288d2/openspace/skill_engine/store.py`
- File blob SHA: `b3e27516c9b5582d4b7377bab0e126ac405ae0a9`
- Repo commit: `d1e367d0ed4722d67f1f3b95d816ba4a959288d2`
- Lines ported: 80–166 (DDL block `_DDL`)

## Acceptance Criteria

1. `lib/skill_store.py` creates a valid 6-table SQLite DB at `__init__` time.
2. `SkillStore.record_execution()` inserts a `skill_records` row; duplicate `skill_id`
   upserts `last_updated` and counters.
3. `SkillStore.query_lineage(skill_id, depth=3)` performs a recursive CTE traversal
   of `skill_lineage_parents` and returns a list of `(skill_id, depth)` tuples.
4. Hook fires within 200ms on a synthetic `PostToolUse` JSON payload.
5. When `candidate_for_evolution=1` is set, a proposal file appears in
   `docs/reports/skill-analysis-proposals/` and **no** `SKILL.md` is modified.
6. Migration script reports record counts and exits 0 with `--dry-run`.

## Border Cases

| Case | Handling |
|---|---|
| Existing `skill-archive.jsonl` entries | Migrated to `skill_records`; `success=True` maps to `skill_applied=1`; `metadata.observations` splits into `execution_analyses` |
| Future skill-eval models (LLM-as-judge) | Route through discipline gate in `scripts/self_improvement_discipline_gate.py`; judgment written to `skill_judgments` table only; no auto-promote |
| Concurrent hook writes | SQLite WAL mode + threading.Lock pattern (ported from OpenSpace's `_mu` pattern) |
| Missing `skill_id` in PostToolUse payload | Hook skips silently and logs to `error-learning.jsonl` |
| `DISABLE_HOOK_SKILL_POST_EXECUTION_ANALYSIS=1` | Hook exits 0 immediately (killswitch) |

## Consequences

**Positive:**
- SQLite enables JOIN queries across skill executions, lineage, and judgments — replaces
  O(n) JSONL grep with O(log n) indexed queries.
- Content-addressable lineage via SHA-256 output hashing enables reproducibility checks.
- Propose-only discipline gate is enforced structurally (no write path exists to live skills).

**Negative:**
- New binary file (`.db`) in `.cognitive-os/` — must be in `.gitignore`.
- Migration script must handle malformed JSONL entries gracefully.
- Hook adds ~20ms startup overhead per Agent tool completion.

## Operational Guide

### What changes for the operator

Before this ADR, skill execution data was stored in `.cognitive-os/metrics/skill-archive.jsonl` as flat records with no cross-record querying, no lineage graph, and no content-addressable versioning. Post-execution analysis of skill quality required manually reading JSONL or periodic audits.

After this ADR:

| Surface | Before | After |
|---|---|---|
| Skill execution storage | Flat JSONL, O(n) grep | SQLite at `.cognitive-os/skill_store.db` with indexed queries and JOIN support |
| Post-execution analysis | Periodic manual audit | `hooks/skill-post-execution-analysis.sh` fires on every `PostToolUse Agent` completion |
| Skill evolution proposals | None | Propose-only artifacts at `docs/reports/skill-analysis-proposals/<date>/<skill>.md` when heuristic fires |
| Live skill rewrites | No guard | Structurally impossible from the hook — no write path exists to `packages/*/SKILL.md` |

### What this answers (and what it doesn't)

**Answers:**
- "Which skills have the highest error rates?" — `SkillStore.query_lineage()` and the `execution_analyses` table; standard SQL queries on `.cognitive-os/skill_store.db`.
- "Is there a proposal to improve skill X today?" — Check `docs/reports/skill-analysis-proposals/<today>/`.
- "Was a skill rewrite proposed or auto-applied?" — Only proposals exist; the discipline gate makes auto-apply structurally impossible. Check `tests/integration/test_skill_post_execution_hook.py::test_discipline_gate_blocks_live_write`.

**Does not answer:**
- "Should I accept a skill improvement proposal?" — The operator reads proposals in `docs/reports/skill-analysis-proposals/` and applies them manually; this ADR does not automate acceptance.
- "What the OpenSpace evolver or analyzer logic does" — Those were explicitly rejected. The schema was adopted, not the behavior.

### Daily operational pattern

1. Skill execution data flows automatically via the hook — no operator action needed during normal operation.
2. When a proposal appears in `docs/reports/skill-analysis-proposals/`: read it, evaluate the suggested changes, apply manually to the relevant `SKILL.md` if appropriate.
3. To migrate historical data: `python3 scripts/migrate_skill_archive_to_store.py --dry-run` then `--apply`.
4. To disable the hook temporarily: set `DISABLE_HOOK_SKILL_POST_EXECUTION_ANALYSIS=1`.

The hook is async (`"async": true`) — it never blocks the main session.

### Reading guide for cold readers

1. The schema origin is `openspace/skill_engine/store.py` at commit `d1e367d0ed4722d67f1f3b95d816ba4a959288d2`, lines 80–166. The COS port is `lib/skill_store.py`. The key adaption: `analyzed_by` maps to model-name instead of user-id.
2. The **propose-only discipline gate** is the critical constraint: the hook can write to `docs/reports/skill-analysis-proposals/` but has zero write access to `packages/*/SKILL.md` or `.claude/skills/`. This is enforced by absence of the write path, not by a runtime check.
3. `.cognitive-os/skill_store.db` must be in `.gitignore` — it is a binary runtime artifact.
4. `tests/contracts/test_promotion_propose_only.py` (from ADR-180) provides the invariant test that the proposer never modifies live manifests.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Full OpenSpace auto-apply (evolver + analyzer) | Violates ADR-133/ADR-134 propose-only mandate; `_apply_with_retry` has no human gate |
| Lighter NoSQL (TinyDB, shelve) | No JOIN support; lineage graph queries require relational model |
| Custom flat-file schema | Reinvention — OpenSpace's 6-table schema is already validated at production scale |
| DuckDB | External dependency; SQLite sufficient for single-instance use case |

## Falsifiable Claims

1. `SkillStore.query_lineage("test-skill", depth=3)` returns a list with correct depth
   values (verified by `tests/unit/test_skill_store.py::test_query_lineage_depth`).
2. The analysis trigger fires within 200ms on a synthetic payload
   (verified by `tests/integration/test_skill_post_execution_hook.py::test_hook_latency`).
3. The discipline gate intercepts 100% of "skill rewrite" attempts — zero writes to
   live `SKILL.md` files (verified by
   `tests/integration/test_skill_post_execution_hook.py::test_discipline_gate_blocks_live_write`).

## Cross-References

- [ADR-133](ADR-133-expansion-without-monsterization.md) — expansion-without-monsterization
- [ADR-134](ADR-134-headless-self-improvement-proposer.md) — propose-only doctrine + discipline gate
- `docs/reports/openspace-opus-deep-audit-2026-05-05.md` — source audit, §5 Observability + §1 Loop architecture

## Migration Plan

1. Run `python3 scripts/migrate_skill_archive_to_store.py --dry-run` — review output.
2. Run `python3 scripts/migrate_skill_archive_to_store.py --apply` — write migration.
3. Add `.cognitive-os/skill_store.db` to `.gitignore`.
4. Verify hook fires: `DISABLE_HOOK_SKILL_POST_EXECUTION_ANALYSIS=0 bash hooks/skill-post-execution-analysis.sh`.
5. Old `skill-archive.jsonl` is retained (read-only) for 30 days, then archived to `.cognitive-os/archive/`.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

