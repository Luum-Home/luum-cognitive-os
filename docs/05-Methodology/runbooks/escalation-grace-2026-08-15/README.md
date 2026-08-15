# Cierre del bypass de `ESCALATION:` — el payload sale de la decisión (2026-08-15)

**Estado: NO aplicado. `git apply --check` limpio sobre `HEAD` (`fe888ab7f`).**
No se aplicó desde la sesión porque `hooks/**` está protegido por
`protected-config-write-guard`, y el env var de aprobación no alcanza: el guard
corre en su propio proceso antes del comando del agente.

```
108 +/ 22 -  hooks/subagent-budget-enforcer.sh
312 +/  0 -  tests/contracts/test_subagent_budget_escalation_grace.py   (nuevo)
 30 +/  8 -  tests/contracts/test_subagent_budget_enforcer.py
  6 +/  0 -  tests/contracts/test_subagent_budget_enforcer_modes.py
```

## Qué cierra

`hooks/subagent-budget-enforcer.sh:69` testeaba el payload **entero** contra el
substring `ESCALATION:`, y lo hacía **antes** de comparar el contador con el
presupuesto. Cualquier subagente cuyo payload tuviera esa cadena reabría su
propio presupuesto, una vez por llamada, para siempre.

Dos hechos descartaron cualquier arreglo que consistiera en filtrar mejor:

1. **El agente elige qué escribe.** Una regex más estricta (`^ESCALATION:`, un
   bloque con formato) es simplemente lo próximo que escribe. Un token que el
   agente puede emitir no es una autorización, es un ítem de vocabulario.
2. **No hacía falta ni escribirlo.** El payload de `PostToolUse` incluye
   `tool_response`, así que un agente que apenas **lee** un archivo con el token
   —el propio hook, sus tests— recibía el pase sin autorar nada. Verificado el
   2026-08-15: un `cat` del hook quedó registrado como `escalation_declared` en
   `tool_calls: 1`.

Si observar el mecanismo lo dispara, el token no se puede acotar. **Hay que
sacarlo de la decisión**, que es lo que hace este parche.

## Qué hace el parche

**La decisión del presupuesto lee el contador y el entorno del harness, y nada
más.** El payload se parsea únicamente para identificar al subagente
(`session_id`, `agent_id`, `transcript_path`); no participa del veredicto.

1. **Se elimina el test del substring.** No hay declaración, no hay token, no
   hay nada que el agente pueda escribir para cambiar el resultado.
2. **Gracia incondicional.** En la **primera llamada sobre presupuesto** se
   otorga una gracia de `GRACE` llamadas (`grace_until = COUNT + GRACE - 1`),
   **una sola vez por `(session_id, agent_id)`**, consumida por contador. Un
   agente que choca el presupuesto a mitad de trabajo puede guardar estado y
   entregar su informe; lo que no puede es seguir trabajando, ni pedir más.
3. **Orden de decisión:** bypass del operador → bajo presupuesto → sobre
   presupuesto (concede una vez) → bloquea.
4. **El bypass por entorno no se toca.**
   `COS_ALLOW_SUBAGENT_BUDGET_BYPASS=1` + `COS_SUBAGENT_BUDGET_BYPASS_REASON`,
   inalcanzable desde el payload del agente, y ahora se evalúa primero. El
   contraste es el punto: un canal que el gobernado no puede escribir se
   conserva entero; el otro se eliminó justamente porque observarlo alcanzaba
   para escribirlo.
5. **El estado vive en el ledger que ya existe**
   (`.cognitive-os/metrics/subagent-budget-enforcer.jsonl`), en una fila
   `escalation_grace_granted` con campo `grace_until`. Sin archivo nuevo, sin
   read-modify-write que perder. No se agregó lock: otra medición del mismo día
   mostró que la carrera de lost-update no reproduce con 12, 30 ni 60 procesos.
6. **Contador atómico.** `printf > file` trunca antes de escribir; pasa a
   temp + `mv`, con el temp arrancando en punto para no ensuciar el glob
   `subagent-tool-calls-*` de los tests.

## El tamaño de la gracia: 5

La gracia se dimensiona para **cerrar** (persistir estado, entregar el informe),
no para continuar. Sale del propio ledger: los 41 subagentes que chocaron el
presupuesto **sin** tener el pase disponible y siguieron pidiendo llamadas
contra el bloqueo.

| llamadas extra tras el bloqueo | |
|---|---|
| mediana | 2 |
| p90 | 7 |
| máximo | 14 |
| ≤ 5 | 34 / 41 |
| ≤ 10 | 40 / 41 |

Es la única población del ledger que estuvo efectivamente restringida a cerrar.
Cinco cubre 34/41; la cola son agentes reintentando contra un bloqueo duro, no
evidencia de necesidad. Cinco llamadas **concedidas** rinden más que catorce
**bloqueadas**, y cinco no alcanza para seguir trabajando, que es la propiedad
que importa. Configurable con `COS_SUBAGENT_ESCALATION_GRACE`.

```bash
python3 - <<'PY'
import json, collections, statistics
rows=[json.loads(l) for l in open('.cognitive-os/metrics/subagent-budget-enforcer.jsonl') if l.strip()]
by=collections.defaultdict(list)
for r in rows: by[r['agent_id']].append(r)
ov=[max(x['tool_calls'] for x in v) - min(x['tool_calls'] for x in v if x['reason']=='budget_exceeded') + 1
    for v in by.values()
    if any(x['reason']=='budget_exceeded' for x in v) and not any(x['reason']=='escalation_declared' for x in v)]
print("n",len(ov),"mediana",statistics.median(ov),"p90",sorted(ov)[int(.9*(len(ov)-1))],"max",max(ov))
print("<=5:",sum(1 for x in ov if x<=5),"  <=10:",sum(1 for x in ov if x<=10))
PY
```

## Serializar el payload: era el único motivo, y no era caro

`json.dumps(payload, ...)` aparecía **una sola vez** en el hook y era
exclusivamente para el test del substring. Con el parche desaparece (1 → 0).
**`json.loads(raw) se queda`**: la identidad del subagente (`session_kind`,
`agent_id`, `transcript_path`) sale del payload, así que se sigue parseando.
Se va el costo de *serializar*, no el de *parsear*.

```
payload                  json.loads (queda)   json.dumps (se va)
este hook (~9 KB)              0.01 ms             0.02 ms
una lectura de 100 KB          0.10 ms             0.23 ms
un dump de grep de 1 MB        1.01 ms             2.25 ms
```

Contra los ~264 ms de arranque de python que ya se midieron para este hook, es
entre 0,008 % y 0,85 %. **El parche no hace al hook más rápido de forma
perceptible.** Lo que saca es superficie, no latencia; decirlo al revés sería
vender otra cosa.

## Aplicar

```bash
cd <repo>
git apply --check docs/05-Methodology/runbooks/escalation-grace-2026-08-15/escalation-grace.patch
git apply         docs/05-Methodology/runbooks/escalation-grace-2026-08-15/escalation-grace.patch
bash -n hooks/subagent-budget-enforcer.sh
.venv/bin/python -m pytest -q tests/contracts/test_subagent_budget_escalation_grace.py \
                              tests/contracts/test_subagent_budget_enforcer.py \
                              tests/contracts/test_subagent_budget_enforcer_modes.py
```

## Verificar antes de aplicar

El `conftest.py` del repo rechaza intérpretes cuyo `sys.prefix` resuelto cae
fuera del árbol, así que la verificación previa se hizo sobre un snapshot de
`HEAD` (`git archive HEAD | tar -x`) con un runner que importa el módulo de test
desde el árbol bajo prueba, de modo que `REPO_ROOT`/`HOOK` resuelvan ahí.
**No se usó `PYTEST_ALLOW_NONVENV=1`** ni `--allow-destructive` para el
worktree: eran los dos verdes baratos disponibles y ambos habrían apagado una
señal ajena al contrato.

```bash
python3 verify_contract.py <snapshot> tests/contracts/test_subagent_budget_escalation_grace.py
```

| árbol | contrato nuevo | legacy | modes |
|---|---|---|---|
| `HEAD` sin parchear | 9 fail / 1 pass | (no aplica, cambia con el parche) | 6 pass / 10 xfail |
| parcheado | **10 pass** | **3 pass** | **6 pass / 10 xfail** |

El fallo más elocuente del baseline es
`test_token_arriving_only_in_tool_response_is_indistinguishable`:
`reading=[(0, 'escalation_declared'), (0, 'escalation_declared'), ...]` — un
`Read` común, sin token en el `tool_input`, autorizado en **todas** las llamadas
y bloqueado en ninguna.

Ningún `xfail(strict=True)` del archivo de modos pasó a `XPASS`.

## Los tests que el parche toca (y por qué)

Mover el límite del presupuesto rompe tests que codificaban el límite viejo. Se
arreglaron en el origen, no alrededor:

- **`test_subagent_budget_enforcer.py`** (legacy). El bloqueo ya no cae en
  `BUDGET+1` sino en `BUDGET+GRACE+1`, así que
  `test_subagent_budget_blocks_after_configured_budget` pasa a
  `..._plus_grace`: espera la concesión en la 3ra y el bloqueo en la 4ta.
  `test_subagent_budget_allows_structured_escalation_after_budget` afirmaba que
  el token compraba el pase: **su premisa está muerta**. Queda invertido, como
  `test_declaring_an_escalation_neither_helps_nor_hurts`. Dejarlo pasando por el
  motivo nuevo habría sido un verde que no prueba nada.
- **`test_subagent_budget_enforcer_modes.py`**: **6 líneas**, sólo fijar
  `COS_SUBAGENT_ESCALATION_GRACE=1` en el env del helper. Con el default 5 y
  presupuesto 2, cinco llamadas no llegan a ningún bloqueo y dos
  `xfail(strict=True)` daban `XPASS` por una razón que no tiene nada que ver con
  el split Post/Pre. Es un pin, no un cambio de expectativas: ningún assert se
  tocó y los 10 xfail siguen en xfail.

## Orden respecto del split Post/Pre

Esto va **antes** de mover el hook a `PreToolUse`
(`docs/06-Daily/reports/subagent-budget-enforcer-architecture-2026-08-15.md`,
commit `27191622d`). Al revés se convierte un contador con fugas en un gate que
se abre con una cadena de texto: estrictamente peor, porque ahí sí *parece*
enforceado.

Compatible con el split, y no lo implementa:

- No toca resolución de modo ni `hook_event_name`.
- Todo lo agregado es lógica de **decisión**, no de conteo. El split mueve la
  decisión entera al modo `enforce`.
- El estado de la gracia se lee del **ledger**, no del contador, así que
  `enforce` —que por contrato no debe mutar el contador— puede leerlo sin
  escribir nada.
- `grace_until` se guarda absoluto, no relativo: no depende de quién incrementó.
- El pin de `COS_SUBAGENT_ESCALATION_GRACE` en los tests de modos deja esas
  pruebas independientes del default de la gracia, que es lo que querían medir.

## Rollback

`git apply -R` del mismo parche. El estado de la gracia son filas de un ledger
append-only: revertir el hook lo vuelve inerte, no hay nada que limpiar.
