# Reinvención vs. adopción — capa de skills y rules

Alcance: `skills/` y `rules/` del SO. No cubre `lib/`, `hooks/` ni dependencias
Python/Go (esas ya tienen su propio ledger en `manifests/external-tools-adoption.yaml`
y `manifests/dependency-adoption-evidence.yaml`). Diagnóstico únicamente — el
freeze de adopción (`manifests/external-tool-adoption-freeze.yaml`, `frozen: true`
desde 2026-05-11) prohíbe proponer aquí adoptar, vendorizar o instalar nada.

## Resumen ejecutivo

De 18 pares evaluados en la tabla de solapamiento: **6 REINVENTADO, 7 JUSTIFICADO,
5 ÚNICO**. No es un veredicto mayoritariamente cómodo ni mayoritariamente incómodo:
está repartido, y los dos REINVENTADO más concretos tienen evidencia dura, no
apreciación — dos skills propias (`test-driven-development`, `systematic-debugging`)
duplican, nombre por nombre, skills que ya están vendorizadas en este mismo repo
como submódulo MIT (`.claude/plugins/hermes-agent/skills/software-development/`),
y el propio hook de guardia (`reinvention-prevention.md`) que debería haberlo
atrapado tiene **1 sola entrada** en `.cognitive-os/adoption-registry.yaml` pese a
193 skills construidas. El hallazgo más caro no es un skill individual: es que
`manifests/external-tools-adoption.yaml` ya marcó en 2026-05-09 "assess la
conformidad de `skills/` contra el ecosistema Agent Skills / mdskills / Trigger.dev
Skills" y ese ítem sigue en `status: assess_contract_reference_only` sin resolver,
tres meses después.

## Correcciones a las premisas del encargo

1. **"197 skills" es incorrecto — son 193.** `ls -d skills/*/ | wc -l` → 193 (118
   directorios reales + 75 symlinks a 17 paquetes bajo `packages/*/skills/`, sin
   duplicados: `readlink -f` sobre los 75 symlinks da 75 destinos únicos, ninguno
   coincide con los 118 directorios reales). Comando: `find skills -maxdepth 1
   -mindepth 1 -type d | wc -l` (118) + `find skills -maxdepth 1 -mindepth 1 -type
   l | wc -l` (75) = 193.
2. **"131 rules" es correcto en el conteo crudo, pero 2 de esos 131 no son reglas
   de política** — `ROADMAP.md` y `RULES-COMPACT.md` son índices/meta-documentos,
   no contratos de comportamiento. Rules "reales": 129. Comando: `find rules
   -maxdepth 1 -name "*.md" -type f | wc -l` (114) + `-type l` (17) = 131.
3. **"Hermes agent" no es parte del "ecosistema de afuera" a investigar — ya está
   adentro.** Es un submódulo git vendorizado: `.gitmodules` línea 1-3 apunta
   `.claude/plugins/hermes-agent` → `https://github.com/NousResearch/hermes-agent.git`
   (MIT, confirmado en `github.com/NousResearch/hermes-agent/blob/main/LICENSE`).
   Más aún: `rules/reinvention-prevention.md` ya ordena revisarlo **primero**,
   antes que la propia `lib/`, antes de crear cualquier skill nueva. Tratarlo como
   "ecosistema externo a descubrir" hubiera sido redundante — el hallazgo real es
   que existe y el mecanismo que debería consultarlo casi no se usa (ver más abajo).
4. **"OpenClaw" existe pero no es lo que el encargo implicaba.** No es un
   registry de skills/prompts para agentes de codificación: es un agente
   autónomo personal de propósito general (ex-Clawdbot/Moltbot, de Peter
   Steinberger, ~145k stars, corre en la máquina del usuario y opera vía apps de
   mensajería). Es tangencial a "skills y rules reutilizables" — lo incluyo en la
   tabla de fuentes por completitud pero no aporta al cruce.
5. **El manifiesto `external-tools-adoption.yaml` NO es un ledger de skills/rules**
   — es un ledger de dependencias de paquete (Python/Go/Node). El manifiesto que
   sí toca la pregunta del encargo es `feature-tool-due-diligence.yaml`
   (`capability_id: skill-router-retrieval-boundary`, `agent-orchestration-boundary`),
   pero a nivel de 6 "boundaries" de capacidad gruesa, no por primitiva individual.
   El encargo pidió cruce por primitiva — eso es lo que este informe agrega, no
   lo que ya existía.

## Qué ya estaba registrado en manifests

- `manifests/external-tools-adoption.yaml` — entrada `agent-skills-ecosystem`
  (`Agent Skills ecosystem / mdskills / Trigger.dev Skills`, verdict `ASSESS`,
  `consumers: [skills]`, `status: assess_contract_reference_only`, fechado
  2026-05-09 vía `docs/06-Daily/reports/portable-ai-primitive-standards-due-diligence-2026-05-09.md`).
  **Está desactualizado**: marca la pregunta exacta de este encargo como
  pendiente de evaluar, y sigue pendiente 3 meses después sin que el informe de
  due-diligence haya bajado a nivel de skill individual.
- `manifests/feature-tool-due-diligence.yaml` — ya comparó el router de skills
  contra `dspy` (INTEGRATE, "optimiza programas LM tipados, no el enrutamiento
  de skills") y contra `obra/superpowers` (INTEGRATE, "fuente de metodología
  para skills, no implementación del router"). Ya comparó orquestación de
  agentes contra `langgraph` y `autogen` (ambos INTEGRATE/DEFER por no cubrir
  gobierno de worktree/branch/release). Estas decisiones son de alcance
  ("boundary"), no per-skill — no dicen si `skills/systematic-debugging`
  específicamente reinventa algo de `superpowers`.
- `manifests/dependency-adoption-evidence.yaml` + `feature-tool-due-diligence.yaml`
  ya resolvieron el caso del semantic router: se evaluó `aurelio-labs/semantic-router`
  y se descartó por inviable en PyPI (versión atascada en 0.0.3), documentado con
  razón técnica. Esto ya es exactamente el tipo de evidencia que este encargo pide
  — un ejemplo de que el proceso, cuando se usa, funciona.
- `manifests/cross-stack-adoption-truth.yaml` — confirma `hermes-agent`, `pi`
  (pi-mono) y `caveman` como `submodule_reference_only`: reconocidos, pero fuera
  del scope de dependencias en ejecución. Corrobora la corrección #3.
- `manifests/ai-agent-harness-landscape.yaml` — cubre la proyección hacia 30+
  harnesses (Cursor, Cline, Continue, Aider, AGENTS.md, etc.), no la capa de
  contenido de skills/rules en sí. Es el manifiesto más nuevo y mejor mantenido
  de los seis (`review_date: 2026-05-04`, con `next_action` por candidato).
- `rules/reinvention-prevention.md` — el mecanismo mandatorio existe y el hook
  **está registrado** (`grep -c reinvention-check .claude/settings.json` → 1,
  a diferencia de `rate-limiter.sh` que la propia rule documenta como no
  registrado). Pero `.cognitive-os/adoption-registry.yaml` tiene **una sola
  entrada** (`caveman-lite-preamble`, 2026-04-08) para 193 skills + 131 rules
  actuales, y `grep -c reinvention .cognitive-os/metrics/agent-heartbeat.jsonl`
  sobre 1543 líneas da 0 coincidencias. No puedo afirmar que el hook nunca
  disparó (el heartbeat puede no loguear ese string), pero el registro de
  decisiones que la regla exige sí está, en los hechos, prácticamente vacío.

## Inventario propio por función

Comando base: `find skills -maxdepth 1 -mindepth 1 \( -type d -o -type l \) -exec
basename {} \;` (193 nombres) y `find rules -maxdepth 1 -name "*.md"` (131
nombres). Agrupación por función, no exhaustiva primitiva por primitiva:

| Categoría | Skills (aprox.) | Rules (aprox.) | Ejemplos |
|---|---|---|---|
| SDD / spec-driven | 11 | 3 | `sdd-apply/spec/design/tasks/verify/explore/archive`, `plan-bug/chore/feature` |
| Verificación / gates / testing | 20 | 15 | `verification-before-completion`, `test-driven-development`, `run-tests`, `dod-check`, `trust-score.md`, `confidence-gate.md` |
| Seguridad | 9 | 8 | `secret-audit`, `semgrep-scan`, `vuln-remediation-flow`, `credential-management.md`, `supply-chain-defense.md` |
| Memoria / telemetría / observabilidad | 15 | 6 | `memory-scan`, `cognee-search`, `hook-timing`, `dogfood-score`, `engram-organization.md`, `observability.md` |
| Git / release | 11 | 2 | `bump-version`, `tag-release`, `release-os`, `release-publishing.md` |
| Orquestación de agentes | 31 | 12 | `agent-control`, `squad-manager`, `session-wrapup`, `queue-drain`, `orchestrator-mode.md`, `agent-escalation.md` |
| Integraciones a herramientas ya adoptadas | 6 | 4 | `deepeval-integration`, `ragas-integration`, `browser-task`, `context7-auto-trigger.md`, `parry-integration.md` |
| Investigación / análisis | 25 | 3 | `deep-research`, `repo-forensics`, `reverse-engineer`, `research-first-protocol.md` |
| Auditoría de primitivas/componentes | 11 | 2 | `primitive-harvester`, `component-reality-check`, `component-classification` (via rule) |
| Gestión de skills/rules en sí | 8 | 6 | `add-skill`, `install-skill`, `catalog-full`, `skill-management.md`, `skill-invocation-mandatory.md` |
| Infra / config / scaffolding | 34 | 10 | `add-hook`, `generate-config`, `project-scaffold`, `hook-security-profiles.md` |
| Costo / presupuesto | — | 8 | `token-economy.md`, `resource-governance.md`, `rate-limiting.md`, `cost-prediction.md` |
| Resto (misceláneo, sin categorizar a fondo) | ~12 | ~50 | naming, phase-aware, capability-levels, etc. — mayormente política organizacional sin equivalente externo |

La columna "rules" está más poblada de política organizacional pura (naming,
scope, phase-awareness, confidencialidad) que de mecanismos técnicos con
equivalente externo — eso ya se nota antes de cruzar con el ecosistema de afuera.

## El ecosistema externo

Relevado (ver Fuentes): Anthropic Agent Skills + marketplace oficial y
comunitario (>200 plugins, `obra/superpowers` con ~94k stars aceptado en el
marketplace oficial), `awesome-claude-code` / `awesome-claude-skills` (varios
forks, 1000+ skills indexadas por terceros), Claude Code plugin marketplaces
(`claude-plugins-official`, `claude-community`), `.cursor/rules` (formato
`.mdc`, 5 niveles de activación), Continue.dev (`.continue/rules`, YAML,
proyecto ya sin equipo full-time desde julio 2026), Aider (`CONVENTIONS.md` +
`.aider.conf.yml`), `AGENTS.md` (estándar universal, ahora bajo la Agentic AI
Foundation de Linux Foundation junto con MCP y `goose`, adoptado por 60k+
proyectos), OpenHands microagents (`.openhands/microagents`, con triggers
`always`/on-demand, migrando a `.agents/skills/`), SWE-agent (config YAML,
tool bundles), Devin Playbooks + Knowledge (tareas recurrentes vs. contexto
persistente), GitHub Copilot custom instructions + `SKILL.md` nativo desde
abril 2026, Cline (`.clinerules/`), **GitHub Spec Kit** (`specify → plan →
tasks → implement`, MIT, ~120k stars — el equivalente más directo a nuestro
pipeline SDD), BMAD-METHOD (agentes PM/Architect/SM/Dev vía slash commands,
también con gates de calidad), y frameworks de memoria de agente (Mem0, Zep/
Graphiti — ya evaluados internamente para un nicho distinto vía `cognee`).

Corrección de nombres mal recordados en el encargo: no encontré "Hermes agent"
como ecosistema externo (es interno, ver corrección #3); "OpenClaw" existe pero
es un agente autónomo general, no un registry de skills (corrección #4).

## Tabla de solapamiento

| Nuestra primitiva | Equivalente externo (URL, licencia) | Veredicto | Por qué |
|---|---|---|---|
| `skills/test-driven-development` | `hermes-agent` (vendorizado, MIT) → `skills/software-development/test-driven-development/SKILL.md` | **REINVENTADO** | Mismo nombre, mismo concepto, la fuente está en este mismo repo a un `find` de distancia y la regla propia manda revisarla primero. `adoption-registry.yaml` no tiene entrada para este skill. |
| `skills/systematic-debugging` | `hermes-agent` → `skills/software-development/systematic-debugging/SKILL.md` (MIT) | **REINVENTADO** | Misma razón que la fila anterior — evidencia idéntica, mismo submódulo. |
| `skills/sdd-*` (8 skills: propose/spec/design/tasks/apply/verify/explore/archive) | GitHub Spec Kit — `github.com/github/spec-kit` (MIT, ~120k★) | **JUSTIFICADO** | El loop conceptual (spec→plan→tasks→implement) no es original — spec-kit lo resuelve igual y es más maduro. Pero la versión propia está acoplada a Engram (`sdd/{change}/{phase}`), a `retry-contract.md` (máx. 3 reintentos, solo en FAIL+CRITICAL) y al archivo de ADRs propio; spec-kit no tiene ese acoplamiento. El matiz importa: si el acoplamiento se cae, la justificación se cae con él. |
| Enrutamiento semántico de skills (`lib/semantic_skill_matcher.py`, ADR-296) | `aurelio-labs/semantic-router` | **JUSTIFICADO** | Ya evaluado y descartado con evidencia técnica propia (paquete atascado en 0.0.3 en PyPI, sin símbolos `Route`/`RouteLayer`) — documentado en `dependency-adoption-evidence.yaml`. Este es el caso donde el proceso de due-diligence sí funcionó como debía. |
| `skills/deepeval-integration`, `ragas-integration`, `strands-evals-integration`, `browser-task` | DeepEval, RAGAS, browser-use (ya `ADOPT`/`INTEGRATE` en `external-tools-adoption.yaml`) | **ÚNICO** (como adaptador) | No reinventan la librería: son el adaptador que la expone al dispatcher/gobernanza propios (kill-switch, cost tracking). Es la integración documentada en ADR-288, no una reimplementación. |
| `rules/model-routing.md`, `model-directive.md`, `llm-dispatch.md` (ADR-049) | LiteLLM — `github.com/BerriAI/litellm` (MIT) | **JUSTIFICADO explícito** | No es solapamiento pasivo: `external-tools-adoption.yaml` tiene a LiteLLM con `verdict: REMOVE, status: cleanup_required` — se evaluó, se sacó del stack y se construyó la capa propia a propósito. Decisión documentada, no default. |
| `add-skill`, `install-skill`, `catalog-full`, `skill-creator`, `rules/skill-management.md` | Marketplace oficial de Claude Code (`/plugin`, `claude-plugins-official`, >200 plugins) + Anthropic Agent Skills registry | **REINVENTADO** (parcial) | La mecánica de catálogo/instalación/creación de skills reimplementa lo que un marketplace estándar ya resuelve. Coincide exactamente con la entrada `agent-skills-ecosystem` de `external-tools-adoption.yaml`, marcada `ASSESS` desde 2026-05-09 y nunca resuelta a nivel de skill. |
| Metodología de calidad/debug/TDD dispersa (`systematic-debugging`, `test-driven-development`, `epistemic-review`, `verification-before-completion`, `proof-drill`) | `obra/superpowers` — `github.com/obra/superpowers` (licencia no confirmada en esta pasada, aceptado en el marketplace oficial de Anthropic) | **REINVENTADO** | `feature-tool-due-diligence.yaml` ya concluyó "fuente de metodología para skills" — es decir, la propia organización ya decidió que superpowers debía informar estos skills. No hay entrada en `adoption-registry.yaml` que muestre que ese porteo ocurrió; el patrón de nombres sugiere reinvención paralela, no adaptación documentada. |
| `bump-version`, `tag-release`, `generate-changelog`, `validate-release`, `push-release`, `release-os` | semantic-release / changesets (ecosistema JS/Node maduro, MIT) | **REINVENTADO** | Nada en estos 6 skills está acoplado a algo específico de COS que un versionador semántico estándar no resuelva; el acoplamiento real (branching G2K) vive en la skill `release-based-flow`, que sí es específica y queda fuera de este veredicto. |
| `rules/rate-limiting.md` (token bucket + refill + diversity penalty) | Librerías de token-bucket genéricas (p. ej. `pyrate-limiter`, MIT) | **REINVENTADO** (en el mecanismo base) | El patrón de balde de tokens es de décadas y hay librerías maduras y chicas para la parte genérica. Agravante: el propio archivo de la regla dice que el hook **no está registrado** en `.claude/settings.json` (0 disparos en 37.424 filas de telemetría) — se construyó el mecanismo pero no se activó. |
| `rules/engram-organization.md` + `memory-scan`, `recall-search`, `conversation-memory` | Mem0 / Zep+Graphiti (memoria de agente, ambos con oferta open-source) | **JUSTIFICADO** | Mem0/Zep apuntan a personalización de consumidor o grafos temporales de hechos — no al modelo de topic-keys/sesión/observación con el que Engram gobierna decisiones de arquitectura y hallazgos de auditoría de este SO específico. Ya existe además `cognee` como dependencia `INTEGRATE` para el nicho de memoria-RAG, que es un layer distinto. |
| `rules/trust-score.md` + `skills/trust-audit`, `confidence-check` (bandas HIGH/MEDIUM/LOW/CRITICAL, evidencia+incertidumbre) | No se encontró equivalente directo en el research (DeepEval/RAGAS evalúan calidad de respuesta LLM, no el auto-reporte de confianza de un agente en formato estructurado) | **ÚNICO** | Nadie relevado exige al agente un sobre `TRUST_REPORT` con incertidumbre obligatoria como contrato de salida. |
| `rules/reinvention-prevention.md` (guardia que obliga a mirar hermes-agent/pi-mono antes de construir) | No se encontró equivalente (ningún harness relevado tiene un hook que fuerce mirar submódulos vendorizados antes de crear una skill) | **ÚNICO**, pero subejecutado | El mecanismo en sí no tiene par externo. La ironía: como muestra este mismo informe, no está evitando la reinvención que debería evitar (ver filas 1-2). |
| `manifests/ai-agent-harness-landscape.yaml` + proyección a 30+ harnesses (Cursor, Cline, Continue, Aider, AGENTS.md, etc.) | `AGENTS.md` como estándar universal cubre parte de esto, pero no la proyección activa multi-formato (`.cursor/rules`, `.clinerules`, `.continue/rules`, etc. generados desde una fuente única) | **ÚNICO** | Ningún proyecto relevado genera automáticamente los N formatos nativos de cada harness desde una fuente canónica propia; `AGENTS.md` es un formato a adoptar, no una herramienta de proyección. |
| `skills/semgrep-scan`, `secret-audit`, `vulnerability-scan` | Semgrep, gitleaks-style tooling (ya `INTEGRATE` como `enforcement-tools` en `external-tools-adoption.yaml`) | **ÚNICO** (como wrapper) | Exponen binarios ya adoptados como skill invocable — no reimplementan el scanner. |
| `rules/broken-window-policy.md`, `agent-quality.md`, `phase-aware-agents.md` | Ninguno — son política organizacional (no-TODOs, no-stubs, reescribir en fase `reconstruction`) | **ÚNICO** | No es una capacidad técnica sustituible por una librería; es una decisión de estilo del equipo. |
| `skills/deep-research`, `research-protocol`, `repo-forensics`, `reverse-engineer` | Ningún equivalente empaquetado encontrado (herramientas como `deep-research` de otros vendors son productos, no skills reutilizables de harness) | **ÚNICO** | Construidos como flujos de investigación propios de COS; no hay un "skill de deep-research" estándar de mercado equivalente al nuestro con estos triggers. |
| `skills/agent-control`, `squad-manager`, `session-wrapup`, `queue-drain` (31 skills de orquestación) | LangGraph, AutoGen (ya evaluados en `feature-tool-due-diligence.yaml`, `agent-orchestration-boundary`, decisión `BUILD`) | **JUSTIFICADO** | Decisión ya documentada con ADR-251: COS necesita gobernar worktree/branch/claims/receipts/freeze de release localmente; los frameworks son adapters, no reemplazo. |

## Fuentes

1. https://github.com/GetBindu/awesome-claude-code-and-skills (2026)
2. https://github.com/travisvn/awesome-claude-skills (2026)
3. https://github.com/ComposioHQ/awesome-claude-skills (2026)
4. https://www.agensi.io/learn/open-source-claude-code-skills-github (2026)
5. https://www.ayautomate.com/blog/best-claude-code-github-repos (2026)
6. https://claudefa.st/blog/tools/resources/awesome-claude-code (2026)
7. https://github.com/obra/superpowers (referenciado, 2026)
8. https://www.taskade.com/blog/claude-skills-explained (2026)
9. https://heyclau.de/entry/skills/anthropic-agent-skills (2026)
10. https://www.nimbleway.com/blog/anthropic-claude-agent-skills (2026)
11. https://claude-world.com/articles/anthropic-official-skills-complete-guide/ (2026)
12. https://designrevision.com/blog/official-claude-code-plugins (2026)
13. https://buildtolaunch.substack.com/p/best-claude-code-plugins-tested-review (2026)
14. https://www.agensi.io/learn/claude-code-plugin-marketplace-guide (2026)
15. https://www.sean-weldon.com/blog/2026-01-06-how-to-install-and-discover-claude-code-plugins-through-mark (2026-01)
16. https://www.digitalocean.com/resources/articles/what-is-openclaw (2026)
17. https://en.wikipedia.org/wiki/OpenClaw (2026)
18. https://medium.com/@vibecodingdirectory/how-to-structure-cursor-rules-in-2026-the-5-level-system-cursor-rules-eaf0df16e8e7 (2026)
19. https://dev.to/deadbyapril/the-best-cursor-rules-for-every-framework-in-2026-20-examples-29ag (2026)
20. https://docs.continue.dev/customize/deep-dives/rules (2026)
21. https://docs.continue.dev/reference (2026)
22. https://github.com/Aider-AI/conventions (2026)
23. https://aider.chat/docs/usage/conventions.html (2026)
24. https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation (2025-12)
25. https://agents.md/ (referenciado, 2026)
26. https://docs.openhands.dev/overview/skills (2026)
27. https://docs.all-hands.dev/modules/usage/prompting/microagents-repo (2026)
28. https://github.com/SWE-agent/SWE-agent (2026)
29. https://swe-agent.com/latest/config/config/ (2026)
30. https://docs.devin.ai/product-guides/creating-playbooks (2026)
31. https://medium.com/@nitinmatani22/devins-knowledge-base-how-to-teach-an-ai-agent-your-codebase-conventions-6a30a89eb3a1 (2026)
32. https://github.com/github/awesome-copilot/blob/main/docs/README.instructions.md (2026)
33. https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills (2026)
34. https://www.agensi.io/learn/github-copilot-skills-setup-guide (2026-04+)
35. https://github.com/github/spec-kit (2026)
36. https://github.com/github/spec-kit/blob/main/spec-driven.md (2026)
37. https://docs.cline.bot/customization/cline-rules (2026)
38. https://cline.ghost.io/clinerules-version-controlled-shareable-and-ai-editable-instructions/ (2026)
39. https://atlan.com/know/best-ai-agent-memory-frameworks-2026/ (2026)
40. https://blog.devgenius.io/ai-agent-memory-systems-in-2026-mem0-zep-hindsight-memvid-and-everything-in-between-compared-96e35b818da8 (2026)
41. https://github.com/bmad-code-org/BMAD-METHOD (referenciado, 2026)
42. https://reenbit.com/the-bmad-method-how-structured-ai-agents-turn-vibe-coding-into-production-ready-software/ (2026)
43. https://github.com/NousResearch/hermes-agent/blob/main/LICENSE (verificado localmente vía `.gitmodules` + búsqueda)
44. https://github.com/NousResearch/hermes-agent/blob/main/skills/software-development/requesting-code-review/SKILL.md (2026)

Evidencia local (comandos ejecutados en esta sesión, no URLs):
`ls -d skills/*/ | wc -l`, `find skills -maxdepth 1 -mindepth 1 -type d|l | wc -l`,
`find rules -maxdepth 1 -name "*.md" -type f|l | wc -l`, `cat manifests/*.yaml`,
`cat rules/reinvention-prevention.md`, `ls .claude/plugins/hermes-agent/skills/*/*`,
`grep -c reinvention-check .claude/settings.json`, `wc -l
.cognitive-os/adoption-registry.yaml`, `grep -c reinvention
.cognitive-os/metrics/agent-heartbeat.jsonl`.
