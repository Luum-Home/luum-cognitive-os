# Auditoría externa de ADRs — ¿la comunidad avala lo que este repo decidió?

**Fecha:** 2026-08-15
**Juez:** agente externo, read-only
**Lente única:** ¿las decisiones estructurales coinciden con documentación oficial vigente y práctica pública del campo?

---

## 1. Veredicto

De **13 decisiones estructurales evaluadas a fondo contra fuentes externas**:
**4 ALINEADAS**, **3 DIVERGENTES JUSTIFICADAS**, **2 DIVERGENTES SIN JUSTIFICAR**, **4 VENCIDAS**, **0 REINVENCIONES confirmadas**.

Lo caro no son los errores de criterio: es el **mantenimiento**. Las cuatro vencidas son todas del mismo tipo — el harness creció y las decisiones quedaron fijadas al harness de abril 2026.

---

## 2. Método de selección y muestreo declarado

### Censo (script reproducible)

Script: `scratchpad/classify_adrs.py` (read-only, determinista, sin red).

```
python3 classify_adrs.py docs/02-Decisions/adrs
```

Conteo verificado con:

```
cd docs/02-Decisions/adrs
ls *.md | wc -l                                          # 504 archivos
ls *.synthesis.md | wc -l                                # 150 sintesis
ls *tombstone*.md | wc -l                                # 11 tombstones
ls *.md | grep -v '\.synthesis\.md$' | grep -v tombstone \
        | grep -vE '^(INDEX|README|STATUS-TAXONOMY)\.md$' | wc -l   # 340
```

### Criterio de selección (no gusto)

Se rankeó cada ADR por **score estructural = (citas entrantes desde otros ADRs × 10) + señales de alcance** (`supersedes`, `umbrella`, `contract`, `canonical`, `single source of truth`, `authority`). Las citas entrantes miden lo pedido: *una decisión es estructural si otras decisiones dependen de ella*.

Sobre ese ranking se aplicó un **segundo filtro, el que define esta auditoría**: la decisión tiene que estar **sobre un borde donde plausiblemente existe un estándar externo** — o sea, donde el repo pudo haber delegado en el campo en vez de decidir solo. Una decisión puramente interna (p. ej. `ADR-105 claim-verification-contract`) puede ser muy estructural y aun así no ser auditable con esta lente.

### Muestreo

| Universo | Cantidad |
|---|---|
| Archivos en `docs/02-Decisions/adrs/` | 504 |
| ADRs reales (sin síntesis, tombstones, meta) | **340** |
| Clasificados por tema (todos) | 340 |
| **Evaluados a fondo contra fuentes externas** | **13** |
| Declarados NO EVALUADOS a fondo | **327** |

**3,8 % del corpus fue al fondo.** No se leyó en profundidad el 96 % restante y no se emite juicio sobre él.

---

## 3. Tabla por decisión

| ADR | Qué decidió | Qué dice la práctica externa | Fuente + fecha de acceso | Clasificación |
|---|---|---|---|---|
| **ADR-008 / ADR-064 / ADR-159** — harness-agnóstico | El SO no puede ser Claude-Code-only; capa de adapters + proyección estructural a múltiples harnesses. El repo tiene `AGENTS.md` en raíz y **no** tiene `CLAUDE.md` en raíz. | `AGENTS.md` es de facto el estándar: 60.000+ repos, administración formal bajo la Linux Foundation (Agentic AI Foundation), leído nativamente por Codex, Cursor, Copilot, Gemini CLI, Aider, Windsurf, Zed y 20+ más. Muse Code CLI (Meta, 2026-08-05) prefiere `AGENTS.md` sobre `CLAUDE.md`. | codersera.com/blog/agents-md-complete-guide-2026/ ; blog.agentailor.com/posts/top-ai-agent-standards-2026 — acceso 2026-08-15 | **ALINEADA** |
| **ADR-092** — sync de skills a `.claude/skills/` | Agregar `{project}/.claude/skills/` como segundo destino de sync en `self-install.sh`. | Documentación oficial: skills de proyecto en `.claude/skills/`, personales en `~/.claude/skills/`; skills de plugin en namespace `plugin:skill`. Precedencia enterprise > personal > proyecto. | code.claude.com/docs/en/skills ; platform.claude.com/docs/en/agents-and-tools/agent-skills/overview — acceso 2026-08-15 | **ALINEADA** |
| **ADR-072** — taxonomía de test lanes | Registro YAML como fuente única + **inyección automática de markers vía `pytest_collection_modifyitems` en `tests/conftest.py`**, aditiva e idempotente. | Es literalmente el patrón documentado por pytest: "Implement the `pytest_collection_modifyitems` hook to inspect test node IDs and apply markers automatically" (`doc/en/example/markers.rst`). Registrar los markers en config está también recomendado. | Context7 `/pytest-dev/pytest` → `doc/en/example/markers.rst`, `doc/en/how-to/mark.rst` — acceso 2026-08-15 | **ALINEADA** |
| **ADR-058** — Langfuse → Arize Phoenix | Deprecar Langfuse, adoptar Phoenix en `mode: pip` (sin Docker), MLflow sin cambios para costo/outcome. | No hay un estándar estable que contradiga esto: las convenciones GenAI de OpenTelemetry siguen en estado *Development*, sin release 1.0, y se movieron a un repo dedicado en v1.42.0 (2026-06-12). Phoenix es OTel-nativo, así que la elección no cierra la puerta a converger. | dev.to/azena-ai/opentelemetrys-genai-semantic-conventions-are-not-stable-yet ; greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions — acceso 2026-08-15 | **ALINEADA** |
| **ADR-049** — gateway LLM | Sacar LiteLLM, **no** adoptar Bifrost, dispatch directo por SDK en `lib/model_router.py`. | La preocupación se sostiene: el compromiso de cadena de suministro de LiteLLM (marzo 2026) sigue siendo el eje de la discusión pública de 2026. El campo recomienda Bifrost para producción a escala; el ADR **evalúa Bifrost con tabla comparativa y escribe explícitamente en qué condiciones Bifrost sería la elección correcta** (multi-usuario, alto RPS, cache semántico). Ese es el estándar de redacción que el resto del corpus no alcanza. | medium.com/@pranaybatta2014/litellm-vs-bifrost-in-2026-an-honest-comparison-after-the-supply-chain-wake-up-call ; getmaxim.ai/articles/top-5-llm-gateways-in-2026-a-production-ready-comparison/ — acceso 2026-08-15 | **DIVERGENTE JUSTIFICADA** |
| **ADR-033** — captura de eventos harness-agnóstica (schema canónico propio) | Schema canónico propio en `lib/harness_adapter/`, un archivo de adapter por harness. | **No hay estándar estable que cubra esto.** Las convenciones GenAI de OTel modelan spans de agente (`invoke_agent`, `execute_tool`) pero siguen experimentales, sin 1.0, y no cubren el vocabulario de *hooks de ciclo de vida* de un harness. La capa propia es legítima. Dato nuevo a evaluar: Claude Code ya emite trazas OTel GenAI (beta). | dev.to/azena-ai/opentelemetrys-genai-semantic-conventions-are-not-stable-yet ; veraexmachina.com/tech/opentelemetry-genai-agent-observability-production/ — acceso 2026-08-15 | **DIVERGENTE JUSTIFICADA** |
| **ADR-329** — `platform_support:` en frontmatter de SKILL.md | Clave top-level propia con estructura anidada (`support_level`, `evidence: []`). | La spec de Agent Skills define `metadata` como **map de string a string**, así que una estructura anidada genuinamente no entra ahí. Los campos desconocidos se ignoran, no rompen. La divergencia tiene causa técnica real. | agentskills.io/specification.md §`metadata` field — acceso 2026-08-15 | **DIVERGENTE JUSTIFICADA** |
| **ADR-019** — scope tagging (`audience:` top-level) | `audience: os-only\|project\|both` como clave top-level en 188 SKILL.md (`grep -l '^audience:' skills/*/SKILL.md \| wc -l` → 188). | La spec provee **exactamente ese casillero**: `metadata` es "arbitrary key-value mapping… Clients can use this to store additional properties **not defined by the Agent Skills spec**", con recomendación de usar claves únicas para evitar colisiones. `audience` es un string plano: entra perfecto. El ADR compara **tres alternativas propias** (directorio, filtrado en runtime, ignorar) y **cero mecanismos nativos**. La premisa del encargo queda confirmada. | agentskills.io/specification.md §`metadata` field — acceso 2026-08-15 | **DIVERGENTE SIN JUSTIFICAR** |
| **ADR-087** — namespace y numeración de ADRs | `ADR-NNN-slug.md` con **sufijos-letra para addenda** (`028a`, `028b`, `028c`, `174b`, `174c`). Alternativas evaluadas: tres, todas internas. | MADR es la convención del campo (`adr.github.io/madr`, MADR 4.0.0): numeración `NNNN-slug.md` y **enmienda vía supersede + número nuevo**, con header `Superseded by ADR-NNN` y referencia cruzada. Verificación: `grep -il 'MADR\|Nygard\|adr-tools' *.md` → **0 de 340 ADRs mencionan la convención externa.** | adr.github.io/madr ; github.com/adr/madr — acceso 2026-08-15 | **DIVERGENTE SIN JUSTIFICAR** (daño bajo) |
| **ADR-010** — arquitectura de hooks v2 | Fijó **10 tipos de evento** + 3 perfiles de seguridad. `.claude/settings.json` registra hoy exactamente esos 10 (161 hooks). | La doc oficial de Claude Code documenta hoy **31 eventos**. Sin cubrir en el repo, entre otros: `SessionEnd`, `SubagentStop`, `PostToolUseFailure`, `StopFailure`, `PostCompact`, `PermissionRequest`, `PermissionDenied`, `WorktreeCreate`/`WorktreeRemove`, `FileChanged`, `ConfigChange`, `InstructionsLoaded`, `PostToolBatch`, `UserPromptExpansion`. Varios calzan con maquinaria que el repo ya tiene (ver §4). | code.claude.com/docs/en/hooks — acceso 2026-08-15 | **VENCIDA** |
| **ADR-012** — gobernanza declarativa por prompt | 4 hooks de juicio convertidos a plantillas de prompt en `templates/prompt-hooks/`, evaluadas llamando a Haiku desde bash. | Claude Code ships hooks nativos `type: "prompt"`: campo `prompt` con placeholder `$ARGUMENTS`, campo `model` opcional, timeout por defecto 30s. También `type: "mcp_tool"` y hooks HTTP. Verificación: `grep -c '"type": *"prompt"' .claude/settings.json` → **0**. La idea del ADR fue adoptada por el harness; la implementación propia quedó atrás. | code.claude.com/docs/en/hooks §"Prompt and agent hook fields" — acceso 2026-08-15 | **VENCIDA** |
| **ADR-064 / ADR-081** — adapter de Codex, cobertura de tool-hooks | `manifests/harness-driver-capabilities.yaml` documenta la limitación "PreToolUse/PostToolUse **solo sobre Bash**, as of v0.126.0-alpha.8", y los tests de paridad **excluyen eventos de tool no-Bash** con ese fundamento. | PR openai/codex#23757 (mergeado **2026-05-23**, commit `5c20513`) hizo que `CoreToolRuntime` provea el contrato de hooks por defecto para function tools locales — la mayoría ya emite `PreToolUse`/`PostToolUse`, con `updatedInput` reescribible. Follow-up #24149 agregó `spawn_agent`. La brecha no cerró del todo (issue #20204 sigue documentando handlers sin cobertura), pero la matriz del repo describe un estado de hace tres meses. | github.com/openai/codex/pull/23757 ; github.com/openai/codex/issues/20204 — acceso 2026-08-15 | **VENCIDA** |
| **ADR-067** — defensa en profundidad de frontmatter | 3 capas propias: test de auditoría, gate de pre-commit, hook PostToolUse sobre SKILL.md, más plantilla canónica. | La spec de Agent Skills ships un validador oficial: `skills-ref validate ./my-skill` — "checks that your SKILL.md frontmatter is valid and follows all naming conventions". Cubre buena parte de las capas 1-2. **Incertidumbre declarada:** no pude fechar cuándo `skills-ref` estuvo disponible, así que no puedo afirmar que existía el 2026-04-24. Por eso VENCIDA y no REINVENCIÓN. | agentskills.io/specification.md §Validation ; github.com/agentskills/agentskills/tree/main/skills-ref — acceso 2026-08-15 | **VENCIDA** |

### Sobre la ausencia de REINVENCIÓN

No se encontró **ninguna** reinvención confirmada. Es un resultado, no una cortesía: en los cuatro casos candidatos (ADR-010, ADR-012, ADR-067, ADR-033) el mecanismo nativo o no existía en la fecha de la decisión, o sigue sin existir como estándar estable. La advertencia del encargo — *que algo sea propio no lo vuelve reinvención* — se aplicó y cambió dos veredictos.

---

## 4. Recomendaciones — las VENCIDAS primero

**V1. Re-medir la matriz de capacidades de Codex (ADR-064 / ADR-081).**
`manifests/harness-driver-capabilities.yaml` afirma "Bash only" con fecha de abril. El PR #23757 mergeó el 2026-05-23. Los tests de paridad excluyen eventos de tool no-Bash citando esa limitación: si la limitación se movió, la exclusión es hoy un **supresor que no suprime nada** — cobertura declarada que no se está tomando. Es la corrección más barata y la que más rápido envejece de nuevo: conviene que la matriz salga de una medición, no de un texto.

**V2. Migrar los 4 prompt-hooks a `type: "prompt"` nativo (ADR-012).**
El harness adoptó el mecanismo. Mantener el shell-out a Haiku desde bash paga latencia, manejo de errores y presupuesto propios por algo que ahora tiene campo `model` y timeout nativos. Las plantillas en `templates/prompt-hooks/` se conservan casi tal cual: cambia el invocador, no el contenido.

**V3. Revisar los 21 eventos de hook sin cubrir (ADR-010).**
No se trata de registrar los 31. Se trata de que hay maquinaria del repo que hoy se implementa por los costados cuando existe el evento nativo:

- `PostToolUseFailure` ↔ `error-learning.jsonl`
- `SessionEnd` ↔ la disciplina de `/session-wrapup`
- `SubagentStop` ↔ telemetría de agentes (ADR-028)
- `WorktreeCreate` / `WorktreeRemove` ↔ ADR-117 (stash/worktree)
- `PermissionRequest` / `PermissionDenied` ↔ perfiles de seguridad
- `ConfigChange` / `InstructionsLoaded` ↔ documentation-truth (ADR-277)

Nota lateral: ADR-010 dice que "settings.json no usa la propiedad `async: true`". Es falso hoy — `grep -o '"async": *true' .claude/settings.json | wc -l` → **50**. Candidato directo para el ledger de documentation-truth (ADR-277).

**V4. Decidir sobre `skills-ref validate` (ADR-067).**
Correr el validador oficial en el gate de pre-commit y quedarse con las capas propias solo para lo que el validador no cubre (contenido de `description`, plantilla canónica). Si se decide no adoptarlo, que quede escrito el motivo — hoy no está evaluado.

### Después, las divergencias sin justificar

**D1. `audience:` → `metadata.audience` (ADR-019).**
188 archivos. El campo top-level lo ignoran los clientes conformes a la spec, así que no rompe nada — pero el repo está usando un casillero que la spec definió para otra cosa (nada) teniendo uno definido para exactamente esto. Dos caminos honestos: migrar a `metadata:`, o **escribir en el ADR por qué no** (p. ej. costo de migración, o que las herramientas propias leen top-level). Lo que no se sostiene es la sección "Alternatives Considered" actual: compara tres opciones propias y ningún mecanismo del harness.

**D2. ADR-087 — dejar escrito por qué no MADR.**
Daño bajo, costo de corrección bajísimo: un párrafo. Cero de 340 ADRs menciona la convención dominante del campo. El esquema de sufijos-letra (`028a/b/c`) es defendible; que no esté contrastado, no.

### Lo que está bien y conviene no tocar

ADR-049 es el modelo de redacción del corpus: evalúa la alternativa externa con tabla, la reconoce superior en varias dimensiones, y escribe **en qué condiciones cambiaría de opinión**. Si se quiere una plantilla para arreglar D1 y D2, es ésa.

---

## 5. Clasificación temática de los 340

Salida de `classify_adrs.py` (clasificador por keywords sobre nombre + primeros 4 KB del cuerpo; un ADR cae en un solo tema, el de mayor score).

| Tema | ADRs | Evaluados a fondo |
|---|---|---|
| testing/quality-gates | 58 | 1 (ADR-072) |
| skills/primitives | 55 | 3 (ADR-019, 067, 329) |
| concurrency/session-safety | 43 | 0 |
| agents/orchestration | 29 | 1 (ADR-033) |
| docs/truth-maintenance | 28 | 1 (ADR-087) |
| cost/routing/llm | 25 | 1 (ADR-049) |
| harness/cross-harness | 24 | 3 (ADR-008, 064, 081/159) |
| release/packaging/install | 22 | 1 (ADR-058) |
| hooks/lifecycle | 21 | 2 (ADR-010, 012) |
| memory/context | 12 | 0 |
| security/privacy | 8 | 0 |
| sdd/workflow | 6 | 0 |
| scope/naming/conventions | 5 | 0 |
| observability/telemetry | 4 | 0 |
| **Total** | **340** | **13** |

**327 ADRs quedan clasificados y NO evaluados en profundidad.** Zonas ciegas más grandes, por si se quiere una segunda pasada: `concurrency/session-safety` (43 ADRs, cero evaluados — y es el tema con más ADRs de alto score estructural: 116, 106, 117, 098, 226, 089, 200) y `memory/context` + `security/privacy` (20 ADRs combinados, cero evaluados).

---

## 6. Correcciones a las premisas del encargo

1. **"Hay 350 ADRs reales" → son 340.** 504 archivos en el directorio, menos 150 `.synthesis.md`, 11 tombstones y 3 meta (`INDEX`, `README`, `STATUS-TAXONOMY`). El `INDEX.md` dice "501 ADR files", que cuenta síntesis y tombstones como ADRs. Discrepancia menor pero es un número publicado: candidato al ledger de documentation-truth.

2. **"ADR-019 fijó el esquema de `SCOPE:` sin evaluar un mecanismo nativo" → confirmado, y con un matiz que mejora la nota del repo.** El mecanismo de comentario HTML antes del fence (`<!-- SCOPE: both -->`), que ADR-067 documenta como causa del bug del parser, **ya no existe en skills**: `for f in skills/*/SKILL.md; do head -1 "$f"; done | sort | uniq -c` → 192/192 empiezan con `---`. Eso importa porque la spec exige que el frontmatter YAML abra el archivo. El problema vivo hoy es distinto y más chico: `audience:` como clave top-level en vez de `metadata.audience`.

3. **"Los hooks de ciclo de vida no tienen estándar cross-harness, y eso hace legítima la capa propia" → sigue siendo cierto, pero se erosionó.** Codex, Cursor y Claude Code convergieron en vocabulario `PreToolUse`/`PostToolUse`/`SessionStart`/`Stop`, y las convenciones GenAI de OTel ya modelan `invoke_agent` / `execute_tool`. No hay estándar (siguen experimentales, sin 1.0), así que ADR-033 se mantiene como divergencia justificada — pero la premisa envejece y conviene re-verificarla en la próxima auditoría, no darla por sentada.

4. **El encargo pedía 12–15 decisiones al fondo; se entregan 13.** Dos candidatos previstos se cayeron por falta de fuente y se declaran no evaluados (§7), en vez de rellenarse.

---

## 7. VERIFICADO vs NO VERIFICADO

### VERIFICADO — con fuente externa citada y fecha de acceso

- Spec de Agent Skills: campos requeridos (`name`, `description`), opcionales (`license`, `compatibility`, `metadata`, `allowed-tools` experimental), `metadata` como map string→string para propiedades no definidas por la spec, campos desconocidos ignorados, frontmatter YAML debe abrir el archivo, validador `skills-ref`. — agentskills.io/specification.md, 2026-08-15
- Claude Code: 31 eventos de hook documentados; hooks `async`/`asyncRewake`, HTTP, `type: "prompt"` con campo `model`, `type: "mcp_tool"`. — code.claude.com/docs/en/hooks, 2026-08-15
- Claude Code: rutas de discovery de skills `.claude/skills/` y `~/.claude/skills/`. — code.claude.com/docs/en/skills, 2026-08-15
- Codex CLI: PR #23757 mergeado 2026-05-23 extendiendo cobertura de tool-hooks a function tools locales; issue #20204 con la brecha original. — github.com/openai/codex, 2026-08-15
- `AGENTS.md`: adopción 60.000+ repos, administración Linux Foundation / Agentic AI Foundation, soporte multi-harness. — codersera.com, blog.agentailor.com, 2026-08-15 *(fuentes de comunidad, no oficiales de la spec)*
- OTel GenAI: sigue en *Development*, sin 1.0, movido a repo dedicado en v1.42.0 (2026-06-12). — dev.to/azena-ai, greptime.com, 2026-08-15 *(comunidad, corroborado por dos fuentes independientes)*
- pytest: `pytest_collection_modifyitems` como patrón documentado para asignar markers dinámicamente. — Context7 `/pytest-dev/pytest`, `doc/en/example/markers.rst`, 2026-08-15 *(documentación oficial vía MCP)*
- MADR como convención del campo, numeración y semántica de supersede. — adr.github.io/madr, github.com/adr/madr, 2026-08-15
- LiteLLM / Bifrost: estado 2026, brecha de performance, el compromiso de cadena de suministro como eje de la discusión. — medium.com/@pranaybatta2014, getmaxim.ai, 2026-08-15 *(comunidad y contenido de vendor — el segundo tiene interés comercial en la comparación; pesar en consecuencia)*

Mediciones sobre el repo (comandos reproducibles, todos en §2, §3 y §4): 340 ADRs reales; 10 tipos de evento registrados con 161 hooks; 188 skills con `audience:` top-level; 0 hooks `type: "prompt"`; 50 `"async": true`; 192/192 SKILL.md abriendo con `---`; 0/340 ADRs mencionando MADR/Nygard/adr-tools.

### NO VERIFICADO — juicio propio, sin fuente externa

- **La fecha de disponibilidad de `skills-ref`.** No pude establecer si existía el 2026-04-24. Por eso ADR-067 quedó VENCIDA y no REINVENCIÓN; con esa fecha el veredicto podría endurecerse.
- **ADR-259 (postura clean-room / patterns-only) — NO EVALUADA.** El razonamiento interno y la cita de 17 USC §102(b) parecen correctos, pero no obtuve fuente externa sobre práctica establecida de clean-room, así que no emito clasificación.
- **ADR-105 (claim-verification-contract) — NO EVALUADA.** Alto score estructural, pero no encontré un estándar externo contra el cual contrastarlo. Ausencia de búsqueda exitosa no es prueba de ausencia de estándar.
- **Los 327 ADRs no evaluados.** Sin juicio. La clasificación temática de §5 es un mapa para elegir dónde mirar después, no una evaluación.
- **El peso relativo de las fuentes de comunidad.** `AGENTS.md`, OTel GenAI y la comparación de gateways se apoyan en fuentes de comunidad y de vendor, no en specs oficiales. Corroboré con dos fuentes independientes donde pude; aun así pesan menos que la doc oficial de Claude Code, de Agent Skills o de pytest.
- **Que los hooks registrados efectivamente disparen.** Se leyó `.claude/settings.json`; no se ejecutó nada. El precedente del rate-limiter (registrado en la doc, 0 disparos en telemetría) sugiere que registro ≠ ejecución, y esta auditoría no lo midió.
