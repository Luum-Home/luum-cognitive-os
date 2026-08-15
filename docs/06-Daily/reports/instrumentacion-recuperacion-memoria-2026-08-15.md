# Instrumentación de recuperación de memoria — 2026-08-15

**Veredicto.** El hook `engram-reinforce-on-access.sh` estaba registrado desde el
2026-05-05 y nunca escribió una fila, por **dos defectos independientes, cada uno
fatal por sí solo**: leía un campo que el harness no manda (`tool_result`), y
—aun sobre el campo correcto— buscaba una forma que una respuesta MCP no tiene.
Arreglar sólo el primero habría movido de un fantasma a otro. Los dos están
arreglados, y hay un verificador de **llegada** que hoy dice, con razón, que
todavía no llegó nada.

El límite que el encargo anticipaba —"quizás el hook no puede ver lo recuperado
porque `mem_search` es un MCP externo"— **no existe**. La respuesta llega entera
al payload, con los ids de las observaciones adentro.

---

## Correcciones a las premisas del encargo

| # | Premisa | Estado |
|---|---|---|
| 1 | "17.417 observaciones escritas y **cero evidencia de una sola lectura en toda la historia**" | **Falsa en la segunda mitad.** Evidencia de lecturas hay de sobra: 30 recuperaciones reales en los transcripts de este proyecto (13 con resultados, 8 con "No memories found"), la última el 2026-07-10. Lo que estaba en cero era el registro **propio del SO**, no la evidencia. La distinción importa: creer que "no hay evidencia" habilitaba concluir "el hook no puede ver nada", y la evidencia estaba a un directorio de distancia. |
| 2 | "17.417 observaciones" | **No verificada.** No consulté la base de Engram (prohibido por el encargo, y no hacía falta). El número no lo reproduje y no lo cito como propio. |
| 3 | "`engram-reinforce-on-access.sh` está registrado con el matcher correcto" | **Confirmada.** `.claude/settings.json`, bloque PostToolUse, matcher exactamente `mcp__plugin_engram_engram__mem_search\|mcp__plugin_engram_engram__mem_get_observation`, con `async: true`. Registrado desde `3ba41b39a` (2026-05-05). |
| 4 | "el ledger no existe — ni vivo ni en `.archive/*.gz`" | **Confirmada.** `find . -name '*lifecycle-reinforcement*' -not -path './.git/*'` → 0 resultados. |
| 5 | "el esquema de la base tampoco tiene contador de accesos" | **No verificada** — no toqué la base. Es además irrelevante: el ledger no lo necesita. |
| 6 | "si la respuesta de `mem_search` no llega al payload, decilo y no lo simules" | **Refutada — la salida de emergencia no hacía falta.** El payload trae la respuesta completa. Ver §2. |
| 7 | "`cos_lib/memory_retriever.py` sólo se instancia en `mcp-server/cos_mcp.py:176`" | **Confirmada, literal.** `grep -rn "MemoryRetriever" --include="*.py"` da una sola instanciación fuera de tests, en esa línea exacta. El `mem_search` que usan los agentes es el server del plugin (`mcp__plugin_engram_engram__*`), que no pasa por ahí: el chequeo de frescura está efectivamente puenteado. |
| 8 | Permiso: `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` sólo para ese hook | **Usado, y sólo para ese archivo.** No verifiqué que sin la variable el guard hubiera bloqueado, así que no puedo afirmar que el permiso fuera necesario — sólo que fue suficiente. |

### Un error mío, del mismo tipo que el encargo advierte

Mi primera lectura fue: "0 disparos en 20.447 filas de `hook-timing.jsonl` ⇒ el
hook nunca corrió". **Mal.** `hook-timing.jsonl` cubre sólo tres horas de hoy
(`19:32:58Z` → `22:35:32Z`), y la última recuperación de engram en este proyecto
fue el 2026-07-10. Ese cero no medía el hook, medía la ventana. La evidencia
buena es otra: 30 recuperaciones reales **posteriores al registro** y 0 filas.

```bash
python3 -c "
import json
ts=[json.loads(l).get('timestamp') for l in open('.cognitive-os/metrics/hook-timing.jsonl')]
ts=[t for t in ts if t]; print(len(ts), min(ts), max(ts))"
# 20763 2026-08-15T19:32:58Z 2026-08-15T22:35:32Z
```

---

## 1. Qué campos llegan de verdad, y con qué comando

El campo es **`tool_response`**. No `tool_result`, no `tool_output`, no
`toolUseResult` (ése es el nombre en el transcript, no en el stdin del hook). Es
el mismo contrato que ya documenta `hooks/_lib/tool-outcome.sh`.

Para un tool MCP, `tool_response` **no es un objeto**: es un **array de bloques de
contenido**.

```
tool_response = [ {"type":"text","text":"<json string>"} ]
                                          │
                                          └─ {"project", "project_path",
                                              "project_source", "result"}
                                                                    │
                                              result es PROSA, y los ids
                                              viven ahí como "#<dígitos>"
```

Formas reales, leídas de 89 resultados de engram en transcripts locales:

```bash
python3 - <<'EOF'
import json,glob,os,collections
fs=glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl"))
res=collections.Counter()
for f in fs:
    lines=open(f,errors="replace").readlines(); calls={}
    for l in lines:
        try: r=json.loads(l)
        except: continue
        c=(r.get("message") or {}).get("content")
        if isinstance(c,list):
            for b in c:
                if isinstance(b,dict) and b.get("type")=="tool_use" and (
                   "mem_search" in str(b.get("name","")) or "mem_get_observation" in str(b.get("name",""))):
                    calls[b.get("id")]=b.get("name")
    for l in lines:
        try: r=json.loads(l)
        except: continue
        c=(r.get("message") or {}).get("content")
        if not isinstance(c,list): continue
        for b in c:
            if isinstance(b,dict) and b.get("type")=="tool_result" and b.get("tool_use_id") in calls:
                res[(calls[b["tool_use_id"]].split("__")[-1], type(r.get("toolUseResult")).__name__)]+=1
print(dict(res))
EOF
# {('mem_search','list'): 82, ('mem_get_observation','list'): 7,
#  ('mem_get_observation','str'): 1, ('mem_search','str'): 2}
```

Prosa de un acierto de `mem_search`, tal cual llega:

```
Found 1 memories:

[1] #29943 (manual) — Auditoría arquitectura + seguridad de g2k-packgo-v2
    ... [preview]
```

y de `mem_get_observation`: `#29943 [manual] Título`.

### Por qué el hook viejo no podía escribir nada

Dos cortes, en cascada:

1. `data.get("tool_result") or data.get("tool_output") or {}` → siempre `{}`.
   El `or {}` es la misma patología que el `// "0"` de `error-learning`: convierte
   *ausencia* en un valor legal, así que el fallo es invisible.
2. Aunque hubiera leído `tool_response`, su `collect_ids()` buscaba dicts con
   clave `"id"`. En un payload MCP **no hay ninguna**. Cero ids → `exit 0` en la
   línea 135, sin ledger y sin ruido.

Demostrado corriendo el hook **de HEAD** contra un payload **real**:

```bash
git show HEAD:hooks/engram-reinforce-on-access.sh > /tmp/old-hook.sh
COGNITIVE_OS_PROJECT_DIR=/tmp/tr bash /tmp/old-hook.sh < payload_search_hit.json
# exit 0, y ni siquiera creó .cognitive-os/metrics/ — cero filas
```

### Nota lateral: `classify_tool_outcome()` no cubre payloads MCP

`hooks/_lib/tool-outcome.sh` ramifica sobre `tool_response` siendo **string** u
**objeto**. Un array cae al `else` final y sale `absent`:

```bash
. hooks/_lib/tool-outcome.sh
classify_tool_outcome "$(cat payload_search_hit.json)"; echo $TOOL_OUTCOME
# absent
```

No es un bug del clasificador —es correcto para Bash/Read/Write/Edit/Agent, que
es sobre lo que se midió— pero **cualquier hook que lo aplique a un tool MCP va a
leer `absent` sobre un payload perfectamente legible**. Vale como aviso para los
demás consumidores. Este hook usa su *registrador de drift*, no su veredicto, y
lo dice en la cabecera.

---

## 2. El límite que el encargo esperaba, y que no está

La hipótesis era: el hook quizás sólo ve "hubo una llamada", no "se recuperó
esto". **No es el caso.** El payload trae la respuesta completa del server MCP:
qué observaciones volvieron, con qué ids, de qué proyecto, y si la búsqueda no
encontró nada. Por eso no hay que simular nada y el ledger puede ser honesto.

Sí hay un límite real, más chico: `project_path` viene en el payload y es una
ruta absoluta con el usuario del operador. **Se descarta a propósito**; sólo se
guarda el nombre del proyecto.

---

## 3. Qué se escribe, y qué deliberadamente no

Una fila **sólo** cuando el payload se leyó y el resultado se observó:

| `outcome` | Significa |
|---|---|
| `hit` | `observation_ids[]` son las observaciones que el harness devolvió |
| `miss` | el server contestó "No memories found" — un negativo real y útil: se consultó la memoria y no había nada |

No se escribe fila por "se llamó al tool". Un ledger que cuenta invocaciones
parece cobertura y no mide nada — es exactamente el verde barato que el encargo
marcaba. Un payload ilegible va a `payload-contract-drift.jsonl`, **nunca** al
ledger.

Filas reales, producidas por el hook nuevo sobre payloads reales:

```json
{"timestamp":"2026-08-15T22:37:38Z","tool":"mem_search","outcome":"hit","observation_ids":["29943"],"n":1,"project":"g2k-packgo-v2"}
{"timestamp":"2026-08-15T22:37:38Z","tool":"mem_search","outcome":"miss","observation_ids":[],"n":0,"project":"g2k-time-tracker"}
{"timestamp":"2026-08-15T22:37:38Z","tool":"mem_get_observation","outcome":"hit","observation_ids":["29943"],"n":1,"project":"g2k-packgo-v2"}
```

**Extracción de ids anclada.** Un `#(\d+)` suelto sobre la prosa también
matchearía números de PR o de issue citados *dentro del cuerpo de una
observación*, inflando el ledger con ids que nunca se recuperaron. Se anclan a
inicio de línea: `[N] #id (` para `mem_search`, `#id [` para
`mem_get_observation`.

---

## 4. Cómo se prueba la llegada, no la emisión

`scripts/check_memory_retrieval_arrival.py`. La regla que lo define:

> No sintetiza un payload, se lo pasa al hook y después encuentra su propia fila.
> Eso pondría el semáforo en verde sin probar nada.

Compara dos cosas que el hook no controla:

- **verdad de terreno**: las recuperaciones visibles en transcripts reales, con
  los ids que el server MCP devolvió de verdad;
- **medido**: las filas del ledger.

**Llegada** = una fila cuyos ids aparecen también en una recuperación real. Eso
contesta la pregunta 4 de ADR-342 ("¿se lo vio decidir? al menos una decisión
registrada sobre una entrada real, no una fixture") sobre datos reales.

Códigos de salida: `0` llegó / `1` hubo recuperaciones y no se registraron /
`2` nada que medir.

Estado honesto de hoy, después del arreglo:

```bash
python3 scripts/check_memory_retrieval_arrival.py -v
# retrievals seen: 30  (hits 13, stated misses 8)
# ledger         : ABSENT  rows=0
# VERDICT: DOES NOT ARRIVE — 30 real retrieval(s) on record, 0 ledger row(s)
#          corroborated by them.
# exit=1
```

### Y después ocurrió una recuperación real

Con el hook ya commiteado, se hizo un `mem_search` de verdad por el harness
—ninguna simulación, ninguna fixture— y **el ledger apareció en producción**:

```bash
ls -la .cognitive-os/metrics/lifecycle-reinforcement.jsonl
# -rw-r--r--  148  Aug 15 19:42
cat .cognitive-os/metrics/lifecycle-reinforcement.jsonl
# {"timestamp":"2026-08-15T22:42:56Z","tool":"mem_search","outcome":"hit",
#  "observation_ids":["32048"],"n":1,"project":"luum-cognitive-os"}

grep -c 'engram-reinforce' .cognitive-os/metrics/hook-timing.jsonl
# 1   ← primer disparo registrado del hook, nunca antes
```

El id `32048` es exactamente la observación que esa búsqueda devolvió. El hook
escribe, en producción, sobre una recuperación real.

**Y eso destapó un defecto en mi propio verificador**, que vale registrar porque
es del mismo tipo que todo lo demás: con la fila fresca en el ledger, el checker
seguía diciendo *"DOES NOT ARRIVE — the hook is not recording what the harness
retrieves"*. Falso, y ya demostrablemente falso. La causa es benigna: el harness
vuelca el transcript de la sesión en curso con retraso, así que una fila escrita
hace segundos todavía no tiene transcript que la respalde. El veredicto se
corrigió a **`PENDING CORROBORATION`** — *el hook SÍ está escribiendo; la llegada
todavía no es demostrable* — que sigue saliendo por 1, porque no probado no es
probado, pero ya no afirma lo contrario de lo que se ve.

**El ledger no se backfilleó.** Llenarlo con las recuperaciones de julio para que
el checker diera 0, con timestamps de hoy sobre eventos de hace un mes, era el
verde barato de este entregable. La única fila que hay la escribió el harness.

### Que la rama positiva no sea inalcanzable

Un verificador que siempre devuelve 1 no verifica. Se probó la rama `ARRIVES`
con `HOME` temporal, transcripts **reales** copiados, y el ledger generado
replayeando **esos mismos payloads reales** por el hook **real** — nada
sintético:

```
real transcripts copied: 60   real payloads to replay: 21
ledger rows written by the REAL hook: 20
VERDICT: ARRIVES — 56 observation id(s) present in both a real retrieval
         and the ledger. ADR-342 Q4 satisfied for this hook.
exit=0
```

21 payloads → 20 filas: el `while IFS= read -r` del replay descarta la última
línea sin `\n` final. Es un artefacto del arnés de prueba, no del hook.

### Control negativo: el arreglo es portante

Al hook nuevo se le pasó el payload real con el campo renombrado al fantasma
viejo (`tool_result`):

```
ledger rows: 0
drift rows:
{"timestamp":"2026-08-15T22:37:54Z","hook":"engram-reinforce-on-access.sh",
 "reason":"tool_response absent, or MCP content shape not recognised — no retrieval could be observed"}
```

Cero filas y **una alarma**, en vez de un `exit 0` mudo.

---

## 5. Diff completo del hook

Condición del permiso. `git diff hooks/engram-reinforce-on-access.sh`:
169 inserciones, 128 borrados. Cambios de fondo:

- **Campo**: `data.get("tool_result") or data.get("tool_output") or {}` →
  `data["tool_response"]`, y su ausencia **sale por 3** (drift), no por 0.
- **Forma**: `collect_ids()` recursivo buscando clave `"id"` → aplanado de
  bloques de contenido MCP + parseo del JSON interno + regex anclada sobre
  `result`.
- **Semántica de la fila**: `{timestamp, observation_id, tool}` por id →
  `{timestamp, tool, outcome, observation_ids[], n, project}` por evento, con
  `outcome ∈ {hit, miss}`. `project_path` se descarta por privacidad.
- **Drift**: no existía. Ahora un payload ilegible escribe en
  `payload-contract-drift.jsonl` vía `record_payload_contract_drift()`.
- **Subprocesos**: 3 (`extract` + `json.dumps` + `batch_reinforce`) → 1.
- **Cabecera**: la vieja decía "This hook is DORMANT until registered" — falso
  desde el 2026-05-05. Reemplazada por el diagnóstico y el comando que lo
  reproduce.
- `reinforce()` ahora corre **sólo sobre ids realmente devueltos**.

El diff textual completo está en el commit; el archivo entero es legible en
`hooks/engram-reinforce-on-access.sh` y su cabecera lleva el porqué de cada
decisión.

---

## 6. Lo que queda abierto

- **La escritura en producción está probada; la corroboración todavía no.** El
  harness disparó el hook y el ledger se escribió (§4). Falta que el transcript
  de esta sesión se vuelque para que el checker pueda cruzar la fila contra la
  recuperación que la causó. Correr de nuevo `check_memory_retrieval_arrival.py`
  después de cerrar la sesión: debería pasar de `PENDING CORROBORATION` a
  `ARRIVES`. Si no pasa, hay algo más.
- **`async: true`** en el registro: quedó demostrado que un hook async se ejecuta
  y escribe (el ledger apareció), pero no medí si el payload que recibe es
  idéntico en todos los casos.
- **`classify_tool_outcome()` sobre tools MCP** devuelve `absent` sobre payloads
  legibles. Este hook lo esquiva; otros consumidores puede que no.
- **El puenteo de `MemoryRetriever`** (premisa 7) sigue en pie: el chequeo de
  frescura de `cos_lib/memory_retriever.py` no corre para el `mem_search` que
  usan los agentes. Este trabajo lo documenta, no lo arregla.
