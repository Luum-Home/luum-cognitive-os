# Juicio: la lógica de `orchestrator-skill-invocation-gate.sh` (ADR-188)

Fecha: 2026-08-20 · Rol: juez (read-only) · Repo: luum-agent-os

## Veredicto

**HAY QUE RECONSTRUIRLA.** La lógica está rota en una rama que nadie miró —el gate
no evalúa la sugerencia del prompt actual sino el **máximo histórico de todo el
log**, hoy una fila del 3 de julio— y encima la política del conteo acumulado
castiga la sesión larga en vez de la mala conducta. Aislar la identidad de sesión
—lo que está haciendo el implementador— arregla la contaminación y deja el gate
**inerte**, no correcto.

## Correcciones a las premisas del encargo

1. **No son 11 filas, son 12; y N no es 142, es 143.**
   `wc -l < .cognitive-os/metrics/skill-bypass.jsonl` → `12`;
   `cat .cognitive-os/runtime/skill-bypass-counter-unknown` → `143`.
   La fila 12 es de `2026-08-20T04:51:34Z`, posterior a la medición del encargo.

2. **El contador no es de esta sesión ni de esta semana: nació el 2026-05-18.**
   `stat -f 'birth=%SB mtime=%Sm' .cognitive-os/runtime/skill-bypass-counter-unknown`
   → `birth=May 18 13:13:47 2026  mtime=Aug 20 01:51:34 2026`. 94 días, 143
   incrementos, sin un solo reset en todo el repo
   (`grep -rn "skill-bypass-counter" . --exclude-dir=.git` → solo el hook, dos
   tests y reportes; **ningún** código que borre o baje el contador).

3. **«Anotar el bypass es imposible» es FALSO como está enunciado — y VERDADERO
   en la forma que prescribe ADR-188.** Ver la sección siguiente: la anotación se
   lee del `tool_input`, no del transcript. Puesta ahí, funciona (sonda, caso 3).
   Lo que no puede funcionar es lo que el ADR manda literalmente: *«emit a
   one-line `SKILL_BYPASS:` annotation **in the assistant response**»*
   (`ADR-188-mandatory-skill-invocation-at-high-confidence.md:76-79`). Un
   PreToolUse no ve la respuesta del asistente. **El ADR y el hook no describen
   el mismo mecanismo.**

4. **«`session_id` vacío en 296.383 de 296.383 filas» no lo pude reproducir.** Lo
   que sí medí: `hook-timing.jsonl` tiene **4.920 filas y 4.920 con `session_id`
   vacío** (100%); pero en el conjunto de la telemetría —126 archivos JSONL de
   `.cognitive-os/metrics/` y `.cognitive-os/sessions/`— hay **58.933 filas con
   campo `session_id` y 49.068 no vacías (83%)**. La afirmación global no se
   sostiene; la del hook-timing sí. Y en los dos logs que el gate realmente lee el
   problema no es el vacío sino la **cadena literal `"unknown"`**, que es peor:
   una clave compartida, no una ausencia.

5. **«Nadie revisó su lógica en toda la sesión» es casi cierto, no del todo.**
   `docs/06-Daily/reports/adr-188-gate-auditoria-2026-08-19.md` ya había revisado
   la rama de auditoría (por qué no escribía el JSONL) y
   `investigacion-router-adopcion-2026-08-19.md` dejó abierto el bucket
   compartido. Ninguno miró `last_suggestion()`, que es donde está el bug grande.

6. **El encargo asume que el gate evalúa «la skill sugerida para este prompt».
   No lo hace.** Es la corrección más importante y no estaba en las premisas:
   evalúa la sugerencia de **confianza máxima de todo el archivo**, desde el
   comienzo de los tiempos. Ver «Qué mide N» y la tabla.

7. **El hook cambió bajo mis pies mientras lo juzgaba y el cambio ya está en el
   working tree** (la rama «sin identidad probada, el gate se abstiene»). Mi
   veredicto contempla ese código, no el de HEAD.

## La hipótesis de la anotación imposible

**Refutada en su forma fuerte, confirmada en la que importa.**

De dónde saca el gate la anotación (línea 158 del archivo actual):

```bash
if printf '%s' "$TOOL_BLOB" | grep -qE "SKILL_BYPASS:[[:space:]]*${SKILL}([[:space:]]|\$)"; then
```

y `TOOL_BLOB` (línea 104) es exclusivamente el payload del tool call:
`.tool_input | tostring` más `prompt`, `command`, `cmd`, `description`. **No hay
lectura de transcript, ni de archivo de sesión, ni de la respuesta del modelo.**
O sea:

- **Sí se puede anotar**: metiendo la línea dentro del prompt del Agent o del
  comando de Bash. Sonda caso 3 → `exit 0`, fila `bypass-annotated`.
- **No se puede anotar como manda el ADR**: en la respuesta del asistente. Un
  `PreToolUse` corre antes de que el modelo escriba, y aunque escribiera, ese
  texto nunca entra al payload. Sonda caso 5 → BLOCK.
- **Y la anotación que la orquestación escribió no podía servir nunca**, por un
  motivo distinto y peor: el gate exige el nombre de **su** skill, y su skill es
  un fósil. En los 16 transcripts del proyecto la orquestación escribió
  `SKILL_BYPASS:` para `auto-refine` (12), `code-review` (4), `browser-task` (2),
  `agent-stress-test` (2), `agent-run-supervision` (1) — **cero veces
  `repo-forensics`**, que es la única que el gate acepta. Sonda caso 4 (anotar
  `auto-refine` mientras el gate espera `repo-forensics`) → BLOCK.

Evidencia de los nombres:
```bash
grep -o "SKILL_BYPASS: [a-z-]*" ~/.claude/projects/-Users-*-luum-agent-os/*.jsonl \
  | sed 's/.*jsonl://' | sort | uniq -c | sort -rn
```

**Conclusión operativa**: el remedio que el mensaje ofrece *es* ejecutable —el
mensaje dice «add ... to the tool input», que es la vía correcta— pero el mensaje
**nunca llegó al modelo** (ver «¿Bloqueó algo?»), así que la orquestación anotó
guiándose por el *system-reminder* del hook blando, que nombra otra skill. Dos
productores, dos ideas distintas de «la sugerencia vigente».

## Tabla de decisión reconstruida del código

Sonda reproducible (read-only, escribe solo en un `PROJECT_DIR` de scratch con
`cos_lib` symlinkeado; hace `env.pop` de `COS_ALLOW_PROTECTED_CONFIG_WRITE`,
`CLAUDE_SESSION_ID`, `COGNITIVE_OS_SESSION_ID` y `COS_METRICS_DIR` antes de
medir):

El script está transcrito completo en el apéndice del final: guardalo donde sea
y corrélo con `.venv/bin/python3`.

| # | Entrada | Veredicto | Fila de auditoría | Contador |
|---|---------|-----------|-------------------|----------|
| 0 | `tool_name` ∉ {Agent,Bash,task,delegate} | allow (0) | — | — |
| 1 | sin `session_id` en el payload ni en env | **abstain (0)** | `metrics/anonymous/…` `outcome=abstained` | — |
| 2 | con sesión, pero `last_suggestion()` = null | allow (0) | **ninguna** | — |
| 3 | sugerencia < 0.90 | allow (0) | **ninguna** | — |
| 4 | ≥0.90 + `/skill` o `Load skills/X/SKILL.md` o `skill: X` en el payload | allow (0) | `outcome=invoked`, `reason` vacío | no toca |
| 5 | ≥0.90 + evento `skill-invoked` en `events.jsonl` para esa sesión | allow (0) | `invoked` | no toca |
| 6 | ≥0.90 + `SKILL_BYPASS: <la skill exacta>` en el `tool_input` | allow (0) | `bypass-annotated` | no toca |
| 7 | ≥0.90 + `SKILL_BYPASS: <otra skill>` | igual que 9/10 | `bypass-unannotated`/`blocked` | +1 |
| 8 | `COS_ALLOW_SKILL_BYPASS=1` sin `COS_SKILL_BYPASS_REASON` | **BLOCK (2)** | **ninguna** | no toca |
| 9 | `COS_ALLOW_SKILL_BYPASS=1` + reason | allow (0) | `env-override` | no toca |
| 10 | ≥0.90, nada de lo anterior, contador < 3 | WARN (0) | `bypass-unannotated` | +1 |
| 11 | ≥0.90, nada de lo anterior, contador ≥ 3 | **BLOCK (2)** | `blocked` | +1 |

Salida literal de la sonda para los casos 10/11/6/7/1/4/8/9:

```
1. alta conf, sin anotacion, x1        exits=[0]      counter=1 audit=['bypass-unannotated']
2. alta conf, sin anotacion, x3        exits=[0,0,2]  counter=3 audit=[...,'blocked']
3. anotacion EXACTA                    exits=[0]      counter=- audit=['bypass-annotated']
4. anotacion de OTRA skill             exits=[0,0,2]  counter=3 audit=[...,'blocked']
5. anotacion fuera del tool_input      exits=[0,0,2]  counter=3 audit=[...,'blocked']
6. /repo-forensics en el prompt        exits=[0]      counter=- audit=['invoked']
7. payload sin session_id              exits=[0,0,0]  counter=- audit=[]
8. env-override sin reason             exits=[2]      counter=- audit=[]
9. env-override con reason             exits=[0]      counter=- audit=['env-override']
```

### Ramas inalcanzables o muertas

- **Fila 5 (detección por `events.jsonl`) está muerta en la práctica.** Requiere
  eventos `skill-invoked`/`skill_invoked` con `session_id` igual al de la sesión.
  En `events.jsonl` los `event_type` presentes son `session-heartbeat` (15.380),
  `merge_queued` (3.662), `file-write-intent` (2.076), `gate_outcome` (1.254)…
  **cero `skill-invoked`**. Nadie los emite.
- **Fila 8 es un bloqueo sin auditoría**: la única rama que devuelve `exit 2` sin
  escribir fila. Contradice el comentario del propio archivo («por eso escriben
  TODAS las ramas»).
- **Fila 2 es hoy el caso universal**, y por eso el gate quedó inerte: ver abajo.
- **El marcador `skill-gate-pass-*` nunca se creó** en 94 días
  (`ls .cognitive-os/runtime/ | grep -c skill-gate-pass` → `0`), coherente con
  que la rama «invoked» jamás se tomó en producción.

## Qué mide N

**N no cuenta bypasses. Cuenta llamadas a herramienta de payloads anónimos que
cayeron en el bucket compartido, contra una sugerencia fosilizada.** En detalle:

- **Vive en** `.cognitive-os/runtime/skill-bypass-counter-<SESSION_ID>`, un
  archivo de texto plano con un entero. Hoy existe **uno solo**: `-unknown` = 143.
- **Incrementa** (línea 200) una vez por cada tool call `Agent|Bash|task|delegate`
  que llega a la rama sin anotar. Un `for` de la suite de tests que corre el hook
  20 veces suma 20. Once de las 12 filas de auditoría entraron entre las 04:36 y
  las 04:38 de hoy, con el mismo `prompt_hash`: son replays, no conducta.
- **Nunca se resetea.** No hay código que lo toque salvo el propio incremento.
- **Y lo que cuenta es contra un fósil.** `last_suggestion("unknown")` devuelve
  hoy:

```bash
.venv/bin/python3 -c "import sys;sys.path.insert(0,'.');\
from cos_lib.skill_router import last_suggestion;print(last_suggestion('unknown',project_root='.'))"
# {'skill': 'repo-forensics', 'confidence': 0.99,
#  'prompt_hash': '0c2d5e662ce11ff8', 'timestamp': '2026-07-03T18:39:16.715516+00:00'}
```

  El motivo está en `cos_lib/skill_router.py:1979-2004`: el «ancla» es el último
  evento `user_prompt_submit` de esa sesión en `events.jsonl`, y **para
  `"unknown"` hay cero anclas** (medido: `anchors for unknown: 0`). Sin ancla, el
  docstring dice «we treat the entire suggestion log for that session as
  in-scope», y como después se queda con el **máximo de confianza**, el resultado
  es constante para siempre: la fila más alta de la historia del archivo. Una
  sugerencia del 3 de julio gobierna cada tool call de agosto.
- Consecuencia: **de 122 sugerencias ≥0.90 registradas** (`skill-suggestion.jsonl`, rango 2026-06-10 → 2026-08-20), repartidas entre
  `hook-timing` (16), `skill-creator` (11), `sdd-verify` (9), `repo-forensics`
  (8), `agent-run-supervision` (7), `graphify-query` (7) y otras, **el gate solo
  pudo exigir una: `repo-forensics`**. Las otras 121 nunca se enforzaron.

## ¿Bloqueó algo que valía la pena?

**No. Cero verdaderos positivos, y ni siquiera falsos positivos visibles: el
mensaje nunca llegó a un turno de la orquestación.**

Método copiado de `juicio-mencion-vs-escritura-2026-08-20.md` (corpus completo,
clasificación uno por uno):

```bash
cd ~/.claude/projects/-Users-*-luum-agent-os
grep -c "invocation-gate: BLOCK\|invocation-gate: WARN" *.jsonl   # -> 0 en los 16
grep -o "bypassed [0-9]* times this session" *.jsonl              # -> 0
```

- **16 transcripts, 295 MB, cero apariciones** del WARN o del BLOCK. Con
  `exit 2` en PreToolUse el stderr se le muestra al modelo y quedaría en el
  transcript; no está.
- Las **12 filas de auditoría** son todas `outcome=blocked`, todas con el mismo
  `prompt_hash 0c2d5e662ce11ff8` (el fósil del 3 de julio) y **todas de hoy entre
  04:36 y 04:51**, once de ellas en dos minutos. Clasificación: **12 replays de
  test / sondas, 0 bloqueos de trabajo real, 0 verdaderos positivos**.
- Los **~141 bloqueos implícitos** (contador 3→143 desde el 18 de mayo) no
  dejaron rastro en ningún transcript. Sea cual sea el proceso que los produjo,
  no era la orquestación haciendo trabajo.
- **Verdadero positivo posible por construcción**: cero. Para acertar, el gate
  tendría que exigir la skill que corresponde al prompt actual; exige la de julio.

Contraste con el incidente que motivó el ADR (2026-05-06, `/repo-scout` ignorado
12 veces): **ese caso hoy no se detectaría**, porque `repo-scout` no es el máximo
histórico del log.

## La política del conteo acumulado

**ADR-188 sí declara el conteo, y lo declara *por sesión*, no acumulado.**
Textual, `ADR-188-…md:93`: «emit `WARN` to stderr and increment a counter. **Three
WARNs in one session** escalate to a single BLOCK»; y el criterio de aceptación 4:
«WARN once, BLOCK after 3». El síntesis dice lo mismo. O sea: **la política escrita
no es «acumulado», es «3 en una sesión»** — y la implementación la habría cumplido
si `SESSION_ID` fuera una sesión. El acumulado no se agregó por decisión: es el
efecto colateral de fabricar la clave `"unknown"`. No hay ADR que lo justifique
porque nadie lo decidió.

Dicho eso, **la política escrita tampoco es la correcta**, por tres razones:

1. **Cuenta llamadas, no decisiones.** Una sugerencia sigue viva mientras no
   cambie el prompt; el gate se dispara en *cada* Agent/Bash. Tres tool calls
   seguidas contra la misma sugerencia son **una** decisión de no invocar, no
   tres. La rama positiva ya reconoce esto —deduplica por
   `(sesión, prompt_hash, skill)` con `skill-gate-pass-*`— y la rama negativa no.
   Asimetría sin motivo escrito.
2. **Un umbral por conteo mide duración, no drift.** Con la deduplicación
   arreglada el problema se achica, pero sigue: la sesión de catorce horas junta
   sugerencias distintas y llega a 3 trabajando bien; la de diez minutos no llega
   nunca. Lo que hay que penalizar es **reincidir sobre la misma sugerencia**, y
   eso ya lo dice el propio ADR en sus KPIs: «repeat-bypass-**same-skill** rate».
   El código no implementa ese KPI: implementa un total.
3. **El costo del bloqueo cae en el lugar equivocado.** El bloqueo mata la tool
   call número N —una cualquiera, quizás inocente— y no la conducta. Y con la
   auditoría hoy escribiendo en todas las ramas, la información necesaria para el
   loop retro ya existe sin necesidad de bloquear.

## Qué debería hacer el implementador

Aviso directo: **el arreglo de identidad que estás terminando es correcto y no
alcanza. Con él, el gate pasa de bloquear siempre a no bloquear nunca**, y eso es
un cambio invisible que hay que decir en voz alta:

- El productor `hooks/skill-router-prompt-suggest.sh:61` también hace
  `${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}`, y **no lee el
  `session_id` del payload** (a diferencia del gate, línea 36). En este harness
  las dos variables están vacías (`env | grep -c '^CLAUDE_SESSION_ID='` → `0`), así
  que **las 582 filas de `skill-suggestion.jsonl` dicen `"unknown"`**.
- Por lo tanto, para cualquier `session_id` real, `last_suggestion()` devuelve
  `null` (verificado con tres ids distintos) → fila 2 de la tabla → `exit 0`
  siempre. Y para los anónimos, tu rama nueva abstiene. **Las dos puertas dan a la
  calle.** Si el PR se cierra así, el gate queda REAL-pero-inerte, no arreglado.

Orden sugerido, y por qué:

1. **Arreglar el productor primero** (leer `session_id` del stdin del
   `UserPromptSubmit`, como ya hace el gate). Sin eso, nada de lo demás se puede
   probar en vivo.
2. **Anclar la sugerencia al prompt, no al máximo histórico.** Es el bug de fondo
   y vive en `cos_lib/skill_router.py`, no en el hook: sin ancla, `last_suggestion`
   debe devolver **la más reciente**, no la de mayor confianza, y debe **caducar**
   (una sugerencia sin ancla y con más de N minutos no gobierna nada). Mientras
   esto no cambie, cualquier gate que lea `last_suggestion` juzga un fósil.
3. **No dejes fila 8 sin auditar** (`COS_ALLOW_SKILL_BYPASS=1` sin reason
   bloquea y no escribe). Es la excepción a tu propia regla, escrita tres líneas
   más abajo del comentario que la enuncia.
4. **Latencia**: los 4 disparos reales de hoy miden `body_duration_ms` 532, 552,
   612 y 644 ms (`hook-timing.jsonl`), contra el «< 30 ms» que ADR-188 declara en
   su AC #2 y en su tabla de KPIs. El diff en el working tree **borra la línea
   `# Latency budget: <30 ms.`** del encabezado. Borrar el presupuesto no es
   cumplirlo: o se mide y se baja (el hook arranca dos intérpretes de Python por
   invocación), o se cambia el número en el ADR con motivo escrito.

### Reconstrucción, en prosa

**Entradas.** (a) La sugerencia vigente = la última fila de
`skill-suggestion.jsonl` **para esta sesión y este `prompt_hash`**, con caducidad
explícita: si el `prompt_hash` del turno no coincide, no hay sugerencia vigente.
(b) Identidad de sesión probada; sin ella, abstención (ya está). (c) El payload
del tool call. (d) Un registro de decisiones por `(sesión, prompt_hash, skill)`,
no un entero por sesión.

**Veredictos.** Tres, no dos: `invoked` (la skill aparece en el payload o hay
evento de invocación), `bypass-audited` (hay anotación que nombra la skill
vigente, o env-override con motivo), `bypass-unaudited`. **El bloqueo se reserva
para la reincidencia sobre la MISMA sugerencia**: la primera decisión de no
invocar se registra y avisa; a partir de la segunda decisión **distinta** sobre el
mismo `(prompt_hash, skill)` —no la segunda tool call— se bloquea. Cambió el
prompt, empieza de cero. Eso implementa el KPI que el ADR ya declara
(«repeat-bypass-same-skill») y deja de medir duración de sesión.

**Qué se registra.** Una fila por *decisión*, no por tool call: dedup por
`(sesión, prompt_hash, skill)` en las tres ramas —la positiva ya lo hace—, con
`outcome` explícito, y **también** en el camino del env-override sin motivo. El
mensaje de bloqueo tiene que imprimir **el nombre exacto de la skill que el gate
exige** (hoy lo hace) y decir que la anotación va **dentro del `tool_input`**
(hoy lo dice) — pero eso sólo sirve si el mensaje llega, así que la anotación
debería aceptarse además por una vía que el modelo controle sin adivinar: un
campo dedicado, o la skill que el *system-reminder* nombró en ese mismo turno.
Que el hook blando y el hook duro no puedan discrepar sobre cuál es «la
sugerencia vigente» es la condición de que todo lo demás funcione.

**Y una decisión de política que hay que escribir en el ADR, no en el código**:
si el gate no puede probar identidad de sesión, ¿se abstiene (hoy) o bloquea? Con
abstención, cualquier harness que no propague `session_id` desactiva el gate
entero sin que se note. Esa es una puerta trasera de una línea y merece su propio
párrafo en ADR-188.

## Lo que no pude medir

- **Quién produjo los ~141 incrementos entre el 18 de mayo y hoy.** El contador no
  guarda procedencia y la auditoría JSONL nació el 2026-08-20 04:36. Sé que no
  fueron turnos de la orquestación (cero rastro en 16 transcripts), pero no puedo
  atribuirlos a una suite concreta.
- **Si el gate bloqueó alguna vez en los harnesses `codex`/`opencode`.** Está
  registrado en `.codex/hooks.json` y `.opencode/cos-hooks.json` (ambos con
  cambios sin commitear), y ahí no hay transcripts que auditar.
- **La discrepancia entre `hook-timing.jsonl` (4 disparos, todos `exit 0`, hoy) y
  la auditoría (un `blocked` a las 04:51:34, sin fila de timing).** O el wrapper
  no envuelve todas las vías de invocación, o no propaga el exit code. No lo
  resolví; afecta a cualquier medición futura de este gate.
- **El comportamiento con `COS_SKILL_ROUTER_DISABLE_SEMANTIC` apagado**: la sonda
  usa el log ya escrito, no reejecuta el router.

## Apéndice: la sonda (evidencia ejecutable)

Read-only sobre el repo: arma un `PROJECT_DIR` de scratch con `cos_lib`
symlinkeado y su propio `.cognitive-os`, y limpia el entorno heredado antes de
medir. No toca `.cognitive-os/metrics/` del proyecto.

```python
#!/usr/bin/env python3
"""Sonda read-only del gate ADR-188. No escribe en el repo: arma un PROJECT_DIR
de scratch con cos_lib symlinkeado y su propio .cognitive-os."""
import json, os, shutil, subprocess, sys, tempfile, pathlib

REPO = pathlib.Path(".")
HOOK = REPO / "hooks/orchestrator-skill-invocation-gate.sh"
SKILL = "repo-forensics"

def make_root(sid, conf=0.99):
    root = pathlib.Path(tempfile.mkdtemp(prefix="gateprobe-"))
    (root / "cos_lib").symlink_to(REPO / "cos_lib")
    m = root / ".cognitive-os" / "metrics"; m.mkdir(parents=True)
    (root / ".cognitive-os" / "runtime").mkdir(parents=True)
    (m / "skill-suggestion.jsonl").write_text(json.dumps({
        "ts": "2026-08-20T00:00:00+00:00", "session_id": sid,
        "prompt_hash": "deadbeef", "skill_name": SKILL,
        "invoke_command": f"/{SKILL}", "confidence": conf, "threshold_met": True}) + "\n")
    return root

def run(root, payload, env_extra=None):
    env = {k: v for k, v in os.environ.items()
           if k not in ("COS_ALLOW_PROTECTED_CONFIG_WRITE", "CLAUDE_SESSION_ID",
                        "COGNITIVE_OS_SESSION_ID", "COS_METRICS_DIR")}
    env["COGNITIVE_OS_PROJECT_DIR"] = str(root)
    env.update(env_extra or {})
    p = subprocess.run(["bash", str(HOOK)], input=json.dumps(payload),
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stderr.strip().replace("\n", " ")[:150]

def audit(root):
    f = root / ".cognitive-os" / "metrics" / "skill-bypass.jsonl"
    return [json.loads(l) for l in f.read_text().splitlines()] if f.exists() else []

def counter(root, sid):
    f = root / ".cognitive-os" / "runtime" / f"skill-bypass-counter-{sid}"
    return f.read_text() if f.exists() else "-"

def case(name, sid, tool_input, env_extra=None, repeats=1):
    root = make_root(sid) if sid else make_root("unknown")
    out = []
    for _ in range(repeats):
        out.append(run(root, {"tool_name": "Bash", "session_id": sid, "tool_input": tool_input}, env_extra))
    rows = audit(root)
    print(f"{name}\n  exits={[o[0] for o in out]} counter={counter(root, sid)} "
          f"audit_outcomes={[r.get('outcome') for r in rows]}\n  stderr={out[-1][1]!r}")
    shutil.rmtree(root, ignore_errors=True)

SID = "probe-session-1"
case("1. alta conf, sin anotacion, x1", SID, {"command": "echo hola"})
case("2. alta conf, sin anotacion, x3 (esperado BLOCK al 3ro)", SID, {"command": "echo hola"}, repeats=3)
case("3. anotacion EXACTA en tool_input.command", SID,
     {"command": f"# SKILL_BYPASS: {SKILL} confidence=0.99 reason=probe\necho hola"})
case("4. anotacion en OTRA skill (auto-refine)", SID,
     {"command": "# SKILL_BYPASS: auto-refine confidence=0.95 reason=probe\necho hola"}, repeats=3)
case("5. anotacion en campo ajeno al tool_input (simula respuesta del asistente)", SID,
     {"command": "echo hola"}, repeats=3)
case("6. skill invocada (/repo-forensics en el prompt)", SID, {"command": "/repo-forensics ahora"})
case("7. payload SIN session_id (anonimo)", "", {"command": "echo hola"}, repeats=3)
case("8. env-override sin reason", SID, {"command": "echo hola"}, {"COS_ALLOW_SKILL_BYPASS": "1"})
case("9. env-override con reason", SID, {"command": "echo hola"},
     {"COS_ALLOW_SKILL_BYPASS": "1", "COS_SKILL_BYPASS_REASON": "probe"})
```
