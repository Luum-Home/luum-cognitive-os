---
title: "Auditoría de arquitectura — código (cos_lib/ y scripts/)"
date: 2026-08-15
tipo: auditoría
alcance: cos_lib/, scripts/
modo: read-only
---

# Auditoría de arquitectura — el código

Porción auditada: `cos_lib/` (369 módulos) y `scripts/` (742 archivos trackeados).
Fuera de alcance por partición: hooks, skills+rules, instalador+packages, tests+CI+telemetría, ADRs.

Todas las cifras salen de tres scripts pegados al final. Read-only: no se editó
ni commiteó nada del repo; las salidas intermedias fueron al scratchpad.

---

## 1. Veredicto

**Acumulación con contabilidad**: no hay capas ni límites en el código —el grafo de
`cos_lib` es un archipiélago, 45% de los módulos no importan ni son importados por
ningún otro— pero encima se montó un aparato de registro (ledgers, manifests, roles)
que sí tiene estructura. La arquitectura está en la contabilidad del inventario, no
en el código que inventaría.

---

## 2. El grafo de `cos_lib`

369 nodos, **232 aristas**, densidad `0.0017`, grado medio `0.63`.

| Métrica | Valor |
|---|---|
| Módulos aislados (fan-in 0 **y** fan-out 0) | **167 (45%)** |
| Raíces (fan-in 0) | 255 (69%) |
| Hojas (fan-out 0) | 234 (63%) |
| fan-in mediana / p90 / máx | 0 / 2 / **14** |
| fan-out mediana / p90 / máx | 0 / 2 / **11** |
| Ciclos (SCC > 1) | **1** |

### ¿Módulos-dios? No

El fan-in máximo es 14 sobre 369 módulos: el módulo más importado del sistema
llega al **3,8%** de sus pares. No hay dios porque no hay religión — casi nadie
importa a nadie.

| Núcleo de facto | fan-in |
|---|---:|
| `paths` | 14 |
| `time_utils` | 12 |
| `metric_event` | 10 |
| `dispatch` | 9 |
| `config_loader` | 8 |
| `model_catalog` | 8 |
| `engram_http_client` | 7 |

Ese es todo el núcleo compartido: siete módulos de utilidad. No existe una capa de
dominio que otros construyan encima.

### Fan-out desmedido: no

Máximo `dispatch` con 11. Nadie orquesta a muchos porque no hay a quién orquestar.

### El único ciclo

`model_router` ↔ `dispatch_model_advisor`, y está **gestionado a mano con imports
diferidos dentro de funciones** para que no explote a nivel de módulo:

- `cos_lib/model_router.py:384` → `from cos_lib.dispatch_model_advisor import classify_task_type, _TASK_MODEL_MAP` (dentro de una función, e importa un privado ajeno `_TASK_MODEL_MAP`)
- `cos_lib/dispatch_model_advisor.py:371` → `from cos_lib.model_router import get_consequence_override` (dentro de una función)

Un ciclo que se resuelve difiriendo imports y cruzando un símbolo privado es la
señal de que el corte de responsabilidad entre "enrutar modelo" y "aconsejar
modelo" no cierra. Es el único punto del grafo donde hay acoplamiento real.

### Estructura de directorios

`cos_lib/` es **plano**: 369 `.py` sin subpaquetes propios. Las tres únicas entradas
de directorio son symlinks que apuntan afuera:

- `cos_lib/harness_adapter` → `packages/agent-lifecycle/lib/harness_adapter`
- `cos_lib/event_projections` → `packages/agent-lifecycle/lib/event_projections`
- `cos_lib/providers` → `packages/llm-providers/lib`

No hay jerarquía que exprese capas. El nombre del archivo es la única taxonomía.

---

## 3. Vitalidad: código muerto real

Criterio: no "sin referencias en grep" sino **nivel de evidencia de ejecución**.
Se descartan como consumidores los manifests (inventarios), los reportes
autogenerados y los tests, que no son camino de ejecución.

| Clase | Módulos | % | Qué significa |
|---|---:|---:|---|
| **vivo** | 285 | 77% | lo importa otro módulo, un script, un hook registrado, CI, Make o un binario |
| **solo-tests** | 40 | 11% | únicamente lo importan tests — muerto en producción |
| **solo-registro** | 15 | 4% | solo aparece en manifests/config: inventariado, no ejecutado |
| **solo-exposición** | 14 | 4% | solo lo ofrece un skill o un adapter `.ai/` |
| **solo-hook-no-registrado** | 13 | 4% | lo llama un hook que **no está en `.claude/settings.json`** |
| **huérfano** | 2 | 1% | nadie, en ningún lado |

Comando: `python3 reach2.py .` (§8.2), campo `coslib_nivel`.

**Muerto en la práctica: 69 módulos (19%)** — la suma de solo-tests, solo-registro,
solo-exposición y huérfanos. Los 13 "solo-hook-no-registrado" dependen de una
decisión que está en la porción de hooks: si el hook nunca se registra, son muertos
también; ahí llegan a 82 (22%).

Huérfanos absolutos, por si se quieren mirar primero: `auto_executor`,
`return_contract_validator` (medidos sin ninguna referencia en ningún archivo del repo).

---

## 4. Los 742 scripts

### Primero: el número

`find scripts -type f` da **1.348**, pero 610 son `.pyc` no trackeados. Trackeados
son **742**: 298 sin extensión (con shebang), 287 `.py`, 153 `.sh`, 4 otros.
De los que tienen shebang de shell, 341 son bash.

### Alcanzabilidad, por nivel de evidencia

| Nivel | Scripts | % |
|---|---:|---:|
| **N1 — ejecución** (invocado con path desde CI, Make, hook registrado, otro script o código) | **432** | 58% |
| **N2 — exposición** (solo lo ofrece un skill o un adapter `.ai/`) | 153 | 21% |
| **N3 — registro** (solo existe en manifests: nada lo invoca) | **155** | 21% |
| N5 — solo tests | 2 | 0% |
| N6 — huérfano | **0** | 0% |

Cero huérfanos: todo script está al menos inventariado. El problema no es abandono,
es inventario sin uso.

### De dónde viene la evidencia de los N1

| Invocador | Scripts |
|---|---:|
| otro script | 354 |
| código Python | 81 |
| hook **registrado** | 61 |
| CI (`.github/`) | 42 |
| binario (`cmd/`, `bin/`) | 25 |
| Makefile | 22 |

Matiz que importa: **237 de los 432 N1 tienen como único invocador ejecutable otro
script**. Y solo **62 scripts en total son tocados por CI o Makefile** — el resto de
la cadena se sostiene entre scripts que se llaman entre sí, sin una raíz automatizada
que garantice que alguna vez corre.

### Agrupados por función (rol declarado por el propio ledger del repo)

`docs/06-Daily/reports/primitive-readiness-ledger-scripts-latest.json` ya clasifica
741 de los 742 (falta `scripts/okf-schema.json`, que no es script). Cruzo ese rol
declarado contra mi nivel de evidencia — ese cruce es el aporte:

| Rol declarado | Total | N1 ejecuta | N2 expone | **N3 nadie ejecuta** |
|---|---:|---:|---:|---:|
| maintainer-tool | 329 | 198 | 13 | **117** |
| agentic-primitive | 273 | 163 | 110 | **0** |
| lab | 98 | 60 | 23 | 14 |
| migration-only | 15 | 3 | 0 | **12** |
| driver-specific | 14 | 7 | 2 | 5 |
| archive | 12 | 0 | 5 | 7 |

Dos lecturas, una buena y una mala:

- **Buena, y hay que decirla**: los 273 `agentic-primitive` —el producto— tienen
  todos evidencia de ejecución o exposición. **Ninguno cae en N3.** La superficie que
  se le ofrece al usuario está viva.
- **Mala**: la acumulación está en `maintainer-tool`: **117 herramientas de mantenedor
  que nadie invoca**, más 12 `migration-only` (migraciones de un solo uso ya pasado
  que nunca se archivaron) y 7 ya marcados `archive` que siguen en `scripts/`.

### El espejismo de los 155 N3

Los 155 aparecen **los 155** en un doc, **los 155** en un manifest y **154** en un
test. Parece cobertura; no lo es:

- Los "docs" son reportes autogenerados: `primitive-readiness-ledger-scripts-latest`
  los menciona a los 155 porque es el ledger que los lista.
- El test que más los toca es `tests/red_team/portability/test_os_only_scope_family.py`,
  que menciona 121 de los 155: es un test de inventario, no de comportamiento.
- **50 de los 155 tienen como único test uno de inventario/portabilidad.** Los otros
  105 sí tienen al menos un test específico — se testea el script que nadie corre.

---

## 5. Duplicación de mecanismo

Criterio aplicado a cada familia: *¿un cambio en uno obligaría a tocar el otro?*
Si no, es coincidencia y se deja anotada.

### 5.1 Resolución de la raíz del proyecto — **coincidencia parcialmente documentada**

| Técnica | Archivos |
|---|---:|
| `Path(__file__).parents[N]` | **165** |
| variable de entorno | 44 |
| `cos_lib.paths` (el canónico) | 16 |
| `git rev-parse --show-toplevel` | 8 |

`cos_lib/paths.py:4-24` **ya documenta la taxonomía**: define el Patrón A como
canónico y declara que los patrones A′, C y D *"intentionally differ from Pattern A
and must NOT be migrated"*, nombrando los call-sites. Y el código lo respeta: hay
comentarios `NOTE: custom resolution — differs from cos_lib.paths.project_root()`
en `model_router.py:311` (A′), `queue_drainer.py:347` (C) y `telemetry.py:60` (D).

**Veredicto: no es deuda, es coincidencia con motivo escrito.** Es la mejor práctica
que encontré en el repo. El problema es de alcance: la taxonomía cubre ~13 call-sites
y hay **165 que resuelven root por su cuenta sin estar clasificados**. La decisión
existe; la cobertura de la decisión, no.

### 5.2 Lectura de `cognitive-os.yaml` — **deuda**

| | Archivos |
|---|---:|
| Delegan en `cos_lib.config_loader` (o solo lo nombran) | 26 |
| **Parsean el YAML por su cuenta** (`yaml.safe_load` propio) | **51** |

`config_loader.py` son 204 LOC y expone `load_structured()`, que devuelve el
documento entero: los 51 podrían usarlo. Un cambio en la ubicación del archivo, en
el orden de precedencia o en el manejo de ausencia obliga a tocar los 51.
**Es deuda real.**

### 5.3 Lectura de JSONL de telemetría — **deuda**

| | Archivos |
|---|---:|
| **Parseo manual línea a línea** | **103** |
| Helper `read_jsonl`/`iter_jsonl` | 20 |

103 sitios reimplementan el mismo bucle sobre los mismos archivos de telemetría.
Un cambio de formato (compresión, rotación, línea corrupta) obliga a tocar 103.
**Es deuda real**, y además es la superficie donde más aparece el patrón de falla
silenciosa de la §6.

### 5.4 Frontmatter — **deuda**

16 módulos implementan su propio split de `---`; **1 solo delega** en un parser
canónico (`scripts/primitive_structure_standardizer.py`). Entre los 16 están
`skill_router`, `rule_router`, `pattern_detector`, `product_answer`. Los skills y
rules son un formato de producto: si cambia la convención del frontmatter, hay que
tocar 16 lugares y ninguno es la autoridad. **Deuda real.**

### 5.5 Locks — **los dos esquemas del encargo, confirmados**

| Mecanismo | Módulos |
|---|---:|
| `fcntl.flock` **+** lockfile/`O_EXCL` | 22 |
| solo lockfile/`O_EXCL` | 15 |
| solo `fcntl.flock` | 1 (`event_bus`) |

Hay dos esquemas compitiendo y un grupo que usa los dos a la vez. **Si dos procesos
coordinan sobre el mismo recurso usando esquemas distintos, no se excluyen entre sí**
— un `flock` no ve un lockfile `O_EXCL` y viceversa. Para decidir si es deuda o
coincidencia hace falta saber si los conjuntos protegen recursos compartidos; eso no
lo resuelve el análisis estático y queda como **la pregunta abierta más riesgosa de
esta auditoría**. `cos_lib/event_bus.py`, con `flock` puro frente a 15 módulos con
lockfile, es el candidato más probable a incompatibilidad real.

### 5.6 Clientes de Engram — **deuda**

| Vía | Módulos |
|---|---:|
| **HTTP/subprocess propio, sin cliente** | **28** |
| `engram_http_client` | 7 |
| `engram_client` | 7 |
| `engram_lifecycle` | 2 |

Hay dos clientes canónicos y 28 módulos que hablan con el servicio por su cuenta.
Un cambio de endpoint, de auth o de manejo de timeout obliga a tocar 28 sitios que
el grafo de imports no muestra. **Deuda real.**

---

## 6. El patrón de falla, medido por AST

Un solo pase de `ast` sobre 3.148 archivos, **cero errores de parseo**.
Criterio de "silencioso": un `try` **todos** cuyos handlers contienen únicamente
`pass`, `...` o un literal.

### Python

| Métrica | `cos_lib/` (369 arch, 125.252 LOC) | `scripts/` (396 arch, 95.578 LOC) |
|---|---:|---:|
| `try` con **todos** los handlers silenciosos | **266** en 109 arch | 89 en 46 arch |
| — de esos, protegen un `import` (legítimo) | 36 en 23 arch | 3 en 3 arch |
| — **silencio real (no-import)** | **230** | **86** |
| `except:` desnudo | **0** | **0** |
| `except Exception` que solo loguea | 40 en 17 arch | 5 en 5 arch |
| `sys.exit(0)` explícito | 5 | 1 |
| TODO/FIXME/XXX | 79 en 9 arch | 9 en 7 arch |

**Cero `except:` desnudos en todo el código auditado** — eso es disciplina real y
merece decirse. El problema no es el except desnudo, es el `except <Algo>: pass`:
**316 bloques que se tragan un error sin dejar rastro**, de los cuales solo 39 son
guardas de import.

Concentración en `cos_lib` (silencio no-import):

| Módulo | `try` silenciosos |
|---|---:|
| `cos_lib/repo_analyzer.py` | 20 |
| `cos_lib/rate_limiter.py` | 11 |
| `cos_lib/symbiosis_monitor.py` | 7 |
| `cos_lib/homeostasis.py` | 7 |
| `cos_lib/auto_repair.py` | 6 |
| `cos_lib/agent_bus.py` | 6 |
| `cos_lib/tool_adoption_evaluator.py` | 5 |
| `cos_lib/stash_ops.py` | 5 |

Los nombres importan: `auto_repair`, `homeostasis`, `symbiosis_monitor` y
`rate_limiter` son los módulos cuyo trabajo es *detectar que algo anda mal*. Son los
que más silencio tienen.

### Shell (341 scripts bash en `scripts/`)

| Métrica | Ocurrencias | Archivos |
|---|---:|---:|
| `\|\| true` | **230** | 80 |
| `2>/dev/null` | 482 | 102 |
| `exit 0` explícito | 169 | 100 |
| `set -e` presente | — | 270 |
| `set -euo pipefail` | — | **269** |

Misma lectura ambivalente: **269 de 341 scripts (79%) arrancan con
`set -euo pipefail`** —disciplina alta— y después el mismo cuerpo de scripts
neutraliza esa disciplina 230 veces con `|| true`. La barandilla está puesta y
salteada en el mismo archivo.

### El gate de duplicación no suprime nada — **el hallazgo más accionable**

`manifests/python-helper-duplication-baseline.json` tiene 134 entradas y **todas
referencian rutas `lib/...`, un directorio que no existe**.

Cronología verificada:
- `877b80dd1` (2026-05-31): se genera el baseline, con rutas `lib/`.
- `785ced2f3` (2026-07-10): `feat(cos-lib): rename lib package to cos_lib`.
- El baseline **nunca se regeneró**.

El ratchet identifica findings por un hash de las rutas del par, así que ninguna de
las 134 entradas puede matchear una finding actual bajo `cos_lib/`. Medido:

```
baseline_findings: 134
current_findings:   32
new_findings:       32     <-- las 32, o sea 0 de 134 suprime algo
status:           fail
```

Consecuencias, las tres:
1. **El baseline no suprime nada**: 134 entradas, 0 aplicables. Es un supresor inerte.
2. **El gate está en fail permanente** desde el 2026-07-10, y por eso su rojo ya no
   informa nada.
3. `scripts/acc_pipeline.py:319` sigue pasando `--include lib` — un directorio
   inexistente — junto a `--include scripts`.

Atenuante: `acc_pipeline.py` **no está en `.github/workflows/` ni en el Makefile**,
así que ese fail no bloquea a nadie. Que es también el motivo por el que pudo estar
roto dos meses sin que se notara.

---

## 7. Salud básica

| Métrica | `cos_lib/` | `scripts/` |
|---|---:|---:|
| LOC mediana / p90 / máx | 280 / 657 / **2005** | 197 / 473 / **2051** |
| Funciones | 4.293 | 3.536 |
| Funciones > 100 LOC | 61 | 49 |
| Funciones > 200 LOC | 5 | 2 |
| Complejidad > 20 | 75 | 78 |
| Complejidad > 40 | 5 | 8 |
| **Imports rotos** | **0** | **0** |
| **Errores de parseo** | **0** | **0** |

Módulos más grandes: `scripts/cos_init.py` (2.051), `cos_lib/skill_router.py`
(2.005), `scripts/cos_work_inventory.py` (1.814), `cos_lib/routing_benchmark.py`
(1.704), `scripts/acc_pipeline.py` (1.560), `cos_lib/rate_limiter.py` (1.511).

### Funciones-monstruo

| Función | LOC | Complejidad |
|---|---:|---:|
| `cos_lib/dispatch.py:477 dispatch()` | 593 | **129** |
| `scripts/cos_init.py:1635 main()` | 412 | **88** |
| `scripts/primitive_lifecycle.py:132 validate_manifest()` | 111 | 62 |
| `scripts/agent-orchestration-boundary-audit.py:107 audit()` | 120 | 58 |
| `cos_lib/script_exposure_audit.py:113 classify_script()` | 147 | 55 |
| `scripts/cos_flow_register.py:82 validate_contract()` | 112 | 54 |
| `cos_lib/claude_executor.py:430 run()` | 251 | 41 |

`dispatch()` con complejidad ciclomática **129 en 593 líneas** es el peor punto del
repo por un margen amplio: son ~129 caminos independientes en una sola función, y es
la función que decide a qué proveedor va cada llamada — o sea, la ruta caliente.

Falso positivo que conviene descartar de entrada:
`cos_lib/skill_router.py:574 _build_hand_coded_routing_table()` tiene **977 LOC pero
complejidad 1**: es una tabla literal, no lógica. Grande, no compleja.

TODOs concentrados en pocos lugares: `project_scaffolder.py` (35), `ops_runbook.py`
(25), `domain_model.py` (7).

---

## 8. Los scripts (evidencia ejecutable)

Los tres se corren desde la raíz del repo. Son read-only salvo que escriben su JSON
a stdout.

### 8.1 `arqaudit.py` — grafo, patrón de falla y salud (un solo pase AST)

```python
#!/usr/bin/env python3
"""Auditoria de arquitectura read-only sobre cos_lib/ y scripts/.
Un solo proceso, un solo pase de AST sobre todos los .py del repo.
Uso: python3 arqaudit.py <repo_root>   (imprime JSON en stdout)
"""
import ast, json, os, subprocess, sys
from collections import defaultdict

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")

def tracked(prefix=None):
    cmd = ["git", "-C", ROOT, "ls-files"] + ([prefix] if prefix else [])
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.split("\n")
    return [p for p in out if p]

# ---------- inventario ----------
# cos_lib: dedup por realpath (symlink y destino son UNO)
coslib_files, seen_real = {}, {}
for rel in tracked("cos_lib"):
    if not rel.endswith(".py"):
        continue
    ab = os.path.join(ROOT, rel)
    real = os.path.realpath(ab)
    mod = os.path.basename(rel)[:-3]
    coslib_files[mod] = {"rel": rel, "real": real,
                         "symlink": os.path.islink(ab),
                         "target": os.path.relpath(real, ROOT) if os.path.islink(ab) else rel}
    seen_real.setdefault(real, []).append(mod)

# todos los .py del repo + scripts sin extension con shebang python
allpy = {}
for rel in tracked():
    ab = os.path.join(ROOT, rel)
    if not os.path.isfile(ab):
        continue
    if rel.endswith(".py"):
        allpy[rel] = ab
    elif rel.startswith(("scripts/", "hooks/")) and "." not in os.path.basename(rel):
        try:
            with open(ab, "rb") as f:
                if b"python" in f.readline():
                    allpy[rel] = ab
        except OSError:
            pass

# ---------- pase AST unico ----------
COSLIB_MODS = set(coslib_files)
parse_err, files = {}, {}

class V(ast.NodeVisitor):
    """Recolecta metricas por archivo en un solo recorrido."""
    def __init__(self, src):
        self.src = src.split("\n")
        self.imports = set()          # modulos cos_lib importados
        self.try_all_pass = []        # try cuyos handlers son TODOS pass/...
        self.try_import_pass = []     # de esos, los que envuelven un import
        self.bare_except = []
        self.broad_log_only = []      # except Exception que solo loguea/print
        self.exit0 = []               # sys.exit(0) explicito
        self.funcs = []               # (nombre, linea, loc, complejidad)
        self.classes = 0
        self.subproc = 0

    # --- imports ---
    def visit_Import(self, n):
        for a in n.names:
            p = a.name.split(".")
            if p[0] == "cos_lib" and len(p) > 1:
                self.imports.add(p[1])
        self.generic_visit(n)

    def visit_ImportFrom(self, n):
        m = n.module or ""
        p = m.split(".")
        if p[0] == "cos_lib":
            if len(p) > 1:
                self.imports.add(p[1])       # from cos_lib.x import y
            else:
                for a in n.names:            # from cos_lib import x  <-- lib_closure lo pierde
                    if a.name in COSLIB_MODS:
                        self.imports.add(a.name)
        self.generic_visit(n)

    # --- manejo de errores ---
    def visit_Try(self, n):
        def silent(h):
            return all(isinstance(s, ast.Pass) or
                       (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
                       for s in h.body)
        def log_only(h):
            for s in h.body:
                if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call):
                    f = s.value.func
                    nm = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                    if nm in ("print", "debug", "info", "warning", "warn",
                              "error", "exception", "log", "write"):
                        continue
                    return False
                elif isinstance(s, ast.Pass):
                    continue
                else:
                    return False
            return True
        has_import = any(isinstance(x, (ast.Import, ast.ImportFrom))
                         for s in n.body for x in ast.walk(s))
        if n.handlers and all(silent(h) for h in n.handlers):
            self.try_all_pass.append(n.lineno)
            if has_import:
                self.try_import_pass.append(n.lineno)
        for h in n.handlers:
            t = h.type
            if t is None:
                self.bare_except.append(h.lineno)
            broad = (isinstance(t, ast.Name) and t.id in ("Exception", "BaseException")) or t is None
            if broad and not silent(h) and log_only(h):
                self.broad_log_only.append(h.lineno)
        self.generic_visit(n)

    def visit_Call(self, n):
        f = n.func
        nm = (f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")) or ""
        if nm == "exit" and isinstance(f, ast.Attribute) and getattr(f.value, "id", "") == "sys":
            if n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value in (0, None):
                self.exit0.append(n.lineno)
            elif not n.args:
                self.exit0.append(n.lineno)
        if nm in ("run", "check_output", "Popen", "call", "check_call"):
            self.subproc += 1
        self.generic_visit(n)

    def visit_ClassDef(self, n):
        self.classes += 1
        self.generic_visit(n)

    def _fn(self, n):
        end = getattr(n, "end_lineno", n.lineno)
        cx = 1
        for x in ast.walk(n):
            if isinstance(x, (ast.If, ast.For, ast.While, ast.ExceptHandler,
                              ast.With, ast.Assert, ast.comprehension)):
                cx += 1
            elif isinstance(x, ast.BoolOp):
                cx += len(x.values) - 1
        self.funcs.append((n.name, n.lineno, end - n.lineno + 1, cx))
        self.generic_visit(n)
    visit_FunctionDef = _fn
    visit_AsyncFunctionDef = _fn

for rel, ab in sorted(allpy.items()):
    try:
        src = open(ab, encoding="utf-8", errors="replace").read()
        tree = ast.parse(src)
    except SyntaxError as e:
        parse_err[rel] = f"{type(e).__name__}: {e}"
        continue
    v = V(src)
    v.visit(tree)
    lines = src.split("\n")
    files[rel] = {
        "loc": len(lines), "imports": sorted(v.imports),
        "try_all_pass": len(v.try_all_pass), "try_import_pass": len(v.try_import_pass),
        "bare_except": len(v.bare_except), "broad_log_only": len(v.broad_log_only),
        "exit0": len(v.exit0), "funcs": v.funcs, "classes": v.classes,
        "subproc": v.subproc,
        "todo": sum(1 for l in lines if "TODO" in l or "FIXME" in l or "XXX" in l),
        "has_main": "__main__" in src, "symlink": os.path.islink(ab),
    }

# ---------- grafo intra-cos_lib ----------
def modkey(rel):
    if rel.startswith("cos_lib/") and rel.endswith(".py"):
        return os.path.basename(rel)[:-3]
    real = os.path.realpath(os.path.join(ROOT, rel))
    for m, d in coslib_files.items():
        if d["real"] == real:
            return m
    return None

graph = defaultdict(set)
for rel, d in files.items():
    k = modkey(rel)
    if k is None:
        continue
    for t in d["imports"]:
        if t in COSLIB_MODS and t != k:
            graph[k].add(t)
for m in COSLIB_MODS:
    graph.setdefault(m, set())

fan_out = {m: len(graph[m]) for m in graph}
fan_in = defaultdict(int)
for m, ts in graph.items():
    for t in ts:
        fan_in[t] += 1

# Tarjan SCC (iterativo)
idx, low, onstk, stk, comps, counter = {}, {}, set(), [], [], [0]
for root in sorted(graph):
    if root in idx:
        continue
    work = [(root, iter(sorted(graph[root])))]
    idx[root] = low[root] = counter[0]; counter[0] += 1
    stk.append(root); onstk.add(root)
    while work:
        node, it = work[-1]
        adv = False
        for w in it:
            if w not in idx:
                idx[w] = low[w] = counter[0]; counter[0] += 1
                stk.append(w); onstk.add(w)
                work.append((w, iter(sorted(graph[w])))); adv = True
                break
            elif w in onstk:
                low[node] = min(low[node], idx[w])
        if adv:
            continue
        work.pop()
        if work:
            low[work[-1][0]] = min(low[work[-1][0]], low[node])
        if low[node] == idx[node]:
            c = []
            while True:
                w = stk.pop(); onstk.discard(w); c.append(w)
                if w == node:
                    break
            if len(c) > 1 or node in graph[node]:
                comps.append(sorted(c))

print(json.dumps({
    "coslib_total": len(COSLIB_MODS),
    "coslib_symlinks": sum(1 for d in coslib_files.values() if d["symlink"]),
    "realpath_dupes": {k: v for k, v in seen_real.items() if len(v) > 1},
    "py_analizados": len(files), "parse_err": parse_err,
    "cycles": comps, "fan_out": fan_out, "fan_in": dict(fan_in), "files": files,
}))
```

### 8.2 `reach2.py` — alcanzabilidad por nivel de evidencia

Distingue **referencia en doc** de **camino de ejecución**. La v1 (substring suelto)
daba 99% de entrypoints; el falso positivo eran los manifests, uno de los cuales
menciona 448 scripts porque es un inventario. Esta versión usa patrones de
invocación y clasifica al referente.

```python
#!/usr/bin/env python3
"""Alcanzabilidad: niveles de evidencia, no substring suelto.
N1 EJECUCION  = invocado con path desde hook registrado / CI / Makefile / otro script / codigo
N2 EXPOSICION = ofrecido por un skill o un adapter de harness (.ai/)
N3 REGISTRO   = solo aparece en manifests/ (inventario, no ejecucion)
N4 DOC / N5 TEST / N6 HUERFANO
Uso: python3 reach2.py <repo_root>   (JSON a stdout)
"""
import json, os, re, subprocess, sys
from collections import defaultdict, deque

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
def git(*a):
    return [p for p in subprocess.run(["git", "-C", ROOT, *a],
            capture_output=True, text=True).stdout.split("\n") if p]

tracked = git("ls-files")
SKIP_EXT = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".ico",
            ".woff", ".woff2", ".ttf", ".so", ".dylib", ".db", ".jsonl", ".lock"}
text = {}
for rel in tracked:
    ab = os.path.join(ROOT, rel)
    if not os.path.isfile(ab) or os.path.splitext(rel)[1].lower() in SKIP_EXT:
        continue
    try:
        if os.path.getsize(ab) > 3_000_000:
            continue
        text[rel] = open(ab, encoding="utf-8", errors="replace").read()
    except OSError:
        continue

# hooks REGISTRADOS en el harness (un hook no registrado no ejecuta nada)
settings_blob = ""
for cand in (".claude/settings.json", ".claude/settings.local.json", "settings.json"):
    settings_blob += text.get(cand, "")
hooks_registrados = {rel for rel in tracked
                     if rel.startswith("hooks/") and os.path.basename(rel) in settings_blob}

def clase(rel):
    b = os.path.basename(rel)
    if rel.startswith("manifests/"): return "manifest"
    if rel.startswith(".ai/"): return "adapter"
    if rel.startswith("archive/") or "/_archived/" in rel or rel.startswith(("plans/", "checkpoints/")):
        return "archivo"
    if rel.startswith("tests/") or "/tests/" in rel or b.startswith("test_"): return "test"
    if "/skills/" in rel or rel.startswith(("skills/", "agents/")): return "skill"
    if rel.startswith("docs/") or rel.endswith((".md", ".mdx", ".rst", ".txt")): return "doc"
    if rel.startswith(".github/"): return "ci"
    if b in ("Makefile", "makefile") or rel.endswith(".mk"): return "make"
    if rel.startswith("hooks/") or "/hooks/" in rel:
        return "hook-reg" if rel in hooks_registrados else "hook-no-reg"
    if rel.startswith("scripts/") or "/scripts/" in rel: return "script"
    if rel.endswith(".py"): return "py"
    if rel.startswith(("cmd/", "bin/", "internal/", "pkg/", "crates/", "src/")) or rel.endswith(".go"):
        return "bin"
    if rel.endswith((".yaml", ".yml", ".json", ".toml")): return "config"
    return "otro"

scripts = [r for r in git("ls-files", "scripts") if os.path.isfile(os.path.join(ROOT, r))]

def patrones(s):
    """Patron de INVOCACION, no de mera mencion."""
    b = os.path.basename(s); stem = os.path.splitext(b)[0]; eb = re.escape(b)
    pats = [rf"(?:^|[\s'\"`=|(&;])(?:[\w./$'\"{{}}-]*/)?{eb}(?:$|[\s'\"`)|&;:,])",
            rf"scripts/{eb}"]
    if b.endswith(".py"):
        pats.append(rf"scripts\.{re.escape(stem)}\b")
        pats.append(rf"from\s+scripts\s+import\s+[^\n]*\b{re.escape(stem)}\b")
    return re.compile("|".join(pats), re.M)

EJEC = {"ci", "make", "hook-reg", "script", "bin", "py"}
evid = {}
for s in scripts:
    rx = patrones(s); base = os.path.basename(s); hits = defaultdict(set)
    for rel, txt in text.items():
        if rel == s or base not in txt:      # prefiltro barato
            continue
        if rx.search(txt):
            hits[clase(rel)].add(rel)
    evid[s] = hits

directo = {s for s in scripts if any(k in EJEC for k in evid[s])}
for s in scripts:
    if os.path.basename(s) in settings_blob:
        directo.add(s)

s_edges = defaultdict(set)
for s in scripts:
    for r in evid[s].get("script", ()):
        s_edges[r].add(s)
alc, q = set(directo), deque(directo)
while q:
    for nxt in s_edges.get(q.popleft(), ()):
        if nxt not in alc:
            alc.add(nxt); q.append(nxt)

def nivel(s):
    h = evid[s]
    if s in directo: return "N1-ejecucion"
    if s in alc: return "N1-ejecucion-transitiva"
    if h.get("skill") or h.get("adapter"): return "N2-exposicion"
    if h.get("manifest") or h.get("config"): return "N3-registro"
    if h.get("test"): return "N5-test"
    if h.get("doc") or h.get("archivo"): return "N4-doc"
    return "N6-huerfano"

# --- vitalidad de cos_lib con los mismos niveles ---
coslib = {os.path.basename(r)[:-3]: r for r in git("ls-files", "cos_lib") if r.endswith(".py")}
cl = {}
for m in coslib:
    rx = re.compile(rf"cos_lib\.{re.escape(m)}\b|cos_lib/{re.escape(m)}\.py|"
                    rf"from\s+cos_lib\s+import\s+[^\n]*\b{re.escape(m)}\b", re.M)
    hits = defaultdict(set)
    for rel, txt in text.items():
        if rel.startswith("cos_lib/") and os.path.basename(rel)[:-3] == m:
            continue
        if m not in txt:
            continue
        if rx.search(txt):
            k = clase(rel)
            if rel.startswith("cos_lib/") or (rel.startswith("packages/") and rel.endswith(".py")):
                k = "lib"
            hits[k].add(rel)
    cl[m] = hits

def nivel_lib(m):
    h = cl[m]
    prod = {"lib", "script", "hook-reg", "ci", "make", "bin", "py"}
    if any(k in prod for k in h): return "vivo"
    if h.get("hook-no-reg"): return "solo-hook-no-registrado"
    if h.get("skill") or h.get("adapter"): return "solo-exposicion"
    if h.get("manifest") or h.get("config"): return "solo-registro"
    if h.get("test"): return "solo-tests"
    if h.get("doc") or h.get("archivo"): return "solo-doc"
    return "huerfano"

print(json.dumps({
    "n_scripts": len(scripts), "hooks_registrados": len(hooks_registrados),
    "niveles": {s: nivel(s) for s in scripts},
    "evid": {s: {k: sorted(v) for k, v in h.items()} for s, h in evid.items()},
    "coslib_nivel": {m: nivel_lib(m) for m in coslib},
}))
```

Cruce con el ledger de roles (produce la tabla de §4):

```bash
python3 reach2.py . > /tmp/reach2.json
python3 - <<'PY'
import json
from collections import Counter, defaultdict
niv = json.load(open('/tmp/reach2.json'))['niveles']
led = json.load(open('docs/06-Daily/reports/primitive-readiness-ledger-scripts-latest.json'))
rol = {s['path']: s['role'] for s in led['scripts']}
t = defaultdict(Counter)
for s, l in niv.items():
    t[rol.get(s, '(sin-rol)')][l] += 1
for r, c in sorted(t.items(), key=lambda x: -sum(x[1].values())):
    print(f"{r:20s} tot={sum(c.values()):4d}  N1={c['N1-ejecucion']:4d}  "
          f"N2={c['N2-exposicion']:4d}  N3={c['N3-registro']:4d}")
PY
```

### 8.3 `dup.py` — duplicación de mecanismo

```python
#!/usr/bin/env python3
"""Duplicacion de mecanismo en cos_lib/ y scripts/: misma responsabilidad, dos veces.
Mide con AST quien delega en el helper canonico y quien reimplementa.
Uso: python3 dup.py <repo_root>
"""
import ast, os, re, subprocess, sys
from collections import defaultdict

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
def git(*a):
    return [p for p in subprocess.run(["git", "-C", ROOT, *a],
            capture_output=True, text=True).stdout.split("\n") if p]

targets = [r for r in git("ls-files", "cos_lib") + git("ls-files", "scripts")
           if r.endswith(".py") and os.path.isfile(os.path.join(ROOT, r))]
src, trees = {}, {}
for r in targets:
    try:
        s = open(os.path.join(ROOT, r), encoding="utf-8", errors="replace").read()
        trees[r] = ast.parse(s); src[r] = s
    except (OSError, SyntaxError):
        pass

def imports_de(r):
    out = set()
    for n in ast.walk(trees[r]):
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("cos_lib"):
            p = (n.module or "").split(".")
            out.add(p[1]) if len(p) > 1 else out.update(a.name for a in n.names)
        elif isinstance(n, ast.Import):
            for a in n.names:
                p = a.name.split(".")
                if p[0] == "cos_lib" and len(p) > 1:
                    out.add(p[1])
    return out

# 1. lectura de cognitive-os.yaml
propios, delega = [], []
for r in targets:
    if "cognitive-os.yaml" not in src[r]:
        continue
    if "config_loader" in imports_de(r):
        delega.append(r)
    elif re.search(r"yaml\.safe_load|yaml\.load|tomllib\.load|json\.load", src[r]):
        propios.append(r)
    else:
        delega.append(r)
print(f"config: delegan={len(delega)}  parsean por su cuenta={len(propios)}")

# 2. resolucion de la raiz del proyecto
pat = {"Path(__file__).parents[N]": re.compile(r"Path\(__file__\)\.(resolve\(\)\.)?parents?\["),
       "git rev-parse": re.compile(r"rev-parse.*--show-toplevel"),
       "env var": re.compile(r"COS_(PROJECT|REPO)_ROOT|CLAUDE_PROJECT_DIR")}
root_impl = defaultdict(list)
for r in targets:
    tec = [k for k, rx in pat.items() if rx.search(src[r])]
    if "paths" in imports_de(r):
        tec.append("cos_lib.paths")
    if tec:
        root_impl[", ".join(sorted(tec))].append(r)
for k, v in sorted(root_impl.items(), key=lambda x: -len(x[1])):
    print(f"root [{k}]: {len(v)}")

# 3. frontmatter
CANON = {"primitive_parser", "skill_router", "ref_key_loader", "rule_router"}
fm_prop, fm_deleg = [], []
for r in targets:
    if not re.search(r"frontmatter|front_matter|^---\s*$", src[r], re.M):
        continue
    if imports_de(r) & CANON:
        fm_deleg.append(r)
    elif re.search(r"split\(\s*['\"]---|startswith\(\s*['\"]---|re\.(match|search|split)\([^)]*---", src[r]):
        fm_prop.append(r)
print(f"frontmatter: delegan={len(fm_deleg)}  propio={len(fm_prop)}")

# 4. locks
lock_tec = defaultdict(list)
for r in targets:
    t = []
    if "fcntl" in src[r]: t.append("fcntl.flock")
    if re.search(r"O_EXCL|mkdir.*lock|\.lock['\"]", src[r]): t.append("lockfile/O_EXCL")
    if re.search(r"threading\.(Lock|RLock)", src[r]): t.append("threading.Lock")
    if t: lock_tec[", ".join(sorted(t))].append(r)
for k, v in sorted(lock_tec.items(), key=lambda x: -len(x[1])):
    print(f"lock [{k}]: {len(v)}")

# 5. clientes engram
CLIENTES = {"engram_client", "engram_http_client", "engram_lifecycle", "engram_sync"}
eng = defaultdict(list)
for r in targets:
    im = imports_de(r)
    for c in CLIENTES & im:
        eng[c].append(r)
    if "engram" in src[r].lower() and not (im & CLIENTES) \
       and re.search(r"requests\.(get|post)|urllib|httpx|subprocess", src[r]):
        eng["HTTP/subproc propio (sin cliente)"].append(r)
for k, v in sorted(eng.items(), key=lambda x: -len(x[1])):
    print(f"engram [{k}]: {len(v)}")

# 6. lectura de JSONL
jsonl = defaultdict(list)
for r in targets:
    if ".jsonl" not in src[r]:
        continue
    if re.search(r"json\.loads\([^)]*\)\s*for|for .* in .*readlines|\.splitlines\(\)", src[r]):
        jsonl["parseo manual linea a linea"].append(r)
    elif re.search(r"read_jsonl|iter_jsonl|load_jsonl", src[r]):
        jsonl["helper read_jsonl/iter_jsonl"].append(r)
for k, v in sorted(jsonl.items(), key=lambda x: -len(x[1])):
    print(f"jsonl [{k}]: {len(v)}")
```

### 8.4 El gate de duplicación roto

```bash
# 1. El baseline apunta a un directorio que no existe
python3 -c "import json; d=json.load(open('manifests/python-helper-duplication-baseline.json')); \
print(d['summary']['by_common_home']); print(d['entries'][0]['pair_key'])"
#   {'lib/': 134}
#   lib/adaptive_profile.py::_now_iso :: lib/dynamic_tool_creator.py::_timestamp
git ls-files lib | wc -l          # -> 0

# 2. Cronologia
git log --oneline -1 --format='%h %ad %s' --date=short -- manifests/python-helper-duplication-baseline.json
#   877b80dd1 2026-05-31 Add Python helper duplication ratchet
git log --oneline --format='%h %ad %s' --date=short -- cos_lib | grep -i rename | head -1
#   785ced2f3 2026-07-10 feat(cos-lib): rename lib package to cos_lib (U1 resolution)

# 3. El ratchet: 134 en el baseline, 0 aplicables (escribe solo al scratchpad)
python3 scripts/primitive_duplication_audit.py --project-root . \
  --include scripts --include lib --min-tokens 60 --threshold 0.86 \
  --primitive-threshold 0.75 \
  --baseline manifests/python-helper-duplication-baseline.json \
  --json-out /tmp/dupA.json --markdown /tmp/dupA.md --fail-on-new
#   exit 1 — baseline_findings:134  current_findings:32  new_findings:32  status:fail

# 4. Y el pipeline que lo corre no esta en CI ni en el Makefile
grep -rn 'acc_pipeline' .github/ Makefile   # -> sin resultados
```

---

## 9. Correcciones a las premisas del encargo

1. **«369 módulos, ~22% symlinks»** — 369 es correcto; los symlinks son **70 = 19%**,
   no 22%. Más importante: **los 369 realpaths son únicos** (`realpath_dupes: 0`), o
   sea que dentro de `cos_lib` no hay ningún symlink apuntando a otro archivo de
   `cos_lib`. Los 70 destinos están todos en `packages/*/lib/` — fuera de la porción.
   La advertencia de `readlink -f` era pertinente pero no había doble conteo que
   corregir. Concentración: `packages/agent-lifecycle` recibe 21 de los 70.

2. **«`lib/` no existe»** — **confirmado** (`git ls-files lib | wc -l` → 0). Y no hay
   ni un `from lib.` ni un `import lib.` en `cos_lib`, `scripts` ni `hooks`. Pero el
   directorio fantasma sí dejó daño: el baseline de duplicación y
   `acc_pipeline.py:319` siguen apuntando ahí (§6).

3. **«61 `try` con import silencioso, en 42 archivos»** — la cifra es **repo-wide, no
   de `cos_lib`**. Mido **63 en 42 archivos** (el 42 coincide exacto; la diferencia de
   2 es de criterio: cuento también `...` y literal como handler silencioso). El
   reparto: `cos_lib` 36, `packages` 16, `hooks` 3, `mcp-server` 3, `scripts` 3,
   resto 2. **En `cos_lib` son 36, no 61.** Extendido a todos los `try`: **266 en
   `cos_lib` y 89 en `scripts`**, de los cuales solo 39 son guardas de import.

4. **«`scripts/lib_closure.py:92-96` descarta `from cos_lib import x`; 6 módulos, 16
   usos»** — **el bug está confirmado**: la rama `ImportFrom` (líneas 92-96) exige
   `parts[0]=="cos_lib" and len(parts)>1`, nunca lee `node.names`. Y no hay backstop:
   el regex de seeding `_LIB_IMPORT_RE` (línea 39) también exige `from cos_lib\.` con
   punto, así que tampoco captura la forma sin punto.

   **Pero el impacto es cero hoy, no 16 usos.** `lib_closure` opera sobre **hooks**
   (`extract_lib_modules_from_hook`, `compute_closure(hook_paths, ...)`), y en
   `hooks/` hay **0 ocurrencias** de `from cos_lib import X`:
   `git grep -cE 'from cos_lib import ' -- hooks` → 0. Repo-wide hay 31 ocurrencias,
   de las cuales 15 son tests y varias son fixtures (`x`, `y`, `baz`); en código de
   producción son **13** (11 en `cos_lib`, 2 en `scripts`), ninguna en el dominio del
   script. **Es un bug latente, no activo**: se dispara el día que un hook use esa
   forma de import, y el fallo sería silencioso (un módulo que falta en la clausura
   proyectada).

5. **«742 scripts»** — correcto para archivos **trackeados**. En disco hay 1.348
   porque 610 son `.pyc` no trackeados. Y ninguno de los 742 es huérfano: el 21% que
   nadie ejecuta está inventariado en manifests, que es otra cosa.

6. **«`cos_lib` es plano»** (premisa mía, corregida sobre la marcha) — los 369 `.py`
   sí son planos, pero hay **3 subpaquetes** que son symlinks a directorios de
   `packages/`: `harness_adapter`, `providers`, `event_projections`. Un chequeo de
   imports rotos que solo mire `.py` los reporta como faltantes; no lo están.

---

## 10. Fuera de mi porción

Cosas que crucé y pertenecen a otro juez:

- **Hooks**: hay **257 archivos en `hooks/` y 155 registrados** en
  `.claude/settings.json` — ~100 hooks no registrados. De ahí salen dos efectos que
  sí tocan mi porción: 13 módulos de `cos_lib` cuyo único consumidor es un hook no
  registrado, y 8 scripts en la misma situación (entre ellos
  `scripts/audit_adrs.py` y `scripts/check_entrypoint_adr_links.py`, llamados por
  `hooks/pre-commit-gate.sh`, que no está en `settings.json`).
- **`hooks/pre-commit-gate.sh`** no está registrado en el harness, pero existe un
  `.git/hooks/pre-commit` local **no versionado**: hay un camino de ejecución que no
  se ve en el repo y no es reproducible en otra máquina.
- **Tests**: `tests/red_team/portability/test_os_only_scope_family.py` menciona 121
  de los 155 scripts N3. Es un test de inventario que da apariencia de cobertura
  sobre código que nadie ejecuta — vale revisarlo desde la porción de tests.
- **CI**: `scripts/acc_pipeline.py` —que corre 20 auditorías, incluido el gate de
  duplicación— **no está en `.github/workflows/` ni en el Makefile**. Solo 62 de 742
  scripts son alcanzados por CI o Make.
- **Packages**: los 70 symlinks entrantes y los 3 subpaquetes hacen que `cos_lib`
  sea en parte una fachada sobre `packages/`. Quién es dueño de qué es decisión de
  esa porción.

---

## 11. Si hay que elegir por dónde empezar

Ordenado por relación entre daño y esfuerzo, sin prescribir el arreglo:

1. **El gate de duplicación lleva dos meses en fail con un baseline inerte** (§6).
   Es el único hallazgo donde un control de calidad está apagado sin que nadie lo
   sepa. Regenerar el baseline con las rutas reales y corregir `--include lib` es
   acotado; decidir si `acc_pipeline` entra a CI, no.
2. **Los dos esquemas de lock** (§5.5). Es el único hallazgo con riesgo de
   corrupción real, y el análisis estático no puede cerrarlo: hace falta saber qué
   recursos comparten `event_bus` y los 15 módulos de lockfile.
3. **`dispatch()`, complejidad 129 en 593 líneas** (§7), en la ruta caliente y en el
   único ciclo del grafo.
4. **117 `maintainer-tool` que nadie invoca, 12 `migration-only` ya pasadas y 7
   `archive` todavía en `scripts/`** (§4). Es el 19% del directorio y el ledger ya
   los tiene identificados por rol.
5. **316 `try` que se tragan errores sin dejar rastro**, concentrados en los módulos
   cuyo trabajo es detectar fallas (§6).
