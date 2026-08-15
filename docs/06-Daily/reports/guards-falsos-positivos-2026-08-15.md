# Dos guards que se trababan entre sí — 2026-08-15

Dieciséis entregables no entraban al repo porque dos controles se bloqueaban
mutuamente: uno rechazaba un informe **sobre** fugas de rutas de home, y el otro
rechazaba el `git restore --staged` con el que se salía de ese estado.

Los dos quedaron arreglados por la causa, no por el síntoma. Este informe deja el
recuento, los diffs, y el mutation-test de cada relajación en las dos direcciones.

---

## Correcciones a las premisas del encargo

El encargo pedía explícitamente recontar antes de citar. Recontado:

| Premisa del encargo | Verificación | Veredicto |
|---|---|---|
| 4 coincidencias en el informe bloqueado, todas del runner de CI | `grep -coE '/Users/[A-Za-z0-9._-]+'` → `4`; las 4 líneas son 34, 46, 351, 473 y todas dicen `runner` | **Confirmada** |
| `grep "$HOME" <archivo>` da 0 | exit 1, cero líneas | **Confirmada** |
| `git restore --staged` sólo toca el índice | `git-restore(1)`: *"Specifying --staged will only restore the index"* | **Confirmada** |
| El guard 2 imprime `línea 382: checkout: orden no encontrada` | Reproducido en vivo; además el mensaje al operador salía mutilado: `Rationale: discards working-tree changes (modern equivalent of )` | **Confirmada, y peor de lo reportado** |
| Los 12 informes figuran como `??` en `git status` | Figuran como `A` (**staged**), no como `??`. También estaban staged `scripts/compare_claim_runs.py`, `scripts/context_injection_report.py` y los dos tests unitarios | **Falsa** — el intento previo dejó staged todo el lote, no sólo el informe de QA |
| 32 verdes en los tres archivos de tests | `32 passed in 0.74s` | **Confirmada** |
| `research-compliance-guard.sh` necesita el discriminador de `3a6e737ba` para el caso documentado | El caso canónico (`/Users/[a-zA-Z0-9._-]+`) **ya pasaba** antes de tocar nada: `HOME_PATH_RE` usa la clase `[A-Za-z0-9._-]+`, que no puede empezar con `[`, así que nunca disparó ahí | **Parcialmente falsa** — ver abajo |

### Lo que era falso del encargo

**1. Los 16 entregables no estaban sin trackear: estaban staged.** El encargo decía
`??`; `git status --porcelain` decía `A`. Cambia poco el resultado y cambia mucho el
riesgo: si hubiera obedecido "bajá los 12 que figuran como `??`" con un `git add`
de directorio, habría barrido también los `.jsonl` de métricas que el propio
encargo prohíbe tocar.

**2. El discriminador de `3a6e737ba` no era lo que faltaba acá.** Medido antes de
escribir una línea: un archivo con el patrón documentado canónico ya pasaba este
guard. Copiarlo tal cual habría sido agregar un supresor que no suprime nada —
exactamente el bug invisible que la norma de gates describe. Lo que sí faltaba era
**extraer el segmento de usuario completo**: `HOME_PATH_RE` corta en el primer
carácter ilegal en una cuenta, o sea justo donde empieza la evidencia para
juzgarlo. Con la extracción arreglada el discriminador **sí** queda vivo (cubre
`/Users/user[0-9]+`, donde el prefijo `user` sí matchea y el guard sí disparaba), y
hay un test que lo prueba. Se implementó así: extracción primero, discriminador
después, y ninguno de los dos como decoración.

**3. Una restricción del encargo resultó ser real y otra no.** `hooks/**` está
efectivamente protegido: el `Edit` fue rechazado por `protected-config-write-guard`
sobre los dos archivos autorizados, y hubo que aplicar los parches por Bash con
`COS_ALLOW_PROTECTED_CONFIG_WRITE=1`. En cambio la prohibición de usar
`COS_ALLOW_DESTRUCTIVE_GIT=1` nunca hizo falta: no se desestageó nada.

### Hallazgo no pedido: el guard 2 se auto-bypassea

Al escribir los tests apareció algo que no estaba en el diagnóstico y que importa
más que los tres bloqueos reportados.

`destructive-git-blocker.sh` tiene un `_is_bypass_context()` que devuelve
verdadero, entre otras cosas, cuando **`PYTEST_CURRENT_TEST` está definida**. En
ese estado el guard permite todo en silencio y loguea `so_internal_context`. La
primera versión de la suite mostró **10 casos peligrosos "permitidos"** —
`git reset --hard`, `git clean -fd`, `git stash pop` — no porque la relajación se
hubiera desbordado, sino porque el guard nunca llegó a decidir.

El propio hook documenta el contrato correcto:

> *"Agents running under pytest/CI must still be blocked; otherwise a malicious or
> buggy sub-agent could exploit the test harness env to destroy state."*

Y lo cumple: con `CLAUDE_AGENT_ID` presente bloquea. Pero eso significa que
**cualquier suite que no simule contexto de agente mide el bypass, no el guard**, y
pasa en verde por la peor de las razones. Es el "verde barato" del encargo,
encontrado del lado de la verificación en vez del lado del arreglo. La suite nueva
tiene un test dedicado (`test_agent_context_is_what_the_suite_actually_exercises`)
que falla si el harness vuelve a caer en el bypass.

Detalle adicional para quien escriba tests contra este hook: **el código de salida
depende del contexto** — `2` en contexto de usuario, `1` en contexto de agente. Una
aserción `== 2` da falso rojo bajo agente. Las aserciones son sobre "rechazó" más
el banner, no sobre un número.

**No lo arreglé** (está fuera de los dos archivos autorizados en su parte de
diseño, y cambiar cuándo un guard se auto-bypassea es una decisión de operador, no
un bug tipográfico). Queda reportado.

---

## Guard 1 — `hooks/research-compliance-guard.sh`

### Diagnóstico

Las 4 coincidencias del informe bloqueado son `/Users/runner/`, la ruta fija del
workspace de un runner de GitHub Actions. Es idéntica en todos los runners del
mundo: identifica una **clase de máquina**, no a una persona. El informe la
clasificaba así en su propio texto y concluía cero fugas — y no podía commitearse
por decir eso.

Este era el más crudo de los tres enforcers de la familia: `check-local-privacy.sh`
tiene `PLACEHOLDER_USERS` y `ALLOWED_POSIX_PREFIXES` (con `jovyan`),
`check_absolute_paths.py` tiene `PLACEHOLDER_USER_SEGMENTS`, y éste no tenía
ninguna forma de excepción — un `grep -Eq` booleano por archivo y nada más.

### El límite que no se cruzó

La pregunta que decide cada entrada: *¿esta cadena identifica a una persona en
alguna máquina?* `runner` califica porque es una ruta de CI publicada y fija.
`admin`, `dev`, `ubuntu` **no** califican: en algún lado son la cuenta real de
alguien. Hay un test que lo fija (`test_a_plausible_username_is_not_exempt`), y
también prueba `runners` — para que la pertenencia sea por igualdad exacta y no por
substring.

Dos decisiones de diseño que acotan la relajación:

- **La detección no se tocó.** `HOME_PATH_RE` es idéntico. El token ancho se usa
  sólo para *clasificar* un hallazgo que ya existe, así que el camino nuevo sólo
  puede **quitar** un hallazgo, nunca agregar uno.
- **Fail-closed.** Si un archivo matchea `HOME_PATH_RE` pero no se le puede extraer
  ningún token clasificable, **no** queda exento: sigue bloqueando. Una forma que
  el clasificador no entiende bloquea, no pasa.

### Mutation test — las dos direcciones

Sobre un repo temporal, con el guard real leyendo el índice:

```
CASO                                          ANTES     DESPUÉS
A  runner de CI (macOS)                       BLOCK  →  PASS      ← relajación
E  runner de CI (Linux)                       BLOCK  →  PASS      ← relajación
C  patrón documentado /Users/[a-zA-Z0-9._-]+  PASS   →  PASS      (ya pasaba)
F  patrón documentado /Users/user[0-9]+       BLOCK  →  PASS      ← relajación
G  mención suelta de la raíz en un snippet    PASS   →  PASS
B  ruta de home REAL                          BLOCK  →  BLOCK     ← sigue firme
D  runner + ruta real en el MISMO archivo     BLOCK  →  BLOCK     ← sigue firme
```

**El caso D es el que importa.** Prueba que la exención es **por token, no por
archivo**: un archivo que menciona el runner no queda blanqueado, la fuga de la
línea 2 se sigue detectando. Sin ese caso, la relajación habría sido "si el archivo
habla de CI, dejalo pasar" — que es justo cómo un control deja de serlo.

Sobre el árbol real, después del arreglo:

```
$ echo '{"tool_input":{"command":"git commit -m x"}}' | bash hooks/research-compliance-guard.sh
exit=0
```

Antes: `exit=2`, con el hallazgo sobre `qa-contrafactual-aisotropy-2026-08-15.md`.

### Lo que quedó bloqueado a propósito

- Cualquier segmento de usuario que sea un nombre de cuenta legal y no esté en la
  lista corta: **bloquea**. La lista tiene una sola entrada (`runner`).
- Un archivo cuyo hallazgo no se puede tokenizar: **bloquea** (fail-closed).
- La regla de clones de research, la de código runtime que referencia caches de
  research, y la de licencias: **sin tocar**.

---

## Guard 2 — `hooks/destructive-git-blocker.sh`

### Diagnóstico

Tres defectos, los tres confirmados:

1. **`git restore --staged <path>` bloqueado.** `git-restore(1)` es explícito:
   *"Specifying --staged will only restore the index."* Es el desestage moderno, el
   equivalente de `git reset HEAD <file>`. El working tree no se toca.
2. **`git reset -- <path>` bloqueado.** Con pathspec, git no mueve HEAD y no toca
   el árbol; además rechaza `--hard`/`--merge`/`--keep` en esa forma.
3. **Bug propio en la línea 382.** Backticks dentro de un `echo` con comillas
   dobles: bash ejecutaba `checkout` como comando, escupía el error a stderr, y
   sustituía su salida vacía en el mensaje al operador, que quedaba
   `(modern equivalent of )` — sin el referente que explicaba el bloqueo.

El guard tiene **dos capas**: un clasificador semántico en Python (que sí ve
flags) y un `DESTRUCTIVE_PATTERN` grueso de fallback que matchea `reset` y
`restore` incondicionalmente. Arreglar sólo la primera no alcanza: la segunda
vuelve a bloquear. Por eso el clasificador emite un veredicto nuevo, `index_only`,
y el loop de despacho hace `continue` (salta el segmento entero) en vez de
`break` — así el fallback no puede re-bloquear lo que el parser acaba de despejar.
El parser es la única capa que puede ver flags, así que es la única que puede
otorgarlo.

### Lo que se relajó, y con qué precisión

- `restore`: exento sólo si hay `--staged`/`-S` **y** no hay `--worktree`/`-W`.
- `reset`: exento sólo si hay separador `--` explícito **con al menos una ruta
  después**, y ningún `--hard`/`--merge`/`--keep`/`--soft`. Se exige el `--` a
  propósito: `git reset HEAD file` sin separador es ambiguo y **sigue bloqueado**
  en vez de adivinado.

### Mutation test — las dos direcciones

```
DEBE PASAR (sólo índice)                        exit
  git restore --staged docs/x.md                 0    ← antes 2
  git restore -S docs/x.md                       0    ← antes 2
  git reset -- docs/x.md                         0    ← antes 2
  git reset HEAD -- docs/x.md                    0    ← antes 2

DEBE SEGUIR BLOQUEANDO (toca el árbol)          exit
  git restore docs/x.md                          2    ← sin --staged: descarta
  git restore --staged --worktree docs/x.md      2    ← --worktree escribe el árbol
  git restore --source=HEAD docs/x.md            2
  git reset --hard HEAD~1                        2
  git reset --hard                               2
  git reset --merge                              2
  git reset HEAD docs/x.md                       2    ← sin `--`: ambiguo
  git checkout -- docs/x.md                      2
  git clean -fd                                  2
  git stash pop                                  2
```

Y el bug de la línea 382, antes y después:

```
ANTES:   hooks/destructive-git-blocker.sh: línea 382: checkout: orden no encontrada
         Rationale: discards working-tree changes (modern equivalent of )

DESPUÉS: Rationale: discards working-tree changes (modern equivalent of `checkout --`)
         (stderr sin errores de shell)
```

### Veredicto sobre la reparación que sugería el guard

**Coincido con la observación del encargo, y la corregí.**

El guard sugería, para *toda* operación destructiva, `git stash push -u -m '...'`.
Sin pathspec, ese comando **barre el working tree entero** — incluidos los archivos
sin trackear y sin stagear de otra sesión — dentro de una sola entrada. Sobre un
checkout compartido eso es más destructivo que la operación que pretende reparar:
desestagear un archivo afecta un archivo; el stash sin scope afecta todo el árbol.

Peor: es exactamente el residuo por el que existe `ADR-055b r5`. El propio guard
bloquea `git stash pop` con el motivo *"stash ops can re-enact prior state from
user-context or pop the wrong entry"*. Recomendar como reparación el mismo tipo de
operación cuya recuperación el guard considera peligrosa es una contradicción
interna.

Texto nuevo:

```
inspect with 'git status --porcelain' and 'git diff -- <path>' first;
if you must park work, scope it:
git stash push -u -m 'pre-destructive-git-<reason>' -- <path>
```

Primero la inspección no mutante; y si hay que aparcar trabajo, con pathspec. Hay
un test que falla si vuelve a aparecer un `git stash push` sin `-- <path>`.

---

## Los tests

`tests/unit/test_guard_false_positives.py` — **23 verdes**, cada relajación fijada
en las dos direcciones.

Con guarda de población, porque un test que pasa por no haber encontrado nada que
revisar es teatro:

- `test_both_guards_exist_and_are_executable` — falla si un guard se renombra o se
  mueve, en vez de dejar que todo lo demás pase vacío.
- `test_agent_context_is_what_the_suite_actually_exercises` — prueba que el harness
  llega a la decisión real: con marcador de agente el guard rechaza, sin marcador
  el mismo comando pasa por el bypass. Sin este test, los 10 casos peligrosos
  pasaban en verde sin que el guard opinara.
- `_clean_env()` — limpia `COS_*` y `CLAUDE_*` del entorno ambiente.
  `CLAUDE_TOOL_INPUT` en particular tiene precedencia sobre stdin dentro del
  blocker: una suite corrida dentro de una sesión viva habría evaluado el comando
  de la sesión en vez del que estaba bajo test.

El archivo de tests arma los literales de rutas en tiempo de ejecución
(`"/" + "Users" + "/"`) para no disparar los guards que él mismo ejercita.

## Verificación de los entregables

```
$ .venv/bin/python -m pytest tests/unit/test_compare_claim_runs.py \
    tests/unit/test_context_injection_report.py \
    tests/contracts/test_session_start_tooling_contract.py -q
32 passed in 0.74s
```

---

## Lo que NO se hizo

- **No se editó el informe** para que dejara de matchear. Ya se intentó esta mañana
  y se revirtió en `3a6e737ba` como *"cambió lo medido en vez de la medición"*.
- **No se amplió ningún regex** hasta que dejara de molestar. `HOME_PATH_RE` y
  `DESTRUCTIVE_PATTERN` están intactos; lo que se agregó es una clasificación
  posterior, acotada y fail-closed.
- **No se usó ningún bypass**: ni `COS_ALLOW_DESTRUCTIVE_GIT`, ni
  `--allow-destructive`, ni `COS_ALLOW_RESEARCH_COMPLIANCE_BYPASS`. El punto era
  que no hiciera falta, y no hizo falta.
- **No se tocó ningún path protegido fuera de los dos autorizados.**
  `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` se usó sólo para esos dos archivos.
- **No se arregló el auto-bypass del guard 2** — reportado arriba, es decisión de
  operador.

---

## Diff completo de los dos hooks

```diff
diff --git a/hooks/destructive-git-blocker.sh b/hooks/destructive-git-blocker.sh
index 8587453dc..d21c87f88 100755
--- a/hooks/destructive-git-blocker.sh
+++ b/hooks/destructive-git-blocker.sh
@@ -224,6 +224,20 @@ def emit(kind: str, op: str, wip: int = 0) -> None:
 if sub == "stash" and args and args[0] in {"pop", "drop", "apply"}:
     emit("destructive", f"git stash {args[0]}")
 if sub == "reset":
+    # `git reset [<tree-ish>] -- <paths>` never moves HEAD and never touches
+    # the working tree: with a pathspec, git resets index entries only, and it
+    # refuses --hard/--merge/--keep in that form outright. It is the classic
+    # unstage, and the modern spelling of it (`git restore --staged`) is
+    # handled below. The explicit `--` separator is what makes the pathspec
+    # unambiguous, so it is required: `git reset HEAD file` without it stays
+    # blocked rather than guessed at. --hard/--merge/--keep/--soft anywhere in
+    # the args disqualify, belt-and-braces against a future git that permits
+    # the combination.
+    _tree_touching = {"--hard", "--merge", "--keep", "--soft"}
+    if "--" in args and not _tree_touching.intersection(args):
+        _paths = args[args.index("--") + 1 :]
+        if any(a.strip() for a in _paths):
+            emit("index_only", "git reset -- <pathspec>")
     emit("destructive", "git reset")
 if sub == "pull" and "--rebase" in args:
     emit("destructive", "git pull --rebase", 1)
@@ -241,6 +255,15 @@ if sub == "switch":
 if sub == "clean" and any(arg.startswith("-") and "f" in arg for arg in args):
     emit("destructive", "git clean -f")
 if sub == "restore":
+    # git-restore(1): "Specifying --staged will only restore the index."
+    # Index-only, so nothing in the working tree is discarded — this is the
+    # modern `git reset HEAD <file>`. --worktree/-W alongside it restores both
+    # and stays blocked, as does plain `git restore <path>`, which is the
+    # genuinely destructive form.
+    _staged = any(a in {"--staged", "-S"} for a in args)
+    _worktree = any(a in {"--worktree", "-W"} for a in args)
+    if _staged and not _worktree:
+        emit("index_only", "git restore --staged")
     emit("destructive", "git restore")
 if sub == "revert":
     emit("destructive", "git revert")
@@ -279,6 +302,15 @@ while IFS= read -r segment; do
   trimmed="${segment#"${segment%%[![:space:]]*}"}"
   semantic_hit=$(_semantic_git_match "$trimmed" || true)
   if [ -n "$semantic_hit" ]; then
+    # An index_only verdict means the parser proved the segment touches the
+    # index and nothing else (unstage forms). Skip the whole segment rather
+    # than break: the coarse DESTRUCTIVE_PATTERN below matches `reset` and
+    # `restore` unconditionally and would otherwise re-block what the parser
+    # just cleared. The semantic parser is the only layer that can see flags,
+    # so it is the only layer that can grant this.
+    if [ "$(printf '%s' "$semantic_hit" | awk -F '\t' '{print $1}')" = "index_only" ]; then
+      continue
+    fi
     FIRST_HIT="$trimmed"
     FIRST_HIT_TYPE=$(printf '%s' "$semantic_hit" | awk -F '\t' '{print $1}')
     SEMANTIC_OP_NAME=$(printf '%s' "$semantic_hit" | awk -F '\t' '{print $2}')
@@ -379,7 +411,7 @@ _op_rationale() {
     "git clean -f")
       echo "force-delete untracked files including generated state and WIP";;
     "git restore")
-      echo "discards working-tree changes (modern equivalent of `checkout --`)";;
+      echo 'discards working-tree changes (modern equivalent of `checkout --`)';;
     "git revert")
       echo "creates new commits that may conflict unexpectedly with in-flight work";;
     "git worktree")
@@ -421,7 +453,13 @@ _op_repair_command() {
     branch_context_change)
       echo "announce current branch, target branch, reason, and rerun with --allow-branch-switch if approved";;
     *)
-      echo "git stash push -u -m 'pre-destructive-git-<reason>' && inspect the named stash before any restore";;
+      # `git stash push -u` was suggested here for every destructive op. On a
+      # shared checkout it is strictly worse than most of what it repairs: it
+      # sweeps the ENTIRE working tree, including another session's untracked
+      # and unstaged work, into a single entry, and ADR-055b r5 exists because
+      # restoring such an entry re-enacts state nobody asked for. Scope the
+      # advice to the file at hand and prefer the non-mutating inspection.
+      echo "inspect with 'git status --porcelain' and 'git diff -- <path>' first; if you must park work, scope it: git stash push -u -m 'pre-destructive-git-<reason>' -- <path>";;
   esac
 }
 
diff --git a/hooks/research-compliance-guard.sh b/hooks/research-compliance-guard.sh
index 4a2e5bf34..fbe081b84 100755
--- a/hooks/research-compliance-guard.sh
+++ b/hooks/research-compliance-guard.sh
@@ -63,6 +63,78 @@ failures=()
 MAC_HOME_SEG='/'"Users"
 LINUX_HOME_SEG='/'"home"
 HOME_PATH_RE="(^|[^A-Za-z0-9_.-])((${MAC_HOME_SEG}|${LINUX_HOME_SEG})/[A-Za-z0-9._-]+|${MAC_HOME_SEG}/[^.][^/[:space:]]+/Projects/)"
+# Wider token, used ONLY to classify a hit that HOME_PATH_RE already produced —
+# never to create one. HOME_PATH_RE stops at the first character illegal in an
+# account name, so the user segment it captures is truncated exactly where the
+# evidence needed to judge it begins. Detection semantics are unchanged: the
+# classification below can only remove a finding, never add one.
+HOME_TOKEN_RE="(${MAC_HOME_SEG}|${LINUX_HOME_SEG})/[^/[:space:]]+"
+
+# User segments that are not a personal home by construction.
+#
+# `runner` is the fixed home of a GitHub Actions runner: identical on every
+# runner in the world, published in the runner image, allocated to a machine
+# rather than to a person. The bar for adding an entry here is that question
+# and only that question — *does this string identify a person on some
+# machine?* If the answer is "it depends", it does not belong. A username that
+# merely happens to be common (admin, dev, ubuntu) does NOT qualify: somewhere
+# it is someone's actual account.
+#
+# Observed 2026-08-15: a report auditing home-path leakage blocked its own
+# commit on four matches, all of them the CI runner path, which the report
+# itself classified as CI before concluding zero leaks.
+CI_MACHINE_SEGMENTS=" runner "
+
+# Placeholder segments, kept in parity with PLACEHOLDER_USERS in
+# scripts/check-local-privacy.sh and PLACEHOLDER_USER_SEGMENTS in
+# scripts/check_absolute_paths.py.
+PLACEHOLDER_SEGMENTS=' <user> {user} $USER ${USER} USER ... '
+
+# True when the segment is a pattern *matching* usernames rather than being
+# one. Same discriminator as `describes_a_username` in
+# scripts/check-local-privacy.sh (commit 3a6e737b): none of []()*+?\|^$ is
+# legal in a POSIX or macOS account name, so a segment containing one is
+# describing usernames by construction. Exact, not heuristic — it cannot mask
+# an accidental commit of a real path, only a deliberately obfuscated one,
+# which this guard never caught.
+_describes_a_username() {
+  case "$1" in
+    *'['*|*']'*|*'('*|*')'*|*'*'*|*'+'*|*'?'*|*'\'*|*'|'*|*'^'*|*'$'*) return 0 ;;
+  esac
+  return 1
+}
+
+_is_exempt_home_segment() {
+  local seg="$1"
+  [ -n "$seg" ] || return 1
+  case "$CI_MACHINE_SEGMENTS" in *" $seg "*) return 0 ;; esac
+  case "$PLACEHOLDER_SEGMENTS" in *" $seg "*) return 0 ;; esac
+  _describes_a_username "$seg"
+}
+
+# True when EVERY home-path token in the file is provably not a personal home.
+# Fail-closed on purpose: a file with no extractable token is not exempt, so a
+# hit shape this function cannot parse keeps blocking instead of slipping past.
+_home_paths_all_exempt() {
+  local file="$1" token seg found=0
+  while IFS= read -r token; do
+    [ -z "$token" ] && continue
+    seg="${token#*/}"
+    seg="${seg#*/}"
+    # Only tokens whose segment opens with a character legal in an account
+    # name can have produced a HOME_PATH_RE hit in the first place. A segment
+    # opening with a quote or a backtick is the tail of a shell snippet that
+    # merely mentions the home root — HOME_PATH_RE never fired on it, so it
+    # must not be allowed to deny an exemption either.
+    case "$seg" in
+      [A-Za-z0-9._-]*) ;;
+      *) continue ;;
+    esac
+    found=1
+    _is_exempt_home_segment "$seg" || return 1
+  done < <(grep -oE "$HOME_TOKEN_RE" "$file" 2>/dev/null)
+  [ "$found" -eq 1 ]
+}
 
 add_failure() {
   failures+=("$1")
@@ -92,7 +164,7 @@ while IFS= read -r rel; do
   size="$(wc -c < "$abs" 2>/dev/null || echo 0)"
   [ "${size:-0}" -gt 1048576 ] && continue
 
-  if grep -Eq "$HOME_PATH_RE" "$abs" 2>/dev/null; then
+  if grep -Eq "$HOME_PATH_RE" "$abs" 2>/dev/null && ! _home_paths_all_exempt "$abs"; then
     add_failure "$rel: contains a personal absolute home path; use repo-local or redacted paths"
   fi
 
```
