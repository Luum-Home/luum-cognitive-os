# Landscape de arneses de agentes — 19 de agosto de 2026

> **Método.** Todo número de este informe sale de una de dos fuentes: (a) la API
> pública de GitHub / npm consultada el 2026-08-19, con el comando escrito al
> lado; (b) una URL citada en `## Fuentes`. No hay cifras de memoria. Los
> comandos son reproducibles y read-only.
>
> **Comando base de cadencia** (usado en toda la tabla):
> ```bash
> curl -sL "https://api.github.com/repos/<org>/<repo>/releases?per_page=100" \
>   | python3 -c "import sys,json,datetime; r=json.load(sys.stdin); \
> d=sorted([x['published_at'][:10] for x in r], reverse=True); \
> old=datetime.date(*map(int,d[-1].split('-'))); \
> span=(datetime.date(2026,8,19)-old).days or 1; \
> print(r[0]['tag_name'], d[0], len(d), 'releases', 'rate %.1f/sem'%(len(d)/(span/7)))"
> ```
> **Comando base de descargas npm:**
> ```bash
> curl -s "https://api.npmjs.org/downloads/point/2026-07-19:2026-08-18/<paquete>"
> ```
>
> **Nota de reproducción:** el hook `bash-hot-path-dispatcher` (network egress
> guard) bloquea un heredoc que contenga estas URLs junto con las cadenas
> `.env` o `SECRET`. Este informe se escribió con la herramienta de archivo, no
> con `cat <<EOF`. Es un falso positivo del guard, no un problema del contenido.

---

## Resumen ejecutivo

1. **Claude Code domina la adopción real** (39% global, 47% US, mayo–jul 2026,
   n>15.000, JetBrains [F1]); Codex domina las descargas npm (67,9M/30d vs 63,0M
   de Claude Code, medido 2026-08-19).
2. **Codex y Claude Code son los dos que importan** para un SO de gobierno: son
   los únicos con hooks que **deniegan** una acción, documentados y estables.
3. **Sí, esto envejece rápido — y ya envejeció.** Codex shippea **16,3
   releases/semana**; Claude Code **5,9**; qwen-code **24,1**. El motor de hooks
   de Codex cambió en **6 de sus últimos 6 minors** (0.143 a 0.148, del 8-jul al
   18-ago), incluyendo cobertura de herramientas MCP el 2026-08-18 [F14].
4. **El caso más caro de envejecimiento no es una versión: es una muerte.**
   Google anunció el 2026-05-19 que Gemini CLI deja de servir el **2026-06-18**
   para tiers de consumo, migrando a Antigravity CLI [F11]. Treinta días entre
   anuncio y apagado. Ninguna cadencia de re-verificación mensual lo agarra a
   tiempo.
5. **La convergencia de estándares es real y va a favor del SO**: MCP, AGENTS.md
   y goose viven hoy bajo la Agentic AI Foundation (Linux Foundation) [F19], y
   Agent Plugins 1.0 (2026-08-06) unifica el empaquetado con firmas de Amazon,
   Cursor, Microsoft, OpenAI y Vercel [F20].
6. **Lo que NO converge son los hooks.** Cada arnés inventó el suyo: `hooks.json`
   (Claude, Codex, Copilot, Antigravity), `.cursor/hooks.json` (Cursor), plugin
   TypeScript (opencode), `amp.hooks` en settings (Amp). Ahí sigue habiendo
   trabajo de traducción, que es exactamente donde vive el SO.

---

## Correcciones a las premisas del encargo

1. **«El manifest tiene 40 días»** — Impreciso, y por dos lados.
   `git log -1 --format='%h %ad' --date=short -- manifests/harness-driver-capabilities.yaml`
   devuelve `785ced2f3 2026-07-10`, pero ese commit es el rename `lib` →
   `cos_lib`, no una re-verificación. La antigüedad **real** que importa es la
   que declara cada driver:
   - `opencode.version_baseline: "official-docs-2026-05-08"` → **103 días**.
   - `codex.version_baseline: "0.126.0-alpha.8"` → contra `0.148.0` publicada el
     2026-08-18 [F13], son **22 minors de atraso**.

   La cifra de 40 días subestima el problema por un factor de ~2,5.

2. **«No declara cuándo se verificó»** — Falso como está escrito.
   `grep -n version_baseline manifests/harness-driver-capabilities.yaml` muestra
   que **sí** declara un ancla por driver (`official-docs-2026-05-08`,
   `0.126.0-alpha.8`). Lo que no tiene es un campo `verified_at` uniforme y
   legible por máquina — que es un problema distinto y menor. La corrección
   importa porque el arreglo no es «agregar una fecha», es «hacer que el ancla
   que ya existe sea comparable con la versión viva del arnés».

3. **«Afirmaba que opencode soporta PreToolUse mientras el driver emite cero
   handlers ahí» — el manifest tenía razón; el defecto es del driver.**
   El manifest dice, literal:
   ```yaml
   PreToolUse:
     status: supported
     native_event: tool.execute.before
     enforcement: plugin_can_mutate_or_throw
   ```
   Y eso es **correcto al 2026-08-19**: la doc de opencode (última actualización
   19-ago-2026) lista `tool.execute.before` / `tool.execute.after` entre sus
   hooks de plugin, y su ejemplo canónico de protección de archivos de entorno
   bloquea lanzando una excepción [F7]. O sea: el mapa describía bien el terreno
   y el camino no se construyó. Llamarlo «el mapa envejeció y causó un defecto
   real» invierte la causa, y esa inversión lleva a arreglar el documento
   equivocado.

4. **El envejecimiento que sí duele está en el driver de codex, no en el de
   opencode.** El manifest declara `PreToolUse: limited / matcher_semantics:
   bash_only` con fallback gobernado. La doc oficial de Codex hoy dice que los
   hooks cubren «Bash, ediciones vía `apply_patch`, llamadas a herramientas MCP y
   otras function tools locales», que soportan `permissionDecision: "deny"`, y
   que están **habilitados por defecto** (`[features].hooks = false` para
   apagarlos; `codex_hooks` quedó como alias deprecado) [F12]. Esa es la línea
   del manifest que hay que reescribir primero.

5. **La lista de candidatos del encargo trae tres bajas y dos mudanzas.**
   - **Aider**: última release `v0.86.0` del **2025-08-09** [F16]; cero releases
     en los últimos 6 meses. Sigue citándose en comparativas, pero está parado.
   - **Roo Code**: repo **archivado** el 2026-05-15 (`archived: true` en la API).
   - **Windsurf**: Cognition la plegó dentro de Devin Desktop [F5].
   - **goose**: ya no es `block/goose`; el repo redirige a **`aaif-goose/goose`**,
     bajo la Agentic AI Foundation [F19].
   - **opencode**: ya no es `sst/opencode`; redirige a **`anomalyco/opencode`**.

   Un chequeo que resuelva nombres de repo sin seguir redirects (`curl` sin `-L`)
   devuelve `null` en tres de estos y los reporta como inexistentes. Lo verifiqué
   en carne propia en la primera pasada de este informe.

6. **«Cada versión y cada fecha lleva su URL al lado»** — Cumplido con un matiz
   que conviene decir: para versiones y fechas de release **no cito una URL de
   blog sino la API que las devuelve**, porque un blog se reescribe y la API no.
   La URL está igual, pero es la del endpoint, y el comando que la consulta está
   arriba. Es evidencia más fuerte, no más débil.

7. **No pude cerrar dos cosas.** (a) El Stack Overflow Developer Survey 2026:
   `https://survey.stackoverflow.co/2026/` y `/2026/ai` devuelven **404** al
   2026-08-19; las cifras que circulan (84% adopción, 29% confianza) vienen de
   terceros que lo citan [F3], no de la fuente. Las marco como **secundarias**.
   (b) La fecha exacta en que los hooks de Codex pasaron de opt-in a
   on-by-default: hay contradicción entre fuentes, documentada abajo.

8. **Advertencia operativa, no pedida pero relevante:** el network egress guard
   bloquea escribir este tipo de informe por heredoc de Bash, porque el cuerpo
   contiene URLs junto con las cadenas `.env` y `SECRET`. Cualquier automatismo
   futuro que genere este informe desde un script va a chocar con eso.

---

## El ranking y sus fuentes

### Adopción declarada por desarrolladores (la métrica más cercana a «qué usan»)

JetBrains Developer Ecosystem Survey 2026, décima edición, campo mayo–julio 2026,
n > 15.000 profesionales, publicada agosto 2026 [F1]:

| Herramienta | Adopción en el trabajo |
|---|---|
| Claude Code | **39%** global / 47% US |
| GitHub Copilot | 21% (baja desde 29% un año antes) |
| Codex | 16% |
| Cursor | 12% (baja desde 18% en enero) |
| JetBrains AI / Junie | 9% |
| OpenCode | 7% |
| Google Antigravity | 6% |

Contexto de la misma fuente: 90% usa agentes al menos semanalmente, 68% a diario.
Claude Code casi duplicó su adopción entre enero (18%) y mayo–julio (39%) [F1].

### Descargas npm — 30 días, 2026-07-19 a 2026-08-18

Medido el 2026-08-19 contra `https://api.npmjs.org/downloads/point/...` [F41]:

| Paquete | Descargas/30d | Última versión | Fecha |
|---|---:|---|---|
| `@openai/codex` | **67.877.458** | 0.148.0 | 2026-08-18 |
| `@anthropic-ai/claude-code` | **63.039.047** | 2.1.236 | 2026-08-19 |
| `opencode-ai` | 9.439.213 | 1.18.18 | 2026-08-13 |
| `@github/copilot` | 7.251.002 | 1.0.80 | 2026-08-14 |
| `@google/gemini-cli` | 1.801.983 | 0.56.0 | 2026-08-19 |
| `@qwen-code/qwen-code` | 302.938 | 0.21.14 | 2026-08-19 |
| `@sourcegraph/amp` | 112.376 | 0.0.1787169759-g8b6940 | 2026-08-19 |

### Estrellas de GitHub — API, 2026-08-19

`anomalyco/opencode` **199.197** · `anthropics/claude-code` **142.006** ·
`openai/codex` **106.851** · `google-gemini/gemini-cli` **106.582** ·
`zed-industries/zed` 88.894 · `OpenHands/OpenHands` 84.499 ·
`cline/cline` 66.490 · `warpdotdev/warp` 64.358 · `aaif-goose/goose` 53.008 ·
`Aider-AI/aider` 48.334 · `continuedev/continue` 35.547 ·
`cursor/cursor` 33.143 · `QwenLM/qwen-code` 27.197 ·
`RooCodeInc/Roo-Code` 24.331 (archivado) · `github/copilot-cli` 11.102.

### Las contradicciones, sin promediar

- **Codex #1 en descargas, #3 en adopción declarada.** 67,9M descargas npm/30d
  vs 16% de adopción [F1]. Las descargas npm están contaminadas por CI y
  auto-update; además Claude Code distribuye también por instalador nativo, con
  lo cual npm la **subcuenta**. Un ranking que use solo npm invierte el podio.
- **opencode #1 en estrellas (199k), #6 en adopción (7%).** Las estrellas miden
  atención, no uso.
- **Star counts que no cierran entre sí.** Un comparativo de agosto 2026 reporta
  opencode con 193.678 estrellas y Claude Code con 140.331 [F4]; la API el
  2026-08-19 devuelve 199.197 y 142.006. La diferencia (~5.500 estrellas en
  opencode) es crecimiento real en pocos días, no error — y es en sí mismo un
  dato sobre la velocidad del terreno.
- **Gemini CLI: muerta y viva a la vez.** El blog de Google dice que deja de
  servir el 2026-06-18 [F11]. El repo `google-gemini/gemini-cli` publicó
  `v0.57.0-preview.0` el **2026-08-19** y no tiene aviso de deprecación en el
  README. Las dos cosas son ciertas: se apagó para tiers de consumo (AI Pro,
  Ultra, Code Assist individual) y sigue para Code Assist Standard/Enterprise y
  claves de Gemini Agent Platform [F11]. Un mapa que anote «Gemini CLI: muerta»
  o «Gemini CLI: activa» está mal en los dos casos.
- **Hooks de Codex: opt-in o default.** Fuentes secundarias de junio/julio 2026
  dicen que el motor está en `Stage::UnderDevelopment` y requiere
  `[features].codex_hooks = true` [F15]. La doc oficial al 2026-08-19 dice que
  están **habilitados por defecto** y que `codex_hooks` es alias deprecado de
  `hooks` [F12]. Doy por buena la doc oficial y dejo la contradicción anotada
  como marcador temporal: el cambio ocurrió entre julio y agosto de 2026.
- **Los rankings editoriales no coinciden entre sí ni con las encuestas.** Uno
  pone Codex #1 por Terminal-Bench 2.1 (89,5%) y luego lo baja a #2 tras un
  refresh de fines de julio [F4]. Son rankings de capacidad del modelo, no de
  adopción del arnés. No los uso para ordenar.

---

## Tabla por arnés

Versión y fecha verificadas el 2026-08-19 por API. «Rel/sem» = releases por
semana en la ventana de las últimas 100 releases publicadas (o desde 2026-02-19
si hubo menos de 100 en 6 meses).

| Arnés | Versión | Fecha | Rel/sem (6m) | Hooks | ¿Puede DENEGAR? | Skills/comandos | Memoria / subagentes / contexto | Config |
|---|---|---|---:|---|---|---|---|---|
| **Claude Code** | v2.1.236 | 2026-08-19 [F21] | **5,9** (100 rel. desde 22-abr) | Sí — ~30 eventos [F6] | **Sí**, `permissionDecision:"deny"` o exit 2, en 14 eventos: PreToolUse, UserPromptSubmit, Stop, SubagentStop, TeammateIdle, TaskCreated, TaskCompleted, ConfigChange, PostToolBatch, PreCompact, Elicitation… [F6] | Skills + plugins + marketplace (feb-2026) [F9] | CLAUDE.md + MEMORY.md; subagentes anidados hasta prof. 3; auto-compact; sandbox con enmascarado de credenciales [F10] | `.claude/settings.json` (hooks anidados) + CLAUDE.md |
| **OpenAI Codex CLI** | rust-v0.148.0 / npm 0.148.0 | 2026-08-18 [F13] | **16,3** (100 rel. desde 7-jul) | Sí — 11 eventos: SessionStart/End, SubagentStart/Stop, PreToolUse, PermissionRequest, PostToolUse, Pre/PostCompact, UserPromptSubmit, Stop [F12] | **Sí**, `permissionDecision:"deny"` o exit 2 en PreToolUse. Cobertura: Bash, `apply_patch` (alias Edit/Write), herramientas MCP, function tools locales [F12] | Agent Plugins portables; Agent Skills desde dic-2025 [F17] | AGENTS.md; subagentes (hooks SubagentStart/Stop); compaction con hooks Pre/Post; sesiones nombradas y forkeables (0.146, 29-jul) [F13] | `~/.codex/hooks.json`, `.codex/hooks.json`, o tabla `[hooks]` en `config.toml` [F12] |
| **opencode** | v1.18.18 | 2026-08-13 [F22] | **5,6** (100 rel. desde 15-abr) | Sí — 25+ eventos de plugin TS, incl. `tool.execute.before/after`, `permission.asked/replied`, `session.*`, `file.edited` [F7] | **Sí, por dos vías**: (a) plugin que lanza excepción en `tool.execute.before`; (b) config de permisos `allow/ask/deny` por herramienta (`read`, `edit`, `bash`, `task`, `skill`, `webfetch`, `websearch`, `external_directory`, `doom_loop`), con override por agente [F8] | Agent Skills nativas; comandos; rules [F18] | AGENTS.md al init; agentes/subagentes con permisos propios; `session.compacted`; soporte ACP [F18] | `opencode.json` + plugins TS en `.opencode/plugins/` y `~/.config/opencode/plugins/` [F7] |
| **GitHub Copilot CLI** | v1.0.81-4 / npm 1.0.80 | 2026-08-19 [F23] | **8,0** (100 rel. desde 24-may) | Sí — carpetas con `README.md` + `hooks.json` [F24] | **No verificado.** La doc los describe como «workflow hooks»; no encontré contrato de denegación documentado. Marcar como desconocido, no como no. | Agent Skills en `.github/skills` **o `.claude/skills`**; custom agents `*.agent.md` [F24] | AGENTS.md + custom instructions; custom agents | `.github/` + `AGENTS.md` + `hooks.json` |
| **Cursor** | (IDE; el repo público no publica releases) | — | — | Sí — `.cursor/hooks.json`, incl. `beforeShellExecution` [F2] | **Sí** — respuesta `allow`/`deny`/`ask`; **falla abierto** por defecto (si el proceso del hook muere, la acción procede) salvo `failClosed: true`. Bug reportado: hoy solo se respeta `deny`; `allow` y `ask` se ignoran ante la allow-list [F2] | Agent Skills (cliente de lanzamiento de Agent Plugins 1.0) [F20] | AGENTS.md; reglas `.cursor/rules` | `.cursor/hooks.json` + `.cursor/rules` + AGENTS.md |
| **Antigravity CLI (`agy`)** | sucesor de Gemini CLI, GA 2026-05-19 | 2026-05-19 [F11] | — (no publica releases en GitHub) | Sí — `hooks.json` dentro del plugin [F25] | **Heredado de Gemini CLI**: `decision: "allow"` / `"deny"` (alias `block`) en BeforeTool, más un `"ask"` implementado sin documentar [F26] | Plugins namespaced: skills + subagentes + rules + MCP + hooks en un bundle; las skills se vuelven slash-commands [F25] | Subagentes; workflows asíncronos multi-agente; comparte harness con Antigravity 2.0 desktop [F11] | `~/.gemini/antigravity-cli/plugins/<n>/` con `hooks.json` [F25] |
| **Gemini CLI** (legacy, enterprise) | v0.57.0-preview.0 / npm 0.56.0 | 2026-08-19 [F27] | **7,1** (100 rel. desde 12-may) | Sí — `hooks/hooks.json` en la extensión; corren **sincrónicos** dentro del loop [F26] | **Sí** — `decision: "deny"` (alias `block`) en BeforeTool [F26] | Extensions: prompts + MCP + comandos + temas + hooks + subagentes + Agent Skills [F26] | AGENTS.md; subagentes; `/rewind` | `hooks/hooks.json` (NO en `gemini-extension.json`) |
| **Cline** | desktop-v0.0.14 | 2026-08-19 [F28] | **9,1** (100 rel. desde 3-jun) | Sí — desde v3.36; `~/Documents/Cline/Rules/Hooks/` o `.clinerules/hooks/` [F29] | **Sí** — JSON por stdin/stdout con campo `cancel` que bloquea; PreToolUse valida antes de ejecutar [F29] | `.clinerules/` + workflows | Memory Bank (archivos MD jerárquicos); hooks de ciclo de vida para memoria persistente [F29] | `.clinerules/` + `hooks/` |
| **goose (AAIF)** | v1.46.0 | 2026-08-12 [F30] | **1,6** (32 rel. en 6m) | Parcial — `ToolInspectionManager` con inspectores encadenados, no hooks de usuario tipo shell | **Sí, pero no por hook de usuario**: la cadena Security → Egress → Adversary → Permission → Repetition puede aprobar, denegar o pedir aprobación antes de cada tool call [F31] | Recipes; 70+ extensiones MCP | Extensiones MCP-native; modos de permiso; sandbox | config propia + MCP |
| **Zed** | v1.17.0-pre | 2026-08-19 [F32] | **5,5** (100 rel. desde 13-abr) | **No** — hay discussion/issue abiertos de extensibilidad del agente (custom commands, lifecycle hooks, skills) [F33] | **No** | Agent Skills desde 1.4.2 (reemplazan la Rules Library) [F34] | AGENTS.md de proyecto + global (primer editor con ambos, 1.4.2); subagentes vía tool `task` que heredan las skills del padre [F34] | settings de Zed + AGENTS.md + SKILL.md |
| **Amp (Sourcegraph)** | 0.0.1787169759-g8b6940 | 2026-08-19 (npm) [F41] | continuo (versionado por timestamp) | Sí — array `amp.hooks` en settings, par evento+acción [F35] | **No verificado** — la doc habla de «override determinístico»; no encontré contrato de deny explícito | Skills en `skills/<n>/SKILL.md` o `.agents/skills/<n>/SKILL.md` [F35] | AGENTS.md | settings de Amp + AGENTS.md |
| **OpenHands** | v1.14.0 | 2026-08-17 [F36] | **1,2** (34 rel. en 6m) | No documentado como hooks de usuario | — | — | — | — |
| **qwen-code** | v0.21.14 | 2026-08-19 [F37] | **24,1** (100 rel. desde 21-jul) | Fork de Gemini CLI; hereda su superficie | Presunto sí (heredado) — **no verificado directamente** | heredado | heredado | heredado |
| **Continue.dev** | v2.1.0-vscode | **2026-06-19** [F38] | 2,9 (26 rel. en 6m) | — | — | — | — | — |
| **Roo Code** | v3.54.0 | 2026-05-15 — **repo archivado** | 0 desde entonces | — | — | — | — | — |
| **Aider** | v0.86.0 | **2025-08-09** [F16] | **0** en 6 meses | No | No | No | AGENTS.md (lectura) | `.aider.conf.yml` |

**Los que pueden denegar, en una línea**: Claude Code (14 eventos), Codex
(PreToolUse sobre Bash + apply_patch + MCP), opencode (excepción en plugin +
permisos por herramienta y por agente), Cursor (falla abierto por defecto),
Gemini CLI / Antigravity (BeforeTool), Cline (campo `cancel`), goose (cadena de
inspectores, no hook de usuario). **No pueden**: Zed, Aider. **Sin verificar**:
Copilot CLI, Amp, qwen-code, OpenHands.

---

## Qué se volvió nativo en los últimos 6 meses

Ordenado por cuánto trabajo le quita a un SO externo.

**1. Hooks con denegación, en todos lados.** Hace un año era rasgo distintivo de
Claude Code. Hoy: Gemini CLI los anunció el 2026-01-28 en v0.26.0 [F26]; Cline en
v3.36 [F29]; Codex los tiene en 11 eventos y **habilitados por defecto** [F12];
Cursor los expone con `failClosed` [F2]. **Consecuencia directa para el SO**: la
primitiva «guarda por tool-call» dejó de ser un diferenciador y pasó a ser un
formato de traducción. El valor se corrió de *tener* la guarda a *escribirla una
vez y proyectarla a seis dialectos*.

**2. Skills portables como estándar de facto.** Anthropic publicó la spec Agent
Skills el 2025-12-18; en 48 horas Microsoft la cableó a VS Code y OpenAI a
ChatGPT y Codex CLI; para marzo 2026 eran 32 herramientas leyendo el mismo
`SKILL.md`, y ~40 productos en junio [F17]. Copilot CLI lee skills desde
`.github/skills` **o `.claude/skills`** [F24]. Zed las adoptó en 1.4.2 y jubiló
su Rules Library [F34].

**3. Empaquetado unificado — Agent Plugins 1.0, 2026-08-06.** Manifest
`plugin.json` + `skills/` + `mcp.json`, publicado por un TSC con gente de Amazon,
Cursor, Microsoft, OpenAI y Vercel; clientes de lanzamiento: ChatGPT, Codex,
Cursor, GitHub Copilot, Kiro y VS Code [F20]. **Con un hueco declarado**: v1.0.0
no define modelo de permisos, sandboxing, firmas ni secretos — todo listado como
trabajo futuro. Ese hueco es donde sigue viviendo el gobierno.

**4. Subagentes y gestión de contexto.** Claude Code: subagentes anidados hasta
profundidad 3, fork que hereda conversación y cache de prompt, mensajería entre
sesiones con `@`, tope de 200 subagentes por sesión [F10]. Codex: hooks
`SubagentStart`/`SubagentStop`, identidad de subagente en el input del hook,
sesiones nombradas / fijadas / forkeables (0.146, 2026-07-29) [F13]. Zed:
subagentes que heredan las skills del padre [F34]. Antigravity: workflows
asíncronos multi-agente [F11]. Auto-compaction es hoy tabla estándar.

**5. Gobierno de costo, nativo.** Claude Code: límites de gasto provistos por
gateway, fila de créditos en `/usage`, atribución de costo por agente, tope de
200 búsquedas web por sesión [F10]. Esto pisa directamente la familia «gobierno
de costo» del SO.

**6. Sandboxing y manejo de credenciales.** Claude Code: modo `mask` que
sustituye credenciales reales en egress, decodificación de JWT, re-firma AWS
SigV4, precedencia de deny con wildcards sobre archivos de entorno (2.1.236,
2026-08-19) [F10]. Codex: sandbox nativo en Windows con exec-server y proxy de
red (0.145, 2026-07-21) [F13]. opencode: los archivos de entorno están denegados
por defecto para `read` [F8].

**7. Memoria persistente.** Claude Code: MEMORY.md con timestamps ISO y avisos de
overflow de índice [F10]. Cline: Memory Bank vía hooks de ciclo de vida, sin
tool-calls dentro de la tarea [F29]. opencode y Codex: AGENTS.md generado en el
init.

**8. Reorganización institucional.** goose pasó de Block a la Agentic AI
Foundation (Linux Foundation) el 2026-04-07 [F19]; MCP y AGENTS.md también son
proyectos fundacionales de AAIF, con AWS, Anthropic, Block, Bloomberg,
Cloudflare, Google, Microsoft y OpenAI como platinum [F19]. opencode se mudó de
`sst/` a `anomalyco/`.

---

## Qué está claramente en camino

| Señal | Qué implica | Fuente |
|---|---|---|
| **MCP 2026-07-28, final** — protocolo **stateless**: se eliminan el handshake `initialize/initialized` y `Mcp-Session-Id`; RPC `server/discover` obligatorio; Roots, Sampling, Logging y HTTP+SSE deprecados; headers `Mcp-Method`/`Mcp-Name`; framework de Extensions (Tasks, MCP Apps); Enterprise-Managed Authorization estable | Cualquier integración MCP del SO tiene una migración obligatoria por delante. Lo bueno: `server/discover` + headers hacen que un gateway pueda gobernar sin parsear el body — se puede gobernar MCP desde afuera del arnés | [F39] |
| **Agent Plugins 1.0 declara faltantes: permisos, sandboxing, firmas, secretos** | Es un roadmap publicado de lo que el estándar **no** cubre. Es la ventana más clara de dónde un SO sigue aportando en 12 meses | [F20] |
| **Codex: hooks con MCP tool handlers (0.148.0, 2026-08-18) y hooks asíncronos** | Codex está construyendo activamente el plano de control. En 3–6 meses su superficie de hooks probablemente iguale a la de Claude Code | [F14] |
| **Codex 0.146+: sesiones nombradas, threads fijados, fork de conversación (2026-07-29)** | Gestión de sesión nativa; la coordinación entre sesiones concurrentes del SO se va a solapar | [F13] |
| **Claude Code: streaming de logs de agente y checkpointing del árbol de agentes, en beta** | Telemetría y recuperación nativas — dos familias del SO | [F40] |
| **Claude Code `self-hosted-runner` (2.1.224)** | Entornos de ejecución propios manejados por el arnés | [F10] |
| **Zed: issue y discussion abiertos de custom commands + lifecycle hooks + skills** | Zed va a tener hooks. Hoy no los tiene: es la ventana para no invertir ahí todavía | [F33] |
| **Antigravity 2.0: el CLI y el desktop comparten harness** | Google unifica; toda mejora del agente aparece en las dos superficies a la vez | [F11] |
| **AAIF endosó AGENTS.md como complemento de los Agent Cards de A2A** | AGENTS.md se consolida como piso, no como formato de un vendor | [F17] |

**Dónde NO invertir**, leído de lo anterior: guardas de tool-call específicas por
arnés (ya son nativas en 6 de 7); memoria de proyecto en markdown (nativa en
todos); descubrimiento de skills (Agent Plugins 1.0 lo resolvió); gestión de
sesión y compaction (nativas). **Dónde el hueco sigue abierto**: el modelo de
permisos que Agent Plugins 1.0 declara como no-cubierto, la traducción de una
política única a seis dialectos de hooks, y la coordinación entre sesiones
concurrentes de *distintos* arneses.

---

## Convergencia de estándares

**Converge, y fuerte, en tres capas de las cuatro.**

1. **Contexto de proyecto — `AGENTS.md`: convergido.** Adoptado por Codex,
   Cursor, GitHub Copilot, Gemini CLI, Aider, Windsurf y Zed; 60.000+ repos
   open-source a mediados de 2026 [F17]. Es proyecto fundacional de AAIF [F19].
2. **Capacidades — `SKILL.md` (Agent Skills): convergido.** De la spec de
   2025-12-18 a ~40 productos en junio 2026 [F17]. Copilot CLI lee incluso el
   directorio `.claude/skills` de la competencia [F24].
3. **Herramientas — MCP: convergido, con migración.** Bajo Linux Foundation /
   AAIF; la revisión 2026-07-28 es el cambio más grande desde 2024 [F39].
4. **Empaquetado — Agent Plugins 1.0: convergiendo desde 2026-08-06.** Manifest
   común, ubicaciones fijas, namespace para extensiones por cliente [F20].

**NO converge: los hooks.** No hay estándar de hooks. Los formatos vivos hoy:

| Arnés | Dónde | Forma |
|---|---|---|
| Claude Code | `.claude/settings.json` | objeto anidado con `matcher` |
| Codex | `.codex/hooks.json` o `[hooks]` en `config.toml` | JSON/TOML, matchers de tool |
| Copilot CLI | carpeta con `README.md` + `hooks.json` | carpeta |
| Antigravity | `hooks.json` dentro del plugin | JSON en bundle |
| Gemini CLI | `hooks/hooks.json` de la extensión (**no** en el manifest) | JSON |
| Cursor | `.cursor/hooks.json` | JSON, eventos propios (`beforeShellExecution`) |
| Cline | `.clinerules/hooks/` | ejecutables, JSON por stdin |
| opencode | plugin TypeScript | módulo TS con objeto de hooks |
| Amp | array `amp.hooks` en settings | par evento+acción |
| goose | inspectores internos | no es hook de usuario |

Y ni siquiera los nombres coinciden: `PreToolUse` (Claude, Codex, Cline) vs
`BeforeTool` (Gemini/Antigravity) vs `beforeShellExecution` (Cursor) vs
`tool.execute.before` (opencode). Tampoco la semántica de falla: Cursor **falla
abierto** salvo opt-in `failClosed` [F2]; Claude Code y Codex bloquean con exit 2.

**Veredicto para la apuesta multi-arnés.** Mejora con el tiempo en tres de las
cuatro capas: skills, contexto y herramientas se escriben una vez y corren en
todos lados, y eso abarata el SO. La cuarta —hooks y permisos, que es justamente
donde el SO pone su valor— sigue fragmentada, y Agent Plugins 1.0 la deja fuera
de alcance **explícitamente**. Un SO cuyo diferenciador sea «tengo guardas»
envejece mal; uno cuyo diferenciador sea «escribo la política una vez y la
proyecto a diez dialectos que nadie está unificando» tiene la ventana abierta al
menos hasta que un Agent Plugins 2.0 defina permisos. No hay señal pública de esa
2.0 hoy.

---

## Cada cuánto habría que re-verificar esto

Derivado de cadencias medidas, no de intuición.

| Qué | Cada cuánto | De dónde sale |
|---|---:|---|
| Superficie de hooks y permisos de los 4 top (Claude Code, Codex, opencode, Copilot CLI) | **30 días** | El motor de hooks de Codex cambió en 6 de 6 minors entre 2026-07-08 y 2026-08-18: uno cada ~10 días. Tres ciclos de cambio es el máximo tolerable antes de que el manifest describa otro producto. |
| Versión y cadencia de todos los arneses de la tabla | **45 días** | Sale del arnés más lento que sigue importando: goose a 1,6 rel/sem produce ~10 releases en 45 días. Debajo de eso el chequeo no encuentra nada nuevo y es gasto. |
| Ranking, adopción y estándares | **90 días** | JetBrains publica ~cuatrimestral (enero → mayo-julio [F1]); Agent Plugins 1.0 y MCP 2026-07-28 salieron con ~6 semanas de diferencia. |

**Y el piso que ningún intervalo cubre: 30 días de anuncio a apagado.** Google
anunció el 2026-05-19 y apagó el 2026-06-18 [F11]. Con re-verificación mensual,
un arnés puede morir entre dos chequeos. Mitigación barata, sin cambiar el
intervalo: un chequeo semanal automatizable de tres señales de bajo costo — repo
archivado (`archived: true`), redirect de nombre de repo (`Moved Permanently` sin
`-L`), y días desde la última release. Las tres se leen de la misma API que usa
este informe y las tres agarraron algo real hoy: Roo Code archivada, goose y
opencode mudados de organización, Aider parada hace 375 días.

**Lo que debería tener el manifest y hoy no tiene**, en orden de valor:

1. `verified_at` en ISO-8601 por driver — hoy hay `version_baseline`, que ancla
   pero no fecha de forma comparable.
2. `upstream_version_at_verification` — para que un script compare contra la API
   viva y calcule el atraso solo (hoy: `0.126.0-alpha.8` vs `0.148.0`).
3. `verification_command` — el `curl` que reproduce el chequeo.
4. `max_age_days` por driver, con los intervalos de la tabla de arriba, para que
   un gate falle cuando el mapa vence en vez de esperar a que cause un defecto.

---

## Fuentes

Todas consultadas el **2026-08-19**. Las marcadas **[2026]** son publicaciones de
este año. Cuando el dato es una versión o una fecha de release, la fuente es la
API que la devuelve, no una nota editorial.

1. **[2026]** JetBrains Research, «AI Coding Agents: Adoption Trends», agosto
   2026 — campo mayo–julio 2026, n>15.000 — https://blog.jetbrains.com/research/2026/08/ai-coding-agent-adoption-2026/
2. **[2026]** Cursor Docs, «Hooks» — https://cursor.com/docs/hooks · Elastic
   Security Labs, «AI coding agent audit: Cursor hooks» — https://www.elastic.co/security-labs/ai-coding-agent-audit-cursor-hooks · bug de `allow`/`ask` ignorados — https://forum.cursor.com/t/beforeshellexecution-hook-permissions-allow-ask-ignored-allow-list-takes-precedence/144244
3. **[2026]** Stack Overflow Developer Survey 2026 — **fuente primaria caída**:
   https://survey.stackoverflow.co/2026/ y https://survey.stackoverflow.co/2026/ai
   devuelven 404 al 2026-08-19. Cifras vía terceros (84% adopción, 29%
   confianza) — https://byteiota.com/stack-overflow-dev-survey-2026-ai-at-84-trust-at-3/ — **secundaria, sin verificar**
4. **[2026]** morphllm, «Best AI Coding Agent (2026)» — https://www.morphllm.com/ai-coding-agent (429 al re-fetch; datos vía resultados de búsqueda)
5. **[2026]** Cognition pliega Windsurf dentro de Devin Desktop — https://www.morphllm.com/ai-coding-agent
6. **[2026]** Claude Code, referencia de hooks (~30 eventos, 14 con capacidad de
   bloqueo) — https://code.claude.com/docs/en/hooks
7. **[2026]** opencode, «Plugins» — lista completa de eventos; última
   actualización de la página: 19-ago-2026 — https://opencode.ai/docs/plugins/
8. **[2026]** opencode, «Permissions» — allow/ask/deny por herramienta y por
   agente; última actualización: 19-ago-2026 — https://opencode.ai/docs/permissions/
9. **[2026]** Marketplace de plugins de Claude Code (feb-2026) — https://www.gradually.ai/en/changelogs/claude-code/
10. **[2026]** Claude Code CHANGELOG (versiones 2.1.210–2.1.236, jul–ago 2026) — https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
11. **[2026]** Google Developers Blog, «An important update: Transitioning Gemini
    CLI to Antigravity CLI», **publicado 2026-05-19**, apagado 2026-06-18 — https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/
12. **[2026]** Codex, doc oficial de Hooks — 11 eventos, `permissionDecision:
    "deny"`, on-by-default, cobertura Bash + apply_patch + MCP — https://learn.chatgpt.com/docs/hooks (redirect 308 desde https://developers.openai.com/codex/hooks)
13. **[2026]** openai/codex releases API — rust-v0.148.0 (2026-08-18),
    rust-v0.146.0 (2026-07-29), rust-v0.145.0 (2026-07-21) — https://api.github.com/repos/openai/codex/releases
14. **[2026]** Notas de rust-v0.148.0, 2026-08-18: «Hooks can now run commands
    asynchronously and invoke MCP tools» (#37533, #38705) — https://github.com/openai/codex/releases/tag/rust-v0.148.0
15. **[2026]** Fuente secundaria en contradicción con [F12] (hooks opt-in,
    `Stage::UnderDevelopment`, primer ship v0.114 en marzo 2026) — https://agenticcontrolplane.com/blog/codex-cli-hooks-reference
16. Aider releases API — v0.86.0, **2025-08-09**, sin releases posteriores — https://api.github.com/repos/Aider-AI/aider/releases
17. **[2026]** Spec Agent Skills (2025-12-18) y su difusión a ~40 productos;
    AGENTS.md en 60.000+ repos; endoso de AAIF — https://devtoollab.com/blog/agent-skills-open-standard-guide · https://ai.gopubby.com/the-agentic-ai-toolkit-mcp-vs-agent-skills-vs-agents-md-2b558f225b75 · https://zylos.ai/research/2026-03-26-agent-interoperability-protocols-mcp-a2a-acp-convergence/
18. **[2026]** opencode, índice de documentación (Agent Skills, Agents, MCP,
    Permissions, Policies, ACP, Custom Tools); última actualización:
    19-ago-2026 — https://opencode.ai/docs/
19. **[2026]** Linux Foundation, formación de la Agentic AI Foundation con MCP,
    goose y AGENTS.md — https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation · mudanza de goose, **2026-04-07** — https://goose-docs.ai/blog/2026/04/07/goose-moves-to-aaif/
20. **[2026]** Agent Plugins 1.0.0, **2026-08-06** — TSC de Amazon, Cursor,
    Microsoft, OpenAI, Vercel; sin modelo de permisos, sandbox, firmas ni
    secretos — https://github.com/agentplugins/agent-plugins-spec · https://aaif.io/blog/from-skills-and-tools-to-portable-agent-plugins
21. anthropics/claude-code releases API — v2.1.236, 2026-08-19 — https://api.github.com/repos/anthropics/claude-code/releases
22. anomalyco/opencode releases API — v1.18.18, 2026-08-13 — https://api.github.com/repos/sst/opencode/releases (redirige a anomalyco)
23. github/copilot-cli releases API — v1.0.81-4, 2026-08-19 — https://api.github.com/repos/github/copilot-cli/releases
24. **[2026]** GitHub Docs, agent skills y custom agents para Copilot CLI — https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills · https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli
25. **[2026]** Google Antigravity Docs, «Plugins & Skills» — https://antigravity.google/docs/cli/plugins
26. **[2026]** Gemini CLI hooks — anunciados 2026-01-28 en v0.26.0; `decision:
    allow|deny` (alias `block`), más `ask` no documentado — https://geminicli.com/docs/hooks/reference/ · https://developers.googleblog.com/tailor-gemini-cli-to-your-workflow-with-hooks/ · https://github.com/google-gemini/gemini-cli/issues/28046
27. google-gemini/gemini-cli releases API — v0.57.0-preview.0, 2026-08-19 — https://api.github.com/repos/google-gemini/gemini-cli/releases
28. cline/cline releases API — desktop-v0.0.14, 2026-08-19 — https://api.github.com/repos/cline/cline/releases
29. **[2026]** Cline v3.36 Hooks — https://cline.bot/blog/cline-v3-36-hooks ·
    Memory Bank vía hooks de ciclo de vida — https://hindsight.vectorize.io/blog/2026/06/09/cline-persistent-memory
30. aaif-goose/goose releases API — v1.46.0, 2026-08-12 — https://api.github.com/repos/block/goose/releases (redirige a aaif-goose)
31. **[2026]** goose, cadena de inspectores Security → Egress → Adversary →
    Permission → Repetition — https://wuu73.org/aiguide/infoblogs/coding_agents/goose.html
32. zed-industries/zed releases API — v1.17.0-pre, 2026-08-19 — https://api.github.com/repos/zed-industries/zed/releases
33. **[2026]** Zed, discussion e issue de extensibilidad del agente (custom
    commands, lifecycle hooks, skills) — https://github.com/zed-industries/zed/discussions/57943 · https://github.com/zed-industries/zed/issues/57890
34. **[2026]** Zed 1.4.2: Agent Skills reemplazan la Rules Library; AGENTS.md de
    proyecto + global — https://byteiota.com/zed-1-4-2-agent-skills-agents-md-mcp/ · https://zed.dev/docs/ai/skills
35. **[2026]** Amp manual — `amp.hooks`, skills en `skills/<n>/SKILL.md` — https://ampcode.com/manual
36. OpenHands/OpenHands releases API — v1.14.0, 2026-08-17 — https://api.github.com/repos/OpenHands/OpenHands/releases
37. QwenLM/qwen-code releases API — v0.21.14, 2026-08-19 — https://api.github.com/repos/QwenLM/qwen-code/releases
38. continuedev/continue releases API — v2.1.0-vscode, 2026-06-19 — https://api.github.com/repos/continuedev/continue/releases
39. **[2026]** MCP, revisión 2026-07-28 (stateless, `server/discover`,
    deprecación de Roots/Sampling/Logging/HTTP+SSE, Extensions, auth
    empresarial) — https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/ · https://aaif.io/blog/mcp-2026-07-28-whats-changing-and-how-to-migrate
40. **[2026]** Claude Code: streaming de logs de agente y checkpointing del árbol
    de agentes, en beta (CLI 2026.6) — https://www.mindstudio.ai/blog/code-with-claude-2026-new-agent-features
41. npm downloads API, ventana 2026-07-19 a 2026-08-18 — https://api.npmjs.org/downloads/point/2026-07-19:2026-08-18/@openai/codex (ídem para cada paquete de la tabla); versiones vía https://registry.npmjs.org/<paquete>
42. **[2026]** Moonshot Kimi Code CLI (TypeScript, MIT, con subagentes), junio
    2026 — https://www.marktechpost.com/2026/06/06/moonshot-ai-releases-kimi-code-cli-a-terminal-ai-coding-agent-built-in-typescript-for-next-gen-agents/
