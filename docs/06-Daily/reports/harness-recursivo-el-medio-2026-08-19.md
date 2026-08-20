# Harness recursivo: el medio

**Fecha:** 2026-08-19 · **Commit base:** `e11719383` · **Estado:** apagado por default

## Resumen ejecutivo

El inventario de hoy encontró el arnés construido en los dos extremos: un runtime de
loop con seis fusibles, y un evaluador de progreso en `Stop` con 337 corridas. Lo que
faltaba cruzaba sesiones. Quedaron las tres piezas: `cos_lib/session_lineage.py` escribe
`parent_session_id`, que estaba declarado y no aparecía en ninguno de los 27.283 eventos;
los fusibles son **dos**, no uno, porque profundidad y volumen son cantidades distintas;
y `hooks/lineage-relaunch-gate.sh` actúa sobre el veredicto del evaluador. Está apagado, y
apagado como decisión: sin un archivo de armado que ningún código de este repo escribe
solo, el hook sale antes de nombrar al lanzador. Armar son dos actos, no uno: `arm` deja
modo `dry-run` y sólo `arm --spawn` habilita un proceso real. Los seis fusibles se prueban
**forzando la condición**: `scripts/cos_lineage.py probe` devuelve 1 si alguno no cortó.
35 tests, todos verdes. Nada mata procesos.

## Correcciones a las premisas del encargo

1. **«El registro canónico es `cognitive-os.yaml > harness.hooks`, proyectado por
   `apply-efficiency-profile.sh default`» — falso para Claude Code.** Registré los dos
   hooks en el yaml, corrí el proyector, y `.claude/settings.json` **no cambió**:
   `grep -c lineage .claude/settings.json` devolvió `0` y `git status` lo dio limpio. El
   driver lo documenta en su propia cabecera
   (`scripts/_lib/settings-driver-claude-code.sh:96`): *"this driver does not read
   cognitive-os.yaml"*, y en la línea 19: *"A hook added only to the yaml never reaches
   Claude Code"*. Hay que editar a mano **cuatro** lugares: el yaml, el driver, el resumen
   de `apply-efficiency-profile.sh` y `templates/security-profiles/{standard,paranoid}.json`
   — los dos últimos porque el gate de pre-commit los exige por separado. ADR-064 describe
   una intención, no el código.

2. **«El contador de generaciones es *un* fusible duro» — son dos.** Corregido en vuelo por
   el propio orquestador y lo confirmo: la profundidad es propiedad del **camino** y viaja
   bien en una env var heredada con `+1` (que dos hermanas compartan valor es correcto,
   `pi-subagents#239`); el **total** y el **ancho** son propiedades del **árbol** y ninguna
   env var los acota. Implementé los dos: `COS_SESSION_DEPTH` para profundidad,
   `counters.json` bajo `flock` para total y ancho, con check-e-incremento en una sola
   transacción — leer y después incrementar es cómo dos hooks concurrentes pasan un tope
   de uno.

3. **«Un prefijo `VAR=1 <comando>` NO llega a ningún hook de ningún evento» — parcialmente
   falso, y la parte falsa importa.** No llega a un hook de **la sesión actual**, que es el
   caso que el repo pagó caro. Pero sí llega a una sesión **hija** lanzada por ese comando:
   ahí la variable es el entorno propio del proceso hijo, y es exactamente el vehículo por
   el que viaja `COS_SESSION_DEPTH`. Si hubiera tomado la premisa como universal habría
   descartado el mecanismo correcto para la profundidad.

4. **«`pgrep` prueba que no se lanzó nada» — no en esta máquina.** Mi primer chequeo de la
   prueba 1 (`pgrep -f "claude -p"`) devolvió **SI** con el hook desarmado. El match es
   ambiente (PID 52071, preexistente, no lo toqué). La evidencia usable es de disco: el
   directorio `.cognitive-os/lineage/` no se crea, y `child-logs/` —único lugar donde un
   spawn escribe— no existe.

5. **«Commiteá con `git commit -F ... -- <paths>`» — no alcanza en `main`.** El commit
   directo está bloqueado por `destructive-git-blocker` (ADR-055b) y requiere token
   explícito. Usé el comentario final `# --allow-main-branch` que el propio guard documenta.

6. **Un error propio, que dejo escrito porque es el mismo patrón que el encargo prohíbe.**
   La primera versión del interruptor mid-session leía `COS_BYPASS_HOOKS=` del archivo de
   runtime. El nombre real es `COS_BYPASS=`
   (`hooks/_lib/bypass-resolver.sh:26`). El hook «pasaba» porque un bypass que nunca
   matchea nunca bloquea: verde por no hacer nada. Lo encontré porque la prueba es
   diferencial —misma sesión armada, dos corridas, con y sin el archivo— y contaba filas,
   no exit codes. Una aserción sobre la corrida con bypass solamente habría quedado verde.

## Lo que ya existía y reusé

| Pieza | Cómo la usé |
|---|---|
| `hooks/goal-stop-gate.sh` | El evaluador. Mi gate lo consulta vía `GoalStateStore.load()` y su `consecutive_no_progress` alimenta el fusible de estancamiento. No lo toqué. |
| `cos_lib/goal_state.py` | Estado del objetivo, ya persistido y con presupuesto de turnos/tiempo que sobrevive entre sesiones. Un objetivo archivado por presupuesto devuelve `None` y mi gate sale: el fusible de presupuesto sigue gobernando sin que yo lo reimplemente. |
| `cos_lib/hook_event_types.py:82` | La declaración de `parent_session_id`. Ahora tiene escritor. |
| `hooks/_lib/killswitch_check.sh` | Killswitch de emergencia, sourceado al tope de los dos hooks. |
| `hooks/_lib/bypass-resolver.sh` (ADR-241) | El interruptor mid-session. Relee `.cognitive-os/runtime/bypass.env` en cada invocación, que es la única vía accionable con el loop corriendo. Reusado, no reimplementado. |
| `cos_lib/claude_executor.py` | Su `extra_env` sobreescribe el allowlist, así que las variables de linaje llegan a la hija sin tocar `ENV_ALLOWLIST`. El spawn real usa `Popen` detached con ese mismo contrato. |
| `hooks/protected-config-write-guard.sh:48` | El patrón de ancla de prefijo para tokens leídos del texto del comando, y el incidente que lo motivó. |

## Las tres piezas, una por una

### 1. El escritor de `parent_session_id`

`hooks/session-lineage-record.sh` (SessionStart) + `cos_lib.session_lineage.LineageRecord`.
Lee `COS_PARENT_SESSION_ID` del entorno; si no está, escribe `null`. **Un padre inventado
es peor que un hueco**: el hueco se ve, el inventado hace que la cadena parezca completa
apuntando a la sesión equivocada. `LineageStore.chain()` reconstruye de raíz a hoja y es
a prueba de ciclos (termina en vez de colgarse).

### 2. Los contadores — dos, no uno

- **Profundidad** (`COS_SESSION_DEPTH`, `+1` por generación, tope 3). Vehículo correcto
  para una propiedad del camino. Un valor ilegible o negativo se trata como *profundo*, no
  como *superficial*: la basura en la variable no es evidencia de estar cerca de la raíz.
- **Total y ancho** (`counters.json`, tope 5 y 2). Bajo `flock` exclusivo, con
  check-e-incremento en la misma transacción. Keyed por raíz de linaje. **Nunca se resetea
  al empezar una sesión**: el test `test_total_cap_binds_across_sessions_and_does_not_reset`
  rechaza la tercera sesión usando sólo lo que escribieron las dos primeras.
- **Estancamiento** (`consecutive_no_progress`, tope 2). Es el que salva la factura: un tope
  de iteraciones dispara recién cuando ya se gastó todo.

### 3. El hook que decide

`hooks/lineage-relaunch-gate.sh` (Stop, perfiles standard/paranoid, después de
`goal-stop-gate`). Orden de compuertas: archivo de armado → kill-switch de entorno →
bypass de runtime → objetivo activo → `evaluate_relaunch` → `cos_relaunch.py`, que
**re-chequea todo** antes de reservar el slot. La guardia duplicada no es desconfianza del
llamador: es que el segundo llamador que aparezca dentro de seis meses no la va a tener.

**El peligro que el diseño evita explícitamente:** si `goal-stop-gate` bloquea el `Stop`
(la sesión sigue en proceso) y además se lanza una sucesora, el mismo objetivo continúa
dos veces. Por eso armar tiene dos actos: `arm` deja `dry-run` —decide, reserva, registra,
no lanza— y sólo `arm --spawn` habilita el proceso. El modo lo manda el **archivo**, no el
llamador: un `relaunch(dry_run=False)` sobre un armado en `dry-run` no lanza
(`test_arm_file_mode_outranks_the_caller`).

## Los fusibles y sus corridas en rojo

`scripts/cos_lineage.py probe` fuerza cada condición en un temporal y sale 1 si alguno no
cortó. El hueco que dejó la investigación —nadie ejercita sus propios fusibles— se cierra acá.

```
$ .venv/bin/python3 scripts/cos_lineage.py probe
[CUT ] disarmed: not armed: .../autonomy.enabled does not exist
[CUT ] kill-switch: COS_DISABLE_AUTONOMOUS_RELAUNCH=1 in the harness environment
[CUT ] stall: no progress for 2 consecutive evaluations (limit 2); relaunching would buy nothing
[CUT ] total: allowed sequence=[True, True, False, False, False] (cap 2)
[CUT ] width: allowed sequence=[True, True, False, False] (width cap 2)
[CUT ] depth: depth cap reached: child would be generation 4, cap 3

6/6 fuses cut when forced
```

### Las cuatro pruebas, por efecto en disco

**1 — Sin armado, el hook de `Stop` no lanza nada.**
```
### PRUEBA 1 - Stop hook SIN archivo de armado
exit=0
lineage dir existe? -> NO
```
Sin fila, sin archivo, sin directorio. El `pgrep` de la corrida original dio un falso
positivo de ambiente (ver corrección 4); la evidencia es la ausencia del directorio y de
`child-logs/`.

**2 — Armado (`dry-run`) + objetivo activo + generación 0: decide, y se ve.**
```
{"allowed": true, "child_depth": 1, "fuse": "none", "reason": "all fuses clear
 (armed for goal 'g-e2e'); child would be generation 1 | mode=dry-run: slot reserved,
 nothing spawned", "root_id": "S-root", "total_used": 1, "width_used": 1}
counters: {"S-root": {"children": {"S-root": 1}, "total": 1}}
child-logs? -> NO
```

**3 — Generación EN el tope: no lanza y deja constancia.**
```
allowed= False fuse= depth
reason= depth cap reached: child would be generation 4, cap 3
counters tras el rechazo: {"S-root": {"children": {"S-root": 1}, "total": 1}}
```
El contador no se movió: rechazar no consume slot.

**4 — El linaje se reconstruye.**
```
gen0 A (parent=None, source=startup)
 -> gen1 B (parent=A, source=relaunch)
 -> gen2 C (parent=B, source=relaunch)
```

**Extra — el interruptor mid-session, en diferencial.**
```
decisiones CON bypass.env: 0
decisiones SIN bypass.env: 1
```

### Suites

```
$ .venv/bin/python3 -m pytest tests/behavior/test_session_lineage.py \
    tests/red_team/portability/{cos_lineage,cos_relaunch}_test.py \
    tests/red_team/portability/{session-lineage-record,lineage-relaunch-gate}_test.py -q
35 passed

$ .venv/bin/python3 -m pytest tests/behavior/test_goal_stop_hook.py \
    tests/unit/test_goal_budget.py tests/unit/test_cos_loop.py \
    tests/behavior/test_session_lineage.py -q
71 passed
```

## Por qué está apagado por default y qué hace falta para encenderlo

Un hook de `Stop` que lanza sesiones gasta la cuota del operador mientras nadie mira. La
seguridad no puede ser un accidente del filesystem —un directorio aparece la primera vez
que algo lo toca—, así que es una decisión: `is_armed()` es el único método del store que
**no** crea sus directorios, y la compuerta 0 del hook sale antes de nombrar
`cos_relaunch.py`. En un clon recién hecho, la ruta de lanzamiento es inalcanzable.

Para encenderlo, en orden:

1. `.venv/bin/python3 scripts/cos_lineage.py arm --goal-id <id>` — modo `dry-run`, TTL 1h.
   Decide y registra; no lanza. **Empezar acá siempre.**
2. Leer `.cognitive-os/lineage/decisions.jsonl` y confirmar que las decisiones son las
   esperadas.
3. Sólo entonces `arm --goal-id <id> --spawn`, y sólo con conciencia de que
   `goal-stop-gate` puede estar bloqueando el mismo `Stop`.

Para apagarlo:

- `scripts/cos_lineage.py disarm` (borra el archivo), o esperar el TTL.
- **Mid-session, sin reiniciar el arnés:** `COS_BYPASS=autonomous_relaunch` en
  `.cognitive-os/runtime/bypass.env`. Es la única vía que funciona con el loop corriendo.
- `export COS_DISABLE_AUTONOMOUS_RELAUNCH=1` **antes** de lanzar el arnés, o el bloque
  `env` de `.claude/settings.json`. Un prefijo `VAR=1 claude` en la sesión actual **no**
  llega al hook.

Nada mata procesos. El PID de una hija queda en `decisions.jsonl` y pararla es decisión
del operador.

## Lo que NO hice y por qué

- **No lancé ninguna sesión real.** Todo el camino de spawn se probó en `dry-run` y con
  `CLAUDE_CODE_PATH` apuntando a un binario inexistente, para que un test que llegara al
  spawn fallara ruidosamente en vez de gastar cuota.
- **No toqué `hooks/session-cleanup.sh`, `secret-detector.sh`,
  `protected-config-write-guard.sh`, `manifests/defect-classes.yaml` ni
  `scripts/defect_class_coverage.py`** — rutas ajenas.
- **No subí ningún tope ni moví ningún baseline.** Los defaults (3 / 5 / 2 / 2) son bajos a
  propósito: un tope por encima de lo que la carga alcanza nunca dispara y por lo tanto
  nunca se prueba solo.
- **No arreglé la brecha de ADR-064** (que el driver de Claude Code no lee el yaml). Es un
  cambio de arquitectura con blast radius sobre 200 hooks y cuatro sesiones concurrentes;
  queda documentado en la corrección 1 como deuda con dueño ausente.
- **No agregué un oráculo de convergencia propio.** El evaluador ya existe y la
  investigación es explícita: un fusible implementado con un LLM se degrada 2×–30× después
  de 800K tokens. Mis seis cortes están en código, no en un prompt.
- **No pusheé.** Commit `e11719383` en `main`, más el interruptor mid-session.
