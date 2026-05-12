---
adr: 37
title: Self-Knowledge Base
status: accepted
implementation_status: not-applicable
date: '2026-04-20'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted decision/policy record with no explicit implementation
  surface
---

# ADR-037 — Self-Knowledge Base

**Status**: Accepted
**Date**: 2026-04-20
**Related**: ADR-031 (aspirational audit), ADR-036 (sprint orchestration)

## Problem

Sub-agents spend 3-10K tokens per session grepping source files to answer basic questions:

- "Does `lib/rate_limiter.py` exist and what does it export?"
- "Who calls `hooks/_lib/hook-runtime-probe.sh`?"
- "What does `ADR-028` decide?"

This is pure discovery waste. The answers don't change between sessions unless the codebase changes.
There is no cached, queryable index of the codebase's own API surface, dependency graph, or glossary.

## Decision

Introduce `.cognitive-os/self-knowledge/` — a lightweight, auto-rebuilt index of the OS codebase.
Four artifacts, one generator script, one SessionStart hook, one query library.

## Artifacts

### `api-surface.json`
Maps every Python module and Bash script in `lib/`, `hooks/`, `scripts/`, `packages/*/lib/` to its
exported surface:

```json
{
  "lib/rate_limiter.py": {
    "classes": ["RateLimiter", "TokenBucket"],
    "functions": [
      {"name": "check_rate_limit", "signature": "(service: str, budget: float) -> bool", "doc": "Returns True if within budget."},
      {"name": "reset_all", "signature": "() -> None", "doc": "Resets all buckets. Used in tests."}
    ],
    "shebang_bash_entrypoints": []
  },
  "hooks/rate-limiter.sh": {
    "classes": [],
    "functions": [],
    "shebang_bash_entrypoints": ["hooks/rate-limiter.sh"]
  }
}
```

### `dep-graph.json`
Forward dependency graph. Parses `import lib.X` (Python) and `source hooks/_lib/Y` (Bash):

```json
{
  "lib/agent_bus.py": ["lib/circuit_breaker.py", "lib/cost_predictor.py"],
  "hooks/rate-limiter.sh": ["hooks/_lib/hook-runtime-probe.sh"]
}
```

### `glossary.md`
Extracted from H2/H3 headings in `docs/adrs/*.md` and `docs/guides/*.md`, with the first sentence
of each ADR section. Deduped. Sorted alphabetically. Enables fast "what does X mean" lookups.

### `codebase-summary.md`
~500-token overview:
- 5 largest subsystems by file count
- 10 most-imported `lib/` modules (by dep-graph in-degree)
- ADR index (number → title → status)

## Generator

`scripts/cos_build_self_knowledge.py` — pure Python 3, no third-party deps.

- Scans all four source trees.
- Writes all four artifacts plus `.cognitive-os/self-knowledge/.mtime`.
- Idempotent; safe to run any time.
- Typical runtime: < 2 seconds on the current codebase (~300 files).

## Auto-Rebuild Trigger

`hooks/self-knowledge-refresh.sh` runs at SessionStart.

1. Reads `.mtime` stamp from the index.
2. Compares against newest mtime in `lib/`, `hooks/`, `scripts/`, `docs/adrs/`, `packages/*/lib/`.
3. If stale (or index missing): rebuilds in background (`nohup python3 ... &`).
4. Always exits 0 — never blocks session startup.
5. Logs to `.cognitive-os/metrics/self-knowledge-refresh.jsonl`.

## Query API

`lib/self_knowledge.py` (symlink → `packages/cos-self-knowledge/lib/self_knowledge.py`):

```python
from lib.self_knowledge import query, get_module, get_importers

# Substring search across all four artifacts — top 10 ranked by relevance
results = query("rate limiter")
# [{"source": "api-surface", "key": "lib/rate_limiter.py", "snippet": "...", "score": 3}, ...]

# Fast O(1) module lookup
mod = get_module("lib/rate_limiter.py")

# Reverse dep-graph: who imports this module?
callers = get_importers("lib/circuit_breaker.py")
# ["lib/agent_bus.py", "lib/claude_executor.py"]
```

`query()` scoring:
- +3 if term found in module/file path
- +2 if found in function/class name
- +1 if found in docstring or section heading
- Results sorted descending, capped at 10

## Rollout

1. `scripts/cos_build_self_knowledge.py` runs once manually to seed the index.
2. `hooks/self-knowledge-refresh.sh` registered in `scripts/apply-efficiency-profile.sh`
   under SessionStart — rebuilds stale index automatically.
3. Sub-agent prompts can include: "Check `lib/self_knowledge.py` for module lookups before grepping."

## Rebuild Triggers

| Trigger | Mechanism |
|---------|-----------|
| SessionStart (stale) | `self-knowledge-refresh.sh` detects mtime delta, rebuilds in background |
| Manual | `python3 scripts/cos_build_self_knowledge.py` |
| CI (future) | Can be added as a post-merge step |

## Consequences

**Positive**:
- Sub-agents answer "does X exist" questions in < 100 tokens (query call vs grep).
- `codebase-summary.md` replaces ad-hoc `ls` + `cat` exploration at session start.
- `dep-graph.json` makes blast-radius analysis cheap.

**Negative / Mitigations**:
- Index can go stale mid-session if files change. Mitigation: mtime check at SessionStart covers
  between-session drift; mid-session staleness is acceptable for the current use cases.
- Generator adds ~2s to session startup path. Mitigation: runs in background (`nohup ... &`).

## Alternatives Considered

- **repomix / repo-scout**: External tools, not always installed, produce token-heavy output.
- **Engram per-file**: Too granular, not queryable as a surface, drift-prone.
- **Language server (pyright/pylsp)**: Heavy dependency, overkill for discovery queries.
