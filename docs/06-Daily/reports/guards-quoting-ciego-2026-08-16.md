# Guards ciegos al quoting — qué era y qué no

Fecha: 2026-08-16
Alcance autorizado: `hooks/destructive-git-blocker.sh`, `hooks/research-compliance-guard.sh`

## Las cuatro filas, recontadas

El encargo traía cuatro filas medidas. Las recontré ejecutando el hook con el
payload real del harness (`{"tool_name":"Bash","tool_input":{"command":…}}`),
no buscando strings en el fuente:

| # | comando | rc medido | coincide con el encargo |
|---|---------|-----------|--------------------------|
| 1 | `cd /tmp && <op destructiva>` | 2 | sí |
| 2 | `<op destructiva>` | 2 | sí |
| 3 | `echo "texto con && <op destructiva>"` | 2 | sí |
| 4 | `git status` | 0 | sí |

**Las cuatro se confirman.** El encargo también decía que un informe del día
anterior afirmaba lo contrario —que `cd x && git …` se escapa por el anclaje—
y que eso es falso. Confirmado: el `^` de `DESTRUCTIVE_PATTERN`
(`hooks/destructive-git-blocker.sh:109`) es real, pero el comando se parte
ANTES con `tr '|&;' '\n'` (línea 347 del original), así que cualquier `git`
después de un separador queda al principio de un segmento y el ancla no
protege nada.

Una fila del encargo estaba **contaminada y hubo que aislarla**: el checkout
está en `main`, y el hook bloquea `git commit`/`git push` en rama protegida
por una vía distinta (`protected_branch_write`). Cualquier caso con
`git commit` daba rc=2 por la rama, no por el quoting. Todas las mediciones de
abajo corren contra un repo descartable en rama `work`.

## Reproducción

```bash
python3 <scratchpad>/run.py hooks/destructive-git-blocker.sh
```

Equivalente versionado y ejecutable:

```bash
.venv/bin/python3 -m pytest tests/behavior/test_destructive_git_blocker_quoting.py -q
```

## Censo de la familia — por la forma, no por el nombre

Buscando la forma (partir `$COMMAND` en separadores de shell sin tokenizar):

```bash
git grep -nE "tr[[:space:]]+'[^']*[&|;][^']*'" -- hooks/ scripts/
```

| hook | forma | severidad | autorizado |
|------|-------|-----------|------------|
| `hooks/destructive-git-blocker.sh` | `tr '|&;' '\n'` + regex `^git…`, y un parser semántico que buscaba `git` en CUALQUIER posición de la lista de tokens | bloquea (exit 2) | **sí — arreglado** |
| `hooks/destructive-rm-blocker.sh` | `tr '|&;' '\n'` idéntico, línea 257 | bloquea | no |
| `hooks/post-git-orphan-notifier.sh` | `tr '|&;' '\n'` idéntico, línea 79 | solo notifica (PostToolUse) | no |

Sobre el `git grep`: el encargo decía que acá **sí** soporta `\b` y **no**
`\s`. **La mitad es falsa.** Medido con un control contra un positivo conocido:

```
plain 'DESTRUCTIVE_PATTERN'   -> 1 archivo
'\bDESTRUCTIVE_PATTERN\b'     -> 0     <- \b NO funciona
'\<DESTRUCTIVE_PATTERN\>'     -> 0     <- tampoco
-w 'DESTRUCTIVE_PATTERN'      -> 1     <- la forma que sí anda
"tr\s'"                       -> 0     <- \s NO funciona (esto sí lo decía bien)
"tr[[:space:]]'"              -> 33
```

O sea: ni `\b` ni `\s` ni `\<`. Solo clases POSIX y `-w`. Un censo escrito con
`\b` habría devuelto cero y parecido "no hay más miembros".

## `research-compliance-guard.sh` no es de esta familia

El encargo lo daba por miembro: *"`_strip_commit_message_args` es por líneas y
no puede recortar un `-m` multilínea, así que el cuerpo del mensaje se escanea
como comandos"*. **Falso, y en dos puntos:**

1. Ese hook **no tiene** `_strip_commit_message_args`
   (`grep -c` devuelve `0`). La función vive en
   `hooks/destructive-git-blocker.sh:161`.
2. Ese hook **no juzga el texto del comando en absoluto**. Su única referencia
   a `$CMD` es el disparador de la línea 49 (`[[ "$CMD" != *"git commit"* ]]`).
   Todos sus veredictos salen del **contenido de los archivos staged**, no del
   comando. No puede tener este defecto.

No lo toqué. Escribir un cambio ahí habría sido inventar un problema para
llenar una autorización.

Lo que **sí** es cierto de la descripción, en el archivo correcto: el
`_strip_commit_message_args` de `destructive-git-blocker.sh` usa `echo | sed`,
que es por líneas, y por eso no recorta un `-m` multilínea. Medido:

```
entrada:  git commit -m 'a\n\n<op> b'
salida:   git commit -m 'a\n\n<op> b'      (sin recortar)
```

## Qué porté, y de dónde

De `hooks/git-commit-scope-guard.sh` (commit `3045f71f8`): tokenizar el
comando entero con `shlex` —que respeta comillas—, partirlo en segmentos de
shell y juzgar cada uno por separado. No escribí un tercer parser de la
gramática; porté ese.

Además del port, el arreglo agrega cuatro cosas que el original de
`git-commit-scope-guard.sh` no necesitaba:

- **Newline como separador.** `shlex.split` se come el `\n` como espacio, y
  entonces `echo hi\n<op>` deja de bloquear. Se usa
  `shlex.shlex(..., punctuation_chars="();<>|&\n")` para que el `\n` sea un
  token separador, mientras un `\n` **dentro** de un `-m` entrecomillado sigue
  siendo texto. Esa distinción es justo la que un split por caracteres no
  puede hacer.
- **Cuerpos de heredoc descartados.** Un heredoc es data en stdin, nunca
  comandos — salvo que quien lo lee sea un intérprete (`bash <<EOF`), en cuyo
  caso se conserva.
- **Comentarios recortados a mano** (`_strip_comments`), preservando el `\n`.
  El comentador propio de `shlex` llama a `readline()` y se lleva el newline
  junto con el comentario; con el newline perdido, `ls # <op>\n<op>` colapsaba
  en un solo segmento cuyo comando era `ls` y **el op real de la línea
  siguiente dejaba de verse**. Eso lo encontró mi propio test de conducta, y
  es pérdida de detección, no falso positivo — por eso los comentarios se
  recortan antes de lexear y no después.
- **Recursión en `bash -c` / `sh -c` / `eval`**, y salteo de prefijos
  `VAR=VAL` y wrappers (`sudo`, `env`, …), para poder anclar el veredicto en la
  palabra de comando sin perder detección.

El parser semántico también se ancló: antes hacía
`next(i for i, token in enumerate(parts) if token == "git")`, o sea encontraba
`git` en cualquier posición. Por eso `ls -la  # never run <op>` bloqueaba **sin
que hubiera ningún separador involucrado**. Ahora exige que `git` sea la
palabra de comando del segmento.

**Ante la duda, bloquear**: si `shlex` falla por comillas desbalanceadas, el
analizador sale con 3 y el hook cae al split viejo por caracteres, que
sobre-bloquea. `echo "oops && <op>` (comilla sin cerrar) sigue dando rc=2.

## Mutation test — desglose

37 casos, ejecutando el hook de verdad con payload del harness. Ninguno busca
un string en el fuente.

**Contra el código ARREGLADO: 37/37.**

**Contra el código ORIGINAL: 31/37 — 6 divergentes, las 6 por conducta, 0 por
símbolo ausente.** Es decir: no hay ningún test que falle por "todavía no
existe la función"; los seis describen comportamiento observable.

Los seis se parten en dos grupos que valen distinto:

*Cuatro son el bug del encargo (falsos positivos, el guard bloquea texto que
no se ejecuta):*

| caso | original | arreglado |
|------|----------|-----------|
| `echo "texto con && <op>"` | 2 | 0 |
| `ls -la  # never run <op>` | 2 | 0 |
| `cat <<'EOF'\n<op> && true\nEOF` | 2 | 0 |
| `git commit -m 'title\n\nbody: <op> && ok'` | 2 | 0 |

*Dos son agujeros de DETECCIÓN preexistentes que el arreglo cerró de paso —
valen más, porque acá el guard dejaba pasar una ejecución real:*

| caso | original | arreglado |
|------|----------|-----------|
| `sh -c '<op>'` | **0** | 2 |
| `eval "<op>"` | **0** | 2 |

Los otros 31 dan igual en ambos: 22 siguen bloqueando lo que se ejecuta
(incluidos `sudo <op>`, `VAR=1 <op>`, subshell, `git -C`, heredoc leído por
`bash`, comilla desbalanceada) y 9 siguen permitiendo lo que no.

Suites existentes: `tests/behavior/test_destructive_git_blocker.py`,
`tests/unit/test_destructive_git_block.py`,
`tests/red_team/portability/test_destructive-git-blocker.py` → **118 passed**,
sin regresiones.

## Medición de latencia

Es hot path de PreToolUse. **El wall de esta máquina no es portable** —incluye
lo que el resto del equipo esté haciendo—; el número que viaja es el CPU
(user+sys del árbol de hijos, `resource.RUSAGE_CHILDREN`), así que van
separados.

| caso | CPU antes | CPU después | wall p50 antes | wall p50 después |
|------|-----------|-------------|----------------|------------------|
| `ls -la` (comando sin git) | 49,2 ms | 47,0 ms | 55,5 ms | 56,6 ms |
| `git status` | 49,0 ms | 87,6 ms | 55,7 ms | 101,0 ms |

n=20 por celda. El costo es **un `python3` extra (~38 ms CPU) y solo en
comandos que contienen `git`**. El tráfico que no menciona git —la mayoría del
PreToolUse— sale por un prefiltro `grep -q 'git'` que no gasta ningún proceso,
y quedó igual o apenas mejor que antes.

**Deuda anotada, no escondida:** los 38 ms son el arranque de un intérprete
que ya se paga otra vez más adelante (`_semantic_git_match` es un segundo
spawn). Fusionar segmentador y analizador semántico en un solo proceso
python borra ese costo. No lo hice acá para no mezclar un refactor de
rendimiento con un arreglo de seguridad.

## Extraer el parser a `hooks/_lib/`: viable, no autorizado

Es el mejor entregable posible del lote y **sigue pendiente**. `hooks/_lib/`
es config protegida y quedó fuera de la autorización (solo
`destructive-git-blocker.sh` y `research-compliance-guard.sh`), así que **no
lo escribí**.

Estado real: ahora hay **dos** copias de la misma gramática
(`git-commit-scope-guard.sh` y `destructive-git-blocker.sh`), más los dos
miembros del censo que todavía usan el split por caracteres. La cabecera de
`hooks/provenance-scan.sh` (commit `f2d339a5b`) ya dejó escrito que van a
divergir.

Diff propuesto, para cuando se autorice:

1. **Crear `hooks/_lib/shell_segments.py`** con el contenido íntegro del
   bloque `SEGPY` que hoy vive embebido en
   `hooks/destructive-git-blocker.sh` (`_segment_command`): `_strip_comments`,
   `_lex`, `_command_word`, `_drop_heredocs`, `segments`, `normalized`, y el
   `__main__` que imprime un segmento por línea y sale con 3 si las comillas
   no cierran.
2. **En `hooks/destructive-git-blocker.sh`**, reemplazar el heredoc `SEGPY`
   por:
   ```bash
   _segment_command() {
     command -v python3 >/dev/null || return 3
     python3 "$(dirname "${BASH_SOURCE[0]}")/_lib/shell_segments.py" "$1"
   }
   ```
3. **En `hooks/git-commit-scope-guard.sh`**, reemplazar sus `SEPARATORS` y
   `segments()` locales por `from shell_segments import segments` (con
   `sys.path.insert` al `_lib`), conservando su `find_commit`/`scope_of`.
4. **En `hooks/destructive-rm-blocker.sh:257` y
   `hooks/post-git-orphan-notifier.sh:79`**, cambiar
   `done <<< "$(echo "$CMD" | tr '|&;' '\n')"` por
   `done <<< "$(_segment_command "$CMD" || echo "$CMD" | tr '|&;' '\n')"`.
   Estos dos tienen el mismo defecto y no fueron medidos acá.

Antes de mover el parser hay que portar los tests de conducta de los tres
hooks, porque el `\n`-como-separador y el descarte de heredocs son decisiones
que `git-commit-scope-guard.sh` hoy **no** toma y podrían cambiarle el
veredicto.

## Qué del encargo era falso

1. **`research-compliance-guard.sh` no es miembro de la familia.** No tiene
   `_strip_commit_message_args` y no juzga texto de comando. La función
   descrita existe, pero en `destructive-git-blocker.sh:161`.
2. **`git grep` acá no soporta `\b`.** El encargo decía que sí. Devuelve 0
   contra un positivo conocido, igual que `\s`. La forma que anda es `-w` o
   `[[:space:]]`.
3. **El `echo` no es el único falso positivo, y "agregar una excepción para
   echo" no era ni siquiera el verde barato correcto**: `printf`,
   `echo '…'` con comillas simples y `git grep '…'` **ya pasaban** antes del
   arreglo. El discriminante real no era el comando ni el tipo de comilla,
   sino **si el texto del op caía justo al principio de un segmento después
   del split**. Una excepción para `echo` no habría tocado ni el comentario ni
   el heredoc, que son la mitad de los falsos positivos medidos.
4. **El guard tenía además dos agujeros de detección** que el encargo no
   mencionaba: `sh -c '<op>'` y `eval "<op>"` pasaban con rc=0.
5. Confirmado del encargo, sin corrección: las cuatro filas, el `^` real de
   `DESTRUCTIVE_PATTERN`, que el split lo neutraliza, que `\s` no anda, que
   `timeout` no existe en este macOS, y que escribir el nombre de una
   operación destructiva en un comando bastaba para que el guard bloqueara —
   **me pasó en mi primera llamada a Bash**, con el nombre del op dentro de un
   heredoc de un script de prueba.
