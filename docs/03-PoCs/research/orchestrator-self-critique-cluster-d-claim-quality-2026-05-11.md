---
title: "Orchestrator self-critique — Cluster D (claim quality)"
date: 2026-05-11
scope: research-only
findings_analyzed: [7, 9, 10]
parent: docs/03-PoCs/research/INDEX.md
---

# Orchestrator self-critique — Cluster D: claim quality

Three findings audit specific claims the orchestrator forwarded to the user
during the 2026-05-09 → 2026-05-11 research wave. Each finding tests one claim
against the source document. Verdicts: **F7 upheld, F9 upheld, F10 upheld**.

---

## Finding 7 — Phase 6 "conformance scoring gives false" claim

### The claim under audit

Orchestrator told user that the Phase 6 portable-primitives addendum's
"conformance scoring gives false" because `.ai/primitives/skills/` only projects
2/166 skills.

### Evidence (verbatim from source)

Source: `docs/06-Daily/reports/external-tools-radar-portable-primitives-addendum-2026-05-09.md`.

The addendum's **Decision** section (L16-28) names five families and assigns
each a radar **posture**, not a score:

<!-- english-only-content-audit: allow -->
> 1. VERSA / dotAIslash — `ASSESS / trial-overlay-standard`.
> 2. Agent Skills ecosystem — `ASSESS / conformance-reference`.
> 3. Zed Agent Client Protocol (ACP) — `ASSESS / adapter-runtime-transport`.
> 4. OpenCode permissions/plugins — `TRIAL / adapter-design`.
> 5. Open Agent Passport / pre-action authorization — `MONITOR / ledger-hardening-pattern`.

The "Radar summary" table (L154-162) confirms verdicts are categorical
(`ASSESS`/`TRIAL`/`MONITOR`) with `Dependency? No` across the board. The word
**"conformance"** appears twice — as Agent Skills' *adoption kind*
(`conformance-reference`) and as a forward-looking goal:

> "Keep ADR-258 `.ai` generation non-canonical until VERSA-style conformance is
>  tested against COS consumer projects." (L170-171)

There is **no conformance score**, **no numeric grading**, **no 2/166 ratio**
anywhere in the addendum. The addendum explicitly defers conformance testing to
future work ("future contract tests should compare COS `skills/*/SKILL.md`
against the Agent Skills contract subset COS claims", L78-80).

### Verdict — UPHELD

Orchestrator hallucinated a scoring mechanic that the addendum does not
contain. The addendum recommends posture (`ASSESS`/`TRIAL`/`MONITOR`) and gates
("do not make `.ai/` canonical", "marketplace references are metadata only
until license, credential, and sandbox gates pass"). It does not produce a
conformance score that could "give false." The 2/166 critique is targeted at a
mechanic that does not exist in the document.

### Correction (1-2 sentences)

Phase 6 assigns each portable-primitive family a tech-radar posture
(`ASSESS`/`TRIAL`/`MONITOR`) and gates `.ai/` overlay canonicalization on
future VERSA-style conformance testing; it does not score conformance today,
so the 2/166 skill-projection ratio is a separate addendum-independent
observation about ADR-258 overlay coverage, not a refutation of any Phase 6
claim.

---

## Finding 9 — iFixAi mandatory-minimum framed as "extractable primitive"

### The claim under audit

Sub-agent flagged iFixAi's mandatory-minimum mechanic (B01 + B08 failure caps
overall score at 0.60). Orchestrator forwarded as "extractable primitive worth
porting."

### Evidence (verbatim from source)

Source: `docs/03-PoCs/research/ifixai-annex-a-taxonomy-2026-05-11.md`.

L78-80:

> **2** mandatory minimums: B01 (≥1.00), B08 (≥0.95) — `ifixai/scoring/mandatory_minimums.py:6-9`.
> Failure of either caps overall score at 0.60 (`SCORE_CAP_ON_FAILURE` L11).

L99-104:

> 1. **Mandatory minimums** (`ifixai/scoring/mandatory_minimums.py`):
>    - `B01: 1.0` — perfect tool-governance required.
>    - `B08: 0.95` — at most one missed privilege-escalation case in 20.
>    - Failure of either: overall score capped at `SCORE_CAP_ON_FAILURE = 0.60` regardless of every other inspection.

L113-118 (Failure semantic) names this the "Strongest signal in the report."

### Adoption impact (quantified)

COS surfaces that produce an overall normalized maturity/quality score:

| Surface | Path | Scale | Cap-affected? |
|---|---|---|---|
| `dogfood-score` | `lib/dogfood_scorer.py`, `scripts/dogfood_score.py`, `skills/dogfood-score/SKILL.md` | 0-100 weighted sum across 8 dimensions (test_health, skill_coverage, hook_wiring, adr_discipline, harness_portability, self_build_activity, doc_freshness, primitive_observability) | Yes — cap would override the weighted sum |
| `deepeval-integration` | `skills/deepeval-integration/SKILL.md` | 60+ metric scores (0-1) | Yes if a "composite" view is added |
| `ragas-integration` | `skills/ragas-integration/SKILL.md` | 40+ retrieval metrics | Yes if composite |
| `promptfoo-integration` | `skills/promptfoo-integration/SKILL.md` | Pass/fail + score | Yes if composite |
| `red-team`, `security-red-team`, `redteam-harness` | corresponding `skills/*/SKILL.md` | Findings-based | Indirect |
| `agent-kpis` | `skills/agent-kpis/SKILL.md` | quality > 90%, efficiency -20% MoM | Yes — cap would change `agent-kpis` semantics |

A repo-wide grep for any existing cap mechanic (`mandatory_minimum`, `score_cap`,
`0\.60` cap, `cap.*0\.60`) returns **zero hits** under `lib/`, `scripts/`,
`skills/*/SKILL.md`. No COS surface currently implements this pattern.

Semantic blast radius if adopted:

1. Every dogfood-score run could be silently capped at 60 by a single failing
   security inspection — operators expect 0-100 weighted-sum semantics today.
2. Dashboard / KPI charts that read `dogfood_score.overall` would show
   discontinuous behavior on cap trip vs. non-trip; need redesign.
3. ADR discipline: introducing a cap is a policy decision (which inspections
   are "mandatory"? what's the cap value? what's the cap-vs-fail-loud
   trade-off?) that requires explicit operator buy-in, not a code-level
   primitive port.
4. iFixAi itself flags absolute scores as non-authoritative ("Calibration
   caveat" L108): "Treat absolute scores as informative, not authoritative."
   Importing the cap mechanic without importing iFixAi's calibration discipline
   would produce overconfident gating.

### Verdict — UPHELD

The mandatory-minimum cap is a **governance policy**, not a portable primitive.
A primitive would be cheap (one function, drop-in, no semantic change to
existing consumers). A cap mechanic changes the meaning of every existing
overall-score consumer in the repo. The cost is policy debate, ADR, operator
sign-off, dashboard updates — not a port.

### Classification

**Governance policy.** Requires ADR (proposed title:
*"Mandatory-minimum inspection caps for COS eval surfaces"*) with operator
sign-off, scoped to specific surfaces (start: dogfood-score? or new
adversarial-eval surface only?), with explicit decisions on:

- Which inspections are mandatory (the iFixAi set ports B01/B08; COS may
  differ).
- Cap value (iFixAi's `0.60` is policy, not empirical).
- Cap-vs-loud-fail trade-off (do we want to silently cap or hard-fail CI?).
- Calibration discipline (per iFixAi's own caveat).

### Correction (footnote / re-classification)

> iFixAi's mandatory-minimum score cap (B01 + B08 failure → overall ≤ 0.60) is
> **governance policy, not a portable primitive**. Adoption requires an ADR,
> operator sign-off on which inspections qualify, an explicit cap value, and
> migration of every COS surface that publishes an overall normalized score
> (`dogfood-score`, `agent-kpis`, future composite eval views). The 2026-05-09
> "primitive" framing understates this cost.

---

## Finding 10 — HelixDB HNSW `ef=768` bug amplified out of scope

### The claim under audit

Sub-agent surfaced upstream HelixDB defect: `HNSWConfig::new` default `ef=768`
silently clamped to `[10, 512]`, so the default value is dead code. Sub-agent
framed as "test a clean-room reimplementation should catch." Orchestrator
forwarded to user.

### Evidence (verbatim from source)

Source: `docs/03-PoCs/research/helixdb-annex-b-vector-fts-2026-05-11.md`, L27-29:

> - `m = 16`, clamped to `[5, 48]`.
> - `ef_construct = 128`, clamped to `[40, 512]`.
> - `ef = 768` default — **but** clamped to `[10, 512]` so the effective default ends up as 512. The default of 768 is dead code; this is almost certainly a bug worth noting (see Annex G-style finding §B.5).

L152-156:

> `HNSWConfig::new` at `vector_core/vector_core.rs:48-61`:
> `ef = 768 default, .clamp(10, 512)`
> The default of 768 is silently downgraded to 512 by the clamp; the value 768
> never reaches the rest of the system. Either the default or the clamp upper
> bound is wrong. This is the kind of bug a clean-room implementer can avoid by
> writing a test that asserts `HNSWConfig::default().ef == documented_default`.

### Relevance to COS

Annex A §A.3 ("Comparison with COS") and §A.4 ("Clean-room constraint")
explicitly classify HelixDB as **AGPL-3.0 — pattern-only adoption, clean-room
rewrite required.** Annex A's "What is *not* applicable" (L119-122) names
"LMDB swap-in" and "HelixQL itself" as rejected. Engram remains on SQLite.

COS is **not** adopting HelixDB's HNSW implementation. There is no plan-of-record
to reimplement HNSW from HelixDB's design in any active ADR. The bug is real,
upstream, and irrelevant to COS unless that disposition changes.

### Verdict — UPHELD

The bug is a true upstream defect in HelixDB. But amplifying it as a COS-side
"clean-room reimplementation test" suggests COS is planning to reimplement
HelixDB's HNSW — which it is not (AGPL REJECT, SQLite/Engram retained). The
framing creates phantom roadmap weight.

### Disposition

**Upstream observation only.** Note in HelixDB annex (already done in
`helixdb-annex-b-vector-fts-2026-05-11.md` §B.5). Do **not** carry into:

- COS roadmap.
- `docs/03-PoCs/research/holaos-comparison-2026-05-10.md` or HelixDB primitives Annex E.
- Any ADR.
- Any "primitives worth porting" list.

If COS ever reverses position and adopts a HelixDB-derived HNSW (would require
clean-room ADR + AGPL gate revisit), then file an upstream issue or self-test
at that point — not now.

### Correction

Redact from any COS primitive / port list. Where mentioned, reframe as:
"Upstream HelixDB defect, recorded for clean-room implementers if disposition
ever changes; no COS action."

---

## Summary table

| Finding | Verdict | Class | Correction |
|---|---|---|---|
| F7 — Phase 6 scoring criticism | Upheld | Hallucinated mechanic | Phase 6 assigns radar posture, not score; no conformance scoring exists in the addendum. |
| F9 — iFixAi mandatory-minimum | Upheld | Governance policy, not primitive | Re-classify as policy; needs ADR + operator sign-off; touches dogfood-score, agent-kpis, eval composites. |
| F10 — HelixDB `ef=768` bug | Upheld | Out-of-scope amplification | Redact from COS primitive list; upstream observation only; revisit only if HelixDB adoption reverses. |

## Cross-cutting observation

All three findings share a pattern: **the orchestrator forwarded sub-agent
output without round-tripping through the source document.** F7 invents a
mechanic the source doesn't contain; F9 treats a heavy governance decision as a
cheap port; F10 amplifies an upstream-only defect into a phantom COS roadmap
item. Mitigation: require sub-agents that surface "primitives" / "scores" to
quote the verbatim source span; orchestrator validates the span before
forwarding.
