# Emisores de contexto `async` en `UserPromptSubmit` — 2026-08-19

## Resumen ejecutivo

- El defecto no eran tres hooks sino **seis**: todo emisor de `additionalContext`
  registrado `async: true` en `UserPromptSubmit` entrega su contexto un prompt tarde.
- Los seis pasan a `async: false`. Costo medido de bloquear: **0,83–0,90 s** de
  wall-clock corriendo los seis en paralelo, contra el techo de 3 s que la suite ya
  asserta. Ninguno queda async con motivo escrito: ninguno lo necesitaba.
- El `async` **no se lee de `cognitive-os.yaml`**: está hardcodeado en
  `scripts/_lib/settings-driver-claude-code.sh`. Editar solo el YAML habría dejado
  el arreglo con cara de aplicado y sin efecto.
- La redacción del skill-router ahora dice qué hace la skill, qué cuesta cargarla y
  qué obliga ADR-188 según el umbral. Suma 165–231 caracteres, solo en prompts que
  matchean ≥0,80.
- Test nuevo `test_async_not_used_on_prompt_coupled_context_events`, baseline vacío.
  **Rojo con el defecto (6 ofensores nombrados), verde con el arreglo.**

## Correcciones a las premisas del encargo

1. **«Tres hooks», no: son seis.** El encargo nombra `cross-session-peer-context`,
   `agent-message-inbox-context` y `skill-router-prompt-suggest`. El censo de
   emisores sobre las 12 entradas de `UserPromptSubmit` devuelve además
   `session-wrapup-trigger`, `rule-router-prompt-suggest` y `adr-relevance-suggest`.
   Los seis contienen `additionalContext` y los seis estaban `async: true`.
   No es un detalle de conteo: el test que pide el encargo usa baseline exacto, así
   que arreglar tres y baselinear tres habría sido exactamente el verde barato
   prohibido. Comando:

   ```bash
   for h in $(python3 -c "import json;d=json.load(open('.claude/settings.json'));\
   print(' '.join(x['command'].split('hooks/')[1].rstrip('\"') for g in d['hooks']['UserPromptSubmit'] for x in g['hooks']))"); do
     printf '%-36s async=%s emitter=%s\n' "$h" \
       "$(grep -c "hooks/$h\",$" /dev/null)" "$(grep -c additionalContext hooks/$h)"
   done
   ```

2. **La premisa del orquestador sobre `cognitive-os.yaml` es medio cierta y la
   mitad falsa importa.** El aviso decía: el registro canónico es
   `cognitive-os.yaml > harness.hooks`, editar `.claude/settings.json` se pisa.
   Lo primero es cierto para `script`/`event`/`scope`. **Para `async` no**: el
   driver lo tiene hardcodeado en su propia lista, y el comentario del driver lo
   dice con todas las letras (línea 252, escrito para el caso `subagent-context-injector`):

   > *"The flag lives here, not in cognitive-os.yaml. Setting async: false there and
   > stopping is the trap this comment exists to close: the yaml entry is not read
   > for this field, so the fix looks landed, survives review, and is undone by the
   > next run of this driver."*

   Seguir la receta del aviso al pie (editar YAML → proyectar → verificar) habría
   funcionado igual porque el paso 3 es verificar el generado, pero el paso 1 solo
   no alcanza. El arreglo real toca **las dos** fuentes.

3. **La pregunta del orquestador —«¿hay deriva entre fuente y proyección?»— tiene
   respuesta: no, pero por casualidad.** Los seis declaraban `async: true` en
   `cognitive-os.yaml` Y en el driver, y coincidían. No había deriva de valor. Lo
   que sí hay es **deriva de autoridad**: dos declaraciones del mismo hecho, una
   sola leída, sin nada que las obligue a coincidir. Hoy están de acuerdo; nada
   impide que mañana no lo estén, y el desacuerdo sería silencioso. Queda anotado
   como deuda abajo.

4. **`.claude/settings.json` tenía deriva propia, previa a mí.** Al correr el
   proyector, además de los seis `async` cambió `"TaskCompleted": []` →
   `"TaskCompleted": [\n\n]`. Eso significa que el archivo commiteado **no era
   byte-idéntico** a lo que produce el driver: alguien lo editó a mano o el
   generador cambió sin re-proyectar. Ruido cosmético, pero es la prueba de que
   «generado» no estaba siendo verificado.

5. **La telemetría viva sí alcanzaba, esta vez.** El encargo advierte que contar
   solo `hook-timing.jsonl` produce conclusiones falsas. Correcto como norma, y lo
   respeté (8 archivos, 240.872 filas). Dato: para estos seis hooks las 7 rotaciones
   aportan ~260 de las ~327 muestras por hook, o sea el vivo cubría el 20%. La
   advertencia estaba bien puesta.

6. **`bash -n` no era suficiente y `/bin/bash -n` tampoco es todo.** Validé los
   `.sh` con `/bin/bash -n` (3.2.57) como pide el encargo. Pero el cambio grande de
   este trabajo está en un **heredoc de Python dentro** de un `.sh`: `bash -n` no
   mira adentro del heredoc. Lo cubrí ejecutando el hook contra tres prompts reales
   y verificando el JSON de salida, no solo la sintaxis del wrapper.

## Medición de latencia por hook

### Histórico (telemetría, vivo + 7 rotados)

```bash
python3 - <<'EOF'
import gzip, json, glob
H = ["session-wrapup-trigger","cross-session-peer-context","agent-message-inbox-context",
     "rule-router-prompt-suggest","adr-relevance-suggest","skill-router-prompt-suggest"]
files = [".cognitive-os/metrics/hook-timing.jsonl"] + sorted(
    glob.glob(".cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz"))
d = {h: [] for h in H}
for f in files:
    op = gzip.open if f.endswith(".gz") else open
    with op(f, "rt", errors="ignore") as fh:
        for line in fh:
            if '"hook":"' not in line: continue
            try: r = json.loads(line)
            except Exception: continue
            if r.get("hook") in d and r.get("event") == "UserPromptSubmit":
                d[r["hook"]].append(r["duration_ms"])
def q(v, p):
    v = sorted(v); k = (len(v)-1)*p; f = int(k); c = min(f+1, len(v)-1)
    return v[f] + (v[c]-v[f])*(k-f)
for h in H:
    v = d[h]
    print(f"{h:34} n={len(v):<5} p50={q(v,.5):>6.0f} p95={q(v,.95):>7.0f} max={max(v):>7.0f}")
EOF
```

`files=8 rows_scanned=240872`

| hook | n | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|
| session-wrapup-trigger | 327 | 180 | 585 | 1383 | 4504 |
| cross-session-peer-context | 327 | 184 | 748 | 2145 | 137348 |
| agent-message-inbox-context | 327 | 187 | 850 | 1391 | 879204 |
| rule-router-prompt-suggest | 326 | 232 | 1030 | 2207 | 5699 |
| adr-relevance-suggest | 323 | 546 | 4336 | 7488 | 12850 |
| skill-router-prompt-suggest | 315 | 1108 | 15111 | 26153 | 246718 |

Los tres máximos absurdos (137 s, 879 s, 246 s) son **todos del mismo instante**,
`2026-07-20T12:29:13Z`: un proceso async descheduleado, no el costo del hook.
Filtrando a las muestras posteriores a los dos commits de performance del 18-08
(`bbedb3c80`, `8a2d75c93`) el panorama es otro:

| hook | n | p50 | p95 | max |
|---|---:|---:|---:|---:|
| session-wrapup-trigger | 69 | 209 | 487 | 2875 |
| cross-session-peer-context | 69 | 208 | 616 | 2938 |
| agent-message-inbox-context | 69 | 212 | 687 | 2618 |
| rule-router-prompt-suggest | 68 | 289 | 674 | 1186 |
| adr-relevance-suggest | 67 | 681 | 2788 | 4570 |
| skill-router-prompt-suggest | 67 | 935 | 4361 | 10849 |

### Directo (el comando que pide el runbook)

Cinco prompts distintos, `session_id` fresco en cada corrida para no comer caché:

```bash
P='{"session_id":"lat-'$RANDOM'","cwd":"'$PWD'","hook_event_name":"UserPromptSubmit",
    "prompt":"quiero crear un skill nuevo para documentar el flujo de release y revisar el codigo"}'
time (echo "$P" | CLAUDE_PROJECT_DIR=$PWD bash hooks/<hook>.sh >/dev/null)
```

| hook | corridas individuales |
|---|---|
| session-wrapup-trigger | 0,24 / 0,12 / 0,13 s |
| cross-session-peer-context | 0,13 / 0,11 / 0,12 s |
| agent-message-inbox-context | 0,18 / 0,12 / 0,07 s |
| rule-router-prompt-suggest | 0,14 / 0,13 / 0,15 s |
| adr-relevance-suggest | 0,62 / 0,45 / 0,47 s |
| skill-router-prompt-suggest | 0,81 / 0,92 / 0,73 s |

**Los seis en paralelo** —que es lo que realmente cuesta bloquear, porque el host
corre el grupo de un matcher en paralelo— dan **0,83 / 0,83 / 0,90 s** de
wall-clock, marcados por `skill-router-prompt-suggest`. Secuencial (peor caso, si
el host los serializara) el mismo set da ~1,9 s. Las dos cifras quedan bajo el
techo de 3 s que `test_completes_under_3_seconds` asserta para el injector.

### Decisión, hook por hook

| hook | p50 reciente | directo | decisión | motivo |
|---|---:|---:|---|---|
| session-wrapup-trigger | 209 ms | 0,13 s | **sync** | costo despreciable; el aviso de cierre no sirve un turno después |
| cross-session-peer-context | 208 ms | 0,12 s | **sync** | ídem; el contexto de pares es sobre *este* prompt |
| agent-message-inbox-context | 212 ms | 0,12 s | **sync** | ídem; un mensaje de inbox leído tarde es un mensaje perdido |
| rule-router-prompt-suggest | 289 ms | 0,14 s | **sync** | la regla sugerida gobierna el prompt que la disparó |
| adr-relevance-suggest | 681 ms | 0,47 s | **sync** | el más caro de los baratos; sigue una orden de magnitud bajo el techo |
| skill-router-prompt-suggest | 935 ms | 0,73–0,92 s | **sync** | marca el paso del grupo; aun así ≈30% del techo |

**Ninguno queda async.** El único candidato defendible era
`skill-router-prompt-suggest` por su p95 de 4,4 s bajo carga real, y lo descarté
por dos razones: (a) ese p95 es de un proceso **de fondo** compitiendo con toda la
sesión —el mismo hook en primer plano mide 0,73–0,92 s—, y (b) dejarlo async
volvería decorativa la Parte 2: reescribir un texto que nunca llega a tiempo no
mejora nada. Queda como **presupuesto de performance**, no como excusa: si su p95
en primer plano supera 3 s, el arreglo es hacerlo más rápido.

Los tres hooks de `UserPromptSubmit` que **siguen async con motivo**:
`user-prompt-capture.sh`, `memory-prefetch.sh`, `stash-budget-warn.sh`. No emiten
`additionalContext` — son efecto de lado puro, no hay llegada que perder. El test
nuevo los excluye por censo, no por lista.

## La redacción nueva

`hooks/skill-router-prompt-suggest.sh`.

**Antes** (136 caracteres, ejemplo real):

> Skill router suggests `/skill-creator` (confidence 0.90) for this prompt. Invoke
> it when the workflow fits better than a bespoke prompt.

Problemas: «Invoke it when…» es discrecional y contradice `skill-invocation-mandatory`
(ADR-188), que a ≥0,90 declara la sugerencia vinculante. Y nombra la skill sin decir
qué hace ni qué cuesta: el consumidor compara un costo conocido (seguir a mano)
contra uno desconocido, y elige el conocido.

**Después** (367 caracteres, mismo prompt):

> Skill router: `/skill-creator` matches this prompt at 0.90. Applies when a user
> asks to create a new SKILL.md, turn repeated instructions into a reusable skill,
> migrate a…. Loading it costs ~2000 tokens. ADR-188 binds a match at 0.90+: the
> session invokes it, invokes a strictly stronger skill, or records
> `SKILL_BYPASS: skill-creator confidence=0.90 reason=<why>`.

Bajo el umbral el cierre cambia:

> Under the ADR-188 0.90 threshold, so advisory: the skill is the cheaper path
> wherever its workflow already covers the request.

Lo que se agregó y de dónde sale:

- **Qué hace**: `description` (o `whenToUse`) del frontmatter del propio SKILL.md,
  vía `_detect_skill_md_paths()` + `_read_skill_md_cached()` —ambas ya memoizadas
  por el router, así que no agrega parseos—. Primera oración, tope duro de 110
  caracteres. Se le saca el boilerplate `"Use when you need this Cognitive OS skill:"`
  que el generador antepone a todas y no informa nada.
- **Qué cuesta**: tamaño del SKILL.md / 4, redondeado a centenas → `~2000 tokens`.
- **Qué obliga**: escalonado por el umbral real de ADR-188 (0,90), que no es el
  umbral de emisión del hook (0,80). El texto anterior no distinguía; el nuevo sí.

Sobre el `authoring_guidance` del manifest (*«afirmaciones factuales, no
instrucciones imperativas de sistema»*): el texto nuevo no tiene ni un imperativo.
No dice «invocá la skill» ni «DEBÉS»; dice *«ADR-188 binds a match at 0.90+: the
session invokes it, invokes a strictly stronger skill, or records…»* — es la
descripción de una regla del repo, en tercera persona, enumerando los tres caminos
que la satisfacen. Directivo por precisión, no por tono de comando.

**Caracteres agregados: +231** (`/skill-creator`, 136 → 367) y **+165**
(`/repo-forensics`, 137 → 302). La diferencia entre los dos es el largo de la
`description` de cada skill. Se paga **solo en prompts que matchean ≥0,80**, no en
todos: el hook no emite nada por debajo del umbral (verificado: el tercer prompt de
prueba devolvió 0 bytes).

Latencia después del cambio: **0,68 / 0,68 / 0,70 s** contra 0,73–0,92 s antes.
Sin regresión.

## El test que faltaba

`tests/contracts/test_claude_code_hooks_schema_conformance.py`.

### Por qué el test viejo no lo agarraba

`test_async_not_used_on_prompt_preceding_context_events` deriva su conjunto de
eventos de `manifests/claude-code-hooks-schema.yaml`, campo
`handler_fields.async.contraindicated_for`, que nombra **`SubagentStart` y
`SessionStart`** — los dos eventos cuyo punto de inserción *precede al primer
prompt*. `UserPromptSubmit` inserta *junto al prompt*: otra categoría, y por eso
seis ofensores vivos pasaban el test **por quedar fuera de la pregunta**, no por
cumplirla. Baseline vacío y suite verde sobre un defecto real.

### Qué se agregó

1. **Manifest**: nueva lista `handler_fields.async.contraindicated_for_prompt_coupled_context`
   con `UserPromptSubmit` y el motivo escrito —misma clase de inferencia declarada
   que las otras dos entradas («Inference, not a quoted rule»), con la diferencia de
   categoría explicitada: *ahí no llega nada, acá llega un prompt tarde*.
2. **Test nuevo** `test_async_not_used_on_prompt_coupled_context_events`, con
   baseline propio `KNOWN_ASYNC_ON_PROMPT_COUPLED_EMITTER: set[str] = set()`, mismo
   estilo exacto que los otros cuatro: `unexpected` y `stale` en las dos
   direcciones, de modo que un baseline por encima de la realidad también falla.
3. **Dos guardas anti-vacuidad** dentro del test, que es la falla que este trabajo
   viene a cerrar: `assert contra` (si el manifest deja de declarar la
   contraindicación, el test grita en vez de pasar) y `assert emitters` (si el censo
   de emisores se rompe, ídem).
4. **Censo compartido** extraído a `_context_emitting_hooks()`, usado por los dos
   tests: el alcance sigue siendo solo hooks que emiten `additionalContext`.

Se dejó el test viejo intacto: su historia documentada (el caso del injector,
`0 de 149`) es evidencia, no ruido.

### Corrida ROJA — con el defecto presente

`.claude/settings.json` todavía con `async: true` en los seis:

```
$ .venv/bin/python3 -m pytest tests/contracts/test_claude_code_hooks_schema_conformance.py -q
...F..F...                                                               [100%]
=================================== FAILURES ===================================
E   AssertionError: Hooks registered async:true on UserPromptSubmit while emitting
    additionalContext: ['adr-relevance-suggest.sh on UserPromptSubmit',
    'agent-message-inbox-context.sh on UserPromptSubmit',
    'cross-session-peer-context.sh on UserPromptSubmit',
    'rule-router-prompt-suggest.sh on UserPromptSubmit',
    'session-wrapup-trigger.sh on UserPromptSubmit',
    'skill-router-prompt-suggest.sh on UserPromptSubmit']. Async output is delivered
    on the next conversation turn, so the context arrives attached to a prompt that
    did not produce it. [...]
tests/contracts/test_claude_code_hooks_schema_conformance.py:414: AssertionError

E   AssertionError: New hook header(s) contradict their registration in
    .claude/settings.json: ['adr-relevance-suggest.sh', 'rule-router-prompt-suggest.sh',
    'skill-router-prompt-suggest.sh']. Full set:
        adr-relevance-suggest.sh header says Async: false but registered on UserPromptSubmit with async=True
        rule-router-prompt-suggest.sh header says Async: false but registered on UserPromptSubmit with async=True
        skill-router-prompt-suggest.sh header says Async: false but registered on UserPromptSubmit with async=True
tests/contracts/test_claude_code_hooks_schema_conformance.py:281: AssertionError

=========================== short test summary info ============================
FAILED ...::test_hook_async_header_matches_registration
FAILED ...::test_async_not_used_on_prompt_coupled_context_events
2 failed, 8 passed in 0.71s
```

El test nuevo nombra **los seis ofensores, uno por uno**. El segundo fallo es el
ratchet de headers que ya existía haciendo su trabajo: al poner `# Async: false` en
los tres hooks que declaran el campo, y todavía con el registro en `true`, la
contradicción salta sola — exactamente lo que avisó el orquestador.

### Corrida VERDE — con el arreglo aplicado

Después de `bash scripts/apply-efficiency-profile.sh default`:

```
$ .venv/bin/python3 -m pytest tests/contracts/test_claude_code_hooks_schema_conformance.py -q
..........                                                               [100%]
10 passed in 0.79s
```

Las 9 que ya pasaban siguen pasando; la décima es la nueva.

### Verificación del generado (leída, no asumida)

```bash
python3 -c "import json;d=json.load(open('.claude/settings.json'))
for g in d['hooks']['UserPromptSubmit']:
    for h in g['hooks']: print('async=%-5s %s' % (h.get('async'), h['command'].split('/')[-1]))"
```

```
async=True  user-prompt-capture.sh          <- efecto de lado, correcto
async=None  session-wrapup-trigger.sh
async=None  session-heartbeat.sh
async=True  memory-prefetch.sh              <- efecto de lado, correcto
async=None  edit-lock-process-negotiations.sh
async=True  stash-budget-warn.sh            <- efecto de lado, correcto
async=None  cross-session-peer-context.sh
async=None  agent-message-inbox-context.sh
async=None  rule-router-prompt-suggest.sh
async=None  adr-relevance-suggest.sh
async=None  skill-router-prompt-suggest.sh
async=None  context-budget-meter.sh
```

## Lo que NO hice y por qué

- **No commiteé.** El worktree principal tiene trabajo concurrente del orquestador
  (`cos_lib/duplicate_scanner.py`, `hooks/orchestrator-skill-invocation-gate.sh`,
  dos archivos sin trackear). Mezclarlos en un commit mío sería justo lo que
  prohíbe la norma de escritores concurrentes. Tampoco pusheé.
- **No toqué `.claude/settings.json` a mano.** Es generado; se regeneró con el
  proyector y se verificó leyéndolo.
- **No moví ningún baseline.** Los cinco conjuntos `KNOWN_*` del archivo siguen
  vacíos. Meter los seis hooks en uno era el verde barato explícitamente prohibido.
- **No marqué nada `skip` ni `xfail`.**
- **No arreglé la deriva de autoridad del campo `async`** (declarado en dos lugares,
  leído de uno). Es un cambio de diseño del driver, excede este encargo, y hacerlo
  a medias sería peor. Queda como deuda con nombre: *el driver debería leer `async`
  de `cognitive-os.yaml` en vez de hardcodearlo, o el YAML no debería declararlo.*
- **No arreglé la deriva cosmética de `TaskCompleted`** en `settings.json`
  (`[]` → `[\n\n]`). Es preexistente, la introduce el generador, y aparece en mi
  diff sin ser mía.
- **No optimicé `skill-router-prompt-suggest`.** No hacía falta para esta decisión
  (0,73–0,92 s contra un techo de 3 s) y ya tuvo dos pasadas de performance el 18-08.
  Su p95 histórico bajo carga (4,4 s) queda anotado arriba como presupuesto a vigilar.
- **No corrí la suite completa del repo**, solo el archivo de contratos que pedía el
  encargo. El cambio de `.claude/settings.json` y del driver puede tener otros tests
  aguas abajo que no verifiqué.

---

**Rutas protegidas escritas con `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`** (queda
auditado en `.cognitive-os/metrics/protected-config-bypass.jsonl`):
`.claude/settings.json` (vía proyector), `hooks/skill-router-prompt-suggest.sh`,
`hooks/rule-router-prompt-suggest.sh`, `hooks/adr-relevance-suggest.sh`. El guard
también se dispara por **lecturas** cuyo comando menciona esas rutas (p. ej.
`python3 -c "...open('.claude/settings.json')"`), así que varias de las mediciones
de arriba llevan el prefijo sin ser escrituras.

**Validación de sintaxis**: `/bin/bash -n` (3.2.57, ruta absoluta) sobre
`scripts/_lib/settings-driver-claude-code.sh` y los tres hooks modificados.
`ast.parse` sobre el archivo de tests. El heredoc de Python dentro del hook, que
`bash -n` no inspecciona, se validó ejecutando el hook contra tres prompts reales.
