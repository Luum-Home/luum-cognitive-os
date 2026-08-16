# Nombres que prometen un protocolo — censo, decisión y barrido

**Fecha:** 2026-08-15
**Disparador:** `docs/06-Daily/reports/investigacion-a2a-interop-2026-08-15.md` §4 dejó
un hallazgo accionable: `A2AHttpAgentTeamTransport` no implementa A2A.
**Alcance:** arreglar ese nombre y barrer el repo buscando **la forma**, no el caso.
**Commits:** `9acb76ee0` (código + tests), `91cc13504` (ADR-233), este informe.

---

## 1. Lo que se verificó antes de tocar nada

Las dos mitades de la premisa se comprobaron por separado, porque el encargo pedía
distinguirlas.

**El docstring era honesto.** Decía textualmente *"Minimal HTTP JSON adapter for
A2A-style agent messages"* y *"executable against any HTTP A2A bridge/gateway"*.
El calificador `-style` estaba puesto. Es un docstring que no miente, aunque
*"any HTTP A2A bridge/gateway"* sí promete de más: un bridge A2A no acepta este
sobre sin traducirlo.

**El nombre de la clase no era honesto.** El cuerpo que POSTeaba:

```python
body = {
    "schema_version": SCHEMA_VERSION,
    "transport": "a2a-http",
    "team_name": self.team_name,
    "recipient": session_id,
    "message_part": payload,
}
```

Ninguno de esos campos existe en A2A. No hay framing JSON-RPC 2.0, no hay agent
card, no hay `messageId`/`role`/`parts`/`contextId`/`taskId`. Confirmado leyendo
el archivo, no el informe previo.

`ADR-230` también se leyó: el rechazo está escrito y con motivo —
*"Adopt Google A2A protocol directly. Apache 2.0 OK; over-engineered for our scope
(designed for cross-org task delegation). Adopt the `referenceTaskIds` shape; skip
the rest"* (`ADR-230-handoff-envelope-and-cycle-deduplication.md:233`). La brecha es
una decisión tomada, no deuda pendiente. Por eso el arreglo es el nombre, no el
protocolo.

---

## 2. El censo de consumidores, con su comando

```bash
git grep -n 'A2AHttpAgentTeamTransport'          # sin filtros de extensión
git grep -n 'agent_team_transport'
```

**5 archivos** mencionan la clase (`git grep -l 'A2AHttpAgentTeamTransport' | wc -l`):

| Archivo | Qué es | ¿Consumidor real? |
|---|---|---|
| `packages/agent-lifecycle/lib/agent_team_transport.py:157` | la definición | — |
| `scripts/cos-team:22,243` | **importa y construye la clase** | **sí, código ejecutable** |
| `tests/unit/test_agent_team_transport.py:32,73` | test unitario | sí |
| `docs/02-Decisions/adrs/ADR-233-...md:79` | contrato documentado | doc |
| `docs/06-Daily/reports/investigacion-a2a-interop-2026-08-15.md` | el informe previo | doc |

Más un consumidor por CLI, que el grep del nombre de clase no ve:
`tests/behavior/test_cos_team_cli.py:270` ejercita `transport-send --backend a2a`.

### El dato duro del encargo era falso

El encargo afirmaba: *"`packages/agent-lifecycle/lib/agent_team_transport.py` **no lo
importa ningún código** — sólo aparece en docs y manifiestos. Verificalo."*

Verificado: **es falso.** `scripts/cos-team:22` lo importa y `scripts/cos-team:243`
lo instancia. Es un ejecutable **kebab-case sin extensión** — exactamente la clase de
archivo que el propio encargo advertía que un `--include='*.py'` no ve. El encargo
cometió el error contra el que avisaba.

La confusión tiene una causa concreta y verificable: los audits de aspiracionalidad
lo cuentan como `callers=0`.

```
docs/06-Daily/reports/aspirational-audit-2026-07-09.md:339
| lib/agent_team_transport.py | ON_DEMAND | callers=0, has_test=True | covered by test — legit sleeper (imported by test only) |
```

Tres audits seguidos (2026-05-08, 2026-05-20, 2026-07-09) dicen `callers=0`. **Los
tres se equivocan por la misma razón**: `scripts/cos-team` no termina en `.py`. Es
decir, el "hallazgo por sí mismo" que el encargo esperaba —un transporte sin
llamador— no existe; el hallazgo real es el opuesto y es peor: **un contador de
llamadores que no ve los ejecutables kebab-case, repetido en tres audits**.

Lo que sí es cierto del encargo: **en manifiestos el nombre de la clase no aparece
nunca**. `git grep -niE 'a2a' -- manifests/ .ai/` devuelve sólo falsos positivos
(`sha256: ...a2a...` en `agentic-primitive-registry.lock.yaml`). Los manifiestos
referencian la *ruta del archivo*, no la clase — no hubo nada que corregir ahí.

---

## 3. La decisión: renombrar, y por qué

**Se renombró.** `A2AHttpAgentTeamTransport` → `HttpJsonAgentTeamTransport`.

El motivo es el que el encargo adelantaba y la evidencia confirmó: **el docstring lo
lee quien abre el archivo; el nombre lo lee quien escribe la llamada.** El sitio de
uso era `scripts/cos-team:243`, y ahí no hay docstring a la vista — hay un nombre que
dice A2A. El próximo que lea el árbol de módulos iba a creer que la interop ya estaba
resuelta.

Nombre elegido: dice el mecanismo real (HTTP + JSON) y no promete nada que el cuerpo
no haga.

### Lo que se cambió más allá de la clase

Renombrar sólo la clase era el segundo verde barato que el encargo marcaba. El
alcance real de la mentira era más grande que el nombre:

| Superficie | Antes | Después | Motivo |
|---|---|---|---|
| clase | `A2AHttpAgentTeamTransport` | `HttpJsonAgentTeamTransport` | el nombre en el sitio de uso |
| campo del sobre | `"transport": "a2a-http"` | `"http-json"` | lo que ve el receptor HTTP |
| `TransportSendResult.backend` | `"a2a"` | `"http-json"` | lo que ve el operador en la salida |
| CLI | `transport-send --backend a2a` | `--backend http-json` | **el peor de todos**: prometía mandar A2A |
| ayuda de `--endpoint` | `"A2A HTTP endpoint"` | `"HTTP endpoint ... (COS envelope, not A2A)"` | idem |

### Lo que deliberadamente NO se cambió

`transport-plan --backend a2a` **se queda**. No es una implementación: es un
descriptor con `status: "upgrade_target"` y `dependency_policy:
"opt-in-only; no A2A SDK dependency in default COS install"`. Nombrar un destino de
migración con el nombre del estándar al que se migraría es correcto — es lo que el
operador busca cuando pregunta "¿y A2A?".

Lo que faltaba ahí era que dijera la brecha en la misma salida. Se agregó al
`compatibility` del plan:

```bash
cos-team --json transport-plan --team release --backend a2a \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['transport_plan']['compatibility']['conformance'])"
# none - COS ships no A2A-conformant adapter (no JSON-RPC, no agent card);
# ADR-230 rejected adopting A2A directly. This mapping is a migration target, not an implementation.
```

El campo no es metadata muerta: lo emite el CLI y lo asegura
`tests/unit/test_agent_team_transport.py`.

### El test que impide que vuelva a pasar

El rename solo no evita la recaída. Se agregó una aserción que falla si el sobre
vuelve a tener nombre de A2A sin serlo:

```python
assert not {"messageId", "role", "parts", "contextId", "jsonrpc"} & set(received)
```

Si alguien implementa A2A de verdad, ese test rojo es la señal de que además hay que
renombrar la clase — en la dirección contraria, y con razón.

### Verificación

```bash
.venv/bin/pytest tests/unit/test_agent_team_transport.py \
  tests/behavior/test_cos_team_cli.py \
  tests/red_team/portability/test_agent_team_transport.py \
  tests/contracts/test_promotion_propose_only.py -q
# 14 passed in 36.15s

.venv/bin/python scripts/cos-team --project-dir <tmp> transport-send --backend a2a ...
# error: argument --backend: invalid choice: 'a2a' (choose from nats, http-json)
```

---

## 4. El barrido: ¿hay otros nombres que prometen un estándar?

La pregunta era por la forma, no por el caso. Dos barridos.

**Nombres de clase/función que llevan un estándar:**

```bash
git grep -nE '^[[:space:]]*(class|def|func|type)[[:space:]]+[A-Za-z_]*(A2A|MCP|Mcp|JsonRpc|JSONRPC|OpenAPI|OpenApi|OAuth|Oauth|SAML|Saml|GRPC|Grpc|OTLP|Otel|SPDX|Spdx|CloudEvent|JWT|Jwt|LSP)' \
  -- '*.py' '*.go' '*.ts' '*.js' '*.rs'
```

**Gotcha de la herramienta, medido:** la primera pasada usó `\s` en vez de
`[[:space:]]` y devolvió **cero resultados, incluido el caso conocido**. `git grep -E`
usa ERE POSIX, donde `\s` no es una clase. Un barrido que devuelve cero y no se
contrasta contra un positivo conocido es un falso verde. Por eso la corrida real
incluye el control:

```bash
git grep -nE '^class A2A' -- '*.py'   # control: debe devolver 1
```

**Nombres de archivo:**

```bash
git ls-files | grep -iE '(a2a|jsonrpc|json_rpc|openapi|oauth|saml|grpc|otlp|opentelemetry|spdx|cloudevent|jwt|_mcp|mcp_|mcp-|-mcp)'
```

### Resultado: 13 candidatos, 12 honestos, 1 mentiroso (el ya arreglado)

| Nombre | Ubicación | Veredicto | Evidencia |
|---|---|---|---|
| `A2AHttpAgentTeamTransport` | `packages/agent-lifecycle/lib/agent_team_transport.py:157` | **MENTÍA** — arreglado en `9acb76ee0` | sobre propio, sin JSON-RPC ni agent card |
| `_FastMCPCompat` | `packages/mcp-server/cos_mcp.py:69`, `packages/advisor-mcp/advisor_server.py:66` | **honesto, y es el patrón a copiar** | su `run()` hace `raise RuntimeError("fastmcp is required to run the MCP server transport")`. Se niega explícitamente a fingir que es un transporte |
| `mcp = FastMCP(...)` | `packages/mcp-server/cos_mcp.py:335`, `advisor_server.py:92` | honesto | `from fastmcp import FastMCP` — habla MCP de verdad vía librería |
| `MCPClient` (Protocol) | `packages/agent-service/src/.../runtime_lab/mcp.py:18` | honesto | es un `Protocol` que declara la firma de un cliente inyectado, no una implementación |
| `MCPToolWrapper` | idem `:23` | honesto | el nombre dice *Wrapper*; delega en `self.client.call_tool(...)`. El docstring aclara que no reemplaza la config MCP del host |
| `FakeMCPClient` | `packages/agent-service/tests/test_runtime_lab.py:106` | honesto | `Fake` en el nombre |
| `FakeMCP` | `tests/unit/test_cos_mcp_otel.py:33` | honesto | idem |
| `_FastMCPStub` | `tests/unit/test_safe_engram_contract.py:432` | honesto | `Stub` en el nombre |
| `MCPServer` (dataclass) | `cos_lib/manifest_loader.py:75` | honesto | describe una *entrada de manifiesto* de un server MCP, no un server |
| `MCPThreadBridge` | `cos_lib/mcp_thread_bridge.py:30` | honesto | puentea hilos para llamadas MCP; no dice implementar MCP |
| `normalizeSPDX` | `cmd/cos/internal/security/license.go:80` | honesto | normaliza identificadores SPDX, que es exactamente lo que SPDX es (una lista de identificadores) |
| `TestMcpScanHook*` | `tests/behavior/test_security_integrations.py:42,65` | honesto | tests de un hook llamado `mcp-scan` |
| `primitive_coverage/adapters/openapi.yaml` | — | honesto | es un adapter que **busca** archivos `openapi*.yaml` por glob; no pretende parsear la spec |

**Conclusión del barrido:** el repo está limpio en esta dimensión salvo el caso ya
arreglado. Eso no debilita el hallazgo, lo refuerza: `A2AHttpAgentTeamTransport` era
la única excepción a una convención que el resto del código respeta sin que nadie la
haya escrito. El contraejemplo útil es `_FastMCPCompat`, que ante la ausencia del
protocolo **lanza una excepción en vez de degradar en silencio** — la forma correcta
de nombrar algo que podría no ser lo que dice.

**Límite de este barrido, dicho de frente:** encuentra nombres que *contienen* el
token de un estándar. No encuentra el caso inverso —algo que implementa un estándar y
no lo dice— ni nombres que prometen un estándar con otra palabra (`Bridge`,
`Gateway`, `Adapter` sin el token). No se buscó eso.

---

## 5. Deuda encontrada de paso (NO arreglada, con evidencia)

Dos cosas que se cruzaron y quedan escritas en vez de arregladas, porque están fuera
del alcance de este encargo:

**a) `callers=0` es un contador ciego a los ejecutables sin extensión.**
Tres audits consecutivos reportan `lib/agent_team_transport.py | callers=0 | legit
sleeper (imported by test only)` mientras `scripts/cos-team` lo importa. El error no
es de este archivo: es del contador. Cualquier otro módulo cuyo único llamador sea un
ejecutable kebab-case está mal clasificado hoy.

**b) El sha256 del lock de `scripts/cos-team` ya estaba desactualizado antes de este
cambio.**

```bash
shasum -a 256 scripts/cos-team
# b5a34db4469ddd6355736efd2e62a09cb4e2946068f05a929d51e860e7a517be
grep -A9 'id: scripts/cos-team' manifests/agentic-primitive-registry.lock.yaml | grep sha256
#   sha256: 211a37d5212e55f8b584399ed5e7f3b7cd6a0d2f19c7ef1c71ab7419d8e78036
```

Divergían **en HEAD, antes de tocar el archivo**. Ningún gate lo enforcea:
`tests/contracts/test_promotion_propose_only.py` pasa igual (verificado en la corrida
de 14 tests). Un lock que nadie chequea es un supresor que no suprime nada.

---

## 6. Correcciones a las premisas del encargo

1. **"`agent_team_transport.py` no lo importa ningún código — sólo docs y
   manifiestos"** → **FALSO**. `scripts/cos-team:22` lo importa y `:243` lo
   instancia. El encargo cayó en el mismo pozo que advertía dos párrafos antes: el
   ejecutable es kebab-case sin extensión. Consecuencia práctica: renombrar **no**
   era gratis, tocaba una superficie de CLI.

2. **"Es un hallazgo por sí mismo: un transporte sin llamador"** → **no existe ese
   hallazgo**. El hallazgo real es el inverso: sí tiene llamador, y **tres audits
   seguidos dicen `callers=0`** porque el contador no ve ejecutables sin `.py`.

3. **"El docstring es honesto; el nombre no"** → **CONFIRMADO**, con un matiz. El
   docstring decía `A2A-style` (correcto), pero también *"executable against any HTTP
   A2A bridge/gateway"*, que promete de más: ningún bridge A2A acepta este sobre sin
   traducir. Se reescribió entero.

4. **"El nombre aparece en manifiestos"** → **FALSO para la clase**. `git grep -niE
   'a2a' -- manifests/ .ai/` devuelve sólo colisiones dentro de hashes sha256. Los
   manifiestos referencian la ruta del archivo. No hubo nada que corregir ahí.

5. **"~22% de `lib/*.py` serían symlinks según un gotcha que hoy se midió falso
   (`lib/` no existe en el root; es `cos_lib/`)"** → **la refutación del encargo es
   correcta pero la conclusión que sugiere es peligrosa**. `cos_lib/` está lleno de
   symlinks: `ls -la cos_lib/agent_team_transport.py` →
   `-> ../packages/agent-lifecycle/lib/agent_team_transport.py`. Editar el archivo
   packaged fue lo correcto; editar `cos_lib/` habría escrito en el mismo inodo
   (`md5` idéntico, verificado). El gotcha estaba mal *de nombre*, no de fondo.

6. **Presupuesto de ~40 tool calls** → se usaron ~35. La restricción se respetó, pero
   no era la que apretaba: lo caro fue el control del regex, no las llamadas.

7. **Lo que el encargo acertó y conviene decirlo:** la advertencia sobre
   `--include='*.py'` y ejecutables kebab-case era exactamente el error que había que
   evitar (aunque el propio encargo lo cometiera en su dato duro), los tres verdes
   baratos estaban bien identificados, y "renombrar es lo correcto" resultó ser la
   salida correcta por el motivo que daba.

---

## 7. Archivos tocados

- `packages/agent-lifecycle/lib/agent_team_transport.py` — clase renombrada, docstring
  reescrito, wire fields, `compatibility.conformance`
- `scripts/cos-team` — import, construcción, `--backend`, textos de ayuda
- `tests/unit/test_agent_team_transport.py` — rename + guarda anti-recaída
- `tests/behavior/test_cos_team_cli.py` — `--backend http-json`
- `docs/02-Decisions/adrs/ADR-233-cross-session-agent-team-file-ipc.md` — Slice E
  corregida
