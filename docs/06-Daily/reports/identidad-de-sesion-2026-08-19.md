# Identidad de sesión: el archivo que nadie podía leer

**Fecha:** 2026-08-19 · **Alcance:** `hooks/_lib/common.sh`, la librería que sourcean 68 hooks.

## Resumen ejecutivo

`resolve_session_dir()` no podía resolver la sesión desde ningún proceso que no
fuera `session-init`: su único fallback leía `.current-session-$$` con el PID del
lector, y ese archivo lo escribe `hooks/session-init.sh:223` con el suyo.
Consecuencia medida: **8.887 eventos** de hooks que creen segregar por sesión
cayeron al directorio global el 2026-08-19, y **0** a los seis
`.cognitive-os/sessions/*/metrics/` que existen. Los seis están **vacíos** —la
hipótesis del encargo de que 6 de 21 funcionaban es falsa: funcionan 0.
El arreglo no fue inventar un mecanismo: **`CLAUDE_CODE_SESSION_ID` ya viene
seteada en todo subproceso de hook y de Bash**, está documentada, y el repo la
usaba cero veces mientras nombraba 101 veces una variable que no existe
(`CLAUDE_SESSION_ID`, sin `CODE`). Se agregó `cos_session_id()` a `common.sh` y
`resolve_session_dir()` la usa. **El redirect de métricas quedó apagado por
defecto**: encenderlo hoy pierde datos, porque el merge de vuelta al global vive
en un hook que sufre el mismo bug y que, si se arreglara, borraría el directorio
de sesión una vez por turno.

## Correcciones a las premisas del encargo

1. **«6 de 21 directorios de sesión tienen `metrics`» es cierto, pero la lectura
   que colgaba de ese número no.** Los seis subdirectorios están **vacíos**: 0
   archivos, y su `mtime` coincide al segundo con la creación de la sesión.
   No hay ninguna sesión en la que la segregación haya funcionado.

   ```
   $ for d in .cognitive-os/sessions/*/metrics; do echo "$(basename $(dirname $d)) -> $(ls -1 $d | wc -l)"; done
   1787139789-12750-df4f90a2 -> 0
   1787139796-13248-cf8af75d -> 0
   1787160951-62498-a59d0f6a -> 0
   1787177350-95640-d6d5f379 -> 0
   1787182710-78393-fbe796dd -> 0
   1787183298-51467-3fe05b4a -> 0
   ```

2. **El motivo de los 6 no es «session-init resuelve en su propio proceso».** Es
   más simple: `hooks/session-init.sh:21` hace `mkdir -p "$SESSION_DIR/metrics"`
   incondicionalmente al abrir la sesión. Son seis directorios creados por un
   `mkdir`, no seis casos de éxito. Los otros 15 de los 21 ni siquiera son
   sesiones: son `locks/`, `current/`, `default/`, `pid-*`, `session-abc-123`,
   `test-configured` y demás fixtures.

3. **`CLAUDE_SESSION_ID` no existe.** El encargo la trata como candidata razonable
   («que el harness exporte una variable que no exporta»). La variable real es
   **`CLAUDE_CODE_SESSION_ID`**, con `CODE` en el medio:

   ```
   $ curl -sSL https://code.claude.com/docs/en/env-vars.md | grep -c CLAUDE_CODE_SESSION_ID     # 1
   $ curl -sSL https://code.claude.com/docs/en/env-vars.md | grep -cE '(^|[^_A-Z])CLAUDE_SESSION_ID'  # 0
   $ env | grep CLAUDE_CODE_SESSION_ID
   CLAUDE_CODE_SESSION_ID=93e6e34f-a5b1-4921-a480-a36496b3c566
   ```

   No se inventó una variable: **se escribió mal el nombre de una que existe**.

4. **La causa raíz está una capa más abajo de donde la puso el encargo.**
   `hooks/session-init.sh:17` se **inventa** el id de sesión
   (`$(date +%s)-$$-<rand>`) en vez de adoptar el del arnés. Por eso hizo falta un
   archivo marcador: si session-init usara el id del arnés, cualquier hook lo
   derivaría de su propio entorno sin coordinación. Hoy conviven **dos espacios de
   nombres** en `.cognitive-os/sessions/`: los seis `<epoch>-<pid>-<hash>` vacíos,
   y `93e6e34f-a5b1-4921-a480-a36496b3c566` —el id real del arnés— **vivo, con 209
   entradas y escrito ahora mismo** por otro componente.

5. **`.current-session-*` no es sólo del 20 de julio y de hoy: son cuatro y tres
   son de hoy.** Detalle menor, pero el de julio (`.current-session-367`) apunta a
   una sesión cuyo directorio ya no existe.

6. **`CLAUDE_PROJECT_DIR` está UNSET en el subproceso de Bash.** No rompe nada
   acá porque `common.sh:28` cae a `git rev-parse --show-toplevel`, pero conviene
   saberlo antes de apoyarse en ella fuera de hooks.

7. **La lane de hooks tenía ya un test al borde del timeout.**
   `test_completely_empty_stdin_no_crash[pre-commit-content-hash-dedupe.sh]` falla
   por tiempo (límite 15s, tarda 13,5–14,9s). Ese hook **no sourcea `common.sh`**,
   así que no puede verse afectado por este cambio; es deuda previa.

## La consecuencia medida

**13 hooks únicos** (resueltos por `readlink -f`, para no contar dos veces los
symlinks `hooks/` → `packages/*/hooks/`) llaman `resolve_session_dir()` y creen
estar segregando. Escriben 13 archivos `.jsonl`. Ninguno segregó nunca.

Censo, con la distinción que exige `cos_lib/measurement.Census` — un cero sin
población no es juzgable:

| archivo | eventos hoy en el **global** | eventos en `sessions/*/metrics` |
|---|---:|---:|
| `aci-observations.jsonl` | 2.850 | 0 |
| `agent-trajectory.jsonl` | 2.850 | 0 |
| `lethal-trifecta.jsonl` | 2.876 | 0 |
| `truncation-events.jsonl` | 246 | 0 |
| `skill-metrics.jsonl` | 65 | 0 |
| `large-file-reads.jsonl` | 0 (4 históricos) | 0 |
| `task-created.jsonl` | 0 (12 históricos) | 0 |
| `teammate-idle.jsonl` | 0 (12 históricos) | 0 |
| `scope-proportionality.jsonl` | 0 (4 históricos) | 0 |
| `obsidian-export`, `task-completed`, `prompt-quality`, `scope-creep` | archivo ausente | 0 |
| **total** | **8.887** | **0** |

- **Población no nula → el cero es juzgable.** 8.887 eventos demuestran que hubo
  tráfico; el cero del lado de sesión es "no segregó", no "no hubo nada que
  segregar".
- **Cuatro archivos son NO JUZGABLES por otra razón**: `obsidian-export`,
  `task-completed`, `prompt-quality` y `scope-creep` no existen ni en el global.
  Sus hooks o no están registrados o no llegaron nunca a escribir; de esos no se
  puede afirmar nada sobre segregación.

Reproducible: `.venv/bin/python3 -m pytest tests/hooks/test_session_identity_across_processes.py -v`
para el mecanismo; el conteo de arriba sale de contar líneas con `timestamp`
`2026-08-19` en `.cognitive-os/metrics/<archivo>.jsonl` y comparar contra
`ls .cognitive-os/sessions/*/metrics`.

## Por qué 6 de 21 sí funcionan

**No funcionan.** Los seis directorios existen porque `hooks/session-init.sh:21`
ejecuta `mkdir -p "$SESSION_DIR/metrics"` al abrir cada sesión, antes de que
ningún hook escriba nada. Los seis tienen 0 archivos y `mtime` igual al instante
de creación de la sesión. Los 15 restantes de los 21 no son sesiones: son
fixtures de test (`session-abc-123`, `test-configured`, `default`), directorios
de coordinación (`locks/`, `current/`) y marcadores `pid-*`.

La hipótesis del encargo —que en el proceso de `session-init` escritura y lectura
comparten PID— es **correcta como mecánica** pero **no explica los seis**:
`session-init` nunca llama a `resolve_session_dir()`; usa rutas directas.

## Las opciones y por qué elegí una

| opción | costo | veredicto |
|---|---|---|
| `.current-session` sin PID | 1 línea | **Rechazada.** Dos sesiones concurrentes sobre el mismo checkout se pisan el archivo: exactamente el caso que el SO existe para cubrir. Hay un test que lo fija (`test_dos_sesiones_concurrentes_no_se_pisan`). |
| Escritor exporta, lectores heredan | 1 línea | **Rechazada, verificada.** Los hooks son procesos **hermanos**, no hijos: el `parent_chain` de los marcadores ADR-088 muestra `session-init` en `[51626, 51467, 66524, 48908, 24825, …]` y un subproceso de Bash en `[18067, 24825, …]` — comparten el ancestro 24825 (el proceso `claude`), no una relación padre-hijo. Un `export` no viaja hacia arriba. |
| Cada hook lee `session_id` del payload y lo pasa como argumento | 13 llamadores, y **3 de ellos llaman antes de leer stdin** | **Rechazada como diseño principal.** Obliga a tocar 13 archivos y a reordenar `prompt-quality.sh:27` y `result-truncator.sh:27`, que invocan `resolve_session_dir` **antes** de su `INPUT="$(cat)"`. |
| Derivar de `transcript_path` | parseo de ruta | **Innecesaria.** El id viene ya limpio en una variable. |
| **`CLAUDE_CODE_SESSION_ID` del entorno** | **4 líneas, 0 llamadores tocados** | **Elegida.** |

**Motivo escrito.** `resolve_session_dir()` es una función de librería: no ve el
`$INPUT` del hook, pero **sí ve su propio entorno**. La documentación oficial
(`env-vars.md:339`) dice que `CLAUDE_CODE_SESSION_ID` se setea automáticamente en
subprocesos de Bash **y de comandos de hook**, y que coincide con el campo
`session_id` del payload. Verificado en este entorno: la variable está presente y
su valor nombra un directorio vivo bajo `.cognitive-os/sessions/`. Es la única
opción que resuelve para los 13 llamadores sin tocar ninguno, funciona para hooks
que no leen stdin, y separa dos sesiones concurrentes por construcción.

Se implementó `cos_session_id()` en `hooks/_lib/common.sh`, con la precedencia de
`scripts/_lib/session-id.sh` —la primitiva que ya existía para los locks de
edición— extendida con el idioma del payload que ya estaba en
`hooks/orchestrator-skill-invocation-gate.sh:36`. No hay mecanismo nuevo:

1. `COGNITIVE_OS_SESSION_ID` (override explícito del SO)
2. **`CLAUDE_CODE_SESSION_ID`** (arnés, documentada, presente)
3. `CODEX_SESSION_ID`
4. `CLAUDE_SESSION_ID` (no existe; se deja última porque el repo la nombra 101 veces)
5. payload ya cacheado en `$_STDIN_JSON` — **nunca consume stdin**
6. `$INPUT` de los hooks que hacen su propio `cat`
7. `.current-session-$$` legacy (sólo resuelve dentro de `session-init`; se conserva porque `scripts/commit_provenance.py` la lee)

Los pasos 5 y 6 no son redundantes con el 2: cubren el arnés que mande payload sin
setear la variable, y hay un test que fija que **no** consuman stdin.

## La prueba en las dos direcciones

`tests/hooks/test_session_identity_across_processes.py` — prueba el **efecto**
(que la métrica aterrice en el directorio correcto), no el exit code.

**Dirección 1 — con `common.sh` previo al fix, el mismo escenario falla:**

```
$ cp $SCRATCH/common.sh.bak hooks/_lib/common.sh
$ .venv/bin/python3 -m pytest tests/hooks/test_session_identity_across_processes.py -q
E   AssertionError: resolvio a .../proj/.cognitive-os/metrics
    assert '/private/var...ve-os/metrics' == '/private/var...05b4a/metrics'
      - nitive-os/sessions/1787183298-51467-3fe05b4a/metrics
      + nitive-os/metrics
E   AssertionError: assert '' == '1787183298-51467-3fe05b4a'
E   AssertionError: assert '.../proj/.cognitive-os/metrics' != '.../proj/.cognitive-os/metrics'
FAILED ...::test_hook_en_otro_proceso_resuelve_la_sesion_del_payload
FAILED ...::test_hook_que_lee_su_propio_input_tambien_resuelve
FAILED ...::test_dos_sesiones_concurrentes_no_se_pisan
3 failed, 3 passed in 0.31s
```

El tercer fallo es el más elocuente: con el código viejo, **dos sesiones
concurrentes resuelven al mismo directorio global** — el `!=` compara dos rutas
idénticas.

**Dirección 2 — con el fix:**

```
$ .venv/bin/python3 -m pytest tests/hooks/test_session_identity_across_processes.py -v
test_codigo_previo_al_fix_no_resuelve_la_sesion PASSED                   [ 11%]
test_hook_en_otro_proceso_resuelve_la_sesion_del_payload PASSED          [ 22%]
test_resolve_session_dir_no_consume_stdin PASSED                         [ 33%]
test_hook_que_lee_su_propio_input_tambien_resuelve PASSED                [ 44%]
test_default_sigue_escribiendo_al_global PASSED                          [ 55%]
test_dos_sesiones_concurrentes_no_se_pisan PASSED                        [ 66%]
test_claude_code_session_id_resuelve_sin_payload PASSED                  [ 77%]
test_claude_session_id_sin_code_no_es_la_variable_del_arnes PASSED       [ 88%]
test_codigo_previo_al_fix_tampoco_lee_la_variable_del_arnes PASSED       [100%]
9 passed in 0.63s
```

`test_codigo_previo_al_fix_*` no compara contra un backup del scratchpad: busca
en `git log` la última versión commiteada de `common.sh` **sin** `cos_session_id`,
para seguir apuntando al código defectuoso después de commitear el arreglo.

Prueba adicional, fuera de pytest, de que la vía del entorno funciona en un
proceso cualquiera sin payload alguno:

```
$ /bin/bash -c 'source hooks/_lib/common.sh; echo "cos_session_id -> $(cos_session_id)"'
cos_session_id -> 93e6e34f-a5b1-4921-a480-a36496b3c566
```

Un detalle que vale como evidencia: al agregar la vía del arnés, **tres tests que
pasaban empezaron a fallar** porque el proceso de pytest hereda la
`CLAUDE_CODE_SESSION_ID` real y, por precedencia, ganaba sobre el payload del
fixture. Hubo que limpiarla en `_clean_env`. Que eso haya ocurrido es la
demostración de que la variable está seteada de verdad en cada subproceso.

## Radio de impacto: qué cambia en runtime

**Nada, por defecto. A propósito.**

`resolve_session_dir()` devuelve el directorio de sesión sólo si
`COS_SESSION_SCOPED_METRICS=1` (o si `COGNITIVE_OS_SESSION_ID` viene seteada
explícitamente, que era la única vía que funcionaba antes — se preserva para no
alterar comportamiento existente). Sin eso, sigue devolviendo el global, y hay un
test que lo fija (`test_default_sigue_escribiendo_al_global`).

**Por qué no se encendió**, que es la parte importante:

1. **La ruta de merge está muerta.** `hooks/session-cleanup.sh` es quien devuelve
   las métricas de sesión al global (Step 1, `merge_metrics_on_exit: true`, con
   locking) y resuelve la sesión con el **mismo** `.current-session-$$` imposible
   (`session-cleanup.sh:18`). Encender la segregación sin arreglar eso deja 13
   `.jsonl` fuera del alcance de los consumidores del global — y no son pocos:
   `skill-metrics.jsonl` se nombra en **45** lugares del repo,
   `aci-observations.jsonl` en 14, `truncation-events.jsonl` en 12. Además hay 4
   consumidores que hacen `metrics_dir.glob("*.jsonl")` sin nombrar archivo
   (`cos_lib/primitive_fitness.py:187`, `cos_lib/promote_from_telemetry.py:161`,
   `scripts/cos_false_positive_ledger.py:121`, `cos_lib/sprint_test_aggregator.py:265`).

2. **Arreglar ese merge tampoco es libre — y acá hay una mina.**
   `session-cleanup.sh` está registrado en **`Stop`**, que dispara **una vez por
   turno**, no al cerrar la sesión. Con `cleanup_on_exit: true` (el default en
   `cognitive-os.yaml:181`) su Step 4 borra el directorio de sesión
   (`session-cleanup.sh:125`), su Step 3 suelta los locks de la sesión (`:118`) y
   su Step 2 la desregistra de `active-sessions.json`. **Hoy no destruye nada sólo
   porque el mismo bug de identidad lo hace salir en el `exit 0` de la línea 26.**
   Arreglarle la resolución "para completar el fix" convertiría un bug latente en
   destrucción de estado por turno — incluidos los locks que
   `concurrent-write-guard` recién empezó a tomar hoy (commit `82969b80f`).

O sea: la identidad ya se resuelve bien; el redirect espera a que se resuelva
`Stop` vs `SessionEnd`. Ambos motivos están escritos en el comentario de
`resolve_session_dir()`, no sólo acá.

**Lanes corridas** (`hooks/_lib/common.sh` la sourcean **68** hooks):

- `tests/hooks/` → **1119 passed, 1 skipped, 0 failed** (225,7 s) en la corrida
  final, con el arreglo completo aplicado. Una corrida intermedia había mostrado
  un fallo en `test_completely_empty_stdin_no_crash[pre-commit-content-hash-dedupe.sh]`
  por timeout; ese hook **no sourcea `common.sh`**, en aislamiento tarda 13,5 s y
  14,9 s contra un límite de 15 s, y no reprodujo. Es un flake de tiempo
  preexistente, no una regresión.
- `tests/contracts/` → **859 passed, 4 failed, 4 skipped, 16 xfailed** (711 s).
  Los 4 fallos son **previos y ajenos**: reproducen idénticos contra el
  `common.sh` anterior al arreglo, y ninguno de los cuatro archivos de test
  nombra `common.sh`, `resolve_session_dir` ni `cos_session_id`.

  ```
  $ cp $SCRATCH/common.sh.bak hooks/_lib/common.sh   # version PRE-fix
  $ .venv/bin/python3 -m pytest <los 4 tests> -q
  assert 407.79 < 400.0
  .../test_ram_ceiling.py:113: AssertionError: .cognitive-os/ disk usage 407.8 MiB exceeds ceiling 400.0 MiB
  FAILED tests/contracts/test_portable_ai_completion.py::test_adapter_manifests_are_generated_for_profiles
  FAILED tests/contracts/test_portable_ai_overlay.py::test_portable_ai_overlay_is_generated_and_current
  FAILED tests/contracts/test_primitive_harness_partial_ratchets.py::test_primitive_harness_partial_debt_does_not_regress
  FAILED tests/contracts/test_ram_ceiling.py::test_so_vitals_reports_disk_under_ceiling
  4 failed in 9.89s
  ```

  Los dos `portable_ai_*` y el ratchet de primitivas son consistentes con el
  trabajo simultáneo de otros agentes sobre hooks y perfiles; el de disco es
  ambiental (`.cognitive-os/` pesa 407,8 MiB contra un techo de 400).

## Lo que NO ejecuté y por qué

- **No encendí la segregación de métricas.** Motivo arriba: merge muerto + `Stop`
  que borraría el directorio de sesión por turno. El encargo autoriza
  explícitamente traerlo como propuesta si el impacto es grande. Lo es.
- **No toqué `hooks/session-cleanup.sh`.** Arreglarle la identidad sin antes
  decidir `Stop` vs `SessionEnd` es activar la mina, no desactivarla.
- **No reconcilié `session-init.sh` con el id del arnés**, que es la continuación
  natural: mueve `active-sessions.json`, `session-cleanup`, `commit_provenance.py`
  y el naming de los directorios de sesión. Merece su propia decisión.
- **No borré los cuatro `.current-session-*` huérfanos.** Es el verde barato
  literal que el encargo prohíbe, y además `scripts/commit_provenance.py:157`
  todavía los lee como fallback de compatibilidad.
- **No corregí los ~101 usos de `CLAUDE_SESSION_ID`** repartidos por el repo. Es
  una barrida aparte, con su propia medición; acá sólo quedó fijada la precedencia
  correcta y un test que la defiende.
- **No registré ningún hook nuevo ni toqué `.claude/settings.json`** ni
  `cognitive-os.yaml` (este último lo está editando otro agente).

## Archivos

- `hooks/_lib/common.sh` — `cos_session_id()` nueva; `resolve_session_dir()` la usa.
- `tests/hooks/test_session_identity_across_processes.py` — 9 tests, prueba de efecto en las dos direcciones.
