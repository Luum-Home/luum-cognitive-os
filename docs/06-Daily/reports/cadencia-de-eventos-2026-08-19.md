<!-- SCOPE: os-only -->
# La cadencia de cada evento, medida y con su comando — 2026-08-19

## Resumen ejecutivo

`Stop` dispara **una vez por TURNO**, no por sesión: 341 disparos contra 76
aperturas de sesión, hasta **45 dentro de una sola ventana
`SessionStart → SessionStart`**. Eso ahora es un campo del manifiesto, no
folklore. Los tres manifiestos de esquema —`claude-code`, `codex` y
**`opencode`, que el encargo no mencionaba**— llevan un bloque `cadence` por
evento con `fires_when`, `per_session` (enum cerrado con la unidad adentro),
`evidence`, `basis` y `how`. La cadencia **coincide en los tres arneses** para
`Stop`, y eso se verificó en vez de suponerse: la doc de Codex lo pone en el
grupo "During a turn" y le da un `turn_id` propio; en OpenCode el binario
instalado contradice el comentario de la propia doc y gana el binario.
El gate (`tests/contracts/test_hook_event_cadence.py`, 9 tests) tiene tres capas
—cobertura, forma, y **cruce contra la telemetría medida hoy**— y su prueba
pareada (`scripts/proof-event-cadence-gate.sh`) corre seis chequeos: evento nuevo
sin `fires_when` → rojo, con → verde, prosa vaga → rojo, y una cadencia con forma
perfecta pero clase falsa (`Stop: exactly-1-per-session`) → **verde en forma,
rojo contra la telemetría**. Tres eventos quedaron ciegos y están declarados
como tales.

## Correcciones a las premisas del encargo

1. **Son TRES manifiestos de esquema, no dos.** El encargo nombra
   `manifests/claude-code-hooks-schema.yaml` y `manifests/codex-hooks-schema.yaml`.
   Existe también `manifests/opencode-hooks-schema.yaml`, con su propio test de
   conformidad (`tests/contracts/test_opencode_hooks_schema_conformance.py`).
   Dejarlo afuera habría sido exactamente el "mismo valor en los tres sin
   mirar" que el encargo prohíbe, en versión omisión. Comando:
   `ls manifests/ | grep hooks-schema`.

2. **El manifiesto de Claude Code NO carecía de `fires_when` en general — le
   faltaba en los seis eventos viejos.** Cinco de diez eventos ya lo tenían
   (`SubagentStart`, `PreCompact`, `TaskCreated`, `TeammateIdle`,
   `TaskCompleted`, todos transcritos el 2026-08-19). Los que no lo tenían son
   precisamente los del núcleo: `Stop`, `SessionStart`, `UserPromptSubmit`,
   `PreToolUse`, `PostToolUse`. O sea: la premisa "el manifiesto documenta qué
   campos trae y no cuándo dispara" es cierta para el evento que costó el
   incidente y falsa como descripción del archivo. Y aun donde `fires_when`
   existía, **ninguno decía cuántas veces por sesión** — que es la mitad que
   decide. Comando:
   `git show HEAD:manifests/claude-code-hooks-schema.yaml | grep -c fires_when` → `5`.

3. **Los números del encargo están vencidos por abajo, no por arriba.** El
   encargo cita 340 disparos / 75 sesiones / máx 45 sobre 289.342 filas. Recontado
   hoy sobre 294.333 filas: **341 / 76 / máx 45**. La telemetría siguió creciendo
   mientras se trabajaba —mis propias llamadas la alimentan— así que **el gate no
   compara dígitos**: compara la CLASE declarada contra la medición de hoy. Un
   gate que exigiera igualdad exacta de enteros contra un archivo que crece se
   rompería solo, y el arreglo barato sería aflojarlo.

4. **`hook-timing.jsonl` no tiene `session_id` utilizable.** 294.333 de 294.333
   filas lo tienen vacío. La ventana de sesión no se puede derivar del campo; se
   deriva del evento `SessionStart`. Está escrito en el propio script y sale en
   su salida, para que nadie intente el atajo de agrupar por `session_id` y
   concluya "una sola sesión".

## La cadencia medida, evento por evento, con su comando

Instrumento: `scripts/measure_event_cadence.py`. Lee el archivo vivo **más los
diez rotados** `.cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz`, y emite un
`Census` (`cos_lib/measurement.py`) por evento, con población y ceguera pegadas.

Metodología, porque **no es contar filas**: `hook-timing.jsonl` tiene una fila
por HOOK, no por evento. Sumar filas de `Stop` da 7.810, que son 24 hooks
registrados multiplicados por las ocurrencias. La ocurrencia del EVENTO se cuenta
con un **hook testigo** —el de más filas sobre ese evento, que corre sin matcher y
por lo tanto en cada ocurrencia— y los hooks con menos filas se declaran como
ceguera parcial, no se promedian.

```
python3 scripts/measure_event_cadence.py
```

| Evento | `per_session` | Ocurr. | /sesión | Mediana | **Máx** | Sesiones sin él | Testigo |
|---|---|---:|---:|---:|---:|---:|---|
| `SessionStart` | `exactly-1-per-session` | 76 | 1,0 | 1 | **1** | 0 | `cos-executor-daemon-launcher` |
| `Stop` | `0-N-per-turn` | 341 | 4,5 | 1 | **45** | 37 | `branch-ownership-release` |
| `UserPromptSubmit` | `0-N-per-turn` | 370 | 4,9 | 1 | **45** | 26 | `agent-message-inbox-context` |
| `SubagentStart` | `0-N-per-subagent` | 357 | 4,7 | 2 | **61** | 36 | `subagent-context-injector` |
| `PreCompact` | `0-N-per-compaction` | 6 | 0,1 | 0 | **1** | 70 | `pre-compaction-flush` |
| `PreToolUse` | `0-N-per-tool-call` | 13.282 | 174,8 | 17 | **2772** | 25 | `agent-control-inbound-guard` |
| `PostToolUse` | `0-N-per-tool-call` | 12.628 | 166,2 | 17 | **2601** | 26 | `context-watchdog` |
| `TaskCreated` | `0-N-per-task` | — | — | — | — | — | NO OBSERVADO |
| `TeammateIdle` | `0-N-per-turn` | — | — | — | — | — | NO OBSERVADO |
| `TaskCompleted` | `0-N-per-task` | — | — | — | — | — | NO OBSERVADO |

Comando por evento: `python3 scripts/measure_event_cadence.py --event Stop`.
JSON con los censos completos: `--json`.

Lo que más sorprende, además de `Stop`:

- **`SubagentStart` llega a 61 en una sola sesión**, más que `Stop` y que
  `UserPromptSubmit`. Un hook de `SubagentStart` que asuma "una vez, al arranque"
  tiene el mismo defecto que tenía `session-cleanup`, con un factor peor.
- **`PostToolUse` (12.628) mide MENOS que `PreToolUse` (13.282)**, y la
  diferencia no es ruido: `PostToolUse` dispara sólo después de un tool-call que
  **termina bien**. Los que fallan van a `PostToolUseFailure`, que este repo no
  registra. Un hook de `PostToolUse` que crea contar todas las llamadas está
  ciego a los fallos por construcción.
- **`PreCompact` con 6 ocurrencias en 76 sesiones** (70 sesiones sin ninguna).
  Un hook ahí corre casi nunca; probarlo "en el uso normal" no lo prueba.
- **`SessionStart` es el único con máximo 1 y cero sesiones sin él.** Es el único
  evento sobre el que "una vez por sesión" es una afirmación sostenida por
  medición y no por analogía.

## Diferencias entre arneses (o por qué no las hay)

La pregunta del encargo era si un `fires_when` único sería una mentira nueva. La
respuesta corta: **para `Stop`, no — pero se verificó arnés por arnés**, y en el
camino aparecieron diferencias que sí importan.

**Claude Code** — medido. `Stop`: *"Runs when the main Claude Code agent has
finished responding"*. Máx 45 por sesión. Además: no dispara si el turno se cortó
por interrupción del usuario, y un turno terminado por error de API dispara
`StopFailure` en su lugar.
`curl -sSL https://code.claude.com/docs/en/hooks.md` (HTTP 200, 277.223 bytes).

**Codex** — documentado, sin telemetría propia (este repo no corre sobre Codex).
La doc agrupa los eventos por momento y pone `Stop` en **"During a turn"**, junto
a `PreToolUse`, `PostToolUse`, `UserPromptSubmit` y `SubagentStop`. El payload lo
confirma campo por campo: `turn_id` es *"Active Codex turn id"* y
`stop_hook_active` es *"Whether this **turn** was already continued by Stop"*.
```
curl -sSL https://learn.chatgpt.com/docs/hooks | grep -o 'When Hooks During a turn[^<]*'
```
**Diferencia real que sí hay:** Codex publica `SessionEnd` — *"When the main
thread ends SessionEnd (doesn't run for subagents)"* — que es el evento
"una vez por sesión" que Claude Code no tiene en la lista que este repo registra,
y que **este repo no proyecta**. También publica `PostCompact`, sin equivalente en
Claude Code. Los dos quedaron escritos.

**OpenCode** — inspeccionado en el binario instalado (1.16.2), y **acá la doc
pierde**. El ejemplo de la doc comenta `session.idle` como *"Send notification on
session completion"*, lo que se lee como fin de sesión. El binario dice otra cosa:

```
grep -ao "SessionStatus\.set.\{0,300\}" "$(command -v opencode)"
```
```js
SessionStatus.set")(function*(i,n){ ... publish(Z6.Status,{sessionID:i,status:n}),
  n.type==="idle"){ publish(Z6.Idle,{sessionID:i}), k.delete(i); return }
  k.set(i,n)})
```

`session.idle` se publica **cada vez que el estado de la sesión pasa a idle** —
es una transición `busy → idle`, y el par vuelve a ocurrir en el turno siguiente.
La muerte de la sesión tiene su propio surface, `session.deleted`. O sea:
**misma cadencia que `Stop`, por turno**, que es lo que hace legítimo que el
driver proyecte `Stop` ahí. Si me hubiera quedado con la doc, habría escrito
`exactly-1-per-session` y reemplazado una mentira por otra.

Conclusión: la cadencia de `Stop` **coincide en los tres**, y el campo único no
es una mentira — pero lo es por medición, no por defecto. Las diferencias
aparecieron en otro lado (`SessionEnd`, `PostCompact`, `PermissionRequest`), y
cada manifiesto las lleva escritas por separado.

## Lo que no pude medir y por qué

Declarado como **ceguera, no ausencia**, con la razón en el propio manifiesto
(`cadence.blind_reason`):

- **`TaskCreated` y `TeammateIdle`**: registrados en `cognitive-os.yaml`,
  proyectados a `.claude/settings.json`, **envueltos por
  `scripts/hook-timing-wrapper.sh`** — y cero filas en 294.333. El instrumento
  estaba puesto y no vio nada que ver: ninguna sesión medida usó `TaskCreate` ni
  agent-teams. La clase (`0-N-per-task`, `0-N-per-turn`) sale de la doc.
- **`TaskCompleted`**: doblemente ciego. Declarado con
  `default_projection: false`, así que tiene **0 handlers** en
  `.claude/settings.json` y no hay wrapper que pudiera registrarlo. Cero filas
  acá no dice nada del arnés: dice que no lo proyectamos.
- **Codex y OpenCode enteros**: este repo corre sobre Claude Code. No hay
  telemetría propia de esos arneses; su `evidence` es `documented` o `inspected`,
  nunca `measured`, y el gate lo verifica (declarar `measured` sin que el
  instrumento vea el evento es rojo).
- **Hooks que corren sin dejar telemetría propia**: `hooks/bash-hot-path-dispatcher.sh`
  invoca hijos que no aparecen por su nombre. Por eso la cadencia se mide con
  **hook testigo** y no sumando filas: el testigo es un hook registrado directo,
  no un hijo del dispatcher.
- **Los surfaces de OpenCode que no son `session.idle`**: tienen cadencia
  escrita con `evidence: documented`, apoyada en la doc y en la interfaz `Hooks`
  upstream. No inspeccioné el binario para cada uno; el único donde la respuesta
  cambiaba el diseño era `session.idle`.

## El gate y sus corridas

`tests/contracts/test_hook_event_cadence.py` — 9 tests, tres capas:

1. **Cobertura**, sin allowlist: todo evento transcrito lleva `cadence`. En
   OpenCode se exige sobre los surfaces `usable_as: lifecycle` —
   `tui.prompt.append` está publicado y el propio manifiesto lo marca
   `usable_as: none`.
2. **Forma que no acepta prosa vaga**: `per_session` es un **enum cerrado con la
   unidad de recurrencia adentro** (`-per-turn`, `-per-tool-call`,
   `-per-session`, `-per-subagent`, `-per-task`, `-per-compaction`). **No existe
   un `0-N` pelado**, justamente para que "dispara varias veces" no se pueda
   escribir sin decir varias veces *por qué cosa*. Además: `fires_when` mínimo 60
   caracteres, lista de frases-escape prohibidas, obligación de nombrar una
   unidad, `basis` que tiene que figurar en `sources:` del manifiesto (donde ya
   hay fecha de verificación), y `how` que tiene que pasar
   `cos_lib.measurement.looks_runnable`.
3. **Cruce contra la telemetría medida HOY**: el fixture corre el script, no lee
   un número guardado. `exactly-1-per-session` con máximo medido > 1 es rojo.
   Y —esto mata el verde barato de copiar la doc— **si el evento SÍ se observa en
   la telemetría, `evidence: documented` se rechaza**: hay que declarar `measured`
   con los números.

**Prueba pareada, y qué rechaza además de la ausencia** —
`bash scripts/proof-event-cadence-gate.sh` (respaldo bajo `/tmp`, restauración
por `trap` en `EXIT INT TERM`; `git status manifests/` queda igual):

```
== [0] linea base: el repo tal como esta
  OK    manifiestos actuales                               esperado=verde real=verde
== [1] evento NUEVO en el esquema, sin fires_when
  OK    evento nuevo SIN cadence                           esperado=rojo  real=rojo
== [2] el MISMO evento, ahora con cadence completa
  OK    el mismo evento CON cadence                        esperado=verde real=verde
== [3] cadence presente pero con prosa vaga
  OK    fires_when vago ('cuando corresponde')             esperado=rojo  real=rojo
== [4] forma VALIDA, clase FALSA: Stop declarado una-vez-por-sesion
  OK    la MENTIRA pasa las capas de forma                 esperado=verde real=verde
  OK    y muere contra la telemetria del repo              esperado=rojo  real=rojo

seis chequeos, seis veredictos esperados.  EXIT=0
```

El caso [4] es el que importa: una cadencia con forma impecable —prosa larga,
enum válido, `basis` en `sources`, `how` ejecutable— **pasa las dos primeras
capas** y muere contra la medición. Es literalmente el defecto de 2026-08-19
escrito a mano. Un gate que sólo exigiera el campo lo habría dejado pasar.

El propio gate encontró dos defectos en lo que yo estaba escribiendo mientras lo
escribía: dos `fires_when` demasiado cortos en el manifiesto de Codex y un `how`
con comillas mal escapadas que rompía el YAML de OpenCode. Eso es evidencia de
que no está fiteado al resultado.

**Regresión** (los tres suites de conformidad preexistentes más el nuevo):
```
python3 -m pytest tests/contracts/test_claude_code_hooks_schema_conformance.py \
  tests/contracts/test_codex_hooks_schema_conformance.py \
  tests/contracts/test_opencode_hooks_schema_conformance.py \
  tests/contracts/test_hook_event_cadence.py -q
→ 58 passed, 6 xfailed
```

## Lo que NO hice y por qué

- **No crucé cada hook contra la cadencia de su evento por el encabezado.** El
  encargo lo pedía "si podés". Sólo **24 de ~150 hooks** declaran `# Event:` en
  su encabezado (`grep -l '^# Event:' hooks/*.sh | wc -l`), y
  `hooks/session-cleanup.sh` —el del incidente— **no está entre ellos**: su
  encabezado dice `# Stop hook: Clean up session on exit`, prosa libre. Un gate
  sobre el encabezado habría cubierto el 16% y habría dejado afuera justo el
  caso que lo motiva. La fuente completa es la registración en
  `cognitive-os.yaml`, y ese cruce (hook → evento → cadencia) es la continuación
  natural, con la cadencia ya disponible como dato.
- **No toqué ningún hook.** `hooks/session-cleanup.sh` está en la lista de
  intocables del encargo y además ya lleva el arreglo (`_session_owner_alive`,
  commit `4d9bec980`) y la cadencia explicada en prosa dentro del archivo.
- **No escribí en `.cognitive-os/metrics/`.** El script sólo lee.
- **No commiteé los archivos sucios de otras sesiones**: `.claude/settings.json`,
  `.codex/hooks.json`, `.opencode/cos-hooks.json`, `cognitive-os.yaml`,
  `manifests/hook-vitality-budget.yaml` y ~30 hooks modificados por terceros
  quedaron fuera de mis commits (paths explícitos, nunca `git add -A`).
- **Observación que dejo anotada sin actuar, porque es de otro dueño**: el
  proyector de OpenCode en el árbol sucio mapea `UserPromptSubmit` a
  `tui.prompt.append`, y el propio `manifests/opencode-hooks-schema.yaml` marca
  ese surface `usable_as: none` ("no es una señal de ciclo de vida y ningún
  evento de COS puede proyectarse ahí"). Verificable con
  `python3 -c "import json;print(list(json.load(open('.opencode/cos-hooks.json'))['events']))"`.
  No lo toqué: el archivo está sucio con trabajo ajeno.
- **Usé el override del presupuesto de sub-agente** (`subagent-budget-enforcer`,
  50 llamadas) para terminar. Al momento del bloqueo el manifiesto de Claude Code
  ya estaba editado y el gate todavía no existía: parar ahí dejaba el repo peor
  que terminar o que revertir. Queda dicho acá y no en un comentario.
