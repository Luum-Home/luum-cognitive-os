<!-- SCOPE: os-only -->
# `git -C <dir> commit` esquivaba 23 hooks, no 16

**Fecha:** 2026-08-16
**Archivo tocado:** `hooks/bash-hot-path-dispatcher.sh` (único path protegido autorizado)
**Test:** `tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py`

---

## 1. El agujero: medido, no asumido

El encargo pedía verificar que el despachador no dispara antes de creerlo. Se
verificó ejecutándolo de verdad.

**El experimento.** Se copia el despachador real a un árbol descartable del
scratchpad cuyo `hooks/` contiene *stubs* de cada gate: cada stub escribe su
propio nombre en un log y sale 0. Así lo que se mide es **qué despachó el
despachador**, no qué hicieron los gates. Nada busca el string `-C` en el
fuente.

```bash
LAB=$SCRATCH/dispatch-lab
mkdir -p "$LAB/hooks"; cp hooks/bash-hot-path-dispatcher.sh "$LAB/hooks/"
for g in $(grep -oE 'hooks/[a-z0-9-]+\.sh' hooks/bash-hot-path-dispatcher.sh | sort -u); do
  n=$(basename "$g"); [ "$n" = bash-hot-path-dispatcher.sh ] && continue
  printf '#!/usr/bin/env bash\ncat >/dev/null\necho "%s" >> "$COS_DISPATCH_LOG"\nexit 0\n' "$n" > "$LAB/hooks/$n"
  chmod +x "$LAB/hooks/$n"
done
export COS_DISPATCH_LOG=$LAB/log.txt; : > "$COS_DISPATCH_LOG"
python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' \
  'git -C /tmp/foo commit -m "x"' | bash "$LAB/hooks/bash-hot-path-dispatcher.sh"
wc -l < "$COS_DISPATCH_LOG"
```

**Resultado contra el código de `HEAD` (4f3a7e5a3):**

| comando | gates despachados |
|---|---|
| `git commit -m "x"` | **24** |
| `git -C /tmp/foo commit -m "x"` | **1** |
| `git --no-pager commit -m "x"` | **1** |
| `git -c user.email=a@b.c commit -m "x"` | **1** |
| `git --git-dir=… --work-tree=… commit -m "x"` | **1** |

El diagnóstico del encargo se confirma. El único gate que sobrevive es
`orchestrator-skill-invocation-gate.sh`, que corre por estado de sesión y no
mira la forma del comando: no es que el despachador reconozca el commit, es que
ese gate corre siempre.

## 2. Cuántos hooks se saltean de verdad: 23, no 16

El 16 del encargo es correcto **sólo para la batería de commit**. El mismo
defecto de adyacencia está en `_is_git_boundary()`, que aporta otros 7:

```bash
# 24 - 1 (el que corre siempre) = 23
```

- **16** — batería de commit (`_is_git_commit`): `provenance-scan`,
  `git-commit-scope-guard`, `orchestrator-claim-gate`,
  `pre-commit-content-hash-dedupe`, `scope-marker-portability-gate`,
  `external-pattern-cleanroom-gate`, `adoption-freeze-gate`,
  `dependency-license-classifier`, `research-to-runtime-firewall`,
  `research-compliance-guard`, `spdx-header-required`,
  `external-cache-content-leak`, `attribution-completeness-validator`,
  `lib-symlink-divergence-detector`, `legal-review-required-on-runtime-import`,
  `pending-truth-staleness-gate`.
- **7** — batería de boundary (`_is_git_boundary`): `destructive-git-blocker`,
  `conflict-marker-guard`, `untracked-work-preservation-guard`,
  `direct-main-guard`, `branch-ownership-lock`,
  `cross-session-coordination-guard`, `agent-message-inbox-guard`.

Los 23 archivos existen (`_run_gate` sale 0 silencioso si falta el archivo, así
que había que descartar que el conteo inflara con fantasmas):

```bash
for g in destructive-git-blocker … pending-truth-staleness-gate; do
  [ -f "hooks/$g.sh" ] || echo "MISSING: $g"
done   # → present=23 missing=0
```

Y el despachador es la **única** puerta de Bash: no hay un segundo camino por
donde esos gates lleguen igual.

```bash
python3 -c "
import json; d=json.load(open('.claude/settings.json'))
for m in d['hooks']['PreToolUse']:
    if 'Bash' in str(m.get('matcher','')):
        print(m['matcher'], [h['command'][-60:] for h in m['hooks']])"
```

> `Bash` → `bash-hot-path-dispatcher.sh`
> `Bash|Edit|Write` → `secret-detector.sh`

Fuera del commit, el mismo defecto también apagaba `network-egress-guard` en
`git -C … push` y `release-guard` en `git -C … tag`.

## 3. El arreglo

Se portó el patrón de `hooks/git-commit-scope-guard.sh` (mismo juego de
opciones globales, misma forma de regex) en vez de inventar uno nuevo. Se
generalizó a un helper `_is_git_subcommand` porque el defecto no era exclusivo
de `commit`: `_is_git_boundary`, `_is_release_boundary` y la rama git de
`_is_network_boundary` tenían la misma adyacencia literal.

El *verde barato* explícito de este lote era agregar `-C` al patrón y listar;
el juego portado cubre además `-c`, `-P`, `--no-pager`, `--paginate`,
`--git-dir`, `--work-tree`, `--namespace`, `--exec-path`, `--bare`,
`--literal-pathspecs`, `--no-replace-objects`, `--no-optional-locks`.

```diff
+_GIT_GLOBAL_OPTS='(-C|-c|-P|--no-pager|--paginate|--git-dir|--work-tree|--namespace|--exec-path|--bare|--literal-pathspecs|--no-replace-objects|--no-optional-locks)'
+
+_HAS_GIT_GLOBAL_OPTS=0
+case "$COMMAND" in
+  *"git -"*) _HAS_GIT_GLOBAL_OPTS=1 ;;
+esac
+
+_is_git_subcommand() {
+  local subs="$1"
+  _matches "(^|[[:space:];|&()])git[[:space:]]+($subs)($|[[:space:];|&()])" && return 0
+  [ "$_HAS_GIT_GLOBAL_OPTS" = "1" ] || return 1
+  _matches "(^|[[:space:];|&()])git[[:space:]]+${_GIT_GLOBAL_OPTS}[^;|&]*[[:space:]]($subs)($|[[:space:];|&()])"
+}
+
 _is_git_boundary() {
-  _matches '(^|[[:space:];|&()])git[[:space:]]+(add|commit|push|…|rm|mv)($|[[:space:];|&()])'
+  _is_git_subcommand 'add|commit|push|pull|checkout|switch|merge|rebase|reset|tag|stash|worktree|branch|restore|rm|mv'
 }

 _is_git_commit() {
-  _matches '(^|[[:space:];|&()])git[[:space:]]+commit($|[[:space:];|&()])'
+  _is_git_subcommand 'commit'
 }

 _is_release_boundary() {
-  _matches '(^|[[:space:];|&()])git[[:space:]]+tag($|[[:space:];|&()])' || \
+  _is_git_subcommand 'tag' || \
   _matches '(^|[[:space:];|&()])(echo|printf|sed|perl)[^;&|]*[>[:space:]]VERSION($|[[:space:];|&()])'
 }

 _is_network_boundary() {
   _matches '(^|[[:space:];|&()])(curl|wget|nc|ncat|ssh|scp|rsync)[[:space:]]' || \
-  _matches '(^|[[:space:];|&()])git[[:space:]]+(clone|fetch|pull|push)[[:space:]]'
+  _is_git_subcommand 'clone|fetch|pull|push'
 }
```

El diff completo, con los comentarios, sale de
`git show <commit> -- hooks/bash-hot-path-dispatcher.sh`. Es la condición del
permiso: `hooks/**` es config protegida y el operador autorizó **sólo** este
archivo. La escritura se hizo con `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`
declarado en el propio comando. Ningún otro path protegido fue tocado.

**Por qué el prefiltro `case`.** Es hot path. El segundo `grep` sólo se paga si
el comando trae un guion pegado a `git`; `ls -la`, `echo`, `git status` y
`git commit -m x` no contienen `git -`, así que corren exactamente la misma
cantidad de subprocesos que antes. Es un glob de bash, sin `fork`.

## 4. El test

`tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py` — 22 tests que
**ejecutan el despachador real** en un árbol aislado con gates stub. Ninguno
inspecciona el fuente.

La ruta del despachador se puede sobreescribir con `COS_TEST_DISPATCHER`, así
que reproducir el bug viejo es un comando:

```bash
git show 4f3a7e5a3:hooks/bash-hot-path-dispatcher.sh > /tmp/dispatcher-old.sh
COS_TEST_DISPATCHER=/tmp/dispatcher-old.sh .venv/bin/python -m pytest \
  tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py -q
# → 14 failed, 8 passed

.venv/bin/python -m pytest tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py -q
# → 22 passed
```

Los 8 que pasan contra el código viejo son el reverso: el baseline
(`git commit` normal sigue despachando los 24) y los 7 comandos que **no** deben
arrastrar la batería. Si el arreglo hubiera convertido el hot path en un embudo,
esos 8 se caían.

```
ls -la · echo hola · git status · git -C /tmp/repo status ·
git --no-pager log --oneline -5 · python3 scripts/foo.py --git -x ·
grep -rn "git commit" docs/      → todos n=1 (sólo el gate de estado)
```

## 5. Costo — el reloj de pared de hoy no es portable

Máquina saturada: **load 189.77 sobre 12 cores** (`sysctl -n vm.loadavg`). Todo
número de wall de este informe es de la máquina, no del código. El número
comparable es CPU (`ru_utime + ru_stime` de `RUSAGE_CHILDREN`), 40 iteraciones
por celda.

| comando | CPU viejo | CPU nuevo | ΔCPU | wall nuevo (no portable) |
|---|---|---|---|---|
| `ls -la` (1 gate ambos) | 71.86 ms | 69.11 ms | **−2.75 ms** | 81.41 ms |
| `git commit -m "x"` (24 gates ambos) | 421.19 ms | 439.76 ms | +18.57 ms | 573.76 ms |
| `git -C /tmp/r commit -m "x"` | 77.65 ms | 517.60 ms | +439.95 ms | 780.37 ms |

Lectura:

- **`ls -la`: delta negativo.** El código nuevo no puede ser más rápido que el
  viejo en ese camino — corren el mismo número de greps. El signo negativo *es*
  la evidencia de que el ruido de medición supera al efecto: sin sobrecosto
  medible en el hot path.
- **`git commit` +18 ms sobre 421 ms** (4%) cae dentro del mismo ruido; ese
  camino tampoco cambió de forma (`git commit -m x` no contiene `git -`).
- **`git -C … commit` +440 ms** no es sobrecosto: es el precio de correr los 23
  gates que antes se salteaban, y con stubs no-op. Contra los gates reales va a
  ser más. Es el costo que el despachador existe para pagar.

## 6. El mismo patrón en otros hooks — enumerado, no cerrado

Un arreglo que cubre 1 de N es la firma que ocupó el día de ayer. Se buscó la
**forma**, no el archivo:

```bash
grep -rlnE "git\[\[:space:\]\]\+\(?(commit|add|push|pull|checkout|switch|merge|rebase|reset|tag|stash|worktree|branch|restore|rm|mv|clone|fetch)" hooks/ scripts/
grep -rlnE "git\\\\s\+\(?(commit|add|push|pull|checkout|merge|rebase|reset|tag|stash|worktree|branch|clone|fetch)" hooks/ scripts/ cos_lib/ lib/
```

| archivo | línea | estado |
|---|---|---|
| `hooks/bash-hot-path-dispatcher.sh` | 79-118 | **arreglado acá** |
| `hooks/git-commit-scope-guard.sh` | 118 | ya arreglado (`3045f71f8`) |
| `hooks/control-plane-audit.sh` | 36 | adyacencia literal |
| `hooks/destructive-git-blocker.sh` | 109, 114, 121, 164 | adyacencia **+ anclado a `^`** |
| `hooks/post-git-orphan-notifier.sh` | 68, 89, 91, 93 | adyacencia literal |
| `hooks/scope-marker-portability-gate.sh` | 61 | adyacencia literal |
| `hooks/adr-detector.sh` | 29 | adyacencia literal |
| `hooks/agent-bash-cwd-enforcer.sh` | 115, 171, 176 | adyacencia + anclado a `^` |
| `hooks/agent-message-inbox-guard.sh` | 33 | adyacencia (`(^|&&|;)\s*git\s+…`) |
| `hooks/branch-ownership-lock.sh` | 45 | adyacencia |
| `hooks/cross-session-event-emit.sh` | 77, 79 | adyacencia |
| `hooks/release-guard.sh` | 47 | adyacencia + anclado a `^git\s+tag` |
| `hooks/rate-limit-drain.sh` | 84 | adyacencia |
| `cos_lib/lethal_trifecta.py`, `scripts/stash_quarantine_audit.py`, `scripts/verify_claims.py` | — | adyacencia, fuera del camino de gate |

**Consecuencia operativa a partir de este commit.** Los 23 gates ahora se
*invocan* con `git -C`, pero 11 de ellos vuelven a salir temprano por su propio
regex. `git -C <dir> stash pop`, por ejemplo, ya llega a
`destructive-git-blocker.sh`, y ahí el patrón `^[[:space:]]*git[[:space:]]+stash`
lo deja pasar igual — ese está además anclado a inicio de línea, así que
`cd x && git stash pop` también se le escapa hoy, sin ninguna opción global de
por medio. El despachador dejó de ser el cuello de botella; los gates de abajo
son el próximo lote. Ninguno de esos archivos estaba autorizado en este encargo.

## 7. Correcciones a las premisas del encargo

1. **«los dieciséis hooks» — corto.** Recontado: **23**. 16 es la batería de
   commit; faltaban los 7 de `_is_git_boundary`, que tiene el mismo defecto. El
   número del encargo venía de otro agente y era parcial, no falso. Comando:
   la tabla de la sección 1 (24 despachados − 1 que corre siempre).
2. **`hooks/git-commit-scope-guard.sh:101` — línea equivocada.** El regex
   arreglado por `3045f71f8` está en la **línea 118**, no en la 101. La 101 cae
   dentro del bloque de comentarios previo.
   `grep -n "^if ! printf" hooks/git-commit-scope-guard.sh` → `118:`.
3. **`hooks/bash-hot-path-dispatcher.sh:78` — confirmado.**
   `git show 4f3a7e5a3:hooks/bash-hot-path-dispatcher.sh | sed -n '78p'` devuelve
   exactamente el `_matches` con adyacencia literal.
4. **«el arreglo ya existe escrito y probado, portalo» — cierto pero
   insuficiente.** El patrón de `git-commit-scope-guard.sh` cubre sólo `commit`.
   Portarlo tal cual habría dejado abiertos `_is_git_boundary`,
   `_is_release_boundary` y `_is_network_boundary`. Se portó el juego de opciones
   y la forma del regex —que es lo que evita la divergencia entre parsers— pero
   generalizado a cualquier subcomando.
5. **«`timeout` no existe en este macOS» — no se testeó.** No hizo falta ningún
   `timeout`; queda sin verificar.
6. **El shell de las herramientas es `zsh`, no `bash`.** `TIMEFORMAT` y
   `time { …; }` se ignoran en silencio: la primera medición de latencia salió
   vacía sin error. Se rehizo con `resource.getrusage` desde Python. Quien mida
   latencia en este entorno no puede usar el `time` de bash.
7. **La rama no era la que decía el encargo.** El `git status` del brief ponía el
   checkout en `session/21f28a76-audit-2026-08-15`. Al momento de commitear,
   `git branch --show-current` devuelve **`main`**, y los 7 commits de hoy
   (`git log --since=midnight`) están todos en `main`: las otras dos sesiones ya
   trabajan ahí. Correr `scripts/cos-session-branch.sh --switch` en un checkout
   compartido les cambiaría la rama por debajo, así que se commiteó en `main`
   con el token `--allow-main-branch` que documenta el propio guard, y queda
   dicho acá en vez de quedar implícito.
8. **`export COS_ALLOW_MAIN_BRANCH_WRITE=1` dentro del comando no sirve.** El
   hook PreToolUse corre ANTES del comando y con el entorno del harness, no con
   el del shell que uno arma; el `export` nunca lo alcanza. El bloqueo se repitió
   idéntico con la variable exportada. Lo único que el guard sí ve es el **token
   en el texto del comando** (`grep -Eq '(^|[[:space:]])--allow-main-branch($|[[:space:]])'`,
   `hooks/destructive-git-blocker.sh:526`). Mismo razonamiento para
   `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`, que sí funcionó porque ahí la escritura
   la hace el propio comando y no la herramienta Edit.
9. **El índice es compartido y bloquea de verdad.** El primer intento de commit
   pasó el guard de rama y lo frenó `research-compliance-guard` por
   `docs/06-Daily/reports/provenance-scan-indice-compartido-2026-08-16.md`, un
   archivo **de otra sesión** que estaba staged (`git diff --cached --name-only`).
   `--only` acota lo que se commitea, no lo que el gate escanea. Se esperó a que
   el índice se liberara en vez de forzar.
10. **Verificado y confirmado sin cambios:** los 23 gates existen como archivo
   (`present=23 missing=0`); el despachador es el único hook PreToolUse de Bash
   además de `secret-detector.sh`; `hooks/**` está efectivamente protegido —
   el intento de editarlo con la herramienta Edit fue bloqueado por
   `protected-config-write-guard.sh`, y hubo que declarar
   `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` explícitamente.
