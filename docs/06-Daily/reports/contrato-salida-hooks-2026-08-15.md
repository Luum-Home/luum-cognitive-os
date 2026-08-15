# Contrato de salida de los hooks — qué consume el host, y qué de esto estaba mal contado

**Fecha**: 2026-08-15
**Alcance**: forma de salida de `additionalContext` en los hooks de este repo, y
por qué el bloque inyectado no llega a ningún subagente.
**Contrato**: `manifests/claude-code-hooks-schema.yaml`
**Runbook**: `docs/05-Methodology/runbooks/hooks-additional-context-shape-2026-08-15.md`

---

## Veredicto en una línea

Hay **una sola forma válida** —`hookSpecificOutput.additionalContext`, con
`hookEventName` al lado— y el injector ya la usa. El bloque no llega igual,
porque está registrado con `"async": true`. Son **dos defectos distintos**, y el
encargo los tenía fusionados en uno.

---

## El contrato, con fuente

Todo lo de abajo sale de `https://code.claude.com/docs/en/hooks.md`, consultado
el 2026-08-15 con `curl -sSL` (272.682 bytes) y grepeado localmente. Se grepeó
en vez de resumir por un motivo concreto: la página HTML se trunca antes de la
sección que contesta la pregunta, y **tres pasadas de fetch resumido informaron
con seguridad que la respuesta "no estaba en el contenido"**. Estaba: a 3.250
líneas del principio.

### 1. `additionalContext` va anidado. Siempre.

> "Return `additionalContext` inside `hookSpecificOutput` alongside the event
> name" — sección *Add context for Claude*.

No existe la forma plana. Para ningún evento.

### 2. Por qué la forma plana falla en silencio

Esto es lo que convierte un error de tipeo en un defecto invisible. El host
decide si stdout es JSON o texto según **el primer carácter**:

> "Whether Claude Code reads your stdout as JSON output or as plain text
> depends on its first character, ignoring leading whitespace" — sección
> *Exit code 0*.

- Empieza con `{` → se parsea como JSON. Si **no** es JSON válido, se trata como
  texto plano.
- Empieza con otra cosa → texto plano.

`{"additionalContext": "..."}` empieza con `{` **y es JSON válido**. Entonces se
parsea como salida estructurada, no encuentra ningún campo reconocido, y se
descarta. No hay error, no hay warning, y **no hay caída a texto plano** — ese
rescate solo existe para JSON inválido. Un hook con la forma plana sale 0,
imprime JSON impecable, y no entrega nada.

### 3. Dónde aterriza el recordatorio, por evento

| Eventos | Punto de inserción |
|---|---|
| `SessionStart`, `Setup`, `SubagentStart` | al inicio de la conversación, **antes del primer prompt** |
| `UserPromptSubmit`, `UserPromptExpansion` | junto al prompt enviado |
| `PreToolUse`, `PostToolUse`, … | junto al resultado de la tool |
| `Stop`, `SubagentStop` | al final del turno |

### 4. `async: true`

> "Async hooks can't block or control Claude's behavior: response fields like
> `decision`, `permissionDecision`, and `continue` have no effect, because the
> action they would have controlled has already completed." — sección *Run hooks
> in the background*.
>
> "When the script finishes, its output is delivered on the next conversation
> turn."

**Acá hay que ser preciso, y el manifest lo es.** La doc nombra
`decision`/`permissionDecision`/`continue` como inertes bajo async. **No nombra
`additionalContext`.** Lo que sí dice es el punto de entrega —"the next
conversation turn"— y, por separado, que `SubagentStart` inserta "before its
first prompt". Las dos no se satisfacen juntas: un hook que vuelve después de
que la conversación del subagente empezó no puede insertarse antes de su primer
prompt.

Por eso el manifest registra async-sobre-SubagentStart como **CONTRA-INDICADO
por inferencia**, no como inerte-por-documentación. La distinción es
deliberada: es la diferencia entre una cita y una deducción, y el próximo que
lea el archivo tiene derecho a saber cuál de las dos está mirando. Lo que lo
zanjaría: aplicar el Paso 2 del runbook y volver a correr el chequeo de llegada.

---

## Qué se midió, con el comando

### Llegada: 0 de 149

```bash
python3 scripts/check_subagent_context_arrival.py
# marker           : 'Phase: `reconstruction`'
# transcripts      : 149
# genuine arrivals : 0
# exit 1
```

### Emisión: correcta, 10.253 bytes

```bash
echo '{"prompt":"test","hook_event_name":"SubagentStart"}' \
  | CLAUDE_PROJECT_DIR=$PWD bash hooks/subagent-context-injector.sh
# top-level keys: ['hookSpecificOutput']
# hookSpecificOutput keys: ['hookEventName', 'additionalContext', 'permissionDecision']
# ctx len: 9745  · contiene el template completo
```

**Emisión perfecta, llegada cero.** Ése es el defecto entero en dos líneas.

### Censo de formas

| Hook | Evento | Forma | Estado |
|---|---|---|---|
| `subagent-context-injector.sh` | SubagentStart | anidada ✅ | **no llega** — `async: true` |
| `cross-session-peer-context.sh` | UserPromptSubmit | **plana ❌** | descartada en silencio |
| `agent-message-inbox-context.sh` | UserPromptSubmit | **plana ❌** | descartada en silencio |
| `eas-validation-gate.sh` | Stop | anidada, **sin `hookEventName`** | objeto incompleto |
| otros 11 | varios | anidada ✅ | ok |

---

## Qué del encargo era falso

Se recontó todo. Cinco correcciones.

**1. "0 de 145" → el comando da 1 de 147, y hoy 149.** El literal aparecía en
un transcript, en la **línea 64, mensaje del assistant**: otro agente lo
escribió al reportar sobre el template. No era una inyección. El comando del
encargo cuenta *ocurrencias del string en el archivo*, y un brief que cita el
marcador o un agente que lo escribe cuentan como falso positivo. El chequeo que
quedó en el repo distingue llegada de mención parseando el JSONL y exigiendo que
el marcador esté en un bloque de system-reminder, no en un turno de assistant.
Con ese criterio el conteo es **0 de 149** — la conclusión del encargo era
correcta, su medición no.

**2. "el template tiene `Phase: {{phase}}` sin interpolar" — casi.** El literal
real es ``Phase: `{{phase}}`.`` con backticks alrededor del placeholder. Buscar
la forma del encargo hace que el chequeo reporte "el template ya no trae el
placeholder" sobre un template que lo trae perfecto. Costó una iteración.

**3. "otros dos hooks usan la otra [forma]" — dos con la forma plana, pero hay un
tercero roto de otra manera.** `eas-validation-gate.sh` anida bien y omite
`hookEventName`, que el host exige para rutear `hookSpecificOutput`. Apareció
como falso positivo del detector de forma plana; es un defecto real de otra
familia. Y hay un **cuarto**: `skill-md-routing-validator.sh` tiene el header
`# Async: true` contra un registro sin `async` — la contradicción header/registro
que el encargo atribuía solo al injector existe en dos hooks, en direcciones
opuestas.

**4. "`docs.claude.com` hace 301 a `code.claude.com`" — en algunos prefijos, y en
el sentido inverso en otros.** `code.claude.com/docs/en/sdk/sdk-typescript` hace
301 a `docs.claude.com/en/docs/agent-sdk/typescript`. Ninguno de los dos hosts
es canónico para todo. Lo que sí sirve: el sufijo `.md` en `code.claude.com`
devuelve la fuente completa sin truncar.

**5. El "verde barato" que el encargo señalaba resultó ser la respuesta
correcta** — pero por un motivo que solo la doc podía dar. Apretar el helper a la
forma del injector era efectivamente adivinar mientras la fuente no estuviera
leída. Leída la fuente, esa forma es la que el host consume. **El encargo tenía
razón en prohibir el atajo y razón en sospechar del resultado; lo que no podía
saber es que el atajo llegaba al mismo lugar.** La diferencia entre las dos
rutas no es el diff: es que ahora hay una cita, y el helper falla con un mensaje
que explica por qué.

**Lo que el encargo tenía bien, y era lo importante**: el aviso de que el canal
nativo **sí** entrega `rules/RULES-COMPACT.md`. Se confirmó — 83 de 147
transcripts lo mencionan. Eso descartó de entrada la hipótesis "el canal está
muerto" y mandó la investigación al payload específico, que es donde estaba.

---

## La capa 3: qué se decidió y por qué

Un test unitario no puede probar llegada. Las tres salidas del encargo, y lo que
se hizo:

**Legítima A — tomada.** `TestMandatoryRulesDelivery` → `TestMandatoryRulesEmission`.
Sus mensajes ya no dicen "arrive". La clase afirmaba transporte y medía
`result.stdout`, que es la salida del hook **una capa antes** de que el host
decida consumirla. Costó un rename y una docstring.

**Legítima B — tomada.** `scripts/check_subagent_context_arrival.py`, exit
0/1/2, contra transcripts reales. **No** es un caso de pytest, a propósito: lee
`~/.claude/projects` y su resultado depende de qué corrió en esta máquina. En CI
sería un skip permanente o un mock.

**Ilegítima — no tomada.** Mockear el transcript y assertear que el mock
contiene lo que el mock puso. Habría dado verde probando nada, que es
exactamente el modo de falla que originó toda esta investigación.

El helper que aceptaba las dos formas era el mismo error una capa más abajo: un
supresor que no suprimía nada, adentro del test que existe para descartar ese
error. Ahora rechaza la forma plana con un mensaje que cita el contrato.

---

## Estado de entrega

| Artefacto | Estado |
|---|---|
| `manifests/claude-code-hooks-schema.yaml` | escrito, 2 fuentes con fecha |
| `tests/hooks/test_subagent_context_injector.py` | helper apretado, clase renombrada — 18/18 |
| `tests/contracts/test_claude_code_hooks_schema_conformance.py` | 9 tests, 4 baselines exactos |
| `scripts/check_subagent_context_arrival.py` | exit 1 hoy (0 de 149) |
| Parche de `hooks/**` | `git apply --check` OK, 3 archivos |
| Fix de `async` | **pendiente de operador** — es el que arregla el 0 de 149 |

Los cuatro baselines de la suite de conformidad son de coincidencia exacta, no
de umbral: si algo se arregla y queda listado, el test falla pidiendo que se
saque. Un baseline por encima de la realidad es colchón donde una regresión
futura entra gratis.
