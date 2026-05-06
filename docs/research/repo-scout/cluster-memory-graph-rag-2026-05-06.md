---
cluster: memory-graph-rag
date: 2026-05-06
phase: shallow
budget_max_tool_calls: 45
tool_calls_used: 5
theme: graph-RAG / graph-memory / hierarchical retrieval
totals:
  input: 12
  resolved: 11
  unresolved: 1
  passed_license: 11
  rejected_license: 0
  triage:
    extract: 4
    monitor: 5
    skip: 2
    unresolved: 1
  phase2_candidates: 4
sums_check: "extract(4) + monitor(5) + skip(2) + unresolved(1) = 12 == input(12)"
---

# Repo Scout — memory-graph-rag (shallow)

Theme: graph-based retrieval and graph-memory primitives for AI agents. Project already runs an Engram graph-memory primitive, so overlap with full frameworks is high. Strategy: extract algorithms (LightRAG dual-level retrieval, HippoRAG personalized PageRank, graphiti bi-temporal model) rather than adopt frameworks wholesale. Reject AGPL/SSPL/BSL/FSL — none triggered.

## Per-repo triage

### 1. CodeGraphContext/CodeGraphContext
- URL: https://github.com/CodeGraphContext/CodeGraphContext
- License: MIT
- Stars: 3,160
- Last commit: 2026-05-04
- Primary language: Python
- Purpose: MCP server + CLI that indexes local code into a graph DB to feed AI assistants.
- Verdict: MONITOR
- Rationale: Active, well-licensed, MCP-shaped — but scope (code-as-graph for assistants) overlaps with our Engram primitive. Watch for indexing-pipeline patterns (AST → nodes/edges) we can lift; not framework-adopt.

### 2. DEEP-PolyU/Awesome-GraphMemory
- URL: https://github.com/DEEP-PolyU/Awesome-GraphMemory
- License: none (curated list, no code; LICENSE file absent)
- Stars: 260
- Last commit: 2026-04-01
- Primary language: n/a (markdown survey)
- Purpose: Curated survey of graph-based agent memory papers, benchmarks, projects.
- Verdict: EXTRACT (read-only, references not code)
- Rationale: Survey-quality index of the exact problem space we are in. No code to license. Use as a Phase-2 reading list to seed taxonomy and benchmark choices for our graph-memory work.

### 3. HKUDS/LightRAG
- URL: https://github.com/HKUDS/LightRAG
- License: MIT
- Stars: 34,788
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: EMNLP'25 paper — simple/fast graph-augmented RAG with dual-level (low/high) retrieval.
- Verdict: EXTRACT
- Rationale: Dual-level retrieval algorithm (entity-level + topic-level) is a small, portable idea that maps cleanly onto our existing graph store. MIT lets us adopt code+patterns. Top Phase 2 candidate.

### 4. OSU-NLP-Group/HippoRAG
- URL: https://github.com/OSU-NLP-Group/HippoRAG
- License: MIT
- Stars: 3,483
- Last commit: 2025-09-04
- Primary language: Python
- Purpose: NeurIPS'24 — hippocampus-inspired RAG using KG + Personalized PageRank for multi-hop recall.
- Verdict: EXTRACT
- Rationale: Personalized PageRank over an entity graph is a well-defined algorithm we can port to Engram for multi-hop recall. MIT, paper-grade reference impl. Small, lift the algorithm not the framework.

### 5. devwhodevs/engraph
- URL: https://github.com/devwhodevs/engraph
- License: MIT
- Stars: 130
- Last commit: 2026-04-21
- Primary language: Rust
- Purpose: Local KG for AI agents with hybrid search + MCP server, scoped to Obsidian vaults.
- Rationale: Direct namespace + scope overlap with our own Engram primitive. Rust impl could inform performance choices, but feature set (hybrid search + MCP) duplicates ours. Lean monitor; revisit only if it ships a unique retrieval trick.
- Verdict: MONITOR

### 6. getzep/graphiti
- URL: https://github.com/getzep/graphiti
- License: Apache-2.0
- Stars: 25,732
- Last commit: 2026-04-30
- Primary language: Python
- Purpose: Real-time bi-temporal knowledge graphs for AI agents (Zep's open core).
- Verdict: EXTRACT
- Rationale: Bi-temporal model (event-time vs ingest-time) is a known gap in our graph-memory primitive. Apache-2.0 permits adopting the schema/algorithm. Extract the temporal edges design, not the full server.

### 7. jayminwest/overstory
- URL: https://github.com/jayminwest/overstory
- License: MIT
- Stars: 1,271
- Last commit: 2026-05-02
- Primary language: TypeScript
- Purpose: Multi-agent orchestration with pluggable runtime adapters (Claude Code, Pi, etc.).
- Verdict: SKIP
- Rationale: Mis-clustered — orchestration/runtime, not graph-RAG. Out of scope for this cluster's theme.

### 8. microsoft/graphrag
- URL: https://github.com/microsoft/graphrag
- License: MIT
- Stars: 32,785
- Last commit: 2026-04-30
- Primary language: Python
- Purpose: Modular graph-based RAG system (Microsoft Research reference impl).
- Verdict: MONITOR
- Rationale: Heavy framework with strong batch-pipeline assumptions; full adoption overlaps Engram. Worth watching for indexing-pipeline ideas (community summarization, hierarchical clustering) but Phase 2 should target a focused extract, not framework integration.

### 9. safishamsi/graphify
- URL: https://github.com/safishamsi/graphify
- License: MIT
- Stars: 43,430
- Last commit: 2026-05-05
- Primary language: Python
- Purpose: AI-coding-assistant skill turning folders (code/SQL/docs/media) into a queryable knowledge graph.
- Verdict: MONITOR
- Rationale: Star count is anomalously high for the description — flag for verification before deeper engagement (possible star-inflation). Functionality overlaps Engram + CodeGraphContext. If genuine, a Phase-2 sandbox sample of its multi-modal-to-graph conversion patterns may be useful.

### 10. topoteretes/cognee
- URL: https://github.com/topoteretes/cognee
- License: Apache-2.0
- Stars: 17,050
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: "Memory control plane" for AI agents — pipelines from raw data to graph+vector memory.
- Verdict: MONITOR
- Rationale: Project already has a `cognee-integration` skill, so direct overlap with current Engram strategy is acknowledged. Apache-2.0 allows code+pattern adoption. Keep monitoring; deeper integration owned by the existing skill, not this scout.

### 11. vitali87/code-graph-rag
- URL: https://github.com/vitali87/code-graph-rag
- License: UNRESOLVED
- Stars: UNRESOLVED
- Last commit: UNRESOLVED
- Primary language: UNRESOLVED
- Purpose: UNRESOLVED
- Verdict: UNRESOLVED
- Rationale: 404 on `repos/vitali87/code-graph-rag`. User account `vitali87` itself returns no matches via `gh api users/vitali87/repos` and search `user:vitali87` is rejected. Repo is dead/renamed/deleted. No case-insensitive variant locatable. Do not pursue without a user-supplied alternate URL. Note: third-party `code-graph-rag` candidates exist (e.g., `er77/code-graph-rag-mcp`, `abhigyanpatwari/GitNexus`) but none are confirmed forks of the original; out of scope for this scout.

### 12. yifanfeng97/Hyper-Extract
- URL: https://github.com/yifanfeng97/Hyper-Extract
- License: Apache-2.0 (NOASSERTION on API; verified via LICENSE file)
- Stars: 833
- Last commit: 2026-04-30
- Primary language: Python
- Purpose: Unstructured text → graphs / hypergraphs / spatio-temporal extractions via LLMs, single-command.
- Verdict: EXTRACT (algorithm-only)
- Rationale: Hypergraph + spatio-temporal extraction is a primitive we don't have. Apache-2.0 confirmed. Phase-2 candidate to evaluate the extractor pipeline as a complement to LightRAG/HippoRAG retrieval; do not adopt the whole tool, lift the extractor's prompt/schema design.

## Phase 2 candidates

Priority order — algorithms over frameworks, smallest extractable delta first:

1. **HKUDS/LightRAG** — extract dual-level (entity + topic) retrieval algorithm into Engram retrieval layer.
2. **OSU-NLP-Group/HippoRAG** — port Personalized PageRank multi-hop recall over Engram entity graph.
3. **getzep/graphiti** — adopt bi-temporal edge schema (event-time vs ingest-time) into Engram graph model.
4. **yifanfeng97/Hyper-Extract** — evaluate hypergraph + spatio-temporal extractor pipeline (extractor schema only).

Deferred to Phase 2 reading-only: **DEEP-PolyU/Awesome-GraphMemory** as taxonomy/benchmark seed.

Out of scope this round: graphify (verify star anomaly first), microsoft/graphrag (extract narrowly only if a specific community-summarization need surfaces), cognee (owned by existing `cognee-integration` skill), engraph + CodeGraphContext (Engram-overlap, monitor), overstory (mis-clustered), vitali87/code-graph-rag (UNRESOLVED, drop unless user supplies alternate).
