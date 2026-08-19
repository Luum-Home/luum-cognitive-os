# contextual-rule-loader: el renglón no vale la pena, y en el lugar declarado ni siquiera corre

**Fecha:** 2026-08-19
**Alcance:** la propuesta P1 de `docs/06-Daily/reports/observabilidad-primitivas-2026-08-19.md`
— registrar `hooks/contextual-rule-loader.sh` para llevar el canal del registry de 15,1% a 24,2%.
**Evidencia ejecutable:** `scripts/audit_contextual_rule_channel.py` (read-only, exit 0/1/2).

## Veredicto: NO registrar

Tres motivos independientes. Cualquiera alcanza; los tres juntos cierran el caso.

1. **En el evento que su propia nota de exclusión declara (`SubagentStart`), el hook
   no llega nunca a la línea que escribe.** Medido, no inferido.
2. **En `PreToolUse:Agent`, donde sí corre, la fila de log es un subproducto de
   inyectar ~12 KB de reglas por lanzamiento en el contexto del orquestador** — que
   ya tiene las reglas cargadas. El log no sale gratis: sale caro y del lado
   equivocado.
3. **El 24,2% es falso.** El canal no puede nombrar 131 reglas: puede nombrar 47, y
   en 267 lanzamientos reales nombró 34. El número honesto es 18,3%.

## 1. La acusación, punto por punto

| Premisa del encargo | Verificado | Resultado |
|---|---|---|
| existe y es symlink | `ls -la hooks/contextual-rule-loader.sh` | **cierto** → `../packages/context-optimization/hooks/contextual-rule-loader.sh` |
| no está registrado | `grep -c 'contextual-rule-loader' .claude/settings.json` → `0` (exit 1) | **cierto** |
| las 33 filas son de banco | 11 repeticiones de 3 prompts sintéticos idénticos, 2026-08-15 a 2026-08-18 | **cierto** |
| "está muerta por un renglón" | `tests/contracts/EXCLUDED_HOOKS.txt:144` | **falso**: la omisión está **declarada**, no olvidada |
| registrarlo lleva el canal a 24,2% | recalculado abajo | **falso**: 18,3% techo, 17,4% observado |

Las 33 filas, desglosadas:

```
prompt_preview: {'Define acceptance criteria for the new endpoint': 11,
                 'The service is crashing with a failure in the auth module': 11,
                 'error failure crash acceptance criteria ... library adoption': 11}
```

Tres prompts, once corridas cada uno. Banco de pruebas, confirmado.

## 2. La omisión es declarada, y el destino que declara no funciona

`tests/contracts/EXCLUDED_HOOKS.txt:144`:

```
contextual-rule-loader.sh | FUTURE: dynamically loads contextual rules; planned for SubagentStart — not yet wired
```

Ese es el mecanismo de omisión que aplica acá: no es `default_projection`, ni la
matriz de capacidades, ni el colapso del hot path de ADR-311. Es una entrada
explícita en la lista de hooks intencionalmente no registrados, con motivo escrito.

El problema es que el motivo escrito no se sostiene. El hook, en su línea 24, hace:

```bash
require_tool "Agent" "task" "delegate"
```

y `require_tool` (`hooks/_lib/common.sh:42-56`) sale con `exit 0` si `tool_name`
no está en la lista. `SubagentStart` no trae `tool_name`: sus campos requeridos, según
`manifests/claude-code-hooks-schema.yaml:157`, son
`[session_id, transcript_path, cwd, hook_event_name, agent_id, agent_type]`.
Y después, en la línea 42, el hook lee `.tool_input.prompt`, que tampoco existe ahí.

Dos bloqueos en serie. Probado con el stdin exacto del schema:

```
SubagentStart  → exit=0, 0 filas, 0 bytes de stdout
PreToolUse:Agent (mismo prompt) → 1 fila, 17.212 bytes de stdout
```

O sea: registrarlo en `SubagentStart` produce cero filas para siempre. Es el caso
de "hook registrado cuya lógica es inalcanzable" — la misma familia de bug que ya
apareció hoy en el repo. La nota de exclusión describe un plan que, con el hook tal
como está escrito, no se puede ejecutar.

## 3. El costo real: no es una fila de log, es contexto

El hook no loguea y ya. Primero hace `cat` del contenido completo de hasta 3
archivos de `rules/` a stdout, y recién después escribe la fila. Ese stdout es el
producto principal; el JSONL es el subproducto.

Replay de **267 prompts reales de `Agent`** extraídos de 22 transcripts de sesión,
pasados por el matcher propio del hook:

| Métrica | Valor |
|---|---:|
| lanzamientos que emitirían fila | 250 / 267 (93,6%) |
| bytes de reglas inyectados, total | 2.971.436 |
| promedio por lanzamiento que emite | **11.885 bytes** |

Unos 12 KB por lanzamiento de agente, ~3.000 tokens, en una sesión que llegó a 140
lanzamientos. Y por el contrato de Claude Code
(`manifests/claude-code-hooks-schema.yaml:95-96`), el `additionalContext` de un
`PreToolUse` aterriza *"next to the tool result"*: en el contexto del **orquestador**,
no del subagente. El orquestador ya carga `rules/RULES-COMPACT.md` y las reglas
completas por trigger. El subagente, que es quien necesita las reglas, no ve nada de
esto — a él ya le llegan por `hooks/subagent-context-injector.sh` (registrado en
`SubagentStart`, entrega `templates/agent-mandatory-rules.md`).

Pagar 12 KB del contexto más escaso, del lado que menos lo necesita, para obtener
una fila de telemetría, en un OS que tiene registrados `context-diet.sh`,
`context-budget-meter.sh` y una regla `token-economy`. No cierra.

### Latencia: no es el problema

Medida real, 20 corridas con un prompt de agente de 3.319 bytes, en sandbox con
`COGNITIVE_OS_PROJECT_DIR` desviado:

```
20 corridas: total 4.293s -> per-call 214.7 ms
```

Más del doble del objetivo `< 100ms` que declara su propio header (línea 9) y que el
comentario de las líneas 49-53 afirma haber alcanzado. Pero comparado con el hot path
real, no desentona: sobre 230.160 filas de `hook-timing` (vivo + 7 archivos rotados
en `.archive/*.gz`), los `PreToolUse` dan **p50 = 182 ms, p95 = 1054 ms**, con
`lethal-trifecta-gate` en 216 ms y `protected-config-write-guard` en 218 ms. El hook
sería un vecino más. La latencia no descalifica; el contexto sí.

Volumen, para el que quiera el dato: ~250 filas cada 267 lanzamientos. La sesión más
cargada del corpus tuvo 140 lanzamientos → ~131 filas de sesión. Entra sin drama en
la rotación. Tampoco es el problema.

## 4. El número recalculado

La aritmética del informe original es correcta; la premisa que la alimenta, no.

| | primitivas con canal | sobre 1440 |
|---|---:|---:|
| hoy | 217 | **15,1%** |
| propuesto (rules = 131) | 348 | **24,2%** |
| techo real (rules = 47 alcanzables) | 264 | **18,3%** |
| observado en replay (rules = 34) | 251 | **17,4%** |

De las 131 reglas de la familia, sólo **47** tienen entrada en
`rules.loading.contextual_triggers` con un `rules/<nombre>.md` que exista. Las otras
**84 no son alcanzables por ningún prompt**: no es baja captación, es imposibilidad
estructural. Acreditarle 131 al canal usa un criterio distinto del que el mismo
informe aplicó a skills (donde contó 194 porque el canal genérico *puede* nombrarlas).

Y hay un segundo recorte, este de diseño: `MAX_RULES=3` corta en las **primeras tres
que matcheen en orden del YAML**, no en las más relevantes. Las primeras siete
entradas tienen regex laxísimas (`error|failure|crash`, `done|complete|finished`,
`quality|verification`, `session`), así que se comen el cupo casi siempre. Por eso el
replay observó 34 y no 47, y la cola es larga: 15 reglas aparecieron una o dos veces
en 267 lanzamientos.

Además, el canal mide **reglas cargadas por coincidencia de regex**, no reglas usadas.
Que `auto-repair` se haya inyectado 126 veces sólo dice que 126 prompts contenían la
palabra "error". Como señal de utilidad de la primitiva, vale poco más que cero.

## 5. Qué se cambió

Nada en `.claude/settings.json`: el veredicto es no registrar.

- **`scripts/audit_contextual_rule_channel.py`** (nuevo): reproduce todos los números
  de este informe. `--json` para consumo automático. Exit 1 mientras el techo del
  canal siga por debajo del tamaño de la familia.
- **`tests/contracts/EXCLUDED_HOOKS.txt:144`**: el motivo decía `planned for
  SubagentStart`. Probado inalcanzable con el hook tal como está. Corregido para que
  la próxima sesión no vuelva a proponer lo mismo.

## Evidencia

```bash
# 1. registro, techo del canal, replay y números recalculados
.venv/bin/python scripts/audit_contextual_rule_channel.py            # exit 1
.venv/bin/python scripts/audit_contextual_rule_channel.py --json

# 2. no está registrado (grep -c da 0 con exit 1)
grep -c 'contextual-rule-loader' .claude/settings.json || true

# 3. la omisión está declarada
sed -n '144p' tests/contracts/EXCLUDED_HOOKS.txt

# 4. las 33 filas son de banco
.venv/bin/python -c "
import json,collections
rows=[json.loads(l) for l in open('.cognitive-os/metrics/contextual-rules.jsonl') if l.strip()]
print(len(rows), collections.Counter(r['prompt_preview'][:40] for r in rows))"

# 5. SubagentStart no alcanza la línea que escribe — sandbox, sin tocar el ledger real
SB=/tmp/crl-sandbox && mkdir -p "$SB/.cognitive-os/metrics"
ln -sfn "$PWD/rules" "$SB/rules"; ln -sfn "$PWD/cognitive-os.yaml" "$SB/cognitive-os.yaml"
printf '%s' '{"session_id":"s","transcript_path":"/tmp/t","cwd":"/tmp","hook_event_name":"SubagentStart","agent_id":"a","agent_type":"general-purpose","prompt":"error failure done quality session"}' \
  | env -u TOOL_NAME COGNITIVE_OS_PROJECT_DIR="$SB" bash hooks/contextual-rule-loader.sh | wc -c   # 0
printf '%s' '{"tool_name":"Agent","tool_input":{"prompt":"error failure done quality session"}}' \
  | env -u TOOL_NAME COGNITIVE_OS_PROJECT_DIR="$SB" bash hooks/contextual-rule-loader.sh | wc -c   # 17212

# 6. presupuesto del hot path, sobre el histórico COMPLETO (vivo + .archive/*.gz)
.venv/bin/python -c "
import json,glob,gzip,statistics
v=[]
for f in ['.cognitive-os/metrics/hook-timing.jsonl']+glob.glob('.cognitive-os/metrics/.archive/hook-timing*.gz'):
    op=gzip.open if f.endswith('.gz') else open
    for l in op(f,'rt',errors='ignore'):
        try: d=json.loads(l)
        except Exception: continue
        if d.get('event')=='PreToolUse' and isinstance(d.get('duration_ms'),(int,float)): v.append(d['duration_ms'])
print(len(v), statistics.median(v), sorted(v)[int(len(v)*.95)])"
```

## Lo que no cierra este informe

- **Tres totales distintos para "el registry"**: este informe y el de observabilidad
  usan 1440; `cobertura-scope-1441-2026-08-19.md` usa 1441; y
  `manifests/agentic-primitive-registry.lock.yaml` tiene 1034 primitivas (121 de
  `kind: rule`, contra 131 archivos en `rules/`). Los porcentajes de arriba se
  calculan sobre 1440 para ser comparables con el informe que refutan, no porque 1440
  esté verificado. Alguien tiene que decidir cuál es el denominador.
- **Si las 84 reglas sin trigger deberían tenerlo** es una decisión de producto que no
  tomo acá. Agregar 84 triggers haría el canal completo en el papel, y con `MAX_RULES=3`
  seguiría observando ~34. Sin tocar el cupo, ampliar la tabla no mueve la aguja.
- **Los 214,7 ms** se midieron con la máquina a load alto. El orden de magnitud aguanta;
  el dígito, no.
