# El conteo que encabeza el brief

Fecha: 2026-08-21 · HEAD del encargo: `7a3f1758a` (main) · autor: sub-agente ejecutor

El proyector de arranque (ADR-275) abría el brief con
`control-plane findings: 119034`. No son 119.034 hallazgos: es el número de
FILAS de un log append-only de propuestas, publicado bajo una etiqueta que
promete hallazgos abiertos. Este informe deja la cadena medida, la cifra
correcta, el barrido de los otros conteos del mismo brief, y el gate que impide
que un conteo vuelva a alejarse un orden de magnitud de lo que su etiqueta dice.

## Correcciones a las premisas del encargo

1. **`open_findings` no es un conteo legítimo, pero la premisa "es un conteo de
   filas de un jsonl acumulativo" se queda corta en el porqué.** No es sólo que
   cuente filas: el filtro que el proyector aplicaba
   (`status not in {resolved, closed}`) es **vacío por construcción**. El 100 %
   de las filas del log tiene `status: "queued"` y `event: "proposed"` — el
   escritor nunca escribe cierre en ese archivo. O sea que el filtro "abiertos"
   no descartaba nada; era decorativo.

2. **`pending_truth` no dice 74 hallazgos pendientes: dice 74 ítems, de los
   cuales 70 están pendientes y 4 ya están hechos.** El desglose se mostraba,
   así que la mentira era chica, pero el número que encabezaba la línea incluía
   los cerrados.

3. **`operational_guide` no "dice P0=0 / P1=0" porque no haya backfill: lo dice
   porque el campo `priority` no existe en el reporte fuente.** Los 287
   resultados tienen `priority: None`. Ese cero medía la ausencia del campo, no
   la ausencia de trabajo. Es el falso cero clásico y era el segundo conteo sin
   sentido del brief, tal como sospechaba el punto 4 del encargo.

4. **`staged_deployments: 4` es correcto como conteo de directorios y falso como
   "cosas por desplegar".** Cuenta directorios cuyo NOMBRE contiene `staging`.
   Al menos dos de los cuatro ya están desplegados (ver §4).

5. **El repo se movió durante la corrida.** A las `11:42:48Z` corrió el carril
   `hourly` del audit y cambió el estado en vivo: el log pasó de 119.034 a
   120.503 filas y los hallazgos activos de 0 a 1460. Todo número de este
   informe lleva su marca temporal; los del encargo eran de antes de esa corrida.

6. **No pude tocar `skills/session-pending-brief/SKILL.md`**: está protegido por
   `hooks/protected-config-write-guard.sh` y el encargo prohíbe el bypass. Queda
   como acción de operador con el parche exacto en §7.

## 1. Qué cuenta `open_findings` de verdad

Cadena de origen, leída en la fuente:

```bash
grep -n "control_plane\|control-plane" scripts/cos-session-start-projector
# 194:    entries = _load_jsonl(root / ".cognitive-os/tasks/control-plane-remediation.jsonl")
# 196:    open_findings = [e for e in entries if e.get("status") not in {"resolved", "closed"}]
# 202:        "open_findings": len(open_findings),
```

El archivo, medido:

```bash
ls -la .cognitive-os/tasks/control-plane-remediation.jsonl
# 57201452 bytes (57 MB), Aug 20 20:00
wc -l .cognitive-os/tasks/control-plane-remediation.jsonl
# 119034     (11:30Z; a las 11:42:48Z ya eran 120503)
```

Qué representa cada fila, y cuál es la ventana:

```bash
.venv/bin/python3 - <<'PY'
import json, collections
p=".cognitive-os/tasks/control-plane-remediation.jsonl"
ev=collections.Counter(); st=collections.Counter(); ids=set(); dates=[]
for line in open(p):
    e=json.loads(line); ev[e.get("event")]+=1; st[e.get("status")]+=1
    ids.add(e.get("stable_id")); dates.append(e.get("created_at"))
print(len(dates), dict(ev), dict(st), len(ids), min(dates), max(dates))
PY
# 119034 {'proposed': 119034} {'queued': 119034} 5136
#        2026-05-14T16:11:33Z 2026-08-20T23:00:05Z
```

Lectura:

- **Cada fila es un EVENTO de propuesta**, no un hallazgo. Las 119.034 filas son
  el mismo conjunto de hallazgos re-propuesto una y otra vez.
- **Ventana: 98 días** (2026-05-14 → 2026-08-20). No es "el estado de hoy": es
  la historia entera desde que el log existe.
- **Hallazgos distintos: 5.136** (`stable_id`). Factor de inflación 23,2×.
- **Cero eventos de cierre.** `event` es siempre `proposed`, `status` siempre
  `queued`. El filtro de "abiertos" del proyector no podía descartar nada.

**Escritor.** Dos, y sólo uno infla:

```bash
grep -rln "control-plane-remediation" scripts/ hooks/ cos_lib/ lib/ tests/
# scripts/cos-control-plane-audit        <- escribe eventos 'proposed'  (ADR-248)
# cos_lib/telemetry_aggregator.py        <- append idempotente por stable_id (ADR-304)
```

`cos_lib/telemetry_aggregator.py:636` (`append_findings_idempotent`) se saltea
lo que ya está. `scripts/cos-control-plane-audit:284` appendea sin deduplicar:
depende de una máquina de estados aparte para saber qué es nuevo.

**Dónde vive de verdad el abierto/cerrado:**
`.cognitive-os/runtime/control-plane-audit/findings-state.json`, escrito por
`scripts/cos-control-plane-audit:275-284`, con `status: active|resolved` por
`stable_id`. El log de la cola no es una cola: es un diario.

## 2. La cifra correcta de hallazgos abiertos

```bash
.venv/bin/python3 -c "
import json,collections
d=json.load(open('.cognitive-os/runtime/control-plane-audit/findings-state.json'))
f=d['findings']
print(d['updated_at'], len(f), collections.Counter(v['status'] for v in f.values()))"
```

Dos lecturas, con veinte minutos de diferencia:

| momento (UTC) | carril de la última corrida | trackeados | activos |
|---|---|---|---|
| 2026-08-21T11:38:58Z | `hook-fast` | 3951 | **0** |
| 2026-08-21T11:42:48Z | `hourly` | 4075 | **1460** |

La cifra correcta al cierre de este informe es **1460 hallazgos abiertos**
(estado @ 2026-08-21T11:42:48Z), no 119.034 ni 120.503. El 0 de veinte minutos
antes tampoco era cierto: era el efecto del bug de §3.

## 3. Por qué el log tiene 119 mil filas: los carriles se pisan el estado

`findings-state.json` es un único diccionario global por `stable_id`, pero cada
corrida escribe estado **sólo para el carril que corrió**. En
`scripts/cos-control-plane-audit:230-247`, todo hallazgo del estado previo que
no esté en la corrida actual pasa a `resolved`. Como el carril `hook-fast` audita
otras cosas que el carril `hourly`, cada corrida de `hook-fast` da por resueltos
los 1460 hallazgos de `hourly`, y la siguiente corrida de `hourly` los vuelve a
proponer como nuevos (`if not old or old.get("status") == "resolved"`, línea 214).

Evidencia del ciclo, en las métricas del propio audit:

```bash
.venv/bin/python3 - <<'PY'
import json, collections
rows=[json.loads(l) for l in open(".cognitive-os/metrics/control-plane-audit.jsonl") if l.strip()]
print(len(rows), rows[0]["timestamp"], "->", rows[-1]["timestamp"])
for r in rows[-6:]:
    print(r["timestamp"], r["lane"], r["findings_total"], r["new_findings"], r["resolved_findings"])
print(collections.Counter({k: sum(r["new_findings"] for r in rows if r["lane"]==k) for k in {r["lane"] for r in rows}}))
PY
# 1160 filas, ventana 2026-05-15T23:28:24Z -> 2026-08-21T11:42:48Z
# 2026-08-20T19:01:22Z hourly    1459 1459    0
# 2026-08-20T19:08:42Z hook-fast    0    0 1459
# 2026-08-20T20:01:38Z hourly    1460 1460    0
# 2026-08-20T22:51:23Z hook-fast    0    0 1460
# 2026-08-20T23:00:05Z hourly    1460 1460    0
# 2026-08-21T11:38:03Z hook-fast    0    0 1460
# nuevos acumulados por carril: {'hourly': 119259, 'hook-fast': 50}
```

119.259 "nuevos" del carril `hourly` sobre ~1460 hallazgos reales: el log es el
registro de ese flip-flop. **Esto no lo arregla este encargo** (toca la máquina
de estados del audit, no el proyector) y queda anotado en §7 como deuda con
causa identificada.

## 4. Los demás conteos del brief, uno por uno

| conteo | decía | qué contaba de verdad | veredicto |
|---|---|---|---|
| `control_plane.open_findings` | 119034 | filas-evento del log (98 días, 5136 hallazgos distintos) | roto, arreglado |
| `pending_truth.total` | 74 | ítems del ledger, hechos incluidos (70 pendientes + 4 done); reporte del **2026-07-08**, 43 días viejo | etiqueta corregida + vintage declarado |
| `operational_guide.total_p0/p1` | 0 / 0 | ausencia del campo `priority` en los 287 resultados; reporte del **2026-05-12**, 100 días viejo | falso cero, ahora UNKNOWN |
| `adr_partials.total` | 127 | ítems del reporte de backlog — **coincide** con `len(items)`; `generated_at` es la cadena literal `<generated>`, o sea vintage desconocido | conteo correcto, frescura no auditable |
| `staged_deployments` | 4 dirs | directorios `*staging*`, sin verificar despliegue | etiqueta corregida |

Comandos:

```bash
.venv/bin/python3 -c "
import json,collections
pt=json.load(open('docs/06-Daily/reports/pending-truth-latest.json'))
print(pt['generated_at'], len(pt['items']), collections.Counter(i['status'] for i in pt['items']))"
# 2026-07-08T21:23:36Z 74 Counter({'verified-pending': 70, 'verified-done': 4})

.venv/bin/python3 -c "
import json,collections
og=json.load(open('docs/06-Daily/reports/operational-guide-audit-latest.json'))
print(og['generated_at'], og['summary']['by_priority'], len(og['results']),
      collections.Counter(r.get('priority') for r in og['results']))"
# 2026-05-12T17:12:06Z {} 287 Counter({None: 287})
```

Sobre los cuatro `*staging*`: al menos dos ya aterrizaron, y el conteo igual los
publicaba como pendientes de desplegar.

```bash
grep -c "session-start-projector" .claude/settings.json   # 1  -> adr-275-...-staging YA desplegado
ls -la hooks/pending-truth-drift-detector.sh              # existe -> adr-273-slice-c-staging desplegado (al menos en parte)
ls -la hooks/wrong-instrument-interceptor.sh              # No such file -> ese SÍ sigue staged
```

## 5. Qué hace ahora el proyector

`scripts/cos-session-start-projector`:

- `control_plane.open_findings` = entradas `status: active` de
  `findings-state.json`. Las filas del log salen aparte y con nombre honesto:
  `queue_event_rows`, `queue_distinct_findings`, `queue_window`.
- Si hay filas en el log pero **no** hay máquina de estados, `open_findings` es
  `null`, `open_findings_known` es `false` y `unknown_reason` explica por qué.
  El brief imprime `control-plane open findings: UNKNOWN — ...`. "No puedo
  contar los abiertos" es la salida válida; un conteo de filas no lo es.
- `pending_truth` agrega `open` (los `verified-pending`) y el vintage del reporte.
- `operational_guide` devuelve `null` en P0/P1 cuando la fuente no trae
  `priority`, con el motivo escrito.
- `staged_deployments` declara qué cuenta (`counts`) y que no verifica despliegue.
- Todo conteo lleva `source: {generated_at, age_days}`.

Salida real, misma máquina, después del arreglo:

```
pending-truth ledger: 70 open of 74 items {'verified-pending': 70, 'verified-done': 4} (source @ 2026-07-08T21:23:36Z, 43d old)
operational-guide backfill: UNKNOWN — source report carries no `priority` field on any of its 287 results; P0/P1 cannot be counted from it (source @ 2026-05-12T17:12:06Z, 100d old)
control-plane open findings: 1460 active of 4075 tracked (basis: findings-state.json @ 2026-08-21T11:42:48Z)
  remediation log (append-only, proposals only): 120503 event rows / 5269 distinct findings, window 2026-05-14T16:11:33Z -> 2026-08-21T11:42:48Z
ADR partial backlog: 127 items {'deferred': 1, 'partial': 124, 'partial-blocked': 2}; missing partial_remaining=9 (source @ <generated>)
staged-for-operator-deploy candidates: 4 dir(s) matching *staging* (deployment not verified)
```

## 6. El gate y su contrafáctico

`scripts/projector_count_sanity.py` recalcula, **desde las fuentes**, el universo
que cada etiqueta nombra, y compara contra lo que el proyector publicó:

- conteo por encima de su universo → `exceeds-universe` (rojo);
- conteo ≥ 10× su universo → `order-of-magnitude` (rojo);
- número publicado donde la fuente no tiene el campo → `false-zero` (rojo);
- `null` sin motivo escrito → `silent-null` (rojo);
- `null` con motivo → **pasa**: declarar que no se puede contar es válido.

Exit codes: 0 sin hallazgos, 1 con hallazgos, 2 error.

### Contrafáctico A — la misma proyección antes y después del arreglo

Rama A: la salida JSON del proyector **anterior** (capturada en `7a3f1758a`,
la que decía 119034), contra las fuentes de hoy:

```
$ .venv/bin/python3 scripts/projector_count_sanity.py --projection /tmp/.../proj.json
projector-count-sanity: FAIL (3 finding(s))
  [red] order-of-magnitude: control_plane.open_findings=119034 is 22.6x distinct findings in the remediation log=5269; the number cannot mean what the label says
  [red] order-of-magnitude: control_plane.open_findings=119034 is 29.2x findings tracked by the audit state machine=4075; the number cannot mean what the label says
  [red] false-zero: source has 287 results and no `priority` field on any of them; reporting a number counts the missing field, not the backlog
EXIT=1
```

Rama B: el proyector arreglado, mismas fuentes:

```
$ .venv/bin/python3 scripts/projector_count_sanity.py
projector-count-sanity: PASS (0 finding(s))
  universes: {"cp_distinct_findings": 5269, "cp_queue_rows": 120503, "cp_tracked": 4075,
              "pt_items": 74, "pt_pending": 70, "og_results": 287, "og_priced": 0,
              "ap_items": 127, "staged_dirs": 4}
EXIT=0
```

Las dos ramas dan distinto: la sonda no está rota.

### Contrafáctico B — mutar el dato para inflar el conteo

`tests/red_team/portability/test_projector_count_sanity.py` siembra 40 filas de
log sobre 4 `stable_id` (2 activos) y muta el conteo publicado a 40, que es
exactamente la regresión original en miniatura:

```
$ .venv/bin/python3 -m pytest tests/red_team/portability/test_projector_count_sanity.py \
    tests/red_team/portability/test_cos-session-start-projector.py -q
17 passed in 1.19s
```

Las seis sondas del gate son bilaterales: proyección coherente pasa, conteo
inflado a las filas cae por `order-of-magnitude`, `null` sin motivo cae por
`silent-null`, `null` con motivo pasa, P0/P1 numérico sobre fuente sin
`priority` cae por `false-zero`, y un conteo de staging que no coincide con el
disco cae por `mismatch`.

### Control positivo del guard (para no leer un cero como ausencia)

Antes de afirmar "no está protegido", sembré el caso que sí debe bloquear:

```bash
for p in manifests/documentation-truth-claims.yaml scripts/cos-session-start-projector \
         docs/02-Decisions/adrs/ADR-275-closure-and-projection-primitives.md \
         skills/session-pending-brief/SKILL.md; do
  printf '{"tool_name":"Bash","tool_input":{"command":"echo x >> %s"}}' "$p" \
    | bash hooks/protected-config-write-guard.sh >/dev/null 2>&1; echo "$p -> rc=$?"
done
# manifests/documentation-truth-claims.yaml -> rc=0
# scripts/cos-session-start-projector       -> rc=0
# docs/.../ADR-275-...md                    -> rc=0
# skills/session-pending-brief/SKILL.md     -> rc=2   <- el guard sí dispara
```

## 7. Qué queda abierto

1. **Flip-flop entre carriles (causa raíz del log de 57 MB).**
   `findings-state.json` es global pero cada corrida sólo conoce su carril, así
   que `hook-fast` marca `resolved` los hallazgos de `hourly` y viceversa. Arreglo
   propuesto: particionar el estado por `lane` (o resolver sólo dentro de los
   `stable_id` cuyo carril corrió). Mientras siga así, el log crece ~1460 filas
   por hora y `open_findings` oscila entre 0 y 1460 según qué carril corrió último.
   Toca `scripts/cos-control-plane-audit:230-247`; fuera del alcance de este encargo.

2. **`skills/session-pending-brief/SKILL.md` (protegido, requiere operador).**
   Sigue describiendo `open_findings` como "remediation queue size". Parche exacto:

   ```diff
   -   - `sections.control_plane.open_findings` — remediation queue size
   +   - `sections.control_plane.open_findings` — findings currently `active` in the
   +     control-plane audit state machine. May be `null`: when it is, print
   +     `unknown_reason` verbatim instead of a number. `queue_event_rows` is the
   +     append-only proposal log's row count — never report it as findings.
   ```
   y en la plantilla de salida:
   ```diff
   -         - control-plane findings:  {open_findings}
   +         - control-plane findings:  {open_findings} open (o UNKNOWN + motivo)
   +         - operational-guide P0/P1: {total_p0}/{total_p1} (UNKNOWN si priorities_known es false)
   ```

3. **Frescura de las fuentes.** El proyector ya declara el vintage, pero no lo
   gatea: el reporte de operational-guide tiene 100 días y el de pending-truth 43.
   El brief hoy lo dice; nadie lo bloquea.

4. **`staged_deployments` sigue sin verificar despliegue.** La etiqueta ya no
   miente ("candidates ... deployment not verified"), pero verificar de verdad
   pide un marcador de despliegue por directorio.

## Paths tocados

- `scripts/cos-session-start-projector` (modificado)
- `scripts/projector_count_sanity.py` (nuevo)
- `tests/red_team/portability/test_projector_count_sanity.py` (nuevo)
- `tests/red_team/portability/test_cos-session-start-projector.py` (3 sondas nuevas)
- `docs/02-Decisions/adrs/ADR-275-closure-and-projection-primitives.md` (contrato de conteo)
- `manifests/documentation-truth-claims.yaml` (claim `session_start_projection_counts`)
- `docs/06-Daily/reports/el-conteo-que-encabeza-el-brief-2026-08-21.md` (este informe)

Sin commit, por instrucción del encargo.
