---
title: "Anexo G — Hallazgos sorpresa: Capability envelope + Unified work queue"
date: 2026-05-11
annex: G
parent: holaos-comparison-2026-05-10.md
status: research-deep-dive
research_only: true
source_repo: /tmp/holaOS-investigation
license_constraint: "BSL-like — patrón-only, clean-room (ver Anexo F)"
scope: project
type: discovery
---

# Anexo G — Hallazgos sorpresa: Capability envelope + Unified work queue

> Companion a `holaos-comparison-2026-05-10.md` y profundización del Anexo E §Pattern 2 y §Pattern 6.
> Este anexo NO repite el análisis del E — lo profundiza con mapping concreto a paths luum,
> interfaces Python propuestas, y planes de adopción clean-room.

---

## §1. Resumen ejecutivo

El top-10 inicial del estudio holaOS se concentró en features visibles del runtime API: grants
HMAC, writeback workers, session compaction con context-reserve, y similares. Dos patrones
cross-cutting pasaron inadvertidos hasta el análisis arquitectónico del Anexo E porque no son
features puntuales sino **infraestructura de plomería** que atraviesa todo el sistema.

El primero es el **capability HTTP result envelope** (`capability-http.ts:197-243`): una función
que serializa el resultado de cualquier tool call y, si supera 32 KB, lo reemplaza por un sobre
compacto con preview, metadata y puntero al payload real. Es ortogonal a las features de control
del runtime y por eso se pasó por alto — no "hace" nada visible, sólo evita que la ventana de
contexto del modelo se sature con blobs de JSON. Valor estimado: **1-2 días de implementación,
impacto inmediato**.

El segundo es la **unified leased work queue** (`queue-worker.ts`): un worker que implementa
claim/lease/heartbeat/recovery sobre cualquier item de trabajo. luum hoy tiene **8 módulos de
queue dispersos** cubriendo parcialmente las mismas preocupaciones (prioridad, reintentos, DLQ,
rate-limit, mutación de archivos, merge serializado, solicitudes de usuario, drenaje de slots).
La consolidación es el **mayor engineering win individual** identificado en todo el estudio, al
costo de mayor complejidad de migración.

Ninguno de los dos apareció en el top-10 porque ambos son patrones *transversales*: no resuelven
un dominio acotado sino que son primitivas sobre las que se construyen otros patrones.

---

## §2. Feature G1 — Capability HTTP result envelope

### §2.1 Código holaOS (referencia mínima — clean-room)

Archivo: `runtime/harnesses/src/capability-http.ts`, líneas 197-243 (fragmento representativo):

```typescript
// capability-http.ts — líneas 114-115 (constantes)
const DEFAULT_COMPACT_TOOL_RESULT_THRESHOLD_BYTES = 32 * 1024;  // 32 KB
const DEFAULT_COMPACT_TOOL_RESULT_PREVIEW_BYTES = 8 * 1024;     // 8 KB preview

// líneas 197-243 — función principal
export function formatCapabilityToolResultForModel(
  payload: unknown,
  options?: { thresholdBytes?: number; previewBytes?: number },
): FormattedCapabilityToolResult {
  const serialized = formatCapabilityToolResult(payload);
  const serializedBytes = utf8ByteLength(serialized);
  const thresholdBytes = options?.thresholdBytes ?? DEFAULT_COMPACT_TOOL_RESULT_THRESHOLD_BYTES;
  if (serializedBytes <= thresholdBytes) {
    return { text: serialized, compacted: false, serializedBytes, modelTextBytes: serializedBytes };
  }
  const envelope = {
    tool_result_format: "compact_envelope",
    status: "truncated",
    serialized_bytes: serializedBytes,
    summary: topLevelPayloadSummary(payload),   // shape summary, no content
    preview,                                     // first 8 KB
    raw_result: { available: true, stored_in: "tool_result.details.raw" },
    ...(isRecord(payload) && typeof payload.ok === "boolean" ? { ok: payload.ok } : {}),
  };
  return { text: JSON.stringify(envelope, null, 2), compacted: true, ... };
}
```

> NOTA clean-room: las líneas anteriores son una cita de referencia reducida. La implementación
> luum (`lib/tool_result_envelope.py`) se escribirá en Python con interfaz diferente.

### §2.2 Lectura conceptual

El patrón tiene tres componentes:

**Threshold 32 KB.** Si el payload serializado es ≤ 32 768 bytes, pasa sin modificación. El valor
32 KB no es arbitrario: es aproximadamente el tamaño donde un JSON response empieza a consumir
una fracción no trivial de una ventana de contexto de 200K tokens (1 token ≈ 4 bytes → 32 KB ≈
8 000 tokens, ~4% de Claude Sonnet). Para Claude Code con contextos de 200K la heurística es
válida, aunque el threshold óptimo puede diferir (ver §2.6 UNSURE).

**`compact_envelope`.** Cuando el payload excede el threshold, la función *no descarta* el
resultado — lo reemplaza por un sobre estructurado que contiene: (a) los primeros 8 KB como
preview para que el modelo vea el comienzo del resultado, (b) un `topLevelPayloadSummary` que
lista las claves de primer nivel con sus tipos (sin valores), y (c) un puntero
`raw_result.stored_in` que indica dónde está el payload completo si el modelo lo necesita en un
tool-call subsecuente. Si el payload original tenía un campo `ok: boolean`, éste se eleva al
sobre para que el modelo pueda evaluar éxito/fallo sin leer el payload.

**Metadata preservada.** El sobre incluye `serialized_bytes` (tamaño real) y `model_text_bytes`
(tamaño del sobre). El caller puede usar estos dos valores para contabilizar el ahorro en el
presupuesto de contexto.

### §2.3 Mapping a luum

Los puntos de aplicación en luum son:

- **`lib/agent_runner.py`** — ejecuta tool calls y concatena resultados al contexto. Es el lugar
  natural para interceptar el resultado antes de añadirlo al historial de conversación.
- **`lib/dispatch_helper.py`** — construye el payload que va al modelo en cada turno. Si
  `agent_runner` no aplica el envelope, `dispatch_helper` puede hacerlo como segunda línea.
- **`hooks/result-truncator.sh`** (symlink a
  `packages/verification-audit/hooks/result-truncator.sh`) — hook post-ejecución que ya trunca
  resultados grandes. Actualmente opera con lógica propia; podría delegar al nuevo módulo Python
  para consistencia.
- **`lib/smart_truncator.py`** — módulo de 20 833 bytes que ya implementa head/tail truncation.
  Actualmente usado en `lib/openai_compatible_agent_loop.py:267,290`. El envelope lo
  complementaría (ver §2.5).

### §2.4 Plan de adopción clean-room

Nuevo archivo: **`lib/tool_result_envelope.py`**

Interfaz propuesta (Python, distinta a las firmas TS del original):

```python
from dataclasses import dataclass
from typing import Any

ENVELOPE_THRESHOLD_BYTES: int = 32 * 1024   # ajustable por caller
ENVELOPE_PREVIEW_BYTES: int = 8 * 1024

@dataclass
class EnvelopedResult:
    text: str              # lo que va al modelo
    compacted: bool        # True si se aplicó el sobre
    original_bytes: int    # tamaño del payload serializado
    model_bytes: int       # tamaño del texto entregado al modelo

def wrap_tool_result(
    payload: Any,
    *,
    threshold_bytes: int = ENVELOPE_THRESHOLD_BYTES,
    preview_bytes: int = ENVELOPE_PREVIEW_BYTES,
) -> EnvelopedResult:
    """Serializa el resultado de un tool call.
    Si supera threshold_bytes, produce un compact_envelope.
    El payload completo se pasa en raw_payload al caller para
    almacenamiento side-channel si se desea.
    """
    ...

def top_level_summary(payload: Any) -> dict[str, str]:
    """Retorna {key: type_name} para claves de primer nivel."""
    ...
```

Integración con dispatch: `lib/agent_runner.py` importa `wrap_tool_result`, lo aplica después de
cada tool call, y pasa `EnvelopedResult.text` al historial. Si `compacted=True`, puede loguear el
ahorro en `agent-heartbeat.jsonl` como `tool_result_compacted: true`.

### §2.5 Comparación con Anexo B (tool-replay budget ledger)

El Anexo B describe un presupuesto de repetición de tool calls: limita cuántas veces el mismo
tool puede ser invocado en una sesión para evitar loops de reintentos costosos.

**Son ortogonales y se componen.** El mecanismo del Anexo B opera sobre *repeticiones del mismo
tool a lo largo del tiempo* (dimensión temporal). El envelope G1 opera sobre *el tamaño de un
único resultado* (dimensión espacial). Un resultado grande de un tool que se llama por primera
vez todavía necesita el envelope. Un tool llamado 5 veces con resultados pequeños todavía necesita
el presupuesto B. Cuando ambos están activos: B decide si el tool se ejecuta; G1 decide cómo se
serializa su resultado si se ejecuta.

La composición natural es: B actúa en `lib/agent_runner.py` como gate antes de la ejecución;
G1 actúa en el mismo lugar como post-procesador del resultado.

### §2.6 Esfuerzo y riesgo

- **Esfuerzo**: 1-2 días (nuevo módulo Python ~150 líneas, integración en `agent_runner.py`,
  tests unitarios con payloads sintéticos de distintos tamaños).
- **Riesgo**: bajo. La función es pura (input → output, sin side effects), fácilmente testeable,
  y completamente reversible (se puede desactivar con `threshold_bytes=math.inf`).

### §2.7 Recomendación

**Adoptar en 0.29.x como quick win.** Es la intervención de menor esfuerzo / mayor impacto
identificada en el estudio completo. El único prerequisito es decidir el valor de
`threshold_bytes` adecuado para Claude Code (ver §6 UNSURE).

---

## §3. Feature G2 — Unified leased work queue

### §3.1 Inventario de las 8 queue modules existentes en luum

Todas verificadas con `ls -la`. `merge_queue` es symlink a
`packages/agent-coordination/lib/merge_queue.py`.

| # | Path (`lib/`) | Tamaño | Descripción (1 línea) | Concerns solapados |
|---|---------------|--------|-----------------------|--------------------|
| 1 | `work_queue.py` | 160 líneas / 6 414 B | Cola persistente cross-session en `.cognitive-os/work-queue.json`; prioridad, user concerns, sprint backlog | prioridad, persistencia |
| 2 | `request_queue.py` | 137 líneas / 3 378 B | Enqueue de mensajes de usuario que llegan mientras el orchestrator está ocupado; previene pérdidas por compaction | persistencia, FIFO |
| 3 | `dead_letter_queue.py` | 193 líneas / 6 889 B | DLQ para agentes que agotan reintentos; append-only JSONL con soporte de re-enqueue | DLQ, retry, persistencia |
| 4 | `merge_queue.py` | 160 líneas / symlink | Cola serializada de merges de branches; single-writer con `fcntl.flock`; enqueue/dequeue/peek | serialización, mutex, persistencia |
| 5 | `queue_advisor.py` | 726 líneas / 27 198 B | Reordenador heurístico de dispatch queue; scoring por budget, contexto, dependencias, staleness | prioridad, scheduling |
| 6 | `queue_drainer.py` | 539 líneas / 20 114 B | Cola de agentes bloqueados por falta de slots; persistencia en `dispatch-queue.json`; slot-based | slots/concurrencia, persistencia |
| 7 | `file_mutation_queue.py` | 109 líneas / 4 288 B | Serializa escrituras concurrentes al mismo archivo; `threading.Lock` por path resuelto | mutex, serialización |
| 8 | `rate_limit_queue_migration.py` | 93 líneas / 3 513 B | Helper de migración one-shot de formato JSON → JSONL para la rate-limit queue | migración, formato |

**Concerns en overlap visible:** `work_queue` y `request_queue` ambas persisten en JSON con
estructura similar. `dead_letter_queue` y `queue_drainer` ambas rastrean estado de retry/fallo.
`merge_queue` y `file_mutation_queue` ambas implementan exclusión mutua. Ninguna implementa
lease/heartbeat/claim — la garantía de que un item en proceso no sea reclamado por otro worker.

### §3.2 Código holaOS — primitiva lease+heartbeat+claim (referencia mínima)

Archivo: `runtime/api-server/src/queue-worker.ts`, fragmento representativo:

```typescript
// Constantes (líneas 17-20)
const DEFAULT_LEASE_SECONDS = 300;
const DEFAULT_POLL_INTERVAL_MS = 1000;
const DEFAULT_MAX_CONCURRENCY = 2;
const DEFAULT_CLAIM_STALE_HEARTBEAT_MS = 20_000;

// Claim con lease (líneas 216-222)
const claimed = this.#store.claimInputs({
  limit: availableSlots,
  claimedBy: this.#claimedBy,       // "worker-pid-uuid" único por proceso
  leaseSeconds: this.#leaseSeconds,  // claimed_until = now + 300s
  distinctSessions: true,
  excludeSessionIds: blockedSessionIds,
});

// Recovery de claims expirados (líneas 311-368)
// Si heartbeat no se renovó en claimStaleHeartbeatMs → recover
// Si claim_expired Y hay session_checkpoint pendiente → renovar lease
```

> NOTA clean-room: cita reducida para referencia conceptual.

### §3.3 Lectura conceptual — lease semantics

El patrón implementa cuatro garantías que ninguno de los 8 módulos luum provee hoy:

1. **Lease temporal**: al clamar un item, el worker recibe un `claimed_until = now + N segundos`.
   Si el worker muere o cuelga sin renovar, el item queda disponible para re-claim automático.
   Evita items "stuck" en estado CLAIMED indefinidamente.

2. **Heartbeat**: mientras el worker procesa, actualiza periódicamente `heartbeat_at`. El recovery
   loop chequea si el heartbeat es fresco (`now - heartbeat_at <= claimStaleHeartbeatMs`). Si no,
   libera el claim aunque `claimed_until` no haya expirado aún.

3. **Claim ownership**: el campo `claimed_by` incluye `pid + uuid`, lo que permite a múltiples
   workers en el mismo proceso distinguir sus claims y evitar re-procesar items del propio worker.

4. **Idempotency en recovery**: si un claim expiró pero hay un `session_checkpoint` job pendiente,
   el lease se renueva en lugar de liberar, evitando falsos recoveries durante operaciones largas.

La primitiva es **storage-agnostic**: `claimInputs`, `renewInputClaim`, `updateInput`, etc. son
métodos del `RuntimeStateStore` que puede ser SQLite, Redis, o cualquier backend con atomicidad.

### §3.4 Análisis de duplicación — matriz queue × concern

| Module | Prioridad | Retry/DLQ | Lease/Claim | Rate-limit | Mutex/Serial. | Persistencia | Heartbeat |
|--------|-----------|-----------|-------------|------------|---------------|--------------|-----------|
| `work_queue` | ✓ | — | — | — | — | JSON | — |
| `request_queue` | — | — | — | — | — | JSON | — |
| `dead_letter_queue` | — | ✓ | — | — | — | JSONL | — |
| `merge_queue` | — | — | — | — | ✓ (flock) | JSONL | — |
| `queue_advisor` | ✓ (scoring) | — | — | ✓ (budget) | — | — | — |
| `queue_drainer` | ✓ (slots) | partial | — | ✓ (cooldown) | — | JSON | — |
| `file_mutation_queue` | — | — | — | — | ✓ (Lock) | in-memory | — |
| `rate_limit_queue_migration` | — | — | — | — | — | JSON→JSONL | — |
| **holaOS leased queue** | ✓ | ✓ | **✓** | — | ✓ (claim) | SQLite | **✓** |

La columna **Lease/Claim** y **Heartbeat** son vacíos en toda la columna luum: son los gaps
exactos que G2 resuelve.

### §3.5 Plan de consolidación clean-room

Nueva primitiva: **`lib/leased_queue.py`** (~300 líneas).

**Interfaz Python propuesta** (distinta a las firmas TS del original):

```python
from dataclasses import dataclass, field
from typing import Any, Optional
import time, uuid, threading

@dataclass
class QueueItem:
    item_id: str
    payload: Any
    priority: int = 0
    status: str = "QUEUED"          # QUEUED | CLAIMED | DONE | FAILED | DLQ
    claimed_by: Optional[str] = None
    claimed_until: Optional[float] = None   # epoch seconds
    heartbeat_at: Optional[float] = None
    attempt: int = 0
    max_attempts: int = 3
    error: Optional[str] = None

class LeasedQueue:
    """Cola persistente con lease/heartbeat/claim semánticos.
    Backend: JSONL append-only + compaction periódica.
    Thread-safe con threading.RLock.
    """

    def __init__(
        self,
        queue_path: str,
        lease_seconds: int = 300,
        heartbeat_stale_seconds: int = 20,
        max_concurrency: int = 4,
    ): ...

    def enqueue(self, payload: Any, *, priority: int = 0, item_id: str | None = None) -> str:
        """Agrega un item. Retorna item_id."""

    def claim(self, *, worker_id: str | None = None, limit: int = 1) -> list[QueueItem]:
        """Toma hasta `limit` items QUEUED o con lease expirado. Setea claimed_by+claimed_until."""

    def heartbeat(self, item_id: str, worker_id: str) -> bool:
        """Renueva heartbeat_at. Retorna False si el item ya no pertenece a este worker."""

    def complete(self, item_id: str, worker_id: str) -> None:
        """Marca DONE. Libera claim."""

    def fail(self, item_id: str, worker_id: str, error: str) -> None:
        """Incrementa attempt. Si attempt >= max_attempts → DLQ. Sino → QUEUED para retry."""

    def recover_stale_claims(self) -> int:
        """Libera claims con heartbeat vencido o lease expirado. Retorna count."""

    def dead_letter_items(self) -> list[QueueItem]:
        """Lista items en DLQ."""

    def requeue(self, item_id: str) -> bool:
        """Saca un item de DLQ y lo vuelve a QUEUED."""
```

**Plan de migración por waves:**

**Wave 1 — nueva primitiva + 2 queues piloto (2-3 días):**
- Crear `lib/leased_queue.py` con tests completos.
- Migrar `lib/dead_letter_queue.py` como cliente (es la más simple y de menor blast radius).
- Migrar `lib/request_queue.py` como segundo piloto (FIFO puro, fácil de validar).
- Criterio de éxito: tests existentes de ambas queues pasan sin cambios visibles a callers.

**Wave 2 — queues de control plane (1 semana):**
- Migrar `lib/work_queue.py` (cross-session backlog).
- Migrar `lib/queue_drainer.py` (slot-based dispatch).
- `lib/queue_advisor.py` no se migra como queue — es un priorizador, no un storage; se convierte
  en un `Advisor` que recibe `list[QueueItem]` y retorna orden recomendado.

**Wave 3 — queues de infraestructura + deprecación (1 semana):**
- Migrar `lib/merge_queue.py` (requiere verificar compatibilidad con `fcntl.flock` hook externo).
- `lib/file_mutation_queue.py` es especial: usa `threading.Lock` in-memory, no persiste. Se
  integra como modo `in_memory=True` en `LeasedQueue` o se mantiene separado.
- `lib/rate_limit_queue_migration.py` se depreca directamente (es un helper de migración
  one-shot ya completado).
- Marcar las 7 módulos originales migrados como `@deprecated`.

### §3.6 Riesgos específicos

**Alta blast radius.** 8 módulos, ~1 957 líneas de código de queue hoy. Los consumers incluyen
hooks en bash (`setup-git-hooks.sh`, `completion-gate.sh`) que leen archivos JSON directamente.
Un cambio en la estructura de persistencia sin backward-compat rompería hooks sin test de
integración explícito.

**Migration drift.** Si Wave 1 y Wave 2 se hacen en sprints distintos, puede haber un período
donde `dead_letter_queue` usa el nuevo backend pero `work_queue` usa el viejo. Los hooks que
consultan ambos pueden ver inconsistencias en el estado global.

**Regresiones en hooks.** `packages/agent-lifecycle/hooks/review-spawner.sh` y
`packages/quality-gates/hooks/completion-gate.sh` (ambos modificados en el branch actual según
`git status`) son consumers de queue state. Deben estar en el test plan de cada wave.

**Plan de mitigación:**
- Cada wave entrega un wrapper de compatibilidad que mantiene el mismo JSON format de salida
  para callers bash, delegando internamente al nuevo backend.
- Tests de integración existentes en `tests/integration/` corren en CI entre waves.
- Wave 3 solo inicia cuando Wave 1 y 2 están en `main` y CI verde por 48h.

### §3.7 Esfuerzo y riesgo

- **Esfuerzo**: 2-3 semanas con 3 waves, ~1 semana cada una con holgura para backward-compat.
- **Riesgo**: alto si se hace big-bang (refactor de 8 módulos a la vez); **medio si se hace
  wave-by-wave** con wrappers de compatibilidad y CI entre waves.

### §3.8 Recomendación

**Priorizar como sprint dedicado en 0.30+.** No mezclar con otras adopciones del estudio
holaOS — la blast radius requiere foco total. El trigger ideal es cuando el conteo de bugs
relacionados a queue (lost tasks, stale claims, retry storms) justifique el costo de migración.
Hoy hay deuda de duplicación pero no hay bugs críticos reportados — es engineering debt, no
incident remediation.

---

## §4. Por qué no estaban en el top-10

El top-10 inicial se construyó revisando features del runtime API de holaOS en secuencia: grants
HMAC, session compaction, writeback workers, capability projections, y similares. Todos esos son
features con un dominio acotado — se pueden adoptar de forma independiente sin tocar el resto del
sistema.

El capability envelope (G1) y la unified leased queue (G2) son distintos: no pertenecen a un
dominio, *atraviesan todos los dominios*. El envelope es relevante cada vez que cualquier tool
retorna cualquier resultado. La leased queue es relevante cada vez que cualquier componente del
control plane encola cualquier trabajo. Patrones cross-cutting no aparecen cuando se lee el
código feature por feature — solo emergen cuando se hace el análisis arquitectónico que pregunta
"¿qué primitivas faltan a nivel de plataforma?", que es exactamente lo que el Anexo E realizó.
La lección metodológica: el análisis de top-10 inicial debe incluir una pasada explícita de
"¿qué primitivas transversales usa holaOS que nosotros no tenemos?"

---

## §5. Interacciones con otros anexos

**G1 ↔ Anexo B (tool-replay budget ledger)**
Ortogonal, se componen sin conflicto. B opera en la dimensión temporal (¿cuántas veces se llamó
este tool?). G1 opera en la dimensión espacial (¿qué tan grande es este resultado?). En
`lib/agent_runner.py`: B actúa como gate antes de ejecución; G1 actúa como post-procesador del
resultado. Ambos reducen consumo de contexto por caminos independientes.

**G2 ↔ Anexo C (todo state machine)**
El todo state machine es un consumer natural del leased queue: cada item de todo (`pending`,
`in_progress`, `done`) puede ser un `QueueItem` con el estado mapeado a `status`. La transición
`pending → in_progress` corresponde a `claim()`. La transición `in_progress → done` corresponde
a `complete()`. Si el agente que trabaja en el todo muere, el lease expira y otro agente puede
recuperar el item — garantía que el state machine actual no provee.

**G2 ↔ Anexo A (writeback worker)**
El writeback worker (Anexo A) es exactamente el tipo de trabajo de background que se beneficia
de lease semantics: si el worker de writeback cuelga a mitad de una escritura, hoy el estado
queda inconsistente. Con `LeasedQueue`, el item de writeback queda en CLAIMED hasta que el
worker confirma `complete()` o el lease expira y se retoma.

**G1 ↔ Anexo D (snapshot bootstrap)**
El snapshot JSON de contexto (Anexo D) puede crecer si el snapshot incluye resultados de tools
recientes. Si `lib/tool_result_envelope.py` se aplica antes de que los resultados entren al
snapshot, el snapshot se mantiene compacto desde el origen, en lugar de requerir truncation
post-hoc.

---

## §6. UNSURE / HUMAN-CHECK

1. **Las 8 queue modules están verificadas** (`ls -la` exitoso en §3.1), pero las descripciones
   de concerns solapados se basan en lectura de docstrings y primeras líneas, no en auditoría
   exhaustiva de todo el código. Es posible que alguno de los módulos tenga funcionalidad
   adicional no capturada en la matriz §3.4. **Acción recomendada**: antes de Wave 1, hacer una
   lectura completa de `queue_drainer.py` (539 líneas, la más compleja) para validar que la
   interfaz `LeasedQueue` cubre todos sus casos de uso.

2. **El threshold de 32 KB puede no ser óptimo para Claude Code.** holaOS usa el threshold con
   el modelo `pi` (harness propio). Claude Code tiene una ventana de contexto de 200K tokens y
   un pricing diferente. 32 KB ≈ 8 000 tokens ≈ 4% del contexto disponible: puede ser
   demasiado conservador (generando envelopes innecesarios para resultados medianos) o puede ser
   adecuado dependiendo del número típico de tool calls por sesión. **Acción recomendada**:
   medir en producción los percentiles p50/p95 del tamaño de tool results antes de fijar el
   threshold. El módulo `lib/tool_result_envelope.py` debe exponer `ENVELOPE_THRESHOLD_BYTES`
   como configurable para poder ajustarlo sin redeployment.

3. **`lib/rate_limit_queue_migration.py` es un helper de migración one-shot.** Si la migración
   JSON → JSONL ya fue ejecutada en todos los entornos, este módulo puede ser candidato a
   deprecación directa sin necesitar `LeasedQueue`. **Acción recomendada**: verificar si la
   migración se completó y si el archivo `.rate-limit-queue.json` ya no existe en ningún
   entorno antes de incluirlo en Wave 3.
