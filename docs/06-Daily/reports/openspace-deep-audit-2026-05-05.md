# HKUDS/OpenSpace — Deep Audit (Source-Level)

**Date**: 2026-05-05
**Target**: github.com/HKUDS/OpenSpace
**COS equivalent**: scripts/cos-self-improvement-loop (ADR-134) + cos-doctrine-proposer (ADR-135)
**Status**: research-only — no adoption decision yet
**Method**: /repo-scout --level=deep + /reverse-engineer (source-level comparison)

---

## TL;DR

- OpenSpace and COS solve **different problems** at the same layer: OpenSpace auto-evolves SKILL.md files for external agents (Claude Code, Codex, Cursor) from live execution telemetry; COS auto-proposes governance improvements from its own audit trail.
- OpenSpace's loop **auto-applies** changes to skill files without human approval; COS's loop is **propose-only** with an enforced discipline gate.
- OpenSpace has **richer observability** (SQLite store, lineage graph, frontend dashboard, cloud search); COS has **stronger safety contracts** (discipline gate, forbidden-action patterns, human approval required).
- OpenSpace has **collective intelligence** (cloud skill sharing, federation-by-upload); COS has a runway for it (ADR-136) but no live implementation yet.
- **Verdict: pattern-only** — adopt OpenSpace's post-execution analysis trigger pattern and SQLite skill lineage store design; do not adopt auto-apply semantics.

---

## OpenSpace architecture (verified from source)

Entry point: `openspace/__main__.py` → `OpenSpace.execute()` → `finally: analyze_execution()`.

**The loop (three triggers, all in `openspace/skill_engine/evolver.py`):**

1. **Trigger 1 — Post-execution analysis** (`openspace/skill_engine/analyzer.py`): After every task, `ExecutionAnalyzer.analyze_execution()` loads the recording artifacts (conversation log, tool call results), sends them to an LLM-as-judge (up to `_ANALYSIS_MAX_ITERATIONS=5` tool-calling rounds), and returns an `ExecutionAnalysis` with `SkillJudgment` + `EvolutionSuggestion` per skill. Stored in SQLite via `SkillStore` (`openspace/skill_engine/store.py` — table `execution_analyses`).

2. **Trigger 2 — Tool degradation** (`SkillEvolver.process_tool_degradation()`): A `ToolQualityManager` watches tool error rates. When a tool degrades, all dependent skills are queued for evolution. Anti-loop: `_addressed_degradations` dict prevents re-evolving the same skill-tool pair until the tool recovers.

3. **Trigger 3 — Metric monitor** (`SkillEvolver.process_metric_monitor()`): Periodic scan of skill health (fallback rate, completion rate, effective rate). Rule-based screening followed by LLM confirmation. Anti-loop: newly-evolved skills need `min_selections=5` new data points before re-evaluation.

**Evolution types** (from `openspace/skill_engine/evolver.py` + `openspace/skill_engine/patch.py`):
- `FIX` — in-place repair of the same skill directory
- `DERIVED` — new versioned directory (e.g., `skill-name-enhanced-<sha>`)
- `CAPTURED` — brand new skill captured from a successful workflow

**Safety contract**: `_apply_with_retry()` (lines 1271–1350) applies the LLM-generated edit, runs `_validate_skill_dir()` (structural check), retries up to `_MAX_EVOLUTION_ATTEMPTS=3` times. **No human approval gate**. No rollback to previous state on final failure — directory is removed (`shutil.rmtree`) for DERIVED/CAPTURED, but the original FIX target is overwritten in-place with no backup.

**Storage**: `.openspace/openspace.db` (SQLite). Tables: `skill_records`, `execution_analyses`, `skill_judgments`, `skill_lineage_parents`, `skill_tool_deps`, `skill_tags`. Lineage is tracked via parent-child UUIDs.

**Federation**: `openspace/cloud/` — upload/download skill ZIPs to `open-space.cloud`. Public, private, or team-only visibility. One-command: `openspace cloud upload`, `openspace cloud download`. Not decentralized; the cloud is a single hosted registry.

**Cost discipline**: `_ANALYSIS_MAX_ITERATIONS=5`, `_MAX_EVOLUTION_ITERATIONS=5`, `_MAX_EVOLUTION_ATTEMPTS=3`. Concurrency bounded by `asyncio.Semaphore(max_concurrent=3)`. No explicit per-iteration token budget; cost is bounded only by iteration caps and the LLM provider's own limits.

---

## COS architecture (verified from source)

Entry point: `scripts/cos-self-improvement-loop` → `scripts/cos_self_improvement_loop.py` → `lib/self_improvement_loop.py:build_self_improvement_plan()`.

**The loop (single trigger, deterministic):**

`build_self_improvement_plan()` calls two existing audit scripts synchronously:
1. `cos_boring_reliability.build_dashboard()` — aggregates findings from demotion loop, false-positive ledger, manifest tier-claims, silent-failure audit.
2. `cos_claim_signature_audit.build_report()` — checks whether product claims are signed by real evidence.

Each finding maps to a `SelfImprovementProposal` dataclass (frozen, immutable) with: `finding_id`, `source`, `severity`, `candidate_action`, `allowed_write_paths`, `required_tests`, `human_approval_required=True`, `blocked_actions` (always includes `auto_merge`, `auto_promote_core_or_team`, `invent_roi_evidence`, `delete_without_reversible_path`).

**Safety contract**: `scripts/self_improvement_discipline_gate.py` validates every plan before it can be used. Regex patterns reject any proposal containing `auto_merge`, `auto_promote`, `promote_to_core`, `extend_warning_budget`, `invent_roi`. The discipline gate is an explicit veto layer that runs before any proposal reaches an operator.

**Doctrine proposer** (`lib/doctrine_proposer.py`): reads same audit sources, emits Markdown proposals under `docs/03-PoCs/proposals/` with `status: proposed`, `runtime_effect: none`. Cannot touch live rules, hooks, skills, ADR statuses.

**Cross-instance runway** (ADR-136): `cos-export-consumer-evidence` / `cos-import-consumer-evidence` — bilateral evidence exchange as YAML files. Portable Engram bundles (propose-only import). Registry locks. No live federation; shape-B triggers not yet fired.

**Observability**: proposals written to `.cognitive-os/improvements/proposals/` as timestamped JSON. No persistent database; no frontend; no lineage graph. Audit output is readable in CI or terminal.

---

## Side-by-side comparison

| Dimension | OpenSpace | COS | Verdict |
|---|---|---|---|
| Loop architecture clarity | Three clearly-named triggers (analysis, tool degradation, metric monitor), each with a docstring, concurrency model, and anti-loop guard. `evolver.py` is 1300+ lines but well-structured. | Single deterministic loop in ~300 lines (`lib/self_improvement_loop.py`). Extremely easy to read; architecture visible in one file. | **IGUAL** — OpenSpace is richer; COS is simpler. Complexity matches scope. |
| Proposal generation | LLM-as-judge post-execution analysis: reads real conversation artifacts, tool error rates, and execution history to generate `EvolutionSuggestion` per skill. Hybrid: rule screening → LLM confirmation. | Deterministic: maps existing audit findings (boring-reliability, claim-signature) to fixed proposal templates. No LLM inference in the loop itself. | **MEJOR** (OpenSpace) — OpenSpace generates proposals from live execution data; COS generates from static audit findings. OpenSpace proposals are grounded in actual task outcomes. |
| Safety contract | No human approval gate. FIX evolutions overwrite skill files in-place with no backup. DERIVED/CAPTURED create new dirs; structural validation via `_validate_skill_dir()` but no governance checkpoint. | Enforced `human_approval_required=True` in every proposal. Discipline gate (regex veto) blocks forbidden actions. Write paths are explicitly whitelisted per proposal. | **MEJOR** (COS) — COS's propose-only contract with an explicit discipline gate is significantly stronger. OpenSpace auto-applies without operator review. |
| Validation / judge | `_validate_skill_dir()` is structural only (SKILL.md exists, skill_id present). The LLM-as-judge in `analyzer.py` evaluates execution quality, not the evolved skill correctness. Apply-retry with 3 attempts; no semantic validation. | Proposals go through discipline gate (regex patterns + policy field checks). Proposals are not auto-executed; human validates at apply time. Tests are declared per proposal but not auto-run by the loop. | **IGUAL** — OpenSpace validates structure but not semantics; COS validates governance but not code. Both have a gap in full semantic validation. |
| Observability | SQLite database with full execution history, skill lineage (parent-child), judgment records, and evolution timestamps. React frontend with lineage graph (`SkillEvolutionGraph.tsx`), diff viewer (`DiffViewer.tsx`). Cloud activity visible via dashboard server. | Timestamped JSON proposals under `.cognitive-os/improvements/proposals/`. No database, no frontend, no lineage graph. Readable in terminal/CI. | **MEJOR** (OpenSpace) — SQLite lineage store + frontend dashboard is materially more observable than flat JSON files. |
| Drift handling | Skills accumulate `total_selections`, `fallback_count`, `effective_count` metrics. Metric monitor fires when rates cross thresholds. Skills that drift from quality baselines are re-evolved. Anti-loop prevents oscillation. | No live drift detection. Drift surfaces when an audit script fails on next scheduled run. No automatic re-proposal; operator must re-run the loop. | **MEJOR** (OpenSpace) — OpenSpace has continuous metric-driven drift detection; COS only detects drift at audit schedule boundaries. |
| Cost discipline | Bounded by iteration caps (5 LLM rounds analysis, 5 evolution, 3 apply-retry). No per-session token budget or $ cap. Concurrent evolutions capped at `max_concurrent=3`. | Loop runs no LLM inference; cost is zero per invocation. Doctrine proposer runs LLM only when `--write` is used. Explicit model routing in COS rules (`model-routing`). | **MEJOR** (COS) — COS's propose-only architecture incurs zero LLM cost in the loop itself. OpenSpace's async multi-trigger loop has no explicit budget cap, only iteration limits. |
| Federation / cross-instance | Cloud registry (`open-space.cloud`): upload/download skill ZIPs with visibility controls. Centralized but functional today. Network effects documented in benchmark. | Runway only (ADR-136): export/import YAML evidence, portable Engram bundles, registry locks. No live cloud or federation. Shape-B triggers not fired. | **MEJOR** (OpenSpace) — OpenSpace has working federation today; COS has a designed runway but no implementation. |
| Maintenance load | ~6,800 LOC Python (skill_engine alone), React frontend, SQLite, litellm dependency, local server, communication gateway, cloud client. Significant surface area. | ~500 LOC core loop + discipline gate. Zero new dependencies; relies on existing COS audit scripts. Minimal surface area. | **MEJOR** (COS) — COS's loop has 1/10th the maintenance surface area. OpenSpace bundles an entire agent platform. |

---

## Verdict

**pattern-only**

OpenSpace and COS operate at the same conceptual layer (observe → propose/apply → evolve) but with fundamentally different safety contracts and scope. OpenSpace is a **complete agent platform** with auto-apply evolution; COS is a **governed audit-to-proposal pipeline** with mandatory human review. These are not interchangeable.

The critical disqualifier for adoption-as-replacement or adoption-as-augmentation is OpenSpace's **auto-apply without human approval**. COS ADR-133 (governance contract) and the discipline gate exist precisely to block this. Adopting OpenSpace's evolver as-is would mean auto-modifying `skills/*/SKILL.md` files without operator review — a violation of COS's core governance invariant.

The critical disqualifier for adopt-as-augmentation (selective pieces) is **scope mismatch**: OpenSpace evolves externally-facing SKILL.md files for any agent host (Claude Code, Codex, Cursor); COS's self-improvement loop targets COS's own governance primitives (demotion decisions, claim signatures, doctrine rules). The audiences are different enough that grafting OpenSpace's evolver into COS would require rebuilding its audit-trigger layer from scratch.

What COS **should borrow** from OpenSpace:
1. **Post-execution analysis trigger**: COS currently runs proposals only from static audit outputs. OpenSpace's pattern of analyzing conversation artifacts after each task execution to generate `EvolutionSuggestion` objects is genuinely better and COS should prototype this for skill proposals — but routed through the discipline gate before any write.
2. **SQLite skill lineage store**: COS's proposals are flat JSON files with no lineage tracking. OpenSpace's `SkillStore` schema (parent-child lineage, execution analyses, judgment records) is a clean, reproducible design worth adopting verbatim as the persistence layer for COS proposals (replacing `.cognitive-os/improvements/proposals/*.json`).

These two patterns can be implemented by COS without adopting OpenSpace's auto-apply semantics — they are architectural ideas, not runtime components.

---

## First concrete step if adopting

Since verdict is **pattern-only**, the first step is a contained spike:

**File to create**: `lib/execution_analysis_trigger.py`
**Inspired by**: `openspace/skill_engine/analyzer.py` (post-execution LLM-as-judge pattern)
**What it does**: After a COS session ends, reads the conversation log (already in `.cognitive-os/`) and sends it to an LLM judge that produces `EvolutionSuggestion`-compatible output — but instead of auto-applying, routes through `lib/self_improvement_loop.py:_proposal()` and the existing discipline gate.
**Falsifiable claim**: Running `scripts/cos-self-improvement-loop --profile core --json` after the spike should surface at least one proposal derived from session conversation artifacts (not just from boring-reliability audit), with `human_approval_required: true` and no forbidden actions.

---

## Open questions / blockers

1. **OpenSpace's auto-apply safety in practice**: The repo has no tests for evolution correctness — only structural validation (`_validate_skill_dir` checks SKILL.md exists and has a skill_id). The benchmark shows 4.2× economic improvement, but the benchmark (`gdpval_bench/`) runs against external agent tasks, not the evolver's own output quality. It is unknown whether auto-evolved skills regress over time in out-of-distribution tasks. This is the most important open question if any adoption beyond pattern-only is considered: **what is the evolution failure rate in production, and what is the recovery path?**

---

## Sources

**OpenSpace source files read via `gh api`:**
- `github.com/HKUDS/OpenSpace/blob/main/openspace/skill_engine/evolver.py` — full file (1300+ lines), focusing on lines 1–160 (class/triggers) and 1271–1350 (`_apply_with_retry`)
- `github.com/HKUDS/OpenSpace/blob/main/openspace/skill_engine/analyzer.py` — lines 1–120 (`ExecutionAnalyzer`, `_correct_skill_ids`)
- `github.com/HKUDS/OpenSpace/blob/main/openspace/skill_engine/store.py` — lines 1–80 (SQLite schema, `_db_retry`)
- `github.com/HKUDS/OpenSpace/blob/main/openspace/prompts/skill_engine_prompts.py` — grep for cost/budget/human patterns
- `github.com/HKUDS/OpenSpace/blob/main/README.md` — full file

**gh api calls:**
- `gh api repos/HKUDS/OpenSpace` — repo metadata
- `gh api repos/HKUDS/OpenSpace/git/trees/main?recursive=1` — full file tree (flat + recursive)
- `gh api repos/HKUDS/OpenSpace/contents/<path>` — base64 file fetch for 4 source files

**COS files read:**
- `/docs/02-Decisions/adrs/ADR-134-headless-self-improvement-proposer.md`
- `/docs/02-Decisions/adrs/ADR-135-self-evolving-doctrine-proposals.md`
- `/docs/02-Decisions/adrs/ADR-136-cross-instance-learning-runway.md`
- `/scripts/cos_self_improvement_loop.py`
- `/scripts/cos_doctrine_proposer.py`
- `/lib/self_improvement_loop.py`
- `/scripts/self_improvement_discipline_gate.py`

**TRUST REPORT**: Uncertainty acknowledged — OpenSpace's production evolution failure rate is unknown. The benchmark (`gdpval_bench/`) measures task economic outcome, not skill quality over time. The verdict (pattern-only) is conservative precisely because auto-apply safety without rollback cannot be confirmed from the source alone.
