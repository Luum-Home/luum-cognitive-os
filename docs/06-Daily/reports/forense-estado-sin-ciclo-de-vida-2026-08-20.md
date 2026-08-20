# Forense: estado de runtime sin ciclo de vida

Fecha: 2026-08-20 · Alcance: `.cognitive-os/runtime/` y `.cognitive-os/metrics/`
Instrumento: `scripts/state_lifecycle_census.py` (nuevo, commiteado con este informe)
Reproducir: `python3 scripts/state_lifecycle_census.py` · JSON: `--json`

## Resumen ejecutivo

Censo sobre **164 familias de estado** (40 familias en `runtime/`, colapsadas desde
73 entradas de primer nivel + 124 `.jsonl` vivos en `metrics/`). Cubetas:
**97 solo-reporta · 54 gobierna-con-ciclo · 9 gobierna-sin-reset · 4 nadie-lo-lee.**

De los 9 que el instrumento marca como "gobierna sin reset", la confirmación a mano
deja **4 bombas reales**: `edit-locks/` (1301 locks, 5,1 MB, 781 con más de 7 días,
bloquea Edit con `exit 2`), `control-plane-audit/findings-state.json` (2,4 MB de
hallazgos conocidos que deciden BLOCK), `validation-activity.jsonl` (decide si un
lock está stale, append-only sin poda) y `rate-limits.jsonl` (decide throttle al 85 %
y su rotación declarada **no existe**). Los otros 5 se auto-invalidan por
construcción (tres `.pid` que se validan contra el proceso, un cooldown que se
sobreescribe, `orchestrator-mode` de 8 bytes).

**Nadie los lee: 4**, encabezados por `reaper-daemon.log` con **9,5 MB** escritos por
dos hooks y cero lectores.

El caso que motivó el encargo — `skill-bypass-counter-unknown` — **ya está desarmado**
en producción. Ver correcciones.

## Correcciones a las premisas del encargo

1. **"72 archivos en `.cognitive-os/runtime/`" — falso por dos órdenes.**
   `find .cognitive-os/runtime -type f | wc -l` → **1403**. El 72 es el conteo de
   entradas de *primer nivel*, que hoy son **73** (65 archivos + 8 directorios); la
   diferencia de uno es un `skill-gate-insist-*` que creó **mi propia sesión** entre
   que se escribió el encargo y que lo medí. La masa real está adentro:
   `edit-locks/` sola tiene 1297 subdirectorios. Contar el primer nivel esconde
   exactamente el archivo que más importa.

2. **"124 `.jsonl` en `.cognitive-os/metrics/`" — correcto**, verificado con
   `find .cognitive-os/metrics -maxdepth 1 -name '*.jsonl' | wc -l` → 124. Hay
   además **75** rotados en `.archive/*.jsonl.gz` que el número no incluye.

3. **"no existe código de reset en el repo" — falso como afirmación general.**
   Existe `manifests/state-retention.yaml` (386 líneas, ADR-199) con **14 superficies
   registradas**, `scripts/state_retention_audit.py`, un presupuesto global de disco
   (400 MiB) y un ratchet de no registrado (210 MiB). El problema no es la ausencia
   de un mecanismo: es que **de las 40 familias de `runtime/`, el manifiesto cubre
   una sola** (`runtime-locks` = `runtime/*.lock*`, y en modo `observe`). El propio
   manifiesto ya lo dice: "more than half of `.cognitive-os` belongs to no registered
   surface".

4. **"un gate bloquea contra ese número" — está en pasado, no en presente.**
   `hooks/orchestrator-skill-invocation-gate.sh:199` dice literalmente que ese hook
   "NO toca `skill-bypass-counter-*`", y su línea 273 documenta el reemplazo: la
   política de insistencia por gate-key (`skill-gate-insist-<key>`, línea 300) en
   lugar del acumulado de por vida. El contador de 143 sigue en disco pero **ningún
   camino de producción lo lee**. Es residuo, no bomba activa.

5. **El contador tiene `mtime` de HOY, y eso no lo hace vivo — lo hace peor.**
   `tests/audit/test_metrics_isolation.py:216` y
   `tests/contracts/test_skill_gate_identity_and_insistence.py:340` construyen la ruta
   contra el `REPO` real, no contra un `tmp_path`. El estado del operador se está
   tocando desde la suite. No lo modifiqué: ambos archivos están en el alcance de
   otros agentes (`git status` los muestra modificados).

6. **"probablemente sean pocos" (los que gobiernan sin resetearse) — se cumple, pero
   por el motivo equivocado.** Son pocos *en cantidad de familias* y enormes *en
   bytes y en consecuencia*: `edit-locks/` es el 78 % de los archivos de todo
   `runtime/` y bloquea ediciones.

7. **Mi propio instrumento nació ciego y lo corregí en la corrida.** El primer
   barrido filtraba por extensión y se perdía `scripts/cos-graphify-*` (sin
   extensión, con shebang), lo que inventó dos "nadie lo lee" que sí tenían
   productor. Es la misma falla que el encargo advirtió sobre los `.jsonl` rotados,
   en otra dimensión: el filtro que abarata la búsqueda es el que fabrica el falso
   negativo.

## Los que GOBIERNAN y no se resetean

Confirmados leyendo al lector, no por heurística.

### 1. `.cognitive-os/runtime/edit-locks/` — 1301 locks · 5,1 MB · nace 2026-05-20

- **Escribe**: `scripts/edit-coop.sh:17-18` (`acquire`).
- **Lee para decidir**: `hooks/edit-lock-pre-tool.sh:66` arma la ruta a
  `edit-locks/<ruta--con--guiones>/meta.yaml`; el hook termina en `exit 2` (línea 99),
  o sea **niega la edición**. Esto es gobierno directo sobre la herramienta Edit.
- **Ciclo de vida**: parcial y perezoso. `edit-coop.sh` detecta stale (línea 28),
  borra el lock al re-adquirir el **mismo** archivo (`rm -rf "$lock_dir"`, :223),
  y ofrece `release` (:287) y `release-mine` (:378). No hay poda global ni por edad.
- **Evidencia del problema**:
  `find .cognitive-os/runtime/edit-locks -maxdepth 1 -mindepth 1 -type d | wc -l` → **1300**;
  con `-mtime +7` → **781**. Seiscientos y pico de locks de archivos que nadie volvió
  a tocar: nunca se van a limpiar solos, porque la limpieza depende de que alguien
  vuelva a editar ese archivo exacto.
- **No está registrado** en `state-retention.yaml`: la única superficie de runtime
  registrada es `runtime/*.lock*`, y estos son directorios sin `.lock` en el nombre.

### 2. `.cognitive-os/runtime/control-plane-audit/` — 2,4 MB · nace 2026-05-16 · escrito hoy 09:28

- **Escribe y lee**: `hooks/control-plane-audit.sh`.
- **Gobierna**: `MODE=block` por defecto (línea 8); con `STATUS=block` el hook imprime
  `[control-plane-audit] BLOCK:` y corta. `hourly.last` (11 bytes) es el cooldown que
  decide si la auditoría corre.
- **El riesgo real está en `findings-state.json` (2.495.032 bytes)**: es la memoria de
  hallazgos ya vistos. Un baseline de hallazgos conocidos que solo crece es
  precisamente el "colchón" de `gates-sin-trampa` — mientras engorda, la diferencia
  entre "no hay hallazgos nuevos" y "el gate dejó de mirar" se vuelve indistinguible
  desde afuera.
- **Ciclo de vida**: ninguno. Ni reaper, ni registro, ni poda.

### 3. `.cognitive-os/runtime/validation-activity.jsonl` — 40 KB · nace 2026-05-23

- **Gobierna**: `hooks/validation-lock-cleanup.sh:102-110` lee el log entero,
  compara la última actividad contra `COS_VALIDATION_ACTIVITY_THRESHOLD` (300 s) y
  con eso agrega `stale_signals` — la decisión de **limpiar un lock de validación
  ajeno**. También lo lee `hooks/_lib/validation-lock.sh:76,176`.
- **Ciclo de vida**: ninguno. Append-only, sin rotación ni registro.
- **Matiz honesto**: el lector solo necesita el último evento, así que crecer no
  corrompe la decisión — la encarece. Es una bomba de latencia de hook, no de
  corrección. Sigue en esta sección porque un hook `PreToolUse` que escanea un
  archivo que crece sin techo es un costo que nadie está mirando.

### 4. `.cognitive-os/runtime/rate-limits.jsonl` — 187 B hoy · reaper declarado inexistente

- **Gobierna**: `cos_lib/rate_limit_tracker.py` — `should_throttle()` corta antes de
  cada llamada a proveedor cuando un bucket pasa `THROTTLE_THRESHOLD_PCT = 85`.
- **Ciclo de vida declarado**: el docstring dice "append-only; daily rotation via
  `metrics-rotation.sh`". **Ese script no existe**:
  `ls scripts/ | grep -i rotation` no devuelve nada. Un reaper documentado que no
  existe es peor que ninguno, porque cierra la pregunta.
- **Por qué hoy pesa 187 bytes**: el módulo es opt-in (`COS_RATE_TRACKER=1`) y está
  apagado. Es una bomba dormida: el día que se prenda, empieza a crecer contra una
  rotación imaginaria.

### Los 5 restantes que el instrumento marca y yo bajo de categoría

`cos-executor.pid`, `reaper-heartbeat.pid`, `session-watchdog.pid` gobiernan
(`hooks/cognitive-os-health.sh:274-275` decide relanzar) pero **se auto-invalidan**:
el lector valida el PID contra el proceso, así que un archivo viejo no miente, avisa.
`skill-failure-monitor-last` es un cooldown de 5 minutos que se sobreescribe: acotado
por construcción. `orchestrator-mode` (8 bytes, nace 2026-08-19, lo lee
`cos_lib/orchestrator_capabilities.py:79`) sí puede quedar latcheado en `executor` si
el daemon muere sin limpiar — es la misma forma que el contador de bypass, en
miniatura. Lo dejo anotado, no lo cuento entre las cuatro.

## Los que nadie lee

| Superficie | Peso | Escribe | Lectores |
|---|---|---|---|
| `runtime/reaper-daemon.log` | **9,5 MB** | `hooks/reaper-daemon-launcher.sh:87`, `hooks/reaper-heartbeat.sh:87` | 0 |
| `runtime/state-retention-auto-safe.last-run` | 11 B | reaper auto-safe | 0 |
| `metrics/auto-verify.fixtures.jsonl` | 622 B, 0 rotados | — | 0 |
| `metrics/chaos-weekly.jsonl` | 0 B vivo, **1 rotado** en `.archive` | — | 0 |

`reaper-daemon.log` es la deuda más grande por bytes de todo el censo: 9,5 MB de log
de un daemon, sin rotación, sin nadie que lo consulte ni en hooks, ni en scripts, ni
en `cos_lib/`, ni en tests. El ratchet de "no registrado" del manifiesto (210 MiB) lo
está pagando en silencio.

`chaos-weekly.jsonl` merece la aclaración que el encargo pidió: el archivo vivo está
en 0 bytes, pero hay **un rotado** en `.archive`. Alguna vez se escribió. Sigue sin
lector.

Aparte de la tabla, el residuo ya mencionado: `skill-bypass-counter-unknown`
(nace 2026-05-18, contenido `143`) — sin lector de producción desde que el gate
migró a la política de insistencia.

## Población, medibles y ciegos

- **Población**: 164 familias. La unidad es la **familia**, no el archivo: 34
  `suppress-agent-snapshot-toolu_*.json` son UNA superficie con UNA política, no 34
  problemas. Runtime: 73 entradas de primer nivel → 40 familias. Metrics: 124 `.jsonl`
  vivos → 124 familias.
- **Fuentes declaradas**: `runtime/` (primer nivel), `metrics/*.jsonl` **más**
  `.archive/*.jsonl.gz` (75 rotados), `manifests/state-retention.yaml`, y el código en
  `hooks scripts cos_lib lib tests packages templates cmd commands skills .claude
  .codex .opencode`.
- **Medibles**: quién escribe, quién lee, si hay reaper registrado o código de reset,
  fecha de nacimiento (`stat -f %SB`), peso y cantidad de miembros.
- **Ciegos declarados** (salen en la propia salida del instrumento):
  1. **`decide-vs-reporta` es heurística.** `GOVERN_PAT` mira una ventana de ±8
     líneas alrededor de la lectura. Estrecha candidatos; no dicta. Caso concreto: en
     `hooks/edit-lock-pre-tool.sh` la lectura está en la línea 66 y el `exit 2` en la
     99 — el instrumento **no** lo vio, lo confirmé a mano. Y al revés,
     `scripts/cross_session_reconciler.py:41` fue un falso positivo (es un
     `json.dumps(report)`, un reporte, no una decisión) que hizo caer tres
     superficies de golpe cuando lo saqué del patrón.
  2. **Sesiones vivas escribiendo durante la medición.** Hay tres agentes corriendo
     suites. Los tamaños difieren entre corridas y esa diferencia **no** es la
     variable medida. Los bytes de este informe son de la corrida del 2026-08-20
     ~09:30; la de las 09:28 ya daba distinto en `control-plane-audit`.
  3. **Lectores fuera del repo**: 0 detectables. Un script ad-hoc del operador o un
     `jq` en la terminal no aparecen en ningún barrido estático.
  4. **Token demasiado corto para buscar**: 0 familias, pero el umbral existe
     (`MIN_TOKEN = 8`) porque tokens cortos como `locks` producen falsos positivos por
     substring.

## Qué se pierde si se limpia cada cosa

Nadie limpie nada a partir de esta lista sin leer esta sección. Este informe es el
mapa, no la limpieza.

- **`edit-locks/` (781 con >7 días)**: se pierde la prueba de quién estaba tocando
  qué. Un lock viejo puede pertenecer a una sesión **parkeada**, no muerta:
  `edit-coop.sh` distingue `active | parking | released | stale` (línea 26) y borrar
  un `parking` desbloquea un archivo que alguien reclamó a propósito. Lo que se puede
  podar sin discusión es lo que `edit-coop.sh` ya clasifica como `stale`; el resto
  necesita la decisión del dueño.
- **`control-plane-audit/findings-state.json`**: se pierde la memoria de "esto ya lo
  vimos". Vaciarlo hace que la próxima corrida reporte **todos** los hallazgos como
  nuevos — un rojo masivo que no corresponde a ninguna regresión. Lo correcto es
  registrar la superficie con `max_total_mib` y decidir la política de olvido, no
  truncarla.
- **`validation-activity.jsonl`**: se pierde la línea de tiempo que decide si un lock
  de validación está abandonado. Truncarlo **hace ver todos los locks como stale de
  golpe** y habilita limpiezas que no corresponden. Solo es seguro conservar la cola
  reciente (los últimos eventos por encima de los 300 s del threshold).
- **`rate-limits.jsonl`**: hoy no se pierde nada — el tracker está apagado. Con
  `COS_RATE_TRACKER=1` prendido, borrarlo resetea la percepción de consumo a cero y el
  guard deja de esquivar al proveedor justo antes de un 429.
- **`reaper-daemon.log` (9,5 MB)**: se pierde el único rastro de por qué el reaper
  hizo o no hizo algo. Nadie lo lee **hoy**; el día que el reaper se coma algo que no
  debía, es lo único que hay. Rotación con retención, no borrado.
- **`skill-bypass-counter-unknown`**: se pierde la evidencia forense del incidente
  (143 contra un umbral de 3, con identidad fabricada). Es la prueba que justifica
  ADR y tests. Archivar, no borrar — y arreglar primero los dos tests que escriben
  sobre el runtime real, o va a renacer.
- **Los 4 `.jsonl` sin lector**: se pierde poco, pero `chaos-weekly` tiene un rotado,
  así que hubo un productor alguna vez. Antes de borrar, confirmar si el productor
  murió o si el consumidor nunca se escribió — son dos deudas distintas.

## Lo que NO hice y por qué

- **No escribí ni borré nada bajo `.cognitive-os/`.** Todo el censo es lectura. El
  único efecto del instrumento sobre el árbol es `stat` y `read`.
- **No corrí ninguna suite ni barrido pesado.** La máquina está bajo carga con tres
  agentes ejecutando tests. El censo completo es un `os.walk` sobre el código y
  `stat` sobre el estado: segundos, sin subprocesos por archivo.
- **No propuse un cron de limpieza.** El encargo lo prohíbe con razón, y la sección
  anterior explica por qué: cuatro de las seis superficies pierden algo que gobierna
  una decisión si se las limpia sin política.
- **No toqué `hooks/orchestrator-skill-invocation-gate.sh`** (lo leí para confirmar
  que ya no consulta el contador), ni `tests/chaos/**`, ni
  `tests/audit/test_hook_payload_fidelity.py`, ni
  `tests/contracts/test_hook_quality_system.py`, ni `tests/red_team/portability/**`:
  son de otros agentes.
- **No arreglé los dos tests que escriben en el runtime real**
  (`tests/audit/test_metrics_isolation.py:216`,
  `tests/contracts/test_skill_gate_identity_and_insistence.py:340`): ambos aparecen
  modificados en `git status`, es trabajo en curso de otro. Queda reportado.
- **No registré las superficies faltantes en `state-retention.yaml`.** Registrar
  implica decidir `max_age`, `max_count`, `reaper` y `tombstone` para cada una: es
  una decisión de operador con consecuencias de borrado, no un subproducto de un
  censo.
- **No conté `edit-locks/` archivo por archivo en el JSON**: 1301 miembros como una
  familia con su peso. Enumerarlos habría inflado la salida sin agregar una decisión.
