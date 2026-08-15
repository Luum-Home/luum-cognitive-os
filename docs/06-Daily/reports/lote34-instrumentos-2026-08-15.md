# Lote 34 — Instrumentos: corridas contra artefactos

Fecha: 2026-08-15
Alcance: los 119 hooks de clase `instrument` del censo canónico.
Evidencia ejecutable: `scripts/audit_instrument_productivity.py` (read-only, determinista).

```bash
.venv/bin/python scripts/audit_instrument_productivity.py            # tabla
.venv/bin/python scripts/audit_instrument_productivity.py --json     # filas completas
.venv/bin/python scripts/audit_instrument_productivity.py --class gate
```

Exit codes: 0 = todos productivos, 1 = hay improductivos, 2 = error.

---

## 1. Qué del encargo era falso

**La premisa de población reprodujo exacto.** `scripts/audit_gate_registration.py`
devuelve `instrument 119, wired 102, unwired 17`. A diferencia del lote 1, acá el
censo no está mirando un archivo generado: ya resuelve symlinks y las cuatro
superficies de cableado. Esa parte del encargo se sostiene.

**Los cuatro casos ya medidos: la dirección es correcta, los números no.** Los
cuatro son improductivos, pero ninguna de las cuatro cifras reproduce.

| Instrumento | Corridas s/ encargo | Corridas medidas | Diferencia |
|---|---:|---:|---|
| `error-pipeline` | 33.942 | **10.497** | encargo 3,2x de más |
| `error-learning` | 24.329 | **10.549** | encargo 2,3x de más |
| `doc-sync-detector` | 10.069 | **1.991** | encargo 5,1x de más |
| `rate-limit-drain` | 1.288 | **5.230** | encargo 4x de **menos** |
| **Total de los cuatro** | **~68.000** | **28.267** | **el encargo infla 2,4x** |

El error va en las dos direcciones, así que no es un factor de escala: es un
conteo distinto. Dos causas probables: `33.942` está a 86 filas del total de
`hook-timing.jsonl` (33.856 líneas), o sea que parece el largo del archivo y no
las filas de `error-pipeline`; y `rate-limit-drain` sale más bajo en el encargo
porque quedó contado solo sobre telemetría viva, sin las rotaciones gzipeadas de
`metrics/.archive/` (que aportan ~25% del total).

**`doc-sync-detector` no es «sin artefacto».** El encargo lo da como caso 2. Es
caso 1: escribe `stale-docs.jsonl` vía `safe_jsonl_append` (línea 142) y tiene
**dos consumidores reales** — `cos_lib/singularity.py` (monitor #9, `_monitor_stale_docs`)
y `hooks/_lib/singularity-suggestion.sh`. Borrarlo sería exactamente el verde
barato de este lote: apagaría el hook y dejaría dos lectores alimentándose de un
archivo que nadie escribe.

**`rate-limit-drain` no es «una cola sin productor».** Es más específico y peor:
el productor existe en `cos_lib/rate_limiter.py` y escribe
`.cognitive-os/rate-limit-queue.jsonl` (43 KB, última escritura 2026-05-01). El
drain lee **otra ruta**: `rate-limit-queue.json` (`hooks/rate-limit-drain.sh:113`),
la ruta legacy que la migración a JSONL dejó como
`rate-limit-queue.json.deprecated` (2 bytes). Encima, el hook productor
`rate-limiter.sh` no está registrado (`grep -c 'rate-limiter' .claude/settings.json`
→ `0`). Son dos fallas apiladas, no una.

**Los 17 no cableados no son desperdicio.** Los 17 tienen estado escrito en el
manifiesto (`future` 6, `conditional_opt_in` 5, `manual_trigger` 4, `demoted` 1) y
**0 corridas cada uno**. No cuestan invocaciones y su ausencia es una decisión
registrada, no un olvido. No hay nada que recortar ahí.

---

## 2. Los cuatro casos verificados

| Instrumento | Corridas | Artefacto | Filas | Consumidores | Veredicto | Desenlace |
|---|---:|---|---:|---:|---|---|
| `error-learning` | 10.549 | `metrics/error-learning.jsonl` | 11 | 40 | `starved` | **1 — roto y arreglable** |
| `error-pipeline` | 10.497 | `metrics/error-learning.jsonl` | 11 | 61 | `starved` | **1 — roto y arreglable** |
| `rate-limit-drain` | 5.230 | ninguno (lee ruta deprecada) | 0 | 0 | `no-artifact` | **3 — sin productor** |
| `doc-sync-detector` | 1.991 | `metrics/stale-docs.jsonl` | 0 | 2 | `no-artifact` | **1 — roto y arreglable** |

### `error-pipeline` y `error-learning` — misma causa raíz

Los dos leen el código de salida del nivel superior del payload:

```bash
# hooks/error-pipeline.sh:39
EXIT_CODE=$(echo "$INPUT" | jq -r '.exit_code // "0"' 2>/dev/null)
# hooks/error-learning.sh:18
EXIT_CODE=$(stdin_field '.exit_code' '0')
```

El harness lo manda anidado. La forma real del payload está documentada en el
propio repo, `docs/04-Concepts/architecture/agentic-mastery-operations.md:101`:

```json
{"tool_name":"Bash","tool_input":{...},"tool_response":{"content":"1 failed","exit_code":1}}
```

Como `.exit_code` no existe, el default `"0"` gana siempre, y la línea siguiente
corta:

```bash
[ "$EXIT_CODE" = "0" ] && exit 0
```

Resultado: **21.046 invocaciones que salen en la línea 4 sin mirar nada**, contra
11 filas escritas (y esas 11 son de antes de que el campo se moviera). Los dos
artefactos tienen consumidores de verdad — `bin/cos-errors`,
`cos_lib/error_insights.py`, `cos_lib/feedback_consumer.py`,
`cos_lib/evolve_task_queue.py`, `cos_lib/consumer_improvement_proposals.py` — así
que todo el pipeline de aprendizaje de errores está alimentándose de un archivo
vacío desde hace meses. Esto no es un instrumento que sobra: es el de mayor
retorno del lote.

**Parche propuesto, NO aplicado.** El intento de editar `hooks/error-pipeline.sh`
fue bloqueado por `protected-config-write-guard`, que exige revisión humana
explícita sobre rutas del control-plane. No se bypaseó. Queda para decisión del
operador:

```bash
# hooks/error-pipeline.sh:39
EXIT_CODE=$(echo "$INPUT" | jq -r '.tool_response.exit_code // .exit_code // "0"' 2>/dev/null)
# hooks/error-learning.sh:18
EXIT_CODE=$(stdin_field '.tool_response.exit_code' "$(stdin_field '.exit_code' '0')")
```

El fallback a `.exit_code` se mantiene a propósito: si algún harness sí lo manda
arriba, el hook sigue andando.

### `doc-sync-detector` — el filtro excluye el lenguaje del repo

```bash
# hooks/doc-sync-detector.sh:27
if ! echo "$FILE_PATH" | grep -qE '\.(go|ts|java)$'; then exit 0; fi
```

El SO se escribe en Python y Bash: **3.565 archivos `.py`/`.sh` versionados contra
195 `.go`/`.ts`/`.java`**. El hook fue escrito para proyectos consumidores y acá
descarta casi toda edición. 1.991 corridas, 0 filas, con dos lectores esperando.
Arreglo: extender el filtro a `.py` y `.sh` y mapear los patrones de ruta a la
estructura real (`hooks/`, `cos_lib/`, `scripts/`). También es control-plane, así
que va como propuesta.

### `rate-limit-drain` — desenlace 3

Corre 5.230 veces sobre una ruta deprecada mientras el productor está sin
registrar. Las dos salidas válidas: apagar el drain, o registrar `rate-limiter.sh`
y apuntar el drain a `rate-limit-queue.jsonl`. Ojo con la segunda: registrar el
limitador cambia el comportamiento de bloqueo de la sesión y es una decisión
pendiente del operador ya documentada en `rules/rate-limiting.md`. **No** es un
cambio de mantenimiento.

---

## 3. Panorama de los 119

```
productive 25   |  no-artifact 50  |  idle 36  |  starved 5  |  no-consumer 3
```

- **Invocaciones improductivas medidas: 89.401** sobre un total de ~148.000 filas
  de telemetría retenida. Pero ver la advertencia de abajo: la cifra es un techo,
  no un número firme.
- **`idle` 36**: nunca corrieron en la ventana retenida. No cuestan nada. Incluye
  los 17 no cableados.
- **`no-consumer` 3**: escriben y nadie lee. El más caro es
  `reaper-daemon-launcher` → `runtime/reaper-daemon.log`, **127.693 filas**,
  última escritura 2026-08-03, sin ningún lector fuera del propio hook. Candidato
  claro a desenlace 2, pero es un `.log` de daemon: confirmar que no lo consume
  una herramienta externa antes de tocarlo.

---

## 4. Lo que no pude medir

**El bucket `no-artifact` (50) es una hipótesis, no un veredicto.** La detección
de escrituras es estática sobre el cuerpo del hook y tiene falsos positivos
confirmados. Dos que verifiqué a mano y **sí producen**, pese a figurar como
`no-artifact`:

- `cross-session-event-emit` → `.cognitive-os/sessions/events.jsonl`, **6,5 MB**,
  escrito hoy. Escribe desde adentro de un heredoc `python3 <<'PY'`.
- `post-git-orphan-notifier` → `metrics/orphan-notifier.jsonl`, 185 bytes,
  escrito hoy. Delega la escritura a un script Python externo.

El script ya resuelve tres caminos de escritura (variable + redirect,
`safe_jsonl_append` con ruta inline, y heredocs Python simples), y con eso
`codebase-itinerary-capture` pasó de falso positivo a `productive`. Los que quedan
delegan a scripts Python externos, que exigirían seguir la llamada. **Ningún hook
del bucket `no-artifact` debería borrarse sin confirmación manual de una
corrida.** Los cuatro casos de la sección 2 sí están confirmados a mano, uno por
uno.

Tampoco medí: si los consumidores que cuenta el script se ejecutan de verdad (que
`cos_lib/error_insights.py` lea `error-learning.jsonl` no prueba que alguien
invoque `error_insights`), ni las clases `gate` y `ambiguo` (137 hooks), que
corren con el mismo script cambiando `--class`.

Un sesgo del propio censo, heredado de `audit_gate_registration.py` y que conviene
tener a mano: **82 de los 119 «instrumentos» no tienen ningún token en el nombre**.
Caen en la clase por descarte — la última línea de `classify()` manda a
`instrument` todo lo que no bloquea. «119 instrumentos» es el resto de una resta,
no 119 cosas identificadas como instrumento.

---

## 5. Qué queda para el operador

Nada se borró ni se modificó en este pase, según el encargo.

| Prioridad | Acción | Por qué |
|---|---|---|
| P1 | Aplicar el parche de `exit_code` a `error-pipeline` + `error-learning` | Recupera el pipeline de errores; 21.046 invocaciones hoy sin efecto; requiere levantar `protected-config-write-guard` con revisión |
| P2 | Extender el filtro de `doc-sync-detector` a `.py`/`.sh` | Dos consumidores esperando; 1.991 corridas a cero |
| P2 | Decidir `rate-limit-drain`: apagar, o registrar el productor y corregir la ruta | 5.230 corridas sobre ruta deprecada |
| P3 | Confirmar a mano el bucket `no-artifact` antes de recortar | Falsos positivos confirmados |
| P3 | Correr `--class gate` y `--class ambiguo` | 137 hooks sin medir |
