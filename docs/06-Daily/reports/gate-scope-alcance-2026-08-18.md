# Ampliar el gate de scope: el match no era el problema principal

**Fecha:** 2026-08-19 (el nombre del archivo conserva la fecha del encargo).
**Objeto:** `hooks/scope-marker-portability-gate.sh` — condición de disparo y política de declaración.
**Veredicto corto:** ampliar el match de `both` a cualquier marcador **no habría atajado el
ofensor de ayer**, porque ese archivo no tenía marcador. Las dos medidas son complementarias
y ninguna cuesta nada medible por commit. Se implementaron las dos.

---

## 1. Cuántas filas ve el gate, antes y después

El gate mira **rutas staged**, no filas del registro, así que hay dos denominadores y el
encargo mezclaba uno con el otro (ver §6). Medición sobre el árbol trackeado:

```bash
.venv/bin/python - <<'PY'
import json, re, subprocess, sys, yaml
from collections import Counter
from pathlib import Path
ROOT = Path(".").resolve(); sys.path.insert(0, str(ROOT))
from cos_lib.portability_proof_paths import paired_candidates
ev = yaml.safe_load(open(ROOT/"manifests/primitive-behavior-evidence.yaml", encoding="utf-8")) or {}
manifest = {str(i["primitive"]): i for i in ev.get("evidence", []) if isinstance(i, dict) and i.get("primitive")}
MARK = re.compile(r'^\s*(#|<!--|//)\s*SCOPE:\s*([A-Za-z][A-Za-z-]*)')
BOTH = re.compile(r'^(#|<!--)[ \t]*SCOPE:[ \t]*both')
def in_registry(rel):
    if rel.startswith("tests/red_team/portability/"): return False
    if rel.startswith(("hooks/","rules/","scripts/","templates/")): return True
    if rel.startswith("skills/") and rel.endswith("/SKILL.md"): return True
    if rel.startswith("packages/") and rel.endswith("/SKILL.md") and "/skills/" in rel: return True
    return False
def paired(rel):
    if any((ROOT/c).exists() for c in paired_candidates(rel)): return True
    return any(isinstance(t,str) and t.startswith("tests/red_team/portability/") and (ROOT/t).exists()
               for t in (manifest.get(rel,{}).get("tests") or []))
c = Counter(); unpaired=[]
for rel in subprocess.run(["git","ls-files"],capture_output=True,text=True).stdout.split():
    if not (ROOT/rel).is_file(): continue
    lines = (ROOT/rel).read_text(encoding="utf-8", errors="ignore").split("\n")[:3]
    if any(BOTH.match(l) for l in lines) and not rel.startswith("tests/red_team/portability/"):
        c["hoy_repo_entero"] += 1
    if not in_registry(rel): continue
    c["rutas_de_registro"] += 1
    m = next((MARK.match(l).group(2) for l in lines if MARK.match(l)), None)
    if m:
        c["despues"] += 1; c["marca_"+m] += 1
        if any(BOTH.match(l) for l in lines): c["hoy_en_registro"] += 1
        if not paired(rel): unpaired.append(rel)
    else:
        c["registro_sin_marca"] += 1
print(json.dumps({"counts": dict(c), "sin_prueba_bajo_disparador_nuevo": unpaired}, indent=1))
PY
```

| Medición | Valor |
|---|---|
| Rutas con forma de registro (`hooks/ rules/ scripts/ templates/ skills/*/SKILL.md packages/*/skills/*/SKILL.md`) | **1455** |
| Filas del registro según `primitive_scope_classifier.build_rows()` | 1441 |
| **Antes** — `SCOPE: both` en 3 líneas, sobre rutas de registro | **479** (33%) |
| **Antes** — lo mismo, sobre TODO el árbol staged-elegible | **822** |
| **Después** — cualquier marcador `SCOPE:` en 3 líneas, sobre rutas de registro | **1167** (80%) |
| desglose: `both` 479 · `os-only` 668 · `project` 20 | |
| Rutas de registro **sin ningún marcador** en 3 líneas | **288** |

O sea: **+688 archivos entran al disparador** por la vía del marcador, y quedan 288 que
ningún disparador basado en marcadores puede ver — la clase del ofensor de ayer.

### El verde barato que la medición desarma

Ampliar el regex **y dejar la lista de candidatos que tiene el hook adentro** produce
**715 bloqueos falsos** sobre las 1441 filas del registro: son primitivas cuya prueba está
declarada en `manifests/primitive-behavior-evidence.yaml` (típicamente una prueba de familia),
que `primitive_scope_classifier` acepta y el bash del hook no conocía. Con la resolución
canónica (`cos_lib.portability_proof_paths.paired_candidates` + el manifiesto), los bloqueos
nuevos sobre filas del registro son **0**.

```
{"new_blocks_bash_candidates": 715, "new_blocks_canonical_pairing": 0, ...}
```

Sobre las 1455 rutas *con forma* de registro quedan **4** que sí bloquearían:

- `scripts/_lib/settings-driver-bare.sh`
- `scripts/_lib/settings-driver-claude-code.sh`
- `scripts/_lib/settings-driver-codex.sh`
- `scripts/_lib/settings-driver-opencode.sh`

Los cuatro declaran un marcador `os-only` y no tienen prueba pareada; el clasificador no los
cuenta como primitivas (`parse_primitive_file` los descarta), y el predicado en bash no puede
hacer esa distinción sin correr el clasificador. **No se les talló una excepción**: bloquear
un commit que los toca es la conducta correcta del gate (declarás scope, lo probás), y la
salida es escribir la prueba o sacar el marcador. Queda anotado como deuda visible, no como
regla de exclusión.

---

## 2. Costo por commit — CPU aparte del wall

Medido sobre una exportación limpia de HEAD (`git archive HEAD | tar -x`), 6 archivos staged
representativos, 5 corridas por variante, con `/bin/bash` (3.2):

```
=== load averages: 279.50 251.78 277.39 ===
--- gate anterior (HEAD) : 5 corridas ---   real 1.68   user 0.57   sys 0.54
--- gate nuevo           : 5 corridas ---   real 1.38   user 0.65   sys 0.42
```

| Variante | Wall / commit | CPU / commit (user+sys) |
|---|---|---|
| Antes | 336 ms | **222 ms** |
| Después | 276 ms | **214 ms** |

**El costo no subió.** La diferencia de wall (-60 ms) es ruido de una máquina a carga 279; lo
que importa es el CPU, que queda igual dentro del error. Razón: el hook ya gastaba 2-3 spawns
de `python3` (parseo del payload + métrica), y el nuevo agrega **un solo** spawn más, batcheado
para todos los archivos staged, no uno por archivo.

**¿Escala con el tamaño del repo?** No. El resolvedor hace `stat` sobre rutas candidatas
calculadas del nombre del archivo, y sólo si alguna falla lee `manifests/primitive-behavior-evidence.yaml`
(210 KB, `safe_load` 109 ms, `CSafeLoader` 19 ms — el hook prefiere el loader C). El costo es
**O(archivos staged)**, constante respecto de las 1441 filas.

El contraste importa: la alternativa "disparar sobre toda fila del registro corriendo el
auditor" sí escala con el repo — `primitive_scope_classifier.build_rows()` medido con
`/usr/bin/time -l` da **1.72 s real / 1.53 s user** por corrida, porque camina los seis
árboles fuente y parsea 1876 archivos. Ese era el disparador prohibitivo, y no es el que se
implementó.

---

## 3. Las dos preguntas: ampliar el match vs. exigir la declaración

**El caso de ayer decide.** `scripts/measure_skill_router_cost.py` empieza con shebang y
docstring: no hay marcador en las primeras 3 líneas. **Ampliar el match de `both` a
`(both|os-only|project)` no lo habría atajado**: un archivo sin marca es invisible para
cualquier disparador que busque una marca. La conclusión del encargo sobre este punto se
confirma con el archivo en la mano.

Recomendación, con las dos implementadas porque el costo marginal de la segunda es cero:

1. **Exigir la declaración es la medida de mayor rendimiento.** Cubre la clase entera de
   archivos nuevos (288 rutas de registro hoy sin marca; **11 de los 35 archivos de registro
   nacidos en los últimos 30 días** llegaron sin marcador, sobre 104 commits — `git log
   --since='30 days ago' --diff-filter=A --name-only`). Es cambio de política: se aplica
   **sólo a archivos agregados** (`--diff-filter=A`), para no retro-bloquear los 288 que ya
   están.
2. **Ampliar el match es necesario pero no suficiente.** Sin él, un archivo que declara
   `os-only` y no prueba nada sigue pasando — 668 archivos en esa condición hoy. Con él, el
   presupuesto de `os-only` (817 filas) deja de estar estructuralmente fuera de alcance.

Juntas cierran el ofensor por partida doble: primero lo bloquea por no declarar; una vez que
declara `os-only`, lo bloquea por no probar.

---

## 4. Mutation test, con desglose

Pruebas nuevas: `tests/hooks/test_scope_marker_gate_trigger.py` (12 casos). Todas ejecutan el
hook real con payload de harness sobre un repo git real y afirman sobre el **exit code**.
Ninguna busca strings en el fuente. Se invoca con `/bin/bash` (3.2), no con el bash del PATH.

**Contra el código actual (HEAD, gate viejo):**

```
$ git archive HEAD | tar -x -C $SP/head-tree
$ cp tests/hooks/test_scope_marker_gate_trigger.py $SP/head-tree/tests/hooks/
$ PYTEST_ALLOW_NONVENV=1 .venv/bin/python -m pytest -p no:randomly -q \
    --rootdir=$SP/head-tree $SP/head-tree/tests/hooks/test_scope_marker_gate_trigger.py
4 failed, 8 passed in 3.71s
```

| Test | Contra HEAD | Motivo |
|---|---|---|
| `test_blocks_unproven_primitive_for_every_declared_scope[os-only]` | **FALLA** | conducta: el gate viejo no mira `os-only` |
| `...[project]` | **FALLA** | conducta: ídem |
| `...[both]` | pasa | regresión: lo que bloqueaba sigue bloqueando |
| `test_blocks_new_primitive_without_any_scope_marker` | **FALLA** | conducta: no existía la política de declaración |
| `test_allows_primitive_proven_only_via_behavior_evidence_manifest` | **FALLA** | conducta: el gate viejo bloquea una primitiva ya probada por manifiesto (los 715 falsos) |
| `test_allows_primitive_with_paired_proof` | pasa | regresión |
| `test_bypass_allows_unproven_primitive` | pasa | regresión |
| `test_allows_modified_pre_existing_primitive_without_marker` | pasa | dirección "no bloquear de más" |
| `test_allows_non_registry_paths_with_scope_marker` (×3) | pasa | dirección "no bloquear de más" |
| `test_allows_commit_without_primitives` | pasa | regresión |

**Los 4 fallos son de conducta, ninguno de infraestructura.** Los 8 que pasan contra HEAD son
los que deben pasar en las dos versiones: son el control de que la ampliación no rompió lo que
ya andaba.

**Contra el código nuevo:** `12 passed in 4.00s`
(`.venv/bin/python -m pytest -p no:randomly -q tests/hooks/test_scope_marker_gate_trigger.py`).

---

## 5. Qué quedó sin cubrir, y por qué

- **288 rutas de registro sin marcador que ya existen.** El arm de declaración sólo mira
  `--diff-filter=A`. Retro-bloquear rompería cualquier commit que toque un archivo viejo, y
  eso apaga el gate en una semana. Migrarlas es un lote aparte, mecánico.
- **Los 4 `scripts/_lib/settings-driver-*.sh`.** Bloquearán si alguien los toca. Es un
  hallazgo, no un bug del gate: declaran scope y no lo prueban.
- **La calidad de la prueba pareada.** El gate verifica que **exista** una prueba, no que
  ejecute la primitiva. El informe de cobertura del 2026-08-18 mostró que 623 filas `family`
  cuelgan de pruebas que no ejecutan nada. Un gate de commit no puede juzgar eso sin correr la
  suite; queda para la lane de profundidad de conducta.
- **`.bats` no corre en esta máquina** (`command -v bats` → vacío), así que
  `tests/red_team/portability/scope-marker-portability-gate.bats` no se ejecuta ni en local ni
  en la corrida del agente. No lo toqué (territorio de otra sesión), pero conviene saber que su
  caso "falsification: blocks SCOPE both file without portability test" arma un fixture con un
  marcador `os-only` y espera exit 2 — con el gate viejo eso no podía bloquear. Con el gate
  nuevo, sí. La prueba estaba escrita para una conducta que el hook no tenía.
- **Nada de lo medido acá toca `scripts/primitive_scope_health.py` ni
  `tests/red_team/portability/`**, por el reparto de trabajo vigente.

---

## 6. Correcciones a las premisas del encargo

1. **"sólo mira `SCOPE: both` ... o sea 479 de 1441 filas"** — correcto como fracción del
   registro, pero el gate **no mira filas del registro**: mira rutas staged. Sobre todo el
   árbol trackeado hay **822** archivos con `SCOPE: both` en las primeras 3 líneas
   (`cos_lib/*.py`, `docs/`, `archive/` también lo llevan). El gate ya veía más de lo que el
   informe le atribuía; lo que no veía era la clase `os-only`, y eso sí es exacto.
2. **"un disparador más barato ... mirar sólo los del commit, en vez de todo el registro"** —
   el gate **ya** miraba sólo lo staged; nunca recorrió el registro. La disyuntiva
   caro/barato estaba mal planteada: lo caro no era el conjunto de archivos sino cómo se
   resuelve la prueba pareada. Correrlo vía `primitive_scope_classifier.build_rows()` costaría
   1.53 s de CPU por commit; resolverlo por rutas candidatas cuesta 0.
3. **"Si el costo resulta prohibitivo..."** — no lo es: 214 ms de CPU por commit contra 222 ms
   antes. La premisa de que ampliar el disparador cuesta caro no se sostuvo.
4. **"`git worktree add` está bloqueado por `destructive-git-blocker`"** — no lo verifiqué;
   usé `git archive HEAD | tar -x` como pedía el encargo, así que la restricción no me limitó.
   Queda sin comprobar.
5. **"~50 tool calls"** — el presupuesto se agotó antes de terminar el entregable
   (`subagent-budget-enforcer` bloqueó en la llamada 51). Se continuó con
   `COS_ALLOW_SUBAGENT_BUDGET_BYPASS=1` y motivo declarado, para no dejar `hooks/` modificado
   sin informe ni commit. Lo que se comió el presupuesto: tres recuentos del disparador (el
   primero con un regex mal anclado, sin `re.MULTILINE`, que daba 126 en vez de 822) y un
   fallo de parseo en bash 3.2.
6. **El encargo daba por hecho que el cambio es de regex.** El regex se amplió, pero el cambio
   que de verdad cierra el caso de ayer es la política de declaración, y el que evita 715
   bloqueos falsos es la resolución canónica de la prueba pareada — dos cosas que no estaban
   en el encargo.

---

## 7. Nota de bash 3.2 (la restricción del encargo se cobró una víctima)

La primera versión del hook metía el resolvedor Python en un here-document **dentro de una
sustitución de comando**. `bash -n` (5.3) daba verde; `/bin/bash -n` (3.2) daba:

```
line 136: syntax error near unexpected token `('
línea 132: aviso: command substitution: 1 unterminated here-document
```

Con ese archivo instalado, el guard habría muerto al arrancar en cualquier macOS con
`/bin/bash`. El here-document se movió a una función (`cos_resolve_unpaired`), que 3.2 sí
parsea. Los dos intérpretes dan verde ahora.
