---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-029b-reinvention-phase-b-semantic.md
adr: ADR-029b
status: accepted (Phase B-alpha MVP; Phase B-beta embeddings deferred then wired optional)
reality_level: PARTIAL
provenance: Phase A's filename-substring reinvention gate (ADR-029) misses the common real-world case of an agent renaming a concept — concretely, it would not have caught the `lib/agent_heartbeat.py` vs existing `lib/agent_bus.py::publish_heartbeat()` duplication, which is literally the incident that motivated ADR-029 itself.
---

## Decision
Ship Jaccard token-bag similarity (docstring + function-name tokens) as Phase B-alpha: stdlib-only, <300ms, advisory-only (never blocks), scored 0.3 threshold by default. Reject LLM-as-judge (too slow/costly for a per-launch hook) and defer local sentence-transformer embeddings (`all-MiniLM-L6-v2`) as Phase B-beta behind an opt-in dependency extra and env gate, with graceful fallback to Jaccard on import failure.

## Why
Phase A (`hooks/reinvention-check.sh`) is "a glorified `find -name`" — it only catches reinvention when the proposed filename contains the basename of an existing module. Real near-misses from this project's own history show the gap: `lib/request_throttle.py` vs existing `lib/rate_limiter.py` (same responsibility, no name match), and most pointedly `lib/agent_heartbeat.py` vs `lib/agent_bus.py` — the exact duplication that had originally motivated writing ADR-029, meaning the gate ADR-029 shipped would not have caught the bug that inspired it. The failure mode: agents describe behavior in English and pick a new name; Phase A compares names, not what the module does. Four candidate approaches were scored on recall/precision/latency/deps/cost/offline; Jaccard on token bags won as the cheap stdlib-only MVP that also builds 80% of the architecture (index, query, scoring, hook integration, metrics) that embeddings would later reuse as a drop-in scoring-function swap.

## Consequences
Advisory-only by design: false negatives are cheap (caught by human review/`/simplify`) while false-positive hard-blocks would train developers to override and then ignore the gate forever. Index lives at `.cognitive-os/reinvention-index.json`, lazily built (falls back to Phase A only if missing, no synchronous hot-path build). Moving to hard-block (Phase B-γ) is explicitly deferred to a separate ADR gated on ≥30 days of advisory data showing precision ≥0.9.

## Status & current state
Accepted; Phase B-alpha (Jaccard) shipped this ADR with passing tests. Resolution Log (2026-04-21) records Phase B-beta (embeddings) moved from "deferred" to "optional, wired, not installed by default": `pyproject.toml` gained an opt-in `semantic` extra (sentence-transformers + numpy, deliberately excluded from `dev` extra to avoid ~200MB PyTorch bloat in CI); `REINVENTION_PHASE_B=2` triggers the embeddings path with silent fallback to Jaccard on any failure. `EmbeddingsIndex` already existed and a latent `_persist()` numpy tempfile bug was fixed in place rather than creating a duplicate module (avoiding a reinvention incident within the reinvention-gate ADR itself). Explicitly deferred: real-corpus precision/recall benchmark, SessionStart auto-build of the index, threshold recalibration in production, and CI installation of the `semantic` extra. Residual risk noted: Phase B-beta has never run against a real (non-mocked) sentence-transformers install.

## Key links
Supersedes ADR-029 §"Phase B (future)" placeholder. Debt ticket D07 (`rules/ROADMAP.md` §1.7). Key files: `lib/reinvention_semantic.py`, `hooks/reinvention-check.sh`, `scripts/reinvention-query.sh`, `tests/unit/test_reinvention_semantic.py`, `tests/unit/test_reinvention_embeddings.py`, `rules/so-slo.md` (SLO 2 latency budget).
