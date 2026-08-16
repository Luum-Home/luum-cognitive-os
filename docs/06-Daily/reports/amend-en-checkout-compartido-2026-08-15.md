# `--amend` en checkout compartido — la premisa era falsa y el guard ya bloqueaba

**Fecha:** 2026-08-15
**Cambio:** commit `3045f71f8` — `hooks/git-commit-scope-guard.sh` + `tests/unit/test_git_commit_scope_guard_amend.py`
**Nota de procedencia:** el agente que hizo este trabajo **no podía escribir archivos `.md` de informe** por sus propias reglas de operación, así que entregó el contenido en su resultado. Este archivo lo persiste al repo, que es donde tiene que vivir. La medición y el razonamiento son suyos; la transcripción, del orquestador.

## El encargo estaba mal, y la corrección importa

Se lanzó a bloquear `git commit --amend` con esta premisa:

> `--amend` ignora el pathspec y commitea el índice entero.

**Es falsa.** Verificado en un repo descartable, no deducido:

```
[3] git commit --amend -m 'fixed' -- mine.txt
    -> commit: mine.txt
    -> índice después: theirs.txt   <-- SOBREVIVIÓ, no entró al commit

[4] git commit --amend --no-edit          (sin pathspec)
    -> commit: mine.txt + theirs.txt      <-- SE LO COMIÓ
    -> índice después: vacío
```

**No es el flag el peligroso: es la ausencia de pathspec.** `git commit --amend -- <paths>` acota exactamente igual que `--only`. Prohibir `--amend` habría sido el verde barato: elimina el síntoma y también el uso legítimo.

## El guard ya bloqueaba. Se escapó por otro lado

Matriz corrida contra el hook **original** (exit 2 = bloquea):

```
BLOCK (2)  git commit --amend --no-edit
BLOCK (2)  git commit --amend -m "fixed msg"
BLOCK (2)  git commit --amend -F /tmp/msg.txt
ALLOW (0)  git commit --amend -m "fixed" -- docs/report.md          <- correcto, es seguro
ALLOW (0)  git commit --only -m "x" -- a.md && git commit --amend --no-edit   <- ESCAPE 1
ALLOW (0)  git -C /some/repo commit --amend --no-edit                          <- ESCAPE 2
```

La regla existía y disparaba. El agente que produjo `3506e1481` **no chocó contra ella**. Tres puertas, todas de la misma familia — **el hook lee mal el string**:

1. **Lavado por composición.** `grep -oE 'git[[:space:]]+commit.*'` tomaba la **primera** ocurrencia y todo lo que seguía. El `--only` del primer comando le declaraba scope al amend pelado escrito después del `&&`. Es la ruta más plausible de lo que pasó.
2. **`git -C`.** El disparador exigía adyacencia literal entre `git` y `commit`, así que salía antes de analizar.
3. **Indirección por archivo.** Descubierto sin querer: el laboratorio quedó bloqueado con el `git commit` en un heredoc, y pasó apenas se escribió en un `.sh`. **Contra esto no hay regex** — es el límite de todo gate que mira el texto del comando.

Cerrados 1 y 2 dentro del archivo autorizado. El 3 no tiene arreglo en este hook y queda declarado.

## El escape es mecánico, no una variable

El discriminante es **el estado del índice**:

| Índice | Conducta | Motivo |
|---|---|---|
| Limpio | **Pasa solo** | Un amend pelado sólo puede reescribir su propio mensaje. No hay nada de nadie que absorber. |
| Sucio | **Bloquea**, listando por nombre lo que iba a tragarse | Es el caso que produjo `3506e1481`. |
| Incertidumbre (git falla, no hay repo) | Bloquea | Conducta previa; no relaja nada. |

Mejor que una variable de entorno porque **el caso legítimo no pide permiso**: "me equivoqué en mi mensaje y no pusheé" simplemente funciona. `COS_BYPASS_COMMIT_GUARD=1` queda para el residuo, auditado.

### Qué hacer, por situación

| Situación | Comando |
|---|---|
| Mensaje mal, **ya pusheado** | Commit nuevo que corrija (ver `merge-sobre-rebase`) |
| Mensaje mal, sin pushear, índice limpio | `git commit --amend` — pasa solo |
| Mensaje mal, con algo ajeno staged | `git restore --staged <lo ajeno>`, después el amend |
| Sumar un archivo propio al commit anterior | `git commit --amend -- <mi path>` |
| Hace falta igual sobre índice ajeno | `COS_BYPASS_COMMIT_GUARD=1`, auditado |

**No verifica si el commit ya está pusheado** — requiere `@{u}` y no toda rama lo tiene. Va como texto en el mensaje del bloqueo. Limitación conocida, no olvido.

## La salida real del guard rechazando un amend

Corrido contra el hook instalado, reproduciendo el escenario del día:

```
[git-commit-scope-guard] BLOCKED: `git commit --amend` without a pathspec, with a non-empty index.

--amend rewrites the tip commit using the ENTIRE index, so it will
absorb every file staged right now — including files staged by the
other sessions sharing this checkout. That is exactly how commit
3506e1481 ended up with five files belonging to three other agents
under a message that describes none of them.

Currently staged (would be swallowed):
  theirs.md

INSTEAD — do not rewrite shared history (see rules/merge-sobre-rebase):
  git commit --only -m "..." -- path/to/file    (new corrective commit)
  git commit --amend -m "..." -- path/to/file   (amend, pathspec IS honoured)

A bare --amend is allowed automatically once the index is clean:
  git restore --staged <other-agents-paths>   then retry
--> exit code: 2
```

`tests/unit/test_git_commit_scope_guard_amend.py`: **13 casos que ejecutan el hook contra repos git reales** y verifican exit codes. Ninguno busca el string `--amend` en el fuente. `13 passed in 14.60s`.

## El cambio en el hook

- **Cabecera:** documenta que `--amend -- <path>` es seguro (medido) y que el discriminante es el índice.
- **Disparador:** acepta opciones globales entre `git` y `commit` (`-C`, `-c`, `--no-pager`, `--git-dir`, …).
- **Analizador:** tokeniza el comando entero con `shlex` (respeta comillas), lo parte en segmentos de shell y juzga **cada `git commit` por separado**. Devuelve `OK | BLOCK_UNSCOPED | BLOCK_AMEND` más el directorio de `-C`.

Efecto lateral necesario y cubierto por test: un mensaje de commit que *hable* de `git commit --amend` ya no genera un segmento fantasma ni un bloqueo falso.

## Hallazgos colaterales, más graves que lo arreglado

**1. `hooks/bash-hot-path-dispatcher.sh:78` — `git -C` esquiva 16 hooks.**
`_is_git_commit()` tiene el mismo patrón de adyacencia literal que se acaba de arreglar en el guard, así que `git -C <dir> commit` saltea **toda la batería de commit**, no sólo este guard. El arreglo es el mismo patrón que ya quedó escrito. No estaba autorizado.

**2. `hooks/provenance-scan.sh` corre con `--staged`: escanea el índice entero.**
Bloqueó todas las escrituras de este agente por una ruta host-local en un archivo staged por **otro** agente. Un escritor le corta la mano a los demás por contenido que no controla, y el arreglo natural —destagear lo ajeno— es justo lo que la norma prohíbe. **Es la misma familia que este encargo**: un control que decide sobre el índice compartido en vez de sobre lo que uno escribe.

**3. `grep -c` sobre `settings.json` no dice si un hook está registrado.**
`git-commit-scope-guard` da 0 y **sí está registrado**, vía `bash-hot-path-dispatcher.sh:135`. Conviene revisar con esa lente lo que `rules/rate-limiting.md` declara sobre el rate-limiter.

**4. La cabecera del hook promete `< 50 ms` y la realidad son ~180-208 ms** (mediana, A/B interleaved de 15 muestras; lo paga el arranque de `python3`). Documentación falsa preexistente, no regresión del cambio. Entra en documentation-truth.

## Lo que no se sabe

- **Con qué comando exacto se produjo `3506e1481`.** Se reprodujeron tres rutas que lo explican; cuál fue es inferencia. La telemetría del harness lo diría.
- **El escape por indirección sigue abierto.** Un agente que escriba sus comandos en un `.sh` no ve ningún guard, y eso no se arregla dentro de este hook.
- La latencia se midió con cinco agentes activos en la máquina: p90 entre 430 y 476 ms. La conclusión "sin regresión" se sostiene por la mediana y el mínimo, no por el p90.

## Pendiente de decisión del operador

El diff de la norma **no va a `rules/`**: la sección de escritores concurrentes vive en el skill `ruteo-de-agentes`, canónico en `g2k-infra` y sincronizado al perfil. Escribirlo es un cruce de repo y pide checkpoint explícito. El texto propuesto quedó en el resultado del agente.

Y una decisión de política: **permitir el amend pelado con índice limpio relaja el estado anterior**, que bloqueaba siempre. Es lo correcto —el caso legítimo no debería pedir permiso— pero es un cambio de postura, no sólo un arreglo.
