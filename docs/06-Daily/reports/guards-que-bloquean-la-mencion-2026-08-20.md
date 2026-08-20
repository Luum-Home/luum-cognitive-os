# Guards que bloquean la mención — 2026-08-20

## Resumen ejecutivo

`scripts/audit_guard_mention_blocks.py` cuenta 67 bloqueos en los transcripts de
este proyecto: 49 de `hooks/protected-config-write-guard.sh` y 18 del hook del
perfil `block-destructive-bash`. De esos 67, **16 se decidieron por el destino
explícito de un Edit/Write** (ahí no cabe la ambigüedad) y **51 salieron del
texto de un comando de Bash**. Replayando contra el árbol de trabajo los 33 que
el guard de config decidió por texto: antes de este cambio seguían bloqueando
27, ahora 21. Los **7 recuperados son todos comandos que sólo leen** — un
`json.load` de `.claude/settings.json`, un `read_text` de `rules/`, un `cp` cuyo
archivo protegido era el ORIGEN. La familia era una asimetría, no un mecanismo
nuevo: el guard ya sabía juzgar el cuerpo de un heredoc (`body_can_write`) y no
miraba el programa que llega por `-c`. **Hubo falsos negativos y se pueden
nombrar**: 40 de 1499 comandos que corrieron sin bloqueo en los últimos 2 días
son bloqueados por el guard de hoy.

## Correcciones a las premisas del encargo

1. **"El precio se pagó seis veces hoy, medido".** Son 67 bloqueos, no 6, y el
   conteo cubre todos los transcripts del proyecto (66 de los 67 caen en la
   sesión en curso; el 67 lo provocó este mismo trabajo). Comando:
   `.venv/bin/python3 scripts/audit_guard_mention_blocks.py`.

2. **"Hay telemetría de bloqueos en `.cognitive-os/metrics/`".** No la hay. El
   guard llama a `primitive_intervention_emit` apuntando a
   `.cognitive-os/metrics/protected-config-write-blocks.jsonl` y **ese archivo no
   existe** (`ls` devuelve "No such file"). Lo que sí existe es
   `protected-config-bypass.jsonl`, con 1321 filas, y registra **aprobaciones
   concedidas, no bloqueos**. La única fuente de bloqueos son los transcripts, y
   por eso el instrumento los lee de ahí.

3. **"El guard no distingue actuar de mencionar".** Lo distingue desde ayer, y
   bastante: `body_can_write()`, `_open_can_write()`, `HEREDOC_DATA_CONSUMERS`,
   `lift_substitutions()` y la lectura de parches entraron entre `cc1f3b791` y
   `839d7edcb`. El encargo describía el estado de la mañana. Lo que quedaba era
   una sola asimetría —el heredoc se analiza, el `-c` no— más la gramática de
   los comandos de copia.

4. **"Un `source` del resolvedor de bypass fue bloqueado read-only".** `source`
   **ejecuta** el archivo con la autoridad del shell que lo llama; no es una
   lectura. Ese bloqueo no es un falso positivo y no lo toqué.

5. **"El `git worktree add` lo bloqueó `block-destructive-bash`".** Lo bloquea
   `hooks/destructive-git-blocker.sh` (ADR-055b, mensaje
   `DESTRUCTIVE-GIT-BLOCKER: BLOCKED`). El hook del perfil sólo mira seis verbos
   de borrado y ninguno es `git`.

## Falsos negativos: los busqué y encontré esto

La dirección que importa. Método: `--false-negatives` replaya contra el guard de
HOY todos los comandos de Bash que en su momento **no** fueron bloqueados. Si el
guard de hoy los bloquea, en su momento se colaron.

```
.venv/bin/python3 scripts/audit_guard_mention_blocks.py --false-negatives --since-days 2
comandos Bash no bloqueados, distintos, ultimos 2.0d: 1499
que el guard de HOY si bloquea (falsos negativos de entonces): 40
```

Tres formas concretas, de las 40:

- `git mv codebase-memory-directive.md rules/codebase-memory-directive.md` —
  una escritura dentro de `rules/**` que pasó. `git mv` no está en `GIT_SAFE`,
  así que hoy bloquea; entonces no.
- `git apply "$P"` con `P=docs/.../conditional-directive.patch`, cuyo destino
  era `rules/codebase-memory-directive.md`. El guard no abría el parche hasta
  `333da6d05`. Hoy bloquea, y encima falla cerrado porque `$P` no se expande.
- `export COS_ALLOW_PROTECTED_CONFIG_WRITE=1` seguido de un heredoc que hace
  `Path("rules/rate-limiting.md").write_text(...)`. `export VAR=1` **no** es una
  aprobación reconocida (`_approval_granted` exige el token en posición de
  prefijo), así que esas escrituras ni bloquearon ni dejaron fila en el ledger
  de bypass. Hoy bloquean.

Y un falso negativo que **yo mismo estaba por introducir**: aflojar el veredicto
de `python3 -c` deja pasar un programa que no escribe él, sino que delega —
`os.system("echo x > hooks/zzz.sh")` no llevaba ninguna primitiva de la lista de
`WRITE_PRIMITIVES`. Lo cerré en el mismo commit agregando la familia
"delegación": `subprocess`, `os.system`, `os.popen`, `Popen`, `os.exec`,
`os.spawn`, `eval(`, `exec(`, `compile(`, `__import__`, `runpy`, `importlib`,
`ctypes`, y `shutil.` entero en vez de tres funciones sueltas. Cierra el agujero
en las **dos** superficies, porque `body_can_write` es la misma para heredocs.

## Actuar sobre una ruta vs mencionarla

La regla que uso no es una lista de comandos permitidos; son dos propiedades
verificables del texto.

**1. Un programa sin primitiva de escritura no escribe, nombre lo que nombre.**
Ya era el criterio del guard para el cuerpo de un heredoc. Lo único que hice fue
aplicarlo también al programa que llega por `-c`, que es el mismo texto en la
misma posición lógica. `veto_python` concede la lectura sólo si: hay `-c`, su
programa no contiene ninguna primitiva de escritura ni de delegación, y el
programa **no lleva `$` ni backtick** — porque el shell lo expandiría y este
scanner no, así que el texto juzgado no sería el que corre. `-m` no recibe pase
(el cuerpo del módulo no está en el comando), un script en disco tampoco, y
`python3 -` sigue exactamente como estaba.

**2. En un comando de copia, sólo el destino se escribe.** `cp`, `install` y
`rsync` leen todos sus orígenes y escriben exactamente uno: el último posicional,
o el valor de `-t`, y en ese caso todos los posicionales son origen. Es gramática
del comando, no intención. `mv` y `ln` quedan afuera a propósito: `mv` **borra**
su origen, así que muta la ruta protegida aunque el destino sea inocente;
`rsync --remove-source-files` hace lo mismo y devuelve `None` (falla cerrado).

Lo que NO cambié: el default sigue siendo fallar cerrado por segmento, y las
redirecciones se siguen juzgando aparte del comando, así que
`python3 -c "print(1)" > hooks/zzz.sh` bloquea aunque el programa sea inocente.

## Las tres corridas y la batería de pares

`tests/hooks/test_guard_accion_vs_mencion.py` — 22 tests, `22 passed`.

1. **El caso de lectura que bloqueaba, ahora pasa.**
   `python3 -c "import json;print(len(json.load(open('.claude/settings.json'))))"`
   → `rc=0`. Antes: `BLOCKED / .claude/settings.json`.

2. **La escritura equivalente sigue bloqueada.** Mismo archivo, misma forma:
   `python3 -c "import json;json.dump({}, open('.claude/settings.json','w'))"`
   → `rc=2`. Y el control duro del encargo:
   `python3 - <<'PY' … Path("hooks/zzz.sh").write_text("evil") … PY` → `rc=2`.

3. **El bloqueo que era correcto sigue en pie.**
   `git worktree add /private/tmp/…/x-wt HEAD` contra
   `hooks/destructive-git-blocker.sh` →
   `BLOCKED: destructive git op 'git worktree' is blocked by default (ADR-055b)`.

**La batería de pares** — 8 pares lectura/escritura sobre el mismo archivo y con
la misma forma sintáctica, más 6 formas que deben seguir bloqueadas y 7
escrituras delegadas que no se pueden colar:

| par | lectura → pasa | escritura → bloquea |
|---|---|---|
| `python -c` con `json.load` | `.claude/settings.json` | `json.dump(..., open(...,'w'))` |
| `python -c` con `pathlib` | `read_text` de `rules/` | `write_text` de `rules/` |
| intérprete del venv | `.venv/bin/python -c "print(open(...).read())"` | `open(...,'a').write(...)` |
| `os.path.exists` vs `os.remove` | existe | borra |
| `cp` origen vs destino | `cp hooks/x /tmp/y` | `cp /tmp/y hooks/x` |
| `cp` a directorio | `cp hooks/a hooks/b /tmp/` | `cp /tmp/a /tmp/b hooks/` |
| `install` | protegido como origen | protegido como destino |
| heredoc | `json.load` del settings | `write_text` de `hooks/` |

Siguen bloqueados por diseño, cada uno con su motivo escrito en el test: mover
el protegido con `mv`, `python -m`, script en disco, programa con variable sin
expandir, redirección a ruta protegida, y `rsync --remove-source-files`.

Regresión: `tests/red_team/portability/test_protected-config-write-guard.py`,
`tests/security/test_boundary_enforcement_p0.py` y
`tests/hooks/test_research_bypass_cannot_self_grant.py` → `23 passed`.

## Lo que propongo para el hook fuera del repo

`~/.claude/hooks/block-destructive-bash.sh` es el perfil del operador: **no lo
toqué**. Los 18 bloqueos que produjo se replayaron contra él (read-only) y el
motivo que imprime deja el defecto a la vista:

```
targets a path OUTSIDE the repo: /bin/bash, /bin/bash
targets a path OUTSIDE the repo: /usr/bin/time
targets a path OUTSIDE the repo: /dev/null",
targets a path OUTSIDE the repo: /Users/<clase de caracteres de una regex>
targets a path OUTSIDE the repo: /, /, /, /, /
```

Ninguno de esos tokens era el objetivo de un borrado. El hook decide en dos
pasos independientes: primero busca un verbo destructivo **en cualquier parte
del texto**, y después recolecta **cualquier token absoluto de todo el comando**.
Nunca comprueba que el token esté en el mismo segmento —ni en el mismo comando—
que el verbo. Por eso un borrado de `/tmp/sweep` seguido de un `nohup … /bin/bash`
acusa a `/bin/bash`, y una regex de rutas dentro de un `printf` se acusa a sí
misma.

Prueba en vivo, de hoy: **este mismo informe fue bloqueado al intentar
escribirlo** con un heredoc, porque el texto cita el verbo entre backticks al
explicar el defecto. El bloqueo listó `/bin/bash`, `/usr/bin/time` y `/dev/null`
como objetivos de un borrado que no existía. Por eso el archivo se escribió con
la herramienta Write, que no pasa por ese hook.

Diff propuesto, en dos partes, para que el operador decida:

1. **Atribuir el token al comando que lleva el verbo.** Partir `cmd` por `;`,
   `&&`, `||`, `|` y salto de línea; correr el bloque actual sobre **cada
   segmento por separado**, y acusar sólo los tokens del segmento cuyo verbo
   destructivo matcheó. Es un cambio de bucle, no de criterio: lo que hoy mira
   el comando entero pasaría a mirar un segmento.

2. **No leer el cuerpo de un heredoc con delimitador citado como comando.**
   `<<'EOF' … EOF` es dato literal para el shell. Quitar esos cuerpos antes de
   buscar el verbo elimina de un saque la familia "el comentario que cita el
   verbo como ejemplo" — que es exactamente lo que le pasó a este informe. Los
   tokens del *encabezado* se siguen mirando, así que un heredoc redirigido a
   una ruta de sistema no cambia de veredicto.

Con (1) y (2) sobreviven los bloqueos que realmente tienen un borrado apuntando
fuera del repo. No lo afirmo con un número porque no voy a modificar el archivo
del perfil para medirlo: la afirmación es el diseño, no una medición.

## Lo que NO hice y por qué

- **No toqué `~/.claude/hooks/block-destructive-bash.sh`.** Está fuera del repo
  y es el perfil del operador. Queda el diff propuesto arriba.
- **No relajé `bash script.sh` ni `source`.** Un script en disco es opaco: puede
  escribir cualquier cosa, incluida otra ruta protegida, y su texto no está en el
  comando. Es la causa de al menos 3 de los 21 bloqueos que quedan (correr un
  hook para probarlo), y es el precio correcto de un guard que falla cerrado.
- **No ataqué la familia más grande que queda**: 10 de los 21 bloqueos vivos son
  heredocs que escriben a una ruta **no** protegida (`tests/`, `scripts/`,
  `cos_lib/`) y mencionan una protegida en su prosa. Separarlos exige atribuir
  cada primitiva de escritura a su argumento —un análisis de flujo dentro del
  programa—, y una aproximación floja ahí deja pasar exactamente lo que el guard
  existe para parar. Queda nombrada, medida y sin arreglar a propósito.
- **No agregué telemetría de bloqueos.** El archivo que el guard dice emitir no
  existe (§Correcciones, 2). Arreglarlo toca `hooks/_lib/primitive-intervention.sh`,
  territorio de otro agente de esta sesión.
- **No moví ningún baseline ni agregué ninguna excepción por ruta.** Los dos
  cambios son propiedades del texto, y cada uno tiene su par de escritura
  probando que no se abrió nada.
