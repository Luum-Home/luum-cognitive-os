# Señal sin consumidor: censo, poda y destinatarios

Fecha: 2026-08-19 · Alcance: `os-only` · Estado: **propuesta de diseño, no implementada**
Autor: sub-agente arquitecto (lote A). No reclama número de ADR.

## Resumen ejecutivo

- Censo automático sobre los **124 artefactos** de `.cognitive-os/metrics/`: **40 no tienen
  ningún lector** y **9 más tienen lector pero ese lector no tiene invocador** → **49 flujos
  sin consumidor efectivo (39,5%)**, 15,4 MB de los 81 MB del directorio.
- **La recomendación es poda, no capa nueva**: de los 49, **31 dejan de emitir**
  (20 se apagan del todo, 10 conservan el hook y pierden la escritura, 1 es un fixture de
  test mal ubicado), **13 ganan consumidor**, **1 se invierte** (`governance-catches` no
  necesita lector: ya lo tiene, necesita *input*) y **4 quedan en verificación**.
- No hace falta construir el consumidor: **ya existe y está registrado**.
  `hooks/cos-session-start-projector.sh` (SessionStart, ADR-275) emite a **stderr** —
  llega al operador y **cuesta cero tokens de modelo**. El diseño lo extiende.
- **No un agregador: tres destinatarios.** Modelo-en-el-turno (caro, mínimo),
  operador-al-abrir-sesión (gratis en tokens, casi todo va acá), CI/auditoría (ya existe).
- **Tope duro del canal caro: 300 tokens por turno y 2.000 por sesión**, tomados *de*
  `context_budget.static_max_tokens: 4000`, no sumados. Al superarlo se descarta por
  prioridad y **el descarte se anuncia contado** — nunca en silencio.
- El costo medido de emitir sin lector: `quality-duplicates` sola consume **4.471 s =
  21,8% de todo el tiempo de hooks** en una ventana de 6 h, y su único producto es un
  reporte que ningún código lee.

## Correcciones a las premisas del encargo

1. **«Hay canal. Nadie lo usa para esto.»** — Falso en la primera mitad de la frase, que
   es la que importa. **31 archivos** bajo `hooks/` y `packages/` ya emiten
   `hookSpecificOutput`, y **26 hooks** lo usan como canal de contexto real
   (`git grep -l hookSpecificOutput -- hooks/ packages/ | wc -l` → 31). El canal no está
   ocioso: está **poblado**. El recurso escaso no es el canal, es el presupuesto — que es
   exactamente por qué el punto 3 del encargo (tope duro) es el que decide el diseño y no
   un detalle de implementación.
2. **«Es una capa que no existe.»** — La capa operador **existe y está registrada**:
   `hooks/cos-session-start-projector.sh` corre en SessionStart y delega en
   `scripts/cos-session-start-projector`, que ya proyecta pending-truth, ADRs parciales,
   estado de git y acciones sugeridas, con `--limit`. Lo que falta no es la capa: es que
   los 49 flujos huérfanos estén **declarados** como fuentes suyas.
3. **«Los dos modos de falla que tenés que resolver desde el día uno.»** — El segundo
   (agregador caído indistinguible de silencio sano) **ya está resuelto conceptualmente en
   este repo**, y mejor que en Alertmanager: `scripts/audit_gate_liveness.py` cruza «¿puede
   bloquear?» con «¿bloqueó?» en cuatro cuadrantes y se niega explícitamente a leer un cero
   como salud; `scripts/hook_vitality_audit.py` hace lo mismo para hooks. Adoptar esos dos,
   no inventar un dead-man's-switch nuevo.
4. **`governance-catches` no pertenece a la misma familia que los otros tres.** Su
   consumidor existe (`scripts/cos_governance_roi.py`) y funciona; lo que falta es el
   **input**. Meterlo en la bolsa «señal sin consumidor» invierte el diagnóstico: darle un
   consumidor a algo que ya tiene lector y no tiene escritor no arregla nada. Es una falla
   **opuesta** y pide un arreglo opuesto (bajar el costo de registrar, no agregar lectura).
5. **`skill-suggestion` tampoco.** Sí tiene lector — `scripts/skill_adherence_loop.py` — y
   ese lector corre y publica veredictos. Su patología es una tercera: **el lector existe y
   no puede ver** (90 UNMEASURABLE). Tres enfermedades distintas bajo un nombre: sin lector,
   sin escritor, lector ciego. Un diseño único para las tres sería el error de plomería que
   el propio encargo advierte.
6. **Los números de `quality-duplicates` del encargo subestiman el residual.** En la ventana
   de `hook-timing.jsonl` viva hoy (`2026-08-19T15:20Z → 21:21Z`) suma **4.471 s en 51
   corridas = 87,7 s promedio**, y es **el hook más caro del repo por un factor de 2,3x**
   sobre el segundo. «Hoy 27 s» describe la mejor corrida, no lo que muestra el ledger.
   Los 245.704 hallazgos **no los recontéé**: los cito como dato del encargo, no como
   medición propia.
7. **Ceguera declarada del censo** (en la línea de `cos_lib/measurement.py`): la búsqueda es
   por *basename literal* sobre archivos trackeados. **No ve** (a) rutas construidas
   dinámicamente sin el nombre literal, (b) consumo humano —alguien abriendo el archivo—,
   (c) lectores fuera del repo. Y **falló concretamente** en scripts sin extensión:
   `scripts/cos-control-plane-audit` escribe 13,5 MB y las dos primeras versiones del
   clasificador lo listaron con `escritor = ninguno`. El número 49 es **cota inferior de
   consumo, cota superior de orfandad** — es decir, los huérfanos podrían ser menos, nunca
   más, salvo por (a).
8. **Bug encontrado en el lugar exacto donde el encargo sugiere alojar el consumidor.**
   `cos_lib/context_budget.py::filter_hook_output` devuelve `""` cuando el veredicto es
   `BLOCK`: **descarta el payload entero sin dejar rastro en el canal**. Es el modo de falla
   nº1 del encargo, ya presente en el repo, en producción, en el filtro de presupuesto.
   Cualquier diseño que se apoye ahí hereda el silencio.
9. **Restricción del encargo verificada, no asumida.** `git status --short` muestra 13
   archivos modificados por otras corridas y 3 informes ajenos sin trackear en
   `docs/06-Daily/reports/`. Escribí un único archivo, el mío. No toqué
   `.cognitive-os/metrics/`, no maté procesos, no reclamé número de ADR (el máximo en uso
   hoy es ADR-343 y es identificador escaso compartido).
10. **Prueba en vivo del caso que el encargo llama «la forma pura».**
    `hooks/protected-config-write-guard.sh` me bloqueó **dos veces** durante este censo, las
    dos sobre comandos **read-only** que apenas mencionaban la ruta protegida en un
    argumento (`grep`, `python3 -c` leyendo el JSON). Las dos veces ofreció el canal de
    feedback. `wc -l .cognitive-os/metrics/governance-catches.jsonl` → **0**. Dos falsos
    positivos más que el guard no va a saber nunca, generados por el mismo agente que estaba
    midiendo el fenómeno.

## Censo de emisores y sus lectores

**Comando** (read-only, determinista; exit 0 siempre). Se propone promoverlo a
`scripts/signal_consumer_census.py` como parte de la implementación:

```python
# Regla: un archivo de código que MENCIONA el artefacto es ESCRITOR si hay una operación
# de append/write en ±12 líneas; en cualquier otro caso cuenta como LECTOR CANDIDATO
# (conservador: sobreestima lectores, subestima huérfanos).
# HUÉRFANO = todos los mencionadores son escritores, o no hay mencionadores.
# 2º nivel: para cada lector, ALCANZABILIDAD (registrado en settings.json / invocado
# desde skill, workflow u otro módulo). Lector sin invocador = huérfano de 2º orden.
```

Resultado: **124 artefactos · 75 con lector alcanzable · 40 sin lector · 9 con lector sin
invocador**.

| artefacto | filas | tamaño | escritor(es) | lector | disposición | criterio |
|---|--:|--:|---|---|---|---|
| `control-plane-audit.jsonl` | 965 | 13.0 MB | `_(script sin extensión)_` | ninguno | **APAGAR** | 13,5 MB, 965 filas; nadie nombra la decisión que cambia |
| `state-retention-audit.jsonl` | 3540 | 539 KB | `state_retention_audit.py` | ninguno | **APAGAR** | auditoría que se audita a sí misma |
| `subagent-budget-enforcer.jsonl` | 1235 | 243 KB | `subagent-budget-enforcer.sh` | ninguno | **NO-ESCRIBIR** | el valor del hook es el corte en turno, ya probado |
| `orchestrator-claim-gate.jsonl` | 1006 | 214 KB | `orchestrator_claim_gate.py` | ninguno | **CONSUMIDOR** | operador: claims bloqueados por sesión |
| `reinvention-checks.jsonl` | 307 | 119 KB | `reinvention-check.sh` | ninguno | **NO-ESCRIBIR** | el aviso ya viaja en turno |
| `acc-pipeline-history.jsonl` | 169 | 115 KB | `acc_pipeline.py` | ninguno | **CONSUMIDOR** | operador: historial de pipeline ACC |
| `orchestrator-decision-trace.jsonl` | 306 | 106 KB | `orchestrator-decision-trace.sh` | ninguno | **APAGAR** | traza sin pregunta asociada |
| `control-plane-audit-hook.jsonl` | 954 | 97 KB | `control-plane-audit.sh` | ninguno | **APAGAR** | duplica el anterior |
| `adr-suggestion.jsonl` | 307 | 96 KB | `adr-relevance-suggest.sh` | ninguno | **NO-ESCRIBIR** | la sugerencia ya se inyecta en UserPromptSubmit |
| `rule-suggestion.jsonl` | 306 | 72 KB | `rule-router-prompt-suggest.sh` | ninguno | **NO-ESCRIBIR** | idem adr-suggestion |
| `peer-card.jsonl` | 554 | 65 KB | `user-prompt-capture.sh` | ninguno | **APAGAR** | 554 filas, ningún lector, ninguna doc |
| `claim-enforcer.jsonl` | 245 | 53 KB | `claim_enforcer.py, cos_agent_flicker_report.py` | ninguno | **CONSUMIDOR** | operador: claims falsos por sesión |
| `cwd-inject.jsonl` | 304 | 26 KB | `agent-working-dir-inject.sh` | ninguno | **NO-ESCRIBIR** | la inyección es el producto |
| `advisor-consultations.jsonl` | 90 | 17 KB | `advisor_server.py` | ninguno | **CONSUMIDOR** | operador: uso real del advisor MCP |
| `predev-completeness.jsonl` | 110 | 16 KB | `predev-completeness-check.sh` | ninguno | **NO-ESCRIBIR** | gate en turno |
| `skill-synthesis-queue.jsonl` | 41 | 12 KB | `skill-synthesis-scanner.sh` | ninguno | **CONSUMIDOR** | cola: si nadie la drena es hallazgo |
| `surface-fix-detector.jsonl` | 57 | 10 KB | `surface-fix-detector.sh` | ninguno | **CONSUMIDOR** | operador: arreglos de superficie detectados |
| `infra-usage.jsonl` | 21 | 5 KB | `smart_infra.py` | ninguno | **APAGAR** | 21 filas en 3 meses |
| `confidentiality-enforcer.jsonl` | 23 | 4 KB | `confidentiality-enforcer.sh` | ninguno | **CONSUMIDOR** | seguridad: redacciones aplicadas |
| `agent-verification.jsonl` | 63 | 4 KB | `agent-output-verifier.sh` | ninguno | **CONSUMIDOR** | operador: verificación de salida de agentes |
| `adr-section-warnings.jsonl` | 16 | 3 KB | `adr-section-validator.sh` | ninguno | **NO-ESCRIBIR** | warning en turno |
| `push-collision-detect.jsonl` | 21 | 2 KB | `push_collision_detect.py` | ninguno | **CONSUMIDOR** | concurrencia: colisiones de push |
| `worktree-removals.jsonl` | 6 | 1 KB | `safe-worktree-remove.sh, cos-validation-capsule.sh` | ninguno | **CONSUMIDOR** | reversibilidad: qué worktree se borró |
| `scope-proportionality.jsonl` | 4 | 1 KB | `scope-proportionality.sh, scope-proportionality.sh` | ninguno | **NO-ESCRIBIR** | gate en turno |
| `hook-header-warnings.jsonl` | 7 | 1 KB | `hook-header-validator.sh` | ninguno | **APAGAR** | 7 filas, sin doc, sin lector |
| `engram-daemon-down.jsonl` | 8 | 1 KB | `engram_lifecycle.py` | ninguno | **CONSUMIDOR** | liveness de engram: caída = hallazgo |
| `teammate-idle.jsonl` | 12 | 1 KB | `teammate-idle.sh` | ninguno | **APAGAR** | 12 filas, sin pregunta |
| `approval-ledger-missing.jsonl` | 15 | 1 KB | `claim-validator.sh, claim-validator.sh` | ninguno | **CONSUMIDOR** | gobierno: aprobaciones faltantes |
| `auto-verify.fixtures.jsonl` | 1 | 1 KB | `_(script sin extensión)_` | ninguno | **APAGAR** | fixture de test en el dir de producción |
| `adversarial-review-gate.jsonl` | 4 | 1 KB | `adversarial-review-gate.sh` | ninguno | **NO-ESCRIBIR** | gate en turno |
| `adr-implementation.jsonl` | 0 | 0 KB | `adr_implementation_ledger.py` | ninguno | **APAGAR** | 0 filas desde 2026-06-12 |
| `backlog-reconciliation.jsonl` | 0 | 0 KB | `cos_session_backlog.py` | ninguno | **APAGAR** | 0 filas desde 2026-05-27 |
| `chaos-weekly.jsonl` | 0 | 0 KB | `_(script sin extensión)_` | ninguno | **APAGAR** | 0 filas desde 2026-07-20, sin escritor |
| `decision-depth-gate.jsonl` | 0 | 0 KB | `decision-depth-gate.sh` | ninguno | **APAGAR** | 0 filas desde 2026-05-23 |
| `governance-catches.jsonl` | 0 | 0 KB | `cos_governance_roi.py` | ninguno | **INVERTIR** | falta el INPUT, no el lector: cos_governance_roi.py ya lo lee |
| `graphify-context-replay-benchmark.jsonl` | 0 | 0 KB | `_(script sin extensión)_` | ninguno | **APAGAR** | 0 filas desde 2026-06-12 |
| `graphify-token-reduction-smoke.jsonl` | 0 | 0 KB | `_(script sin extensión)_` | ninguno | **APAGAR** | 0 filas desde 2026-07-19 |
| `repair-dispatch.jsonl` | 0 | 0 KB | `auto-repair-dispatcher.sh` | ninguno | **APAGAR** | 0 filas |
| `session-audit.jsonl` | 0 | 0 KB | `changelog_generator.py, git-context-capture.sh` | ninguno | **APAGAR** | 0 filas |
| `so-impact-eval-trigger.jsonl` | 0 | 0 KB | `so-impact-eval-trigger.sh` | ninguno | **APAGAR** | 0 filas |
| `tool-replay-ledger.jsonl` | 2670 | 604 KB | `_(script sin extensión)_` | tool_replay_ledger.py (sin invocador) | **VERIFICAR** | lector sin invocador: 618 KB |
| `tool-use-correlation.jsonl` | 321 | 24 KB | `_(script sin extensión)_` | tool_use_correlation.py (sin invocador) | **VERIFICAR** | lector sin invocador |
| `canonical-live.jsonl` | 105 | 23 KB | `cos_executor.py, cos_sprint.py` | cos_watch.py (sin invocador) | **VERIFICAR** | cos_watch.py sin invocador registrado |
| `contextual-rules.jsonl` | 33 | 7 KB | `contextual-rule-loader.sh, contextual-rule-loader.sh` | symbiosis_monitor.py, symbiosis_monitor.py (sin invocador) | **VERIFICAR** | symbiosis_monitor sin invocador |
| `subagent-input-schema-validator.jsonl` | 18 | 2 KB | `_(script sin extensión)_` | subagent-input-schema-validator.sh (sin invocador) | **NO-ESCRIBIR** | se lee a sí mismo |
| `ref-key-misses.jsonl` | 4 | 1 KB | `_(script sin extensión)_` | ref_key_loader.py (sin invocador) | **CONSUMIDOR** | ref-keys inexistentes = deuda de RULES-COMPACT |
| `validator-promotion-evaluations.jsonl` | 2 | 0 KB | `_(script sin extensión)_` | validator_soak_evaluator.py (sin invocador) | **VERIFICAR** | 2 filas |
| `install-timing.jsonl` | 0 | 0 KB | `_(script sin extensión)_` | install_timing.py, install-timing-test.sh (sin invocador) | **APAGAR** | 0 filas |
| `maintainer-decision-impact.jsonl` | 0 | 0 KB | `_(script sin extensión)_` | maintainer_impact.py (sin invocador) | **APAGAR** | 0 filas desde 2026-05-27 |

**Distribución de disposiciones**: APAGAR 20 · NO-ESCRIBIR 10 · CONSUMIDOR 13 ·
VERIFICAR 5 · INVERTIR 1. Sumando `quality-duplicates` (que escribe fuera de
`.cognitive-os/metrics/`, en `.cognitive-os/reports/quality-duplicates/`), **31 emisores
dejan de emitir y 13 ganan consumidor**.

## Uno o varios consumidores

Un agregador único es el diseño equivocado, y la razón no es de gusto: **las señales no
comparten destinatario, y el costo de cada destinatario difiere en tres órdenes de
magnitud**. Un agregador único obliga a pagar el canal más caro para todo, o a inventar
adentro suyo el ruteo que se quiso evitar.

| destinatario | canal | costo por evento | qué va acá | criterio de admisión |
|---|---|---|---|---|
| **Modelo, en el turno** | `hookSpecificOutput.additionalContext` en `UserPromptSubmit` | **tokens, cada turno** | sólo lo que cambia la PRÓXIMA acción del modelo | «si el modelo no lo lee ahora, ¿toma una decisión distinta?» |
| **Operador, al abrir sesión** | `scripts/cos-session-start-projector` → stderr | **cero tokens** | todo lo periódico, rankeado | «¿el operador decidiría distinto mañana?» |
| **CI / auditoría** | `control-plane-audit` + `manifests/documentation-truth-claims.yaml` | fuera de sesión | ratchets y claims | «¿esto puede ponerse en rojo?» |
| **Nadie** | — | — | el resto | **se apaga** |

La cuarta fila es la que hace del diseño una **poda** y no una **plomería**. Sin ella, todo
flujo termina en la primera columna por defecto y el problema se traslada al presupuesto.

**El mecanismo que sostiene esto es una sola regla de admisión, no un servicio:**
`manifests/signal-consumers.yaml`, una fila por flujo, con `destinatario`,
`decision` (texto libre, **obligatorio**: qué decisión cambia cuando el valor cambia),
`retention` y `deadman` (silencio máximo tolerado). Auditoría bidireccional:
un flujo declarado sin emisor real **falla**; un emisor sin fila **falla**. Un flujo cuyo
campo `decision` nadie puede llenar tiene `destinatario: none` y entra en la cola de apagado.

Por qué manifiesto y no código: el fallo que estamos arreglando es *declarativo*
(«esto sirve») sin verificación. Un manifiesto verificado contra el filesystem cierra el
lazo; un servicio agregador lo deja abierto un nivel más arriba.

## El presupuesto de contexto

Restricción dura, y es la que decide el diseño:

- **Tope por turno: 300 tokens** (~1.200 caracteres) para el digest de señal.
- **Tope por sesión: 2.000 tokens.** Agotado, el canal modelo queda cerrado hasta el
  próximo `SessionStart`, y el cierre se anuncia una vez.
- **Es reasignación, no adición.** Sale de `context_budget.static_max_tokens: 4000`
  (`cognitive-os.yaml:171`), que hoy ya mide y bloquea vía `hooks/context-budget-meter.sh`
  (last-in-chain, ADR-186). El presupuesto total del turno **no sube**.
- **Emisión por evento, no por turno.** El digest se emite sólo cuando un flujo cruza su
  umbral. En un turno normal el costo esperado es **cero**; 300 es el techo del peor turno,
  no el promedio. Un mecanismo que gasta 300 tokens por turno para arreglar adherencia
  traslada el problema, exactamente como advierte el encargo.
- **Descarte por prioridad, anunciado y contado.** Al superar el tope se descarta de menor
  a mayor prioridad y la última línea del digest dice
  `+N señales omitidas por presupuesto · cos signal show`. **El conteo del descarte es
  señal**: sin esa línea el recorte es el «verde barato» de `gates-sin-trampa`.

**Costo de referencia**: 2.000 tokens/sesión de tope. A precio opus (~$0,18/10K tokens) son
**$0,036 por sesión en el peor caso**; el caso esperado, con emisión por evento, está más
cerca de cero. Contra eso, la vía operador cuesta **$0** y absorbe 13 de los 13 flujos que
ganan consumidor. **Ningún flujo del censo justifica hoy ocupar el canal modelo de forma
permanente**: el canal caro se reserva para el gate que necesita corregir la acción en curso
—el patrón ya probado de `subagent-budget-enforcer`, que frenó a un agente en 50 tool calls
y fue obedecido sin discusión.

## Los dos modos de falla

### 1. Inhibición que suprime señal real sin dejar rastro

Dos reglas, y la primera es la que falta hoy:

- **El descarte ocurre en presentación, nunca en emisión.** La fila se escribe siempre. Lo
  que el presupuesto recorta es lo que se *muestra*, y el recorte deja un contador.
- **Prohibido el drop silencioso.** Hoy `cos_lib/context_budget.py::filter_hook_output`
  devuelve `""` en `BLOCK`: el payload desaparece y el turno no se entera. **Arreglo
  concreto**: en `BLOCK`, devolver un `additionalContext` mínimo con el conteo de lo
  descartado, la razón y el comando para verlo (≈20 tokens). Un filtro que puede callar sin
  contar es un supresor que no suprime nada auditable — el bug que `gates-sin-trampa`
  nombra explícitamente.

Un flujo **no se silencia por configuración**. Si molesta, se apaga con una fila en el
manifiesto que dice por qué; y esa fila la ve el audit.

### 2. Agregador caído indistinguible de «no hay alertas»

- **Se reusa el cuadrante existente**, no se inventa: `scripts/audit_gate_liveness.py`
  ya cruza «¿puede disparar?» (alcanzabilidad estática) con «¿disparó?» (telemetría) y
  clasifica en `live` / `untested` / `THEATRE` / `telemetry-lying`. Cada flujo del
  manifiesto declara `deadman: <silencio máximo>`; el proyector reporta
  `flujo X en silencio hace N días (máximo declarado M)` **como hallazgo propio**.
- **El digest nunca calla sobre sí mismo.** Siempre imprime una línea de latido con la hora
  de su última corrida exitosa, incluso —sobre todo— cuando no hay hallazgos. Si esa línea
  falta en el arranque, el proyector está muerto y se ve.

### La tensión, resuelta

El silencio mantiene creíble la señal; el silencio también esconde al muerto. Se resuelve
**separando las dos cosas que el silencio significa**:

> **Silencio sobre el contenido, nunca sobre la vitalidad.** Sin hallazgos ⇒ no se imprime
> ningún hallazgo. Pero el digest imprime **siempre** una línea diciendo que corrió y cuándo.

**Costo exacto de la resolución: una línea por `SessionStart`, en stderr, cero tokens de
modelo.** Esa asimetría —vitalidad gratis en el canal del operador, contenido caro en el
canal del modelo— es la razón por la que el latido vive del lado del operador y no del lado
del modelo. Poner el dead-man's-switch en el canal caro sería pagar tokens por turno para
enterarse de que el sistema sigue vivo.

## Qué se apaga en vez de consumirse

**31 emisores dejan de emitir.** Cuatro criterios, aplicados en la tabla:

1. **APAGAR (20)** — cero filas desde su creación, o filas que nadie puede atar a una
   decisión. Se borra el archivo *y* la ruta de escritura. Casos límite:
   `control-plane-audit.jsonl` (13,5 MB, 965 filas de ~14 KB cada una) y
   `state-retention-audit.jsonl` (3.540 filas) son las dos escrituras más caras del censo y
   ninguna tiene lector. Diez archivos tienen **0 filas** desde su creación, algunos desde
   mayo: la telemetría de que el emisor nunca existió de verdad.
2. **NO-ESCRIBIR (10)** — el hook se queda, la escritura se va. Es la distinción que evita
   el error caro: **`subagent-budget-enforcer` no es un emisor inútil**, es el ejemplo que
   el propio encargo cita como éxito. Su valor es el corte en turno; su JSONL es incidental.
   Apagar el hook sería tirar lo que funciona por el archivo que sobra.
3. **`quality-duplicates`: apagar, no consumir.** 4.471 s = **21,8% de todo el tiempo de
   hooks** medido en 6 h (`hook-timing.jsonl`), 2,3x más caro que el segundo hook del repo, y
   su único producto son dos archivos gitignoreados que ningún código lee. Si alguien nombra
   la decisión que depende de esos 245.704 hallazgos, vuelve como ratchet de CI —
   **no como hook de `Stop`**.
4. **INVERTIR (1)** — `governance-catches`: no se apaga y no gana lector. Su lector ya
   existe. Lo que se arregla es el **costo de escribir**: hoy el guard imprime un comando de
   ~120 caracteres que hay que copiar, editar y correr a mano; el resultado son **0 filas en
   dos meses contra 780 bypasses registrados** en el archivo de al lado. Un canal cuyo costo
   de uso supera el valor percibido no tiene un problema de consumo.

**Lo que NO se apaga**: los 75 flujos con lector alcanzable no se tocan. Este diseño no
audita utilidad; audita **existencia de destinatario**.

## Costo

| ítem | costo | evidencia |
|---|---|---|
| Emitir hoy sin lector | 15,4 MB de 81 MB en `.cognitive-os/metrics/` | censo, columna tamaño |
| `quality-duplicates` | 4.471 s / 6 h = 21,8% del tiempo total de hooks | `hook-timing.jsonl`, ventana `15:20Z→21:21Z` |
| Implementar el manifiesto + audit | 1 manifiesto, 1 script de audit, 1 test | comparable a `hook_vitality_audit.py` |
| Extender el proyector | 13 fuentes nuevas, `--limit` ya existe | `scripts/cos-session-start-projector` |
| Arreglar el drop silencioso | ~10 líneas en `context_budget.py` | `filter_hook_output`, rama `BLOCK` |
| Canal modelo, peor caso | 2.000 tok/sesión ≈ **$0,036** | tope propuesto |
| Canal operador | **$0** en tokens, 1 línea por sesión | stderr en `SessionStart` |

**El saldo es negativo en el buen sentido**: la propuesta *libera* tiempo de hooks y disco, y
el gasto nuevo se concentra en el canal que no cuesta tokens. Un diseño que sólo agregara
consumidores sería más caro que el problema — que es, textualmente, la salida que el encargo
autorizaba y que el censo confirma.

## Relación con B

**A es una instancia de B, y el mecanismo general debería ganar.**

B dice: el mismo hecho vive en N lugares mantenidos a mano, y la declaración no está atada a
la realidad. Un emisor sin lector es exactamente eso: **una utilidad declarada —en un
manifiesto, en un ADR, en el comentario de cabecera del hook— y nunca verificada contra el
filesystem**.

Lo que la medición sí muestra, dicho con precisión para no comprar barato mi propio
argumento: el huérfano promedio acumula **4,4 menciones declarativas** (2,7 en `docs/`,
1,7 en `manifests/`) contra **1,0 mención en código** —o sea, exactamente su escritor y nadie
más—, y **33 de los 40** tienen más menciones declarativas que ejecutables.
`confidentiality-enforcer.jsonl`: 9 documentos, 4 manifiestos, **0 lectores**.
`so-impact-eval-trigger.jsonl`: 6 documentos, 2 manifiestos, **0 filas**.
**Contradato honesto**: los flujos con lector tienen todavía *más* menciones declarativas
(8,6 docs / 6,8 manifiestos), así que la razón declarativo:código es parecida en ambos grupos
(4,4:1 contra 3,4:1). Lo que separa al huérfano no es un exceso de declaración: es que su
piso de código es exactamente 1 —el que escribe—, y aun así la declaración se sostuvo sola
durante meses. La creencia la cargaba el documento, y nada la contrastaba.

Concretamente, `manifests/signal-consumers.yaml` **no debería ser un manifiesto nuevo e
independiente**: debería instanciar el mismo contrato declaración↔realidad que B proponga,
con la verificación bidireccional (fila sin emisor ⇒ falla; emisor sin fila ⇒ falla) como
caso particular de su audit. Si B entrega ese contrato, A aporta el **predicado específico**
—«todo artefacto de telemetría declara un destinatario nombrado y una decisión»— y el censo
que lo mide, no un mecanismo paralelo.

Lo que **no** hereda de B: los topes de tokens, la separación de destinatarios y el latido
del dead-man's-switch son propios de A, porque nacen de una restricción que B no tiene —el
contexto del modelo es un recurso que se consume en cada turno. B puede verificar que la
declaración sea verdadera; no puede decidir **a quién** y **a qué precio** se le cuenta.
