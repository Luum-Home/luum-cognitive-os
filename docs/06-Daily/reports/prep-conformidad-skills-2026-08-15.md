# Preparación — conformidad de skills y subagentes con la spec de Agent Skills

**Fecha:** 2026-08-15
**Repo:** `luum-agent-os` · rama `session/21f28a76-audit-2026-08-15`
**Modo:** preparación. **No se aplicó nada.** No se editó ningún archivo trackeado, no se
hizo el `git mv`, no se corrió la suite. Único archivo escrito: éste.
**Degradación declarada:** máquina recién reiniciada (load alto, swap ~74% sobre 4 GB). No
se corrió `pytest` ni ningún gate. Todo lo de abajo sale de lectura y parseo de archivos.
Lo que eso deja sin poder afirmar está en §6.

**Antecedente:** `docs/06-Daily/reports/judge3-conformidad-2026-08-15.md` (misma fecha) cubre
el mismo terreno como diagnóstico. Este informe es el plan aplicable, y **corrige tres de
sus números** — ver §5.

---

## 1. Veredicto

De los 5 defectos: **1 es mecánico** (#4, tres archivos), **2 requieren lockstep** (#1 chico
— dos lectores; #2 grande — 20 lectores de producción), y **2 son decisión del operador
antes de tocar nada** (#3, porque el gate que fuerza el patrón está vivo y el generador
dormido; #5, porque `__contracts__` no es una skill sino un namespace y "arreglarle el
nombre" es elegir qué es).

---

## 2. Tabla de defectos

| # | Defecto | Comando que lo confirma | Arreglo | Clase |
|---|---|---|---|---|
| 1 | `agents/test-coverage-enforcer.md` en ubicación no válida; el harness carga 0 subagentes | `ls agents/ .claude/agents/` → el único `.md` está en `agents/`, `.claude/agents/` solo tiene `_archived/`. Confirmación externa: la lista "Available agent types" de esta sesión no incluye `test-coverage-enforcer` | `git mv agents/test-coverage-enforcer.md .claude/agents/` **+** actualizar `tests/audit/test_integrity.py:32` (`AGENTS_DIR = REPO_ROOT / "agents"`) **+** revisar `hooks/cognitive-os-health.sh:78` (`find "$AOS/agents"`, con `AOS=$PROJECT_DIR/.cognitive-os`) | **lockstep chico** |
| 2 | 39 claves fuera del vocabulario de Claude Code / 44 fuera de los 6 campos de la Skills API, en 188 de 192 skills | `python3 skills_conformance_audit.py --repo .` (§7.1) | Ver plan §3 | **lockstep grande** |
| 3 | 150 de 192 descripciones no dicen cuándo usar la skill (84 con envoltorio circular + 66 sin "cuándo"); `when_to_use` con 0 usos y 0 lectores | mismo script; y `grep -rn "do not use when a narrower" scripts/` → `scripts/migrate_skill_descriptions_use_when.py:57` | Arreglar el **gate** antes que los archivos — ver §4 | **decisión** |
| 4 | `name` ≠ directorio en 3 skills | mismo script, sección `name != directorio`: `caveman-compress`→`compress`, `component-classifier`→`primitive-classifier`, `cost-predictor`→`cost-predict` | Alinear `name` al directorio en los 3 `SKILL.md`. **No cambia el comando invocable**: el `/` sale del directorio (§6, fuente CC) | **mecánico** |
| 5 | `skills/__contracts__/SKILL.md` con `name: __contracts__`, inválido por spec | mismo script, sección `name invalido por regex` | Decidir qué es (§2.5) | **decisión** |

### 2.5 — Por qué #5 no es mecánico

`skills/__contracts__/` tiene `user-invocable: false`, `triggers: []` y una descripción que
dice literalmente "Structural namespace for shared Cognitive OS skill contracts". No es una
skill: es un contenedor. Además tiene una skill **anidada** un nivel más abajo
(`skills/__contracts__/canonical-event-emitter/SKILL.md`) que Claude Code **no carga** — la
spec define `.claude/skills/<skill-name>/SKILL.md`, un solo nivel. Evidencia empírica en esta
misma sesión: la lista de skills disponibles incluye `__contracts__` pero **no**
`canonical-event-emitter`.

Las tres salidas, en orden de mi preferencia:

1. **Sacarlo de `skills/`** — mover el árbol a `contracts/` o `docs/04-Concepts/contracts/`
   y borrar el `SKILL.md`. Resuelve el nombre inválido y el anidamiento de una sola vez.
2. Renombrar el directorio a `skill-contracts` y `name: skill-contracts`, y promover
   `canonical-event-emitter` a `skills/canonical-event-emitter/`.
3. Dejarlo, con la excepción escrita en `manifests/documentation-truth-claims.yaml`.

Lo mismo aplica a `skills/experimental/auto-bash-agent-bash-9c6b89/SKILL.md`, el otro
anidado que no carga.

---

## 3. Plan de migración del punto 2 (el entregable central)

### 3.1 Las tres opciones, evaluadas

**(a) Mover las claves y actualizar los lectores en un commit atómico.**
Requiere tocar 192 `SKILL.md` + 20 archivos de producción + ~25 de tests en un solo cambio.
Cualquier lector que se escape no rompe ruidosamente: **degrada el ruteo en silencio** (una
skill deja de matchear, nadie ve un stack trace). Bajo sesiones concurrentes sobre este
checkout es además un conflicto garantizado. **Rechazada.**

**(c) No migrar y documentar por qué.**
Es más defendible de lo que suena. Claude Code documenta "All fields are optional" y el
error duro por clave desconocida sólo ocurre en el canal de packaging/upload
(`package_skill.py`, claude.ai, Skills API) — canal que este repo hoy no usa. Prueba de que
no rompe nada vivo: **las 192 skills cargaron en esta sesión** con las 39 claves puestas.
Y el argumento de "ruteo invisible" no se sostiene: `triggers` y `routing_intents` los lee
el router **propio** del SO, no Claude Code; moverlas a `metadata:` no las vuelve visibles
para un cliente conforme, porque un cliente conforme tampoco actúa sobre el contenido de
`metadata` ("Claude Code doesn't act on its contents"). **Rechazada igual**, por una razón
distinta: el repo se publica como producto y la primera vez que alguien corra
`package_skill.py` sobre estas skills falla con `Unexpected key(s) in SKILL.md frontmatter`,
188 veces.

**(b) Leer de `metadata:` con fallback al nivel superior y migrar gradualmente. ELEGIDA.**
Es la única sin estado intermedio roto: después de la Etapa 1 los dos layouts funcionan, y
cada archivo se puede migrar solo, en cualquier orden, sin coordinar con nadie.

**Lo que banco, dicho sin adorno:** la Etapa 1 se paga sola (es el punto único de lectura que
hoy no existe, y arregla de paso el bug de `prerequisites`). Las Etapas 2 y 3 sólo devuelven
valor el día que se publique por el canal API/claude.ai. Si esa publicación no está en el
roadmap, la Etapa 1 se hace igual y las 2–3 quedan como deuda escrita en el ledger — no como
trabajo "pendiente de hacer".

### 3.2 Los lectores

**Producción (20 archivos).** Verificado con `skill_key_readers.py` (§7.2).

| Clave | # skills | Lectores de producción |
|---|---:|---|
| `version` | 188 | — (0 lectores de frontmatter de skill) |
| `audience` | 188 | `cos_lib/primitive_parser.py`, `cos_lib/skill_runner.py`, `scripts/cos_init.py`, `scripts/generate_compact_catalog.py`, `scripts/routing_corpus_audit.py`, `hooks/skill-frontmatter-validator.sh` (vía `_fm`) |
| `triggers` | 187 | `cos_lib/cross_instance_learning.py`, `cos_lib/learning_pipeline.py`, `cos_lib/primitive_parser.py`, `mcp-server/cos_mcp.py`, `packages/mcp-server/cos_mcp.py`, `scripts/cos_efficiency_primitives.py`, `scripts/primitive_row_audit.py`, `scripts/primitive_structure_standardizer.py`, `scripts/routing_corpus_audit.py` |
| `routing_intents` | 187 | `cos_lib/language_dependence_audit.py`, `cos_lib/routing_benchmark.py`, `cos_lib/semantic_skill_matcher.py`, `cos_lib/skill_description_enricher.py`, `cos_lib/skill_router.py`, `scripts/primitive_structure_standardizer.py`, `scripts/routing_intent_audit.py` |
| `platforms` | 181 | `cos_lib/skill_runner.py`, `scripts/skill_platform_support_audit.py` |
| `prerequisites` | 165 | **0 lectores** |
| `summary_line` | 147 | `cos_lib/language_dependence_audit.py`, `cos_lib/routing_benchmark.py`, `cos_lib/semantic_skill_matcher.py`, `cos_lib/skill_router.py`, `scripts/generate_compact_catalog.py`, `scripts/primitive_structure_standardizer.py` |
| `routing_patterns` | 126 | `cos_lib/language_dependence_audit.py`, `cos_lib/rule_router.py`, `cos_lib/skill_router.py`, `hooks/skill-md-routing-validator.sh`, `scripts/primitive_structure_standardizer.py`, `scripts/routing_corpus_audit.py` |
| `last-updated` | 84 | `hooks/skill-frontmatter-validator.sh` (vía `_fm`) |

Dos hechos que cambian el tamaño del trabajo:

- **`prerequisites` tiene 0 lectores.** 165 archivos cargan una clave que nadie lee. Vino de
  ADR-076 (spec de Hermes). No hay que migrarla: hay que **borrarla**, o el "supresor que no
  suprime nada" queda instalado. Lo mismo hay que preguntarle a `version` (188 archivos, 0
  lectores de frontmatter de skill) y a `platform_support`/`tag`/`tech`/`inputs`/`outputs`.
- **15 de los 20 lectores usan `yaml.safe_load`** (acceso por dict → el fallback es una línea)
  y sólo 5 escanean con regex sobre el texto: `cos_lib/session_hygiene.py` (`_fm`),
  `cos_lib/skill_runner.py`, `scripts/generate_compact_catalog.py`,
  `scripts/cos_efficiency_primitives.py`, `scripts/primitive_row_audit.py`,
  `cos_lib/learning_pipeline.py`.

**El cuello de botella real: `cos_lib/session_hygiene._fm()`.** Es un regex
`^{key}\s*:` con `re.MULTILINE` — con la clave indentada bajo `metadata:` **deja de
matchear**. Y de él cuelgan los dos enforcement points vivos: el hook
`hooks/skill-frontmatter-validator.sh` y `tests/audit/test_skill_descriptions_nonempty.py`.
Sus consumidores: `hooks/session-hygiene.sh`, `hooks/skill-frontmatter-validator.sh`,
`scripts/regen_catalog_bullets.py`, `tests/audit/test_skill_descriptions_nonempty.py`,
`tests/integration/test_compaction_resilience.py`, `tests/unit/test_session_hygiene.py`,
`tests/unit/test_smart_access.py`.

**Contratos que hay que reescribir, no sólo código:**
- **ADR-067 §4** exige `audience`, `version`, `last-updated` **de primer nivel**. Es
  el contrato que el hook implementa. Migrar sin tocar ADR-067 deja el hook peleado con
  el layout nuevo.
- **ADR-076** metió `version`/`platforms`/`prerequisites` citando la spec de Hermes. Esa
  spec ya divergió de agentskills.io (`version` no existe en ninguna de las dos listas
  vigentes). ADR-076 necesita un tombstone o un supersede.
- `tests/audit/test_skill_descriptions_nonempty.py::test_every_skill_has_valid_audience`
  y `tests/audit/test_skill_platform_support_audit.py` codifican el layout viejo.
- Artefactos generados a regenerar al final: `skills/CATALOG.md`,
  `skills/CATALOG-COMPACT.md`, `skills/CATALOG-MICRO.md`, `skills/REGISTRY.lock`.

### 3.3 El orden de los pasos

> Invariante: **después de cada etapa el repo queda verde y funcional con AMBOS layouts.**
> Ninguna etapa depende de que la siguiente se haga.

**Etapa 0 — decidir qué claves sobreviven (sin escribir código).**
Para cada una de las 39 claves, una fila: ¿tiene lector? ¿tiene consumidor humano? →
`migrar a metadata` / `borrar` / `promover a campo real de la spec`. Candidatos claros a
borrar: `prerequisites` (0 lectores), y a evaluar `version`, `tag`, `tech`, `inputs`,
`outputs`, `platform_support`, `invocation`, `invocation_pattern`, `routing`, `source`,
`scope`. Candidata a **promover**: `summary_line` + `triggers` + `routing_intents` no van a
`metadata` sino a **`when_to_use`**, que es campo real de Claude Code, hoy con 0 usos, y que
sí alimenta el listado de skills que ve el modelo. Salida: una tabla en el ADR nuevo.

**Etapa 1 — el accessor compartido (sin tocar un solo `SKILL.md`).**
1. Crear `cos_lib/skill_frontmatter.py` con `fm_get(frontmatter: dict, key: str)`:
   devuelve `frontmatter["metadata"][key]` si existe, si no `frontmatter[key]`, si no
   `None`. Precedencia metadata-primero, para que la migración de un archivo sea la que
   manda.
2. Extender `cos_lib/session_hygiene._fm()` para que, si no encuentra `^key:`, busque la
   clave **indentada dentro del bloque `metadata:`**. Es el cambio de mayor apalancamiento
   del plan: arregla el hook y los tests de auditoría de una sola vez.
3. Cambiar los 15 lectores `yaml.safe_load` a `fm_get(...)` — una línea cada uno, sin cambio
   de comportamiento observable.
4. Adaptar a mano los 4 lectores regex restantes (`skill_runner`, `generate_compact_catalog`,
   `cos_efficiency_primitives`, `primitive_row_audit`, `learning_pipeline`).
5. **Test de lockstep, escrito antes que el punto 3:** un fixture con el mismo skill en los
   dos layouts, y una aserción de que cada lector devuelve lo mismo para ambos. Sin ese test
   la Etapa 2 no es segura.
   *Criterio de aceptación de la etapa:* `pytest tests/audit tests/unit -m audit` verde
   **sin haber tocado ningún `SKILL.md`**.

**Etapa 2 — migrar los archivos en lotes, por paquete.**
Un script `scripts/migrate_skill_frontmatter_to_metadata.py` con `--check` / `--write`
`--only <ruta>`, idempotente, que respeta la tabla de la Etapa 0 (borra lo que hay que
borrar, mueve lo que hay que mover, promueve a `when_to_use` lo que corresponde). Lotes:
primero un paquete de `packages/*/skills/` (5–8 archivos) → correr el gate → después
`skills/` en tandas de ~20. Regenerar los catálogos **una sola vez, al final** de la etapa.
*Criterio:* `--check` en 0 y ruteo sin regresión, medido con `scripts/routing_quality_gate.py`
contra el baseline previo a la Etapa 2 (no contra uno nuevo — eso sería mover la medición).

**Etapa 3 — cerrar el fallback.**
Recién cuando `--check` dé 0 sobre las 192: invertir `fm_get` para que el nivel superior
emita `DeprecationWarning`, y agregar `tests/audit/test_skill_frontmatter_spec.py` que falle
si aparece una clave fuera de los 6 campos de la Skills API. Reescribir ADR-067 §4 y poner
tombstone a ADR-076. Recién ahí borrar la rama de fallback.

**Lo que NO va en este plan:** el comentario `<!-- SCOPE: ... -->` antes del frontmatter.
Judge 3 lo marca como violación (`skills/patch-release/SKILL.md:1`) y el patrón está en
prácticamente todos los `SKILL.md` del repo, con un hook propio
(`hooks/scope-marker-portability-gate.sh`). Es un cuarto frente, con su propio lockstep, y
mezclarlo acá vuelve la Etapa 2 irrevisable.

---

## 4. Diagnóstico del generador de descripciones

**El generador es `scripts/migrate_skill_descriptions_use_when.py`, no
`cos_lib/skill_description_enricher.py`.** El enricher genera `routing_intents`, no
descripciones — el único match del patrón ahí es una línea de prompt.

**¿Sigue produciendo el patrón circular? Sí, la función está intacta.** Probado sin tocar el
repo, importando el módulo y llamando la función pura:

```
'Use when you need this Cognitive OS skill: Foo bar; do…'  -> sin cambios (idempotente)
'Use when the operator asks for a coverage report…'        -> sin cambios
'Measure declared-but-unwired vs real agentic primitives.' -> 'Use when you need this Cognitive OS skill: Measure…; do not use when a narrower skill directly matches the task.'
'Usar cuando el operador pide auditar el tracker.'         -> 'Use when you need this Cognitive OS skill: Usar cuando…; do not use when a narrower…'
''                                                          -> 'Use when this skill is explicitly requested; do not use…'
```

Tres conclusiones, y la tercera es la que importa:

1. **El barrido de los 84 no se auto-regenera.** `use_when_description()` devuelve el texto
   tal cual si ya empieza con `Use when` (case-insensitive). Reescribir los 84 con prosa que
   arranque con "Use when" es estable: una corrida posterior de `--write` no los vuelve a
   envolver. La premisa "barrer los 73 sin tocarlo los regenera" es **falsa** para ese caso.
2. **El script está dormido: 0 callers.** Confirmado en tres auditorías del repo
   (`docs/06-Daily/reports/aspirational-audit-*.md`: `ON_DEMAND | callers=0`). No corre en
   ningún hook ni en CI.
3. **Lo que está vivo, y es el problema real, es el gate.**
   `tests/audit/test_skill_descriptions_nonempty.py::test_every_skill_description_starts_with_use_when`
   exige que **toda** descripción empiece con el literal `"Use when"`. Ese gate mide la
   forma, no el contenido: la forma más barata de satisfacerlo desde cualquier descripción
   es exactamente el envoltorio circular, y por eso el envoltorio existe. Y como el gate
   fuerza un literal en inglés, choca de frente con `tests/audit/test_language_policy.py`
   y `cos_lib/language_dependence_audit.py` — una descripción en español correcta ("Usar
   cuando el operador…") **falla el gate y el script la envuelve**.

**La acción de mayor retorno, en orden:**

1. **Reemplazar el gate lexical por uno semántico**: en vez de `startswith("Use when")`,
   exigir que la descripción contenga un marcador de disparo de una lista multilingüe
   (`use when`, `usar cuando`, `when the user`, `trigger`, …) **y** que no contenga ninguna
   de las frases genéricas ya listadas en `scripts/routing_intent_audit.py:21-27`
   (`_GENERIC_PHRASES` ya incluye las dos mitades del envoltorio — el detector existe, sólo
   que no está conectado al gate de descripciones).
2. **Cambiar `use_when_description()`** para que, cuando no reconozca un disparador, **falle
   en vez de envolver** (`--write` no debería poder fabricar una descripción; que devuelva
   la lista de archivos que necesitan mano humana).
3. **Recién ahí** reescribir los 84 + 66. Que en el mismo pase se llene `when_to_use` con
   los disparadores (hoy 0 usos, campo real de la spec) en lugar de meterlos en la
   `description`.

Sin el paso 1 y 2, el paso 3 es reversible por accidente: basta que alguien corra
`--write` sobre una descripción nueva en español.

---

## 5. Correcciones a las premisas del encargo

1. **"189 de 194 `SKILL.md`" / "~45 claves".** Mi enumeración da **188 de 192** con **39**
   claves desconocidas para Claude Code y **44** fuera de los 6 de la Skills API. La
   diferencia de denominador (192 vs 194) son dos skills **anidadas dos niveles**
   (`skills/__contracts__/canonical-event-emitter/`,
   `skills/experimental/auto-bash-agent-bash-9c6b89/`) que git lista pero que
   **Claude Code no carga** — no aparecen en la lista de skills de esta sesión. Contarlas
   infla el denominador con archivos que ninguna spec ve.
2. **"~13 lectores".** Son **20 archivos de producción** (más ~25 de tests). Y
   `scripts/routing_quality_gate.py`, citado en el encargo, **no lee frontmatter**: consume
   un reporte ya calculado por `cos_lib/routing_benchmark.py`. Es lector indirecto.
3. **"Mover las claves sin actualizar los lectores rompe el ruteo propio."** Correcto, y peor
   de lo enunciado: rompe **en silencio**. `_fm()` devuelve `None` y los callers tienen
   `or "No description"` como fallback — no hay excepción, hay degradación.
4. **"El campo `when_to_use`, que Claude Code sí lee".** Correcto, verificado en la tabla de
   frontmatter (fila `when_to_use`, "Additional context for when Claude should invoke the
   skill… Appended to `description` in the skill listing"). Pero **no** es campo de la Agent
   Skills spec ni de los 6 de la Skills API: llenarlo mejora el ruteo en Claude Code y
   **rompe** el packaging para claude.ai. Es exactamente la divergencia que el encargo pedía
   confirmar, y sí, se sostiene (§6).
5. **"`name` ≠ directorio → defecto".** Se sostiene contra agentskills.io ("Must match the
   parent directory name") pero **no** rompe nada en Claude Code: "In a personal or project
   skill, `name` sets only the display label… the command still comes from the directory
   name". Prueba empírica: las tres skills aparecen en la lista de esta sesión por su
   nombre de directorio (`caveman-compress`, `component-classifier`, `cost-predictor`).
   Es cosmético para el harness y bloqueante para el canal API. Bajar la prioridad.
6. **`skills/__contracts__` con `name: __contracts__`.** Inválido por agentskills.io
   (`a-z0-9-` solamente), y sin embargo **Claude Code lo cargó** en esta sesión. Confirma que
   Claude Code no valida el charset de `name`. El defecto es real sólo para el canal API.
7. **El `git mv` del punto 1 no es una sola línea.** Tiene dos consumidores del path viejo:
   `tests/audit/test_integrity.py:32` (`AGENTS_DIR = REPO_ROOT / "agents"`, con un
   `assert len(agents) >= 1` en la línea 249 que se pondría rojo) y
   `hooks/cognitive-os-health.sh:78` (`find "$AOS/agents"` con `AOS=$PROJECT_DIR/.cognitive-os`,
   que hoy resuelve por el symlink `.cognitive-os/agents/test-coverage-enforcer.md →
   ../../agents/test-coverage-enforcer.md`, que quedaría colgado).
8. **El punto 1 tiene un defecto más grande debajo, y mover el archivo no lo arregla.** El
   frontmatter declara `triggers: [{file_pattern: "**/*.go", …}]` — un campo que **no existe
   en la spec de subagentes** (name, description, tools, disallowedTools, model,
   permissionMode, maxTurns, skills, mcpServers, hooks, memory, background, effort,
   isolation, color, initialPrompt) y una semántica —"activarse cuando cambian archivos
   fuente"— que los subagentes **no tienen**: se delegan por `description`, no por glob. El
   propio repo ya lo documenta:
   `docs/04-Concepts/architecture/functional-audit/scorecard-packages-squads-agents.md:104`
   ("no hook scans for frontmatter triggers on file edits"). Después del `git mv` el
   subagente carga, pero **sigue sin dispararse solo**. Si lo que se quiere es el
   comportamiento, hace falta un hook PostToolUse, no un subagente.
9. **La ubicación correcta ya está escrita en el repo.**
   `docs/05-Methodology/root/configurable-quality-gates.md:92` dice
   **"Location: `.claude/agents/test-coverage-enforcer.md`"**. La doc tiene razón y el árbol
   no. Es un caso de "lo escrito no se aplica solo".
10. **`skills/` en la raíz no es ubicación válida tampoco** — la spec sólo reconoce
    `~/.claude/skills/`, `.claude/skills/`, `<plugin>/skills/` y managed settings, y este
    repo **no tiene** `.claude-plugin/plugin.json`. No es un defecto porque hay una capa de
    proyección: `.claude/skills/` es un directorio real con 197 symlinks a `../../skills/*`
    (gitignored, `.gitignore:62`), creado por `install.sh` / `scripts/cos_init.py`. Las
    skills cargan por ahí. **El punto es que para los subagentes esa misma proyección no
    existe** — y ésa, no la ubicación en sí, es la causa raíz del defecto #1. El arreglo
    duradero es agregar `agents/` al proyector, igual que `skills/`; el `git mv` arregla el
    síntoma de hoy y deja el mecanismo asimétrico.
11. **Mi clasificador de descripciones da 150, no 128** (84 circulares + 66 sin "cuándo",
    contra 73 + 55 del encargo / judge 3). No es que uno esté mal: son heurísticas
    distintas. La mía está entera en §7.1 (`CIRCULAR_RE`, `WHEN_RE`) y es corrible; la del
    encargo no vino con su regex. Uso la mía y dejo el delta anotado.
12. **`metadata` no acepta cualquier cosa adentro, según cuál spec se lea.** Claude Code:
    "Free-form YAML map… drops a value that isn't a map". agentskills.io: "**a map from
    string keys to string values**". `routing_patterns` es una lista de mapas y `triggers`
    una lista: metidos bajo `metadata:` pasan en Claude Code y **siguen fuera de spec** en
    agentskills.io. Si la Etapa 3 apunta al canal API, hay que serializarlos a string o
    aceptar la divergencia por escrito.
13. **El aviso del encargo sobre `lib/*.py` es correcto**: `lib/` no existe (0 archivos
    trackeados); son 369 en `cos_lib/`. Todas las rutas de este informe apuntan a `cos_lib/`.

---

## 6. VERIFICADO vs NO VERIFICADO

### Fuentes externas (spec), con fecha de acceso

| Regla aplicada | Fuente | Acceso |
|---|---|---|
| Tabla completa de frontmatter aceptada por Claude Code (20 campos: `name`, `description`, `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell`, `metadata`, `license`, `compatibility`) + "All fields are optional" | `code.claude.com/docs/en/skills` §Frontmatter reference | 2026-08-15 |
| Lista **cerrada** de 6 campos para claude.ai / Skills API / `package_skill.py`: `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`; y el error duro `Unexpected key(s) in SKILL.md frontmatter…` | misma página, §Using skill frontmatter outside Claude Code | 2026-08-15 |
| Ubicaciones válidas de skills (`~/.claude/skills/`, `.claude/skills/`, `<plugin>/skills/`, managed) | misma página, §Where skills live | 2026-08-15 |
| `name` es sólo etiqueta de display en skills personales/de proyecto; el comando sale del directorio | misma página, §How a skill gets its command name | 2026-08-15 |
| `metadata`: "Claude Code doesn't act on its contents, and drops a value that isn't a map" | misma página, tabla | 2026-08-15 |
| `name`: 1-64 chars, `a-z0-9-`, sin guion inicial/final, sin `--`, **debe coincidir con el directorio padre**; `name` y `description` **requeridos**; `metadata` = map string→string | `agentskills.io/specification` | 2026-08-15 |
| Ubicaciones de subagentes (`.claude/agents/`, `~/.claude/agents/`, `<plugin>/agents/`, CLI `--agents`, managed) y sus campos de frontmatter | `code.claude.com/docs/en/sub-agents` | 2026-08-15 |

**La divergencia que el encargo pedía chequear se sostiene**, y es explícita en la doc de
Claude Code: acepta 20 campos y declara que todos son opcionales; el canal claude.ai / Skills
API / `package_skill.py` valida contra 6 y **falla duro** con el resto. Consecuencia práctica:
"conforme" no es una sola cosa. Este informe usa **conforme-CC** (39 claves fuera) y
**conforme-API** (44 claves fuera, 188 skills bloqueadas para packaging) como dos métricas
separadas, y el script las reporta por separado.

### VERIFICADO en el repo (con comando)

- 192 skills únicas por `realpath` en `skills/` + `packages/*/skills/`; 194 si se cuentan las
  dos anidadas que no cargan. Symlink y destino cuentan una vez.
- 39 claves desconocidas para Claude Code en 188 skills; 44 fuera de los 6 de la API en 188.
- `prerequisites`: 165 skills, **0 lectores** en código.
- `when_to_use`: **0 usos**, **0 lectores**.
- 84 descripciones con el envoltorio circular, 66 sin marcador de "cuándo" (heurística §7.1);
  las 150 están en `skills/`, **ninguna** en `packages/*/skills/`.
- `name` ≠ directorio: exactamente 3. `name` inválido por charset: exactamente 1.
- 20 lectores de producción, mapeados archivo:línea (§7.2). 15 vía `yaml.safe_load`, 5 vía
  regex.
- El generador es `scripts/migrate_skill_descriptions_use_when.py`; su función pura probada
  con 5 casos; 0 callers según tres auditorías del repo.
- El gate vivo es `tests/audit/test_skill_descriptions_nonempty.py` (`startswith("Use when")`)
  + `hooks/skill-frontmatter-validator.sh` (contrato ADR-067 §4, advisory salvo
  `COS_STRICT_SKILL_VALIDATION=1`).
- `agents/test-coverage-enforcer.md` es el único subagente trackeado; `.claude/agents/` sólo
  tiene `_archived/`; `.cognitive-os/agents/` es un symlink gitignored.
- Consumidores del path `agents/`: `tests/audit/test_integrity.py:32,249`;
  `hooks/cognitive-os-health.sh:78`.
- El repo **no** es un plugin: no existe `.claude-plugin/plugin.json`.

### VERIFICADO por observación de esta sesión (no por script)

- Las 192 skills cargaron: aparecen en el listado de skills de esta sesión, con las 39 claves
  fuera de spec puestas. → Claude Code no rechaza claves desconocidas.
- `__contracts__` figura en ese listado. → no valida el charset de `name`.
- `canonical-event-emitter` **no** figura. → no carga skills anidadas dos niveles.
- `test-coverage-enforcer` **no** figura en "Available agent types". → el subagente
  efectivamente no carga.

Es observación reproducible (abrir una sesión y mirar el listado), no una aserción de script.
Un script equivalente tendría que hablar con el harness, que no está expuesto.

### NO VERIFICADO

- **Nada se corrió: ni `pytest`, ni `scripts/routing_quality_gate.py`, ni el hook.** Los
  criterios de aceptación de las etapas §3.3 están **propuestos, no medidos**. En particular
  no puedo afirmar que las Etapas 1–2 dejen la suite verde: sólo que están diseñadas para
  que quede.
- **No se midió el baseline de ruteo previo.** La Etapa 2 lo exige y hay que tomarlo
  **antes** de tocar archivos, o no hay contra qué comparar.
- **No se auditaron los `SKILL.md` fuera de `skills/` y `packages/`**: `.claude/skills/` (6),
  `.codex/skills/` (9), `.cognitive-os/skills/` (10), `examples/` (1). Algunos son copias,
  otros no; no lo determiné.
- **El comportamiento exacto de Claude Code ante una clave desconocida no está documentado.**
  La doc dice qué acepta y qué falla en packaging, pero no dice si ignora, avisa o descarta.
  Lo que sé es empírico (cargan), no normativo.
- **La lista de 39 claves no está clasificada** en migrar/borrar/promover. Ésa es la Etapa 0
  y es trabajo de operador, no de script.
- **`hooks/scope-marker-portability-gate.sh` y el comentario `<!-- SCOPE -->`** quedaron
  fuera de alcance a propósito. Judge 3 lo llama violación de spec; no lo evalué.

---

## 7. Los scripts, enteros

Ambos son read-only, deterministas, sin dependencia de estado de sesión, con exit codes
`0` sin hallazgos / `1` hallazgos / `2` error. Viven hoy sólo en el scratchpad de la sesión;
si se van a usar más de una vez, su lugar es `scripts/`.

### 7.1 `skills_conformance_audit.py`

```
python3 skills_conformance_audit.py --repo .            # tabla
python3 skills_conformance_audit.py --repo . --json     # detalle por archivo
```

```python
#!/usr/bin/env python3
"""Audita conformidad de SKILL.md con la spec de Agent Skills. READ-ONLY.

Uso:  python3 skills_conformance_audit.py [--repo PATH] [--json]
Exit: 0 sin hallazgos / 1 hallazgos / 2 error

Universo: skills/<name>/ (dirs reales + symlinks resueltos) + packages/*/skills/<name>/.
Un symlink y su destino cuentan UNA vez (dedup por os.path.realpath).
"""
import argparse
import json
import os
import re
import sys

# Tabla completa de frontmatter aceptada por Claude Code
# Fuente: https://code.claude.com/docs/en/skills #frontmatter-reference (2026-08-15)
SPEC_CC = {
    "name", "description", "when_to_use", "argument-hint", "arguments",
    "disable-model-invocation", "user-invocable", "allowed-tools",
    "disallowed-tools", "model", "effort", "context", "agent", "background",
    "hooks", "paths", "shell", "metadata", "license", "compatibility",
}
# Lista CERRADA de la Agent Skills spec / Skills API / package_skill.py.
# Fuente: misma pagina, seccion "Using skill frontmatter outside Claude Code".
SPEC_API = {"name", "description", "license", "compatibility", "metadata",
            "allowed-tools"}
SPEC_TOP_LEVEL = SPEC_CC

CIRCULAR_RE = re.compile(
    r"use when you need this cognitive os skill", re.I)
WHEN_RE = re.compile(
    r"\b(use when|when the user|when you|trigger|triggers on|activates when|"
    r"usar (siempre )?(antes|cuando)|use this (skill )?when|invoke when|"
    r"para cuando|al (crear|cerrar|iniciar))", re.I)


def parse_frontmatter(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        return None, str(exc)
    if not text.startswith("---"):
        return None, "sin frontmatter"
    end = text.find("\n---", 3)
    if end == -1:
        return None, "frontmatter sin cierre"
    body = text[3:end]
    keys = []
    scalars = {}
    for line in body.splitlines():
        if not line or line.startswith("#"):
            continue
        if line[0] in " \t-":          # anidado o item de lista
            continue
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*:\s*(.*)$", line)
        if not m:
            continue
        keys.append(m.group(1))
        scalars[m.group(1)] = m.group(2).strip()
    return (keys, scalars), None


def collect(repo):
    roots = [os.path.join(repo, "skills")]
    pkg = os.path.join(repo, "packages")
    if os.path.isdir(pkg):
        for p in sorted(os.listdir(pkg)):
            d = os.path.join(pkg, p, "skills")
            if os.path.isdir(d):
                roots.append(d)
    seen, out = {}, []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            sk = os.path.join(root, name, "SKILL.md")
            if not os.path.isfile(sk):
                continue
            real = os.path.realpath(sk)
            if real in seen:
                continue
            seen[real] = sk
            out.append((os.path.relpath(sk, repo), real, name))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)

    skills = collect(repo)
    key_hist, offenders, api_offenders = {}, {}, {}
    circular, no_when, name_mismatch, bad_name, no_desc = [], [], [], [], []
    when_to_use_users = []
    parse_err = []

    for rel, real, dirname in skills:
        parsed, err = parse_frontmatter(real)
        if err:
            parse_err.append((rel, err))
            continue
        keys, scalars = parsed
        for k in keys:
            key_hist[k] = key_hist.get(k, 0) + 1
            if k not in SPEC_CC:
                offenders.setdefault(k, []).append(rel)
            if k not in SPEC_API:
                api_offenders.setdefault(k, []).append(rel)
        if "when_to_use" in keys:
            when_to_use_users.append(rel)
        nm = scalars.get("name", "")
        if not nm:
            bad_name.append((rel, "sin name"))
        else:
            if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", nm):
                bad_name.append((rel, nm))
            if nm != dirname:
                name_mismatch.append((rel, nm, dirname))
        desc = scalars.get("description", "")
        if not desc:
            no_desc.append(rel)
        elif CIRCULAR_RE.search(desc):
            circular.append(rel)
        elif not WHEN_RE.search(desc):
            no_when.append(rel)

    report = {
        "total_skills": len(skills),
        "parse_errors": parse_err,
        "out_of_spec_keys": {k: len(v) for k, v in
                             sorted(offenders.items(), key=lambda kv: -len(kv[1]))},
        "out_of_spec_key_count": len(offenders),
        "api_blocking_keys": {k: len(v) for k, v in
                              sorted(api_offenders.items(), key=lambda kv: -len(kv[1]))},
        "api_blocking_key_count": len(api_offenders),
        "skills_blocked_for_api": len({f for v in api_offenders.values() for f in v}),
        "skills_unknown_to_cc": len({f for v in offenders.values() for f in v}),
        "when_to_use_users": when_to_use_users,
        "desc_circular": circular,
        "desc_no_when": no_when,
        "desc_missing": no_desc,
        "name_dir_mismatch": name_mismatch,
        "name_invalid": bad_name,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"skills unicas: {report['total_skills']}")
        print(f"claves desconocidas para Claude Code: {report['out_of_spec_key_count']}"
              f" en {report['skills_unknown_to_cc']} skills")
        print(f"claves que rompen la Skills API (lista de 6): "
              f"{report['api_blocking_key_count']} en {report['skills_blocked_for_api']} skills")
        for k, n in list(report["out_of_spec_keys"].items())[:25]:
            print(f"  {k:28s} {n}")
        print(f"when_to_use usado en: {len(when_to_use_users)}")
        print(f"descripciones circulares: {len(circular)}")
        print(f"descripciones sin 'cuando': {len(no_when)}")
        print(f"descripciones ausentes: {len(no_desc)}")
        print(f"name != directorio: {len(name_mismatch)} -> {name_mismatch}")
        print(f"name invalido por regex: {len(bad_name)} -> {bad_name}")
        if parse_err:
            print(f"errores de parseo: {parse_err}")
    bad = (offenders or circular or no_when or name_mismatch or bad_name
           or no_desc or parse_err)
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
```

**Salida al 2026-08-15 sobre `HEAD` de `session/21f28a76-audit-2026-08-15`:**

```
skills unicas: 192
claves desconocidas para Claude Code: 39 en 188 skills
claves que rompen la Skills API (lista de 6): 44 en 188 skills
  version                      188
  audience                     188
  triggers                     187
  routing_intents              187
  platforms                    181
  prerequisites                165
  summary_line                 147
  routing_patterns             126
  last-updated                  84
  tags                          54
  auto-generated                53
  command                       29
  trigger                       23
  invoke                        21
  platform_support              13
  invocation_pattern            12
  inputs                        12
  outputs                       12
  tech                           8
  tag                            7
  invocation                     5
  routing                        5
  scope                          3
  source                         3
  related_adr                    2
when_to_use usado en: 0
descripciones circulares: 84
descripciones sin 'cuando': 66
descripciones ausentes: 0
name != directorio: 3 -> [('skills/caveman-compress/SKILL.md', 'compress', 'caveman-compress'), ('skills/component-classifier/SKILL.md', 'primitive-classifier', 'component-classifier'), ('skills/cost-predictor/SKILL.md', 'cost-predict', 'cost-predictor')]
name invalido por regex: 1 -> [('skills/__contracts__/SKILL.md', '__contracts__')]
```

### 7.2 `skill_key_readers.py`

```
python3 skill_key_readers.py --repo . --key triggers --key routing_intents ...
python3 skill_key_readers.py --repo .          # las 22 claves por defecto
```

```python
#!/usr/bin/env python3
"""Localiza el CODIGO que lee claves de frontmatter de SKILL.md. READ-ONLY.

Uso:  python3 skill_key_readers.py [--repo PATH] [--key KEY ...]
Exit: 0 sin lectores / 1 hay lectores / 2 error

Busca patrones de acceso reales (fm["k"], fm.get("k"), yaml key regex, jq .k)
en codigo (.py/.sh/.go), excluyendo los propios SKILL.md y los .md en general.
"""
import argparse
import os
import re
import subprocess
import sys

DEFAULT_KEYS = [
    "triggers", "routing_intents", "routing_patterns", "platforms",
    "prerequisites", "summary_line", "audience", "tags", "last-updated",
    "auto-generated", "command", "invoke", "trigger", "platform_support",
    "invocation_pattern", "inputs", "outputs", "scope", "source", "tech",
    "when_to_use", "metadata",
]
CODE_EXT = (".py", ".sh", ".go", ".bash", ".zsh")
EXCLUDE_DIRS = ("node_modules", ".git", "archive/")


def tracked_code(repo):
    out = subprocess.run(["git", "-C", repo, "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    for p in out.splitlines():
        if not p.endswith(CODE_EXT):
            continue
        if any(d in p for d in EXCLUDE_DIRS):
            continue
        yield p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--key", action="append")
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    keys = args.key or DEFAULT_KEYS

    pats = {}
    for k in keys:
        ke = re.escape(k)
        pats[k] = re.compile(
            r"""(?:                       # acceso dict python
                  \[\s*['"]%s['"]\s*\]
                | \.get\(\s*['"]%s['"]
                | ['"]%s['"]\s*(?:in|not\s+in)\b
                | \bfrontmatter\.%s\b
                | ^\s*%s\s*=            # asignacion homonima (ruido bajo)
                | grep[^\n]*['"^ ]%s:    # grep de yaml en bash
                | sed[^\n]*%s:
                | awk[^\n]*%s:
                | \.%s\b\s*[|)\]]        # jq
                )""" % ((ke,) * 9),
            re.X | re.M)

    hits = {k: {} for k in keys}
    for rel in tracked_code(repo):
        path = os.path.join(repo, rel)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        if "SKILL" not in text and "skill" not in text.lower():
            continue
        for k, pat in pats.items():
            lines = [i + 1 for i, ln in enumerate(text.splitlines())
                     if pat.search(ln)]
            if lines:
                hits[k][rel] = lines

    total = 0
    for k in keys:
        files = hits[k]
        if not files:
            print(f"{k}: 0 lectores")
            continue
        total += len(files)
        print(f"{k}: {len(files)} archivos")
        for f, lns in sorted(files.items()):
            print(f"    {f}:{','.join(map(str, lns[:6]))}")
    return 1 if total else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
```

**Salida al 2026-08-15 (claves de ruteo; se omiten las filas de `tests/`):**

```
triggers: 14 archivos
    cos_lib/cross_instance_learning.py:332
    cos_lib/learning_pipeline.py:287,323,342,417
    cos_lib/primitive_parser.py:315,363,395,440
    mcp-server/cos_mcp.py:414
    packages/mcp-server/cos_mcp.py:414
    scripts/cos_efficiency_primitives.py:241
    scripts/primitive_row_audit.py:179
    scripts/primitive_structure_standardizer.py:103,104,157
    scripts/routing_corpus_audit.py:83
routing_intents: 10 archivos
    cos_lib/language_dependence_audit.py:270
    cos_lib/routing_benchmark.py:250,607
    cos_lib/semantic_skill_matcher.py:354,369,563,591
    cos_lib/skill_description_enricher.py:518,587
    cos_lib/skill_router.py:326,330
    scripts/primitive_structure_standardizer.py:119
    scripts/routing_intent_audit.py:132
routing_patterns: 7 archivos
    cos_lib/language_dependence_audit.py:422,425
    cos_lib/rule_router.py:238
    cos_lib/skill_router.py:255,282
    hooks/skill-md-routing-validator.sh:62
    scripts/primitive_structure_standardizer.py:116
    scripts/routing_corpus_audit.py:83
platforms: 5 archivos
    cos_lib/skill_runner.py:201,210,236,445
    scripts/skill_platform_support_audit.py:63,123
prerequisites: 0 lectores
summary_line: 9 archivos
    cos_lib/language_dependence_audit.py:275
    cos_lib/routing_benchmark.py:606
    cos_lib/semantic_skill_matcher.py:246,353,368,563,590
    cos_lib/skill_router.py:1756
    scripts/generate_compact_catalog.py:115
    scripts/primitive_structure_standardizer.py:64
audience: 12 archivos
    cos_lib/primitive_parser.py:367,375,406,426,452,469
    cos_lib/skill_runner.py:180
    scripts/cos_init.py:341,347
    scripts/generate_compact_catalog.py:128,141,165,238,240
    scripts/routing_corpus_audit.py:84
when_to_use: 0 lectores
```
