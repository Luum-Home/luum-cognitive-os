# Juez de diseño — ¿cuál es el arreglo correcto? (scope en la proyección al consumidor)

Fecha: 2026-08-15 · Read-only · Repo: `luum-agent-os`

**Estado de la máquina al correr esto**: swap 36629 MiB / 37888 MiB (96.7%), load 16.57.
Degradación declarada: cero sub-agentes en paralelo, cero suites de tests, cero
corridas de `install.sh`. Todo lo medido sale de una proyección de descarte con
`scripts/cos_init.py` directo (que no hace `rm -rf` fuera de `.cognitive-os/`) y de
análisis estático. Comandos citados uno por uno.

---

## 1. Veredicto

**Opción (d): mover el contrato del call-site al árbol producido — un gate post-instalación
que corre sobre lo que quedó instalado, falla la instalación, y trae una allowlist nombrada
para lo que estructuralmente tiene que viajar.** Las guardas por call-site son la
remediación que ese gate obliga, no el contrato.

---

## 2. Fallo sobre la tensión: `both` correcto o verde barato

**Las dos, pero no en partes iguales: `both` quedó bien por casualidad, y el arreglo fue
verde barato por construcción.**

### El argumento "un paquete Python necesita su `__init__.py`" no sostiene el cambio

El call-site ya tiene la salida estructural escrita, 2 líneas abajo del `copy2`
(`scripts/cos_init.py:1887-1893`):

```python
    if not lib_init_file.exists():
        source_init = cos_source / "cos_lib" / "__init__.py"
        if source_init.is_file():
            shutil.copy2(str(source_init), str(lib_init_file))
        else:
            lib_init_file.write_text("", encoding="utf-8")
```

La rama `else` **ya sintetiza un `__init__.py` vacío**. El paquete importa igual. Es decir:
la necesidad estructural justifica *que exista un `__init__.py` en el destino*, no *que se
copie el archivo fuente*. Meter `scope_allows` ahí y caer al `write_text("")` cuando dé
`False` costaba una línea y no rompía ningún import. La premisa "si `cos_lib/` viaja, su
`__init__` tiene que viajar" es verdadera; la conclusión "por lo tanto hay que copiar *ese*
archivo" no se sigue.

### Lo que sí hace correcto a `both` es otra cosa, y es más débil

`cos_lib/__init__.py` pesa **52 bytes** y su contenido completo es:

```
# SCOPE: both
# Cognitive OS Python library modules
```

Dos comentarios. Cero código. No hay nada os-only adentro que proteger. La declaración
`os-only` no era "equivocada" en el sentido de clasificar mal un contenido sensible: era
**vacía de referente**, porque el archivo no tiene contenido que clasificar. Cambiarla a
`both` no empeora nada. Por eso digo *correcto por casualidad*: el resultado es defendible,
el razonamiento que lo produjo no.

### Por qué fue verde barato, con el recibo

El gate que estaba en rojo es
`tests/contracts/test_primitive_scope_governance.py:149`
`::test_default_consumer_projection_contains_no_os_only_markers`. Lo que mide, textual
(líneas 163-170):

```python
header = "\n".join(path.read_text(...).splitlines()[:8])
if re.search(r"\bSCOPE:\s*os-only\b", header):
    offenders.append(...)
```

**El gate mide el texto del marcador en las primeras 8 líneas de los archivos instalados.**
Editar el marcador de la línea 1 es literalmente la acción más corta que apaga ese rojo, y
no cambia un solo byte de lo que se instala. Eso es el verde barato de manual: el arreglo
redujo la medición, no el problema.

Y hay confirmación empírica, no retórica. El commit que hizo el cambio es `5ba9de934`,
"CLASS 3 — real bugs", y su propio mensaje describe las dos mitades:

> os-only cos_lib modules were projected into consumer installs because the closure walk
> had no SCOPE filter (scripts/cos_init.py); [...] cos_lib/__init__.py reclassified
> os-only -> both

Ese mismo commit **agregó** `scope_allows` al loop de la clausura (`cos_init.py:1909`) y
**dejó sin tocar** el `copy2` del `__init__.py` que está 18 líneas más arriba. La misma
mano, el mismo diff, dos call-sites hermanos: a uno le puso el filtro, al otro le cambió el
hecho.

### La prueba de que el mecanismo quedó intacto: hoy hay una fuga viva de la misma familia

`skills/cos-status/SKILL.md` declara en la línea 30:

```
<!-- SCOPE: os-only -->
```

y **se instala igual en un consumidor**. Motivo: `skill_scope_allows`
(`scripts/cos_init.py:328`) lee `lines[:8]`, no ve la línea 30, y cae al fallback legacy que
lee `audience:` del frontmatter — que dice `both`. El test de gobernanza tampoco la ve,
porque también lee 8 líneas.

Medido:

```
$ python3 scripts/cos_init.py --default --harness claude   # en dir descartable
$ grep -rlniE '(#|<!--)[[:space:]]*scope:[[:space:]]*os-only' <install>
.cognitive-os/skills/cos/cos-status/SKILL.md
```

Un mes después del "arreglo", un primitivo que declara `os-only` viaja al consumidor por
exactamente el mismo mecanismo — un marcador que la ruta de copiado no consulta. Eso, y no
la discusión sobre el `__init__.py`, es el fallo.

---

## 3. Call-sites de copiado que saltean el filtro

`scripts/cos_init.py` tiene **22** llamadas `shutil.copy2` / `shutil.copytree` que escriben
en el árbol del consumidor. **8 consultan el filtro. 14 no.** El encargo conocía 3.

| Archivo | Línea | Qué copia | Motivo escrito de saltear |
|---|---|---|---|
| `scripts/cos_init.py` | 388 | `install_rule()` — cualquier `rules/<n>.md` del boundary manifest | Ninguno. Comentario adyacente: "Byte-for-byte port — do NOT optimise the bash logic" |
| `scripts/cos_init.py` | 420 | `install_hook()` — cualquier `hooks/<n>.sh` del boundary manifest | Ninguno (mismo port literal del bash) |
| `scripts/cos_init.py` | 1431 | `scripts/provenance-scan`, `scripts/provenance_scan.py` | Ninguno |
| `scripts/cos_init.py` | 1439 | `manifests/provenance-scan.yaml` | Ninguno |
| `scripts/cos_init.py` | 1507 | `fixtures/so-impact/money-format-refactor/` (árbol entero) | Ninguno |
| `scripts/cos_init.py` | 1629 | `.claude/settings.json` (fallback sin `jq`) | Ninguno |
| `scripts/cos_init.py` | 1808 | reglas en modo `--full` — **acá sí hay guarda**, en 1805 (falso positivo de mi heurística AST, ver §7) | — |
| `scripts/cos_init.py` | 1822 | `rules/RULES-COMPACT.md` | Ninguno. El comentario dice "Always install RULES-COMPACT.md" |
| `scripts/cos_init.py` | 1849 | `hooks/_lib/` entero (rama `--full`) | Ninguno |
| `scripts/cos_init.py` | 1855 | `scripts/hook-timing-wrapper.sh` (rama `--full`) | Ninguno |
| `scripts/cos_init.py` | 1871 | `hooks/_lib/` entero (rama default) | Ninguno |
| `scripts/cos_init.py` | 1877 | `scripts/hook-timing-wrapper.sh` (rama default) | Ninguno |
| `scripts/cos_init.py` | 1891 | `cos_lib/__init__.py` | Ninguno |
| `scripts/cos_init.py` | 1963 | `skills/CATALOG.md` | Ninguno |

Con guarda (8): 476 (`skill_scope_allows`), 1456, 1464, 1484, 1526, 1839, 1912, 1978.

**Corrección sobre 1808**: mi detector AST lo marcó, pero la guarda está en 1805 dentro del
mismo `for`. Son **13** sin filtro real, no 14. Los otros 13 los verifiqué a mano leyendo
el bloque.

### Qué otros archivos pasan por el call-site del `__init__.py`

**Ninguno.** El call-site de 1891 copia exactamente un archivo, `cos_lib/__init__.py`, con
ruta literal. Su radio propio es 1. La premisa del encargo ("ése es el radio real del
agujero, no `__init__.py` solo") **no se sostiene para ese call-site**. El radio real está
en los otros 12, y el más grande de lejos es `hooks/_lib/` (líneas 1849/1871): un
`copytree` sin filtro de **38 archivos** hacia todo consumidor.

### Lo que hoy se filtra por esos huecos (medido, no inferido)

Instalación default en dir de descarte, harness claude, `COS_INSTALL_SCOPE=both`:

- **`__pycache__/` completo — 10 `.pyc`** entran al consumidor vía el `copytree` de
  `hooks/_lib/` (1871). Bytecode de dos versiones de Python (3.12 y 3.14) de la máquina del
  que empaquetó.
- **11 imports colgantes**: archivos instalados que hacen `import cos_lib.X` donde `X` no
  está en el árbol instalado. Se rompen en runtime, no en instalación.
- **1 skill os-only** (`cos-status`), por marcador fuera de ventana.
- **0 archivos con marcador `os-only` visible al parser** — o sea, el contrato *declarado*
  hoy se cumple; el contrato *pretendido* no.

Los 11 colgantes:

```
.cognitive-os/cos_lib/engram_client.py           -> cos_lib.engram_http_client
.cognitive-os/hooks/cos/_lib/common.sh           -> cos_lib.capability_levels
.cognitive-os/hooks/cos/_lib/context_budget_lib.sh -> cos_lib.context_budget
.cognitive-os/hooks/cos/_lib/dispatch_gate_check.py -> cos_lib.dispatch_model_advisor
.cognitive-os/hooks/cos/_lib/dispatch_gate_check.py -> cos_lib.record_completion
.cognitive-os/hooks/cos/_lib/recap_adapter.py    -> cos_lib.harness_environment
.cognitive-os/hooks/cos/_lib/register-bg.sh      -> cos_lib.process_registry
.cognitive-os/hooks/cos/_lib/session_init_helper.py -> cos_lib.project_profile_bootstrap
.cognitive-os/hooks/cos/_lib/session_init_helper.py -> cos_lib.user_model
.cognitive-os/hooks/cos/_lib/task_panel_adapter.py -> cos_lib.harness_environment
.cognitive-os/hooks/cos/_lib/timing.sh           -> cos_lib.performance_monitor
```

Dos causas distintas, y conviene no mezclarlas:

1. **`hooks/_lib/` viaja pero no siembra la clausura.** `projected_hook_paths` contiene solo
   los `.sh` de `hooks/`, nunca los `hooks/_lib/*.py`. Todo `cos_lib.*` alcanzable *solo*
   desde ahí se cae. Es el agujero que dejó muerto el circuit breaker.
2. **`from cos_lib import X` es invisible al caminante.** En
   `scripts/lib_closure.py:92-96`, la rama `ast.ImportFrom` hace
   `parts = node.module.split(".")` y exige `len(parts) > 1`. Para
   `from cos_lib import engram_http_client`, `node.module == "cos_lib"` → `len(parts) == 1`
   → se descarta, y **nunca se miran los `node.names`**. El regex de la línea 39 tampoco lo
   agarra porque exige el punto (`cos_lib\.`). Hay **14 ocurrencias** de esa forma en
   `cos_lib/`, `hooks/`, `scripts/`, alcanzando 6 módulos distintos
   (`compat_tomllib`, `cosd_grant`, `engram_client`, `engram_http_client`,
   `qwen_agent_loop`, `qwen_provider`).

### Latente vs vivo — no confundirlos

Los call-sites 388/420 (`install_rule`/`install_hook`) no filtran nada, pero **hoy no
filtran nada malo**: las 15 reglas y los 43 hooks que la instalación default proyecta son
todos `SCOPE: both` en el fuente. Igual que en el resto de este sistema, la protección es
una propiedad emergente del contenido, no un control. Un solo hook `os-only` agregado al
boundary manifest lo publica sin que nada se ponga rojo.

---

## 4. Opciones evaluadas

| # | Opción | Qué rompe | Qué cuesta | Qué modo de falla deja |
|---|---|---|---|---|
| **a** | `scope_allows` en los 13 call-sites | Nada hoy (todo lo que pasa por ahí es `both`). Riesgo real: el `copytree` de `hooks/_lib/` no tiene granularidad por archivo — filtrar ahí exige reescribirlo como walk archivo a archivo, que es donde se rompe algo | ~13 ediciones + reescribir 2 `copytree` + tests. Medio. Choca con el comentario "Byte-for-byte port — do NOT optimise the bash logic" en 388/420 | **El mismo.** El call-site nº 23 nace sin guarda y nada se entera. No toca ningún fail-open: sin marcador sigue viajando, marcador en línea 4 sigue invisible, `__pycache__` sigue viajando, los 11 colgantes siguen colgando |
| **b** | Excepción nombrada para lo que estructuralmente viaja (`__init__.py`, JSON sin comentarios) | Nada | Bajo: un manifest + leerlo. Pero como *única* medida es una lista que nadie obliga a consultar | Deja el problema entero: la excepción es la parte fácil, el enforcement es la que falta. **Sirve solo como escape hatch dentro de (c)/(d), no sola** |
| **c** | Mover el contrato al fuente: prohibir `os-only` en cualquier archivo alcanzable desde la proyección (gate de repo, tipo `scope_closure_gate.py`) | Obliga a resolver 4 `os_only_published` + 4 `scope_conflict` del baseline actual antes de poder mergear | Alto: el ratchet ya existe (4/5/4/0) pero descender esos números es trabajo de dependencias, no de instalador | Mide el **grafo de imports**, no el árbol producido. No ve `__pycache__`, no ve `cos-status`, no ve `settings.json`, no ve `RULES-COMPACT.md`. Modela lo que *debería* pasar; el bug vive en lo que *pasa* |
| **d** | **Contrato sobre el árbol producido**: proyectar a un dir temporal y afirmar invariantes sobre el resultado; falla la instalación; allowlist nombrada (= b) adentro | Falla hoy con 41 hallazgos reales. Hay que arreglarlos o allowlistearlos con motivo escrito antes de que quede verde | Medio-alto, pero **~70% ya está escrito y sin aplicar** en `/tmp/origin-fix/origin.patch` (ver §6) | Es agnóstico al call-site: no le importa cuántos haya ni cuál se olvide. El modo de falla que deja es el clásico del ratchet — alguien allowlistea en vez de arreglar. Se acota exigiendo motivo escrito por entrada y que el ratchet solo descienda, como ya hace `manifests/scope-closure-baseline.yaml` |

**Elegida: (d)**, con (a) como la remediación que (d) obliga y (b) como su escape hatch.

Razón en una línea: **(a) arregla los 13 call-sites que hay; (d) arregla la clase.** El
episodio del `__init__.py` no fue "se olvidaron un `if`", fue "no existe ningún lugar donde
el contrato se verifique una vez". Un contrato repartido en 22 sitios se rompe en el 23.

---

## 5. Radio de explosión de (d), medido

### Qué deja de viajar

| Deja de viajar | Cuántos | ¿Algo entregado depende de eso? |
|---|---|---|
| `hooks/_lib/__pycache__/*.pyc` | 10 archivos | **No.** Es bytecode de la máquina origen, de dos versiones de Python. Python lo regenera. Su única función hoy es leakear el layout de quien empaquetó |
| `skills/cos-status/` | 1 skill | **Sí, potencialmente.** Declara `os-only`, pero está expuesta como `/cos-status` y su `audience:` dice `both`. Antes de sacarla hay que resolver la contradicción en el fuente, no en el instalador. **Es una decisión de producto, no del gate** — el gate solo la vuelve visible |
| Nada más | — | Ningún archivo con marcador `os-only` visible al parser está hoy en el árbol proyectado (medido: 0) |

### Qué *empieza* a viajar

Los 11 imports colgantes se resuelven agregando `hooks/_lib/*.py` a la semilla de la
clausura y arreglando `_extract_lib_modules_ast`. Eso **agrega** módulos al consumidor, no
los saca. Ahí sí hay que mirar el scope de cada uno antes de que entre — y para eso ya
existe el gate:

```
$ python3 scripts/scope_closure_gate.py --profile default --json
closure_size: 65 · seed_hooks: 80
scope_conflict: 4   unmarked_published: 5   os_only_published: 4   marker_invisible: 0
(igual al baseline → exit 0)
```

Los 4 `os_only_published` (`gateway_selector`, `learning_pipeline`, `mlflow_bridge`,
`skill_archive`) **no** entran al consumidor: la guarda de `cos_init.py:1909` los veta. Pero
`record_completion` los importa y hoy tampoco entra `record_completion`. Al ampliar la
semilla, `record_completion` entra y sus imports diferidos a `learning_pipeline` /
`mlflow_bridge` se convierten en features silenciosamente apagadas — que es el estado que
ya describe el docstring del gate y que ya mató el circuit breaker. **Ampliar la clausura
sin resolver los 4 `scope_conflict` cambia un `ImportError` por un `except` que se traga
todo.** Ese es el riesgo real de (d), y es la razón por la que el gate tiene que correr
sobre el árbol producido *y* fallar, no advertir.

### Un latente que conviene mirar antes

`cos_lib/pattern_detector.py:15` declara `SCOPE: os-only` **en la línea 15**, invisible al
parser de 3 líneas. Hoy no está en la clausura. Es el único archivo de las superficies
gobernadas por `scope_allows` (`cos_lib/*.py`, `hooks/*.sh`, `scripts/*`, `rules/*.md`,
`templates/*.md`) con el marcador fuera de ventana. Si alguien lo importa desde un hook,
viaja.

---

## 6. El comando de verificación

Hoy da **rojo (exit 1, 41 hallazgos)**; después del arreglo da **verde (exit 0)**.

El script está inline abajo para que sobreviva al reinicio. Ubicación propuesta al aplicar:
`scripts/projection_invariant_gate.py`, con baseline en
`manifests/projection-invariant-baseline.yaml` siguiendo el patrón de
`scope-closure-baseline.yaml` (ratchet que solo desciende).

```
$ python3 scripts/projection_invariant_gate.py .
unguarded_callsites: 14
    cos_init.py:388   shutil.copy2(str(src), str(dest / f"{name}.md"))
    cos_init.py:420   shutil.copy2(str(src), str(dest_path))
    cos_init.py:1431  shutil.copy2(str(src), str(dest))
    cos_init.py:1439  shutil.copy2(str(policy_src), str(policy_dest))
    cos_init.py:1507  shutil.copytree(
    cos_init.py:1629  shutil.copy2(str(src), str(settings_path))
    cos_init.py:1808  shutil.copy2(...)            # falso positivo, guarda en 1805
    cos_init.py:1822  shutil.copy2(str(compact), ...)
    cos_init.py:1849  shutil.copytree(str(hooks_lib), str(dest_lib))
    cos_init.py:1855  shutil.copy2(str(wrapper_src), str(wrapper_dest))
    cos_init.py:1871  shutil.copytree(str(hooks_lib), str(dest_lib))
    cos_init.py:1877  shutil.copy2(str(wrapper_src), str(wrapper_dest))
    cos_init.py:1891  shutil.copy2(str(source_init), str(lib_init_file))
    cos_init.py:1963  shutil.copy2(str(catalog_src), str(catalog_kernel))
os_only_shipped: 0
closure_incomplete: 11
build_artifacts: 10
marker_invisible: 7
TOTAL: 42
$ echo $?
1
```

(42 con el falso positivo; 41 reales.)

Las cinco invariantes, y por qué cada una es red-hoy:

| Invariante | Hoy | Qué prueba |
|---|---|---|
| `unguarded_callsites` | 13 | AST sobre `cos_init.py`: todo `copy2`/`copytree` consulta `scope_allows` en su bloque |
| `os_only_shipped` | 0 | Sanidad. Es la única que hoy está verde, y es exactamente la que el arreglo del `__init__.py` puso verde |
| `closure_incomplete` | 11 | Todo `cos_lib.X` referido por un archivo instalado resuelve dentro del árbol instalado |
| `build_artifacts` | 10 | Ni `__pycache__` ni `.pyc` en el consumidor |
| `marker_invisible` | 7 | Ningún archivo instalado lleva un marcador que el parser real no puede ver |

La invariante que hace de esto un gate y no un lint es la segunda columna: **si el "arreglo"
consiste en editar un marcador, `closure_incomplete` y `build_artifacts` siguen rojos.** No
hay camino corto que las apague sin tocar lo que se instala.

### El script

```python
#!/usr/bin/env python3
# SCOPE: os-only
"""Projection invariant gate — asserts properties of the PRODUCED consumer tree,
not of the code path that produced it. Read-only. Exit: 0 clean · 1 findings · 2 error."""
from __future__ import annotations
import ast, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO_ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
COS_INIT = REPO_ROOT / "scripts" / "cos_init.py"
VISIBLE = re.compile(r"(?:# SCOPE:|<!-- SCOPE:)\s+([a-zA-Z_/-]+)")
ANY_MARKER = re.compile(r"(?:#|<!--)\s*SCOPE:\s*([a-zA-Z_/-]+)", re.IGNORECASE)
IMPORT_RE = re.compile(
    r"(?:from\s+cos_lib\.([a-z0-9_]+)\s+import"
    r"|import\s+cos_lib\.([a-z0-9_]+)"
    r"|from\s+cos_lib\s+import\s+([a-z0-9_,\s]+))"
)

def visible_scope(p: Path) -> str:
    try:
        with p.open(encoding="utf-8", errors="replace") as fh:
            head = [fh.readline() for _ in range(3)]
    except OSError:
        return ""
    for line in head:
        m = VISIBLE.search(line)
        if m:
            return m.group(1).strip()
    return ""

def any_scope(p: Path) -> tuple[str, int]:
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except (OSError, UnicodeDecodeError):
        return "", -1
    for i, line in enumerate(lines[:40], 1):
        m = ANY_MARKER.search(line)
        if m:
            return m.group(1).strip(), i
    return "", -1

def unguarded_callsites() -> list[tuple[int, str]]:
    src = COS_INIT.read_text(encoding="utf-8")
    tree, src_lines = ast.parse(src), src.splitlines()
    copies = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and isinstance(n.func.value, ast.Name) and n.func.value.id == "shutil"
        and n.func.attr in ("copy2", "copytree")
    ]
    guard_lines = {
        i + 1 for i, ln in enumerate(src_lines)
        if "scope_allows(" in ln and not ln.lstrip().startswith("def ")
    }
    def block(lineno: int) -> tuple[int, int]:
        best = (1, len(src_lines))
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.If, ast.FunctionDef, ast.While)):
                start = node.lineno
                end = max(getattr(n, "end_lineno", start) or start for n in ast.walk(node))
                if start <= lineno <= end and (end - start) < (best[1] - best[0]):
                    best = (start, end)
        return best
    out = []
    for c in copies:
        lo, _ = block(c.lineno)
        if not any(g in range(lo, c.lineno + 1) for g in guard_lines):
            out.append((c.lineno, src_lines[c.lineno - 1].strip()))
    return out

def main() -> int:
    keys = ("unguarded_callsites", "os_only_shipped", "closure_incomplete",
            "build_artifacts", "marker_invisible")
    findings: dict[str, list[str]] = {k: [] for k in keys}
    for lineno, text in unguarded_callsites():
        findings["unguarded_callsites"].append(f"cos_init.py:{lineno}  {text}")

    tmp = Path(tempfile.mkdtemp(prefix="cos-projection-"))
    try:
        r = subprocess.run(
            [sys.executable, str(COS_INIT), "--default", "--harness", "claude"],
            cwd=tmp, env={**os.environ, "COS_INSTALL_SCOPE": "both"},
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            print("projection failed:\n" + r.stderr, file=sys.stderr)
            return 2
        files = [p for p in tmp.rglob("*") if p.is_file()]
        for p in files:
            rel = p.relative_to(tmp).as_posix()
            if "__pycache__" in rel or rel.endswith(".pyc"):
                findings["build_artifacts"].append(rel)
                continue
            vis = visible_scope(p)
            if vis == "os-only":
                findings["os_only_shipped"].append(rel)
            if not vis:
                tag, line = any_scope(p)
                if tag and line > 0:
                    findings["marker_invisible"].append(f"{rel} (line {line}: {tag})")
        lib_dir = tmp / ".cognitive-os" / "cos_lib"
        available = {p.stem for p in lib_dir.glob("*.py")} if lib_dir.is_dir() else set()
        for p in files:
            if p.suffix not in (".py", ".sh") or "__pycache__" in p.as_posix():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in IMPORT_RE.finditer(text):
                mods = [x for x in (m.group(1), m.group(2)) if x]
                if m.group(3):
                    mods += [s.strip() for s in m.group(3).split(",") if s.strip()]
                for mod in mods:
                    if mod and mod not in available:
                        findings["closure_incomplete"].append(
                            f"{p.relative_to(tmp).as_posix()} -> cos_lib.{mod}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    total = 0
    for k in keys:
        v = sorted(set(findings[k]))
        print(f"{k}: {len(v)}")
        for item in v:
            print(f"    {item}")
        total += len(v)
    print(f"TOTAL: {total}")
    return 1 if total else 0

if __name__ == "__main__":
    sys.exit(main())
```

### Sobre el parche sin aplicar

**Mi recomendación se apoya parcialmente en `/tmp/origin-fix/origin.patch`** (911 líneas, no
aplicado, no lo toqué). Lo leí. Implementa una parte grande de (d):

- `scripts/cos_install_selfcheck.py` — self-check post-instalación sobre el árbol producido,
  con las categorías `missing_shipped` / `scope_conflict` / `dangling`.
- `manifests/install-selfcheck-allowlist.yaml` — la allowlist nombrada con motivo escrito
  (= mi opción **b** como escape hatch).
- `scripts/lib_closure.py` — agrega `extract_lib_modules_from_path()`, que `ast.parse`a los
  `.py` completos, y cambia la semilla de `extract_lib_modules_from_hook` a esa. **Arregla
  la causa 1** de los 11 colgantes (`hooks/_lib/*.py` fuera de la semilla).
- `scripts/cos_init.py` — mueve la clausura al paso 7c, después de instalar los `bin/*`,
  para que esos primitivos también siembren.

Dos límites del parche, dichos sin adornar:

1. **No cierra el call-site.** El `copy2` del `__init__.py` queda literalmente igual, sin
   `scope_allows`. El parche vuelve el problema *detectable*, no *imposible*. Es exactamente
   la mitad que le falta a la opción (c).
2. **No cubre `build_artifacts` ni `marker_invisible`.** El `__pycache__` sigue viajando y
   `cos-status` sigue instalándose.

Y un problema de proceso que no es del parche pero sí del operador: **vive en `/tmp`.** 911
líneas de trabajo real, más 4 instalaciones de consumidor de evidencia (`consumer-baseline`,
`consumer-fixed`, `consumer-sabotaged`, `consumer-frompatch`) y 7 probes con su output. Un
reinicio y no queda nada. Si algo de esto se va a usar, va al repo hoy.

---

## 7. Correcciones a las premisas del encargo

| Premisa | Estado | Corrección |
|---|---|---|
| `cos_init.py:1889-1891` copia `__init__.py` salteando `scope_allows` | **Confirmada** | Líneas exactas 1887-1893. La rama `else` sintetiza un `__init__.py` vacío — dato que el encargo no tenía y que decide la tensión |
| "Qué otros archivos pasan por ese call-site sin filtro. Ése es el radio real" | **Falsa** | Ese call-site copia un solo archivo, con ruta literal. Radio 1. El radio real está en los otros 12 call-sites, sobre todo `hooks/_lib/` (38 archivos + `__pycache__`) |
| "Ya se conocen tres" call-sites sin filtro (1891, 1436-1440, 1845/1875) | **Incompleta** | Son **13**, no 3. Los faltantes: 388, 420, 1431, 1507, 1629, 1822, 1855, 1877, 1963. Los dos de `hooks/_lib` están en 1849 y 1871 (no 1845/1875), y el de `provenance-scan.yaml` en 1439 (no 1436-1440) |
| `scope_allows` tiene cuatro fail-opens | **Confirmada, con precisión** | Hay 6 `return True` en la función (269, 273, 281, 293, 297, 301). Cuatro son fail-opens (269 no-es-archivo, 281 OSError, 293 sin-marcador, 297 tag-desconocido); 273 es la política `scope=="all"` y 301 es inalcanzable |
| El default sin marcador está en 291-293, no en 294 | **Confirmada** | Comentario en 292, `return True` en 293 |
| **8 archivos usan `# scope:` minúscula y caen al fail-open** | **Falsa** | Hay 106 archivos con `# scope:` minúscula en las primeras 3 líneas, pero **los 106 tienen además `# SCOPE:` en mayúscula en la línea 1**. El parser lee la línea 1 y acierta. Archivos cuyo único marcador es minúscula, en las primeras 3 líneas: **0**. En todo el archivo, sin ningún marcador en mayúscula: **1** (`cognitive-os.yaml:894`, que no pasa por `scope_allows`). El riesgo que el encargo describe existe pero su magnitud medida es cero |
| El parser lee solo las 3 primeras líneas; un marcador en la línea 4 es invisible | **Confirmada, y hay un caso vivo** | `cos_lib/pattern_detector.py:15 -> os-only` es el único archivo con marcador fuera de ventana en las superficies gobernadas por `scope_allows`. Hoy latente (no está en la clausura). **El caso vivo está en otra ventana**: `skill_scope_allows` lee 8 líneas y `skills/cos-status/SKILL.md` declara `os-only` en la 30 → se instala |
| `hooks/_lib/` viaja entero sin filtro y sus imports nunca entran a la clausura | **Confirmada, con una causa adicional** | El filtro no aplicaría igual: los 37 archivos de `hooks/_lib/` son todos `SCOPE: both`. El daño real es el otro: la semilla de la clausura son solo los `.sh` de `hooks/`. **Y hay una segunda causa independiente** que el encargo no tenía: `lib_closure.py:92-96` descarta `from cos_lib import X` porque exige `len(node.module.split(".")) > 1` y nunca mira `node.names`. 14 ocurrencias, 6 módulos |
| El gate `scope_closure_gate.py` está en 4/5/4/0 | **Confirmada** | `scope_conflict: 4, unmarked_published: 5, os_only_published: 4, marker_invisible: 0`, exit 0 (igual al baseline) |
| Hay un parche sin aplicar en `/tmp/origin-fix/origin.patch` | **Confirmada** | 911 líneas. Leído, no aplicado, no modificado. Ver §6 |

---

## 8. VERIFICADO vs NO VERIFICADO

### VERIFICADO (comando corrido en esta sesión)

- `scripts/cos_init.py` tiene 22 `copy2`/`copytree` al árbol del consumidor; 8 con guarda,
  13 sin (el 14º detectado es falso positivo, guarda en 1805). Detector AST inline en §6;
  los 22 cruzados a mano contra `grep -n "copy2\|copytree" scripts/cos_init.py`.
- El call-site 1887-1893 tiene rama `else: lib_init_file.write_text("")`. Lectura directa.
- `cos_lib/__init__.py` = 52 bytes, dos líneas de comentario, cero código.
  `wc -c cos_lib/__init__.py`.
- El commit `5ba9de934` agregó el filtro en 1909 y reclasificó `__init__.py` de `os-only` a
  `both` en el mismo diff. `git show 5ba9de934 -- scripts/cos_init.py` + mensaje de commit.
- `test_primitive_scope_governance.py:165` lee `splitlines()[:8]`. Lectura directa.
- Instalación default en dir de descarte: 15 reglas, 43 hooks, 8 skills, 39 módulos
  `cos_lib`. Todas las reglas y hooks proyectados son `SCOPE: both` en el fuente.
- 10 `.pyc` bajo `hooks/cos/_lib/__pycache__/` en el árbol instalado. `find`.
- 11 imports `cos_lib.*` colgantes en el árbol instalado. Script §6.
- `skills/cos-status/SKILL.md` declara `<!-- SCOPE: os-only -->` en la línea 30 y se
  instala. `sed -n '28,32p'` + `grep -rl` sobre el árbol instalado.
- `skill_scope_allows` lee `lines[:8]` y cae al fallback `audience:`. Lectura directa,
  `cos_init.py:328-345`.
- `lib_closure.py:92-96` descarta `from cos_lib import X`. Lectura directa + 14 ocurrencias
  por `grep -rnE "^\s*from cos_lib import "`.
- 106 archivos con `# scope:` minúscula en las primeras 3 líneas; los 106 con `# SCOPE:`
  mayúscula también. 0 con solo minúscula. Script Python de un pase sobre `git ls-files`.
- `cos_lib/pattern_detector.py:15` es el único `os-only` fuera de ventana en superficies
  gobernadas por `scope_allows`.
- `scope_closure_gate.py --profile default --json` → 4/5/4/0, exit 0, closure_size 65.
- `/tmp/origin-fix/origin.patch` toca `record_completion.py`, `cos_init.py`,
  `lib_closure.py`, `hook-timing-wrapper.sh` y crea `cos_install_selfcheck.py`,
  `install-selfcheck-allowlist.yaml`, `confidentiality.yaml.template`. No aplicado, no
  modificado.

### NO VERIFICADO

- **No corrí ninguna suite de tests.** Que `test_primitive_scope_governance` pase hoy lo
  infiero de que la proyección tiene 0 archivos con marcador `os-only` visible en las
  primeras 8 líneas — no de haberlo corrido.
- **No probé el arreglo.** El script de §6 lo corrí contra el estado actual (rojo). Que dé
  verde después es una afirmación de diseño, no una medición.
- **No apliqué ni probé `origin.patch`.** Mi lectura de qué arregla y qué no sale del diff,
  no de correrlo. Los directorios `consumer-fixed` / `consumer-frompatch` en `/tmp` sugieren
  que su autor sí lo probó; no los inspeccioné.
- **No medí el modo `--full`.** Todo lo de arriba es `--default --harness claude`. Los
  call-sites 1808/1849/1855 solo se ejecutan en `--full` y ahí el conteo de lo que viaja
  cambia.
- **No medí otros harnesses.** El test de gobernanza parametriza sobre varios; yo corrí
  `claude`.
- **No verifiqué si `cos-status` debe ser `os-only` o `both`.** Solo que las dos
  declaraciones coexisten en el mismo archivo y que gana la que ships. Cuál es la correcta
  es decisión de producto.
- **No estimé el trabajo de bajar el baseline 4/5/4/0.** Los 4 `scope_conflict` son
  dependencias reales entre módulos; resolverlos puede ser mover código, no mover un
  marcador. Sin medir.
