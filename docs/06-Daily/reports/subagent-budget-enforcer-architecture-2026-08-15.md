# Partición de `subagent-budget-enforcer` en dos modos — diseño, medición y parches

**Fecha:** 2026-08-15
**Alcance:** `hooks/subagent-budget-enforcer.sh`, su registro, y el contrato de tests.
**Estado:** diseño confirmado con correcciones. **Ningún parche aplicado** a `hooks/` ni
a `.claude/settings.json` (superficies protegidas). Entregado: parches exactos + test
partido + medición.

---

## 1. Veredicto en una línea

El defecto es real y peor de lo reportado: el hook está registrado **solo en
`PostToolUse`**, sus bloqueos no previenen nada, y **cada bloqueo consume presupuesto**,
así que un agente bloqueado sigue gastando el contador mientras reintenta. El diseño del
chip `task_885b5369` es correcto en su núcleo, pero **le faltan tres piezas sin las
cuales el `PreToolUse` sería un gate de cartón**: el registro no se hace donde el encargo
dice, la identidad del agente no está garantizada en `PreToolUse`, y el pase por
`ESCALATION:` es un agujero abierto que en enforce se vuelve un bypass permanente.

---

## 2. Recuento: qué del encargo era cierto y qué no

| # | Premisa del encargo | Veredicto | Evidencia |
|---|---|---|---|
| 1 | Registrado solo en `PostToolUse`, `matcher: ""` | **Cierto** | §2.1 |
| 2 | «48 `exit 2`» | **Desactualizado** — son **50** y siguen subiendo hoy; en el ledger propio del hook son **95** bloqueos | §2.2 |
| 3 | Es el conteo de bloqueos más alto del sistema | **Cierto** (50 vs. 20 del segundo) | §2.2 |
| 4 | Ninguno previno una llamada | **Cierto, y peor**: 61 llamadas se gastaron *después* del primer bloqueo | §2.2 |
| 5 | «El registro canónico vive en `cognitive-os.yaml > harness.hooks`» | **Falso para Claude Code** | §2.3 |
| 6 | «Registrarlo en Pre duplica ~5 spawns de `python3` por tool call» | **Cifra corregida**: hoy son **2** spawns por llamada de orquestador y **5–6** por llamada de subagente | §2.4 |
| 7 | «El bail temprano deja el orquestador en cero spawns» | **Cierto como filtro negativo**, falso como test de subagente | §4.1 |
| 8 | «El repo ya tiene `safe_jsonl_append` con lock por `mkdir`» | **Cierto** — y es la herramienta equivocada acá | §4.2 |
| 9 | «El presupuesto 50 lo chocan constantemente» | **Cierto**: 46,9 % de los subagentes lo superan | §4.4 |
| 10 | Chip: «los chequeos de `ESCALATION:` y bypass van solo en enforce» | **Incompleto y peligroso** tal cual está | §4.5 |
| 11 | «Puede haber un cableado en `PreToolUse` que nadie vio» | **No existe** — barrido de 6 superficies, cero | §2.1 |

### 2.1 Registro: una sola entrada, `PostToolUse`

```bash
python3 -c "
import json
s=json.load(open('.claude/settings.json'))
for ev,groups in s.get('hooks',{}).items():
    for g in groups:
        for h in g.get('hooks',[]):
            if 'subagent-budget' in json.dumps(h):
                print(ev,'| matcher=',repr(g.get('matcher')),'|',h.get('command'))
"
# PostToolUse | matcher= '' | bash ".../hook-timing-wrapper.sh" PostToolUse ".../hooks/subagent-budget-enforcer.sh"
```

Barrido de todas las superficies donde podría existir otro cableado — settings de
proyecto, settings de usuario, `settings.local.json`, `opencode.json`,
`.codex/config.toml`, y la copia proyectada `.cognitive-os/hooks/`:

```bash
for p in ~/.claude/settings.json ~/.claude/settings.local.json .claude/settings.local.json \
         opencode.json .codex/config.toml; do
  [ -e "$p" ] && echo "$p -> $(grep -c 'subagent-budget' "$p")"
done
# todas devuelven 0
```

Y en la telemetría, **1718 invocaciones, el 100 % con `event=PostToolUse`**:

```bash
python3 -c "
import json,collections
c=collections.Counter()
for l in open('.cognitive-os/metrics/hook-timing.jsonl',errors='ignore'):
    try: r=json.loads(l)
    except Exception: continue
    if r.get('hook')=='subagent-budget-enforcer': c[r.get('event')]+=1
print(dict(c))
"
# {'PostToolUse': 1718}
```

No hay cableado oculto. El encargo se sostiene.

### 2.2 Recuento de bloqueos: 50, no 48 — y 95 en el ledger propio

El número del encargo salió de `hook-timing.jsonl`, que es una ventana móvil (arranca
`2026-08-15T04:42:23Z`). Hoy va en **50**, porque el hook siguió bloqueando durante la
propia auditoría:

```bash
python3 -c "
import json,collections
ec=collections.Counter(); rows=[]
for l in open('.cognitive-os/metrics/hook-timing.jsonl',errors='ignore'):
    try: r=json.loads(l)
    except Exception: continue
    if r.get('exit_code')==2: ec[r.get('hook')]+=1
    if r.get('hook')=='subagent-budget-enforcer': rows.append(r)
print('exit2 por hook:',dict(ec))
print('ventana:',min(r['timestamp'] for r in rows),'->',max(r['timestamp'] for r in rows))
"
# exit2 por hook: {'subagent-budget-enforcer': 50, 'bash-hot-path-dispatcher': 20,
#                 'protected-config-write-guard': 7, 'provenance-scan': 3,
#                 'exit2-hook': 1, 'lethal-trifecta-gate': 1}
```

> **Nota para quien repita esto:** filtrar por `hook == 'subagent-budget-enforcer.sh'`
> devuelve **0**. El campo `hook` en `hook-timing.jsonl` **no lleva la extensión**. Un
> primer intento mío dio «0 invocaciones» por ese motivo; la conclusión correcta apareció
> recién al enumerar los 156 valores distintos del campo.

El ledger propio del hook cubre desde el 2026-07-02 y da el número grande:

```bash
python3 -c "
import json,collections
rows=[json.loads(l) for l in open('.cognitive-os/metrics/subagent-budget-enforcer.jsonl') if l.strip()]
print('filas',len(rows), collections.Counter(r['action'] for r in rows))
blk=collections.Counter((r['session_id'][:8],r['agent_id']) for r in rows if r['action']=='block')
print('agentes bloqueados:',len(blk),'| filas block:',sum(blk.values()),'| peor:',blk.most_common(1))
"
# filas 614 Counter({'observe': 431, 'block': 95, 'allow': 52, 'warn': 36})
# agentes bloqueados: 34 | filas block: 95 | peor: [(('05404980','a26243aae0709953c'), 10)]
```

**95 bloqueos repartidos en 34 agentes = 61 llamadas consumidas *después* del primer
bloqueo.** Es la métrica que mejor describe el defecto: el hook incrementa el contador en
la línea 118 *antes* de decidir si bloquea (línea 182), así que cada reintento bloqueado
—que ya corrió, porque es `PostToolUse`— también gasta presupuesto. Un agente llegó a 10
bloqueos consecutivos.

### 2.3 El registro canónico NO es `cognitive-os.yaml` (para Claude Code)

Esta es la corrección más importante para quien aplique el parche.

`scripts/_lib/settings-driver-claude-code.sh` **nunca parsea el YAML**. Declara
`CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"` en la línea 39 y no lo vuelve a usar
nunca; los grupos de hooks son arreglos bash literales (líneas 196–340):

```bash
grep -n "CONFIG_FILE" scripts/_lib/settings-driver-claude-code.sh
# 39:CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"     <- única aparición

grep -n "cognitive-os.yaml" scripts/_lib/settings-driver-claude-code.sh
# 3, 6, 19  -> comentarios ("ADR-064: canonical hook registry lives in ...")
# 32, 39    -> detección de raíz de proyecto
```

Y su modo `--check` compara **su propia salida generada** contra `.claude/settings.json`,
no contra el YAML (líneas 560–585). O sea: el YAML *declara* y los censos lo leen, pero
lo que se emite sale del driver. **Un parche que toque solo `cognitive-os.yaml` no cambia
nada en Claude Code y además introduce drift.** Hay que tocar los dos.

Los drivers de Codex, opencode y bare **sí** parsean el YAML
(`settings-driver-codex.sh:163` lee `entry.get("event")`), así que el YAML sigue siendo
obligatorio — es la única fuente para esos harnesses y para
`primitive-harness-coverage`.

Esto es deuda de verdad documental: el encabezado del driver afirma ser generado desde
`harness.hooks` y no lo es. Va como entrada al ledger de pending-truth (§8).

### 2.4 Costo real de hoy, contado por líneas

`python3` se invoca en las líneas 26, 93, 96, 97, 98 y dentro de `emit_metric` (126):

- **Llamada de orquestador** (el caso mayoritario): línea 26 + línea 93 → sale en la 94.
  **2 spawns.**
- **Llamada de subagente**: 26, 93, 96, 97, 98 → **5 spawns**, **6** cuando además emite
  métrica.

Lo que eso cuesta en la práctica:

```bash
python3 -c "
import json
d=sorted(json.loads(l)['duration_ms'] for l in open('.cognitive-os/metrics/hook-timing.jsonl',errors='ignore')
         if '\"subagent-budget-enforcer\"' in l)
print('n',len(d),'p50',d[len(d)//2],'p90',d[int(.9*len(d))],'p99',d[int(.99*len(d))],'max',d[-1])
print('wall-clock total s',round(sum(d)/1000,1))
"
# n 1718 p50 264 p90 412 p99 702 max 1260
# wall-clock total s 497.9
```

**264 ms de mediana en cada tool call**, 498 s acumulados en 12,5 h. Registrar el hook en
`PreToolUse` sin el bail lo duplicaría. Con el bail, el caso orquestador pasa de 264 ms a
un `case` de shell, y el total baja aun teniendo dos registros.

---

## 3. El diseño, confirmado y completado

Confirmo el núcleo del chip y agrego cuatro piezas (marcadas **NUEVO**).

| Pieza | Origen | Estado |
|---|---|---|
| `PostToolUse` = `count`, nunca sale 2 | chip | confirmado |
| `PreToolUse` = `enforce`, lee sin mutar, sale 2 | chip | confirmado |
| `BUDGET=N` ⇒ el subagente consume exactamente N | chip | confirmado, con test |
| Resolución de modo: env > `hook_event_name` > `COGNITIVE_OS_HOOK_EVENT` > `count` | chip | confirmado |
| Bail temprano en shell antes de cualquier `python3` | chip | confirmado como **filtro negativo** (§4.1) |
| **Identidad unificada: `agent_id` ⊕ basename del `transcript_path`** | **NUEVO** | §4.1 |
| **Escritura atómica del contador (temp + `mv`), sin lock** | **NUEVO** | §4.2 |
| **Fila `degraded` cuando enforce no puede leer el contador** | **NUEVO** | §4.3 |
| **Gracia de `ESCALATION:` acotada a un uso** | **NUEVO** | §4.5 |
| **Rollout en dry-run (`would_block`) antes de morder** | **NUEVO** | §6 |

### Por qué la identidad unificada no es un detalle

El contador se llama por `(session_id, agent_id)`. Si `PreToolUse` derivara un
`agent_id` distinto del que derivó `PostToolUse`, habría **dos contadores** y el enforce
leería siempre 0: un gate que jamás dispara, indistinguible de uno que funciona. Los
transcripts de subagente son `.../subagents/agent-<agent_id>.jsonl`, así que el id se
puede extraer del path. Verificado contra producción — el agente que fue bloqueado en la
llamada 53 durante esta sesión:

```bash
ls ~/.claude/projects/<proyecto>/93e6e34f-.../subagents/ | grep afbce854
# agent-afbce854e9979dd85.jsonl
grep afbce854 .cognitive-os/metrics/subagent-budget-enforcer.jsonl | tail -1
# {"action":"block","agent_id":"afbce854e9979dd85",...,"tool_calls":53}
```

`agent-afbce854e9979dd85.jsonl` ↔ `agent_id: afbce854e9979dd85`. Idénticos. Derivar del
basename cuando falta el campo hace que los dos eventos coincidan aunque uno de los dos
canales no traiga `agent_id`.

---

## 4. Las cuatro preguntas abiertas

### 4.1 ¿El bail temprano funciona? — Sí como filtro negativo, no como test

**Lo que está probado:** en `PostToolUse`, los payloads de subagente traen `agent_id`.
De los 165 agentes que pasaron por el hook, **165 tienen id de 17 hex** y **cero** tienen
la forma del fallback (`sha1(transcript)[:12]`, 12 hex):

```bash
python3 -c "
import json,re
ids={json.loads(l)['agent_id'] for l in open('.cognitive-os/metrics/subagent-budget-enforcer.jsonl') if l.strip()}
sha=[i for i in ids if re.fullmatch(r'[0-9a-f]{12}',i)]
print('ids',len(ids),'| forma sha1-fallback',len(sha))
"
# ids 165 | forma sha1-fallback 0
```

Y no vienen del entorno: `scripts/hook-timing-wrapper.sh:116` solo deriva
`COGNITIVE_OS_HOOK_AGENT_ID` para `SessionStart`/`SubagentStart`; en eventos de
herramienta lo exporta **vacío** (línea 151). Por descarte, el valor sale del payload.
El marcador `/subagents/` también es real: **111 transcripts** bajo esa ruta en este
proyecto (`find ~/.claude/projects/<proyecto> -path '*/subagents/agent-*.jsonl' | wc -l`).

**Lo que NO está probado, y es la premisa que sostiene todo:** que `PreToolUse` traiga
los mismos campos. No pude observar un payload de `PreToolUse` sin registrar un hook, y
`hooks/` está protegido. Ningún hook ya registrado en `PreToolUse` persiste `agent_id`
ni `transcript_path` (`grep -n 'agent_id\|transcript' hooks/{session-heartbeat,lethal-trifecta-gate,protected-config-write-guard,cross-session-event-emit}.sh` → sin resultados).

**Cómo lo resuelve el diseño, en vez de apostar:**

1. **Identidad redundante** — `agent_id` del payload, o el id extraído del basename del
   `transcript_path`. Si `PreToolUse` trae cualquiera de los dos, la clave coincide con
   la de `PostToolUse`.
2. **Fila `degraded`** — si enforce no logra identificar al agente, emite
   `action=degraded, reason=no_identity` y deja pasar. La primera hora de telemetría
   contesta la pregunta con datos en vez de con una suposición:
   ```bash
   grep -c '"reason": "no_identity"' .cognitive-os/metrics/subagent-budget-enforcer.jsonl
   ```
   Si ese número es alto, el canal `PreToolUse` no trae identidad y el enforce hay que
   revertirlo — sin haber roto nada mientras tanto.
3. **Dry-run primero** (§6): el enforce arranca registrando `would_block` sin salir 2.

**Sobre el bail en sí:** es correcto como *negativa barata* y no como test.

```bash
case "$INPUT" in
  *'"agent_id"'*|*'"subagent_id"'*|*'/subagents/'*) : ;;   # puede ser subagente -> seguir
  *) ...chequear env... ; exit 0 ;;                        # con certeza no lo es
esac
```

No tiene falsos negativos: si el payload es de subagente contiene alguno de los tres
marcadores. **Sí tiene falsos positivos** — cualquier payload que mencione el literal
`/subagents/` cae al camino caro. Esta misma auditoría lo provocó varias veces al
grepear esa ruta. No importa: un falso positivo cuesta exactamente lo que cuesta hoy
(el evaluador Python sigue siendo la autoridad y descarta), y el caso común —
orquestador escribiendo código — queda en **0 spawns**. El ahorro del chip se sostiene;
lo que no se sostiene es tratar al bail como decisión.

### 4.2 ¿Estado compartido? — No hace falta lock. La carrera no se reproduce

Primero, el alcance real: el contador es **por `(session_id, agent_id)`**, no global. Seis
sesiones concurrentes escriben seis archivos distintos. La única carrera posible es entre
llamadas **del mismo agente**, que sí pueden ir en paralelo (los harnesses ejecutan tool
calls independientes concurrentemente — este informe se armó batcheando llamadas).

Intenté reproducir la pérdida de incrementos con 12, 30 y 60 procesos simultáneos sobre
el mismo contador:

```bash
# read-only sobre un PROJECT_DIR temporal; no toca el repo
WT=$(mktemp -d)
python3 - <<'EOF'
import json,os,subprocess,pathlib
wt=pathlib.Path(os.environ['WT'])
payload=json.dumps({"hook_event_name":"PostToolUse","session_id":"s","agent_id":"aRACE",
                    "tool_name":"Bash","tool_input":{"command":"echo"}})
env={**os.environ,"COGNITIVE_OS_PROJECT_DIR":str(wt),"COGNITIVE_OS_SESSION_ID":"s",
     "COS_SUBAGENT_TOOL_CALL_BUDGET":"999","COGNITIVE_OS_HOOK_AGENT_ID":"","COGNITIVE_OS_SESSION_KIND":""}
for n in (12,30,60):
    for f in wt.glob(".cognitive-os/sessions/s/*"): f.unlink()
    ps=[subprocess.Popen(["bash","hooks/subagent-budget-enforcer.sh"],stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True,env=env) for _ in range(n)]
    for p in ps: p.communicate(payload)
    c=wt/".cognitive-os/sessions/s/subagent-tool-calls-aRACE"
    got=int(c.read_text().strip()) if c.exists() else 0
    print(f"lanzados={n} contador={got} perdidos={n-got}")
EOF
rm -rf "$WT"
# lanzados=12 contador=12 perdidos=0
# lanzados=30 contador=30 perdidos=0
# lanzados=60 contador=60 perdidos=0
```

**Cero pérdidas.** La explicación es que los 264 ms de arranque de `python3` empequeñecen
la sección crítica (`cat` + `printf`, microsegundos) y desincronizan a los escritores.

**Decisión: no se agrega lock.** Contrastando con lo que el repo ya tiene —
`hooks/_lib/safe-jsonl.sh:50` implementa `safe_jsonl_append` con lock por `mkdir`, spin
con `sleep 0.1` y recuperación de lock stale a los 30 s — meterlo en un hook que ya está
en 264 ms p50 costaría más que el defecto que evita. Es exactamente el caso donde el
remedio es peor.

**Lo que sí se agrega, porque cuesta una línea:** la escritura de hoy
(`printf '%s' "$COUNT" > "$COUNTER_FILE"`) **trunca y después escribe**. Mientras no
hubo lectores concurrentes eso fue inofensivo; el `PreToolUse` introduce uno. Un lector
puede ver el archivo vacío, o `5` en medio de la escritura de `53` — y en ese caso el
enforce dejaría pasar. Se elimina por construcción con temp + `mv` en el mismo
directorio (rename atómico): el lector ve el valor viejo o el nuevo, nunca uno partido.
No es una defensa probabilística, es cerrar el caso.

*(Si alguna vez se abarata el hook —caché del intérprete, reescritura en Go— la carrera
de incrementos vuelve a ser posible. Por eso el test de 12 procesos queda como guarda de
regresión y no como xfail.)*

### 4.3 ¿Fail-open o fail-closed cuando no existe el contador? — **Fail-open, y el motivo escrito**

**Decisión: enforce deja pasar cuando no hay contador.**

El repo tiene la norma «un gate que falla abierto no es un gate», y acá no se la está
violando, porque **la ausencia del contador no es una falla: es el estado legítimo de la
primera llamada de todo subagente**. Fail-closed sobre ausencia bloquearía al 100 % de
los agentes en su tool call nº 1 — el gate se apagaría el mismo día, que es el peor
desenlace posible para una norma de seguridad.

La obligación de fail-closed no desaparece: **se muda al lado que puede fallar de
verdad.**

1. **La autoridad de conteo es `count` (Post).** Si esa escritura falla en silencio, el
   enforce lee 0 para siempre y el gate desaparece sin que nadie se entere. Por eso
   `count` pasa a emitir `action=degraded, reason=counter_write_failed` + aviso por
   stderr cuando no puede escribir. Hoy esa falla es literalmente invisible: la línea 119
   termina en `|| true`.
2. **Enforce deja pasar, pero nunca callado.** Contador ilegible, sin identidad o sin
   `python3` ⇒ `action=degraded` con el motivo. La pérdida de cobertura se vuelve
   contable:
   ```bash
   grep -c '"action": "degraded"' .cognitive-os/metrics/subagent-budget-enforcer.jsonl
   ```
   Cero es el estado sano; distinto de cero es un hallazgo, no un ruido.
3. **Donde sí se falla cerrado:** `COS_ALLOW_SUBAGENT_BUDGET_BYPASS=1` sin
   `COS_SUBAGENT_BUDGET_BYPASS_REASON` sale 2. Ya está en el código (línea 176), pero hoy
   vive en `PostToolUse`, donde salir 2 no cancela nada. Al mudarse a enforce **recién ahí
   empieza a valer**.

Resumen de la regla: *fail-open sobre la ausencia, fail-loud sobre la falla,
fail-closed sobre el bypass mal declarado.*

### 4.4 ¿Sigue siendo 50 el número correcto? — La distribución de hoy no puede contestarlo

Medición sobre los 49 contadores reales que quedaron en disco:

```bash
python3 -c "
import pathlib,statistics
v=sorted(int(p.read_text().strip()) for p in pathlib.Path('.cognitive-os/sessions').glob('*/subagent-tool-calls-*') if p.read_text().strip().isdigit())
print('n',len(v),'min',v[0],'mediana',statistics.median(v),'media',round(statistics.mean(v),1),'max',v[-1])
for q in (.75,.9,.95): print(f'p{int(q*100)}',v[int(q*(len(v)-1))])
print('superan 50:',sum(1 for x in v if x>50),'/',len(v))
print('buckets',{b:sum(1 for x in v if b<=x<b+10) for b in range(0,100,10)})
"
```

| métrica | valor |
|---|---|
| n | 49 subagentes |
| mín / mediana / media / máx | 4 / 48 / 42,0 / **96** |
| p75 / p90 / p95 | 52 / 53 / 56 |
| superan el presupuesto (>50) | **23 / 49 = 46,9 %** |
| distribución por decena | 0-9: 2 · 10-19: 4 · 20-29: 3 · 30-39: **12** · 40-49: 5 · 50-59: **22** · 90-99: 1 |

Los 49 valores crudos:

```
4, 9, 14, 14, 16, 16, 23, 29, 29, 31, 32, 33, 35, 35, 35, 36, 36, 38, 38, 39, 39, 42,
43, 44, 48, 48, 51, 51, 51, 51, 51, 51, 52, 52, 52, 52, 52, 52, 52, 52, 52, 52, 53, 53,
53, 56, 56, 57, 96
```

**Lo que dice esta distribución no es lo que parece.** Está *truncada por el propio
mecanismo*: la montaña en 51–53 (20 de 49 agentes) no es demanda, es la firma de agentes
que chocaron el bloqueo y reintentaron una a tres veces antes de rendirse. Cada uno de
esos reintentos **corrió** (es `PostToolUse`) y **gastó presupuesto**. La distribución
mide dónde los agentes se dan por vencidos, no cuántas llamadas necesitaban.

Y la cola larga confirma que la demanda real es mayor: un agente llegó a **96** llamadas
usando el pase por `ESCALATION:` **43 veces** (§4.5).

**Recomendación, contra la tentación de mover el número ahora:**

1. **No tocar el 50 al aplicar el parche.** Cambiar el mecanismo y el umbral en el mismo
   movimiento hace imposible atribuir el efecto.
2. **Una semana de enforce en dry-run** (§6). Ahí la distribución deja de estar truncada:
   los agentes ya no gastan llamadas en reintentos bloqueados y el `would_block` registra
   cuánto habrían pedido.
3. **Recién entonces fijar el número en el p90 de esa distribución limpia**, con el
   comando que lo produjo escrito en el ADR.

Mi expectativa —explícitamente una hipótesis, no una medición— es que va a caer entre 60
y 70, porque hoy el 47 % de la flota lo choca y el trabajo igual se termina. Pero el
orden importa: **primero cerrar el agujero de `ESCALATION:`, después elegir el número.**
Con el agujero abierto, cualquier presupuesto es decorativo.

### 4.5 El agujero que el chip no vio: `ESCALATION:` es un bypass permanente

El hook (líneas 68-69) hace `"ESCALATION:" in blob` sobre **el JSON entero del payload**,
y si aparece sale 0 **antes** de evaluar el presupuesto. Es decir: cualquier tool call
que mencione ese literal en cualquier lado —un `grep`, un archivo que se está escribiendo,
este mismo informe— pasa gratis. No es teoría:

```bash
python3 -c "
import json,collections
rows=[json.loads(l) for l in open('.cognitive-os/metrics/subagent-budget-enforcer.jsonl') if l.strip()]
esc=collections.Counter((r['session_id'][:8],r['agent_id']) for r in rows if r['reason']=='escalation_declared')
print('agentes con pase:',len(esc),'| filas:',sum(esc.values()),'| top:',esc.most_common(2))
"
# agentes con pase: 9 | filas: 53 | top: [(('93e6e34f','a632278962fd85ae2'), 43), ...]
```

**Un agente usó el pase 43 veces.** Hoy eso es casi inocuo, porque el bloqueo tampoco
bloquea. **Mudarlo a `PreToolUse` tal cual lo especifica el chip convierte un contador
con fuga en un gate que se abre con una cadena de texto** — y un agente que aprende que
mencionar `ESCALATION:` lo desbloquea nunca se detiene.

Por eso el diseño acota la gracia: **un solo uso por agente**, marcado en
`$RUNTIME_DIR/subagent-escalation-$AGENT_ID`, registrado como
`action=allow, reason=escalation_grace`. El segundo intento bloquea con un mensaje
distinto. La escalación sigue siendo una salida —que es su propósito— pero deja de ser
una puerta.

---

## 5. Parches exactos

Cuatro archivos. **Ninguno aplicado**: `hooks/` y `.claude/settings.json` están detrás de
`protected-config-write-guard`, que exige `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` con
revisión humana (§7).

### 5.1 `hooks/subagent-budget-enforcer.sh`

```diff
--- a/hooks/subagent-budget-enforcer.sh
+++ b/hooks/subagent-budget-enforcer.sh
@@ -2,10 +2,17 @@
 # SCOPE: both
 # subagent-budget-enforcer.sh — ADR-311
 #
-# PostToolUse hook. Counts tool calls for subagent sessions and forces a
-# structured escalation once a subagent exceeds its per-agent tool-call budget.
-# This turns the preamble's "50 tool calls" instruction into runtime evidence.
+# Dual-mode hook over a single script.
+#
+#   count   (PostToolUse) — increments the per-(session, agent) counter and
+#                           writes telemetry. NEVER exits 2: a PostToolUse
+#                           block runs after the tool already executed, so it
+#                           only discards the result.
+#   enforce (PreToolUse)  — READS the counter without mutating it and blocks
+#                           the call that would exceed the budget. Here exit 2
+#                           actually cancels the call.
+#
+# Mode: COS_SUBAGENT_BUDGET_MODE > payload hook_event_name >
+#       COGNITIVE_OS_HOOK_EVENT > count (counting is the safe default).
 #
 # Killswitch: DISABLE_HOOK_SUBAGENT_BUDGET_ENFORCER=1
 # Bypass: COS_ALLOW_SUBAGENT_BUDGET_BYPASS=1 + COS_SUBAGENT_BUDGET_BYPASS_REASON
@@ -19,9 +26,44 @@
 PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}}"
 HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
 COS_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
 INPUT="$(cat)"
 
+# ── Cheap negative filter (pure shell, zero subprocesses) ────────────────────
+# A subagent payload always carries one of these markers. If none is present
+# and no env marker is set, this is certainly not a subagent: leave before
+# paying for python3. False positives (a payload that merely mentions the
+# literal "/subagents/") fall through to the precise check below and cost
+# exactly what they cost today.
+case "$INPUT" in
+  *'"agent_id"'*|*'"subagent_id"'*|*'/subagents/'*) : ;;
+  *)
+    if [ -z "${COGNITIVE_OS_HOOK_AGENT_ID:-}${COGNITIVE_OS_AGENT_ID:-}${CLAUDE_AGENT_ID:-}${CODEX_AGENT_ID:-}${COS_AGENT_ID:-}" ] &&
+       [ "${COGNITIVE_OS_SESSION_KIND:-}" != "subagent" ] &&
+       [ "${COS_SESSION_KIND:-}" != "subagent" ]; then
+      exit 0
+    fi
+    ;;
+esac
+
+# ── Mode resolution (also pure shell) ───────────────────────────────────────
+MODE="${COS_SUBAGENT_BUDGET_MODE:-}"
+if [ -z "$MODE" ]; then
+  case "$INPUT" in
+    *'"hook_event_name":"PreToolUse"'*|*'"hook_event_name": "PreToolUse"'*)   MODE="enforce" ;;
+    *'"hook_event_name":"PostToolUse"'*|*'"hook_event_name": "PostToolUse"'*) MODE="count" ;;
+    *)
+      case "${COGNITIVE_OS_HOOK_EVENT:-}" in
+        PreToolUse) MODE="enforce" ;;
+        *)          MODE="count" ;;
+      esac
+      ;;
+  esac
+fi
+case "$MODE" in count|enforce) ;; *) MODE="count" ;; esac
+
+# Dry-run: enforce evaluates and records `would_block`, but never exits 2.
+# Default 1 (dry-run) for the first rollout week; flip to 0 to make it bite.
+ENFORCE_DRY_RUN="${COS_SUBAGENT_BUDGET_DRY_RUN:-1}"
+
 command -v python3 >/dev/null 2>&1 || exit 0
 
 EVAL_JSON="$(PROJECT_DIR="$PROJECT_DIR" INPUT_JSON="$INPUT" python3 - <<'PYEOF' 2>/dev/null || true
@@ -63,8 +105,17 @@
     (payload.get("tool_input") or {}).get("agent_id") if isinstance(payload.get("tool_input"), dict) else "",
 )
 transcript = first(payload.get("transcript_path"), payload.get("transcript"))
-is_subagent = session_kind == "subagent" or bool(agent_id) or "/subagents/" in transcript
+
+# Subagent transcripts are `.../subagents/agent-<agent_id>.jsonl`. Deriving the
+# id from the basename makes PreToolUse and PostToolUse agree on ONE counter
+# even if only one of the two channels carries the agent_id field. Two keys
+# would mean enforce always reads 0 — a gate indistinguishable from a working
+# one. Verified: transcript agent-afbce854e9979dd85.jsonl <-> ledger
+# agent_id afbce854e9979dd85.
+match = re.search(r"/subagents/agent-([A-Za-z0-9_.-]+)\.jsonl", transcript)
+agent_from_transcript = match.group(1) if match else ""
+agent_id = agent_id or agent_from_transcript
+is_subagent = session_kind == "subagent" or bool(agent_id) or "/subagents/" in transcript
 
 blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
 escalation_declared = "ESCALATION:" in blob
@@ -106,18 +157,38 @@
 RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID"
 METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
 mkdir -p "$RUNTIME_DIR" "$METRICS_DIR" 2>/dev/null || true
 COUNTER_FILE="$RUNTIME_DIR/subagent-tool-calls-$AGENT_ID"
+ESCALATION_FILE="$RUNTIME_DIR/subagent-escalation-$AGENT_ID"
 METRICS_FILE="$METRICS_DIR/subagent-budget-enforcer.jsonl"
 RESOURCE_LEDGER="$METRICS_DIR/ai-resource-ledger.jsonl"
 
-COUNT=0
-if [ -f "$COUNTER_FILE" ]; then
-  COUNT="$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)"
-  case "$COUNT" in ''|*[!0-9]*) COUNT=0 ;; esac
-fi
-COUNT=$((COUNT + 1))
-printf '%s' "$COUNT" > "$COUNTER_FILE" 2>/dev/null || true
+COUNT=0
+COUNTER_DEGRADED=""
+if [ -f "$COUNTER_FILE" ]; then
+  RAW="$(cat "$COUNTER_FILE" 2>/dev/null || echo '')"
+  case "$RAW" in
+    ''|*[!0-9]*) COUNT=0; COUNTER_DEGRADED="counter_unreadable" ;;
+    *)           COUNT="$RAW" ;;
+  esac
+fi
```

```diff
@@ (continúa: el bloque de decisión, reemplaza las líneas 113-119 y 166-196)
+# ── count mode: the counting authority. Never exits 2. ──────────────────────
+if [ "$MODE" = "count" ]; then
+  COUNT=$((COUNT + 1))
+  # Atomic replace: truncate-then-write lets the PreToolUse reader observe an
+  # empty or partial value ("5" mid-write of "53"), which would silently let a
+  # call through. temp + mv in the same directory closes that by construction.
+  if ! { printf '%s' "$COUNT" > "$COUNTER_FILE.tmp.$$" 2>/dev/null &&
+         mv -f "$COUNTER_FILE.tmp.$$" "$COUNTER_FILE" 2>/dev/null; }; then
+    rm -f "$COUNTER_FILE.tmp.$$" 2>/dev/null || true
+    # A silent write failure makes enforce read 0 forever: the gate would
+    # disappear without a trace. Make it countable.
+    emit_metric "degraded" "counter_write_failed"
+    printf 'subagent-budget-enforcer: DEGRADED — cannot persist the tool-call counter for `%s`; budget enforcement is off for this agent.\n' "$AGENT_ID" >&2
+    exit 0
+  fi
+
+  if [ "$COUNT" -ge "$WARN_AT" ]; then
+    emit_metric "warn" "budget_reached"
+    printf 'subagent-budget-enforcer: WARN — subagent `%s` reached %s/%s tool calls. The next tool call will be blocked before it runs; emit `ESCALATION:` with diagnosis, progress, files touched, and next safe action.\n' "$AGENT_ID" "$COUNT" "$BUDGET" >&2
+    exit 0
+  fi
+
+  if [ "$((COUNT % 10))" -eq 0 ]; then
+    emit_metric "observe" "periodic"
+  fi
+  exit 0
+fi
+
+# ── enforce mode: reads, never mutates the counter. exit 2 cancels. ─────────
+if [ -n "$COUNTER_DEGRADED" ]; then
+  # Fail-open on a broken read (count mode self-heals on the next call), but
+  # never silently: a lost gate has to be countable.
+  emit_metric "degraded" "$COUNTER_DEGRADED"
+  exit 0
+fi
+
+if [ "${COS_ALLOW_SUBAGENT_BUDGET_BYPASS:-0}" = "1" ]; then
+  reason="${COS_SUBAGENT_BUDGET_BYPASS_REASON:-}"
+  if [ -z "$reason" ]; then
+    printf 'subagent-budget-enforcer: COS_ALLOW_SUBAGENT_BUDGET_BYPASS=1 requires COS_SUBAGENT_BUDGET_BYPASS_REASON=<text>\n' >&2
+    emit_metric "block" "missing_bypass_reason"
+    exit 2
+  fi
+  emit_metric "allow" "bypass:$reason"
+  exit 0
+fi
+
+if [ "$COUNT" -lt "$BUDGET" ]; then
+  exit 0
+fi
+
+# Over budget. `ESCALATION:` buys ONE extra call, not a standing pass: the
+# check is a substring match over the whole payload, and in production one
+# agent rode it 43 times up to 96 tool calls.
+if [ "$ESCALATION_DECLARED" = "1" ] && [ ! -f "$ESCALATION_FILE" ]; then
+  printf '%s' "$COUNT" > "$ESCALATION_FILE" 2>/dev/null || true
+  emit_metric "allow" "escalation_grace"
+  exit 0
+fi
+
+if [ "$ENFORCE_DRY_RUN" = "1" ]; then
+  emit_metric "would_block" "budget_exceeded_dry_run"
+  printf 'subagent-budget-enforcer: WOULD BLOCK (dry-run) — subagent `%s` is at %s/%s tool calls.\n' "$AGENT_ID" "$COUNT" "$BUDGET" >&2
+  exit 0
+fi
+
+emit_metric "block" "budget_exceeded"
+printf 'subagent-budget-enforcer: BLOCK — subagent `%s` is at %s tool calls, budget %s. This call did NOT run. Emit `ESCALATION:` with diagnosis, progress, files touched, and next safe action. Override only with COS_ALLOW_SUBAGENT_BUDGET_BYPASS=1 and COS_SUBAGENT_BUDGET_BYPASS_REASON=<text>.\n' "$AGENT_ID" "$COUNT" "$BUDGET" >&2
+exit 2
```

Notas de aplicación:

- `emit_metric` no cambia de cuerpo, pero pasa a recibir `would_block` y `degraded` como
  valores de `action`. `cos_lib.taximeter.resource_tick` los recibe como
  `kind=subagent_budget_would_block` / `..._degraded`; no hay enum que romper.
- El bloque `if [ "$ESCALATION_DECLARED" = "1" ]` original (líneas 166-169) **se elimina**:
  en `count` no debe existir (contar siempre) y en `enforce` queda subsumido por la
  gracia acotada.
- `re` ya está importado en el evaluador Python (línea 30).

### 5.2 `cognitive-os.yaml` — segunda entrada, mismo script

Precedente idiomático ya presente: 7 scripts están registrados bajo dos o más nombres
(`session-heartbeat-pre`, `native-agent-heartbeat-pre` / `-post`,
`cross-session-event-emit` ×4). Verificable con:

```bash
python3 -c "
import yaml,collections
h=yaml.safe_load(open('cognitive-os.yaml'))['harness']['hooks']
c=collections.Counter(v.get('script') for v in h.values() if isinstance(v,dict))
print('scripts con más de un nombre:',sum(1 for k,n in c.items() if n>1))
"
# scripts con más de un nombre: 7
```

Insertar en el bloque `PreToolUse` de matcher `""`, después de
`lethal-trifecta-gate` (línea 1095-1099):

```diff
--- a/cognitive-os.yaml
+++ b/cognitive-os.yaml
@@ -1099,6 +1099,25 @@
     lethal-trifecta-gate:
       script: hooks/lethal-trifecta-gate.sh
       event: PreToolUse
       matcher: ""
       scope: os-only
 
+    subagent-budget-enforcer-pre:
+      script: hooks/subagent-budget-enforcer.sh
+      event: PreToolUse
+      matcher: ""
+      async: false
+      scope: both
+      default_projection: true
+      codex_projection: gap
+      codex_gap_reason: >
+        Same gap as the PostToolUse registration: Codex only emits tool events
+        for Bash and exposes no subagent lifecycle, so the enforce mode has
+        nothing to read there.
+      notes: >
+        ADR-311 mode split. This registration runs the script in `enforce`
+        mode (resolved from the payload's hook_event_name): it READS the
+        per-agent counter and blocks the call that would exceed the budget
+        BEFORE it runs. The PostToolUse registration below stays as the
+        counting authority and must never exit 2 — a PostToolUse block only
+        discards a result that the tool already produced.
+
```

Y en la entrada existente (línea 1445), aclarar el rol:

```diff
@@ -1445,6 +1464,10 @@
     subagent-budget-enforcer:
       script: hooks/subagent-budget-enforcer.sh
       event: PostToolUse
       matcher: ""
       async: false
       scope: both
       default_projection: true
+      notes: >
+        ADR-311 `count` mode: the counting authority. Never exits 2.
+        Enforcement lives in `subagent-budget-enforcer-pre` (PreToolUse).
       codex_projection: gap
```

### 5.3 `scripts/_lib/settings-driver-claude-code.sh` — el que realmente emite

**Sin este parche, el 5.2 no cambia nada en Claude Code** (§2.3). En el grupo `pre_all`
(línea 197):

```diff
--- a/scripts/_lib/settings-driver-claude-code.sh
+++ b/scripts/_lib/settings-driver-claude-code.sh
@@ -197,6 +197,7 @@
   pre_all=$(_cc_hook_group "PreToolUse" "" \
     "hooks/protected-config-write-guard.sh" "false" \
     "hooks/cosd-auth-guard.sh" "false" \
     "hooks/agent-control-inbound-guard.sh" "false" \
     "hooks/session-heartbeat.sh"    "false" \
     "hooks/lethal-trifecta-gate.sh" "false" \
+    "hooks/subagent-budget-enforcer.sh" "false" \
   )
```

Después, regenerar y verificar (esto sí escribe `.claude/settings.json`, así que va con
la revisión humana del guard):

```bash
bash scripts/_lib/settings-driver-claude-code.sh --check   # DRIFT esperado antes de regenerar
bash scripts/_lib/settings-driver-claude-code.sh           # escritura atómica
bash scripts/_lib/settings-driver-claude-code.sh --check   # OK: in sync
```

**Orden obligatorio del despliegue:** `hooks/` primero, registro después. Al revés, el
script viejo —que sale 2 al pasar el presupuesto sin importar el evento— se registra en
`PreToolUse` y bloquea a media flota de entrada.

### 5.4 `tests/contracts/test_subagent_budget_enforcer.py` — el que codifica el contrato roto

Ese archivo invoca el hook sin evento y espera `exit 2` en la tercera llamada
(líneas 44-69). Con el parche, sin evento el modo es `count` y `count` nunca sale 2:
**el test pasa a fallar, y hace bien.** Es el contrato viejo.

Reemplazo: renombrar el caso y fijar el modo explícitamente, dejando el resto del archivo
intacto.

```diff
--- a/tests/contracts/test_subagent_budget_enforcer.py
+++ b/tests/contracts/test_subagent_budget_enforcer.py
-def test_subagent_budget_blocks_after_configured_budget(tmp_path: Path) -> None:
-    payload = {"tool_name": "Bash", "tool_input": {"command": "echo ok"}}
-
-    first = _run_hook(tmp_path, payload)
-    second = _run_hook(tmp_path, payload)
-    third = _run_hook(tmp_path, payload)
-
-    assert first.returncode == 0, first.stderr
-    assert second.returncode == 0, second.stderr
-    assert "WARN" in second.stderr
-    assert third.returncode == 2
-    assert "BLOCK" in third.stderr
-    assert "ESCALATION:" in third.stderr
+def test_subagent_budget_blocks_after_configured_budget(tmp_path: Path) -> None:
+    """Blocking is an enforce-mode (PreToolUse) behaviour.
+
+    The pre-ADR-311 version of this test drove the hook with no event at all
+    and expected exit 2 on the third call. That encoded the defect: the hook
+    ran on PostToolUse, so its exit 2 arrived after the tool had already run.
+    """
+    payload = {"tool_name": "Bash", "tool_input": {"command": "echo ok"}}
+    enforce = {"COS_SUBAGENT_BUDGET_MODE": "enforce", "COS_SUBAGENT_BUDGET_DRY_RUN": "0"}
+
+    first = _run_hook(tmp_path, payload)          # count -> 1
+    second = _run_hook(tmp_path, payload)         # count -> 2 (== budget)
+    third = _run_hook(tmp_path, payload, enforce)  # enforce reads 2 -> blocks
+
+    assert first.returncode == 0, first.stderr
+    assert second.returncode == 0, second.stderr
+    assert "WARN" in second.stderr
+    assert third.returncode == 2
+    assert "BLOCK" in third.stderr
+    assert "ESCALATION:" in third.stderr
```

Los otros dos casos del archivo (`..._allows_structured_escalation_after_budget`,
`..._ignores_orchestrator_sessions`) siguen valiendo sin cambios; el primero pasa a
ejercitar la gracia de un solo uso.

También hay que revisar `tests/contracts/test_primitive_closure_ratchet.py:135`
(`assert "hooks/subagent-budget-enforcer.sh" in settings.read_text()`): sigue en verde
con dos registros, pero conviene endurecerlo a contar **dos** apariciones, una por
evento — si no, un futuro borrado del `PreToolUse` pasa desapercibido.

---

## 6. Rollout: el enforce no muerde el primer día

`COS_SUBAGENT_BUDGET_DRY_RUN` arranca en `1` en el parche, a propósito.

| Fase | Estado | Qué se mide | Criterio para avanzar |
|---|---|---|---|
| 0 | Parche del hook, sin registrar en Pre | nada cambia | tests en verde |
| 1 | Registrado en Pre, `DRY_RUN=1` | `would_block` + `degraded` | **`reason=no_identity` en 0** durante una semana → §4.1 contestada con datos |
| 2 | `DRY_RUN=0`, presupuesto sin tocar en 50 | `block` real, sin cola en 51-53 | ningún agente supera 50 en los contadores |
| 3 | Elegir el número desde la distribución limpia | p90 de fase 1 | ADR-311 actualizado con el comando |

Comandos de la fase 1:

```bash
# ¿La identidad llega en PreToolUse? Si esto no es 0, revertir el registro.
grep -c '"reason": "no_identity"' .cognitive-os/metrics/subagent-budget-enforcer.jsonl

# Demanda real, ya sin truncar
python3 -c "
import json,collections
mx=collections.defaultdict(int)
for l in open('.cognitive-os/metrics/subagent-budget-enforcer.jsonl'):
    r=json.loads(l); mx[(r['session_id'],r['agent_id'])]=max(mx[(r['session_id'],r['agent_id'])],r['tool_calls'])
v=sorted(mx.values()); print('p50',v[len(v)//2],'p90',v[int(.9*len(v))],'max',v[-1])
"
```

Kill-switch inmediato si algo sale mal, sin desregistrar nada:
`DISABLE_HOOK_SUBAGENT_BUDGET_ENFORCER=1` (línea 15) o `COS_SUBAGENT_BUDGET_MODE=count`.

---

## 7. Guards encontrados y respetados

- `hooks/` y `.claude/settings.json` están cubiertos por `protected-config-write-guard`
  (`PreToolUse`, matcher `""`, primero del grupo `pre_all`). Exige
  `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` con revisión humana, y el env var no se puede
  inyectar desde la línea de comandos de un agente: el hook corre en su propio proceso
  antes del comando. **No intenté escribir esas rutas.** Los parches van como diff.
- **No toqué** ninguno de los archivos reservados a otros agentes (los cuatro gates
  `exit-1-not-2`, `bash-hot-path-dispatcher.sh`, los tres censos, `error-pipeline.sh`,
  `error-learning.sh`, el harness opencode) ni `.cognitive-os/metrics/*.jsonl` — todo el
  uso de métricas fue de lectura, y la prueba de concurrencia corrió sobre un
  `PROJECT_DIR` temporal que se borró.
- `scripts/_lib/settings-driver-claude-code.sh` **no** está protegido, pero como el
  parche solo tiene efecto junto con el del hook, va también como diff: aplicarlo suelto
  registraría en `PreToolUse` el script viejo, que bloquea de verdad.

## 8. Deuda documental que deja este trabajo

Dos afirmaciones del repo quedaron refutadas y no se arreglan solas:

1. **`scripts/_lib/settings-driver-claude-code.sh:3,6`** dice que el registro canónico
   vive en `cognitive-os.yaml > harness.hooks` (ADR-064). El driver no lee el YAML;
   emite literales. Cualquier lector que confíe en el encabezado va a parchear el archivo
   equivocado — a mí me pasó al preparar el parche. Corresponde: o el driver pasa a leer
   el YAML de verdad, o el encabezado dice que los literales son la fuente y el YAML es
   la declaración para censos y otros harnesses.
2. **`hooks/subagent-budget-enforcer.sh:5`** se autodescribe como «PostToolUse hook» que
   «fuerza una escalación estructurada». No fuerza nada: 95 bloqueos, 0 llamadas
   prevenidas. El parche de §5.1 corrige el encabezado.

## 9. Este informe también fue contado

El hook contó cada tool call de esta auditoría. Con la firma de siempre: el conteo
avanza en `PostToolUse`, así que si me hubiera bloqueado, el comando ya habría corrido.
Es, en pequeño, el defecto que el informe describe — el instrumento que audita al gate
es contado por el gate que audita, y ninguno de los dos puede detener al otro a tiempo.
