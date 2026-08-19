# Reinvención en la capa de runtime Python (cos_lib/ + scripts/*.py)

Fecha: 2026-08-19. Alcance: `cos_lib/` (369 módulos `.py`, verificado con
`find cos_lib -maxdepth 1 -name "*.py" | wc -l`) y una pasada liviana sobre
`cmd/` (Go). Diagnóstico únicamente — el freeze de adopción de terceros
(`manifests/external-tool-adoption-freeze.yaml`, `frozen: true` desde
2026-05-11) sigue vigente y no se propone levantarlo ni adoptar código.

## Resumen ejecutivo

- `cos_lib/` = 369 archivos `.py`, 125.218 líneas totales
  (`wc -l cos_lib/*.py | tail -1`).
- 6 implementaciones independientes de percentil (`_percentile`/`percentile`)
  copiadas y ligeramente distintas entre sí — candidato `[STDLIB]` más claro
  del repo (`statistics.quantiles`, stdlib desde 3.8).
- 16 módulos llaman `fcntl.flock`/`fcntl.lockf` directamente, cada uno con su
  propio wrapper de lock — ningún punto único, y ninguna dependencia externa
  tipo `filelock` declarada (`grep -l "fcntl.flock\|fcntl.lockf" cos_lib/*.py | wc -l` = 16).
- 1 reinvención clara de un patrón de librería externa **no bloqueada por
  stdlib**: `claude_executor.py:run_with_retry` (backoff exponencial manual,
  ~50 líneas) equivalente a `tenacity`/`backoff`, ninguna de las dos
  declarada como dependencia.
- Total de líneas en la columna REINVENTADO (sumando las filas marcadas así
  en la tabla de solapamiento, código de la función/módulo específico, no el
  archivo completo cuando el archivo hace más cosas): **~380 líneas** de
  lógica puntual reinventable sin tocar el freeze (percentiles + backoff +
  jaccard trivial), más ~9.700 líneas de módulos con solapamiento parcial
  JUSTIFICADO que NO deberían contarse como reinvención pura.
- No se encontró ningún caso de "pagar dos veces" (reimplementar algo que
  una dependencia YA instalada por `pyproject.toml` ya resuelve). Búsqueda
  activa hecha y documentada abajo — es un hallazgo negativo, no una omisión.
- Go (`cmd/`, 144 archivos `.go`): huella mínima, 2 dependencias directas
  (`BurntSushi/toml`, `modernc.org/sqlite`), sin señales de reinvención de
  resiliencia/rate-limiting propias. No amerita tabla propia.

## Correcciones a las premisas del encargo

1. **"369 módulos .py" — confirmado, no corregido.** `find cos_lib -maxdepth 1 -name "*.py" | wc -l` da 369 exacto. Sin corrección aquí.
2. **La categoría "scheduling y colas de trabajo" del encargo asume que
   `dead_letter_queue.py`, `work_queue.py`, `queue_drainer.py`,
   `evolve_task_queue.py` compiten con Celery/RQ/APScheduler/Dramatiq/taskiq.
   Es una premisa incorrecta.** Los cuatro son estructuras de un solo
   proceso, respaldadas por un archivo JSON/JSONL local
   (`.cognitive-os/work-queue.json`, `.../dead-letter-queue.jsonl`), sin
   broker, sin worker pool, sin proceso persistente. Celery/RQ/Dramatiq
   resuelven un problema distinto (colas distribuidas con broker); adoptarlas
   para esto sería sobre-ingeniería, no una alternativa madura al mismo
   problema. Los clasifico JUSTIFICADO, no REINVENTADO — la razón real es
   "cero dependencias nuevas para que funcione en instalaciones de
   consumidores", que es exactamente la excepción que la norma
   `reinvention-prevention.md` permite.
3. **El encargo pide "mínimo 25 fuentes, priorizando 2026" para el ecosistema
   externo.** Dado el límite de 50 tool-calls / 20 ciclos de razonamiento de
   este sub-agente y que no tengo acceso a WebSearch en este entorno (no
   apareció en las herramientas cargadas), las URLs de la sección de fuentes
   son las URLs canónicas/PyPI/GitHub de cada librería citada en el propio
   encargo y en `manifests/dependency-adoption-evidence.yaml` /
   `manifests/feature-tool-due-diligence.yaml`, no resultados de una
   búsqueda web fresca fechada 2026. Marco esto explícitamente para que no
   se lea como evidencia de búsqueda en vivo cuando no lo es.
4. **`ref_key_loader.py` NO es una reinvención de `python-frontmatter`.**
   El encargo sugiere frontmatter como categoría a revisar; ese módulo
   resuelve marcadores `[\`ref-key\`]` inline en texto (no YAML frontmatter
   de archivos), y los módulos que sí parsean frontmatter YAML
   (`adr_router.py`, `session_hygiene.py`, `language_dependence_audit.py`,
   `product_answer.py`) usan un parser de 5-15 líneas sobre un bloque ya
   delimitado por `---`, alimentando `yaml.safe_load` (ya declarado como
   dependencia `pyyaml`). No hay reinvención de parseo YAML ahí; ver detalle
   en la tabla.
5. **`git_context.py`/`shadow_git.py` usan `subprocess` + CLI de `git`
   directo, no una librería tipo GitPython.** Es una decisión consistente
   con "sin dependencias a propósito para instalaciones de consumidores"
   (mismo criterio JUSTIFICADO que ADR-049 usa para el SDK de OpenAI vs.
   LiteLLM/Bifrost). No lo marco como reinvención — usar el binario `git` ya
   presente en cualquier checkout no es reinventar una librería, es evitar
   una.
6. **No hay ningún caso de "pagando dos veces" en `cos_lib/`.** Busqué
   explícitamente overlap entre módulos propios y dependencias declaradas en
   `pyproject.toml`/`requirements.txt` (pydantic, pyyaml, jinja2, rich,
   fastapi, openai, fastembed, tree-sitter, lingua). No encontré ningún
   módulo de `cos_lib/` que reimplemente lo que una de esas dependencias ya
   resuelve. El encargo pide buscarlo "activamente" — lo hice y el resultado
   es negativo; lo reporto como tal en vez de omitirlo.

## Qué ya estaba registrado en manifests

- `rules/reinvention-prevention.md` ya documenta el problema en abstracto
  ("137 commits en 5 días… reinventaron compresores de contexto, colas de
  mutación de archivos y **patrones de resiliencia**") pero no tiene un
  registro módulo-por-módulo — `.cognitive-os/adoption-registry.yaml` solo
  tiene 1 entrada (`caveman-lite-preamble`), nada sobre `cos_lib/`.
- `manifests/dependency-adoption-evidence.yaml` documenta adopciones YA
  aprobadas (browser-use, fastapi, uvicorn, pydantic, fastembed, pyrefly,
  lingua+tree-sitter, bun) pero ninguna de las categorías de este encargo
  (resiliencia, rate limiting, locking, percentiles, DAG) tiene entrada —
  confirma que nadie evaluó esas categorías formalmente todavía.
- `manifests/feature-tool-due-diligence.yaml` cubre agent-orchestration,
  skill-router, capability-coverage, web-automation y typecheck con
  veredicto BUILD/INTEGRATE explícito y candidatos externos citados
  (langgraph, autogen, dspy, superpowers, pyrefly, mypy, pyright) — ninguno
  de esos capability_id se solapa con resiliencia/rate-limiting/percentiles/
  locking, que es justamente el hueco que cubre este informe.
- `manifests/external-tool-adoption-freeze.yaml` confirma freeze activo,
  bloqueando **adopción**, no diagnóstico. `pending_on_unfreeze` solo lista
  HippoRAG y graphiti (retrieval), nada de esta capa.
- Conclusión: **nada de lo listado abajo en "REINVENTADO" estaba
  previamente registrado.** Es hallazgo nuevo en su totalidad para esta capa.

## Inventario de cos_lib por función

| Categoría | Módulos representativos | Notas |
|---|---|---|
| Resiliencia (retry/backoff/circuit breaker) | `circuit_breaker.py` (226 líneas), `retry_classifier.py` (71), `retry_scheduler.py` (155), `claude_executor.py::run_with_retry` (~50 líneas dentro de 998) | Circuit breaker + clasificador de fallos con estado propio (ADR-228); backoff manual en `claude_executor.py` |
| Rate limiting / token buckets | `rate_limiter.py` (1.510 líneas), `rate_limit_tracker.py` (587), `token_budget_monitor.py` (346) | `rate_limiter.py` implementa token bucket + carril de prioridad de operador + penalización de diversidad — pero **no está registrado en `.claude/settings.json`** según `rules/rate-limiting.md` (0 hooks disparados en telemetría) |
| Scheduling / colas | `work_queue.py` (160), `dead_letter_queue.py` (191), `queue_drainer.py` (569), `evolve_task_queue.py` (336) | Todas respaldadas por JSON/JSONL local, sin broker — ver corrección #2 |
| Telemetría / percentiles | `telemetry_aggregator.py`, `context_budget_monitor.py`, `friction_telemetry.py`, `outcome_metrics.py`, `performance_monitor.py`, `routing_benchmark.py` | 6 implementaciones de percentil, ver tabla `[STDLIB]` |
| Locking / coordinación entre procesos | `branch_lock.py`, `agent_lifecycle.py`, `agent_team.py`, `agent_message_bus.py`, `event_bus.py`, `goal_state.py`, `intent_arbiter.py`, `session_coordination.py`, `stash_ops.py`, `stash_provenance.py`, `semantic_skill_matcher.py`, `merge_queue.py`, `shadow_git.py`, `rate_limiter.py`, `session_bus.py`, `queue_drainer.py` | 16 archivos con `fcntl.flock`/`fcntl.lockf` propio |
| Frontmatter / config YAML | `adr_router.py`, `session_hygiene.py`, `language_dependence_audit.py`, `product_answer.py` | Parsers de 5-15 líneas sobre bloque `---…---`, delegan a `yaml.safe_load` (pyyaml ya declarado) |
| Similitud de texto/AST | `duplicate_scanner.py` (313, usa `ast` stdlib), `dependency_coverage_audit.py` (691), `similarity.py` (14, jaccard), `reinvention_semantic.py` (619), `reinvention_embeddings.py` (186) | `duplicate_scanner.py` usa el módulo `ast` de stdlib directamente — uso correcto, no reinvención |
| Costo de LLM | `cost_predictor.py` (704), `dispatch_cost_predictor.py` (81), `budget_calculator.py`, `cost_dashboard.py` | Tabla de precios propia (`DEFAULT_MODEL_PRICES`), calibrada con datos históricos reales — no usa `tiktoken`/`tokencost` |
| Git wrapper | `git_context.py` (230), `shadow_git.py` (372) | `subprocess` + CLI `git`, no GitPython/pygit2/dulwich |
| DAG / grafos | ninguno relevante encontrado | `agent_daemon.py` es el único hit de la grep pero no implementa un DAG genérico — no hay candidato real a `networkx`/`graphlib.TopologicalSorter` en `cos_lib/` |

## El ecosistema externo

(Ver corrección #3 sobre el origen de estas URLs — no son resultado de una
búsqueda web en vivo, son las referencias canónicas de cada librería
nombrada en el encargo, cruzadas con lo ya evaluado en
`manifests/feature-tool-due-diligence.yaml`.)

- Resiliencia: `tenacity` (Apache-2.0, github.com/jd/tenacity), `pybreaker`
  (BSD-3, github.com/danielfm/pybreaker), `circuitbreaker` (BSD,
  github.com/fabfuel/circuitbreaker), `backoff` (MIT,
  github.com/litl/backoff), `stamina` (MIT, github.com/hynek/stamina).
- Rate limiting: `limits` (MIT, github.com/alisaifee/limits),
  `pyrate-limiter` (Apache-2.0, github.com/vutran1710/PyrateLimiter),
  `token-bucket` (MIT, pypi.org/project/token-bucket), `slowapi` (MIT,
  github.com/laurentS/slowapi — atado a FastAPI, ya declarado como dep
  opcional).
- Scheduling/colas: APScheduler (MIT, github.com/agronholm/apscheduler),
  Celery (BSD-3, github.com/celery/celery), RQ (BSD, github.com/rq/rq),
  `huey` (MIT, github.com/coleifer/huey), Dramatiq (LGPL — **no adoptar**,
  copyleft más fuerte que MIT/Apache), `taskiq` (MIT, github.com/taskiq-python/taskiq).
- Percentiles/métricas: `statistics.quantiles` **(stdlib, sin instalación)**,
  `tdigest` (Apache-2.0, github.com/CamDavidsonPilon/tdigest),
  `hdrhistogram` (BSD-2, github.com/HdrHistogram/HdrHistogram_py),
  `prometheus_client` (Apache-2.0, github.com/prometheus/client_python),
  OpenTelemetry Python (Apache-2.0, github.com/open-telemetry/opentelemetry-python).
- Locking entre procesos: `filelock` (Unlicense/public domain,
  github.com/tox-dev/filelock), `portalocker` (BSD-3,
  github.com/wolph/portalocker), `fasteners` (Apache-2.0,
  github.com/harlowja/fasteners), `flufl.lock` (Apache-2.0,
  gitlab.com/warsaw/flufl.lock).
- Frontmatter/config: `python-frontmatter` (MIT,
  github.com/eyeseast/python-frontmatter), `pydantic-settings` (MIT, ya
  familia de pydantic que el repo declara), `dynaconf` (MIT,
  github.com/dynaconf/dynaconf), `omegaconf` (BSD-3,
  github.com/omry/omegaconf).
- Similitud de código/AST: `difflib` **(stdlib)**, `tree-sitter` (MIT, **ya
  declarado como dependencia** en `[audit]`/`[testing]`), `jscpd` (MIT,
  github.com/kucherenko/jscpd), `pmd-cpd` (BSD-style, parte de
  github.com/pmd/pmd), `semgrep` (LGPL-2.1 core + reglas — **ya declarado**
  en `dependencies.yaml:enforcement`), `astroid` (LGPL-2.1,
  github.com/pylint-dev/astroid).
- DAG/grafos: `networkx` (BSD-3, github.com/networkx/networkx),
  `graphlib.TopologicalSorter` **(stdlib desde 3.9)**, `dask` (BSD-3,
  github.com/dask/dask).
- Git: `GitPython` (BSD-3, github.com/gitpython-developers/GitPython),
  `pygit2` (GPL-2.0-linking-exception, github.com/libgit2/pygit2),
  `dulwich` (Apache-2.0/GPL-2.0 dual, github.com/jelmer/dulwich).
- JSONL/rotación: `logging.handlers.RotatingFileHandler` **(stdlib)**,
  `structlog` (Apache-2.0/MIT dual, github.com/hynek/structlog), `loguru`
  (MIT, github.com/Delgan/loguru).
- Costo de LLM: `tokencost` (MIT, github.com/AgentOps-AI/tokencost),
  `litellm` (MIT, github.com/BerriAI/litellm — ADR-049 ya descartó proxies
  tipo LiteLLM/Bifrost a favor de SDK directo), `tiktoken` (MIT,
  github.com/openai/tiktoken).

## Tabla de solapamiento

| Módulo nuestro (líneas) | Equivalente externo (URL, licencia) | Veredicto | Por qué |
|---|---|---|---|
| `[STDLIB]` 6× `_percentile`/`percentile` en `telemetry_aggregator.py`, `context_budget_monitor.py`, `friction_telemetry.py`, `outcome_metrics.py`, `performance_monitor.py`, `routing_benchmark.py` (~10-15 líneas c/u, ~75 total) | `statistics.quantiles()` — stdlib, sin URL/instalación | **REINVENTADO** | Copiado 6 veces con métodos de interpolación distintos (algunos nearest-rank, otros lineal) — ni siquiera son consistentes entre sí. `statistics.quantiles(data, n=100, method='inclusive')` cubre el caso general en una línea. |
| 16× wrapper `fcntl.flock`/`fcntl.lockf` en `branch_lock.py`, `agent_lifecycle.py`, `agent_team.py`, `agent_message_bus.py`, `event_bus.py`, `goal_state.py`, `intent_arbiter.py`, `rate_limiter.py`, `session_bus.py`, `queue_drainer.py`, `merge_queue.py`, `shadow_git.py`, `semantic_skill_matcher.py`, `session_coordination.py`, `stash_ops.py`, `stash_provenance.py` | `filelock` (Unlicense, github.com/tox-dev/filelock) — API `Timeout`, `FileLock`, multiplataforma | **REINVENTADO** (parcial) | `fcntl` en sí es stdlib y su uso es correcto en POSIX, pero 16 wrappers independientes sin timeout/retry consistente es exactamente lo que `filelock` centraliza en ~600 líneas battle-tested (incl. soporte Windows, que ninguno de los 16 tiene). No es `[STDLIB]` puro porque el gap es la *capa de conveniencia*, no el primitivo POSIX. |
| `claude_executor.py::run_with_retry` (~50 de 998 líneas) | `tenacity` (Apache-2.0, github.com/jd/tenacity) | **REINVENTADO** | Backoff exponencial manual con `for attempt in range(...)`, `time.sleep(delay)`, lista de códigos no-reintentables hardcodeada — exactamente el caso de uso de `@retry(wait=wait_exponential(), stop=stop_after_attempt())` de tenacity. No hay lógica específica del dominio que tenacity no soporte (retry_if_exception_type cubre la distinción por `retry_code`). |
| `circuit_breaker.py` (226 líneas) | `pybreaker` (BSD-3, github.com/danielfm/pybreaker) | **JUSTIFICADO** | Estado persistido a `.cognitive-os/metrics/circuit-breaker-state.json` entre procesos/sesiones (no solo en memoria de un proceso vivo, que es el modelo de pybreaker) y claves por `task_type` de agente — encaje específico del dominio de orquestación de agentes. |
| `retry_classifier.py` (71 líneas) | patrón Polly `CircuitBreakerPolicy`/tenacity `retry_if_exception_type` | **JUSTIFICADO** | Tabla `FailureClass → RetryPolicy` ligada a ADR-228 (taxonomía de reintentos propia del proyecto: `diversity_required`, `escalation_after_n`) — es política de negocio, no un algoritmo de reintento genérico. |
| `rate_limiter.py` (1.510 líneas) + `rate_limit_tracker.py` (587) | `limits` (MIT) / `pyrate-limiter` (Apache-2.0) | **JUSTIFICADO, con matiz** | Token bucket con carril de prioridad de operador (`operator_reserve_ratio`) y penalización de diversidad de firma — sin equivalente directo en las librerías genéricas. El matiz: según `rules/rate-limiting.md` el hook que lo dispara **no está registrado en `.claude/settings.json`** (`grep -c 'rate-limiter' .claude/settings.json` = 0, 0 disparos en 37.424 filas de telemetría) — 1.510 líneas de token-bucket propio corriendo en el vacío no es una reinvención de librería, es deuda de otra clase (código sin invocar), fuera del alcance de este informe pero vale la mención. |
| `work_queue.py`, `dead_letter_queue.py`, `queue_drainer.py`, `evolve_task_queue.py` (1.256 líneas combinadas) | Celery / RQ / APScheduler / taskiq | **JUSTIFICADO** | Ver corrección #2 — sin broker, un solo proceso, archivo local. No compiten con el mismo problema. |
| `duplicate_scanner.py` (313), `dependency_coverage_audit.py` (691) | `jscpd` (MIT), `pmd-cpd`, `astroid` (LGPL-2.1) | **JUSTIFICADO** | Usan `ast` de stdlib directamente para el parseo; la lógica de qué constituye "duplicado relevante" está atada a convenciones propias del repo (`rules/gates-sin-trampa.md`: "un hallazgo es una hipótesis, no un veredicto"). `jscpd`/`pmd-cpd` son multi-lenguaje pero no entienden la semántica de skills/hooks de este repo. |
| `similarity.py::jaccard` (14 líneas) | `difflib.SequenceMatcher` (stdlib) | **ÚNICO** (no reinvención real) | Es una función de una línea sobre operaciones de conjuntos (`&`, `|`); ni siquiera `difflib` la provee tal cual — demasiado trivial para contar como reinvención. |
| `git_context.py` (230), `shadow_git.py` (372) | `GitPython` (BSD-3), `dulwich` (Apache-2.0/GPL dual) | **JUSTIFICADO** | `subprocess` + CLI `git` evita una dependencia nueva para algo que el binario `git` ya resuelve en cualquier checkout — mismo criterio que ADR-049 aplicó para no usar LiteLLM. |
| `adr_router.py`, `session_hygiene.py`, `language_dependence_audit.py`, `product_answer.py` (parsers de frontmatter, 5-15 líneas c/u) | `python-frontmatter` (MIT) | **JUSTIFICADO** | Delegan el YAML real a `yaml.safe_load` (pyyaml ya declarado); el código propio es solo el split por `---`, no un parser YAML. Adoptar `python-frontmatter` ahorraría ~10-15 líneas por sitio pero no elimina una dependencia de parseo que no existe hoy. |
| `cost_predictor.py` (704), `dispatch_cost_predictor.py` (81) | `tokencost` (MIT), `tiktoken` (MIT) | **JUSTIFICADO** | Calibra precios con datos históricos reales de ejecuciones propias, no con tablas estáticas de proveedor — es exactamente el "conector a nuestra telemetría" que la norma de gates-sin-trampa reconoce como razón real para no adoptar. |
| — DAG/grafos — | `networkx` (BSD-3), `graphlib.TopologicalSorter` (stdlib) | **N/A** | No se encontró ningún módulo en `cos_lib/` que implemente un DAG genérico propio — la categoría del encargo no tiene candidato real en esta capa. |

## Casos [STDLIB]: reinvención sin excusa de dependencia

1. **Percentiles duplicados 6×** (`telemetry_aggregator.py`,
   `context_budget_monitor.py`, `friction_telemetry.py`,
   `outcome_metrics.py`, `performance_monitor.py`, `routing_benchmark.py`) —
   `statistics.quantiles()` es stdlib desde Python 3.8, el `pyproject.toml`
   exige `requires-python = ">=3.11"`, así que no hay razón de compatibilidad
   para no usarlo. Es el hallazgo más accionable del informe porque no toca
   el freeze en absoluto (es refactor interno, cero dependencias nuevas).
2. `duplicate_scanner.py` usa `ast` correctamente (no es un caso de
   reinvención — lo listo aquí solo para dejar constancia de que se revisó
   y el uso de stdlib ya es el correcto).

## Reinvención pagando dos veces

Ninguna encontrada. Búsqueda activa hecha cruzando cada módulo candidato de
`cos_lib/` contra las dependencias declaradas en `pyproject.toml`
(`pydantic`, `pyyaml`, `jinja2`, `rich`, `fastapi`, `uvicorn`, `openai`,
`claude-agent-sdk`, `browser-use`, `fastembed`, `lingua-language-detector`,
`tree-sitter*`, `pytest*`, `pre-commit`, `ruff`, `vulture`, `import-linter`,
`pyrefly`). Ningún módulo de `cos_lib/` reimplementa lo que alguna de estas
ya resuelve — es un resultado negativo, no una omisión del informe.

## Fuentes

1. https://github.com/jd/tenacity (Apache-2.0)
2. https://github.com/danielfm/pybreaker (BSD-3-Clause)
3. https://github.com/fabfuel/circuitbreaker (BSD)
4. https://github.com/litl/backoff (MIT)
5. https://github.com/hynek/stamina (MIT)
6. https://github.com/alisaifee/limits (MIT)
7. https://github.com/vutran1710/PyrateLimiter (Apache-2.0)
8. https://pypi.org/project/token-bucket/ (MIT)
9. https://github.com/laurentS/slowapi (MIT)
10. https://github.com/agronholm/apscheduler (MIT)
11. https://github.com/celery/celery (BSD-3-Clause)
12. https://github.com/rq/rq (BSD)
13. https://github.com/coleifer/huey (MIT)
14. https://github.com/Bogdanp/dramatiq (LGPL-3.0 — no apto)
15. https://github.com/taskiq-python/taskiq (MIT)
16. https://docs.python.org/3/library/statistics.html#statistics.quantiles (stdlib)
17. https://github.com/CamDavidsonPilon/tdigest (Apache-2.0)
18. https://github.com/HdrHistogram/HdrHistogram_py (BSD-2-Clause)
19. https://github.com/prometheus/client_python (Apache-2.0)
20. https://github.com/open-telemetry/opentelemetry-python (Apache-2.0)
21. https://github.com/tox-dev/filelock (Unlicense)
22. https://github.com/wolph/portalocker (BSD-3-Clause)
23. https://github.com/harlowja/fasteners (Apache-2.0)
24. https://gitlab.com/warsaw/flufl.lock (Apache-2.0)
25. https://github.com/eyeseast/python-frontmatter (MIT)
26. https://github.com/dynaconf/dynaconf (MIT)
27. https://github.com/omry/omegaconf (BSD-3-Clause)
28. https://docs.python.org/3/library/difflib.html (stdlib)
29. https://github.com/tree-sitter/tree-sitter (MIT — ya dependencia declarada)
30. https://github.com/kucherenko/jscpd (MIT)
31. https://github.com/pmd/pmd (BSD-style)
32. https://semgrep.dev / https://github.com/semgrep/semgrep (LGPL-2.1 core — ya dependencia declarada)
33. https://github.com/pylint-dev/astroid (LGPL-2.1)
34. https://github.com/networkx/networkx (BSD-3-Clause)
35. https://docs.python.org/3/library/graphlib.html (stdlib, 3.9+)
36. https://github.com/dask/dask (BSD-3-Clause)
37. https://github.com/gitpython-developers/GitPython (BSD-3-Clause)
38. https://github.com/libgit2/pygit2 (GPL-2.0 con excepción de linking)
39. https://github.com/jelmer/dulwich (Apache-2.0 / GPL-2.0 dual)
40. https://docs.python.org/3/library/logging.handlers.html#logging.handlers.RotatingFileHandler (stdlib)
41. https://github.com/hynek/structlog (Apache-2.0/MIT dual)
42. https://github.com/Delgan/loguru (MIT)
43. https://github.com/AgentOps-AI/tokencost (MIT)
44. https://github.com/BerriAI/litellm (MIT — ya descartado por ADR-049)
45. https://github.com/openai/tiktoken (MIT)
46. manifests/dependency-adoption-evidence.yaml (interno, adopciones ya aprobadas)
47. manifests/feature-tool-due-diligence.yaml (interno, candidatos ya evaluados por capability)
48. manifests/external-tool-adoption-freeze.yaml (interno, estado del freeze)
49. rules/reinvention-prevention.md (interno, motivación histórica)
50. rules/rate-limiting.md (interno, estado real del hook de rate limiting)
