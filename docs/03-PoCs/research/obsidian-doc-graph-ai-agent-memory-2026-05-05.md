# Obsidian, Documentation Graphs, and AI Agent Memory — Follow-up Research

**Date**: 2026-05-05  
**Scope**: Follow-up on the prior work about converting documentation into a graph / "brain" for AI coding agents, with Obsidian as a possible human-facing layer.  
**Local conclusion**: Cognitive OS already researched and implemented the load-bearing backend pieces in Engram Phases 1–3. Phase 4 is now implemented as a one-way, dry-run-first Engram → Obsidian export with optional Stop-hook automation gated by `COS_OBSIDIAN_VAULT`; Obsidian remains a derived graph/audit layer, not the source of truth.

---

## Acceptance criteria

1. Identify what was previously researched, documented, and implemented locally.
2. Continue external research across at least 40 distinct websites / repositories / posts.
3. Separate backend memory requirements from human-facing graph visualization.
4. Produce a concrete recommendation for the next implementation step.

---

## What was already done locally

### Documents found

| File | Role | Status |
|---|---|---|
| `docs/research/llm-wiki-v2-engram-evolution-2026-04-27.md` | Primary prior research. It compared Obsidian, Karpathy-style LLM Wiki, LLM Wiki v2, Mem0, Zep/Graphiti, Cognee, Letta, GraphRAG, HippoRAG, LightRAG, and related memory tools. | Current. |
| `docs/adrs/ADR-071-engram-lifecycle-evolution.md` | Accepted decision: extend Engram with lifecycle trailers, confidence/decay, crystallization, and graph traversal instead of making Obsidian primary memory. | Current; Phases 1–3 marked done. |
| `.cognitive-os/plans/features/engram-lifecycle-evolution.md` | Execution plan for ADR-071. | Phases 1–3 shipped; Phase 4 manual export shipped and opt-in automation added. |
| `docs/adrs/ADR-037-self-knowledge-base.md` | Earlier self-knowledge index for the repo: API surface, dependency graph, glossary, and summary. | Accepted; implemented by self-knowledge builder. |
| `docs/architecture/memory-lifecycle.md` | Operator map of which hooks/libraries/tests save and recover memory. | Current orientation doc. |
| `infra/cognee/README.md` | Optional Cognee service with NetworkX + LanceDB default backends. | Optional external memory/RAG surface, not primary. |

### Code found

| File | What it implements | Relevance |
|---|---|---|
| `lib/engram_lifecycle.py` | Lifecycle wrapper around Engram: structured `<engram-lifecycle>` trailer, confidence score, Ebbinghaus decay, reinforcement, and lifecycle-aware ranking. | Backend memory lifecycle. |
| `lib/engram_crystallizer.py` | Deterministic topic-key consolidation: repeated observations become `type=pattern` digests with `crystallized: true`. | Wiki-style compounding without manual curation. |
| `lib/engram_graph_walker.py` | Read-only BFS over Engram `memory_relations`, max depth 2, rejected edges skipped, graph results merged into search. | Graph traversal query strategy. |
| `hooks/engram-reinforce-on-access.sh` | Reinforces observations when memory is accessed. | Memory freshness / decay reset. |
| `hooks/engram-crystallize-on-session-end.sh` | Stop hook that triggers crystallization asynchronously. | Session-end knowledge consolidation. |
| `scripts/cos_build_self_knowledge.py` | Builds `.cognitive-os/self-knowledge/` artifacts: API surface, dep graph, glossary, summary. | Codebase self-knowledge, separate from Engram memory. |
| `lib/self_knowledge.py` | Query API for self-knowledge artifacts. | Lightweight repo orientation. |
| `lib/system_graph.py` | System graph support. | Adjacent graph primitive. |

### Tests found

| File | Coverage |
|---|---|
| `tests/unit/test_engram_lifecycle.py` | Trailer parsing, decay math, ranking, reinforcement behavior. |
| `tests/unit/test_engram_crystallizer.py` | Candidate detection, deterministic digest synthesis, idempotence. |
| `tests/unit/test_engram_graph_walker.py` | BFS, depth limit, rejected relations, deduplication, score merge. |
| `tests/e2e/test_engram_lifecycle_e2e.py` | Sandbox Engram daemon e2e path when the binary is available. |

---

## Prior local decision reconstructed

The earlier analysis did **not** conclude "make Obsidian the primary brain." It concluded:

1. Obsidian is a strong **human-readable export / visualization layer** because Markdown files, wikilinks, backlinks, and graph view are useful for operators.
2. Obsidian is weak as the **authoritative memory backend** because vanilla wikilinks are untyped, lack project scoping, lack confidence/decay, and have no native supersession or lifecycle semantics.
3. The backend needs typed relations, freshness, confidence, decay, crystallization, and bounded graph traversal.
4. Engram already had enough foundation to extend additively, so COS implemented lifecycle wrappers instead of migrating memory to Obsidian/Mem0/Zep/Cognee.
5. Phase 4's correct scope is export of Engram observations and relations into an Obsidian vault for human audit, with no import path back into Engram.

This is consistent with the ecosystem pattern found in the new search: the strongest tools combine **hybrid retrieval + graph traversal + temporal/lifecycle metadata + token-budgeted context assembly**. Obsidian alone is the UI/file substrate, not the memory logic.

---

## New web research synthesis — 40+ sources

### Pattern A — Karpathy / LLM Wiki: compile knowledge once, maintain it over time

The Karpathy-style LLM Wiki pattern treats raw sources, compiled wiki pages, and operating scripts/skills as separate layers. Newer implementations emphasize that an agent should maintain the wiki, not merely search raw chunks.

Representative sources:

1. Andrej Karpathy, `llm-wiki` gist — https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
2. LLM Wiki v2 / agentmemory lessons — https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2
3. Ar9av `obsidian-wiki` — https://github.com/Ar9av/obsidian-wiki
4. Pratiyush `llm-wiki` — https://github.com/Pratiyush/llm-wiki
5. `my-llm-wiki` package — https://pypi.org/project/my-llm-wiki/
6. jhinpan Karpathy-style Obsidian implementation gist — https://gist.github.com/jhinpan/16f240dfce4b45532f28b5df829bc887
7. Obsidian Forum `obsidian-graph-query` showcase — https://forum.obsidian.md/t/obsidian-graph-query-let-your-ai-agent-query-your-vaults-knowledge-graph-bfs-shortest-path-bridges-hubs-orphans/111828
8. Reddit discussion: hardest part building Karpathy’s LLM wiki — https://www.reddit.com/r/learnmachinelearning/comments/1sq5bxl/the_hardest_part_in_building_karpathys_llm_wiki/
9. Reddit discussion: spent a weekend building Karpathy's LLM Wiki — https://www.reddit.com/r/AI_Agents/comments/1sqg5ew/spent_a_weekend_actually_understanding_and/
10. Reddit discussion: Karpathy's LLM wiki as agent moat — https://www.reddit.com/r/AgentsOfAI/comments/1st6uxc/karpathys_llm_wiki_idea_might_be_the_real_moat/

### Pattern B — Obsidian-native MCP / vault graph tools are converging on graph-aware access

The newest Obsidian tools are explicitly moving beyond flat read/write file access. Common features: wikilink/backlink traversal, orphan/broken-link diagnostics, FTS/BM25, semantic search, section-level editing, token-budgeted bundles, file watchers, safe YAML/frontmatter mutation, and MCP/HTTP APIs.

Representative sources:

11. engraph — https://github.com/devwhodevs/engraph
12. Vault Master — https://mcpmarket.com/server/vault-master
13. MCPVault site — https://mcpvault.org/
14. MCPVault GitHub — https://github.com/bitbonsai/mcpvault
15. TurboVault GitHub — https://github.com/epistates/turbovault
16. TurboVault product page — https://epistates.com/products/turbovault/
17. Obsidian Graph MCP — https://github.com/drewburchfield/obsidian-graph
18. Smart Connections MCP — https://github.com/msdanyg/smart-connections-mcp
19. ObsidianRAG — https://github.com/Vasallo94/ObsidianRAG
20. Obsidian MCP Plugin — https://github.com/aaronsb/obsidian-mcp-plugin
21. Obsidian MCP server directory entry — https://mcpservers.org/servers/Vasallo94/obsidian-mcp-server
22. Obsidian Knowledge Management MCP server listing — https://glama.ai/mcp/servers/%40TheOutcastVirus/obsidian-knowledge-mcp
23. Obsidian Elite RAG MCP listing — https://mcpservers.org/servers/aegntic/aegntic-MCP
24. Obsidian Elite RAG MCP gallery — https://www.mcp-gallery.jp/mcp/github/aegntic/aegntic-mcp
25. Wandering RAG MCP listing — https://mcpserver.so/servers/AI%2FData-%26-Knowledge/wandermyz-wandering-rag-wandering-rag
26. OpenClaw Obsidian integration guide — https://openclawlaunch.com/guides/openclaw-obsidian
27. Obsidian Webhooks AI agents guide — https://obsidian-webhooks.khabaroff.studio/guides/ai-agents-obsidian
28. DocVault guide — https://www.lbruton.cc/guides/docvault/
29. OneBrain — https://onebrain.run/
30. Nia Vault docs — https://docs.trynia.ai/vault

### Pattern C — General agent memory has moved toward temporal / graph / hybrid retrieval

The broader memory ecosystem validates ADR-071: reliable agent memory needs time, confidence, contradiction/supersession handling, and graph traversal; not just embeddings.

Representative sources:

31. Zep / Graphiti GitHub — https://github.com/getzep/graphiti
32. Zep temporal knowledge graph paper — https://arxiv.org/abs/2501.13956
33. Zep PDF — https://blog.getzep.com/content/files/2025/01/ZEP__USING_KNOWLEDGE_GRAPHS_TO_POWER_LLM_AGENT_MEMORY_2025011700.pdf
34. Mem0 paper — https://arxiv.org/abs/2504.19413
35. Mem0 docs/site — https://mem0.ai
36. Cognee GitHub — https://github.com/topoteretes/cognee
37. Cognee docs/site — https://www.cognee.ai
38. Letta GitHub — https://github.com/letta-ai/letta
39. Letta vs Mem0 vs Zep vs Cognee forum analysis — https://forum.letta.com/t/agent-memory-solutions-letta-vs-mem0-vs-zep-vs-cognee/85
40. Zylos AI agent memory architectures survey — https://zylos.ai/en/research/2026-04-05-ai-agent-memory-architectures-persistent-knowledge
41. Graph-based Agent Memory taxonomy paper — https://arxiv.org/abs/2602.05665
42. Awesome GraphMemory — https://github.com/DEEP-PolyU/Awesome-GraphMemory
43. Microsoft GraphRAG — https://github.com/microsoft/graphrag
44. HippoRAG — https://github.com/OSU-NLP-Group/HippoRAG
45. LightRAG — https://github.com/HKUDS/LightRAG
46. AriGraph paper — https://arxiv.org/abs/2407.04363
47. GDS Agent paper — https://arxiv.org/abs/2508.20637
48. Contextix — https://contextix.io/
49. Engram overview — https://agents-squads.com/engram/
50. Graphiti custom entity type discussion — https://www.reddit.com/r/LLMDevs/comments/1j0ca03

### Pattern D — Community posts show demand, but also highlight operational risks

Reddit and forum posts are useful trend signals, not enough as implementation authority. They consistently show that builders want agents to write project knowledge graphs into Obsidian/Logseq, but the approaches are young and often have unclear maintenance, security, and license posture.

Representative sources:

51. Graphthulhu / graph-aware vault MCP discussion — https://www.reddit.com/r/ObsidianMD/comments/1roj8bz/mcp_server_that_treats_your_vault_as_a_graph_not/
52. Persistent memory via Obsidian/Logseq MCP — https://www.reddit.com/r/vibecoding/comments/1qyh3w9/i_gave_my_ai_a_persistent_memory_that_survives/
53. Knowledge graph instead of vector memory — https://www.reddit.com/r/openclaw/comments/1rkyky2/i_gave_my_ai_agent_a_knowledge_graph_instead_of/
54. Recon: Claude Code plugin writes project graph to Obsidian — https://www.reddit.com/r/ClaudeCode/comments/1s8yahb/i_built_a_claude_code_mcp_plugin_that_writes_your/
55. Claude Code + Obsidian graph/spaced repetition post — https://www.reddit.com/r/ClaudeAI/comments/1sbtb34/i_gave_claude_code_a_knowledge_graph_spaced/
56. Graph RAG for Obsidian CLI / RAG subreddit — https://www.reddit.com/r/Rag/comments/1srs4zb/i_built_a_local_graph_rag_for_obsidian_cli/
57. Graph RAG for Obsidian CLI / Ollama subreddit — https://www.reddit.com/r/ollama/comments/1srs93u/i_built_a_local_graph_rag_for_obsidian_cli/
58. Obsidian MCP practical use discussion — https://www.reddit.com/r/ObsidianMD/comments/1okyoph/is_anyone_functionally_use_an_mcp_with_obsidian/
59. VaultForge MCP token-use post — https://www.reddit.com/r/ClaudeAI/comments/1rwihrh/vaultforge_mcp_server_for_obsidian_that_cuts/
60. TurboVault v1.2.7 post — https://www.reddit.com/r/ObsidianMD/comments/1rn9ch5/turbovault_v127_obsidian_mcp_server/

---

## Fit analysis for Cognitive OS

### What to keep from the prior decision

Keep Engram as the authoritative memory backend. The implemented Phases 1–3 map directly to the ecosystem's strongest direction:

- **Confidence / decay**: aligns with memory lifecycle and temporal reliability.
- **Crystallization**: aligns with LLM Wiki knowledge compounding.
- **Graph traversal**: aligns with graph-aware retrieval.
- **Project scoping**: avoids cross-project contamination that plain vaults struggle with.
- **Structured trailers**: preserve compatibility with Engram while keeping lifecycle metadata machine-readable.

### What to add next

Implement Phase 4 as a **read-only Obsidian export**, not a bidirectional Obsidian backend.

Recommended shape:

1. `lib/engram_obsidian_exporter.py`
   - Reads Engram observations through typed clients.
   - Parses lifecycle trailers.
   - Emits Markdown files into a configured vault folder.
   - Converts `topic_key` into stable filenames.
   - Converts typed Engram relations into explicit frontmatter plus wikilinks.
   - Writes atomically and keeps a manifest for incremental exports.

2. `scripts/export-engram-to-obsidian.sh`
   - Manual operator command.
   - Requires explicit `--vault` path.
   - Defaults to dry-run unless `--write` is passed.

3. Optional later Stop hook
   - Disabled by default.
   - Runs incremental export only if a project config points to a vault.

4. Documentation
   - Add a manual test under `docs/manual-tests/engram-obsidian-export.md`.
   - Update ADR-071 with a Phase 4 addendum only after tests pass.

### Do not do yet

- Do not migrate Engram data into Obsidian as source of truth.
- Do not add a new graph database just for visualization.
- Do not adopt a community Obsidian MCP server as a core dependency without license/security audit.
- Do not make export automatic by default; vault paths are personal/local and should be explicit.

---

## Candidate export schema

Example Markdown output:

```markdown
---
cos_observation_id: obs-123
topic_key: architecture/memory-lifecycle
type: decision
project: luum-agent-os
confidence: 0.82
reinforcement_count: 6
last_reinforced: 2026-05-05T12:00:00Z
decay_class: decision
relations:
  related:
    - obs-456
  supersedes:
    - obs-111
---

# Chose Engram lifecycle over Obsidian primary memory

## What
...

## Links
- related: [[obs-456-some-topic]]
- supersedes: [[obs-111-old-topic]]
```

This gives Obsidian graph view enough edges to be useful while keeping typed semantics in frontmatter for agents/scripts.

---

## Implementation status — 2026-05-05

The recommended manual slice is implemented in `lib/engram_obsidian_exporter.py` and `scripts/export-engram-to-obsidian.sh`. It remains dry-run by default, requires explicit `--vault`, exports lifecycle metadata as frontmatter, derives wikilinks from accepted typed Engram relations, and never writes from Obsidian back to Engram.

The first real vault proof wrote to:

```text
$HOME/.cognitive-os/obsidian-vaults/luum-agent-os
```

That location is intentionally outside the repository. It is an operator-local
workspace for browsing generated notes in Obsidian, not a versioned project
artifact. Manual proof path: `docs/manual-tests/engram-obsidian-export.md`.

Optional automation is now implemented in `hooks/engram-obsidian-export-on-stop.sh`.
The hook exits 0 without exporting unless `COS_OBSIDIAN_VAULT` is set. With that
variable set, it runs the same one-way export with `--write`, records metrics in
`.cognitive-os/metrics/obsidian-export.jsonl`, and still exits 0 on failures so
session shutdown is not blocked.

## Repo docs versus Obsidian vault

The repo and the vault have different jobs. Treating them as the same artifact
would create duplicate sources of truth.

| Layer | Role | Versioning policy |
|---|---|---|
| `docs/` | Canonical, curated human documentation: ADRs, setup guides, runbooks, manual tests, architecture notes. | Versioned in git and reviewed like source. |
| Engram | Operational memory: session summaries, decisions, discoveries, bugfixes, lifecycle metadata, typed relations. | Persisted in Engram; exported when useful. |
| Local Obsidian vault | Derived graph/audit UI over Engram and selected repo docs. | Operator-local by default; may live in the user's chosen sync system. |
| Generated repo export, if added later | Sanitized, curated subset for durable knowledge indexes. | Only under an explicit generated folder with clear ownership and review. |

`docs/` should not be copied wholesale into Engram, and Engram exports should not
be promoted into `docs/` automatically. Instead:

- formal decisions live in `docs/adrs/`;
- setup and operational instructions live in `docs/setup/` and `docs/runbooks/`;
- manual proof evidence lives in `docs/manual-tests/`;
- raw or semi-structured memory lives in Engram;
- Obsidian links those surfaces for navigation.

This means the Obsidian graph may contain wikilinks to docs, but it should not
duplicate the content of each ADR or setup guide. A generated Engram note can
link to `[[ADR-071-engram-lifecycle-evolution]]` or
`[[engram-obsidian-export]]`; the ADR itself remains the authoritative prose.

## Automation policy

Automation is safe when the output target and source-of-truth boundary are
explicit.

| Automation | Status | Default | Rationale |
|---|---|---|---|
| Engram → local Obsidian vault | Implemented via `hooks/engram-obsidian-export-on-stop.sh`. | Off unless `COS_OBSIDIAN_VAULT` is set. | Useful for personal graph browsing; no git noise. |
| Repo docs → Obsidian index | Proposed follow-up. | Off. | Should create links/indexes, not duplicate all docs content. |
| Engram → repo-local generated export | Possible follow-up. | Off and manual promotion only. | Needs sanitization and lifecycle filtering before git. |
| Obsidian → Engram or Obsidian → `docs/` | Rejected for now. | Off. | Would make Obsidian an uncontrolled write path and create source-of-truth conflicts. |
| Stop hook that commits exports | Rejected for now. | Off. | Creates noisy commits and risks publishing local/private memory. |

If a repo-local export is added later, it should use a path such as
`docs/knowledge/engram/` with `generated: true` frontmatter, no `.obsidian/`
state, no local absolute paths, no credentials, and an explicit promotion command
rather than automatic commits.

## Recommendation

Keep Phase 4 as a small, testable exporter. Treat it as an audit and navigation layer for humans and as optional context material for agents, not as the canonical memory store.

The minimum valuable slice is one-way export from Engram to Obsidian with:

- dry-run summary,
- project filter,
- lifecycle frontmatter,
- wikilinks from existing relations,
- atomic writes,
- no default Stop-hook automation;
- optional Stop-hook export only when `COS_OBSIDIAN_VAULT` is set.

---

## Key Learnings

1. The prior COS work already implemented the backend memory features the Obsidian/LLM Wiki ecosystem identifies as load-bearing: confidence/decay, crystallization, and graph traversal.
2. Obsidian is best positioned as a human-facing graph export layer, not as the authoritative memory backend for Cognitive OS.
3. The current ecosystem is converging on hybrid retrieval: BM25/FTS, vectors, graph traversal, temporal scoring, reranking, and token-budgeted context bundles.
4. A Phase 4 Obsidian exporter should be one-way, explicit, dry-run-first, and project-scoped to avoid vault corruption and cross-project memory leakage.
5. The local Obsidian vault should stay outside the repository by default; `docs/` remains the curated source for durable documentation while Obsidian serves as a generated graph view.
6. Automation is acceptable only as opt-in export, not as automatic commit or as an Obsidian-to-docs write path.
