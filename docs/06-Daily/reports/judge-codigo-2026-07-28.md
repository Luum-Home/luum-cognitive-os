# Juez independiente — Calidad de código y coherencia arquitectónica

**Fecha:** 2026-07-28
**Repo:** `luum-agent-os` · rama `session/content-bound-receipts`
**Lente:** calidad de código y coherencia arquitectónica
**Modo:** read-only (único archivo escrito: este informe)

---

## Veredicto

> **El código está sano y la arquitectura es coherente: cero duplicación de contenido, cero código muerto medible, 97% de los tests ejercitan comportamiento real, y la higiene de TODOs/paths es casi perfecta — el problema real no es la calidad sino la escala (624K LOC, 731 entrypoints en `scripts/`) y una minoría de funciones-monstruo.**

## Score de salud del código: **88 / 100**

| Dimensión | Peso | Score | Justificación (medida) |
|---|---|---|---|
| Duplicación | 20 | 19 | 0 archivos `.py` con contenido idéntico sobre 2962 únicos; 14 cuerpos de función duplicados sobre 7857 (0.18%) |
| Código muerto | 20 | 19 | 0/368 módulos `cos_lib` muertos; 2/731 scripts sin referencia (ambos WIP sin commitear de esta misma rama) |
| Calidad de tests | 20 | 17 | 97.1% ejercitan comportamiento real; 424 tests débiles; estilos de assert inconsistentes (`assert` vs `self.assertX`) |
| Estructura / hotspots | 20 | 14 | No hay dios-módulo (máx 2050 LOC), pero 227 funciones ≥80 líneas y una de 977 |
| Higiene | 20 | 19 | 3 marcadores TODO en todo el código no-test; 0 paths `/Users/` hardcodeados |

Descuento principal: **funciones-monstruo** (dimensión 4). Todo lo demás está en el decil superior de lo que se ve en repos de este tamaño.

---

## Correcciones a las premisas del orquestador

Ninguna de las cifras del encargo sobrevivió intacta. Se recontaron todas.

| Premisa | Realidad medida | Comando |
|---|---|---|
| `~6944 .py` | **2962 archivos `.py` únicos** (3037 paths trackeados, 75 son symlinks). El 6945 del `find` crudo incluía `.venv/`, `__pycache__/`, `archive/` | `git ls-files '*.py' \| wc -l` → 3037; dedup por `realpath` → 2962 |
| `~2155 tests` | **Correcta.** 2156 archivos `tests/**/test_*.py`, 2155 tras dedup de symlinks | `git ls-files 'tests/**/test_*.py' 'tests/test_*.py' \| wc -l` → 2156 |
| `~550 .go` | **193 archivos `.go`** trackeados. El ~550 incluía `vendor/` y caché de módulos | `git ls-files '*.go' \| wc -l` → 193 |
| `2.4G` | Tamaño del working tree con `.venv`, `target/`, `.git`. El **código fuente trackeado es 624.327 LOC** en 3635 archivos | ver `scratchpad/hotspots.py` |
| "hay `cos_lib/` y referencias a `lib/`" | **`lib/` no existe en la raíz.** Las 52 referencias `from lib.` son todas internas a `workflows/`, un sub-proyecto autocontenido con su propio `pyproject.toml` y su propio `workflows/lib/`. No son imports rotos | `ls -d lib` → No such file; `git ls-files \| grep -E '^lib/' \| wc -l` → 0 |
| "Cargo.toml, package.json, bunfig.toml = poliglotismo" | Parcialmente falso. Rust son **3 archivos**; TS/JS son **14**; `bunfig.toml` es 4 líneas de hardening de supply-chain, no un stack | `git ls-files '*.rs'` → 3; `cat bunfig.toml` |

### Corrección crítica del propio orquestador (mid-task): `timeout` no existe

El orquestador avisó que `timeout` no está en este macOS y que cualquier comando iniciado con `timeout` devolvió exit 127 con salida vacía.

**Verificado:** `which timeout gtimeout` → not found; `timeout 2 echo hola` → exit 127.

**Exposición de este informe: una (1) invocación, sin contaminación de hallazgos.** El único comando afectado fue `timeout 900 python3 .../deadcode.py`, que devolvió un `command not found` visible y fue reejecutado correctamente antes de derivar ninguna conclusión. **Ningún número de este informe proviene de un comando contaminado.**

Aclaración importante: el resto de las corridas largas usó el **parámetro `timeout` de la herramienta Bash** (una feature del harness, expresada en milisegundos), que no es el binario `timeout` y sí se ejecutó — evidenciado por su salida real.

---

## Tabla de hallazgos

| # | Severidad | Hallazgo | Evidencia (comando) |
|---|---|---|---|
| 1 | **MEDIA** | **227 funciones ≥80 líneas** sobre 7857 (2.9%). La peor: `cos_lib/skill_router.py::_build_hand_coded_routing_table` con **977 líneas** (es tabla de datos incrustada como código, debería ser un manifest). El *code smell* real es `cos_lib/dispatch.py::dispatch` con **593 líneas** de lógica de control | `scratchpad/dup_funcs.py` (AST, `end_lineno - lineno`) |
| 2 | **MEDIA** | **424 tests (2.87%) no ejercitan comportamiento**: 226 existence-only, 125 tautologías puras, 73 sin assert alguno. Viola la regla propia del repo contra tests de mera existencia | `scratchpad/testquality3.py` |
| 3 | **BAJA** | **Duplicación cross-language deliberada y controlada**: el crate Rust `cos-script-exposure-audit-rs` reimplementa `scripts/cos-script-exposure-audit` (Python). Está **gobernada por un test de paridad** que ejecuta ambos y compara JSON | `head -40 crates/cos-script-exposure-audit-rs/tests/parity.rs` |
| 4 | **BAJA** | **Colisión de nombre con solapamiento de concern**: `cos doctor harness` (Go, 159 LOC) y `scripts/cos-doctor-harness.sh` (Bash, 255 LOC) son *chequeos distintos* del mismo dominio, sin referencia cruzada. Riesgo de confusión para el operador, no duplicación literal | `wc -l scripts/cos-doctor-harness.sh cmd/cos/internal/cli/doctor.go` |
| 5 | **BAJA** | **`workflows/` (36 archivos) es código muerto autodeclarado** — `DEPRECATED.md` lo marca desde marzo 2026 y está excluido de `pyproject.toml` (`packages = ["cos_lib"]`). Es deuda honesta, no oculta | `head -20 workflows/DEPRECATED.md` |
| 6 | **BAJA** | **`scripts/yaml.py` y `yaml.py` (raíz) son dos copias del mismo shim** de PyYAML, divergentes (md5 distintos, 4 funciones duplicadas). El shim en sí está bien diseñado: delega a PyYAML real cuando existe | `md5 yaml.py scripts/yaml.py`; `scratchpad/dup_funcs.py` |
| 7 | **INFO** | 2 scripts sin ninguna referencia: `scripts/cos-review-approve`, `scripts/cos-review-gate` — **ambos son WIP sin commitear de la rama actual**. No es deuda, es trabajo en vuelo | `scratchpad/scripts_dead2.py` + `git status` |
| 8 | **INFO** | Estilos de aserción mezclados: 253 tests usan `self.assertX` (unittest) conviviendo con `assert` de pytest en el mismo corpus | análisis del bucket `NO_ASSERT` |

### Lo que NO se encontró (hipótesis refutadas)

| Hipótesis del encargo | Resultado |
|---|---|
| "¿Funcionalidad duplicada entre Python y Go?" | **No.** El binario Go **consume manifests generados por Python**. `scripts/generate_harness_projection_registry.py` declara literalmente: *"Generate the shared harness projection registry used by Bash/Python/Go UX"*. Fuente de verdad única, 104 manifests leídos por Python, 5 por Go. Es el patrón correcto |
| "¿Hay código copiado entre `cos_lib/` y `packages/*/lib/`?" | **No, cero.** 70 de los 369 entries de `cos_lib/` son **symlinks** a `packages/*/lib/`; los otros 299 son archivos reales. `cos_lib/` es la fachada canónica declarada en `pyproject.toml`. **0 archivos `.py` con contenido idéntico sobre 2962 únicos** |
| "Código muerto: dame los 15 peores" | **No hay 15.** 0/368 módulos `cos_lib` sin importador; 7 (1.9%) importados solo por tests. 726/731 scripts wired a producción |
| "¿Hay un dios-módulo?" | **No.** El archivo más grande es `scripts/cos_init.py` con 2050 líneas sobre 624K LOC totales (0.3%) |

---

## Inventario canónico (symlinks resueltos)

Método: `git ls-files` (solo trackeado) → `os.path.realpath()` → dedup por path real. Script: `scratchpad/inventory.py`.

| Lenguaje | Paths trackeados | Archivos únicos | LOC |
|---|---:|---:|---:|
| Python | 3037 | **2962** | 506.924 |
| Bash | 519 | 477 | 73.833 |
| Go | 193 | 193 | 42.706 (24.534 prod + 18.172 test) |
| TS/JS | 14 | 14 | 1.930 |
| Rust | 3 | 3 | 864 |

**136 paths trackeados resuelven a otro archivo** (symlinks). Contarlos como componentes separados es exactamente el falso-duplicado que arruinó auditorías previas.

**Rol de cada lenguaje:**
- **Python** — el kernel. `cos_lib/` (368 módulos) + `scripts/` (731 entrypoints).
- **Go** — el CLI `cos` (38 archivos de comando, 3 `go.mod` separados). Implementa nativo, pero lee los manifests que genera Python. Solo 4 comandos hacen shell-out a Python; 12 de 38 invocan procesos externos.
- **Bash** — hooks (`hooks/` → symlinks a `packages/*/hooks/`) y scripts de operador.
- **Rust** — un solo crate, reimplementación con test de paridad.
- **TS/JS** — packaging npm + dashboard. No es un stack de aplicación.

---

## Muestreo de tests: 20 al azar, adjudicados a mano

**Semilla:** `random.seed(20260728)` sobre las 14.779 funciones de test — reproducible con `scratchpad/testquality3.py`.

| # | Veredicto | Test |
|---:|---|---|
| 1 | REAL | `tests/unit/test_tool_result_envelope.py::test_persist_true_file_exists` |
| 2 | REAL | `tests/contracts/test_install_timing.py::test_jsonl_is_valid_json_lines` |
| 3 | REAL | `tests/unit/test_cross_platform_discipline.py::test_env_shebang` — test de política sobre TODOS los `.sh` del repo |
| 4 | REAL | `tests/unit/test_cos_init_py.py::test_installs_hook_to_dest` |
| 5 | REAL | `tests/behavior/test_session_changelog.py::test_creates_changelogs_dir_if_missing` — corre el hook real por subprocess |
| 6 | REAL | `tests/unit/test_smart_truncator.py::test_go_test_extracts_fail_status` |
| 7 | REAL | `tests/unit/test_model_router.py::test_known_model_returns_dict` |
| 8 | REAL | `tests/unit/test_sprint_test_aggregator.py::test_detect_recent_sessions_sorts_by_epoch_prefix` |
| 9 | **EXISTENCE** | `tests/contracts/test_proof_drill_registry.py::test_selectors_docs_and_automated_checks_resolve` — solo `.exists()`; defendible como integridad de manifest, pero viola la regla en su letra |
| 10 | REAL | `tests/unit/test_history_sanitization.py::test_preserve_conflicts_detects_literal_against_regex` |
| 11 | REAL | `tests/unit/test_peer_card.py::test_update_rejects_secrets_without_partial_write` |
| 12 | REAL | `tests/unit/test_cos_yaml_readers.py::test_happy_path_nested_value` — escribe config, corre el gate, verifica el valor parseado |
| 13 | REAL | `tests/unit/test_record_completion.py::test_truncates_to_100` |
| 14 | REAL | `tests/unit/test_goal_evaluator.py::test_evaluate_read_only_on_complete_path` |
| 15 | REAL | `tests/unit/test_dead_letter_queue.py::test_non_existent_dlq_file_list_returns_empty` |
| 16 | REAL | `tests/unit/test_hook_tuner.py::test_format_report_contains_hook_name` |
| 17 | REAL | `tests/unit/test_safe_engram_contract.py::test_is_dataclass` — test de contrato con racional documentado |
| 18 | REAL | `tests/unit/test_agent_bus.py::test_read_events_filters_by_time` |
| 19 | REAL | `tests/unit/test_return_contract_parser.py::test_parse_current_agent_preamble_contract_shape` |
| 20 | REAL | `tests/unit/test_trust_report_schema.py::test_high_lower_bound` — test de valor frontera |

**Resultado del muestreo: 19/20 = 95% ejercitan comportamiento real.**

### Convergencia de dos métodos independientes

| Método | Resultado |
|---|---|
| Muestreo manual (n=20, adjudicado leyendo el AST de cada función) | **95.0%** |
| Clasificador mecánico sobre las 14.779 funciones | **97.1%** |

Los dos métodos convergen. Se reporta **97.1%** como cifra de corpus completo y **95%** como cota del muestreo.

### Honestidad metodológica: dos clasificadores previos fueron descartados

Este número costó tres iteraciones, y las dos primeras estaban mal:

1. **v1** (`testquality.py`) clasificó 32.6% como "THIN" por tener 1 solo assert → **falso positivo**. Al leerlos, `assert score_to_status(90) == 'HIGH'` es un test de frontera legítimo. Un assert no es debilidad.
2. **v2** (`testquality2.py`) dio 54% real porque solo reconocía imports `from cos_lib.` → **falso negativo**: muchos tests importan vía `sys.path` (`from smart_truncator import ...`).
3. **v3** (`testquality3.py`) construye el set de módulos de producción desde los nombres reales del repo. Coincide con la adjudicación manual en 19/20.

Además, 253 de los 356 tests inicialmente contados como "sin assert" usan `self.assertX` de unittest — assert real que el chequeo de `ast.Assert` no ve. **Solo 73 son genuinamente sin aserción.**

### Desglose final (14.779 funciones de test)

| Categoría | Count | % |
|---|---:|---:|
| Ejercitan comportamiento real | 14.355 | **97.1%** |
| Existence-only (viola regla propia) | 226 | 1.53% |
| Tautología pura (solo literales) | 125 | 0.85% |
| Genuinamente sin assert | 73 | 0.49% |

Complemento: **736 funciones de test en Go** + 19 archivos de test en Bash.

**Dónde se concentra lo débil** (`tests/unit` 411 de los 707 tests marcados existence/no-assert):
`test_skill_routing.py` (42), `test_qwen_provider.py` (37), `test_orchestrator_fallback.py` (29), `test_dispatch.py` (28), `test_agent_qwen_bridge.py` (22).

**Veredicto sobre la regla del repo:** se cumple en el **98.5%** de los casos. 226 violaciones reales sobre 14.779.

---

## Hotspots: 15 archivos más grandes

Symlink-deduplicado. Comando: `scratchpad/hotspots.py`.

| LOC | Archivo |
|---:|---|
| 2050 | `scripts/cos_init.py` |
| 2004 | `cos_lib/skill_router.py` |
| 1813 | `scripts/cos_work_inventory.py` |
| 1703 | `cos_lib/routing_benchmark.py` |
| 1559 | `scripts/acc_pipeline.py` |
| 1510 | `cos_lib/rate_limiter.py` |
| 1482 | `tests/behavior/test_singularity.py` |
| 1380 | `bin/cognitive-os.sh` |
| 1308 | `cos_lib/singularity.py` |
| 1307 | `cos_lib/reverse_engineer.py` |
| 1304 | `cos_lib/repo_analyzer.py` |
| 1164 | `cos_lib/system_graph.py` |
| 1153 | `cmd/cos/internal/installer/installer_test.go` |
| 1135 | `tests/unit/test_agent_bus.py` |
| 1098 | `cos_lib/history_sanitization.py` |

**No hay dios-módulo.** 2050 líneas sobre 624K LOC es 0.3%.

### Funciones monstruo (las 8 peores de 227 con ≥80 líneas)

| Líneas | Función |
|---:|---|
| 977 | `cos_lib/skill_router.py::_build_hand_coded_routing_table` |
| 593 | `cos_lib/dispatch.py::dispatch` |
| 412 | `scripts/cos_init.py::main` |
| 373 | `scripts/cos_init.py::_write_structural_instruction_harness_settings` |
| 251 | `cos_lib/claude_executor.py::run` |
| 232 | `cos_lib/history_sanitization.py::execute` |
| 217 | `cos_lib/routing_benchmark.py::_benchmark_one` |
| 191 | `workflows/backend_feature_pipeline.py::run_pipeline` (código deprecado) |

La de 977 líneas es **datos disfrazados de código** — debería ser un manifest YAML, como ya hace el repo con sus otros 129 manifests. La de 593 (`dispatch`) es el verdadero riesgo de mantenibilidad.

---

## Higiene

| Chequeo | Resultado | Comando |
|---|---|---|
| TODO/FIXME/HACK en código no-test | **3 marcadores** — y 2 son legítimos (placeholder de template, docstring del propio auditor). El único "real" es un `// TODO` **dentro de un template de generación de código Go** | `git grep -nIE '(TODO\|FIXME\|HACK\|XXX)' -- '*.py' '*.go' '*.sh' '*.rs' \| grep -v '^tests/' \| grep -E ':\s*(#\|//)\s*(TODO\|FIXME)'` |
| `raise NotImplementedError` | 1 en todo el código no-test | `git grep -nIE 'raise NotImplementedError' -- '*.py' \| grep -v '^tests/' \| wc -l` |
| `pass  # TODO` | **0** | `git grep -nIE '^\s*pass\s*#\s*TODO' -- '*.py'` |
| Paths `/Users/` hardcodeados | **0** (grep exit 1 = cero legítimo, verificado) | `git grep -nI '/Users/' -- '*.py' '*.go' '*.sh' '*.rs' \| grep -v '^tests/'` |
| Literales `/home/` o `/opt/` | 4 | `git grep -nI -E '"/home/[a-z]\|"/opt/[a-z]'` |
| Imports rotos | **0** — las referencias `from lib.` son internas a `workflows/`, resuelven bien en su propio root | `ls -d lib`; `head -20 workflows/DEPRECATED.md` |

La regla del repo contra TODOs en código commiteado **se cumple**. La regla de privacidad local (sin paths de home) **se cumple al 100%**.

---

## No verificado

Lo que este informe **no** puede sostener, y por qué:

1. **No se corrió la suite de tests.** "97% ejercitan comportamiento real" es una propiedad **estructural** (el test invoca código de producción), no una garantía de que pasen ni de que el assert sea fuerte. Un test puede llamar a producción y afirmar algo trivial. **Medir la fuerza de las aserciones requiere mutation testing** — hay un `.cosmic-ray.toml` configurado que no se ejecutó.
2. **Cobertura de líneas desconocida.** No se corrió `pytest --cov`. 97% de tests con comportamiento real no dice qué fracción del código tocan.
3. **Código muerto en Go y Bash no medido.** El análisis de alcanzabilidad cubrió `cos_lib/` (368 módulos) y `scripts/` (731 entrypoints), ambos Python. Los 193 archivos Go y 477 Bash no recibieron el mismo tratamiento.
4. **Duplicación interna de Go no medida.** El hash de funciones fue AST de Python. Go y Bash quedaron fuera.
5. **Calidad de Bash no evaluada.** `shellcheck` no se corrió; las reglas del repo lo marcan como "advisory only / future tier".
6. **`gofmt -l` y `go vet` no ejecutados.** Las reglas del repo admiten deuda preexistente de gofmt en HEAD; no se cuantificó.
7. **El análisis de alcanzabilidad es sintáctico, no dinámico.** Un módulo importado por un script que a su vez nadie invoca cuenta como "vivo". Cadenas de invocación transitivamente muertas escaparían al método.
8. **Los 129 manifests no se validaron contra su consumidor.** Se contó quién los lee, no si el esquema coincide.
9. **Trabajo sin commitear.** La rama tiene cambios en vuelo (`cos-review-approve`, `cos-review-gate`, receipts). Los 2 "scripts sin referencia" son de ese conjunto y podrían wired-earse antes del commit.

---

## Evidencia ejecutable

Scripts deterministas y read-only usados. Viven en el scratchpad de sesión; para durabilidad, los métodos están descritos arriba con suficiente detalle para reconstruirlos:

| Script | Qué mide |
|---|---|
| `inventory.py` | Inventario por lenguaje, symlink-resuelto, solo trackeado |
| `dup_modules.py` | Duplicación exacta de contenido (sha256) entre `cos_lib/` y `packages/*/lib/` |
| `dup_funcs.py` | Duplicación a nivel función (AST normalizado) + funciones ≥80 líneas |
| `deadcode3.py` | Alcanzabilidad estricta de módulos `cos_lib` (solo formas reales de import) |
| `scripts_dead2.py` | Alcanzabilidad de entrypoints `scripts/` vía índice invertido |
| `testquality3.py` | Clasificación de las 14.779 funciones de test + muestreo con semilla |
| `hotspots.py` | Ranking de tamaño symlink-deduplicado |

**Nota de rendimiento:** las versiones ingenuas de los detectores de código muerto (`deadcode.py`, `scripts_dead.py`) son O(n·m) — 368 patrones × 8239 archivos — y superan los 10 minutos. Las versiones útiles (`deadcode3`, `scripts_dead2`) usan una sola pasada con índice invertido y corren en segundos. Si se reconstruyen, hacerlo así.

---

## Recomendaciones priorizadas

Cada una atada a una señal medida, no a preferencia estética.

| P | Acción | Por qué (señal) |
|---|---|---|
| **P1** | Extraer `_build_hand_coded_routing_table` (977 líneas) a un manifest YAML | Es data-as-code; el repo ya tiene 129 manifests y un generador que sirve a Bash/Python/Go. El patrón correcto ya existe en el repo |
| **P2** | Descomponer `cos_lib/dispatch.py::dispatch` (593 líneas) | Es lógica de control, no datos. Es el punto de mayor riesgo de mantenibilidad del kernel |
| **P3** | Convertir las 226 aserciones existence-only en verificaciones de contenido | Viola una regla explícita del repo; 1.53% del corpus |
| **P3** | Unificar `yaml.py` y `scripts/yaml.py` en una sola copia | Ya divergieron (md5 distintos); un shim de compatibilidad que se bifurca es una bomba de tiempo silenciosa |
| **P4** | Decidir el destino de `workflows/` (36 archivos, deprecado desde marzo 2026) | Es deuda honesta y aislada, pero lleva 4 meses marcada |
| **P4** | Documentar la relación entre `cos doctor harness` y `scripts/cos-doctor-harness.sh` | Colisión de nombre sin referencia cruzada; confunde al operador |
