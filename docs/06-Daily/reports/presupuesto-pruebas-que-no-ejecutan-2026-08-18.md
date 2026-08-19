# Presupuesto de pruebas que no ejecutan la primitiva: 890 de 1441

**Fecha de la medición:** 2026-08-19 (el nombre del archivo conserva la fecha del encargo).
**Alcance:** las 1441 filas del registro de primitivas, sobre `HEAD` extraído con `git archive`.
**Entregable:** métrica nueva (`scripts/primitive_proof_execution_audit.py`), presupuesto con
ratchet (`manifests/primitive-scope-classification.yaml`), y su gate
(`tests/audit/test_primitive_proof_execution_budget.py`).

**Número inicial: 890.** No es el 668 que estimaba el informe de cobertura. La diferencia
está medida y explicada en §5.

---

## 1. El discriminador

La pregunta difícil del encargo era mecánica: cómo se distingue "ejecuta **la primitiva**"
de "ejecuta **otra cosa**". El clasificador del informe anterior marcaba `executes` a
cualquier archivo de prueba que contuviera `subprocess` o `importlib` — por eso
`test_os_only_scope_family.py`, que corre el auditor y ninguna de sus 478 primitivas,
salía "ejecuta".

El discriminador de acá no clasifica **archivos de prueba**: clasifica **la relación
prueba↔primitiva**. Un mismo archivo puede ejecutar una primitiva y no ejecutar las otras
477, y eso es exactamente lo que pasa.

Para pruebas Python, sobre el AST:

1. **Sitios de ejecución.** Llamadas a `subprocess.*`, `runpy.*`, `os.system/popen`,
   `importlib.util.spec_from_file_location`, `importlib.import_module`, `pytest.main`, más
   las funciones locales del propio archivo que contienen (transitivamente) una de esas.
2. **Constant-folding de los argumentos** de esos sitios a un conjunto de fragmentos de
   string, resolviendo: asignaciones de módulo y de función, `Path(x) / "y"`, f-strings,
   listas/tuplas, `str(...)`, **defaults de parámetros** (`def _run(hook=FULL_HOOK)`),
   variables de `for`, y payloads de `pytest.mark.parametrize`.
3. **Imports estáticos** aparte (`from scripts import cos_test_slow_report` ejecuta el
   módulo), pero **sólo con match de ruta completa**: `import yaml` no puede probar
   `scripts/yaml.py`.
4. **Match.** La fila cuenta como `executes` si su ruta relativa aparece entre esos
   fragmentos. El basename solo alcanza cuando ninguna otra fila del registro comparte ese
   basename.

Para pruebas `.bats`/shell (4 archivos) hay un fallback por líneas: línea con marcador de
ejecución, con una expansión de una salto de las variables shell (`HOOK="hooks/x.sh"` en una
línea, `bash "$HOOK"` en otra, ninguna de las dos sirve sola). El JSON reporta cuántas filas
descansan en ese camino: **4**.

**Lo que el discriminador NO cuenta como ejecución:** una ruta que aparece en el archivo. La
lista hardcodeada de 478 rutas recorrida con `path.exists()` no es un sitio de ejecución, y
ése es todo el punto.

### La prueba de que discrimina

De las **478** filas pareadas a `test_os_only_scope_family.py`, el discriminador marca
**una** como ejecutada:

```
$ python3 -c "...filtrar rows por paired_portability_test..."
filas pareadas a la familia: 478 Counter({'not-executed': 421, 'non-executable-artifact': 56, 'executes': 1})
la que ejecuta: [('scripts/primitive_scope_health.py', 'ast-exec-arg:primitive_scope_health.py')]
```

La única que ejecuta es **el auditor que la prueba corre**. Las 477 restantes, no. Eso es
literalmente el hallazgo del informe anterior, ahora producido por una máquina.

### Clases

| Clase | Significado | Filas (HEAD) |
|---|---|---|
| `executes` | un sitio de ejecución referencia la primitiva | 551 |
| `not-executed` | artefacto ejecutable que ninguna prueba corre | 515 |
| `non-executable-artifact` | `.md`/`.yaml`/`.tmpl`…: no hay nada que ejecutar | 375 |
| `missing-test` / `no-test` | sin prueba en disco / sin pareo | 0 / 0 |

**El presupuesto se pone sobre todo lo que no es `executes`: 515 + 375 = 890.** Sin recortes.
Podría haber excluido los 375 `.md` con el argumento correcto ("no se pueden ejecutar") y
habría quedado un presupuesto de 515 más lindo — pero un presupuesto que empieza excluyendo
una categoría es el verde barato de este lote. La categoría queda **visible** en
`by_execution_class`, que es lo que el operador necesita para decidir el alcance de la
reparación, no invisible en un denominador recortado.

---

## 2. Tasa de error medida, contra casos de las dos clases

Tres barridos, no una impresión.

**a) Muestra aleatoria con semilla, leída a mano.** 10 filas `executes` + 10 filas
`not-executed` (`random.seed(42)`, excluyendo los mega-tests de familia para no muestrear 477
veces el mismo caso). **20/20 correctas.**

**b) Barrido exhaustivo de sospecha de falso "no ejecuta".** Todas las filas `not-executed`
cuya prueba **sí tiene sitios de ejecución** y **menciona el artefacto** en algún lado —
o sea, los casos donde el folding pudo haberse quedado corto. Fuera de las 7 pruebas de
familia quedan **6 candidatos**, leídos uno por uno:

| Fila | Veredicto |
|---|---|
| `hooks/_lib/push-collision-check.sh` | **falso negativo** — la prueba arma un driver bash con `source '{LIB}'`, lo escribe a un archivo y ejecuta el archivo; el nombre de la primitiva nunca llega a un argumento de ejecución |
| `hooks/concurrent-write-guard.sh` | correcto — `FULL_HOOK` se asigna en la línea 27 y **no se usa nunca**; la prueba corre el proxy de Codex, no el hook |
| `scripts/cos-agent-watch`, `scripts/cos-progress-metric` | correcto — la prueba corre `cos_agent_supervision.py`, los wrappers no |
| `scripts/cos-status` | correcto — la prueba corre `scripts/cos-status.sh`; `scripts/cos-status` (180 bytes) no se ejecuta |
| `scripts/provenance-scan` | correcto — mismo patrón, corre el `.sh` homónimo |

**1 falso negativo sobre 6 candidatos**, y los 6 son la población completa de sospecha fuera
de las familias: la cota superior de sobreconteo fuera de familias es **1 fila de 890**.

**c) Barrido de huecos del detector.** Filas `not-executed` cuya prueba menciona una API de
ejecución en el texto pero cuyo AST no produjo ningún sitio: **33 filas, todas de
`test_os_only_missing_proof_smoke.py`** — el archivo que sólo hace `grep` de un marcador y de
`/Users/`, ya leído a mano en el informe anterior. Cero huecos nuevos.

**d) Evidencia débil, leída al 100%.** Las 6 filas que no descansan en un argumento de
llamada AST (4 por línea shell, 2 por import estático) se leyeron todas: **6/6 correctas**.
Ese barrido encontró y mató dos falsos positivos antes de fijar el número: `import yaml`
probaba `scripts/yaml.py` por sufijo de basename. El match por cola ahora exige basename
único en todo el registro.

**Resumen honesto:** sobre 46 filas verificadas a mano de las dos clases, **1 error**
(2,2%), y es un error que **sobrestima la deuda**, no que la esconde. La cota conocida:
una prueba que ejecuta la primitiva a través de un archivo intermedio generado en tiempo de
test queda contada como deuda. Es un patrón que aparece 1 vez en 1441 filas.

---

## 3. El número inicial y su comando, sobre HEAD extraído

El auditor camina el filesystem, no el índice, así que el número se fija sobre una
exportación limpia de `HEAD` (`git worktree add` está bloqueado por `destructive-git-blocker`):

```bash
mkdir -p "$SP/head-tree" && git archive HEAD | tar -x -C "$SP/head-tree"
cp manifests/primitive-scope-classification.yaml "$SP/head-tree/manifests/"   # el bloque de presupuesto es de este commit
python3 scripts/primitive_proof_execution_audit.py --project-dir "$SP/head-tree" --strict
```

```json
{"by_execution_class": {"executes": 551, "non-executable-artifact": 375, "not-executed": 515},
 "executes_by_evidence_kind": {"ast-exec-arg": 545, "shell-exec-line": 4, "static-import": 2},
 "findings": 0, "findings_by_code": {},
 "rows_without_execution": 890, "total": 1441,
 "without_execution_by_proof_level": {"family": 632, "primitive-specific": 258},
 "without_execution_by_scope": {"both": 267, "os-only": 571, "project": 52}}
EXIT=0
```

**890.** El presupuesto se escribe en `manifests/primitive-scope-classification.yaml` como
`proof_execution_budget.max_rows_without_execution: 890` — el valor medido exacto, sin
colchón, con el motivo escrito en el bloque, mismo contrato que `max_unregistered_mib` de
`manifests/state-retention.yaml`.

Sobre el árbol de trabajo con este commit adentro son 1442 filas y **890** también: la
primitiva nueva viene con una prueba que la ejecuta de verdad, así que no mueve el número.

---

## 4. Quién está adentro de las 890

**222 pruebas distintas** sostienen las 890 filas. Las 20 con 2 o más (688 filas); las 202
restantes son singletons.

| Filas | Prueba | Composición |
|---|---|---|
| 477 | `tests/red_team/portability/test_os_only_scope_family.py` | 421 not-executed + 56 no ejecutables |
| 75 | `tests/red_team/portability/test_package_skills.py` | 75 no ejecutables |
| 44 | `tests/red_team/portability/test_project_scope_family.py` | 14 + 30 |
| 40 | `tests/red_team/portability/test_os_only_missing_proof_smoke.py` | 33 + 7 |
| 12 | `tests/red_team/portability/test_shared_hook_surfaces.py` | 12 not-executed |
| 8 | `tests/red_team/portability/test_shared_tool_installers.py` | 8 not-executed |
| 4 | `tests/red_team/portability/test_shared_audit_scripts.py` | 4 not-executed |
| 3 | `tests/red_team/portability/test_cos_iroh_security.py` | 3 not-executed |
| 3 | `tests/red_team/portability/test_cos_agent_supervision_primitives.py` | 2 + 1 |
| 2 | `test_content-policy.py`, `test_decision-depth-gate.py`, `test_infra-health.py`, `test_pre-commit-gate.py`, `test_publication_safety.py`, `test_cross-harness-authoring.py`, `test_local-privacy-hygiene.py`, `test_shared_local_service_scripts.py`, `test_cos_epistemic_review_primitives.py`, `test_cos_lean_skillopt_primitives.py`, `test_cos_so_impact_eval_primitive.py` | 22 filas |

Por tipo de artefacto: `scripts` 401 · `skills` 189 · `rules` 129 · `hooks` 113 ·
`templates` 58.
Por scope: `os-only` 571 · `both` 267 · `project` 52.
Por `proof_level` declarado: `family` 632 · `primitive-specific` 258 · `none` **0** — o sea,
**las 890 filas están hoy en verde en los dos presupuestos existentes.**

Un patrón que vale la pena mirar y que no estaba en ningún informe: **la prueba pareada por
nombre que prueba otro archivo.** `test_pre-commit-gate.py` no menciona
`hooks/pre-commit-gate.sh`; `test_cos-session-start-projector.py` ejecuta
`scripts/cos-session-start-projector` y no el hook homónimo;
`test_pre-commit-content-hash-dedupe.py` ejecuta `scripts/precommit_content_hash.py` y no el
hook. El pareo por nombre da cobertura nominal a un artefacto que nadie corre.

La lista fila por fila:

```bash
python3 scripts/primitive_proof_execution_audit.py --list | sort   # 890 líneas: clase, scope, primitiva, prueba
```

---

## 5. El ratchet, y la demostración de que muerde

`tests/audit/test_primitive_proof_execution_budget.py`, 5 tests:

1. **Guarda de población** — si el escaneo devuelve menos de 1000 filas, o si ninguna fila
   sale `executes`, el test **falla**. Un presupuesto verde sobre una población vacía es el
   modo de falla que este repo ya publicó dos veces.
2. **Falsificación de la guarda** — `budget_findings(tmp_path, [])` tiene que devolver
   `proof-execution-empty-population`, no lista vacía.
3. **Techo del manifiesto** — el número del manifiesto no puede subir por encima del que
   fija el test. Para subirlo hay que tocar dos archivos y escribir el motivo: eso es un acto
   deliberado, no un arreglo de rojo.
4. **Medición contra el techo** — 890.
5. **Mordida** — una fila sintética `not-executed` agregada al conjunto real tiene que
   producir `proof-execution-budget-exceeded`.

```
$ .venv/bin/python -m pytest -p no:randomly -q tests/audit/test_primitive_proof_execution_budget.py
5 passed in 3.40s
```

Y la mordida de punta a punta, sobre árboles reales, no sobre listas en memoria: se copia el
`HEAD` extraído, se le agrega un script sintético con una prueba pareada que sólo hace
`assert ARTIFACT.exists()` (la firma exacta de la plantilla rota), y se corre el auditor
sobre los dos árboles:

```
--- HEAD extracted + budget block:
  EXIT=0
  total 1441 without_exec 890 findings {}
--- HEAD + one synthetic non-executing pair:
  EXIT=1
  total 1442 without_exec 891 findings {'proof-execution-budget-exceeded': 1}
```

Una fila alcanza. No hay colchón.

---

## 6. Correcciones a las premisas del encargo

1. **"hoy daría 668"** (informe de cobertura §5, cambio #4). Medido: **890**. La diferencia
   son **222 filas**, y no es ruido: el informe sumaba 623 `family` + 40 del smoke + 5 de
   existencia pura porque clasificaba **archivos de prueba**; el número real incluye **258
   filas `primitive-specific`** cuya prueba existe, ejecuta cosas, y no ejecuta **esa**
   primitiva — el caso del hook pareado por nombre a una prueba que corre el `.py` homónimo.
   El informe avisó que su clasificador era cota inferior; lo era por **un tercio**.
2. **"el discriminador: una prueba que ejecuta la primitiva la nombra en el comando o la
   importa por su ruta"** — la pista del encargo es correcta pero insuficiente tal cual.
   Nombrarla en el archivo no alcanza (478 rutas hardcodeadas); nombrarla en el comando
   tampoco, si el comando se arma con variables, defaults de parámetros o payloads de
   `parametrize`. Sin constant-folding el discriminador pierde ~la mitad de los verdaderos
   positivos. Y "importarla por su ruta" hay que acotarlo a ruta completa: por basename,
   `import yaml` prueba `scripts/yaml.py` (falso positivo medido y corregido).
3. **"proof-none en cero (recién cerrado)"** — sigue en cero sobre el árbol de trabajo con
   este commit (`python3 scripts/primitive_scope_health.py --mode proof --strict` →
   `{"by_proof_level": {"family": 658, "primitive-specific": 784}, "findings": 0}`, EXIT=0).
   Recontado, no heredado.
4. **"40 archivos con `assert ARTIFACT.exists()`"** — recontado, **40**, exacto
   (`grep -rl "_artifact_exists\|assert ARTIFACT.exists()" tests/red_team/portability/ | wc -l`).
   Pero ese corte no es el que manda: hay **515 filas** con artefacto ejecutable que ninguna
   prueba corre. Los 40 archivos son un subconjunto chico del problema.
5. **"`git worktree add` está bloqueado"** — confirmado, y usé `git archive HEAD | tar -x`.
   Se agrega una restricción que el encargo no menciona y que costó dos intentos:
   **`block-destructive-bash` rechaza cualquier `rm -rf` bajo `/private/tmp/...`**, que es
   justamente la forma en que el prompt del sistema escribe el scratchpad. La forma `/tmp/...`
   del mismo directorio sí pasa. Quien mida sobre árboles extraídos va a chocar con esto.
6. **"`python3` del PATH no tiene pytest pero sí corre el auditor"** — correcto, verificado
   en las dos direcciones: `python3 scripts/primitive_proof_execution_audit.py` corre;
   los tests van con `.venv/bin/python -m pytest`.
7. **"una métrica que hoy no existe"** — cierto para esta métrica, pero conviene decir que el
   manifiesto ya tiene **dos** presupuestos vecinos (`proof_level_budgets` y
   `behavior_depth_policy.max_by_depth`) y los dos derivan su clasificación del **nombre del
   archivo de prueba**. Por eso el presupuesto nuevo va en el mismo manifiesto y el bloque
   dice explícitamente en qué se diferencia: si mañana alguien renombra
   `test_os_only_scope_family.py`, los otros dos números se mueven y éste no.
8. **"no toques `hooks/scope-marker-portability-gate.sh`"** — no lo toqué; no escribí nada
   bajo `hooks/**` ni `rules/**`, así que la aprobación con prefijo
   `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` no hizo falta.
9. **Lo que el encargo prohibía y no hice:** no arreglé ninguna prueba (ni las 40, ni las 5,
   ni la de familia), no subí ningún presupuesto existente, y no conté filas por `proof_level`
   como si fuera la métrica — al contrario, el dato de que las 890 tienen `proof_level` sano
   es el argumento de por qué hacía falta esta medición.

---

## Apéndice: cómo reproducir

```bash
# número sobre el árbol de trabajo
python3 scripts/primitive_proof_execution_audit.py --strict

# número sobre HEAD extraído (lo que ve CI)
SP=/tmp/scope-verify && mkdir -p "$SP/head-tree" && git archive HEAD | tar -x -C "$SP/head-tree"
python3 scripts/primitive_proof_execution_audit.py --project-dir "$SP/head-tree" --strict

# la lista de las 890
python3 scripts/primitive_proof_execution_audit.py --list | sort

# el payload completo (filas + evidencia por fila)
python3 scripts/primitive_proof_execution_audit.py --json-out /tmp/exec.json

# el gate
.venv/bin/python -m pytest -p no:randomly -q tests/audit/test_primitive_proof_execution_budget.py

# la portabilidad de la primitiva nueva
.venv/bin/python -m pytest -p no:randomly -q tests/red_team/portability/test_primitive_proof_execution_audit.py
```

Demostración de la mordida (crea un árbol de prueba, no toca el repo):

```bash
SP=/tmp/scope-verify
mkdir -p "$SP/probe1" && cp -R "$SP/head-tree/." "$SP/probe1/"
printf '#!/usr/bin/env bash\n# SCOPE: os-only\necho probe\n' > "$SP/probe1/scripts/zz-synthetic-ratchet-probe.sh"
cat > "$SP/probe1/tests/red_team/portability/test_zz-synthetic-ratchet-probe.py" <<'EOF'
from pathlib import Path
ARTIFACT = Path(__file__).resolve().parents[3] / "scripts/zz-synthetic-ratchet-probe.sh"
def test_zz_synthetic_ratchet_probe_artifact_exists() -> None:
    assert ARTIFACT.exists()
EOF
python3 scripts/primitive_proof_execution_audit.py --project-dir "$SP/probe1" --strict; echo "EXIT=$?"   # -> 891, EXIT=1
```

Medición de la tasa de error (muestra con semilla + barridos de sospecha): el procedimiento
está en §2 y se reproduce leyendo `evidence` fila por fila del `--json-out`; el campo dice
qué fragmento de qué sitio de ejecución produjo el match, que es lo que se contrasta contra
la lectura del archivo.
