<!-- SCOPE: os-only -->
# Triage de las 52 skills + 17 rules marcadas BORRAR TRAS DECISIÓN

> Fecha: 2026-08-19 · Alcance: las **69** primitivas de tipo `skills` y `rules` del
> censo `lista-de-poda-2026-08-19.md` (los 24 hooks los toma otro agente).
> **No se borró nada.** El único archivo escrito es este informe.
> Colector reproducible en `## Apéndice`.

## Resumen ejecutivo

- Mi lote son **69 primitivas** (52 skills + 17 rules), no 46. Las cubrí **todas**
  con las cuatro columnas medidas; **38** tienen verificación de segunda capa (leí
  la línea del consumidor o abrí el equivalente), **31** quedan con veredicto
  provisional y están listadas al final.
- Skills: **BORRAR 0 · CONSERVAR 17 · REDIRIGIR 8 · NO PUEDO DECIDIRLO 27.**
- Rules: **BORRAR 0 · CONSERVAR 13 · REDIRIGIR 0 · NO PUEDO DECIDIRLO 4.**
- **El cargador apagado no afecta a ninguna de mis 17 rules.** Afecta a las **30**
  rules configuradas en `cognitive-os.yaml:contextual_triggers`, y ninguna de las 17
  está ahí. Para las 17 el cuerpo no tiene vía automática *con el cargador
  registrado o sin él*: tampoco tienen `routing_patterns` (el router registrado
  carga **7 de 131** rules) ni figuran en `templates/agent-mandatory-rules.md`.
- **Ninguna rule ejecuta nada.** Borrar una nunca pierde capacidad: pierde la
  referencia escrita de un gate que sí corre. Y la fricción que elimina es de
  **4-8 tokens** por rule (el marcador en el índice; el cuerpo no se entrega).
  Podar las 17 ahorra ~350 tokens y deja 13 gates vivos sin documento.
- La fricción real está del lado de skills: **~3.900 tokens** entre `description`
  y línea de catálogo para las 52.

## Correcciones a las premisas del encargo

1. **"46" no es el tamaño de mi lote: son 69** (52 skills + 17 rules). El encargo
   usa 46 dos veces; el censo dice 52+17 y lo confirmé contando las filas.
2. **"52 skills … sin consumidor nombrado en ningún hook/script/template" es falso
   para al menos 19.** Medido con `grep -rIl` sobre `hooks/ scripts/ lib/ cos_lib/
   templates/ packages/` y leyendo la línea: `hooks/session-init.sh` (registrado)
   imprime `run /catalog-full` y `Report: /session-report-executive`;
   `hooks/session-wrapup-trigger.sh` (registrado) emite un **`AUTO-TRIGGER:`** que
   nombra `/os-session-wrapup`; `hooks/project-docs-convention.sh` (registrado)
   imprime `run /project-scaffold`; `hooks/skill-failure-monitor.sh` (registrado)
   llama a `skills/repair-skill/SKILL.md` "el consumidor gateado";
   `scripts/check_catalog_sync.py` imprime `Fix: run /add-skill`;
   `scripts/llm_status.py` se declara "companion script for the /llm-status skill".
3. **La premisa 8 del censo ("140 ref-keys apuntan al cargador apagado") mezcla dos
   mecanismos distintos.** `hooks/contextual-rule-loader.sh` **no lee ref-keys**:
   lee `cognitive-os.yaml:rules.loading.contextual_triggers` (30 claves). El
   mecanismo `[\`ref-key\`]` lo consume `cos_lib/ref_key_loader.py` desde
   `hooks/inject-phase-context.sh`, que **sí está registrado**
   (`grep -c inject-phase-context .claude/settings.json` → 1). O sea: el cargador
   apagado no es "el único consumidor" de los ref-keys, y los ref-keys no dependen
   de él.
4. **Pero el expansor registrado tampoco expande los 140.** `inject-phase-context.sh`
   expande su propio `CONTEXT_BUF`; los únicos marcadores que emite son los
   literales `[\`ref-key\`]` y `[\`rule-name\`]` de su documentación.
   `rules/RULES-COMPACT.md` nunca se pasa por `expand()`. Las dos afirmaciones
   opuestas ("los ref-keys están vivos" / "están muertos") son falsas: el mecanismo
   corre, sobre otro texto.
5. **Hay una tercera vía de rules que el censo no nombra y está viva:**
   `hooks/rule-router-prompt-suggest.sh` (registrado) corriendo
   `cos_lib/rule_router.py`. `.cognitive-os/metrics/rule-suggestion.jsonl` tiene
   77 KB y su última línea es de hoy 23:28. Cubre **7 de 131** rules — las que
   tienen `routing_patterns` en frontmatter. Ninguna de mis 17 la tiene.
6. **"Buscá activamente el caso de la skill duplicada en `.claude/plugins/
   hermes-agent`": lo busqué y dentro de mis 52 no hay ninguna.** El submódulo
   expone 71 `SKILL.md`; el cruce por nombre contra mis 52 da **0**. Las dos
   duplicaciones que encontró la auditoría de reinvención
   (`systematic-debugging`, `test-driven-development`, ambas en
   `hermes-agent/skills/software-development/`) corresponden a skills nuestras que
   **no están en la lista de poda** — el hallazgo es real y sigue abierto, pero cae
   fuera de mi lote.
7. **`scaffold-project` y `project-scaffold` no son duplicados**, aunque el nombre
   invita a borrar uno: el primero arma el árbol `docs/` de 10 categorías (ADR-054),
   el segundo arma `.claude/` y genera rules/skills/hooks desde
   `detected-stack.json`. Riesgo de nombre, no deuda.
8. **`skills/eval-repo` se declara a sí misma obsoleta**: su `description` empieza
   con `DEPRECATED — renamed to /repo-scout`. El censo la puso en la lista genérica
   de "auditoría y meta-análisis" sin ese dato, que es el que decide.
9. **`rules/encargo-refutable.md` sí llega a todos los sub-agentes, pero por copia.**
   El texto "The Brief Is Refutable" vive en `templates/agent-mandatory-rules.md`,
   que inyecta `hooks/subagent-context-injector.sh` en `SubagentStart` (registrado):
   lo recibí en mi propio contexto. El template **no cita** el archivo de rule, y la
   rule declara el template en `related:`. Son dos copias de la misma doctrina sin
   ningún test que las ate — eso es una fuente de deriva, no una duplicación
   borrable.
10. **Verifiqué la premisa de propiedad antes de escribir**: `git status --short`
    muestra 20+ archivos modificados por otras sesiones (hooks/, reports `-latest`),
    ninguno es mi ruta de informe. No commiteo, no pusheo, no borro, no toco
    `.cognitive-os/metrics/`.

## Por qué skills y rules no se miden como hooks

Un hook deja rastro porque **se ejecuta**: `hook-timing.jsonl` lo cuenta. Una skill y
una rule **no se ejecutan, se entregan a un contexto**. Su "actividad" es una cadena
de entrega, y la pregunta correcta es *¿existe la vía y llega hasta el final?*.

Vías reales, verificadas en este repo:

| Vía | Estado | Cobertura |
|---|---|---|
| Listado de skills del arnés (name + `description`) | **viva** — la recibí en mi contexto | 197 entradas de `.claude/skills/` |
| `skills/CATALOG-MICRO.md` | **puntero**, no inyección: `session-init.sh` solo imprime el nombre del archivo | 51 de mis 52 tienen línea |
| `rules/RULES-COMPACT.md` | **viva** — es instrucción de proyecto, la recibí verbatim | las 17 tienen su ref-key |
| `templates/agent-mandatory-rules.md` (SubagentStart) | **viva** | 9 rules nombradas; **0 de mis 17** |
| `cos_lib/rule_router.py` vía `rule-router-prompt-suggest.sh` | **viva** | **7 de 131** rules |
| `cos_lib/ref_key_loader.py` vía `inject-phase-context.sh` | **viva pero sobre otro texto** | 0 ref-keys de RULES-COMPACT |
| `hooks/contextual-rule-loader.sh` | **apagada** (no registrada) | cubriría 30 rules; 0 de mis 17 |
| Puntero emitido por un hook/script registrado (`run /skill`) | **viva** | 19 de mis 52 skills |

Instrumentos que **no** sirven de prueba de desuso, y por qué:
`skill-invocation-logger` tiene 6 disparos en 269.876 eventos; `skill-usage.jsonl`
pesa 1,4 KB; `skill-suggestion.jsonl` solo graba el **top-1** por prompt. Cero en
cualquiera de los tres es cero-medición, no cero-uso. Por eso **ninguna fila de este
informe usa "0 invocaciones" como argumento**: el argumento siempre es *existe o no
existe una vía de entrega nombrada*.

## Tabla ordenada por fricción de contexto

`fricción` = tokens de `description` en `SKILL.md` (lo que viaja en el listado del
arnés) + tokens de su línea en `CATALOG-MICRO.md`. `asientos` = archivos de
`manifests/` que la nombran. `tests` = archivos de `tests/` que la nombran.

| Fricción | Skill | Vía de entrega verificada | Qué se rompe si se saca | Veredicto |
|---|---|---|---|---|
| 137 | `plan-chore` | referida por `plan-feature`/`plan-chore` en `packages/sdd-compound` | 2 asientos + 3 tests + la tríada plan-feature/plan-bug/plan-chore queda coja | CONSERVAR |
| 123 | `llm-status` | `scripts/llm_status.py` se declara su "companion script" | script huérfano + 4 asientos + 3 tests | CONSERVAR |
| 107 | `cos-maintainer-operations` | ninguna nombrada | 4 asientos + 2 tests (inventario) | NO PUEDO DECIDIRLO |
| 102 | `analyze-improvements` | citada por `skills/self-improve` y `review-output` | 5 asientos + 1 test + 2 skills con puntero roto | NO PUEDO DECIDIRLO |
| 100 | `os-session-wrapup` | **`AUTO-TRIGGER:` de `hooks/session-wrapup-trigger.sh` (registrado)** | el hook emite un auto-trigger a una skill inexistente: instrucción obligatoria apuntando al vacío | CONSERVAR |
| 98 | `compat-test` | ninguna nombrada | 3 asientos + 2 tests | NO PUEDO DECIDIRLO |
| 97 | `session-report-executive` | `hooks/session-init.sh:328` imprime `Report: /session-report-executive` | puntero roto en el arranque de **cada** sesión | CONSERVAR |
| 96 | `rules-export` | `scripts/rules_export.py:103` imprime `Re-run /rules-export` | puntero roto en el output del script + 4 asientos | CONSERVAR |
| 95 | `adr-tombstone` | `scripts/cos_daemon.py` tiene el intent `adr-tombstone-request`; `manifests/session-coordination-contract.yaml` | lado operador de un intent del daemon + 7 asientos + 6 tests | CONSERVAR |
| 95 | `apply-improvements` | citada por `skills/self-improve` | 5 asientos + 1 test | NO PUEDO DECIDIRLO |
| 93 | `pattern-audit` | los hits de `scripts/` son otros audits homónimos (coincidencia) | 6 asientos + 2 tests | NO PUEDO DECIDIRLO |
| 93 | `test-contract-repair` | `scripts/test_run_inventory.py:357` cita `skills/test-contract-repair/SKILL.md` como clasificación final | el script referencia un archivo que no existiría + `proof-drill-registry.yaml` | CONSERVAR |
| 91 | `eval-repo` | **se autodeclara `DEPRECATED — renamed to /repo-scout`** | 3 asientos + 3 tests; capacidad: nada, está en `skills/repo-scout` | **REDIRIGIR** |
| 91 | `research-protocol` | ninguna; `rules/research-first-protocol.md` + `skills/deep-research` cubren el mismo terreno | 4 asientos + 1 test | **REDIRIGIR** |
| 89 | `project-scaffold` | `hooks/project-docs-convention.sh:250` imprime `run /project-scaffold` | consejo roto justo cuando falta `docs/` | CONSERVAR |
| 89 | `deep-tool-research` | ninguna; `CLAUDE.md` empareja `/repo-forensics` (superficie) con `/reverse-engineer` (profundidad) | 3 asientos + 4 tests | **REDIRIGIR** |
| 85 | `coordination-status` | `templates/edit-conflict-response.md` la nombra | 8 asientos (incluye `session-coordination-contract`) + 2 tests | NO PUEDO DECIDIRLO |
| 83 | `install-skill` | `scripts/cos-install-skill` es el ejecutor real | 5 asientos + 2 tests; la capacidad vive en el script | NO PUEDO DECIDIRLO |
| 81 | `scaffold-project` | ninguna nombrada (**no** es duplicado de `project-scaffold`) | 3 asientos + 4 tests | NO PUEDO DECIDIRLO |
| 81 | `primitive-surface-reduction` | `scripts/primitive_surface_reduce.py` + `scripts/cos-weekly-primitive-gap.sh` | 4 asientos + 3 tests; script queda sin cara operable | CONSERVAR |
| 80 | `generate-config` | ninguna nombrada | 3 asientos + 2 tests | NO PUEDO DECIDIRLO |
| 79 | `detect-stack` | consumida conceptualmente por `project-scaffold` (`detected-stack.json`) | 4 asientos + 2 tests | NO PUEDO DECIDIRLO |
| 79 | `cos-install-operations` | ninguna nombrada | 5 asientos + 2 tests | NO PUEDO DECIDIRLO |
| 77 | `review-output` | `packages/agent-lifecycle/skills/review-output` es la misma skill | 4 asientos; `rules/agent-output-reading` + `skills/self-review` cubren la capacidad | **REDIRIGIR** |
| 77 | `install-hook` | `scripts/cos-install-hook` es el ejecutor | 5 asientos + 4 tests | NO PUEDO DECIDIRLO |
| 77 | `detect-patterns` | `hooks/pattern-check.sh` la nombra dos veces pero **ese hook no está registrado** (`grep -c` → 0) | 3 asientos + 1 test; el puntero ya está muerto | NO PUEDO DECIDIRLO |
| 77 | `primitive-usage-map` | `scripts/primitive_usage_map.py` + `cos-weekly-primitive-gap.sh` | 6 asientos + 4 tests | CONSERVAR |
| 76 | `docs-execution-audit` | `templates/adoption-tiers.md.j2` | 5 asientos + 1 test | NO PUEDO DECIDIRLO |
| 71 | `synthesize-skill` | `cos_lib/skill_synthesizer.py:324`: "operator-gated through /synthesize-skill" | el gate operador del sintetizador se queda sin puerta | CONSERVAR |
| 70 | `validate-release` | ninguna; `rules/release-publishing.md` la supone | 5 asientos + 2 tests; la rule queda sin ejecutor | NO PUEDO DECIDIRLO |
| 69 | `vuln-remediation-flow` | ninguna nombrada | 5 asientos + 2 tests | NO PUEDO DECIDIRLO |
| 66 | `repair-skill` | `hooks/skill-failure-monitor.sh:12` (registrado) la llama "the gated consumer" | la cola de reparación queda sin consumidor | CONSERVAR |
| 66 | `push-release` | ninguna; ver `release-publishing` | 5 asientos + 1 test | NO PUEDO DECIDIRLO |
| 64 | `catalog-full` | `hooks/session-init.sh:216` imprime `run /catalog-full for details` | puntero roto en **cada** arranque de sesión | CONSERVAR |
| 62 | `sdd-compound` | `packages/sdd-compound/` es el paquete homónimo | 5 asientos + 3 tests | NO PUEDO DECIDIRLO |
| 62 | `recall-search` | ninguna; el arnés expone `mcp__ccd_session_mgmt__search_session_transcripts` y Engram `mem_search` | 5 asientos + 1 test; capacidad: cubierta y mejor | **REDIRIGIR** |
| 62 | `install-recommended` | ninguna nombrada | 3 asientos + 2 tests | NO PUEDO DECIDIRLO |
| 61 | `add-mcp` | ninguna nombrada | 3 asientos + 1 test | NO PUEDO DECIDIRLO |
| 60 | `tag-release` | ninguna; ver `release-publishing` | 5 asientos + 3 tests | NO PUEDO DECIDIRLO |
| 59 | `add-skill` | `scripts/check_catalog_sync.py:148` imprime `Fix: run /add-skill` | el gate de catálogo pierde su remedio | CONSERVAR |
| 59 | `add-rule` | `scripts/backfill_session_decisions.py` | 4 asientos + 3 tests | NO PUEDO DECIDIRLO |
| 59 | `add-hook` | `cos_lib/skill_drift_detector.py` la nombra | 4 asientos + **13 tests** | NO PUEDO DECIDIRLO |
| 58 | `lean-code` | ninguna; el arnés trae la skill nativa `simplify` (mismo objetivo) | 4 asientos + 2 tests | **REDIRIGIR** |
| 58 | `bump-version` | ninguna; ver `release-publishing` | 5 asientos + 3 tests | NO PUEDO DECIDIRLO |
| 58 | `harness-audit` | `packages/verification-audit/skills/harness-audit` es la misma | 3 asientos + 1 test | NO PUEDO DECIDIRLO |
| 53 | `wiki-ingest` | `scripts/cos-wiki-ingest` + `cos_lib/wiki_ingester.py` | 3 asientos + 3 tests; el ingestor queda sin cara | CONSERVAR |
| 53 | `artifact-workflow` | ninguna; **no** es la skill de Artifacts del arnés (habla de work-graph y refutación de claims) | 4 asientos + 2 tests | NO PUEDO DECIDIRLO |
| 52 | `self-improvement-loop` | `scripts/cos-self-improvement-runner` + `self_improvement_discipline_gate.py` | **12 asientos** + 5 tests — la más anclada del lote | CONSERVAR |
| 49 | `component-classifier` | ninguna; **sin línea en `CATALOG-MICRO`** | 4 asientos + 1 test | NO PUEDO DECIDIRLO |
| 43 | `evaluate-plan` | referida por `plan-feature` y `plan-chore` | 4 asientos + 1 test + 2 skills con puntero roto | CONSERVAR |
| 38 | `cognitive-os-benchmark` | ninguna; `skills/so-vs-vanilla` y `skills/arena` hacen la comparación | 4 asientos, 0 tests | **REDIRIGIR** |
| 31 | `squad-manager` | ninguna; `skills/agent-control` + `skills/coordination-status` + `rules/squad-protocol` | 3 asientos + 2 tests | **REDIRIGIR** |

### Las 17 rules

Fricción marginal = tokens que se ahorran sacando su marcador del índice. El cuerpo
**no se entrega por ninguna vía automática**, así que no cuenta como fricción.

| Marginal | Rule | Gate/consumidor vivo | Qué se rompe | Veredicto |
|---|---|---|---|---|
| 150 | `session-close-doc-truth` | `scripts/cos-adr-close` + `manifests/documentation-truth-claims.yaml` | sección 16 entera del índice + el criterio que cita `/session-wrapup` | CONSERVAR |
| 89 | `lane-taxonomy` | `.cognitive-os/test-lanes.yaml` + `cos-test` (ADR-072) | sección 15 + 2 tests | CONSERVAR |
| 24 | `python-naming` | `tests/audit/test_python_naming.py` (gate vivo) | el gate queda sin documento; 5 tests la nombran | CONSERVAR |
| 6 | `ai-provider-identity` | `hooks/ai-provider-identity-guard.sh` + `cos_lib/ai_provider_identity_guard.py` + 3 perfiles de seguridad | hook activo sin doctrina escrita; **8 tests** | CONSERVAR |
| 8 | `clean-room-detection-limits` | `hooks/clean-room-ast-similarity-gate.sh` + `scripts/cos_clean_room_ast_similarity.py` | el límite tier-2 (ADR-271) deja de estar escrito | CONSERVAR |
| 6 | `local-privacy-hygiene` | citada por `hooks/skill-feedback-tracker.sh` y `scripts/cos-patch-release` | 3 tests + 2 consumidores sin referencia | CONSERVAR |
| 4 | `bash-naming` | `tests/audit/test_bash_naming.py`; 2 hooks la citan en comentario | gate sin documento | CONSERVAR |
| 6 | `routing-quality-gate` | `scripts/routing_quality_gate.py` + `scripts/cos-routing-max-gate` | gate sin documento | CONSERVAR |
| 5 | `memory-governance` | `cos_lib/memory_governance.py` (ADR-261) | biblioteca sin doctrina | CONSERVAR |
| 4 | `retry-contract` | `scripts/cos_agent_flicker_report.py` (ADR-228) | taxonomía de reintentos sin fuente; 150 tokens de archivo | CONSERVAR |
| 5 | `encargo-refutable` | su contenido se entrega **copiado** en `templates/agent-mandatory-rules.md` | queda una copia sin fuente canónica; 2 tests | CONSERVAR |
| 7 | `routing-pattern-authoring` | par documental de `routing-quality-gate` | 1 test | CONSERVAR |
| 5 | `release-publishing` | sus ejecutores son 4 skills de este mismo lote | si se van las 4 skills *y* la rule, no queda nada del flujo de release | CONSERVAR |
| 7 | `codebase-memory-directive` | menciona `scripts/check_codebase_memory_readiness.py` (ADR-343) | 1 test | NO PUEDO DECIDIRLO |
| 7 | `recommendation-grounding` | parte de la sección 12 (research-first) | 3 tests | NO PUEDO DECIDIRLO |
| 7 | `skill-invocation-mandatory` | el logger que la mediría ve 6 de 269.876 eventos | 1 test | NO PUEDO DECIDIRLO |
| 5 | `cosd-secure-api` | `tests/contracts/test_cosd_auth_primitives.py` | contrato de auth sin documento | NO PUEDO DECIDIRLO |

## Las REDIRIGIR: qué equivalente ya está en el árbol

Ocho skills cuya capacidad ya está disponible **sin instalar nada**. Borrarlas no
pierde capacidad: la redirige. Las tres primeras son las de evidencia más dura.

| Skill | Equivalente presente | Dónde está | Qué hay que hacer además de borrar |
|---|---|---|---|
| `eval-repo` | `skills/repo-scout` | mismo repo; la propia `description` de `eval-repo` dice `DEPRECATED — renamed to /repo-scout` | 3 asientos + 3 tests + línea de `CATALOG-*` |
| `recall-search` | `mcp__ccd_session_mgmt__search_session_transcripts` (nativo del arnés) y `mem_search` de Engram | herramientas expuestas en esta misma sesión | 5 asientos + 1 test; `packages/recall-search/` queda como paquete a decidir |
| `lean-code` | skill nativa `simplify` del arnés | listado de skills del arnés | 4 asientos + 2 tests |
| `cognitive-os-benchmark` | `skills/so-vs-vanilla` + `skills/arena` | mismo repo | 4 asientos, sin tests |
| `deep-tool-research` | `skills/reverse-engineer` (profundidad) + `skills/repo-forensics` (superficie) | mismo repo; el emparejamiento está escrito en `CLAUDE.md` | 3 asientos + 4 tests |
| `research-protocol` | `skills/deep-research` + `rules/research-first-protocol.md` | mismo repo | 4 asientos + 1 test |
| `review-output` | `skills/self-review` / `skills/code-review` + `rules/agent-output-reading.md` | mismo repo | 4 asientos; existe además una copia en `packages/agent-lifecycle/` |
| `squad-manager` | `skills/agent-control` + `skills/coordination-status` + `rules/squad-protocol` | mismo repo | 3 asientos + 2 tests |

**Lo que busqué y no encontré:** ninguna de las 52 tiene equivalente por nombre en
`.claude/plugins/hermes-agent` (71 `SKILL.md`, cruce = 0). Las dos duplicaciones MIT
conocidas (`systematic-debugging`, `test-driven-development`) son de skills que **no
están en la lista de poda**; ese hallazgo sigue abierto y no es de mi lote.

**Cierre de asientos, en un comando:** `scripts/cos_primitive_closure_check.py` es el
entrypoint declarado para dejar en lockstep lifecycle metadata, overlay `.ai`,
reportes ACC/readiness, locks de registro, proyecciones de arnés y pruebas de
portabilidad. Sin correrlo, cada borrado se descubre "una lane a la vez" por cascada
de tests.

## El efecto del cargador contextual no registrado

Verificado: `grep -c 'contextual-rule-loader' .claude/settings.json` → **0**
(las dos apariciones en `settings.local.json` son permisos de Bash, no registro).
El archivo existe: `hooks/contextual-rule-loader.sh` → symlink a
`packages/context-optimization/hooks/contextual-rule-loader.sh`.

Ahora bien, **a cuántas rules afecta**:

- El cargador **no lee ref-keys**. Lee `cognitive-os.yaml:rules.loading.contextual_triggers`:
  **30 claves** (`auto-repair`, `trust-score`, `blast-radius`, `token-economy`…).
  Ésas son las rules cuyo cuerpo no llega por esta vía. **Cero de mis 17** están ahí.
- Los **140 ref-keys** de `RULES-COMPACT.md` son otro mecanismo, con otro consumidor
  (`cos_lib/ref_key_loader.py`) invocado desde un hook **registrado**
  (`inject-phase-context.sh`). Pero ese hook expande solo su propio buffer de
  contexto de fase: `RULES-COMPACT.md` nunca pasa por `expand()`. Los ref-keys del
  índice no se expanden — no por el cargador apagado, sino porque **nadie los pasa
  por el expansor**.
- La vía viva y registrada es `cos_lib/rule_router.py` desde
  `hooks/rule-router-prompt-suggest.sh`, que carga **7 de 131** rules (las que
  tienen `routing_patterns` en frontmatter) y escribe en `rule-suggestion.jsonl`
  (77 KB, última línea de hoy). Ninguna de mis 17 es routable.

Consecuencia para la decisión: para las 17, **registrar el cargador no cambiaría
nada** (no tienen trigger), y **borrarlas no apaga ningún comportamiento** (ninguna
ejecuta). La única pérdida es la referencia escrita de 13 gates que sí corren, contra
un ahorro de ~350 tokens de índice. Por eso las 17 van a CONSERVAR o NO PUEDO
DECIDIRLO, y ninguna a BORRAR: es un mal cambio por costo/beneficio, no por riesgo.

La palanca real sobre rules, si se quiere fricción menos: las **30** con trigger
configurado y cargador apagado son deuda de decisión (registrar o borrar el
mecanismo), y las **124 sin `routing_patterns`** son la brecha del router vivo.

## Las que no alcancé a mirar

Cubrí las 69 con las cuatro columnas. Lo que **no** alcancé, dicho sin adorno:

- **31 filas con veredicto provisional** (27 skills + 4 rules): tienen medición pero
  no verificación de segunda capa. Son todas las marcadas `NO PUEDO DECIDIRLO`. Lo
  que falta en cada una es lo mismo: leer el `SKILL.md` completo y decidir si la
  capacidad que describe existe en otro lado. Las 4 de release
  (`bump/tag/push/validate-release`) conviene decidirlas **juntas y con
  `rules/release-publishing.md`**, no de a una.
- **No ejercité ninguna skill ni cargué ninguna rule.** Mi evidencia es "existe la
  vía de entrega y termina en algo que existe", no "la vía se disparó y entregó".
- **No abrí los 71 `SKILL.md` de `hermes-agent`**: el cruce con mis 52 fue por
  nombre de directorio. Una duplicación semántica con nombre distinto se me escapa.
- **No medí el listado real del arnés por skill.** Uso `description` de `SKILL.md`
  como proxy; en el listado que recibí, varias de las 52 aparecen solo con el nombre.
  El total de ~3.900 tokens es entonces una **cota superior**.
- **No audité `packages/*/skills/`**: al menos 6 de mis 52 tienen copia ahí
  (`review-output`, `harness-audit`, `squad-manager`, `sdd-compound`,
  `recall-search`, `research-protocol`). Borrar la de `skills/` sin mirar la del
  paquete es exactamente el error que este informe intenta evitar.

## Apéndice: el colector, reproducible

```bash
# 1. Vías de entrega (registro de hooks)
grep -c 'contextual-rule-loader' .claude/settings.json          # -> 0
grep -c 'rule-router-prompt-suggest' .claude/settings.json      # -> 1
grep -c 'inject-phase-context' .claude/settings.json            # -> 1

# 2. Cobertura del router de rules vivo
.venv/bin/python3 -c "from cos_lib.rule_router import RuleRouter; r=RuleRouter(); \
print(r.loaded_rule_count, r.routable_rule_count)"              # -> 7 7  (de 131)

# 3. Claves del cargador apagado
sed -n '255,300p' cognitive-os.yaml | grep -E '^\s{6}[a-z0-9-]+:' | wc -l   # -> 30

# 4. Cruce contra el submodulo MIT vendorizado
find .claude/plugins/hermes-agent/skills -name SKILL.md | sed 's|.*/skills/||;s|/SKILL.md||'

# 5. Consumidores nombrados, por skill
grep -rIl '<skill>' hooks/ scripts/ lib/ cos_lib/ templates/ packages/

# 6. Friccion de contexto (description + linea de catalogo), asientos y tests
#    Guardar como collect.py y correr: .venv/bin/python3 collect.py
```

```python
import re, subprocess
from pathlib import Path

R = Path('.')
micro = (R / 'skills/CATALOG-MICRO.md').read_text().splitlines()
SKILLS = [d.name for d in (R / 'skills').iterdir() if (d / 'SKILL.md').exists()]

def desc_tok(path):
    txt = path.read_text(errors='replace')
    m = re.search(r"^---\n(.*?)\n---", txt, re.S)
    if not m:
        return 0
    d = re.search(r"^description:\s*(.*?)(?=\n[a-zA-Z_-]+:|\Z)", m.group(1), re.S | re.M)
    return len(d.group(1)) // 4 if d else 0

def hits(name, *roots):
    out = subprocess.run(['grep', '-rIl', '--', name, *roots],
                         capture_output=True, text=True).stdout
    return [ln for ln in out.splitlines() if ln.strip()]

rows = []
for s in SKILLS:
    dt = desc_tok(R / 'skills' / s / 'SKILL.md')
    cat = sum(len(ln) // 4 for ln in micro if re.search(r'\b' + re.escape(s) + r'\b', ln))
    rows.append((dt + cat, s, dt, cat,
                 len(hits(s, 'manifests')), len(hits(s, 'tests')),
                 len(hits(s, 'hooks', 'scripts', 'lib', 'cos_lib', 'templates', 'packages'))))
rows.sort(reverse=True)
print('friccion|skill|desc|catalogo|asientos|tests|consumidores')
for r in rows:
    print('|'.join(map(str, r)))
```

Para rules, el mismo colector cambiando la fuente: presencia del ref-key en
`rules/RULES-COMPACT.md`, presencia de la clave en `cognitive-os.yaml:contextual_triggers`,
presencia en `templates/agent-mandatory-rules.md`, `routing_patterns` en frontmatter,
y conteo en `.cognitive-os/metrics/rule-suggestion.jsonl`.

Exit codes: es un colector, no un gate — siempre 0. Read-only: no escribe fuera de
stdout y no toca `.cognitive-os/metrics/`.
