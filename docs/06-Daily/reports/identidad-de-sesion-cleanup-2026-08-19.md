# Identidad de sesión en el hook de cleanup: el borrado que faltaba desarmar

**Fecha:** 2026-08-19/20 · **Alcance:** `hooks/session-cleanup.sh`, `scripts/session-cleanup-counterfactual.sh` y sus tests.
**Commit:** `cf3f445b7`. **Precedentes:** `4d9bec980` (paso 1, archive-first), `adafefb66` (`cos_session_id()` en `common.sh`).

## Resumen ejecutivo

El paso 2 hacía falta, y era **más grande** de lo que decía el encargo. Sí:
`_deregister_session` corría incondicionalmente en cada turno. Pero abajo había
algo peor: **el guard de vitalidad que el paso 1 instaló es una tautología**.
`_session_owner_alive` leía `meta.json.pid`, y ahí `session-init.sh:29` escribe
el PID de su propio subproceso, que vive segundos. Las **10** sesiones en disco
dan ese PID como muerto —incluida una abierta hace dos horas mientras su sesión
seguía viva—. O sea que arreglar la identidad hacia el árbol de `session-init`
habría archivado una sesión **viva** en cada turno, con el guard diciendo que sí.

El arreglo no es una heurística mejor: es el único hecho que un hook de `Stop`
puede afirmar gratis. **`Stop` dispara DENTRO de la sesión, así que la sesión en
la que corre está viva por construcción**, y ningún PID puede desmentirlo. El
PID queda para una sesión ajena, con una ventana de gracia por `mtime` encima.

## Correcciones a las premisas del encargo

1. **El entregable ya existía, escrito por otro agente.**
   `docs/06-Daily/reports/identidad-de-sesion-2026-08-19.md` está **commiteado**
   (`adafefb66`), 315 líneas, y cubre `hooks/_lib/common.sh`. Escribir el mío en
   esa ruta lo habría pisado. Va en `identidad-de-sesion-cleanup-2026-08-19.md`.

   ```
   $ git log --oneline -1 -- docs/06-Daily/reports/identidad-de-sesion-2026-08-19.md
   adafefb66 fix(sesion): que un hook pueda saber en que sesion esta
   ```

2. **`CLAUDE_CODE_SESSION_ID` ya estaba adoptada; la parte de identidad estaba
   medio hecha.** El encargo la plantea como pendiente. `cos_session_id()` existe
   en `common.sh` desde `adafefb66` y ya resuelve por esa variable. Lo que
   faltaba era que el hook de cleanup la **usara** — no descubrirla.

3. **«El paso 1 desarmó el borrado» es cierto a medias.** Reemplazó el borrado
   por `mv` (recuperable: bien), pero la **condición** que agregó nunca es falsa
   sobre el árbol de `session-init`. Un guard que siempre dice "muerta" no
   contiene nada; lo único que contenía el daño era que la identidad no
   resolviera. Medición:

   ```
   $ for d in .cognitive-os/sessions/*/; do [ -f "$d/meta.json" ] || continue; \
       pid=$(jq -r .pid "$d/meta.json"); \
       ps -p "$pid" >/dev/null 2>&1 && echo "$(basename $d) ALIVE" || echo "$(basename $d) DEAD"; done
   1787139789-12750-df4f90a2 DEAD
   ... (10/10 DEAD, incluida 1787190815-50188-3dbfb933, start 01:53:35 de hoy)
   ```

4. **El encargo dice «301 borrados sobre sesiones vivas» con objetivo
   `.cognitive-os/sessions/<uuid>/`. El objetivo depende de qué identidad se
   elija, y el árbol del uuid NO se habría borrado.** No tiene `meta.json`, así
   que `_session_owner_alive` devuelve 0 ("viva") y el paso 4 nunca corre. El
   árbol en peligro era el **otro**, el de `session-init`. Ver la sección
   siguiente.

5. **`session_id` vacío en las 294.333 filas: confirmado, y no cambia el diseño.**
   Recontado sobre 296.383 filas: **1** valor distinto de `session_id`, y es `""`.
   Es un defecto del *wrapper* de telemetría (`scripts/hook-timing-wrapper.sh`),
   no del hook, y no afecta la resolución de identidad, que sale del entorno.

6. **Encontré una muerte que el encargo no mencionaba, y que la identidad sola no
   arreglaba: `flock` no existe en macOS.**

   ```
   $ command -v flock ; echo "exit=$?"
   exit=1
   ```

   `_deregister_session` lo llamaba sin fallback y sin `|| true` (a diferencia
   del merge del paso 1 y del paso 5, que sí degradan). O sea que el paso 2 **no
   podía correr en esta plataforma ni con la identidad resuelta**. Se ve en la
   corrida B: dueño probadamente muerto, directorio archivado, y la sesión seguía
   en `active-sessions.json`. Corregido con el mismo lock por `mkdir` que el
   archivo ya usa.

## El paso 2: ¿hacía falta? La evidencia

**Sí.** Dos hallazgos, uno esperado y uno no.

**a) La cadencia de `Stop` sigue siendo por turno.** Recontada hoy sobre 296.383
filas (el encargo citaba 286.163):

```
filas totales: 296383
disparos session-cleanup: 344
max session-cleanup dentro de una ventana SessionStart->SessionStart: 41
```

**b) `_deregister_session` no tenía guard alguno.** El paso 3 (locks) y el paso 4
(retiro del directorio) sí lo tenían desde el paso 1; el paso 2 corría suelto,
entre los dos. Con la identidad resuelta, eso da de baja del registro a una
sesión que sigue trabajando, hasta 41 veces por ventana. Y es el peor de los
tres para detectar, porque **no deja rastro en disco** — es exactamente por eso
que sobrevivió al paso 1, que se enfocó en lo visible.

Consumidores que quedan viendo una sesión de menos: `scripts/cos_coordination_status.py:62`,
`scripts/cos_task_claims.py:56`, `cos_lib/concurrent_agent_safety_status.py:184`.

## A qué apunta cada identidad, medido

Hay **dos espacios de nombres** conviviendo en `.cognitive-os/sessions/`:

| | `session-init` (`<epoch>-<pid>-<rand>`) | arnés (`<uuid>` = `CLAUDE_CODE_SESSION_ID`) |
|---|---|---|
| Cantidad en disco | 10 | 1 (`93e6e34f-…`, la sesión viva) |
| `meta.json` | **sí** (10/10) | **no** |
| `metrics/` | **sí** (10/10), **vacío** (0 archivos) | **no** |
| Contenido | `tasks.json`, `test-baseline.txt` | **219** contadores `subagent-tool-calls-*` |
| Quién escribe | `hooks/session-init.sh:21` | `hooks/subagent-budget-enforcer.sh:106` |
| Registrado en `active-sessions.json` | sí (y luego podado) | no |
| Locks con ese id | 0 | **21/21** |

```
$ for d in .cognitive-os/sessions/*/; do printf '%-40s meta=%s metrics=%s files=%s\n' \
    "$(basename $d)" "$([ -f $d/meta.json ] && echo Y || echo N)" \
    "$([ -d $d/metrics ] && echo Y || echo N)" "$(ls -1 $d/metrics 2>/dev/null | wc -l)"; done
$ for f in .cognitive-os/sessions/locks/*.lock; do jq -r .session_id "$f"; done | sort | uniq -c
  21 93e6e34f-a5b1-4921-a480-a36496b3c566
```

Consecuencias de elegir el **uuid del arnés** (que es lo que hice):

- **Paso 3 (locks): pasa de muerto a correcto.** Los 21 locks llevan ese id
  —`hooks/concurrent-write-guard.sh:45` los estampa con el `session_id` del
  payload—, así que es la única identidad con la que ese paso matchea algo.
- **Paso 1 (merge): inerte hoy, y no por accidente.** El árbol del uuid no tiene
  `metrics/`; los 10 de `session-init` lo tienen **vacío**. No hay métrica que
  mergear porque el redirect está apagado (ver más abajo). El merge se enciende
  solo si se enciende el redirect, y ahí sí escribe en ese mismo árbol: el
  circuito cierra.
- **Paso 4 (archivado): inalcanzable para la propia sesión, que es lo correcto.**

Elegir el id de `session-init` habría sido la trampa: es el árbol con `meta.json`,
o sea el único donde el guard tautológico dispara.

## Las tres corridas

`bash scripts/session-cleanup-counterfactual.sh <dir-temporal>` — por efecto en
disco, nunca por exit code. El hook sale 0 en los tres casos.

```
### RUN A - la sesion esta VIVA (es la del propio proceso)
  session dir  : EXISTE
  contenido    : INTACTO en su lugar
  archivado    : NO
  registrada   : ["fake-session-abc123"]
  merge global : SI (2 lineas)

### RUN B - duenio PROBADAMENTE MUERTO (sesion ajena, PID 93631, fuera de gracia)
  -- despues del disparo 1 --
  session dir  : BORRADO
  contenido    : INTACTO en el archivo (nada se destruyo)
  archivado    : SI -> archive/sessions/fake-session-abc123
  registrada   : []
  merge global : SI (2 lineas)
  -- despues del disparo 2 (el merge NO debe duplicar) --
  archivado    : SI -> archive/sessions/fake-session-abc123
  merge global : SI (2 lineas)          <-- incremental por offset, no duplico

### RUN C - CONTRAFACTICO: identidad arreglada + el borrado que desarmo el paso 1
  session dir  : BORRADO
  contenido    : DESTRUIDO
  archivado    : NO
  registrada   : []

### Integridad del arbol
  sha256 antes  : 8dbb9e58d2913a87801eafa301c9c875315ca6bf6567afb48a73b579f3605dcd
  sha256 despues: 8dbb9e58d2913a87801eafa301c9c875315ca6bf6567afb48a73b579f3605dcd
  -> IDENTICO (el contrafactico nunca toco el repo)
```

El PID muerto no se inventa: se arranca un proceso, se espera a que muera y se
confirma con `ps` que ya no está. RUN C corre sobre una **copia mutada** en un
temporal, así que el árbol nunca se toca —el script lo verifica por `sha256`, no
por promesa—. RUN C reproduce el daño sobre la misma sesión que RUN A prueba
viva: el modelo del defecto se sostiene.

**Dos falsos verdes que el propio contrafáctico destapó**, y que valen más que el
resultado final:

1. **RUN B daba "no archivado" con el dueño muerto.** El merge crea
   `.merge-offsets` dentro del directorio de sesión, eso le mueve el `mtime`, y
   la ventana de gracia veía la escritura **del propio hook** como prueba de
   vida. El hook se declaraba a sí mismo prueba de que la sesión estaba viva.
   Arreglado fijando el veredicto **una sola vez, antes del paso 1**.
2. **RUN C daba "sin daño" y era mentira.** El `setup()` limpiaba el temporal y
   se llevaba puesto el mutante, y el `bash` sobre un archivo inexistente fallaba
   en silencio con la salida redirigida. El mutante se mudó fuera del temporal y
   ahora se valida con `bash -n` antes de correrlo.

Tests que lo fijan: `tests/hooks/test_session_cleanup_identity_and_liveness.py`
(8) y `tests/red_team/portability/test_session-cleanup-counterfactual.py` (4).

El test de portabilidad viejo afirmaba `"BORRADO" not in stdout` sobre la salida
**entera**. Con una corrida alcanzaba; con tres no distingue el caso bueno del
malo, porque en RUN B el retiro es correcto y en RUN C el daño es el objetivo.
Pasa a afirmar por bloque, y **agrega la dirección que le faltaba**: que RUN C
reproduzca el daño. Si no lo reproduce, falla.

## Qué decidí sobre `COS_SESSION_SCOPED_METRICS` y por qué

**Queda apagado.** Con la identidad arreglada el circuito **ya cierra** —lo
verifiqué, no lo supuse— y ése era el motivo escrito la vez anterior, que ahora
caducó. El motivo nuevo es otro:

```
=== 1. un hook escribe con COS_SESSION_SCOPED_METRICS=1 ===
   resuelve a: /.cognitive-os/sessions/sesion-redirect/metrics
   landed en sesion: skill-metrics.jsonl
   global tiene    : (vacio)
=== 2. el Stop de la MISMA sesion (viva) intenta mergear ===
   global skill-metrics.jsonl: 1 lineas          <-- el merge SI vuelve
   dir de sesion sigue?      : SI
=== 3. ventana de invisibilidad ===
   sesion tiene: 2 lineas
   global tiene: 1 lineas   <-- lo que ve el consumidor hasta el proximo Stop
```

El circuito cierra, pero pasa a ser **consistente sólo al final de cada turno**.
Entre una escritura y el próximo `Stop`, el global está atrasado. Y lo leen
**228** archivos bajo `scripts/`, `cos_lib/`, `lib/` y `hooks/`, sobre **123**
`.jsonl` distintos:

```
$ grep -rIl "cognitive-os/metrics" --include='*.py' --include='*.sh' scripts/ cos_lib/ lib/ hooks/ | wc -l
228
$ ls -1 .cognitive-os/metrics/*.jsonl | wc -l
123
```

Encenderlo es cambiar un contrato de lectura de 228 consumidores, de "lo que pasó
hasta recién" a "lo que pasó hasta el turno anterior". Ninguno de los 228 está
auditado para tolerarlo, y un consumidor que lee dentro del mismo turno en que se
escribió —cualquier gate que mire su propia métrica— pasaría a ver cero. Eso es
un cambio propio, con su propia auditoría; no un efecto colateral de un arreglo
de identidad. **Lo que faltó la vez anterior era el motivo escrito: acá está.**

## `active-sessions.json`: ¿mismo defecto o no?

**Mismo defecto de fondo, otro archivo, y fuera de mi territorio.**

`{"sessions": []}` con 10 árboles de `session-init` en disco. No es que la
registración falle: `session-init.sh:171` registra bien. Lo que pasa es que
registra `--arg pid "$$"` — **el mismo PID efímero** que va a `meta.json`. Y
`_schedule_active_sessions_prune` (mismo archivo) corre un podador que saca del
registro toda entrada cuyo PID esté muerto pasada una gracia de 900 s
(`COS_ACTIVE_SESSION_PRUNE_GRACE_SECONDS`). Como el PID muere a los segundos,
**toda sesión se autopoda a los 15 minutos de abierta**.

Es la misma raíz que la tautología del guard: *un PID efímero usado como dueño de
la sesión*. Pero el arreglo vive en `hooks/session-init.sh`, que **no es mi
territorio** — y tocarlo mueve también `commit_provenance.py`, que todavía lee el
marcador `.current-session` por PID. **No lo toqué.** Lo que sí hice es que mi
hook no empeore el registro: sin prueba de muerte, no deregistra.

Arreglo natural, para quien siga: que `session-init` guarde el PID del proceso
del arnés (`CLAUDE_PID`, verificado presente y de vida larga:
`ps -o comm= -p $CLAUDE_PID` → el binario de `claude`) en vez del `$$` del script,
y que adopte `CLAUDE_CODE_SESSION_ID` como id en lugar de inventarse uno.

## Lo que NO hice y por qué

- **No toqué `hooks/session-init.sh`.** Es donde vive la raíz del PID efímero y
  del segundo espacio de nombres, pero está fuera del territorio asignado y
  arrastra `commit_provenance.py`. Queda escrito arriba con el arreglo propuesto.
- **No encendí `COS_SESSION_SCOPED_METRICS`.** Motivo medido arriba.
- **No toqué `.cognitive-os/`** (registro, métricas, directorios de sesión): es
  estado de runtime del operador y hay sesiones vivas escribiéndolo. Todas las
  pruebas corren sobre proyectos temporales.
- **No reconcilié los dos espacios de nombres.** Es el cambio que sigue, y es más
  grande que este: mueve `session-init`, `active-sessions.json`,
  `commit_provenance.py` y el reaper de ADR-119.
- **No hice que el paso 4 archive la propia sesión bajo ninguna condición.** Un
  hook que dispara 41 veces por ventana no tiene la evidencia que ADR-119 sí
  tiene (PID, contenido pendiente, ventana de gracia). Retirar sesiones es
  trabajo de `cos_lib/session_lifecycle.py` vía `scripts/so-reaper.sh`.
- **No moví ningún baseline ni suprimí ninguna regla.** El único test que falló
  (`"BORRADO" not in stdout`) se reescribió más estricto, no más laxo.
