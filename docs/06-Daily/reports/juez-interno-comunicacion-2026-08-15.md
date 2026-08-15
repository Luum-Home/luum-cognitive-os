# Juez interno — comunicación subagente↔principal y sesión↔sesión

- Fecha: 2026-08-15
- Alcance: qué construyó ESTE repo para los dos ejes de comunicación, si está vivo bajo ADR-342, si viaja al consumidor, y qué problema resuelve.
- Método: censo por `git ls-files` sin filtro de extensión, telemetría propia de cada pieza cuando la tiene, y —para el eje 1— verificación en los transcripts del harness, que es la única fuente fuera de la primitiva que puede responder "¿llegó?".

---

## Resumen ejecutivo

**El eje 1 (subagente↔principal) construyó un canal de entrada que no entrega.**
`hooks/subagent-context-injector.sh` dispara 32 veces hoy, sale con código 0 y
emite 10.253 bytes de JSON bien formado. **Cero de 144 transcripts de subagente
contienen el bloque inyectado.** Bajo ADR-342 pregunta 4 (¿se la vio decidir
sobre un input real?) la respuesta es: se la vio *ejecutar*, nunca se la vio
*llegar*. Es el mismo defecto de las cuatro formas del ADR, en una quinta forma
que el ADR no tabuló: **la primitiva corre en el evento correcto, lee el campo
correcto, emite la forma correcta, y el host no consume su salida porque está
registrada `async: true`.**

**El eje 2 (sesión↔sesión) construyó un log de eventos y un sistema de locks que
sí están vivos** — 19.678 eventos de 34 sesiones distintas, 977 locks de edición
con los tres más recientes correspondiendo a los informes de los jueces de esta
misma tanda. Lo que **no** está vivo es la mitad de *entrega*: los dos hooks que
convierten ese log en contexto para el operador emiten una forma JSON que el host
no publica, y también están `async: true`.

Dicho corto: **este repo resolvió el descubrimiento y el registro. No resolvió la
entrega.** Y las dos mitades están del mismo lado de una frontera que ninguna
telemetría interna cruza.

---

## Correcciones a las premisas del encargo

| Premisa del encargo | Qué mide el comando | Veredicto |
|---|---|---|
| "27 disparos hoy" del injector | `grep -c '"SubagentStart"' .cognitive-os/metrics/hook-timing.jsonl` → **32** | **Refutada por stale.** 27 era correcto al momento de escribir el brief; la cuenta subió mientras esta tanda de jueces corría (yo soy uno de los disparos). El número no es el hallazgo. |
| "se probó que el bloque llega (`stdout_bytes` 9398→10162)" | `stdout_bytes` lo escribe `scripts/hook-timing-wrapper.sh` midiendo lo que el hook **emitió** | **Refutada, y es el hallazgo central.** `stdout_bytes` prueba emisión, no recepción. Es exactamente la trampa que el propio ADR-342 describe: la respuesta salió de un artefacto que está del lado de la primitiva. Ver §Eje 1. |
| "cap de 10.000 chars en la línea 154" | `sed -n '150,160p' hooks/subagent-context-injector.sh` | **Confirmada** (`MAX_CONTEXT_CHARS=10000`, línea 153-154). Y es un cap que ya está mordiendo: 7 de 32 disparos emitieron ≥10.162 bytes. Irrelevante mientras nada llegue. |
| "`hook-timing.jsonl` … 37.424 filas" | `wc -l .cognitive-os/metrics/hook-timing.jsonl` → **13.193** | **Refutada / no reproducible en este checkout.** No sé si rotó o si el brief citó otro archivo. Reporto mi cuenta con su comando; no elijo. |
| "Valkey (OFF)" del índice RULES-COMPACT | Ver §Anexo A | **Refutada como estado, correcta como default.** Hay una fila registrada de conexión real a un daemon local. |
| Lista de piezas del brief | censo propio abajo | **Incompleta.** El brief no nombró `hooks/subagent-input-schema-validator.sh`, `hooks/agent-message-inbox-context.sh`, `cos_lib/agent_message_bus.py`, `scripts/cos-agent-message` (ejecutable sin extensión), ni los eventos `TeammateIdle`/`TaskCreated`/`TaskCompleted` de `.claude/settings.json`. |
| "`rules/agent-communication.md` — el índice dice Valkey (OFF)" | — | El índice **y** la regla lo dicen; la regla además documenta el fallback. La regla no es el problema. |

Cero premisas sobre restricciones de entorno resultaron inventadas en este
encargo: `hooks/**` y `rules/**` están efectivamente protegidos
(`grep -n 'protected-config-write-guard' .claude/settings.json` → registrado en
`PreToolUse` sin matcher), y no necesité escribir fuera del informe.

---

## Censo — cómo se armó

```bash
git ls-files | grep -Ei 'subagent|agent-communication|agent-message|session_bus|cross-session|task_claim|edit-lock|task-panel|recap-sync|session_concurrency'
```
→ 82 rutas. De ahí, las **runtime** (no tests, no docs, no `.ai/`) son 21:

```bash
git ls-files hooks scripts cos_lib manifests | grep -Ei 'subagent|agent-message|session_bus|cross-session|task_claim|edit-lock|task-panel|recap-sync'
```

Registro real (no `grep` sobre `settings.json`, que no ve la delegación):

```bash
python3 -c "
import json,re;s=json.load(open('.claude/settings.json'))
for ev,bl in s['hooks'].items():
  for b in bl:
    for h in b['hooks']:
      for n in re.findall(r'hooks/([A-Za-z0-9_.-]+)',h['command']):
        print(ev, repr(b.get('matcher','')), n, 'async=%s'%h.get('async'))"
```
→ 168 registros sobre 10 claves de evento: `SessionStart`, `UserPromptSubmit`,
`SubagentStart`, `PreCompact`, `PreToolUse`, `PostToolUse`, `Stop`,
`TeammateIdle`, `TaskCreated`, `TaskCompleted`. **No hay `SubagentStop`**, y
`TaskCompleted` está declarada con **lista vacía**.

Más los delegados, que ese dump no ve:
```bash
grep -nE '_run_gate|hooks/' hooks/bash-hot-path-dispatcher.sh
```
→ `cross-session-coordination-guard.sh` y `agent-message-inbox-guard.sh` corren
por delegación desde el dispatcher de `PreToolUse:Bash`, línea 119-120.

---

## EJE 1 — Subagente ↔ principal

### 1.1 Entrada de contexto al subagente: `hooks/subagent-context-injector.sh`

**Vida bajo ADR-342:**

| Pregunta | Respuesta | De dónde sale (fuera de la primitiva) |
|---|---|---|
| 1. ¿El host publica el nombre? | **Sí.** `SubagentStart` es un evento real; el wrapper lo registró 32 veces. | `grep -c '"SubagentStart"' .cognitive-os/metrics/hook-timing.jsonl` → 32 |
| 2. ¿Corre donde puede hacer algo? | **No, y por una razón nueva.** Registrado `"async": true` (`.claude/settings.json`, bloque `SubagentStart`). Un hook async es fire-and-forget: el subagente ya arrancó. Su propio header dice `# Async: false (completes before subagent starts)` — **el archivo se contradice con su registro**. | `python3 -c "import json;print(json.load(open('.claude/settings.json'))['hooks']['SubagentStart'])"` vs `sed -n '1,12p' hooks/subagent-context-injector.sh` |
| 3. ¿Llega el campo que lee? | **Sí.** Lee `.prompt // .message // .description`; el payload de `SubagentStart` los trae (el hook produce 10.253 bytes de contexto interpolado, imposible sin payload). | `stdout_bytes` > 0 en 32/32 filas |
| 4. ¿Se la vio decidir? | **Se la vio ejecutar. Nunca se la vio llegar.** | ver abajo |

**La medición que decide.** El template `templates/agent-preamble.md` contiene el
literal `Phase: {{phase}}`; el hook lo interpola a `Phase: \`reconstruction\``. Esa
cadena interpolada **solo puede existir si el hook la produjo** — leer el archivo
nunca la genera. Sobre los transcripts del harness:

```bash
D=~/.claude/projects/<slug-del-repo>
python3 - <<'PY'
import json,glob
files=glob.glob(D+"/*/subagents/*.jsonl")
marker='MANDATORY PROJECT RULES (injected by subagent-context-injector)'
hits=sum(1 for f in files
         for r in map(json.loads, filter(str.strip, open(f)))
         if (r.get('type')=='attachment' or
             (r.get('type')=='user' and isinstance(r.get('message',{}).get('content'),str)))
         and marker in json.dumps(r))
print(len(files), hits)
PY
```
→ **`144 0`**. Ciento cuarenta y cuatro transcripts de subagente, **cero**
portadores del bloque.

La única coincidencia bruta de `grep -rl` en un transcript de subagente es **mi
propio transcript**, y la inspección fila por fila muestra que las dos ocurrencias
son mis propios `tool_use`/`tool_result` — yo leyendo el template y yo grepeando
el marcador. Autocontaminación, no entrega. Filtrarla es exactamente la
disciplina que ADR-342 pide: la respuesta no puede salir de la primitiva, y
tampoco del que mide.

**Corroboración de primera persona.** Soy uno de los 32 disparos: la fila
`{"timestamp":"2026-08-15T21:41:04Z","event":"SubagentStart","stdout_bytes":10253,"pid":16097}`
coincide al segundo con `ts=2026-08-15T21:41:04.595Z` de la fila 0 de mi propio
transcript (mi encargo). El hook emitió 10.253 bytes para mí. **Mi contexto no
contiene el bloque.** Lo que sí llegó —las reglas del proyecto, el CLAUDE.md— vino
por el canal nativo del harness, no por este hook.

**Consecuencia concreta y verificable:** la norma `encargo-refutable` que
`rules/RULES-COMPACT.md` línea de §8 declara *"Delivered via
`templates/agent-mandatory-rules.md`, the one path proven to reach every
sub-agent"* **viaja por el canal que no entrega**. La sección
`## Corrections to the brief's premises` que este informe trae, la traje porque el
orquestador la pidió a mano en el encargo, no porque me llegara la regla.

**Qué problema resuelve si funcionara:** que cada subagente arranque con las
reglas del proyecto y el sidecar de sesiones previas sin que el orquestador las
copie a mano en cada prompt. **Qué pasa hoy sin él:** exactamente lo que pasa —
el orquestador las copia a mano, y cuando se olvida, no se entera.

### 1.2 Presupuesto de subagente: `hooks/subagent-budget-enforcer.sh`

- **Vivo, y es el único con ledger propio poblado.** 794 filas
  (`wc -l .cognitive-os/metrics/subagent-budget-enforcer.jsonl`), repartidas
  `observe=542, block=134, allow=71, warn=47`.
- **Trampa de medición confirmada de nuevo:** `hook-timing.jsonl` le atribuye
  **566** disparos contra **794** de su ledger propio — un veredicto **1,40×**
  más bajo. El ledger propio manda.
  ```bash
  grep -c '"subagent-budget-enforcer"' .cognitive-os/metrics/hook-timing.jsonl   # 566
  wc -l < .cognitive-os/metrics/subagent-budget-enforcer.jsonl                    # 794
  ```
- **ADR-342 pregunta 2: falla.** Registrado en `PostToolUse` — decide después del
  efecto. Ya está documentado en el propio ADR-342 y en
  `docs/06-Daily/reports/subagent-budget-enforcer-architecture-2026-08-15.md`.
  Lo confirmo, no lo re-litigo.
- **Problema que resuelve:** que un subagente en loop consuma la ventana entera.
  Sin él, el loop termina cuando el contexto revienta.

### 1.3 Preflight de capacidades: `hooks/subagent-capability-preflight.sh`

- **Corre, pero no por el wrapper:** `hook-timing.jsonl` le da **0**; su ledger
  propio tiene **20 filas** (`status=block ×10, pass ×10`). Segundo caso del
  mismo sesgo del wrapper.
- Sus filas traen `"hook_payload_seen": true` — o sea, la pregunta 3 de ADR-342 se
  contesta desde el registro. **Vivo.**
- **Problema que resuelve:** que se lance un `Explore` (read-only) con una tarea
  que exige persistir. Sin él, el agente descubre el conflicto a mitad de camino
  y devuelve un informe que no escribió.

### 1.4 Validación de schema de entrada: `hooks/subagent-input-schema-validator.sh`

- **6 filas**, la última `{"ok": false, "error_count": 1, "payload_keys": ["task_description","blast_radius"]}`.
- **No registrado** en `settings.json` ni en el dispatcher →
  ADR-342 pregunta 1/2: **no existe como control**. Las 6 filas son de
  invocación manual o de test, no de runtime.
- **Problema que resolvería:** decirle al orquestador que el payload que arma para
  el subagente no tiene los campos que los gates aguas abajo van a leer.

### 1.5 Lo que el eje 1 NO construyó

- **No hay `SubagentStop`.** La clave no existe en `settings.json`. El repo no
  construyó nada sobre "qué devuelve el subagente" — el resultado vuelve por el
  canal nativo del harness (`<result>` del `Agent` tool), y `rules/RULES-COMPACT.md`
  §9 lo reconoce (`agent-output-reading`: "inspect `<result>` first").
- **No hay interrupción del principal hacia un subagente en vuelo.**
  `hooks/agent-control-inbound-guard.sh` existe y está registrado en `PreToolUse`,
  pero es el subagente el que se autoconsulta la señal en su próximo tool call —
  no hay preemption. Es un semáforo, no un freno.
- **No hay mensajes al subagente mientras corre.** El único canal de entrada es
  el de §1.1, que dispara una vez al arranque y no entrega.

---

## EJE 2 — Sesión ↔ sesión

### 2.1 Registro y descubrimiento: `.cognitive-os/sessions/events.jsonl` + `hooks/cross-session-event-emit.sh`

**Vivo, y es lo más vivo del informe.**

```bash
wc -l .cognitive-os/sessions/events.jsonl                       # 19678
python3 -c "
import json,collections
r=[json.loads(l) for l in open('.cognitive-os/sessions/events.jsonl') if l.strip()]
print(len(set(x.get('session_id') for x in r)))
print(collections.Counter(x.get('event_type') for x in r).most_common(6))"
```
→ 19.678 filas, **34 session_id distintos**,
`session-heartbeat=8998, merge_queued=3337, file-write-intent=1608, merge_completed=1041, gate_outcome=943, merge_failed=890`.

- ADR-342 1-4: **pasa las cuatro.** Registrado en `PreToolUse` (dos veces),
  `PostToolUse` y `Stop`; 498 disparos hoy vía wrapper; el archivo crece.
- **Problema que resuelve:** que dos sesiones sobre el mismo checkout no sepan que
  la otra existe. Sin él, la colisión se descubre en `git status`
  (ver `docs/06-Daily/reports/postmortem-cross-session-collision-2026-05-05.md`).

**Pero:** `.cognitive-os/sessions/active-sessions.json` es `{"sessions": []}` — el
registro de descubrimiento *derivado* está vacío mientras el log crudo tiene 34
sesiones. Y `cos_lib.session_bus.peers()` devuelve **0** ahora mismo, con otra
sesión de agentes corriendo en este checkout:

```bash
python3 -c "
import sys;sys.path.insert(0,'.')
from cos_lib.session_bus import peers; from pathlib import Path
print(len(peers(project_dir=Path('.').resolve(), within_seconds=1800, alive_only=True, current_session_id='x', limit=200)))"
```
→ `0`. **Registrar funciona; descubrir no.** No sé si es `alive_only` mirando PIDs
muertos o el filtro de 1800s; lo reporto como hallazgo abierto, no elijo causa.

### 2.2 Entrega del contexto de pares: `hooks/cross-session-peer-context.sh`

**No entrega. Dos razones independientes, cada una suficiente.**

1. **Forma equivocada** (ADR-342 pregunta 1). Emite
   `{"additionalContext": "..."}` en la raíz
   (`sed -n '40p' hooks/cross-session-peer-context.sh`). El shape que el host
   publica para `UserPromptSubmit` es
   `{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":...}}`
   — que es, textualmente, la forma que **sí** usa `subagent-context-injector.sh`
   líneas 191-197. **Dos hooks del mismo repo, dos formas distintas para el mismo
   campo.** Una de las dos está mal por construcción.
2. **`async: true`** en su registro, igual que §1.1.

**Verificación:** su cadena de salida `"Peer orchestrator sessions detected:"` no
aparece en **ningún** transcript del proyecto salvo el mío (autocontaminación por
este mismo grep):
```bash
grep -rl 'Peer orchestrator sessions detected' ~/.claude/projects/<slug>/ | wc -l   # 1, y es este informe
```
**Caveat honesto:** `peers()` devuelve 0 hoy, así que el hook sale por
`sys.exit(0)` sin emitir. Bajo ADR-342 esto es **`unmeasured`, no `broken`** para
la pregunta 4 — pero las preguntas 1 y 2 ya fallan por lectura de código, y eso
alcanza para "no existe como control".

- **Problema que resolvería:** avisarle al operador, antes de que escriba, que
  otra sesión tocó los mismos paths. **Hoy:** ese aviso lo da el edit-lock,
  después.

### 2.3 Mensajería dirigida: `cos_lib/agent_message_bus.py` + `hooks/agent-message-inbox-context.sh` + `hooks/agent-message-inbox-guard.sh` + `scripts/cos-agent-message`

- `agent-message-inbox-context.sh`: **27 disparos hoy**, registrado en
  `UserPromptSubmit`, `async: true`, y **la misma forma JSON de raíz** que §2.2
  (`sed -n '42p'`). `inbox()` devuelve **0 filas** ahora. Mismo veredicto:
  registro vivo, entrega no demostrada y con dos defectos de forma.
- `agent-message-inbox-guard.sh`: **0 en `hook-timing`**, porque corre **por
  delegación** desde `bash-hot-path-dispatcher.sh:120` — el wrapper
  estructuralmente no lo ve. Sin ledger propio → **`unmeasured`**, no muerto.
- `scripts/cos-agent-message`: **ejecutable sin extensión**. Un
  `git grep --include='*.py'` no lo ve. Es la CLI de envío/ack.
- **Problema que resuelve:** que una sesión le pase un hallazgo a otra sin el
  operador de cartero. **Hoy:** el operador es el cartero (este encargo mismo lo
  demuestra: los dos jueces no se hablan a propósito, y el que los junta después
  es una persona).

### 2.4 Locks de edición: `hooks/edit-lock-*.sh` (4 piezas)

**Vivo, y es lo único de los dos ejes que se ve trabajando sobre esta tanda.**

```bash
ls .cognitive-os/runtime/edit-locks/ | wc -l          # 977
ls -t .cognitive-os/runtime/edit-locks/ | head -3
```
→ los tres locks más recientes son
`docs--06-Daily--reports--juez-externo-comunicacion-agentes-2026-08-15.md`,
`...juez-externo-orquestacion...`, `...juez-interno-orquestacion...` — los
informes de los jueces hermanos de esta misma tanda, a las 18:39-18:41.

| Hook | Evento | Disparos hoy (`hook-timing`) |
|---|---|---|
| `edit-lock-pre-tool.sh` | `PreToolUse:Edit\|Write` | 43 |
| `edit-lock-drain-parked.sh` | `PostToolUse:Edit\|Write` | 43 |
| `edit-lock-process-negotiations.sh` | `UserPromptSubmit` | 27 |
| `edit-lock-session-end.sh` | `Stop` | 23 |

- ADR-342: pasa 1, 2 (pre-tool **antes** del efecto), 3 y 4. **La única familia
  del informe que pasa las cuatro.**
- **Problema que resuelve:** dos sesiones escribiendo el mismo archivo. Sin él,
  gana la última en guardar y la otra no se entera.
- **Deuda:** **sin ledger propio** (`ls .cognitive-os/metrics/ | grep -i lock` →
  solo `git-op-blocks`, `rm-op-blocks`, `untracked-delete-blocks`, ninguno suyo).
  Los 43 disparos son ejecuciones; cuántas **bloquearon** no se puede contar. Es
  "instrumento honesto con nombre de gate" hasta que tenga ledger.

### 2.5 Reclamo de tareas: `cos_lib/task_claim_ledger.py`, `scripts/cos_task_claims.py`

- Estado vivo en dos archivos distintos: `.cognitive-os/runtime/task-claims.json`
  y `.cognitive-os/tasks/active-claims.json`, con claims reales (`agent_id`,
  `expires_at`, `host`, `pid`, `scope`).
- **Hallazgo:** los dos usan `"session_id": "default-session"` como valor real, no
  el id de sesión. El ledger sabe qué agente reclamó, **no qué sesión**. Para el
  eje 2 eso es la mitad del punto.
- **Problema que resuelve:** dos agentes tomando la misma tarea. **Hoy:** lo
  resuelve entre agentes, no entre sesiones.

### 2.6 Muertos o no registrados

| Pieza | Estado | Comando |
|---|---|---|
| `hooks/task-panel-sync.sh` | **No registrado** (ni `settings.json` ni dispatcher), 0 disparos, sin ledger | `grep -c task-panel-sync .claude/settings.json` → 0 |
| `hooks/recap-sync.sh` | idem | `grep -c recap-sync .claude/settings.json` → 0 |
| `hooks.TaskCompleted` | Clave declarada con **lista vacía** | `python3 -c "import json;print(json.load(open('.claude/settings.json'))['hooks']['TaskCompleted'])"` → `[]` |
| `TeammateIdle` / `TaskCreated` | Registrados y vivos, pero triviales: 5 filas cada uno, todas `idle_no_tasks_file` / `no_description_field_in_json` | `wc -l .cognitive-os/metrics/teammate-idle.jsonl` → 5 |

`TaskCreated` con las 5 filas en `reason: "no_description_field_in_json"` es
literalmente la forma 3 de ADR-342: lee un campo que el payload no trae, y su
`default` es una lectura legal, así que la ausencia es invisible.

---

## ¿Viajan al consumidor? — Contradicción encontrada

**`# SCOPE:` dice que sí; `manifests/primitive-install-boundary.yaml` dice que no.**

```bash
for h in subagent-context-injector cross-session-peer-context agent-message-inbox-context \
         cross-session-event-emit edit-lock-pre-tool subagent-budget-enforcer \
         subagent-capability-preflight agent-message-inbox-guard cross-session-coordination-guard; do
  printf "%-34s %s\n" "$h" "$(grep -m1 '^# SCOPE:' hooks/$h.sh)"; done
```
→ **9 de 9 marcadas `# SCOPE: both`** (o sea: deben viajar al proyecto consumidor).
Solo `task-panel-sync`, `recap-sync` y `subagent-input-schema-validator` son `os-only`.

```bash
grep -cE 'subagent-context-injector|cross-session-peer-context|agent-message-inbox|cross-session-event-emit|edit-lock|subagent-budget|subagent-capability' manifests/primitive-install-boundary.yaml
```
→ **0**. El perfil `default`/`core` lista 44 hooks y **ninguno** es de comunicación.

**No elijo.** Cualquiera de los dos puede ser el correcto: o el boundary está
incompleto y 9 primitivas marcadas "both" no se están proyectando, o los
marcadores `SCOPE: both` son aspiracionales y el boundary es la verdad. Los dos
son manifiestos declarativos; **ninguno de los dos se verifica contra un install
real**, que es la misma ausencia que ADR-342 describe para la pregunta 1.

**Nota lateral del mismo tipo:** `hooks/rate-limiter.sh` **sí** está en el perfil
`core` del boundary, y `rules/rate-limiting.md` documenta —correctamente— que no
está registrado en `settings.json`. Es decir: el boundary manda al consumidor un
hook que en el repo de origen nunca corrió.

Los registros `.ai/primitives/hooks/*.json` de estas piezas **no tienen** campos
`scope`, `distribution` ni `runtime_projection` en la raíz — usan
`contract.projection_fidelity` por harness. Para `subagent-context-injector`
declara `claude: {"claims_runtime_enforcement": true, "fidelity": "native-lifecycle-enforced"}`.
**Ese `true` es falso** por §1.1: no hay enforcement, no hay ni entrega.

---

## Anexo A — El "Valkey (OFF)" del índice

`rules/RULES-COMPACT.md` §7 dice `[agent-communication] Valkey(OFF)`. Tratado como
hipótesis, contra el código:

- `cognitive-os.yaml:470-476` — `valkey: mode: on_demand`, con
  `VALKEY_URL: redis://localhost:6379` y `review_by: 2026-10-01`. No es "OFF": es
  "opcional bajo demanda", con fallback de filesystem siempre válido.
- `rules/agent-communication.md:16` — "Valkey is **OFF by default**", habilitable
  con `AGENT_BUS_ENABLED=true`. Correcto como **default**.
- `.cognitive-os/metrics/valkey-health.jsonl` — **1 fila**, hoy 05:38:50:
  `{"event_type":"local-daemon-hit", "connection_type":"local-daemon", "port":6379, "detail":"fell back to local daemon at redis://localhost:6379"}`.
  **Hubo una conexión real a un daemon Redis local hoy.**
- El fallback de filesystem está **muy** vivo: `find .cognitive-os/agent-bus -type f | wc -l` → **86** archivos `heartbeat.jsonl`, uno por `tool_use_id` de agente.

**Veredicto:** "OFF" es correcto como *default de transporte* e incorrecto como
*estado del bus*. El bus de agentes está vivo por el camino de filesystem, y hay
evidencia de al menos una conexión al daemon. La celda del índice comprime una
cosa de tres estados en un booleano.

---

## Anexo B — Trampas de medición, verificadas de nuevo

Las cuatro del encargo se confirmaron, y aparece una quinta:

1. **`hook-timing.jsonl` subcuenta.** `subagent-budget-enforcer`: 566 (wrapper)
   vs 794 (ledger propio) = **1,40×**. `subagent-capability-preflight`: 0
   (wrapper) vs 20 (ledger propio) = **∞**. Si tiene ledger propio, manda.
2. **El campo `hook` no lleva `.sh`.** Confirmado en el esquema de filas.
3. **Registro por delegación.** `agent-message-inbox-guard` y
   `cross-session-coordination-guard` dan 0 en todo grep de `settings.json` y
   corren desde `bash-hot-path-dispatcher.sh:119-120`.
4. **`hook-health.jsonl` se autoatribuye** — y por eso **ninguna** de las 12
   piezas de este informe aparece en sus 5.727 filas (todas son de
   `protected-config-write-guard`, `tool-sequence-capture`, `secret-detector`,
   `error-pipeline`, `error-learning`, `result-truncator`). Para estos dos ejes
   `hook-health` no sirve: mide otra población.
5. **NUEVA — autocontaminación del transcript.** Un `grep -rl '<marcador>'` sobre
   los transcripts se encuentra a sí mismo: el texto del comando se escribe en el
   transcript antes de que llegue el resultado. **Todo censo sobre transcripts
   tiene que descartar `tool_use`/`tool_result` propios**, o mide su propio eco.
   Sin ese filtro, el injector "llega a 1 transcript"; con el filtro, a 0.

---

## Anexo C — El verde barato que no tomé

La conclusión fácil sobre el eje 1 era **"reinvención: el harness ya inyecta
contexto al subagente"**. La pregunta que decide —¿un cambio en uno obliga a tocar
el otro?— se contesta que **no**: el canal nativo del harness entrega el prompt y
el `CLAUDE.md`, y su contenido lo elige quien lanza el agente; el injector entrega
reglas del proyecto y sidecar de sesiones previas, y su contenido lo elige el
repo. Si el harness cambia el formato del prompt, el injector no se entera; si el
repo cambia `templates/agent-mandatory-rules.md`, el harness no se entera.
**Coincidencia de propósito, no reinvención.** Se acepta con el motivo escrito.

Y al revés, la otra trampa: no concluí "está vivo" porque el injector tenga
`tests/hooks/test_subagent_context_injector.py` verde y 32 disparos con exit 0.
Los tests verifican que **emite**; el defecto está del otro lado de la emisión.
Es el mismo patrón que el `assert backend_ready is False` que el encargo cita.

---

## Lo que queda abierto (no lo cierro yo — este encargo mide)

1. **`SubagentStart` async.** El registro dice `async: true`, el archivo dice
   `Async: false`. Alguna de las dos es la intención. Decidirlo es del operador.
2. **Dos formas JSON para `additionalContext`** dentro del mismo repo
   (`hookSpecificOutput` anidado en el injector vs raíz plana en peer-context e
   inbox-context). No hay un test que compare ninguna de las dos contra el
   contrato publicado del host — que es exactamente el censo que ADR-342 declara
   inexistente para la pregunta 1.
3. **`SCOPE: both` vs `primitive-install-boundary.yaml`** — 9 primitivas de
   comunicación en contradicción. Reportado, no resuelto.
4. **`peers()` devuelve 0** con sesiones concurrentes reales y 34 session_id en el
   log crudo. Causa no determinada.
5. **Los edit-locks no tienen ledger.** Son la familia más viva de las dos y la
   única sin cómo contar sus bloqueos.
