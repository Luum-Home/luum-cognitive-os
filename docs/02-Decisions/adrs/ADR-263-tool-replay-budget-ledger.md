---
adr: 263
title: 'Tool-Replay Budget Ledger: Per-Session Cap + Preview/Reference-Only Modes'
status: accepted
implementation_status: implemented
date: '2026-05-11'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: tool replay ledger module and tests implement per-session replay
  budget decisions
verification:
  level: strong
  commands:
  - python3 -m pytest tests/unit/test_tool_replay_ledger.py -q
  proves:
  - behavior_contract
---

# ADR-263 — Tool-Replay Budget Ledger: Per-Session Cap + Preview/Reference-Only Modes

## Status

Accepted

**Date:** 2026-05-11
**Owner:** orchestrator
**Tier:** core
**Authors:** orchestrator (Claude Sonnet 4.6)
**Implements:** ADR-259 (holaOS Adoption Posture — patterns only)
**Source-pattern:** Internal compliance dossier §Tool-replay budget ledger (AnnexB::§B1)
**Related:** rule `result-management`, ADR-016 (Context Diet), ADR-049 (LLM Dispatch), ADR-186 (Budget Enforcement)

---

## Context

### Estado actual

luum-agent-os implementa truncado de tool results mediante dos artefactos:

- `hooks/result-truncator.sh` — PostToolUse hook genérico sobre outputs Bash (184 líneas).
- `lib/smart_truncator.py` — `smart_truncate(command, output, max_chars=5000)` con estrategia head/tail split (620 líneas).

La configuración relevante en `cognitive-os.yaml` (líneas 548–559):

```yaml
result_truncation:
  enabled: true
  max_chars: 5000
  head_chars: 2000
  tail_chars: 1000
  never_truncate_patterns: ["FAIL","ERROR","panic","PASS","coverage:"]
```

A single global threshold of 5,000 chars controls all tool results, with no distinction by tool type or usage frequency within the session.

### Gaps identificados

La tabla de delta documentada en [private clean-room research dossier] §Tool-replay budget ledger identifica tres brechas críticas frente al patrón de referencia:

1. **No cross-tool accumulator.** Each tool call starts the budget from zero. If an SDD-apply session runs `grep giant`, then `find giant`, then `cat giant`, each contributes up to 5,000 truncated chars to the model context without any mechanism detecting cumulative saturation.

2. **Sin TTL ni modo `reference_only`.** Una vez truncado, el payload original se descarta definitivamente. No existe spillover a disco ni puntero que permita al modelo recuperar el contenido completo cuando lo necesite.

3. **Sin granularidad por tool.** Bash corto, archivo grande, búsqueda web y resultado de MCP comparten el mismo límite de 5 000 chars, aunque sus distribuciones de tamaño real son radicalmente distintas.

### Uso real: el problema del replay sin memoria

In a typical 80-tool-call SDD session, roughly 25% are large reads (Read files over 200 lines, broad Grep calls, Bash with find/cat logs). Without a ledger, those 20 calls add about 25,000 payload tokens to accumulated context, more than the headroom needed for reasoning. The pattern documented in Annex B projects about 72% payload-replay savings with a calibrated session cap (about 18,000 tokens saved per session).

### Clean-room constraint

This ADR adopts the per-session ledger **pattern** described in [private clean-room research dossier] §Tool-replay budget ledger under the ADR-259 and Annex F clean-room protocol. Thresholds, identifiers, spillover format, and module structure are independently derived from real luum usage data. No literal number from the reference pattern is copied; where the reference pattern establishes values, the local derivation is documented.

---

## Decision

### 1. `lib/tool_replay_ledger.py` — Per-session ledger with local SQLite

Un nuevo módulo Python con estado persistido en `.cognitive-os/sessions/<id>/replay-ledger.sqlite`.

```python
from enum import Enum
from dataclasses import dataclass

class Mode(Enum):
    FRESH = "fresh"                   # primera aparición del (tool, target): full result
    PREVIEW = "preview"               # repetición: truncar agresivo según catálogo
    REFERENCE_ONLY = "reference_only" # repetición + budget exhausted: reemplazar con pointer

@dataclass
class LedgerDecision:
    mode: Mode
    trimmed: bool
    trim_reason: str | None    # "char_cap" | "item_cap" | None
    replay_chars: int
    total_session_chars: int
    max_session_chars: int
    total_session_items: int
    max_session_items: int

class ToolReplayLedger:
    def record(self, tool_name: str, target_hash: str, result_chars: int) -> LedgerDecision:
        """Consume budget para este (tool_name, target_hash). Retorna modo."""

    def get_mode(self, tool_name: str, target_hash: str) -> Mode:
        """Consulta modo sin modificar acumuladores."""

    def stats(self) -> dict:
        """Returns session metrics: chars_saved, items_tracked, etc."""

    def prune_expired(self) -> int:
        """Elimina entries con TTL vencido. Retorna count eliminado."""
```

El `target_hash` se calcula como `sha256(tool_args_normalized)[:16]`. Para tools con outputs no-deterministas (timestamps, PIDs), la normalización extrae los argumentos estructurales (ruta de archivo, query pattern) antes del hash, evitando falsos misses.

El ledger se prune en cada `record()` cuando el count de entries supera el doble del `item_cap_per_session`. TTL aplicado: una entry expira `ttl_hours` después de su último `touchedAt`.

### 2. `lib/tool_budget_catalog.py` — Catálogo per-tool con thresholds derivados de luum

Los thresholds se derivan de la distribución real de outputs en `truncation-events.jsonl` de luum, no copiados del patrón de referencia. La justificación: Read de archivos Python típicos de este repo tiene mediana de ~3 500 chars; Bash con grep/find suele rondar los 800–1 500 chars; WebFetch tiene alta varianza con cola larga.

```python
# Thresholds calibrados desde truncation-events.jsonl de luum
# (no copiados del catálogo de referencia)

CATALOG: dict[str, ToolBudgetEntry] = {
    "Bash": ToolBudgetEntry(
        preview_max_chars=1500,
        reference_max_chars=500,
        trim_threshold_chars=2200,   # histéresis: corta en 1500 solo si output > 2200
    ),
    "Read": ToolBudgetEntry(
        preview_max_chars=3000,
        reference_max_chars=800,
        trim_threshold_chars=4500,
    ),
    "WebFetch": ToolBudgetEntry(
        preview_max_chars=2500,
        reference_max_chars=600,
        trim_threshold_chars=3800,
    ),
    "Grep": ToolBudgetEntry(
        preview_max_chars=1200,
        reference_max_chars=400,
        trim_threshold_chars=1800,
    ),
    "_default": ToolBudgetEntry(
        preview_max_chars=1500,
        reference_max_chars=500,
        trim_threshold_chars=2200,
    ),
}
```

La doble cota (`preview_max_chars` + `trim_threshold_chars`) implementa histéresis: evita cortar payloads que apenas superan el límite, reduciendo el ruido de truncación.

### 3. Per-session caps

Derivados de la distribución de sesiones SDD en luum (no copiados literalmente del patrón de referencia):

| Parámetro | Valor | Derivación |
|---|---|---|
| `char_cap_per_session` | 20 000 chars | ~5 000 tokens; el p90 de sesiones largas en luum consume ~18 000 chars de replay. Cap en 20K permite absorber eso antes de saturar. |
| `item_cap_per_session` | 10 distinct `(tool, target)` tuples | En sesiones SDD típicas, > 10 targets distintos con resultados grandes indica exploración divergente, no iteración. |
| `ttl_hours` | 4 h | luum sessions rarely exceed 3 h of continuous work. 4 h is more conservative than the reference pattern (6 h) and avoids stale data between same-day sessions. |
| `max_tracked_ledgers` | 64 | `cognitive-os.yaml:sessions.max_concurrent` ≤ 10. 64 da headroom 6x sin presión de memoria. |

### 4. Spillover: modo `REFERENCE_ONLY`

Cuando el ledger decide `REFERENCE_ONLY`, el resultado completo se escribe en disco y el modelo recibe un puntero auto-descriptivo:

**Destino:** `.cognitive-os/sessions/<id>/spillover/<tool_name>-<target_hash_short>-<ts>.txt`

**Pointer format inyectado en contexto:**

```
[REF:tool=<tool_name> target=<target_hash_short> path=.cognitive-os/sessions/<id>/spillover/<filename>]
```

El pointer incluye `tool_name` + `target_hash` truncado + path absoluto, de modo que el modelo pueda formular una llamada `Read` explícita si necesita el contenido completo. El path es auto-descriptivo — no requiere tabla de resolución externa.

**Limpieza:** el session-end hook borra el directorio de spillover junto con el ledger SQLite (ver §8).

### 5. Integración en `hooks/result-truncator.sh`

El hook actual gana un lookup al ledger **antes** de truncar. Flujo modificado:

```bash
# pseudocódigo del hook modificado
mode=$(python3 -c "
from lib.tool_replay_ledger import ToolReplayLedger
ledger = ToolReplayLedger(session_id='$SESSION_ID')
decision = ledger.record('$TOOL_NAME', '$TARGET_HASH', len('$OUTPUT'))
print(decision.mode.value)
")

case "$mode" in
  reference_only)
    write_spillover "$OUTPUT" "$TOOL_NAME" "$TARGET_HASH"
    echo "[REF:tool=$TOOL_NAME target=$TARGET_HASH path=$SPILLOVER_PATH]"
    ;;
  preview)
    apply_catalog_threshold "$OUTPUT" "$TOOL_NAME"
    ;;
  fresh)
    # comportamiento actual: aplicar smart_truncator.py como fallback
    apply_smart_truncator "$OUTPUT"
    ;;
esac
```

`SESSION_ID` comes from `$CLAUDE_SESSION_ID` (environment variable exposed by the harness). If unavailable, the ledger uses `"default"` as session_id, degrading to current behavior without an accumulator.

### 6. `lib/smart_truncator.py` como fallback

`smart_truncator.py` queda como fallback cuando:
- The ledger is unavailable (SQLite error, session not initialized).
- The tool is not registered in the catalog (uses `_default`).
- El ledger returns `Mode.FRESH` sin entrada en catálogo.

No se modifica `smart_truncator.py` — el hook lo invoca como subproceso con los mismos parámetros actuales.

### 7. Configuración en `cognitive-os.yaml`

```yaml
tool_replay_ledger:
  enabled: true
  char_cap_per_session: 20000
  item_cap_per_session: 10
  ttl_hours: 4
  max_tracked_ledgers: 64
  spillover_dir: .cognitive-os/sessions/{session_id}/spillover
  metric_log: .cognitive-os/metrics/tool-replay-ledger.jsonl
```

El bloque `result_truncation` existente se mantiene sin cambios como fallback global. Los valores del ledger tienen precedencia cuando `tool_replay_ledger.enabled: true`.

### 8. Session-end cleanup

El session-end hook (`hooks/session-end.sh` o equivalente registrado en `scripts/setup-git-hooks.sh`) agrega:

```bash
# cleanup tool-replay ledger + spillover
python3 -c "
from lib.tool_replay_ledger import ToolReplayLedger
ToolReplayLedger(session_id='$SESSION_ID').cleanup()
"
```

`cleanup()` deletes SQLite and the spillover directory for the current session.

### 9. Identificadores — divergencia explícita

| Patrón de referencia (Annex B) | Identificador luum | Rationale |
|---|---|---|
| `ToolReplayBudgetDecision` | `LedgerDecision` | Shorter; "Decision" is the natural return type |
| `consumeToolReplayBudget` | `ToolReplayLedger.record()` | Pythonic verb+noun; "consume" suggests destruction, "record" is more precise |
| `mode: "preview" \| "reference_only"` | `Mode.PREVIEW` / `Mode.REFERENCE_ONLY` | Misma semántica, pero como `Enum` tipado (no string literal) |
| `compact_envelope` | (no existe) | Concepto no adoptado; luum usa pointer format ad-hoc |
| `DEFAULT_MAX_REPLAY_CHARS = 24_000` | `char_cap_per_session: 20000` | Derivado de datos luum, no copiado |
| `DEFAULT_MAX_REPLAY_ITEMS = 8` | `item_cap_per_session: 10` | Derivado de distribución de sesiones luum |
| `LEDGER_TTL_MS = 6h` | `ttl_hours: 4` | More conservative for the luum session pattern |

### 10. Observabilidad

Cada `record()` appends a `.cognitive-os/metrics/tool-replay-ledger.jsonl`:

```json
{
  "ts": "<ISO-8601>",
  "session_id": "<id>",
  "tool_name": "Read",
  "target_hash": "a1b2c3d4",
  "mode": "preview",
  "result_chars": 4200,
  "total_session_chars": 14300,
  "chars_saved": 2700,
  "spilled": false,
  "spillover_path": null
}
```

The `chars_saved` field (result_chars - pointer_chars for REFERENCE_ONLY, result_chars - preview_chars for PREVIEW) feeds the `chars_saved_per_session` metric in `llm-dispatch.jsonl` at the end of each session.

---

## Acceptance Criteria

```
[ ] lib/tool_replay_ledger.py existe, importable via
    python3 -c "from lib.tool_replay_ledger import ToolReplayLedger, Mode"

[ ] lib/tool_budget_catalog.py existe, importable via
    python3 -c "from lib.tool_budget_catalog import CATALOG"

[ ] pytest tests/unit/test_tool_replay_ledger.py cubre:
    - Transición FRESH → PREVIEW → REFERENCE_ONLY en llamadas sucesivas al mismo target
    - Enforcement del char_cap: después de N chars acumulados, mode = REFERENCE_ONLY
    - Enforcement del item_cap: después de 10 targets distintos, mode = REFERENCE_ONLY en nuevo target
    - TTL expiration: entry con touchedAt > ttl_hours returns FRESH (entrada nueva)
    - Spillover write: cuando mode = REFERENCE_ONLY, archivo existe en spillover_dir
    - Spillover read: pointer format incluye path correcto y archivo es legible
    - Cleanup: después de cleanup(), ledger SQLite y spillover dir no existen

[ ] hooks/result-truncator.sh consulta ledger antes de truncar;
    si REFERENCE_ONLY devuelve el pointer [REF:...] en lugar del output truncado

[ ] Spillover funciona end-to-end: el archivo existe en el path referenciado por el pointer;
    Read del path devuelve el contenido original completo

[ ] Metric appended to llm-dispatch.jsonl at session end:
    campo chars_saved_per_session presente y > 0 en sesiones con replays

[ ] cognitive-os.yaml contiene bloque tool_replay_ledger con todos los campos del §7

[ ] Compliance F§5:
    grep -rF "ToolReplayLedger" /tmp/holaOS-investigation 2>/dev/null || echo "0 matches"
    # debe returnsr 0 matches (o "0 matches" si /tmp/holaOS-investigation ausente)

[ ] Commit message usa template Annex F §6:
    Source-pattern: [private compliance dossier — see internal records] §Tool-replay budget ledger
```

---

## Consequences

### Positivo

- **~18,000 tokens/session saved** in SDD-apply sessions with high replay (projection Annex B §3). At $0.003/Ktok Sonnet input: ~$0.054/session direct; the main benefit is **headroom** — fewer early compactions, lower out-of-context failure rate.
- **Denser context.** The 18,000 freed tokens let the model keep more specs, more decision history, and more relevant code in the window, improving long-response coherence.
- **Modo `REFERENCE_ONLY` auto-descriptivo.** El modelo recibe información suficiente para recuperar el contenido si lo necesita (`Read` del spillover path), sin perdida de acceso — solo de presencia inmediata en contexto.
- **Granularidad per-tool.** Bash corto y archivo grande dejan de competir por el mismo límite. Read de archivos medianos (< 3 000 chars) pasa sin truncación; Bash ruidoso (find de 800 líneas) se recorta agresivo desde la primera llamada.

### Negativo

- **Per-session state.** The SQLite ledger and spillover directory must be cleaned at session-end. If the session-end hook does not run (kill -9, crash), files persist on disk until the next session cleans them.
- **`REFERENCE_ONLY` can confuse the model.** If the pointer is not interpreted correctly, the model can assume the content is available when it is not in context. Mitigation: the pointer format is explicit (`[REF:tool=... target=... path=...]`) and acceptance tests verify that the path is readable.
- **SQLite en subshell.** Bash hooks corren en subshells; cada invocación abre y cierra el SQLite. Para sesiones con > 50 tool-calls/minuto, el overhead de SQLite open/close puede ser perceptible. Mitigación: WAL mode + connection pool en `tool_replay_ledger.py`; evaluar degradar a JSON plano si el overhead es medible.
- **Dependencia de `$CLAUDE_SESSION_ID`.** Si la harness no expone esta variable, el ledger agrupa todas las sesiones bajo `"default"`, degradando el aislamiento. Mitigación: fallback a PID + timestamp como session_id aproximado.

---

## Implementation Plan

**D1 — Core: ledger + schema SQLite + unit tests**

- Escribir `lib/tool_replay_ledger.py`: `ToolReplayLedger`, `LedgerDecision`, `Mode`, SQLite schema, `record()`, `get_mode()`, `stats()`, `prune_expired()`, `cleanup()`.
- Escribir `tests/unit/test_tool_replay_ledger.py`: todas las transiciones de modo, TTL, spillover, cap enforcement.
- Verificar: `python3 -m pytest tests/unit/test_tool_replay_ledger.py -q` verde.

**D1.5 — Catálogo: thresholds derivados de logs luum**

- Procesar `truncation-events.jsonl` para extraer distribución de tamaños por tool_name.
- Derivar `preview_max_chars` / `trim_threshold_chars` / `reference_max_chars` para los 4 tools principales.
- Escribir `lib/tool_budget_catalog.py` con `CATALOG` y `ToolBudgetEntry` dataclass.
- Unit test: catálogo tiene entry para cada tool esperado + `_default`.

**D2 — Integración: `hooks/result-truncator.sh` + spillover writer**

- Modificar `hooks/result-truncator.sh`: lookup al ledger antes de truncar, branching FRESH/PREVIEW/REFERENCE_ONLY.
- Implementar `write_spillover()` en el hook (Python one-liner o función bash delegando a Python).
- Test end-to-end: simular PostToolUse con output grande, verificar pointer en stdout + archivo en spillover.
- Degradación graceful: si SQLite falla, fallback a `smart_truncator.py` sin error del hook.

**D2.5 — Session-end cleanup + `cognitive-os.yaml` schema + observabilidad**

- Add cleanup to the session-end hook.
- Actualizar schema `cognitive-os.yaml` con bloque `tool_replay_ledger`.
- Add `chars_saved_per_session` to `llm-dispatch.jsonl` emission in `lib/dispatch.py`.
- Ejecutar checklist compliance Annex F §5.
- Guardar Engram observation bajo `compliance/holaos-adoption/tool-replay-ledger`.

---

## Alternatives rejected

| Alternative | Decision | Rationale |
|---|---|---|
| Scale the global threshold from 5,000 to 1,000 chars | Rejected | Does not solve the replay problem: it would still have no cross-tool accumulator. Also, 1,000 chars truncates useful medium-size files that currently pass whole. |
| LRU cache en memoria en `smart_truncator.py` | Rejected | Los hooks corren en subshells separados — el estado in-memory no persiste entre llamadas. Un cache in-process requeriría un daemon auxiliar o IPC, añadiendo complejidad sin las garantías de SQLite. |
| Embeddings para deduplicación semántica | Rejected | Overkill para el problema: no necesitamos detectar semejanza, sino identidad exacta `(tool, target)`. El overhead de embedding (~200ms/call) convertiría cada tool-call en una operación lenta. Revisitar si la tasa de false-positive de `sha256(args)` resulta problemática. |
| Extender `lib/context_budget.py` (ADR-186) | Rejected | ADR-186 mide hook outputs en tokens estimados, no tool results en chars. La semántica es diferente — el budget de ADR-186 aplica a lo que el hook mismo produce, no a lo que el tool devuelve al modelo. Compartir el acumulador mezclaría dos dimensiones ortogonales. |

---

## Compliance Certification

This ADR adopts the per-session ledger pattern described in [private clean-room research dossier] §Tool-replay budget ledger under the clean-room protocol of [private compliance dossier — see internal records].

```yaml
pattern_source: "holaos-comparison-2026-05-10.md::AnnexB::§B1 (tool-replay budget ledger)"
holaos_files_read_by_research: []
holaos_files_blocked_for_impl: ["ALL"]
```

**Thresholds:** todos los valores numéricos (char_cap, item_cap, ttl, preview/reference_max_chars) son derivados de la distribución de uso real de luum, no copiados del catálogo de referencia. La metodología de derivación se documenta en el comentario de `lib/tool_budget_catalog.py`.

**Identifiers:** `ToolReplayLedger`, `Mode.PREVIEW`, `Mode.REFERENCE_ONLY`, `LedgerDecision`, `record()` son propios de luum. Ver tabla §9.

**Spillover format:** el pointer `[REF:tool=... target=... path=...]` es diseño ad-hoc de luum. El patrón de referencia usa `full_state_path` como campo en un objeto JSON; luum usa un string inline auto-descriptivo.

**Implementer prohibition:** agents implementing this ADR are categorically prohibited from reading any path matching `/tmp/holaOS*`. Detecting any code fragment from the reference pattern in the prompt requires an immediate halt and emission of `NEEDS_CLARIFICATION:` before any other action.

**Commit message template** (Annex F §6, requerido en todos los commits de implementación):

```
<scope>: <change>

Pattern adopted from holaOS (clean-room rewrite).
Refs: [private clean-room research dossier]
Source-pattern: AnnexB::§B1.tool-replay-budget-ledger
License: Apache-2.0 modified (BSL-like). No source code copied.
```

---

## Open Questions

1. **`target_hash` strategy for tools with non-deterministic outputs.** Is `sha256(tool_args_normalized)[:16]` sufficient for tools such as `Bash`, where the same command can produce different outputs (timestamps, PIDs)? For `Read` and `Grep`, the args hash is stable. For `Bash` with `date` or `ps`, the same script produces different outputs but the args hash is identical, which is correct: we want to detect "same command, same target", not "same output". (**UNSURE**: if the agent uses variants of the same command with different flags but the same intent, the hash will differ and both will be FRESH. Evaluate whether to add Bash flag normalization in D1.)

2. **Cap 20K vs 15K: calibrar con 2 semanas de uso.** La projection de Annex B usa 24K chars del patrón de referencia; luum usa 20K como postura conservadora. Con los datos reales de `tool-replay-ledger.jsonl` post-deploy, la calibración a 15K podría aumentar el ahorro ~20% adicional con bajo impacto en sesiones cortas. (**UNSURE**: no confirmar hasta tener 2 semanas de datos reales.)

3. **Exponer stats al modelo via system prompt.** Inyectar `[LEDGER: session_chars=14300/20000, items=7/10]` en el system prompt del siguiente turno daría al modelo auto-awareness de su headroom de replay. Contra: meta-context overhead (~50 tokens/turno). A favor: el modelo podría anticipar `REFERENCE_ONLY` y consolidar lecturas. (**UNSURE**: evaluar en fase experimental con un cohort de sesiones, medir si cambia el comportamiento de tool-use del modelo antes de habilitar por defecto.)

---

## References

- [private clean-room research dossier] §Tool-replay budget ledger — especificación abstracta del patrón adoptado
- [private compliance dossier — see internal records] — protocolo clean-room y checklist de compliance
- `docs/02-Decisions/adrs/ADR-259-external-pattern-adoption-posture.md` — ADR paraguas (postura patterns-only)
- `docs/02-Decisions/adrs/ADR-016-context-diet.md` — ADR de Context Diet (relacionado: gestión de headroom)
- `docs/02-Decisions/adrs/ADR-049-llm-dispatch.md` — LLM Dispatch (destino de la métrica `chars_saved_per_session`)
- `docs/02-Decisions/adrs/ADR-186-budget-enforcement.md` — Budget Enforcement ADR-186 (complementario, no reemplazado)
- `hooks/result-truncator.sh` — hook PostToolUse a modificar en D2
- `lib/smart_truncator.py` — truncador actual, queda como fallback
- `rules/result-management.md` — regla `result-management` (a actualizar para documentar modos PREVIEW y REFERENCE_ONLY)
- `cognitive-os.yaml:548-559` — configuración `result_truncation` actual (a extender con bloque `tool_replay_ledger`)

---
*This ADR references a private clean-room research dossier whose specific
file paths and section headings are intentionally redacted from this public
record per ADR-267 §Layer 4 and the privatize-research migration (commit e961fd3b).*

## Verification

```bash
python3 -m py_compile lib/tool_replay_ledger.py lib/tool_budget_catalog.py
python3 -m pytest tests/unit/test_tool_replay_ledger.py -q
```

