# Cross-check Part A: Memory & RAG (2026-05-08)

Phase: reconstruction. Read-only audit. Sources: `lib/skill_router.py`, `lib/skill_routing.py`, `lib/cognee_client.py`, `lib/engram_client.py`, `lib/engram_http_client.py`, `lib/engram_graph_walker.py`, `lib/engram_lifecycle.py`, `lib/memory.py`; deep dives under `docs/03-PoCs/research/repo-scout/deep/`; MIRIX follow-up.

---

## 🔍1 DSPy (stanfordnlp/dspy, MIT)

**Verdict:** EXTERNAL_BETTER (in its domain) — **NOT_COMPARABLE** in the strict sense: our skill router solves a different problem.

**Local logic:**
- `lib/skill_router.py` (1816 lines): `SkillRouter` class with method `match(user_message) -> List[SkillMatch]` and `best_match()`. Internally: regex compiled per skill (`_compile`), `routing_patterns` loaded from each `SKILL.md` (`_parse_routing_patterns_block`), negative heuristics (`_is_router_negative_context`, `_is_auto_rollback_meta_reference`), profile filter (`_load_profile_projected_skills`), checksum-cached index (`SkillRoutingIndexCache`). It is 100% **message → score → skill** lightweight NLU, with no I/O typing, prompt optimization, or compilation.
- `lib/skill_routing.py` (336 lines): tabla auxiliar of patrones.

**DSPy offers** (deep dive `stanfordnlp__dspy-2026-05-06.md`):
- `dspy/signatures/` — contracts tipados of I/O for LLM (`InputField`/`OutputField` with tipos).
- `dspy/predict/` + `dspy/primitives/` — Composable modules (ChainOfThought, ReAct, ProgramOfThought, Avatar agentic).
- `dspy/teleprompt/` — Optimizers (BootstrapFewShot, MIPROv2, GEPA) that **compile** a program against a dataset+metric.
- `dspy/adapters/`, `dspy/clients/`, `dspy/retrievers/`.

**Delta:**
1. Our router decides *which skill* to invoke; DSPy defines *what the skill does* internally and *how the prompt is optimized*. Zero functional overlap.
2. We have nothing equivalent to Signatures: skills use YAML frontmatter + free-form Markdown. There is no typed I/O validation.
3. We have no prompt optimizer. We have `lib/skill_efficacy.py` (KPIs) and `lib/skill_failure_repair.py`, but they are post-hoc and do not compile the prompt against a dataset.

**Recommendation:** **adopt-code (as dependency)** for the internal "prompt-as-program" use case (e.g. skills with hard verification such as `sdd-verify`, `confidence-check`). Keep our router intact: it solves a problem DSPy does not solve.

**Technical reason:** saying that the skill router "implements Signatures/Modules/Optimizers" is categorically false — the router is a regex classifier over user input messages; DSPy is an LLM program compiler. They are orthogonal layers. The temptation to hybridize (rewriting the router *in* DSPy) would be over-engineering: 1.8k lines of regex+negation heuristics work O(skills) per message without calling an LLM, while DSPy requires an LLM call per inference. The clearly valuable path is to use DSPy for skills that already perform structured reasoning (verify, propose, design): replace Markdown templates with `dspy.Signature` + `dspy.ChainOfThought` and compile with MIPROv2/GEPA against the corpus of session transcripts. That attacks the real gap (`agent-quality`, `prompt-quality` in RULES §2/§8) without touching the routing layer.

**Effort if adopted:** 3-7 days for the first pilot skill (probably `sdd-verify` or `confidence-check` — both have clear I/O structure). +1-2 days for wiring of GEPA with `dspy/teleprompt/gepa/` (deep target #15).

---

## 🔍2 LightRAG + HippoRAG + graphiti

### LightRAG (HKUDS, MIT) — **EXTERNAL_BETTER** in retrieval; our storage layer is parallel

**Local logic:**
- `lib/engram_http_client.py` + `lib/engram_client.py` (198 L) — wrapper FTS5 sobre engram daemon. `search_observations(query, type_filter, project)` es full-text search plano via HTTP `/search?q=...&type=...`.
- `lib/engram_lifecycle.py` (580 L) — orquesta search → graph-walk → ranking, exposes `EngramLifecycle.search()`.
- `lib/cognee_client.py` (296 L) — HTTP client to Cognee (optional external service, gated por `COGNEE_ENABLED`); offers `search(search_type=INSIGHTS|CHUNKS|GRAPH_COMPLETION)` via `/api/v1/search`. **It is a proxy, not an in-house retriever**.

**LightRAG offers** (deep dive `HKUDS__LightRAG-2026-05-06.md`):
- Dual-level retrieval: **entity-level** (precise, KG-anchored) + **topic-level** (broad, embedding-based) — fusionados with score combinado. EMNLP 2025 paper.
- Multi-backend KG (Neo4j/Mongo/Postgres/Qdrant/Redis/ES); FastAPI server; WebUI.

**Delta:**
1. Engram FTS5 + graph walker does not perform retrieval *dual-level* — searches text, then walks relations. There is no fused scoring entity+topic.
2. Cognee partially covers the gap (offers `INSIGHTS`/`GRAPH_COMPLETION`) but is an optional external service; when `COGNEE_ENABLED=false` (default), there is no semantic retrieval.
3. We have no benchmarks (LightRAG ships `lightrag/evaluation/`).

**Recommendation:** **adopt-pattern** (algorithm, not framework). Port dual-level scoring to `lib/engram_lifecycle.py` as optional ranking over FTS5+graph. **Discard** the full framework (k8s+webui+6 storages duplicates Engram).

**Technical reason:** current retrieval is valid for internal use (decisions, ADRs, sessions with topic_keys conocidos), but degrades when the query is semantically fuzzy ("how does authentication work"). FTS5 + BFS over typed relations does not compensate for missing embedding-based topic recall. Cognee covers it, but as an external HTTP dependency with health-check (`is_cognee_available`); for reconstruction we want something in-process. The dual-level algorithm is ~200 LOC portables and does not require a new KG.

**Effort:** 3-5 days for port + benchmark A/B against the current Engram corpus.

### HippoRAG (OSU-NLP-Group, MIT) — **EXTERNAL_BETTER** in multi-hop

**Local logic:**
- `lib/engram_graph_walker.py` (315 L) — BFS bounded to `DEFAULT_MAX_DEPTH=2` over `memory_relations` (edges: supersedes/related/compatible/conflicts_with), boost `DEFAULT_GRAPH_BOOST=0.3`. **There is no PageRank**, there is no node-importance scoring, all hops have the same value.

**HippoRAG offers** (deep dive `OSU-NLP-Group__HippoRAG-2026-05-06.md`): Personalized PageRank over entity graph for multi-hop recall (NeurIPS 2024). 8 months without push but v1.0.0 estable.

**Delta:** flat BFS vs weighted PPR. For queries requiring 2+ hops and disambiguation, PPR is strictly superior: central nodes receive more weight, and the personalized vector anchors propagation to the query.

**Recommendation:** **adopt-pattern**. Port PPR scoring to `EngramGraphWalker` as an alternative mode to BFS (`walk_strategy="ppr"`). Reuse of `prompts/dspy_prompts/` as reference to align with DSPy adoption from item #1.

**Technical reason:** we already have the graph (`memory_relations` with typed relations and confidence). Moving from BFS to PPR means adding `networkx.pagerank(personalization=...)` over the loaded subgraph — ~150 LOC. The 8-month stagnation is acceptable: the algorithm is from a paper, not an active framework.

**Effort:** 2-4 days.

### graphiti (getzep, Apache-2.0) — **EXTERNAL_BETTER** in temporal model

**Local logic:**
- `memory_relations` (schema in `engram_graph_walker.py`): has `created_at`, `updated_at`, `superseded_at`, `superseded_by_relation_id`. That is **mono-temporal** (transaction time / ingest time). There is no separation entre "when the described event happened" vs "when the observation was ingested".
- Search in `lib/`: `event_time` aparece only in `lib/trace_joiner.py:94` (telemetry event timestamp, not observations). Zero support bi-temporal in Engram.

**graphiti offers** (deep dive `getzep__graphiti-2026-05-06.md`): edges with (`valid_from`, `valid_to`) **+** (`ingested_at`) — bi-temporal. Cross-encoder reranking. MCP server. Eval against LongMemEval.

**Delta:**
1. Engram cannot answer "what did the system believe about X *at time T*" vs "what do we know today about X *during period T*". `superseded_at` partially covers the first, not the second.
2. There is no neural reranker — the final ranking is linear FTS5 score + graph_boost.
3. No benchmark standard (LongMemEval).

**Recommendation:** **adopt-pattern** (schema bi-temporal). **Discard** the full framework (Apache-2.0 with NOTICE compliance, pre-1.0 churn, 4 KG drivers we do not need). Cross-encoder reranking is secondary optional.

**Technical reason:** the bi-temporal gap is real and has concrete impact in COS — ADRs and session summaries describe past events; without `valid_from/valid_to` we cannot query history correctly. It is a schema migration (`ALTER TABLE memory_relations ADD COLUMN valid_from/valid_to`) + update of writers, does not require vendoring.

**Effort:** 4-7 days (schema + migration + writers + a couple of LongMemEval-style test queries).

---

## 🔍12 MIRIX taxonomy

**Verdict:** **EXTERNAL_BETTER** (real but small gap).

**Local logic:**
- Engram treats `type` as a **free string**: `engram_client.save_observation(type_="manual")`, `engram_http_client.search_observations(type_filter="discovery")`. There is no enum, validation, or exported constant. Search in `lib/` and `mcp-server/`: zero `OBSERVATION_TYPES` / `VALID_TYPES`. The taxonomy exists only in docstrings and CLAUDE.md (`bugfix|decision|architecture|discovery|pattern|config|preference`) — convention, no contract.
- That means nothing prevents storing `type="anything"` and nothing conceptually distinguishes a procedural observation ("to do X, execute Y") from a semantic one ("X is Y") or an episodic one ("at 10:00 X happened").

**MIRIX offers** (follow-up `Mirix-AI__MIRIX-2026-05-06.md`, Apache-2.0, 3.5k stars, push 2026-04-28):
- Formal memory split: **semantic** (facts), **episodic** (timestamped events), **procedural** (how-to), **working** (transient/active context). Multi-agent routing sends each capture to the correct store.

**Delta:**
1. Our types are developer-action-oriented (`bugfix`, `decision`) and mix dimensions — a `bugfix` is episodic+procedural at once.
2. There is no distinction between **working** memory (session context, should expire) and persistent memory. `lib/memory_decay.py` exists but is not coupled to the working/episodic dimension.
3. There is no concept of "procedural" as first-class — runbooks live in `docs/05-Methodology/runbooks/`, separate from Engram.

**Recommendation:** **adopt-pattern** (taxonomy overlay), **do not adopt-code** (MIRIX is a personal-AI framework with screen capture, out of scope).

**Technical reason:** the gap is real but the cost is low. Adding a `memory_class IN (semantic, episodic, procedural, working)` field orthogonal to the current `type` enables: (a) coupling `memory_decay` to `memory_class=working` (aggressive decay), (b) retrieval routing ("how do I do X" queries → procedural; "what did we decide about Y" → semantic; "when did Z happen" → episodic), (c) alignment with literature (LongMemEval uses the same taxonomy). It is not strictly required for reconstruction, but the marginal cost is low if we are already touching schema for bi-temporal support (item #2/graphiti).

**Effort:** 1-2 days if done together with the migration bi-temporal; 2-3 days standalone.

---

## Resumen ejecutivo

**Adoptar (alta prioridad):**
1. **graphiti bi-temporal schema** (`valid_from/valid_to` in `memory_relations`) — 4-7d. Covers a real gap in historical queries.
2. **LightRAG dual-level retrieval** ported to `engram_lifecycle.search()` — 3-5d. Covers the semantic gap that today depends on Cognee optional.
3. **MIRIX memory_class overlay** (semantic/episodic/procedural/working) — 1-2d marginal si se hace with #1. Low cost, high return in routing and decay.

**Adoptar (media prioridad):**
4. **HippoRAG PPR** as an alternative mode in `EngramGraphWalker` — 2-4d. Improves multi-hop over current BFS.
5. **DSPy as a dependency** for skills with I/O structured (`sdd-verify`, `confidence-check`) — 3-7d pilot. Does not replace the router.

**Discard:**
- LightRAG full framework (k8s+webui+6 storages duplica Engram).
- graphiti full framework (Apache-2.0 + pre-1.0 churn + irrelevant drivers).
- HippoRAG framework (8 meses stale; only the algorithm).
- MIRIX code (framework of personal-AI with screen-capture, out of scope).
- **Rewrite the skill router in DSPy** — wrong category (message classifier ≠ program compiler LLM).

**What we already have and can defend:**
- Skill router (regex+frontmatter+negation heuristic) is O(skills) with no LLM call. Do not touch.
- `EngramGraphWalker` with typed relations (supersedes/related/compatible/conflicts_with) is a good substrate for PPR — requires no refactor, only extension.
- Cognee as opt-in HTTP is reasonable as fallback, but should not be the default path: port LightRAG first.
