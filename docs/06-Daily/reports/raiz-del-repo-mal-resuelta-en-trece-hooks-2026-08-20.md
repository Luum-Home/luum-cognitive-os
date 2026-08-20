# La raíz del repo mal resuelta en trece hooks

**Fecha:** 2026-08-20
**Alcance:** `hooks/*.sh` (189 declaran `PROJECT_DIR`; 13 la resuelven fuera del repo)
**Estado:** diagnóstico cerrado, gate escrito y corrido, arreglo **listo pero sin aplicar** —
`hooks/**` es ruta protegida y el desbloqueo lo decide el operador (ver §7).

---

## 1. Correcciones a las premisas del encargo

1. **El riesgo de los symlinks no existe: `../..` está mal en TODAS las topologías.**
   El encargo pedía cuidado porque `../..` podría ser correcto desde la ruta real del
   paquete. No lo es. Aritmética medida, no razonada:

   ```
   $ ( cd "$(dirname hooks/confidence-gate.sh)/../.." && pwd )
   <repo-parent>                      <- padre del repo
   $ ( cd "$(dirname packages/quality-gates/hooks/confidence-gate.sh)/../.." && pwd )
   <repo>/packages   <- <root>/packages
   ```

   Ninguno de los trece queda "bien por topología". No hay hooks que no haya que tocar.

2. **La degradación reproduce, pero los tamaños del encargo (1636 vs 8645) no.**
   Mi sonda mide **834 bytes con `CLAUDE_PROJECT_DIR` y 827 sin él** (§2). La diferencia
   de tamaño es casi nula; el discriminante real es *qué proyecto dice ser*:
   `PROJECT: luum-cognitive-os` vs `PROJECT: my-project`. Un instrumento que solo mirara
   bytes habría dicho "no reproduce". Los 1636 del encargo sí existen — son el tamaño de
   varios `.ctx` cacheados, pero **cacheados afuera del repo** (§3), no la salida de la
   corrida buena.

3. **No son trece hooks los que declaran `PROJECT_DIR`: son 189.** Trece la resuelven mal.
   El gate mide los 189 y señala 13, así que el número tiene denominador.

4. **Cinco hooks más aparecieron como rojos y eran falsos positivos MÍOS**, no del repo:
   `aspirational-audit-weekly`, `bash-hot-path-dispatcher`, `promotion-proposer-weekly`,
   `self-knowledge-refresh`, `validator-soak-weekly` usan `"$SCRIPT_DIR/.."` (un nivel,
   correcto). Mi extractor evaluaba la línea del `PROJECT_DIR=` sin arrastrar el
   `SCRIPT_DIR=` previo, así que `cd "/.."` daba `/`. Corregido; hoy el gate los deja en
   verde. Queda dicho porque el instrumento roto duró tres corridas.

5. **El arreglo no se pudo aplicar.** `hooks/**` está en `protected_globs` de
   `hooks/protected-config-write-guard.sh:128`; el guard bloqueó tanto el archivo nuevo
   en `hooks/_lib/` como la edición de los siete hooks reales. No activé
   `COS_ALLOW_PROTECTED_CONFIG_WRITE`: el propio guard dice "only after explicit human
   review", y el permiso no me lo puede dar quien me mandó. Detalle y comando en §7.

---

## 2. Reproducción de la degradación

Sonda: `scratchpad/probe.sh` (dos corridas del mismo hook, mismo payload, mismo cwd; lo
único que cambia es si `CLAUDE_PROJECT_DIR` está seteada; `COGNITIVE_OS_SESSION_ID`
distinto por corrida para que no conteste la caché).

```
=== A: WITH CLAUDE_PROJECT_DIR (correct root) ===
with BYTES=834
with FIRST_200: {"hookSpecificOutput": ... "\nPROJECT: luum-cognitive-os (webapp)\nPHASE: reconstruction\n...

=== B: WITHOUT CLAUDE_PROJECT_DIR (fallback exercised) ===
without BYTES=827
without FIRST_200: {"hookSpecificOutput": ... "\nPROJECT: my-project (webapp)\nPHASE: reconstruction\n...

=== PROJECT: marker in each ===
PROJECT: luum-cognitive-os
PROJECT: my-project
```

Reproduce. Sin `CLAUDE_PROJECT_DIR` el hook no encuentra `cognitive-os.yaml` —lo busca en
el padre del repo— y emite el contexto por defecto. El agente que reciba eso cree estar
en un proyecto llamado `my-project`.

## 3. Lo que ya pasó, no lo que podría pasar

El fallback no es teórico: dejó rastro en el **directorio padre del repo**, que ni
siquiera es un repositorio git.

```
$ git -C <repo-parent> rev-parse --show-toplevel
fatal: not a git repository (or any of the parent directories): .git

$ find <repo-parent>/.cognitive-os -type f | wc -l
      14
$ ls -la .../luum/.cognitive-os/cache/inject-phase-context/ | head
-rw-r--r--@ 1 ... 1636 Aug 20 13:01 24a22d4f....ctx
-rw-r--r--@ 1 ... 1297 Jun 10 16:52 504e3458....ctx
-rw-r--r--@ 1 ...  827 Jun 10 16:52 cb069025....ctx
```

Siete pares `.ctx`/`.ts` de `inject-phase-context`, el más viejo del **10 de junio**. El
hook viene escribiendo su caché afuera del repo desde hace más de dos meses, en silencio.
(En el mismo padre hay también un `.cos-agent-worktrees/` del 7 de mayo; no lo atribuyo a
estos trece hooks, no lo verifiqué.)

## 4. Los trece, uno por uno

`ls -la hooks/<name>.sh` para la columna symlink; `grep -n 'PROJECT_DIR'` +
`grep -nE 'mkdir -p|>>|tee|touch|safe_jsonl'` para qué hace con la raíz.

### 4.1 Los que ESCRIBEN fuera del repo (prioridad)

| Hook | symlink | qué escribe con la raíz mal resuelta | veredicto |
|---|---|---|---|
| `inject-phase-context.sh` | no | `<padre>/.cognitive-os/cache/inject-phase-context/*.ctx|.ts` (`:73-75`) y el marcador `<padre>/.cognitive-os/sessions/$SID/.gotchas-injected` (`:326`) | **ESCRIBE — confirmado en disco (§3)** |
| `pre-cleanup-snapshot.sh` | no | `mkdir -p` + `safe_jsonl_append` sobre `<padre>/.cognitive-os/metrics/capability-snapshots.jsonl` (`:21,68,74`); `CHECKPOINTS_DIR` en `<padre>` (`:22`) | ESCRIBE |
| `architecture-compliance.sh` | → `packages/verification-audit/hooks/` | `mkdir -p` + jsonl sobre `<padre>/.cognitive-os/metrics/architecture-violations.jsonl` (`:21,91,101`) | ESCRIBE |
| `infra-intent-detector.sh` | no | `mkdir -p` + jsonl sobre `<padre>/.cognitive-os/metrics/infra-detections.jsonl` (`:22-23,119,122`) | ESCRIBE |
| `resource-check.sh` | no | `mkdir -p "<padre>/.cognitive-os/metrics"` (`:39`) + cinco `safe_jsonl_append` a `resource-checks.jsonl` (`:22,100-149`) | ESCRIBE |
| `engram-auto-import.sh` | → `packages/engram-sync/hooks/` | `touch "<padre>/.engram/exports/.last-import"` (`:13,49`) — el `touch` falla si el dir no existe, así que puede no llegar a escribir; igual lee el export dir equivocado | ESCRIBE (condicional) |

### 4.2 Los que LEEN mal (degradan en silencio)

| Hook | symlink | qué hace con la raíz mal resuelta | veredicto |
|---|---|---|---|
| `goal-stop-gate.sh` | no | pasa `PROJECT_DIR` a un python que hace `sys.path.insert(0, project_dir)` e importa `cos_lib.goal_state`; el import falla → `except ImportError: sys.exit(0)` → **el gate deja pasar todo**. Además `base_dir = <padre>/.cognitive-os/goals` (`:51-77`) | LEE — gate desactivado en silencio |
| `confidence-gate.sh` | → `packages/quality-gates/hooks/` | `CONFIG_FILE="<padre>/cognitive-os.yaml"` (`:75`); el log va por `_resolve_metrics_dir` (safe-jsonl, que sí resuelve bien) | LEE |
| `auto-rollback-trigger.sh` | → `packages/auto-repair-rollback/hooks/` | `CONFIG_FILE="<padre>/cognitive-os.yaml"` (`:29`); log por `_resolve_metrics_dir` | LEE |
| `eas-validation-gate.sh` | no | `find <padre>/openspec/changes`, `find <padre>/docs`, `python3 <padre>/scripts/eas_validate.py` (`:57-82`) — no encuentra nada, valida nada | LEE |
| `cognitive-os-health.sh` | no | `<padre>/.cognitive-os`, `<padre>/.claude/settings*.json`, `<padre>/docker-compose.cognitive-os.yml` (`:14-249`) — reporta salud de un proyecto que no existe | LEE |
| `engram-auto-sync.sh` | → `packages/engram-sync/hooks/` | `EXPORT_DIR`, `SYNC_SCRIPT` y un **`cd "$PROJECT_DIR"`** al padre del repo (`:12-13,34`); el script no está ahí, así que corta | LEE (+ `cd` afuera) |
| `dry-run-preview.sh` | → `packages/dry-run-simulation/hooks/` | **ninguno**: `PROJECT_DIR` se asigna en `:21` y no se usa en ninguna otra línea (`grep -c 'PROJECT_DIR'` = 1). Variable muerta | inocuo hoy, mina para mañana |

Resumen: **6 escriben** (5 confirmados por código + 1 condicional), **7 leen**, de los
cuales `goal-stop-gate` es el peor de los "solo lee" porque su degradación es *permitir*.

## 5. El arreglo

Helper compartido, no trece parches. Antes de escribirlo busqué uno existente:

```
$ git grep -n 'PROJECT_DIR=' -- hooks/_lib/
hooks/_lib/common.sh:29:  _PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
hooks/_lib/hook-pipe.sh:35: ... (idem)
hooks/_lib/safe-jsonl.sh:37: ... (idem)
```

Existe la cadena de precedencia correcta, pero (a) publica `_PROJECT_DIR`, no una función
reutilizable, (b) su último recurso depende del **cwd**, y (c) solo cuatro de los trece
sourcean `common.sh`. Por eso el helper nuevo `hooks/_lib/project-root.sh` expone
`cos_project_root()` y ancla en **la ubicación física de la propia librería**:

```bash
_COS_PROJECT_ROOT_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
_COS_PROJECT_ROOT_ANCHORED="${_COS_PROJECT_ROOT_LIB_DIR%/*/*}"
```

`pwd -P` es lo que hace que funcione desde las dos rutas: `packages/*/hooks/_lib` es un
symlink a `../../../hooks/_lib` (`ls -la packages/quality-gates/hooks/`), así que toda
invocación colapsa sobre el mismo directorio físico. No usa `$0` (que es exactamente lo
que varía) ni el cwd.

Prueba en las cuatro topologías, contra una raíz derivada por `git rev-parse` —o sea, por
una fuente distinta de la expresión bajo prueba (`scratchpad/build-sandbox.sh`):

```
EXPECTED ROOT (git rev-parse, independent of the code under test): .../sandbox/proj

INVOCATION PATH                            OK?  RESOLVED
OLD  hooks/buggy.sh          (cwd=proj)    BAD  .../sandbox            <- padre
OLD  hooks/buggy-pkg.sh -> pkg (cwd=proj)  BAD  .../sandbox            <- padre
OLD  packages/pkg/hooks/buggy-pkg.sh       BAD  .../sandbox/proj/packages
NEW  hooks/fixed.sh          (cwd=proj)    OK   .../sandbox/proj
NEW  hooks/fixed.sh          (cwd=/)       OK   .../sandbox/proj
NEW  hooks/fixed-pkg.sh -> pkg (cwd=proj)  OK   .../sandbox/proj
NEW  packages/pkg/hooks/fixed-pkg.sh       OK   .../sandbox/proj
NEW  hooks/fixed.sh          (cwd=/tmp)    OK   .../sandbox/proj
```

El aplicador es `scripts/fix_hook_project_root_fallback.py` (idempotente): escribe el
helper, reemplaza la asignación por `PROJECT_DIR="$(cos_project_root)"` e inserta el
`source` si falta. Resuelve el symlink antes de escribir (`Path.resolve()`), así que toca
el archivo real en `packages/*/hooks/` y no intenta escribir a través del link.

## 6. El gate, y por qué no se certifica a sí mismo

`tests/red_team/portability/test_hook_project_root_fallback.py`. Tres aserciones:

1. **Dinámica** — extrae de cada uno de los 189 hooks su propia asignación de
   `PROJECT_DIR` (verbatim, arrastrando el `SCRIPT_DIR=` previo cuando hace falta) y la
   ejecuta con `$0` = la ruta del hook y **sin** `CLAUDE_PROJECT_DIR`/`CODEX_*`/`COGNITIVE_OS_*`.
   Compara contra la raíz esperada.
2. **Estática** — ningún `hooks/*.sh` puede contener `dirname "$0")/../..`.
3. **Falsación** — planta un hook con el idiom malo en un `tmp_path` y exige que el
   checker lo marque. Sin esto, un checker que devuelve siempre `[]` pasaría para siempre.

**La trampa evitada:** la raíz esperada NO se deriva con la expresión que se está
auditando. Se encuentra subiendo desde `__file__` hasta el directorio que *contiene*
`.git` y `hooks/_lib` — identidad por contenido, no aritmética de `..`.

La aserción 3 ya se ganó el lugar: en la primera corrida verde detectó que yo había
roto la regex de extracción (quedó `r'^\\s*PROJECT_DIR='`, o sea backslash literal) y el
gate estaba evaluando **cero** hooks mientras informaba verde.

### Contrafáctico, corrido sobre el mismo árbol

`scratchpad/counterfactual.py` arma un árbol desechable con los prólogos **verbatim** de
los trece hooks reales (la mitad como archivos de paquete expuestos por symlink, como en
el repo) más tres hooks sanos de control, y corre el gate tres veces:

```
=== RUN 1  fix NOT applied: RED (13 of 16 hooks misresolve) ===
    architecture-compliance.sh: resolved '.../cf', expected '<proj>'
    ... (13 líneas)

--- scripts/fix_hook_project_root_fallback.py ---
offending hooks: 13
  wrote hooks/_lib/project-root.sh
  patched architecture-compliance.sh -> packages/pkg/hooks/architecture-compliance.sh
  ... (13 líneas)

=== RUN 2  fix applied: GREEN (0 of 16 hooks misresolve) ===

=== RUN 3  fix REVERTED on auto-rollback-trigger.sh: RED (1 of 16 hooks misresolve) ===
    auto-rollback-trigger.sh: resolved '.../cf', expected '<proj>'

SUMMARY  red_before=13  green_after=0  red_again_after_revert=1
PASS
```

Los tres hooks sanos quedan verdes en las tres corridas: el gate distingue, no falla todo.

Sobre el árbol real, hoy, el gate está **rojo**:

```
$ .venv/bin/python3 -m pytest tests/red_team/portability/test_hook_project_root_fallback.py -q
FAILED ...::test_hooks_resolve_project_root_without_claude_project_dir
FAILED ...::test_no_hook_uses_the_two_level_dollar_zero_idiom
2 failed, 1 passed in 25.48s
# 189 hooks evaluados, 13 fallan, todos resolviendo <repo-parent>
```

## 7. Por qué el arreglo no está aplicado

`hooks/**` es ruta protegida (`hooks/protected-config-write-guard.sh:128`,
`protected_globs`). El guard bloqueó:

- crear `hooks/_lib/project-root.sh` → `PROTECTED CONFIG WRITE GUARD: BLOCKED`;
- editar los siete hooks reales bajo `hooks/`.

(Los seis que son symlink viven en `packages/*/hooks/`, que **no** está protegido: ahí sí
se puede escribir. Lo verifiqué editando y revirtiendo `dry-run-preview.sh`; el árbol
quedó limpio, `git diff --stat` vacío. Aplicar solo esos seis dejaría el sistema peor:
llamarían a `cos_project_root` sin que la librería exista.)

El desbloqueo es del operador:

```bash
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 .venv/bin/python3 scripts/fix_hook_project_root_fallback.py
.venv/bin/python3 -m pytest tests/red_team/portability/test_hook_project_root_fallback.py -q
```

Antes de aplicar conviene mirar `--dry-run`, que lista los trece con el archivo real
detrás de cada symlink.

## 8. Lo que queda abierto

- **Basura fuera del repo.** Los 14 archivos en `<repo-parent>/.cognitive-os/`
  no los toqué. Son caché regenerable; borrarlos es decisión del operador y no depende de
  este arreglo.
- **`dry-run-preview.sh` asigna `PROJECT_DIR` y no la usa.** El aplicador se la arregla
  igual (la variable muerta con el valor correcto no molesta), pero lo suyo sería
  borrarla.
- **La cadena de precedencia se unifica de paso.** Ocho de los trece solo miraban
  `CLAUDE_PROJECT_DIR`; con el helper pasan a respetar también `COGNITIVE_OS_PROJECT_DIR`
  y `CODEX_PROJECT_DIR`. Es una mejora de portabilidad, pero es un cambio de
  comportamiento en un arreglo de bug: vale decirlo en voz alta.
- **El gate mide con `cwd` = raíz del repo**, el caso más benévolo. Hay hooks que caen a
  `$(pwd)` y pasarían el gate hoy pero resolverían mal con otro cwd. No los conté; sería
  otro encargo.
