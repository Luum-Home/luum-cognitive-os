# Aislamiento de sub-agentes por worktree: lo nuestro (ADR-223) contra lo nativo

**Fecha**: 2026-08-19
**Alcance**: ADR-223 (worktree-per-write-agent), ADR-035 / ADR-239 (política `sub_agent_cwd`)
**Evidencia ejecutable**: `tests/red_team/test_agent_worktree_isolation_escapes.py`

## Resumen ejecutivo

Los tres escapes se reprodujeron. Los dos del relay son reales, pero el hallazgo
que manda es el tercero: **nuestro aislamiento es advisory de punta a punta**.
ADR-223 crea el worktree de verdad y después le *pide* al agente que trabaje ahí
con un `WORKING DIR:` inyectado como texto. El único guard que podría forzarlo,
`hooks/agent-bash-cwd-enforcer.sh`, nunca bloquea (siempre `exit 0`,
`permissionDecision: "allow"`) y además el driver de settings lo emite con
`enabled=false`: `grep -c agent-bash-cwd-enforcer .claude/settings.json` → `0`.
Contra eso, `isolation: "worktree"` de Claude Code bloquea a nivel de tool con
cuatro checks, uno de ellos —"command shape"— que ni siquiera se puede apagar.
**Recomendación: las dos cosas, pero no en partes iguales** — nativo donde corre
Claude Code, y en los otros tres arneses asumir que lo nuestro es provisión de
worktree + convención, no un control, y decirlo así en la doc.

## Correcciones a las premisas del encargo

1. **"La familia en más riesgo de obsolescencia"** subestima el problema. No es
   que lo nativo sea *mejor* que lo nuestro: es que lo nuestro **no es un control
   de seguridad**. Comparar "dos escapes que no cubrimos" contra una
   implementación que no cubre *ninguno* mide mal la distancia. No hay un
   mecanismo con dos agujeros; hay una convención documentada.

2. **El escape del symlink, tal como viene en el relay, no aplica a nuestro
   código.** En la doc oficial (`worktrees.md`, `hooks.md` §WorktreeCreate) el
   vector es el *hook* `WorktreeCreate` devolviendo un path que atraviesa un
   symlink commiteado. Nosotros no usamos `WorktreeCreate`: el path lo produce
   `scripts/cos-agent-worktree-prepare`. Refutado como está enunciado — pero
   existe una **variante equivalente en nuestro código**, que sí reproduje y sí
   cerré (ver abajo). La premisa era falsa en la forma y verdadera en el fondo.

3. **"Mantener nuestra implementación cuesta mantenimiento y es menos segura"**:
   el costo de mantenimiento es medible y es peor que "mantenimiento". Ahora
   mismo hay **31 manifests, 18 de ellos apuntando a worktrees que ya no
   existen, 13 worktrees vivos y 13 ramas `codex/agent/*`** sin reapear. El
   reaper es TTL 24h y opt-in (`--execute`). Lo nativo limpia solo cuando el
   sub-agente no dejó cambios.

4. **"Una capacidad nativa de Claude Code no existe en `bare_cli`"** — cierto,
   pero la conclusión que se saca de ahí no se sostiene: en `bare_cli`,
   `codex` y `opencode` **tampoco existe lo nuestro como enforcement**.
   `lifecycle_projection()` (`cos_lib/agent_lifecycle.py`) devuelve un string:
   `"write-capable agents receive a dedicated git worktree and must not mutate
   the operator worktree"`. No hay nada a lo que degradar: los cuatro arneses
   ya están degradados. La pregunta correcta no es "¿degradamos avisando?" sino
   "¿por qué la doc dice que hay aislamiento en cuatro arneses?".

5. **Auditorías propias vencidas.** `docs/06-Daily/reports/aspirational-audit-2026-07-20.md`
   y la de 2026-05-20 clasifican el enforcer como `ON_DEMAND ... registered=True`,
   "legit sleeper (fires when triggered)". Está mal: no está registrado y no
   dispara. La señal `fire_count_7d=0` era correcta y se interpretó al revés.

6. **No pude confirmar la versión del arnés.** `claude --version` devuelve
   `1.32885.1`, que no mapea contra el esquema `v2.1.x` que usa la doc para
   fechar los arreglos (`v2.1.203`, `v2.1.210`, `v2.1.216`). Las capacidades
   nativas las tomo de la doc publicada hoy, no de la build local.

## Los tres escapes, reproducidos o refutados

Reproducción: `.venv/bin/python3 -m pytest tests/red_team/test_agent_worktree_isolation_escapes.py -q`

### Escape 1 — redirigir git al checkout del operador (`git -C`, `GIT_DIR`) → **REPRODUCIDO**

Desde el cwd de un worktree de agente, un commit dirigido al checkout del
operador entra sin resistencia:

```
=== PROBE A: git -C redirect from the agent worktree into the operator checkout ===
commit rc: 0
operator HEAD: 794d941 landed from agent cwd
PROBE A ESCAPE: True

=== PROBE A2: GIT_DIR/GIT_WORK_TREE redirect ===
rc 0 -> ['## fixturebase']

=== PROBE A3: does hooks/agent-bash-cwd-enforcer.sh block it? ===
enforcer exit: 0 | stdout:  | stderr:
```

La doc oficial confirma que lo nativo sí lo cubre (`worktrees.md`, §How Claude
Code enforces isolation): bloquea el redirect por `git -C`, `--git-dir`,
`GIT_DIR`, `GIT_WORK_TREE` **y por `cd` al main checkout antes de correr git**.

### Escape 2 — symlink que saca el worktree afuera → **REFUTADO como está enunciado, REPRODUCIDO en su variante nuestra, CERRADO**

El vector de la doc es el hook `WorktreeCreate`, que no usamos. La variante
equivalente en nuestro código es peor: `prepare_agent_worktree()` no validaba el
path destino, así que un `wt-root/<task-slug>` pre-plantado como symlink al
checkout del operador devolvía tranquilamente:

```
returned worktree_path: .../wt-root/evil-task
resolves to:            .../operator
operator checkout:      .../operator
PROBE B ESCAPE: True
```

Es decir: no creaba worktree ninguno (`created=False`), leía la rama del
checkout del operador, escribía el manifest como si todo estuviera bien, y al
agente se le decía "tu worktree aislado es X" donde X **es** el checkout que el
aislamiento existe para proteger. Un escape que se disfraza de cumplimiento.

### Escape 3 — el aislamiento no se obedece → **REPRODUCIDO, y es el que importa**

Ver la sección siguiente.

## ¿Nuestro aislamiento es forzado o advisory?

**Advisory. Sin matices.** Cuatro pruebas independientes:

1. **El mecanismo de entrega es texto.** `hooks/agent-prelaunch.sh:322` arma
   `AGENT_WORKTREE_CONTEXT="WORKING DIR: ..."` y lo emite por
   `hookSpecificOutput.additionalContext`. Eso entra al prompt del agente. Un
   prompt no es un permiso denegado.

2. **El guard nominal no bloquea, por diseño.** Encabezado de
   `hooks/agent-bash-cwd-enforcer.sh`: *"Never blocks (always exits 0)"*. Su
   propio test se llama `test_cwd_enforcer_warns.py` y su matriz declara
   "Enforcer always exits 0 (never blocks)".

3. **Y ni siquiera corre.** `grep -c agent-bash-cwd-enforcer .claude/settings.json`
   → `0`. Tampoco lo despacha `hooks/bash-hot-path-dispatcher.sh`.
   `scripts/_lib/settings-driver-claude-code.sh:304` lo proyecta con `"false"`, y
   solo en el perfil `full`. Estaba en `.claude/settings.json.bak-before-regen` y
   se perdió en la regeneración.

4. **En modo default ni siquiera tendría efecto.** `cognitive-os.yaml:582` fija
   `sub_agent_cwd: isolated_worktree`; por ADR-239 el enforcer solo reescribe
   cuando la política es `main_worktree` (legacy).

Prueba viva, hoy, sin fixture: este sub-agente recibió tarea de escritura, tiene
worktree preparado (`.cos-agent-worktrees/luum-agent-os/`, 13 vivos) y sin
embargo su cwd es la raíz del repo — el checkout del operador — donde
además están las modificaciones sin commitear de los otros agentes de la tanda.
Este mismo informe se escribió ahí.

Corolario que hay que decir en voz alta: **el escape más grande no es `git -C`.
Es que el agente simplemente no vaya al worktree.** `git -C` requiere que el
agente quiera evadir; esto pasa sin que nadie evada nada.

## Nativo vs propio: la tabla

| Dimensión | ADR-223 (nuestro) | `isolation: "worktree"` (Claude Code) |
|---|---|---|
| Crea el worktree | Sí, real, con lock | Sí |
| Base de la rama | `HEAD` de la sesión | rama default del repo (no el `HEAD` del padre) |
| Edits (`Edit`/`Write`) al checkout del operador | permitidos | **bloqueados** |
| cwd de Bash fuera del worktree | permitido | **bloqueado** |
| `git -C` / `--git-dir` / `GIT_DIR` / `GIT_WORK_TREE` / `cd` previo | permitido | **bloqueado** |
| Comandos de forma no verificable (heredocs, brace expansion) | permitidos | **bloqueados, no se puede apagar** |
| Symlink que redirige el path del worktree | vulnerable → **cerrado hoy** | cubierto desde v2.1.216 |
| Limpieza | reaper TTL 24h, opt-in `--execute`; hoy 18 manifests huérfanos, 13 ramas colgadas | automática si el sub-agente no dejó cambios |
| Cobertura de arneses | 4 declarados; **enforcement real: 0** | 1 (Claude Code) |
| Código a mantener | `cos_lib/agent_lifecycle.py`, `scripts/cos-agent-worktree-prepare`, 3 hooks, ~6 suites | ninguno |

La fila que decide es la penúltima. La restricción "el SO corre en cuatro
arneses" pierde fuerza cuando en los cuatro el aislamiento es una frase.
Mantener dos implementaciones tiene sentido si la propia protege algo en los
otros tres; hoy no protege nada, solo *provisiona* worktrees y deja una
convención escrita.

Sobre el freeze de adopción (`manifests/external-tool-adoption-freeze.yaml`):
usar `isolation: "worktree"` no es vendorizar código de terceros. Es dejar de
reimplementar —mal— lo que el arnés en el que ya corremos hace a nivel de tool.
El freeze cubre traer código ajeno adentro; esto es lo contrario: sacar código
propio que duplica la plataforma.

## Qué cerré y su prueba en dos direcciones

**Cerrado**: escape 2 en su variante nuestra, en `cos_lib/agent_lifecycle.py`
(fuera de `hooks/**`, `manifests/**` y del wrapper de timing, respetando la
partición de la tanda).

`_reject_unsafe_target()` rechaza, antes de tocar git, un destino que (a) tenga
segmentos `.`/`..`, (b) atraviese un symlink **por debajo del root ya resuelto**
—resolver el root primero evita tratar `/var → /private/var` de macOS como
ataque—, o (c) resuelva dentro del checkout del operador.

**ROJO (antes del arreglo)**

```
$ .venv/bin/python3 -m pytest tests/red_team/test_agent_worktree_isolation_escapes.py -p no:randomly -q
..F.F.
E   Failed: DID NOT RAISE <class 'cos_lib.agent_lifecycle.AgentLifecycleError'>
FAILED ...::test_symlinked_worktree_target_pointing_at_operator_checkout_is_refused
FAILED ...::test_worktree_root_nested_in_the_operator_checkout_is_refused
2 failed, 4 passed in 1.34s
```

**VERDE (después)**

```
$ .venv/bin/python3 -m pytest tests/red_team/test_agent_worktree_isolation_escapes.py -p no:randomly -q
6 passed in 1.48s
```

**Sin regresión**, y sin verde barato: hay un test explícito de que el camino
feliz sigue funcionando (`test_legitimate_worktree_preparation_still_succeeds`),
y el guard se validó contra el path de producción real:

```
$ .venv/bin/python3 -m pytest tests/unit/test_agent_lifecycle.py \
    tests/behavior/test_agent_lifecycle_worktree_mode.py \
    tests/unit/test_auto_repair_worktree.py -p no:randomly -q
30 passed in 9.49s

$ .venv/bin/python3 -c "...; _reject_unsafe_target(p, r, t)"
root: <parent-del-repo>/.cos-agent-worktrees/luum-agent-os
LIVE PATH ACCEPTED by guard: OK
```

Los escapes 1 y 3 quedan **pinneados como abiertos** en el mismo archivo
(`test_git_c_redirect_into_operator_checkout_is_currently_unguarded`,
`test_cwd_enforcer_is_not_projected_as_an_active_claude_code_hook`). Cuando
alguien los cierre, esos tests van a fallar: eso es la señal, y se actualiza la
aserción, no se afloja.

### Lane completo `tests/red_team/`: 4 rojos, ninguno mío

```
4 failed, 1431 passed, 22 warnings in 478.02s
```

Verificado uno por uno, no inferido:

- `test_hook_exercise_audit.py::test_runs_from_arbitrary_project_root` — **pasa
  aislado**. Flake de la corrida en paralelo.
- Los otros tres (`test_os_only_scope_family`, `test_project_scope_family`,
  `test_primitive_behavior_depth_audit`) fallan por los mismos tres primitivos,
  que el propio JSON del audit nombra: `scripts/hook_artifact_derivation.py`
  (todavía untracked), `scripts/hook_test_reality_census.py` y
  `scripts/signal_orphan_verify.py` — `depth none below required structural`,
  mtimes entre 18:16 y 18:59 de hoy. Son de la tanda concurrente de hooks, no
  de este trabajo: ninguno de mis archivos aparece en ningún finding.

Dato para quien cierre esa tanda: el budget de `behavior_depth: none` es **0**,
o sea que el gate se pone rojo con el primer script que entre sin su prueba de
profundidad. Mover el budget sería el verde barato; lo que corresponde es la
prueba de los tres.

## Lo que NO ejecuté y por qué

- **La migración a `isolation: "worktree"`**: cambia cómo corren todos los
  sub-agentes del operador. Radio de impacto suyo, decisión suya.
- **Cerrar los escapes 1 y 3**: viven en `hooks/agent-bash-cwd-enforcer.sh` y en
  el registro de `.claude/settings.json`. Ambos están fuera de mi partición
  (hay seis agentes tocando hooks y manifests en esta misma tanda).
- **No agregué más texto al prompt.** Si el agente ya ignora un `WORKING DIR:`,
  más instrucción no lo fuerza — eso es el verde barato de esta familia.
- **No borré nada de ADR-223.** La provisión de worktrees es la parte que sí
  funciona y es la única pieza que los otros tres arneses pueden usar.

### Plan para el operador (tres decisiones, no una)

1. **Corto plazo, barato y sin migrar**: registrar el enforcer y pasarlo a
   `deny`. Cierra el escape 1 en Claude Code. Riesgo: es un parser de strings
   sobre el comando —durante esta investigación el mesh bloqueó un `git worktree`
   sobre un repo descartable en `/tmp`, o sea que no distingue el checkout del
   operador de un repo cualquiera— y no cubre "command shape". Es un parche.
2. **Migración**: pasar `isolation: "worktree"` en las llamadas al tool `Agent`
   para agentes de escritura, y desactivar la preparación de ADR-223 en
   `COGNITIVE_OS_HARNESS=claude_code`. Dos cosas que verificar antes:
   (a) la rama sale de la **rama default**, no del `HEAD` del padre — los agentes
   dejan de ver trabajo sin commitear del orquestador; (b) con agent-teams
   activo, un sub-agente con `name` se lanza como teammate y el `isolation` del
   frontmatter no lo evita: hay que pasarlo **en la llamada**.
3. **Los otros tres arneses**: dejar de declarar aislamiento. Lo honesto es
   documentar ADR-223 como *provisión de worktree + convención*, y anotar la
   contradicción de documentación en `manifests/documentation-truth-claims.yaml`
   junto con la corrección de las auditorías de 2026-05-20 y 2026-07-20 que
   marcaban el enforcer como `registered=True`.

> Nota sobre el ledger: no toqué `manifests/pending-truth.yaml` a mano porque lo
> deriva `scripts/cos-pending-truth-aggregator --write` desde nueve superficies;
> un append manual lo pisa el próximo refresh. La entrada de deuda documental
> tiene que entrar por la superficie de origen (la auditoría aspiracional) o por
> `manifests/documentation-truth-claims.yaml`, y eso va junto con la decisión de
> migrar — por eso queda del lado del operador.
