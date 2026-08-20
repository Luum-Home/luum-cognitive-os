# GNU-ismos que no existen en macOS — el censo de la clase que `flock` inauguró

Fecha: 2026-08-20 · Máquina medida: Darwin 25.5, `/bin/bash` 3.2.57, userland BSD
Reproducir todo: `python3 scripts/portability_census.py --json`

## Resumen ejecutivo

Sobre **689 archivos shell versionados** (deduplicados por realpath: un symlink y
su destino son un archivo), el censo encuentra **19 sitios sin guarda de
portabilidad** al empezar y **13 al terminar**; además **21 sitios ya guardados**,
que se cuentan para que el denominador no mienta.

De los 13 que quedan: **4 son de falla silenciosa** y **2 están en un camino que
se ejecuta** (hooks registrados en `.claude/settings.json`). Los otros 11 son
`REFERENCIADO`: alguien los nombra, pero no corren por turno.

Se arreglaron **6 sitios en 5 archivos**, todos en hooks registrados, con la
falla reproducida antes y las dos direcciones probadas después
(`bash scripts/portability-two-way-proof.sh`: BSD bash 3.2 → 7 ok, GNU debian
bash 5.2 → 7 ok). El hallazgo de mayor alcance: `hooks/subagent-context-injector.sh`
usaba `grep -oP`, que en el grep de macOS **devuelve vacío sin error**, así que
`agent_name` quedaba en `""` en **cada spawn de sub-agente de esta máquina**.

Instrumento: `scripts/portability_census.py` (censo, con `Census`), gate
`tests/audit/test_gnuismos_no_portables.py` (igualdad exacta, forma reusada del
gate de `flock`), prueba bidireccional `scripts/portability-two-way-proof.sh`.
Commits: `d7ee0bd38` (arreglos), `b90dc7693` (instrumento).

## Correcciones a las premisas del encargo

1. **La lista de sospechosos del encargo tiene falsos.** Medido con el PATH del
   sistema (`python3 scripts/portability_census.py --probe`), en este macOS
   **`readlink -f`, `realpath`, `sha256sum`, `xargs -r`, `sort -V`, `seq -f` y
   `mktemp -d -t` funcionan**. Darwin 25 los trae. Los que de verdad rompen son
   otros: `timeout` y `tac` **ausentes**; `date -d`, `sed -i` sin sufijo,
   `stat -c`, `grep -P`, `base64 -w`, `find -printf` **presentes con otra
   semántica**. Buscar los siete que sí andan habría producido hallazgos
   inventados.

2. **`${var^^}` no es un error de sintaxis, es un error de expansión.**
   `/bin/bash -n hooks/rule-md-routing-validator.sh` da **rc=0**: bash 3.2
   parsea el archivo entero sin quejarse. La falla llega en runtime
   (`bad substitution`, rc=1) y mata el script *en esa línea*, no antes. La
   diferencia importa: un `-n` en CI no lo detecta.

3. **Los tres shebangs son `#!/usr/bin/env bash`, no `#!/bin/bash`.** En esta
   máquina `env bash` resuelve a **bash 5.3.15** de Homebrew, así que
   `${base^^}` **hoy acá funciona**. El bug es real y late en un macOS sin
   Homebrew, pero decir "está roto ahora en esta máquina" habría sido falso.
   `grep -oP` y `timeout`, en cambio, **sí fallan acá y ahora**: no dependen de
   qué bash corra.

4. **El encargo pide sacar los dos `flock` de la `DEUDA` si los arreglo, y la
   regla 1 me prohíbe tocar `tests/audit/test_flock_has_a_portable_fallback.py`.**
   Las dos no se pueden cumplir a la vez. Gana la regla de atribución: no toqué
   los `flock` de `packages/agent-lifecycle/hooks/`. Quedan para quien es dueño
   de ese gate.

5. **`hooks/_lib/portable.sh` ya existía**, con `portable_date_minus`,
   `portable_sed_inplace`, `portable_stat_mtime`, `portable_stat_size` y
   `portable_readlines`, y 20 archivos ya lo sourcean. El encargo lo trata como
   terreno virgen. No lo es: la parte de `date`/`sed`/`stat`/`mapfile` ya estaba
   resuelta, y por eso el censo encuentra 21 sitios **guardados**. Lo que
   faltaba era `timeout`; se agregó ahí y no en un helper nuevo.

6. **Mezclé un cambio ajeno en un commit, sin querer, y hay que decirlo.**
   Construí a mano el blob de `hooks/rule-md-routing-validator.sh` desde HEAD
   para no arrastrar el borrado de otra sesión (`# Latency: <100ms…`), pero
   `git commit -- <paths>` **commitea el worktree, no el índice**: el
   `update-index` quedó ignorado y el borrado ajeno entró igual en `d7ee0bd38`.
   Es una línea de comentario, pero el mecanismo que creí que me protegía no me
   protegió, y esa es la parte que importa.

7. **Dos gates del propio repo bloquearon mis commits** — y los dos tenían
   razón: `destructive-git-blocker` (commit directo sobre `main`; se usó el
   token `--allow-main-branch` que el propio hook ofrece, porque `--switch` en
   un checkout con tres sesiones movería la rama de todas) y
   `scope-both-portability-proof` (todo artefacto `# SCOPE: both` necesita su
   proof pareado; se generaron con `scripts/cos-portability-proof-scaffold`).
   El segundo es irónicamente apropiado: el gate de portabilidad frenó al censo
   de portabilidad.

## El censo: población, medibles, ciegos

```
$ python3 scripts/portability_census.py --json
población: 689 archivos shell versionados únicos
           (git ls-files, sufijo .sh/.bash/.zsh o shebang, dedup por realpath)

buckets (lo que el instrumento SÍ pudo juzgar)
  sin-guarda-SILENCIOSA   4
  sin-guarda-RUIDOSA      9
  con-guarda             21

ciegos (lo que no pudo ver, declarado con tamaño)
  ilegible                              0
  symlink-externo                       0
  familia-delegada-flock                1   -> test_flock_has_a_portable_fallback.py
  shell-embebido-en-yaml-json-md       43   -> workflows y manifests con `run:`
```

Decisiones de medición que cambian el número, escritas para que se puedan
discutir:

- **La disponibilidad se prueba, no se lee de una lista.** Cada familia corre su
  comando contra `PATH=/usr/bin:/bin:/usr/sbin:/sbin`. Medir contra el PATH del
  operador mediría *su máquina*: con `coreutils` de Homebrew hay `gdate` y
  `gtimeout` adelante y taparían justo lo que se busca.
- **Los comentarios no cuentan.** La mitad de los falsos positivos de la primera
  corrida (19 → 13 tras el filtro) eran comentarios que *explicaban* el GNU-ismo
  (`# macOS sed -i differs from GNU`), o sea justo los archivos donde alguien ya
  se había dado cuenta.
- **El idioma portable cuenta como guarda.** `date -j -f … || date -d …` es BSD
  primero, GNU de fallback: es el arreglo correcto, no un hallazgo. Seis sitios
  salieron del conteo por esto.
- **`flock` se delega, no se duplica.** Hay un test (`test_flock_no_se_mide_dos_veces`)
  que falla si alguien agrega una familia `flock` al censo. Dos instrumentos
  midiendo lo mismo con criterios distintos es peor que uno: el día que
  discrepen, nadie sabe cuál creer.

## Falla ruidosa vs falla silenciosa

| Familia | En esta máquina | Qué pasa cuando falla |
|---|---|---|
| `timeout`, `tac` | **AUSENTE** | 127. Ruidoso… salvo `\|\| true`, `2>/dev/null` o `if !`, que es lo habitual |
| `date -d`, `stat -c`, `grep -P`, `base64 -w`, `find -printf` | **BSD-DISTINTO** | rc≠0 con stderr, **o peor**: salida distinta sin error |
| `sed -i` sin sufijo | **BSD-DISTINTO** | con `-i -e`, BSD toma `-e` como sufijo y **escribe backups fantasma** |
| `declare -A`, `${v^^}`, `mapfile`, `&>>` | **bash 3.2** | `invalid option` y sigue (silenciosa), o `bad substitution` y muere |

La peligrosa es la silenciosa, y en este repo tiene **dos formas distintas**:

1. **El supresor en el sitio.** `grep -oP … 2>/dev/null`: el 127 o el
   "invalid option" se tiran a la basura y el llamador lee vacío.
2. **La degradación sin error.** `grep -oP` en BSD grep **sale 0 con salida
   vacía** cuando el patrón no compila como BRE. No hay nada que suprimir: no
   hay error.

Y un matiz que el instrumento no puede ver, dicho acá: **"ruidosa" dentro de un
hook puede ser invisible igual**. El stderr de un hook no llega al operador. Un
`timeout: command not found` en `query-tailored-context-inject.sh` es ruidoso
para el shell y mudo para la persona.

## Los que están en un camino que se ejecuta

Liveness contra los tres manifests (`.claude/settings.json`, `.codex/hooks.json`,
`.opencode/cos-hooks.json`). Al empezar, **6 hooks registrados** tenían
GNU-ismos sin guarda. Quedan **2**:

| Archivo | Familia | Ruido | Estado |
|---|---|---|---|
| `hooks/docker-drift-detector.sh` | `timeout` | SILENCIOSA | queda (ver abajo) |
| `hooks/query-tailored-context-inject.sh` | `timeout` | RUIDOSA | queda (ver abajo) |

Los 11 restantes son `REFERENCIADO`: `hooks/adr-detector.sh`,
`code-review-on-commit.sh`, `ecosystem-check.sh`, `mlflow-sync.sh`,
`orchestrator-mode-detect.sh`, `session-hygiene.sh`, `usage-health-check.sh`,
`scripts/cos-update.sh`, `scripts/startup-benchmark.sh`,
`scripts/benchmark-hooks.sh` y
`packages/quality-gates/hooks/clarification-interceptor.sh`. Son deuda, no
fallo por turno.

## Lo arreglado, con sus dos direcciones

Commit `d7ee0bd38`. Cada uno con el rojo antes y el verde después; el control de
que en GNU sigue andando está en `scripts/portability-two-way-proof.sh`, que
corre **las mismas aserciones** sobre los dos userlands.

### 1. `hooks/subagent-context-injector.sh` — `grep -oP` ×3 (SILENCIOSA, registrado)

**Antes**, en esta máquina:

```
$ env bash -c 'grep --version | head -1'
grep (BSD grep, GNU compatible) 2.6.0-FreeBSD

$ agent_prompt="Identity: mi-agente-de-prueba"
$ echo "$agent_prompt" | grep -oP "Identity:\s*(\S+)" 2>/dev/null | head -1
                      # (vacío, sin error)
```

`agent_name` quedaba `""`, los tres fallbacks fallaban igual, y la búsqueda de
sidecar (`COS_SUBAGENT_SIDECAR_LOOKUP`) no se intentaba nunca. En **cada** spawn.

**Después**: `sed -nE 's/.*Identity:[[:space:]]*([^[:space:]]+).*/\1/p'` (POSIX
ERE; `\s`/`\S` tampoco existen en ERE) y `grep -oE` para las fases sdd.

**Las dos direcciones**:

```
$ bash scripts/portability-two-way-proof.sh
=== direccion BSD: /bin/bash 3.2.57(1)-release ===
  ok: Identity: -> nombre
  ok: skills/<x>/ -> nombre
  ok: fase sdd-*
  ok: prompt sin marcas -> vacio        <- control anti-falso-positivo
  ...
  info: este userland NO tiene grep -P (BSD) <- la falla original
  fallas=0
=== direccion GNU: debian:stable-slim en docker ===
  bash: 5.2.37(1)-release
  ok: (las mismas 7)
  info: este userland SI tiene grep -P (GNU)
  fallas=0
```

### 2. `hooks/rule-md-routing-validator.sh` — `${base^^}` (registrado)

**Antes**, con el bash del sistema:

```
$ /bin/bash -c 'base="Roadmap.md"; case "${base^^}" in ROADMAP.MD) echo si;; esac'
/bin/bash: ${base^^}: bad substitution
rc=1
```

El hook muere ahí: no saltea `ROADMAP.md`, ni valida nada de lo que sigue.
**Después**: `printf '%s' "$base" | tr '[:lower:]' '[:upper:]'`, POSIX, idéntico
en los dos userlands (aserción 5 del proof).

**Alcance honesto**: con `#!/usr/bin/env bash` y Homebrew instalado, hoy acá
corría bash 5 y esto **no** estaba fallando. Es un bug latente, no uno activo.

### 3. `timeout` → `portable_timeout` en `hooks/_lib/portable.sh`

**Antes**:

```
$ env bash -c 'command -v timeout || echo AUSENTE; command -v gtimeout || echo AUSENTE'
AUSENTE
AUSENTE
```

Todo `timeout N cmd` sale 127. En `inject-phase-context.sh` eso vaciaba
`ENGRAM_WARNINGS`; en `error-pipeline.sh`, marcaba el fix como fallido.

**Después**: `portable_timeout` en `hooks/_lib/portable.sh` — detecta `timeout`,
si no `gtimeout`, si no cae a `python3` con `subprocess.run(timeout=)`, que
devuelve **124** al cortar igual que coreutils. Si tampoco hay python3, corre
sin límite **y lo dice por stderr**: bajar el límite en silencio sería cambiar
una falla ruidosa por una muda, que es exactamente el bug que el helper viene a
sacar. Aserciones 6 y 7 del proof (pasa el rc; corta con 124), verdes en los dos
userlands.

Convertidos: `hooks/inject-phase-context.sh` y `hooks/error-pipeline.sh` — los
dos que **ya** sourcean `portable.sh`.

## Lo que NO arreglé y por qué

Todo lo de abajo está en la `DEUDA` de `tests/audit/test_gnuismos_no_portables.py`
con **igualdad exacta**: si alguien lo arregla, el test *exige* sacarlo de ahí;
si aparece uno nuevo, falla. No es un colchón.

- **Los 9 `timeout` restantes** (incluidos los 2 hooks registrados). El arreglo
  correcto es `portable_timeout`, pero exige que el archivo sourcee
  `portable.sh`, y `portable.sh` corre **tres feature-tests más un `mktemp`** al
  cargarse. `query-tailored-context-inject.sh` usa `timeout 0.4` justamente
  porque está en el camino caliente de cold-start: meterle ese costo es
  latencia que **no medí**. Un cambio que no puedo tasar no es un arreglo, es
  una apuesta.

- **`packages/quality-gates/hooks/clarification-interceptor.sh`** (`grep -oP`).
  El archivo trae un fallback a `sed` en la línea siguiente. Falta verificar que
  el fallback produzca lo mismo; sin ese rojo previo, tocarlo sería una
  hipótesis con formato de commit.

- **`scripts/benchmark-hooks.sh`** (`declare -A … 2>/dev/null || true  # bash 3.2
  compat handled below`). La degradación es deliberada y está escrita al lado.
  Queda listado para que se **vea**, no para que se arregle.

- **Los dos `flock` de `packages/agent-lifecycle/hooks/`** (`agent-checkpoint.sh`,
  `agent-prelaunch.sh`). Ver corrección 4: el encargo pide arreglarlos y la
  regla de atribución prohíbe editar el gate donde están listados. No se puede
  arreglar uno sin tocar el otro, así que quedan enteros para su dueño. Siguen
  siendo el caso peor de la clase: `flock -w 2 200 2>/dev/null || true` **hace
  el trabajo sin lock**, en un checkout con varias sesiones escribiendo a la vez.

- **Shell embebido en YAML/JSON/Markdown** (43 archivos con `run:`/`command:`).
  El censo lo cuenta como ceguera con tamaño en vez de reportar cero. Extender
  el detector ahí es trabajo aparte, y un cero sin decir que no se miró es
  peor que un ciego declarado.

- **`tac`, `find -printf`, `base64 -w`, `stat -c`, `sed -i` sin sufijo**: cero
  sitios sin guarda en el árbol. No es que no se buscaron — el detector los
  tiene y su control anti-falso-positivo los ejercita
  (`test_el_detector_discrimina`). Simplemente no hay.
