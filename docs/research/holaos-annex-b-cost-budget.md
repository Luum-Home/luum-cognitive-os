---
title: "Annex B — Cost & Context Budget: holaOS vs luum-agent-os"
date: 2026-05-10
author: orchestrator (research-only Opus pass)
status: draft
parent: holaos-comparison-2026-05-10.md
source-repo: "/tmp/holaOS-investigation"
license-classification: "BSL-like / BLOCK for adoption — patterns only, clean-room"
scope: "2 of top-10 features: (B1) tool-replay budget ledger, (B2) session checkpoint with context-reserve ratio"
---

# Annex B — Cost & Context Budget Comparison

> Anexo B del comparativo holaOS. Foco exclusivo en **gobernanza del costo del contexto**: cómo cada sistema decide qué texto entra al modelo, cuánto, durante cuánto tiempo, y qué hace cuando el cinturón aprieta.
>
> **Constraint**: holaOS está bajo licencia BSL-like. Solo se citan patrones; cualquier implementación luum debe ser clean-room.

---

## 0. TL;DR

| Eje | holaOS | luum (actual) | Delta |
|---|---|---|---|
| **Granularidad de truncado** | Por `tool_id` (browser_get_state, terminal_session_read, skill, scratchpad, web_search, browser_screenshot) — cada uno con su política y sub-budgets | Único umbral global `max_chars=5000` para outputs Bash | **3 órdenes** de granularidad |
| **Modos de resultado** | `default` vs `preview` (negociable por header `x-holaboss-tool-result-mode`) | Solo `truncate-on-overflow` | Sin negociación |
| **Acumulación cross-tool** | Ledger por sesión: `totalReplayChars` + `totalReplayItems` con TTL 6h y `reference_only` mode al saturar | Ningún acumulador cross-tool; cada bash se trunca aislado | **Crítico** |
| **Spillover a disco** | Sí — payload grande va a `workspace/tool-results/<tool>/<session>/...` y queda `full_state_path` como referencia | No (excepto step-files para fases largas) | Pérdida real |
| **Compactación basada en context window real** | `shouldQueueSessionCheckpoint` mide `tokens / contextWindow` y dispara cuando excede `1 - reserve_ratio` (0.5 hardcoded) | Heurística por tool-call-count (50/70/85%) + `pre-compaction-flush.sh` reactivo | **Crítico**: medimos uso, no medimos *headroom* |
| **Compactación asincrónica idempotente** | Job en `RuntimeStateStore` con `idempotency_key`, guard de `leafId` + `latestCompactionId`, ejecución en proceso aparte | `pre-compaction-flush.sh` sincrónico, oportunista | Sin garantías |
| **Persistencia del resultado** | Outcome enum: `merged`, `merged_without_boundary`, `deferred_busy`, `binding_changed`, `soft_provider_422`, etc. | `engram-mem_session_summary` (best effort) | Sin taxonomía de fallo |

**Veredicto adelantado**: ambas features son adoptables vía patrón. La **B1 (ledger por tool)** es la de mayor ROI inmediato; la **B2 (checkpoint async con reserve ratio)** requiere infraestructura nueva (job queue persistente) pero alinea con singularity/MAPE-K.

---

## 1. Feature B1 — Tool-Replay Budget Ledger

### 1.1 holaOS — superficie

Dos archivos coordinados:

- `runtime/harnesses/src/tool-replay-budget-ledger.ts` (141 líneas) — el **ledger** acumulador por sesión.
- `runtime/api-server/src/tool-result-budget.ts` (16 líneas) — el **catálogo de límites** por tool_id.
- `runtime/api-server/src/tool-result-preview.ts` (~810 líneas) — el **modeller** que aplica los límites + spillover.

#### Patrón clave del ledger (`tool-replay-budget-ledger.ts:1-20`):

```
DEFAULT_MAX_REPLAY_CHARS = 24_000
DEFAULT_MAX_REPLAY_ITEMS = 8
LEDGER_TTL_MS = 6h
MAX_TRACKED_LEDGERS = 512

ToolReplayBudgetDecision {
  mode: "preview" | "reference_only"
  trimmed: boolean
  trimReason: "max_replay_chars" | "max_replay_items" | null
  replayChars, totalReplayChars, maxReplayChars,
  totalReplayItems, maxReplayItems
}
```

Lógica (`tool-replay-budget-ledger.ts:85-132`): cada vez que el harness va a *replayar* un tool result al modelo, llama `consumeToolReplayBudget({ledgerKey, replayChars})`. Si la suma cruza `maxReplayChars` **o** `maxReplayItems`, el modo bascula a `reference_only` (se manda un puntero — `full_state_path` — en lugar del payload). El ledger se prune por TTL y por tamaño (LRU implícito vía `touchedAt`).

#### Patrón clave del catálogo (`tool-result-budget.ts:1-16`):

```
TOOL_RESULT_PREVIEW_TEXT_MAX_CHARS = 8000          // genérico
TOOL_RESULT_PREVIEW_TEXT_TRIM_THRESHOLD_CHARS = 12000  // histéresis
BROWSER_GET_STATE_TEXT_MAX_CHARS = 1500            // específico
BROWSER_GET_STATE_ELEMENTS_MAX = 20
BROWSER_GET_STATE_MEDIA_MAX = 12
TERMINAL_EVENTS_PREVIEW_MAX = 40
TERMINAL_EVENT_PREVIEW_TEXT_MAX_CHARS = 1200
SCRATCHPAD_CONTENT_PREVIEW_MAX_CHARS = 12000
SKILL_TEXT_PREVIEW_MAX_CHARS = 12000
```

Nótese la doble cota: `MAX_CHARS` (corte real) y `TRIM_THRESHOLD_CHARS` (umbral con histéresis — evita el corte de payloads apenas por encima del límite, ver `clipTextByThreshold` en `tool-result-preview.ts:73-82`).

#### Patrón clave del shaper (`tool-result-preview.ts:783-813`):

```
shapeCapabilityToolResultPayload(toolId, payload, ...)
  switch toolId
    browser_get_state -> shapeBrowserGetState (paginación: elements_offset, has_more, next_elements_offset)
    browser_screenshot -> escribe base64 a disco -> file_path + size_bytes
    web_search -> recorta + spillover full_text_path
    skill -> recorta skill_block + text + spillover full_result_path
    terminal_session_* -> mantiene events[:40] + next_after_sequence + remaining_event_count
    holaboss_scratchpad_read -> recorta + source_file_path
```

Cada shaper inyecta `_preview: {mode, tool_id, truncated, spilled, spillover_paths}` en la respuesta, así el modelo *sabe* que hay un puntero al payload completo y puede pedirlo si lo necesita.

### 1.2 luum — superficie equivalente

Buscado:

```
grep -rn "result-management\|truncate" hooks/ scripts/ packages/
find . -name "*budget*"
```

Encontrado:

- `hooks/result-truncator.sh` (184 líneas) — PostToolUse genérico sobre Bash.
- `rules/result-management.md` (133 líneas) — doc + configuración `result_truncation` en `cognitive-os.yaml:548-559`.
- `lib/smart_truncator.py` (620 líneas) — `smart_truncate(command, output, max_chars=5000)` con head/tail split.
- `lib/context_budget.py` (178 líneas) — ADR-186 4-layer (static/turn/user/cache) en **tokens estimados** (`len(text)//4`), no en chars; aplica a **hook outputs** vía `filter_hook_output`, no a tool results.

La configuración relevante (`cognitive-os.yaml:548-559`):

```yaml
result_truncation:
  enabled: true
  max_chars: 5000      # global, sin discriminar por tool
  head_chars: 2000
  tail_chars: 1000
  never_truncate_patterns: ["FAIL","ERROR","panic","PASS","coverage:"]
```

### 1.3 Delta concreto

| Dimensión | holaOS | luum |
|---|---|---|
| Política por tool | 6 tools con presupuesto propio + paginación | 1 política Bash, agnóstico de qué comando es |
| Acumulación cross-tool | Sí (ledger sesión, 24K chars / 8 items) | **No existe**: dos calls de 5K cada uno ven el budget desde cero |
| TTL del acumulador | 6h con prune LRU | N/A |
| Modo `reference_only` | Sí — punteros a `workspace/tool-results/...` | **No**: una vez truncado, el payload original se pierde |
| Histéresis (TRIM vs MAX) | Sí, dos cotas (12K trigger / 8K corte) | No, un único corte 5K |
| Negociación por header | Sí, `x-holaboss-tool-result-mode: preview/default` | N/A |
| Métrica observable | `_preview.truncated/spilled/spillover_paths` en payload | `truncation-events.jsonl` (post-hoc, no observable por el modelo) |

**Insight crítico**: luum trunca **sin memoria**. Si en una sesión un agente hace `grep gigante`, luego `find gigante`, luego `cat gigante`, cada uno se corta en 5K y todos los recortes terminan en el contexto del modelo. holaOS detectaría que el modelo ya consumió 24K de replay y devolvería `reference_only` para los siguientes — manteniendo el archivo en disco accesible.

### 1.4 Plan de adopción clean-room (B1)

#### Archivos a crear

- `lib/tool_result_ledger.py` — implementación python del acumulador. API:
  ```
  consume(session_id, tool_id, payload_chars) -> Decision(mode, trimmed, trim_reason, totals)
  reset(session_id=None)
  prune(now_epoch) -> None   # TTL + LRU
  ```
  Estado en `.cognitive-os/runtime/tool-replay-ledger.json` (atómico via tmp+rename); o RAM-only por sesión con sync periódico.
- `lib/tool_result_budget.py` — catálogo de límites por tool_id (dataclass, mismo shape que holaOS).
- `lib/tool_result_preview.py` — shapers per-tool: `bash`, `grep_results`, `read_file`, `web_search`, `mcp_engram_search`. Cada uno con dos cotas (max + trim_threshold).
- `hooks/tool-result-shaper.sh` — PostToolUse que reemplaza/complementa `result-truncator.sh`. Lee tool_id desde el evento PostToolUse, despacha al shaper, escribe spillover a `.cognitive-os/runtime/tool-results/<session>/<tool>/<ts>.txt`, devuelve preview + `full_result_path`.

#### Archivos a modificar

- `cognitive-os.yaml`: extender `result_truncation` con sub-bloque `per_tool:` (mapa tool_id → {max_chars, trim_threshold_chars, max_items}). Mantener `max_chars` global como fallback.
- `rules/result-management.md`: documentar modos `preview` y `reference_only`, sección de spillover.
- `hooks/result-truncator.sh`: marcar deprecated o reducir a fallback cuando `per_tool` no aplica.

#### Integración

- `scripts/orchestrator.py` / `lib/dispatch.py`: cuando el dispatcher inyecta tool outputs en el prompt del próximo turno, consultar `lib/tool_result_ledger.consume(...)`. Si retorna `reference_only`, emitir el preview con puntero en lugar del payload.
- Metric: append a `.cognitive-os/metrics/tool-result-ledger.jsonl` (campos: session_id, tool_id, mode, trimmed, totals, spilled, path).

#### Estimación

| Item | LOC | Días |
|---|---:|---:|
| `tool_result_ledger.py` + tests | ~200 | 0.5 |
| `tool_result_budget.py` (catálogo) | ~60 | 0.1 |
| `tool_result_preview.py` (3 shapers iniciales: bash, grep, read) | ~250 | 0.7 |
| `hooks/tool-result-shaper.sh` | ~120 | 0.3 |
| Integración dispatch + cognitive-os.yaml + docs | ~150 | 0.4 |
| Tests integración + chaos (LRU, TTL, corrupted state) | ~250 | 0.5 |
| **Total B1** | **~1030** | **~2.5 días** |

### 1.5 Tradeoffs B1

- **TTL muy alto (>12h)**: el ledger persiste estado de sesiones que el modelo ya no recuerda → bloqueo artificial de replays legítimos en sesiones nuevas que reusan el mismo `session_id`. holaOS mitiga con `pruneExpiredLedgers` cada `consume`.
- **TTL muy bajo (<1h)**: pierde el efecto acumulador justamente cuando un agente está iterando largo sobre el mismo dominio. Recomendado: **6h** (igual que holaOS), parametrizable en yaml.
- **`MAX_TRACKED_LEDGERS` muy bajo**: en deploys multi-tenant podríamos perder ledgers activos por LRU. holaOS usa 512; luum tiene ~10 sesiones concurrentes max (per `cognitive-os.yaml:sessions.max_concurrent`), así que 64 es suficiente.
- **`max_replay_chars` global vs por agente**: holaOS no diferencia. Para luum, si un sub-agent corre 30 min con su propio session_id, va a tener su propio ledger — bueno. Si comparte session_id con el padre, hay riesgo de saturación cruzada. Recomendación: ledgerKey = `{session_id}:{agent_id}` opcional.

---

## 2. Feature B2 — Session Checkpoint con Context-Reserve Ratio

### 2.1 holaOS — superficie

Archivo único masivo: `runtime/api-server/src/session-checkpoint.ts` (991 líneas).

#### Patrón clave de decisión (`session-checkpoint.ts:305-319`):

```
PI_COMPACTION_CONTEXT_RESERVE_RATIO = 0.5

shouldQueueSessionCheckpoint(contextUsage) -> bool
  reserveTokens = ceil(contextWindow * 0.5)
  return tokens > contextWindow - reserveTokens
  # i.e. dispara cuando ya consumiste > 50% del window
```

La métrica entra como `PiContextUsage { tokens, contextWindow, percent }` — **medición real**, no proxy por tool-call count. holaOS la recibe del runtime del modelo (pi-coding-agent).

#### Patrón clave de orquestación (`session-checkpoint.ts:388-436`):

```
enqueueSessionCheckpointJob({...}):
  idempotencyKey = `session_checkpoint:{sessionId}:{harnessSessionId}:{leafId}`
  if exists -> wake worker, return existing
  else -> enqueuePostRunJob(payload={
    base_harness_session_id, base_session_fingerprint,
    base_leaf_id, base_latest_compaction_id, context_usage
  })
```

La compactación se hace **fuera del turn loop** en un worker (`processSessionCheckpointJob`, líneas 750-988). El worker:

1. Vuelve a chequear el threshold (puede haber cambiado).
2. Verifica `runtimeState.status !== "BUSY"` (deferred_busy).
3. Verifica que la `harnessSessionId` del binding no haya cambiado (binding_changed).
4. Verifica `canMergeCheckpointIntoLiveSession` — el `leafId` + `latestCompactionId` deben coincidir (merge_guard_failed).
5. Copia el session file a un snapshot (`snapshotSessionPath`).
6. Spawn child process `compact-pi-session` con timeout 0 (sin límite).
7. Re-verifica el guard.
8. `appendSnapshotCompactionToLiveSession` — append al branch del session_file en vivo.

#### Taxonomía de outcomes (`session-checkpoint.ts:42-53`):

```
skipped_below_threshold | deferred_busy | binding_changed |
session_missing | merge_guard_failed | not_compacted |
merge_failed | soft_provider_422 | merged |
merged_without_boundary | error
```

Cada outcome se persiste con `recordSessionCheckpointResult` en el job payload, para retry/observabilidad.

### 2.2 luum — superficie equivalente

Buscado:

```
grep -rn "context-management\|compactation\|compaction" hooks/ scripts/
grep -A 6 "context_budget:" cognitive-os.yaml
```

Encontrado:

- `rules/context-management.md` (88 líneas): heurística **por tool-call count** (15/50/70/85%) con instrucciones para el modelo, **no medición real del context window**.
- `hooks/pre-compaction-flush.sh` (41 líneas): PreCompact hook, sincrónico, *reactivo* (corre cuando la harness ya decidió compactar). Llama `AnchoredSummarizer.auto_save` y emite un mensaje al agente.
- `lib/context_budget.py`: ADR-186 4-layer, mide **outputs de hooks**, no el turn completo del modelo. No tiene noción de `contextWindow`.
- `lib/context_budget_monitor.py`, `lib/session_budget.py`, `lib/token_budget_monitor.py`: monitores que generan reportes post-hoc; tampoco disparan compactación.
- `hooks/context-budget-meter.sh`, `hooks/token-budget-monitor.sh`, `hooks/context-watchdog` (referido en rules): los watchdogs emiten warnings, no orquestan compactación.

Configuración relevante (`cognitive-os.yaml:170-176`):

```yaml
context_budget:
  static_max_tokens: 4000      # preamble
  turn_max_tokens: 8000        # per tool-use round
  user_max_tokens: 12000       # accumulated user-facing
  cache_max_tokens: 32000      # MCP/engram
```

### 2.3 Delta concreto

| Dimensión | holaOS | luum |
|---|---|---|
| Señal de disparo | `tokens > contextWindow * 0.5` (medición real del modelo) | Heurística count-based o trigger nativo de la harness (PreCompact) |
| Reserve ratio | Explícito, hardcoded 0.5 (= compacta cuando llenaste 50%) | **No existe el concepto** |
| Mecanismo | Job queue persistente + worker async | Hook sincrónico oportunista |
| Idempotencia | `idempotency_key` por leaf+session | Best-effort (corre cada vez que la harness invoca PreCompact) |
| Guard de race condition | `leafId` + `latestCompactionId` + `harnessSessionId` binding | Ninguno (la harness garantiza no-concurrencia) |
| Snapshot + rollback | Sí (`snapshotSessionPath` + `maybeDeleteFile`) | No |
| Taxonomía outcomes | 11 outcomes enumerados | 1 (corrió o no corrió) |
| Persistencia del resultado | `RuntimeStateStore.updatePostRunJob({payload:{checkpoint_result}})` | `mem_session_summary` opcional |
| Soft-fail handling | `soft_provider_422` detectado y degradado a warning Sentry | N/A |

**Insight crítico**: luum **no decide cuándo compactar**, depende de la harness anfitriona (Claude Code) para emitir PreCompact, y entonces *reacciona*. holaOS **decide proactivamente** porque mide. Esto significa que luum no puede compactar antes de que el provider empiece a recortar, mientras que holaOS sí (con margen del 50%).

### 2.4 Plan de adopción clean-room (B2)

Honestidad: B2 requiere infraestructura que luum **no tiene** (job queue persistente con leases). Hay dos rutas:

#### Ruta A — Adopción completa (recomendada para 0.30+)

Archivos a crear:

- `lib/context_reserve_meter.py` — wrap del cálculo `should_queue_checkpoint(usage)` clean-room. API:
  ```
  PiContextUsage = dataclass(tokens: int, context_window: int, percent: float)
  should_queue_checkpoint(usage, reserve_ratio=0.5) -> bool
  ```
- `lib/checkpoint_queue.py` — job queue minimal en SQLite (`.cognitive-os/runtime/checkpoint-queue.db`). Schema: `(job_id, session_id, leaf_id, latest_compaction_id, status, idempotency_key, payload, claimed_at, lease_ttl)`. Idempotency via UNIQUE constraint.
- `scripts/checkpoint_worker.py` — daemon que poll-lockea jobs y ejecuta compactación. Puede correr como service via `cosd` (ya existe el mecanismo).
- `lib/session_compactor.py` — encapsula la lógica de compactación real: snapshot del transcript, summarize via opus, append al state actual con guard.

Archivos a modificar:

- `hooks/pre-compaction-flush.sh`: en lugar de bloquear el turn, **encolar** el job si el threshold ya está cerca y dejar que el worker lo procese.
- `cognitive-os.yaml`: nueva sección
  ```yaml
  context_reserve:
    reserve_ratio: 0.5          # spec del patrón
    poll_interval_ms: 100
    max_in_flight_jobs: 4
    lease_ttl_seconds: 300
  ```
- `lib/context_budget_monitor.py`: integrar lectura de `tokens/context_window` reportados por `lib/llm_dispatch.py` (si llm-dispatch.jsonl los registra) o por la harness.

#### Ruta B — Pragmática (recomendada para 0.29.x)

Aplicar **solo** el patrón `should_queue_checkpoint` sincrónicamente dentro de `hooks/pre-compaction-flush.sh`:

- Leer último `tokens/context_window` de `llm-dispatch.jsonl` (donde ADR-049 los registra por turn).
- Si ratio actual > `1 - reserve_ratio` (0.5), correr `AnchoredSummarizer` + `mem_session_summary` **antes** de que la harness empiece a recortar.
- No async, no queue, pero ya tenemos la *medida real* en lugar de la heurística.

#### Integración

Tanto A como B requieren:

- `lib/dispatch.py`: emitir `context_usage` en cada turn output (tokens_in/out → ratio). Probablemente ya lo emite — auditar `llm-dispatch.jsonl`.
- `scripts/orchestrator.py`: en cada turn-loop iter, pasar `context_usage` al meter; si excede, abrir checkpoint job (A) o spawn flush sync (B).

#### Estimación

| Variante | LOC | Días |
|---|---:|---:|
| **B (pragmática)**: meter + integración pre-compaction + tests | ~300 | 0.8 |
| **A (completa)**: meter + queue SQLite + worker daemon + cosd integration + tests | ~1500 | 4.5 |

Recomendación: **B en sprint actual, A en backlog 0.30**.

### 2.5 Tradeoffs B2

- **`reserve_ratio` muy alto (>0.6)**: compacta demasiado pronto — el modelo pierde contexto reciente útil para razonar. Para tareas largas (SDD apply de 20 archivos), esto es desastroso: la compactación a 40% borra los specs/design recién leídos.
- **`reserve_ratio` muy bajo (<0.3)**: compacta tarde — el provider empieza a evict-ear antes de que termine el snapshot+summarize, y obtenemos `soft_provider_422` o peor. holaOS justamente codifica el outcome `soft_provider_422` porque le pasó.
- **0.5 hardcoded** (holaOS) es prudente pero asume `context_window` reportado correctamente. Para Claude Max (200K, 1M con flag) vs Sonnet (200K), el reserve absoluto cambia drásticamente: 0.5 × 1M = 500K tokens de reserva, lo que es excesivo. **Sugerencia para luum**: `reserve_ratio` configurable + tope absoluto `max_reserve_tokens` (e.g. 60K).
- **Idempotencia por `leafId`**: si tu storage de sessions no tiene noción de leaf (tree de compactaciones), tendrás que inventarla. luum usa `.cognitive-os/sessions/<session_id>/` plana — habría que introducir un `leaf_id` derivado del hash del último checkpoint para que el guard funcione. Esto es **el costo escondido** de la Ruta A.

---

## 3. Ahorro de costo proyectado

Análisis grueso, con datos hipotéticos hasta que `llm-dispatch.jsonl` sea procesado:

### B1 — Tool result ledger

Supuesto: en una sesión SDD típica de 80 tool-calls, ~25% son lecturas grandes (Read de archivos >200 líneas, Grep amplios, Bash con find/cat de logs). Sin ledger:

- Cada Read/Grep grande aporta ~5K chars truncados ≈ 1.25K tokens → 20 calls × 1.25K = **25K tokens/sesión** de payload en context.
- Con ledger (24K chars cap = 6K tokens), después del ~5to call entra modo `reference_only`: 5×1.25K + 15×0.05K (puntero) = 6.25K + 0.75K = **7K tokens/sesión**.
- **Ahorro estimado**: 18K tokens/sesión, ~72% del payload-replay.

Sonnet @ ~$0.003/Ktok input → **$0.054/sesión × 100 sesiones/mes = $5.4/mes**. Pequeño en dólares directos, **enorme en headroom** (evita compactaciones tempranas).

### B2 — Checkpoint con reserve ratio

Sin medición real, las compactaciones de luum suelen dispararse al borde (90%+), generando:
- 1 compaction emergency call (opus, ~10K tokens in + 2K out) = ~$0.20.
- Pérdida de contexto que fuerza re-reads en la siguiente sesión = ~5-10K tokens extra = $0.03.

Con reserve_ratio 0.5:
- 1 compaction proactiva (sonnet posible, ~6K in + 1K out) = ~$0.018.
- Sin pérdida.

**Ahorro: ~$0.21 por compactación**. Si una sesión SDD-apply compacta 2-3 veces, ahorro ~$0.5/sesión.

**Combinado**: ~$0.55 × 100 sesiones = **$55/mes** + drásticamente menos *out-of-context* failures. ROI principal es **calidad y completitud**, no dinero.

---

## 4. Tradeoffs globales (TTL, reserve, granularidad)

| Parámetro | Muy alto | Muy bajo | Recomendación luum |
|---|---|---|---|
| `ledger_ttl_hours` | Stale data, bloqueo artificial entre sesiones | Pierde acumulador en sesiones largas (>4h) | **6h** (igual holaOS), exponer en yaml |
| `max_replay_chars` (per session) | Permite saturación, hace inútil el ledger | Sobre-bloquea, todos los replays son `reference_only` | **24K chars** (~6K tokens), igual holaOS |
| `max_replay_items` | Mucho ruido cross-tool | Bloquea iteración legítima (5to grep ya es referencia) | **8 items**, **revisar** según data real |
| `reserve_ratio` | Compactación temprana, pérdida de contexto reciente | Compactación tardía, riesgo de provider eviction | **0.5** con cap `max_reserve_tokens=60K` |
| `per_tool` granularity | Mantener N catálogos custom | Pérdida de info en payloads chicos | Empezar con 3 tools (bash, grep, read), expandir según métrica |
| Spillover paths TTL | Disco crece | Modelo pide ref y archivo ya no está | **24h** (sesión + buffer) con limpieza en `cleanup_on_exit` |

---

## 5. Recomendación final

**Prioridad de adopción**:

1. **B1 — Tool result ledger (clean-room)**: **adoptar en 0.29.x**. ROI alto, bajo riesgo, ~2.5 días. Sustituye/extiende `result-truncator.sh` con políticas per-tool y acumulador cross-tool. Habilita observabilidad mediante `_preview` injection que el modelo lee. **Sin esto, las sesiones largas seguirán saturándose por replay redundante**.

2. **B2 — Ruta pragmática (`should_queue_checkpoint` sync)**: **adoptar en 0.29.x**. ~0.8 días. Sustituye la heurística count-based de `rules/context-management.md` por medición real de `tokens/context_window` leída de `llm-dispatch.jsonl`. Disparo en 50% (configurable) con tope absoluto.

3. **B2 — Ruta completa (job queue async)**: **backlog 0.30+**. ~4.5 días + diseño de `leaf_id`/`latest_compaction_id` en sessions. Solo justifica el costo si:
   - Las compactaciones se vuelven cuello de botella latencia (>10s).
   - Se necesita compactar en background mientras el modelo sigue respondiendo (capacidad que la harness Claude Code no expone hoy).
   - Hay > 10 sesiones concurrentes regularmente.

**Riesgos clean-room a vigilar**:
- No copiar nombres `consumeToolReplayBudget`, `shouldQueueSessionCheckpoint`, ni la constante `0.5` aislada (usar `RESERVE_RATIO = 0.5` con justificación documentada propia).
- No copiar la taxonomía de outcomes literal — derivar la nuestra desde nuestros casos de fallo reales (`audit-trail` + `error-learning.jsonl`).
- No copiar las constantes específicas de tool (`BROWSER_GET_STATE_TEXT_MAX_CHARS = 1500` etc.) — re-calibrar contra nuestra propia distribución de outputs.

**Bloqueante para B2-A**: necesitamos confirmar que la harness (Claude Code / Codex) expone `context_usage` por turn. Si solo expone count, B2-A queda con la misma señal que la heurística actual; en ese caso recomendar Ruta B siempre.

---

## 6. Referencias

- holaOS: `runtime/harnesses/src/tool-replay-budget-ledger.ts:1-141`
- holaOS: `runtime/api-server/src/tool-result-budget.ts:1-16`
- holaOS: `runtime/api-server/src/tool-result-preview.ts:1-813`
- holaOS: `runtime/api-server/src/session-checkpoint.ts:1-991`
- luum: `lib/context_budget.py`, `lib/smart_truncator.py:80`, `lib/budget_calculator.py`
- luum: `rules/result-management.md`, `rules/context-management.md`
- luum: `hooks/result-truncator.sh`, `hooks/pre-compaction-flush.sh`
- luum: `cognitive-os.yaml:170-176` (context_budget), `cognitive-os.yaml:548-559` (result_truncation)
- ADRs relacionadas: ADR-038 (4-layer budget), ADR-049 (LLM dispatch), ADR-186 (budget enforcement)
- Annex parent: `docs/research/holaos-comparison-2026-05-10.md`
