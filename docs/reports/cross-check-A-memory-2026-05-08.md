# Cross-check Part A: Memory & RAG (2026-05-08)

Phase: reconstruction. Read-only audit. Sources: `lib/skill_router.py`, `lib/skill_routing.py`, `lib/cognee_client.py`, `lib/engram_client.py`, `lib/engram_http_client.py`, `lib/engram_graph_walker.py`, `lib/engram_lifecycle.py`, `lib/memory.py`; deep dives under `docs/research/repo-scout/deep/`; MIRIX follow-up.

---

## 🔍1 DSPy (stanfordnlp/dspy, MIT)

**Veredicto:** MEJOR_EXTERNO (en su dominio) — **NO_COMPARABLE** en sentido estricto: nuestro skill router resuelve un problema distinto.

**Nuestra lógica:**
- `lib/skill_router.py` (1816 líneas): clase `SkillRouter` con método `match(user_message) -> List[SkillMatch]` y `best_match()`. Internamente: regex compilado por skill (`_compile`), `routing_patterns` cargado desde frontmatter de cada `SKILL.md` (`_parse_routing_patterns_block`), heurísticas negativas (`_is_router_negative_context`, `_is_auto_rollback_meta_reference`), filtro por perfil (`_load_profile_projected_skills`), checksum-cached index (`SkillRoutingIndexCache`). Es 100% **mensaje → score → skill** estilo NLU light, sin tipado de I/O, sin optimización de prompts, sin compilación.
- `lib/skill_routing.py` (336 líneas): tabla auxiliar de patrones.

**DSPy ofrece** (deep dive `stanfordnlp__dspy-2026-05-06.md`):
- `dspy/signatures/` — contratos tipados de I/O para LLM (`InputField`/`OutputField` con tipos).
- `dspy/predict/` + `dspy/primitives/` — Modules componibles (ChainOfThought, ReAct, ProgramOfThought, Avatar agéntico).
- `dspy/teleprompt/` — Optimizers (BootstrapFewShot, MIPROv2, GEPA) que **compilan** un programa contra un dataset+métrica.
- `dspy/adapters/`, `dspy/clients/`, `dspy/retrievers/`.

**Delta:**
1. Nuestro router decide *qué skill* invocar; DSPy define *qué hace* la skill internamente y *cómo se optimiza el prompt*. Cero solapamiento funcional.
2. No tenemos nada equivalente a Signatures: los skills usan YAML frontmatter + markdown libre. No hay validación de I/O tipada.
3. No tenemos optimizer de prompts. Tenemos `lib/skill_efficacy.py` (KPIs) y `lib/skill_failure_repair.py`, pero son post-hoc, no compilan el prompt contra un dataset.

**Recomendación:** **adoptar-código (como dependencia)** para el caso de uso de "prompt-as-program" interno (e.g. skills con verificación dura como `sdd-verify`, `confidence-check`). Mantener nuestro router intacto: resuelve un problema que DSPy no resuelve.

**Razón técnica:** decir que el skill router "implementa Signatures/Modules/Optimizers" es categóricamente falso — el router es un clasificador regex sobre mensajes de entrada del usuario; DSPy es un compilador de programas LLM. Son capas ortogonales. La tentación de hibridizar (reescribir el router *en* DSPy) sería sobre-ingeniería: 1.8k líneas de regex+heurística-de-negación funcionan O(skills) por mensaje sin llamar a un LLM, mientras DSPy requiere un LLM-call por inferencia. Lo que sí tiene retorno claro es usar DSPy para los skills que ya hacen razonamiento estructurado (verify, propose, design): reemplazar las plantillas Markdown por `dspy.Signature` + `dspy.ChainOfThought` y compilar con MIPROv2/GEPA contra el corpus de session transcripts. Eso ataca el gap real (`agent-quality`, `prompt-quality` en RULES §2/§8) sin tocar la capa de routing.

**Esfuerzo si adoptamos:** 3-7 días para el primer skill piloto (probablemente `sdd-verify` o `confidence-check` — ambos tienen estructura de I/O clara). +1-2 días para wiring de GEPA con `dspy/teleprompt/gepa/` (deep target #15).

---

## 🔍2 LightRAG + HippoRAG + graphiti

### LightRAG (HKUDS, MIT) — **MEJOR_EXTERNO** en retrieval; nuestra capa de almacenamiento es paralela

**Nuestra lógica:**
- `lib/engram_http_client.py` + `lib/engram_client.py` (198 L) — wrapper FTS5 sobre engram daemon. `search_observations(query, type_filter, project)` es full-text search plano vía HTTP `/search?q=...&type=...`.
- `lib/engram_lifecycle.py` (580 L) — orquesta search → graph-walk → ranking, expone `EngramLifecycle.search()`.
- `lib/cognee_client.py` (296 L) — cliente HTTP a Cognee (servicio externo opcional, gated por `COGNEE_ENABLED`); ofrece `search(search_type=INSIGHTS|CHUNKS|GRAPH_COMPLETION)` via `/api/v1/search`. **Es un proxy, no un retriever in-house**.

**LightRAG ofrece** (deep dive `HKUDS__LightRAG-2026-05-06.md`):
- Dual-level retrieval: **entity-level** (precise, KG-anchored) + **topic-level** (broad, embedding-based) — fusionados con score combinado. EMNLP 2025 paper.
- Multi-backend KG (Neo4j/Mongo/Postgres/Qdrant/Redis/ES); FastAPI server; WebUI.

**Delta:**
1. Engram FTS5 + graph walker no hace retrieval *dual-level* — busca por texto, luego camina relaciones. No hay scoring fusionado entity+topic.
2. Cognee tapa parcialmente el gap (ofrece `INSIGHTS`/`GRAPH_COMPLETION`) pero es servicio externo opcional; cuando `COGNEE_ENABLED=false` (default), no hay retrieval semántico.
3. No tenemos benchmarks (LightRAG ships `lightrag/evaluation/`).

**Recomendación:** **adoptar-patrón** (algoritmo, no framework). Port del scoring dual-level a `lib/engram_lifecycle.py` como ranking opcional encima de FTS5+graph. **Descartar** el framework completo (k8s+webui+6 storages duplica engram).

**Razón técnica:** el retrieval actual es válido para uso interno (decisiones, ADRs, sessions con topic_keys conocidos), pero degrada cuando la query es semántica difusa ("how does authentication work"). FTS5 + BFS de relaciones tipadas no compensa la falta de embedding-based topic recall. Cognee lo tapa, pero como dependencia HTTP externa con health-check (`is_cognee_available`); para reconstruction queremos algo in-process. El algoritmo dual-level es ~200 LOC portables y no requiere KG nuevo.

**Esfuerzo:** 3-5 días para port + benchmark A/B contra el corpus actual de Engram.

### HippoRAG (OSU-NLP-Group, MIT) — **MEJOR_EXTERNO** en multi-hop

**Nuestra lógica:**
- `lib/engram_graph_walker.py` (315 L) — BFS bounded a `DEFAULT_MAX_DEPTH=2` sobre `memory_relations` (edges: supersedes/related/compatible/conflicts_with), boost `DEFAULT_GRAPH_BOOST=0.3`. **No hay PageRank**, no hay scoring por importancia de nodo, todos los hops valen lo mismo.

**HippoRAG ofrece** (deep dive `OSU-NLP-Group__HippoRAG-2026-05-06.md`): Personalized PageRank sobre entity graph para multi-hop recall (NeurIPS 2024). 8 meses sin push pero v1.0.0 estable.

**Delta:** BFS plano vs PPR ponderado. Para queries que requieren 2+ hops y desambiguación, PPR es estrictamente superior — los nodos centrales reciben más peso, y el "personalized" vector permite anclar la propagación al query.

**Recomendación:** **adoptar-patrón**. Port de PPR scoring a `EngramGraphWalker` como modo alternativo a BFS (`walk_strategy="ppr"`). Reuse de `prompts/dspy_prompts/` como referencia para alinear con la adopción DSPy del item #1.

**Razón técnica:** ya tenemos el grafo (`memory_relations` con relations tipadas y confidence). Pasar de BFS a PPR es agregar `networkx.pagerank(personalization=...)` sobre la subgrafía cargada — ~150 LOC. El stagnation de 8 meses es aceptable: el algoritmo es de paper, no de framework activo.

**Esfuerzo:** 2-4 días.

### graphiti (getzep, Apache-2.0) — **MEJOR_EXTERNO** en modelo temporal

**Nuestra lógica:**
- `memory_relations` (schema en `engram_graph_walker.py`): tiene `created_at`, `updated_at`, `superseded_at`, `superseded_by_relation_id`. Eso es **mono-temporal** (transaction time / ingest time). No hay separación entre "cuándo ocurrió el evento descrito" vs "cuándo se ingirió la observación".
- Búsqueda en `lib/`: `event_time` aparece sólo en `lib/trace_joiner.py:94` (timestamp de eventos de telemetría, no de observaciones). Cero soporte bi-temporal en Engram.

**graphiti ofrece** (deep dive `getzep__graphiti-2026-05-06.md`): edges con (`valid_from`, `valid_to`) **+** (`ingested_at`) — bi-temporal. Cross-encoder reranking. MCP server. Eval contra LongMemEval.

**Delta:**
1. Engram no puede responder "qué creía el sistema sobre X *al momento T*" vs "qué sabemos hoy sobre X *en el período T*". Los `superseded_at` cubren parcialmente la primera, no la segunda.
2. No hay reranker neuronal — el ranking final es score FTS5 + graph_boost lineal.
3. Sin benchmark estándar (LongMemEval).

**Recomendación:** **adoptar-patrón** (schema bi-temporal). **Descartar** el framework completo (Apache-2.0 con NOTICE compliance, pre-1.0 churn, 4 KG drivers que no necesitamos). Cross-encoder reranking es opcional secundario.

**Razón técnica:** el gap bi-temporal es real y tiene impacto concreto en COS — los ADRs y session summaries describen eventos pasados; sin `valid_from/valid_to` no podemos consultar histórico correctamente. Es una migración de schema (`ALTER TABLE memory_relations ADD COLUMN valid_from/valid_to`) + actualización de writers, no requiere vendoring.

**Esfuerzo:** 4-7 días (schema + migration + writers + un par de queries de prueba estilo LongMemEval).

---

## 🔍12 MIRIX taxonomy

**Veredicto:** **MEJOR_EXTERNO** (gap real, pero pequeño).

**Nuestra lógica:**
- Engram trata `type` como **string libre**: `engram_client.save_observation(type_="manual")`, `engram_http_client.search_observations(type_filter="discovery")`. No hay enum, no hay validación, no hay constante exportada. Búsqueda en `lib/` y `mcp-server/`: cero `OBSERVATION_TYPES` / `VALID_TYPES`. La taxonomía existe sólo en docstrings y CLAUDE.md (`bugfix|decision|architecture|discovery|pattern|config|preference`) — convención, no contrato.
- Eso significa que nada impide guardar un `type="anything"` y nada distingue conceptualmente una observación procedural ("para hacer X, ejecutar Y") de una semántica ("X es Y") o episódica ("a las 10:00 ocurrió X").

**MIRIX ofrece** (follow-up `Mirix-AI__MIRIX-2026-05-06.md`, Apache-2.0, 3.5k stars, push 2026-04-28):
- Memory split formal: **semantic** (hechos), **episodic** (eventos con timestamp), **procedural** (cómo-hacer), **working** (transitorio/contexto activo). Multi-agent que dirige cada captura al store correcto.

**Delta:**
1. Nuestros tipos son orientados-a-acción del desarrollador (`bugfix`, `decision`) y mezclan dimensiones — un `bugfix` *es* episódico+procedural a la vez.
2. No hay distinción entre memoria **working** (contexto de sesión, debe expirar) y persistente. `lib/memory_decay.py` existe pero no está acoplado a la dimensión working/episodic.
3. No hay concepto de "procedural" como first-class — los runbooks viven en `docs/runbooks/`, separados de Engram.

**Recomendación:** **adoptar-patrón** (taxonomy overlay), **no adoptar-código** (MIRIX es framework de personal-AI con captura de pantalla, irrelevante).

**Razón técnica:** el gap es real pero el costo es bajo. Agregar un campo `memory_class IN (semantic, episodic, procedural, working)` ortogonal al `type` actual permite: (a) acoplar `memory_decay` a `memory_class=working` (decay agresivo), (b) routing de retrieval (queries "cómo hago X" → procedural; "qué decidimos sobre Y" → semantic; "cuándo ocurrió Z" → episodic), (c) alineación con la literatura (LongMemEval usa la misma taxonomía). No es estrictamente necesario para reconstruction, pero el costo marginal es bajo si ya tocamos schema para bi-temporal (item #2/graphiti).

**Esfuerzo:** 1-2 días si se hace junto con la migración bi-temporal; 2-3 días aislado.

---

## Resumen ejecutivo

**Adoptar (alta prioridad):**
1. **graphiti bi-temporal schema** (`valid_from/valid_to` en `memory_relations`) — 4-7d. Tapa gap real en queries históricas.
2. **LightRAG dual-level retrieval** portado a `engram_lifecycle.search()` — 3-5d. Tapa el gap semántico que hoy depende de Cognee opcional.
3. **MIRIX memory_class overlay** (semantic/episodic/procedural/working) — 1-2d marginal si se hace con #1. Bajo costo, alto retorno en routing y decay.

**Adoptar (media prioridad):**
4. **HippoRAG PPR** como modo alternativo en `EngramGraphWalker` — 2-4d. Mejora multi-hop sobre el BFS actual.
5. **DSPy como dependencia** para skills con I/O estructurada (`sdd-verify`, `confidence-check`) — 3-7d piloto. No reemplaza el router.

**Descartar:**
- LightRAG framework completo (k8s+webui+6 storages duplica Engram).
- graphiti framework completo (Apache-2.0 + pre-1.0 churn + drivers irrelevantes).
- HippoRAG framework (8 meses stale; sólo el algoritmo).
- MIRIX código (framework de personal-AI con screen-capture, fuera de scope).
- **Reescribir el skill router en DSPy** — categoría incorrecta (clasificador de mensajes ≠ compilador de programas LLM).

**Lo que ya tenemos y es defendible:**
- Skill router (regex+frontmatter+heurística-de-negación) es O(skills) sin LLM-call. No tocar.
- `EngramGraphWalker` con relations tipadas (supersedes/related/compatible/conflicts_with) es buen sustrato para PPR — no requiere refactor, sólo extensión.
- Cognee como opt-in HTTP es razonable como fallback, pero no debería ser el camino default — port LightRAG primero.
