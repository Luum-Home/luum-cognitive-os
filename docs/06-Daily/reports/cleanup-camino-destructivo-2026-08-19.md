# El camino destructivo de session-cleanup.sh — 2026-08-19

## Resumen ejecutivo

La cadena se sostiene: los cinco eslabones son reales y el camino destructivo
estaba armado y desactivado únicamente por el bug de identidad. `Stop` dispara
**por turno**, no al cerrar sesión: 339 disparos de `session-cleanup` contra 75
aperturas de sesión, con hasta 44 dentro de una misma ventana. Con la identidad
resuelta y el código anterior, **301 disparos** habrían ejecutado `rm -rf` sobre
el directorio de una sesión viva. El daño era peor de lo descrito: con el id del
arnés el objetivo no habría sido el directorio de `session-init` sino
`.cognitive-os/sessions/<uuid>/`, el estado vivo de presupuesto de subagentes
(210 contadores), donde además no hay métricas que mergear — puro destruir, cero
beneficio. Arreglado el camino (merge incremental, locks solo de PID muerto,
archivado en vez de borrado, según ADR-119), sin tocar la identidad ni
`COS_SESSION_SCOPED_METRICS`. Seis tests nuevos en dos direcciones, verde.

## Correcciones a las premisas del encargo

1. **`cleanup_on_exit: true` no está activo "en la configuración de hoy": está
   activo porque el hook nunca lee ninguna configuración.** El hook lee
   `$PROJECT_DIR/.cognitive-os/cognitive-os.yaml` (`:34`) y ese archivo **no
   existe**:

   ```
   $ ls .cognitive-os/cognitive-os.yaml
   ls: .cognitive-os/cognitive-os.yaml: No such file or directory
   $ find . -name cognitive-os.yaml -not -path './node_modules/*'
   ./cognitive-os.yaml
   ./primitive_coverage/adapters/cognitive-os.yaml
   ./examples/hello-world/cognitive-os.yaml
   ./.cognitive-os/runtime/edit-locks/cognitive-os.yaml
   ```

   El valor sale del default hardcodeado en `session-cleanup.sh:32`. El
   `cognitive-os.yaml:181` de la raíz sí dice `cleanup_on_exit: true`, pero es
   decorativo: **poner `false` ahí no habría desactivado nada.** El efecto neto
   coincide con la premisa; el mecanismo no, y la diferencia importa porque el
   operador creía tener una perilla que no está conectada.

2. **El daño no era "el directorio de sesión": eran dos directorios distintos y
   el hook habría atacado el equivocado.** Conviven dos espacios de nombres bajo
   `.cognitive-os/sessions/`: el que `session-init.sh:17` se inventa
   (`<epoch>-<pid>-<rand>`, con `metrics/` adentro) y el del arnés
   (`CLAUDE_CODE_SESSION_ID`, un UUID). `cos_session_id()` devuelve el del arnés.
   Ese directorio UUID existe, está vivo y lo escribe
   `hooks/subagent-budget-enforcer.sh:106` — 210 contadores
   `subagent-tool-calls-*` al momento de medir — y **no tiene subdirectorio
   `metrics/`**. Conclusión que el encargo no anticipaba: arreglarle la identidad
   al hook no habría "encendido el merge y de paso borrado"; habría borrado
   estado vivo de runtime **sin mergear una sola métrica**.

3. **Había un cuarto defecto que el encargo no menciona y que también se arma con
   la identidad: el merge no era idempotente.** El paso 1 hacía
   `cat "$metric_file" >> "$global_file"` en cada disparo. Con `Stop` por turno,
   cada turno reapendaba el archivo entero: el global habría quedado con N copias
   de las mismas filas. Es "recuperable" en el sentido de que no borra, pero
   corrompe el dato igual.

4. **El contrato escrito relevante es ADR-119, no ADR-047.** ADR-047 (Session
   Lifecycle Management) está `status: proposed`, `implementation_status:
   planned`, y trata del reaper de **procesos** huérfanos (watchdog, Phase B
   bloqueada por gate); sus dos únicas menciones a `SessionEnd` son un diagrama
   y una fila de una tabla de portabilidad. No gobierna este hook. ADR-119
   (Session Filesystem Reaper) sí: `status: implemented`, manda **archive-first**
   sobre `.cognitive-os/sessions/`, con estados `KEEP_ACTIVE` /
   `KEEP_PENDING_CONTENT` / `KEEP_RECENT_GRACE` y borrado recién en
   `RM_ARCHIVED`. Está realmente implementado y cableado
   (`hooks/_lib/session-fs-reap.sh`, invocado por `scripts/so-reaper.sh:305`,
   destino `.cognitive-os/archive/sessions/` con 405 entradas). O sea: el
   `rm -rf` no era solo peligroso, **contradecía un contrato implementado**.

5. **Un test defendía el bug.** `test_cleanup_removes_session_directory`
   (`tests/unit/test_session_lifecycle.py:360`) sólo exigía
   `not session_dir.exists()`. Cualquier forma de hacer desaparecer el
   directorio pasaba, incluido el `rm -rf` incondicional. Reescrito contra el
   contrato de ADR-119: ahora verifica el **destino** (archivado), no la
   ausencia.

6. **El limitante de "no soltar locks" es más suave de lo que sugiere el
   encargo, y eso refuerza la conclusión en vez de debilitarla.** Un lock
   colgado no es permanente: `concurrent-write-guard.sh` lo recicla solo cuando
   supera `LOCK_TIMEOUT` (300 s) o cuando su PID está muerto (`:104-:112`). Es
   decir, la asimetría que plantea el encargo —soltar a mitad de sesión es peor
   que dejar colgado— es correcta **y además barata de respetar**: el costo
   máximo de no soltar es 300 s.

7. **Restricciones del entorno, verificadas y no sólo aceptadas.**
   `hooks/**` es efectivamente ruta protegida: el guard me bloqueó dos veces y
   sólo pasó con `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` (confirmado). Pero hay un
   choque que el encargo no anticipa: `~/.claude/hooks/block-destructive-bash.sh`
   bloquea cualquier comando donde aparezca `/bin/bash` como token de path
   ("targets a path OUTSIDE the repo"), así que la regla 6 del encargo
   (validar con `/bin/bash -n` absoluto) **sólo se puede cumplir con el prefijo
   de bypass**. Se hizo así; queda anotado porque la próxima persona va a
   tropezar igual.

8. **No toqué `hooks/secret-detector.sh`** (agente hermano) ni ningún archivo de
   los 30 que `git status` mostraba modificados por el orquestador. Commit con
   paths explícitos, sin `git add`, sin push.

## Los cinco eslabones, verificados uno por uno

| # | Afirmación del encargo | Veredicto | Evidencia |
|---|---|---|---|
| 1 | `session-cleanup.sh:18` tiene el mismo fallback imposible | **Se sostiene** | `sed -n '14,27p' hooks/session-cleanup.sh` → `SESSION_FILE="$SESSIONS_DIR/.current-session-$$"`, con `$$` = PID del propio hook; el escritor es `session-init.sh:223`, con SU PID |
| 2 | Está registrado en `Stop` y `Stop` dispara por turno | **Se sostiene** | ver sección siguiente |
| 3 | `cleanup_on_exit: true` efectivamente activo | **Se sostiene, con matiz** | activo por *default hardcodeado* (`:32`), no por configuración — ver corrección 1 |
| 4 | `:125` borra el directorio y `:118` suelta locks | **Se sostiene** | `:124-126` `rm -rf "$SESSION_DIR"` bajo `CLEANUP_ON_EXIT=true && -d "$SESSION_DIR"`; `:113-121` `rm -f "$lockfile"` para todo lock cuyo `.session_id` sea el de la sesión, **sin mirar si el escritor vive** |
| 5 | El `exit 0` de `:26` es lo único que lo detiene hoy | **Se sostiene** | contrafáctico ejecutado, abajo |

Contrafáctico del eslabón 5, sobre proyecto temporal
(`scripts/session-cleanup-counterfactual.sh`, nunca sobre `.cognitive-os/` real), con el
código **anterior**:

```
### RUN A - como corre HOY (identidad rota)
  session dir : EXISTE
  locks       : aaa.lock bbb.lock
  merge global: NO
### RUN B - identidad ARREGLADA (COGNITIVE_OS_SESSION_ID seteado)
  session dir : BORRADO
  locks       : bbb.lock          <- se llevó el lock de la sesión
  merge global: SI (1 lineas)
```

Una sola variable de entorno separa "no hace nada" de "borra el directorio y
suelta el lock". El eslabón 5 es exacto.

## Stop: ¿por turno o al cerrar?

**Por turno.** Y esto es lo que convierte todo lo demás en un problema.

`manifests/claude-code-hooks-schema.yaml:250` transcribe `Stop` pero **no tiene
campo `fires_when`** — la pregunta que decide el caso es justamente la que el
manifiesto no contesta (deuda anotada abajo). Se resolvió con telemetría, sobre
el archivo vivo **más los rotados**:

```bash
python3 scripts/session_stop_fire_census.py   # lee hook-timing.jsonl + .archive/hook-timing-*.jsonl.gz
```

```
filas totales de telemetria      : 289187
aperturas de sesion (SessionStart): 75
disparos de session-cleanup (Stop): 339
maximo de disparos en UNA ventana : 44
disparos INEQUIVOCAMENTE a mitad de sesion: 301
distribucion por ventana: [(0,37),(1,8),(2,6),(3,6),(4,3),(5,2),(6,1),(7,1),(8,1),
                           (15,1),(17,1),(19,2),(23,1),(24,1),(28,2),(41,1),(44,1)]
```

44 disparos dentro de una única ventana `SessionStart → SessionStart` no admiten
la lectura "dispara al cerrar". Los 301 disparos que no son el último de su
ventana son, inequívocamente, disparos con la sesión viva: **301 borrados de una
sesión en curso** si la identidad se hubiera arreglado sola.

`SessionEnd` sí existe como evento del arnés (tiene presupuesto propio en el
esquema, `:419`: 1,5 s compartidos, ampliable a 60 s con `timeout` explícito),
pero **este repo no registra ningún handler en él** (`:183`), y el hook declara
en su cabecera que necesita <10 s. Mover la registración no es gratis y no se
hizo — ver "Qué NO ejecuté".

## El orden correcto de arreglo

La pregunta del encargo —¿qué hay que arreglar primero para que lo segundo sea
seguro?— tiene una respuesta que el contrafáctico deja sin ambigüedad:

1. **Primero, desarmar el camino destructivo** (borrado, locks, merge no
   idempotente). Mientras el `rm -rf` esté ahí, cualquier arreglo de identidad
   —en este hook o en el `common.sh` que ya lo comparte— arma la bomba.
2. **Después, el evento**: `session-cleanup` no debería vivir en `Stop`. Un
   cleanup de sesión en un evento por turno es una contradicción de nombre.
3. **Recién al final, la identidad de sesión** — y con el evento ya corregido,
   porque incluso sin borrado, deregistrar la sesión de `active-sessions.json`
   en cada turno (paso 2, `:138-154`) rompe la contabilidad de concurrencia.

Al revés destruye datos, y la magnitud está medida: 301 borrados históricos.

De los cuatro candidatos que planteaba el encargo:

- **Mover a `SessionEnd`**: correcto como destino, pero es cambio de
  registración en ruta protegida y compartida, con presupuesto de 1,5 s por
  default contra un hook declarado <10 s. Va como plan, no ejecutado.
- **Borrado condicional a que la sesión terminó de verdad**: ejecutado. La única
  evidencia barata y confiable dentro de un hook de `Stop` es "el proceso dueño
  murió", que es exactamente el `KEEP_ACTIVE` de ADR-119.
- **Separar merge de borrado**: ejecutado, y con un hallazgo extra — el merge
  tampoco era seguro por turno (duplicaba), así que separarlo no alcanzaba:
  había que hacerlo incremental.
- **Desacoplar locks del cleanup**: ejecutado como "soltar sólo locks de PID
  muerto", que es el mismo test de obsolescencia que el guard aplica sobre sí
  mismo. No hacía falta desacoplarlo del todo: alcanzaba con que no pueda
  arrancarle el lock a un vivo.

## Qué arreglé y sus dos corridas

`hooks/session-cleanup.sh`:

- **Paso 1 — merge incremental.** Offset en bytes por archivo bajo
  `$SESSION_DIR/.merge-offsets/`; se apendan sólo las filas nuevas
  (`tail -c +N`). Maneja truncado/rotación reseteando el offset. Idempotente
  bajo disparo por turno.
- **Paso 3 — locks.** Se suelta un lock sólo si su `.pid` ya no existe
  (`ps -p` y `kill -0`). Un lock de un escritor vivo queda intacto; en el peor
  caso lo recicla el propio guard a los 300 s.
- **Paso 4 — archivar, no borrar.** Se eliminó `rm -rf "$SESSION_DIR"`. Ahora,
  y sólo cuando el proceso dueño (`meta.json.pid`) está probadamente muerto, el
  directorio se **mueve** a `.cognitive-os/archive/sessions/`, que es el destino
  que ADR-119 define. Sin prueba de muerte —incluido "no hay `meta.json`"— no se
  toca nada: el default es conservador.
- **`_session_owner_alive()`** nueva, con el porqué y los números en el propio
  archivo, para que el próximo lector no tenga que rederivarlos.

`tests/unit/test_session_lifecycle.py`:

- `test_cleanup_removes_session_directory` → reescrito como
  `test_cleanup_archives_dead_session_directory`: verifica que la sesión muerta
  **aparece en el archivo**, no sólo que desapareció. El assert anterior
  codificaba el defecto.
- Clase nueva `TestCleanupDoesNotDestroyLiveSessions`, **en las dos
  direcciones**:

  | Test | Dirección | Qué exige |
  |---|---|---|
  | `test_live_session_directory_survives_cleanup` | **no borra** | dueño vivo → directorio y contador de subagentes intactos, y tampoco archivado |
  | `test_live_lock_survives_cleanup` | **no borra** | lock de PID vivo → sobrevive |
  | `test_stale_lock_is_released` | sí actúa | lock de PID muerto → se suelta |
  | `test_dead_session_is_archived_not_deleted` | sí actúa | dueño muerto → archivado **con el contenido intacto** (prueba que es `mv`, no borrado) |
  | `test_metrics_merge_is_idempotent_across_turns` | ambas | 3 corridas → 2 filas, no 6; y una fila nueva sí llega al global |
  | `test_hook_has_no_unconditional_recursive_delete` | regresión | el `rm -rf` no vuelve por código (ignora comentarios) |

Las dos corridas:

```bash
# 1) suite completa del ciclo de vida de sesión
uv run python -m pytest tests/unit/test_session_lifecycle.py -q -p no:randomly
# -> 21 passed, 8 skipped in 114.52s

# 2) sintaxis con el bash 3.2 del sistema (no el 5.3 del PATH)
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 /bin/bash -n hooks/session-cleanup.sh   # -> OK
```

Y el contrafáctico del eslabón 5, **repetido después del arreglo** con el mismo
script y el mismo proyecto temporal:

```
### RUN B - identidad ARREGLADA (COGNITIVE_OS_SESSION_ID seteado)
  session dir : EXISTE        <- antes: BORRADO
  locks       : aaa.lock bbb.lock   <- antes: se llevaba aaa.lock
  merge global: SI (1 lineas)       <- el merge sigue funcionando
```

La variable de entorno ya no separa "no hace nada" de "destruye": el camino
quedó desarmado y el paso recuperable sigue vivo.

Nota de honestidad sobre el guardarraíl de regresión: en la primera corrida
falló porque mi propio comentario contenía la cadena `rm -rf "$SESSION_DIR"`.
Se corrigió filtrando líneas de comentario. Un test que no distingue código de
comentario es un test que va a mentir en los dos sentidos.

## Qué NO ejecuté y por qué

- **La identidad de sesión de `session-cleanup.sh`.** Es el arreglo que el
  encargo prohíbe como primer paso y sigue prohibido, aunque el borrado ya esté
  desarmado: el paso 2 (`_deregister_session`) sacaría la sesión viva de
  `active-sessions.json` **en cada turno**, rompiendo `max_concurrent` y el
  contexto de peers. Ese paso necesita el evento correcto antes que la
  identidad correcta.
- **Mover la registración de `Stop` a `SessionEnd`.** Requiere escribir
  `.claude/settings.json`, ruta protegida y compartida con las sesiones hermanas
  que están corriendo ahora mismo, y `SessionEnd` trae un presupuesto de 1,5 s
  contra un hook declarado `<10 s`: sin un `timeout` explícito, el arnés lo
  cancela y **descarta la salida**. Va como plan, con el número (301) que lo
  justifica.
- **`COS_SESSION_SCOPED_METRICS` sigue apagado.** No se tocó. Lo que sí cambió
  es que el motivo (a) que `hooks/_lib/common.sh:138` documenta —"la ruta de
  merge está muerta y arreglarla es peor"— ya no es cierto en su segunda mitad:
  el merge es idempotente y el borrado no existe. Queda el motivo del evento.
- **Reconciliar los dos espacios de nombres de sesión** (`session-init.sh:17`
  inventando un id en vez de adoptar `CLAUDE_CODE_SESSION_ID`). Es la raíz de
  que hiciera falta un archivo marcador por PID, y es trabajo aparte.

### Deuda anotada (documentation-truth)

`manifests/claude-code-hooks-schema.yaml:250` transcribe `Stop` sin
`fires_when`, siendo que el archivo declara transcribir "en full" todo evento
registrado. La pregunta que decide este incidente —por turno o al cerrar— no se
puede contestar leyendo el manifiesto. El dato medido para cerrarla:
**`Stop` dispara una vez por turno; 339 disparos contra 75 aperturas de sesión,
hasta 44 en una misma ventana** (`scripts/session_stop_fire_census.py` sobre
`hook-timing.jsonl` + `.archive/hook-timing-*.jsonl.gz`). No se editó el
manifiesto en esta corrida por presupuesto; queda como ítem pendiente con el
número ya producido.
