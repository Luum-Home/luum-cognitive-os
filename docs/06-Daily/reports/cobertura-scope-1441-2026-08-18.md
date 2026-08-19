# Cobertura de scope sobre 1441 primitivas: el cero no es un presupuesto, es un detector de llegada tardía

**Fecha de la auditoría:** 2026-08-19 (el nombre del archivo conserva la fecha del encargo).
**Alcance:** `scripts/primitive_scope_health.py --mode proof --strict` sobre las 1441 filas del registro.
**Veredicto corto:** el cero es sostenible como **invariante**, pero hoy no lo sostiene nada:
el único control temprano cubre 479 de 1441 filas (33%), y la mayor prueba de familia
—478 filas, un tercio del registro— no ejecuta ninguna de las primitivas que declara cubrir.

---

## 0. Lo primero: el rojo NO cerró

El encargo dice "el rojo ya lo cerré yo, verificalo". En el árbol de trabajo, sí:

```
$ python3 scripts/primitive_scope_health.py --mode proof --strict
{"by_proof_level": {"family": 658, "primitive-specific": 783}, "findings": 0, "total": 1441}
EXIT=0

$ .venv/bin/python -m pytest -p no:randomly -q \
    tests/red_team/portability/test_os_only_scope_family.py \
    tests/red_team/portability/test_project_scope_family.py \
    tests/red_team/portability/test_primitive_behavior_depth_audit.py \
    tests/red_team/portability/test_measure_skill_router_cost.py
11 passed in 15.33s
```
(wall 21.4s; CPU 14.17s user + 5.12s sys; `load averages: 392.25 411.28 437.85` — la máquina
venía de la corrida de 22.000 tests, cualquier número de reloj de pared es de la máquina.)

En el repo, no. `tests/red_team/portability/test_measure_skill_router_cost.py` está
**sin trackear** (`git status --short` → `?? tests/red_team/portability/test_measure_skill_router_cost.py`),
y el auditor camina el filesystem, no el índice. Sobre una exportación limpia de HEAD:

```
$ mkdir -p $SP/head-tree && git archive HEAD | tar -x -C $SP/head-tree
$ python3 scripts/primitive_scope_health.py --project-dir $SP/head-tree --mode proof --strict
{"by_proof_level": {"family": 658, "none": 1, "primitive-specific": 782},
 "findings": 2, "findings_by_code": {"proof-none-budget-exceeded": 1,
 "proof-none-zero-budget-violated": 1}, "total": 1441}
EXIT=1
```

Verde local, rojo en cualquier checkout de HEAD: CI, otra sesión, un clon nuevo.
**Acción #1 para el orquestador: commitear ese archivo.** No lo commiteo yo —
es un untracked de otra sesión y mezclarlo en mi commit va contra la norma de
escritores concurrentes.

La prueba en sí es real: corre `scripts/measure_skill_router_cost.py` con `--help`
desde un cwd ajeno y desde el repo y exige mismo exit code y stdout byte-idéntico.
No es una prueba de existencia.

---

## 1. Frecuencia real: no son "tres veces en dos días", es el modo de operación

Medido, no recordado. Mapa de nacimiento de cada archivo (`git log --diff-filter=A
--name-only --pretty=format:'C|%H|%ct'`, 14.780 líneas) cruzado con las 1441 filas del
auditor:

| Medición | Valor |
|---|---|
| Filas cuya prueba nació en el **mismo commit o antes** que la primitiva | **173** (12%) |
| Filas cuya prueba llegó en un commit **posterior** | **1133** (79%) |
| Filas con prueba sin trackear | 2 |
| Filas sin fecha de nacimiento resoluble | 133 |

Distribución del atraso de las 1133: `<1d`: 55 · `1-7d`: 200 · `7-30d`: 546 · `30d+`: 332.

O sea: **escribir la prueba después es la norma histórica del repo, no la excepción.**
El presupuesto de cero no está midiendo un accidente ocasional; está midiendo la
diferencia de días entre dos commits que casi nunca coinciden.

El lote de esta semana, con fechas:

| Día | Qué pasó |
|---|---|
| 2026-08-15 | nacen **30** primitivas |
| 2026-08-15/16 | el gate de commit bloquea **13** veces por falta de prueba pareada |
| 2026-08-18 | aterrizan **28** pruebas para primitivas nacidas antes |
| 2026-08-18 08:13 | `hooks/_lib/git-command-parse.sh` nace **junto con** su prueba (commit `d13e32710`) — el gate funcionó |
| 2026-08-18 20:14 | nace `scripts/measure_skill_router_cost.py` **sin** prueba (commit `bbedb3c80`) — el gate no lo miró |

El propio gate lleva el registro (`.cognitive-os/metrics/scope-marker-portability-gate.jsonl`,
140 filas, 2026-07-19 a 2026-08-18):

```
decisiones: {'allow': 126, 'block_missing_portability_test': 14}
bloqueos por día: 2026-08-15: 11, 2026-08-16: 2, 2026-07-29: 1
tasa: 14/140 commits vistos = 10.0%  (~0.47 bloqueos/día sobre 30 días)
```

**Uno de cada diez commits que el gate mira trae una primitiva sin prueba** — y eso es
sólo sobre el tercio del registro que el gate puede ver (§2).

---

## 2. El chequeo temprano existe, está cableado, dispara — y no puede ver el presupuesto que se rompe

`hooks/scope-marker-portability-gate.sh` es exactamente el control temprano que el encargo
supone ausente: PreToolUse sobre Bash, se activa con `git commit`, bloquea con exit 2 si un
archivo staged no tiene prueba pareada. **Está activo**: lo rutea
`hooks/bash-hot-path-dispatcher.sh` (por eso `grep -c scope-marker .claude/settings.json`
da 0 y aun así el hook corre), `manifests/hook-registration-classification.yaml` lo declara
`status: active`, y las 140 filas de métrica con 14 bloqueos prueban que decide de verdad.
No es un control fantasma.

El problema es su condición de disparo. Del propio hook:

```bash
header="$(head -3 "$abs" 2>/dev/null || true)"
if ! printf '%s\n' "$header" | grep -Eq '(^#|<!--)[[:space:]]*SCOPE:[[:space:]]*both'; then
  continue
fi
```

Sólo mira artefactos que declaran `SCOPE: both` en las primeras 3 líneas. Medido sobre las
1441 filas:

| Categoría | Filas | ¿El gate la ve? |
|---|---|---|
| `SCOPE: both` en las primeras 3 líneas | **479** | sí (33%) |
| otro marcador `SCOPE:` en las primeras 3 líneas | 684 | no |
| sin marcador `SCOPE:` en las primeras 3 líneas | 278 | no |

Y el presupuesto que se rompió es el de **`os-only`** — 817 filas, todas fuera del gate.
La fila del ofensor lo dice completo:

```json
{"path": "scripts/measure_skill_router_cost.py", "scope": "os-only",
 "declared_scope": null, "decision_source": "scope-override", ...}
```

Sin marcador declarado, y `os-only`: invisible para el gate por dos motivos independientes.

**Este es el hallazgo de la pregunta 2.** No falta el control: el control tiene un
recorte que hace estructuralmente imposible que proteja el presupuesto de cero de
`os-only`. Mientras el gate mire sólo `both`, el cero de `os-only` sólo lo puede
descubrir una lane de tests o la cola de merge — tarde, por diseño.

Costo de cerrarlo: cambiar la condición de `SCOPE: both` a "cualquier fila del registro
de primitivas", que es la misma lista que ya usa `primitive_scope_health.py`. Es un cambio
en `hooks/**` (config protegida) y no lo hago acá: el encargo pide la tabla, no el parche.

---

## 3. Qué ejercita una prueba `family`: 478 filas apoyadas en cero ejecuciones

14 archivos `family` cubren 658 filas. Uno solo,
`tests/red_team/portability/test_os_only_scope_family.py` (527 líneas, nacido 2026-05-15),
declara cubrir **478 filas — el 33% del registro entero**. Sus tres tests:

1. `test_os_only_scope_family_has_maintainer_metadata_and_non_user_plane` — para cada una de
   las 478 rutas hardcodeadas: `assert path.exists()`, y después `row.scope == "os-only"`,
   `row.consumer_surface == "maintainer-only"`, `row.plane != "user-plane"`. Esas tres son
   campos que produce `primitive_scope_health.build_rows()`, el mismo módulo que el test
   importa. **Es el manifiesto comparado contra sí mismo.**
2. `test_os_only_scope_family_is_registered_as_behavior_evidence` — verifica que cada ruta
   figure en `manifests/primitive-behavior-evidence.yaml` **apuntando a este mismo archivo
   de test**. Circularidad pura: la evidencia de que hay evidencia.
3. `test_os_only_scope_none_budget_is_zero_after_family_proof` — corre el auditor y exige
   `findings == 0`. Es el gate assertando su propio verde.

Ninguna de las 478 primitivas se ejecuta. Ninguna se corre desde un cwd ajeno. Ninguna
prueba portabilidad, que es lo que el nombre del directorio promete. Un clasificador
automático la marca como `executes` porque usa `importlib` — pero lo que importa es
`scripts/primitive_scope_health.py`, no las primitivas. **Mi clasificador automático es
cota inferior; la lectura a mano es peor que el número.**

¿Comparten riesgo las 478? No. La lista mezcla `hooks/self-install.sh`,
`skills/adr-tombstone/SKILL.md`, `templates/hook-template.sh` y `scripts/cosd`. Lo único que
tienen en común es la etiqueta `os-only`. La pregunta del encargo —"¿o `family` se volvió
una forma de declarar cobertura sin tenerla?"— tiene respuesta: **para estas 478, sí.**

Segundo caso, y peor porque no se llama `family`:
`tests/red_team/portability/test_os_only_missing_proof_smoke.py` cubre **40 filas**, se
clasifica `primitive-specific` (el nombre no matchea ninguno de los tokens de familia), y
lo único que hace es `grep` de un marcador de scope en las primeras 20 líneas y buscar
`/Users/` en el texto. **La clasificación `family` vs `primitive-specific` sale del
NOMBRE DEL ARCHIVO de la prueba**, no de lo que hace:

```python
def proof_level(row) -> str:
    ...
    if any(token in name for token in ("shared_", "package_skills", "family", "surfaces",
                                       "scripts", ...)):
        return "family"
    return "primitive-specific"
```

Con ese criterio, cualquier prueba cuyo nombre contenga `scripts` es "familia" y cualquiera
que no, es "específica". La taxonomía de proof levels no mide profundidad de prueba: mide
sustrings.

Tabla completa de familias (filas / qué ejercita realmente):

| Filas | Archivo | Qué hace |
|---|---|---|
| 478 | `test_os_only_scope_family.py` | metadata + circularidad + auto-verde (0 primitivas ejecutadas) |
| 75 | `test_package_skills.py` | sólo existencia (3 asserts) |
| 44 | `test_project_scope_family.py` | mismo patrón que el de 478 |
| 40 | `test_os_only_missing_proof_smoke.py` (marcada `primitive-specific`) | grep de marcador + grep de `/Users/` |
| 12 | `test_shared_hook_surfaces.py` | lectura de texto |
| 12 | `test_cos_lean_skillopt_primitives.py` | ejecuta |
| 8 | `test_shared_tool_installers.py` | lectura de texto |
| 7 | `test_cos_artifact_workflow_primitives.py` | ejecuta |
| 6 | `test_cos_agent_supervision_primitives.py` | ejecuta |
| 5 | `test_cos_epistemic_review_primitives.py` | ejecuta |
| 4 | `test_shared_audit_scripts.py` | lectura de texto |
| 3 | `test_cos_so_impact_eval_primitive.py` | ejecuta |
| 2 | `test_shared_local_service_scripts.py` | lectura de texto |
| 1+1 | `test_family_conformance_probe.py`, `test_home-path-family-mutation-check.py` | ejecutan |

**623 de las 658 filas `family` (95%) cuelgan de las siete pruebas de arriba que no
ejecutan la primitiva que cubren.** Las familias chicas (12, 7, 6, 5, 3) sí ejercitan.
El problema no es el mecanismo de familia: es su uso a escala de 478.

---

## 4. Los 782 (hoy 783) `primitive-specific` frente al arreglo del scaffold

**La premisa del encargo no se sostiene tal como está escrita.** Sí: 781 de 783 filas
tienen su prueba nacida antes de `0d925f5d3` (`git log -1 --format=%ct 0d925f5d3` →
`1787083567`, 2026-08-18 17:06). Pero "anterior al arreglo" no es lo mismo que "generada
por el scaffold roto": `scripts/cos-portability-proof-scaffold` nació el **2026-05-13**, y la
mayoría de estas pruebas son de mayo y junio, escritas a mano o por otras vías.

La medición que sí discrimina es la **firma de la plantilla rota** (`assert ARTIFACT.exists()`
o una función `*_artifact_exists`, el test que no podía fallar según
`docs/06-Daily/reports/scaffold-portabilidad-2026-08-18.md`):

```
$ grep -rl "_artifact_exists\|assert ARTIFACT.exists()" tests/red_team/portability/ | wc -l
40
```

**40 archivos** siguen cargando la aserción de existencia que no puede fallar. La mayoría
también contiene un test que ejecuta de verdad, así que no son 40 falsos verdes completos:
son 40 archivos con una mitad muerta adentro. Clasificación automática de los 711 archivos
`primitive-specific`:

| Qué hace la prueba | Archivos | Filas cubiertas |
|---|---|---|
| ejecuta la primitiva (subprocess / importlib / runpy) | 543 | — |
| sólo lee texto o parsea | 235 | — |
| ni ejecuta ni lee (existencia pura) | 5 | 5 |

Los cinco de existencia pura, la lista corta que el operador puede decidir de un vistazo:

- `tests/red_team/portability/plan-claim-validator.bats`
- `tests/red_team/portability/scope-marker-portability-gate.bats`
- `tests/red_team/portability/verify-archived.bats`
- `tests/red_team/portability/test_cos_test_slow_report.py`
- `tests/red_team/portability/test_hook-io-overhead-bench.py`

**Criterio propuesto para el lote de 40 + 5** (el encargo pide el criterio, no los commits):

1. **Borrar, no reescribir**, toda función `test_*_artifact_exists` cuyo archivo ya tenga un
   test que ejecute la primitiva. No agrega señal y sí agrega verde. 40 archivos, cambio
   mecánico, verificable con el mismo `grep` de arriba llegando a 0.
2. **Reescribir a mano** los 5 de existencia pura, con la plantilla por familia que el
   scaffold ya emite bien desde `0d925f5d3`.
3. **No tocar** los 235 `reads-text`: parsear frontmatter tras relocalizar el archivo es
   una prueba de portabilidad legítima para un `.md`. Marcarlos como deuda sería mover la
   medición, no el problema.

---

## 5. Veredicto: ¿el cero es sostenible?

**Sí como invariante, no con la maquinaria actual.** Tres razones, en orden de fuerza:

1. **El control temprano no alcanza al presupuesto.** El gate cubre 479/1441 filas y el
   presupuesto que se rompe es el de las 817 `os-only`. Con ese recorte, el cero de
   `os-only` sólo lo puede descubrir una lane tardía. No es una alarma que suena tarde por
   negligencia: suena tarde porque nadie la conectó a ese circuito.
2. **La regla de admisión es una lista hardcodeada.** Agregar una primitiva `os-only` no
   agrega una fila a `OS_ONLY_PRIMITIVE_PROOF_BASELINE`: la deja afuera, con
   `proof_level: none`, y rompe el presupuesto. El cero no premia escribir la prueba;
   castiga agregar un script. Ese es el mecanismo exacto de las tres roturas de esta semana.
3. **El cero mide presencia de archivo, no de prueba.** 623 filas `family`, las 40 del smoke y 5
   `primitive-specific` de existencia pura están en cero con pruebas que no ejecutan nada. Un presupuesto que
   da cero con 668 filas sin conducta verificada es un supresor que no suprime: da
   sensación de cobertura sobre el 46% del registro.

**No hay que subir el presupuesto.** Subirlo apagaría el único rojo honesto que queda.
Lo que hay que cambiar es qué lo dispara y qué lo satisface:

| # | Cambio | Efecto sobre el cero |
|---|---|---|
| 1 | Ampliar la condición del gate de `SCOPE: both` a toda fila del registro | el rojo llega en el `git commit`, no en la lane |
| 2 | Que el gate ofrezca `scripts/cos-portability-proof-scaffold` en el mensaje de bloqueo | el costo de cumplir baja al de aceptar una sugerencia |
| 3 | Derivar `proof_level` de lo que la prueba hace, no del nombre del archivo | `family` deja de ser una etiqueta que se gana por sustring |
| 4 | Segundo presupuesto, separado: filas cuya prueba no ejecuta la primitiva | hoy daría 668 (623 `family` + 40 del smoke + 5 de existencia pura); ése sí arranca con un número y baja con ratchet |

El (1) y el (2) hacen sostenible el cero. El (3) y el (4) hacen que el cero signifique algo.
Sin el (4), cerrar el rojo de hoy es cerrar el síntoma más chico de los dos.

---

## 6. Correcciones a las premisas del encargo

1. **"El rojo ya lo cerré yo; probablemente lo encuentres cerrado."** Cerrado en el árbol de
   trabajo, **abierto en HEAD**: la prueba está sin trackear y el auditor camina el
   filesystem. `git archive HEAD` + auditor → `findings: 2`, `EXIT=1`. §0.
2. **"¿Existe un chequeo más temprano y no está cableado, o no existe?"** — falsa dicotomía.
   Existe, está cableado, y **dispara de verdad** (140 filas de métrica, 14 bloqueos). El
   defecto es su condición de disparo: `SCOPE: both`, 33% del registro. §2.
3. **"Contá cuántas de las 782 son anteriores al arreglo del scaffold."** 781 de 783 lo son,
   pero el número no significa lo que la pregunta supone: el scaffold nació el 2026-05-13 y
   casi todas esas pruebas son anteriores o ajenas a él. La medición que discrimina es la
   firma de la plantilla rota: **40 archivos**. §4.
4. **"Tres veces en dos días."** Subestimado. **1133 de 1441 filas** tuvieron su prueba en un
   commit posterior a la primitiva, y sólo 173 en el mismo commit o antes. Escribir la prueba
   después es el modo normal del repo. §1.
5. **`by_proof_level` del encargo** (`family: 658, none: 1, primitive-specific: 782`,
   `total: 1441`) — verificado exacto sobre HEAD. Sobre el árbol de trabajo es
   `family: 658, primitive-specific: 783`.
6. **`grep -c scope-marker .claude/settings.json` da 0** y aun así el hook corre: lo rutea
   `hooks/bash-hot-path-dispatcher.sh`. Ausencia en `settings.json` **no** es prueba de que
   un hook no esté registrado en este repo — el mismo error que documenta
   `rules/rate-limiting.md` para su caso, que ahí sí es real (ese hook tiene 0 disparos).
7. **Restricción "`python3` del PATH no tiene pytest"**: correcto para pytest, pero
   `python3 scripts/primitive_scope_health.py` corre perfecto con el `python3` del PATH — la
   restricción no aplica al auditor.
8. **No pude usar `git worktree add` para reproducir como CI**: lo bloquea
   `destructive-git-blocker` (ADR-055b) y no forcé el bypass. Usé `git archive HEAD | tar -x`,
   que da el mismo árbol sin mutar el repo. La receta de `gates-sin-trampa` ("reproducir con
   `git worktree add /tmp/wt-verify HEAD`") está bloqueada por otro control de la casa;
   conviene actualizarla a `git archive`.

---

## Apéndice: cómo reproducir los números

Auditor y suite:

```bash
python3 scripts/primitive_scope_health.py --mode proof --strict            # árbol de trabajo
mkdir -p "$SP/head-tree" && git archive HEAD | tar -x -C "$SP/head-tree"
python3 scripts/primitive_scope_health.py --project-dir "$SP/head-tree" --mode proof --strict
.venv/bin/python -m pytest -p no:randomly -q tests/red_team/portability/test_os_only_scope_family.py \
  tests/red_team/portability/test_project_scope_family.py \
  tests/red_team/portability/test_primitive_behavior_depth_audit.py \
  tests/red_team/portability/test_measure_skill_router_cost.py
```

Gate y su punto ciego:

```bash
python3 -c "import json,collections; rows=[json.loads(l) for l in open('.cognitive-os/metrics/scope-marker-portability-gate.jsonl') if l.strip()]; print(collections.Counter(r['decision'] for r in rows))"
grep -rl "_artifact_exists\|assert ARTIFACT.exists()" tests/red_team/portability/ | wc -l
```

Fan-out por prueba, atraso de la prueba y clase de cada archivo (las tres tablas de §1, §3 y
§4 salen de acá). Requiere el mapa de nacimientos:

```bash
git log --diff-filter=A --name-only --pretty=format:'C|%H|%ct' > "$SP/births.txt"
```

```python
#!/usr/bin/env python3
"""Forense de cobertura: fan-out por prueba, atraso vs nacimiento, clase de prueba."""
import json, collections, datetime, sys
from pathlib import Path

ROOT = Path('.').resolve()
SP = Path(sys.argv[1])
SCAFFOLD_FIX_EPOCH = 1787083567          # git log -1 --format=%ct 0d925f5d3

births, cur = {}, None                   # log es newest-first: la última escritura gana = el add más viejo
for line in (SP / 'births.txt').read_text().splitlines():
    if line.startswith('C|'):
        cur = int(line.split('|')[2])
    elif line.strip():
        births[line] = cur

rows = json.load(open('.cognitive-os/reports/primitive-scope-proof-audit.json'))['rows']

EXEC_TOKENS = ('subprocess.run', 'subprocess.check', 'exec_module', 'importlib',
               'runpy', 'os.system', 'pytest.main')

def classify_test(rel):
    p = ROOT / rel
    if not p.exists():
        return 'missing'
    txt = p.read_text(errors='replace')
    if any(t in txt for t in EXEC_TOKENS):
        return 'executes'                # cota inferior: importlib puede cargar el AUDITOR, no la primitiva
    if 'read_text' in txt or 'yaml.safe_load' in txt or 'json.load' in txt:
        return 'reads-text'
    return 'existence-only'

late = same = unknown = 0
for r in rows:
    bp, bt = births.get(r['path']), births.get(r['paired_portability_test'])
    if bp is None or bt is None:
        unknown += 1
    elif bt > bp:
        late += 1
    else:
        same += 1
print(f'prueba posterior a la primitiva: {late} | mismo commit o antes: {same} | sin fecha: {unknown}')

by_test = collections.defaultdict(list)
for r in rows:
    by_test[r['paired_portability_test']].append(r)
for t, rs in sorted(by_test.items(), key=lambda kv: -len(kv[1]))[:15]:
    bt = births.get(t)
    born = datetime.date.fromtimestamp(bt).isoformat() if bt else 'untracked'
    print(f'{len(rs):5d}  {classify_test(t):14s} born={born}  {t}')

spec = [r for r in rows if r['proof_level'] == 'primitive-specific']
pre = sum(1 for r in spec
          if (b := births.get(r['paired_portability_test'])) is not None and b < SCAFFOLD_FIX_EPOCH)
print(f'primitive-specific con prueba anterior a 0d925f5d3: {pre}/{len(spec)}')
```

Punto ciego del gate (479/1441):

```python
import json, re
from pathlib import Path
rows = json.load(open('.cognitive-os/reports/primitive-scope-proof-audit.json'))['rows']
pat = re.compile(r'(^#|<!--)[ \t]*SCOPE:[ \t]*both')
vis = sum(1 for x in rows
          if any(pat.search(l)
                 for l in Path(x['path']).read_text(errors='replace').splitlines()[:3]))
print(vis, 'de', len(rows), 'filas visibles para scope-marker-portability-gate.sh')
```
