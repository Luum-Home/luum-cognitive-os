---
adr: 264
title: 'Tool Result Envelope: Compact Envelope Format for Large Tool Outputs'
status: accepted
implementation_status: implemented
date: '2026-05-11'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: 'tool result envelope module, agent/dispatch integration, spillover behavior, and tests implement compact result envelopes'
---

# ADR-264 — Tool Result Envelope: Compact Envelope Format for Large Tool Outputs

## Status

Accepted

**Date:** 2026-05-11
**Owner:** orchestrator
**Tier:** core
**Authors:** orchestrator (Claude Sonnet 4.6)
**Implements:** ADR-259 (holaOS Adoption Posture — patterns only)
**Source-pattern:** Internal compliance dossier §Capability HTTP result envelope (AnnexG::§G1)
**Related:** ADR-263 (tool-replay ledger — ortogonal y composable), ADR-016 (context diet)

---

## Context

### Estado actual

luum trunca large tool outputs mediante `lib/smart_truncator.py` (20 833 bytes) con estrategia
head/tail. El truncator opera sin estructura: simplemente corta el texto y agrega un marcador de
elipsis. Los puntos de uso son `lib/openai_compatible_agent_loop.py:267,290`.

El resultado de esta estrategia tiene dos consecuencias negativas comprobables:

1. **El modelo pierde metadata sobre lo truncado.** No sabe el tamaño real del output original,
   no tiene el nombre del tool que lo generó, ni el target (file path, URL, comando) que produjo
   el resultado. El corte es semánticamente opaco.
2. **Los reviewers no pueden correlacionar un resultado truncado en los logs con su fuente.**
   El log muestra un bloque de texto cortado sin contexto estructural.

El módulo `lib/agent_runner.py` ejecuta tool calls y concatena resultados al historial de
conversación del modelo sin post-procesamiento de tamaño. `lib/dispatch_helper.py` construye el
payload que va al modelo en cada turno, igualmente sin inspección de tamaño por resultado
individual.

### Patrón identificado en investigación

El [private clean-room research dossier] §Capability HTTP result envelope del estudio holaOS identifica un patrón de infraestructura transversal: cuando un
tool result supera un threshold, en lugar de descartarlo o truncarlo ciegamente, se lo reemplaza
por un **envelope estructurado** que preserva:

- Los primeros N bytes como preview (el modelo ve el comienzo del resultado).
- Metadata explícita: tamaño real, nombre del tool, target hint.
- Un puntero al payload completo (spillover storage) para recuperación opcional.

El patrón es ortogonal al tool-replay ledger (ADR-263): ADR-263 opera sobre la dimensión temporal
(cuántas veces se ejecutó un mismo tool en la sesión); este ADR opera sobre la dimensión espacial
(cuán grande es el resultado de una ejecución individual). Ambos reducen consumo de contexto por
caminos independientes y se componen sin conflicto.

### Threshold derivado de luum

El [private clean-room research dossier] §Capability HTTP result envelope usa 32 KB como threshold, derivado del harness `pi` de holaOS. Para luum con
Claude Code (ventana de 200K tokens, 1 token ≈ 4 bytes):

- 28 KB ≈ 7 000 tokens ≈ 3.5% del contexto disponible.
- En sesiones con 15-20 tool calls activos, 3-4 resultados grandes a 28 KB cada uno suman
  ~14% del contexto solo en resultados, antes de incluir historial de conversación.
- 28 KB es más conservador que 32 KB, apropiado para un contexto compartido con más artefactos
  concurrentes (engram, session state, agent prompts). Ver §Open Questions para calibración futura.

---

## Decision

### 1. Nuevo módulo `lib/tool_result_envelope.py`

Módulo Python puro (sin dependencias externas) con la siguiente interfaz pública:

```python
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib, os

ENVELOPE_THRESHOLD: int = 28 * 1024   # 28 KB — derivado de context window luum (ver §Context)
ENVELOPE_PREVIEW_SIZE: int = 7 * 1024  # 7 KB preview

@dataclass
class EnvelopePreview:
    preview_text: str         # primeros ~7 KB del resultado original
    full_chars: int           # tamaño real en caracteres
    tool_name: str            # nombre del tool que produjo el resultado
    target_hint: str          # ej. file path, URL, shell command
    full_pointer: str | None  # path al archivo de spillover, o None si persist_full=False

def wrap_if_large(
    raw_result: str,
    tool_name: str,
    target_hint: str,
    threshold: int = ENVELOPE_THRESHOLD,
    preview_size: int = ENVELOPE_PREVIEW_SIZE,
    persist_full: bool = True,
    spillover_dir: str | None = None,
) -> str:
    """Retorna raw_result tal cual si len(raw_result) <= threshold.
    Si excede, retorna un envelope estructurado Markdown con preview + metadata + pointer.
    Si persist_full=True, escribe el contenido completo en spillover_dir.
    """
```

El módulo expone adicionalmente:

```python
def render_envelope(ep: EnvelopePreview) -> str:
    """Renderiza un EnvelopePreview como string Markdown para consumo del modelo."""
```

### 2. Formato del envelope (Markdown estructurado — distinto a holaOS JSON)

El envelope se renderiza como texto Markdown legible, deliberadamente distinto al JSON que usa
el patrón de referencia (que usa `tool_result_format: "compact_envelope"` con JSON anidado):

```
[TOOL RESULT ENVELOPE]
tool: <tool_name>
target: <target_hint>
full_size: <N> chars (truncated; preview below)
full_pointer: <path-or-none>

--- preview (<M> chars) ---
<preview_text>
--- end preview ---
```

Diferencias intencionales respecto al patrón de referencia (Anexo F §2, Nivel 1):

| Dimensión | holaOS (referencia) | luum (este ADR) |
|-----------|---------------------|-----------------|
| Formato de envelope | JSON serializado | Markdown plain-text |
| Nombre del tipo | `FormattedCapabilityToolResult` | `EnvelopePreview` |
| Nombre de la función | `formatCapabilityToolResultForModel` | `wrap_if_large` |
| Threshold | 32 KB (literal del harness `pi`) | 28 KB (derivado de context window luum) |
| Preview size | 8 KB | 7 KB |
| Summary de estructura | `topLevelPayloadSummary` (shape sin valores) | no incluido (YAGNI: añadir si se necesita) |
| Campo `ok` elevado | sí (si payload tiene `ok: boolean`) | no (envelope es agnóstico al contenido) |

### 3. Integración en `lib/agent_runner.py`

Cualquier tool result pasa por `wrap_if_large` antes de ser agregado al historial de conversación.

```python
from lib.tool_result_envelope import wrap_if_large

# Después de ejecutar el tool call:
result_text = wrap_if_large(
    raw_result=raw_tool_output,
    tool_name=tool_name,
    target_hint=target_hint,
    spillover_dir=_session_envelope_dir(),
)
# result_text va al historial del modelo
```

Si `wrap_if_large` produce un envelope (`len(raw_tool_output) > threshold`), se loguea en
`agent-heartbeat.jsonl`:

```json
{"event": "tool_result_enveloped", "tool_name": "<name>", "full_chars": N, "preview_chars": M}
```

### 4. Integración en `lib/dispatch_helper.py`

Idem para tools dispatched a través del helper. Si el resultado ya fue procesado por
`agent_runner`, `dispatch_helper` omite el segundo wrap (detecta si el string ya contiene el
marcador `[TOOL RESULT ENVELOPE]`).

### 5. Spillover storage

Los payloads completos de resultados enveloped se persisten en:

```
.cognitive-os/sessions/<session-id>/envelopes/<sha256-of-content>.txt
```

- El directorio se crea en la primera escritura de la sesión.
- El nombre del archivo es el SHA-256 hex del contenido original (primeros 64 chars del digest).
- `full_pointer` en el envelope apunta al path absoluto de este archivo.
- Cleanup: el directorio completo se elimina al finalizar la sesión (hook `session-end`).
- Si `persist_full=False` (útil en tests o contextos de solo-preview), no se escribe archivo y
  `full_pointer` es `None`.

### 6. Composabilidad con ADR-263 (tool-replay ledger)

Cuando ADR-263 esté implementado, la composición es la siguiente en `lib/agent_runner.py`:

```
ledger.check(tool_name) → REFERENCE_ONLY | FRESH | BLOCKED
    │
    ├─ BLOCKED    → no ejecutar el tool (ADR-263 gate)
    ├─ REFERENCE_ONLY → ejecutar, luego wrap_if_large con preview_size=0
    │                   (envelope colapsa a solo pointer, sin preview)
    └─ FRESH      → ejecutar, luego wrap_if_large normal (preview completo)
```

Cuando el ledger dice `REFERENCE_ONLY`, el envelope se renderiza con `preview_text=""` y
`full_pointer` apunta al spillover del resultado más reciente del mismo tool.

---

## Acceptance Criteria

```
[ ] lib/tool_result_envelope.py existe, es importable vía:
    python3 -c "from lib.tool_result_envelope import wrap_if_large, EnvelopePreview"
    sin dependencias externas al stdlib.

[ ] pytest tests/unit/test_tool_result_envelope.py pasa con cobertura de:
    - under-threshold passthrough: resultado < 28KB retorna el string original sin modificar
    - over-threshold envelope: resultado > 28KB retorna string con marcador [TOOL RESULT ENVELOPE]
    - persist_full=False: no se escribe ningún archivo en spillover_dir
    - persist_full=True: se escribe archivo en spillover_dir y full_pointer apunta al path
    - spillover filename: nombre es SHA-256 hex del contenido original (64 chars)
    - preview truncation: preview_text tiene exactamente min(7KB, len(raw)) chars
    - idempotency: llamar wrap_if_large en un envelope ya renderizado no re-envuelve

[ ] lib/agent_runner.py aplica wrap_if_large a cada tool result antes de agregarlo al historial.
    Test de integración: mock tool que retorna 30KB de texto → historial contiene envelope,
    no el blob completo.

[ ] lib/dispatch_helper.py idem. Test: payload con envelope ya aplicado no genera doble-wrap.

[ ] Composición con ADR-263 testeada (puede ser test pendiente/skip si ADR-263 no está
    implementado aún):
    ledger=REFERENCE_ONLY + wrap_if_large → preview_text="" + full_pointer solo.

[ ] El envelope renderizado es human-readable cuando un reviewer lee los logs manualmente.
    (Verificación manual — no automatizable.)

[ ] Compliance F§5:
    grep -rF "EnvelopePreview" /tmp/holaOS-investigation 2>/dev/null | wc -l = 0
    (gate pasa con WARN si /tmp/holaOS-investigation no existe en CI)

[ ] Commit message incluye template F§6:
    Source-pattern: [private compliance dossier — see internal records] §Capability HTTP result envelope
```

---

## Consequences

### Positivo

- **El modelo preserva awareness del tamaño truncado.** El campo `full_size` le permite al modelo
  saber cuántos caracteres se omitieron y decidir si solicitar el payload completo.
- **Metadata explícita en logs.** Los reviewers ven `tool_name` + `target_hint` + `full_pointer`
  en lugar de un blob de texto cortado sin contexto.
- **Reducción de out-of-context errors.** En sesiones largas con múltiples tool calls grandes,
  el envelope evita que un solo resultado grande ocupe una fracción desproporcionada del contexto.
- **Reversible con un parámetro.** `threshold=math.inf` desactiva el envelope completamente.
  Zero blast radius para rollback.
- **Complementa `smart_truncator.py` sin reemplazarlo.** `smart_truncator` sigue operando como
  fallback en `openai_compatible_agent_loop.py`; el envelope opera upstream en `agent_runner.py`.

### Negativo

- **Overhead de render.** El texto del envelope agrega ~200 bytes de markup por resultado
  enveloped. Negligible frente al ahorro (resultado típico de 50KB → 7KB preview + 200B markup).
- **Spillover dir crece durante la sesión.** En sesiones con muchos tool calls grandes, el dir
  `.cognitive-os/sessions/<id>/envelopes/` puede crecer varios MB. Mitigado con cleanup en
  session-end y cap futuro (ver §Open Questions).
- **Double-wrap risk.** Si `agent_runner` y `dispatch_helper` ambos aplican el envelope, se
  necesita detección de idempotencia. El marcador `[TOOL RESULT ENVELOPE]` en el texto actúa
  como flag de detección.

### Mitigación

- Cleanup automático del spillover dir en hook `session-end` (a añadir en `scripts/session-end.sh`
  o equivalente).
- Cap de spillover dir a 50 MB como guardrail de sesión (futuro, ADR follow-up).

---

## Implementation Plan

**D1 — Módulo puro + tests unitarios**

- Crear `lib/tool_result_envelope.py`: `EnvelopePreview`, `wrap_if_large`, `render_envelope`.
- Crear `tests/unit/test_tool_result_envelope.py`: todos los casos del Acceptance Criteria.
- Verificar: `python3 -m pytest tests/unit/test_tool_result_envelope.py -q` pasa.

**D1.5 — Integración en agent_runner y dispatch_helper**

- Modificar `lib/agent_runner.py`: import + llamada a `wrap_if_large` post-tool-execution.
- Modificar `lib/dispatch_helper.py`: idem + guard de idempotencia.
- Añadir log `tool_result_enveloped` en `agent-heartbeat.jsonl` cuando se activa el envelope.
- Test de integración en `tests/integration/` con mock tool de 30KB output.

**D2 — Spillover storage + cleanup + composición**

- Implementar lógica de spillover: path derivado de session ID + SHA-256.
- Añadir cleanup al hook `session-end`.
- Agregar test de composición con ADR-263 (skip si ledger no implementado).
- Ejecutar checklist de compliance F§5.

---

## Alternatives Considered

| Alternativa | Decisión | Razón |
|-------------|----------|-------|
| Hard truncate sin envelope (status quo) | Rechazado | Pierde metadata; el modelo no sabe qué se truncó ni cuánto |
| JSON envelope (al estilo holaOS) | Rechazado | El modelo parsea Markdown más naturalmente en el contexto de Claude Code; JSON requiere parsing adicional; format distinto satisface constraint clean-room |
| Streamed truncation per-chunk | Rechazado | Overkill para el caso de uso; añade complejidad de streaming al loop síncrono |
| Reemplazar `smart_truncator.py` completamente | Rechazado | `smart_truncator` tiene lógica de head/tail para casos where el modelo necesita ver tanto el inicio como el fin; envelope preserva solo el inicio. Coexistencia es más segura |
| threshold 32 KB (literal de holaOS) | Rechazado | Violaría constraint clean-room de Anexo F §2 Nivel 1 (no copiar valores literales del harness de referencia); 28 KB es derivado independiente del context window luum |

---

## Compliance Certification

Este ADR adopta el patrón descrito en [private clean-room research dossier] §Capability HTTP result envelope
bajo el protocolo clean-room establecido en [private compliance dossier — see internal records].

Declaraciones de compliance per Annex F §4.2:

```yaml
pattern_source: "holaos-annex-g-surprise-findings.md::§G1 (Capability HTTP result envelope)"
holaos_files_read_by_research: []
holaos_files_blocked_for_impl: ["ALL"]
```

Identifier divergence (Annex F §2, Nivel 1 PATTERN-ONLY):

| holaOS identifier (de la research annex) | luum identifier | Razón |
|------------------------------------------|-----------------|-------|
| `formatCapabilityToolResultForModel` | `wrap_if_large` | Snake_case Python; nombre descriptivo del comportamiento |
| `FormattedCapabilityToolResult` | `EnvelopePreview` | Nombre refleja el contenido del sobre, no el proceso de formateo |
| `compact_envelope` (campo JSON) | `[TOOL RESULT ENVELOPE]` (marcador Markdown) | Formato completamente distinto: texto plano vs JSON |
| `DEFAULT_COMPACT_TOOL_RESULT_THRESHOLD_BYTES = 32 * 1024` | `ENVELOPE_THRESHOLD = 28 * 1024` | Valor derivado independientemente del context window luum |
| `DEFAULT_COMPACT_TOOL_RESULT_PREVIEW_BYTES = 8 * 1024` | `ENVELOPE_PREVIEW_SIZE = 7 * 1024` | Valor ajustado para luum |
| `topLevelPayloadSummary` | no incluido (YAGNI) | Feature no adoptada en esta iteración |
| `raw_result.stored_in: "tool_result.details.raw"` | `full_pointer: str \| None` (path absoluto) | Semántica de puntero al archivo, no ruta lógica de campo |

Adiciones luum-específicas no presentes en el patrón de referencia:

- `persist_full=False` como opción explícita (útil para tests y contextos de solo-preview).
- Guard de idempotencia por marcador de texto (evita double-wrap).
- Composición documentada con ADR-263 (`REFERENCE_ONLY → preview_text=""`).
- SHA-256 como nombre de archivo de spillover (vs referencia que usa path lógico interno).

**Los agentes implementadores tienen PROHIBIDO leer `/tmp/holaOS*`.** Cualquier prompt que
contenga paths holaOS debe ser rechazado con `NEEDS_CLARIFICATION:`.

Commit messages para commits de implementación DEBEN incluir:

```
Pattern adopted from holaOS (clean-room rewrite).
Refs: [private clean-room research dossier]
Source-pattern: AnnexG::§G1.capability-envelope
License: Apache-2.0 modified (BSL-like). No source code copied.
```

---

## Open Questions

1. **Threshold óptimo: 28 KB vs 24 KB vs 32 KB.** El valor 28 KB es una derivación conservadora
   del context window de Claude Code. La calibración correcta requiere medir p50/p95 del tamaño
   de tool results en producción durante 2 semanas. `ENVELOPE_THRESHOLD` debe ser configurable
   vía `cognitive-os.yaml` (`tool_result_envelope.threshold_kb`) para ajustar sin redeployment.
   **UNSURE** si 28 KB es too conservative para sesiones con pocos tool calls.

2. **Preview size: ¿7 KB es suficiente para que el modelo decida si solicitar el full output?**
   En resultados de tipo JSON (estructurados, inicio predecible), 7 KB puede ser más que
   suficiente. En resultados de tipo log de compilación o diff grande, el inicio puede ser poco
   informativo. **UNSURE** — candidato a `preview_kb` configurable también.

3. **¿Exponer `expand_envelope(pointer)` como tool del modelo?** Permitiría al modelo solicitar
   explícitamente el payload completo de un envelope mediante tool call. Requiere registrar el
   tool en el harness. Potencialmente más útil que el spillover pasivo. Parking para ADR
   follow-up (no bloquea esta adopción).

4. **Cap del spillover dir.** Sin cap, una sesión con 100 tool calls grandes podría acumular
   ~500 MB en `.cognitive-os/sessions/<id>/envelopes/`. El cleanup en session-end mitiga esto
   para sesiones normales, pero sesiones largas no terminan pronto. Parking como guardrail
   en ADR follow-up.

---

## References

- [private clean-room research dossier] §Capability HTTP result envelope — especificación abstracta fuente
- [private compliance dossier — see internal records] — protocolo clean-room y checklist
- ADR-259 — holaOS Adoption Posture (política umbrella de adopción patterns-only)
- ADR-263 — Tool-Replay Ledger (ortogonal y composable con este ADR)
- ADR-016 — Context Diet (contexto de reducción de ventana de contexto en luum)
- `lib/smart_truncator.py` — módulo existente que este ADR complementa (no reemplaza)
- `lib/agent_runner.py` — punto de integración primario
- `lib/dispatch_helper.py` — punto de integración secundario

---
*This ADR references a private clean-room research dossier whose specific
file paths and section headings are intentionally redacted from this public
record per ADR-267 §Layer 4 and the privatize-research migration (commit e961fd3b).*
