# A2A e interoperabilidad entre agentes — qué resuelve y qué no

**Fecha:** 2026-08-15
**Alcance:** A2A (Agent2Agent), OASF/AGNTCY, ACP, y si Claude Code / Codex / opencode exponen algo compatible.
**Método:** clones `--depth 50` leídos localmente. Nada del clon se ejecutó. Los clones se borraron al terminar; por eso cada afirmación cita archivo y línea.

---

## Licencias — ninguna bloqueada

`rules/license-policy` bloquea AGPL/SSPL/BSL. **No apareció ninguna.** Las cuatro licencias salieron del archivo `LICENSE` del clon, no del README ni de la API de GitHub:

| Repo | Licencia | Fuente |
|---|---|---|
| `a2aproject/A2A` | Apache-2.0 | `LICENSE:2` |
| `openai/codex` | Apache-2.0 | `LICENSE:1-3` |
| `sst/opencode` | MIT | `LICENSE:1` |
| `agntcy/oasf` | Apache-2.0 | `LICENSE.md:2` (ojo: `LICENSE.md`, no `LICENSE` — un chequeo que busque `LICENSE` exacto lo reporta como "sin licencia") |
| `i-am-bee/acp` | Apache-2.0 | `LICENSE:2` |

---

## Correcciones a las premisas del encargo

Esta sección es la más importante del informe. **La premisa central del encargo era falsa, y de forma verificable en un comando.**

### 1. "Cero menciones en todo el repo" — falso. Son 47 archivos.

El encargo afirmaba, y pedía verificar:

```
git grep -l --untracked -E 'A2A|Agent2Agent|AGNTCY|AgentCard'   → 0 archivos
```

Corrido en `HEAD` de `session/21f28a76-audit-2026-08-15`:

```
$ git grep -l --untracked -E 'A2A|Agent2Agent|AGNTCY|AgentCard' | wc -l
47
```

Desglose por patrón (mismo comando, un patrón por vez): `A2A` → 47, `Agent2Agent` → 2, `AgentCard` → 1, `AGNTCY` → 0. Sólo el último coincidía con lo que decía el encargo.

### 2. "Incluidos los cuatro informes de hoy" — falso. Uno de hoy lo trata en detalle.

`docs/06-Daily/reports/juez-externo-orquestacion-multimodelo-2026-08-15.md:196` ya tiene el estado de gobernanza verificado, y mejor fechado que lo que yo hubiera reconstruido solo:

> **A2A (Agent2Agent Protocol)** — propuesta #37, **aprobada**: el TC la aprobó como Growth Stage el 2026-07-15 y el Governing Board el **2026-08-04**

Ese mismo informe ya había detectado la trampa del dominio: `agenticaifoundation.org` responde 307 a una página de GoDaddy en venta; el sitio real es `aaif.io`. El encargo mencionaba ese incidente como algo a evitar, sin registrar que ya estaba documentado.

### 3. "Y después no miró el estándar diseñado para esa capa" — falso, y hay una decisión escrita rechazándolo.

`docs/02-Decisions/adrs/ADR-230-handoff-envelope-and-cycle-deduplication.md:233`, en la sección de alternativas rechazadas:

> **Adopt Google A2A protocol directly.** Apache 2.0 OK; over-engineered for our scope (designed for cross-org task delegation). Adopt the `referenceTaskIds` shape; skip the rest.

O sea: A2A se miró, se evaluó, se adoptó una pieza (la forma de `referenceTaskIds`) y se rechazó el resto **con motivo escrito**. Es exactamente la disciplina de "coincidencia aceptada con el motivo escrito" que pide el criterio de la casa. El encargo pedía investigar como si eso no existiera.

### 4. Lo que el encargo NO sabía y es peor que lo que creía

Hay una clase llamada `A2AHttpAgentTeamTransport` en `packages/agent-lifecycle/lib/agent_team_transport.py:157`. **No implementa A2A.** El cuerpo que POSTea (líneas 173-182) es:

```python
body = {
    "schema_version": SCHEMA_VERSION,
    "transport": "a2a-http",
    "team_name": self.team_name,
    "recipient": session_id,
    "message_part": payload,
}
```

Ninguno de esos campos existe en A2A. El `Message` de A2A tiene `messageId`, `role`, `parts`, `contextId`, `taskId`, `referenceTaskIds` (spec §Message). Tampoco hay JSON-RPC, ni agent card, ni negociación de auth. El docstring es honesto —dice *"A2A-style"* y *"executable against any HTTP A2A bridge/gateway"*— pero el nombre de la clase no lo es: promete conformidad con un estándar y entrega un POST de JSON propio.

Esto es un verde barato de nomenclatura: le pone el nombre del estándar a algo que no lo cumple, y el próximo que lea el árbol de módulos va a creer que la interop ya está resuelta. **Es el hallazgo más accionable de este informe** y no estaba en el encargo.

### 5. El freeze — la premisa del encargo era correcta, verificado

`manifests/external-tool-adoption-freeze.yaml:117-122`, textual:

```yaml
  not_governed_by_freeze:
    - repo: agentsmd/agents.md
      reason: |
        ... The freeze governs adoption of external code, not adherence to a published spec.
```

Confirmado. El freeze sigue `frozen: true` (línea 10). Adherir a la spec de A2A no lo activa; vendorear un SDK sí.

---

## Pregunta 3 (la más accionable): ¿los tres arneses exponen algo compatible?

**No. Ninguno de los tres. Cero.** Esto vuelve teórico casi todo lo demás.

| Arnés | Refs A2A / agent-card | Control (MCP) | Comando |
|---|---|---|---|
| Claude Code 2.1.152 | **0** | 13 | `strings -a <bin> \| grep -ciE 'agent2agent\|well-known/agent-card\|a2aproject\|a2a-protocol'` |
| `openai/codex` @ `b3cc217` | **0** | muchas | `grep -rniE 'agent2agent\|agent-card\.json\|well-known/agent' . \| wc -l` |
| `sst/opencode` @ `4643e65` | **0** | muchas | idem |

Detalles que importan:

- **Claude Code**: los únicos `.well-known/` en el binario son `openid-configuration`, `oauth-authorization-server` y `appspecific/com.chrome.devtools.json`. Auth y devtools, no descubrimiento de agentes. (El binario auditado es `~/.local/share/claude/versions/2.1.152`; el archivo `2.1.195` del mismo directorio está en **0 bytes** — vale la pena que lo mire alguien, es un artefacto de instalación roto ajeno a esta investigación.)
- **codex**: todos los `well-known` del árbol Rust son `oauth-authorization-server/mcp` en `codex-rs/rmcp-client/`. Habla MCP con OAuth, no A2A.
- **opencode**: los "hits" del grep amplio eran falsos positivos — colores hex (`#1a3a2a`) y base64 en fixtures.

### El hallazgo colateral: codex ya tiene directorio y admisión, propietarios

`codex-rs/agent-identity/src/lib.rs` es un sistema completo de identidad de agentes: registro, material de clave, JWT con claims (`AgentIdentityJwtClaims`, línea 116), firma de payload de registro (`sign_task_registration_payload`, línea 306), `AgentBillOfMaterials` (línea 103), y errores de registro con reintento (`is_retryable_registration_error`, línea 208).

Apunta a `agent_identity_authapi_base_url` (línea 83), derivado de `chatgpt_base_url`. Es decir: **el único de los tres arneses que resolvió el problema de directorio y admisión lo resolvió contra la API de OpenAI, cerrado y por vendor.** No es A2A y no es interoperable. Si alguien esperaba que la convergencia viniera sola por adopción de los arneses, esto es la evidencia de que va en la dirección contraria.

---

## Pregunta 1 (la que decide): ¿A2A resuelve el directorio y la admisión, o los describe?

**Los describe. La parte difícil queda explícitamente a cargo del implementador**, y la spec lo dice con todas las letras en dos lugares.

### El registro no tiene API estándar

`docs/topics/agent-discovery.md:59`, sobre la estrategia de registro curado:

> The current A2A specification does not prescribe a standard API for curated registries.

Las tres estrategias que la spec ofrece (`agent-discovery.md`) son: `.well-known/agent-card.json` por dominio (línea 25), registro curado (línea 43) y configuración directa/hardcodeada (línea 63). La primera exige que ya sepas el dominio. La tercera es hardcodear. **La única que es realmente un directorio es la segunda, y es justo la que no está especificada.** Línea 112: *"The A2A community explores standardizing registry interactions"* — futuro, no presente.

### La autorización es "implementation-specific"

`docs/specification.md:1901`, §7.5 "Server Authorization Responsibilities", textual:

> Once authenticated, the A2A Server authorizes requests based on the authenticated identity and its own policies. **Authorization logic is implementation-specific** and **MAY** consider: [specific skills requested / actions attempted within tasks / data access policies / OAuth scopes]

Eso es la sección entera. A2A estandariza **cómo se autentica** (cinco esquemas: API key, HTTP bearer, OAuth2, OIDC, mTLS — §4.5) y deja **quién puede pedir qué** enteramente afuera. Y en autorización dentro de una tarea es aún más explícito, §7.6 (`specification.md:1966`):

> The A2A protocol **does not define** the scope, representation, validity, or revocation semantics of the authorization decision or credential obtained in response to this state.

### La tarjeta es una afirmación, y firmarla es opcional

La intuición del encargo acá era correcta y la spec la confirma. `docs/specification.md:2014`:

> Agent Cards **MAY** be digitally signed using JSON Web Signature (JWS) as defined in RFC 7515 to ensure **authenticity and integrity**.

**`MAY`, no `MUST`.** Y la verificación tampoco es obligatoria — `specification.md:2138`, en Security Considerations de §8.4.3:

> Clients **SHOULD** verify at least one signature before trusting an Agent Card

`SHOULD`, no `MUST`. Pero lo decisivo es **qué prueba la firma**. Los seis pasos de verificación (§8.4.3, líneas 2130-2136) son: extraer firma, obtener clave pública vía `kid`/`jku`, quitar defaults, excluir `signatures`, canonicalizar con RFC 8785, verificar. Eso prueba que **el documento no fue alterado y viene de quien dice la clave**. No prueba absolutamente nada sobre si el agente sabe hacer lo que la tarjeta dice que sabe hacer.

Un agente puede firmar criptográficamente una tarjeta que declara `"skills": [{"name": "process-refund"}]` sin tener la menor capacidad de procesar un reembolso, y la firma verifica perfecto. **La tarjeta firmada es una afirmación autenticada, no una afirmación verificada.** No hay conformance test, ni atestación de capacidad, ni revocación de skills en la spec.

Nota de corrección a un documento propio: `docs/03-PoCs/research/orchestration-gaps/agent-to-agent-handoff.md:277` describe la Agent Card como *"a signed JSON document"* con un campo `"signature"` obligatorio. Es más fuerte que la spec (firma opcional, campo `signatures` plural, formato JWS de tres partes) y el ejemplo de esquema que trae ahí no coincide con `specification/a2a.proto:396` (`repeated AgentCardSignature signatures = 13`). Ese doc es de mayo y la spec llegó a 1.0 en marzo con breaking changes; probablemente se escribió sobre material previo.

### Veredicto de la pregunta que decide

**Adherir a A2A no nos ahorra la parte difícil.** Nos da un formato de tarjeta, un vocabulario de tarea (8 estados) y una lista de esquemas de auth. El directorio (quién existe) y la admisión (quién puede pedirle qué a quién) siguen siendo enteramente nuestros. La conclusión del trabajo de transporte de hoy —que lo que falta es directorio y política de admisión— **sigue en pie después de mirar A2A**.

---

## Pregunta 4: la relación con MCP

La frase "MCP conecta agentes con herramientas, A2A agentes entre sí" **no es una simplificación de blogs: es la posición oficial**, escrita en el repo del estándar. `docs/topics/a2a-and-mcp.md` es un documento entero dedicado a eso:

- MCP (líneas 10-20): *"Standardizes how AI models and agents connect to and interact with tools, APIs, and other external resources"*.
- A2A (líneas 24-35): *"Standardizes how independent, often **opaque**, AI agents communicate and collaborate as peers"*.
- El criterio de corte (líneas 39-53): herramientas = primitivas con I/O estructurado, sin estado, discretas. Agentes = razonan, planifican, usan varias herramientas, mantienen estado, multi-turno.

La palabra que hace el trabajo real es **opaque**. A2A asume que del otro lado hay algo cuyo interior no ves ni controlás. Ése es el supuesto que no se cumple en nuestro caso: entre sesiones de Claude Code, Codex y opencode del mismo operador, en la misma máquina, los agentes **no son opacos entre sí** —comparten filesystem, se pueden leer los logs, corren bajo el mismo usuario— y no hay frontera de organización que cruzar.

Dónde se superponen: en que un agente A2A puede exponerse como herramienta MCP y viceversa, con lo cual la frontera es de intención, no de mecanismo. La spec no lo prohíbe ni lo estandariza.

---

## Pregunta 2: estado real a agosto de 2026

**Vivo, y activamente.** El comando que lo prueba, sobre la rama default del clon:

```
$ git log -1 --format='%ci %h %s'
2026-08-15 15:15:28 +0200 134a382 docs: fix broken links (#2139)
```

Commit **del mismo día** de esta investigación. En los últimos 50 commits (desde `2026-05-19`) hay **26 autores distintos** (`git log --format='%an' | sort -u | wc -l`). No es un repo de una persona.

- **Versión:** `v1.0.1`, único tag en la ventana. `CHANGELOG.md`: 1.0.0 el **2026-03-12** (con breaking changes fuertes: refactor grande de la spec, remoción de flows OAuth implicit/password, `extendedAgentCard` movido a `AgentCapabilities`), y 1.0.1 el **2026-05-26** (tres bugfixes de spec).
- **Gobernanza — ya NO es de Google.** `GOVERNANCE.md:3-14`: Technical Steering Committee de ocho asientos, uno por empresa: **Google, Microsoft, Cisco, AWS, Salesforce, ServiceNow, SAP, IBM**. Google tiene un voto de ocho. La composición actual es "Startup Phase"; el "Steady State" se decide a los 18 meses de la inception.
- **Fundación:** aprobado como proyecto de la AAIF — TC el 2026-07-15, Governing Board el **2026-08-04**, verificado en los comentarios de la propuesta #37 según `docs/06-Daily/reports/juez-externo-orquestacion-multimodelo-2026-08-15.md:196`. **No verifiqué yo esa fecha contra el issue**; la tomo de ese informe de hoy, que sí dice haberlo abierto.

**Sobre "quién lo implementa de verdad":** no lo pude establecer, y lo dejo como no verificado en vez de rellenarlo. Lo que sí sé: `docs/partners.md` existe en el repo del estándar, y una lista de partners es exactamente lo que el encargo advirtió que no cuenta como adopción. No la usé. Lo único que medí de primera mano es lo de la pregunta 3: **ninguno de los tres arneses que nos importan implementa nada.**

---

## Pregunta 5: el panorama, y lo descartado con motivo

### ACP (`i-am-bee/acp`) — DESCARTADO: está muerto, se fusionó con A2A

El dato más limpio de todo el relevamiento. Último commit:

```
$ git log -1 --format='%ci %h %s'
2025-08-25 14:42:35 -0400 e5265ca docs: A2A announcement (#230)
```

**Casi un año sin actividad, y el último commit es el anuncio de su propia absorción.** `README.md:25`:

> **ACP is now part of A2A under the Linux Foundation!**

Apache-2.0, 12 autores. No hay nada que evaluar: dejó de existir como estándar separado. Si alguien vuelve a encontrarse el nombre en un blog de 2025, es esto.

### OASF / AGNTCY (`agntcy/oasf`) — DESCARTADO para este problema, pero es el más cercano conceptualmente

"Open Agentic Schema Framework". Apache-2.0 (`LICENSE.md:2`). Vivo pero mucho más chico: último commit `2026-07-21` (`e856537 perf(server): server memory handling (#487)`), **25 días antes de hoy**, y sólo **4 autores** en los últimos 50 commits contra los 26 de A2A. Hay una rama `169-create-new-oasf-module-agentskills`, o sea el esquema de skills todavía se está moviendo.

Es un esquema de capacidades —la misma capa que la Agent Card— pero no lo profundicé porque **la pregunta 3 ya lo desactivó**: si ningún arnés publica una Agent Card de A2A, mucho menos publica un registro OASF. Se descarta por falta de consumidor, no por defecto propio. Si el directorio alguna vez se construye acá y hace falta un vocabulario de skills, vale volver.

`agntcy/slim` existe y está activo (ramas con números de issue >1000) pero no lo miré: por el nombre y las ramas parece transporte/mensajería, y transporte es justo lo que la investigación de hoy ya cerró como no-problema.

### Lo que ya estaba relevado en el repo y no repetí

`docs/06-Daily/reports/juez-externo-orquestacion-multimodelo-2026-08-15.md` barrió **las 31 propuestas de proyecto de la AAIF** buscando algo equivalente para routing de modelos y contrato de comportamiento de subagentes. Conclusión de ahí, que confirmo y no dupliqué: agentgateway y Agent Router / Envoy AI Gateway enrutan **requests** (auth, rate limiting, failover), no comportamiento. Y `agentsmd/agents.md#184` propone un `.agent/` tool-agnostic pero su propio "Out of Scope" excluye la lógica de runtime.

---

## Qué significaría adherir acá, y qué no

**No requiere descongelar el freeze:** precedente escrito y verificado arriba (`external-tool-adoption-freeze.yaml:122`).

**Lo que sí requeriría descongelar:** vendorear cualquier SDK de A2A. Y acá está el punto práctico — la spec es implementable sin SDK. El binding HTTP+JSON es JSON-RPC 2.0 sobre HTTPS con un JSON en `/.well-known/agent-card.json`; la firma es JWS RFC 7515 con canonicalización JCS RFC 8785, que es más trabajo pero sigue siendo stdlib. **No es un caso de "esto sólo sirve con su SDK".**

**La pregunta del criterio de la casa** — *¿un cambio en uno de los dos conceptos debería obligar a tocar el otro?*

Nuestro problema: sesiones locales del mismo operador, en la misma máquina, mismo usuario, sin frontera organizacional, con confianza mutua ya establecida por el filesystem. El problema de A2A: sistemas de agentes **opacos** de vendors distintos, cruzando fronteras de organización, sin confianza previa, negociando credenciales por par.

Si A2A 1.2 cambia el flow de OAuth device code, ¿deberíamos tocar nuestro directorio local? No. Si nuestro directorio local pasa a indexar por rama de git, ¿A2A debería cambiar? No. **Es coincidencia de superficie: los dos tienen una tarjeta con capacidades declaradas, y ahí se termina el parecido.** Se deja aceptada, con este motivo escrito.

**Lo que sí vale la pena tomar prestado, sin adherir:** la separación entre *autenticar* (estandarizada, cinco esquemas, §4.5) y *autorizar* (explícitamente del implementador, §7.5) es una distinción bien puesta que nuestro diseño de admisión debería copiar. Y la lección negativa de la firma —autenticidad ≠ veracidad de la capacidad— es directamente aplicable: cualquier directorio que construyamos donde el agente se autodeclare va a tener el mismo agujero, y firmarlo no lo tapa. Eso es adopción de patrón, igual que ADR-230 con `referenceTaskIds`.

**Lo primero que hay que hacer no tiene nada que ver con A2A:** renombrar `A2AHttpAgentTeamTransport` o hacerlo conformante. Hoy promete un estándar que no cumple.

---

## Qué no pude verificar

- **Quién implementa A2A en producción.** No lo establecí. Sé que los tres arneses no, y sé que no usé la lista de partners. Es el hueco más grande de este informe.
- **La fecha del Governing Board (2026-08-04).** La tomo del informe de hoy citado; no abrí el issue #37 yo.
- **`agntcy/slim`**: no lo cloné ni lo leí. Descartado por inferencia del nombre y las ramas, que es más débil que el resto del informe.
- **Conformidad real de las implementaciones contra la spec.** No corrí nada (regla del encargo, correcta). Todo lo de A2A es *documentado*; nada es *verificado en ejecución*.
- **Encontré un checkout local, ajeno a este repo, con una implementación de A2A v2 (rutas de servidor y tests de streaming).** No lo audité ni lo cité por archivo: es de otro proyecto y está fuera del alcance. Queda como pista de que sí existen implementaciones reales, no como evidencia.

## Estado de cada afirmación

- **Documentado** (cita de spec o de código leído): licencias, gobernanza/TSC, versión y changelog, registro sin API estándar, autorización implementation-specific, firma `MAY`, semántica de verificación, relación con MCP, ausencia total en los tres arneses, identidad propietaria de codex, muerte de ACP, no-conformidad de `A2AHttpAgentTeamTransport`, precedente del freeze, contenido de ADR-230.
- **En el código sin documentar**: `codex-rs/agent-identity/` no tiene doc comments de módulo (`grep '^//!'` → vacío); su propósito se infiere de los nombres de las funciones públicas.
- **Lo dice un informe y no lo confirmé**: fecha del Governing Board.

---

## Qué de este encargo era falso

El encuadre — *"A2A es la capa que nos falta"* — **no se sostiene**, por dos motivos independientes, y el operador tenía razón en pedir que se lo refutara.

1. **A2A no resuelve la capa que falta**, la delega. Registro sin API estándar, autorización implementation-specific, firma opcional que prueba procedencia y no capacidad. Adherir nos daría vocabulario, no mecanismo.
2. **No hay con quién hablarlo.** Ninguno de los tres arneses expone nada. Y el único que construyó directorio + admisión (codex) lo hizo cerrado contra su propio vendor.

Y la premisa fáctica que sostenía el encargo —cero menciones en el repo— era falsa por 47 archivos, incluyendo un ADR con la decisión de rechazo ya escrita y un informe de hoy con el estado de gobernanza ya verificado. **La medición que el encargo presentaba como evidencia era la parte más débil del encargo.**

El resultado útil, entonces, no es "adoptemos A2A" ni "no sirve": es que **la conclusión del trabajo de transporte de hoy queda confirmada por descarte** —falta directorio y admisión, y no hay estándar que nos lo regale— más un bug concreto de nomenclatura en `packages/agent-lifecycle/lib/agent_team_transport.py:157` que hoy le miente al que lee el árbol de módulos.
