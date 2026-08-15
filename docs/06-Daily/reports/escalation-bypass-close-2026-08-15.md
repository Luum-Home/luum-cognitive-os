# Cierre del bypass de autorización del subagent-budget-enforcer (2026-08-15)

Entregable: `docs/05-Methodology/runbooks/escalation-grace-2026-08-15/`
(parche + runbook + runner de verificación). El parche **no está aplicado**:
`hooks/**` está protegido por `protected-config-write-guard` y el env var de
aprobación no alcanza, porque el guard corre en su propio proceso antes del
comando del agente. `git apply --check` limpio sobre `fe888ab7f`.

## 1. Verificación de la premisa

Todo lo que sigue sale de `.cognitive-os/metrics/subagent-budget-enforcer.jsonl`
(732 filas al momento de medir).

| afirmación del encargo | veredicto | evidencia |
|---|---|---|
| `hooks/subagent-budget-enforcer.sh:69` hace match de substring sobre el payload entero | **confirmado** | `blob = json.dumps(payload, ...)` → `"ESCALATION:" in blob` |
| se evalúa antes del presupuesto | **confirmado** | el bloque de línea 166 corre antes de la comparación de línea 182 |
| un agente lo usó 43 veces | **confirmado, exacto** | agente `a632278962fd85ae2`, 43 filas `escalation_declared` |
| se comió 7 bloqueos | **confirmado, exacto** | bloqueos en las llamadas 51, 54, 60, 61, 62, 63, 73 |
| llegó a 96 tool calls con presupuesto 50 | **confirmado, exacto** | 39 usos del pase entre la llamada 52 y la 96 |

Comando:

```bash
python3 - <<'PY'
import json, collections
rows=[json.loads(l) for l in open('.cognitive-os/metrics/subagent-budget-enforcer.jsonl') if l.strip()]
c=collections.Counter(r['reason'] for r in rows); print(c)
v=[r for r in rows if r['agent_id']=='a632278962fd85ae2']
print("esc:",sum(1 for r in v if r['reason']=='escalation_declared'),
      "blocks@",sorted(r['tool_calls'] for r in v if r['action']=='block'),
      "max:",max(r['tool_calls'] for r in v))
PY
# Counter({'periodic': 502, 'budget_exceeded': 129, 'escalation_declared': 57, 'budget_reached': 44})
# esc: 43 blocks@ [51, 54, 60, 61, 62, 63, 73] max: 96
```

Las tres cifras del encargo reprodujeron exactas. Es el caso contrario al de la
tanda anterior, donde de 19 cifras publicadas reprodujeron 4.

## 2. Qué del encargo era falso o incompleto

**(a) "Cualquier agente que *escriba* esa cadena". Alcanza con leerla.**
El payload de `PostToolUse` incluye `tool_response`. El hook serializaba el
payload completo, así que un agente que simplemente **lee** un archivo que
contiene el token —el propio hook, sus tests, cualquiera de los informes de hoy—
se abría el presupuesto sin haberlo escrito nunca. Reproducción con `rc=0` en la
tercera llamada contra presupuesto 2, con el token únicamente en
`tool_response`: está en el runbook, sección "El defecto que el encargo no
tenía".

Esto cambia la lectura de la telemetría. Los 18 usos por debajo del presupuesto
no son "agentes escribiendo prosa sobre escalaciones": lo más probable es que
sean **agentes leyendo el hook que los gobierna**. Yo mismo lo disparé en mi
primera llamada de esta sesión —un `cat` del hook— antes de haber escrito una
sola línea.

**(b) La telemetría no puede dimensionar la gracia por el camino que sugería el
encargo.** El encargo proponía medir "cuántas llamadas usaron los agentes
después de escalar". Ese número no sirve: de los 57 usos del pase, la primera
declaración de cada agente cayó en la llamada 1–20, muy por debajo del
presupuesto de 50. Ninguno estaba escalando *porque* chocó el presupuesto, así
que sus llamadas posteriores son trabajo normal, no cierre. El delta mediano
(15) mide continuación, no cierre, y habría sobredimensionado la gracia por un
factor de ~7.

**(c) `--allow-destructive` no es una analogía, está acá adentro.** El encargo lo
mencionaba como "medido esta mañana en otra capa". Lo choqué de frente: al
intentar crear un worktree para verificar, `destructive-git-blocker` me bloqueó y
me ofreció, en el propio mensaje de bloqueo, dos formas de anularlo, una de ellas
un flag en mi propia línea de comando. **No lo usé** — habría sido acuñar mi
propio token de autorización mientras auditaba exactamente eso. Verifiqué con un
snapshot read-only (`git archive HEAD | tar -x`). Es el mismo defecto de forma
que el de este hook, en un guard distinto, y sigue abierto.

## 3. El tamaño de la gracia: 5

La gracia existe para **cerrar**: persistir estado y entregar el informe. No para
continuar. El dato que la dimensiona son los 41 subagentes que chocaron el
presupuesto **sin** el pase disponible y siguieron pidiendo llamadas contra el
bloqueo: mediana **2**, p90 **7**, máximo **14**; 34/41 dentro de 5, 40/41 dentro
de 10. Es la única población del ledger que estuvo efectivamente restringida a
cerrar.

Cinco cubre 34/41. La cola son agentes reintentando contra un bloqueo duro, no
evidencia de necesidad; y cinco llamadas concedidas rinden más que catorce
bloqueadas, porque la bloqueada se gasta igual. Cinco tampoco alcanza para
seguir trabajando, que es la propiedad que importa. Configurable con
`COS_SUBAGENT_ESCALATION_GRACE`; el comando que reproduce la tabla está en el
runbook.

## 4. Cómo se consume y dónde se registra

- **Otorgamiento**: una sola vez por `(session_id, agent_id)`, en la primera
  declaración que ocurra **por encima** del presupuesto.
  `grace_until = COUNT + GRACE - 1`, absoluto, contado desde el momento de la
  declaración — demorarla no compra nada.
- **Consumo**: por contador. Desde el otorgamiento **el payload deja de
  importar**; solo decide si `COUNT <= grace_until`. Esa es la línea que hace que
  la segunda declaración valga cero.
- **Registro**: en el ledger que ya existía,
  `.cognitive-os/metrics/subagent-budget-enforcer.jsonl`, con `reason` en
  `escalation_grace_granted` / `escalation_grace_consumed` /
  `escalation_grace_exhausted` y un campo nuevo `grace_until`. Sin archivo nuevo.
  El ledger es append-only, así que el estado no tiene read-modify-write que
  perder y **no se agregó lock**, de acuerdo con la medición previa de
  concurrencia. Sí se cerró el truncado: el contador pasa a temp + `mv`.
- **Orden de decisión**: bypass del operador → bajo presupuesto → sobre
  presupuesto. El bypass por entorno (`COS_ALLOW_SUBAGENT_BUDGET_BYPASS` +
  `COS_SUBAGENT_BUDGET_BYPASS_REASON`) **no se tocó** y ahora se evalúa primero.

## 5. El test que fija que la segunda no abre

`tests/contracts/test_subagent_budget_escalation_grace.py` (nuevo, 8 casos,
mode-agnostic para sobrevivir al split). Los dos que fijan el invariante:

- `test_second_declaration_over_budget_opens_nothing` — gasta el presupuesto,
  declara (otorga), consume la gracia, y la siguiente declaración **bien
  formada** devuelve `exit 2`. Chequea además que el ledger tenga exactamente un
  `escalation_grace_granted`.
- `test_repeated_declarations_never_exceed_the_pre_sized_grace` — diez
  declaraciones consecutivas compran exactamente `GRACE` llamadas. Sobre `HEAD`
  falla con `expected exactly 3 allowed calls, got 10`: el 96-llamadas en
  miniatura.

Medición antes/después (runner en el runbook; no se usó `PYTEST_ALLOW_NONVENV=1`,
que era el verde barato disponible):

| árbol | nuevo contrato | legacy | modes |
|---|---|---|---|
| `HEAD` sin parchear | 7 fail / 1 pass | 3 pass | 6 pass / 10 xfail |
| parcheado | **8 pass** | **3 pass** | **6 pass / 10 xfail** |

Ningún `xfail(strict=True)` pasó a `XPASS`. El trinquete del split queda intacto,
incluido `test_escalation_grace_is_bounded_and_recorded`, que sigue en `xfail`
porque corre con presupuesto 2 y el default de gracia 5 lo excede: es del otro
encargo y no había que hacerlo pasar desde acá.

**Lo que este test NO cubre**: el defecto de contrato de
`tests/contracts/test_subagent_budget_enforcer.py` sigue en pie. Ese archivo
invoca el hook sin evento y espera `exit 2` en la tercera llamada, codificando el
comportamiento roto de `PostToolUse` —donde el `exit 2` llega después de que la
herramienta ya corrió—. Es el quinto test de esa forma que aparece hoy. Mi parche
lo deja pasando (no lo rompe), pero no lo arregla: el arreglo es del split.

## 6. Por qué no fue el verde barato

- **Regex más estricta** (`^ESCALATION:`, bloque con formato): no cierra nada. El
  agente elige qué escribe y pasa a escribir el formato exacto. El problema no
  era la laxitud del patrón sino que el agente controla el canal.
- **Sacar el pase sin reemplazo**: un agente trabado sin forma de entregar pierde
  el trabajo hecho. Hoy pasó tres veces que agentes escalaron y entregaron
  hallazgos que se usaron.
- **Lo que quedó**: el token ya no *autoriza*, solo *dispara* una gracia
  pre-dimensionada, otorgada una vez y consumida por contador. Su valor total en
  toda la vida del agente es exactamente `GRACE` llamadas, se escriba una vez o
  cuarenta y tres. No se puede derrotar escribiéndolo mejor.

Nota sobre el acotamiento a `tool_input`: **no es la parte de seguridad** y está
comentado como tal en el hook. El agente autora el `tool_input` igual. Lo único
que compra es que una lectura ajena no queme en silencio una gracia de un solo
uso. Si se lo lee como el arreglo, se lee mal.

## 7. Compatibilidad con el split Post/Pre

Este cambio va **antes** de mover el hook a `PreToolUse`. Al revés se convierte
un contador con fugas en un gate que se abre con una cadena de texto:
estrictamente peor, porque ahí sí parece enforceado.

No implementa el split y es compatible con él: no toca resolución de modo ni
`hook_event_name`; todo lo agregado es lógica de **decisión** (no de conteo), que
es lo que el split mueve entero al modo `enforce`; el estado de la gracia se lee
del **ledger**, no del contador, así que `enforce` —que por contrato no debe
mutar el contador— puede leerlo sin escribir; y `grace_until` se guarda absoluto,
así que no depende de quién incrementó.

## 8. Incertidumbres

- El `5` es una decisión de diseño anclada en un proxy razonable, no una
  medición directa del costo de cerrar: la población que lo justifica estuvo
  restringida por un bloqueo, no por una gracia concedida. Las filas
  `escalation_grace_consumed` que empiece a emitir el hook parcheado son la
  medición directa; revisar el número cuando haya ~20 casos.
- No pude correr `pytest` de verdad sobre el árbol parcheado (guard de venv +
  `hooks/**` protegido). La verificación es sólida —mismo código, mismas
  aserciones, dos árboles, resultados opuestos— pero el `pytest -q` sobre el
  repo con el parche aplicado sigue pendiente y está en el runbook como paso 1
  post-aplicación.
- Un diseño más simple y de idéntica seguridad es conceder la gracia
  **automáticamente** en la primera llamada sobre presupuesto, sin mirar el
  payload: ahí el token queda inerte en todas partes. No lo elegí porque el
  encargo pedía la gracia disparada por la declaración y porque la fila de
  otorgamiento sirve de señal. Es un cambio de dos líneas si el operador
  prefiere la versión pura.

## 9. Sobre `ESCALATION:` en mi propia salida

Soy el agente que audita ese pase, así que escribirlo lo dispara. Lo manejé
así, y lo dejo asentado para que el operador pueda filtrar el ruido que agregué:

- **Agente `a44a1d4a2126bb6fe`**, sesión `93e6e34f`: **7 disparos**, en las
  llamadas 1, 7, 8, 11, 15, 25 y 26. Todos **por debajo del presupuesto**, donde
  el token es inerte incluso hoy, así que ninguno me consiguió nada.
- **El primero no fue deliberado, y es el hallazgo**: mi llamada 1 fue un `cat`
  del hook. Quedó registrado como `escalation_declared` en `tool_calls: 1` sin
  que yo escribiera nada. Así descubrí (b) de la sección 2.
- De los 7, **la mayoría son lecturas, no escrituras**: correr los tests, mirar
  el parche, imprimir el ledger. Solo dos vienen de haber autorado yo el token.
  Esa proporción es en sí misma el resultado: auditar el pase durante media hora
  produjo siete autorizaciones, y cinco de ellas nadie las pidió.
- Mientras construía el parche, escribí el token por concatenación
  (`"ESCALATION" + ":"`) para no ensuciar más el ledger. Eso también es un
  hallazgo: el detector de substring se evade con una barra invertida o un `+`,
  por el mismo agente al que gobierna. Sirve como recordatorio de que ni siquiera
  era un control difícil de sortear a propósito — y de que el arreglo no puede
  depender de detectar la cadena.

Filas mías, para descontarlas de cualquier medición futura:

```bash
grep '"agent_id": "a44a1d4a2126bb6fe"' .cognitive-os/metrics/subagent-budget-enforcer.jsonl
```
