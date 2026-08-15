# Comunicación entre sesiones de harnesses distintos — Claude Code ↔ Codex ↔ opencode

- **Fecha:** 2026-08-15
- **Encargo:** investigación previa a construir. ¿Existe alguien que conecte sesiones de
  harnesses distintos, cuál es el contrato de cada punta, cuál es la intersección real, y
  cuánto dura un puente encima?
- **No recomiendo adoptar nada.** `manifests/external-tool-adoption-freeze.yaml` sigue
  `frozen: true` desde 2026-05-11. Este informe describe lo que existe y su licencia; no
  propone traerlo, vendorearlo ni portarlo.
- **No propongo arquitectura.** No es el encargo.

---

## 1. El veredicto de existencia

**Existe. Varias veces, con licencias distintas, y una de ellas es de OpenAI.**

El operador quiere construir esto, así que conviene ser brutal con la respuesta que no le
gusta: no hay hueco virgen. Hay al menos cuatro cosas publicadas que conectan sesiones de
harnesses distintos, y la más grande tiene 31.915 estrellas.

| Qué | Alcance | Licencia (verificada contra el LICENSE crudo) | Estado real |
|---|---|---|---|
| **`openai/codex-plugin-cc`** | Claude Code → Codex. **Primera parte de OpenAI** | **Apache-2.0** | 31.915 ★. Último commit **2026-07-08**, 0 commits en 30 días |
| **`raysonmeng/agent-bridge`** (AgentBridge) | Claude Code ↔ Codex, bidireccional, mid-turn | **MIT** | 303 ★, 31 tags. Último commit funcional en `master`: **2026-07-07** |
| **`ctliz/agent-intercom-*`** (Agent Intercom) | **Claude Code + Codex + opencode + Pi**, un broker local común, protocolo v4 | **AGPL-3.0** | 0 ★. Repos creados el **2026-08-12/14**. Días de vida |
| **`SeemSeam/claude_codex_bridge`** (CCB) | 17 familias de CLI, incluye Claude Code, Codex y OpenCode | **AGPL-3.0** (GitHub reporta `NOASSERTION`) | 3.405 ★, 334 forks, activo |
| **`ofekron/better-agent`** | Claude, Codex, Gemini en un workspace local | **Licencia propia "Source-Available Non-Commercial"** | 55 ★, activo |

**Las tres cosas que cambian la conversación:**

1. **OpenAI publica un plugin oficial para Claude Code.** `codex-plugin-cc` es de la org
   `openai`, Apache-2.0, y su descripción es literal: *"Use Codex from Claude Code to review
   code or delegate tasks."* Instala con `/plugin marketplace add openai/codex-plugin-cc`.
   O sea: la interoperabilidad Claude Code ↔ Codex **ya tiene una implementación de
   fabricante**, no solo comunitaria. Es delegación de una vía (request in, response out),
   no peering — pero existe y tiene soporte de una de las dos empresas.
   Fuente: `https://github.com/openai/codex-plugin-cc`.

2. **Agent Intercom es exactamente el pedido del operador, palabra por palabra.** Su propia
   descripción: *"a cross-harness, same-machine messaging system for coding agents. Its Pi,
   Codex, Claude Code, and OpenCode adapters share one local broker and protocol, so sessions
   can discover and message each other regardless of which harness they run in."* Los cuatro
   adaptadores existen. **Y es AGPL-3.0**, que la política de licencias del repo
   (`rules/RULES-COMPACT.md` §10, `license-policy`) manda BLOQUEAR.
   Fuente: `https://github.com/ctliz/agent-intercom-opencode`.

3. **La respuesta obvia requeriría descongelar, y eso tiene gate propio.** Si el objetivo es
   "que el SO hable entre harnesses", Agent Intercom ya resolvió el problema y ya eligió las
   mismas cuatro puntas. Adoptarlo, mirarlo de cerca para copiar el diseño, o portar su
   protocolo, son todas cosas que caen del lado del freeze — y además choca de frente con
   AGPL bajo un pivot comercial/SaaS. **Es una decisión del operador con revisión legal, no
   un hallazgo técnico que se ejecute solo.**

**Lo que NO existe:** un estándar. Ninguno de los cinco habla A2A. No hay contrato compartido,
no hay implementación de referencia de un fabricante que cubra las tres puntas, y el único
proyecto que cubre las tres tiene días de vida y cero usuarios. **Existe la plomería; no
existe la norma.**

---

## 2. Método, y los tres estados de evidencia

- **[DOC]** — documentado oficialmente por el fabricante.
- **[CÓDIGO]** — está en el código o el LICENSE publicado, sin doc que lo respalde.
- **[BLOG]** — lo dice un tercero y no lo confirmé. **No cuenta como evidencia.**

**Mirrors, verificados con `curl -sI`** (§9):

| URL que uno escribiría | Qué devuelve | Fuente real |
|---|---|---|
| `developers.openai.com/codex/app-server` | **308** | `learn.chatgpt.com/docs/app-server` |
| `docs.claude.com/en/docs/claude-code/cross-session-messaging` | **301** | `code.claude.com/docs/en/cross-session-messaging` |

Las dos canónicas responden 200. Ningún blog entra como fuente en este informe.

**Licencias verificadas contra el LICENSE crudo, no contra el badge.** Valió la pena: GitHub
reporta `license.spdx_id = NOASSERTION` para `SeemSeam/claude_codex_bridge`, y el LICENSE
crudo dice **AGPL-3.0** en la primera línea. Un proyecto de 3.405 estrellas que la API
clasifica como "sin licencia" es, en realidad, copyleft de red — el peor caso posible para un
pivot SaaS, y el que un pipeline automático dejaría pasar como "sin restricción conocida".

---

## 3. La tabla de cuatro columnas

Lo que sigue es **sesión ↔ sesión**, que es el eje del encargo. Cada celda es lo que el
fabricante publica, no lo que un puente logra a fuerza de trucos.

### Claude Code — la única punta con contrato

Recontado hoy contra `https://code.claude.com/docs/en/cross-session-messaging`, no heredado
del informe de la mañana.

| Columna | Qué dice la fuente |
|---|---|
| **Direccionamiento** | **Por nombre.** El nombre sale de `/rename`, del flag `--name`, o lo deriva Claude Code del directorio (`my-app-3f`). Desde **v2.1.232** se menciona con `@nombre` desde el prompt. Si un solo vivo responde a ese nombre, entrega con el nombre pelado; si hay varios, Claude agrega **un identificador corto** a cada fila y direcciona con él **[DOC]** |
| **Descubrimiento** | Tool `ListAgents`, comando `/list-agents` (alias `/peers`). Cubre subagentes, otras sesiones locales, sesiones cloud (etiqueta `cloud`) y de otras máquinas vía Remote Control (etiqueta `Remote Control`, o `offline` si se cayó la conexión). **Mecanismo real: cada sesión se registra en archivos en disco y bindea ahí su socket** — *"two sessions can reach each other only when they can see the same files"*. Un contenedor no ve al host **[DOC]** |
| **Transporte** | Misma máquina: **socket UDS por sesión, nunca por servidores de Anthropic**, restringido al usuario del SO. Otra máquina tuya: **por servidores de Anthropic**, llegando por Remote Control. Claude Code on the web: por servidores de Anthropic. La ruta se exporta a hooks y Bash como `CLAUDE_CODE_MESSAGING_SOCKET`, con token por sesión en `CLAUDE_CODE_MESSAGING_TOKEN` y frame de auth `{"type":"auth","token":"<token>"}` **[DOC]** |
| **Entrega** | **Tres desenlaces nombrados: `Delivered` / `Held` / `Refused`.** La garantía la niega la propia doc: *"Delivery isn't guaranteed in every configuration"*. Control del receptor con `crossSessionInbound` ∈ `accept`/`hold`/`refuse`. Sin config, decide por clase de modo de permisos de las dos puntas. `dialogExpiry` **5 minutos** por defecto y el mensaje se descarta. Topes: **100 retenidos** por sesión (pasado eso se tira el más viejo) y **50 aceptados** esperando lectura. Anti-loop: rate-limit por emisor y descarte de repeticiones idénticas en ventana corta. Feedback al emisor en la misma máquina (retenido → entregado/denegado/expirado); **un mensaje rechazado al llegar no genera aviso**. Solo texto plano. **Un comando en el texto llega como texto y no se ejecuta.** Un mensaje **nunca** es consentimiento ni cambia permisos/`CLAUDE.md`/config **[DOC]** |

**Disponibilidad:** v2.1.224+, **macOS y Linux** (WSL 2 cuenta), **no** en Windows nativo, y
**no** en Bedrock, Claude Platform on AWS, Google Cloud Agent Platform ni Microsoft Foundry.
Si `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `DISABLE_TELEMETRY`, `DO_NOT_TRACK` o
`DISABLE_GROWTHBOOK` apagan la evaluación de feature flags, **la mensajería queda apagada**.

**El detalle que importa para cualquier puente, y que el informe de la mañana no marcó:**
existe una vía documentada para que **un proceso externo inyecte en una sesión de Claude
Code** — postear al socket con el token como primer frame. La doc la llama *own-child
messages* y describe qué pasa cuando no puede verificar el origen: *"it treats the message
like any other that asserts no permission class"*, o sea que una sesión en bypass lo retiene
para aprobación. **Ésa es la costura oficial de entrada, y viene con su propia degradación
escrita** **[DOC]**.

### Codex CLI — sin mensajería entre sesiones, pero con plano de control documentado

| Columna | Qué dice la fuente |
|---|---|
| **Direccionamiento** | **No hay direccionamiento sesión→sesión.** Lo que hay es direccionamiento de *thread*: `thread/start`, `thread/resume`, `thread/read` sobre el app server **[DOC]** |
| **Descubrimiento** | `thread/list` — *"pages through stored threads with filtering and pagination"*. Es un listado de threads almacenados para un cliente, no un directorio de pares vivos **[DOC]** |
| **Transporte** | **`codex app-server`, JSON-RPC 2.0.** Tres transportes: stdio (NDJSON, default), **WebSocket** (`--listen ws://127.0.0.1:4500`, experimental) y **Unix socket** (`--listen unix://`). WebSocket acepta auth opcional por bearer token o token hasheado SHA256 (`--ws-auth capability-token`) **[DOC]** |
| **Entrega** | **Sin contrato publicado.** Lo que sí está documentado es la primitiva que un puente necesita: **`turn/steer` "appends input to an active in-flight turn"** — inyección mid-turn sin abrir turno nuevo. Más `turn/start` y `turn/interrupt`. Eventos como notificaciones (`thread/started`, `turn/started`, `turn/completed`, `item/*`). **Nada sobre qué pasa si el thread murió, si hay cola, orden o reintento** **[DOC — por ausencia]** |

Fuente: `https://learn.chatgpt.com/docs/app-server`.

**Y esto corrige el brief.** El encargo me pasó `features.multi_agent` / `multi_agent_v2` como
el mecanismo de Codex, con el issue #27331 abierto rompiendo todos los turnos con un 400. Eso
es cierto **y es irrelevante para este encargo**: `multi_agent` es comunicación *entre threads
de agente dentro de una sesión*. La punta que de verdad usa un puente cross-harness es el
**app server**, que está documentado oficialmente, es el que **usa la extensión de VS Code de
Codex**, y no depende de ningún feature flag roto. AgentBridge lo confirma: no toca
`multi_agent` para nada; habla `turn/start` contra el app server.

### opencode — plano de control, cero semántica de agente

| Columna | Qué dice la fuente |
|---|---|
| **Direccionamiento** | **Por `sessionID` en la URL.** No hay nombres, no hay pares, no hay concepto de remitente **[DOC]** |
| **Descubrimiento** | `GET /session` lista sesiones. Es un listado del servidor, no descubrimiento entre pares: **una sesión no tiene forma de saber que otra existe** **[DOC — por ausencia]** |
| **Transporte** | **HTTP.** `opencode serve [--port] [--hostname]`, default **`127.0.0.1:4096`**, solo localhost. Auth **opcional** por HTTP basic con `OPENCODE_SERVER_PASSWORD` (usuario default `opencode`). Eventos por SSE en `GET /event` y `GET /global/event` **[DOC]** |
| **Entrega** | **Nada.** `POST /session/:id/message` = *"send a message and wait for response"*; `POST /session/:id/prompt_async` = *"send a message asynchronously (no wait)"*, devuelve 204. **La doc no dice qué pasa si el destinatario está ocupado, si no existe, si hay cola, ni qué garantía hay.** Un 204 confirma que el HTTP se aceptó, no que la sesión lo haya visto **[DOC — por ausencia]** |

Fuente: `https://opencode.ai/docs/server/`.

---

## 4. La intersección real, y qué se pierde en ella

Las tres puntas tienen mecanismo. La intersección **de lo que hoy funciona** es mucho más
chica que la unión, y lo que se cae es justamente lo único valioso.

**Lo que sobrevive a las tres puntas:**

1. **Un proceso local puede empujar texto dentro de una sesión corriendo.** Claude Code por
   UDS con token; Codex por `turn/start` o `turn/steer` sobre JSON-RPC; opencode por
   `POST /session/:id/prompt_async`. Los tres, **solo en la misma máquina** y solo con un
   demonio externo haciendo de bus.
2. **Texto plano.** Es el techo de Claude Code por contrato (*"Plain text only"*), así que
   ninguna estructura sobrevive el cruce aunque las otras dos puntas la aguanten.
3. **Un identificador opaco por sesión**, con formatos que no se parecen en nada entre sí.

**Lo que se pierde, y hay que decirlo explícito:**

| Se pierde | Por qué |
|---|---|
| **El descubrimiento** | Ninguna punta ve a las otras. El registro en disco de Claude Code solo lista sesiones de Claude Code; `thread/list` de Codex solo lista threads de Codex; `GET /session` de opencode solo lista las suyas. **Un directorio cross-harness no existe: hay que construirlo y mantenerlo, y ése es el demonio.** Es exactamente lo que hace el broker de Agent Intercom |
| **Los tres desenlaces** | `Delivered`/`Held`/`Refused` es de Claude Code y **de nadie más**. Contra Codex y opencode el emisor recibe, como mucho, un ACK de transporte. Un puente que prometa las tres respuestas en las tres puntas está inventando dos de ellas |
| **El control del receptor** | `crossSessionInbound` no tiene equivalente. Un mensaje que entra a Codex por `turn/start` **entra**; no hay `hold`, no hay diálogo, no hay expiry de 5 minutos |
| **El feedback al emisor** | Solo Claude Code, y solo en la misma máquina |
| **El anti-loop** | Rate-limit por emisor y dedup de repetidos son de Claude Code. En la intersección, el loop lo tiene que frenar el puente. AgentBridge lo reconoce: su README lista *"Loop prevention via the per-message `source` field"* como feature propia |
| **El orden** | **Nadie lo promete, en ninguna punta.** Busqué explícitamente en la doc de Claude Code; el único hit de `guarantee` es la frase que niega la entrega. Confirmado hoy |
| **El límite de autoridad** | Y éste es el que duele — ver abajo |

**La pérdida grande: el contrato de Claude Code se cae por la forma en que se lo hace hablar.**

Claude Code garantiza que un mensaje entrante **no aprueba nada**, no cambia config, y que un
comando en el texto llega como texto. Ese contrato depende de que el receptor siga pidiendo
permisos. Ahora, el puente que de verdad funciona hoy, AgentBridge, arranca las dos puntas así
—su propio README, en un bloque `WARNING`:

> `abg claude` lanza con `--dangerously-skip-permissions` y `abg codex` con `--yolo` por
> defecto. *"This is deliberate: an unattended agent pair can't stop to ask you for each
> permission."*

Y para el canal usa `--dangerously-load-development-channels`. O sea: **la interoperabilidad
que hoy funciona se compra apagando exactamente la garantía que hacía valioso el contrato de
Claude Code.** No es un descuido del proyecto; es la consecuencia de que el eslabón más débil
manda. Codex y opencode no tienen inbound controls, así que un par que espera respuestas
automáticas no puede quedarse esperando aprobaciones — y la única forma de que no espere es
sacarle los frenos a las dos puntas.

**Ésa es la intersección real: texto plano, misma máquina, un demonio propio haciendo de
directorio y de anti-loop, y sin frenos de permisos.** Todo lo que en Claude Code está escrito
como garantía, cruzando harnesses hay que volver a construirlo — y quien lo construya es quien
responde por ello.

---

## 5. Vida media de un puente

La pregunta del encargo era si un puente sobre APIs que se mueven así tiene vida media
estimable. Sí, y los números salen de tres lados distintos que coinciden.

**Dato 1 — la superficie de Claude Code se mueve, pero menos de lo que decía el brief.**
Contando entradas del changelog que tocan mensajería entre 2.1.222 y 2.1.233:

| Release | Entradas que tocan mensajería |
|---|---|
| 2.1.222 | 2 (truncado de summary; clasificador de permisos antes del dispatch) |
| 2.1.224 | 3 (**shipping**: `SendMessage` cross-session, `ListAgents`, `crossSessionInbound`, `dialogExpiry`) |
| 2.1.225 | 3 (iniciar conversación cross-machine; expiry en headless) |
| 2.1.228 | 2 (inbox faltante en primera sesión; render inline) |
| 2.1.229 | 1 (`offline` / `cloud` en `ListAgents`) |
| 2.1.232 | 4 (`@mention`; entrega por nombre pelado; filas de `/config`; hardening del directorio de sockets) |
| **2.1.233** | **0** |

Siete de doce releases tocaron la feature. **Pero solo dos cambiaron semántica de
direccionamiento** (2.1.225 y 2.1.232), no cinco. El brief decía *"el direccionamiento cambió
cinco veces en ocho días"*; lo que cambió cinco veces fue la **feature**, y la mayoría fueron
fixes y UI. **Y 2.1.233, que salió después del informe de la mañana, no la tocó.**

**Dato 2 — el costo de mantenimiento observado.** AgentBridge lleva **31 tags** desde
2026-03-20, o sea un release cada ~4,8 días sostenido durante meses, para mantener parado un
puente de **dos** puntas. Ése es el precio empírico.

**Dato 3, y es el que más dice — los dos puentes serios están quietos.**

| Repo | `pushed_at` de la API | **Último commit real en la rama default** |
|---|---|---|
| `raysonmeng/agent-bridge` | 2026-08-15 | **2026-07-07** (README/GIF). 0 commits en 30 días. La rama `integration/v3-all` está peor: **2026-07-03** |
| `openai/codex-plugin-cc` | 2026-07-08 | 0 commits en 30 días |

**Advertencia de método que vale más que el dato:** `pushed_at` decía **hoy** para un repo cuyo
último commit funcional es de hace 39 días. `pushed_at` se mueve con cualquier push de rama o
tag. El informe de la mañana usó `pushed_at` como señal de salud para juzgar los plugins de
opencode, y el brief heredó esa lectura. **Es una métrica falsa; el commit de la rama default
es el dato.**

**La estimación.** Un puente cross-harness tiene **dos relojes distintos**:

- **El reloj rápido, semanas:** todo lo apoyado en superficie marcada como preview —los
  Channels de Claude Code, cuya doc dice que *"the `--channels` flag syntax and protocol
  contract may change"*, el `--dangerously-load-development-channels`, y el WebSocket
  experimental del app server de Codex. Acá la vida media es del orden de **4 a 8 semanas**,
  y el número no es teórico: es el intervalo entre releases de AgentBridge, que es lo que
  cuesta seguirle el paso.
- **El reloj lento, meses:** lo apoyado en superficie con consumidor de primera parte. El app
  server de Codex sostiene la extensión de VS Code de OpenAI, y el socket de Claude Code está
  documentado con env vars estables y un contrato de verificación escrito. Ahí la vida media
  es de **meses**, y las roturas vienen con nota en el changelog.

**El fallo primero no es una API: es la política de permisos.** Un puente que hoy compra
interoperabilidad con `--dangerously-skip-permissions` + `--yolo` se rompe el día que
cualquiera de las dos puntas endurezca eso — y las dos vienen endureciendo (2.1.222 metió el
clasificador de permisos antes del dispatch, 2.1.232 endureció el directorio de sockets contra
symlinks plantados). **La superficie de seguridad se mueve más rápido que la funcional, y en
la dirección contraria a la que un puente necesita.**

---

## 6. Lo que no pude verificar

1. **No ejecuté ninguno de los cinco proyectos.** Todo lo que digo de AgentBridge, Agent
   Intercom, CCB, better-agent y `codex-plugin-cc` sale de su README, su LICENSE y la API de
   GitHub. **No vi a Claude Code hablando con opencode con mis propios ojos.**
2. **El contrato de Agent Intercom.** Su protocolo v4 y el "broker-enforced scope routing"
   los describe su propio README; no leí el código de `agent-intercom-core` ni verifiqué qué
   garantiza de verdad. Es el candidato más relevante y **el menos verificado** de la lista.
3. **Si la línea `dataforxyz/*` y la `ctliz/*` son el mismo software.** El README de `ctliz`
   dice que es una distribución mantenida independientemente con herencia de `dataforxyz` y de
   `nicobailon/pi-intercom`. No auditopé la cadena de forks ni si la relicencia de MIT
   (pi-intercom) a AGPL-3.0 (agent-intercom) está limpia. **Para una decisión de adopción eso
   sería lo primero a mirar, y es trabajo de revisión legal, no mío.**
4. **La licencia de `better-agent`.** Leí las primeras 30 líneas de un texto propio no-OSI.
   Lo que sí es firme: **prohíbe uso comercial**, incluido "commercial internal tool" y
   "consulting deliverable". Bajo el pivot comercial del repo, eso lo descarta solo.
5. **Orden de mensajes.** Nadie lo promete en ninguna punta. Confirmado por ausencia en las
   tres docs, no por una afirmación de nadie.
6. **Las fuentes 2 y 3 del operador** (`nexforce.ai`, `mcpmarket.com`) no las abrí. Son, por
   su propia clasificación en el encargo, mirrors de experiencia; todo lo que podrían aportar
   está cubierto por doc oficial recontada. La 4 (Medium) tampoco: el informe de la mañana ya
   había fallado en leer su cuerpo.

---

## 7. Qué de este encargo era falso

**1. "Issue #37213 — la más concreta, arrancá acá." Es la fuente más débil de las cuatro.**
Está **CERRADA como duplicado**, la cerró su propio autor 4 minutos después de abrirla
(2026-03-21, 19:37 → 19:41), tras un bot que le marcó tres duplicados. Y sobre todo: **no es
cross-harness.** Pide comunicación entre instancias de Claude Code entre sí. Su workaround es
un MCP de tmux; su comparación es contra la feature nativa de Teams. **Claude Code ↔ Codex no
aparece.** Además quedó obsoleta: pedía `claude --list-sessions` y mensajería entre sesiones, y
eso **shipeó** en v2.1.224 cinco meses después. De sus tres duplicados, **#24798 sigue abierto**
(2026-02-10) y los otros dos se cerraron. Arrancar por ahí, como pedía el encargo, habría
costado el lote entero: la respuesta no estaba en el repo de Anthropic sino en el de OpenAI.

**2. "Codex: el issue #27331 sigue abierto, prender el flag rompe todos los turnos." Cierto e
irrelevante.** `multi_agent_v2` es intra-sesión, entre threads de agente. **La punta que un
puente cross-harness usa es el app server**, documentado en `learn.chatgpt.com/docs/app-server`,
con `turn/start`, `turn/steer` y `turn/interrupt`, sin feature flag y con la extensión de VS
Code de OpenAI como consumidor de primera parte. El brief me mandó a mirar el mecanismo roto e
ignorar el que funciona. AgentBridge no toca `multi_agent`.

**3. "El direccionamiento de Claude Code cambió cinco veces en ocho días."** Cinco releases
tocaron la **feature**; el **direccionamiento** cambió **dos** veces (2.1.225 y 2.1.232). El
resto fueron fixes, hardening y filas de `/config`. Y **2.1.233 ya salió sin tocarla**. La
superficie se mueve, pero menos de lo que dice el encargo, y la conclusión de fragilidad hay
que sostenerla con otro argumento —el de permisos, §5— no con ése.

**4. "Existe al menos un puente comunitario sobre MCP... encontralo."** Lo encontré, y el
encargo subestimó el hallazgo por dos lados. Primero, **no es uno: son cinco**, y uno es de
OpenAI con 31.915 estrellas. Segundo, **AgentBridge no es un experimento de 24 horas**: tiene
31 releases y 303 estrellas. Pero está **quieto desde el 2026-07-07**, cosa que `pushed_at` de
la API oculta.

**5. Lo que el encargo no anticipó, y es el hallazgo central.** La pregunta "¿cuál es el mínimo
sustrato común?" da por sentado que el problema es de plomería. **No lo es.** Las tres puntas
saben recibir texto de un proceso local; eso está resuelto y documentado en las tres. Lo que no
existe en la intersección es **el directorio** y **la política de admisión**. Y el puente que
hoy funciona resuelve la política de admisión **apagándola en las dos puntas**. Cualquier cosa
que se construya acá arranca eligiendo entre "hereda el contrato de Claude Code y no puede
correr desatendido" o "corre desatendido y no hereda ningún contrato". **Ese trade-off es el
diseño, y no lo relaja ninguna elección de transporte.**

---

## 8. Evidencia ejecutable

Read-only, deterministas, sin estado de sesión. Requieren `gh` autenticado y salida a internet.

```bash
# §2 — mirrors: las dos URLs "obvias" son alias, no fuentes
for u in https://developers.openai.com/codex/app-server \
         https://docs.claude.com/en/docs/claude-code/cross-session-messaging \
         https://learn.chatgpt.com/docs/app-server \
         https://code.claude.com/docs/en/cross-session-messaging; do
  printf "%-70s " "$u"
  curl -sI "$u" | awk 'BEGIN{ORS=""} /^HTTP/{c=$2} tolower($1)=="location:"{l=$2} END{print c" -> "l"\n"}'
done

# §1 — el veredicto de existencia: qué hay, con licencia y estrellas
for r in openai/codex-plugin-cc raysonmeng/agent-bridge SeemSeam/claude_codex_bridge \
         ofekron/better-agent ctliz/agent-intercom-core ctliz/agent-intercom-claude \
         ctliz/agent-intercom-codex ctliz/agent-intercom-opencode nicobailon/pi-intercom; do
  printf "%-40s " "$r"
  gh api repos/$r -q '"stars=\(.stargazers_count) created=\(.created_at[0:10]) lic=\(.license.spdx_id // "NONE")"'
done

# §2 — la licencia se verifica en el LICENSE crudo, no en el badge.
# GitHub dice NOASSERTION; el archivo dice AGPL-3.0.
gh api repos/SeemSeam/claude_codex_bridge/contents/LICENSE -q '.content' | base64 -d | head -3
gh api repos/ofekron/better-agent/contents/LICENSE -q '.content' | base64 -d | head -3

# §5 — pushed_at MIENTE. El commit de la rama default es el dato.
for r in raysonmeng/agent-bridge openai/codex-plugin-cc; do
  echo "== $r =="
  gh api repos/$r -q '"pushed_at(API) = \(.pushed_at[0:10])"'
  gh api "repos/$r/commits?per_page=1" -q '"ultimo commit real = \(.[0].commit.author.date[0:10])"'
  echo "commits ultimos 30d = $(gh api "repos/$r/commits?since=2026-07-16T00:00:00Z&per_page=100" --paginate -q '.[].sha' | wc -l)"
done

# §5 — costo de mantenimiento observado de un puente de DOS puntas
echo "agent-bridge tags: $(gh api --paginate repos/raysonmeng/agent-bridge/tags -q '.[].name' | wc -l)"

# §5 — churn real de la mensajería de Claude Code (no cinco cambios de direccionamiento)
curl -s https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md \
  | awk '/^## 2\.1\.2(2[0-9]|3[0-9])/{v=$2} /^## 2\.1\.21/{exit}
         v && /SendMessage|ListAgents|cross-session|list-agents|messaging|crossSessionInbound|isolatePeerMachines|dialogExpiry|inbox socket/{print v": "substr($0,3,110)}'

# §3 — Claude Code: nadie promete orden; el unico "guarantee" niega la entrega
curl -s https://code.claude.com/docs/en/cross-session-messaging.md \
  | grep -inE 'order|ordering|sequence|fifo|at-least-once|exactly-once|guarantee'

# §7 — la fuente #1 del encargo: cerrada como duplicado por su propio autor, y no es cross-harness
gh issue view 37213 --repo anthropics/claude-code --json number,state,createdAt,closedAt,labels
for n in 24798 29086 24947; do
  gh issue view $n --repo anthropics/claude-code \
    --json number,title,state,createdAt -q '"#\(.number) [\(.state)] \(.createdAt[0:10]) \(.title)"'
done

# §1 — el puente sobre MCP que pedia el encargo, las dos puntas
gh api graphql -f query='{repository(owner:"openai",name:"codex"){discussion(number:15374){title createdAt url}}}'
gh issue view 36871 --repo anthropics/claude-code --json number,title,state,createdAt

# §1 — busqueda por concepto, no por nombre
for q in "claude+code+codex+bridge" "cross-harness+agent+messaging" "opencode+claude+code+bridge"; do
  echo "### $q"
  gh api "search/repositories?q=${q}&sort=stars&per_page=6" \
    -q '.items[] | "\(.stargazers_count)\t\(.full_name)\t\(.license.spdx_id // "NONE")\t\(.pushed_at[0:10])"'
done
```

### Fuentes primarias

**Claude Code** (`code.claude.com/docs/en/`): `cross-session-messaging`, `channels`, más el
`CHANGELOG.md` de `github.com/anthropics/claude-code`. Nota: `docs.claude.com/en/docs/claude-code/*`
responde **301** hacia `code.claude.com/docs/en/*` — mismo origen, no fuente independiente.

**Codex** (`learn.chatgpt.com/docs/`): `app-server`. Nota: `developers.openai.com/codex/*`
responde **308** hacia allá. Repo de primera parte: `github.com/openai/codex-plugin-cc`.

**opencode** (`opencode.ai/docs/`): `server/`.

**Proyectos de terceros:** `github.com/raysonmeng/agent-bridge` (MIT),
`github.com/ctliz/agent-intercom-{core,claude,codex,opencode,orchestrator}` (AGPL-3.0),
`github.com/SeemSeam/claude_codex_bridge` (AGPL-3.0 en el LICENSE crudo),
`github.com/ofekron/better-agent` (source-available no comercial),
`github.com/nicobailon/pi-intercom` (MIT, single-harness, upstream de Agent Intercom).
Discusión del puente: `github.com/openai/codex/discussions/15374`.
