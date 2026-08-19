# Enchufar la familia de coordinación: qué había para enchufar, y qué no

Fecha: 2026-08-19 · Alcance: `os-only` · Rama: `main` · Sin push

## Resumen ejecutivo

**Enchufados: 0. Frenados: 3. Ya corrían: 18 de 18.** No hay ninguna primitiva
de coordinación esperando que la registren: las 13 con telemetría estaban
registradas, y las 5 con `runs=0` corren desde hace meses como hijas de
`hooks/bash-hot-path-dispatcher.sh` en la rama `_is_git_boundary`. Su `runs=0`
es artefacto de medición, no de muerte — el caso 3 del Tramo 1.

Las 3 que quedaron fuera de settings lo están **a propósito y con razón**:
`concurrent-write-guard-codex-proxy` es la proyección degradada para Codex
(`claude_projection: false`), `worktree-submodule-fix` está anotado
`@manual-trigger`, y `agent-bash-cwd-enforcer` tiene la **ruta de acción
inalcanzable**: exige `orchestration.sub_agent_cwd: main_worktree` y el repo
usa `isolated_worktree`.

El hallazgo que importa no estaba en el encargo: **`concurrent-write-guard.sh`
está registrado, lleva 1.062 corridas y nunca tomó un solo lock.** Su gate de
`SESSION_ID` (línea 39) sale antes del `mkdir -p "$LOCKS_DIR"`; el directorio
`.cognitive-os/sessions/locks/` **no existe en disco**. El `exit 2` de la línea
112 nunca fue alcanzable. La exclusión mutua por archivo entre sesiones —la
pieza estrella del foso— es hoy un no-op con telemetría.

## Correcciones a las premisas del encargo

1. **«18 primitivas son archivos con tests verdes y `runs=0`.»** Falso. De las
   18, **13 tienen telemetría propia** (`cross-session-event-emit` 10.989,
   `post-git-orphan-notifier` 9.396, `concurrent-write-guard` 1.062,
   `edit-lock-pre-tool` 1.062, …). Sólo 5 marcan cero, y las 5 corren por el
   dispatcher. El encargo generalizó a 18 lo que era cierto de 5.

2. **`conflict-marker-guard` y `agent-bash-cwd-enforcer` no están en las 18.**
   El encargo los nombra como parte de la familia; en
   `lista-de-poda-2026-08-19.md` §A los cinco con actividad 0 son
   `agent-message-inbox-guard`, `branch-ownership-lock`,
   `cross-session-coordination-guard`, `concurrent-write-guard-codex-proxy` y
   `worktree-submodule-fix`. Los evalué igual porque el operador los nombró.

3. **Dos conteos de `lista-de-poda-2026-08-19.md` no se reproducen.**
   `post-git-orphan-notifier` da **9.396**, no 18.464 (un factor 2 exacto:
   huele a doble conteo). `untracked-work-preservation-guard` da **0**, no 710
   — es hija del dispatcher y el wrapper de timing no la envuelve. Mismo
   corpus, 275.893 filas, vivo + 7 rotados. `session-start-worktree-nudge` da
   75, no 111.

4. **«`worktree-submodule-fix` corre por perfil.»** Falso: no tiene entrada en
   `cognitive-os.yaml`, no está en ningún molde, y su cabecera dice
   `@manual-trigger: invoked manually after worktree operations; not a global
   default`. Está sin registrar por decisión escrita, no por olvido.

5. **«Los que deniegan, traelos en una tabla y no los registres.»** La premisa
   asume que los deniegan-capaces están apagados. Los cinco `exit 2` de la
   familia (`conflict-marker-guard`, `untracked-work-preservation-guard`,
   `branch-ownership-lock`, `cross-session-coordination-guard`,
   `agent-message-inbox-guard`) **ya están enchufados** vía dispatcher. La
   tabla de frecuencia sigue siendo útil, pero es un retrato de lo que ya está
   corriendo, no un pronóstico de lo que pasaría si se encendiera.

6. **«15 tests verdes entre ellos.»** Son bastantes más (12–42 por hook según
   los archivos que lo mencionan). Y el encargo tenía razón en desconfiar:
   `tests/integration/test_cwd_enforcer_rewrite.py:72` y
   `test_cwd_enforcer_warns.py:55` **escriben su propio `cognitive-os.yaml`
   con `sub_agent_cwd: main_worktree`** — el valor que el repo no usa. Los
   tests ejercitan una rama que la config real apaga.

7. **El arreglo de `claim_task` está en el árbol.** `CONTENTLESS_FINGERPRINT`
   aparece en `scripts/cos_task_claims.py:253-256` y en el reporte de `status`
   (líneas 487-490). Verificado antes de tocar nada.

8. **Propiedad de archivos.** `git status --porcelain` al arrancar: 45 rutas
   sucias, 22 bajo `hooks/` — todas del mismo cambio cosmético (quitar la línea
   `# p95 latency target:` de la cabecera). No toqué ninguna. Mi única
   escritura fuera de este informe fue un `.lock` de sonda que borré
   (`rm -rf .cognitive-os/sessions/locks`, verificado ausente después).

## ¿Funciona cada uno? — la tabla

Evidencia: `scratchpad/exercise-coord-hooks.sh` (payload con la forma de
`manifests/claude-code-hooks-schema.yaml`: `session_id`, `transcript_path`,
`cwd`, `hook_event_name`, `tool_name`, `tool_input.command`,
`permission_mode`). Latencia = una corrida en frío con la máquina cargada.

| Hook | Corre a mano | Ruta alcanzable | Lo invoca el dispatcher | Latencia | Telemetría |
|---|---|---|---|---|---|
| `cross-session-event-emit` | — (ya registrado ×4) | sí | no | — | 10.989 |
| `post-git-orphan-notifier` | — (ya registrado) | sí | no | 1.877 ms (fila real) | 9.396 |
| `concurrent-write-guard` | **sí, rc=0** | **NO — gate de `SESSION_ID`** | no | — | 1.062 |
| `edit-lock-pre-tool` | — | sí | no | — | 1.062 |
| `edit-lock-drain-parked` | — | sí | no | — | 1.032 |
| `untracked-work-preservation-guard` | **sí, rc=0** | **sí — 1 deny real en el replay** | **sí** (`_is_git_boundary`) | 223 ms p50 | 0 (hija) |
| `agent-message-inbox-context` | — | corre en vacío (0 mensajes) | no | — | 350 |
| `cross-session-peer-context` | — | corre en vacío (`peers()`=0) | no | — | 350 |
| `edit-lock-process-negotiations` | — | sí | no | — | 350 |
| `stash-budget-warn` | — | sí | no | — | 350 |
| `branch-ownership-release` | — | libera lock que nadie toma | no | — | 322 |
| `edit-lock-session-end` | — | sí | no | — | 322 |
| `session-start-worktree-nudge` | — | sí | no | — | 75 |
| `agent-message-inbox-guard` | **sí, rc=0** | sí (`exit 2` L61) | **sí** | 77 ms p50 | 0 (hija) |
| `branch-ownership-lock` | **sí, rc=0** | sí (`exit 2` L80) | **sí** | 113 ms p50 | 0 (hija) |
| `cross-session-coordination-guard` | **sí, rc=0** | sí (`exit 2` L27) | **sí** | 136 ms p50 | 0 (hija) |
| `concurrent-write-guard-codex-proxy` | **sí, rc=0** | **NO — `[ -d "$LOCKS_DIR" ] \|\| exit 0`, el dir no existe** | no | 58 ms | 0 |
| `worktree-submodule-fix` | **sí, rc=0** | sí (hay `.gitmodules`) | no | 54 ms | 0 |
| *(extra)* `conflict-marker-guard` | **sí, rc=0** | sí (`exit 2` L81) | **sí** | 138 ms p50 | 0 (hija) |
| *(extra)* `agent-bash-cwd-enforcer` | **sí, rc=0** | **NO — `POLICY != main_worktree` → `exit 0` L108** | no | 109 ms | 0 |

Cadena completa del dispatcher medida con el mismo arnés:
`git commit -m probe` → **1.181 ms** y `rc=2` (lo para `destructive-git-blocker`);
`echo hola` → **317 ms**.

## Los enchufados y qué vi correr

**Ninguno.** Es el resultado honesto y es el correcto: no había nada que
enchufar. Lo que sí vi correr, con el evento provocado a mano:

- Los **cinco guardas hijos del dispatcher** corrieron los 323 comandos del
  replay histórico, uno por uno, leyendo el payload real por stdin. Están
  vivos: `untracked-work-preservation-guard` denegó de verdad en esa corrida
  (mensaje `=== UNTRACKED-WORK-PRESERVATION-GUARD: BLOCKED ===`).
- El **dispatcher completo** sobre `git commit` devolvió `rc=2` propagando el
  veto de `destructive-git-blocker`. La cadena está enchufada y bloquea.
- El **contrafactual de `concurrent-write-guard`**: mismo payload de `Edit`,
  dos corridas. Sin `COGNITIVE_OS_SESSION_ID` → `rc=0`, `.cognitive-os/sessions/locks`
  sigue sin existir. Con `COGNITIVE_OS_SESSION_ID=probe-live` → `rc=0` y aparece
  `fc78e901b6bc4f75619d1a5af51c50be.lock`. El mecanismo funciona; el cableado no.

## LOS QUE DENIEGAN — tabla para el operador con frecuencia estimada

Replay: `scratchpad/replay-deniers.py` sobre **323 comandos git-boundary
únicos** (548 con repeticiones) sacados de `.cognitive-os/metrics/tool-sequences.jsonl`
(`command_preview`) y `.cognitive-os/metrics/git-op-blocks.jsonl` (`command`).

```bash
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 .venv/bin/python3 scratchpad/replay-deniers.py
```

| Hook | Qué bloquea, y bajo qué condición | Deny en 323 | p50 / max | Riesgo concreto |
|---|---|---|---|---|
| `untracked-work-preservation-guard` | borrado/`checkout --`/`clean` que toca trabajo **untracked o protegido** | **1** | 223 / 585 ms | El único que frena algo. El caso capturado era descartar drift de reportes — frenar eso en un repo con 8 agentes es correcto, no falso positivo |
| `conflict-marker-guard` | commit con marcadores `<<<<<<<`/`>>>>>>>` en el índice | **0** | 138 / 1.866 ms | Nulo hoy. Su max de 1.866 ms es el peor de los cinco |
| `branch-ownership-lock` | operación sobre una rama con dueño en otra sesión viva | **0** | 113 / 325 ms | Nulo, y estructuralmente: `.cognitive-os/runtime/branch-locks/` no tiene una entrada desde 2026-05-16. Toma un lock que nadie disputa |
| `cross-session-coordination-guard` | git-boundary con otra sesión activa sin coordinar | **0** | 136 / 540 ms | Nulo con una sola sesión. **Es el que hay que volver a medir el día que haya dos** — es el que consume el ledger de claims que se arregló hoy |
| `agent-message-inbox-guard` | git-boundary con mensajes sin leer en el inbox | **0** | 77 / 355 ms | Nulo por construcción: el store nunca tuvo un mensaje (`cos_lib/agent_message_bus.py` sin productor automático) |

**Costo agregado:** ~687 ms p50 sumando los cinco, pagados en **cada** comando
git-boundary, a cambio de 1 bloqueo en 323. Los cinco ya están enchufados: la
decisión disponible no es encenderlos sino **si vale la pena mantenerlos en la
rama síncrona del dispatcher**.

**Limitación honesta del número:** el replay corre contra el estado de HOY
(rama, working tree, locks). Un guard que decide por estado —`branch-ownership-lock`
mira quién tiene la rama— pudo haber denegado en su momento y no denegar ahora.
El 0 es "no denegaría hoy", no "nunca denegó".

## Los que no funcionan y hay que arreglar antes

1. **`concurrent-write-guard.sh` — registrado, 1.062 corridas, cero locks.**
   `hooks/concurrent-write-guard.sh:30-39`:

   ```bash
   SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
   if [ -z "$SESSION_ID" ]; then
     SESSION_FILE="$SESSIONS_DIR/.current-session-$$"   # $$ = PID del hook, nuevo cada vez
     ...
   fi
   [ -z "$SESSION_ID" ] && exit 0                        # ← siempre acá bajo Claude Code
   ```

   `.claude/settings.json` no exporta `COGNITIVE_OS_SESSION_ID` (0 menciones);
   quien lo exporta es `hooks/session-init.sh:189`, y un `export` en un
   subproceso no llega a sus hermanos. El fallback lee
   `.current-session-$$` con el PID del **propio hook**, que por definición no
   existe (en disco hay `.current-session-367` y `.current-session-95640`, de
   otros PIDs). Resultado: sale antes del `mkdir -p "$LOCKS_DIR"` de la línea
   52 y el directorio no existe después de 1.062 corridas.
   **No lo arreglé a propósito:** el hook tiene `exit 2` en la línea 112. Es
   exactamente el precedente de `trust-score-validator` que el encargo cita —
   arreglar el campo enciende un bloqueador con 1.062 corridas inertes. Decisión
   del operador, con este dato en la mano: hoy denegaría sobre cualquier
   `Edit`/`Write` cuyo archivo tenga un lock vivo de otra sesión, y el ledger
   de sesiones tiene una sola sesión, así que el riesgo inmediato es bajo — pero
   el `$$` hay que arreglarlo igual o el lock quedará keyado por PID.

2. **`concurrent-write-guard-codex-proxy.sh` — dos defectos, ninguno visible
   hoy.** (a) Lee `$SESSIONS_DIR/locks`, el directorio que su hermano nunca
   crea: aunque Codex lo dispare, sale en la línea 46. (b) Deriva `SESSION_ID`
   sólo de `COGNITIVE_OS_SESSION_ID`/`CODEX_SESSION_ID`/`CODEX_THREAD_ID`,
   nunca del `session_id` de stdin; si el directorio llegara a existir, el
   `continue` de "misma sesión" (línea 77) no dispararía y reportaría sus
   **propios** locks como contención.

3. **`agent-bash-cwd-enforcer.sh` — ruta muerta bajo la config vigente.**
   Línea 105-109: si `orchestration.sub_agent_cwd != main_worktree`, `exit 0`.
   `cognitive-os.yaml:582` dice `isolated_worktree`. Y aunque se encendiera,
   su cabecera declara *"Never blocks (always exits 0)"*: registrarlo suma
   ~109 ms por comando Bash y no agrega guardia. Sus dos suites de integración
   pasan porque **se escriben un yaml propio con `main_worktree`**.

## Lo que NO hice y por qué

- **No registré nada en los cuatro moldes.** No hubo candidato que pasara el
  filtro del Tramo 2 (siempre `exit 0` + ruta alcanzable + no duplicado):
  `agent-bash-cwd-enforcer` y `concurrent-write-guard-codex-proxy` tienen la
  ruta inalcanzable, `worktree-submodule-fix` está anotado `@manual-trigger`.
  Registrar cualquiera de los tres es el verde barato que el encargo prohíbe:
  latencia sin guardia.
- **No corrí `apply-efficiency-profile.sh`, `hook_quality_audit.py --check` ni
  `pytest tests/contracts/`.** Son la verificación de un registro que no hice;
  correrlos sin cambios sólo gasta una máquina con load ~136.
- **No arreglé `concurrent-write-guard`.** Está fuera del mandato (el encargo
  pide enchufar, no reparar) y enciende un `exit 2` inerte. Va como decisión.
- **No toqué `hooks/**`.** 22 archivos bajo `hooks/` están sucios por otro
  agente; toda mi evidencia es lectura y ejecución con stdin.
- **No medí la latencia de los 13 ya registrados** salvo la fila real de
  `post-git-orphan-notifier` (1.877 ms): ya está en `hook-timing.jsonl` y
  volver a medirla en una máquina saturada daría peor y más ruidoso.
- **No pusheé.** Sin commit propio salvo este informe.

## Evidencia ejecutable

- `scratchpad/exercise-coord-hooks.sh` — corre cada hook con payload de la
  forma del arnés; imprime `rc` y latencia.
- `scratchpad/replay-deniers.py` — replay de los 323 comandos git-boundary
  históricos contra los cinco `exit 2`; exit 0 sin denies / 1 con denies / 2 error.
- Telemetría (275.893 filas, vivo + 7 rotados):
  ```bash
  { cat .cognitive-os/metrics/hook-timing.jsonl
    for f in .cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz; do gzip -dc "$f"; done
  } | grep -c '"<hook>"'
  ```
- Matriz de registro en los cuatro moldes:
  ```bash
  grep -c "script: hooks/<h>.sh" cognitive-os.yaml
  grep -c "<h>.sh" .claude/settings.json
  grep -c "<h>" hooks/bash-hot-path-dispatcher.sh
  grep -c "<h>" scripts/_lib/settings-driver-claude-code.sh
  grep -rl "<h>" templates/security-profiles/
  ```
