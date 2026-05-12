<!-- SCOPE: os-only -->
<!-- TIER: 2 -->
---
name: clean-room-detection-limits
audience: os-dev
last-updated: 2026-05-11
related-adrs: [ADR-029b, ADR-267, ADR-271]
---

# Clean-Room Detection — Mechanical Limits

## Purpose

Document what pre-commit hooks and audits can and cannot detect when guarding
against derivative-work introduction from external-source-cache material. The
matrix below is the operating contract: when an agent or operator hits a class
of risk that hooks do NOT cover, the residual defense is process + legal review,
not more tooling.

This rule is referenced in error messages from `hooks/external-cache-content-leak.sh`,
`hooks/lib-symlink-divergence-detector.sh`, and any future Tier-2+ tooling.

## The detection matrix

| Tier | What it detects | What is missed | Implementation |
|---|---|---|---|
| **T1 — Verbatim hash** | Identical / near-identical N-line windows (8 lines, SHA-256 fingerprint). | Anything beyond byte-near-identical copy. | `hooks/external-cache-content-leak.sh` + `scripts/cos_verbatim_copy_detector.py` (ADR-267 Hook #2, live) |
| **T2 — AST normalized similarity** | Symbol-renamed clones; structural ports where the algorithm is preserved but identifiers / formatting differ. | Paraphrased adaptations with substantively different syntax; cross-language ports. | `hooks/clean-room-ast-similarity-gate.sh` + `scripts/cos_clean_room_ast_similarity.py` (ADR-271, planned). Reuses Jaccard tokenisation from ADR-029b. |
| **T3 — Semantic embeddings** | Paraphrased adaptations where wording / logic differs but intent is the same. | Pseudocode descriptions; concept-only reuse. | Deferred. Phase B-beta of ADR-029b targets the same infra; will be reused. Not pre-commit (latency); nightly batch only. |
| **T4 — LLM-assisted review** | Pseudocode / prose descriptions of cache content. Highest fidelity for "is this derivative?". | Concept-only reuse where prose is generic. | Not implemented. Cost + latency prohibitive at commit time. Operator-triggered for high-stakes adoptions only. |
| **T5 — Process / legal** | Concept-level reuse, design-pattern lift, idiomatic similarity. Anything the prior tiers do not catch by construction. | Nothing — this is the final stop. | Annex F (per-tool), `reviewed-by-legal: yes` marker, ADR Accepted by counsel, NOTICE preservation, USPTO / trademark searches where relevant. |

## What hooks fundamentally cannot do

Hooks **reduce probability of error**. They **do not establish legal compliance**.
The boundary is structural:

- Copyright law (US) does not protect ideas, methods, or functionality — only
  specific expression. Mechanical similarity measures over-fit to the protected
  surface (expression) but under-fit to the doctrines that matter (substantial
  similarity, idea-expression merger, fair use, scenes a faire).
- A clean-room rewrite passes T1-T4 trivially while remaining vulnerable to the
  doctrines that decide cases.
- Conversely, code that fails T1 may still be defensible (verbatim quotation
  under fair use with proper attribution — what Annex F documents for the 4
  retroactive adoptions).

Tiers are best understood as filters that catch the **obvious accidents**. The
non-obvious cases are inherent to the law and require human judgment.

## Decision rule for "which tier is enough?"

For each tool family entering apply phase under ADR-267:

| Risk profile | Required tiers active | Why |
|---|---|---|
| MIT / Apache-2.0 upstream, attribution present, runtime port | T1 + T2 + T5 (Annex F, NOTICE) | License allows reuse; T1+T2 catch sloppy attribution drift; T5 satisfies the licence obligations. |
| AGPL / SSPL / BSL / ELv2 upstream, pattern-only | T1 + T2 + T5 (Annex F with clean-room rewrite protocol) | License blocks any derivative; T1 + T2 enforce the clean-room boundary mechanically; T5 documents the engineer-A / engineer-B split. |
| Unverified license upstream | All adoption BLOCKED until upstream is identified | No tier helps without a baseline to compare against. |
| Conceptual reuse only (no code copy) | T5 only | T1-T4 will not fire; this is design-pattern adoption. Defended via ADR + idea-expression-merger argument. |

The freeze mechanism (`manifests/external-tool-adoption-freeze.yaml` + ADR-267
Hook #3) is the gross-level kill switch when cumulative risk crosses operator
tolerance, irrespective of per-tool tier coverage.

## What error messages should say

Hooks at T1 and T2 must emit error messages that:

1. State which tier fired.
2. Link to this rule (`rules/clean-room-detection-limits.md`) so the operator
   understands the residual gap.
3. Point at the per-tool Annex F path when a known adoption is involved.
4. Document the bypass env var and the audit-log path so an emergency bypass
   leaves a paper trail.

Generic phrasing for the bottom of every error block:

> Tiers T3-T5 are not enforced by this hook. If your change involves paraphrased
> adaptation or design-level reuse from an upstream tool, file or update the
> per-tool Annex F (`docs/03-PoCs/research/<tool>-annex-f-*.md`) before commit.
> See `rules/clean-room-detection-limits.md` for the full matrix.

## Open questions

1. **Pseudocode detection** — should the verbatim hash hook also scan
   `docs/03-PoCs/research/*-annex-*.md` for verbatim cache blocks? Annexes legitimately
   quote upstream under attribution; pre-commit warn (not block) on these is the
   likely answer. Deferred until T2 lands.
2. **Cross-language drift** — `lib/file_mutation_queue.py` was ported from a
   `.ts` upstream. T1 byte-hash fingerprint will not detect a TS to Python
   translation. T2 AST normalization is also single-language. Cross-language
   similarity is currently T5 only.
3. **Embedding store size** — Phase B-beta of ADR-029b plans embeddings for the
   COS corpus (~550 files). Extending to external-source-cache adds N-thousand
   files. Storage and update cadence design pending.
4. **CI cadence vs commit cadence** — T1 and T2 are pre-commit. T3 nightly is
   the target. Should there be a release gate that re-runs T1-T2 on the full
   diff between main and release tag? Operator decision.
