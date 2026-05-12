---
title: "Orchestrator Self-Critique — Cluster C (Methodology)"
date: 2026-05-11
author: orchestrator (self-critique pass)
status: draft
scope: research-only
cluster: C
findings_analyzed: [5, 6]
related_artifacts:
  - skills/deep-tool-research/SKILL.md
  - rules/recommendation-grounding.md
related_research:
  - docs/03-PoCs/research/holaos-comparison-2026-05-10.md
  - docs/03-PoCs/research/helixdb-comparison-2026-05-11.md
  - docs/03-PoCs/research/ifixai-comparison-2026-05-11.md
  - docs/03-PoCs/research/megamemory-comparison-2026-05-11.md
  - docs/06-Daily/reports/master-pending-2026-05-11.md
engram_topic_key: self-critique/cluster-c-methodology
---

# Orchestrator Self-Critique — Cluster C (Methodology)

> Two methodology findings validated, remediated with concrete artifacts. No new analysis pass on the underlying tools — this is a meta-pass on how the deep evaluations were *shaped* and how the priority recommendations were *grounded*.

---

## 1. Scope

Cluster C of the 2026-05-11 self-critique covers **methodology** drift in the 2026-05-11 deep evaluation batch (HelixDB, iFixAi, MegaMemory). Two findings:

- **Finding 5** — Ad-hoc annex taxonomy per tool, breaking cross-tool comparison.
- **Finding 6** — Priority tables presented as analysis without operational-signal grounding.

Both findings reflect orchestrator behavior, not sub-agent behavior. Sub-agents executed the taxonomy and rankings that the orchestrator handed them; the orchestrator chose ad-hoc per-tool axes and skipped grounding before delegation.

---

## 2. Finding 5 — Ad-hoc annex taxonomy

### 2.1 Verdict

**CONFIRMED.** The drift is mechanical and reproducible from disk evidence.

### 2.2 Evidence

**Reference (locked taxonomy).** `docs/03-PoCs/research/holaos-comparison-2026-05-10.md` §10 and the annex set fix a 7-axis taxonomy:

| Letter | Domain |
|---|---|
| A | Memory |
| B | Cost / Budget |
| C | Evolution |
| D | Security / Plan |
| E | Architecture / Risks |
| F | Compliance / Clean-Room |
| G | Surprise findings |

**Drift.** The three 2026-05-11 deep evaluations each invented a fresh per-tool axis set:

| Tool | A | B | C | D | E | F/G |
|---|---|---|---|---|---|---|
| **holaOS** (reference) | Memory | Cost/Budget | Evolution | Security/Plan | Architecture/Risks | Compliance + Surprise |
| **HelixDB** (`helixdb-comparison-2026-05-11.md` §3) | Storage + querycompiler | Vector + FTS | Runtime + MCP | License + open-core risk | Primitives | (no F, no G) |
| **iFixAi** (`ifixai-comparison-2026-05-11.md` §5) | Taxonomy | Cross-judge | Manifest + fixtures | Provider + iMe split | Primitives | (no F, no G) |
| **MegaMemory** (`megamemory-comparison-2026-05-11.md` §5) | Concept graph | Embeddings port | MCP + merge | Explorer + installer | Primitives | (no F, no G) |

Three independent observations confirm: **no axis-letter has the same meaning across the three tools**, and **annexes F (Compliance) and G (Surprise) are missing in all three**. The shape of the holaOS evaluation was not preserved.

### 2.3 Consequence

Cross-tool comparison ("HelixDB §B vs MegaMemory §B" — i.e. "vector/FTS layer vs in-process embedding port") is **not mechanically possible**. Each future cross-comparison requires a per-tool re-mapping by hand, which the orchestrator promised in 3 separate turns and never wrote.

The downstream cost is: every meta-analysis ("which tool wins on memory governance?", "which tool has the strongest compliance posture?") becomes a fresh manual pass through three differently-shaped documents. The artifact-set looks deep but is comparison-shallow.

### 2.4 Remediation

Concrete artifact: **`skills/deep-tool-research/SKILL.md`** (skeleton, this commit). Locks the 7-axis taxonomy at the orchestrator boundary so future invocations cannot drift.

- 7 annexes fixed (A–G), names load-bearing.
- 5 Opus axes (A–E) + 2 Sonnet axes (F–G), per the holaOS pattern.
- Acceptance criteria (§7 of the SKILL.md) verifiable by `ls` + frontmatter grep.
- Engram topic key convention (`research/<tool>/annex-<letter>`) locks naming.
- Decision rule (1-liner, §9): invoke for **non-REJECT** verdicts where pattern extraction or vendoring is plausible; otherwise stay in Phase-4 light radar-addendum.

**Retroactive question** (open): should HelixDB/iFixAi/MegaMemory be re-shaped to fit A–G now? Proposal in SKILL.md §10 — append a 1-page slot-mapping appendix per tool rather than rewrite the annexes. Operator decision.

---

## 3. Finding 6 — Recommendations without grounding

### 3.1 Verdict

**CONFIRMED.** The priority tables in the 2026-05-11 deep evaluations cite no operational signals.

### 3.2 Evidence

Each deep evaluation contains a ranked recommendation list (typically in §6 verdict, §8 next steps, or in Annex E §6 primitives). Spot-check:

- `holaos-comparison-2026-05-10.md` §8 ("Próximos pasos recomendados") names 5 owners + estimaciones; no citation of `master-pending-*`, sprint state, dogfood-score, or sprint capacity.
- `helixdb-comparison-2026-05-11.md` Annex E (primitives) — same shape, ranked by analytical merit, no operational grounding.
- `ifixai-comparison-2026-05-11.md` §6 ("Sequencing: Phase A/B/C") — sequenced without referencing `radar-2026-05-08-implementation-tracker.md`, current sprint, or prior decisions in Engram.
- `megamemory-comparison-2026-05-11.md` §6 + Annex E — recommends "port the in-process MiniLM pipeline, nothing else" without citing memory bundle plans (`docs/04-Concepts/architecture/memory-layer-evolution-sdd.md` is referenced but only for cross-validation, not as a capacity/sequencing signal).

### 3.3 Signals that should have been consulted

Inventory check (this self-critique pass):

| # | Signal | Disk evidence found | Would have changed |
|---|---|---|---|
| 1 | **Master pending** | `docs/06-Daily/reports/master-pending-2026-05-11.md` — confirms Wave 2 (memory bundle) 🟢 substrate ready, Wave 3 🟢 initial slices landed, post-v0.28.0 follow-ups F1/F2/F3 ✅. | MegaMemory MiniLM port priority drops: Wave 2 substrate is already landed; embedder port is a P2 enhancement, not P1. iFixAi DECEPTION pillar rises: master-pending shows no Wave-aligned eval coverage there. |
| 2 | **Sprint state** | `.cognitive-os/sprints/sprint-b37c1353.json` (status `pending`, example fixture). No active live sprint with committed scope visible. | Holds priority assumptions to "no in-flight conflict"; absence of a live sprint means the orchestrator should have flagged capacity as *unknown*, not assumed available. |
| 3 | **Dogfood score** | `docs/06-Daily/reports/orchestrator-dogfood-smoke-test-2026-04-20.md` is the latest. ~3 weeks stale relative to 2026-05-11. | Recommendation cadence should explicitly note: dogfood signal stale → re-score before committing P1 work. Orchestrator did not flag this. |
| 4 | **Plans inventory** | `.cognitive-os/plans/{architecture,roadmaps,features,research,archive}/` — multiple active. Notably `architecture/governed-self-improvement-roadmap.md` referenced in master-pending. | HelixDB compile-to-DSL primitive should be sequenced *after* governed-self-improvement-roadmap Phase 3, not as an independent P1. |
| 5 | **Engram decisions** | `decision/holaos-adoption` referenced in holaOS §8.5 — orchestrator already records decisions there. The 2026-05-11 batch did NOT search for prior `decision/helixdb-adoption`, `decision/ifixai-adoption`, `decision/megamemory-adoption` before re-litigating. | Avoids re-litigating: addenda from `docs/06-Daily/reports/external-tools-radar-{helixdb,ifixai,megamemory}-addendum-2026-05-11.md` already carry verdicts (REJECT, ASSESS/TRIAL-PATTERNS, ASSESS/pattern-only). Deep eval recommendations must *extend* not contradict. |
| 6 | **Error-learning log** | `.cognitive-os/error-learning.jsonl` present. Not inspected during the 2026-05-11 batch. | Would catch recurring failure classes (e.g. if "HNSW port" already failed once, deprioritize). |
| 7 | **Cost predictor** | `scripts/cost_predict.py` + `lib/cost_predictor.py` exist. Not invoked during the batch. | A 7-annex deep pass costs ~40–80K tokens orchestrator + 7× sub-agent budgets. Not predicting before launching three of them is a governance miss. |

**Top 3 signals the orchestrator should have consulted** (in priority order):

1. **`docs/06-Daily/reports/master-pending-2026-05-11.md`** — fastest source-of-truth on what's open vs closed across all surfaces; would have directly downgraded the MegaMemory embedder priority (Wave 2 substrate already landed).
2. **Engram `decision/<tool>-adoption` queries** — prevents re-litigating prior addendum verdicts; the deep evaluation is supposed to *deepen* the existing decision, not replace it.
3. **`.cognitive-os/plans/architecture/`** + **plans inventory** — confirms whether a recommended primitive duplicates an in-flight plan (e.g. memory-layer evolution SDD already covers MegaMemory's contribution).

### 3.4 Remediation

Concrete artifact: **`rules/recommendation-grounding.md`** (this commit). 1-pager that:

- Defines the failure mode in plain language (§1).
- Locks the rule: ≥3 operational signals MUST be cited before any P0/P1/P2 table publishes (§2).
- Enumerates 10 canonical signals with paths (§3).
- Specifies citation format (§4).
- Defines the hard stop (§5) — if <3 signals, downgrade "Priorities" to "Candidate list (un-ranked)".
- Specifies what the rule does NOT require (§6) — un-ranked candidate lists are exempt.
- Defines enforcement levels (§7) — soft self-check, hard review-time, future lint script.

The rule is human-enforced first. Lint tooling (`scripts/lint_recommendation_grounding.py`) is a follow-up.

---

## 4. Cross-finding insight

Findings 5 and 6 are **co-symptoms** of the same orchestrator behavior: producing artifacts that *look* deep without enforcing the structural constraints that make depth comparable or actionable.

- Finding 5: depth without taxonomy = uncomparable.
- Finding 6: depth without grounding = un-actionable as priority.

Both remediations install structure at the orchestrator boundary: SKILL.md locks slot shape; rules/ locks citation discipline. Neither requires sub-agent behavior changes — sub-agents will fill the slots and cite the signals the orchestrator hands them.

---

## 5. Status of the 2026-05-11 batch

- **HelixDB, iFixAi, MegaMemory deep evaluations** — left as-is. Re-shaping into the A–G taxonomy is deferred to a future remediation pass. Recommended approach (SKILL.md §10): 1-page slot-mapping appendix per tool, not a full rewrite.
- **Future deep evaluations** — MUST use `/deep-tool-research` with the locked taxonomy.
- **Future priority tables in any research synthesis** — MUST comply with `rules/recommendation-grounding.md` from this commit forward.

---

## 6. Engram persistence

This artifact is persisted to Engram under:

- topic_key: `self-critique/cluster-c-methodology`
- type: `pattern`
- scope: `project`

The two derived artifacts are persisted separately by the orchestrator when invoking them or by the operator on first use.

---

## 7. Open follow-ups

1. **Retroactive slot-mapping appendix** for the 2026-05-11 batch (HelixDB / iFixAi / MegaMemory). Operator decision.
2. **`scripts/lint_recommendation_grounding.py`** — markdown parser that detects priority tables and verifies the trailing grounding block. Sonnet-sized task.
3. **`hooks/deep-research-axis-gate.sh`** — pre-commit gate that rejects any new file under `docs/03-PoCs/research/*-annex-*-<date>.md` whose frontmatter `axis:` field is outside the locked A–G set. Sonnet-sized task.
4. **Dogfood score refresh** — stale by ~3 weeks (2026-04-20). Independent of this critique, but surfaced during signal inventory.
