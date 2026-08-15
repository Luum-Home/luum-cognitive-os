# Lote 5 — Los gates cableados del SO: cuáles pueden bloquear y cuáles hacen teatro

**Fecha:** 2026-08-15
**Alcance:** los 66 gates *cableados* del censo canónico (no los 40 del `settings.json`).
**Veredicto corto:** de 66, **22 son teatro** — están cableados y no pueden bloquear.
Otros **11 son advisory-only**: su camino de bloqueo existe pero corre en un evento
que no puede prevenir nada. Sólo **2** previenen y tienen evidencia de haberlo hecho.

> **Corrección post-lote-2 (2026-08-15).** Tres premisas de mi primera pasada
> cayeron. Ver §9. Los números de arriba ya están corregidos.

---

## 1. El censo reproduce

```bash
.venv/bin/python scripts/audit_gate_registration.py
# gate 69, wired 66, unwired 3
```

La corrección del encargo era correcta y la confirmo: contar sobre
`.claude/settings.json` da 40 porque ese archivo es *generado*. Los 26 restantes
llegan por `hooks/bash-hot-path-dispatcher.sh`, que hace fan-out sin figurar en el
settings. Empecé por ésos, como pedía el encargo, y ahí apareció el hallazgo más
caro (§5).

## 2. Evidencia ejecutable

```bash
.venv/bin/python scripts/audit_gate_liveness.py                  # tabla resumen
.venv/bin/python scripts/audit_gate_liveness.py --quadrant theatre
.venv/bin/python scripts/audit_gate_liveness.py --json           # filas completas
.venv/bin/python -m pytest tests/audit/test_gate_liveness_classifier.py -q
```

Read-only, determinista, exit 0 sin teatro / 1 con teatro / 2 error. **No re-deriva
la población**: se la pide a `audit_gate_registration.py`, así que los dos scripts no
pueden discrepar sobre qué es un gate.

Las dos preguntas se responden con fuentes distintas y no se mezclan:

- **¿Puede bloquear?** — lectura estática del código. Cadena de guardas por
  indentación hasta cada salida bloqueante.
- **¿Bloqueó?** — `exit_code == 2` en `.cognitive-os/metrics/hook-timing.jsonl`
  (37.154 filas al momento de correrlo).

## 3. Los cuadrantes

| cuadrante | qué significa | n |
|---|---|---:|
| **live** | puede prevenir + bloqueó | **2** |
| **advisory-only** | tiene camino de bloqueo, pero corre en PostToolUse/Stop: informa, no previene | **11** |
| **untested** | puede prevenir + nunca bloqueó, *y la telemetría lo ve* | 11 |
| **unmeasured** | puede + la telemetría **no puede verlo** (§5) | 20 |
| **theatre** | **no puede** + nunca bloqueó | **22** |
| **telemetry-lying** | no puede + "bloqueó" | 0 |

`unmeasured` es un quinto casillero que el encargo no preveía y que hubo que abrir:
ver §5. No relaja el hallazgo — `theatre` se decide sólo por lectura de código, así
que un gate invisible a la telemetría igual puede caer en teatro.

Que `telemetry-lying` esté en 0 es una señal buena: donde hay medición, coincide con
la lectura estática.

## 4. Los 22 de teatro, por causa

| causa | n | qué pasa |
|---|---:|---|
| `no-block-path` | 15 | no hay ninguna salida bloqueante en el archivo |
| `exit-1-not-2` | 4 | imprime `BLOCKED` y sale **1** — no bloquea (§5) |
| `phase-pinned` | 2 | el `exit 2` exige `phase in (production, maintenance)`; la fase es `reconstruction` |
| `policy-demoted` | 1 | `cos governance policy` degrada la categoría a advisory |

Una causa por gate; 15+4+2+1 = 22. Verificable con
`audit_gate_liveness.py --json --quadrant theatre`.

Los 15 de `no-block-path` no son todos un bug. Varios están **documentados como
advisory** y el nombre es lo que engaña:

- `decision-depth-gate` — el propio encabezado dice *"Fail-silent gate: emits
  warnings, never blocks (exit 0 always)"*. Se llama `-gate` y no es un gate.
- `dod-gate` — *"production / maintenance : BLOCK (note only — never exits
  non-zero)"*. La palabra BLOCK aparece en el mensaje al operador; el proceso sale 0.
- `agent-bash-cwd-enforcer` — imprime `❌❌❌ BLOCKER WARNING` y sale 0.

Eso no es un gate roto: es un instrumento con nombre de gate. La deuda es de
**nomenclatura y de censo** — `audit_gate_registration.py` los clasifica como `gate`
por el token del nombre, y por eso el numerador "66 gates" está inflado.

### Los que sí son bugs

**`exit-1-not-2` (4 gates).** Éstos *quieren* bloquear, imprimen el cartel de
bloqueo, y salen 1:

| gate | ruta | vía |
|---|---|---|
| `adoption-freeze-gate` | `hooks/adoption-freeze-gate.sh:119` | dispatcher |
| `external-pattern-cleanroom-gate` | `hooks/external-pattern-cleanroom-gate.sh:126` | dispatcher |
| `research-to-runtime-firewall` | `hooks/research-to-runtime-firewall.sh:76` | dispatcher |
| `clean-room-ast-similarity-gate` | `hooks/clean-room-ast-similarity-gate.sh:140` | profile |

El contrato lo fija el propio repo en
`docs/04-Concepts/architecture/cos-dispatch/README.md:32` — **"Exit code 2 = block"**.
Un `exit 1` es un error no bloqueante: el agente ve el mensaje y el `git commit`
sigue. Tres de los cuatro son gates de commit de cleanroom/licencias.

**`phase-pinned` (2).** `agnix-lint` y `scope-proportionality` tienen su `exit 2`
detrás de `phase in (production|maintenance)`. `cognitive-os.yaml:9` dice
`phase: reconstruction`. Inalcanzable tal como está configurado — el script lo
demuestra corriendo el mismo fixture con las dos fases (test
`test_phase_pinned_exit_2_is_unreachable`).

**`policy-demoted` (1).** `release-guard`:

```bash
./scripts/cos governance policy --project-dir . --category release --json
# {"allowed_to_block": false, "category": "release", ...}
```

El resolver `hooks/_lib/governance-policy.sh` está bien diseñado (falla *cerrado*:
si no puede responder, permite bloquear). Pero para la categoría `release` responde
`false` hoy, y `release-guard` degrada su bloqueo a advisory. Es un gate apagado por
configuración, no por bug.

## 5. Lo que el encargo daba por cierto y no lo es

### 5.1 La telemetría no puede contestar la pregunta 2 para 20 de los 66

Éste es el hallazgo que rompe el método propuesto. `hook-timing.jsonl` lo escribe el
wrapper que `scripts/generate-project-settings.sh` inyecta **en las entradas de
`.claude/settings.json`**. Un gate que llega sólo por el dispatcher es invisible: la
fila se le atribuye al dispatcher.

```
destructive-rm-blocker      → 0 filas
destructive-git-blocker     → 0 filas
direct-main-guard           → 0 filas
network-egress-guard        → 0 filas
release-guard               → 0 filas
bash-hot-path-dispatcher    → exit_code=1: 22 filas | exit_code=2: 18 filas
```

Esos 22+18 disparos del dispatcher **son** los hijos actuando, agregados y sin
atribuir. Para los 20 gates `unmeasured`, `ever_blocked == 0` significa *"nadie lo
midió"*, no *"nunca bloqueó"*. Reportarlos como "no probados" habría sido afirmar un
hecho desde un archivo que estructuralmente no lo contiene.

Corolario operativo: los 18 `exit_code=2` del dispatcher prueban que **algún** gate
hijo bloqueó de verdad; no se puede saber cuál sin instrumentar el fan-out.

### 5.2 El `//` de jq ya no está vivo en ningún gate

El encargo pedía buscar `// true` y `// false` en los 66. Aparecen 3 veces y
**ninguna es el bug**:

- `hooks/network-egress-guard.sh:21-22` — `.block // false`, leído como
  `[ "$BLOCK" = "true" ]`. Polaridad **sana**: cuando `block` es genuinamente `true`,
  `//` devuelve `true`.
- `hooks/agent-prelaunch.sh:78` — `... // false`, leído contra `= "true"`. Sana.
- `hooks/dispatch-gate.sh:139` — es un **comentario** que documenta el bug ya
  arreglado.

La asimetría importa y quedó fijada en el test: `X // true` probado contra `"false"`
es el bug (no puede ser falso nunca); `X // false` probado contra `"true"` es
correcto. Marcar el segundo sería un falso positivo que enseña a ignorar el primero.

**No apliqué nada acá**: no había nada que arreglar.

### 5.3 El "colchón de allowlist" es real y peor de lo enunciado

`audit_gate_registration.py` ya lo reporta: 185 entradas, **152 ya cableadas**. Un
ratchet con 152 lugares libres no suprime nada. No lo toqué — mover un supresor es
decisión del operador — pero queda confirmado.

### 5.4 El fail-open de `common.sh:190` no afecta a estos gates

`check_disabled_env` sale 0 sólo cuando el operador puso `DISABLE_HOOK_<X>=true`.
Es un interruptor explícito, no una herencia silenciosa. Ningún gate de los 22 cae
en teatro por esta causa.

## 6. Qué arreglé

**Nada del comportamiento de bloqueo.** Los cuatro `exit-1-not-2` son un cambio de
una línea cada uno, pero encender cuatro gates de commit a la vez en un checkout
compartido con sesiones concurrentes es exactamente "cambiar qué se bloquea en
producción" — decisión del operador, no mía. Va como recomendación, no como parche.

Entregado:

- `scripts/audit_gate_liveness.py` — el clasificador (read-only, determinista).
- `tests/audit/test_gate_liveness_classifier.py` — 8 tests sobre fixtures
  sintéticas, incluido el par de polaridad de jq y el `exit 1` vs `exit 2`. No leen
  hooks reales, así que siguen verdes cuando los hooks se arreglen.

### Confirmación no planeada de un gate `live`

Al intentar corregir el encabezado mentiroso de `hooks/bash-hot-path-dispatcher.sh`
(dice *"non-zero/2 propagates the first blocking child gate"*, confundiendo 1 con 2),
**`protected-config-write-guard` me bloqueó la edición con exit 2**. No lo bypasseé.
Es evidencia independiente de que la clasificación `live` de ese gate es correcta: el
contador de `ever_blocked` subió de 4 a 6 durante esta auditoría.

## 7. Deuda registrada, no arreglada

1. **`hooks/bash-hot-path-dispatcher.sh:10`** — el comentario de encabezado afirma que
   propaga "non-zero/2" como bloqueo. Sólo el 2 bloquea. Requiere revisión humana
   (`COS_ALLOW_PROTECTED_CONFIG_WRITE`). Contradicción de documentación → entra al
   ledger de pending-truth por la norma de cierre de sesión.
2. **Los 4 `exit-1-not-2`** — decisión del operador.
3. **`release-guard` demotado** por política de `release` — decisión del operador.
4. **Gates con nombre de gate que son instrumentos** (`decision-depth-gate`,
   `dod-gate`, `agent-bash-cwd-enforcer`, y los demás `no-block-path` documentados
   como advisory): inflan el numerador del censo. O se renombran, o el censo deja de
   clasificar por token del nombre.
5. **Fan-out del dispatcher sin instrumentar** — mientras siga así, 20 de 66 gates no
   tienen respuesta posible a "¿bloqueó alguna vez?".

## 8. Qué no pude medir

- **Si los 20 `unmeasured` bloquearon alguna vez.** §5.1. Es un límite del
  instrumento, no del análisis.
- **Cuál** de los hijos del dispatcher produjo los 18 `exit_code=2`.
- **Alcanzabilidad real bajo shell dinámico.** La cadena de guardas se reconstruye
  por indentación, que es la convención que estos hooks siguen, pero no es un parser.
  Un `exit 2` detrás de `eval`, de una función definida en otro archivo, o de un
  `trap`, se leería como alcanzable. Sesga hacia **subestimar** el teatro: los 22 son
  piso, no techo.
- **Si las condiciones de los 21 `untested` son satisfacibles en la práctica.** Que el
  `exit 2` sea alcanzable no dice que la condición mala vaya a ocurrir. "No probado"
  es literal: no es un veredicto sobre el gate.

---

## Anexo — la tabla completa de los 66

| gate | cuadrante | causa | vía | disparos | bloqueos |
|---|---|---|---|---:|---:|
| `lethal-trifecta-gate` | live | reachable | set | 1574 | 1 |
| `protected-config-write-guard` | live | reachable | set | 1574 | 6 |
| `subagent-budget-enforcer` | live | reachable | set | 1512 | 46 |
| `adoption-freeze-gate` | theatre | exit-1-not-2 | disp | 0 | 0 |
| `adversarial-review-gate` | theatre | no-block-path | set | 28 | 0 |
| `agent-bash-cwd-enforcer` | theatre | no-block-path | prof | 0 | 0 |
| `agnix-lint` | theatre | phase-pinned | prof | 0 | 0 |
| `clarification-interceptor` | theatre | no-block-path | prof | 0 | 0 |
| `clean-room-ast-similarity-gate` | theatre | exit-1-not-2 | prof | 0 | 0 |
| `completion-gate` | theatre | no-block-path | set | 28 | 0 |
| `concurrent-write-guard-codex-proxy` | theatre | no-block-path | set | 0 | 0 |
| `confidence-gate-llm` | theatre | no-block-path | prof | 0 | 0 |
| `decision-depth-gate` | theatre | no-block-path | set | 28 | 0 |
| `dod-gate` | theatre | no-block-path | prof | 0 | 0 |
| `edit-lock-drain-parked` | theatre | no-block-path | set | 165 | 0 |
| `edit-lock-process-negotiations` | theatre | no-block-path | set | 42 | 0 |
| `edit-lock-session-end` | theatre | no-block-path | set | 40 | 0 |
| `external-pattern-cleanroom-gate` | theatre | exit-1-not-2 | disp | 0 | 0 |
| `guardrails-validator` | theatre | no-block-path | prof | 0 | 0 |
| `pending-truth-staleness-gate` | theatre | no-block-path | disp | 0 | 0 |
| `private-mode-gate` | theatre | no-block-path | set | 2 | 0 |
| `release-guard` | theatre | policy-demoted | disp | 0 | 0 |
| `research-to-runtime-firewall` | theatre | exit-1-not-2 | disp | 0 | 0 |
| `scope-proportionality` | theatre | phase-pinned | set | 28 | 0 |
| `validation-lock-cleanup` | theatre | no-block-path | set | 8 | 0 |
| `agent-message-inbox-guard` | unmeasured | reachable | disp | 0 | 0 |
| `ai-provider-identity-guard` | unmeasured | reachable | prof | 0 | 0 |
| `branch-ownership-lock` | unmeasured | reachable | disp | 0 | 0 |
| `conflict-marker-guard` | unmeasured | reachable | disp | 0 | 0 |
| `cross-session-coordination-guard` | unmeasured | reachable | disp | 0 | 0 |
| `destructive-git-blocker` | unmeasured | reachable | disp | 0 | 0 |
| `destructive-rm-blocker` | unmeasured | reachable | disp | 0 | 0 |
| `direct-main-guard` | unmeasured | reachable | disp | 0 | 0 |
| `git-commit-scope-guard` | unmeasured | reachable | disp | 0 | 0 |
| `network-egress-guard` | unmeasured | reachable | disp | 0 | 0 |
| `orchestrator-claim-gate` | unmeasured | reachable | disp | 0 | 0 |
| `pre-commit-content-hash-dedupe` | unmeasured | reachable | disp | 0 | 0 |
| `publication-safety` | unmeasured | reachable | prof | 0 | 0 |
| `rate-limiter` | unmeasured | reachable | prof | 0 | 0 |
| `research-compliance-guard` | unmeasured | reachable | disp | 0 | 0 |
| `scope-marker-portability-gate` | unmeasured | reachable | disp | 0 | 0 |
| `skill-router-bash-gate` | unmeasured | reachable | disp | 0 | 0 |
| `subagent-capability-preflight` | unmeasured | reachable | prof | 0 | 0 |
| `symlink-mutation-guard` | unmeasured | reachable | disp | 0 | 0 |
| `untracked-work-preservation-guard` | unmeasured | reachable | disp | 0 | 0 |
| `agent-control-inbound-guard` | untested | reachable | set | 1574 | 0 |
| `agent-prelaunch` | untested | reachable | set | 28 | 0 |
| `clarification-gate` | untested | reachable | set | 28 | 0 |
| `concurrent-write-guard` | untested | reachable | set | 174 | 0 |
| `confidence-gate` | untested | reachable | set | 28 | 0 |
| `confidentiality-enforcer` | untested | reachable | set | 165 | 0 |
| `content-policy` | untested | reachable | set | 165 | 0 |
| `cosd-auth-guard` | untested | reachable | set | 1574 | 0 |
| `dequeue-notify` | untested | reachable | set | 28 | 0 |
| `dispatch-gate` | untested | reachable | set | 28 | 0 |
| `document-ingest-guard` | untested | reachable | set | 43 | 0 |
| `eas-validation-gate` | untested | reachable | set | 40 | 0 |
| `edit-lock-pre-tool` | untested | reachable | set | 174 | 0 |
| `goal-stop-gate` | untested | reachable | set | 40 | 0 |
| `orchestrator-skill-invocation-gate` | untested | reachable | disp | 28 | 0 |
| `project-docs-convention` | untested | reachable | set | 174 | 0 |
| `quality-duplicates` | untested | reachable | set | 40 | 0 |
| `session-quality-close-gate` | untested | reachable | set | 40 | 0 |
| `task-completed` | untested | reachable | set | 0 | 0 |
| `task-created` | untested | reachable | set | 0 | 0 |
| `teammate-idle` | untested | reachable | set | 0 | 0 |

*`vía`: `disp` = llega por `bash-hot-path-dispatcher.sh`; `set` = nombrado en el
settings generado; `prof` = sólo por perfil de seguridad / registry.*


---

## 9. Correcciones del lote 2 (2026-08-15, posteriores a la primera pasada)

Tres cosas que di por buenas y no lo eran. Las tres cambian números.

### 9.1 `exit 2` no significa lo mismo en todos los eventos — 11 gates reclasificados

Mi cuadrante "puede bloquear" miraba si existía el camino, no **dónde corre el hook**.
En `PostToolUse` la herramienta **ya corrió**: el mensaje vuelve al modelo, informa,
no previene. Lo mismo con `Stop`, `TaskCreated`, `TeammateIdle`.

Once de los 66 tienen camino de bloqueo y corren sólo en eventos que no previenen:

| gate | evento | bloqueos |
|---|---|---:|
| `subagent-budget-enforcer` | PostToolUse | **48** |
| `confidence-gate` | PostToolUse | 0 |
| `confidentiality-enforcer` | PostToolUse | 0 |
| `content-policy` | PostToolUse | 0 |
| `dequeue-notify` | PostToolUse | 0 |
| `eas-validation-gate` | Stop | 0 |
| `goal-stop-gate` | Stop | 0 |
| `quality-duplicates` | Stop | 0 |
| `session-quality-close-gate` | Stop | 0 |
| `task-created` | TaskCreated | 0 |
| `teammate-idle` | TeammateIdle | 0 |

**`subagent-budget-enforcer` era uno de mis 3 `live`.** Tiene 48 `exit 2` reales, pero
ninguno previno una llamada: todos llegaron después. `live` baja de 3 a 2
(`lethal-trifecta-gate` y `protected-config-write-guard`, ambos PreToolUse).

Lo comprobé sin buscarlo: **este gate me bloqueó dos veces durante la auditoría**, a
los 51 y 52 tool calls. Las dos veces la herramienta ya había corrido y el archivo ya
estaba modificado. Es la demostración empírica de la distinción.

### 9.2 `exit 2` no es el único camino de bloqueo

`hooks/secret-detector.sh:181` bloquea emitiendo `permissionDecision: "block"` y
saliendo **0**. Mi `BLOCK_RE` —copiada de `audit_gate_registration.py`— exigía comilla
antes de `permissionDecision` y sólo aceptaba `deny`, así que no lo veía. Corregida.

Alcance real, medido: `secret-detector` es **el único** hook del repo que usa esa
forma, y **no está entre los 66** — el censo lo clasifica `ambiguo` por el token
"detector" del nombre. Los dos hooks de los 66 que tocan `permissionDecision`
(`agent-bash-cwd-enforcer`, `pending-truth-staleness-gate`) emiten `"allow"`.

**Ninguno de los 22 veredictos de teatro cambia por esto.** Pero confirma que el
denominador está mal armado: un bloqueador real queda fuera de la clase `gate` porque
se llama "-detector". Es la misma deuda de §7.4, desde el otro lado.

### 9.3 "No cableado" es hipótesis, no veredicto

El lote 2 encontró una quinta superficie de ejecución que ningún censo enumera.
Consecuencia para este informe: **el cableado no es insumo de mi clasificación de
`can_block`** —ésa se lee del código fuente— así que los 22 de teatro se sostienen.
Pero **la población de 66 es un piso**: puede haber gates que el censo da por no
cableados y que algo ejecuta.

Lo que sí pude verificar: los 3 "no cableados" del censo (`agent-quota-redirect`,
`pre-commit-gate`, `valkey-ensure`) tienen **0 filas** en `hook-timing.jsonl`. Y
`resource-check`/`auto-verify` tampoco aparecen ahí — su evidencia de ejecución sale
de otros archivos (`hook-health.jsonl`, `so-vitals.jsonl`, `tool-sequences.jsonl`), no
de la telemetría que usé. No contradice al lote 2: mide otra cosa.

### 9.4 El colchón de allowlist — no nos contradecimos, medimos objetos distintos

El coordinador verificó que `.claude/settings.json` menciona 155 hooks y registra 155
dentro de `hooks{}`, sin fantasmas. **Lo confirmo**: contar las entradas de `hooks{}`
da exactamente 155.

Mi "185 entradas, 152 ya cableadas" **no era sobre `settings.json`**: es lo que
`audit_gate_registration.py` reporta sobre el allowlist de
`scripts/check_hook_registration.py`, que es otro artefacto. Las dos afirmaciones son
verdaderas a la vez. Retiro la mía como evidencia de colchón en el registro —
sigue en pie sólo como observación sobre ese allowlist, que es donde la medí.
