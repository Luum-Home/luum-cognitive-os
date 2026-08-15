# Cierre del bypass de `ESCALATION:` — gracia de un solo uso (2026-08-15)

**Estado: NO aplicado. `git apply --check` limpio sobre `HEAD` (`fe888ab7f`).**
No se aplicó desde la sesión porque `hooks/**` está protegido por
`protected-config-write-guard`, y el env var de aprobación no alcanza: el guard
corre en su propio proceso antes del comando del agente. El parche queda acá
para que lo aplique el operador.

```
122 +/ 19 -  hooks/subagent-budget-enforcer.sh
259 +/  0 -  tests/contracts/test_subagent_budget_escalation_grace.py   (nuevo)
```

## Qué cierra

`hooks/subagent-budget-enforcer.sh:69` testeaba el payload **entero** contra el
substring `ESCALATION:`, y lo hacía **antes** de comparar el contador con el
presupuesto. Cualquier subagente que tuviera esa cadena en su payload reabría su
propio presupuesto, una vez por llamada, para siempre.

El problema no es la laxitud del patrón. Es que **el canal de autorización y el
canal de contenido eran el mismo canal**: ningún patrón separa "declaro que
estoy trabado" de "mi texto contiene una palabra". Un token que el agente puede
emitir no es una autorización, es un ítem de vocabulario, y un modelo que quiere
seguir trabajando lo va a producir porque es el token que continúa la
trayectoria. Endurecer la regex (`^ESCALATION:`, exigir un bloque con formato)
no cierra nada: el agente elige qué escribe, y pasa a escribir el formato
exacto.

El canal correcto ya estaba en el hook y **el parche no lo toca**:
`COS_ALLOW_SUBAGENT_BUDGET_BYPASS=1` + `COS_SUBAGENT_BUDGET_BYPASS_REASON`, en el
entorno del harness, inalcanzable desde el `tool_input` del agente. Es el modelo
que había que preservar, y el parche lo mueve a evaluarse **primero**.

## Qué hace el parche

1. **Reordena la decisión.** Bypass del operador → bajo presupuesto → sobre
   presupuesto. Antes, el test del substring corría antes que todo.
2. **Bajo presupuesto el token es inerte.** No hay nada que autorizar ahí. Esto
   solo ya elimina 18 de los 57 usos históricos del pase.
3. **Sobre presupuesto: gracia de un solo uso.** La primera declaración otorga
   `GRACE` llamadas contadas desde ese momento (`grace_until = COUNT + GRACE - 1`),
   **una sola vez por `(session_id, agent_id)`**. A partir del otorgamiento el
   payload deja de importar: solo decide el contador. La segunda declaración no
   abre nada y devuelve `exit 2`.
4. **El estado de la gracia vive en el ledger que ya existe**
   (`.cognitive-os/metrics/subagent-budget-enforcer.jsonl`), en una fila
   `escalation_grace_granted` con campo `grace_until`. Sin archivo nuevo, sin
   read-modify-write que perder: el ledger es append-only. No se agregó lock —
   otra medición del mismo día mostró que la carrera de lost-update no reproduce
   con 12, 30 ni 60 procesos concurrentes.
5. **Contador atómico.** `printf > file` trunca antes de escribir; pasa a
   temp + `mv` (temp con punto inicial para no ensuciar el glob
   `subagent-tool-calls-*` de los tests).
6. **Detección acotada a `tool_input`.** Ver "El defecto que el encargo no tenía"
   abajo. Esto **no** es el arreglo de seguridad y no hay que confundirlo con uno.

## El tamaño de la gracia: 5, y por qué

La gracia se dimensiona para **cerrar**, no para continuar: guardar estado y
entregar el informe. El número sale del propio ledger. 41 subagentes chocaron el
presupuesto **sin** tener el pase disponible (nunca escribieron el token), y
siguieron pidiendo llamadas contra el bloqueo:

| llamadas extra tras el bloqueo | agentes |
|---|---|
| mediana | 2 |
| p90 | 7 |
| máximo | 14 |
| ≤ 5 | 34 / 41 |
| ≤ 10 | 40 / 41 |

Cinco cubre 34/41. La cola (6, 7, 8, 10, 14) son agentes reintentando contra un
bloqueo duro, no evidencia de que necesitaran esas llamadas para cerrar; y cinco
llamadas **concedidas** rinden más que catorce **bloqueadas**, porque cada
bloqueada se gasta igual. Cinco tampoco alcanza para seguir trabajando, que es
la propiedad que importa.

Configurable con `COS_SUBAGENT_ESCALATION_GRACE`. El default 5 mantiene en
`xfail` el test del split (`test_escalation_grace_is_bounded_and_recorded`, que
corre con presupuesto 2): es intencional, ese test es el trinquete del otro
encargo y no había que hacerlo pasar desde acá.

Reproducir la tabla:

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

## El defecto que el encargo no tenía: alcanza con *leer*

El encargo decía "cualquier agente que **escriba** esa cadena". La realidad es
peor. El payload de `PostToolUse` incluye `tool_response`, y el hook serializaba
el payload completo. Un agente que simplemente **lee** un archivo que contiene el
token — el propio hook, sus tests, este runbook — se abre el presupuesto sin
haberlo escrito nunca.

Reproducción (sobre `HEAD`, presupuesto 2, tres llamadas, el token solo en
`tool_response`):

```bash
python3 - <<'PY'
import json, os, subprocess, tempfile, pathlib
tok = "ESCALATION" + ":"
tmp = pathlib.Path(tempfile.mkdtemp())
env = dict(os.environ, COGNITIVE_OS_PROJECT_DIR=str(tmp), COGNITIVE_OS_SESSION_ID="s",
           COGNITIVE_OS_SESSION_KIND="subagent", COGNITIVE_OS_HOOK_AGENT_ID="ag",
           COS_SUBAGENT_TOOL_CALL_BUDGET="2")
payload = {"tool_name": "Read",
           "tool_input": {"file_path": "hooks/subagent-budget-enforcer.sh"},
           "tool_response": {"content": f"Emit `{tok}` with diagnosis"}}
for i in range(3):
    r = subprocess.run(["bash","hooks/subagent-budget-enforcer.sh"], input=json.dumps(payload),
                       text=True, capture_output=True, env=env, check=False)
    print(f"call {i+1}: rc={r.returncode}")
PY
# HEAD:      call 1: rc=0 / call 2: rc=0 / call 3: rc=0   <-- la 3ra debía bloquear
# parcheado: call 1: rc=0 / call 2: rc=0 / call 3: rc=2
```

El parche acota la detección a `payload["tool_input"]`. **Esto no agrega
seguridad** — el agente también autora el `tool_input` — y está comentado como
tal en el hook. Lo que compra es que una lectura ajena no queme en silencio la
gracia de cierre, que es de un solo uso.

## Aplicar

```bash
cd <repo>
git apply --check docs/05-Methodology/runbooks/escalation-grace-2026-08-15/escalation-grace.patch
git apply         docs/05-Methodology/runbooks/escalation-grace-2026-08-15/escalation-grace.patch
bash -n hooks/subagent-budget-enforcer.sh
```

## Verificar

El árbol del repo tiene un guard de venv en `conftest.py` que rechaza
intérpretes cuyo `sys.prefix` resuelto cae fuera del árbol, así que la
verificación previa a aplicar se hizo sobre un snapshot de `HEAD`
(`git archive HEAD | tar -x`) con un runner que importa el módulo de test desde
el árbol bajo prueba. **No se usó `PYTEST_ALLOW_NONVENV=1`**: era el verde barato
disponible y habría apagado una señal que no tiene nada que ver con el contrato.

```bash
# ya aplicado, en el repo, con pytest de verdad:
.venv/bin/python -m pytest -q \
  tests/contracts/test_subagent_budget_escalation_grace.py \
  tests/contracts/test_subagent_budget_enforcer.py \
  tests/contracts/test_subagent_budget_enforcer_modes.py

# antes de aplicar, contra dos snapshots (el runner va en este mismo directorio):
python3 verify_contract.py <snapshot> tests/contracts/test_subagent_budget_escalation_grace.py
```

Resultado medido el 2026-08-15:

| árbol | nuevo contrato | legacy | modes |
|---|---|---|---|
| `HEAD` sin parchear | 7 fail / 1 pass | 3 pass | 6 pass / 10 xfail |
| parcheado | **8 pass** | **3 pass** | **6 pass / 10 xfail** |

El fallo más elocuente del baseline es
`test_repeated_declarations_never_exceed_the_pre_sized_grace`:
`expected exactly 3 allowed calls, got 10`. Es el 96-llamadas en miniatura.

Ningún `xfail(strict=True)` del archivo de modos pasó a `XPASS`: el trinquete del
split Post/Pre queda intacto.

## Orden respecto del split Post/Pre

Esto va **antes** de mover el hook a `PreToolUse`
(`docs/06-Daily/reports/subagent-budget-enforcer-architecture-2026-08-15.md`,
commit `27191622d`). Al revés se convierte un contador con fugas en un gate que
se abre con una cadena de texto: estrictamente peor, porque ahí sí *parece*
enforceado.

El parche es compatible con el split y no lo implementa:

- No toca resolución de modo ni `hook_event_name`; sigue siendo un solo camino.
- La lógica agregada es de **decisión**, no de conteo. El split separa conteo
  (Post) de decisión (Pre); todo lo nuevo cae del lado de decisión y se mueve
  entero al modo `enforce`.
- El estado de la gracia se lee del ledger, no del contador, así que el modo
  `enforce` (que por contrato **no** debe mutar el contador) puede leerlo sin
  escribir nada.
- `grace_until` se guarda absoluto, no relativo, así que no depende de quién
  incrementó el contador.

## Rollback

`git apply -R` del mismo parche. El estado de la gracia son filas de un ledger
append-only: revertir el hook lo vuelve inerte, no hay que limpiar nada.
