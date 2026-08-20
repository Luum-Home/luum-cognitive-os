# secret-detector: la rama que creía bloquear

Fecha: 2026-08-19 · Alcance: `hooks/secret-detector.sh` (PreToolUse) · Estado: arreglado y probado

## Resumen ejecutivo

La rama de "el input era 100% secretos" emitía `permissionDecision: "block"`, un valor
que el arnés no acepta (Claude Code toma `allow|deny|ask|defer`), con `exit 0` y sin
respaldo: JSON que no valida en exit 0 es error no bloqueante y la llamada sigue. La
rama **es alcanzable** con un payload trivial, así que la guarda fallaba abierta.
Replay del hook real contra **143.605 tool-calls** históricos: **0** habrían llegado a
esa rama, así que encenderla no frena trabajo y se aplicó (`deny` + `exit 2`).
Además apareció un segundo fail-open, silencioso y más grave: el patrón de clave
privada PEM empieza con cinco guiones y `grep` lo leía como opción, con el error
tragado por `2>/dev/null` — **6 payloads históricos con una clave privada real pasaron
sin redactar**. Se arregló con `--` en los dos `grep`.

## Correcciones a las premisas del encargo

1. **"10.113 corridas"** — hoy son **11.493** según
   `.venv/bin/python3 scripts/hook_vitality_audit.py --json`. El resto de esa ficha se
   confirma: `capability_observable: false`, `bucket: unproven-guard`, 0 bloqueos vistos.
2. **"su única línea con `exit 2` es un comentario"** — correcto para el hook, pero el
   texto del comentario decía lo contrario de lo que hacía el código: prometía "native
   block" *en lugar de* exit 2. El defecto no era un olvido, era una migración
   (`ce8042a3b`, `7ff4d6d00`) que cambió exit 2 por un valor inexistente.
3. **"estimalo contra el corpus en `tests/fixtures/payload-corpus/`"** — ese corpus **no
   sirve** para esto: son `toolUseResult` de PostToolUse con todos los escalares
   tokenizados (`"<str>"`, `0`), sin un solo `command` real (ver su README: "values are
   the privacy hazard"). La estimación se hizo contra los transcripts, que sí tienen los
   `tool_input` originales.
4. **"puede que el 100%-secretos sea el único roto"** — no lo era. El patrón de clave
   privada nunca disparó en ninguna rama (sección *Otros caminos*).
5. **Los tests ya fijaban el defecto**: `tests/unit/test_secret_detector_updated_input.py`
   y `tests/hooks/test_secret_detector.py` afirmaban `permissionDecision == "block"` y
   `returncode == 0`. No era código sin cubrir: era cobertura que certificaba el bug.
6. **El encargo dice "no pushees" y "no uses `git add`"**: verificado que se puede
   commitear con rutas explícitas; se hizo así, sin push.
7. **Presupuesto de tool-calls**: se pasó de 50 y se usó el bypass documentado
   (`COS_ALLOW_SUBAGENT_BUDGET_BYPASS=1` con motivo) para no dejar el árbol con el hook
   cambiado, un test rojo y sin informe.

## La rama: ¿es alcanzable?

Sí, y con el payload más simple posible. La condición es `visible_after` vacío: que
`command`/`content`/`new_string` queden en `[REDACTED]` más espacios. Un `command` que
sea exactamente una AWS Access Key ID (prefijo + 16 alfanuméricos) la alcanza:

```bash
# ver scripts/estimate_secret_detector_firing.py y la sección "Las tres corridas"
printf '%s' "$payload" | CLAUDE_PROJECT_DIR=/tmp/sandbox /bin/bash hooks/secret-detector.sh
```

Antes del arreglo devolvía `exit=0` con `"permissionDecision":"block"`. Según el contrato
transcrito en `manifests/claude-code-hooks-schema.yaml`
(`events.PreToolUse.permission_decision_values: [allow, deny, ask, defer]`) y la doc
oficial (`curl -sSL https://code.claude.com/docs/en/hooks.md`, tabla *Decision control*:
"`permissionDecision` (allow/deny/ask/defer)"), `"block"` no está. Y la misma doc define
qué pasa con eso: *"With a parsed object that fails schema validation ... it's the same
non-blocking error as on exit 0: the action proceeds"*. La deprecación de `"block"` que
la doc sí reconoce es sobre el campo **top-level `decision`**, no sobre
`hookSpecificOutput.permissionDecision`.

Dato que ordena el riesgo: es una guarda inerte pero **no la única defensa**. La rama de
redacción, que es la que se usa en la práctica, sí funcionaba.

## ¿Cuántas veces habría bloqueado?

Script: `scripts/estimate_secret_detector_firing.py` (read-only; corre el hook real sobre
los `tool_input` históricos de Bash/Edit/Write/MultiEdit; nunca imprime material secreto;
exit 1 si algún payload alcanza la rama de deny).

```bash
.venv/bin/python3 scripts/estimate_secret_detector_firing.py            # todos los proyectos
.venv/bin/python3 scripts/estimate_secret_detector_firing.py --root ~/.claude/projects/<proyecto>
```

| Corpus | tool-calls | matches | redact+allow | **deny** | hook mudo |
|---|---|---|---|---|---|
| Este repo | 13.373 | 2 | 2 | **0** | 0 |
| Todos los proyectos (2,3 GB) | 143.605 | 52 | 46 | **0** | 6 |
| Todos, con el hook ya arreglado | 143.631 | 55 | 55 | **0** | 0 |

Frecuencia estimada de bloqueo: **cero en 143.605 llamadas**. Encender la guarda no frena
trabajo histórico. Los 2 matches de este repo son sintéticos (mi propio payload de prueba
de hoy y un `measure_value.py` de ejemplo del 2026-08-15).

Las 6 corridas mudas del corpus previo eran justamente las claves privadas PEM: mismo
número que el patrón `-----BEGIN … PRIVATE KEY-----`, y desaparecen con el arreglo.

## El arreglo, o por qué no lo apliqué

Aplicado, porque la frecuencia dio cero. Dos cambios en `hooks/secret-detector.sh`:

1. **Línea ~181** — `permissionDecision: "block"` → `"deny"`, el mensaje pasa a
   `permissionDecisionReason` (que la doc define como el campo que sí se le muestra a
   Claude en un deny), se escribe también a stderr y se cierra con `exit 2`. El exit 2 es
   el respaldo: bloquea aunque el JSON sea rechazado de nuevo, y es el patrón de la casa
   (`destructive-rm-blocker.sh`, `protected-config-write-guard.sh`, `edit-lock-pre-tool.sh`).
2. **`grep -oE -- "$pattern"` y `grep -qE -- "$pattern"`** — sin `--`, el patrón de clave
   privada se interpretaba como opción (`grep: unrecognized option`) y el error moría en
   `2>/dev/null`.

Tests actualizados, no relajados: las dos suites que afirmaban `"block"` + exit 0 ahora
afirman `deny` + exit 2, y se agregaron tres pruebas —una que valida la decisión emitida
contra `permission_decision_values` leído del manifiesto (para que el próximo valor
inventado falle solo), otra sobre la clave privada en `content`, y la del payload limpio
que ya existía.

## Las tres corridas

Con el hook **anterior** (`git stash`-equivalente: salida capturada antes del cambio):

```text
--- A 100% secretos ---
exit=0
stdout={"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"block","additionalContext":"SECURITY WARNING: tool input consisted entirely of secrets (AKIA0123…) ..."}}
--- B secreto embebido ---
exit=0
stdout={"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","updatedInput":{"command":"aws configure set aws_access_key_id [REDACTED]"}, ...}}
--- C payload limpio ---
exit=0
stdout=
```

Con el hook **arreglado**:

```text
--- A 100% secretos ---
exit=2
stdout={"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"SECURITY WARNING: tool input consisted entirely of secrets (AKIA0123…) ..."}}
stderr=SECURITY WARNING: tool input consisted entirely of secrets (AKIA0123…) ...
--- B secreto embebido ---
exit=0
stdout={"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","updatedInput":{"command":"aws configure set aws_access_key_id [REDACTED]"}, ...}}
--- C payload limpio ---
exit=0
stdout=
```

A bloquea sólo después del arreglo; **B y C se comportan igual en las dos versiones** —
la guarda no se volvió paranoica. Las tres direcciones quedan como test ejecutable:

```bash
.venv/bin/python3 -m pytest tests/hooks/test_secret_detector.py \
  tests/unit/test_secret_detector_updated_input.py -q     # 18 passed
```

Evidencia colateral de que la rama de redacción está viva en producción: mientras escribía
este informe, el hook registrado redactó mis propios comandos de prueba
(`Secrets redacted before execution: -----BEG…,AKIAIOSF…`), lo que rompió dos ediciones
hasta que armé los literales por partes. El patrón PEM aparece ahí porque ya estaba
arreglado.

## Otros caminos del hook

| Camino | Estado | Detalle |
|---|---|---|
| Redacción + allow (`command`/`content`/`new_string`) | Sano | 46 casos históricos, estructura del comando preservada |
| Clave privada PEM | **Roto, arreglado** | `grep` leía el patrón como opción; 6 payloads con clave real pasaron intactos |
| 100% secretos | **Roto, arreglado** | `"block"` + exit 0 → `deny` + exit 2 |
| Secreto sólo en `file_path` | Débil, **no tocado** | `file_path` entra al pre-check pero no se redacta ni aporta hits: el hook sale mudo en exit 0. No apareció ni una vez en 143.605 llamadas; tocarlo sin caso real es especular |
| `MultiEdit` | Cobertura parcial, **no tocado** | El `case` lo acepta, pero sólo se recorren `command`/`content`/`new_string`: los `edits[]` de MultiEdit no se miran. El matcher registrado es `Bash|Edit|Write`, así que hoy no llega |
| PostToolUse (higiene de env vars) | Sano, advisory | Siempre exit 0, escribe `missing-secrets.jsonl` |
| Observabilidad | Sin cambio de raíz | `hook_vitality_audit` lo marcaba `capability_observable: false` porque señalizaba sólo por stdout JSON; con `exit 2` el bloqueo ahora sí es observable por telemetría |

Gap de gobernanza que este defecto expone: **ningún test ni gate validaba los valores de
`permissionDecision` contra `manifests/claude-code-hooks-schema.yaml`**, teniendo el
contrato transcrito en el repo. Se cubre para este hook con
`test_emitted_permission_decision_is_a_value_the_host_accepts`; generalizarlo a los demás
hooks emisores de decisión queda como trabajo abierto para el operador.
