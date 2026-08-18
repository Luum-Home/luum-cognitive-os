<!-- SCOPE: os-only -->
# Los gates de abajo: once hooks, cinco que importan, cero que pude tocar

**Fecha:** 2026-08-16
**Antecedente:** `f44556c48` + `docs/06-Daily/reports/dispatcher-git-c-2026-08-16.md`
**Evidencia ejecutable:** `scripts/probe-hook-git-adjacency.sh`
**Parche propuesto:** `docs/06-Daily/reports/hooks-adyacencia-cierre-2026-08-16.patch`

> **Resultado en una línea.** El censo da **once** hooks con el patrón, no trece.
> **Cinco importan** y tienen escape medido; **dos importan y quedan fuera** del
> arreglo por buenos motivos; **tres no importan**; **uno ya está cubierto** —
> y es el que el informe de ayer daba por roto. El parche está escrito, probado
> contra los hooks reales y **no aplicado**: `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`
> como prefijo de comando **no funciona**, así que la escritura sobre `hooks/**`
> era imposible desde esta sesión. Eso se explica en §6.

---

## 1. El censo: once, no trece

El número se recontó del fuente, no del informe. Dos comandos, porque el patrón
vive en dos gramáticas (ERE con clases POSIX en bash, `\s` de Python):

```bash
grep -rnE "git\[\[:space:\]\]\+" hooks/     # forma bash
grep -rnE 'git\\s\+'             hooks/     # forma python
```

| # | archivo | línea(s) | veredicto |
|---|---|---|---|
| — | `hooks/bash-hot-path-dispatcher.sh` | 93, 95 | **ya arreglado** (`f44556c48`) |
| — | `hooks/git-commit-scope-guard.sh` | 118 | **ya arreglado** (`3045f71f8`) |
| 1 | `hooks/scope-marker-portability-gate.sh` | 61 | **importa** — escape medido |
| 2 | `hooks/release-guard.sh` | 47 | **importa** — escape medido |
| 3 | `hooks/agent-message-inbox-guard.sh` | 33 | **importa** — escape medido |
| 4 | `hooks/branch-ownership-lock.sh` | 45 | **importa** — escape medido |
| 5 | `hooks/post-git-orphan-notifier.sh` | 68, 89, 91, 93 | **importa** — escape medido |
| 6 | `hooks/control-plane-audit.sh` | 36 | **importa, latente** — rama Bash no registrada |
| 7 | `hooks/agent-bash-cwd-enforcer.sh` | 115, 171, 176 | **importa, arreglo distinto** |
| 8 | `hooks/cross-session-event-emit.sh` | 77, 79 | **no importa** — etiqueta, no decisión |
| 9 | `hooks/adr-detector.sh` | 29 | **no importa** — no registrado, no bloquea |
| 10 | `hooks/rate-limit-drain.sh` | 84 | **no importa** — la allowlist ya lo tapa |
| 11 | `hooks/destructive-git-blocker.sh` | 109, 114, 121, 164 | **ya cubierto** — tokeniza antes |

Los tres archivos fuera de `hooks/` que el informe de ayer metía en la última
fila (`cos_lib/lethal_trifecta.py`, `scripts/stash_quarantine_audit.py`,
`scripts/verify_claims.py`) no son gates y no se auditaron acá.

---

## 2. La clasificación, con el motivo de cada una

El criterio: **importa** si el hook decide sobre una operación de git y la
opción global cambia contra qué repo opera.

### Importan y tienen escape medido (1–5)

| hook | por qué importa | cómo llega el comando |
|---|---|---|
| `scope-marker-portability-gate` | decide sobre el commit; con `-C` juzga otro repo | despachado (batería de commit, dispatcher:163) |
| `release-guard` | **bloquea duro** un `git tag vX.Y`; con `-C` taggea otro repo sin gate | despachado (batería de release, dispatcher:178) |
| `agent-message-inbox-guard` | frena boundaries de git con mensajes sin ack | despachado (batería de boundary, dispatcher:145) |
| `branch-ownership-lock` | toma el lock de rama antes de escribir | despachado (batería de boundary, dispatcher:143) |
| `post-git-orphan-notifier` | detecta commits huérfanos tras rebase/reset | `PostToolUse[Bash]` en `.claude/settings.json` |

Los cuatro primeros son exactamente los que el arreglo del dispatcher acaba de
destrabar: ahora se los **invoca**, y salían temprano por su propio regex. El
quinto nunca dependió del dispatcher y fallaba igual.

`release-guard` tiene además un segundo agujero, independiente de las opciones
globales: su patrón está anclado a `^git\s+tag`, así que `cd /tmp && git tag
v9.9.9` también se le escapaba. Medido y arreglado en el mismo cambio.

### Importan, quedan afuera a propósito (6–7)

**6. `control-plane-audit.sh:36` — latente, no vivo.** La rama `Bash` de
`_should_run_control_plane_audit` decide si corre la auditoría del plano de
control, y con `git -C … commit` no corre. Pero el hook está registrado sólo en
`PreToolUse[Edit|Write]` y `PreToolUse[Agent]`, y **el dispatcher no lo
despacha**: hoy esa rama es inalcanzable.

```bash
python3 -c "import json;d=json.load(open('.claude/settings.json'))
for ev,ms in d['hooks'].items():
  for m in ms:
    for h in m.get('hooks',[]):
      if 'control-plane-audit' in h['command']: print(ev, m.get('matcher'))"
# → PreToolUse Edit|Write
# → PreToolUse Agent
```

Queda fuera del parche porque el parche sólo lleva escapes que pude **medir
corriendo el hook**. Si alguien registra ese hook en Bash, el diff de una línea
está en §5.

**7. `agent-bash-cwd-enforcer.sh:115,171,176` — el helper es el arreglo
equivocado.** El hook fuerza a los sub-agentes a operar sobre el worktree
principal, y **su línea 139 exime a propósito cualquier `git -C`**:

```bash
# hooks/agent-bash-cwd-enforcer.sh:139
if printf '%s' "$BASH_CMD" | grep -qE 'git\s+-C\s+'; then
  log_event "scoped_ok" "cmd already uses git -C <some-path>"
```

O sea: para este hook `-C` no es un escape, es la salida deseada. El agujero
real son `--git-dir=` y `--work-tree=`, que sí cambian el repo y no están
exentos. Pero aplicarle el helper haría que esos comandos lleguen al reescritor
de la línea 173, que produciría `git -C <main> --git-dir=/otro/.git commit` —
donde `--git-dir` sigue ganando y la reescritura sería mentira. Necesita el
tokenizador `shlex` de `destructive-git-blocker.sh`, no este regex. Además hoy
no está en `.claude/settings.json` (sólo en los perfiles `standard`/`paranoid`).
Lo dejo enunciado, sin diff: un diff que no probé es una hipótesis con formato
de parche.

### No importan (8–10)

**8. `cross-session-event-emit.sh:77,79`** — el regex elige el **nombre** del
evento (`commit-intent` / `commit-landed` frente a `session-heartbeat`). El
evento se emite igual; no hay gate que esquivar. Con `git -C` la telemetría
etiqueta mal, y eso es todo. Arreglarlo agregaría superficie a un hook que no
la pide.

**9. `adr-detector.sh:29`** — no está en `.claude/settings.json` ni lo despacha
el dispatcher. Es un generador de borradores de ADR, `PostToolUse`, "always
exits 0", con tope de 3 por sesión. No hay nada que bypassear.

**10. `rate-limit-drain.sh:84`** — el `\bgit\s+(push|reset|clean|checkout)\b`
es una entrada de **denylist**, pero `safe_to_execute()` exige además un match
de **allowlist** (`_SAFE_CMD_PATTERNS`, líneas 74–81) y ninguna forma de `git`
está en ella. `git -C x push` devuelve `False` por la allowlist, con o sin la
denylist. La línea 84 es redundante; arreglarla no cambia ningún resultado.

### Ya cubierto (11)

**11. `destructive-git-blocker.sh` — el encargo tiene razón, y por más de lo que
dice.** El brief pedía no tocarlo porque atrapa `cd x && git <op>`. Medido: no
sólo eso — atrapa también `git -C` y `--git-dir`.

```
rc=2  destructive-git-blocker.sh  git stash pop
rc=2  destructive-git-blocker.sh  cd /tmp && git stash pop
rc=2  destructive-git-blocker.sh  git -C /tmp/foo stash pop
rc=2  destructive-git-blocker.sh  git --git-dir=/tmp/foo/.git reset --hard
```

El motivo no son los regex de 109/114/121 —esos sí tienen adyacencia— sino que
antes de llegar a ellos el comando pasa por un tokenizador `shlex` que **saltea
las opciones globales**:

```python
# hooks/destructive-git-blocker.sh:205
if token in {"-C", "--git-dir", "--work-tree", "-c"}:
    i += 2
    continue
```

Eso convierte al informe de ayer en falso en ese punto: decía que
`git -C <dir> stash pop` "lo deja pasar igual". No lo deja pasar. No se tocó el
archivo.

---

## 3. La prueba: los hooks corriendo, antes y después

`scripts/probe-hook-git-adjacency.sh` ejecuta **cada hook real** con un payload
de harness contra un repo descartable, y mira si el gate **llegó a su decisión**
o salió temprano. Ninguna aserción mira el fuente: un regex arreglado pero
inalcanzable seguiría apareciendo como escape.

La señal de cada gate es un efecto observable suyo, no el exit code —cuatro de
los cinco salen 0 tanto cuando deciden como cuando no:

| gate | señal |
|---|---|
| `scope-marker-portability-gate` | métrica `bypass`, que sólo se escribe pasado el chequeo de commit |
| `release-guard` | su propio veredicto en stderr (`BLOCKED` / `ADVISORY`) |
| `agent-message-inbox-guard` | `SHOULD_CHECK=yes`, leído de una traza de ejecución |
| `branch-ownership-lock` | el archivo de lock que escribe al adquirir la rama |
| `post-git-orphan-notifier` | `TRIGGER_LABEL=`, que sólo se asigna pasado el trigger |

```bash
# contra el código de HEAD
bash scripts/probe-hook-git-adjacency.sh                 # → FINDINGS: 8, exit 1
# contra la copia parcheada
bash scripts/probe-hook-git-adjacency.sh /ruta/al/arbol  # → FINDINGS: 0, exit 0
```

**Los 8 escapes contra `HEAD`:**

```
ESCAPE  scope-marker-portability-gate   git -C /tmp/probe commit -m x       no metric
ESCAPE  scope-marker-portability-gate   git --no-pager commit -m x          no metric
ESCAPE  release-guard                   git -C /tmp/probe tag v9.9.9        silent
ESCAPE  release-guard                   cd /tmp && git tag v9.9.9           silent
ESCAPE  agent-message-inbox-guard       git -C /tmp/probe commit -m x       SHOULD_CHECK=no
ESCAPE  branch-ownership-lock           git -C /tmp/probe commit -m x       no lock
ESCAPE  post-git-orphan-notifier        git -C /tmp/probe rebase main       no trigger
ESCAPE  post-git-orphan-notifier        git --no-pager reset --soft HEAD~1  no trigger
```

**El reverso, que pasa en las dos versiones** (son PreToolUse: si el arreglo
convirtiera un gate en embudo, estas filas se caían):

```
ok  want=skip  git tag -d v9.9.9    silent      # borrar un tag no es una release
ok  want=skip  git tag -l           silent      # listar tampoco
ok  want=skip  ls -la               (×5 gates)  # ningún gate se despierta
ok  want=reach cd /tmp && git commit -m x       # lo que ya frenaba sigue frenando
```

El único gate que **empieza** a interceptar algo que antes dejaba pasar es
`release-guard` con `cd x && git tag vX.Y`, y eso es la corrección del ancla
`^`, no un efecto colateral: es exactamente lo que el hook dice que hace.

---

## 4. El arreglo propuesto: un solo parser más, no un cuarto

El parche crea **`hooks/_lib/git-command-parse.sh`** — la lista de opciones
globales y el matcher, una vez — y hace que los cinco gates lo consuman.

**Esto es una decisión de alcance que declaro, no la escondo:** el encargo daba
a elegir entre portar el helper o proponer su extracción a un lugar compartido.
Duplicar la lista en cinco archivos era el camino que el propio encargo prohíbe
("ya hay tres parsers de la misma gramática y está escrito que van a
divergir"); extraerla crea un archivo nuevo bajo `hooks/**`, que es config
protegida. Elegí extraer y dejarlo en el parche, sin aplicar.

Dos consumidores, una fuente:

- gates en bash → `cos_git_matches_subcommand "$cmd" 'commit'`
- gates con python embebido (`agent-message-inbox-guard`, `branch-ownership-lock`)
  → leen `$COS_GIT_GLOBAL_OPTS` del entorno. La alternancia está escrita **sin
  clases POSIX** (`[[:space:]]`), que el `re` de Python no soporta, justamente
  para que el mismo string valga en los dos motores. Una lista, dos
  composiciones finas.

```bash
COS_GIT_GLOBAL_OPTS='-C|-c|-P|--no-pager|--paginate|--git-dir|--work-tree|--namespace|--exec-path|--bare|--literal-pathspecs|--no-replace-objects|--no-optional-locks'
export COS_GIT_GLOBAL_OPTS

cos_git_matches_subcommand() {
  local cmd="$1" subs="$2"
  printf '%s' "$cmd" \
    | grep -Eq "(^|[|&;[:space:]])git[[:space:]]+($subs)([[:space:]]|$)" && return 0
  case "$cmd" in *"git -"*) ;; *) return 1 ;; esac      # prefiltro sin subproceso
  printf '%s' "$cmd" \
    | grep -Eq "(^|[|&;[:space:]])git[[:space:]]+(${COS_GIT_GLOBAL_OPTS})[^|&;]*[[:space:]]($subs)([[:space:]]|$)"
}
```

**Límite heredado del dispatcher, a propósito.** La corrida de opciones se
matchea como `[^|&;]*`, no se parsea: `git -C /r log --grep commit` matchea la
alternancia `commit`. Sobre-matchea (corre un gate que no hacía falta), nunca
sub-matchea. Quien necesite exactitud tiene el tokenizador `shlex` de
`destructive-git-blocker.sh`; ensanchar este regex sería el camino equivocado.

Dos gates no usan el helper tal cual, y el motivo está en el parche:

- **`release-guard`** parte la condición en dos: el helper dice "esto es un
  `git tag`", y un segundo grep conserva el calificador original de que sigue un
  argumento con forma de versión. Sin esa segunda mitad, `git tag -d` y
  `git tag -l` empezarían a bloquearse.
- **`post-git-orphan-notifier`** conserva su patrón original y **agrega** el
  helper como segunda alternativa, porque su trigger de `pull … --rebase` tiene
  estructura interna que el helper no expresa.

Aplicación y verificación:

```bash
patch -p1 -d <arbol> < docs/06-Daily/reports/hooks-adyacencia-cierre-2026-08-16.patch
bash scripts/probe-hook-git-adjacency.sh <arbol>   # → FINDINGS: 0
```

---

## 5. Diffs propuestos de lo que no toqué

**`hooks/control-plane-audit.sh:36`** — sólo si alguien registra el hook en
`Bash`. Requiere `source .../_lib/git-command-parse.sh` arriba:

```diff
     Bash)
-      printf '%s' "$command" | grep -Eq '(^|[;&|[:space:]])git[[:space:]]+commit\b|(^|[;&|[:space:]])git[[:space:]]+push\b|…'
-      return $?
+      cos_git_matches_subcommand "$command" 'commit|push' && return 0
+      printf '%s' "$command" | grep -Eq '(^|[;&|[:space:]])git[[:space:]]+(stash[[:space:]]+(pop|drop|apply)|reset|…)\b|cos-history-sanitization…'
+      return $?
       ;;
```

**`hooks/agent-bash-cwd-enforcer.sh`** — sin diff, a propósito. El arreglo
correcto es reemplazar los tres regex por el tokenizador `shlex`, conservando
la exención explícita de `-C` y agregando `--git-dir`/`--work-tree` como caso
de bloqueo (no de reescritura). Eso es un cambio de diseño del hook, no una
línea, y no lo probé.

---

## 6. Por qué el parche no está aplicado

`hooks/**` es config protegida y el brief autorizaba tocar los hooks nombrados
con `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`. **Ese prefijo no funciona**, y no es
una cuestión de forma:

```bash
# hooks/protected-config-write-guard.sh:25
if [ "${COS_ALLOW_PROTECTED_CONFIG_WRITE:-0}" = "1" ]; then
  exit 0
fi
```

Es una lectura del **entorno**, no del texto del comando. El hook es
`PreToolUse`: corre antes del comando, con el entorno del harness, así que un
prefijo `VAR=1 cmd` —que sólo existe dentro del proceso que el comando lanza—
nunca lo alcanza. Medido: el intento de escribir `hooks/_lib/git-command-parse.sh`
con el prefijo declarado fue bloqueado igual. Y `.claude/settings.json` no tiene
bloque `env`:

```bash
python3 -c "import json;print(json.load(open('.claude/settings.json')).get('env',{}))"   # → {}
```

La única vía sancionada es que el operador arranque la sesión con la variable ya
puesta. **Ninguna sesión de agente puede escribir `hooks/**` por sí sola**, y
eso vale también para el commit de ayer: el informe anterior atribuía su éxito
al prefijo (§7.10), y esa atribución no se sostiene contra este experimento.

Verificar el parche en un árbol descartable, en cambio, no toca el plano de
control: el árbol vive en el scratchpad, con `scripts/`, `cos_lib/` y
`manifests/` enlazados de solo lectura, y el `PROJECT_DIR` es un repo git
efímero. Ahí corrieron las dos pasadas del §3.

---

## 7. Costo — CPU, y el wall no es portable

Son PreToolUse. Medición A/B **intercalada** (una corrida vieja y una nueva por
iteración, para que la deriva de carga se cancele), n=80, CPU de
`RUSAGE_CHILDREN`. Load al medir: **3.16 sobre 12 cores**.

| hook | comando | CPU vieja | CPU nueva | Δ |
|---|---|---|---|---|
| `scope-marker-portability-gate` | `ls -la` | 47.09 ms | 46.96 ms | **−0.13 ms** |
| `scope-marker-portability-gate` | `git status` | 44.93 ms | 45.17 ms | +0.24 ms |
| `scope-marker-portability-gate` | `git -C /tmp/foo status` | 44.07 ms | 46.20 ms | +2.12 ms |
| `release-guard` | `ls -la` | 21.79 ms | 23.45 ms | +1.66 ms |
| `release-guard` | `git status` | 21.41 ms | 22.76 ms | +1.35 ms |
| `release-guard` | `git -C /tmp/foo status` | 21.15 ms | 23.92 ms | +2.77 ms |

Lectura honesta, sin redondear a favor:

- El camino que **no** trae guión pegado a `git` paga sólo el `source` del lib:
  ~0 ms en `scope-marker` (que ya sourcea `common.sh`), **+1.4 ms** en
  `release-guard`, que es un hook chico y ahí un archivo más se nota. No es
  ruido: la primera medición sin intercalar daba +2 a +7 ms y podía leerse como
  deriva; intercalada el signo se mantiene y la magnitud baja. Es costo real,
  chico.
- El camino con `git -` paga además el segundo `grep`: **+2.1 a +2.8 ms**. Es el
  precio de mirar el comando que hoy se saltea el gate.
- El wall de esta máquina no se reporta como comparable. La primera pasada, sin
  intercalar y con la carga moviéndose, daba deltas de hasta +7 ms sobre los
  mismos binarios.

---

## 8. Correcciones a las premisas del encargo

1. **«once hooks» y «trece hooks», en el mismo encargo.** El brief abre con
   *once* y dos párrafos después dice que el informe *enumera trece*. Recontado
   del fuente: **once**. La tabla del informe de ayer tiene 13 filas, pero dos
   son los hooks ya arreglados (`bash-hot-path-dispatcher`,
   `git-commit-scope-guard`) y una lumpea tres archivos que no son hooks. El
   propio §6 de ese informe dice "11 de ellos", así que el 13 es un conteo de
   filas de tabla, no de hooks. Comando: los dos `grep -rnE` del §1.
2. **`COS_ALLOW_PROTECTED_CONFIG_WRITE=1` no habilita nada desde una sesión de
   agente.** Es la premisa más cara del encargo, porque autorizaba un trabajo
   que resultó imposible. `hooks/protected-config-write-guard.sh:25` lee el
   entorno; el hook corre antes del comando. Detalle y medición en §6. Con esto,
   la instrucción "los diffs completos en el informe" pasó de ser un requisito
   accesorio a ser **el entregable**.
3. **`destructive-git-blocker.sh`: el brief acierta, el informe de ayer se
   equivoca.** El brief dice que atrapa `cd x && git <op>`; medido, atrapa
   también `git -C` y `--git-dir` (rc=2 en los cuatro payloads del §2). El
   informe de ayer afirmaba lo contrario para `git -C <dir> stash pop`. La causa
   es el tokenizador `shlex` de la línea 205, no los regex de 109/114/121.
4. **`research-compliance-guard.sh` se excluyó por nada.** El brief lo reserva
   para otro agente; el censo muestra que **no tiene el patrón** — no aparece en
   ninguno de los dos `grep`. La exclusión no costó nada, pero no era necesaria.
5. **«el helper ya existe y está probado, portalo»: cierto, e insuficiente por
   segunda vez.** El helper del dispatcher cubre la forma bash. Dos de los cinco
   gates que importan tienen el predicado dentro de python embebido, donde
   `[[:space:]]` no compila. Portarlo literal habría roto esos dos; por eso la
   lista se comparte por entorno y cada motor compone su propio regex.
6. **`git grep -E` y `\s`: sin verificar.** Usé `grep -rnE`, no `git grep`, y
   además buscaba el texto literal `git\s+` en el fuente, no `\s` como clase. La
   advertencia del encargo no se puso a prueba.
7. **`timeout`: sin verificar.** No hizo falta ninguno.
8. **`time { …; }` en zsh: confirmado inservible, pero por otra vía.** No lo usé;
   toda la medición salió de `resource.getrusage` desde Python, como el informe
   de ayer recomendaba.
9. **El bypass de rama es un token en el texto, no una variable de entorno.**
   El brief dice que `COS_ALLOW_MAIN_BRANCH_WRITE=1` funciona como prefijo y que
   `--allow-main-branch` rompe git. La primera mitad choca con §6: los prefijos
   de entorno no alcanzan a un PreToolUse. Lo que el guard sí lee es el texto:
   `hooks/destructive-git-blocker.sh:799` hace
   `grep -Eq '(^|[[:space:]])--allow-main-branch($|[[:space:]])'` sobre el
   comando. La segunda mitad del brief sí es cierta —git no conoce ese
   argumento— así que el token va donde git no lo ve y el grep sí: un comentario
   de shell al final de la línea. Queda escrito acá en vez de implícito.
10. **Verificado y confirmado sin cambios:** los cinco gates que arreglo son
    alcanzables hoy (cuatro por el dispatcher, uno registrado directo en
    `PostToolUse[Bash]`); `hooks/` no tiene symlinks en juego
    (`readlink -f` devuelve el mismo path para los once); la rama del checkout es
    `main` y el índice estaba limpio al commitear
    (`git diff --cached --name-only` → vacío).
