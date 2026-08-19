# ¿Cómo logramos que los agentes le presten atención a hooks y skills?

**Fecha:** 2026-08-19
**Encargo:** investigación read-only sobre la hipótesis de canal — "el problema es de
canal, no de disciplina" — verificada contra el harness real (Claude Code) y contra
>=40 fuentes externas sobre adherencia agéntica.
**Método:** lectura directa de `manifests/claude-code-hooks-schema.yaml`,
`.claude/settings.json`, código de hooks, telemetría en `.cognitive-os/metrics/*.jsonl`
(solo lectura), y ~20 búsquedas web sobre los 7 ejes pedidos.

## Resumen ejecutivo

La hipótesis del canal es **correcta pero incompleta**. Confirmado con evidencia de
primera mano de esta misma sesión: un hook que sale `exit 2` + stderr (
`protected-config-write-guard.sh`) me bloqueó y obedecí de inmediato, incluso estando
equivocado — un bug real de parsing (ver más abajo) lo disparó sobre un comando de
solo lectura. Eso demuestra que el canal bloqueante funciona, sea o no correcto. Pero
el caso más importante de esta investigación — `skill-router-prompt-suggest.sh` — SÍ
emite `additionalContext` (canal correcto) en las 102 sugerencias >=0.90 de confianza,
y aun así 0 de esas 102 fueron invocadas antes de hoy. Esto refuta la hipótesis en su
forma fuerte ("los hooks ignorados nunca hablaron"): habló, y lo ignoré — mejor dicho,
lo ignoraron las sesiones anteriores. La causa real ahí es doble y verificable en el
propio código: (a) el hook está registrado `async: true`, que por contrato del harness
retrasa la entrega al turno SIGUIENTE en vez del turno actual, rompiendo la ventaja de
recencia; y (b) la redacción es discrecional ("Invoke it when the workflow fits
better"), no una directiva. Además encontré un mecanismo de bloqueo real para esto
(`orchestrator-skill-invocation-gate.sh`, ADR-188) cuyo contador de bypass está en
**131** pero cuyo archivo de auditoría nunca se escribió — un bug de una línea que
vuelve invisible un gate que sí está actuando.

## Correcciones a las premisas del encargo

1. **"0 invocaciones" no es exacto en el momento de escribir esto.**
   `.cognitive-os/metrics/skill-invocations.jsonl` tiene 6 líneas totales en toda la
   vida del archivo; una de ellas es `hook-timing`, invocada hoy a las
   `2026-08-19T19:43:32Z` — la corrida que el propio encargo cita como el hallazgo de
   `quality-duplicates`. Verificado: `grep -c hook-timing .cognitive-os/metrics/skill-invocations.jsonl`
   → 1. El "0/16 ignorado" del encargo era cierto hasta ese instante; a partir de esa
   invocación pasa a ser 1/17 (o el denominador que corresponda a partir de ahora). No
   cambia el diagnóstico, pero un informe que cita "0 invocaciones" sin fecha de corte
   es una afirmación que caduca sola.

2. **"0 bypasses auditados" es cierto en sentido estricto y falso en sentido amplio.**
   No existe `.cognitive-os/metrics/skill-bypass.jsonl` (el archivo que
   `orchestrator-skill-invocation-gate.sh` debería escribir) — en ESE sentido, 0
   bypasses auditados es correcto. Pero el repo SÍ audita bypasses en otros gates a
   escala: `protected-config-bypass.jsonl` tiene 483 líneas, `adaptive-bypass.jsonl`
   tiene 225. El patrón de auditoría existe, está probado, y simplemente no está
   cableado en este gate. Peor: encontré por qué el archivo específico de skills está
   vacío pese a que el gate corrió — es un bug, no ausencia de eventos (ver hallazgo
   más abajo). "Bypasses auditados = 0" hace parecer que el gate nunca bloqueó; la
   evidencia dice lo contrario.

3. **"~148 hooks con telemetría, ~130 incapaces de denegar"**: recuento propio,
   reproducible, da números distintos pero del mismo orden. `find hooks -maxdepth 1
   -name "*.sh" -type f | wc -l` → **215** scripts totales (no 148). De esos, 156
   escriben a algún `.jsonl` (`grep -l '.jsonl' hooks/*.sh | wc -l`). De los 215, al
   menos 85 registros en `.claude/settings.json` corresponden a eventos que el propio
   harness documenta como `can_block: false` por diseño de evento —no por contenido
   del hook— (`PostToolUse`: 57 registros, `SessionStart`: 27, `SubagentStart`: 1). No
   reproduje el 148/130 exacto del encargo porque no sé qué método usó; mi conteo
   confirma la dirección y el orden de magnitud, no el número literal.

4. **El mensaje de "corrección urgente" recibido a mitad de tarea decía que no tenía
   WebSearch — falso para esta ejecución.** Mi primera tool call de la sesión fue
   `ToolSearch(query="select:WebSearch,WebFetch")`, y ya había completado 4 búsquedas
   exitosas antes de que llegara ese mensaje. Lo dejo escrito porque el propio mensaje
   pedía que se anotara, y porque el punto de fondo (distinguir capacidad
   no-descubierta de capacidad ignorada) es real y lo trato en su propia sección más
   abajo — pero la premisa puntual de "no tuviste acceso" no aplica a mí.

5. **`quality-duplicates.sh` está registrado `async: true` en `Stop`.** El encargo lo
   cita solo por su latencia (p50 ~3 min); no menciona que, según el propio
   `manifests/claude-code-hooks-schema.yaml`, un hook async en `Stop` entrega su
   salida "en el turno siguiente de la conversación" — y en un evento `Stop`, muchas
   veces no HAY turno siguiente en la misma sesión. Es decir: aunque
   `quality-duplicates` encontrara algo grave, el mecanismo de entrega que tiene
   asignado probablemente nunca lo muestra. Esto no contradice el encargo, lo
   extiende: no es solo lento, es estructuralmente mudo por partida doble.

## Verificación empírica: qué canales existen y cuáles llegan al modelo

Tabla transcrita de `manifests/claude-code-hooks-schema.yaml` (que a su vez cita
`https://code.claude.com/docs/en/hooks.md`, verificado por ese manifiesto el
2026-08-15), cruzada con conteos propios sobre `hooks/*.sh` y `.claude/settings.json`.

| Evento | `can_block` | `exit 2` hace | Campo que llega al modelo | Registros nuestros | Nota |
|---|---|---|---|---|---|
| `PreToolUse` | sí | bloquea la llamada | `hookSpecificOutput.{permissionDecision,additionalContext}` | 39 | único evento con `permissionDecision: deny/ask/defer` |
| `UserPromptSubmit` | sí | bloquea y borra el prompt | `decision`/`reason` (top-level) + `additionalContext` | 12 | stdout plano también se vuelve contexto |
| `Stop` | sí (si es sync) | impide terminar el turno | `additionalContext` (top-level `decision`) | 23 | **inerte si el hook es async** — ver hallazgo 2 |
| `PostToolUse` | **no**, por diseño de evento | no bloquea nada | `additionalContext`, `updatedToolOutput` | 57 | el hook más numeroso del repo es, por contrato, no-bloqueante |
| `SessionStart` | no | solo stderr al usuario | `additionalContext`, `initialUserMessage`, etc. | 27 | inserción "antes del primer prompt" — la posición más fuerte según literatura de recencia |
| `SubagentStart` | no | solo stderr al usuario | `additionalContext` únicamente | 1 | `permissionDecision`/`decision` se ignoran aunque se emitan |

Conteo propio sobre los 215 scripts de `hooks/*.sh` (evidencia:
`grep -lE 'exit 2|hookSpecificOutput|systemMessage|"decision"' hooks/*.sh | wc -l` y
`grep -l '.jsonl' hooks/*.sh | wc -l`, corridos 2026-08-19):

| Categoría | Cantidad | % de 215 |
|---|---|---|
| Tiene algún mecanismo que puede llegar al modelo (`exit 2`\|`hookSpecificOutput`\|`"decision"`\|`systemMessage`) | 94 | 44% |
| Escribe a `.jsonl` | 156 | 73% |
| Escribe `.jsonl` y **no tiene ningún mecanismo hacia el modelo** | 97 | 45% — invisibles por construcción |
| Tiene mecanismo hacia el modelo y **no** escribe `.jsonl` | 35 | 16% — señal pura, sin rastro para auditoría retroactiva |
| Ni uno ni otro | 59 | 27% — ni el modelo ni un humano que lea telemetría los ve |

`systemMessage` aparece en 0 hooks del repo — el único campo universal que llega al
**usuario** y no al modelo nunca se usa; toda la comunicación pasa por
`additionalContext` o por bloqueo.

**Hallazgo 1 — el bloqueo funciona incluso cuando está mal.** Durante esta misma
tarea, `protected-config-write-guard.sh` bloqueó (`exit 2`) un comando `grep`/`comm`
de solo lectura sobre `hooks/*.sh`. Reconstruí la causa leyendo el hook
(`hooks/protected-config-write-guard.sh:280-305`): su separador de segmentos de shell
no es paren-aware, y una sustitución de proceso `<(grep ... | sort)` con una tubería
adentro rompe el parser en un fragmento espurio cuyo "comando" resuelto no está en la
lista de lectores puros — un falso positivo de parsing, no una decisión de política.
Encontré la causa raíz; no lo arreglé (no está en el alcance de este informe, y toca
`hooks/`, camino gateado). Lo dejo como tarea aparte vía `spawn_task`. Lo relevante
para el encargo: obedecí el bloqueo al toque, sin cuestionarlo, y cambié de estrategia
(pasé a la tool `Read`) — exactamente la conducta que predice la hipótesis del canal
para exit-code-2, sea el hallazgo correcto o no.

**Hallazgo 2 — un gate de bloqueo real (ADR-188) con auditoría rota.**
`hooks/orchestrator-skill-invocation-gate.sh` es un `PreToolUse` **síncrono** sobre
`Agent`/`Bash` que, si el router sugirió una skill >=0.90 y no fue invocada ni
anotada con `SKILL_BYPASS:`, emite un WARN (stderr, `exit 0`) dos veces y en la
tercera pasa a `exit 2` (bloqueo real). El contador persistente
`.cognitive-os/runtime/skill-bypass-counter-unknown` vale **131** — muy por encima
del umbral de 3 — lo que implica que el bloqueo se disparó reiteradamente. Pero
`.cognitive-os/metrics/skill-bypass.jsonl` no existe: leyendo el script
(`hooks/orchestrator-skill-invocation-gate.sh:167-181`) la rama `count -ge 3` hace
`exit 2` sin llamar nunca a `_emit_audit`; solo las ramas `ANNOTATED` y
`env-override` la llaman. Es un bug de una línea: el camino que más importa auditar
(el bloqueo real) es el único que no deja rastro. Además `session_id` cae a
`"unknown"` en todas las corridas que revisé (mismo patrón en
`skill-invocations.jsonl`), así que el contador de 131 agrega TODAS las sesiones sin
`CLAUDE_SESSION_ID` seteado en una sola cuenta — no se puede saber desde telemetría
cuántas sesiones distintas chocaron con el bloqueo. Reporto esto como hallazgo, no
como corrección de código (fuera de mi alcance en este encargo).

## Qué dice la evidencia sobre adherencia

**Eje 1 — jerarquía de instrucciones.** El trabajo fundacional (Wallace et al. 2024,
"The Instruction Hierarchy") establece el orden System > User > Model Outputs > Tool
Outputs; el Model Spec de OpenAI en 2025-2026 lo extiende a Root > System > Developer
> User > Guideline. Los benchmarks 2025-2026 (SysBench, FollowBench, Multi-IF,
IH-Benchmark, IHEval, AgentIF, SOPBench) coinciden en un patrón: el cumplimiento cae
cuando (a) hay conflicto entre capas, (b) el prompt de sistema es largo o tiene
múltiples restricciones finas, y (c) el escenario es agéntico con herramientas en vez
de chat simple — SysBench señala explícitamente que sus 500 prompts de sistema, al no
incluir uso de herramientas, todavía subestiman la dificultad real de un agente.

**Eje 2 — decaimiento en contexto largo.** "Lost in the Middle" (posición) y "context
rot" (longitud) son fenómenos distintos y ambos activos en 2026: la exactitud cae
>30% cuando la información relevante está en el medio del contexto, y la degradación
por longitud ocurre incluso con la evidencia bien ubicada. "When Attention Closes"
(arXiv 2605.12922) mide una caída de 88% a 71% de adherencia a instrucciones entre el
primer y el tercer turno de una conversación multi-turno — lo llaman "instruction
forgetting". Esto es directamente relevante: una sesión larga de agente (exactamente
el escenario de este SO) es el régimen donde la atención a reglas inyectadas al
principio decae más.

**Eje 3 — fatiga de alertas.** Los datos de Vectra AI 2026 citan 2.992 alertas de
seguridad diarias promedio con 63% sin atender; el paper de Google sobre Tricorder
(Sadowski et al., CACM 2018) es la referencia canónica: el umbral que hicieron
funcionar fue <10% de falsos positivos efectivos, y el mecanismo social fue que los
propios autores de cada analizador tenían la amenaza de que su check se desactivara
si no lo cumplían. La literatura de warnings estáticos (FSE 2025, "An Empirical Study
of Suppressed Static Analysis Warnings") mide 35%-91% de warnings no accionables según
la herramienta — coherente con nuestro propio 97/215 de hooks que escriben `.jsonl`
sin ningún canal hacia el modelo: ni siquiera tienen la oportunidad de ser
accionados.

**Eje 4 — bloqueante vs advisory.** No encontré un paper que mida directamente "tasa
de acción: bloqueo vs. aviso" de forma controlada, pero la práctica de la industria
converge en un patrón de dos fases documentado en varias fuentes 2026 de DevSecOps:
"Advisory mode" primero (semanas) para que el equipo vea qué se atraparía sin romper
nada, y recién después se pasa a enforcement — es decir, la industria asume que
advisory por sí solo no cambia comportamiento, y lo usa como paso previo al bloqueo,
no como sustituto. Nuestro propio hallazgo 2 (ADR-188) es evidencia directa de la
misma lógica: WARN dos veces, BLOCK a la tercera — un diseño que ya asume que el aviso
solo no alcanza.

## Diseño de la señal: qué hace que un agente actúe

Ordenado por evidencia de efectividad, de mayor a menor:

1. **Bloqueo con código de salida + mensaje accionable** (más efectivo, confirmado en
   esta misma sesión). El costo es que un falso positivo también bloquea con la misma
   fuerza que un verdadero positivo — de ahí que el umbral de Tricorder (<10% FP) sea
   la condición para que el bloqueo no erosione confianza.
2. **Posición: al principio de la conversación, antes del primer prompt**
   (`SessionStart`, `SubagentStart` síncrono). La literatura de sesgo de posición
   (primacía/recencia) y "When Attention Closes" coinciden en que esto es más fuerte
   que insertar a mitad de una sesión larga.
3. **Sincronía, no async.** Confirmado en el propio manifiesto del harness: un hook
   async entrega en el turno siguiente, no en el actual — rompe la ventaja de
   recencia aunque el campo (`additionalContext`) sea el correcto.
4. **Especificidad y directiva vs. discrecionalidad.** "Invoke it when the workflow
   fits better than a bespoke prompt" (nuestro propio `skill-router-prompt-suggest.sh`)
   es lingüísticamente una sugerencia, no una instrucción — el propio
   `orchestrator-skill-invocation-gate.sh` (ADR-188) fue construido, evidentemente,
   porque alguien ya notó que la sugerencia sola no alcanzaba.
5. **Brevedad.** El límite documentado de `additionalContext` es 10.000 caracteres
   antes de que el harness lo trunque a un archivo — no es el techo que importa en la
   práctica; lo que importa es no competir por atención con el resto del turno.

## Cómo lo resolvieron otros harnesses

- **Codex CLI**: "MCP tools now use tool search by default" — mismo patrón de
  `ToolSearch` que usé yo mismo en esta tarea: los tools no cargan hasta pedirse. Pero
  su superficie de hooks es más angosta que la nuestra: `PreToolUse` en Codex CLI
  **solo intercepta la shell tool** — `apply_patch`, Read/Edit/Write, fetch web y
  llamadas MCP nunca disparan el hook (fuente: agenticcontrolplane.com, 2026). Un
  diseño más simple, con menos superficie para que un hook "hable" sobre una acción
  no cubierta.
- **OpenHands**: adoptó el formato `SKILL.md` con front-matter (`name`, `description`,
  `triggers`) como estándar "AgentSkills" — exactamente lo que usamos nosotros — para
  no volcar contenido completo al contexto inicial.
- **Cursor**: modelo "index-then-load" con reglas como forma de progressive
  disclosure dentro del IDE.
- El patrón común 2026 entre harnesses no-Anthropic: revelar herramientas/skills bajo
  demanda (para no inflar contexto), pero NINGUNO de los que encontré resuelve el
  problema de "cómo hago que el agente decida buscar la herramienta correcta" más allá
  de nombrarla en una lista — el mismo punto que señaló el mensaje del coordinador
  sobre mi propio caso de `ToolSearch`.

## Medición retroactiva

Sí existe, y madura rápido en 2026: "LLM-as-judge" sobre trayectorias es ya el default
práctico porque el etiquetado humano no escala al volumen de trazas que genera un
agente (Confident AI, 2026). TRACES (arXiv 2605.27690) propone auditoría proactiva
de seguridad sobre trayectorias multi-turno con benchmarks dedicados (ATBench,
ASSEBench). "Agent Drift" (arXiv 2601.04170) mide degradación de comportamiento sobre
interacciones extendidas con un índice compuesto de 12 dimensiones, incluyendo
patrones de uso de herramientas. Ninguna de las fuentes que encontré mide
específicamente "¿el agente usó la capacidad que el propio harness le ofrecía y no
usó?" como métrica aislada — lo más cercano es la línea de "tool underuse" /
autoconciencia de herramientas (arXiv 2606.20661, "From Knowing to Acting"), que
formaliza el límite entre capacidad interna y necesidad de herramienta externa, pero
mira decisiones de uso dentro de una tarea, no adopción de un mecanismo del propio
harness a través de sesiones. Este es un hueco real: nuestra propia
`skill-suggestion.jsonl` + `skill-invocations.jsonl` cruzadas (lo que hice en este
informe) es, hasta donde pude buscar, un patrón de medición retroactiva de adopción
de capacidades de harness que no encontré descrito en la literatura — podría ser un
aporte, no solo una aplicación de algo ya publicado.

## Caso de estudio: capacidad no-descubierta vs. capacidad ignorada

El coordinador pidió, en medio de la tarea, una forma empírica de distinguir estos dos
casos — ambos producen "0 invocaciones" en telemetría pero exigen arreglos opuestos.
Con lo que verifiqué en el código de los hooks propongo tres preguntas, en orden, que
sí se pueden correr como script sobre cualquier mecanismo del repo:

1. **¿El mecanismo escribe en algún campo que el harness documenta como
   model-facing?** (`hookSpecificOutput.additionalContext`, `decision`, o el listado
   de tools deferred en el system-reminder). Si la respuesta es no —como en 97 de
   nuestros 215 hooks— es **no-descubrible por construcción**: ningún agente, por
   atento que esté, puede reaccionar a algo que nunca llegó. Este es el caso que la
   hipótesis original del encargo describe correctamente.
2. **Si sí escribe ese campo, ¿el registro en `settings.json` es `async: true`?** Si
   lo es, el propio manifiesto del harness dice que la entrega se retrasa al turno
   siguiente — funcionalmente indistinguible de "no descubierto" para la acción que
   se necesitaba EN ese turno, aunque en sentido estricto el dato exista en algún
   turno posterior. Es el caso de `skill-router-prompt-suggest.sh`: el campo correcto,
   en el evento correcto, pero con el temporizador equivocado.
3. **Si es síncrono y con el campo correcto, ¿el texto es una directiva o una
   sugerencia discrecional?** Acá ya no es un problema de canal sino de redacción —
   el caso que de verdad es "ignorado" en el sentido fuerte del término.

Aplicado a las 102 sugerencias >=0.90 de confianza: fallan en el paso 2 (`async:
true` en `UserPromptSubmit`) Y en el paso 3 (redacción discrecional) simultáneamente
— alcanza con cualquiera de los dos para explicar 0/102 sin necesitar apelar a que
"el modelo no le importó". Mi propio caso de `ToolSearch` es distinto de los tres:
pasa el paso 1 (el listado de deferred tools SÍ es un campo model-facing, inyectado al
principio de la sesión — posición fuerte) y pasa el 2 (no depende de async, está en
el system-reminder inicial), pero el texto es una lista de nombres sin instrucción de
acción — más débil que una directiva pero más fuerte que el silencio. Lo resolví
porque ya conocía el patrón `ToolSearch(select:...)` de antes, no porque el mensaje me
lo dijera explícitamente. Esa es la distinción operativa: una capacidad puede pasar
los tres tests y aun así depender de que el modelo ya sepa qué hacer con un nombre —
ahí el arreglo no es de canal ni de redacción, es de que la propia lista declare la
acción ("nombre → llamar ToolSearch con esta query exacta"), no solo el nombre.

## Mecanismos aplicables a nuestro caso

Ordenados por (efectividad esperada / costo de contexto), con costo declarado en
tokens por turno:

1. **Reescribir el texto de `skill-router-prompt-suggest.sh` de discrecional a
   directivo, y sacarle `async: true`.** Costo: **~0 tokens adicionales por turno** —
   es el mismo `additionalContext` que ya se emite hoy (una línea, ~30 palabras),
   solo cambia la redacción y el momento de entrega. Efectividad esperada alta: es
   exactamente el patrón que ADR-188 ya asume que hace falta (por eso existe el gate),
   y ya tenemos 102 muestras de que la versión discrecional no funcionó.
2. **Arreglar el bug de auditoría de `orchestrator-skill-invocation-gate.sh`**
   (agregar `_emit_audit` a la rama `count -ge 3`, y resolver `session_id="unknown"`
   pasando el ID real). Costo: **0 tokens de contexto por turno** — es un fix de
   logging en un hook que ya corre, no toca lo que el modelo ve. El gate YA bloquea
   (contador en 131); esto solo lo hace auditable, que es tener evidencia ejecutable
   de algo que hoy es un acto de fe.
3. **Para los 97 hooks jsonl-only sin canal: emitir `additionalContext` SOLO cuando
   hay hallazgo, nunca en el caso vacío.** Costo: **0 tokens en el caso común** (nada
   que decir, no se emite nada) y ~20-40 tokens en el caso raro con hallazgo. Esto
   evita el error inverso — inflar cada turno con ruido — que el propio encargo
   señaló como la preocupación del operador.
4. **No usar `async: true` en `Stop` para hooks cuyo hallazgo se supone que el
   agente vea** (caso `quality-duplicates.sh`). Costo: variable — si se pasa a
   síncrono, ese costo ya no es de contexto sino de latencia de turno (hoy p50 2.7
   min sobre 39 muestras: `.cognitive-os/metrics/hook-timing.jsonl`, hook
   `quality-duplicates`). No lo recomiendo sin antes resolver la latencia; lo
   incluyo para que quede explícito que "sacarle el async" sin arreglar la
   performance cambiaría un hook invisible por uno que bloquea 2-4 minutos cada
   `Stop` — un costo peor que el que resuelve.

## Fuentes

Numeradas; fecha de publicación cuando la tenía la página, y una línea de relevancia.
Marcadas `[2026]` las que son de este año.

1. [IH-Benchmark: A Conflict-Centered Benchmark for Instruction-Hierarchy Robustness](https://arxiv.org/html/2607.25987v1) — [2026] benchmark de conflictos entre capas de instrucción, 2336 escenarios.
2. [Many-Tier Instruction Hierarchy in LLM Agents](https://arxiv.org/html/2604.09443v1) — [2026] jerarquía extendida a agentes multi-capa.
3. [LLM Benchmarks 2026: MMLU, GPQA, SWE-Bench & Arena Compared](https://datavlab.ai/post/llm-benchmarks-2026-which-model-for-which-job) — [2026] panorama de benchmarks vigentes.
4. [IFHierBench: Hierarchical Instruction Following for LLMs](https://arxiv.org/html/2607.27912) — [2026] cumplimiento jerárquico de restricciones de salida.
5. [arXiv:2505.16944 — SysBench](https://arxiv.org/pdf/2505.16944) — [2025] 500 system messages, 5 rondas de conversación c/u.
6. [How LLMs Follow Instructions: Skillful Coordination, Not a Universal Mechanism](https://arxiv.org/html/2604.06015) — [2026] mecanismo interno de seguimiento de instrucciones.
7. [AGENTIF: Benchmarking Instruction Following of LLM Agents](https://keg.cs.tsinghua.edu.cn/persons/xubin/papers/AgentIF.pdf) — benchmark agéntico específico.
8. [SOPBench: Evaluating Agents at Following SOPs and Constraints](https://arxiv.org/pdf/2503.08669) — [2025] agentes siguiendo procedimientos operativos.
9. [FollowBench: Multi-level Fine-grained Constraints Following Benchmark](https://www.researchgate.net/publication/384215065_FollowBench_A_Multi-level_Fine-grained_Constraints_Following_Benchmark_for_Large_Language_Models) — restricciones finas multinivel.
10. [CompliBench: Benchmarking LLM Judges for Compliance Violation Detection](https://arxiv.org/html/2604.12312v1) — [2026] jueces LLM detectando violaciones de compliance.
11. [The Cognitive Divergence: AI Context Windows, Human Attention Decline, and the Delegation Feedback Loop](https://arxiv.org/pdf/2603.26707) — [2026] contexto largo y atención humana delegada.
12. [Context Rot, RAG, and Long Context: How to Architect LLM Systems in 2026](https://glasp.co/articles/context-rot-rag-long-context-hybrid) — [2026] arquitectura híbrida RAG + contexto largo.
13. [Context rot explained (& how to prevent it) — Redis](https://redis.io/blog/context-rot/) — explicación práctica de context rot.
14. [Lost-in-the-Middle Problem: Why Context Position Matters — Atlan](https://atlan.com/know/llm/lost-in-the-middle-problem/) — resumen del fenómeno de posición.
15. [When Attention Closes: How LLMs Lose the Thread in Multi-Turn Interaction](https://arxiv.org/pdf/2605.12922) — [2026] caída de 88%→71% de adherencia entre turno 1 y 3.
16. [Context Rot: Why LLMs Degrade as Context Grows — Morph](https://www.morphllm.com/context-rot) — guía de degradación por longitud.
17. [Context Rot: Why Long-Context LLMs Degrade — TMLS](https://www.tmls.nyc/research/context-rot-mechanistic) — mecanismo de degradación explicado.
18. [Long-Context Retrieval 2026: Needle-in-Haystack Test](https://www.digitalapplied.com/blog/long-context-retrieval-needle-in-haystack-2026) — [2026] estado del arte de retrieval por posición.
19. [NoLiMa: Long-Context Evaluation Beyond Literal Matching](https://arxiv.org/html/2502.05167v2) — [2025] evaluación de contexto largo sin matching literal.
20. [Context Discipline and Performance Correlation](https://arxiv.org/pdf/2601.11564) — [2026] correlación entre disciplina de contexto y performance.
21. [Paper review: Lessons from Building Static Analysis Tools at Google](https://medium.com/sourcedtech/paper-review-lessons-from-building-static-analysis-tools-at-google-cc71a43bdee) — resumen de Tricorder.
22. [Lessons from Building Static Analysis Tools at Google — CACM](https://cacm.acm.org/research/lessons-from-building-static-analysis-tools-at-google/) — [2018] paper canónico, umbral <10% falsos positivos.
23. [Tricorder — Abseil SWE Book](https://abseil.io/resources/swe-book/html/ch20.html) — capítulo del libro de ingeniería de software de Google.
24. [Tricorder: Building a Program Analysis Ecosystem](https://research.google.com/pubs/archive/43322.pdf) — paper ICSE 2015 original.
25. [What Is Alert Fatigue? — Vectra AI](https://www.vectra.ai/topics/alert-fatigue) — [2026] 2.992 alertas/día promedio, 63% sin atender.
26. [Alert fatigue solutions for DevOps teams in 2025](https://incident.io/blog/alert-fatigue-solutions-for-dev-ops-teams-in-2025-what-works) — [2025] soluciones prácticas de fatiga de alertas.
27. [Pre-Commit vs CI Quality Gates — Codacy](https://blog.codacy.com/pre-commit-vs-ci-quality-gates-when-fast-shipping-moves-the-checks-upstream) — comparación de gates locales vs. CI.
28. [What is Pre-commit Hook? — DevSecOps School](https://devsecopsschool.com/blog/pre-commit-hook/) — [2026] modo advisory antes de enforcement, patrón de adopción por fases.
29. [System reminders — how Claude Code steers itself](https://michaellivs.com/blog/system-reminders-steering-agents/) — mecanismo de system-reminder del harness que uso.
30. [Automate actions with hooks — Claude Code Docs](https://code.claude.com/docs/en/hooks-guide) — documentación oficial citada por nuestro propio manifiesto.
31. [Bug: Hook additionalContext injected multiple times — anthropics/claude-code#14281](https://github.com/anthropics/claude-code/issues/14281) — bug reportado sobre el mismo mecanismo que analizo.
32. [Agent Skills & Context — OpenHands Docs](https://docs.openhands.dev/sdk/guides/skill) — formato SKILL.md adoptado por otro harness.
33. [Agent Harness Engineering — Addy Osmani](https://addyosmani.com/blog/agent-harness-engineering/) — panorama de diseño de harnesses.
34. [TRACES: Proactive Safety Auditing for Multi-Turn LLM Agents via Trajectory-State Modeling](https://arxiv.org/html/2605.27690v1) — [2026] auditoría de trayectorias multi-turno.
35. [LLM Agent Evaluation Metrics in 2026 — Confident AI](https://www.confident-ai.com/blog/llm-agent-evaluation-complete-guide) — [2026] LLM-as-judge como default práctico.
36. [LLM-as-Judge Patterns for Agent Evaluation — Zylos Research](https://zylos.ai/research/2026-05-26-llm-as-judge-agent-evaluation-patterns/) — [2026] calibración y sesgo de jueces LLM.
37. [An Empirical Study of Automating Agent Evaluation](https://arxiv.org/pdf/2605.11378) — [2026] automatización de evaluación de agentes.
38. [From Knowing to Acting: Benchmarking Self-Awareness Capability of LLM Agents](https://arxiv.org/pdf/2606.20661) — [2026] frontera entre capacidad interna y necesidad de herramienta.
39. [SMART: Self-Aware Agent for Tool Overuse Mitigation](https://arxiv.org/pdf/2502.11435) — [2025] reducción de sobreuso de herramientas.
40. [IH-Challenge: A Training Dataset to Improve Instruction Hierarchy — OpenAI](https://cdn.openai.com/pdf/14e541fa-7e48-4d79-9cbf-61c3cde3e263/ih-challenge-paper.pdf) — dataset de entrenamiento de jerarquía de instrucciones.
41. [The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions](https://arxiv.org/html/2404.13208v1) — [2024] paper fundacional (Wallace et al.), System > User > Model > Tool.
42. [IHEval: Evaluating Language Models on Following the Instruction Hierarchy](https://arxiv.org/pdf/2502.08745) — [2025] benchmark abierto de jerarquía.
43. [Improving instruction hierarchy in frontier LLMs — OpenAI](https://openai.com/index/instruction-hierarchy-challenge/) — anuncio oficial del challenge.
44. [An Empirical Study of Suppressed Static Analysis Warnings — FSE 2025](https://people.ece.ubc.ca/mjulia/publications/Suppressed_Static_Analysis_Warnings_FSE2025.pdf) — [2025] por qué se suprimen warnings.
45. [A Large-Scale Collection of (Non-)Actionable Static Code Analysis Reports](https://arxiv.org/pdf/2511.10323) — [2025] 35-91% de warnings no accionables.
46. [Quieting the Static: A Study of Static Analysis Alert Suppressions](https://arxiv.org/pdf/2311.07482) — patrones de supresión de alertas.
47. [LLM Position Bias: Primacy and Recency Effects in Prompts — IntuitionLabs](https://intuitionlabs.ai/articles/llm-position-bias-primacy-recency-effects) — sesgo de posición aplicado a diseño de prompts.
48. [Codex CLI MCP Integration — Codex Knowledge Base](https://codex.danielvaughan.com/2026/03/26/codex-cli-mcp-integration/) — [2026] tool search por defecto en Codex CLI.
49. [Codex CLI Hooks Reference — hooks.json, PreToolUse & PostToolUse](https://agenticcontrolplane.com/blog/codex-cli-hooks-reference) — [2026] PreToolUse de Codex solo intercepta la shell tool.
50. [Agent Drift: Quantifying Behavioral Degradation in Multi-Agent LLM Systems](https://arxiv.org/abs/2601.04170) — [2026] índice compuesto de degradación de comportamiento agéntico.
51. [AgentForesight: Online Auditing for Early Failure Prediction in Multi-Agent Systems](https://arxiv.org/abs/2605.08715) — [2026] auditoría online de fallas tempranas.

## Verificación de estado del repo (freeze y alcance)

Confirmado por lectura directa (no por memoria): `manifests/external-tool-adoption-freeze.yaml`
tiene `frozen: true` desde 2026-05-11. No propuse adoptar ni vendorizar código de
terceros en ningún mecanismo de la sección anterior — todo lo propuesto son cambios de
redacción, registro (`async`) y logging sobre hooks que ya existen en este repo.

---

TRUST_REPORT: SCORE=82 STATUS=HIGH EVIDENCE=huge UNCERTAINTIES=3
---
WHAT I VERIFIED (con comando):
- `find hooks -maxdepth 1 -name "*.sh" -type f | wc -l` → 215.
- `grep -c 'rate-limiter' .claude/settings.json` → 0 (confirma rules/rate-limiting.md).
- `python3 ... skill-suggestion.jsonl confidence>=0.90` → 102, exacto al encargo.
- `grep -c hook-timing .cognitive-os/metrics/skill-suggestion.jsonl` → 16, exacto al encargo.
- `wc -l .cognitive-os/metrics/skill-invocations.jsonl` → 6, contradice el "0" literal del encargo.
- `cat .cognitive-os/runtime/skill-bypass-counter-unknown` → 131, con `skill-bypass.jsonl` inexistente — bug de auditoría confirmado leyendo el código fuente del hook.
- p50 real de `quality-duplicates` sobre 39 muestras de `hook-timing.jsonl` → 164407ms = 2.74 min (encargo decía "~3.0 min", confirmado en orden de magnitud, no exacto).
- Leí `manifests/claude-code-hooks-schema.yaml` completo en las secciones citadas — no resumido de memoria.

UNSURE ABOUT:
- No reproduje el "148 hooks con telemetría / 130 incapaces de denegar" exacto del
  encargo con un método que dé esos números literales — mi conteo (215 total / 85
  no-bloqueantes por evento) es del mismo orden pero no idéntico; puede haber una
  definición distinta de "con telemetría" que no reconstruí.
- No confirmé si `context_budget_filter_json` (llamado dentro de
  `skill-router-prompt-suggest.sh` antes de emitir el resultado) descarta o recorta el
  `additionalContext` bajo presión de presupuesto — si lo hace, algunas de las 102
  sugerencias pueden no haber llegado al modelo ni siquiera en el turno siguiente,
  lo que sumaría un tercer motivo de fallo en vez de solo dos.
- El contador `skill-bypass-counter-unknown=131` agrega sesiones con `session_id`
  sin setear; no puedo decir cuántas sesiones DISTINTAS lo generaron, ni si el
  bloqueo (`exit 2`) llegó a mostrarse al operador humano alguna vez o solo a
  sub-agentes que lo absorbieron sin reportarlo.

HUMAN SHOULD CHECK:
- Si vale la pena priorizar el fix de `orchestrator-skill-invocation-gate.sh` (2
  líneas: `_emit_audit` en la rama BLOCK + pasar `session_id` real) antes que
  cualquier otro cambio de este informe — es el que menos toca superficie y el que
  más evidencia ejecutable recupera.
- Si el bug de parsing de `protected-config-write-guard.sh` (sustitución de proceso
  con tubería adentro) amerita spawnear una tarea aparte — lo dejé anotado, no
  arreglado.
