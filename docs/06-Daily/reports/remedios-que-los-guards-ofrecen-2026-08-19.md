<!-- SCOPE: os-only -->
# Los remedios que los guards ofrecen (2026-08-19)

## Resumen ejecutivo

Los once mensajes que ofrecian una salida inejecutable quedaron en cero, medido
con el mismo instrumento que los conto: `.venv/bin/python3 scripts/audit_killswitch_activation.py`
pasa de `mentira 11 de 24 medibles` a `mentira 0 de 22 medibles`.

Nueve de los once solo necesitaban **texto**: los siete hooks de licencia y
atribucion leen la variable del entorno, y el mensaje ahora ofrece `export`
antes de lanzar el arnes en vez del prefijo que nunca les llega. Los otros dos
—los dos mensajes de `git-commit-scope-guard.sh`— necesitaban **una linea de
codigo**, y no la que parecia: el hook llamaba a `cos_bypass_allows` sin haber
sourceado el resolvedor, asi que el kill-switch de ADR-241 estaba muerto entero.
El tercer defecto, el remedio que rompe a los vecinos, se confirmo midiendo:
`--switch` mueve el HEAD de todas las sesiones del checkout.

## Correcciones a las premisas del encargo

1. **El censo da 144/24/11, no 143/23/11.** Al recontar antes de citar:
   `poblacion: 144  medibles: 24 / mentira 11`. La diferencia de uno es
   consistente con que otra sesion estaba editando `hooks/research-compliance-guard.sh`
   en el momento del censo del encargo. Las **11 mentiras** si coinciden.

2. **`COS_BYPASS_COMMIT_GUARD` no es "un kill-switch que no existe": es uno que
   existe, esta documentado y estaba muerto por una linea faltante.** El encargo
   dice que el hook "no la consulta ni del entorno ni del texto". Lo consulta:

   ```
   $ grep -n 'cos_bypass_allows' hooks/git-commit-scope-guard.sh
   123:if type cos_bypass_allows >/dev/null 2>&1 && cos_bypass_allows commit_guard; then
   ```

   Y el resolvedor mapea la clave desde antes de esta sesion
   (`git show HEAD:hooks/_lib/bypass-resolver.sh | grep -n commit_guard` -> `57`),
   y ADR-241 y `docs/09-Quality/security/bypass-cheatsheet.md` la documentan como
   clave estable. Lo que faltaba era el `source` del resolvedor: sin el,
   `type cos_bypass_allows` falla, el `&&` corta, y **ninguna** via funcionaba
   —ni el prefijo, ni el `export`, ni `bypass.env`, ni lo que promete el
   cheatsheet—. La direccion de la mentira no era "sobra el mensaje": era
   "el codigo esta a una linea de ser cierto".

3. **"Casi ningun mensaje menciona bypass.env" es cierto, pero `bypass.env` no
   arregla a la mayoria.** Solo seis hooks sourcean el resolvedor
   (`grep -rln bypass-resolver hooks/` -> 6). Los siete hooks de licencia leen
   `${VAR:-0}` a mano y nunca pasan por el. Ofrecerles `bypass.env` habria sido
   cambiar una mentira por otra; para esos, la unica via cierta es el entorno.

4. **`hooks/git-commit-scope-guard.sh`, `hooks/attribution-completeness-validator.sh`
   y `hooks/spdx-header-required.sh` ya estaban modificados por otras sesiones**
   (`git status --porcelain -- <paths>` antes de tocarlos). Son borrados de
   comentarios de latencia, ajenos a esto. No entraron en mi commit: se
   reconstruyo HEAD+mio para el commit y se restauro el contenido ajeno despues
   (`scripts` de proceso en el scratchpad; verificado con `git diff -- <paths>`
   despues del commit, que sigue mostrando los hunks ajenos sin commitear).

5. **La regla 4 del encargo (prefijar `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`)
   funciona, y es la excepcion que confirma el diagnostico**: ese guard si lee el
   token del texto del comando, que es la compensacion canonica. No aplica a los
   siete hooks de licencia, que no leen el comando.

## Las dos poblaciones: los que necesitan codigo y los que necesitan texto

| Poblacion | Cuantos | Por que | Que se hizo |
|---|---|---|---|
| Solo texto | 9 de 11 | El hook lee `${VAR:-0}` del entorno. `export` antes de lanzar el arnes y el bloque `env` de `settings.json` si llegan; el prefijo en linea no. | Reescribir el mensaje con la via cierta y decir explicitamente por que el prefijo no llega. |
| Codigo (una linea) | 2 de 11 | `git-commit-scope-guard.sh` llamaba a `cos_bypass_allows` sin sourcear `hooks/_lib/bypass-resolver.sh`. | `source` del resolvedor + mensaje que ofrece `bypass.env`, la via en caliente. |

Los nueve de texto, por archivo: `adoption-freeze-gate.sh` (2),
`clean-room-ast-similarity-gate.sh` (2), `attribution-completeness-validator.sh`,
`external-cache-content-leak.sh`, `legal-review-required-on-runtime-import.sh`,
`lib-symlink-divergence-detector.sh`, `spdx-header-required.sh`.

El hallazgo es ese reparto: **la mayoria era texto**, y el unico caso de codigo
resulto ser una linea faltante, no una funcionalidad nueva.

## Los tres defectos, uno por uno, con sus dos direcciones

### Defecto 1 — la forma inejecutable (9 mensajes)

Representante: `hooks/spdx-header-required.sh`, corrido de verdad contra un repo
descartable con el arbol de hooks copiado al lado (varios hooks derivan su
`ROOT_DIR` del propio script, asi que copiarlos es lo que permite dispararlos sin
tocar el indice compartido de este checkout):

```
## 2. spdx-header-required (representante de los 7 que solo leen del entorno)
  A sin remedio                                  -> exit 1
  B con el prefijo VIEJO (debe seguir bloqueado) -> exit 1
  C con el remedio NUEVO (export en el entorno)  -> exit 0
  --- mensaje que ve el bloqueado ---
    Bypass (logged): export COS_ALLOW_MISSING_SPDX=1
      Read from the environment of the harness process: export it in the shell
      that LAUNCHES the harness, or add it to the env block of .claude/settings.json.
      In front of the git commit command it is set for git, not for this hook, which
      ran earlier as a child of the harness, in its own process.
```

Las dos direcciones estan: con el remedio procede (C), sin el remedio sigue
bloqueando (A), y la forma vieja —la que el mensaje ya no ofrece— sigue sin
funcionar (B). Congelado en
`tests/contracts/test_killswitch_activation_is_executable.py::test_spdx_*`.

El censo, antes y despues:

```
$ .venv/bin/python3 scripts/audit_killswitch_activation.py
    mentira                  11 de 24 medibles (45.8%)     # antes
    mentira                  0 de 22 medibles (0.0%)       # despues
```

Y el baseline de deuda del gate quedo **vacio**, no agrandado:
`KNOWN_UNREACHABLE_KILLSWITCHES: set[str] = set()`. El propio gate tiene un test
que rechaza entradas rancias y asientos fantasma, asi que vaciarlo era el unico
final valido.

### Defecto 2 — la variable que el hook no leia

```
## 1. git-commit-scope-guard
  A sin remedio          -> exit 2
  B con bypass.env       -> exit 0
  C con el prefijo viejo -> exit 2
  D con export previo    -> exit 0
  audit-trail escrito en B:
{"ts":"2026-08-20T02:18:44Z","event":"commit-guard-bypassed","session":"unknown","command":"git commit -m x"}
```

Antes del `source`, **B y D tambien daban 2**: esa es la medicion que probo que
el problema no era el texto sino el cableado. Ahora el mensaje ofrece
`printf 'COS_BYPASS=commit_guard\n' >> .cognitive-os/runtime/bypass.env` y
reintentar, que es la unica via que sirve a mitad de sesion, y el bypass deja
rastro auditable. La direccion contraria (C) sigue bloqueada.

### Defecto 3 — el remedio que rompe a los vecinos

```
## 3. destructive-git-blocker :: protected_branch_write (commit sobre main)
  A sin remedio                                     -> exit 2
  B con el token que ofrece el mensaje (comentario) -> exit 0
```

El token `# --allow-main-branch` como comentario al final si funciona: el hook lo
lee del texto del comando (`_has_allow_main_branch_flag`, con las comillas ya
despojadas). Eso quedo como esta. Lo que cambio es la linea `SAFER`, que ahora
dice:

```
     SAFER:        bash scripts/cos-session-branch.sh --slug <task>
                   Creates session/<id>-<task> without moving HEAD.
                   Do NOT add --switch on a checkout shared by several
                   sessions: it runs git switch on the whole working
                   tree, so every other session changes branch too.
```

Anecdota que vale como evidencia de campo: mientras preparaba estas pruebas, el
propio `destructive-git-blocker` me bloqueo un `git switch` de laboratorio, y el
`git-commit-scope-guard` me bloqueo un heredoc que contenia el texto
`COS_BYPASS_COMMIT_GUARD=1 git commit -m "..."`. Los mensajes que estaba
arreglando me los leyo el guard a mi, en produccion.

## Que decidi sobre `COS_BYPASS_COMMIT_GUARD` y por que

**Le di implementacion —una linea de `source`— en vez de sacarlo del mensaje.**
El encargo pedia el argumento, no la asuncion, y el argumento es que la pregunta
estaba mal planteada de mi lado tambien hasta que mire el codigo:

- **No es un bypass nuevo.** ADR-241 (accepted) lo lista como una de las siete
  variables consolidadas, `hooks/_lib/bypass-resolver.sh:57` mapea la clave
  `commit_guard` desde antes de esta sesion, el hook ya tenia la llamada **y** el
  registro en `agent-audit-trail.jsonl`, y `docs/09-Quality/security/bypass-cheatsheet.md`
  lo publica como clave estable. Lo unico que faltaba era el `source`.
- **La alternativa dejaba tres mentiras en vez de una.** Sacar el ofrecimiento de
  los dos mensajes no hacia nada con la cabecera del hook, con el cheatsheet que
  el operador lee, ni con ADR-241. Un operador que sigue el cheatsheet escribe
  `bypass.env`, no pasa nada, y no tiene como saber por que: exactamente el
  defecto que este trabajo ataca, un piso mas arriba.
- **El riesgo de habilitarlo es acotado y auditable.** El paso por el bypass
  escribe una linea en `agent-audit-trail.jsonl` (lo verifique, esta arriba). El
  archivo `.cognitive-os/runtime/bypass.env` estaba vacio al momento de cablear
  (`cat` -> `COS_BYPASS=""`), asi que el cableado no cambio el comportamiento de
  ninguna sesion viva. Y sigue estando gitignored, o sea que no viaja.
- **El caso legitimo no lo necesita.** El mensaje ya ofrece `--only -- <paths>`,
  `-a -m` y `-- <path> -m`, que resuelven cualquier commit honesto. El bypass
  queda para el residuo, con rastro. Si en vez de eso hubiera dejado el `if` sin
  `source`, quedaba codigo muerto que el proximo lector iba a interpretar como
  "el bypass existe" —la misma trampa, en el codigo en vez del mensaje.

Lo que **no** hice, y es donde el default seguro si mando: no cablee `bypass.env`
en los siete hooks de licencia. Ahi si habria sido superficie nueva —ADR-241 no
los incluye— y habria permitido apagar un gate a mitad de sesion escribiendo un
archivo.

## Es peligroso `--switch`? La evidencia

Si. Medido sobre repos descartables:

```
## 3b. --switch, medido sobre un checkout limpio
  HEAD antes  (proceso 1): refs/heads/main
  HEAD antes  (proceso 2): refs/heads/main
  exit=0
  HEAD despues (proceso 1): refs/heads/session/368ba2a8-probe
  HEAD despues (proceso 2): refs/heads/session/368ba2a8-probe

## 3c. sin --switch (lo que ofrece ahora el mensaje)
  Status: PASS / Action: created / Branch: session/2be4137c-otra
  HEAD despues: refs/heads/main
  ramas:        main session/2be4137c-otra

## 3d. --switch sobre un arbol sucio (el caso real de hoy)
  Refusing to create/switch session branch with a dirty worktree.
  exit=3
```

La linea que lo explica es `scripts/cos-session-branch.sh:87`:
`git -C "$REPO_ABS" switch "$BRANCH"`. `REPO_ABS` es el checkout, no la sesion:
el HEAD es un archivo del repo, compartido por todos los procesos que trabajan
ahi. Los dos agentes que hoy lo chocaron y lo descartaron tenian razon, y el
"peligroso aca" era literal.

Ademas es inutil justo cuando se lo necesita: con el arbol sucio —el estado
normal de este checkout con cuatro sesiones— se niega con exit 3. O sea que el
remedio ofrecido era daniño en el caso limpio e inoperante en el sucio. Sin
`--switch` la orden hace lo unico que hacia falta: crea la rama y no toca HEAD.

Congelado en `test_ningun_mensaje_ofrece_cos_session_branch_con_switch`, que
barre `hooks/**/*.sh` y falla si alguien vuelve a ofrecerlo.

## Lo que NO hice y por que

- **No toque los 99 casos "ambiguos"** (`set VAR=1`, `override with VAR=1`, sin
  nombrar via). El instrumento los declara fuera de su alcance a proposito y el
  gate no los cuenta; tocarlos en masa habria sido el sed prohibido. Quedan como
  deuda medible: el dia que se decida, el censo ya los tiene aislados.
- **No cablee el resolvedor en los siete hooks de licencia** (argumentado
  arriba): habria sido superficie de bypass nueva, y en caliente.
- **No toque `hooks/_lib/bypass-resolver.sh`**: lo esta editando el orquestador.
  Queda una nota: si algun dia ningun hook usa el alias `commit_guard`, sobra;
  hoy lo usa `git-commit-scope-guard.sh`, asi que esta vivo.
- **No arregle el prefijo roto que tambien tiene ADR-241** en su ejemplo
  (`docs/02-Decisions/adrs/ADR-241-consolidated-cos-bypass-allowlist.md:127`
  escribe la clave con `echo` a `bypass.env`, eso esta bien; el ejemplo del
  cheatsheet si lo corregi porque ofrecia el prefijo en linea). Un ADR accepted
  no se edita de costado.
- **No corri la suite entera.** Corri las que tocan lo que cambie:
  `tests/contracts/test_killswitch_activation_is_executable.py` (20 passed) y
  las tres suites de `destructive-git-blocker` (151 passed, 1 failed). El fallo
  —`test_wip_block_message_lists_recovery_options`, que espera
  `COS_ALLOW_RESET_OVER_WIP=1` en el mensaje del WIP guard— es previo: mis dos
  hunks en ese archivo estan en las lineas 733 y 1084, y el mensaje del WIP guard
  no esta en ninguno de los dos. Queda reportado, no arreglado: es de otra
  familia y de otro dueño.

## Como reproducir todo esto

```bash
.venv/bin/python3 scripts/audit_killswitch_activation.py          # censo: 0 mentiras
.venv/bin/python3 -m pytest tests/contracts/test_killswitch_activation_is_executable.py -q
```
