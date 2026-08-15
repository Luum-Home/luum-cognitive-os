# Cierre del bypass de autorización del subagent-budget-enforcer (2026-08-15)

Entregable: `docs/05-Methodology/runbooks/escalation-grace-2026-08-15/`
(parche + runbook + runner de verificación). El parche **no está aplicado**:
`hooks/**` está protegido por `protected-config-write-guard` y el env var de
aprobación no alcanza, porque el guard corre en su propio proceso antes del
comando del agente. `git apply --check` limpio sobre `fe888ab7f`.

**Resultado de una línea:** el payload deja de participar de la decisión de
presupuesto. El veredicto lo dan el contador y el entorno del harness. Un agente
que choca el presupuesto recibe, sin pedirla, una gracia de 5 llamadas para
cerrar; no hay nada que pueda escribir para conseguir más.

## 1. Verificación de la premisa

Todo sale de `.cognitive-os/metrics/subagent-budget-enforcer.jsonl` (732 filas).

| afirmación del encargo | veredicto | evidencia |
|---|---|---|
| `hooks/subagent-budget-enforcer.sh:69` hace match de substring sobre el payload entero | **confirmado** | `blob = json.dumps(payload, ...)` → `"ESCALATION:" in blob` |
| se evalúa antes del presupuesto | **confirmado** | el bloque de línea 166 corre antes de la comparación de línea 182 |
| un agente lo usó 43 veces | **confirmado, exacto** | agente `a632278962fd85ae2` |
| se comió 7 bloqueos | **confirmado, exacto** | bloqueos en 51, 54, 60, 61, 62, 63, 73 |
| llegó a 96 tool calls con presupuesto 50 | **confirmado, exacto** | 39 usos del pase entre la llamada 52 y la 96 |

```bash
python3 - <<'PY'
import json, collections
rows=[json.loads(l) for l in open('.cognitive-os/metrics/subagent-budget-enforcer.jsonl') if l.strip()]
print(collections.Counter(r['reason'] for r in rows))
v=[r for r in rows if r['agent_id']=='a632278962fd85ae2']
print("esc:",sum(1 for r in v if r['reason']=='escalation_declared'),
      "blocks@",sorted(r['tool_calls'] for r in v if r['action']=='block'),
      "max:",max(r['tool_calls'] for r in v))
PY
# Counter({'periodic': 502, 'budget_exceeded': 129, 'escalation_declared': 57, 'budget_reached': 44})
# esc: 43 blocks@ [51, 54, 60, 61, 62, 63, 73] max: 96
```

Las tres cifras reprodujeron exactas. Es el caso contrario al de la tanda
anterior, donde de 19 cifras publicadas reprodujeron 4.

## 2. Qué del encargo era falso o incompleto

**(a) "Cualquier agente que *escriba* esa cadena". Alcanza con leerla, y eso
cambió el diseño.** El payload de `PostToolUse` incluye `tool_response`. Un
agente que apenas **lee** un archivo que contiene el token —el propio hook, sus
tests, este informe— se abría el presupuesto sin haber autorado nada.

```bash
# sobre HEAD, presupuesto 2, el token SÓLO en tool_response
# HEAD:      call 1: rc=0 / call 2: rc=0 / call 3: rc=0   <-- la 3ra debía bloquear
# parcheado: call 1: rc=0 / call 2: rc=0 / call 3: rc=2
```

Lo descubrí porque **mi propia llamada 1 lo disparó**: un `cat` del hook, que
quedó como `escalation_declared` en `tool_calls: 1`. Esto reinterpreta los 18
usos por debajo del presupuesto: lo más probable es que no sean agentes
escribiendo prosa sobre escalaciones sino **agentes leyendo el hook que los
gobierna**.

Es también lo que decidió el diseño final. El encargo original decía que un
token que el agente puede **emitir** es un ítem de vocabulario; la medición
mostró algo más fuerte: **observar el mecanismo alcanza para dispararlo**. Un
canal que se contamina con la lectura no se puede acotar filtrando mejor, sólo
sacándolo de la decisión.

**(b) La telemetría no dimensiona la gracia por el camino que sugería el
encargo.** El encargo proponía medir "cuántas llamadas usaron los agentes
después de escalar". No sirve: de los 57 usos, la primera declaración de cada
agente cayó en la llamada 1–20, muy por debajo del presupuesto de 50. Ninguno
escalaba *porque* chocó el presupuesto, así que sus llamadas posteriores son
trabajo normal, no cierre. El delta mediano (15) mide continuación y habría
sobredimensionado la gracia por un factor de ~7.

**(c) `--allow-destructive` no es una analogía, está acá adentro.** Al intentar
crear un worktree para verificar, `destructive-git-blocker` me bloqueó y me
ofreció, en el propio mensaje de bloqueo, dos formas de anularlo, una de ellas un
flag en mi propia línea de comando. **No lo usé**: habría sido acuñar mi propio
token de autorización mientras auditaba exactamente eso. Verifiqué con un
snapshot read-only (`git archive HEAD | tar -x`). Mismo defecto de forma, otro
guard, sigue abierto.

## 3. El diseño: la gracia no se pide

- **El payload no participa.** Se parsea sólo para identificar al subagente
  (`session_kind`, `agent_id`, `transcript_path`). El test del substring
  desaparece del hook.
- **Otorgamiento incondicional** en la primera llamada **sobre** presupuesto.
  `grace_until = COUNT + GRACE - 1`, absoluto.
- **Una sola vez por `(session_id, agent_id)`**, consumida por contador.
- **Registro** en el ledger que ya existía, con `reason` en
  `escalation_grace_granted` / `escalation_grace_consumed` /
  `escalation_grace_exhausted` y campo nuevo `grace_until`. Sin archivo nuevo;
  append-only, así que no hay read-modify-write que perder y **no se agregó
  lock**, de acuerdo con la medición previa de concurrencia. Sí se cerró el
  truncado: el contador pasa a temp + `mv`.
- **Orden**: bypass del operador → bajo presupuesto → sobre presupuesto →
  bloqueo. El bypass por entorno **no se tocó** y ahora va primero.

El contraste entre los dos canales es el resultado que vale la pena conservar:
uno inalcanzable para el agente, que queda entero; otro eliminado porque
observarlo alcanzaba para escribirlo.

## 4. El tamaño de la gracia: 5

La gracia se dimensiona para **cerrar**, no para continuar. El dato son los 41
subagentes que chocaron el presupuesto **sin** el pase disponible y siguieron
pidiendo llamadas contra el bloqueo: mediana **2**, p90 **7**, máximo **14**;
34/41 dentro de 5, 40/41 dentro de 10. Es la única población del ledger que
estuvo efectivamente restringida a cerrar.

Cinco cubre 34/41. La cola son agentes reintentando contra un bloqueo duro, no
evidencia de necesidad; y cinco llamadas concedidas rinden más que catorce
bloqueadas, porque la bloqueada se gasta igual. Cinco tampoco alcanza para
seguir trabajando. Configurable con `COS_SUBAGENT_ESCALATION_GRACE`. El comando
que reproduce la tabla está en el runbook.

## 5. Serializar el payload: era el único motivo, y no era caro

Medido, porque el operador preguntó si se iba también el costo:

- `json.dumps(payload, ...)` aparecía **una sola vez** y era exclusivamente para
  el test del substring. Con el parche desaparece (1 → 0).
- **`json.loads(raw)` se queda.** La identidad del subagente sale del payload,
  así que se sigue parseando. Se va el costo de *serializar*, no el de *parsear*.

| payload | `json.loads` (queda) | `json.dumps` (se va) |
|---|---|---|
| este hook (~9 KB) | 0.01 ms | 0.02 ms |
| una lectura de 100 KB | 0.10 ms | 0.23 ms |
| un dump de grep de 1 MB | 1.01 ms | 2.25 ms |

Contra los ~264 ms de arranque de python ya medidos para este hook, es entre
0,008 % y 0,85 %. **El parche no hace al hook más rápido de forma perceptible.**
Lo que saca es superficie, no latencia.

## 6. Los tests

`tests/contracts/test_subagent_budget_escalation_grace.py` (nuevo, 10 casos,
mode-agnostic). Los dos que fijan la propiedad nueva:

- **`test_payload_content_does_not_change_the_verdict`** — el test que la
  versión de cadena no podía tener. Dos agentes, misma secuencia de llamadas,
  payloads idénticos salvo que uno lleva el token en **todas**. Mismo veredicto
  llamada por llamada, y la secuencia esperada completa (`warn`, `granted`,
  `consumed`, `consumed`, `exhausted`, `exhausted`).
- **`test_token_arriving_only_in_tool_response_is_indistinguishable`** — el caso
  que hace obvio mi propio hallazgo: leer un archivo que menciona el token tiene
  que ser una llamada común. Sobre `HEAD` falla con
  `reading=[(0, 'escalation_declared'), (0, 'escalation_declared'), ...]`: un
  `Read` común autorizado en todas las llamadas y bloqueado en ninguna.

| árbol | contrato nuevo | legacy | modes |
|---|---|---|---|
| `HEAD` sin parchear | 9 fail / 1 pass | (cambia con el parche) | 6 pass / 10 xfail |
| parcheado | **10 pass** | **3 pass** | **6 pass / 10 xfail** |

Ningún `xfail(strict=True)` pasó a `XPASS`.

**Tests que el parche toca, y por qué no fue alrededor.** Mover el límite del
presupuesto rompe tests que codificaban el límite viejo:

- *legacy* — el bloqueo ya no cae en `BUDGET+1` sino en `BUDGET+GRACE+1`, así que
  `test_subagent_budget_blocks_after_configured_budget` pasa a `..._plus_grace`.
  Y `test_subagent_budget_allows_structured_escalation_after_budget` afirmaba que
  el token compraba el pase: **su premisa está muerta**, y queda invertido como
  `test_declaring_an_escalation_neither_helps_nor_hurts`. Dejarlo pasando por el
  motivo nuevo habría sido un verde que no prueba nada.
- *modes* — **6 líneas**, sólo fijar `COS_SUBAGENT_ESCALATION_GRACE=1` en el env
  del helper. Con el default 5 y presupuesto 2, cinco llamadas no llegan a ningún
  bloqueo y dos `xfail(strict=True)` daban `XPASS` por una razón ajena al split
  Post/Pre. Es un pin, no un cambio de expectativas: ningún assert se tocó.

**Lo que sigue sin arreglarse**: el defecto de contrato de fondo del archivo
legacy —invoca el hook sin evento, en un mundo donde un `exit 2` de `PostToolUse`
llega después de que la herramienta ya corrió— es del split, no de acá.

## 7. Por qué no fue el verde barato

- **Regex más estricta**: no cierra nada; el agente pasa a escribir el formato
  exacto. Y ni siquiera abarcaba el caso real, que era la lectura.
- **Acotar la detección a `tool_input`**: fue mi primera versión. Arregla el
  disparo accidental por lectura pero **deja la superficie**: el agente autora el
  `tool_input` igual. El operador la descartó con el argumento correcto —filtrar
  mejor deja el canal, eliminarlo lo cierra— y tenía razón.
- **Sacar el pase sin reemplazo**: un agente trabado sin forma de entregar pierde
  el trabajo hecho. Hoy pasó tres veces que agentes escalaron y entregaron
  hallazgos que se usaron. Por eso la gracia.
- **`PYTEST_ALLOW_NONVENV=1`** y **`--allow-destructive`**: los dos verdes
  baratos disponibles para verificar. Ninguno usado.

## 8. Incertidumbres

- El `5` es una decisión anclada en un proxy razonable, no en una medición
  directa del costo de cerrar: la población que lo justifica estuvo restringida
  por un bloqueo, no por una gracia concedida. Las filas
  `escalation_grace_consumed` que empiece a emitir el hook parcheado son la
  medición directa; revisar el número con ~20 casos.
- No pude correr `pytest` de verdad sobre el árbol parcheado (guard de venv +
  `hooks/**` protegido). La verificación es sólida —mismo código, mismas
  aserciones, dos árboles, resultados opuestos— pero el `pytest -q` con el parche
  aplicado sigue pendiente y está en el runbook como paso 1 post-aplicación.
- La gracia incondicional le da 5 llamadas extra a **todo** agente que choque el
  presupuesto, incluido el que iba a parar solo. El presupuesto efectivo pasa de
  50 a 55 en el peor caso. Es el precio de que nadie tenga que pedir permiso, y
  es acotado y medible en el ledger.

## 9. Sobre `ESCALATION:` en mi propia salida

Soy el agente que audita ese pase, así que escribirlo lo dispara. Lo dejo
asentado para que el operador pueda descontar el ruido que agregué.

- **Agente `a44a1d4a2126bb6fe`**, sesión `93e6e34f`. Los disparos están en el
  ledger; todos ocurrieron **por debajo del presupuesto**, donde el token es
  inerte incluso hoy, así que ninguno me consiguió nada.
- **El primero no fue deliberado, y es el hallazgo**: mi llamada 1 fue un `cat`
  del hook y quedó registrada como `escalation_declared` en `tool_calls: 1` sin
  que yo escribiera nada.
- **La mayoría son lecturas, no escrituras**: correr los tests, mirar el parche,
  imprimir el ledger. Esa proporción es en sí misma el resultado — auditar el
  pase produjo autorizaciones que nadie pidió.
- Mientras construía el parche escribí el token por concatenación
  (`"ESCALATION" + ":"`), y el archivo de test hace lo mismo con una constante
  `TOKEN`. Eso también es un hallazgo: el detector de substring se evadía con un
  `+`, por el mismo agente al que gobernaba. Ni siquiera era difícil de sortear a
  propósito.

```bash
grep '"agent_id": "a44a1d4a2126bb6fe"' .cognitive-os/metrics/subagent-budget-enforcer.jsonl
```
