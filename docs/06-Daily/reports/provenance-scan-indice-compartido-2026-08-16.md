# provenance-scan decidía sobre el índice compartido

**Fecha:** 2026-08-16
**Archivo arreglado:** `hooks/provenance-scan.sh` (escritura autorizada por el
operador, `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` acotado a ese path)
**Tests:** `tests/behavior/test_provenance_scan_commit_scope.py` (16 casos)

---

## El defecto

`hooks/provenance-scan.sh:25` invocaba el CLI con `mode="--staged"` siempre. O sea
que juzgaba **el índice entero** en cada invocación, sin mirar nunca su propio
payload de entrada (el hook no leía stdin: no había ni un `cat` ni un `jq`).

Con el idiom que este repo obliga bajo concurrencia —`git commit --only -- <mis
rutas>`— eso es el conjunto equivocado: el commit lleva sólo mi pathspec, pero el
guard bloquea por lo que hayan dejado staged los demás. Y el arreglo que se le
ocurre al bloqueado —destagear lo ajeno— es exactamente lo que la norma de
escritores concurrentes prohíbe. El guard empujaba a la violación.

### Recuento de los bloqueos, con su fuente

```bash
python3 - <<'PY'
import json
rows=[json.loads(l) for l in open('.cognitive-os/metrics/hook-timing.jsonl')
      if 'provenance' in l]
for d in rows:
    if d.get('exit_code')==2: print(d['timestamp'], d['pid'], d['stderr_bytes'])
PY
```

| timestamp (UTC) | local (-03) | pid | stderr_bytes |
|---|---|---|---|
| 2026-08-15T23:28:54Z | 15/08 20:28 | 30693 | 1021 |
| 2026-08-16T02:30:32Z | 15/08 23:30 | 67140 | 335 |
| 2026-08-16T02:30:43Z | 15/08 23:30 | 75604 | 335 |
| 2026-08-16T02:31:24Z | 15/08 23:31 | 11410 | 335 |

Cuatro bloqueos, los cuatro del 15/08 en hora local. Lo que la telemetría **no**
dice está en las correcciones de abajo.

---

## Qué escanea ahora, y por qué lo que dejó de mirar no puede viajar

| Entrada | Antes | Ahora |
|---|---|---|
| `git commit --only -- a.md` (b.md ajeno staged) | índice entero | `a.md` |
| `git commit -a -m ...` | índice (se perdía lo modificado sin stagear) | índice **+** todo lo modificado |
| `git commit -m ...` sin pathspec | índice entero | índice entero (igual) |
| `git commit --amend` sin pathspec | índice entero | índice entero (igual) |
| Edit/Write sobre X | índice entero | `X` |
| Todo lo demás / lo no demostrable | índice entero | índice entero (falla cerrado) |

**El argumento de por qué no abre fuga.**

1. `git commit --only -- a.md` commitea el contenido del **árbol de trabajo** de
   `a.md`, sólo esa ruta, y deja intacto y staged lo del otro agente. No es
   memoria: está medido en repo descartable y quedó escrito como test
   (`test_git_only_commits_the_working_tree_copy_of_the_pathspec`, que verifica
   las tres cosas: contenido committeado, `--name-only` del commit, e índice
   sobreviviente). `b.md` no viaja en ese commit, así que dejar de mirarlo no es
   dejar de mirar algo que viaja.
2. **Una llamada de Edit/Write no crea ningún commit.** Nada viaja en un Edit. El
   contenido staged por otro agente lo sigue escaneando este mismo hook en el
   commit, por el otro punto de entrada (`hooks/bash-hot-path-dispatcher.sh:134`).
   La cobertura no se pierde: se mueve al momento en que el contenido efectivamente
   viaja.
3. El angostamiento es **de una sola dirección**. Todo lo que no se puede probar
   cae a `--staged`: pathspec con glob que no expande, `git -C` a otro repo, flag
   desconocido que podría comerse el token siguiente, payload malformado, `python3`
   ausente, comando sin `git commit`. Escanear de más es una molestia; escanear de
   menos es una fuga.

Además el arreglo **cierra tres fugas preexistentes** que el encargo no mencionaba
(ver "Correcciones a las premisas del encargo", punto 7).

---

## Los cuatro casos del encargo, probados

| Caso | Test | Resultado |
|---|---|---|
| `--only -- a.md` con `b.md` ajeno staged → no mira `b.md` | `test_scoped_commit_ignores_another_agents_staged_leak` | pasa |
| `git commit -a -m` → mira todo lo modificado | `test_commit_all_scans_every_modification` | pasa |
| `git commit -m` sin pathspec → índice entero | `test_bare_commit_still_scans_the_whole_index` | pasa |
| fuga dentro de **mi** pathspec → sigue bloqueando | `test_leak_inside_my_own_pathspec_still_blocks` | pasa |

El cuarto además exige que el mensaje de bloqueo **nombre `mine.md`**: con el
código viejo ese test también daba exit 2, pero por `foreign.md` — bloqueaba bien
por el motivo equivocado. La aserción sobre el nombre es lo que distingue el
arreglo de la casualidad.

---

## Mutation test — desglose

Los tests corren el hook **de verdad** (`bash hooks/provenance-scan.sh`) contra
repos git descartables, con una policy de fixture propia: un patrón sintético de
home ajeno (un usuario inventado bajo `home`), armado por concatenación de
fragmentos para que ni el test ni este informe contengan la ruta literal.

Que el literal no se pueda escribir acá no es una molestia del formato: al primer
intento de commit, `research-compliance-guard` bloqueó este mismo informe por
contener el patrón. O sea que el gate de rutas host-local funciona sobre docs, y
la evidencia de eso es el bloqueo.

Contra el código **anterior** (`uv run pytest tests/behavior/test_provenance_scan_commit_scope.py -q`):
**6 fallan, 9 pasan**. Los seis fallan **por conducta**; ninguno por símbolo
ausente, import roto ni fixture mal armado — el hook existía y corría en los seis.

| Test que falla | Qué demuestra | Familia |
|---|---|---|
| `test_scoped_commit_ignores_another_agents_staged_leak` | el bug del encargo: bloquea por archivo ajeno | sobre-escaneo |
| `test_edit_is_not_blocked_by_another_agents_staged_leak` | el mismo bug por el camino Edit/Write, que es el registrado | sobre-escaneo |
| `test_leak_inside_my_own_pathspec_still_blocks` | bloqueaba, pero nombrando el archivo ajeno | evidencia equivocada |
| `test_policy_fixture_actually_detects_a_leak` | fuga en mi ruta, sólo en árbol de trabajo → **no la veía** | sub-escaneo |
| `test_commit_all_scans_every_modification` | `-a` con fuga sin stagear → **no la veía** | sub-escaneo |
| `test_edit_of_a_file_that_already_leaks_still_blocks` | Edit sobre archivo con fuga sin stagear → **no la veía** | sub-escaneo |

Contra el código **nuevo**: **16 pasan, 0 fallan**. Regresión sobre las suites que
ya tocaban el escáner (`tests/unit/test_provenance_scan.py`,
`tests/red_team/portability/test_provenance_scan.py`,
`tests/red_team/portability/test_provenance-scan.py`,
`tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py`): **34 pasan**.

### Contra el verde barato

El lote tenía tres atajos anunciados y ninguno se tomó:

- **No** se cambió a "sólo los archivos modificados en el working tree": eso no es
  lo que entra al commit (deja afuera lo staged que un `-a` o un commit pelado sí
  llevan). El plan distingue tres modos, y `-a` corre las **dos** pasadas.
- **No** se agregó ninguna variable para saltear el escaneo. `DISABLE_HOOK_PROVENANCE_SCAN`
  ya existía y quedó como estaba. Hay un test tripwire
  (`test_hook_is_not_a_stub`) que falla si aparece un bypass nuevo o si desaparece
  la ruta `--staged`.
- **Ningún** test verifica "que el modo cambió". Todos ejecutan el hook y miran el
  exit code y el archivo que nombra el mensaje.

---

## Parser: duplicado, no reusado

`hooks/git-commit-scope-guard.sh` (commit `3045f71f8`) tiene el parser
autoritativo: tokeniza con `shlex`, parte en segmentos por `&&`/`;`/`|`, y busca
`git [globals] commit` en cada uno. **Se duplicó, no se reusó**, y la razón no es
preferencia:

- ese parser es un **heredoc inline** dentro del hook, sin punto de entrada
  importable;
- sacarlo a `hooks/_lib/` significa **escribir `hooks/git-commit-scope-guard.sh`**,
  que es config protegida y el operador autorizó **sólo** `hooks/provenance-scan.sh`.

Queda escrito como deuda conocida, en la cabecera del propio archivo: **son dos
parsers de la misma gramática y van a divergir.** Lo que se copió: `SEPARATORS`,
`VALUE_FLAGS`, `BOOL_FLAGS`, `GLOBAL_VALUE_OPTS`, `GLOBAL_BOOL_OPTS`, `segments()`
y `find_commit()`. Lo que cambia: el scope-guard responde *"¿tiene scope?"* y éste
responde *"¿cuál es el scope?"*, así que devuelve la lista de tokens en vez de un
booleano, y agrega un caso que el otro no necesita — **flag desconocido ⇒ fallar
cerrado**, porque un flag que no está en las tablas podría comerse el token
siguiente y convertir un mensaje en un pathspec falso.

Si alguna vez se promueve el tokenizer del scope-guard a `hooks/_lib/`, este
duplicado se borra.

---

## Latencia — la máquina está saturada

```
load averages: 31.67  150.40  208.97   (12 cores)
```

**El wall clock de hoy no es portable.** Medición A/B, 5 muestras cada uno,
payload `Edit` sobre `README.md`, `/usr/bin/time -p`:

| | wall (mediana) | CPU user+sys (mediana) |
|---|---|---|
| hook viejo | 0.09 s | 0.06 s |
| hook nuevo | 0.12 s | 0.09 s |

**+30 ms de CPU**, que es el arranque del `python3` del planificador. Es un hook de
pre-commit y de pre-Edit, así que el costo importa: se paga una vez por invocación
y sólo cuando hay payload en stdin. En el camino `git commit -a` se pagan además
dos invocaciones del CLI en vez de una, porque el índice y las modificaciones sin
stagear son dos conjuntos distintos y el CLI ignora las rutas posicionales cuando
recibe `--staged` (`scripts/provenance_scan.py:436-438`).

---

## Correcciones a las premisas del encargo

1. **"`hooks/provenance-scan.sh` corre con `mode="--staged"`"** — **confirmado**,
   línea 25 del archivo original. Es el único punto del diagnóstico que sobrevivió
   entero.

2. **"Ocurrió cuatro veces ayer"** — **confirmado con matiz**. Son 4 filas con
   `exit_code=2` en `hook-timing.jsonl`, pero una es `2026-08-15T23:28:54Z` y tres
   son `2026-08-16T02:30–02:31Z`. Los cuatro caen el 15/08 en hora local (-03), no
   en UTC. Los informes de ayer que dicen **3** (`audit-arq-hooks`,
   `lote2-ambiguos`, `audit-valor-entregado`) no están mal: se escribieron antes
   del cuarto.

3. **"a cuatro agentes distintos"** — **no verificable, y probablemente inflado**.
   Las cuatro filas tienen `session_id: ""` y `session_kind: "orchestrator"`. Lo
   único distinto son los PIDs, y un PID es un proceso de hook, no un agente: cada
   tool call arranca uno nuevo. Tres de los cuatro bloqueos caen en **52 segundos**,
   que es igual de compatible con un agente reintentando tres veces. La telemetría
   no permite contar agentes.

4. **"todas por el mismo archivo ajeno (`tests/behavior/test_orphan_detection_family.py`,
   con una ruta host-local)"** — **falso hasta donde se puede verificar**. Hoy ese
   archivo escanea limpio: `./scripts/provenance-scan tests/behavior/test_orphan_detection_family.py`
   → `provenance-scan-ok`, exit 0. Y el único informe de ayer que **nombra** los
   archivos que dispararon un bloqueo (`sonda-conformidad-familia-2026-08-15.md:283-290`)
   nombra otros: `tests/fixtures/family-probe/home-path-leak/must-not-trigger.md`
   y `tests/audit/test_family_conformance.py`. El mecanismo del encargo es correcto;
   el archivo culpable no. (`stderr_bytes` 1021 en el primer bloqueo vs 335 en los
   otros tres también dice que no fueron todos el mismo mensaje.)

5. **La premisa más cara: el encargo trata al hook como un guard de commit.** Su
   matcher registrado en `.claude/settings.json` es **`Edit|Write`**, no `Bash`.
   El camino de `git commit` le llega por `hooks/bash-hot-path-dispatcher.sh:134`.
   Si me hubiera limitado a "parsear el pathspec del `git commit`" —que es
   literalmente lo que pide el encargo— **el incidente de ayer habría quedado sin
   arreglar**, porque los bloqueos que sufrieron los agentes fueron sobre `Edit`
   (así lo describe `sonda-conformidad-familia-2026-08-15.md`: *"el mismo guard
   bloquea también cualquier Edit sobre cualquier archivo del repo"*). Por eso el
   arreglo cubre los dos caminos.

6. **"Carga ~270 sobre 12 cores"** — desactualizado. Al momento de medir: 31.67 /
   150.40 / 208.97 (1/5/15 min). Sigue siendo alta, y la advertencia del encargo
   —el wall no es portable hoy— se mantiene.

7. **El encargo describe el defecto como sobre-escaneo. También sub-escanea.** Tres
   de los seis tests que fallan contra el código viejo son **fugas**, no molestias:
   con `--staged`, una fuga que existe sólo en el árbol de trabajo era invisible, y
   `git commit --only -- mine.md` y `git commit -a` la habrían llevado igual. El
   guard no sólo bloqueaba de más: dejaba pasar contenido que viajaba.

## Lo que no se sabe

- **Con qué comando exacto se produjeron los cuatro bloqueos.** `hook-timing.jsonl`
  guarda `exit_code` y `stderr_bytes`, no el payload. La reconstrucción de arriba
  cruza tamaños de stderr con los informes de ayer; es inferencia, no registro.
- **Si el camino Edit/Write pierde algo en escenarios que no probé.** El argumento
  ("un Edit no commitea nada") es sólido para este repo, donde el commit está
  gateado por el mismo hook vía el dispatcher. En una instalación donde el
  dispatcher no esté proyectado, el commit quedaría sin escanear — pero eso ya era
  así antes de este cambio.
- **`git commit --pathspec-from-file=<f>`** cae a `--staged` (el flag matchea
  `--[\w-]+=.*` y no deja tokens), o sea que sigue escaneando de más. Correcto pero
  no óptimo; no se agregó soporte porque no hay uso de esa forma en el repo.

---

## Diff completo de `hooks/provenance-scan.sh`

<details>
<summary>328 líneas agregadas, 10 borradas</summary>

```diff
diff --git a/hooks/provenance-scan.sh b/hooks/provenance-scan.sh
index 8f301d170..3f9a11e01 100755
--- a/hooks/provenance-scan.sh
+++ b/hooks/provenance-scan.sh
@@ -1,11 +1,59 @@
 #!/usr/bin/env bash
 # SCOPE: both
 # provenance-scan.sh — block sensitive provenance/local-source leaks.
+#
+# SCOPE OF THE SCAN (fixed 2026-08-16, see
+# docs/06-Daily/reports/provenance-scan-indice-compartido-2026-08-16.md):
+#
+# The hook used to always run the CLI with `--staged`, i.e. it judged the WHOLE
+# shared index on every invocation. Under the concurrent-writer idiom this repo
+# mandates (`git commit --only -- <my paths>`) that is the wrong set: the commit
+# carries only my pathspec, but the guard blocked on whatever the other agents
+# had left staged. It blocked four times on 2026-08-15 (hook-timing.jsonl,
+# exit_code=2) and the "obvious" fix for the blocked agent — unstaging someone
+# else's files — is exactly what the concurrent-writer norm forbids. The guard
+# was pushing towards the violation.
+#
+# It now scans WHAT WILL TRAVEL, and nothing less:
+#
+#   Bash + `git commit --only -- a.md`  -> scans a.md (working-tree content,
+#                                          which is what `--only`/<pathspec>
+#                                          actually commits). Not b.md.
+#   Bash + `git commit -a -m ...`       -> scans the index AND every tracked
+#                                          modification, because all of it enters.
+#   Bash + `git commit -m ...`          -> scans the whole index (unchanged).
+#   Bash + `git commit --amend` (no pathspec) -> whole index (unchanged).
+#   Edit/Write on file X                -> scans X only. An Edit tool call
+#                                          creates no commit, so another agent's
+#                                          staged file cannot travel through it;
+#                                          it is still scanned at commit time by
+#                                          this same hook via
+#                                          hooks/bash-hot-path-dispatcher.sh.
+#   anything unresolvable               -> whole index (fail closed).
+#
+# The narrowing is deliberately one-directional: when the plan cannot be proven
+# (glob pathspec that expands to nothing, `git -C` into another repo, missing
+# python3, malformed payload, unknown commit flag) the hook falls back to
+# `--staged`. Scanning too much is a nuisance; scanning too little is a leak.
+#
+# KNOWN DEBT: the `git commit` tokenizer below is a SECOND parser of the same
+# command string — hooks/git-commit-scope-guard.sh (commit 3045f71f8) has the
+# authoritative one. They were not unified because the scope-guard's parser is
+# an inline heredoc inside that hook, and extracting it into a shared library
+# means writing hooks/git-commit-scope-guard.sh, which is protected config this
+# change was not authorised to touch. Two parsers of one grammar drift; if the
+# scope-guard's tokenizer is ever promoted to hooks/_lib/, this one must be
+# deleted and replaced by it.
 set -uo pipefail
 
 [ "${COS_DISABLE_ALL_GOVERNANCE:-}" = "1" ] && exit 0
 [ "${DISABLE_HOOK_PROVENANCE_SCAN:-}" = "true" ] && exit 0
 
+INPUT=""
+if [ ! -t 0 ]; then
+  INPUT=$(cat 2>/dev/null || true)
+fi
+
 PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
 CLI_PATH="${COS_PROVENANCE_SCAN_CLI:-$PROJECT_DIR/.cognitive-os/bin/provenance-scan}"
 if [ ! -x "$CLI_PATH" ] && [ -x "$PROJECT_DIR/scripts/provenance-scan" ]; then
@@ -22,21 +70,291 @@ fi
 
 [ -x "$CLI_PATH" ] || exit 0
 
-mode="--staged"
-if [ ! -d "$PROJECT_DIR/.git" ]; then
-  mode=""
+# ── Plan the scan set ────────────────────────────────────────────────────────
+# PLAN is a newline-separated list. First line is the mode:
+#   STAGED           — scan the whole index (fail-closed default)
+#   PATHS            — scan the listed repo-relative paths only
+#   STAGED_AND_PATHS — both (the `git commit -a` case)
+#   WORKTREE_ALL     — not a git repo; scan the tree (previous behaviour)
+# Remaining lines are repo-relative paths.
+
+PLAN="STAGED"
+
+if [ ! -d "$PROJECT_DIR/.git" ] && [ ! -f "$PROJECT_DIR/.git" ]; then
+  PLAN="WORKTREE_ALL"
+elif [ -n "$INPUT" ] && command -v python3 >/dev/null 2>&1; then
+  PLAN=$(HOOK_INPUT_JSON="$INPUT" COS_PS_ROOT="$PROJECT_DIR" python3 - <<'PYEOF' 2>/dev/null || printf 'STAGED\n'
+import json, os, re, shlex, subprocess, sys
+
+ROOT = os.environ.get("COS_PS_ROOT", ".")
+
+try:
+    data = json.loads(os.environ.get("HOOK_INPUT_JSON", "") or "{}")
+except Exception:
+    print("STAGED"); sys.exit(0)
+if not isinstance(data, dict):
+    print("STAGED"); sys.exit(0)
+
+tool = str(data.get("tool_name") or "")
+tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
+
+
+def rel(p):
+    """Repo-relative path, or None when the path escapes the repo."""
+    if not p:
+        return None
+    ap = p if os.path.isabs(p) else os.path.join(ROOT, p)
+    try:
+        r = os.path.relpath(os.path.realpath(ap), os.path.realpath(ROOT))
+    except Exception:
+        return None
+    return None if r.startswith("..") else r
+
+
+# ── Edit / Write: only the file being written can carry my leak ──────────────
+if tool in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
+    fp = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
+    r = rel(str(fp))
+    if r:
+        print("PATHS"); print(r); sys.exit(0)
+    print("STAGED"); sys.exit(0)
+
+command = str(tool_input.get("command") or data.get("command") or "")
+if tool and tool != "Bash":
+    print("STAGED"); sys.exit(0)
+if not command:
+    print("STAGED"); sys.exit(0)
+
+# ── Bash: tokenize the command and find every `git commit` invocation ────────
+# NOTE: duplicated grammar — see the KNOWN DEBT note in the file header.
+SEPARATORS = {"&&", "||", ";", "|", "&", "\n"}
+VALUE_FLAGS = {
+    "-m", "--message", "-C", "--reuse-message", "-F", "--file",
+    "--author", "--date", "--trailer", "--cleanup", "--squash",
+    "--fixup", "--pathspec-from-file", "-e", "--edit",
+    "--allow-empty", "--allow-empty-message",
+}
+BOOL_FLAGS = {
+    "--no-edit", "--amend", "--no-verify", "--signoff", "-s",
+    "--verbose", "-v", "--quiet", "-q", "--dry-run", "-n",
+    "--reset-author", "--no-gpg-sign", "--no-status",
+    "--pathspec-file-nul", "--only", "--all", "-a",
+    "--include", "-i", "--patch", "-p",
+}
+GLOBAL_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
+GLOBAL_BOOL_OPTS = {
+    "--no-pager", "-P", "--paginate", "--bare", "--literal-pathspecs",
+    "--no-replace-objects", "--no-optional-locks",
+}
+
+
+def pathspec_of(args):
+    """(pathspec_tokens|None, commits_everything) for the tokens after `commit`."""
+    everything = "-a" in args or "--all" in args
+    out, skip_next, saw_ddash = [], False, False
+    for tok in args:
+        if skip_next:
+            skip_next = False
+            continue
+        if tok == "--":
+            saw_ddash = True
+            continue
+        if saw_ddash:
+            out.append(tok)
+            continue
+        if tok in BOOL_FLAGS:
+            continue
+        if tok in VALUE_FLAGS:
+            skip_next = True
+            continue
+        if re.match(r"^(--[\w-]+=.*|-S.+|-C.+)", tok):
+            continue
+        if re.match(r"^-[a-zA-Z]{2,}$", tok):
+            continue
+        if tok.startswith("-"):
+            # Unknown flag: cannot tell whether it consumes the next token,
+            # so the pathspec cannot be trusted. Fail closed.
+            return None, everything
+        out.append(tok)
+    return out, everything
+
+
+def segments(tokens):
+    cur = []
+    for tok in tokens:
+        if tok in SEPARATORS:
+            if cur:
+                yield cur
+            cur = []
+        else:
+            cur.append(tok)
+    if cur:
+        yield cur
+
+
+def find_commit(seg):
+    for i, tok in enumerate(seg):
+        if tok != "git" and not tok.endswith("/git"):
+            continue
+        j, cdir = i + 1, ""
+        while j < len(seg):
+            t = seg[j]
+            if t in GLOBAL_VALUE_OPTS:
+                if t == "-C" and j + 1 < len(seg):
+                    cdir = seg[j + 1]
+                j += 2
+                continue
+            if t in GLOBAL_BOOL_OPTS:
+                j += 1
+                continue
+            if re.match(r"^--(git-dir|work-tree|namespace|exec-path)=", t):
+                j += 1
+                continue
+            break
+        if j < len(seg) and seg[j] == "commit":
+            return seg[j + 1:], cdir
+    return None
+
+
+def expand(tokens):
+    """Resolve pathspec tokens to repo-relative paths, or None if unprovable."""
+    resolved = []
+    for tok in tokens:
+        r = rel(tok)
+        if r and os.path.exists(os.path.join(ROOT, r)):
+            resolved.append(r)
+            continue
+        # Glob / pathspec magic / deleted path: ask git what it matches.
+        try:
+            res = subprocess.run(
+                ["git", "ls-files", "--cached", "--others", "--exclude-standard",
+                 "-z", "--", tok],
+                cwd=ROOT, capture_output=True, check=False, timeout=20,
+            )
+        except Exception:
+            return None
+        if res.returncode != 0:
+            return None
+        matched = [m for m in res.stdout.decode("utf-8", "replace").split("\0") if m]
+        if not matched:
+            # Nothing matched: either a deleted path (no content travels) or a
+            # pathspec we failed to understand. Cannot prove it is the former.
+            return None
+        resolved.extend(matched)
+    return resolved
+
+
+try:
+    tokens = shlex.split(command, posix=True)
+except ValueError:
+    print("STAGED"); sys.exit(0)
+
+paths, saw_commit, everything = [], False, False
+for seg in segments(tokens):
+    found = find_commit(seg)
+    if not found:
+        continue
+    saw_commit = True
+    args, cdir = found
+    if cdir and rel(cdir) not in ("", "."):
+        print("STAGED"); sys.exit(0)   # commit into another repo: unprovable here
+    spec, seg_everything = pathspec_of(args)
+    if seg_everything:
+        everything = True
+    if spec is None:
+        print("STAGED"); sys.exit(0)
+    if not spec:
+        if not seg_everything:
+            print("STAGED"); sys.exit(0)   # bare commit: the whole index enters
+        continue
+    resolved = expand(spec)
+    if resolved is None:
+        print("STAGED"); sys.exit(0)
+    paths.extend(resolved)
+
+if not saw_commit:
+    print("STAGED"); sys.exit(0)
+
+if everything:
+    # `git commit -a` takes the index PLUS every tracked modification.
+    try:
+        res = subprocess.run(["git", "diff", "--name-only", "-z"], cwd=ROOT,
+                             capture_output=True, check=False, timeout=20)
+        if res.returncode != 0:
+            print("STAGED"); sys.exit(0)
+        paths.extend(m for m in res.stdout.decode("utf-8", "replace").split("\0") if m)
+    except Exception:
+        print("STAGED"); sys.exit(0)
+    print("STAGED_AND_PATHS")
+else:
+    print("PATHS")
+
+seen = set()
+for p in paths:
+    if p not in seen and os.path.isfile(os.path.join(ROOT, p)):
+        seen.add(p)
+        print(p)
+PYEOF
+  )
+  [ -n "$PLAN" ] || PLAN="STAGED"
 fi
 
-if [ -f "$CONFIG_PATH" ]; then
-  "$CLI_PATH" --config "$CONFIG_PATH" $mode >/tmp/cos-provenance-scan-hook.out 2>/tmp/cos-provenance-scan-hook.err
-else
-  "$CLI_PATH" $mode >/tmp/cos-provenance-scan-hook.out 2>/tmp/cos-provenance-scan-hook.err
+MODE_LINE="${PLAN%%$'\n'*}"
+PLAN_REST=""
+case "$PLAN" in
+  *$'\n'*) PLAN_REST="${PLAN#*$'\n'}" ;;
+esac
+
+SCAN_PATHS=()
+if [ "$MODE_LINE" = "PATHS" ] || [ "$MODE_LINE" = "STAGED_AND_PATHS" ]; then
+  if [ -n "$PLAN_REST" ]; then
+    while IFS= read -r line; do
+      [ -n "$line" ] && SCAN_PATHS+=("$line")
+    done <<< "$PLAN_REST"
+  fi
+  # A PATHS plan with nothing left to scan means nothing with content travels.
+  if [ "$MODE_LINE" = "PATHS" ] && [ ${#SCAN_PATHS[@]} -eq 0 ]; then
+    exit 0
+  fi
 fi
-code=$?
+
+# ── Run the scan ─────────────────────────────────────────────────────────────
+
+OUT_FILE=/tmp/cos-provenance-scan-hook.out
+ERR_FILE=/tmp/cos-provenance-scan-hook.err
+: >"$OUT_FILE" 2>/dev/null || true
+: >"$ERR_FILE" 2>/dev/null || true
+code=0
+
+_run_cli() {
+  local cli_args=()
+  [ -f "$CONFIG_PATH" ] && cli_args+=(--config "$CONFIG_PATH")
+  cli_args+=("$@")
+  "$CLI_PATH" ${cli_args[@]+"${cli_args[@]}"} >>"$OUT_FILE" 2>>"$ERR_FILE"
+}
+
+case "$MODE_LINE" in
+  WORKTREE_ALL)
+    _run_cli || code=$?
+    ;;
+  PATHS)
+    _run_cli "${SCAN_PATHS[@]}" || code=$?
+    ;;
+  STAGED_AND_PATHS)
+    _run_cli --staged || code=$?
+    if [ ${#SCAN_PATHS[@]} -gt 0 ]; then
+      _run_cli "${SCAN_PATHS[@]}" || code=$?
+    fi
+    ;;
+  *)
+    _run_cli --staged || code=$?
+    ;;
+esac
+
 if [ $code -ne 0 ]; then
   echo "BLOCKED: provenance-scan found sensitive provenance or local-source leakage." >&2
-  cat /tmp/cos-provenance-scan-hook.err >&2 2>/dev/null || true
-  cat /tmp/cos-provenance-scan-hook.out >&2 2>/dev/null || true
+  cat "$ERR_FILE" >&2 2>/dev/null || true
+  cat "$OUT_FILE" >&2 2>/dev/null || true
   exit 2
 fi
 exit 0
```

</details>
