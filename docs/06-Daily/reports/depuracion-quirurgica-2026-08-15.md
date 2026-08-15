# Depuración quirúrgica — qué se queda y por qué

> Estado: **propuesta**. Nada borrado. Tres ítems esperan agentes en vuelo, marcados abajo.
> Toda cifra sale de las auditorías del 2026-08-15, con su informe citado.

---

## El criterio

Un control **envejece bien** si su respuesta no depende de que el agente diga la verdad sobre sí mismo.

Esa es la línea entera. Todo lo demás se deriva:

| Envejece bien | Envejece mal |
|---|---|
| Verifica un hecho contra el disco, el índice o el proceso | Le pregunta al modelo sobre su propio trabajo |
| Determinista: mismo input, mismo veredicto | Depende de que el modelo se autoevalúe con exactitud |
| Falla cerrado: si revienta, frena | Falla abierto: si revienta, pasa |
| Corre donde todavía puede impedir algo | Corre después de que la acción ocurrió |

**Por qué la autoevaluación envejece al revés:** un modelo mejor no se autoevalúa con más exactitud — se autoevalúa **más convincentemente**. La evidencia está medida: `auto-verify` 0 PASS en 55 corridas, `dod-gate` 0 PASS y nunca bloqueó, `trust-score-validator` 953 corridas sin crear jamás su archivo. No fallaron por estar mal implementados. Fallaron porque le piden a la parte interesada que se juzgue.

---

## Se quedan

Ocho, no cinco. El "cinco" era retórico; la lista medida da ocho.

| Primitiva | Evidencia | Por qué envejece bien |
|---|---|---|
| `result-truncator` | **1 efecto cada 21 corridas** · ~3,16 M tokens ahorrados | Mecánico, sin opinión. El mejor rendimiento del sistema |
| `destructive-git-blocker` | 37 bloqueos · me frenó 2 veces hoy, con razón | Determinista. No le pregunta nada al modelo |
| `direct-main-guard` | 48 bloqueos | Ídem |
| `protected-config-write-guard` | 52 bloqueos · me frenó 4 veces hoy | Determinista — **con un hueco**: no cubre escrituras por Bash |
| `secret-detector` | 8 redacciones (5 fixtures, 3 reales) | Verifica un hecho contra el texto |
| `subagent-budget-enforcer` | 12 `exit 2`, el conteo más alto del sistema | Cuenta llamadas — **con un bug**: corre en `PostToolUse`, bloquea después de ejecutar |
| Guards de rutas y privacidad | Cazaron 18 rutas reales del operador hoy | Verifican texto contra patrón |
| `scope_closure_gate` + contrato de confidencialidad | Creados hoy · el segundo ya atrapó una regresión mía | Miden un hecho y tienen ratchet en las dos direcciones |

**Dos de los ocho tienen bugs conocidos**, anotados arriba. Se arreglan, no se tiran: la clase es correcta.

---

## Se van

### Piden autoevaluación — no hay hecho equivalente

| Primitiva | Evidencia |
|---|---|
| `auto-verify` | 53 `NO_CRITERIA`, **0 PASS** en 55 corridas |
| `dod-gate` | 40 `NO_COMPLEXITY`, 15 `MISSING`, **0 PASS**, nunca bloqueó |
| `trust-score-validator` | **953 corridas**, `trust-scores.jsonl` no existe en ninguna de las 21 instalaciones |
| `confidence-gate` | Su `exit 2` exige `phase in (production, maintenance)`; la fase está clavada en `reconstruction` desde el commit inicial |

⏳ *Espera al arquitecto de gates de autoevaluación, que está costeando si alguno tiene hecho verificable equivalente antes de matarlo.*

### Corren mucho y no producen nada

| Primitiva | Evidencia |
|---|---|
| `error-pipeline` | **33.942 corridas → 12 filas.** Filtra por `.exit_code`, campo que el harness no manda |
| `error-learning` | 24.329 corridas |
| `doc-sync-detector` | 10.069 corridas, sin artefacto |
| `rate-limit-drain` | 1.288 corridas drenando una cola **sin productor** desde mayo |
| `rate-limiter` | Sin registrar. Su propia regla lo declara inoperante |

Juntas: **~68.000 invocaciones**, dos tercios de toda la actividad de hooks en consumidores, para escribir prácticamente nada.

### Roto en más de una capa

**`claim-validator`** — tres defectos independientes, cada uno suficiente por sí solo:

1. El enforcer **no detecta claims fabricados**. Verificado: cuatro claims en dos idiomas (*"Done. I ran the tests and they all pass"*, *"Listo, corrí los tests y pasan todos"*) → los cuatro `ok=true, status=noop, 0 findings`. El único que marcó algo fue el que **traía** evidencia.
2. El hook lee `.ok // true` con jq, que **no puede devolver `false` nunca**.
3. Su otro camino de bloqueo depende de la fase, clavada desde el commit inicial.

Es la primera promesa del README: *"blocks agents that report test results without running tests"*. Se le dio exactamente eso y pasó limpio.

---

## Lo que reemplaza a lo que se va

No es "achicar y ya". Lo que se va deja tres huecos reales, y hay tres mecanismos que hoy no existen como primitiva y que fueron **lo más productivo de la sesión**:

**1. El encargo refutable.** El brief de un sub-agente lleva los comandos, no las conclusiones, y permiso explícito de refutar la premisa de quien lo manda. Medido hoy: **en 4 de 5 encargos de preparación la premisa era falsa** — el generador equivocado, un 93,8% inflado, trece lectores que son veinte, un "22" que no está en la portada. Si se les hubiera pedido ejecutar en vez de preparar, habrían aplicado esos errores con prolijidad. Son tres líneas de prompt y el repo tiene 129 reglas, ninguna es ésa.

**2. Verificación cruzada.** Dos agentes, contextos disjuntos, la misma pregunta, comparación de los números. Encontró más defectos reales en un día que la capa de hooks en 26. Hoy ocurrió por casualidad, porque había otra sesión abierta.

**3. Instrumentar el 99%.** El costo no está en el markdown —el impuesto fijo es el **1,08%** de los 374.047 tokens por turno— sino en la acumulación de conversación y la salida de herramientas, que **no tiene gate ninguno**. Y `hook-timing.jsonl` guarda duración y exit code pero **nunca el tamaño del stdout**, así que el segundo componente del costo por tool call no está medido.

Los tres son la misma familia: **verificar un hecho, no pedir una opinión.**

---

## Lo que hay que publicar

Es lo único acá adentro que nadie más puede escribir, y sale de 26 días de telemetría y 22 auditorías:

> Los controles de agentes que piden autoevaluación se degradan a medida que los modelos mejoran, porque un modelo mejor se autoevalúa más convincentemente y no más exactamente. Los que verifican un hecho contra el estado sobreviven. Medido sobre 255 primitivas, 152.542 invocaciones y 21 instalaciones.

---

## Qué falta antes de borrar

| Espera | Quién lo está estableciendo |
|---|---|
| Si alguno de los 4 gates de autoevaluación tiene hecho verificable equivalente | Arquitecto de gates de autoevaluación |
| Si el contrato gate/instrumento vale su costo de migración | Arquitecto del contrato |
| Si Codex ejecuta los hooks proyectados — cambia el alcance de todo | Forense de Codex |
| Cuántos de los eventos malos reales el SO previno | QA contrafactual sobre un consumidor vivo |

**Nada se borra hasta que los cuatro cierren.** Podar sobre una medición incompleta es el error que este mismo documento denuncia.
