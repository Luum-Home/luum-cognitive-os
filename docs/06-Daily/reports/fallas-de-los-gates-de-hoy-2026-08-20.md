<!-- SCOPE: os-only -->
# Fallas de los gates de hoy — 2026-08-20

## Resumen ejecutivo

16 fallas (14 archivos). Las cuatro cubetas, contadas por falla:

| Cubeta | Fallas |
|---|---|
| Deuda real | 9 |
| Defecto del test | 5 |
| Indecidible con motivo | 2 |
| **Efecto del árbol sucio** | **0** |

Cero es el hallazgo principal: las 16 se reprodujeron **idénticas** contra un
worktree desprendido en HEAD, sin los 55 cambios de otras sesiones. Ninguna
falla se puede atribuir a trabajo ajeno en vuelo. Arreglé 9; quedan 7, cada una
con su motivo escrito abajo. Los tres gates de hoy fallaron por tres causas
distintas y **ninguno se aflojó**: uno tenía razón (deuda real de hoy), uno
afirmaba algo que un fix legítimo del mismo día volvió falso, y uno tenía el
fixture roto tapando 17 tests que pasaban por el motivo equivocado.

## Correcciones a las premisas del encargo

1. **`git worktree` SÍ está bloqueado.** El encargo dice: «`git worktree` NO
   está bloqueado —verificalo con `git worktree list`; la orquestación afirmó lo
   contrario en encargos anteriores y era falso—». La verificación propuesta no
   distingue: `git worktree list` es lectura y pasa; `git worktree add` lo
   bloquea `destructive-git-blocker` (ADR-055b) con
   `reason='destructive_git_op'`. Se destraba con el token
   `# --allow-destructive` como comentario shell al final de la línea. La
   premisa era correcta en el espíritu (se puede hacer) y falsa en el mecanismo
   (no sale gratis). Es la forma peligrosa de premisa: la que dice «podés» y
   deja al agente concluyendo «no puedo» cuando choca.

2. **`git archive` no era necesario y el atajo del `.venv` no funciona.** El
   encargo advierte que el árbol de `git archive` no lleva `.venv/`. El worktree
   tampoco, y **symlinkear el `.venv` del repo no alcanza**: el `conftest`
   resuelve el `realpath` del intérprete, así que un symlink devuelve la ruta
   del repo original y falla igual. Lo que funciona es crear un venv propio
   dentro del worktree y agregarle un `.pth` que apunte al `site-packages` real.
   Queda escrito porque es el paso que convierte «correr contra el árbol limpio»
   de idea en procedimiento.

3. **La advertencia sobre `COS_ALLOW_PROTECTED_CONFIG_WRITE` no aplicaba acá.**
   El encargo avisa que el subproceso hereda la variable y que hay que hacer
   `env.pop` antes de medir. En `tests/hooks/test_protected_config_guard_read_vs_write.py`
   el runner **no hereda nada**: arma `env` como diccionario nuevo con PATH,
   HOME y CLAUDE_PROJECT_DIR y nada más. El mismo cuidado ya estaba en
   `test_scope_marker_gate_trigger.py` (`env.pop("COS_ALLOW_UNPROVEN_SCOPE_BOTH")`).
   El riesgo era real y estaba cerrado antes de que yo llegara; verificarlo era
   obligatorio porque de ser cierto habría invertido el diagnóstico entero del
   gate 2.

4. **«De 43 fallas … éstas son tuyas» — mi lote son 16, no 14.** Los números
   entre paréntesis del encargo suman 16; los 14 son archivos. Reproduje 16 y
   sobre 16 informo. No verifiqué las 43 totales: no es mi lote y repetir ese
   número sin contarlo sería adoptarlo.

5. **`tests/audit/test_hook_payload_fidelity.py` no se arregla tocando ese
   archivo.** El encargo lo pone en mi territorio como si el defecto viviera
   ahí. El gate estaba bien; los ofensores eran
   `tests/audit/test_metrics_isolation.py` y
   `tests/contracts/test_skill_gate_identity_and_insistence.py`, dos archivos
   fuera de la lista (y fuera de la lista de prohibidos). Sin salir del lote
   literal, la única salida era sumarlos al baseline — el verde barato exacto
   que ese gate existe para impedir.

## Los tres gates de hoy, uno por uno

### 1. `test_hook_payload_fidelity` (2 fallas) — el gate tenía razón

Veredicto: **deuda real**, creada hoy por commits hermanos.

El gate detecta tests que arman el sobre del hook a mano en vez de usar
`tests.utils.harness_payload.payload()`. Señaló dos archivos que aterrizaron
hoy: `test_metrics_isolation.py` (e568fafe6) y
`test_skill_gate_identity_and_insistence.py` (c6c165bca). Ambos mandaban
`{"tool_name": ..., "tool_input": ...}` — dos campos de los seis o siete que
manda el arnés.

La pregunta que separa los casos —*¿el gate afirma algo falso, o algo verdadero
que molesta?*— se contesta sola acá: los archivos fabricaban el sobre. El verde
barato disponible era agregarlos al baseline, y el docstring del propio gate lo
prohíbe por escrito («the baseline cannot be used as a cushion»).

El matiz que importa: `test_metrics_isolation.py` **necesita** un payload sin
`session_id` — su tesis es que un llamador anónimo no puede tocar el estado del
operador. Migrarlo a `payload()` habría destruido el test. Se migró a
`without("PreToolUse", "session_id", ...)`, que es la salida sancionada por el
helper: el sobre queda completo en los otros cinco campos y le falta exactamente
el que el test quiere que falte. El test terminó **más fuerte**, no más débil.

### 2. `test_protected_config_guard_read_vs_write` (2 fallas) — la aserción se volvió falsa

Veredicto: **defecto del test** (aserción vencida), no deuda.

La lista `CONSERVATIVE_OVERBLOCKS` fija sobre-bloqueos conocidos «como contrato
actual del guard». Dos de sus tres casos dejaron de bloquear porque
**96367406e**, de hoy, le enseñó al guard a parsear el programa de `python3 -c`
como ya parseaba el heredoc.

Acá es donde el sesgo que el encargo me pidió compensar apunta al revés de lo
habitual: la salida cómoda no era aflojar, era **dejar el rojo y declarar deuda
del guard**. Lo que decide es medir el guard en las dos direcciones:

```
exit=2  WRITE via -c open w
exit=2  WRITE via -c write_text
exit=2  WRITE via -c os.open
exit=0  READ via -c (el caso fijado como sobre-bloqueo)
exit=0  cp protegido -> scratch
exit=2  cp scratch -> protegido (escritura)
exit=2  helper-script-with-protected-arg
```

El ensanche es correcto en las siete formas: lee lo que lee y bloquea lo que
escribe. El sobre-bloqueo se resolvió de verdad. El comentario de la lista ya
había previsto este día: «a future fix flips the assertion here». Los dos casos
se movieron a `READ_ONLY`, que es la aserción **más fuerte** (falla si el guard
vuelve a bloquear), y se agregaron a `REAL_WRITES` las tres escrituras
alcanzables por `-c` más `cp` hacia ruta protegida, para cercar el ensanche.

El tercer caso, `helper-script-with-protected-arg`, **sigue fijado**: el guard no
puede ver dentro de un script sin ejecutarlo, y no debe. La lista no se vació.

### 3. `test_scope_marker_gate_trigger` (1 falla) — el fixture tapaba 17 tests

Veredicto: **defecto del test**, y bastante peor de lo que se veía.

`hooks/scope-marker-portability-gate.sh` empezó a sourcear
`hooks/_lib/bypass-resolver.sh` (a3157e0c8, de hoy). El fixture crea
`hooks/_lib` y copia dos libs: `common.sh` y `git-command-parse.sh`.

El modo de falla es el interesante. Bash imprime `No such file or directory`,
**sigue adelante**, y la función que la lib definía sale `command not found` con
código distinto de cero → el gate bloquea → `exit 2`, que es exactamente el
código de un bloqueo legítimo. Por eso solo se veía rojo el único caso que
esperaba `ALLOW`: los 17 que esperaban `BLOCK` pasaban **por el motivo
equivocado**, sobre un hook que ni siquiera había cargado.

El arreglo copia la lib, y además convierte ese silencio en ruido: `run_hook`
ahora falla si el stderr trae `No such file or directory` o `command not found`,
con el mensaje de que lo que sigue es el fixture rompiéndose y no el gate
decidiendo.

## Árbol sucio vs deuda real: cómo lo determiné

El árbol tenía 55 entradas (`git status --porcelain | wc -l`), 12 sin trackear,
20 de ellas `hooks/*.sh` de otra sesión. Cualquier test que camine el
filesystem podía estar midiendo trabajo ajeno.

Procedimiento, reproducible:

```bash
# 1. worktree desprendido en HEAD (el token es obligatorio: ver corrección 1)
git worktree add --detach "$WT" HEAD  # --allow-destructive

# 2. el .venv: symlink NO sirve (el conftest resuelve realpath).
#    venv propio dentro del worktree + .pth al site-packages real
"$REPO/.venv/bin/python3" -m venv --without-pip "$WT/.venv"
SP=$("$REPO/.venv/bin/python3" -c 'import site;print(site.getsitepackages()[0])')
echo "$SP" > "$WT/.venv/lib/python3.12/site-packages/repo-sitepackages.pth"

# 3. los mismos 14 archivos, mismo comando, los dos árboles
.venv/bin/python3 -m pytest -p no:randomly -q <los 14 archivos>
```

Resultado: **16 failed en los dos árboles, y son las mismas 16.** El árbol sucio
no explica ninguna. La cubeta queda en cero por medición, no por descarte.

Un ejemplo de por qué había que correrlo: `test_sdd_topic_keys` señala
`docs/06-Daily/reports/reinvencion-skills-rules-2026-08-19.md`, y el árbol
sucio tiene seis informes del 19/08 sin trackear. Era el candidato natural a
«ruido de otra sesión». Falla igual en el árbol limpio: el archivo está en HEAD.

## Las dos direcciones de cada arreglo

Cada arreglo con su rojo antes, su verde después y un control que muestra que la
aserción sigue midiendo.

| Arreglo | Verde después | Control (la aserción no se aflojó) |
|---|---|---|
| Payload fidelity | 103 passed en los 3 gates + los 2 ofensores | Sembré `tests/hooks/test_zzz_control_probe.py` con un payload fabricado → el gate lo reporta como `new: ['tests/hooks/test_zzz_control_probe.py']`. Removido, vuelve a `new: [] stale: []` |
| Guard: 2 casos a `READ_ONLY` | 59 passed | Contra el guard **anterior** al fix (`git show 96367406e^:hooks/protected-config-write-guard.sh`, vía `COS_GUARD_UNDER_TEST`): los dos casos promovidos **fallan**, los otros 57 pasan. La aserción detecta la regresión y no toqué el lado de escritura |
| Guard: 4 escrituras nuevas en `REAL_WRITES` | pasan contra el guard actual | Pasan también contra el guard viejo: son un cerco agregado, no un intercambio |
| Fixture de scope-marker | 18 passed | Volví a sacar `bypass-resolver.sh` de la lista: fallan **los 18**, no uno. Antes fallaba uno y 17 pasaban por el motivo equivocado |
| Regex de model IDs | 53 passed | Dos pines nuevos: recall (todo alias `claude-*` real del catálogo debe seguir matcheando) y precisión (`claude-settings`, `claude-code`, `claude-plugin` no son modelos). Estrechar de más ahora falla |
| `rules/procedencia-de-los-numeros.md` | 2 rojos → verde | El contenido normativo no se tocó: se agregó el marco que el cargador lee (`## Rule`, `<!-- TIER: 1 -->`, `## Contextual Trigger`) |
| `test_sdd_topic_keys` allowlist | verde | Entra **un archivo por nombre**, no el directorio: el próximo informe con el patrón se vuelve a justificar |

Un control encontró algo por su cuenta: el pin de recall del catálogo de modelos
falló al primer intento con `claude-shell-snapshot-repo-scan`. No es un modelo:
está declarado en `cos_lib/model_catalog.py:132` y `cos_lib/orphan_process_audit.py`
lo usa como **etiqueta de proceso**. Quedó excluido por nombre y anotado — no
absorbido ensanchando el patrón de vuelta — más una aserción de que si esa
entrada desaparece del catálogo, la exclusión falla por obsoleta. Sacarlo del
catálogo toca `cos_lib` y su consumidor: decisión del operador.

## Lo que NO hice y por qué

Las 7 que quedan rojas, con su cubeta.

1. **`test_integration_lane_coverage`** — *deuda real*.
   `tests/integration/test_install_rules_manifest_parity.py` no tiene carril.
   Remedio: registrarlo en `.cognitive-os/test-lanes.yaml`, probablemente en
   `integration-installer` por vecindad. **No lo hice**: no verifiqué la
   precedencia entre el carril amplio (`tests/integration/`) y los carriles de
   archivo explícito, y un carril mal asignado corre el test en el lote
   equivocado — peor que no asignarlo.

2. **`test_cross_session_events::test_peer_context_hook_emits_additional_context_for_peer`**
   — *deuda real, en vuelo de otra sesión*. El hook ya migró:
   `hooks/cross-session-peer-context.sh:40` dice «Claude Code reads
   additionalContext ONLY from inside hookSpecificOutput». El test lee la clave
   de nivel superior. Es el territorio de
   `tests/contracts/test_claude_code_hooks_schema_conformance.py`, que otra
   sesión tiene modificado en el árbol. **No lo toqué por colisión.**

3. **`test_primitive_runtime_reality`** — *deuda real*.
   `hooks/session-lineage-record.sh` y `hooks/lineage-relaunch-gate.sh` sin
   metadata de ciclo de vida. Arreglarlo es editar `hooks/*.sh` con 20 hooks
   modificados por otra sesión en el mismo checkout. **No lo toqué por
   concurrencia**, no por dificultad.

4. **`test_external_claims_declare_verification`** — *indecidible con motivo*.
   Pide `verified: YYYY-MM-DD` + `how:` en los tres
   `manifests/*-hooks-schema.yaml`. El mensaje del propio gate lo dice: «NO
   pongas la fecha de hoy sin haber mirado la fuente: eso convierte el
   instrumento en su opuesto». No miré las fuentes ajenas (Claude Code, Codex,
   OpenCode). Fechar sin mirar sería el verde barato exacto que el gate nombra.
   **Requiere que alguien verifique contra la fuente.**

5. **`test_core_extensions_split::test_aspirational_audit_reports_zero_active_dormant_debt`**
   — *deuda real*. Ratio de deuda dormant `0.0021` contra un piso de `0.0`.
   Es un ratchet, y el encargo me los prohíbe explícitamente. **No lo toqué.**

6. **`test_pentest_self::test_rate_limit_hooks_registered_in_settings`** —
   *indecidible con motivo*, y vale la pena leerlo dos veces. El test afirma que
   los hooks de rate-limit están registrados en `settings.json`.
   `rules/rate-limiting.md` afirma, con fecha 2026-08-15 y comando
   (`grep -c 'rate-limiter' .claude/settings.json` → `0`), que **no** lo están, y
   que «Registrarlo es una decisión pendiente del operador, no un olvido de
   documentación». Uno de los dos miente. No es que el test esté mal escrito:
   codifica un requisito que el operador difirió por escrito. Resolverlo es o
   registrar el hook (ruta protegida y contendida) o retirar el requisito — las
   dos son decisiones del operador, ninguna es mía.

7. **`test_confidentiality_enforcer::test_downgrades_operator_absolute_path_in_gitignored_doc_to_warn`**
   — *deuda real, de hoy*. El test busca el jsonl en
   `<project>/.cognitive-os/metrics/`, pero el `conftest` raíz redirige
   `COS_METRICS_DIR` a un sandbox (trabajo de aislamiento de métricas de hoy,
   241cf1e58 / e568fafe6). El escritor honra el redirect; el lector del test no.
   Remedio: leer desde `COS_METRICS_DIR`. **No lo arreglé por presupuesto de
   llamadas** — es el más barato de los siete y el que recomiendo atacar
   primero.

Además, dos cosas que deliberadamente **no** hice en ninguna de las 16: no
agregué un `xfail` ni un `skip`, y no borré ningún test. La única exclusión
nueva en todo el trabajo es un archivo nombrado en el allowlist de
`test_sdd_topic_keys`, con el motivo escrito al lado y por nombre en vez de por
directorio.

### Nota sobre un falso positivo recurrente al medir

Varias corridas terminan con `FALLO: la suite dejo escrituras en la telemetria
del operador (.cognitive-os/metrics/)`. En esta sesión ese aviso es del
**operador vivo**: los hooks del arnés escriben `hook-timing.jsonl` y compañía
mientras la suite corre. Aparece incluso en corridas de 18 tests que pasan.
Quien mida aislamiento de métricas mientras hay sesión activa va a ver ese rojo
sin que ningún test lo haya causado; el propio mensaje ofrece la salida
(`COS_ALLOW_OPERATOR_METRICS_WRITES=1`).
