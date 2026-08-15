# prime-agent y el aprendizaje persistente: qué es realmente

**Licencia: MIT.** Verificada contra el `LICENSE` del clon, no contra el README ni contra la API
de GitHub. No hay AGPL, SSPL ni BSL en la cadena principal. El `LICENSE` trae **dos** líneas de
copyright, y eso importa:

```
Copyright (c) 2025 Mario Zechner
Copyright (c) 2026 Prime Intellect
```

`prime-agent` es un derivado de [`earendil-works/pi`](https://github.com/earendil-works/pi)
(agente `pi` de Mario Zechner), también MIT, y lo consume como dependencia npm
(`@earendil-works/pi-agent-core`, `pi-ai`, `pi-tui`, `^0.7.2`, en
`packages/coding-agent/package.json:51-53`). La cadena de licencias cierra: MIT sobre MIT.

**Nada de esto es una recomendación de adopción.** `manifests/external-tool-adoption-freeze.yaml`
sigue en `frozen: true` desde 2026-05-11. Lo que sigue describe lo que existe.

- Fecha de consulta de todo el informe: **2026-08-15**.
- Repo: `https://github.com/PrimeIntellect-ai/prime-agent`, commit medido `97b994c` (2026-08-14).

---

## Cómo se midió (evidencia reproducible)

Todo lo que afirmo abajo sale de un clon superficial, no de la web. El clon era material de
proceso y ya no existe; por eso cada afirmación de código cita **archivo y línea**.

```bash
# 1. Clonar (scratchpad, nunca dentro del repo del operador)
git clone --depth 50 https://github.com/PrimeIntellect-ai/prime-agent.git <scratch>/pa

# 2. Licencia autoritativa: el archivo, no la API
head -1 <scratch>/pa/LICENSE            # -> "MIT License"
grep Copyright <scratch>/pa/LICENSE     # -> 2 titulares

# 3. ¿Está vivo? El commit de la rama default, no pushed_at
git -C <scratch>/pa log -1 --format='%ci %h %s' origin/main
git -C <scratch>/pa shortlog -sn origin/main | wc -l

# 4. Sin red y sin clon: el feed atom da el último commit real de la rama
curl -sL "https://github.com/<org>/<repo>/commits/main.atom" \
  | grep -m1 '<updated>'
```

El comando 4 es el que reemplaza a `pushed_at`. Verifiqué el punto del encargo: para
`earendil-works/pi`, la API decía `pushed_at: 2026-08-15T21:44:54Z`, y el último commit real de
`main` era `2026-08-15T05:33:05Z`. Ahí la diferencia fue de horas, no de 39 días, pero el campo
sigue sin ser el dato: `pushed_at` se mueve con cualquier push a cualquier rama.

---

## 1. Qué hace exactamente: destilación a artefactos de prompt, no fine-tuning

**No toca pesos. No es memoria vectorial. No hay embeddings.** Lo verifiqué buscando en el
subsistema completo:

```bash
grep -rniE 'embedding|vector|cosine|faiss|chroma|qdrant|pgvector' \
  packages/coding-agent/src/core/refinement/ prime-agent-runtime/src/rlm/harness.py
# -> vacío
grep -riE 'train|reward|grpo|lora|finetune|checkpoint|distill' <tree del repo>
# -> único match: examples/extensions/git-checkpoint.ts (no relacionado)
```

De las cuatro opciones que planteaba el encargo, es la tercera con una vuelta de tuerca:
**destilación de la trayectoria a artefactos tipados que se inyectan en el system prompt**, con
edición y borrado como operaciones de primera clase.

### El mecanismo, pieza por pieza

El subsistema se llama **continual harness** y vive en
`packages/coding-agent/src/core/refinement/refinement.ts` (1017 líneas).

**Qué persiste.** Cuatro tipos, y esto es lo importante
(`refinement.ts:30`, `RefinementKind = "prompt" | "memory" | "skill" | "subagent"`):

| kind | qué es | por qué importa |
|---|---|---|
| `memory` | hechos, decisiones, fallas, preferencias, resultados | el único que se parece a `mem_save` |
| `prompt` | notas suplementarias al system prompt | **política de comportamiento**, no un hecho |
| `skill` | descripción de una llamada Python reusable, con `reference` y contrato de `arguments` | procedimiento invocable |
| `subagent` | spec de delegación reusable (propósito, instrucciones, cuándo invocar) | rol, no dato |

El system prompt del refinador es explícito sobre el techo:
*"The base system prompt is immutable and MUST NOT be rewritten"* (`refinement.ts:129`). Las
entradas `prompt` son addendums, no reemplazo.

**Dónde persiste** (`refinement.ts:269-278`, y documentado en `docs/rlm-runtime.md:211`):

- Global (cruza sesiones): `~/.prime/agent/harness/harness_state.json`
- Local (por sesión, **es el default**): `<session artifact dir>/harness/harness_state.json`
- Historial de refinamientos: `refinements.jsonl` en el mismo directorio

Al construir el prompt, `mergeHarnessStates()` (`refinement.ts:326`) fusiona global + local.

**Cuándo se dispara.** Tres caminos, y el tercero es el que cambia el análisis:

1. `/refine [instrucciones]` desde el TUI (`docs/usage.md:55`).
2. `await refine.run()` desde el kernel IPython (`skills/refine/SKILL.md`). Nunca corre a mitad
   de celda: se agenda y se ejecuta al terminar el turno.
3. **Automático, prendido por default** (`src/core/settings-manager.ts:23-28, 882-896`):

   ```
   enabled    -> true
   turnInterval -> 25 turnos de asistente
   compact    -> true  (también al compactar contexto)
   cooldownMs -> 20 minutos
   ```

   Esto es lo que no se ve en el README: el agente se auto-edita cada 25 turnos sin que nadie se
   lo pida. Y `docs/settings.md` **no menciona `autoRefine` ni una vez**
   (`grep -ci 'refine' docs/settings.md` devuelve `0`).

**Quién decide qué se guarda.** Dos llamadas LLM separadas, no heurísticas:

- Un **gate de revisión** (`reviewAutoRefine()`, `refinement.ts:949`) que recibe los últimos
  40.000 caracteres de la conversación y devuelve `{shouldRefine, rationale, instructions}`. Su
  prompt dice: *"Reject one-off noise, unsupported hypotheses, and transient tool outputs"*
  (`refinement.ts:174`).
- El **planificador** (`planRefinement()`, `refinement.ts:863`), que emite un JSON con ediciones
  `create|update|delete` y las aplica `applyRefinementProposal()` (`refinement.ts:707`).

O sea: **la decisión de qué vale la pena conservar es un juicio de un modelo, en dos etapas, sin
señal externa de éxito.** No hay verificación contra resultados, ni reward, ni confirmación
humana obligatoria.

### La parte que el pitch incluye y el repo no

El README apunta al paper [Continual Harness (arXiv:2605.09998)](https://arxiv.org/abs/2605.09998),
*"Continual Harness: Online Adaptation for Self-Improving Foundation Agents"*, Karten et al.,
11-may-2026 (verificado en arXiv, consulta 2026-08-15). Seth Karten, primer autor del paper, es
el **segundo committer** del repo en la ventana medida (12 de 50 commits).

El paper tiene **dos** loops. El primero es el que ship-ea el repo (refinar prompt, subagentes,
skills y memoria). El segundo, según el abstract, es *"an online process-reward co-learning loop,
in which an open-source agent's rollouts through the refining harness are relabeled by a frontier
teacher and used to update the model"*. **Eso sí actualiza pesos, y no está en este repo.** El
entrenamiento vive en `PrimeIntellect-ai/prime-rl`, que además es **Apache-2.0**, no MIT
(`curl -sL https://raw.githubusercontent.com/PrimeIntellect-ai/prime-rl/main/LICENSE | head -1`),
último commit en `main` 2026-08-14. No lo audité.

Dicho corto: **el paper aprende con pesos; el repo MIT aprende con prompts.**

Ojo también con el vocabulario. El propio system prompt del refinador aclara la distinción, que
el pitch mezcla: *"Use 'continual harness' for that persistent artifact layer; keep 'RLM' for the
runtime, IPython kernel, and native call interface"* (`refinement.ts:135-136`). RLM (Recursive
Language Model) es el runtime, no el aprendizaje.

---

## 2. Qué resuelve que `mem_save`/`mem_search` no

Corto: **`mem_save` es pull; el continual harness es push, y guarda comportamiento además de
hechos.** Tres diferencias que no son de implementación sino de concepto.

**a) Nadie tiene que buscar.** El estado del harness se renderiza siempre dentro del system
prompt (`formatHarnessStateForPrompt()`, `refinement.ts:429`), como un overview de hasta 6
entradas por tipo, 180 caracteres cada una. No hay query, no hay recall, no hay embedding. Con
`mem_search`, si el agente no se le ocurre buscar, lo aprendido no existe. Acá está siempre
delante de los ojos (con el costo que eso tiene, ver más abajo).

**b) Dos de los cuatro tipos no son hechos.** `prompt` es política de comportamiento y `subagent`
es un rol de delegación. Una memoria de hechos puede *almacenar* la frase "siempre corré
`git status` antes de commitear", pero no puede convertirla en una regla activa; para eso hay que
recuperarla y que alguien la lea. El harness la instala como addendum de prompt. Y `skill` va más
lejos: la entrada lleva un contrato ejecutable (`reference` con `{"type":"python"}`, import,
callable, `call_pattern`, más un `arguments` con tipos y requeridos, validado en `validateEdit()`,
`refinement.ts:664`). Eso no es un texto recuperable, es una llamada.

**c) Borrar y revertir son operaciones nativas.** `delete` es una acción de primera clase y hay
rollback por id de refinamiento con snapshots `before`/`after` (ver punto 3).

**Ahora, aplicando el criterio de la casa** ("¿un cambio en uno de los dos conceptos debería
obligar a tocar el otro?"): si `mem_search` cambiara su ranking de recuperación, el harness no se
tocaría. Si el harness cambiara su taxonomía de ediciones, `mem_save` no se tocaría. **No es
duplicación, es coincidencia de superficie** en un solo punto: el `kind: memory`. Ahí sí se
solapan, y ahí la novedad de prime-agent es cero. La novedad está en `prompt`, `skill` y
`subagent`, y en el disparo automático.

Segundo corolario, honesto: **la idea tampoco es de prime-agent.** Es la familia de
"context evolution" que ACE ya había formalizado en 2025 (ver panorama). prime-agent es una
implementación de producción, tipada y con rollback, de una idea publicada.

---

## 3. Qué pasa cuando lo aprendido queda viejo o resulta falso

**Esto es el hallazgo.** Busqué el mecanismo en el código, no en la doc:

```bash
grep -niE 'ttl|expire|evict|stale|prune|decay|max_entries|dedup|conflict|contradict' \
  packages/coding-agent/src/core/refinement/refinement.ts
```

Los únicos matches son la palabra "validate" dentro de un prompt, `validateEdit()` (que valida
**forma**: campos requeridos, no verdad) y un comentario sobre resolución de conflictos de
escritura concurrente. **No hay TTL, no hay expiración, no hay desalojo, no hay decaimiento, no
hay detección de contradicción, y no hay tope de entradas.**

Lo que sí hay:

| Mecanismo | Dónde | Qué cubre de verdad |
|---|---|---|
| Rollback por id | `rollbackProposal()`, `refinement.ts:804-836` | Invierte exacto: lo creado se borra, lo actualizado vuelve al snapshot `before`. Es lo mejor del diseño. |
| Versionado de entrada | `refinement.ts:761`, `version = before.version + 1` | Cuenta ediciones. No expira nada. |
| Guarda de concurrencia | `refinement.ts:723-737` | Rechaza la edición si la entrada cambió mientras se planificaba. Es una carrera, no obsolescencia. |
| Gate de ruido | `AUTO_REFINE_REVIEW_SYSTEM_PROMPT`, `refinement.ts:172-180` | Un LLM decide si hay lección. Es el intento real al problema difícil, y es un juicio, no una medición. |
| Instrucción al planificador | `refinement.ts:151-152` | *"If prior refinements caused issues, rollback or replace the faulty editable entries."* |

Esa última línea es la respuesta completa del sistema a "¿y si lo aprendido es falso?": **una
frase en un prompt pidiéndole al modelo que se dé cuenta.** No hay nada que detecte la falsedad;
depende de que el propio agente, en un refinamiento futuro, note el problema y proponga el
borrado. Si nadie lo nota, la entrada falsa queda en el system prompt para siempre.

Dos consecuencias medibles que se siguen de esto:

1. **Crecimiento no acotado.** `state.refinements.push(...)` (`refinement.ts:783`) nunca se poda.
   El array crece indefinidamente dentro de `harness_state.json`. Lo único acotado es el
   *render*: `state.refinements.slice(-maxRefinements)` con `maxRefinements = 5`
   (`refinement.ts:509`).
2. **El overview miente por omisión a partir de 7 entradas por tipo.** `maxEntriesPerKind = 6`
   (`DEFAULT_OVERVIEW_ENTRY_LIMIT`, `refinement.ts:26`). Pasado ese número, el prompt imprime
   `- +N more <kind> entries` (`refinement.ts:497-500`) y el contenido no entra. Combinado con
   que no hay desalojo: **un harness que acumula 40 memorias muestra 6, elegidas por orden
   alfabético de `path/title/id`** (`refinement.ts:466-468`), no por relevancia ni por
   recencia. Sin desalojo y sin ranking, la utilidad marginal de seguir aprendiendo tiende a
   cero, y peor: es alfabética.

Esto no es una opinión mía sobre el estado del arte. Es exactamente lo que diagnostica el survey
[arXiv:2606.30306](https://arxiv.org/abs/2606.30306), *"Always-On Agents: A Survey of Persistent
Memory, State, and Governance in LLM Agents"* (Ding et al., 29-jun-2026, consultado 2026-08-15),
sobre un corpus de 435 trabajos: *"the literature concentrates more heavily on accumulating and
retrieving state than on governing, recovering, or relinquishing it"*. prime-agent está por
**encima** de la media del campo en *recovering* (el rollback con snapshots es serio) y en la
media en *relinquishing* (o sea, no lo resuelve).

---

## 4. El panorama a agosto 2026

### Lo que sí compite en el mismo espacio

| Proyecto / trabajo | Licencia (verificada) | Último commit en rama default | Cómo se diferencia |
|---|---|---|---|
| `PrimeIntellect-ai/prime-agent` | **MIT** (clon) | 2026-08-14 (`97b994c`) | Artefactos tipados en system prompt, auto-refine cada 25 turnos, rollback |
| `letta-ai/letta` | **Apache-2.0** (clon) | 2026-08-13 (`56ba9c2`) | *Memory blocks* con límite de caracteres + **sleep-time agents** que reescriben memoria en background |
| `letta-ai/letta-code` | **Apache-2.0** (clon) | 2026-08-14 (`d37c903`) | El agente de código sobre lo anterior |
| `earendil-works/pi` | **MIT** (clon) | 2026-08-15 (`086c32e`) | Upstream de prime-agent. No trae continual harness: eso lo agregó Prime Intellect |
| `PrimeIntellect-ai/prime-rl` | **Apache-2.0** (raw) | 2026-08-14 | La mitad de *pesos* del paper. Producto distinto, licencia distinta |
| ACE, [arXiv:2510.04618](https://arxiv.org/abs/2510.04618) | paper (oct-2025) | — | El antecedente conceptual directo |

**Letta es la comparación que vale**, y es genuinamente distinta: en vez de refinar al terminar
el turno, corre **agentes de sueño** que comparten los memory blocks del agente principal y los
reescriben de forma asincrónica mientras el principal no está ocupado
(https://docs.letta.com/guides/agents/architectures/sleeptime/, consultado 2026-08-15). Y sus
bloques tienen **límite de caracteres explícito**, que es justamente la presión de desalojo que a
prime-agent le falta. Direcciones opuestas al mismo problema: prime-agent tipa el artefacto y no
lo acota; Letta lo acota y no lo tipa.

**ACE (Agentic Context Engineering)** es el paper que hay que leer para entender si prime-agent
inventó algo. Propone tratar el contexto como un *playbook* de ítems estructurados que se
actualiza con **deltas incrementales** (Generator / Reflector / Curator), y nombra dos fallas que
prime-agent evita por diseño: *brevity bias* (resumir y perder el detalle) y *context collapse*
(que la reescritura iterativa erosione el contenido). El `create|update|delete` sobre entradas
tipadas de prime-agent **es** la receta de ACE. La contribución propia de prime-agent es el
tipado en cuatro categorías, el scope local/global, y el rollback.

### Lo que descarté, y por qué (para que el próximo no lo repita)

- **`mem0ai/mem0`** (Apache-2.0, verificado por `LICENSE` crudo; último commit en `main`
  2026-08-14 por feed atom). Descartado como comparable: es extracción y consolidación de hechos
  con recuperación, o sea el mismo espacio que `mem_save`/`mem_search`. No representa
  comportamiento ni procedimientos. **El clon se colgó por tamaño (timeout de 2 min), así que su
  licencia está verificada por archivo crudo, no por clon.**
- **Zep / Graphiti.** Descartado por redundante con trabajo propio: ya figura en el backlog
  `pending_on_unfreeze` de `manifests/external-tool-adoption-freeze.yaml`. Mirarlo de nuevo hoy
  no agrega nada que el operador no tenga.
- **Memento-Skills ([arXiv:2603.18743](https://www.emergentmind.com/papers/2603.18743)).**
  Conceptualmente el más cercano de todos (skills programables como memoria externa persistente,
  sin reentrenar). **No lo verifiqué contra código ni contra arXiv directo**: la única referencia
  que vi fue un agregador de papers. Queda como pista, no como evidencia.
- **Sophia (arXiv:2512.18202)**, framework de agente persistente de vida artificial. Descartado:
  el dominio es artificial life, no workflows de código.
- **RIZZ (arXiv:2606.20638)**, adaptación continua de agentes caja-negra. Descartado por
  presupuesto, no por irrelevancia. Es el candidato más razonable para una segunda pasada.
- **Voyager** (skill library en Minecraft, 2023). Es el ancestro de "skill acquisition" y
  explicaría de dónde viene la idea de biblioteca de habilidades, pero es de hace tres años y no
  lo medí hoy.
- **Blogs de "self-improving agents 2026"**. Descartados por método: la primera página de
  resultados tenía piezas de agregadores y un artículo de `technology.org` con pinta de
  contenido generado. Nada de lo que afirmo arriba sale de ahí.

### El workshop, como señal de que el campo se está ordenando

Existe un *2nd Workshop on Lifelong Agents* en COLM 2026 (https://lifelongagent.github.io/,
consultado 2026-08-15). **Estado: lo dice el resultado de búsqueda, no lo confirmé abriendo el
sitio.** Lo dejo marcado así a propósito, porque el encargo advertía que hoy un dominio citado
resultó estar en venta.

---

## 5. ¿Está vivo?

**Sí, y con mucha velocidad.** El comando que lo prueba:

```bash
git -C <clon> log -1 --format='%ci %h %s' origin/main
# 2026-08-14 14:03:09 -0700 97b994c feat(daemon): supervisor-owned rlm spawn ledger...

git -C <clon> log --format='%ci' origin/main | tail -1
# 2026-08-05 01:10:45 -0700   <- 50 commits atrás

git -C <clon> shortlog -sn origin/main | wc -l
# 11
```

**50 commits en 9 días, 11 personas distintas.** El repo se creó el 2026-05-08 (API de GitHub) y
tiene ~16.3k estrellas. No es un proyecto de un autor con tres semanas de vida: es un equipo
empujando fuerte. El commit principal (`Sebastian Müller`, 21 de 50) y el segundo
(`Seth Karten`, el del paper, 12 de 50) muestran que investigación e ingeniería están en el mismo
árbol.

Contraste con la doc: **el mecanismo estrella tiene 6 líneas de documentación en todo el árbol.**

```bash
grep -rniE 'continual harness|/refine' packages/coding-agent/docs/ | wc -l   # -> 6
```

Todo lo demás está en el código y en prompts embebidos. No hay `docs/refine.md` ni
`docs/continual-harness.md`. Para el criterio de tres estados del encargo, casi todo lo que conté
arriba es **"está en el código sin documentar"**, no "documentado".

---

## 6. Lo que no pude verificar

- **Si el harness funciona.** No corrí nada: el encargo prohíbe ejecutar código de terceros sin
  auditar, y lo respeté (ni `install.sh`, ni tests, ni `pip install`). No hay medición propia de
  si un agente con harness rinde mejor que uno sin harness. El paper reporta ganancias en Pokémon
  Red/Emerald, no en workflows de código. **Nadie midió el continual harness en coding.**
- **Los números del paper.** No los reproduje. Solo verifiqué que el paper existe, su título,
  autores y fecha en arXiv.
- **`prime-rl`.** Solo licencia y último commit. No sé qué implementa realmente del loop de pesos.
- **`mem0`** por clon (timeout). Licencia por archivo crudo.
- **Memento-Skills** por fuente primaria.
- **Costo del auto-refine.** Cada disparo son dos llamadas LLM (gate + planificador), la del gate
  con hasta 40.000 caracteres de conversación (`refinement.ts:962`) y la del planificador con
  hasta 32.000 tokens de salida (`REFINEMENT_MAX_OUTPUT_TOKENS`, `refinement.ts:186`). Cada 25
  turnos, con cooldown de 20 minutos. **No lo cuantifiqué en dinero.** Es el número que más falta
  para decidir cualquier cosa.
- **Qué tiene este repo en este espacio.** No lo medí a propósito: lo está haciendo otro agente y
  la verificación cruzada solo vale si medimos distinto.

---

## 7. Qué del encargo era falso

**El encuadre del operador, "esto de que se queda con lo que le enseñas", es cierto a medias y
falso en el punto que más importa.**

1. **Por default NO se queda entre sesiones.** El scope por default es **local**, o sea
   *session-scoped*. El propio prompt del refinador lo dice: *"The default editable continual
   harness store is local to the current Prime Agent session"* (`refinement.ts:139`), y la API
   expone `global_=False` por default (`skills/refine/SKILL.md`). Para que lo aprendido sobreviva
   a la sesión hace falta pedirlo explícito, o que el LLM juzgue que la lección es "durable
   cross-session". La frase del pitch describe el caso opt-in, no el comportamiento por default.
2. **No es "lo que le enseñás".** No hay ningún camino donde el usuario dicte la lección y el
   sistema la guarde tal cual. Lo que se guarda es lo que **un modelo destila de la trayectoria**,
   mayormente sin que nadie lo pida (auto-refine cada 25 turnos, prendido de fábrica). Es más
   parecido a "se queda con lo que él concluye de lo que pasó" que a "con lo que le enseñás".
3. **La hipótesis de riesgo del encargo apuntaba a la licencia. Ahí no hay problema.** MIT sobre
   MIT. El riesgo real está en otro lado: el subsistema que se auto-edita está prendido por
   default, no aparece en `docs/settings.md`, y no tiene forma de olvidar.
4. **"¿Es un nombre nuevo para memoria vectorial?" No, y por un motivo mejor del esperado:** no
   hay vectores en ninguna parte. Es un JSON inyectado en el prompt. La objeción correcta no es
   "esto ya existe como memoria vectorial", es "esto ya existe como ACE, publicado en octubre de
   2025".
5. **El encargo asumía que `pushed_at` iba a mentir feo.** Hoy, sobre estos repos, mintió poco
   (horas, no días). El campo sigue sin servir, pero la magnitud del caso de referencia (39 días)
   no se repitió acá. Lo digo para que no se cite ese número como si fuera general.

**Y una corrección al "verde barato" del encargo**, que pedía no concluir "no sirve" porque se
parezca a algo existente: el riesgo real acá era el opuesto. La tentación era decir *"es memoria,
ya lo tenemos"*. No lo es. `prompt` y `subagent` no tienen análogo en un almacén de hechos, y el
disparo automático tampoco. Donde sí es lo mismo es en `kind: memory`, y eso queda aceptado como
coincidencia, con el motivo escrito arriba.

---

## Cierre, sin recomendación

Lo que resolvería el problema de "el agente olvida entre sesiones" con más elegancia que
`mem_save` es la capa de artefactos tipados con rollback: `prompt`, `skill` y `subagent`, no
`memory`. **Eso requeriría descongelar
`manifests/external-tool-adoption-freeze.yaml`, que es una decisión con gate propio** (revisión
legal de IP, búsquedas de patente y marca, firma del operador). No lo recomiendo ni lo propongo.

Y aun descongelado, quedaría abierto lo que el propio proyecto no resolvió y el survey de junio
dice que el campo tampoco: **qué hace el sistema cuando lo aprendido resulta falso.** La
respuesta de prime-agent, hoy, es una frase en un prompt.
