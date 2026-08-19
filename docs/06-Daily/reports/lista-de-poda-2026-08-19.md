<!-- SCOPE: os-only -->
# Lista de poda — censo de 539 primitivas con cuatro columnas de evidencia

> Fecha: 2026-08-19 · Alcance: **todos** los `hooks/*.sh|*.py` de primer nivel, todos
> los `skills/*/` y todos los `rules/*.md`. No es una muestra.
> **No se borró nada en esta corrida.** El único archivo escrito es este informe.
> Censo reproducible en `## Apéndice`.

## Resumen ejecutivo

- Población real: **215 hooks** archivo regular (+42 symlinks de alias = 257 rutas),
  **193 skills**, **131 rules** → **539 primitivas** distintas.
- **BORRAR YA: 11** (10 skills + 1 hook). **BORRAR TRAS DECISIÓN: 93** (24 hooks +
  52 skills + 17 rules). **CONSERVAR: 28** (28 hooks). **NO PUEDO DECIDIRLO: 407.**
- Si se ejecuta BORRAR YA quedan **538 rutas de 549**: la poda sin decisión es
  **2 %**. El hallazgo central es ese: *no hay materia muerta que se pueda borrar
  sin decidir*. Todo lo inerte está anclado por un asiento de manifest, una línea
  de ratchet o un test. **La poda no es un problema de borrado: es un problema de
  decisión.**
- **De los 215 hooks, cero cumplen las cuatro condiciones de BORRAR YA.** 77 tienen
  actividad cero; de esos, 52 tienen vía de ejecución (dispatcher, hook padre o
  perfil) y los 25 restantes tienen **motivo escrito** en el manifest de
  clasificación. Categoría "olvido": **0 de 215**.
- Fricción medida (269.876 eventos, vivo + 8 archivos rotados): **~22 procesos de
  hook y ~7,9 s de reloj acumulado por cada tool call**; 23 hooks y **276 s por
  `Stop`**. El que más interrumpe no es un hook muerto: es
  `protected-config-write-guard`, que **bloqueó 1.678 veces** sobre 11.941 corridas.
- **La palanca de fricción más grande no es borrar.** `cognitive-os.yaml:586`
  tiene `profile: default | full`; el 90 % del costo por tool call lo ponen los
  ~22 hooks que ya están encendidos en `default`, no los 104 candidatos a poda.

## Correcciones a las premisas del encargo

1. **"257 hooks" es el conteo de rutas, no de primitivas.** `find hooks -maxdepth 1`
   da **215 archivos regulares** `.sh|.py` y **42 symlinks de alias**. Al clasificar
   por primitiva, la población es 215. (El informe `reinvencion-hooks-policy` del
   mismo día dice 249 contando `hooks/**` recursivo; el encargo mezcla las tres
   cifras.)
2. **"119 skills" es falso: son 193** directorios bajo `skills/` (192 con
   `SKILL.md`), y `.claude/skills/` expone **197** entradas al arnés.
3. **"370 módulos" no lo pude verificar y no lo uso.** No hay en el repo un
   denominador llamado "módulos"; no repito el número.
4. **El brief me mandó a usar `hook_test_reality_census.py` como instrumento. Tiene
   un falso negativo que invalida su uso para decidir borrados**, y lo confirmé:
   deriva "registrado" solo de `.claude/settings.json`, y `bash-hot-path-dispatcher.sh`
   (9.644 corridas, 113 `exit 2`) invoca **29 hooks hijos** por ruta directa, sin
   pasar por el wrapper de timing. Esos 29 no dejan telemetría propia y no figuran
   en `settings.json`. Es un **séptimo mecanismo de registro** —indirecto, no de
   omisión— que no estaba en la lista de seis del encargo. La corrección llegó del
   coordinador a mitad de tarea; la verifiqué leyendo `_run_gate` y las líneas
   128-182 del dispatcher antes de incorporarla.
5. **`destructive-git-blocker` NO está muerto: registré 141 `exit 2` suyos** en
   `hook-health` (vivo + archivo). El censo que el brief recomienda lo reporta como
   nunca corrido. Mismo caso `git-commit-scope-guard`, que además es hijo de
   `destructive-git-blocker`.
6. **La premisa "cada fila necesita las cuatro columnas" es incumplible para la
   columna 4 en 539 filas.** El trabajo de campo de absorción cubre **7 familias**,
   no 539 primitivas. Mapear "equivalente nativo" primitiva por primitiva exigiría
   539 verificaciones contra tres arneses. Por eso la columna 4 solo está resuelta
   donde la primitiva cae dentro de una de las 7 familias medidas o donde la
   capacidad envuelta es verificablemente inexistente; el resto va a NO PUEDO
   DECIDIRLO **por esa columna**, que es la causa dominante de las 407 filas.
7. **"Cero actividad" tampoco es medible para skills.** El logger de invocaciones
   (`hooks/skill-invocation-logger.sh`, registrado en `PostToolUse` matcher `Skill`)
   tiene **6 disparos en 269.876 eventos**. O el operador casi nunca usó la
   herramienta Skill, o la invocación por slash no atraviesa ese matcher — **la
   telemetría no distingue las dos cosas**. Cualquier "este skill nunca se usó" es
   por eso indecidible salvo que la capacidad envuelta no exista.
8. **"Los rules están vivos" no se sostiene, pero tampoco su contrario.**
   `hooks/contextual-rule-loader.sh` es el **único** consumidor del mecanismo
   `[`ref-key`]` de `RULES-COMPACT.md` (140 ref-keys) y **no está registrado**
   (`grep -c contextual-rule-loader .claude/settings.json` → `0`). Las reglas llegan
   al agente por otra vía: `templates/agent-mandatory-rules.md` inyectado en
   `SubagentStart`. O sea: hay 140 ref-keys apuntando a un cargador apagado.
9. **Verifiqué la premisa de propiedad antes de escribir**: `git status --porcelain`
   sobre la ruta del informe, vacía. No commiteo, no pusheo, no borro, no toco
   `.cognitive-os/metrics/`.

## Método y su ceguera declarada

Un solo script (`## Apéndice`) une cuatro columnas por fila:

| Columna | Fuente | Comando |
|---|---|---|
| **actividad medida** | `hook-timing.jsonl` + `hook-health.jsonl`, **vivo + los 9 rotados** `.archive/*.gz`; para skills `skill-suggestion/-invocations/-usage/-routing/-metrics/-feedback`; para rules `contextual-rules` + `rule-suggestion` | 269.876 + 89.431 eventos |
| **consumidor** | *de ejecución*: `.claude/settings.json`, `settings.local.json`, `bash-hot-path-dispatcher.sh`, hook padre que lo invoca por ruta, perfiles (`set-security-profile.sh`, `apply-efficiency-profile.sh`, `cognitive-os.yaml`, `harness-projection*.yaml`) | ver script |
| **omisión declarada** | las 6 fuentes del encargo + `hook-vitality-budget.yaml` | 175 de 215 hooks tienen al menos una |
| **equivalente nativo** | tabla de 7 familias de `riesgo-absorcion-arneses-2026-08-19.md`; y para wrappers, si la herramienta envuelta está instalada | `importlib.util.find_spec` |

### Ceguera declarada (leer antes de usar cualquier número de acá)

1. **Los 29 hijos del dispatcher no dejan telemetría.** Actividad 0 para ellos no
   es evidencia de nada. Van todos a NO PUEDO DECIDIRLO.
2. **El wrapper de timing no graba el stdout**, solo `stdout_bytes`. Los hooks que
   deciden por JSON (`permissionDecision`) son **inobservables**, no "incapaces" —
   son 12 según `hook-vitality-budget.yaml`.
3. **La latencia agregada es una cota superior, no la latencia percibida.** Claude
   Code corre en paralelo los hooks que matchean el mismo grupo; el wrapper mide
   cada script por separado. Los "7,9 s por tool call" son la **suma de trabajo**,
   no el retraso de reloj. Lo que sí es exacto es el conteo: **~22 procesos**.
4. **La ventana no es uniforme.** El archivo vivo de `hook-timing` llegó a cubrir
   ~3,6 h; los 8 rotados extienden meses, pero no hay retención garantizada. Un
   hook agregado hace una semana con actividad 0 no es lo mismo que uno de abril.
5. **La columna 4 está sin resolver en la mayoría de las filas** (ver corrección 6).
6. **No audité `packages/*/hooks/`**: el censo mira `hooks/` de primer nivel.
7. **No ejercité ningún hook.** No tracé payloads como sí hizo el agente que
   descubrió el dispatcher. Mi evidencia de "corre" es telemetría + lectura de
   código, no ejecución.

## BORRAR YA, ordenado por fricción eliminada

Criterio de orden: **fricción que elimina**, no líneas. Ninguna de estas 11 filas
interrumpe al dev ni corre por tool call — porque **no quedó ninguna primitiva
inerte que además interrumpa**. El orden real acá es *costo de contexto por sesión*:
los 193 skills inyectan ~4.100 tokens de catálogo (`description` de cada `SKILL.md`)
en **cada** sesión, se usen o no. Borrar 10 saca ~5 % de eso.

| # | Primitiva | Actividad | Consumidor ejec. | Omisión escrita | Equivalente nativo | Fricción que elimina |
|---|---|---|---|---|---|---|
| 1 | `skills/browser-task` | 0 | ninguno | ninguna | **sí** — panel Browser del arnés + `claude-in-chrome` (navigate/read_page/computer) | catálogo + una entrada de skill que compite con la herramienta nativa |
| 2 | `skills/jupyter-execute` | 0 | ninguno | ninguna | **sí** — `NotebookEdit` y lectura nativa de `.ipynb` | ídem |
| 3 | `skills/deepeval-integration` | 0 | ninguno | ninguna | n/a — `deepeval` **no instalado** (`find_spec` → None) y congelado por `external-tool-adoption-freeze.yaml: frozen: true` | catálogo |
| 4 | `skills/promptfoo-integration` | 0 | ninguno | ninguna | n/a — no instalado, congelado | catálogo |
| 5 | `skills/ragas-integration` | 0 | ninguno | ninguna | n/a — no instalado, congelado | catálogo |
| 6 | `skills/strands-evals-integration` | 0 | ninguno | ninguna | n/a — no instalado, congelado | catálogo |
| 7 | `skills/phoenix-trace-ui` | 0 | ninguno | ninguna | n/a — no instalado, congelado | catálogo |
| 8 | `skills/cognee-integration` | 0 | ninguno | ninguna | n/a — no instalado, congelado | catálogo |
| 9 | `skills/memu-context` | 0 | ninguno | ninguna | n/a — no instalado; además Engram cubre memoria | catálogo |
| 10 | `skills/automaker-bridge` | 0 | ninguno | ninguna | n/a — no instalado, sin línea en `requirements` | catálogo |
| 11 | `hooks/rate-limit-protection.sh` | **0** corridas | ninguno (no en `settings.json`, no en dispatcher, no en perfiles) | `classification: deprecated` + comentario en el archivo | n/a | ninguna hoy; saca un archivo cuyo motivo escrito **pide** su borrado |

**Co-borrado obligatorio** (no rompe nada si se hace junto): cada fila arrastra 3-5
asientos en `manifests/` (radar, `external-tools-adoption.yaml`, catálogos de skills)
y tests que solo verifican su existencia: `phoenix-trace-ui` 5, `browser-task` 4,
`wiki-ingest` 3, `cognee-integration` 2, `jupyter-execute` 2, `rate-limit-protection`
4 + 53 menciones en `docs/`. **Ninguno de esos tests ejercita la primitiva**; todos
son referencias de inventario. Si se borra la primitiva y no el asiento, el contrato
de manifests se pone rojo — ese es el único daño, y es autoinfligido.

> `skills/wiki-ingest` quedó **fuera** de esta lista a propósito: no envuelve una
> herramienta verificablemente ausente y no tiene equivalente nativo demostrado.
> Va a BORRAR TRAS DECISIÓN.

## BORRAR TRAS DECISIÓN, con qué se rompe

**93 filas.** Todas sobran hoy; borrarlas cambia algo observable.

### 24 hooks — actividad 0, sin vía de ejecución, con motivo escrito

Lo que se rompe: el contrato de `manifests/hook-registration-classification.yaml`
("todo hook top-level no registrado aparece acá con status y rationale"), la línea
correspondiente de `tests/contracts/EXCLUDED_HOOKS.txt` y la de
`hooks/_lib/registration-allowlist.txt` (dos ratchets que solo pueden encoger — o
sea, sacar la línea **es** el movimiento legal). Lo que se pierde es la capacidad
que el `status` promete a futuro.

| Hook | Status escrito | Qué se pierde al borrarlo |
|---|---|---|
| `agent-output-verifier.sh` | `demoted` | verificación de salida de agente; **6 tests y 38 docs lo nombran** |
| `code-review-on-commit.sh` | `git_or_manual` | code-review automático en commit |
| `cognitive-os-health.sh` | `manual_trigger` | chequeo de salud invocable a mano |
| `conversation-capture.sh` | `future` | captura de conversación (nunca cableada) |
| `cosd-intent-submit.sh` | `manual_trigger` | envío de intent a cosd |
| `guardrails-validator.sh` | `conditional_opt_in` | NeMo Guardrails (servicio no levantado) |
| `infra-intent-detector.sh` | `internal_helper` | detección de intención de infra |
| `jupyter-sandbox.sh` | `conditional_opt_in` | sandbox jupyter (perfil docker `jupyter`) |
| `mlflow-sync.sh` | `conditional_opt_in` | sync a MLflow |
| `notify.sh` | `manual_trigger` | notificaciones |
| `parry-scan.sh` | `conditional_opt_in` | escaneo Parry |
| `pre-cleanup-snapshot.sh` | `manual_trigger` | snapshot previo a limpieza (**red de seguridad**) |
| `pre-commit-gate.sh` | `git_or_manual` | gate de pre-commit; padre de `global-verify.sh` |
| `registration-check.sh` | `manual_trigger` | chequeo de registro de hooks |
| `secret-audit-pre-commit.sh` | `conditional_opt_in` | auditoría de secretos en commit (**`secret-detector` sí corre**, 10.728 veces) |
| `semgrep-scan.sh` | `conditional_opt_in` | semgrep |
| `session-end-cleanup.sh` | `conditional_opt_in` | limpieza tier-1 al cerrar |
| `session-knowledge-extractor.sh` | `future` | extracción de conocimiento de sesión |
| `session-state-save.sh` | `future` | guardado de estado de sesión |
| `singularity-check.sh` | `conditional_opt_in` | MAPE-K (declarado inactivo) |
| `subagent-input-schema-validator.sh` | `conditional_opt_in` | validación de INPUT SCHEMA de sub-agentes |
| `telemetry-budget-violator-detect.sh` | `conditional_opt_in` | detección de violación de presupuesto de telemetría |
| `tool-discovery-trigger.sh` | `future` | descubrimiento de herramientas |
| `worktree-submodule-fix.sh` | `manual_trigger` | fix de submódulos en worktree |

### 52 skills — actividad 0, sin consumidor nombrado en ningún hook/script/template

Lo que se rompe: 2-5 asientos de manifest por skill y, para varios, la **única vía
de operar el SO**. Bloques:

- **Operaciones de release (4)**: `bump-version`, `tag-release`, `push-release`,
  `validate-release`. Borrarlas deja `rules/release-publishing.md` sin ejecutor.
- **Autoría del propio SO (9)**: `add-hook`, `add-mcp`, `add-rule`, `add-skill`,
  `install-hook`, `install-skill`, `install-recommended`, `synthesize-skill`,
  `repair-skill`. Sin ellas el SO se sigue usando pero no se sigue construyendo.
- **Instalación / scaffolding (6)**: `cos-install-operations`,
  `cos-maintainer-operations`, `generate-config`, `project-scaffold`,
  `scaffold-project`, `detect-stack`.
- **Auditoría y meta-análisis (18)**: `pattern-audit`, `docs-execution-audit`,
  `harness-audit`, `primitive-usage-map`, `primitive-surface-reduction`,
  `component-classifier`, `eval-repo`, `detect-patterns`, `catalog-full`,
  `analyze-improvements`, `apply-improvements`, `self-improvement-loop`,
  `review-output`, `evaluate-plan`, `research-protocol`, `deep-tool-research`,
  `rules-export`, `compat-test`.
- **Resto (15)**: `adr-tombstone`, `artifact-workflow`, `coordination-status`,
  `cognitive-os-benchmark`, `lean-code`, `llm-status`, `os-session-wrapup`,
  `plan-chore`, `recall-search`, `sdd-compound`, `session-report-executive`,
  `squad-manager`, `test-contract-repair`, `vuln-remediation-flow`, `wiki-ingest`.

### 17 rules — cuyo único consumidor de ejecución es un cargador apagado

`ai-provider-identity`, `bash-naming`, `clean-room-detection-limits`,
`codebase-memory-directive`, `cosd-secure-api`, `encargo-refutable`, `lane-taxonomy`,
`local-privacy-hygiene`, `memory-governance`, `python-naming`,
`recommendation-grounding`, `release-publishing`, `retry-contract`,
`routing-pattern-authoring`, `routing-quality-gate`, `session-close-doc-truth`,
`skill-invocation-mandatory`.

Lo que se rompe: **cada una tiene entre 1 y 8 tests que la referencian** (medido:
`ai-provider-identity` 8, `python-naming` 5, `local-privacy-hygiene` 3,
`recommendation-grounding` 3...). Y ojo: **varias sí se aplican, pero por hook, no
por el cargador** — `ai-provider-identity` y `bash-naming` tienen 2 hooks cada una,
`local-privacy-hygiene` y `clean-room-detection-limits` 1. Borrar la regla dejaría
al hook sin su documento de referencia. **Estas cuatro no son candidatas reales.**

## CONSERVAR, y por qué

**28 hooks.** Dos motivos, ninguno reemplazable por un arnés.

### A. Coordinación entre sesiones concurrentes (18) — el foso real

La auditoría de absorción encontró que **ningún** arnés cubre esta familia: Claude
Code se acerca con teammates/inbox y `/fork`, pero eso resuelve fan-out *dentro* de
una sesión, no dos sesiones independientes sobre el mismo checkout. Con ocho agentes
escribiendo en este árbol hoy, es la carga que efectivamente se está pagando.

`cross-session-event-emit` (10.702), `post-git-orphan-notifier` (18.464),
`concurrent-write-guard` (1.059), `edit-lock-pre-tool` (1.059),
`edit-lock-drain-parked` (1.029), `untracked-work-preservation-guard` (710, **2
bloqueos reales**), `agent-message-inbox-context` (344),
`cross-session-peer-context` (344), `edit-lock-process-negotiations` (344),
`stash-budget-warn` (344), `branch-ownership-release` (316),
`edit-lock-session-end` (315), `session-start-worktree-nudge` (111), más 5 con
actividad 0 pero **invocados por el dispatcher** (`agent-message-inbox-guard`,
`branch-ownership-lock`, `cross-session-coordination-guard`) o por perfil
(`concurrent-write-guard-codex-proxy`, `worktree-submodule-fix`).

### B. Bloqueadores con veto probado (10 más, sin contar el solapamiento)

Son los únicos con `exit 2` observado en telemetría, o sea los únicos de los que
consta que pueden atajar algo:

| Hook | Corridas | `exit 2` | Nota |
|---|---|---|---|
| `protected-config-write-guard` | 11.941 | **1.678** | 14 % de las tool calls |
| `subagent-budget-enforcer` | 11.403 | 216 | absorbible por `--max-budget-usd` |
| `destructive-git-blocker` | (vía dispatcher) | **141** | el censo lo daba por muerto |
| `bash-hot-path-dispatcher` | 9.644 | 113 | propaga el veto de sus 29 hijos |
| `skill-router-bash-gate` | — | 20 | |
| `confidentiality-enforcer` | — | 9 | |
| `direct-main-guard` | — | 8 | |
| `provenance-scan` | — | 7 | |
| `lethal-trifecta-gate` | 11.941 | 6 | **falso positivo documentado hoy** |
| `destructive-rm-blocker` | (vía dispatcher) | 2 | |

### C. Conservar **y arreglar**: `hooks/secret-detector.sh`

10.728 corridas. Su rama de "el input era 100 % secretos" (líneas 172-188) emite
`permissionDecision: "block"` con `exit 0`. **`block` no es un valor válido** en
ninguno de los dos arneses (`allow | deny | ask`), y no hay `exit 2` de respaldo:
esa rama **falla abierta hoy**. Es una guarda de seguridad que no guarda. No se
borra: se cambia `block` → `deny` y se agrega el `exit 2` de fallback.

## NO PUEDO DECIDIRLO, con el conteo

**407 filas de 539 (75 %).** No es pereza: es el conteo honesto de dónde falta
evidencia, y borrar cualquiera de estas hoy sería a ciegas.

| Tipo | Cantidad | Por qué no puedo |
|---|---|---|
| hooks | **162** | 52 tienen actividad 0 pero vía de ejecución (29 hijos del dispatcher que **no dejan telemetría**, más perfiles y hooks padre): actividad 0 no es evidencia de muerte. Los otros 110 tienen actividad > 0 pero **no tengo la columna 4** — no medí si el arnés hace lo mismo. |
| skills | **131** | 47 con señal de router y 84 nombrados por algún hook/script, pero **la telemetría de invocación tiene 6 filas en total**: no puedo separar "se usa" de "no se registra". Además 170 sugerencias del router cruzaron umbral sobre 51 skills distintos y solo hubo 6 invocaciones — un ratio de ~3,5 % que puede ser "el router falla" o "el operador invoca por otra vía". |
| rules | **114** | Solo 8 de 131 tienen alguna actividad medida. El mecanismo que las cargaría por `ref-key` está apagado, y el que sí corre (`agent-mandatory-rules.md` en `SubagentStart`, 332 disparos) inyecta **una lista fija**, no las 131. No sé cuáles llegan al agente. |

**La causa dominante es la columna 4.** El trabajo de campo de absorción cubre 7
familias; extenderlo por analogía a 539 primitivas sería exactamente el error que
esta sesión ya cometió siete veces. Cerrar estas 407 filas requiere, en orden:
(a) que el wrapper de timing envuelva a los 29 hijos del dispatcher, (b) que la
invocación de skills deje telemetría de verdad, (c) 7 familias más de auditoría de
absorción.

## Las que más molestan de las que quedan

Un dev perdona una capacidad que le falta; no perdona una que lo frena en falso.
Estas son las que quedan **después** de la poda y son las que hay que mirar primero:

1. **`protected-config-write-guard` — 1.678 bloqueos sobre 11.941 corridas.** Una de
   cada siete tool calls que toca config se para. Es el mayor generador de fricción
   del sistema por dos órdenes de magnitud sobre cualquier otro. No sé qué fracción
   son legítimos; **eso es lo primero que hay que medir**.
2. **`quality-duplicates` — 243 segundos por corrida, 306 corridas, 20,6 horas
   acumuladas.** Corre en `Stop`. Es el 85 % de los 276 s de latencia por cierre de
   sesión. Un solo hook.
3. **`lethal-trifecta-gate` — 11.941 corridas, 6 bloqueos, y uno de esos seis fue un
   falso positivo documentado hoy** (impidió a un agente escribir su propio informe).
   Ratio señal/ruido pésimo: corre en cada tool call para atajar seis cosas al año.
4. **`SessionStart`: 27 hooks, 13,2 s de trabajo acumulado antes de que el dev
   escriba nada.** `UserPromptSubmit`: 12 hooks, 10,1 s por prompt.
5. **El catálogo de skills: ~4.100 tokens en cada sesión** por 193 `description`,
   de los cuales el router acertó sobre 51 y se invocaron 6 en total.
6. **140 ref-keys en `RULES-COMPACT.md` apuntando a un cargador desregistrado.** No
   frenan, pero prometen un mecanismo que no existe — y eso hace que un agente
   confíe en que la regla se va a cargar sola.

> **La palanca que el operador tiene y no está en esta lista:** `cognitive-os.yaml:586`
> `profile: default | full`. Los ~22 hooks por tool call son los de `default`. Pasar
> a `full` no reduce fricción: la aumenta. Y al revés — **recortar el perfil `default`
> es una sola decisión que baja la fricción más que borrar las 104 primitivas de las
> dos listas de poda juntas**, porque ninguna de esas 104 corre por tool call.

## Qué hace el SO resultante que ningún arnés haga

Respuesta directa, sin suavizar: **queda poco, y casi todo es coordinación.**

De las **28 primitivas en CONSERVAR, 18 son coordinación entre sesiones
concurrentes** — la única familia de las siete auditadas donde los tres arneses
están en cero. Es literalmente el caso que el encargo anticipó: *"si tu lista deja
quince primitivas y catorce son coordinación entre sesiones, decilo"*. Deja 28, y 18
son eso.

De las 10 restantes (bloqueadores con veto probado), la auditoría de absorción es
inequívoca: **el mecanismo está absorbido en los tres arneses**; lo que no tienen es
el catálogo de reglas. Y la propia doc de Claude Code recomienda `permissions` por
encima de los hooks para el deny duro. O sea: de esos 10, lo defendible no es el
hook, es *saber qué denegar*. Un `permissions` bien escrito reemplaza a la mayoría.

Lo que sigue siendo nuestro, entonces:

1. **Coordinación entre dos sesiones independientes sobre el mismo checkout** —
   locks de edición por archivo, ownership de rama, cola de un solo escritor,
   preservación de trabajo sin commitear. Ningún arnés, ni cerca.
2. **El catálogo de reglas de deny**, no el mecanismo. Frágil: se copia.
3. **El pipeline SDD** (familia 7a: "NO ESTÁ EN SU CAMINO" en los tres) — pero está
   fuera del alcance de este censo, no lo medí.
4. **Engram** — memoria con búsqueda semántica y detección de conflicto, contra
   archivos planos cargados por glob. Gana claro, y tampoco lo medí acá.

Todo lo demás —telemetría de hooks, gobierno de costo, aislamiento por worktree,
enrutamiento de skills, memoria en archivo— está absorbido o en camino, y en dos
casos (worktree, presupuesto duro) la versión nativa es **mejor** que la nuestra.

## Apéndice: el censo, reproducible

Read-only, determinista, sin estado de sesión. Guardar como
`scripts/poda_census.py` y correr con `.venv/bin/python3 scripts/poda_census.py out.json`.

```python
#!/usr/bin/env python3
# SCOPE: os-only
"""Censo de poda — hooks + skills + rules con 4 columnas de evidencia.
Lee telemetria VIVA + ROTADA (.archive/*.gz). Read-only. No borra nada."""
import gzip, json, os, re, glob, sys
from collections import Counter, defaultdict
M = ".cognitive-os/metrics"; A = M + "/.archive"

def jl(prefix):
    """Une el archivo vivo con TODOS los rotados de esa familia."""
    out = []; live = f"{M}/{prefix}.jsonl"
    fs = ([live] if os.path.exists(live) else []) + sorted(glob.glob(f"{A}/{prefix}-*.jsonl.gz"))
    for f in fs:
        op = gzip.open if f.endswith(".gz") else open
        try:
            with op(f, "rt", errors="replace") as fh:
                for L in fh:
                    L = L.strip()
                    if L:
                        try: out.append(json.loads(L))
                        except Exception: pass
        except Exception: pass
    return out, fs

timing, tf = jl("hook-timing"); health, hf = jl("hook-health")
runs = Counter(); ex2 = Counter()
for r in timing + health:
    h = r.get("hook") or ""
    if h:
        runs[h] += 1
        if r.get("exit_code") == 2: ex2[h] += 1

hook_files = [n for n in sorted(os.listdir("hooks"))
              if (n.endswith(".sh") or n.endswith(".py"))
              and os.path.isfile(f"hooks/{n}") and not os.path.islink(f"hooks/{n}")]
sym = [n for n in sorted(os.listdir("hooks"))
       if (n.endswith(".sh") or n.endswith(".py")) and os.path.islink(f"hooks/{n}")]
stem = lambda n: re.sub(r'\.(sh|py)$', '', n)

S = open(".claude/settings.json").read()
reg = set(re.findall(r'hooks/([A-Za-z0-9._-]+\.(?:sh|py))', S))
regl = set()
if os.path.exists(".claude/settings.local.json"):
    regl = set(re.findall(r'hooks/([A-Za-z0-9._-]+\.(?:sh|py))',
                          open(".claude/settings.local.json").read()))
# REGISTRO INDIRECTO: el dispatcher invoca hijos que no figuran en settings.json
# y que NO pasan por el wrapper de timing -> actividad 0 no es evidencia.
disp = set(re.findall(r'"hooks/([A-Za-z0-9._-]+\.sh)"',
                      open("hooks/bash-hot-path-dispatcher.sh").read()))
parent = defaultdict(set); hook_src = {}
for n in hook_files + sym:
    try: hook_src[n] = open(f"hooks/{n}", errors="replace").read()
    except Exception: hook_src[n] = ""
for n, txt in hook_src.items():
    for c in re.findall(r'hooks/([A-Za-z0-9._-]+\.(?:sh|py))', txt):
        if c != n: parent[c].add(n)

wiring_files = [f for f in ["scripts/set-security-profile.sh",
    "scripts/apply-efficiency-profile.sh", "cognitive-os.yaml",
    "manifests/harness-projection.yaml", "manifests/harness-hook-projection-policy.yaml",
    "install.sh", "opencode.json"] if os.path.exists(f)]
wiring = {f: open(f, errors="replace").read() for f in wiring_files}
wired = defaultdict(set)
for f, txt in wiring.items():
    for m in set(re.findall(r'([A-Za-z0-9._-]+\.(?:sh|py))', txt)):
        if m in set(hook_files) | set(sym): wired[m].add(f)

om = defaultdict(list)   # las 6 fuentes de omision declarada + vitality budget
cls = json.load(open("manifests/hook-registration-classification.yaml"))
for e in cls.get("entries", []):
    b = os.path.basename(e.get("path", ""))
    if b: om[b].append("classification:" + e.get("status", "?"))
for L in open("tests/contracts/EXCLUDED_HOOKS.txt"):
    L = L.strip()
    if L and not L.startswith("#"):
        b = os.path.basename(L.split("|")[0].strip())
        if b: om[b].append("EXCLUDED")
for L in open("hooks/_lib/registration-allowlist.txt"):
    L = L.strip()
    if L and not L.startswith("#"): om[L].append("allowlist")
cy = wiring.get("cognitive-os.yaml", "")
for m in re.finditer(r'([A-Za-z0-9._-]+\.sh)(?:(?!\n\s{0,4}-\s).){0,800}?'
                     r'(default_projection:\s*false|projection_note)', cy, re.S):
    om[m.group(1)].append("cognitive-os.yaml:" + m.group(2).split(":")[0])
for n, txt in hook_src.items():
    if re.search(r'#[^\n]*\b(DEPRECATED|superseded|NOT REGISTERED|unregistered'
                 r'|MANUAL_TRIGGER|opt-in|OPT-IN|no registrar)\b', txt[:5000]):
        om[n].append("comentario")
vb = open("manifests/hook-vitality-budget.yaml", errors="replace").read()
for a, b in re.findall(r'([a-z0-9-]+)\s*\((TaskCreated|TeammateIdle)\)', vb):
    om[a + ".sh"].append("vitality:muerto-por-harness")

rows = []
for n in hook_files:
    runtime = []
    if n in reg: runtime.append("settings.json")
    if n in regl: runtime.append("settings.local")
    if n in disp: runtime.append("dispatcher")
    pp = sorted(parent.get(n, set()) - {"bash-hot-path-dispatcher.sh"})
    if pp: runtime.append("hook-padre:" + ",".join(pp[:2]))
    if wired.get(n):
        runtime.append("perfil:" + ",".join(sorted(os.path.basename(x) for x in wired[n])[:2]))
    rows.append(dict(tipo="hook", nombre=n, act=runs.get(stem(n), 0),
                     ex2=ex2.get(stem(n), 0), run=runtime, om=om.get(n, [])))

skills = sorted(d for d in os.listdir("skills") if os.path.isdir(f"skills/{d}"))
sact = Counter()
for pref in ["skill-suggestion", "skill-invocations", "skill-usage",
             "skill-routing", "skill-metrics", "skill-feedback"]:
    for r in jl(pref)[0]:
        c = set(); p = r.get("payload") if isinstance(r.get("payload"), dict) else {}
        for k in ("skill_name", "name", "skill", "target_ref"):
            if r.get(k): c.add(str(r[k]))
            if p.get(k): c.add(str(p[k]))
        for x in c: sact[x.lstrip("/")] += 1
exec_scan = []
for g in ["hooks/*.sh", "scripts/*.py", "scripts/*.sh", "templates/*.md",
          "cos_lib/*.py", ".claude/commands/*.md", "agents/*.md",
          "cognitive-os.yaml", "rules/RULES-COMPACT.md"]:
    exec_scan += [f for f in glob.glob(g) if os.path.isfile(f)]
etxt = {f: open(f, errors="replace").read() for f in exec_scan}
def named(tok):
    return {f for f, t in etxt.items()
            if re.search(r'(?<![A-Za-z0-9_/-])' + re.escape(tok) + r'(?![A-Za-z0-9_-])', t)}
for s in skills:
    rows.append(dict(tipo="skill", nombre=s, act=sact.get(s, 0), ex2=0,
                     run=sorted(os.path.basename(x) for x in named(s))[:3], om=[]))

rules = sorted(os.path.basename(p)[:-3] for p in glob.glob("rules/*.md"))
ract = Counter()
for r in jl("contextual-rules")[0]:
    for n in str(r.get("rules", "")).split(","):
        if n.strip(): ract[n.strip()] += 1
for r in jl("rule-suggestion")[0]:
    if r.get("top_match"): ract[str(r["top_match"])] += 1
    for m in (r.get("matches") or []):
        if isinstance(m, dict) and (m.get("rule") or m.get("name")):
            ract[str(m.get("rule") or m.get("name"))] += 1
compact = open("rules/RULES-COMPACT.md", errors="replace").read()
refk = set(re.findall(r'\[`([a-z0-9-]+)`\]', compact))
mand = open("templates/agent-mandatory-rules.md", errors="replace").read() \
       if os.path.exists("templates/agent-mandatory-rules.md") else ""
for r in rules:
    run = []
    # OJO: hooks/contextual-rule-loader.sh (unico lector de ref-key) NO esta registrado.
    if r in refk: run.append("ref-key(cargador APAGADO)")
    if re.search(re.escape(r) + r'\.md', mand): run.append("agent-mandatory-rules")
    h = named(r) - {"rules/RULES-COMPACT.md"}
    if h: run.append("nombrado:" + ",".join(sorted(os.path.basename(x) for x in h)[:2]))
    rows.append(dict(tipo="rule", nombre=r, act=ract.get(r, 0), ex2=0, run=run, om=[]))

json.dump(dict(pob=dict(hooks=len(hook_files), symlinks=len(sym),
                        skills=len(skills), rules=len(rules)),
               tel=dict(timing_files=len(tf), timing=len(timing), health=len(health)),
               reg=len(reg), disp=sorted(disp), refkeys=len(refk), rows=rows),
          open(sys.argv[1], "w"), indent=1)
print("ok", len(rows), "filas")
```

Fricción (mismo día, mismas fuentes):

```bash
# ~22 procesos de hook y ~7,9 s de trabajo acumulado por tool call
python3 - <<'PY'
import gzip,json,glob
from collections import defaultdict
ms=defaultdict(float); n=defaultdict(int); hk=defaultdict(set); mx=defaultdict(lambda: defaultdict(int))
for f in [".cognitive-os/metrics/hook-timing.jsonl"]+sorted(glob.glob(".cognitive-os/metrics/.archive/hook-timing-*.gz")):
    op=gzip.open if f.endswith(".gz") else open
    with op(f,"rt",errors="replace") as fh:
        for L in fh:
            try: r=json.loads(L)
            except Exception: continue
            e=r.get("event",""); ms[e]+=r.get("duration_ms") or 0; n[e]+=1
            hk[e].add(r.get("hook")); mx[e][r.get("hook")]+=1
for e in sorted(n,key=lambda x:-n[x]):
    oc=max(mx[e].values())
    print(f"{e:16} eventos={n[e]:>7} hooks={len(hk[e]):>3} ocasiones~{oc:>6} "
          f"hooks/ocasion={n[e]/oc:5.1f} ms/ocasion={ms[e]/oc:8.0f}")
PY
```
