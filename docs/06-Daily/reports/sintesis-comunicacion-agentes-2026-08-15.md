# Síntesis — comunicación subagente↔principal y sesión↔sesión: lo que construimos contra lo que existe

- Fecha: 2026-08-15
- Insumos: `juez-interno-comunicacion-2026-08-15.md` (midió este repo) y
  `juez-externo-comunicacion-agentes-2026-08-15.md` (midió el estado del arte).
  Se produjeron sin verse.
- Alcance: el cruce. No arreglé nada, no toqué `hooks/`, `rules/` ni ningún
  manifiesto. No recomiendo adoptar nada de terceros.

---

## 0. La pregunta del operador, contestada primero

> *"...nosotros armamos algo medio por arriba, queriendo formar un estándar, y tal vez
> está mal porque ya los arneses lo resuelven, por lo que por ahí estamos
> sobre complejizando las cosas."*

**La sospecha es correcta en una mitad y falsa en la otra, y las dos mitades están
dentro del mismo eje.** No se separan por arnés, como planteaba el juez externo: se
separan por **qué objeto**.

- **Pasar texto entre sesiones**: sí, el arnés lo resuelve, y con el contrato más
  detallado que aparece en los dos informes. Nuestra versión de eso no entrega.
  Ahí la sospecha del operador es acertada.
- **Coordinar escrituras sobre un checkout compartido**: no lo resuelve nadie, y no
  puede resolverlo el mecanismo nativo **por su propio contrato** — la doc de Claude
  Code dice que un mensaje es *"never conversation history or files"* y que no cambia
  configuración. Nuestra versión de eso es lo único de los dos ejes que pasa las
  cuatro preguntas de ADR-342. Ahí la sospecha es falsa, y sacarlo costaría un
  postmortem ya escrito.

Y en el eje 1 la respuesta no es ninguna de las dos: **usamos el punto de extensión
nativo del arnés y lo configuramos mal**. No es reinvención ni es hueco. Es un flag.

---

## 1. Dónde coinciden, y por qué es lo más firme del lote

### 1.1 La entrega es el eslabón que nadie verifica (firme, y es acuerdo positivo de los dos lados)

Los dos informes, con instrumentos que no se parecen —uno leyó doc oficial de tres
fabricantes, el otro leyó ledgers y transcripts de este checkout—, llegan al mismo
lugar: **emitir no es entregar, y casi nadie mide la segunda mitad.**

- **Afuera**: el único arnés con contrato publicado gasta ese contrato justamente en
  nombrar las formas de **no** entregar (`Delivered` / `Held` / `Refused`), y la
  única frase sobre garantías es la que la niega. Reproducido con el comando que el
  informe externo publica:

  ```bash
  curl -s https://code.claude.com/docs/en/cross-session-messaging.md \
    | grep -inE 'order|ordering|sequence|fifo|at-least-once|exactly-once|guarantee'
  # 1 solo hit, línea 66: "Delivery isn't guaranteed in every configuration"
  ```

- **Acá**: construimos la emisión y nunca medimos la llegada. `stdout_bytes` prueba
  que el hook escribió; nada prueba que alguien leyó. Reproducido:

  ```bash
  # 145 transcripts de subagente, 0 portadores del bloque inyectado
  ```
  (censo completo en §9; el juez interno publicó 144/0, hoy da 145/0 — deriva de un
  transcript, el mío)

**Por qué este acuerdo es firme y no de los débiles.** La síntesis hermana marcó que
un acuerdo entre *evidencia positiva* y *ausencia* vale menos. Éste no es de ésos:
las dos mitades son medición positiva. La doc **dice** que la entrega puede fallar
(11 menciones de los tres desenlaces, verificado), y el censo de transcripts **mide**
un cero, no "no encontré". Los dos afirman algo, no dejan de encontrarlo.

### 1.2 Nadie tiene protocolo estructurado entre agentes, y nosotros tampoco

Segundo acuerdo desde extremos opuestos:

- Externo: *"Plain text only"*. Los mensajes de protocolo estructurados
  (`shutdown_request`, `plan_approval_response`) existen **solo** adentro de agent
  teams, que está detrás de una variable experimental. Ningún arnés promete orden de
  mensajes. A2A, el estándar que sí define ciclo de vida de tarea, **no lo implementa
  ningún arnés de coding**.
- Interno: no hay `SubagentStop` registrado, no hay preemption, y
  `agent-control-inbound-guard.sh` es *"un semáforo, no un freno"* — el subagente se
  autoconsulta la señal en su próximo tool call.

Los dos describen el mismo techo: lo que existe es texto plano, best-effort, sin
orden. Cualquier diseño nuestro que asuma entrega ordenada de mensajes estructurados
está apoyado en algo que nadie promete, ni afuera ni acá.

### 1.3 El punto que ninguno pudo ver solo: usamos un punto de extensión que Codex documenta

Esto es del cruce y es el hallazgo que cambia la lectura del eje 1.

El juez externo documenta, con sello **[DOC]**, que Codex CLI tiene `SubagentStart` y
que *"acepta `additionalContext`, que is added as extra developer context for the
subagent"*. El juez interno midió que nuestro `hooks/subagent-context-injector.sh`
corre en `SubagentStart` y emite `additionalContext`.

**Es el mismo mecanismo.** No estamos armando un estándar por arriba del arnés en el
eje 1: estamos usando el punto de extensión que al menos dos arneses publican, y lo
tenemos registrado de una forma que lo anula. Eso reencuadra el veredicto: la
pregunta no es "¿sobra?", es "¿por qué no llega?".

---

## 2. Dónde se contradicen, y cuál tiene razón

### 2.1 La contradicción principal: ¿el arnés ya resuelve el eje 2?

**El externo dice que sí, y con el mejor contrato del informe** (§4): `ListAgents` +
`SendMessage`, socket UDS por sesión, tres desenlaces nombrados, expiry de 5 minutos,
tope de 100 retenidos y 50 en cola, dedup anti-loop, feedback al emisor,
`isolatePeerMachines`. Y en §9.4 cierra explícitamente la rama del razonamiento del
encargo: *"El antecedente no se cumple: Claude Code tiene contrato"*.

**El interno dice que nuestra capa del eje 2 es lo más vivo que tenemos** (§2.1, §2.4):
19.710 filas de eventos sobre 34 sesiones, 979 locks de edición, y la familia de
edit-locks pasando las cuatro preguntas de ADR-342 — la única del informe que las pasa.

**No promedio. Voy al dato: miden objetos distintos y los dos tienen razón sobre el
suyo.** Es la tercera vez en el día, y esta vez la línea que los separa está escrita
en la propia doc que citó el externo:

> *"A message is a piece of text one Claude writes to another, **never conversation
> history or files**"*, y *"no agent message can change a subagent's permission
> settings, `CLAUDE.md`, or configuration"*.

- El externo midió **pasaje de texto entre sesiones**. Ahí tiene razón entera: existe,
  está documentado, tiene contrato, y nuestra versión (peer-context, message-inbox)
  no entrega.
- El interno midió **coordinación de escrituras sobre un checkout compartido**. Ahí
  tiene razón entera: los edit-locks toman archivos, y el mecanismo nativo, **por su
  propio contrato**, no toca archivos ni configuración. No es que el arnés todavía no
  lo haga: es que declaró que no lo hace.

**Cuál gana para esta decisión: ninguno, porque no es una decisión.** Son dos. La
contradicción se disuelve al separar el eje 2 en sus dos objetos (§5), y la
recomendación es opuesta en cada uno: retirar el canal de texto, conservar la
coordinación de escritura.

Donde sí chocan sobre el **mismo** objeto —el canal de texto entre sesiones— gana el
externo sin discusión: el arnés tiene un contrato de veinte cláusulas, y lo nuestro
tiene dos formas JSON distintas para el mismo campo dentro del mismo repo, `async: true`,
y cero llegadas demostradas.

### 2.2 La contradicción que ninguno vio: ¿el arnés instalado tiene la feature?

El externo verificó que cross-session messaging *"requiere v2.1.224+"*, corre en
macOS/Linux, y que **se apaga sola** si variables de privacidad desactivan la
evaluación de feature flags. El interno nunca lo chequeó: midió el repo, no el
binario.

Lo medí yo, y el resultado es **incómodo y no lo cierro**:

```bash
claude --version                                  # 1.30096.5
env | grep -c CLAUDE_CODE_MESSAGING_SOCKET        # 0
env | grep -c CLAUDE_CODE_MESSAGING_TOKEN         # 0
```

El externo documenta que el socket se exporta *"a hooks y Bash como
`CLAUDE_CODE_MESSAGING_SOCKET`"*. En este proceso no está, y la cadena de versión no
está en la línea 2.1.x que el externo cita.

**No concluyo que la feature no esté disponible**, por dos razones honestas: soy un
subagente de background lanzado por el SDK y mi entorno puede estar filtrado, y una
cadena de versión distinta puede ser otro esquema de numeración, no otra cosa. Pero
**esta pregunta decide la recomendación del eje 2b**, y se contesta con un comando en
la sesión interactiva del operador. Lo dejo marcado como el chequeo que hay que hacer
antes de retirar nada (§6).

### 2.3 El interno subestimó cuánto entrega el canal nativo

El interno, en su Anexo C, cerró el verde barato "el harness ya inyecta contexto"
con este reparto:

> *"el canal nativo del harness entrega el prompt y el `CLAUDE.md` [...]; el injector
> entrega **reglas del proyecto** y sidecar de sesiones previas"*.

**La primera mitad de ese reparto no se sostiene, y lo sé en primera persona.** Este
subagente recibió, por el canal nativo y bajo el rótulo *"project instructions,
checked into the codebase"*, dos archivos de reglas del repo: `rules/RULES-COMPACT.md`
y `rules/rate-limiting.md`. El bloque del injector no llegó (soy uno de los 145
transcripts con cero).

O sea: **las reglas del proyecto ya llegan solas.** Lo que el injector aporta por
encima de lo nativo es más chico de lo que el interno calculó: `templates/agent-mandatory-rules.md`
(6.137 bytes), `templates/agent-preamble.md` (3.674) y el sidecar de engram.

Esto **no invalida** su veredicto de "coincidencia, no reinvención" —su criterio
(¿un cambio en uno obliga a tocar el otro?) sigue dando que no—, pero cambia el
tamaño del hueco, y por lo tanto el precio de dejarlo abierto. Es más chico, y sigue
siendo real: la norma `encargo-refutable` está en `agent-mandatory-rules.md` y **no
está** en lo que llega solo.

### 2.4 Una contradicción interna del repo que ninguno de los dos nombró

`hooks/subagent-context-injector.sh` está marcado `# SCOPE: both` (verificado, 9 de 9
piezas de comunicación lo están). Su carga útil, `templates/agent-mandatory-rules.md`,
abre con `<!-- SCOPE: os-only -->`.

Un hook que viaja al consumidor transportando un archivo que no viaja. Chico, pero es
del mismo género que la contradicción `SCOPE: both` vs `primitive-install-boundary.yaml`
que el interno reportó, y que la síntesis hermana encontró en su propio dominio. Tres
dominios, la misma contradicción entre manifiestos declarativos: deja de ser un
descuido y pasa a ser un patrón.

---

## 3. Dónde cada uno se metió en el terreno del otro

| Quién | Qué afirmó fuera de su dominio | Veredicto |
|---|---|---|
| **Externo** (§1, §9.3) | Plantea la bifurcación como **"apunta a un arnés" vs "apunta a varios"**, y deja que el interno elija rama | **Hedge correcto, eje equivocado.** Delegó bien la decisión, pero la variable que decide no es a cuántos arneses apunta la capa: es **qué objeto** resuelve. La misma capa, sobre un solo arnés, es duplicación en un objeto (texto) y hueco cubierto en otro (archivos). Ninguna de sus dos ramas contesta eso. |
| **Externo** (§9.4) | *"esa rama del razonamiento del encargo se cierra"* porque Claude Code tiene contrato | **Falso como cierre general.** El contrato que verificó excluye explícitamente archivos y configuración. Cierra la rama para el canal de texto y la deja abierta de par en par para la coordinación de escritura. Leído rápido, se lee como "no hay hueco", y hay uno con postmortem. |
| **Interno** (Anexo C) | *"el canal nativo entrega el prompt y el CLAUDE.md"* | **Incompleto**, ver §2.3. Entrega bastante más: también las reglas del repo. Sobreestimó el aporte marginal de la primitiva que estaba juzgando, en la dirección que la favorece. |
| **Interno** (§1.1) | Atribuye el no-arribo a `async: true` | **Hipótesis bien argumentada, no medición.** El hecho medido es 0 de 145. La causa no se probó y no se puede probar sin tocar `settings.json`, que está protegido. Ver §7.2. |

El primero es el más peligroso para la lectura del operador, porque el operador ya
llegaba con la sospecha "esto sobra" y el §9.4 del externo se la confirma en un párrafo
que en realidad habla de otro objeto.

---

## 4. Qué mide realmente el test de entrega

`tests/hooks/test_subagent_context_injector.py`, clase `TestMandatoryRulesDelivery`.

**Mide el stdout del hook. Mide emisión, no entrega.**

El mecanismo, sin ambigüedad. `_run_hook()` (líneas 21-45) hace
`subprocess.run(["bash", HOOK_PATH], ...)` y devuelve `json.loads(result.stdout)`.
`test_template_body_is_delivered_verbatim` (línea 155) toma ese objeto, le saca el
`additionalContext` y asserta `body in context`. El transporte que verifica es
**archivo del repo → stdout del proceso**. El transporte que falla es **stdout →
subagente**, y ese tramo no aparece en ninguna línea del archivo.

Su propio docstring dice: *"The template must ARRIVE intact — this tests transport,
not wording"*. Transporta, sí, hasta la boca del caño. El caño está desconectado del
otro lado.

**Corrida hoy:**

```bash
.venv/bin/python -m pytest tests/hooks/test_subagent_context_injector.py -q
# 18 passed in 1.26s
```

Dieciocho en verde, incluido el de entrega, mientras 0 de 145 transcripts llevan el
bloque. **Es el mismo error un nivel más arriba, en el test que existe para
descartarlo.**

**Y hay un segundo defecto, que no me pidieron y es peor de género.** El helper
`_additional_context()` (líneas 48-53) devuelve
`output["hookSpecificOutput"]["additionalContext"]` **y si no está, cae a
`output["additionalContext"]` de raíz**. O sea: acepta las **dos** formas JSON. Son
exactamente las dos formas que el juez interno encontró contradiciéndose entre hooks
del mismo repo (`subagent-context-injector.sh:195` anidada, `cross-session-peer-context.sh:40`
y `agent-message-inbox-context.sh:42` planas — reproducido). **Un test que acepta las
dos formas no puede fallar por usar la equivocada.** Es un supresor que no suprime
nada, en el sentido literal de la norma de la casa: da sensación de cobertura sobre
el defecto que más caro sale.

**Corolario sobre `TestContextBudget`**, misma clase de error: sus asserts miden el
mismo stdout y su justificación escrita es *"Every sub-agent pays this corpus on every
turn"*. Hoy eso es falso: ningún subagente paga nada, porque nada llega. Los 8
disparos con ≥10.162 bytes son 8 truncados de una carga que nadie recibe.

**No lo arreglé.** El arreglo, si el operador lo quiere, es un test que lea el
transcript del subagente y no el stdout del hook — que es el censo de §9, ya escrito.

---

## 5. Las celdas — la matriz aplicada, y su refutación

### 5.1 Refuto la matriz, en un punto distinto al de la síntesis hermana

Aquélla refutó su **singular** (había tres ejes, no un caso). Eso también pasa acá, y
lo aplico. Pero hay una segunda refutación, propia de este lote:

**La matriz mezcla diagnóstico con receta.** La fila del medio dice, en la misma
celda, *"algo construido que no funciona es peor que la ausencia"* (diagnóstico:
correcto, y lo uso con esas palabras) y *"sacarlo"* (receta). En el eje 1 el
diagnóstico se cumple entero y la receta es probablemente errada, porque la distancia
entre lo construido y lo que funciona **no está en la matriz**: puede ser un rediseño
o puede ser un booleano, y la celda no distingue. Filar el injector como "sacarlo"
borra el único camino que lleva reglas propias del repo, cuando el arreglo tal vez
sea un flag. Filarlo como "hueco abierto" manda a construir un canal que ya existe.

Propongo un tercer valor en el eje "nosotros lo construimos", que es el que este caso
necesita: **construido sobre un punto de extensión nativo, mal configurado**. No es
reinvención (no duplicamos: usamos el hook que el arnés publica), no es hueco (el
mecanismo existe), y no se trata con "sacar" ni con "construir" sino con **un
experimento**.

### 5.2 Eje 1 — subagente ↔ principal

Se parte en dos, porque la carga útil no es una sola cosa (§2.3).

**1a — entrada de contexto al arranque**

| | |
|---|---|
| **El ecosistema lo resuelve** | **El mecanismo, sí**: Codex documenta `SubagentStart` + `additionalContext` **[DOC]**; Claude Code entrega los archivos de instrucciones del proyecto por su canal nativo (verificado en primera persona: `rules/RULES-COMPACT.md` y `rules/rate-limiting.md` llegaron a este subagente). **La carga específica, no**: `agent-mandatory-rules.md` y el sidecar de engram no llegan por ningún canal nativo. |
| **Nosotros lo construimos** | Sí, y **no anda**: 0 de 145 transcripts, 33 disparos, **316.519 bytes emitidos al vacío**. |
| **Celda** | **Fila del medio, y hay que decirlo con esas palabras: lo construido que no funciona es peor que la ausencia.** Pero la columna correcta es *"el ecosistema resuelve el mecanismo, no la carga"*, y la receta no es "sacarlo" sino el experimento de §6. |

**Defensa de la fila del medio, con el daño concreto.** Nadie buscó lo que falta
porque tres artefactos declaran que está:

- `rules/RULES-COMPACT.md` §8: *"Delivered via `templates/agent-mandatory-rules.md`,
  the one path proven to reach every sub-agent"*. **"Proven" es falso.**
- `.ai/primitives/hooks/subagent-context-injector.json`:
  `claims_runtime_enforcement: true`. **Falso.**
- El test de entrega, verde (§4).

Y el daño está medido dos veces en el mismo día, en primera persona por dos jueces
distintos: la norma `encargo-refutable` llegó a este informe y al del juez interno
**porque una persona la escribió a mano en cada brief**. El día que se olvide, nada
avisa. Ésa es la definición operativa de "peor que nada": la ausencia sería visible,
la falla no.

**1b — mensaje al subagente en vuelo**

| | |
|---|---|
| **El ecosistema lo resuelve** | **Sí, con contrato** **[DOC]**: `SendMessage` por ID o nombre, auto-reanudación de un subagente completado, interrupción por `/tasks` o `stop_task`, y el límite duro escrito (*un mensaje nunca es aprobación, no puede cambiar permisos ni `CLAUDE.md` ni configuración*). Corroborado en primera persona: **`SendMessage` está en la lista de herramientas de este subagente ahora mismo**, y `ListAgents` no — exactamente lo que la doc dice de un subagente de background. |
| **Nosotros lo construimos** | **Casi no.** `agent-control-inbound-guard.sh` es un semáforo que el subagente se autoconsulta; no hay preemption ni mensajes entrantes. |
| **Celda** | **No lo construyas.** |

Es la celda más barata del informe. La única acción es no gastar acá, y —si el
semáforo estorba— notar que existe una versión nativa con contrato escrito.

### 5.3 Eje 2 — sesión ↔ sesión

Se parte en tres, y las tres celdas son distintas. Ésta es la parte donde forzar una
conclusión única obligaría a tirar lo que funciona.

**2a — coordinación de escritura sobre un checkout compartido** (edit-locks, `events.jsonl`, `file-write-intent`)

| | |
|---|---|
| **El ecosistema NO lo resuelve** | Y no por omisión: el contrato nativo **se excluye a sí mismo** — *"never conversation history or files"*, y un mensaje no cambia configuración. Codex no tiene eje 2 en absoluto; opencode tiene un API HTTP de plano de control, sin semántica de agente. |
| **Nosotros lo construimos y anda** | 19.710 eventos / 34 sesiones; 979 locks; los tres más recientes son los informes de esta misma tanda. Única familia que pasa las cuatro preguntas de ADR-342. |
| **Celda** | **Hueco real, cubierto.** |

**Defensa.** Es la ubicación más fuerte de las seis, y por dos motivos que ninguno de
los dos jueces tenía completos: el hueco está *declarado* por el contrato del propio
arnés (dato del externo), y la cobertura está *medida* con telemetría propia y
observada trabajando sobre esta sesión (dato del interno). Además es la única celda
del informe con **daño documentado si se saca**:
`docs/06-Daily/reports/postmortem-cross-session-collision-2026-05-05.md`, 18 KB,
titulado *"Cross-Session Branch Collision and Data Loss"*. Verificado que existe.

Límite honesto: los edit-locks **no tienen ledger propio**, así que se cuentan sus
ejecuciones (43 hoy) y no sus bloqueos. Es "instrumento honesto con nombre de gate"
hasta que lo tenga.

**2b — canal de texto entre sesiones** (`cross-session-peer-context.sh`, `agent-message-inbox-context.sh`, `cos_lib/agent_message_bus.py`)

| | |
|---|---|
| **El ecosistema lo resuelve** | Sí, y es el contrato más detallado de los dos informes: tres desenlaces nombrados, `crossSessionInbound`, default por clase de modo de permisos, expiry 5 min, topes 100/50, dedup anti-loop, feedback al emisor, `isolatePeerMachines`. **Sujeto al chequeo de §2.2.** |
| **Nosotros lo construimos y NO anda** | Forma JSON de raíz donde el host espera `hookSpecificOutput` (reproducido: `:40` y `:42` planas vs `:195` anidada), `async: true`, `inbox()` en 0, cadena de salida ausente de todo transcript salvo autocontaminación. |
| **Celda** | **Sacarlo, es peor que nada** — condicionado al chequeo de disponibilidad. |

**2c — descubrimiento de pares** (`cos_lib/session_bus.peers()`, `active-sessions.json`)

| | |
|---|---|
| **El ecosistema lo resuelve** | Sí: `ListAgents`, `/list-agents` (alias `/peers`), fila `Peer address` en `/status`, marcado `offline` de sesiones caídas **[DOC]**. Mismo condicionamiento de §2.2. |
| **Nosotros lo construimos y NO anda** | `peers()` devuelve **0** con otra sesión corriendo en este checkout; `active-sessions.json` es `{"sessions": []}` mientras el log crudo tiene 34 session_id. Reproducido hoy. |
| **Celda** | **Fila del medio.** Pero con una diferencia que lo separa de 2b: **el descubrimiento es el insumo de 2a, que sí funciona.** |

**Por qué 2c no se trata igual que 2b.** El `ListAgents` nativo descubre *sesiones del
arnés para mandarles texto*. Nuestro `peers()` descubre *sesiones que están por
escribir en este checkout*, que es lo que alimenta el aviso previo a la colisión. Los
edit-locks funcionan sin él, pero avisan **después** de que el conflicto existe;
`peers()` era el aviso de **antes**. Es una reparación sobre algo vivo, no una
primitiva suelta.

---

## 6. La recomendación, por eje, con su costo

### Eje 1 — un experimento antes que una decisión

> **No decidas la primitiva antes de decidir el flag.** Poné `async: false` en el
> bloque `SubagentStart` de `.claude/settings.json`, lanzá un subagente cualquiera, y
> volvé a correr el censo de §9. Es una edición, un agente y un comando.

`.claude/settings.json` está bajo `protected-config-write-guard`, así que la edición
es del operador, no de un agente. Los dos resultados llevan a lugares opuestos y
ninguno es caro:

| Resultado | Qué significa | Qué cuesta después |
|---|---|---|
| **Llega** | La primitiva funciona y el defecto era el registro. | Corregir tres declaraciones falsas (`RULES-COMPACT` §8 "proven", `claims_runtime_enforcement: true`, el test de §4) y reescribir el test para que mida el transcript. Barato, y devuelve una entrega automática que hoy hace una persona a mano. |
| **No llega** | El host no consume `additionalContext` de `SubagentStart` en esta versión. | Retirar el hook: se van 33 disparos diarios de latencia y 316 KB al vacío. La carga útil, si se la quiere, se muda al canal que **está probado que llega** — los archivos de instrucciones del proyecto que el arnés descubre solo (verificado: `rules/RULES-COMPACT.md` llegó acá). |

**Costo de no hacer nada, y está medido:** el orquestador sigue pegando la norma a
mano en cada brief, y el día que se olvide nadie se entera. Pasó dos veces hoy y las
dos salieron bien porque una persona se acordó.

**Segundo ítem del eje 1, costo cero:** no construyas mensajería al subagente en
vuelo. Existe nativa, con contrato, y está en la lista de herramientas de este mismo
proceso.

### Eje 2 — conservar una mitad, retirar la otra, reparar la tercera

> **Conservá 2a, retirá o congelá 2b con motivo escrito, y reparalo a 2c** — en ese
> orden de prioridad, y todo condicionado a un chequeo de un comando.

**Chequeo previo, en la sesión interactiva del operador** (no lo puedo hacer yo, §2.2):

```bash
claude --version
echo "${CLAUDE_CODE_MESSAGING_SOCKET:-AUSENTE}"
/list-agents      # o /peers
```

Si el socket está ausente y `/list-agents` no existe, **la premisa de la que cuelga
"retirar 2b" se cae**: el arnés instalado no resolvería el canal de texto, y 2b pasaría
de "reinvención rota" a "hueco disfrazado" — misma fila, otra columna, y la receta
cambia de retirar a reparar.

| Camino | Costo | Riesgo |
|---|---|---|
| **Conservar 2a (edit-locks + eventos)** | Cero. Ya corre. | Ninguno operativo. La deuda es de medición: sin ledger propio no se pueden contar bloqueos. Darle ledger es la única inversión que recomiendo en este eje, y es chica. |
| **Retirar 2b** (peer-context, inbox-context, message bus) | Operativo: **cero medible**. `inbox()` en 0, `peers()` en 0, cero llegadas demostradas, ningún postmortem que cite falta de mensajería entre sesiones. | Que el chequeo de arriba dé "no disponible" y estés sacando la única implementación. Por eso el chequeo va **antes**. |
| **Congelar 2b con motivo escrito** | Cero hoy. | Recurrente: ya consumió dos jueces y esta síntesis. Solo sirve si el motivo escrito dice **qué evento lo reactivaría** — y acá ese evento es nombrable: "cuando el arnés instalado no exponga `CLAUDE_CODE_MESSAGING_SOCKET`". |
| **Reparar 2c (`peers()` = 0)** | Una sesión de debugging. Causa no determinada por el interno: puede ser `alive_only` mirando PIDs muertos o el filtro de 1800s. | Bajo. Es reparación sobre algo vivo: devuelve el aviso *previo* a la colisión, que hoy solo se da *después*, por lock. |
| **Unificar las dos formas JSON** | Chico, pero **no es prioridad**: si 2b se retira, se va el lado plano solo. | Si se retiene 2b sin unificar, el defecto sobrevive y el test de §4 no lo va a atrapar nunca. |

**Sobre el freeze.** Nada de lo que recomiendo adopta código, patrón ni herramienta de
terceros. `manifests/external-tool-adoption-freeze.yaml` (`frozen: true` desde
2026-05-11, motivo IP) alcanza *"radar additions, new annex F documents, new entries
in `manifests/external-tools-adoption.yaml`"*, y usar una feature del arnés que ya
estamos corriendo no entra ahí. Si el operador lee el freeze más ancho que eso,
entonces apoyarse en `SendMessage`/`ListAgents` **requeriría descongelar, y ésa es una
decisión con gate propio**. Lo digo para cerrar la puerta explícitamente, no para
abrirla.

---

## 7. Qué queda sin contestar porque cada uno tenía media respuesta

1. **¿El arnés instalado tiene cross-session messaging?** El externo midió la doc, el
   interno midió el repo, **nadie midió el binario**. Yo lo medí a medias y el
   resultado es sugestivo en contra (§2.2) pero mi entorno es mal testigo. Decide la
   recomendación de 2b y se cierra con tres comandos.
2. **¿`async: true` es la causa del 0 de 145?** Nadie lo probó, y no se puede probar
   sin tocar un archivo protegido. Es la hipótesis mejor argumentada del interno y
   sigue siendo hipótesis. Un flag la cierra.
3. **¿Codex consume de verdad su `additionalContext` de `SubagentStart`?** El externo
   lo documenta **[DOC]**, nadie lo corrió. Decide si el eje 1a es portable o si el
   mecanismo es una promesa de doc en los dos arneses a la vez. Ojo con esto último:
   si Codex tampoco lo consume, el hallazgo deja de ser nuestro y pasa a ser del
   estado del arte.
4. **¿Cuánto cuesta no tener canal de texto entre sesiones?** El externo probó que el
   hueco está cubierto afuera, el interno probó que adentro no entrega, **nadie mostró
   un solo daño**. Y la asimetría es lo que decide: para 2a el daño está escrito
   (postmortem de colisión, 18 KB); para 2b no hay ninguno en 34 sesiones de log. Ésa
   asimetría, y no la elegancia de los contratos, es lo que ordena las prioridades de §6.
5. **¿Qué manifiesto gana cuando se instala?** 9 primitivas de comunicación marcadas
   `SCOPE: both` y **0** en `primitive-install-boundary.yaml` (reproducido). Es la
   misma contradicción que encontró la síntesis hermana en otro dominio y que aparece
   otra vez adentro del injector (§2.4). Tres dominios: es sistémico, y sigue sin
   resolverse con un install real, que es un experimento de un comando.

---

## 8. Qué de este encargo era falso

1. **"Ubicá el caso de cada eje en una celda"** — son cinco celdas, no dos. El eje 1
   se parte en dos (entrada de contexto / mensaje en vuelo) y el eje 2 en tres
   (escritura / texto / descubrimiento), y **caen en cuatro celdas distintas**. La
   partición no es cosmética: la del eje 2 es exactamente lo que resuelve la
   contradicción entre los dos jueces (§2.1), y forzar una celda única obligaría a
   sacar los edit-locks, que es lo único con un postmortem detrás.
2. **La matriz misma, en un punto nuevo** — mezcla diagnóstico con receta (§5.1). Su
   fila del medio diagnostica bien y prescribe mal cuando lo construido está a un flag
   de andar. Propuse un tercer valor: *construido sobre un punto de extensión nativo,
   mal configurado*.
3. **"El orquestador afirmó que la norma llegaba por el hook... es falso"** —
   **confirmado, y con evidencia que el encargo no tenía**: lo reproduje en 145
   transcripts (0), y además lo verifiqué en primera persona: recibí las reglas del
   repo por el canal nativo y **no** recibí `templates/agent-mandatory-rules.md`. La
   sección `Corrections to the brief's premises` de este informe existe porque el
   encargo la pidió a mano, igual que en el informe del juez interno.
4. **"Averiguá contra qué mide el test"** — la premisa implícita (mide el stdout) es
   correcta, y el encargo **se quedó corto**: hay un segundo defecto peor de género,
   el helper que acepta las dos formas JSON y por eso no puede fallar por usar la
   equivocada (§4). El encargo apuntaba a un nivel de indirección y hay dos.
5. **"Esta sesión publicó 19 cifras de las que reprodujeron 4"** — no aplica a este
   par, igual que en la síntesis hermana. De las cifras centrales del interno
   verifiqué 11: **11 reproducen** (5 con deriva monótona del ledger, que es
   crecimiento, no discrepancia), **0 falsas**. Del externo verifiqué su ancla
   principal (el grep de garantías sobre la doc de cross-session messaging) y
   reproduce exacto. Aplicar el prior en bloque me habría hecho desconfiar del 145/0,
   que es el dato más firme del lote.
6. **"~50 tool calls"** — usé 22, de las cuales 11 fueron verificación de cifras. El
   presupuesto no fue la restricción.

---

## 9. Comandos para rehacer esta síntesis

Todos read-only. Ningún archivo de `hooks/`, `rules/`, `manifests/` ni
`.cognitive-os/` fue modificado.

```bash
# --- EJE 1: la medición que decide (0 de 145) ---
D="$HOME/.claude/projects/$(pwd | tr '/.' '--')" python3 - <<'PY'
import json,glob,os
D=os.environ['D']
files=glob.glob(D+"/*/subagents/*.jsonl")
marker='MANDATORY PROJECT RULES (injected by subagent-context-injector)'
hits=[]
for f in files:
    for l in open(f, errors='replace'):
        l=l.strip()
        if not l: continue
        try: r=json.loads(l)
        except Exception: continue
        if (r.get('type')=='attachment' or (r.get('type')=='user'
            and isinstance(r.get('message',{}).get('content'),str))) and marker in json.dumps(r):
            hits.append(f); break
print("transcripts:",len(files),"hits:",len(hits))          # 145 0
raw=[f for f in files if marker in open(f,errors='replace').read()]
print("raw sin filtro:",len(raw))                            # 4 — todas autocontaminación
PY

# el raw creció de 1 a 4 en unas horas, y ninguna es entrega: las 4 son tool_use/tool_result
# propios de agentes que grepearon el marcador. Confirma la trampa 5 del Anexo B del interno:
# el número crudo mide cuántos midieron, no cuántos recibieron.

# registro vs header: la contradicción
python3 -c "import json;print(json.load(open('.claude/settings.json'))['hooks']['SubagentStart'][0]['hooks'][0]['async'])"  # True
sed -n '6p' hooks/subagent-context-injector.sh              # # Async: false (completes before subagent starts)

# bytes emitidos al vacío
python3 -c "
import json
r=[json.loads(l) for l in open('.cognitive-os/metrics/hook-timing.jsonl') if '\"SubagentStart\"' in l]
b=[x.get('stdout_bytes',0) for x in r]
print(len(r), sum(b), min(b), max(b))"                       # 33 316519 9398 10253

# --- EJE 1: qué mide el test ---
sed -n '21,53p;155,168p' tests/hooks/test_subagent_context_injector.py   # subprocess -> stdout; helper acepta 2 formas
.venv/bin/python -m pytest tests/hooks/test_subagent_context_injector.py -q  # 18 passed

# las dos formas JSON en el mismo repo
grep -n "additionalContext" hooks/subagent-context-injector.sh | tail -1   # :195 anidada
grep -n "additionalContext" hooks/cross-session-peer-context.sh            # :40  plana
grep -n "additionalContext" hooks/agent-message-inbox-context.sh           # :42  plana

# --- EJE 2: lo que anda ---
wc -l < .cognitive-os/sessions/events.jsonl                  # 19710
python3 -c "
import json
r=[json.loads(l) for l in open('.cognitive-os/sessions/events.jsonl') if l.strip()]
print(len(set(x.get('session_id') for x in r)))"             # 34
ls .cognitive-os/runtime/edit-locks/ | wc -l                 # 979
ls -la docs/06-Daily/reports/postmortem-cross-session-collision-2026-05-05.md  # existe, 18554 bytes

# --- EJE 2: lo que no anda ---
python3 -c "
import sys;sys.path.insert(0,'.')
from cos_lib.session_bus import peers; from pathlib import Path
print(len(peers(project_dir=Path('.').resolve(), within_seconds=1800,
                alive_only=True, current_session_id='x', limit=200)))"      # 0
cat .cognitive-os/sessions/active-sessions.json                             # {"sessions": []}

# --- disponibilidad nativa: el chequeo que decide 2b (correr en sesión interactiva) ---
claude --version                                             # 1.30096.5 acá
echo "${CLAUDE_CODE_MESSAGING_SOCKET:-AUSENTE}"              # AUSENTE en este subagente

# --- ancla del informe externo (reproduce exacto) ---
curl -s https://code.claude.com/docs/en/cross-session-messaging.md \
  | grep -inE 'order|ordering|sequence|fifo|at-least-once|exactly-once|guarantee'
# único hit, línea 66: "Delivery isn't guaranteed in every configuration"

# --- contradicción de manifiestos (9 vs 0) ---
for h in subagent-context-injector cross-session-peer-context agent-message-inbox-context \
         cross-session-event-emit edit-lock-pre-tool subagent-budget-enforcer \
         subagent-capability-preflight agent-message-inbox-guard cross-session-coordination-guard; do
  grep -m1 '^# SCOPE:' hooks/$h.sh; done | sort | uniq -c   # 9 "# SCOPE: both"
grep -cE 'subagent-context-injector|cross-session-peer-context|agent-message-inbox|cross-session-event-emit|edit-lock|subagent-budget|subagent-capability' \
  manifests/primitive-install-boundary.yaml                  # 0
head -1 templates/agent-mandatory-rules.md                   # <!-- SCOPE: os-only -->
```
