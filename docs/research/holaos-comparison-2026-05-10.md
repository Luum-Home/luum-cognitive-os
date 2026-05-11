---
title: "holaOS Deep Comparison — luum-agent-os vs holaOS"
date: 2026-05-10
author: orchestrator
status: draft
source-repo: "/tmp/holaOS-investigation"
license-classification: "BSL-like / BLOCK for SaaS or commercial embedding — patterns only (Apache 2.0 body, BSL-equivalent restrictions)"
---

# holaOS Deep Comparison — luum-agent-os vs holaOS

> Research-first protocol artifact. Sections 10+ will be added as parallel Opus agent reports complete (see §9).

---

## 1. Resumen ejecutivo

holaOS (Holaboss AI, 2026) es un *agent computer* de código abierto: una plataforma de escritorio Electron + runtime TypeScript (Fastify, SQLite) en la que humanos y agentes IA comparten un mismo entorno de trabajo — browser, archivos, apps, memoria — de forma continua y coherente. Se posiciona como alternativa radical a los agent wrappers: el estado no se pierde entre sesiones, los agentes evolucionan con el tiempo y son inspeccionables. El harness propietario se llama `pi`.

La licencia es Apache 2.0 **modificada con cláusulas BSL-like**: prohíbe SaaS/embedding comercial a terceros y prohíbe remover logos del frontend. Según nuestro `[license-policy]`, esto la clasifica en la categoría **BLOCK para adopción de código**. Solo podemos adoptar **patrones y conceptos** bajo regla clean-room.

El stack es radicalmente distinto al nuestro (TS/Electron vs bash/Python/Claude Code), pero el repositorio contiene ~140 archivos solo en `runtime/api-server/src/` con implementaciones concretas de problemas que nosotros hemos atacado parcialmente: memoria gobernada por tipo, presupuesto de tool-replay, auto-evolución de skills, compactación de sesión con context-reserve, grants HMAC, bootstrapping proactivo de contexto, y más.

**Veredicto**: patrón-only, clean-room obligatorio. Alto valor conceptual. Mínimo riesgo si la implementación es original. No adoptar código ni strings literales.

---

## 2. Licencia y restricciones legales

### Texto literal del LICENSE

```
Modified Apache 2.0 License

holaOS is licensed under a modified version of the Apache License 2.0, with
the following additional conditions:

1. holaOS may be utilized commercially, including as a backend service for
   other applications or as an agent-computing platform for enterprises.
   Should the conditions below be met, a commercial license must be obtained
   from the producer:

   a. Hosted or embedded service: Unless explicitly authorized by Holaboss
      in writing, you may not use the holaOS source code to provide a
      hosted service to third parties, or embed holaOS as a component of
      a product or service that is sold, licensed, or otherwise
      commercially distributed to third parties.

      - This restriction applies to offering holaOS (in whole or
        substantial part) as a SaaS platform, a managed service, or as
        an integrated component within another commercial offering.
      - Internal use within a single organization (including multiple
        workspaces) does not require a commercial license.

   b. LOGO and copyright information: In the process of using holaOS's
      frontend, you may not remove or modify the LOGO or copyright
      information in the holaOS console or applications. This restriction
      is inapplicable to uses of holaOS that do not involve its frontend.

2. As a contributor, you should agree that:

   a. The producer can adjust the open-source agreement to be more strict
      or relaxed as deemed necessary.

   b. Your contributed code may be used for commercial purposes, including
      but not limited to its cloud business operations.

Copyright (c) 2026 Holaboss
```

### Clasificación bajo `[license-policy]` (RULES-COMPACT.md §10)

| Dimensión | Evaluación |
|---|---|
| Tipo base | Apache 2.0 |
| Restricciones adicionales | SaaS/embed comercial bloqueado; branding protegido |
| Categoría COS | **BSL-like** (misma clase que BSL/SSPL) |
| Veredicto policy | **BLOCK** para adopción de código fuente |

### Qué SE PUEDE hacer

- Leer y estudiar el código con fines de investigación y aprendizaje.
- Adoptar **patrones, conceptos y arquitecturas** expresados en implementaciones propias (clean-room): si describimos una idea en prosa y la implementamos desde cero en Python/bash, no hay copia.
- Uso interno dentro de una organización (no aplica a luum ya que no distribuimos holaOS).
- Referenciar el proyecto públicamente como inspiración.

### Qué NO SE PUEDE hacer

- Copiar bloques de código TypeScript y portarlos directamente (derivado de obra protegida con restricciones adicionales).
- Embeber holaOS como componente de un producto comercial distribuido a terceros.
- Ofrecer holaOS como SaaS sin licencia comercial de Holaboss.
- Remover logos del frontend si se usa la UI de holaOS.
- Contribuir asumiendo que el código será solo MIT — el CLA del contributor explícitamente cede derechos comerciales al productor.

**Acción requerida**: cualquier implementación derivada de patrones holaOS debe nacer de una especificación funcional original, sin copiar código. Documentar en ADR correspondiente que la inspiración fue holaOS y que la implementación es clean-room.

---

## 3. Inventario completo

### 3.1 Runtime API Server (`runtime/api-server/src/`)

**Total de archivos**: ~140 (incluyendo tests y fixtures). Archivos de producción relevantes agrupados por dominio:

**Memoria y recall**
- `memory-governance.ts` — reglas por tipo de memoria (staleness, verification policy, recall boost)
- `memory.ts`, `memory-model-client.ts` — cliente de modelo para operaciones de memoria
- `memory-capture-views.ts` — vistas de memoria capturada para prompts
- `memory-recall.ts`, `memory-recall-index.ts`, `memory-recall-manifest.ts` — pipeline de recall con embedding + manifest cacheable
- `memory-embedding-index.ts`, `recall-embedding-model.ts` — índice vectorial local
- `recall-embedding-backfill-worker.ts` — worker de backfill asíncrono
- `memory-writeback-extractor.ts` — extracción de candidatos de memoria desde turno
- `turn-memory-writeback.ts` — writeback durable al store
- `user-memory-proposals.ts` — propuestas de memoria iniciadas por el usuario

**Evolución y skills**
- `evolve.ts` — orquestador de jobs post-run (memory writeback, skill review, task proposals)
- `evolve-skill-review.ts` — revisión de turns para candidatos de skill (confidencia >= 0.72)
- `evolve-tasks.ts` — proposición de tasks desde evolve
- `evolve-worker.ts` — worker que consume la queue de evolve jobs
- `workspace-skills.ts` — resolución de skills del workspace

**Sesión y checkpoint**
- `session-checkpoint.ts` — compactación de sesión con `PI_COMPACTION_CONTEXT_RESERVE_RATIO = 0.5`
- `session-todo.ts` — state machine de todos por sesión (versión 2, ops: replace/add_phase/add_task/update/remove_task)
- `session-scratchpad.ts` — scratchpad de sesión
- `main-session-event-worker.ts`, `main-session-event-prompt.ts` — worker de eventos de sesión principal

**Agentes y runtime**
- `agent-runtime-config.ts`, `agent-runtime-prompt.ts`, `agent-prompt-sections.ts` — configuración y prompt del agente
- `agent-capability-registry.ts` — registro de capacidades del agente
- `subagent-model.ts` — perfiles de ejecución de subagentes (model + thinking_value)
- `runner-worker.ts`, `runner-prep.ts` — preparación y ejecución de runs
- `ts-runner.ts` + events/state — runner TypeScript
- `background-task-model.ts` — modelo de background tasks con provider aliases
- `queue-worker.ts` — worker de queue con concurrencia configurable (`HB_QUEUE_WORKER_CONCURRENCY`)
- `proactive-context.ts` — bootstrap proactivo de contexto para sesión

**Workspace y plan**
- `workspace-runtime-plan.ts` — plan de runtime compilado desde YAML del workspace
- `workspace-snapshot.ts`, `workspace-bundle-paths.ts` — snapshot y paths del workspace
- `workspace-mcp-host.ts`, `workspace-mcp-sidecar.ts` — host y sidecar MCP
- `workspace-tool-loader.ts`, `workspace-apps.ts` — loader de tools y apps
- `resolved-app-bootstrap.ts`, `resolved-app-bootstrap-shared.ts` — bootstrap de apps resueltas

**Seguridad y grants**
- `grant-signing.ts` — firma HMAC-SHA256 de grants (TTL 24h, nonce UUID)
- `oauth-service.ts` — flujo OAuth PKCE con servidor local de redirect
- `app-setup-env.ts`, `apply-app-schema.ts` — setup de entorno y schema de apps

**Integraciones**
- `composio-service.ts` — proxy a Composio (nunca llama directo, sin API key en runtime)
- `composio-minimal-example.ts`, `composio-test-server.ts` — fixtures de Composio
- `integration-broker.ts`, `integration-runtime.ts`, `integration-types.ts`, `integrations.ts` — broker de integraciones
- `native-web-search.ts` — búsqueda web nativa

**Outputs y turn artifacts**
- `turn-output-capture.ts`, `turn-result-summary.ts`, `turn-semantic-artifacts.ts` — captura y análisis de outputs de turn
- `tool-result-budget.ts`, `tool-result-preview.ts` — presupuesto y preview de resultados de tools
- `image-generation.ts`, `image-generation-model.ts` — generación de imágenes

**Infraestructura**
- `app.ts`, `index.ts` — entrada Fastify
- `runtime-config.ts`, `runtime-config-cli.ts` — configuración de runtime
- `runtime-ai-monitoring.ts`, `runtime-sentry.ts`, `runtime-shell.ts` — monitoring y shell
- `cron-worker.ts` — worker de cron
- `bridge-worker.ts`, `claimed-input-executor.ts` — bridge y executor de inputs reclamados
- `harness-registry.ts`, `harness-conformance.test.ts` — registro de harnesses
- `data-schema.ts` — esquemas de datos
- `automations-import.ts` — import de automatizaciones

### 3.2 Harnesses (`runtime/harnesses/src/`)

- `pi.ts` — definición del harness `pi` (Claude Code-compatible, soporta skills/MCP/browser tools)
- `skill-policy.ts` — política de widening de skills (gestión de tool grants por skill)
- `todo-policy.ts` — política de todos del harness
- `tool-replay-budget-ledger.ts` — ledger de presupuesto de replay de tools
- `capability-http.ts` — cliente HTTP para capacidades del harness
- `browser-capability-client.ts`, `browser-capability-tools.ts` — capacidades de browser
- `runtime-capability-tools.ts`, `runtime-tool-capability-client.ts` — tools de capacidad del runtime
- `desktop-browser-tools.ts` — tools de browser para desktop
- `native-web-search.ts`, `native-web-search-tools.ts` — búsqueda web nativa
- `mcp.ts` — integración MCP
- `model-routing.ts` — enrutamiento de modelos
- `workspace-boundary.ts`, `workspace-skills.ts` — boundary y skills del workspace
- `attachment-content.ts` — contenido de attachments
- `runner-events.ts`, `runtime-agent-tools.ts` — eventos y tools del agente
- `embedded-skills/` — skills embebidas: `browser-core-efficient/`, `browser-qa/`, `mcp-configurator/`, `skill-creator/`, `skill-installer/`
- `types.ts` — tipos del harness
- `index.ts` — punto de entrada

### 3.3 Harness host (`runtime/harness-host/`)

Proceso host que lanza y gestiona el harness `pi`. Actúa como supervisor del proceso del agente.

### 3.4 State store (`runtime/state-store/`)

SQLite wrapper tipado: `RuntimeStateStore`. Entidades: workspaces, sessions, inputs, outputs, memory entries, task proposals, post-run jobs, OAuth app configs, MCP servers, cron jobs.

### 3.5 SDK y cliente

- `sdk/app-sdk/` — SDK para construir apps sobre holaOS
- `sdk/runtime-client/` — cliente HTTP del runtime
- `sdk/bridge/` — bridge runtime-desktop
- `sdk/editor/` — integración con editor

### 3.6 Desktop

- `desktop/` — Electron app (Vite + React). Frontend con workspace management, chat, apps marketplace.

### 3.7 Packages

Monorepo con packages compartidos entre desktop y runtime.

### 3.8 Docs

- `docs/images/` — assets de marketing
- Docs técnicos en `holaos.ai/docs` (externos al repo)

---

## 4. Top 10 candidatos a adoptar

> Todos bajo **regla clean-room**: inspiración conceptual, implementación original en Python/bash. Cero copia de código TS.

| # | Patrón | Archivo fuente holaOS | Equivalente luum | Por qué nos sirve | Esfuerzo | Riesgo |
|---|---|---|---|---|---|---|
| 1 | Memory governance tipada | `runtime/api-server/src/memory-governance.ts` | `lib/memory.py`, `lib/memory_manager.py` (sin governance tipada) | Nos da un sistema formal de staleness + verification policy + recall boost por tipo de memoria. Actualmente Engram no distingue tipos con reglas distintas de frescura. | M | Bajo — puro diseño de datos |
| 2 | Tool-replay budget ledger | `runtime/harnesses/src/tool-replay-budget-ledger.ts` | `lib/budget_calculator.py`, `lib/context_budget.py` (no cubre replay chars) | Limitar cuántos chars/items de resultados de tools se replayan en contexto previene context overflow silencioso. Hoy no tenemos este control granular. | S | Bajo — módulo independiente |
| 3 | Evolve loop post-run | `runtime/api-server/src/evolve.ts` + `evolve-skill-review.ts` | `hooks/skill-post-execution-analysis.sh` (hook bash, sin confidencia) | Pipeline estructurado: cada run dispara análisis de skill candidate con score de confidencia (0.72 min), propuesta de task, y memory writeback. Mucho más robusto que nuestro hook. | L | Medio — requiere queue de post-run jobs |
| 4 | Grant signing HMAC | `runtime/api-server/src/grant-signing.ts` | `scripts/adr100_live_headroom_check.py` (sin auth de grants) | El cosd expone API HTTP sin signing robusto hoy. HMAC-SHA256 + TTL 24h + nonce UUID es el patrón exacto que ADR "grant-signed cosd API" debería adoptar. | S | Bajo — crypto estándar |
| 5 | Session checkpoint con context-reserve ratio | `runtime/api-server/src/session-checkpoint.ts` | `lib/session_lifecycle.py`, `lib/context_budget_monitor.py` | `PI_COMPACTION_CONTEXT_RESERVE_RATIO = 0.5` es la idea clave: no compactar hasta que el contexto esté al 50%, y reservar headroom. Nuestra compactación actual no modela este ratio. | M | Medio — toca lifecycle de sesión |
| 6 | Workspace runtime plan compilado | `runtime/api-server/src/workspace-runtime-plan.ts` | `cognitive-os.yaml` (YAML plano sin compilación) | Un plan compilado (YAML → objeto tipado + hash de contenido) permite detectar cambios, cachear, y referenciar desde múltiples workers. Aplicable a `cognitive-os.yaml` + skill registry. | M | Bajo — mejora DX, no rompe nada |
| 7 | Proactive context bootstrap | `runtime/api-server/src/proactive-context.ts` | `lib/agent_context_injector.py` (parcial) | Ensambla contexto del workspace (snapshot, memoria, skills, task proposals, outputs) antes de que el agente arranque. Nuestro injector es más ad-hoc. | M | Bajo — aditivo |
| 8 | Session-todo state machine | `runtime/api-server/src/session-todo.ts` | Engram + TodoWrite (sin state machine formal) | State machine con fases y tareas (v2), ops tipadas (replace/add_phase/add_task/update/remove_task), persistencia por sesión. Más robusto que el TodoWrite ad-hoc actual. | M | Bajo-Medio — cambio de modelo mental |
| 9 | Skill widening policy | `runtime/harnesses/src/skill-policy.ts` | `.claude/settings.json` allowlist (estático) | Gestión dinámica de qué tools/commands otorga cada skill al agente. El scope `run` limita el widening a la ejecución actual. Aplicable a nuestro sistema de permisos por skill. | L | Medio — toca harness Claude Code |
| 10 | Turn-memory writeback extractor | `runtime/api-server/src/memory-writeback-extractor.ts` + `turn-memory-writeback.ts` | `lib/mem_save_prompt` + Engram mem_save (manual) | Extracción automática de candidatos de memoria desde cada turno vía modelo, con scope (workspace/user), tipo (preference/identity/fact/procedure/blocker/reference), subject_key, confidence. Hoy la captura de memoria en luum es mayoritariamente manual. | L | Medio — requiere llamada LLM por turno |

---

## 5. Patrones arquitectónicos novedosos

### 5.1 Environment Engineering

**Descripción**: holaOS posiciona al entorno (workspace) como el artefacto de primera clase, no la conversación ni el modelo. El workspace tiene un contrato explícito: superficies authored (YAML, skills, apps), estado runtime-owned (memoria, outputs, session state), y un plan compilado. El agente opera dentro de ese entorno, no lo es.

**Archivo fuente**: `runtime/api-server/src/workspace-runtime-plan.ts`, `runtime/api-server/src/proactive-context.ts`, y la documentación en `holaos.ai/docs/concepts/environment-engineering`.

**Comparación con luum**: En luum, `cognitive-os.yaml` es el workspace YAML pero no tiene compilación, hash de contenido ni plan resuelto. El entorno se construye implícitamente en cada sesión. No existe un artefacto `CompiledWorkspaceRuntimePlan` que se cachee y versioné.

**Valor potencial**: Compilar `cognitive-os.yaml` + skill registry en un plan con hash permitiría detectar drift de configuración, cachear el contexto de arranque, y hacer reproducibles los runs. Aplicable a nuestro `generate-config` skill.

---

### 5.2 Capability Projection over HTTP

**Descripción**: Las capacidades del harness (browser, shell, MCP tools) se exponen como endpoints HTTP locales que el agente consume mediante `capability-http.ts`. El runtime actúa como proxy entre el agente y las capacidades, con timeout y abort signal por request. Los tools del agente llaman al runtime, no al sistema directamente.

**Archivo fuente**: `runtime/harnesses/src/capability-http.ts`, `runtime/harnesses/src/runtime-tool-capability-client.ts`, `runtime/harnesses/src/runtime-capability-tools.ts`.

**Comparación con luum**: En luum, `cosd` expone una API HTTP pero sin signing ni capability model formal. Las tools del agente (Claude Code) acceden al sistema directamente vía permisos en `settings.json`. No existe un runtime intermediario que modele las capacidades como endpoints tipados.

**Valor potencial**: Formalizar `cosd` como capability server (con signing HMAC, timeout, abort) sería el equivalente directo. Candidato principal para el ADR "Grant-signed cosd API".

---

### 5.3 Apps con Schemas + Grants OAuth

**Descripción**: holaOS tiene un marketplace de apps donde cada app declara un schema (tipos de datos que produce/consume) y requiere grants firmados HMAC para operar dentro de un workspace. El OAuth PKCE local permite que apps obtengan tokens de servicios externos. El runtime valida grants antes de ejecutar cualquier operación de app.

**Archivo fuente**: `runtime/api-server/src/apply-app-schema.ts`, `runtime/api-server/src/grant-signing.ts`, `runtime/api-server/src/oauth-service.ts`, `runtime/api-server/src/workspace-apps.ts`.

**Comparación con luum**: Nuestras "apps" son skills de Claude Code sin grants formales ni schemas de datos. No tenemos OAuth integrado en el runtime. El sistema de permisos es estático (settings.json).

**Valor potencial**: El patrón de grant HMAC es directamente aplicable a `cosd`. El esquema de apps podría inspirar una versión liviana de skill registry con grants por skill.

---

### 5.4 Hidden Subagents (Background Task Model)

**Descripción**: holaOS lanza subagentes invisibles para el usuario en background: memory writeback, skill review, session checkpoint, evolve tasks. Estos subagentes tienen un modelo y thinking_value propios (ver `subagent-model.ts`), se despachan vía queue (`queue-worker.ts`), y tienen un `background-task-model.ts` con aliases de provider y defaults por proveedor.

**Archivo fuente**: `runtime/api-server/src/background-task-model.ts`, `runtime/api-server/src/queue-worker.ts`, `runtime/api-server/src/evolve-worker.ts`.

**Comparación con luum**: En luum, los subagentes se lanzan explícitamente vía `Agent` tool con model routing manual. No existe una queue de post-run jobs con TTL, lease y heartbeat. El `queue-worker.ts` tiene `DEFAULT_LEASE_SECONDS = 300`, `DEFAULT_MAX_CONCURRENCY = 2`, y `CLAIM_STALE_HEARTBEAT_MS = 20_000`.

**Valor potencial**: Una queue de post-run jobs (implementada sobre el sistema de archivos o SQLite) daría más robustez al ciclo de evolución post-sesión. Aplicable a la revisión de skills post-run y memory writeback automático.

---

### 5.5 Embedding Recall con Manifest Cacheable

**Descripción**: El pipeline de recall combina un índice vectorial local (`memory-embedding-index.ts`) con un manifest serializable (`memory-recall-manifest.ts`) que se puede cachear entre sesiones. El manifest limita el número de entradas (`MAX_INDEX_ENTRIES = 200`) y aplica boost por tipo de memoria (preference=4, identity=3, blocker=3). Los vectores son de dimensión fija (`RECALL_EMBEDDING_DIM`).

**Archivo fuente**: `runtime/api-server/src/memory-recall-manifest.ts`, `runtime/api-server/src/memory-embedding-index.ts`, `runtime/api-server/src/memory-recall.ts`.

**Comparación con luum**: Engram provee búsqueda semántica pero el índice es externo (servidor Engram). No tenemos un manifest local cacheable ni boost por tipo de memoria. El `mem_search` no modela recall boost.

**Valor potencial**: Para escenarios offline o de alta latencia, un manifest local con embeddings cacheados sería valioso. El concepto de recall boost por tipo de memoria es implementable en Engram como parámetro de score.

---

### 5.6 Post-Run Jobs Queue

**Descripción**: Después de cada run, holaOS encola un conjunto de jobs en `post_run_jobs` (SQLite): memory writeback, skill review, session checkpoint. El `evolve-worker.ts` los consume de forma asíncrona. Cada job tiene tipo (`EVOLVE_JOB_TYPE`, `SESSION_CHECKPOINT_JOB_TYPE`), payload tipado, y resultado persistido. El `queue-worker.ts` tiene TTL de lease, heartbeat, y concurrencia configurable.

**Archivo fuente**: `runtime/api-server/src/evolve.ts`, `runtime/api-server/src/evolve-worker.ts`, `runtime/api-server/src/session-checkpoint.ts`, `runtime/api-server/src/queue-worker.ts`.

**Comparación con luum**: Los hooks post-ejecución de luum (`hooks/skill-post-execution-analysis.sh`, `packages/agent-lifecycle/hooks/review-spawner.sh`) son síncronos o fire-and-forget sin queue persistida. Si un hook falla, no hay retry. No hay modelo de jobs con TTL ni heartbeat.

**Valor potencial**: Una queue de post-run jobs implementada en Python (usando un archivo JSONL o SQLite) daría retry, observabilidad y desacoplamiento. Es el fundamento del "Evolve loop sobre Claude Code" spike.

---

## 6. Gaps cubiertos vs lo que ya tenemos

| Capacidad | luum hoy | holaOS | Acción recomendada |
|---|---|---|---|
| Memoria gobernada por tipo | Engram con tipos básicos, sin staleness policy formal ni recall boost diferenciado | `memory-governance.ts`: 6 tipos (preference/identity/fact/procedure/blocker/reference), staleness, verification policy, recall boost 1-4 | ADR "Memory Governance v2" — definir policy por tipo en Engram |
| Tool replay budgets | `lib/context_budget.py` (chars totales, sin desglose por items de tool) | `tool-replay-budget-ledger.ts`: chars + items por sesión, TTL 6h, max 512 ledgers | Implementar `lib/tool_replay_budget.py` inspirado en el patrón |
| Self-evolution de skills | `hooks/skill-post-execution-analysis.sh` (bash, sin score de confidencia) | `evolve-skill-review.ts`: confidencia mínima 0.72, revisión cada 3 turns, límite 5 turns recientes | Spike "Evolve loop sobre Claude Code" con score formal |
| Compactación de sesión | `lib/session_lifecycle.py` + compactación manual en hooks | `session-checkpoint.ts`: context-reserve ratio 0.5, poll 100ms, outcomes tipados | Mejorar `lib/session_lifecycle.py` con context-reserve ratio |
| OAuth grants | Sin OAuth en runtime | `oauth-service.ts`: PKCE completo con servidor local, tokens persistidos en store | Futura integración si luum necesita OAuth a servicios externos |
| Grant signing | Sin signing en cosd API | `grant-signing.ts`: HMAC-SHA256, TTL 24h, nonce UUID | ADR "Grant-signed cosd API" — implementar en `cosd` |
| Embedding recall | Engram search (externo) | `memory-recall-manifest.ts`: manifest local cacheable, boost por tipo, vectores locales | Evaluar manifest local como fallback offline |
| Workspace plan compilado | `cognitive-os.yaml` plano | `workspace-runtime-plan.ts`: YAML → plan tipado con hash, MCP servers resueltos, tool refs | Compilar `cognitive-os.yaml` en runtime con hash de versión |
| Marketplace de apps | Sin marketplace | Desktop con apps, schemas, grants, OAuth integrado | No prioritario — stack muy diferente |
| Post-run jobs queue | Hooks fire-and-forget sin retry | `queue-worker.ts`: lease, heartbeat, concurrencia, TTL, retry | Implementar `lib/post_run_jobs.py` como JSONL queue |

---

## 7. Riesgos / red flags

### 7.1 Licencia BSL-like (riesgo legal)

**Nivel**: ALTO. La cláusula 1.a prohíbe explícitamente SaaS y embedding comercial. Si luum alguna vez ofrece el agent OS como servicio, adoptar código holaOS crearía riesgo legal. El CLA de contributor (cláusula 2) es agresivo: cede derechos comerciales al productor de forma irrevocable. **Mitigación**: implementación clean-room obligatoria. Documentar en cada ADR que la inspiración es holaOS y la implementación es original.

### 7.2 Stack mismatch (TS/Electron vs bash/Python)

**Nivel**: MEDIO. Ningún archivo TypeScript es adoptable directamente. Todo patrón requiere reescritura en Python o bash. Los tipos y contratos del state store son específicos de `@holaboss/runtime-state-store` (SQLite). **Mitigación**: usar como referencia de diseño, no de implementación.

### 7.3 No es un harness Claude Code — reemplaza el harness

**Nivel**: ALTO para adopción directa, BAJO para inspiración. `pi` es un harness propio que reemplaza Claude Code. Usar holaOS en lugar de Claude Code nos haría perder el harness nativo de Anthropic, los MCP nativos, y el contexto de tooling que ya tenemos. **Mitigación**: no adoptar holaOS como runtime — solo extraer patrones.

### 7.4 Dependencia de Composio (servicio comercial)

**Nivel**: MEDIO. `composio-service.ts` muestra que holaOS proxea Composio para integraciones. Composio tiene pricing por uso. Si adoptáramos el patrón de integración broker, necesitaríamos evaluar alternativas open source. **Mitigación**: el patrón de proxy (runtime nunca tiene API key directa) es adoptable; Composio como proveedor, no.

### 7.5 Costo de embeddings

**Nivel**: MEDIO. El pipeline de recall usa embeddings vectoriales locales (`RECALL_EMBEDDING_DIM`). Para generarlos se necesita un modelo de embeddings (OpenAI, local). En luum, añadir embeddings por turno tendría costo API o requeriría un modelo local. **Mitigación**: implementar el patrón manifest sin embeddings inicialmente (BM25 o búsqueda por metadata), y añadir embeddings como capa opcional.

### 7.6 Tamaño del proyecto (~140 archivos solo en api-server/src)

**Nivel**: BAJO (para investigación) / MEDIO (para mantenimiento de fork). El volumen de código dificulta una revisión exhaustiva sin agentes paralelos. Para patrones específicos, la granularidad de archivos es buena — cada módulo es cohesivo. **Mitigación**: los 5 agentes Opus paralelos (§9) cubrirán el análisis profundo.

### 7.7 Proyecto activo pero joven

**Nivel**: BAJO-MEDIO. holaOS es de 2026 (copyright `© 2026 Holaboss`). Activo (CI badge presente, release notes en RELEASING.md, OSS release notes en README). Pero el historial de commits no es visible y la madurez de la API no está garantizada. Los contratos pueden cambiar. **Mitigación**: usar para inspiración de patrones estables (HMAC, state machine, governance rules) — no depender de su estabilidad de API.

---

## 8. Próximos pasos recomendados

### 8.1 ADR "Memory Governance v2"

Definir formalmente los 6 tipos de memoria (preference, identity, fact, procedure, blocker, reference) con políticas de staleness, verification y recall boost. Implementar en `lib/memory_manager.py` y Engram como extensión del schema de observaciones. El patrón de `memory-governance.ts` es la referencia de diseño.

**Owner**: sdd-propose → sdd-spec → sdd-apply
**Estimación**: M (1-2 sprints)

### 8.2 ADR "Grant-signed cosd API"

Implementar signing HMAC-SHA256 en los endpoints de `cosd`. Cada request del agente al runtime incluirá un grant firmado con workspace_id, app_id (skill_id), timestamp y nonce. El servidor verifica TTL (24h sugerido) y firma. Referencia: `grant-signing.ts`.

**Owner**: sdd-propose → sdd-spec → sdd-apply
**Estimación**: S (< 1 sprint)

### 8.3 Spike "Evolve loop sobre Claude Code"

Investigar si el patrón evolve (post-run job → skill review con confidencia → candidato → promoción) es reproducible sobre Claude Code sin un runner TypeScript. Hipótesis: implementable como hook Python post-sesión que lee el transcript, llama a un modelo con el prompt de skill review, y escribe en el skill registry si confidencia >= 0.72.

**Owner**: agente Sonnet de investigación
**Estimación**: L (2-3 sprints si se implementa, 1 sprint si solo spike)

### 8.4 Tool-replay budget ledger en orchestrator

Implementar `lib/tool_replay_budget.py` como módulo independiente: ledger en memoria (dict), TTL 6h, límites configurables (default: 24K chars, 8 items). Integrar en `lib/context_budget_monitor.py`. Referencia: `tool-replay-budget-ledger.ts`.

**Owner**: agente Sonnet
**Estimación**: S (< 1 sprint)

### 8.5 Este research doc + `decision_tracker.record_decision("holaos-adoption")`

El presente doc cumple la condición de research-first. El siguiente paso es que el orchestrator llame a `lib/decision_tracker.record_decision("holaos-adoption")` con el veredicto: **patrón-only, clean-room, 4 ADRs recomendados**. Guardar en Engram bajo `decision/holaos-adoption`.

**Owner**: orchestrator (inmediato)
**Estimación**: XS (15 min)

---

## 9. Investigación profunda código-a-código — COMPLETADA (2026-05-11)

5 agentes Opus en paralelo + 2 follow-ups (Sonnet) produjeron los siguientes anexos. Estado: **research complete**, listo para implementación con guardrails de compliance.

| Anexo | Dominio | Doc | Modelo | Engram topic |
|---|---|---|---|---|
| A | Memoria | [holaos-annex-a-memory.md](holaos-annex-a-memory.md) | Opus | `research/holaos/annex-a` |
| B | Cost/Budget | [holaos-annex-b-cost-budget.md](holaos-annex-b-cost-budget.md) | Opus | `research/holaos/annex-b` |
| C | Evolución | [holaos-annex-c-evolution.md](holaos-annex-c-evolution.md) | Opus | `research/holaos/annex-c` |
| D | Seguridad/Plan | [holaos-annex-d-security-plan.md](holaos-annex-d-security-plan.md) | Opus | `research/holaos/annex-d` |
| E | Arquitectura/Riesgos | [holaos-annex-e-architecture-risks.md](holaos-annex-e-architecture-risks.md) | Opus | `research/holaos/annex-e` |
| F | Compliance & Clean-Room Protocol | [holaos-annex-f-compliance-cleanroom.md](holaos-annex-f-compliance-cleanroom.md) | Sonnet | `research/holaos/annex-f` |
| G | Hallazgos sorpresa (capability envelope + unified queue) | [holaos-annex-g-surprise-findings.md](holaos-annex-g-surprise-findings.md) | Sonnet | `research/holaos/annex-g` |

### Insights cross-anexo críticos

1. **Postura legal obligatoria (F)**: patterns-only library con clean-room rewrite. Cada ADR de adopción debe citar source-path y certificar no-transcripción. Pre-commit gate (`hooks/holaos-cleanroom-gate.sh`) diseñado en F§7.
2. **Inversión arquitectónica (E)**: holaOS posee el prompt loop, model routing, tool surface, SQLite por workspace y workers daemon. luum vive *dentro* de Claude Code — 5 puntos de fricción enumerados. Esto descarta de raíz el `pi` harness, el marketplace, Composio y Electron.
3. **P0 urgente (D)**: `cosd` usa bearer estático omnipotente (`scripts/cos_daemon.py:141-158`). Reemplazo HMAC+nonce+TTL+scope binding planificado en `lib/cosd_grant.py` clean-room. ~3 días.
4. **Hallazgos sorpresa (G)**: dos features cross-cutting fuera del top-10 inicial — capability HTTP result envelope (32KB threshold, 1-2 días) y unified leased work queue (consolida nuestras 8 queue modules dispersas, 2-3 semanas).
5. **Moats nuestros confirmados (A, E)**: relations/graph layer, session-end crystallizer, MemoryScanner (seguridad) — holaOS NO los tiene.
6. **Complementariedad memoria (A)**: writeback LLM cada 5 turns + `user-prompt-capture.sh` regex + `engram_crystallizer` session-end son **complementarios**, no redundantes.
7. **Bloqueante señal (B)**: B2-pragmática (context-reserve ratio) requiere que `llm-dispatch.jsonl` exponga `tokens/context_window` por turn. Verificación pre-implementación.
8. **No acoplar evolve→sdd-new (C)**: eludiría comparative-promotion gate y saturaría cola. Sí permitir que `/sdd-explore` lea el queue de candidates.

### Esfuerzo agregado por dominio

| Anexo | Esfuerzo total | Prioridad |
|---|---|---|
| A — Memoria | 15-20 días (3 features) | Alta |
| B — Cost/Budget | 3-7 días | Media-alta |
| C — Evolución | 7-10 días (3 features) | Alta |
| D — Seguridad/Plan | 12 días (P0 urgente: 3 días) | **P0** |
| G1 — Capability envelope | 1-2 días | Quick win |
| G2 — Unified queue | 2-3 semanas | Sprint dedicado 0.30+ |

---

## 10. Anexos — índice

- **[Anexo A — Memoria](holaos-annex-a-memory.md)**: governance tipada, turn-memory writeback (LLM cada 5 turns, dual confidence 0.82/0.60), embedding recall (2 olas).
- **[Anexo B — Cost/Budget](holaos-annex-b-cost-budget.md)**: tool-replay ledger (cap 24K/8items, TTL 6h, reference_only), context-reserve ratio 0.5 con job queue persistente.
- **[Anexo C — Evolución](holaos-annex-c-evolution.md)**: evolve loop con confidence threshold, task proposal queue, skill widening least-privilege, session-todo state machine con invariantes.
- **[Anexo D — Seguridad/Plan](holaos-annex-d-security-plan.md)**: **P0** grant-signed cosd (HMAC+nonce+TTL+scope), compiled runtime plan con checksum, proactive context bootstrap dos-fases.
- **[Anexo E — Arquitectura/Riesgos](holaos-annex-e-architecture-risks.md)**: 6 patrones evaluados, top 3 adoptar/parking/descartar, 5 puntos de fricción de inversión arquitectónica, postura licencia umbrella.
- **[Anexo F — Compliance & Clean-Room Protocol](holaos-annex-f-compliance-cleanroom.md)**: 3 niveles de adopción, matriz 7×4 artefacto×uso, roles research/implementer/reviewer, checklist 12-items, plantilla commit, audit trail, 8 triggers escalation.
- **[Anexo G — Hallazgos sorpresa](holaos-annex-g-surprise-findings.md)**: capability HTTP result envelope (32KB) + unified leased work queue (consolidación de 8 modules).

---

## UNSURE

- La versión exacta de Node.js del runtime en producción (README dice Node 24.14.1 para desktop; el runtime podría diferir).
- Si `RECALL_EMBEDDING_DIM` usa OpenAI embeddings o un modelo local — el archivo `recall-embedding-model.ts` existe pero no fue inspeccionado en profundidad.
- El contenido exacto de `runtime/harness-host/` — no fue listado en detalle. Se asume que es el supervisor de proceso del harness `pi`.
- Si el `desktop/` tiene un backend Hono separado o si el runtime Fastify sirve todo — el `composio-service.ts` menciona "Hono server base URL" lo que sugiere que hay un servidor Hono en el desktop layer.
- El estado de Windows/Linux: README dice "macOS supported, Windows & Linux in progress".
