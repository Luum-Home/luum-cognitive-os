# LLM Wiki v2 — Engram Evolution Analysis

**Date**: 2026-04-27
**Author**: Architecture review (Software Architect agent)
**ADR**: [`docs/02-Decisions/adrs/ADR-071-engram-lifecycle-evolution.md`](../adrs/ADR-071-engram-lifecycle-evolution.md)
**Plan**: [`.cognitive-os/plans/features/engram-lifecycle-evolution.md`](../../.cognitive-os/plans/features/engram-lifecycle-evolution.md)

---

## TL;DR

Obsidian's graph view is a thin visualization on untyped markdown links — not the structured memory backend the system needs. The LLM Wiki v2 gist [1] reframes the problem: the bottleneck is memory lifecycle (confidence scoring with Ebbinghaus decay, automated crystallization, typed-edge graph traversal), not visualization. Engram already provides 80% of the required foundation; three targeted additions close the gap without migrating away from it.

---

## The original question

After 38+ web sources on AI agent memory systems, the question was whether to adopt Obsidian as a graph-based memory layer alongside engram. The surface appeal: Obsidian has a graph view, wikilinks, community plugins (Smart Connections, basic-memory MCP), and a local-first Markdown store that survives model changes. The concern was that engram lacked something "visual" or "graph-shaped" that could help agents navigate their own accumulated knowledge.

---

## The reframing from LLM Wiki v2

The gist [1], written by the author of agentmemory [13] and building explicitly on Karpathy's original LLM Wiki [2], lands on a direct diagnosis: **the original wiki pattern treats all content as equally valid forever**. That is the actual failure mode — not the absence of a graph view. A wiki that never forgets becomes noisy. A wiki that cannot distinguish a pattern confirmed twelve times from one seen once cannot help the agent calibrate confidence. A wiki that does not decay stale observations surfaces six-month-old bugs with the same weight as yesterday's architecture decision.

The gist names four structural solutions: (a) confidence scoring with source count, recency, and contradiction tracking; (b) supersession — old claims explicitly superseded by newer ones, linked and timestamped; (c) forgetting via Ebbinghaus retention curves, where each reinforcement (access, new source confirmation) resets decay; (d) consolidation tiers — working memory → episodic → semantic → procedural, each more compressed, more confident, and longer-lived than the one below.

On graph structure, the gist is precise: "The graph doesn't replace the wiki pages. It augments them. Pages are for reading. The graph is for navigation and discovery." Typed relationships ("uses", "depends on", "contradicts", "caused", "fixed", "supersedes") carry semantic weight that flat wikilinks do not. Graph traversal as a query strategy — walk outward from a node through typed edges — catches connections that keyword search misses. But this graph structure belongs in the **backend**, not in a Markdown visualization tool.

The crystallization concept extends the original idea of "filing good answers back as pages": a completed research thread or debugging session should be automatically distilled into a structured digest, extracted as standalone facts, and promoted into the knowledge base. This is not a manual curation step — it is an automated pipeline that treats agent explorations as first-class knowledge sources.

---

## Capability matrix

| Capability (LLM Wiki v2) | Engram + COS current state | Gap |
|---|---|---|
| Confidence scoring (source count, recency, contradiction) | None — all observations equally weighted at retrieval | **HIGH** — no decay, no confidence field in schema |
| Supersession (linked, timestamped, old marked stale) | `mem_judge` with `supersedes` relation exists; not auto-triggered | PARTIAL — edge exists, no automatic supersession on write |
| Ebbinghaus decay (forgetting curve, retention reset on access) | None | **HIGH** — engram binary does not expose decay hooks |
| Consolidation tiers (working/episodic/semantic/procedural) | `type_` field (bugfix, decision, pattern, etc.) partially maps tiers; `mem_session_summary` is manual episodic compression | PARTIAL — type taxonomy exists, no automated promotion pipeline |
| Entity extraction (people, projects, libraries, decisions) | `project` + `topic_key` + `type_` cover entities partially | PARTIAL — no automatic entity extraction on ingest |
| Typed relationships (uses, depends\_on, contradicts, caused, supersedes) | `mem_judge` relations: supersedes, conflicts\_with, related, compatible, scoped, not\_conflict | PARTIAL — relations exist, not used in query routing |
| Graph traversal for queries | `mem_search` is BM25+vector only | **HIGH** — no edge-walk query strategy |
| Hybrid search (BM25 + vector + graph) | BM25+vector via engram; no graph stream | PARTIAL — graph stream missing |
| Automated hooks (ingest, session start/end, query, schedule) | 158 hooks; session start/end, PostToolUse patterns exist | GOOD — infrastructure is present |
| Crystallization (auto-distill completed threads → digest → facts) | `document-feature` skill + `mem_session_summary`; both manual | PARTIAL — no auto-promotion pipeline |
| Quality scoring + self-healing | trust-score, auto-verify, dod-gate quality chain | GOOD — quality infrastructure is strong |
| Multi-agent / mesh sync | agent-bus, squads | GOOD — coordination layer exists |
| Privacy / governance | secret-detector, confidentiality-enforcer, audit-id-enricher | GOOD — coverage is strong |
| Output formats (table, graph, slide deck) | Markdown-only | OUT OF SCOPE for this ADR |

---

## The 3 gaps in priority order

### Gap 1: Confidence scoring + Ebbinghaus decay (Priority: Critical)

**What it is**: Every observation in engram should carry a confidence score (how many sources confirm it, how recently it was confirmed) and a decay function that reduces retrieval weight over time. Each access (reinforcement) resets the decay curve for that observation.

**Payoff**: Search ranking matches actual epistemic state. A 14-month-old ADR about a deprecated dependency stops surfacing above a 2-week-old bugfix about the same module. The agent can say "I'm fairly confident about X (reinforced 8 times)" vs "I saw this once, six months ago."

**Cost**: Engram's schema has no native confidence/decay fields. Solution: encode lifecycle metadata as a structured trailer in the `content` body — a fenced `<engram-lifecycle>{...}</engram-lifecycle>` block that engram passes through unchanged. Python wrapper `lib/engram_lifecycle.py` parses the trailer, applies decay, and re-ranks results. Overhead: ~10ms per search call.

**Reversibility**: High. The trailer is inert to engram; removing the wrapper layer reverts to current behavior with no data loss.

### Gap 2: Crystallization pipeline — automated promotion (Priority: High)

**What it is**: When N observations share the same `topic_key`, automatically synthesize them into a digest observation of `type=pattern` with elevated confidence. This is the episodic → semantic promotion step. Currently `mem_session_summary` does this manually for sessions; crystallization extends it to any topic cluster.

**Payoff**: Prevents entropy — repeated observations on the same topic accumulate without ever being consolidated into a single authoritative entry. A crystallized pattern carries higher confidence and surfaces before its constituent observations in search.

**Cost**: Requires a trigger (count-based or time-based), an LLM call to synthesize the digest, and a `mem_save` of the result. The trigger can be a hook (`hooks/engram-crystallize.sh`) on session end, or a scheduled job. Medium implementation complexity.

**Reversibility**: Medium. Crystallized entries can be identified by `type=pattern` + `topic_key` + trailer `crystallized: true`; rollback means deleting them and reverting constituent observation confidence scores.

### Gap 3: Graph traversal as query strategy (Priority: Medium)

**What it is**: When querying for an observation, walk `mem_judge` edges (supersedes, conflicts\_with, related, compatible) outward from initial search hits to surface connected knowledge. This is the "start at Redis node, walk depends\_on edges" capability the gist describes.

**Payoff**: Catches structural connections that BM25+vector misses. Currently `mem_judge` creates edges but nothing queries them. An observation about "auth service performance" might be connected via `related` to three other observations about JWT token size, Redis session TTL, and a specific APM incident — none of which share enough text to surface in vector search.

**Cost**: Requires reading the `mem_judge` edge index (engram exposes this via MCP), fetching connected observation IDs, and merging them into the ranked result set. The traversal depth must be bounded (default: 2 hops) to prevent combinatorial explosion on a dense graph.

**Reversibility**: High. Graph traversal is additive to existing search; disabling it reverts to current BM25+vector behavior.

---

## Why NOT Obsidian as primary

Obsidian's graph view visualizes untyped wikilinks between Markdown files. After analyzing the LLM Wiki v2 gist [1] and the broader ecosystem [3–14]:

1. **Markdown breaks at scale**: The gist explicitly notes that `index.md` (Obsidian's analog) stops working past 100–200 pages. With 158+ hooks generating observations, engram already exceeds that threshold.
2. **No project-scoping**: Obsidian vaults are flat or manually organized. Engram's `project` field is a first-class filter that keeps observations from different projects from cross-contaminating retrieval.
3. **Untyped edges**: Obsidian wikilinks have no semantic type. The LLM Wiki v2 gist is explicit that typed relationships ("uses", "supersedes", "conflicts\_with") are what make graph traversal useful. Without types, graph walking produces noise.
4. **No confidence/decay**: Obsidian has no mechanism to score or decay note confidence. Adding it would require a plugin that essentially reimplements what `lib/engram_lifecycle.py` will do — but on top of Markdown files instead of a structured backend.
5. **Visualization is not the bottleneck**: Karpathy's original gist [2] and the LLM Wiki v2 gist [1] both agree: the bottleneck is bookkeeping and lifecycle management. Obsidian solves neither; it solves human readability of a knowledge graph, which is a downstream concern.
6. **Integration cost**: Obsidian's API is not designed for programmatic write-heavy workloads. Community plugins (Smart Connections [9], basic-memory MCP [10]) add partial capability but create a fragile dependency chain outside the project's control.

The conclusion: Obsidian is appropriate as a **human-readable export layer** (Phase 4, deferred) — reading the knowledge base in a graph view after the structured backend has done its work. It is not appropriate as the primary memory backend.

---

## Why NOT migrate to Mem0/Zep/Cognee

The `rules/RULES-COMPACT.md` reinvention-prevention rule and the 38-source research both point in the same direction:

- **Mem0** [3]: Adds confidence scoring and graph-based memory, but requires migrating all existing engram observations, rewriting `lib/engram_client.py` and all 145+ skills that call engram tools. Integration cost is 4–8 weeks. Marginal benefit over extending engram: low, because engram already provides BM25+vector search, typed relations via `mem_judge`, and project scoping.
- **Zep/Graphiti** [4]: Strong graph-based episodic memory with temporal awareness. Same migration cost concern. Also introduces a network dependency on an external service in a system that currently runs fully locally via MCP.
- **Cognee** [5]: Knowledge graph construction with LLM-generated entity extraction. Complementary to engram rather than a replacement, but integration doubles the memory surface area the system must reason about.
- **Letta/MemGPT** [6]: Targets multi-agent persistent memory. The project's agent-bus and squads already cover this use case.

All four alternatives solve subsets of the problem that engram + lifecycle wrapper also solve, at higher integration cost and with worse reversibility. The wrapper approach (`lib/engram_lifecycle.py`) is additive, reversible, and keeps engram as the single source of truth.

---

## Phased path forward

**Phase 1 — Confidence + decay (this sprint)**
Implement `lib/engram_lifecycle.py` with trailer encoding, decay classes (architecture/decision/pattern/discovery/bugfix/manual with tau values 365/180/180/90/60/90 days), ranking formula, and reinforcement on access. Add `hooks/engram-reinforce-on-access.sh` to increment reinforcement count on `mem_search` and `mem_get_observation` events. Unit tests cover trailer round-trip, decay math, reinforcement, ranking bounds, missing-trailer fallback.

**Phase 2 — Crystallization pipeline**
Implement automated observation promotion: when N≥5 observations share a `topic_key`, trigger digest synthesis via LLM and save as `type=pattern` with elevated confidence. Hook fires on session end. The `document-feature` skill feeds into this pipeline.

**Phase 3 — Graph traversal in queries**
Extend `lib/engram_lifecycle.py` search to walk `mem_judge` edges (2-hop max) and merge graph hits into ranked results with a graph contribution weight (default alpha\_graph = 0.2). Bounded traversal prevents combinatorial explosion.

**Phase 4 (deferred) — Obsidian export**
Once Phases 1–3 are stable, implement an export hook that renders engram observations as Obsidian Markdown with wikilinks derived from `mem_judge` edges. Human-readable audit layer only; no writes flow back from Obsidian to engram.

---

## Sources

1. LLM Wiki v2 gist (rohitg00, 2026) — **LOAD-BEARING**: primary reframing for this analysis — https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2
2. Andrej Karpathy, LLM Wiki original gist (2024) — **LOAD-BEARING**: foundation the v2 gist extends — https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
3. Mem0 — graph-enhanced agent memory with confidence scoring — https://mem0.ai
4. Zep / Graphiti — temporal knowledge graph for episodic agent memory — https://github.com/getzep/graphiti
5. Cognee — knowledge graph construction with LLM entity extraction — https://github.com/topoteretes/cognee
6. Letta / MemGPT — multi-agent persistent memory framework — https://github.com/letta-ai/letta
7. Microsoft GraphRAG — graph-based RAG with community detection — https://github.com/microsoft/graphrag
8. HippoRAG — hippocampal-inspired graph memory for LLMs — https://github.com/OSU-NLP-Group/HippoRAG
9. LightRAG — hybrid graph+vector retrieval — https://github.com/HKUDS/LightRAG
10. Obsidian Smart Connections plugin — vector similarity within Obsidian — https://github.com/brianpetro/obsidian-smart-connections
11. basic-memory MCP — Obsidian-backed MCP memory server — https://github.com/basicmachines-co/basic-memory
12. claude-mem — lightweight session memory for Claude — https://github.com/sethlford/claude-mem
13. agentmemory (rohitg00) — persistent memory engine that produced the v2 gist patterns — **LOAD-BEARING**: direct source of crystallization and lifecycle patterns — https://github.com/rohitg00/agentmemory
14. Ebbinghaus forgetting curve — foundational cognitive science model for retention decay — https://en.wikipedia.org/wiki/Forgetting_curve

---

## Post-implementation status (2026-04-27)

**Phases 1, 2, 3 implemented and verified** (89 tests: 75 unit + 14 e2e against a real sandboxed engram daemon). The original analysis held: lifecycle is the bottleneck, Obsidian remains optional Phase 4. Two pieces of the analysis were corrected during execution:

- The Phase 1 caveat ("engram CLI lacks `get`/`update` so `reinforce()` returns False") was **wrong**. Engram's HTTP API at port 7437 exposes both. Discovered on 2026-04-27 after a PATCH probe accidentally overwrote a real observation (#13283); now governed by `rules/engram-api-safety.md`.
- The engram `cloud` branch is BEHIND `main` (10 commits) — cloud sync is already merged. The lifecycle trailer survives sync because it lives in `content`, but cross-device reinforcement aggregation is **not** implemented (each device reinforces locally only).

For honest limitations of the shipped implementation (heuristic synthesis without LLM, `mem_judge` supersedes not written, threshold tuning unvalidated, hooks dormant until profile re-applied), see the **Honest Limitations** section in [ADR-071](../adrs/ADR-071-engram-lifecycle-evolution.md).
