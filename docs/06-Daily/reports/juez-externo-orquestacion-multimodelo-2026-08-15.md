# Juez externo — orquestación de agentes con múltiples modelos en harnesses de coding agents

**Fecha:** 2026-08-15
**Rol:** juez externo. No leí el código del repo para formar opinión; el material es lo publicado afuera.
**Pregunta:** ¿los harnesses ya resuelven nativamente correr agentes con modelos distintos, y hacer que se comporten de forma parecida entre sí?

---

## 1. La respuesta

**Parcialmente, y en la mitad barata.**

**Todos permiten. Ninguno resuelve.**

Al 2026-08-15, los siete harnesses que pude verificar contra doc oficial dejan elegir modelo
por subagente. Es plomería y está documentada. Lo que **ningún harness define** es un contrato
de comparabilidad: no hay en la documentación de Claude Code, Codex CLI, opencode, Gemini CLI,
Cursor, Zed ni Continue una sola frase que garantice —ni que intente— que dos subagentes de
modelos distintos devuelvan el mismo formato, con las mismas garantías, y fallen de la misma
forma. Lo que devuelven es "un resumen" / "un mensaje final" en texto libre.

Tres evidencias duras de que el hueco es real y conocido, no una omisión de lectura mía:

1. **Claude Code**: el pedido de contrato de salida para subagentes existe y fue **cerrado sin
   plan**. Issue [anthropics/claude-code#20625](https://github.com/anthropics/claude-code/issues/20625),
   abierta 2026-01-24, cerrada 2026-02-28 con `state_reason: not_planned` (cierre automático por
   inactividad, sin respuesta de mantenedor). El texto del pedido nombra el problema con las
   palabras del operador: *"they cannot declare a structured-output contract […] without adding
   another orchestration layer around the CLI"*.
2. **Codex CLI**: la doc oficial de subagentes recomienda *"Return **summaries** from subagents
   instead of raw intermediate output"* — una recomendación de prompt, no un contrato.
   Cero menciones de schema, formato o consistencia entre modelos en las 21.893 bytes del
   documento.
3. **El único lugar donde ese contrato SÍ está escrito no es un harness.** Es
   `@ai-sdk/harness` de Vercel — una "Harness Specification" de terceros, marcada
   `**experimental**`, con adaptadores para claude-code, codex, opencode, cline, deepagents,
   grok-build, pi y acp. Ver §4.

Corolario para el encargo: si el proyecto del operador construyó una capa de comparabilidad
sobre agentes de modelos distintos, **no está reinventando una feature de harness, porque esa
feature no existe en ningún harness**. Lo que sí existe, desde hace pocas semanas y todavía
experimental, es un competidor externo a esa capa (§4). Eso es un dato de competencia, no de
reinvención — y **no es una recomendación de adoptarlo**: `manifests/external-tool-adoption-freeze.yaml`
está `frozen: true` y descongelar es decisión del operador con revisión legal.

---

## 2. Método y estados de evidencia

Tres estados, marcados en cada fila:

- **[DOC]** existe y está documentado en fuente oficial (o en el repo oficial del proyecto).
- **[CÓDIGO]** existe en el código/repo pero no en la doc.
- **[BLOG]** lo afirma una fuente secundaria y no lo pude confirmar → **no es evidencia**, y no
  lo uso para llenar ninguna celda de la tabla.

**Sobre espejos.** El único caso ambiguo es OpenAI. `docs/config.md` del repo `openai/codex`
hoy es un **stub de 726 bytes** que solo apunta a `developers.openai.com`, y esa URL responde
**308 Permanent Redirect** hacia `learn.chatgpt.com/docs/...`. O sea: `learn.chatgpt.com` **no
es un espejo**, es el destino oficial del redirect de OpenAI. Aun así crucé: las claves
`agents.*`, `model_providers.<id>.wire_api` y el schema de agente custom las verifiqué por
`grep` sobre el markdown crudo descargado, no por resumen de un modelo. Las marco abajo.

**Reproducción** (read-only, deterministas):

```bash
# el stub del repo oficial de codex
curl -s https://raw.githubusercontent.com/openai/codex/main/docs/config.md

# la referencia real, y la restricción de wire_api
curl -sL https://learn.chatgpt.com/docs/config-file/config-reference.md \
  | grep -n -A4 'wire_api'

# claves [agents] de codex
curl -sL https://learn.chatgpt.com/docs/config-file/config-reference.md \
  | grep -n 'key: "agents' -A6

# schema de subagente de gemini-cli
curl -sL https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/core/subagents.md \
  | grep -n '| `model`'

# el contrato de capacidad de la capa de terceros
curl -sL https://raw.githubusercontent.com/vercel/ai/main/packages/harness/README.md \
  | grep -n 'HarnessCapabilityUnsupportedError' -B6

# el pedido cerrado sin plan en Claude Code
curl -s https://api.github.com/repos/anthropics/claude-code/issues/20625 \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['state'],d['state_reason'],d['closed_at'])"
```

---

## 3. Tabla por harness — permite vs. resuelve

*Permite* = configurar modelo distinto por agente. *Resuelve* = contrato para que agentes de
modelos distintos se comporten de forma comparable (mismo formato de salida, mismas garantías,
misma forma de fallar).

| Harness | ¿Permite modelo por agente? | ¿Cross-vendor? | ¿Resuelve comparabilidad? | Fuente |
|---|---|---|---|---|
| **Claude Code** | **Sí [DOC]** — `model:` en frontmatter de `.claude/agents/*.md`. Acepta `sonnet`/`opus`/`haiku`/`fable`, IDs completos (`claude-opus-5`), o `inherit` (default). También `effort`, `maxTurns`, `permissionMode`, `isolation`. | **No.** La doc solo nombra modelos Claude; el campo acepta *"the same values as the `--model` flag"*. | **No.** El resultado es *"only the summary"* / *"a final report"*. Sin schema. Pedido de contrato cerrado `not_planned` (#20625). | [code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents) · [issue #20625](https://github.com/anthropics/claude-code/issues/20625) |
| **Codex CLI** | **Sí [DOC]** — agentes custom en `~/.codex/agents/*.toml` o `.codex/agents/*.toml`, campos obligatorios `name`/`description`/`developer_instructions`, más `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`. Global: `agents.default_subagent_model`, `agents.max_concurrent_threads_per_session`, `agents.enabled`. Built-ins: `default`, `worker`, `explorer`. | **Ambiguo.** `model_providers.<id>` permite proveedores custom (`base_url`, `env_key`, `wire_api`) pero la referencia dice textual: *"`responses` is the only supported value"* — hay que hablar Responses API. Y si un archivo de agente acepta `model_provider` **no está documentado** (la doc dice "other supported config.toml keys **such as**", lista no exhaustiva). | **No.** Única guía sobre salida: *"Return **summaries** from subagents instead of raw intermediate output."* Cero schema, cero mención de consistencia entre modelos. | [learn.chatgpt.com/docs/agent-configuration/subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) · [config-reference](https://learn.chatgpt.com/docs/config-file/config-reference) (ambas vía 308 desde `developers.openai.com`) — claves verificadas por grep |
| **opencode** | **Sí [DOC]** — agentes en `opencode.json` o markdown en `.opencode/agents/`. `model` con formato `provider/model-id`, más `temperature`, `mode` (`primary`/`subagent`/`all`), `permission`. | **Sí, el más amplio.** *"opencode uses the AI SDK and Models.dev to support 75+ LLM providers"*, más locales vía Ollama / llama.cpp / LM Studio. | **No.** La doc no dice nada sobre formato de salida ni normalización entre proveedores. | [opencode.ai/docs/agents](https://opencode.ai/docs/agents/) · [opencode.ai/docs/providers](https://opencode.ai/docs/providers/) |
| **Gemini CLI** | **Sí [DOC]** — frontmatter con `name`, `description`, `kind` (`local`/`remote`), `tools`, `mcpServers`, `model`, `temperature`, `max_turns` (30), `timeout_mins` (10). `model` default `inherit`. | **No documentado.** El schema dice *"Specific model to use (for example, `gemini-3-preview`)"*; todos los ejemplos son Gemini. | **No.** El schema no incluye formato de salida. | [google-gemini/gemini-cli · docs/core/subagents.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/core/subagents.md) |
| **Cursor** | **Sí [DOC]** — agentes en `.cursor/agents/` o `~/.cursor/agents/`; frontmatter `name`, `description`, `model`, `readonly`, `is_background`. | **Sí, y es el caso más fuerte de multi-vendor real por subagente.** El doc muestra IDs de tres proveedores distintos: `composer-2` (Cursor), `gpt-5.6-sol` (OpenAI), `claude-opus-5[effort=high,context=300k]` (Anthropic), con parámetros entre corchetes. | **No.** *"works autonomously, and returns a final message with its results."* Sin formato. | [cursor.com/docs/subagents](https://cursor.com/docs/subagents) |
| **Zed** | **Sí [DOC]**, pero global, no por agente: setting `agent.subagent_model` (junto a `agent.inline_assistant_model`, `agent.commit_message_model`). Los "Agent Profiles" gobiernan herramientas, no modelo. | **Sí** a nivel de proveedores del editor. | **No.** *"Most Zed AI features use the selected model's default generation behavior."* | [zed.dev/docs/ai/agent-settings](https://zed.dev/docs/ai/agent-settings) |
| **Continue** | **Distinto eje**: no subagentes sino **roles** por modelo — `chat`, `edit`, `apply`, `autocomplete`, `embed`, `rerank`, `summarize` (default `[chat, edit, apply, summarize]`). Es lo más cercano a un *routing* declarativo por función. | **Sí**, roles asignables a modelos de cualquier proveedor. | **No.** Nada sobre normalización de salida entre proveedores. | [docs.continue.dev/reference](https://docs.continue.dev/reference) |
| **Cline, Windsurf, Aider, Kilo** | **No verificado.** Ver §6. | — | — | — |

**Lectura de la tabla:** la columna "permite" está resuelta y hasta commoditizada — Cursor y
opencode permiten cruzar vendors por agente sin fricción. La columna "resuelve" está **vacía en
las siete filas verificadas**. Esa asimetría es el hallazgo.

Detalle que vale marcar: Codex publicó **`agents.max_depth` / anidamiento acotado por default**
y la comunidad ya reporta los problemas operativos de correr flotas (huérfanos, contadores
fantasma, árboles de procesos MCP que no mueren). Buscando `subagent` en el título de issues de
`openai/codex` salen **406 resultados**, la mayoría de agosto 2026 y sobre ciclo de vida, no
sobre modelos. O sea: el ecosistema ya está peleando el problema de **operar** flotas de
subagentes; el de **comparar** su salida ni siquiera está planteado como problema.

---

## 4. Lo que sí define un contrato — y no es un harness

`@ai-sdk/harness` (Vercel AI SDK) es, hasta donde pude verificar, la **única** pieza publicada
que hace lo que el operador llama "resolver". No es un harness: es una especificación con
adaptadores **sobre** los harnesses.

Verificado en el repo oficial `vercel/ai`, directorio `packages/`:

- Adaptadores existentes: `harness-claude-code`, `harness-codex`, `harness-opencode`,
  `harness-cline`, `harness-deepagents`, `harness-grok-build`, `harness-pi`, `harness-acp`.
- El README se titula literalmente **"Harness Specification and Agent"** y arranca con
  `_This package is **experimental**._`
- Hay **versión de especificación**: `specificationVersion: 'harness-v1'`.
- Hay **contrato de salida cross-runtime**: *"Set `output` on `HarnessAgent` to require the
  same typed, schema-backed output on every turn."*
- Y —esto es lo que lo separa de todo lo demás— hay **forma de fallar definida**: *"the adapter
  must enforce the schema and emit the resulting JSON through normal text parts. **If the
  runtime cannot honor the format, throw `HarnessCapabilityUnsupportedError` before starting the
  turn.**"*

Eso es exactamente la tríada del encargo: mismo formato, misma garantía, misma forma de fallar.

**Cronología, porque importa:** la capacidad NO existía hasta hace horas. El pedido
[vercel/ai#16120](https://github.com/vercel/ai/issues/16120) se abrió el 2026-06-15 diciendo que
`HarnessAgent` tenía el genérico `OUTPUT` fijado en `never` y *"the harness contract is
discarding a feature both adapters' runtimes natively expose"*. Un mantenedor confirmó el
2026-07-02: *"**Feature is not available.**"* El PR que lo implementa,
[vercel/ai#18937](https://github.com/vercel/ai/pull/18937), se mergeó el **2026-08-15T19:14:40Z**
— hoy.

**Alcance real, sin inflarlo:** `@ai-sdk/harness` normaliza **entre harnesses** (Claude Code vs.
Codex vs. opencode), no entre modelos dentro de un mismo harness. Cada adaptador queda pegado al
modelo que su harness sabe manejar. Además requiere sandbox con puertos
(`@ai-sdk/sandbox-vercel` es *"the supported choice today"*), es experimental, y es TypeScript.
No es un estándar: es el producto de un vendor.

---

## 5. El estándar emergente — qué es cierto del encargo y qué no

**La premisa del encargo es correcta en el hecho y engañosa en la fecha y en el alcance.**

**Cierto [DOC]:** la Agentic AI Foundation existe, bajo la Linux Foundation, anunciada el
**9 de diciembre de 2025** — no "hoy". Proyectos fundacionales: MCP (Anthropic), goose (Block),
AGENTS.md (OpenAI). Miembros Platinum: AWS, Anthropic, Block, Bloomberg, Cloudflare, Google,
Microsoft, OpenAI.
Fuente: [linuxfoundation.org — press release](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation).

**Cierto [DOC]:** el sitio de AGENTS.md confirma la tutela — *"AGENTS.md is now stewarded by the
Agentic AI Foundation under the Linux Foundation"* — y lista 26+ herramientas compatibles,
incluyendo Codex, Cursor, Gemini CLI, Windsurf, Zed, opencode, Aider, Kilo Code, RooCode,
Copilot. Fuente: [agents.md](https://agents.md/).

**Falso en el alcance, y es el punto que decide:** **AGENTS.md no cubre orquestación. Cubre
instrucciones, y nada más.** Estandariza *"a dedicated, predictable place to provide the context
and instructions"* — build/test, estilo, testing, seguridad, formato de commits. El anuncio de
la LF **no menciona** orquestación, coordinación multi-agente ni selección de modelo.

Y hay prueba positiva de que el hueco está identificado y **abierto**:

- [agentsmd/agents.md#149](https://github.com/agentsmd/agents.md/issues/149) — *"Proposal: Expand
  AGENT.md scope to cover sub-agents + enable interoperable linking with skills, hooks, and
  rules"*. Abierta el 2026-02-08. **Estado: open. Comentarios: 0.** Seis meses sin una sola
  respuesta.
- [agentsmd/agents.md#184](https://github.com/agentsmd/agents.md/issues/184) — *"[Feature] Agent
  Specification"*, un `.agent/` tool-agnostic que incluiría *"Define Subagent Personas Schema"*.
  Abierta 2026-05-11, **open**, 2 comentarios. Y su propio "Out of Scope" excluye la lógica de
  runtime — o sea, aunque prosperara, estandarizaría **dónde se declara** un subagente, no **cómo
  se comporta**.

**Nada equivalente para routing de modelos.** Barrí las 31 propuestas de proyecto de la AAIF
(`aaif/project-proposals`). Lo más cercano:

- **A2A (Agent2Agent Protocol)** — propuesta #37, **aprobada**: el TC la aprobó como Growth Stage
  el 2026-07-15 y el Governing Board el **2026-08-04** (verificado en los comentarios del issue).
  Pero A2A es comunicación **entre sistemas de agentes opacos** de distintos vendors — *"agents
  discover capabilities, negotiate modalities, and collaborate"* — no un contrato de
  comportamiento para subagentes dentro de un harness.
- **agentgateway** (aceptado, ya listado en aaif.io) y **Agent Router / Envoy AI Gateway**
  (propuesta #18, **todavía abierta** desde 2026-04-24): son *routing* de tráfico LLM a nivel de
  red — auth, rate limiting, failover entre proveedores. Enrutan **requests**, no comportamiento.

**Trampa que encontré y conviene anotar:** `agenticaifoundation.org` **no es el sitio de la
fundación** — hoy responde 307 hacia una página de GoDaddy "for sale". El sitio real es
**[aaif.io](https://aaif.io/)** (org de GitHub: `github.com/aaif`). Cualquier cita que apunte al
primero está citando un dominio en venta.

---

## 6. Lo que no pude confirmar

Lo dejo explícito en vez de rellenarlo con secundarias:

1. **Si un archivo de agente custom de Codex acepta `model_provider`.** La doc dice que se pueden
   incluir "otras claves soportadas de `config.toml`, **tales como** `model`,
   `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, `skills.config`" — lista abierta. Si
   `model_provider` funciona ahí, un subagente de Codex podría apuntar a un proveedor no-OpenAI
   que hable Responses API. **No documentado.** Se resuelve leyendo el parser de la capa de config
   de rol en `openai/codex`, que no hice por presupuesto.
2. **Cline, Windsurf, Aider y Kilo Code**: no verifiqué su config de modelo por agente contra doc
   oficial. Único dato duro que tengo es indirecto y sirve poco: existe `@ai-sdk/harness-cline`,
   o sea Cline es un runtime adaptable. Sobre los otros tres, nada verificado.
3. **Si el `model:` de Gemini CLI acepta IDs no-Gemini.** El schema no lo prohíbe explícitamente;
   los ejemplos son todos Gemini. Estado: no documentado en ninguna dirección.
4. **Si los IDs cross-vendor de Cursor (`gpt-5.6-sol`, `claude-opus-5`) llegan a la API del
   vendor o pasan por el gateway propio de Cursor.** La doc remite a "the models reference" y no
   aclara la ruta. Para la pregunta "permite" da igual; para garantías de comportamiento, no.
5. **Los tres estados de `wire_api`.** Verifiqué por grep que la referencia dice *"`responses` is
   the only supported value"*. No verifiqué si el código acepta `chat` como legacy no documentado.

---

## 7. Qué del encargo era falso o estaba desactualizado

Recuento, como pide la norma:

1. **"Hoy se verificó que AGENTS.md pasó a la Agentic AI Foundation"** — el hecho es cierto pero
   **la fecha es de hace ocho meses** (9-dic-2025), no de hoy. Si el orquestador lo verificó "esta
   mañana contra un mirror" y lo reportó como novedad, reportó como nuevo algo que estaba
   consolidado. El contenido resiste; la novedad no.
2. **"¿cubre orquestación o solo instrucciones?"** — la pregunta tenía razón en sospechar:
   **solo instrucciones**, y la propuesta de extenderlo a subagentes lleva seis meses abierta con
   cero comentarios.
3. **"Repos oficiales en GitHub: leé `docs/` del repo `openai/codex`"** — **esa instrucción ya no
   apunta a la fuente autoritativa**. `docs/config.md` es hoy un stub de 726 bytes; `agents_md.md`
   son 126 bytes; `skills.md`, 115. Todo redirige a `developers.openai.com`, que a su vez hace 308
   a `learn.chatgpt.com`. Quien cite "`docs/config.md` del repo `openai/codex`" en agosto 2026
   está citando un cartel indicador. El encargo mencionaba esa ruta como contraste con los blogs
   de SEO — el contraste sigue siendo válido, la ruta no.
4. **"OpenAI Codex CLI — subagentes nativos"** planteado como incógnita: **existen, están en GA y
   con doc propia**, incluyendo tres built-ins (`default`/`worker`/`explorer`), `[agents]` con
   límites de concurrencia, y anidamiento acotado por default.
5. **"la AAIF tiene tres proyectos"** (implícito en el encargo) — son **cuatro o cinco** al día de
   hoy: se sumaron agentgateway y A2A, este último aprobado por el Governing Board el 2026-08-04,
   once días antes de este informe.
6. **Corrección al método del propio encargo:** el brief pedía priorizar "los tres principales"
   (Claude Code, Codex, opencode). Seguirlo al pie habría dejado afuera **Cursor**, que es el
   único harness con doc oficial mostrando tres vendors distintos por subagente — el ejemplo más
   fuerte de la columna "permite". Prioricé según la pregunta, no según la lista.

---

## 8. Nota de alcance

Este informe describe el estado del arte. **No recomienda adoptar nada.**
`manifests/external-tool-adoption-freeze.yaml` está `frozen: true` desde 2026-05-11 por riesgo de
propiedad intelectual; descongelar requiere revisión legal y es decisión del operador con su
propio gate. En particular, la mención de `@ai-sdk/harness` en §4 es un dato de estado del arte
—existe, es experimental, hace X— y no una sugerencia de usarlo, copiarlo ni mirarle el código.

---

## Fuentes

Oficiales (primarias):
- [Claude Code — Subagents](https://code.claude.com/docs/en/sub-agents)
- [anthropics/claude-code — issue #20625](https://github.com/anthropics/claude-code/issues/20625)
- [Codex — Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) (destino 308 de `developers.openai.com/codex/subagents`)
- [Codex — Config reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- [openai/codex — docs/config.md](https://github.com/openai/codex/blob/main/docs/config.md) (stub)
- [opencode — Agents](https://opencode.ai/docs/agents/) · [Providers](https://opencode.ai/docs/providers/)
- [google-gemini/gemini-cli — docs/core/subagents.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/core/subagents.md)
- [Cursor — Subagents](https://cursor.com/docs/subagents)
- [Zed — Agent settings](https://zed.dev/docs/ai/agent-settings)
- [Continue — Reference](https://docs.continue.dev/reference)
- [Linux Foundation — formación de la AAIF](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)
- [agents.md](https://agents.md/) · [aaif.io](https://aaif.io/)
- [agentsmd/agents.md #149](https://github.com/agentsmd/agents.md/issues/149) · [#184](https://github.com/agentsmd/agents.md/issues/184)
- [aaif/project-proposals #37 (A2A)](https://github.com/aaif/project-proposals/issues/37) · [#18 (Agent Router)](https://github.com/aaif/project-proposals/issues/18)
- [vercel/ai — packages/harness/README.md](https://github.com/vercel/ai/blob/main/packages/harness/README.md) · [issue #16120](https://github.com/vercel/ai/issues/16120) · [PR #18937](https://github.com/vercel/ai/pull/18937)

Secundarias consultadas y **no usadas como evidencia**: OpenAI (post institucional sobre la AAIF),
CDO Magazine, eeNews Europe, IntuitionLabs, Credal, foro de Cursor, blogs de terceros sobre
subagentes de Codex y Gemini CLI. Ninguna afirmación de la tabla ni del veredicto se apoya en
ellas.
