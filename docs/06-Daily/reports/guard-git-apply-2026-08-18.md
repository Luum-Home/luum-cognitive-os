# El guard de config protegida no miraba adentro de los parches

**Fecha:** 2026-08-18
**Archivo tocado:** `hooks/protected-config-write-guard.sh` (+ `tests/hooks/test_protected_config_write_guard.py`)
**Estado:** cerrado, con tests que fallan sobre el código anterior y pasan sobre el nuevo.

## 1. La reproducción

El guard clasifica cada segmento del comando por su palabra de comando y busca
rutas protegidas **en el texto del comando**. `git apply x.patch` tiene una sola
ruta en su texto —el `.patch`— y escribe rutas que no aparecen en ningún lado.

Parche usado (`evil.patch`):

```
--- a/hooks/algo.sh
+++ b/hooks/algo.sh
@@ -1,1 +1,1 @@
-old
+pwned
```

Alimentando el hook real con el payload `{"tool_name":"Bash","tool_input":{"command":"..."}}`,
contra `HEAD` (`030e055c2`):

| comando | exit |
|---|---|
| `git apply $D/evil.patch` | **0** |
| `git apply --check $D/evil.patch` | 0 |
| `git apply -R $D/evil.patch` | **0** |
| `git am $D/evil.patch` | **0** |
| `patch -p1 < $D/evil.patch` | **0** |
| `git apply $D/nope.patch` (no existe) | **0** |

Seis de seis pasan. El diagnóstico del encargo se sostiene.

Hay un segundo mecanismo que lo tapaba, y no estaba en el encargo: aunque el
analizador hubiera sabido leer parches, **el prefiltro de la fast path nunca lo
habría llamado**. El prefiltro sale por 0 cuando el payload crudo no contiene el
prefijo literal de ningún glob protegido, y en `git apply /tmp/evil.patch` no hay
ninguno. Por eso el arreglo toca dos capas, no una.

## 2. Qué rutas se extraen y de dónde

No es un parser de diffs. Tres formas de línea llevan destinos:

| línea | por qué |
|---|---|
| `+++ b/RUTA` | donde el parche escribe |
| `--- a/RUTA` | donde un borrado nombra a su víctima, y donde escribe `-R` |
| `diff --git a/VIEJO b/NUEVO` | donde un rename puro nombra ambos y no hay hunk |

`/dev/null` se descarta. De cada ruta se evalúan **dos** lecturas: la cruda y la
misma sin el prefijo `a/` o `b/`, porque `-p1` es el default y `-p0` no strippea;
adivinar el nivel de `-p` podía quitar un bloqueo, y un candidato de más sólo
puede agregar uno.

De dónde sale el texto del parche, por forma de comando:

| forma | fuente |
|---|---|
| `git apply F` / `git am F` | los argumentos posicionales |
| `git apply < F`, `patch -p1 < F` | el destino de la redirección de stdin |
| `git apply - <<'EOF' … EOF` | el cuerpo del heredoc, que ya extraía `strip_heredocs` |
| `patch -i F`, `patch --input=F` | el valor de la opción |
| `patch ORIGINAL [F]` | **ninguna**: `patch` con original explícito escribe ese archivo y nada más, y ese archivo ya es una palabra del comando que el camino normal juzga |
| pipe (`cat F \| git apply`), `git apply` pelado | ninguna → **bloqueo** |

`strip_heredocs` ahora devuelve además los pares `(línea de cabecera, cuerpo)`:
un heredoc alimentado a un aplicador de parches no es dato ni programa, es el
parche, y el segmento que lo consume tiene que poder encontrar su propio cuerpo.

## 3. Fail-closed: qué bloquea sin que ningún glob lo diga

Tres hallazgos no se expresan como ruta y bloquean por sí mismos, con el motivo
adjunto en el mensaje (`FORCED_BLOCKS`):

- `unreadable patch source: F` — el parche no existe o no se puede leer.
- `not a unified diff: F` — el texto no tiene ninguna de las tres formas de línea.
- `patch source not inspectable: …` — el contenido no está en disco (pipe,
  sustitución de proceso, stdin sin origen).

## 4. Las dos decisiones que el encargo pedía por escrito

### `--check` pasa

`git apply --check` parsea el parche y reporta si aplicaría. No toca el working
tree, no toca el índice, no toca los destinos. Es además la pregunta que un
operador hace **antes** de pedir aprobación, y un guard que bloquea el ensayo es
un guard que alguien apaga. Pasa, y el caso está pinneado en dos tests
(`git-apply-check`, `git-apply-check-reverse`).

Costo aceptado: `--check` no lee el parche, así que un parche ilegible con
`--check` tampoco bloquea. No importa — con `--check` no hay escritura que
prevenir.

Alcance deliberadamente mínimo: `--stat`, `--numstat` y `--summary` tampoco
escriben, y **no** están exceptuados. Sobre un parche a `docs/` pasan igual
porque el destino no es protegido; sobre uno a `hooks/**` bloquean. Es un
sobre-bloqueo chico y consciente, en la dirección segura.

### `-R` / `--reverse` bloquea

Revertir escribe. No necesitó caso especial: como se leen **los dos** lados de
cada hunk, el lado que `-R` escribe ya estaba en la lista. Pinneado en
`git-apply-reverse` y `git-apply-reverse-long`.

`git am --abort` / `--quit` / `--continue` también bloquean: no traen parche
legible y la postura es fail-closed. Es una consecuencia asumida, no un descuido;
el prefijo de aprobación los deja pasar y queda la fila en el ledger.

## 5. El mutation test, con desglose

`.venv/bin/python -m pytest tests/hooks/test_protected_config_write_guard.py -q`

**Contra el código actual** (el hook de `HEAD` vía `COS_GUARD_UNDER_TEST`):

```
26 failed, 186 passed in 17.71s
```

Las 26, todas **por conducta** (el guard sale 0 donde el test exige 2) — ninguna
por error de import, fixture, timeout ni entorno:

| grupo | n | qué falla |
|---|---|---|
| `test_patch_writing_a_protected_path_is_blocked[…]` | 17 | `git apply`, `-p0`, `-R`, `--reverse`, `< F`, `- < F`, `-3`, `git am`, `patch -p1 <`, `patch <`, `patch -i`, `patch --input=`, borrado, rename, mixto docs+hooks, `sudo`-wrapped, segundo segmento |
| `test_patch_source_that_cannot_be_read_is_blocked[…]` | 4 | pipe, curl-pipe, `git apply` pelado, pipe a `patch` |
| `test_missing_patch_file_is_blocked` | 1 | parche inexistente |
| `test_unreadable_patch_file_is_blocked` | 1 | parche con `chmod 000` |
| `test_text_that_is_not_a_unified_diff_is_blocked` | 1 | archivo que no es un diff |
| `test_heredoc_patch_is_read_as_a_patch` | 1 | parche por heredoc |
| `test_block_message_names_the_path_from_inside_the_patch` | 1 | el mensaje no nombra la ruta de adentro del parche |

Los casos de **paso** (docs-only, tests-only, `--check`, `patch ORIGINAL F`)
pasan también contra `HEAD`, obviamente: `HEAD` deja pasar todo. Su valor es
hacia adelante — son los que romperían si alguien "arregla" esto agregando
`apply` a una denylist de subcomandos.

**Contra el código nuevo:**

```
212 passed in 49.57s
```

## 6. No-regresión

El encargo hablaba de "las 21 formas de escritura" y "las 8 lecturas". Los
números reales del harness, contados cargando el archivo como módulo:

```
write forms: 40
legit ops:   36
```

Las 40 formas de escritura corren en tres parametrizaciones (bloqueo sobre ruta
protegida, paso con aprobación, paso sobre ruta no protegida) = 120 casos; las 36
lecturas, 36 casos. Los 176 siguen verdes en la corrida de 212. Nada de lo que
bloqueaba dejó de bloquear y nada de lo que pasaba dejó de pasar.

Extra, fuera del archivo: `tests/red_team/portability/test_protected-config-write-guard.py`
→ `6 passed`.

## 7. Dos cosas que casi convierten esto en un verde barato

**El prefiltro.** Agregar la lectura del parche sin tocar el prefiltro habría
dado un test verde con el guard igual de ciego en producción, porque el
analizador nunca corre para un payload que no nombra ninguna ruta protegida. El
prefiltro ahora declina —y deja correr el analizador— cuando el payload contiene
`patch`, `git apply` o `git am`. Cuesta un arranque de python en payloads que
sólo mencionan la palabra (`dispatch`, `*.patch`, prosa); se paga.

**`patch -p1 < F` leía el `<` como el archivo original.** `split_words` deja `<`
como palabra, y el primer posicional decidía "el destino ya está en el comando" →
no leía el parche. Un test que sólo hubiera probado `git apply` no lo habría
visto. `positional_args` ahora descarta redirecciones y sus destinos.

## 8. Lo que rompí y cómo se ve (dato para el próximo)

Editar este hook rompió su parseo **sólo bajo `/bin/bash` 3.2**, que es el que
macOS trae y el que corre el hook. Bash 3.2 parsea el cuerpo de un heredoc
anidado en una sustitución de comando `$( … )` buscando comillas y paréntesis que
cierren. Consecuencias medidas:

1. Un apóstrofo en un comentario de Python = `syntax error: unexpected end of
   file` en la última línea del archivo.
2. Un paréntesis suelto en un comentario = lo mismo.
3. `r'…["\']…'`: dentro de comillas simples de shell el backslash **no** escapa,
   así que `\'` cierra la cadena y da vuelta el estado de comillas del heredoc
   entero. Hay que usar comilla doble afuera, como ya hacía `HEREDOC`.

Y lo peor: **`bash -n` con bash 5 daba verde en los tres casos.** El chequeo tiene
que nombrar `/bin/bash` explícitamente. Quedó pinneado como test
(`test_guard_still_parses_under_bash_3_2`) y como comentario-regla en el propio
heredoc.

Mientras estaba roto, el guard bloqueaba **todo** —incluidos parches a `docs/`—
porque el hook salía 2 por error de sintaxis. Un guard que falla en esa dirección
se nota en minutos; si hubiera fallado en la otra, no.

## 9. Me bloqueé a mí mismo (dato pedido)

Tres veces, y las tres correctamente según su propia regla:

- Editar el hook con la tool `Edit` es imposible desde adentro de la sesión: el
  hook corre en el entorno del harness. Todo el trabajo fue por `Bash` con el
  prefijo `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`, que es lo que arregló `50aa8b0c7`,
  y funciona.
- Un script de bisección **read-only** que sólo copiaba el hook al scratchpad para
  correrle `bash -n` fue bloqueado: el heredoc iba a `.venv/bin/python`, que no es
  reader, y el cuerpo tenía `write_text`. El guard no puede distinguir "escribe en
  el scratchpad" de "escribe el hook" cuando el intérprete nombra el hook y además
  puede escribir.
- **Escribir este informe** fue bloqueado en el primer intento. El comando era
  `mkdir -p docs/06-Daily/reports && cat > informe <<'MDEOF'`: como la línea de
  cabecera del heredoc empieza con `mkdir` y no con `cat`, el cuerpo se clasificó
  como programa, y el cuerpo —este texto— nombra `hooks/**` y contiene las
  palabras `mkdir`, `chmod` y `write_text`. Un informe sobre el guard dispara al
  guard. Se resolvió partiendo el comando en dos, que es exactamente lo que el
  encargo advertía.

Cada bypass quedó en `.cognitive-os/metrics/protected-config-bypass.jsonl`.

## 10. Correcciones a las premisas del encargo

1. **"las 21 formas de escritura que hoy bloquea … las 8 lecturas"** — falso. Son
   **40** formas de escritura y **36** operaciones legítimas (§6).
2. **"`apply` no está en `GIT_SAFE`, así que `git apply x.patch` debería contar
   como escritura"** — cierto pero irrelevante: el segmento se clasifica como
   escritura y aun así pasa, porque sin rutas protegidas en el texto (`hits`
   vacío) el segmento se descarta antes de que la clasificación importe. El
   agujero no estaba en la clasificación del verbo sino en el origen de las rutas.
3. **Premisa faltante: el prefiltro.** El encargo describía una sola capa. Con el
   analizador arreglado y el prefiltro intacto, el agujero seguía abierto (§7).
4. **"el cuerpo ya lo extrae `strip_heredocs`; usalo"** — a medias. Lo extraía y
   lo tiraba en una bolsa global (`programs`) sin decir de qué segmento venía, y
   ese camino además sólo escanea el cuerpo si contiene una primitiva de
   escritura: un diff puro no tiene ninguna, así que el cuerpo se descartaba.
   Hubo que devolver los pares `(cabecera, cuerpo)`.
5. **`patch` no es equivalente a `git apply`.** En `patch ORIGINAL patchfile` el
   posicional es el archivo a parchear, no el parche; leer el parche ahí sería
   leer la fuente equivocada. Se trata distinto (§2), y de paso eso evita romper
   el caso `patch` que el harness ya tenía.
6. **"`--check` … pasarlo es defendible y no trivial"** — de acuerdo con pasarlo,
   pero la parte no trivial no era `--check`: era que `-R` no necesita caso
   especial si se leen los dos lados del hunk (§4).
7. **"~50 tool calls"** — alcanzó, pero seis se fueron en el parseo de bash 3.2
   (§8), que el encargo no anticipaba, y una en descubrir que **el scratchpad de
   la sesión es compartido con los otros agentes**: otro agente pisó `probe.py` a
   mitad de trabajo. Los archivos terminaron en un subdirectorio con nombre único.

## 11. Deuda que dejo declarada

`manifests/agentic-primitive-registry.lock.yaml` guarda un `sha256` del hook
(`ed1544dd…`) que quedó viejo. Ningún test lo exige —
`tests/contracts/test_promotion_propose_only.py` pasa igual — y el encargo acotaba
a "ese hook y sus tests", así que no lo toqué. Lo consume
`scripts/cos_promotion_proposer.py`.

## 12. El diff completo

```diff
diff --git a/hooks/protected-config-write-guard.sh b/hooks/protected-config-write-guard.sh
index cb6667364..ad2bcbee2 100755
--- a/hooks/protected-config-write-guard.sh
+++ b/hooks/protected-config-write-guard.sh
@@ -76,6 +76,15 @@ prefilter_says_skip() {
   # \u escape would hide a protected path from it while jq still hands the
   # analyzer the decoded path. Any escape at all: decline and analyse.
   case "$INPUT" in *'\u'*) return 1 ;; esac
+  # A patch applier takes its destinations from the patch, not from the command,
+  # so a payload free of every protected literal can still write one. The
+  # prefilter only ever sees the payload text, so it cannot rule that out:
+  # decline and let the analyzer open the patch. This costs one python start on
+  # any payload carrying the substring (dispatch, *.patch, prose about patches);
+  # correctness over a subprocess, and the analyzer's verdict is unchanged.
+  case "$INPUT" in
+    *patch*|*"git apply"*|*"git am"*) return 1 ;;
+  esac
   while IFS= read -r line || [ -n "$line" ]; do
     case "$line" in
       protected_globs:*) in_globs=1; continue ;;
@@ -205,9 +214,9 @@ GIT_SAFE={'log','show','diff','status','blame','grep','ls-files','ls-tree','cat-
           'add','commit','push','fetch','ls-remote','check-ignore','stripspace'}
 GIT_OPT_VALUE={'-C','-c','--git-dir','--work-tree','--exec-path','--namespace'}
 
-def veto_git(ws):
+def git_subcommand(ws):
     # The first non-option word is the subcommand. Global options come before it
-    # and must not be mistaken for it.
+    # and must not be mistaken for it; a few of them take a value.
     i=0
     while i < len(ws):
         t=ws[i]
@@ -215,8 +224,12 @@ def veto_git(ws):
             i+=2; continue
         if t.startswith('-'):
             i+=1; continue
-        return t not in GIT_SAFE
-    return True
+        return t, ws[i+1:]
+    return None, []
+
+def veto_git(ws):
+    sub, _ = git_subcommand(ws)
+    return sub is None or sub not in GIT_SAFE
 
 VETOED={'sed':veto_sed,'awk':veto_awk,'gawk':veto_awk,'mawk':veto_awk,
         'find':veto_find,'sort':veto_sort,'yq':veto_yq,'git':veto_git,
@@ -240,7 +253,10 @@ def strip_heredocs(cmd):
     # it IS the program, so it is returned separately and scanned for paths.
     # Either way the header line stays, so a heredoc aimed at a protected path
     # is still caught by redirection.
-    lines=cmd.split('\n'); out=[]; programs=[]; i=0
+    # The (header, body) pairs are returned as well: a heredoc fed to a patch
+    # applier is neither data nor program, it is the patch, and the segment that
+    # consumes it has to be able to find its own body.
+    lines=cmd.split('\n'); out=[]; programs=[]; docs=[]; i=0
     while i < len(lines):
         line=lines[i]; out.append(line)
         terms=[m.group(2) for m in HEREDOC.finditer(line)]
@@ -255,9 +271,11 @@ def strip_heredocs(cmd):
                 body.append(lines[i]); i+=1
             if i < len(lines):
                 i+=1
+            body='\n'.join(body)
+            docs.append((line, body))
             if body_is_program:
-                programs.append('\n'.join(body))
-    return '\n'.join(out), '\n'.join(programs)
+                programs.append(body)
+    return '\n'.join(out), '\n'.join(programs), docs
 
 SEPS=set(';\n&|')
 
@@ -359,6 +377,181 @@ def body_can_write(body):
     return any(tok in body for tok in WRITE_PRIMITIVES)
 
 
+# --- Patch appliers: the destinations are inside the patch -------------------
+# `git apply x.patch` names exactly one path in its text -- the patch -- while
+# the paths it WRITES are two lines per hunk inside that file. Judging the
+# command text alone meant any protected path could be written by a command
+# whose text mentioned none; measured 2026-08-18, that was the path four
+# authorised writes to hooks/** actually took, each disclosed only by choice.
+#
+# Deliberately not a diff parser. Three line shapes carry destinations:
+#   `+++ b/PATH`   where the patch writes
+#   `--- a/PATH`   where a deletion names its victim (and where -R writes)
+#   `diff --git a/OLD b/NEW`  where a pure rename names both and no hunk exists
+# Anything that does not carry at least one of them is not a patch we can read,
+# and an unreadable patch is a block, not a guess.
+
+# One house rule for everything below: every line inside this heredoc must
+# carry an EVEN number of single and of double quotes. /bin/bash 3.2, which is
+# what macOS ships and what this hook runs under, parses the body of a heredoc
+# nested in a command substitution while looking for matching quotes, so an
+# apostrophe in a comment is a syntax error at the END of the file -- and
+# `bash -n` under a modern bash reports the file as clean. Hence QUOTE_CHARS
+# below instead of the obvious literal.
+QUOTE_CHARS=chr(34)+chr(39)
+
+PATCH_APPLIERS={'patch','gpatch'}
+PATCH_OPT_VALUE={'-i','--input','-o','--output','-d','--directory','-D','--ifdef',
+                 '-r','--reject-file','-B','--prefix','-Y','--basename-prefix',
+                 '-z','--suffix','-p','--strip','-F','--fuzz','-g','--get'}
+PATCH_STDIN_ARGS={'-','/dev/stdin'}
+# Double-quoted outer, escaped double quotes inside, exactly like HEREDOC
+# above: a backslash does not escape anything inside single quotes, so a
+# single-quoted pattern carrying \' flips the quote state of the whole heredoc
+# for bash 3.2 and the command substitution never closes.
+DIFF_HEADER=re.compile(r"^diff --git ['\"]?a/(.+?)['\"]? ['\"]?b/(.+?)['\"]?$")
+# Plain stdin redirection only. A doubled marker is a heredoc, handled above,
+# and a marker followed by an open paren is a process substitution, whose
+# content is not on disk to be opened; the character class rejects both instead
+# of matching them and discarding the result afterwards. It also carries an open
+# AND a close paren, because of the same house rule as the quotes: parentheses
+# inside this heredoc must balance or bash 3.2 loses the command substitution.
+STDIN_REDIRECT=re.compile(r"(?<![<>])<(?!<)\s*(['\"]?)([^\s'\"<>&;|()]+)\1")
+
+# Fail-closed findings that no glob can express: a patch we could not read, or
+# text that is not a diff. They block on their own, with the reason attached.
+FORCED_BLOCKS=[]
+
+def patch_paths(text):
+    """(paths, looks_like_a_unified_diff). Both sides, because -R writes the other."""
+    paths=[]; seen=False
+    for line in text.split('\n'):
+        m=DIFF_HEADER.match(line.strip())
+        if m:
+            seen=True
+            paths.extend([m.group(1), m.group(2)])
+            continue
+        if line.startswith('+++ ') or line.startswith('--- '):
+            seen=True
+            raw=line[4:].split('\t')[0].strip().strip(QUOTE_CHARS)
+            if not raw or raw=='/dev/null':
+                continue
+            paths.append(raw)
+            # -p1 is the default, so a/ and b/ are strip prefixes; -p0 keeps
+            # them. Both readings are kept: an extra candidate can only add a
+            # block, never remove one, and guessing the -p level would.
+            if raw[:2] in ('a/','b/'):
+                paths.append(raw[2:])
+    return paths, seen
+
+REDIR_OPS={'<','>','>>','>|','&>','&>>','2>','2>>','1>','1>>','<>'}
+
+def positional_args(ws, opt_value=frozenset()):
+    out=[]; i=0
+    while i < len(ws):
+        t=ws[i]
+        if t in opt_value:
+            i+=2; continue
+        # A redirection is not an argument. Counting it as one is how
+        # `patch -p1 < evil.patch` read the bare < as the file being patched and
+        # concluded the destination was already named in the command.
+        if t in REDIR_OPS:
+            i+=2; continue
+        if t and t[0] in '<>':
+            i+=1; continue
+        if t.startswith('-') and t != '-':
+            i+=1; continue
+        out.append(t); i+=1
+    return out
+
+def opt_value_of(ws, names):
+    for i, t in enumerate(ws):
+        for n in names:
+            if t == n and i+1 < len(ws):
+                return ws[i+1]
+            if t.startswith(n+'='):
+                return t[len(n)+1:]
+    return None
+
+def heredoc_body_for(seg, heredocs):
+    for hline, body in heredocs:
+        h=hline.strip()
+        if h and h in seg:
+            return body
+    return None
+
+def read_patch(label):
+    p=Path(label) if os.path.isabs(label) else project/label
+    try:
+        return p.read_text(errors='replace')
+    except Exception:
+        FORCED_BLOCKS.append('unreadable patch source: %s' % label)
+        return None
+
+def patch_segment_targets(exe, rest, seg, heredocs):
+    """Paths a patch-applying segment writes, read out of the patch itself."""
+    if exe == 'git':
+        sub, args = git_subcommand(rest)
+        if sub not in ('apply','am'):
+            return []
+        if '--check' in args:
+            # The documented dry run: it parses the patch and reports whether it
+            # would apply, touching neither the working tree, the index, nor the
+            # targets of the patch. It is allowed because it is the question an
+            # operator asks BEFORE requesting approval, and a guard that blocks
+            # the rehearsal is a guard people route around. -R/--reverse gets no
+            # such pass -- reverting writes -- and needs no special case, because
+            # both sides of every hunk are read anyway.
+            return []
+        sources=[a for a in positional_args(args) if a not in PATCH_STDIN_ARGS]
+    elif exe in PATCH_APPLIERS:
+        pos=positional_args(rest, PATCH_OPT_VALUE)
+        if pos:
+            # `patch ORIGINAL [patchfile]` writes ORIGINAL and nothing else, and
+            # ORIGINAL is a word in the command, already judged by the ordinary
+            # path. Only the form that takes its destinations from the patch
+            # needs the patch opened.
+            return []
+        explicit=opt_value_of(rest, ('-i','--input'))
+        sources=[explicit] if explicit else []
+    else:
+        return []
+
+    texts=[]
+    if sources:
+        for f in sources:
+            text=read_patch(f)
+            if text is not None:
+                texts.append((f, text))
+    else:
+        body=heredoc_body_for(seg, heredocs)
+        if body is not None:
+            texts.append(('<<heredoc', body))
+        else:
+            redir=stdin_redirect_target(seg)
+            if redir:
+                text=read_patch(redir)
+                if text is not None:
+                    texts.append((redir, text))
+            else:
+                # A pipe, a process substitution, or nothing: the content is not
+                # on disk, so the destinations cannot be known and the command
+                # is not allowed to proceed on the strength of that ignorance.
+                FORCED_BLOCKS.append(
+                    'patch source not inspectable: %s' % ' '.join([exe]+rest)[:80])
+    out=[]
+    for label, text in texts:
+        paths, looks_like_patch = patch_paths(text)
+        if not looks_like_patch:
+            FORCED_BLOCKS.append('not a unified diff: %s' % label)
+            continue
+        out.extend(paths)
+    return out
+
+def stdin_redirect_target(seg):
+    m=STDIN_REDIRECT.search(seg)
+    return m.group(2) if m else None
+
 def resolve_exe(ws):
     i=0
     while i < len(ws):
@@ -374,7 +567,7 @@ def resolve_exe(ws):
 def bash_write_targets(command):
     if not isinstance(command, str) or not command.strip():
         return []
-    cmd, program_body = strip_heredocs(command)
+    cmd, program_body, heredocs = strip_heredocs(command)
     cmd, substituted = lift_substitutions(cmd)
     targets=[]
     for match in REDIRECT.finditer(cmd):
@@ -391,6 +584,10 @@ def bash_write_targets(command):
         exe, rest = resolve_exe(ws)
         if exe is None:
             continue
+        # Out-of-band destinations first: a patch applier writes targets that
+        # are not among the words of this segment at all, so `hits` stays empty
+        # and the segment gets waved through on the strength of naming nothing.
+        targets.extend(patch_segment_targets(exe, rest, seg, heredocs))
         hits=[]
         for tok in rest:
             for cand in TOKEN_PATHS.findall(tok):
@@ -428,6 +625,7 @@ for raw in paths:
             continue
     if is_protected(rel, raw):
         blocked.append(rel)
+blocked.extend(FORCED_BLOCKS)
 seen=[]
 for b in blocked:
     if b not in seen: seen.append(b)
```
