---
title: "MegaMemory Annex C — MCP Tool Surface & Conflict-Merge"
date: 2026-05-11
parent: docs/03-PoCs/research/megamemory-comparison-2026-05-11.md
source-repo: ".cognitive-os/external-source-cache/MegaMemory (v1.6.2)"
---

> **License attribution.** Code excerpts and structural descriptions quoted from `0xK3vin/MegaMemory` v1.6.2 (MIT License, Copyright (c) 2026 0xk3vin — see https://github.com/0xK3vin/MegaMemory/blob/main/LICENSE). MIT permits direct vendoring with copyright preservation. See [`megamemory-annex-f-compliance-cleanroom-2026-05-11.md`](megamemory-annex-f-compliance-cleanroom-2026-05-11.md) for the full compliance protocol and port-vs-vendor decisions.

# Annex C — MCP Tool Surface & Conflict-Merge

Enumerates all 9 MCP tools, drills the two-way merge engine, and contrasts MegaMemory's explicit `list_conflicts` / `resolve_conflict` tools against Engram's `judgment_required` envelope + per-candidate `mem_judge` heuristic.

---

## 1. The 9 MCP tools

All registered in `src/index.ts:205-536`, instrumented uniformly with a `timeline.log(...)` call on both success and error paths.

### 1.1 `understand` — semantic query (`src/index.ts:205-236`, handler `src/tools.ts:109-137`)

```ts
server.tool("understand",
  "Query the project knowledge graph. Call this before starting any task ...",
  {
    query: z.string(),
    top_k: z.number().int().min(1).max(50).optional(),  // default 10
  },
  async (params) => { ... }
);
```

Flow: embed query → fetch all active nodes with embeddings → cosine top-K → build `NodeWithContext` for each match (children + outgoing + incoming + parent).

### 1.2 `get_concept` — exact lookup (`src/index.ts:238-268`, handler `src/tools.ts:139-148`)

Exact ID lookup, returns the same `NodeWithContext` shape. Companion to `understand` for when the agent already knows the ID.

### 1.3 `create_concept` — write a new concept (`src/index.ts:270-320`, handler `src/tools.ts:150-191`)

```ts
{
  name: z.string(),
  kind: NodeKindEnum,
  summary: z.string(),
  why: z.string().optional(),
  parent_id: z.string().optional(),
  file_refs: z.array(z.string()).optional(),
  edges: z.array(z.object({
    to: z.string(),
    relation: RelationEnum,
    description: z.string().optional(),
  })).optional(),
  created_by_task: z.string().optional(),
}
```

Returns `{ id, message }`. Generates ID via slug normalization (`src/tools.ts:33-41`), embeds the composed text, inserts node + edges atomically (`src/db.ts:257-310` `insertNodeAndEdges`).

### 1.4 `update_concept` — partial update (`src/index.ts:322-362`, handler `src/tools.ts:193-223`)

```ts
{ id: z.string(), changes: { name?, kind?, summary?, why?, file_refs? } }
```

Re-embeds **only if** `name`, `kind`, or `summary` changed. This is a smart optimization — `why` and `file_refs` are searched lexically not semantically.

### 1.5 `link` — add edge (`src/index.ts:364-401`, handler `src/tools.ts:225-253`)

```ts
{ from, to, relation: RelationEnum, description?: string }
```

Validates both endpoints exist; relies on schema v4 UNIQUE(from,to,relation) index for idempotency. Returns existing-edge notice if already present.

### 1.6 `remove_concept` — soft delete (`src/index.ts:403-434`, handler `src/tools.ts:255-275`)

```ts
{ id, reason: z.string() }   // reason mandatory
```

Sets `removed_at` + `removed_reason`. Refuses if already removed. **Forced reason** is good governance — Engram's `mem_delete` is comparable.

### 1.7 `list_roots` — overview (`src/index.ts:436-464`, handler `src/tools.ts:277-299`)

Returns top-level concepts (no parent) with their direct children. Adds a `hint` field nudging the agent toward `/user:bootstrap-memory` when the graph is empty. Also returns `db.getStats()` in the same envelope.

### 1.8 `list_conflicts` — surface unresolved merges (`src/index.ts:466-494`, handler `src/tools.ts:303-352`)

Returns groups of `ConflictVersion` entries keyed by `merge_group` UUID. Each group has both branches' versions side-by-side with full data (name, kind, summary, why, file_refs, edges, removed_at).

### 1.9 `resolve_conflict` — write resolved content (`src/index.ts:496-536`, handler `src/tools.ts:354-410`)

```ts
{
  merge_group: z.string(),
  resolved: { summary: z.string(), why?: z.string(), file_refs?: z.array(z.string()) },
  reason: z.string(),  // "Explanation of what you verified ..."
}
```

The handler:

1. Loads all nodes in the merge_group, picks a non-removed base (or first node).
2. Strips the `::left` / `::right` suffix to compute the canonical original ID.
3. Inside a transaction: hard-deletes other versions, renames base to original ID, applies resolved content, re-embeds, clears merge flags on node + edges.

The tool description nudges the agent away from naive picking:

> "Do NOT just pick a side — write the truth."

That instruction in the tool description is itself a pattern worth borrowing for our `mem_judge` prompts.

---

## 2. The merge engine

### 2.1 What it does (`src/merge.ts`, 551 LoC)

`megamemory merge left.db right.db --into merged.db [--left-label X --right-label Y]`:

1. Opens left and right DBs **read-only**, output as a fresh DB.
2. For each node ID in the union of left/right:
   - If only one side has it → clean copy.
   - If both sides have it and `nodesAreIdentical` (deep equality of name/kind/summary/why/parent_id/file_refs/removed_state, `src/merge.ts:43-61`) **and** `edgeSetsAreIdentical` (`src/merge.ts:73-82`) → clean copy.
   - Else → assign a new `merge_group` UUID, write both versions with `::left` / `::right` suffixed IDs, set `needs_merge=1`, `source_branch=label`, `merge_timestamp=now()`.
3. Output DB has both versions sitting side by side, waiting for `resolve_conflict` calls.

### 2.2 What it does **not** do

- No three-way merge (no common ancestor).
- No automated heuristic merger of summaries — every conflict surfaces to the agent.
- No embedding-aware similarity bypass — even near-identical summaries with different whitespace become conflicts.

### 2.3 Suffix discipline (`src/merge.ts:5-37`)

```ts
export const MERGE_SUFFIX_LEFT = "::left";
export const MERGE_SUFFIX_RIGHT = "::right";

export function stripMergeSuffix(id: string): string {
  if (id.endsWith(MERGE_SUFFIX_LEFT)) return id.slice(0, -7);
  if (id.endsWith(MERGE_SUFFIX_RIGHT)) return id.slice(0, -8);
  return id;
}
```

ID-suffix discipline lets the resolved ID round-trip to the original namespace. Simple, works, no extra columns required for routing.

---

## 3. Engram's analogue (CONFLICT SURFACING protocol)

From `CLAUDE.md` (project + global) "CONFLICT SURFACING — when mem_save returns candidates":

```
After every mem_save call, check the response envelope for judgment_required.

IF judgment_required IS TRUE:
  Iterate candidates[] and call mem_judge once per candidate ...

  HEURISTIC — when to ask the user vs. resolve autonomously:

  ASK the user when:
    - confidence < 0.7, OR
    - relation ∈ {supersedes, conflicts_with} AND type ∈ {architecture, policy, decision}

  RESOLVE silently (mem_judge without asking) when:
    - confidence ≥ 0.7 AND relation ∉ {supersedes, conflicts_with}, OR
    - relation ∈ {related, compatible, scoped, not_conflict}
```

Implementation: `judgment_required` envelope is computed at `mem_save` time by the Engram daemon; `mem_judge` is the single resolution endpoint that approves/rejects pending `memory_relations` rows.

---

## 4. MegaMemory vs Engram — conflict surfacing verdict

| Dimension | MegaMemory | Engram | Verdict |
|---|---|---|---|
| **Trigger surface** | Out-of-band: `megamemory merge` CLI seeds conflicts; `list_conflicts` exposes them to the agent. | In-band: every `mem_save` may return `judgment_required=true` with candidates inline. | **MEJOR_NUESTRO** for inline ergonomics; **MEJOR_EXTERNO** for the explicit branch-merge use case (we don't have that today). |
| **Resolution verb** | Explicit MCP tool `resolve_conflict` with a free-text `resolved.summary` and forced `reason`. | `mem_judge` with relation-specific resolution; ASK-vs-RESOLVE heuristic in CLAUDE.md. | **IGUAL** — different ergonomics, same outcome. MegaMemory's explicit verb is friendlier as a tool name in tool-pickers. |
| **Agent guidance** | Tool description literally says: "Do NOT just pick a side — write the truth." | Heuristic in CLAUDE.md tells agent when to ASK user. | **IGUAL** — both apply discipline at the call site. Their inline-in-the-tool-description copy is a nicer pattern; ours is in a rule document. |
| **Auto-resolution** | None. Every conflict requires a `resolve_conflict` call. | Heuristic-driven auto-resolve when `confidence ≥ 0.7` and relation is benign. | **MEJOR_NUESTRO** — less agent overhead on safe cases. |
| **Conflict typing** | Boolean `needs_merge` + `merge_group` UUID. | Typed relations (`supersedes` vs `conflicts_with` vs `scoped` vs ...) carry semantics. | **MEJOR_NUESTRO** — richer wire signal. |
| **Audit** | `timeline` table logs `resolve_conflict` invocation with affected IDs. | Engram observation lifecycle + judgment lifecycle. | **IGUAL**. |
| **Three-way / ancestor merging** | No. | n/a (different model — Engram has no branch concept). | **NO_COMPARABLE**. |
| **Branch model** | Explicit `source_branch` column + `::left` / `::right` suffix IDs. | No branch model — memory is a single timeline per project. | **MEJOR_EXTERNO** for the niche use case (multi-developer divergent Engram DBs); but COS does not currently have that requirement. |

---

## 5. What's worth borrowing for COS

1. **The explicit `resolve_conflict` tool name** as a portability alias over `mem_judge`. Pure surface ergonomics, no semantic change. Reason: tool-pickers and other harnesses see a clearer verb. Cost: trivial (an alias wrapper in the Engram MCP layer).

2. **The forced `reason` parameter** on destructive/resolving tools. Engram's `mem_delete` already forces a reason; consider mirroring on `mem_judge` resolution.

3. **In-description discipline** ("Do NOT just pick a side — write the truth."). Move the agent guidance from CLAUDE.md into the MCP tool description itself for `mem_judge`, so it's seen at call-site, not only at session start.

4. **`source_branch` + UUID `merge_group`** as a *future* mechanism for cross-Engram-instance merging (e.g., long-running worktree branches each accumulating their own Engram observations). Not needed today. Worth noting in the memory-bundle SDD as a future port.

5. The `timeline` audit table (`src/db.ts:138-154`) — append-only per-tool log with `is_write`, `is_error`, `affected_ids`. Engram has equivalent coverage through observation lifecycle, so verdict is **IGUAL**; not a port target.

---

## 6. What's NOT worth borrowing

- The merge CLI itself — no current cross-DB merge requirement in COS.
- The `::left` / `::right` ID-suffix scheme — Engram's typed relations encode this more cleanly.
- The boolean `needs_merge` flag — subsumed by `judgment_status='pending'`.

---

## 7. Where it lands

Nothing in this annex requires immediate action. The tool-naming and forced-reason ideas land in the **memory-bundle SDD** when we cut the `mem_judge` v2 slice. The branch-merge primitive is parked until COS hits the "two long-running worktrees with divergent Engram observations" problem.
