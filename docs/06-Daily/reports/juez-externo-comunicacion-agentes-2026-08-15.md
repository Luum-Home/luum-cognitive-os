# Juez externo — comunicación entre agentes en harnesses de coding, agosto 2026

- **Fecha:** 2026-08-15
- **Rol:** juez externo. No leí el código de este repo. Todo lo que sigue sale de material publicado.
- **Alcance:** dos ejes separados (subagente ↔ principal, y sesión ↔ sesión), por harness.
- **No recomiendo adoptar nada.** El freeze de adopción externa sigue vigente; describir el estado del arte no es proponer traerlo.

---

## 1. La respuesta directa

**¿Quién lo implementa?**

| Harness | Eje 1 (subagente ↔ principal) | Eje 2 (sesión ↔ sesión) |
|---|---|---|
| **Claude Code** | Sí, con contrato | **Sí, con contrato** |
| **Codex CLI** | Sí, mecanismo real — contrato casi ausente | **No existe** |
| **opencode** | Sí, sólo ida (spawn → resultado) | **No nativo.** Hay API HTTP de servidor y plugins de terceros |
| Cursor / Cline / Windsurf / Aider / Zed / Antigravity | No verificado en fuente oficial | No verificado en fuente oficial |

**¿Hay contrato o sólo plomería?**

Hay **un solo harness con contrato publicado: Claude Code.** Es el único que escribe qué pasa
cuando el mensaje no se entrega, quién puede vetarlo, qué ve el que recibe, qué pasa si el
destinatario está muerto o en otro modo de permisos, y cuántos mensajes se aguantan antes de
tirar los viejos. Codex tiene **plomería fuerte y contrato nulo**: las herramientas existen y
funcionan en el código, pero lo publicado las nombra sin garantizar nada. opencode tiene
**plomería genérica**: un API de sesiones que sirve para inyectar mensajes desde afuera, sin
concepto de agente que le hable a otro agente.

**Lo que decide el encargo.** La sospecha del operador —"construyeron un estándar propio sobre
algo que los harnesses ya resuelven"— **es correcta si la capa apunta sólo a Claude Code, y es
falsa si apunta a varios harnesses**. Sobre Claude Code solo, hay contrato escrito y una capa
encima duplica trabajo hecho. Cruzando harnesses no existe nada: ni estándar, ni contrato, ni
implementación de referencia mantenida. Lo único que hay ahí son bridges comunitarios sobre MCP
y wrappers de A2A, todos de una persona y sin tracción (§6). Cuál de los dos casos aplica lo
mide el juez interno; yo dejo la bifurcación planteada con la evidencia de cada rama.

---

## 2. Método, y los tres estados de evidencia

Cada afirmación de abajo lleva uno de estos tres sellos:

- **[DOC]** — documentado oficialmente. Fuente: sitio de doc del propio fabricante.
- **[CÓDIGO]** — existe en el código publicado del fabricante, sin doc que lo respalde.
- **[BLOG]** — lo dice un tercero y no lo confirmé. **No cuenta como evidencia**, se cita para
  marcar de dónde venía una creencia.

Los **mirrors están marcados como mirrors**. La doc de Codex vive hoy en `learn.chatgpt.com`:
`developers.openai.com/codex/*` responde **308** hacia allá, así que la URL vieja es un alias,
no una fuente distinta (verificado, §10).

Un detalle que vale marcar: la primera página de resultados sobre "cross-session messaging"
son cinco o seis posts con el mismo contenido reordenado (`digitalapplied`, `claudehub.fr`,
`explainx.ai`, `kylon.io`, `dev.classmethod.jp`). Coinciden entre sí porque están todos
parafraseando el mismo changelog, no porque se hayan verificado. **Ninguno de ellos entra como
fuente en este informe.** El changelog que copian, sí.

---

## 3. Eje 1 — subagente ↔ agente principal

### Claude Code

| Dimensión | Estado |
|---|---|
| Devolución de resultado | El subagente trabaja aislado y devuelve resultado al principal **[DOC]** |
| Mensaje al subagente corriendo | **Sí.** `SendMessage` con el ID o el nombre del agente en el campo `to` **[DOC]** |
| Cómo lo interpreta el subagente | Desde v2.1.198, trata el mensaje del que lo lanzó como dirección de tarea normal, incluidas correcciones a mitad de camino **[DOC]** |
| Reanudación | Un subagente **completado** que recibe `SendMessage` se auto-reanuda en background sin nueva invocación de `Agent` **[DOC]** |
| Interrupción | Se puede frenar con `x` en `/tasks` o `stop_task` del SDK; desde v2.1.191 uno frenado a mano **no** se auto-reanuda **[DOC]** |
| Contexto preservado | Subagente normal arranca limpio (system prompt, tarea, CLAUDE.md, git status, skills, roster de hermanos). Un `subagent_type: "fork"` hereda la conversación entera y el prompt cache — **por defecto desde v2.1.232** **[DOC]** |
| Lo que **no** cruza | Output style, auto memory, tamaño de ventana de contexto **[DOC]** |

**El límite duro, y es lo que lo convierte en contrato:** *"no message from any agent counts as
your approval for a pending permission prompt, and no agent message can change a subagent's
permission settings, `CLAUDE.md`, or configuration"* **[DOC]**.

**Agent teams** (experimental, detrás de `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) es un
sistema aparte y más fuerte: los teammates se mensajean **entre sí**, no sólo con el lead.
Ahí sí hay **mensajes de protocolo estructurados** —`shutdown_request`,
`plan_approval_response`— y un mailbox en `~/.claude/teams/{team}/inboxes/{agent}.json`.
La garantía está escrita: *"Claude Code reports a message as sent only when the write to the
recipient's mailbox file succeeds"*, y si falla la escritura *"the sending agent receives an
error and nothing is sent"* **[DOC]**. Las entradas malformadas se validan, se reportan y se
eliminan, y las válidas igual se entregan.

Fuentes: `https://code.claude.com/docs/en/sub-agents`, `https://code.claude.com/docs/en/agent-teams`.

**Observación del harness corriendo** (no es doc, es el artefacto): esta misma sesión, que es un
subagente de background, tiene `SendMessage` en su lista de herramientas diferidas y **no** tiene
`ListAgents`. Coincide exactamente con lo que dice la doc: *"a foreground subagent inherits it
[`ListAgents`] in sessions where cross-session messaging is enabled, and a background subagent
doesn't keep it"*. La doc y el binario dicen lo mismo en el punto donde pude cruzarlos.

### Codex CLI

Acá el encargo se queda corto y hay que corregirlo (§9).

| Dimensión | Estado |
|---|---|
| Hooks de ciclo de vida | `SubagentStart` y `SubagentStop` existen, junto con `SessionStart`, `SessionEnd`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `Stop` **[DOC]** |
| Inyección vía hook | `SubagentStart` acepta `additionalContext`, que *"is added as extra developer context for the subagent"*. `continue: false` **no** frena el arranque del subagente **[DOC]** |
| Continuación vía hook | `SubagentStop` puede devolver `{"decision": "block", "reason": "..."}` para pedir otra pasada **[DOC]** |
| Canal de vuelta del modelo | **Sí, y no lo trae el hook.** `features.multi_agent` habilita `spawn_agent`, `send_input`, `resume_agent`, `wait_agent` y `close_agent` **[DOC]** |
| Superficie v2 | `multi_agents_v2` expone handlers `SpawnAgent`, `SendMessage`, `ListAgents`, `FollowupTask`, `InterruptAgent`, `WaitAgent`. La tool se registra como `ToolName::plain("send_message")`, con `MessageDeliveryMode::QueueOnly` **[CÓDIGO]** |
| Sustrato interno | `InterAgentCommunication`, con `AgentCommunicationKind` = `Spawn` / `Message` / `Followup` / `Result`, y telemetría `sender_thread_id → receiver_thread_id` **[CÓDIGO]** |
| Lo que dice la doc de subagentes | *"When many agents are running, Codex waits until all requested results are available, then returns a consolidated response"*. La página **no menciona ninguna de esas herramientas** **[DOC]** |

Es decir: **la doc de subagentes de Codex describe un modelo de fan-out y join sin canal de
vuelta, mientras el código publicado tiene el canal de vuelta completo, feature-flagged.** La
única mención oficial vive en la referencia de configuración, y es una lista de nombres sin
una sola garantía asociada.

**Estado real de la feature.** El issue [#12462](https://github.com/openai/codex/issues/12462)
("Inter-Agent Communication Channels for Direct Agent-to-Agent Messaging", abierto 2026-02-21)
está **cerrado**, y lo cerró un mantenedor de OpenAI con: *"This feature request hasn't received
enough upvotes, so I'm closing it. (Actually, a variant of this feature is under development and
will likely be released soon.)"*. El PR [#15556](https://github.com/openai/codex/pull/15556)
("feat: new op type for sub-agents communication") se mergeó el **2026-03-23**, y el
[#33550](https://github.com/openai/codex/pull/33550) ("Unify multi-agent settings under
`agents`") el **2026-07-16**.

Y no está terminado: el issue [#27331](https://github.com/openai/codex/issues/27331) sigue
**abierto** desde 2026-06-10 — con `features.multi_agent_v2.enabled = true`, **cada** turno
falla con HTTP 400 *"Function 'functions.spawn_agent' declares encrypted parameters but is not
configured for encrypted tool use by this model"* en cuentas ChatGPT. Un issue abierto de 2026
sobre exactamente esto vale más que el catálogo de features, y lo que dice es que la superficie
existe pero no está entregada.

Fuentes: `https://learn.chatgpt.com/docs/hooks`,
`https://learn.chatgpt.com/docs/agent-configuration/subagents`,
`https://learn.chatgpt.com/docs/config-file/config-reference`, y
`codex-rs/core/src/tools/handlers/multi_agents_v2*` + `codex-rs/core/src/agent_communication.rs`
en `github.com/openai/codex`.

### opencode

| Dimensión | Estado |
|---|---|
| Modelo | Agentes primarios + subagentes. Built-in: `general`, `explore`, `scout` **[DOC]** |
| Invocación | Tool `task`, o `@mention` manual. Permisos vía `permission.task` **[DOC]** |
| Sesiones hijas | El subagente corre en una **sesión hija fresca**, navegable con `session_child_first`, `session_child_cycle`, `session_parent` **[DOC]** |
| Mensaje al subagente corriendo | **No documentado.** La página no describe cómo vuelve el resultado ni si el padre puede mensajear **[DOC — por ausencia]** |
| Contexto compartido | No especificado en la doc **[DOC — por ausencia]** |

El hueco es lo bastante conocido como para tener plugin: `opencode-session-context` existe
justamente porque *"the subagent runs in a fresh child session with no access to the parent's
conversation history"*. Sobre la salud de ese plugin, ver §5.

Fuente: `https://opencode.ai/docs/agents/`.

---

## 4. Eje 2 — sesión ↔ sesión

### Claude Code — el único con contrato

Esto es lo que el artículo del operador anuncia, y la doc oficial es muchísimo más específica
que el anuncio. Página: `https://code.claude.com/docs/en/cross-session-messaging`.

**Mecanismo**

- Dos tools: `ListAgents` para descubrir, `SendMessage` para entregar. El usuario **nunca las
  llama a mano**; las llama Claude.
- Comando `/list-agents` (alias `/peers`) para verlas uno mismo. `/status` muestra la fila
  `Peer address`.
- Direccionamiento **por nombre** (`/rename`, flag `--name`, o derivado del directorio, tipo
  `my-app-3f`). Si dos sesiones vivas comparten nombre, Claude agrega un identificador corto y
  direcciona con él. Desde v2.1.232 se puede mencionar con `@nombre` desde el prompt.
- Transporte, y esto es explícito:

  | Dónde corre la otra sesión | Cómo viaja |
  |---|---|
  | En esta máquina | Socket por sesión, **nunca** por servidores de Anthropic |
  | En otra máquina tuya | Por servidores de Anthropic, llegando por Remote Control |
  | En Claude Code on the web | Por servidores de Anthropic, directo a la sesión cloud |

- Socket UDS por sesión, **restringido al usuario del SO**, exportado a hooks y Bash como
  `CLAUDE_CODE_MESSAGING_SOCKET`, con token por sesión en `CLAUDE_CODE_MESSAGING_TOKEN` y frame
  de auth `{"type":"auth","token":"<token>"}`.

**Contrato** — esto es lo que ningún otro harness escribe:

- **Tres resultados posibles, nombrados:** `Delivered` / `Held` / `Refused`. Y el desmentido
  explícito de la garantía fácil: *"Delivery isn't guaranteed in every configuration"*.
- **Control del receptor:** `crossSessionInbound` ∈ `accept` / `hold` / `refuse`, con reglas de
  precedencia entre scopes y fila propia en `/config`.
- **Default sin config:** se decide por la clase de modo de permisos de las dos sesiones. Si el
  receptor pide permisos, entrega —salvo que el emisor se declare bypass. Si el receptor
  bypassea, retiene todo salvo que el emisor también bypassee.
- **Vencimiento:** el diálogo de aprobación expira por `dialogExpiry`, **5 minutos** por
  defecto, y el mensaje se descarta. `"never"` lo mantiene hasta que termine la sesión.
- **Backpressure numerado:** hasta **100 mensajes retenidos** por sesión, y pasado eso se tira
  el más viejo; hasta **50 mensajes aceptados** esperando ser leídos.
- **Anti-loop:** rate-limit por emisor, y descarte de repeticiones idénticas dentro de una
  ventana corta, *"so a message loop between two sessions therefore stops on its own"*.
- **Feedback al emisor:** en la misma máquina, el emisor recibe aviso de retención y luego el
  desenlace (entregado / denegado / expirado). Un mensaje rechazado al llegar **no** genera
  aviso — y eso también está escrito.
- **Destinatario muerto:** `ListAgents` marca `offline` las sesiones de Remote Control caídas
  y `cloud` las de la web. Si la sesión termina con mensajes retenidos, se reportan como
  expirados a cada emisor alcanzable.
- **Qué ve el que recibe:** *"A message is a piece of text one Claude writes to another, never
  conversation history or files"*. Llega bajo el nombre del emisor, con dirección de respuesta
  —salvo el caso cross-machine de una vía, que no la lleva.
- **Qué el mensaje NO puede hacer:** no aprueba nada, no cambia configuración ni `CLAUDE.md`, y
  **un comando en el texto llega como texto plano y no se ejecuta** (`/compact` incluido). Los
  prompts de permisos del receptor siguen disparando igual.
- **En auto mode**, el clasificador de permisos evalúa cada mensaje **antes** del despacho
  (desde v2.1.207) y trata un reclamo de aprobación relayado como input no confiable.
- **Apagado:** `crossSessionInbound: "refuse"` corta la entrada; deny rules sobre `SendMessage`
  y `ListAgents` cortan la salida; `isolatePeerMachines: true` exige aprobación para todo lo que
  salga de la máquina, y **un `true` de cualquier scope gana** (un archivo de proyecto puede
  encenderlo pero no apagarlo). Los admins pueden cerrar las dos puntas por managed settings.
- **Límite honesto:** *"Plain text only"* — los mensajes de protocolo estructurados se quedan
  dentro del team.

**Disponibilidad, verificada:** requiere v2.1.224+, corre en **macOS y Linux** (WSL 2 cuenta),
**no** hay soporte en Windows nativo, y **no** está en Amazon Bedrock, Claude Platform on AWS,
Google Cloud Agent Platform ni Microsoft Foundry. Si `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`,
`DISABLE_TELEMETRY`, `DO_NOT_TRACK` o `DISABLE_GROWTHBOOK` apagan la evaluación de feature flags,
la mensajería **queda apagada**. Vale la pena marcarlo: una política de privacidad razonable
apaga esta feature sin avisar.

**El hueco del contrato.** Después de leer la página entera buscando `order|ordering|sequence|
fifo|at-least-once|exactly-once|guarantee`, **el único hit es la frase que niega la garantía de
entrega**. No hay **ninguna afirmación sobre orden de mensajes** en ningún harness, Claude Code
incluido. Si algo depende de que dos mensajes lleguen en el orden en que se mandaron, eso no está
prometido por nadie.

### Codex CLI — no existe

No hay mecanismo para que dos sesiones de Codex se mensajeen **[DOC]**. `InterAgentCommunication`
es intra-sesión: enruta entre *threads* de agente dentro de una sesión, no entre sesiones. La
demanda está documentada y sin resolver: la discusión
[#14067](https://github.com/openai/codex/discussions/14067) pide sincronizar threads entre
máquinas, y el issue [#23713](https://github.com/openai/codex/issues/23713) pide poder enganchar
una sesión top-level como subagente de un thread orquestador.

### opencode — no nativo, pero hay plomería

- **No hay mecanismo nativo agente-a-agente entre sesiones** **[DOC — por ausencia]**.
- **Sí hay un API de servidor**: `POST /session` (con `parentID` opcional),
  `POST /session/:id/message` ("send a message and wait for response"),
  `POST /session/:id/prompt_async` ("send a message asynchronously (no wait)"), y `GET /event`
  como stream SSE **[DOC]**. Eso es **plano de control**, no plano de agente: sirve para que un
  proceso externo inyecte texto en una sesión, y no define descubrimiento, ni permisos de
  entrada, ni qué pasa si el destinatario murió, ni qué ve el receptor.

Fuente: `https://opencode.ai/docs/server/`.

---

## 5. La distinción que decide: mecanismo vs contrato

| Harness | Eje | Mecanismo | Contrato | Qué garantiza |
|---|---|---|---|---|
| Claude Code | 1 | `SendMessage` a subagente por ID/nombre; auto-reanudación **[DOC]** | **Sí** | Un mensaje nunca es consentimiento; no puede tocar permisos/`CLAUDE.md`/config |
| Claude Code | 1 (teams) | Mailbox JSON en disco, mensajes de protocolo **[DOC]** | **Sí** | "Sent" sólo si la escritura al mailbox tuvo éxito; si falla, error y nada se manda |
| Claude Code | 2 | `ListAgents` + `SendMessage`, socket UDS / Remote Control **[DOC]** | **Sí** | Delivered/Held/Refused, expiry 5 min, tope 100 retenidos + 50 en cola, dedup, feedback al emisor, `offline`, sólo texto plano, comandos no se ejecutan |
| Codex CLI | 1 | `spawn_agent`/`send_input`/`resume_agent`/`wait_agent`/`close_agent` **[DOC]**; `send_message`/`list_agents`/`interrupt_agent` **[CÓDIGO]** | **No** | Nada publicado. Nombres de tools sin garantías, feature flag con bug abierto |
| Codex CLI | 2 | — | — | No existe |
| opencode | 1 | Tool `task`, sesión hija **[DOC]** | **No** | Ni siquiera está documentado cómo vuelve el resultado |
| opencode | 2 | API HTTP de sesiones **[DOC]** | **No** | Plano de control externo, sin semántica de agente |

**Sobre los plugins de opencode, y esto importa para no confundir cantidad con evidencia:**
`gotgenes/opencode-session-context` tiene **0 estrellas** (último push 2026-04-24) y
`malhashemi/opencode-sessions` tiene **168 estrellas** pero **no se toca desde 2025-10-30** —
casi diez meses. Verificado por API (§10). El hueco de opencode no está tapado por un ecosistema:
está tapado por dos repos de una persona cada uno, uno sin uso y otro sin mantenimiento.

---

## 6. MCP y A2A como sustrato

La pregunta era si alguien usa MCP para comunicación agente-a-agente en vez de un mecanismo
propio del harness, porque eso sería el estándar de facto y cambiaría la respuesta. **No lo es.**

**Lo que MCP sí hace en Claude Code:** los **channels** (research preview) son servidores MCP que
**empujan eventos externos** a una sesión corriendo — Telegram, Discord, iMessage, webhooks de CI
**[DOC]**. Tienen su propio contrato: allowlist de emisores por canal, pairing con código,
`channelsEnabled` y `allowedChannelPlugins` en managed settings, y estar en `.mcp.json` **no
alcanza** —hay que nombrarlo en `--channels`. Pero es **sistema externo → agente**, no agente ↔
agente, y la doc lo dice sin vueltas: *"the `--channels` flag syntax and protocol contract may
change"*.

**A2A** es el estándar real de agente-a-agente: v1.0 en abril 2026, alojado junto a MCP en la
Agentic AI Foundation de la Linux Foundation desde diciembre 2025, con Agent Cards para
descubrimiento y un ciclo de vida de tareas (`submitted`/`working`/`input-required`/`completed`/
`canceled`/`failed`) **[BLOG — no verificado contra `a2a-protocol.org`]**.

**Y ningún harness de coding lo implementa.** Ni Claude Code, ni Codex, ni opencode. Lo que
existe son wrappers de terceros: `claude-a2a` (dos repos distintos con el mismo nombre),
`synapse-a2a`, skills de A2A. Todos community, ninguno del fabricante.

**El caso más interesante, y está verificado:** el 2026-03-20, **24 horas después** de que
Anthropic sacara Channels, alguien construyó un bridge que enchufa notificaciones MCP al Codex
App Server (JSON-RPC) para lograr comunicación bidireccional entre Claude Code y Codex *en una
sola sesión viva*. Quedó como discusión [#15374](https://github.com/openai/codex/discussions/15374)
en el repo de Codex, y como issue [#36871](https://github.com/anthropics/claude-code/issues/36871)
en el de Claude Code — **cerrado**. Su planteo del problema es la mejor formulación del hueco que
encontré: *"there is currently no way for Claude Code to receive live external events or messages
from other agent engines... inside the same active session"*.

**Conclusión del eje MCP:** MCP es el sustrato que la gente **usa** para cruzar harnesses, porque
es lo único que hablan todos. Pero no es un estándar de comunicación entre agentes: es un
protocolo agente-a-herramienta que se está usando de caño. El estándar que sí existe para esto
—A2A— no lo adoptó ningún harness de coding.

---

## 7. Qué dice el artículo que la doc no confirma

**Advertencia de método:** del artículo de Medium sólo pude leer título, subtítulo y la primera
línea. El cuerpo no fue accesible. **No puedo evaluar lo que afirma en el cuerpo**, y no voy a
inferirlo de los posts que lo parafrasean. Lo que sigue aplica sólo a lo que sí pude leer.

Lo legible eran dos afirmaciones, y **las dos las confirma el changelog oficial**:

| Afirmación del artículo | Doc oficial |
|---|---|
| Las tools se llaman `ListAgents` y `SendMessage` | Confirmado, v2.1.224 |
| Shipeó en Claude Code v2.1.224 | Confirmado: *"Added cross-session `SendMessage`... with `ListAgents` to discover them (macOS and Linux)"*, 2026-08-07 |

**Lo que el artículo no dice, y la doc sí** — y es la diferencia entre "existe la feature" y
"existe el contrato": los tres desenlaces con nombre, `crossSessionInbound`, el default por clase
de modo de permisos, el expiry de 5 minutos, los topes de 100 y 50, el dedup anti-loop, el
`isolatePeerMachines`, la tabla de por dónde viaja cada mensaje, y que la feature **se apaga sola**
si desactivás la evaluación de feature flags por privacidad. Un post cuenta qué se puede hacer;
esto es lo que hay que leer antes de apoyar algo encima.

**Y el hallazgo que el operador va a querer:** el artículo ya está desactualizado en el punto
más visible. Se publicó sobre v2.1.224 (2026-08-07). Para v2.1.232 (2026-08-13, **seis días
después**) el direccionamiento cambió: apareció el `@mention` desde el prompt, `SendMessage`
pasó a entregar contra un nombre pelado que matchee una sola sesión viva —antes pedía confirmar
con un ref—, y se agregó la fila de `/config` para el control inbound. Entre medio, v2.1.225
agregó poder **iniciar** conversación con sesiones de otras máquinas (antes sólo se podía
responder), y v2.1.228 endureció el directorio de sockets en `/tmp` compartido contra symlinks
plantados. **Cinco releases tocaron esta feature en los ocho días posteriores al artículo.** Es
una superficie en movimiento, y cualquier cosa apoyada encima hoy apunta a un blanco móvil.

---

## 8. Lo que no pude verificar

1. **El cuerpo del artículo de Medium.** Sólo título, subtítulo y lede. Todo lo del artículo que
   no esté en §7 queda sin evaluar.
2. **Orden de mensajes, en ningún harness.** Buscado explícitamente en la doc de Claude Code; el
   único match es la frase que niega la garantía de entrega. Nadie promete orden.
3. **Cursor, Cline, Windsurf, Aider, Zed, Antigravity.** No abrí doc oficial de ninguno. Lo que
   apareció en búsqueda —"Cline tiene subagentes nativos desde v3.58", "Antigravity CLI reemplaza
   a Gemini CLI el 2026-05-19"— es **[BLOG]** y **no lo afirmo**. Si el operador necesita esa fila
   de la tabla, es otro encargo con doc oficial en la mano.
4. **Si `multi_agent_v2` de Codex funciona hoy.** El código está; el issue #27331 dice que
   prenderlo rompe todos los turnos en cuentas ChatGPT, y sigue abierto. No lo ejecuté.
5. **A2A contra su fuente primaria.** Las cifras (v1.0 en abril 2026, 150+ organizaciones, AAIF
   en diciembre 2025) salen de búsqueda, no de `a2a-protocol.org`. Marcadas **[BLOG]**.
6. **Números de code-search de GitHub.** Los totales (49 archivos con `InterAgentCommunication`,
   33 con `MultiAgentV2`) son de la API de búsqueda, que es aproximada y varía. Los archivos
   individuales sí los leí y ésos son firmes.

---

## 9. Correcciones a las premisas del encargo

**1. "Codex tiene `SubagentStart`/`SubagentStop`... ¿hay canal de vuelta, o sólo lifecycle?" —
la premisa mide con el instrumento equivocado.** Los hooks están bien verificados, pero **no son
donde vive la respuesta**. Codex tiene canal de vuelta: `send_input` está en la referencia de
configuración oficial, y `send_message` / `list_agents` / `interrupt_agent` están en el código
publicado bajo `features.multi_agent_v2`. Un juez que se hubiera quedado en la página de hooks
habría contestado "sólo lifecycle", y habría estado equivocado. La respuesta correcta es: **hay
canal de vuelta, no lo trae el hook, y no está documentado donde uno lo buscaría.**

**2. "El operador sabe que Claude Code sí" — verificado, y el alcance es bastante más ancho que
el artículo.** No es una feature, son **tres sistemas distintos**: subagentes con `SendMessage` y
auto-reanudación (eje 1), agent teams con mailbox y mensajes de protocolo estructurados (eje 1,
experimental), y cross-session messaging con `ListAgents` (eje 2). Más channels, que es MCP y es
otra cosa. El artículo cubre **una** de las tres. Si la capa propia se dimensionó contra el
artículo, se dimensionó contra un tercio del harness.

**3. "Una capa por encima queriendo formar un estándar... sobrecomplejizando algo que los
harnesses ya resuelven" — parcialmente falsa, y la parte falsa importa.** "Los harnesses" no
resuelven esto: **uno** lo resuelve. Codex no tiene eje 2 en absoluto y su eje 1 está a mitad de
camino con un bug abierto; opencode no tiene ninguno de los dos de forma nativa. La frase es
verdadera contra Claude Code y falsa contra el resto. Si la capa es harness-agnóstica, no está
sobrecomplejizando algo resuelto: está en el hueco que dejaron. **Cuál de los dos casos es, lo
mide el juez interno** — yo no vi el proyecto.

**4. "Si los harnesses tienen mecanismo pero ninguno tiene contrato, la capa puede no ser
reinvención sino la respuesta a un hueco real."** El antecedente **no se cumple**: Claude Code
tiene contrato, y es de los más detallados que vi en documentación de producto. Así que esa rama
del razonamiento del encargo se cierra. Queda abierta la otra, la del §9.3.

**5. Lo que el encargo no anticipó: el contrato tiene fecha de vencimiento corta.** Cinco
releases tocaron cross-session messaging en ocho días (2.1.224 → 2.1.232), incluyendo un cambio
de semántica de direccionamiento. "Claude Code lo resuelve" es verdad hoy; el contrato al que
uno se ate hoy no es el de dentro de dos semanas.

---

## 10. Evidencia ejecutable

Todo número y toda cita estructural de arriba sale de estos comandos. Read-only, sin estado de
sesión. Requieren `gh` autenticado y salida a internet.

```bash
# §2 — la doc de Codex se mudó: developers.openai.com es alias (308), no fuente aparte
curl -sI https://developers.openai.com/codex/hooks | grep -iE '^(HTTP|location)'
curl -sI https://developers.openai.com/codex/subagents | grep -iE '^(HTTP|location)'

# §4 — no hay garantía de orden en Claude Code; el único hit niega la de entrega
curl -s https://code.claude.com/docs/en/cross-session-messaging.md \
  | grep -inE 'order|ordering|sequence|fifo|at-least-once|exactly-once|guarantee'

# §3 — Codex: la superficie multi-agente existe en el código publicado
gh api repos/openai/codex/contents/codex-rs/core/src/tools/handlers/multi_agents_v2.rs \
  -q '.content' | base64 -d | grep -E 'pub\(crate\) use|^//!'
gh api repos/openai/codex/contents/codex-rs/core/src/tools/handlers/multi_agents_v2/send_message.rs \
  -q '.content' | base64 -d | grep -E 'ToolName::plain|MessageDeliveryMode'
gh api repos/openai/codex/contents/codex-rs/core/src/agent_communication.rs \
  -q '.content' | base64 -d | grep -A6 'enum AgentCommunicationKind'

# §3 — y está detrás de un feature flag, con su clave de config
gh api repos/openai/codex/contents/codex-rs/core/config.schema.json \
  -q '.content' | base64 -d | grep -n 'multi_agent_v2'

# §3 — estado real: feature request cerrada, PRs mergeados, bug abierto
gh issue view 12462 --repo openai/codex --json number,title,state,createdAt
gh pr    view 15556 --repo openai/codex --json number,title,state,mergedAt
gh pr    view 33550 --repo openai/codex --json number,title,state,mergedAt
gh issue view 27331 --repo openai/codex --json number,title,state,createdAt

# §6 — el bridge cross-harness sobre MCP, las dos puntas
gh issue view 36871 --repo anthropics/claude-code --json number,title,state,createdAt
gh api graphql -f query='{repository(owner:"openai",name:"codex"){discussion(number:15374){title createdAt}}}'

# §5 — salud real de los plugins de opencode (estrellas y último push)
for r in gotgenes/opencode-session-context malhashemi/opencode-sessions; do
  gh api repos/$r -q '.full_name+" stars="+(.stargazers_count|tostring)+" pushed="+.pushed_at'
done
```

### Fuentes primarias

**Claude Code** (doc oficial, `code.claude.com/docs/en/`): `cross-session-messaging`,
`sub-agents`, `agent-teams`, `channels`, `changelog`. Nota: `docs.claude.com/en/docs/claude-code/*`
responde 301 hacia `code.claude.com/docs/en/*` — mismo origen, no fuente independiente.

**Codex CLI** (doc oficial, `learn.chatgpt.com/docs/`): `hooks`,
`agent-configuration/subagents`, `config-file/config-reference`. Código: `github.com/openai/codex`,
`codex-rs/core/src/agent_communication.rs` y `codex-rs/core/src/tools/handlers/multi_agents_v2/`.

**opencode** (doc oficial, `opencode.ai/docs/`): `agents/`, `server/`. Repo: `anomalyco/opencode`.

**Punto de partida del operador** (mirror de experiencia, no de contrato, y de lectura parcial):
el artículo de Medium sobre v2.1.224.
