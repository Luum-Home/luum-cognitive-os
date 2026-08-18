# Tests de portabilidad y contratos de scope — 2026-08-16

Lote de 6 tests de `tests/red_team/portability/`. Todo número acá abajo sale de
un comando que está citado al lado.

## 1. CPU vs wall: ninguno de los 6 medía la máquina

El encargo pedía separar "el script cuelga" de "el script espera un core" antes
de tocar nada. Medición con `resource.RUSAGE_CHILDREN` alrededor de cada corrida:

| Test | wall | CPU | CPU/wall | Veredicto |
|---|---|---|---|---|
| `test_codebase-memory-directive::test_runs_from_arbitrary_project_root` | 0,5 s | 0,5 s | 90 % | Falla real (`PermissionError`) |
| `test_cos-doctor-harness::test_cos_doctor_harness_has_passing_scope_contract` | 1,6 s | 1,6 s | 97 % | **No falla**: pasa |
| `test_cos-status::test_portability_json_is_machine_parseable_from_arbitrary_cwd` | 3,0 s | 3,9 s | 131 % | **No falla**: pasa |
| `test_os_only_scope_family::…budget_is_zero…` | 3,3 s | 2,0 s | 62 % | Falla real (`findings=4`) |
| `test_project_scope_family::…budget_is_zero…` | 3,3 s | 2,0 s | 62 % | Falla real (mismo comando) |
| `test_primitive_behavior_depth_audit::…strict_passes…` | 3,1 s | 2,6 s | 86 % | Falla real (`findings=29`) |

Los dos tests de "budget" ejecutan **el mismo** subproceso, así que comparten
una sola medición:

```bash
.venv/bin/python scripts/primitive_scope_health.py \
  --project-dir "$PWD" --mode proof --strict --json-out /tmp/h.json
```

**Ninguno de los 6 falló por timeout, y ninguno estaba midiendo la máquina.**
Las relaciones CPU/wall van de 62 % a 131 % (>100 % = hijos en paralelo). La
carga de la máquina era real —`load averages: 17.52 130.80 185.78` sobre 12
cores— pero no es lo que rompía estos tests. No hubo nada que "arreglar en el
test para que mida lo que dice medir" en los 6.

El único artefacto de este lote que **sí** mide la máquina apareció después, y
en código mío: ver §4, `hook-io-overhead-bench.sh`, 15,2 s de reloj por 1,35 s
de CPU (8 %).

## 2. Qué rompió cada presupuesto

Un solo hecho rompe los tres tests de auditoría: el 2026-08-15 entraron **28
primitivos sin prueba de scope pareada** — 27 `os-only` y 1 `project`, con
presupuesto 0 en ambos scopes (`manifests/primitive-scope-classification.yaml`,
`proof_level_budgets.none_by_scope`).

```bash
.venv/bin/python -c "import json; d=json.load(open('/tmp/h.json')); \
  [print(r['scope'],r['path']) for r in d['rows'] if r['proof_level']=='none']"
```

Los 28, todos con fecha de alta 2026-08-15 (`git log --diff-filter=A`):

- 24 `scripts/*.py` de auditoría/prueba (`audit_gate_liveness`, `verify_claims`,
  `scope_closure_gate`, `hook_behavior`, `revision_probe`, …)
- 3 `scripts/*.sh` (`home-path-family-mutation-check`, `hook-io-overhead-bench`,
  `probe-hook-git-adjacency`)
- `rules/encargo-refutable.md`, `templates/confidentiality.yaml`
- `scripts/check_codebase_memory_readiness.py` (el único `project`)

**Qué se hizo: se les dio la prueba que faltaba, no se subió el presupuesto.**
`proof_level:none` 28 → 0; `behavior_depth:none` 28 → 0; ambos audits salen 0.

Ninguno de los 28 era candidato a cambiarle el scope en vez de darle prueba: los
26 de `scripts/` son herramientas de mantenimiento del propio SO (`os-only`
correcto), y `check_codebase_memory_readiness.py` es justamente el gate que un
proyecto consumidor corre — tiene que viajar.

### El único número que sube

`behavior_depth_policy.max_by_depth.structural`: **472 → 473, exactamente +1 y
sin colchón**, con el motivo escrito en el manifest.

Causa: `_test_depth()` en `scripts/primitive_behavior_depth_audit.py` evalúa
`STRUCTURAL_RE` contra la ruta completa del test antes que `PROJECTION_RE`. La
prueba nueva `test_check_codebase_memory_readiness.py` es una sonda de
invariancia de cwd —projection por lo que hace— pero cae en `structural` porque
el token `readiness` se filtra desde el stem del **artefacto**, no del test.

No es un caso nuevo: el mismo falso positivo ya alcanza a
`test_pentesting-readiness.py`, `test_cos-architecture-readiness.py` y
`test_cos-service-readiness-gate.py`. Arreglar el clasificador saca varias filas
de `structural` de una sola vez, con radio de impacto sobre todo el ledger, así
que es un cambio aparte. **Queda pendiente y es la deuda real de este punto**;
el +1 sostiene el ratchet pegado a la realidad mientras tanto.

## 3. Qué ejercita cada prueba nueva

La invariante que fijan las 28 es la que el scope declara: **el artefacto
resuelve su raíz por `__file__`/`BASH_SOURCE`, nunca por el cwd del proceso**.
Cada prueba lo corre desde un cwd ajeno y compara contra la corrida desde la
raíz del repo. Uno que se anclara en `Path.cwd()` falla ahí en vez de romper
callado en el checkout de un consumidor.

No hay ninguna prueba que sólo verifique que el archivo existe.

| Grupo | N | Qué ejecuta |
|---|---|---|
| CLI con `--help` | 21 | `--help` desde cwd ajeno: exit 0, `usage` en stdout, stdout idéntico desde ambas raíces. El import corre antes de argparse, así que atrapa dependencias de cwd en tiempo de import. |
| Auditorías sin argparse | 2 | La auditoría **entera** desde ambas raíces: mismo exit code, mismo stdout. |
| Shell por invariancia | 2 | Igual, vía `bash`. |
| Benchmark | 1 | Ver §4. |
| Reglas `.md` | 2 | Sin rutas absolutas de este checkout; frontmatter que sobrevive la reubicación a otra raíz; el gate documentado honrando su contrato de exit code. |
| Template `.yaml` | 1 | Se instala en un proyecto descartable y se lee con `load_protected_terms` desde ahí; toda clave del template tiene que ser leída por el parser. |

## 4. Lo que la medición encontró de paso

Cosas que un `--help` copiado del scaffold habría tapado:

- **`audit_gate_registration.py` y `audit_adopt_verdict_linkage.py` no tienen
  argparse.** `--help` corre la auditoría completa y sale 1. Un test que
  afirmara `--help → 0` sería falso; van por invariancia de cwd.
- **`hook_behavior.py` es librería**, sin `__main__`. `--help` sale 0 con stdout
  **vacío**: aseverar sobre eso es aseverar sobre un no-evento. Su prueba lo
  importa y clasifica un hook real desde otra raíz.
- **Contadores volátiles.** `classify_ambiguous_hooks.py` y
  `audit_gate_registration.py` imprimen columnas de telemetría que cambian entre
  dos corridas **en el mismo cwd** (verificado con dos corridas seguidas, no
  supuesto: `8333` → `8334`). Comparar stdout crudo habría dado un test flaky
  disfrazado de riguroso. Se enmascaran los dígitos; toda ruta, nombre,
  veredicto y posición de columna queda bajo aserción.
- **`hook-io-overhead-bench.sh` es un benchmark de wall-clock.** Una iteración
  cuesta ~15,2 s de reloj por ~1,35 s de CPU (8 %). Correrlo dos veces revienta
  el `timeout = 30` de `pytest.ini` y **aborta la sesión entera de pytest** —
  pasó una vez durante este trabajo. Su propio header ya dice que está
  deliberadamente fuera de CI porque cualquier umbral estable en una máquina
  cargada es demasiado flojo para atrapar lo que existe para atrapar. La prueba
  **no asegura sus números**: lo arranca desde una raíz ajena y exige que llegue
  a su primer header, lo que sí es falsable (anclado en `$PWD` moriría en sus
  guardas `-d` antes de imprimir nada). Está escrito en el docstring del test.
- **`scripts/hook-io-overhead-bench.sh` está en modo 644**, mientras el resto de
  `scripts/*.sh` está en 755: ejecutarlo directo da 126. **No se tocó**: su
  header documenta la ruta `bash scripts/hook-io-overhead-bench.sh`, así que el
  modo puede ser deliberado. Queda reportado, no arreglado.

## 5. Qué del encargo era falso

- **"6 tests fallan" — son 4.** `test_cos-doctor-harness::…scope_contract` y
  `test_cos-status::…machine_parseable…` **pasan**, aislados y en lote, antes de
  tocar nada. Eran arrastre de la corrida abortada, no supervivientes de un
  reintento.
- **"Los dos fijan que un presupuesto llegó a cero" — el de project no.** Su
  aserción es `by_proof_level["none"] <= 459`, no `== 0`, a pesar del nombre del
  test. Y ninguno de los dos falló por esa línea: **los dos fallaban por el
  `findings == 0` que comparten**. El nombre del test miente sobre lo que fija.
- **"El timeout no distingue" — cierto en general, irrelevante en estos 6.**
  Cero de los 6 falló por `TimeoutExpired`. La lectura de que los supervivientes
  del reintento seguían siendo casos de tiempo no se sostiene.
- **El scaffold genera pruebas que no prueban.** `cos-portability-proof-scaffold`
  existe y corre, pero su template por defecto emite
  `[str(ARTIFACT), "--help"]` para todo lo que no sea `.py` ni skill — o sea que
  para un `.md` **intenta ejecutar el Markdown como programa**.
  `test_codebase-memory-directive.py` salió de ahí y no podía pasar nunca:
  `PermissionError: [Errno 13] Permission denied: rules/codebase-memory-directive.md`.
  Por eso las 28 pruebas se escribieron a mano y no con el scaffold. **El
  scaffold sigue roto para artefactos no ejecutables**: es deuda abierta.
- **`python3` en esta máquina no corre los tests.** Es el Homebrew 3.14 y **no
  tiene pytest**; `python3 -m pytest` muere con `No module named pytest` y exit
  1, que a ojo se lee como "el test falló". El intérprete de la suite es
  `.venv/bin/python` (3.12). El aviso del encargo sobre `bash` sobre un `.py`
  es correcto, pero éste es el que muerde primero.
- **`hooks/**` y `rules/**` protegidos: no hizo falta tocarlos.** No hay diff
  propuesto. Verificado por `git status --short` sobre las rutas tocadas: sólo
  `tests/red_team/portability/` y `manifests/primitive-scope-classification.yaml`.

## Reproducir

```bash
.venv/bin/python scripts/primitive_scope_health.py --project-dir "$PWD" \
  --mode proof --strict --json-out /tmp/h.json          # 0 findings
.venv/bin/python scripts/primitive_behavior_depth_audit.py --project-dir "$PWD" \
  --strict --json-out /tmp/d.json                        # 0 findings
.venv/bin/python -m pytest tests/red_team/portability/test_os_only_scope_family.py \
  tests/red_team/portability/test_project_scope_family.py \
  tests/red_team/portability/test_primitive_behavior_depth_audit.py -q
```

> Correr en lotes de 5 o menos: `pytest-timeout` con `timeout_method = thread`
> aborta la sesión entera en vez de marcar el test lento, y una corrida que
> muere sin resumen **no es "0 fallas"**.
