---
title: "MegaMemory Annex E — Extractable Primitives (ranked)"
date: 2026-05-11
parent: docs/research/megamemory-comparison-2026-05-11.md
source-repo: ".cognitive-os/external-source-cache/MegaMemory (v1.6.2)"
license_constraint: "MIT — vendoring legally allowed; per-primitive decision recorded below."
---

> **License attribution.** Code excerpts and structural descriptions quoted from `0xK3vin/MegaMemory` v1.6.2 (MIT License, Copyright (c) 2026 0xk3vin — see https://github.com/0xK3vin/MegaMemory/blob/main/LICENSE). MIT permits direct vendoring with copyright preservation. See [`megamemory-annex-f-compliance-cleanroom-2026-05-11.md`](megamemory-annex-f-compliance-cleanroom-2026-05-11.md) for the full compliance protocol and port-vs-vendor decisions.

# Annex E — Extractable Primitives (ranked)

MIT license permits direct vendoring. For each primitive below the table records:

- **Integration cost** into Engram / COS.
- **Complexity** (algorithmic + code).
- **Alignment** with the planned memory bundle (`docs/architecture/memory-layer-evolution-sdd.md`).
- **Vendor vs port** decision and rationale.

Ranking is by `extraction value / port cost` ratio.

---

## Rank 1 — In-process ONNX embedding pipeline ★★★★★

**Source:** `src/embeddings.ts:1-122` (Xenova/all-MiniLM-L6-v2, mean-pool + L2-norm, lazy singleton, cosine top-K linear scan).

| Property | Value |
|---|---|
| Integration cost | 3–5 days (Annex B port plan) |
| Complexity | Low — ~120 LoC in Python with `fastembed` |
| Bundle alignment | **Direct prerequisite for the LightRAG dual-level slice.** |
| Risk | Low — well-bounded, feature-flagged, single column on `observations` |
| Footprint | ~60 MB on-disk (onnxruntime + quantized model) |
| Decision | **PORT (don't vendor).** Different runtime (TS vs Python); idiomatic rewrite is cleaner and audit-friendlier. Attribute MegaMemory in `manifests/external-tools-adoption.yaml`. |

**Why first:** the LightRAG slice cannot ship without an embedder choice. This is the embedder. Cuts a dependency-blocker from the memory-bundle SDD critical path.

---

## Rank 2 — Explicit `resolve_conflict` MCP tool surface ★★★★

**Source:** `src/index.ts:496-536` (tool registration) + `src/tools.ts:354-410` (handler).

| Property | Value |
|---|---|
| Integration cost | <1 day — thin alias over `mem_judge` |
| Complexity | Trivial |
| Bundle alignment | Aligned with the `mem_judge` v2 slice (forced-reason + in-description guidance). |
| Risk | None — purely additive |
| Decision | **PORT pattern (no code).** Add an MCP tool alias named `resolve_conflict` in the Engram MCP server that wraps `mem_judge` with a forced `reason` parameter. Adopt the in-description discipline copy: "Do NOT just pick a side — write the truth." |

**Why second:** improves agent ergonomics across harnesses (clearer verb in tool-pickers), zero semantic change, costs nothing. Also lets COS describe a `resolve_conflict` capability in `manifests/external-tools-adoption.yaml` matching MegaMemory's surface for cross-tool comparability.

---

## Rank 3 — Append-only `timeline` audit table ★★★

**Source:** `src/db.ts:138-154` (schema), `src/timeline.ts` (logger).

```sql
CREATE TABLE timeline (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT DEFAULT (datetime('now')),
  tool TEXT NOT NULL,
  params TEXT NOT NULL,           -- JSON
  result_summary TEXT NOT NULL,
  is_write INTEGER NOT NULL,
  is_error INTEGER NOT NULL,
  affected_ids TEXT NOT NULL      -- JSON array
);
```

| Property | Value |
|---|---|
| Integration cost | 1–2 days |
| Complexity | Low |
| Bundle alignment | Overlaps with Engram observation lifecycle + session events. Not a port target, but a useful reference shape if/when we add a per-tool-call audit table to the Engram daemon. |
| Decision | **REFERENCE only.** Engram already audits via observation + session events. The `affected_ids` column shape is the one detail worth keeping in mind for any future audit-richer schema. |

---

## Rank 4 — Concept-kind schema as governance shape ★★

**Source:** `src/types.ts:22-28` (the 6 kinds: `feature | module | pattern | config | decision | component`).

| Property | Value |
|---|---|
| Integration cost | n/a |
| Complexity | n/a |
| Bundle alignment | Subsumed by the planned MIRIX `memory_class` overlay (semantic / episodic / procedural / working). |
| Decision | **REJECT for adoption.** Engram's free-form `type` strings + the planned MIRIX memory_class overlay are strictly more expressive. Useful as a reference for the MIRIX port: a fixed, agent-friendly enum is easier to reason about than free-form types. |

**Recommended action:** when the MIRIX slice lands, propose a fixed `memory_class` enum mirroring MegaMemory's discipline (closed set, enforced at the MCP boundary).

---

## Rank 5 — Multi-editor installer + managed-file marker ★★

**Source:** `src/install.ts:52-54` (`MANAGED_FILE_MARKER`), full installer module (`src/install.ts`, 724 LoC).

| Property | Value |
|---|---|
| Integration cost | <1 day for marker convention; 5+ days if we ever want full push-mode installer |
| Complexity | Low for marker, Medium for installer |
| Bundle alignment | Orthogonal — operator-experience surface, not memory algorithm. |
| Decision | **REFERENCE only.** COS doctrine is pull-mode (ADR-258 portable overlay), not push. **Borrow the `MANAGED_FILE_MARKER` convention** for any future file `cognitive-os-init` writes into user dotfile paths. The JSONC stripper (`src/install.ts:73-140`) is a small bonus utility worth keeping for any future settings.json-with-comments parsing. |

---

## Rank 6 — `merge_group` + `::left`/`::right` suffix branch-merge ★

**Source:** `src/merge.ts` (551 LoC) + the `source_branch`, `merge_group`, `merge_timestamp` columns on both `nodes` and `edges`.

| Property | Value |
|---|---|
| Integration cost | High (10+ days) |
| Complexity | Medium-high — three-way-merge-style flow without an ancestor |
| Bundle alignment | **No current COS requirement.** Engram is one-instance-per-project; there is no "feature branch with its own Engram" model. |
| Decision | **DEFER.** Park as a future port if COS ever ships long-running worktrees with divergent Engram observations (manifest-tracked branches each with their own `.cognitive-os/.engram/`). |

---

## Rank 7 — Graph explorer (D3-force / Canvas) ★

**Source:** `src/web.ts` (791 LoC) + `web/index.html`.

| Property | Value |
|---|---|
| Integration cost | 3–5 days for a Python+FastAPI re-implementation |
| Complexity | Medium — front-end discipline + a graph-export endpoint on Engram |
| Bundle alignment | Orthogonal — operator visualization surface. |
| Decision | **DEFER.** No current demand. Re-evaluate if "Engram explorer" appears in user requests. If we ever do this, **port** (don't vendor) — a Python+FastAPI re-impl fits the COS stack better than a Node sidecar. |

---

## 8 — ID-slug routine (`src/tools.ts:33-41`) — REJECT

Engram's `topic_key` is already a slug-style identifier with richer namespacing rules. No port value.

---

## 9 — Schema-v4 dedup-then-unique-index pattern — REFERENCE only

The pattern (`DELETE` duplicates then `CREATE UNIQUE INDEX`, `src/db.ts:158-169`) is a clean reference for any future Engram migration adding stricter constraints on `memory_relations`. Not a port target — it's a recipe.

---

## Roll-up table

| # | Primitive | Decision | When | Vendor-or-port |
|---|---|---|---|---|
| 1 | In-process ONNX embedder | **PORT** | LightRAG dual-level slice | Port to Python (fastembed) |
| 2 | `resolve_conflict` tool alias | **PORT pattern** | `mem_judge` v2 slice | Re-implement (no code copy) |
| 3 | Timeline audit table | REFERENCE | If audit-rich schema ever needed | n/a |
| 4 | Closed `kind` enum | REFERENCE | MIRIX slice | n/a |
| 5 | Managed-file marker + JSONC | REFERENCE | If `cognitive-os-init` writes dotfiles | Port marker convention |
| 6 | Branch-merge engine | DEFER | If divergent worktree Engrams appear | Port if ever |
| 7 | D3+Canvas explorer | DEFER | If "Engram explorer" demanded | Port (FastAPI) |

---

## Net actions

- **Immediate (folded into existing memory-bundle SDD):** primitives #1 and #2.
- **Reference shelf (no current ticket):** #3, #4, #5.
- **Triggered ports (open spike only if condition fires):** #6, #7.

No code is vendored from MegaMemory. All adoption is pattern-port with attribution recorded in `manifests/external-tools-adoption.yaml` at port time.
