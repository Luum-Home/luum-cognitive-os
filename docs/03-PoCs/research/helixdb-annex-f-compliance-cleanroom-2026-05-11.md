---
title: "HelixDB Annex F — Compliance & Clean-Room Protocol"
date: 2026-05-11
annex: F
parent: helixdb-comparison-2026-05-11.md
scope: research-only
license_classification: "AGPL-3.0 — REJECT runtime / TRIAL-PATTERNS clean-room only"
---

# Annex F — Compliance & Clean-Room Protocol for HelixDB

## 1. License posture (canonical)

The upstream repository (`https://github.com/HelixDB/helix-db`) is licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0), confirmed verbatim at `LICENSE` line 1: `GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007`.

**Runtime verdict: REJECT.** Per `rules/license-policy.md`, AGPL is on the BLOCK list. AGPL-3.0 §13 triggers the copyleft obligation on any network interaction — including an agent, a user, a remote MCP client, or a CI service interacting with a HelixDB-derived instance. Linking `helix-db` as a Rust dependency would propagate §13 to the entire linked binary. Dynamic linking is not a recognised AGPL escape hatch. See annex D §D.1 for the complete analysis.

**Pattern lane verdict: TRIAL-PATTERNS.** Promoted from HOLD on 2026-05-11 after cluster-B coherence audit (see annex E §1). The three primitives documented in §3 below are available for clean-room reimplementation under TRIAL-PATTERNS doctrine. No other primitives from the HelixDB corpus are authorised for adoption without a separate operator decision.

---

## 2. What this corpus is and is NOT

**This corpus (annexes A–F) contains:**
- Paraphrased structural descriptions of HelixDB components (architecture, data-flow, configuration shapes).
- Short factual excerpts: enum variant names, config field names, numeric defaults. These are non-creative API facts, not expressive authorship.
- Pseudo-syntax code blocks sketching data-structure shapes and algorithm parameters. None reproduce a creative sequence of Rust statements.
- Section references to upstream source files (e.g. `vector_core.rs:31-62`) cited as evidence-of-shape for the documented pattern, not as copy.

**This corpus does NOT contain:**
- Verbatim Rust source code above a creative-expression threshold.
- Redistributed helix-db binaries or compiled artifacts.
- Copied test fixtures, identifiers, or comments from the upstream repository.

**External source cache:** A shallow clone used during the research pass was stored at `.cognitive-os/external-source-cache/helix-db/`. That path is gitignored per ADR-255 and is NOT part of this repository. No content from it was vendored. Engineers implementing clean-room rewrites MUST NOT consult that cache directory.

---

## 3. Clean-room rewrite protocol

The three TRIAL-PATTERNS primitives authorised for adoption (from annex E §1, top-3 rows) are:

1. **Typed-ADT agent-call surface** — a closed, recursive algebraic data type for the MCP tool catalogue (annex E §E.1; evidence-of-shape: annex C §C.4).
2. **Reranker fusion (RRF + MMR)** — an explicit reranker layer with Reciprocal Rank Fusion and Maximal Marginal Relevance strategies (annex E §E.2; evidence-of-shape: annex B §B.3).
3. **Hoisted-embedding / IO-continuation** — separating embedding/network calls from the transaction scope, and expressing mid-transaction IO as a returned continuation (annex E §E.3; evidence-of-shape: annex B §B.1 + annex C §C.3).

For each primitive, the following two-engineer clean-room protocol applies:

**Step 1 — Behavioral spec (Engineer A reads annexes only).**
Engineer A reads the relevant COS-side annex sections (listed in §4 below) and writes a behavioral specification: inputs, outputs, invariants, performance contracts. Engineer A does NOT read upstream helix-db source during or after this step.

**Step 2 — Implementation (Engineer B, no helix-db exposure).**
Engineer B has no prior exposure to the HelixDB codebase. Engineer B implements exclusively from the behavioral spec produced in Step 1. If Engineer B has previously read helix-db source, they must disclose this and a third reviewer must perform an independent diff review before the PR can merge.

**Step 3 — Citation.**
The resulting implementation is cited as: "clean-room derived from behavioral spec, no upstream helix-db code referenced." The ADR for the feature names these annexes as the design-evidence source and explicitly states the upstream file references are cited as evidence the design exists, not as implementation source.

**Step 4 — Pre-commit gate.**
Every PR adding TRIAL-PATTERNS code must pass the external-pattern clean-room gate (see §5). The `git diff` of the PR must contain zero strings copied verbatim from `.cognitive-os/external-source-cache/helix-db/`.

---

## 4. Per-primitive clean-room input source paths

| Primitive | Annex source sections | Implementation rule |
|---|---|---|
| Typed-ADT agent-call surface | Annex E §E.1; Annex C §C.4 (typed `ToolArgs` enum evidence-of-shape) | Spec from annex E §E.1 and annex C §C.4 pattern description only. Do NOT read `helix-db/src/helix_gateway/mcp/tools.rs`. Variant names must be COS memory verbs (`Recall`, `RelatedTo`, `Filter`, `Crystallize`, `Hybrid`) — not graph-traversal verbs (`OutStep`, `InStep`, `NFromType`, etc.). Do not copy the `tag = "tool_name", content = "args"` serde shape. |
| Reranker fusion (RRF + MMR) | Annex E §E.2; Annex B §B.3 (RRF/MMR/score-normalizer evidence-of-shape) | Spec from annex E §E.2 and annex B §B.3 pattern description only. Do NOT read `helix-db/src/helix_engine/reranker/`. Cite papers directly: Cormack/Clarke/Buettcher 2009 (RRF), Carbonell/Goldstein 1998 (MMR). Default `k = 60` and `lambda = 0.7` are paper-canonical values, not helix-specific. |
| Hoisted-embedding / IO-continuation | Annex E §E.3; Annex B §B.1 (HNSW static-hoist evidence); Annex C §C.3 (`IoContFn` runtime-continuation evidence) | Spec from annex E §E.3 and annex C §C.3 pattern description only. Do NOT read `helixc/generator/queries.rs` or `helix_gateway/router/router.rs`. Implement as Python `async with` / context-manager pattern — do not mirror `IoContFn`'s Rust closure-based design. Derive from the requirement: "no SQLite write transaction held across an LLM call." |

---

## 5. Pre-commit gate (recommended)

The repository ships `hooks/external-pattern-cleanroom-gate.sh` as the enforcement mechanism for external-pattern adoption. For any PR adding TRIAL-PATTERNS code derived from HelixDB annexes, either:

- **Extend** `external-pattern-cleanroom-gate.sh` with a HelixDB-specific string-match block, or
- **Add a new hook** `hooks/helixdb-cleanroom-gate.sh` that verifies the `git diff` contains no verbatim strings from known helix-db identifiers (e.g. `IoContFn`, `ToolArgs`, `HNSWConfig`, `HELIX_DATA_DIR`, `helix_engine`, `OutStep`, `NFromType`).

The gate should run on `pre-commit` and `pre-push`, block on any match, and print the offending lines with a remediation message pointing to these annexes.

---

## 6. Open questions

1. **Paraphrased struct-field listings and the creative-expression threshold.** Several code blocks in annex B enumerate config fields such as `HNSWConfig { m, m_max_0, ef_construct, m_l, ef, min_neighbors }`. Field names are factual API surface, not expressive authorship — the lean is NO (does not cross the creative-expression threshold). However, if any primitive derived from these listings enters the `sdd-apply` phase, flag for legal review before merge.

2. **Fair-use posture for research-only use.** The operator's use of these research notes is non-redistributed, internal, and transformative (paraphrase + behavioral-spec derivation). This is likely covered by 17 U.S.C. § 107 fair use on all four factors (purpose/character, nature of the work, amount taken, market effect). Document this position explicitly in the ADR for any primitive that enters implementation.

3. **Cluster-D claim-quality ruling scope.** The HNSW default-clamp inconsistency (annex B §B.5, annex E §E.4.5) was scoped as an upstream-only observation by the cluster-D ruling (2026-05-11). If AGPL disposition ever reverses, that finding should be filed upstream before any COS HNSW work begins.

4. **`HELIX_CLUSTER_ID` and multi-tenant patterns.** Annex C §C.1 documents the cluster-ID env-var pattern. This is a factual config value (non-creative). If a COS multi-tenant scoping mechanism ever needs a similar env-var, derive the name from COS conventions (`COS_CLUSTER_ID` or `ENGRAM_SCOPE`) — not from the helix name.
