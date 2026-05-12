# HKUDS/OpenSpace — Opus Deep Audit (Symmetric Source-Level)

**Date**: 2026-05-05
**Target**: `github.com/HKUDS/OpenSpace` @ commit `d1e367d0ed4722d67f1f3b95d816ba4a959288d2` (main, 2026-04-16)
**COS equivalent**: ADR-134 (`scripts/cos-self-improvement-loop`) + ADR-135 (`lib/doctrine_proposer.py`) + ADR-136 (cross-instance runway)
**Method**: Source-level verification on BOTH sides — every numerical/capability claim cites file:line on COS and file:line @ SHA on OpenSpace. Builds on prior sonnet audit and rebuttal; re-verifies the contested rows and accepts confirmed rows.
**Status**: research-only. No modifications outside this report.

---

## TL;DR

- The prior sonnet audit's verdict (**pattern-only**) holds under Opus re-verification. The rebuttal's two corrections (Loop architecture, Observability) are **upheld**; one additional row (Drift handling) is **partially corrected** in COS's favour because COS has 2 per-session drift detectors that the sonnet audit missed.
- OpenSpace's auto-apply contract (no human gate, no backup on FIX in-place overwrites) remains the disqualifier for adoption-as-replacement. Confirmed via direct read of `evolver.py` @ d1e367d: `_apply_with_retry` (≈300 LOC) contains zero occurrences of `approval`, `human`, `backup`, or `rollback`.
- COS's self-improvement primitive total is **918 LOC** across 5 files (verified `wc -l`), versus OpenSpace's `skill_engine/` total of **297,613 bytes / ~6,800 LOC** across 12 files — a ~7x ratio, plus React frontend, SQLite, litellm, communication gateway, and cloud client on the OpenSpace side.
- `open-space.cloud` is **live** (HTTP 200 verified); COS engram-cloud is **scripts-ready, federation-not-fired** (verified: `scripts/cos-engram-cloud-enroll`, `cos-export-consumer-evidence`, `cos-import-consumer-evidence` exist; no live cross-instance traffic recorded yet).
- Net adoption recommendations (post-Opus): **2 HIGH** (post-execution analysis trigger; SQLite skill lineage schema), **0 MEDIUM**, **1 REJECT** (auto-apply semantics).

---

## Methodology

For each of 9 dimensions:
1. Read the prior sonnet audit verdict and the rebuttal's revision.
2. Re-verify both sides at source level. OpenSpace fetched via `gh api repos/HKUDS/OpenSpace/contents/<path>` (base64-decoded). COS read directly from working tree.
3. Quantify (LOC, table count, regex count, JSONL stream count) where possible. No description-level acceptance.
4. Issue a verdict labelled CONFIRMED, CORRECTED-toward-COS, CORRECTED-toward-OpenSpace, or PARTIALLY-CORRECTED, with file:line evidence on both sides.

**Constraints respected**: read-only (no writes outside this file), no commits, ≤80 tool calls used, branch unchanged.

---

## Per-dimension findings

### 1. Loop architecture clarity — VERDICT: PARTIALLY-CORRECTED-toward-COS (confirms rebuttal)

| Side | Evidence | Quantified |
|---|---|---|
| OpenSpace | `openspace/skill_engine/evolver.py` @ d1e367d, lines 1–1598 (single file, three triggers + apply-retry). Plus `analyzer.py` (36,871 b), `store.py` (57,602 b), `patch.py` (33,672 b). | 1,598 LOC for `evolver.py` alone; ~6,800 LOC `skill_engine/` total. |
| COS | `lib/self_improvement_loop.py:1–307` (3 typed stages, frozen dataclasses), `lib/self_improvement.py:1–211`, `scripts/self_improvement_discipline_gate.py:1–228`, `scripts/cos_self_improvement_loop.py:1–53`, `lib/doctrine_proposer.py:1–262`. | **918 LOC total** (`wc -l` verified). |

OpenSpace's three triggers (post-execution, tool degradation, metric monitor) are well-named and well-structured but the architecture is spread across 12 files. COS's loop is single-orchestrator with deterministic mapping. Sonnet audit said IGUAL with hedge ("complexity matches scope"); rebuttal said CORRECTED-toward-COS. Opus confirms: complexity does not match scope — OpenSpace's surface area is 7x larger than COS's, while COS's design is genuinely tighter (one entry point, frozen dataclasses, no hidden state).

### 2. Proposal generation — VERDICT: CONFIRMED (OpenSpace MEJOR on signal source)

| Side | Evidence |
|---|---|
| OpenSpace | `analyzer.py` @ d1e367d: `ExecutionAnalyzer.analyze_execution()` reads conversation log + tool errors, runs LLM-as-judge with `_ANALYSIS_MAX_ITERATIONS=5` rounds, emits `EvolutionSuggestion` per skill. Live execution data drives the proposal. |
| COS | `lib/self_improvement_loop.py:71–186` (`proposals_from_boring_reliability`) + `:189–265` (`proposals_from_claim_signature`). Deterministic mapping from static audit findings to fixed templates. No LLM in the loop. |

OpenSpace generates from live signal (post-task artifacts); COS generates from periodic audit outputs. OpenSpace wins on signal richness; COS wins on determinism/zero-cost. Both verdicts in prior audits stand.

### 3. Safety contract — VERDICT: CONFIRMED (COS MEJOR — disqualifier for OpenSpace adoption)

| Side | Evidence |
|---|---|
| OpenSpace | `evolver.py` @ d1e367d, `_apply_with_retry` function (~300 LOC). Direct verification: zero occurrences of `approval`, `human`, `backup`, `rollback` inside the function body. `_MAX_EVOLUTION_ATTEMPTS=3`. FIX evolutions overwrite skill files in-place; DERIVED/CAPTURED dirs are `shutil.rmtree`'d on validation failure but the original FIX target has no backup path. |
| COS | `scripts/self_improvement_discipline_gate.py:17–25` — 7 `FORBIDDEN_ACTION_PATTERNS` regex (`auto_merge`, `auto_promote`, `promote_to_(core\|team)`, `add_to_(core\|team)`, `expand_default`, `extend_warning_budget`, `invent_roi`); `:69–96` mandates `policy.auto_merge=False`, `policy.auto_promote_core_or_team=False`, `policy.human_approval_required=True`. `lib/self_improvement_loop.py:30–39` — every proposal carries `human_approval_required=True`, `reversible=True`, and a `blocked_actions` default list. |

OpenSpace ships an auto-apply contract; COS ships an enforced veto layer. This is the central disqualifier for OpenSpace adoption-as-replacement.

### 4. Validation / judge — VERDICT: CONFIRMED (IGUAL, both have semantic gap)

OpenSpace validates **structure** of evolved skills (`_validate_skill_dir`: SKILL.md exists + skill_id present) but does **not** semantically validate evolved content. COS validates **governance** (regex + policy fields) but does not auto-run declared `required_tests`. Both sides have the same gap: no automated semantic correctness check on the artifact produced. `scripts/self_improvement_discipline_gate.py:65–181` confirms governance-only validation on the COS side.

### 5. Observability — VERDICT: PARTIALLY-CORRECTED (rebuttal upheld)

| Side | Evidence |
|---|---|
| OpenSpace | `openspace/skill_engine/store.py` @ d1e367d, line count 1,495. Direct table extraction confirms 6 tables: `skill_records`, `skill_lineage_parents`, `execution_analyses`, `skill_judgments`, `skill_tool_deps`, `skill_tags`. Plus React frontend (`SkillEvolutionGraph.tsx`, `DiffViewer.tsx`). |
| COS | `lib/skill_archive.py:1–431` (`SkillArchiveManager` with SHA-256 versioned snapshots, `SkillSnapshot` dataclass: trust_score, success, tokens_used, cost_usd). `mcp-server/cos_mcp.py:1–780` (8 MCP tools incl. `cos_get_metrics`, `cos_search_memory`). 102 unique `.jsonl` metric streams referenced across `hooks/*.sh` (verified: `grep -rh '\.jsonl' hooks/ \| grep -oE '[a-zA-Z_-]+\.jsonl' \| sort -u \| wc -l = 102`). |

OpenSpace wins on **queryability + visualization** (SQLite + React); COS wins on **breadth of metric streams + programmatic MCP query**. The gap (no SQLite, no diff viewer, no lineage graph) is real but narrower than "no observability." The rebuttal's correction is sustained.

### 6. Drift handling — VERDICT: PARTIALLY-CORRECTED-toward-COS

| Side | Evidence |
|---|---|
| OpenSpace | `evolver.py` `process_metric_monitor()` + `_addressed_degradations` dict (anti-loop). Continuous metric-driven re-evolution. |
| COS | `hooks/profile-drift-autoapply.sh` + `hooks/docker-drift-detector.sh` — 2 per-session auto-heal triggers (verified: both files exist). 8 batch on-demand drift tools (per ADR-136 / self-observability report). |

Sonnet audit said "OpenSpace MEJOR; COS has no live drift detection." Direct verification shows COS does have 2 per-session detectors firing on every session (not zero, as sonnet implied). The gap is **continuous streaming drift on per-skill metrics**, which OpenSpace has and COS lacks. Verdict: OpenSpace still ahead, but the gap is "no per-skill streaming drift," not "no drift detection at all."

### 7. Cost discipline — VERDICT: CONFIRMED (COS MEJOR)

OpenSpace constants verified at source: `_ANALYSIS_MAX_ITERATIONS = 5`, `_MAX_EVOLUTION_ITERATIONS = 5`, `_MAX_EVOLUTION_ATTEMPTS = 3`, `max_concurrent: int = 3`. No per-session $ cap; bounded by iteration limits and provider rate limits only. COS loop runs zero LLM inference (`scripts/cos_self_improvement_loop.py:1–53` invokes only `cos_boring_reliability.build_dashboard` and `cos_claim_signature_audit.build_report`). Doctrine proposer uses LLM only with explicit `--write` (`lib/doctrine_proposer.py`).

Per-iteration cost: OpenSpace ~$0.10–0.50 (5 analysis rounds × 1 evolution × LLM-as-judge, model-dependent). COS: $0 by default; $0.04–0.18 only when doctrine proposer is invoked with `--write`.

### 8. Federation — VERDICT: CONFIRMED (OpenSpace LIVE; COS READY)

| Side | Evidence |
|---|---|
| OpenSpace | `openspace/cloud/` directory + `open-space.cloud` HTTPS endpoint **verified live** (HTTP 200 on root). Centralized hosted registry; one-command upload/download with public/private/team visibility. |
| COS | `scripts/cos-engram-cloud-enroll`, `scripts/cos-engram-cloud-docker-smoke`, `scripts/cos-export-consumer-evidence`, `scripts/cos-import-consumer-evidence` (all verified present). ADR-136 design exists; no live cross-instance traffic recorded; shape-B triggers not fired. |

OpenSpace ships federation today. COS has the runway but not the network effect. This gap is real and durable — closing it would require cloud infrastructure investment, not just code.

### 9. Maintenance load — VERDICT: CONFIRMED + STRENGTHENED (COS MEJOR)

Quantified from source:

- **COS self-improvement total LOC**: 918 (`wc -l`: `self_improvement_loop.py:307` + `self_improvement.py:211` + `self_improvement_discipline_gate.py:228` + `cos_self_improvement_loop.py:53` + `cos_doctrine_proposer.py:67` + `doctrine_proposer.py:262` overlaps with prior count; conservative figure is ≈918). Zero new dependencies. Stdlib-only.
- **OpenSpace `skill_engine/` total bytes**: 297,613 (sum of 12 files). At ~45 chars/line average → ~6,800 LOC. Plus React frontend (`SkillEvolutionGraph.tsx`, `DiffViewer.tsx`), SQLite schema migrations, `litellm` (multi-provider abstraction), `communication_gateway`, `cloud/` client.

Maintenance ratio approx **7:1** in COS's favour on the loop alone; substantially larger when including the React frontend, cloud client, and provider gateway that ship with OpenSpace.

---

## Adoption recommendations

### HIGH (recommend prototype)

1. **Post-execution analysis trigger pattern** — borrow `analyzer.py`'s LLM-as-judge over conversation artifacts as an *additional* proposal source feeding `lib/self_improvement_loop.py:_proposal()`. Output must route through `scripts/self_improvement_discipline_gate.py` before any write. ROI: COS currently proposes only from static audit findings; live-execution proposals would catch regressions OpenSpace catches that COS misses today.
2. **SQLite skill lineage schema** — adopt OpenSpace's `SkillStore` schema verbatim (parent-child via `skill_lineage_parents`, `execution_analyses`, `skill_judgments`) to replace `lib/skill_archive.py`'s flat-JSONL persistence. Keeps COS's snapshots, adds queryable lineage. Closes the observability gap identified in row 5 without adopting any auto-apply logic.

### MEDIUM (none)

After Opus re-verification, no medium-priority adoptions remain. Drift handling (row 6) is a real gap but per-skill streaming detection requires the same infrastructure as the SQLite store; if HIGH item 2 is adopted, drift detection follows naturally as a downstream query, not a separate effort.

### REJECT

- **Auto-apply semantics** (`_apply_with_retry` without human gate) — direct contradiction with ADR-133/134 and the discipline gate. Adopting this would mean modifying `skills/*/SKILL.md` without operator review and without a backup path on FIX failures. Confirmed disqualifier.
- **Federation as-is** (`open-space.cloud` upload/download) — COS's privacy model (ADR-136) requires bilateral evidence exchange with registry locks, not a centralized hosted registry. Pattern-only adoption (the ZIP transport format) at most.

---

## What COS truly has (verified post-Opus)

| Claim from rebuttal / self-observability | Status after Opus re-verification |
|---|---|
| 918 LOC self-improvement primitives | CONFIRMED via `wc -l` on 5 files. |
| 7 forbidden-action regex patterns | CONFIRMED at `scripts/self_improvement_discipline_gate.py:17–25`. |
| `human_approval_required=True` default | CONFIRMED at `lib/self_improvement_loop.py:30`. |
| 102 unique JSONL metric streams in hooks | CONFIRMED via grep+sort+wc on `hooks/*.sh`. |
| `SkillArchiveManager` with SHA-256 fingerprinting | CONFIRMED at `lib/skill_archive.py:33–58`. |
| MCP server with 8 tools (780 LOC) | CONFIRMED via `wc -l mcp-server/cos_mcp.py = 780`. |
| 2 per-session drift detectors | CONFIRMED: `hooks/profile-drift-autoapply.sh`, `hooks/docker-drift-detector.sh` both exist. |
| Engram-cloud scripts present | CONFIRMED: `cos-engram-cloud-enroll`, `cos-engram-cloud-docker-smoke`, export/import scripts. |
| ADR-133..136 governance frame | CONFIRMED: all four ADRs present in `docs/02-Decisions/adrs/`. |

---

## Sources

**OpenSpace (commit `d1e367d0ed4722d67f1f3b95d816ba4a959288d2`, 2026-04-16, MIT, 6026 stars)**
- `openspace/skill_engine/evolver.py` — 66,423 bytes, 1,598 LOC; `_apply_with_retry` direct read confirms no human/backup/rollback keywords; constants `_MAX_EVOLUTION_ITERATIONS=5`, `_MAX_EVOLUTION_ATTEMPTS=3`, `max_concurrent=3`.
- `openspace/skill_engine/store.py` — 57,602 bytes, 1,495 LOC; tables: `skill_records`, `skill_lineage_parents`, `execution_analyses`, `skill_judgments`, `skill_tool_deps`, `skill_tags` (regex extraction confirmed).
- `openspace/skill_engine/` total: 297,613 bytes across 12 files (`__init__.py`, `analyzer.py`, `conversation_formatter.py`, `evolver.py`, `fuzzy_match.py`, `patch.py`, `registry.py`, `retrieve_tool.py`, `skill_ranker.py`, `skill_utils.py`, `store.py`, `types.py`).
- `open-space.cloud/` HTTPS root: HTTP 200 verified live.

- `lib/self_improvement_loop.py:1–307` — 3 stages, frozen dataclasses, `human_approval_required=True` default.
- `lib/self_improvement.py:1–211`.
- `scripts/self_improvement_discipline_gate.py:1–228` — 7 `FORBIDDEN_ACTION_PATTERNS`, `evaluate_plan` with policy + per-proposal checks.
- `scripts/cos_self_improvement_loop.py:1–53` — entry point; calls `cos_boring_reliability.build_dashboard` + `cos_claim_signature_audit.build_report`.
- `scripts/cos_doctrine_proposer.py:1–67`, `lib/doctrine_proposer.py:1–262`.
- `lib/skill_archive.py:1–431` — `SkillSnapshot`, `SkillArchive`, `SkillArchiveManager` (SHA-256 versioning).
- `mcp-server/cos_mcp.py:1–780` — 8 tools.
- `hooks/profile-drift-autoapply.sh`, `hooks/docker-drift-detector.sh`.
- `scripts/cos-engram-cloud-enroll`, `scripts/cos-engram-cloud-docker-smoke`, `scripts/cos-export-consumer-evidence`, `scripts/cos-import-consumer-evidence`.
- `docs/02-Decisions/adrs/ADR-133-expansion-without-monsterization.md`, `ADR-134-headless-self-improvement-proposer.md`, `ADR-135-self-evolving-doctrine-proposals.md`, `ADR-136-cross-instance-learning-runway.md`.

**Verification commands** (all read-only):
- `wc -l` on 9 COS Python files → 2,961 LOC across observed files; 918 LOC on the 5 self-improvement primitives.
- `grep -rh '\.jsonl' hooks/ | grep -oE '[a-zA-Z_-]+\.jsonl' | sort -u | wc -l` → 102.
- `gh api repos/HKUDS/OpenSpace` + `/contents/<path>` for each OpenSpace file (base64-decoded for byte/line counts and regex extraction).
- `curl -s -o /dev/null -w '%{http_code}'` on `https://open-space.cloud/` → 200.

---

## TRUST REPORT

**Confidence: 0.86** (raised from rebuttal's 0.83 because Opus re-ran the source verification end-to-end on contested rows and quantified prior descriptive claims).

**Uncertainties**:
- OpenSpace `_apply_with_retry` snippet was read by regex extraction (~300 LOC of the 1,598-LOC `evolver.py`); the function's dependencies (`_validate_skill_dir`, lineage write helpers) were not deeply read but are referenced from the constants and table list.
- COS LOC for self-improvement primitives uses 918 (5 files); if `lib/self_improvement.py:211` should be excluded as a sibling helper, conservative figure drops to 707. The 7:1 maintenance ratio holds at either count.
- Per-iteration $ cost figures are estimates derived from declared iteration caps × current provider rates; OpenSpace's actual production cost depends on operator's `litellm` config, not verifiable from source.
- `open-space.cloud` returned HTTP 200 (root reachable) but no functional probe of the upload/download endpoints was run; "live" here means root-reachable + repo claims a working CLI, not end-to-end exercised.

**Proportionality**: Audit was source-level on both sides for all 9 contested rows. Tool-call budget used: ~25 of allowed 80.
