# Cinco hooks rotos — reproducción, arreglo y prueba (2026-08-19)

## Resumen ejecutivo

Los cinco diagnósticos se reprodujeron: ninguno se refutó en su sustancia, tres
se corrigieron en los números. Cuatro hooks quedaron arreglados con test propio
en `tests/hooks/` (39 casos): `decision-depth-gate` leía `.tool_result`, un campo
que este harness nunca manda; `post-git-orphan-notifier` capturaba `$?` después
de `|| true` y tenía el aviso al operador como código inalcanzable;
`stash-budget-warn` construía un contador de dos líneas (`"0\n0"`) que hacía
explotar el `[ -le ]` y disparaba "BUDGET EXCEEDED" con cero stashes;
`skill-post-execution-analysis` pedía un `skill_name` inexistente en vez de
`tool_response.agentType`. `teammate-idle` no se tocó: su evento no existe en
este harness y el repo ya lo contabiliza como tal. La corrida de falsificación
contra los hooks de HEAD deja 12 fallas y 27 pases; con los arreglos, 39 pases.
El aviso de huérfanos NO va a ser ruidoso: sobre el estado real habría disparado
0 veces en 13 escaneos. Quedan **tres hooks registrados más** leyendo campos
fantasma, uno de ellos con `exit 2`.

## Correcciones a las premisas del encargo

1. **Los conteos del encargo estaban bajos entre 1,5% y 3,2%.** Recontados sobre
   el vivo más los 7 rotados (`.cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz`),
   252.496 filas y no 245.527:

   | hook | encargo | recuento |
   |---|---|---|
   | `decision-depth-gate` | 176 | **182** |
   | `skill-post-execution-analysis` | 176 | **182** |
   | `post-git-orphan-notifier` | 8244 | **8508** |
   | `stash-budget-warn` | 330 | **335** |
   | `teammate-idle` | 0 / 245.527 | **0 / 252.496** |

   Reproducir:

   ```bash
   python3 - <<'EOF'
   import json,glob,gzip,collections
   c=collections.Counter(); tot=0
   for f in glob.glob('.cognitive-os/metrics/hook-timing*.jsonl')+glob.glob('.cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz'):
       op=gzip.open if f.endswith('.gz') else open
       for l in op(f,'rt',errors='ignore'):
           if not l.strip(): continue
           try: d=json.loads(l)
           except Exception: continue
           tot+=1; h=str(d.get('hook') or d.get('hook_name') or '')
           for n in ['decision-depth-gate','post-git-orphan-notifier','stash-budget-warn','skill-post-execution-analysis','teammate-idle']:
               if n in h: c[n]+=1
   print(tot, dict(c))
   EOF
   ```

2. **"8244 corridas del aviso inalcanzable" mide otra cosa que la que sugiere.**
   De esas 8508 invocaciones, el hook llegó a correr el scanner **13 veces**: el
   resto salió antes por el filtro de comando (`git status`, `git log`, etc.). El
   universo real del aviso son 13 escaneos, no 8508 — y eso es justamente lo que
   permite responder la pregunta de ruido.

3. **`stash-budget-warn` no "cae al aviso" siempre.** El bug del `grep -c` se
   manifiesta **sólo con cero coincidencias**. Con 4 stashes `grep` sale 0, el
   `|| echo "0"` no corre y el contador es correcto. Es decir: el hook estaba
   roto en la dirección de *disparar cuando no corresponde*, y funcionaba en la
   dirección de *disparar cuando corresponde* — salvo que en la práctica nunca
   llegaba, porque la sesión típica tiene 0 auto-stashes y ahí moría.

4. **`decision-depth-gate` tenía un segundo defecto que el encargo no menciona**:
   escribía el JSONL con `jq -n` (pretty, multilínea) sobre `safe_jsonl_append`,
   que espera UNA línea. Misma familia que el `jq -nc` que se le arregló hoy a
   `adversarial-review-gate`. Corregido acá también; sin eso, el ledger habría
   nacido ilegible para todo lector línea a línea.

5. **`.tool_response` del Agent no es un string, es un objeto.** El arreglo de
   hoy en `adversarial-review-gate` (`jq -r '.tool_response // ...'`) devuelve el
   JSON pretty-printeado del objeto, no el texto del agente. Funciona degradado
   (el texto está adentro, escapado) pero no es lo que el autor cree que lee. En
   `decision-depth-gate` se extrajo `content[].text` de verdad.

6. **El campo fantasma no son dos hooks, son cinco.** Además de los dos ya
   conocidos, siguen ciegos `trust-score-validator` (registrado, **con `exit 2`**),
   `review-spawner` (registrado) y `architecture-compliance` (no registrado); y
   `codebase-itinerary-capture` + `tool-sequence-capture` leen
   `.tool_response.exit_code`, que `hooks/_lib/tool-outcome.sh` documenta como
   inexistente. Detalle en §La clase del campo fantasma.

---

## `decision-depth-gate`

### reproducción

El mismo payload, cambiando sólo el nombre del campo:

```bash
D=$(mktemp -d); mkdir -p "$D/.cognitive-os/metrics"
OUT='Finding: the two configs diverge. I will document this difference and move on.'
COGNITIVE_OS_PROJECT_DIR=$D /bin/bash hooks/decision-depth-gate.sh \
  <<< "$(jq -nc --arg o "$OUT" '{tool_name:"Agent",tool_input:{description:"audit"},tool_result:$o}')"
COGNITIVE_OS_PROJECT_DIR=$D /bin/bash hooks/decision-depth-gate.sh \
  <<< "$(jq -nc --arg o "$OUT" '{tool_name:"Agent",tool_input:{description:"audit"},tool_response:$o}')"
```

Con `.tool_result` imprimía el `WARNING [decision-depth-gate]`; con
`.tool_response` — el campo que manda el harness — salía en silencio y sin
escribir nada. Concuerda con `.cognitive-os/metrics/decision-depth-gate.jsonl`
en 0 bytes desde el 2026-05-23 pese a 182 invocaciones, incluida la rama `pass`
que escribe incondicionalmente.

La forma real del `tool_response` del Agent está medida, no supuesta: 226
resultados reales en los transcripts de `~/.claude/projects` traen
`{status, agentType, content:[{type,text}], totalDurationMs, totalTokens,
totalToolUseCount, usage, toolStats, resolvedModel}`.

### arreglo

`hooks/decision-depth-gate.sh`: la extracción pasa a leer `.tool_response`
primero y, cuando es objeto, a juntar `content[].text` (con `tostring` como
respaldo si no hay `content`). `.tool_result` / `.output` quedan como fallback
para las formas Kiro/Devin. Además los dos `jq -n` pasan a `jq -nc`.

### las dos corridas

```
# HEAD (con el bug)
FAILED tests/hooks/test_decision_depth_gate.py::test_shallow_resolution_in_a_real_payload_is_warned
FAILED tests/hooks/test_decision_depth_gate.py::test_legacy_tool_result_string_still_warns
FAILED tests/hooks/test_decision_depth_gate.py::test_investigated_resolution_is_not_warned
FAILED tests/hooks/test_decision_depth_gate.py::test_log_is_one_json_object_per_line

# arreglado
tests/hooks/test_decision_depth_gate.py ........... 11 passed
```

---

## `post-git-orphan-notifier`

### reproducción

La forma del bug, aislada:

```bash
$ /bin/bash -c 'f(){ return 1; }; X=$(f) || true; E=$?; echo "SCAN_EXIT=$E"'
SCAN_EXIT=0
```

`$?` después de `|| true` es el estado de `true`. `SCAN_EXIT` valía 0 siempre y
el bloque `if [ "$SCAN_EXIT" -eq 1 ]` era inalcanzable. El scanner sí devuelve 1
cuando hay huérfanos — verificado en un repo de prueba con un commit tirado por
`git reset --hard`:

```
orphan sha= 2fca7c161dad6dd13c97b51beac909542293eeaa
exit= 1
ORPHAN COMMITS DETECTED (post-reset): 2fca7c1  to-be-orphaned
```

### ¿va a ser ruidoso?

No. El ledger que el scanner escribe es la evidencia de lo que el aviso habría
dicho, y dice cero:

```bash
python3 -c "
import json
rows=[json.loads(l) for l in open('.cognitive-os/metrics/orphan-notifier.jsonl') if l.strip()]
print(len(rows),'escaneos;',sum(1 for r in rows if r.get('orphan_count',0)>0),'con huerfanos')"
# 13 escaneos; 0 con huerfanos   (2026-08-15 → 2026-08-19)
```

13 escaneos en 4 días, ninguno con huérfanos: el aviso arreglado habría
disparado 0 veces. No hace falta amortiguarlo, y amortiguarlo sería el verde
barato de este hook.

### arreglo

`hooks/post-git-orphan-notifier.sh`: la invocación del scanner pasa a
`if SCAN_OUTPUT=$(...); then SCAN_EXIT=0; else SCAN_EXIT=$?; fi` — conserva la
propiedad de no abortar nunca y preserva el código real. Aparte se eliminó la
lectura muerta de `.tool_response.exit_code` (campo fantasma, ver §La clase);
no gateaba nada y era moot: un rebase que falla también deja commits colgando.

### las dos corridas

```
# HEAD (con el bug)
FAILED tests/hooks/test_post_git_orphan_notifier.py::test_orphaned_commit_reaches_the_operator
  AssertionError: the operator was never told about an orphaned commit — the alert block is unreachable

# arreglado
tests/hooks/test_post_git_orphan_notifier.py ......... 9 passed
```

Nótese que en HEAD el test negativo (`test_clean_repo_does_not_alert`) pasa: un
hook que nunca avisa satisface trivialmente "no avises de más". Por eso la
dirección positiva es la que prueba algo acá.

---

## `stash-budget-warn`

### reproducción

```bash
$ /bin/bash -c 'C=$(printf "" | grep -c -E "auto-pre-agent-" || echo "0"); echo "STASH_COUNT=[$C]"; [ "$C" -le 3 ] && echo under || echo "CAE AL AVISO"'
STASH_COUNT=[0
0]
/bin/bash: line 0: [: 0
0: integer expression expected
CAE AL AVISO
```

`grep -c` ya imprime `0` y sale 1 cuando no hay coincidencias; el `|| echo "0"`
agregaba un segundo `0`. El `[ -le ]` falla, el guard de "estoy bajo el umbral"
cae al aviso, y después el `printf %d` con `"0\n0"` dispara el `trap 'exit 0' ERR`
antes del cooldown y antes de las métricas. Eso explica que
`.cognitive-os/metrics/stash-budget.jsonl` no exista después de 335 corridas.

### arreglo

`hooks/stash-budget-warn.sh`: `|| true` en lugar de `|| echo "0"` (evita que el
ERR trap se dispare con el no-match de grep), recorte del sufijo no numérico y
un `case` que garantiza un entero antes de la aritmética.

### las dos corridas

```
# HEAD (con el bug)
FAILED tests/hooks/test_stash_budget_warn.py::test_zero_stashes_is_silent
FAILED tests/hooks/test_stash_budget_warn.py::test_unrelated_stashes_do_not_count

# arreglado
tests/hooks/test_stash_budget_warn.py ......... 9 passed
```

Este es el caso que justifica cubrir las dos direcciones: en HEAD el test
positivo (`test_over_budget_warns_and_records`) **pasa**. Un test que sólo
preguntara "¿avisa cuando hay 5 stashes?" habría dado verde sobre el hook roto.

---

## `skill-post-execution-analysis`

### reproducción

El hook pedía `payload.skill_name` / `tool_response.skill_name` /
`tool_input.skill`. Ninguno de los tres existe en un payload de `Agent`: el
identificador viene en `tool_response.agentType` (y en `tool_input.subagent_type`),
y `tool_input.skill` es del tool `Skill`, no del `Agent` — es el campo que lee
`hooks/skill-usage-tracker.sh`. Con `SKILL_NAME` vacío el hook salía en el
`if [ -z "$SKILL_NAME" ]`, por eso `.cognitive-os/skill_store.db` sigue en 0
bytes desde el 2026-05-06 tras 182 invocaciones.

Mismo origen de evidencia que arriba: 226 resultados reales, `status` siempre
`completed`, y las métricas bajo `totalToolUseCount` / `totalDurationMs` (no
`tool_count` / `duration_ms`).

### arreglo

`hooks/skill-post-execution-analysis.sh`: la identidad se resuelve en cascada
`skill_name → tool_response.agentType → tool_input.subagent_type →
tool_input.skill → tool_input.name`; el conteo y la duración se leen de
`totalToolUseCount` / `totalDurationMs` con los nombres viejos como respaldo; y
el fast-path deja pasar también el tool `Skill`.

**Registro no tocado**: el hook está registrado en `PostToolUse` con matcher
`Agent`. Con este arreglo captura las corridas de Agent, que es lo que estaba
roto. Agregar un matcher `Skill` haría que capture también las invocaciones de
skill — es un cambio de registro de eventos y queda para el operador.

### las dos corridas

```
# HEAD (con el bug)
FAILED tests/hooks/test_skill_post_execution_analysis.py::test_real_agent_payload_is_recorded
FAILED tests/hooks/test_skill_post_execution_analysis.py::test_failed_agent_call_is_still_recorded
FAILED tests/hooks/test_skill_post_execution_analysis.py::test_skill_tool_payload_is_recorded
FAILED tests/hooks/test_skill_post_execution_analysis.py::test_repeated_executions_accumulate
FAILED tests/hooks/test_skill_post_execution_analysis.py::test_discipline_gate_writes_only_proposals

# arreglado
tests/hooks/test_skill_post_execution_analysis.py .......... 10 passed
```

---

## `teammate-idle`: por qué no lo toqué

`TeammateIdle` **no es un evento de este harness**. `manifests/harness-driver-capabilities.yaml`
lo marca `cognitive_os_extension` en los cuatro drivers (y `unsupported` en el
cuarto) — es decir, una extensión propia que ningún driver emite hoy; en Codex y
OpenCode aparece además con `projection: requires_cos_runner` /
`requires_cos_or_opencode_plugin_adapter`, o sea que ni siquiera ahí existe sin
un adaptador que nadie escribió. Coincide con la telemetría: 0 filas en 252.496.

El repo **ya lo tiene contabilizado**: `manifests/hook-vitality-budget.yaml`
define `max_event_absent_hooks: 2` con el comentario "Hooks registrados en un
evento que este harness nunca emite. Muertos por harness, no por bug", nombrando
`task-created` y `teammate-idle`. No hay nada roto que arreglar y la deuda ya
está escrita.

Lo que corresponde, para decisión del operador (no ejecutado):

- **Documentarlo como inactivo** es lo que ya está hecho; alcanza si se acepta
  que el hook viaje como capacidad latente para cuando Agent Teams se habilite.
- **Desregistrarlo** es lo único que baja `max_event_absent_hooks` a 1, y tiene
  costo: el body del hook está sano y `tests/hooks/test_agent_teams_hooks.py`
  cubre 7 escenarios suyos; desregistrar deja esos tests probando un hook que no
  está enganchado a nada.
- **Implementarlo** (un runner COS que emita el evento) es trabajo de ADR-233, no
  un arreglo de hook.

Recomendación: dejarlo registrado y documentado, y mover la decisión al día en
que el operador toque Agent Teams. Cambiar el registro de eventos es suyo.

## La clase del campo fantasma

No son dos hooks: son **cinco leyendo `.tool_result` o `.exit_code` como única
fuente o como fuente principal**, más dos leyendo `.tool_response.exit_code`.
Barrido reproducible:

```bash
python3 - <<'EOF'
import json,re,pathlib
reg=set()
for ev,groups in json.load(open('.claude/settings.json')).get('hooks',{}).items():
    for g in groups:
        for h in g.get('hooks',[]):
            reg.update(re.findall(r'hooks/([a-z0-9._-]+\.sh)', h.get('command','')))
for f in sorted(pathlib.Path('hooks').glob('*.sh')):
    for l in (x.strip() for x in f.read_text(errors='ignore').splitlines()):
        if l.startswith('#'): continue
        if '.tool_result' in l or '.exit_code' in l:
            estado = 'REGISTRADO' if f.name in reg else 'no-registrado'
            ciego  = 'CIEGO' if 'tool_response' not in l else 'fallback'
            print(f'{estado:14s} {ciego:9s} {f.name:38s} {l[:90]}')
EOF
```

| hook | registrado | lectura | corridas |
|---|---|---|---|
| `trust-score-validator.sh` | sí | `.tool_result // .output` — **ciego** | 186 |
| `review-spawner.sh` | sí | `.tool_result // .output // .tool_output` — **ciego** | 186 |
| `architecture-compliance.sh` | no | `.tool_result // .result` — ciego | — |
| `codebase-itinerary-capture.sh` | sí | `.tool_response.exit_code` — fantasma | 332 |
| `tool-sequence-capture.sh` | sí | `.tool_response.exit_code` — fantasma | 10.758 |

**No los arreglé**, y no por trivialidad: `trust-score-validator` tiene `exit 2`
en la línea 118. Arreglarle el campo lo convierte, de un no-op de 186 corridas,
en un **bloqueador activo** — eso no es un fix de una línea, es encender un gate.
`review-spawner` lanza agentes: encenderlo cambia el gasto. Los dos merecen el
mismo tratamiento que estos cuatro (reproducción, arreglo, test en las dos
direcciones), en un encargo propio donde se mire qué empieza a bloquear.
Los dos de `.tool_response.exit_code` tienen la respuesta ya escrita en
`hooks/_lib/tool-outcome.sh` (clasificar por CAMBIO DE TIPO de `tool_response`);
les falta migrar, no diagnosticar.

### ¿vale una guarda de contrato?

Sí, y **no la construí** porque el encargo pide avisar primero. Ya existe
`tests/contracts/test_claude_code_hooks_schema_conformance.py`, que valida la
**salida** de los hooks contra `manifests/claude-code-hooks-schema.yaml`. Falta
el lado espejo: la **entrada**. El manifiesto hoy no tiene una sección de campos
de stdin por evento (sólo `SubagentStart.stdin_fields`), así que la guarda pide
dos cosas, en este orden:

1. agregar `stdin_fields` a `PostToolUse` en el manifiesto
   (`session_id, transcript_path, cwd, permission_mode, hook_event_name,
   tool_name, tool_input, tool_response`), citando la fuente como el resto del
   archivo;
2. un test que barra `hooks/*.sh` buscando lecturas de campos de nivel superior
   que no estén en esa lista, con una allowlist chica y **motivada** para las
   formas de otros harnesses (`.tool_result`, `.output` como *fallback*), y que
   falle cuando un campo ajeno es la ÚNICA fuente.

El matiz que lo hace útil en vez de ceremonial: prohibir `.tool_result` a secas
rompería la portabilidad a Kiro/Devin que varios hooks sostienen a propósito. Lo
que hay que prohibir es que el campo fantasma sea el **primero** de la cascada.

## Lo que NO hice y por qué

- **No arreglé `trust-score-validator` ni `review-spawner`** (ver arriba): un
  campo corregido los enciende, y uno de ellos bloquea. Necesitan su propio
  encargo con test de las dos direcciones.
- **No toqué `adversarial-review-gate`**, arreglado hoy por el orquestador,
  aunque su `jq -r '.tool_response'` sobre un objeto le entrega JSON
  pretty-printeado en vez del texto del agente. Funciona degradado; corregirlo
  ahí exige tocar su test, que fija el payload como string.
- **No registré `skill-post-execution-analysis` en el matcher `Skill`**: cambia
  el registro de eventos, que es decisión del operador.
- **No desregistré `teammate-idle`** ni toqué `.claude/settings.json`.
- **No amortigüé el aviso de huérfanos**: medí que no hace falta (0/13). Bajarle
  el volumen "por las dudas" sería apagar el rojo en vez del problema.
- **No construí la guarda de contrato de entrada**: pedida al operador primero,
  como indica el encargo.
- **No commiteé ni pusheé nada**: todo queda en el working tree.

## Cómo reproducir todo

```bash
# los cuatro arreglados
.venv/bin/python3 -m pytest tests/hooks/test_decision_depth_gate.py \
  tests/hooks/test_post_git_orphan_notifier.py \
  tests/hooks/test_stash_budget_warn.py \
  tests/hooks/test_skill_post_execution_analysis.py -q -p no:randomly
# 39 passed

# falsificación: los mismos tests contra los hooks de HEAD
B=$(mktemp -d)/buggy; mkdir -p "$B/hooks"
for f in decision-depth-gate post-git-orphan-notifier stash-budget-warn skill-post-execution-analysis; do
  git show HEAD:hooks/$f.sh > "$B/hooks/$f.sh"
done
COS_TEST_HOOK_SOURCE_DIR="$B" .venv/bin/python3 -m pytest tests/hooks/test_decision_depth_gate.py \
  tests/hooks/test_post_git_orphan_notifier.py \
  tests/hooks/test_stash_budget_warn.py \
  tests/hooks/test_skill_post_execution_analysis.py -q -p no:randomly
# 12 failed, 27 passed
```
