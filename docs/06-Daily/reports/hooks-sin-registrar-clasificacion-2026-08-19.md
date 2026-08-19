# Los hooks sin registrar: qué son, por destino

**Fecha:** 2026-08-19
**Alcance:** `hooks/*.sh` del repo, contra `.claude/settings.json` y todas las
demás rutas de proyección.
**Evidencia ejecutable:** `scripts/hook_surface_classifier.py`
**Prueba pareada:** `tests/red_team/portability/test_hook_surface_classifier.py` (11 tests)

```bash
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 .venv/bin/python scripts/hook_surface_classifier.py
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 .venv/bin/python scripts/hook_surface_classifier.py --json
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 .venv/bin/python scripts/hook_surface_classifier.py --bucket omitted_reason
```

Exit `0` sin hallazgos, `1` con hallazgos, `2` error. Read-only: no escribe
nada, no toca `.cognitive-os/metrics/`.

## El número, recontado

| medición | valor | comando |
|---|---|---|
| `.sh` a cualquier profundidad bajo `hooks/` | 291 | `find hooks -name '*.sh' \| wc -l` |
| `hooks/_lib/*.sh` (librerías sourceadas, **no son hooks**) | 34 | `find hooks/_lib -name '*.sh' \| wc -l` |
| `hooks/_archived/` (3 archivos, todos `.bak`, ningún `.sh`) | 0 | `find hooks/_archived -name '*.sh' \| wc -l` |
| `hooks/*.sh` de primer nivel | **257** | `find hooks -maxdepth 1 -name '*.sh' \| wc -l` |
| ídem, únicos tras `readlink -f` | 255 | 2 symlinks alias |
| registrados en `.claude/settings.json` | **154** | 162 entradas de hook |
| **sin registrar** | **103** | |

Los 2 alias son `reaper-heartbeat.sh` → `reaper-daemon-launcher.sh` y
`cos-executor-heartbeat.sh` → `cos-executor-daemon-launcher.sh`.

Los `.disabled` (`example-http-callback.sh.disabled`,
`example-prompt-hook.sh.disabled`) no entran: no terminan en `.sh`.

## Clasificación por destino

```
bucket                count
---------------------------
registered              154
adr311_dispatch          27
profile_gated             9
security_profile         14
other_harness             0
omitted_reason           53
delegated                 0
unclassified              0
---------------------------
total                   257
```

Un hook puede caer en varios; la tabla usa el primero por precedencia. Los
solapamientos, sobre los 103 sin registrar: `omitted_reason` 102,
`security_profile` 46, `profile_gated` 36, `adr311_dispatch` 27,
`delegated` 15, `other_harness` 1.

### Qué significa cada uno

- **`adr311_dispatch` (27)** — los despacha `hooks/bash-hot-path-dispatcher.sh`,
  que sí está registrado. Corren sin entrada propia en `settings.json`,
  condicionados a la forma del comando.
- **`profile_gated` (9)** — están en el bloque `full` del driver de Claude Code
  o en el perfil `full` de `manifests/harness-hook-projection-policy.yaml`. El
  perfil activo es `default` → `maintainer`, así que hoy no corren.
- **`security_profile` (14)** — los proyecta
  `templates/security-profiles/{standard,paranoid}.json`, no `settings.json`.
- **`other_harness` (0)** — **cero**. Ver correcciones.
- **`omitted_reason` (53)** — omitidos con motivo escrito en al menos uno de los
  tres registros de abajo.
- **`unclassified` (0)** — ninguno.

### Alcanzabilidad con la configuración que está puesta hoy

| | |
|---|---|
| corren con la config activa | **181** (settings.json + dispatcher ADR-311) |
| latentes: necesitan otro perfil | **76** (`full` / `standard` / `paranoid`, o apagados a propósito) |
| sin destino alguno | **0** |

Contar los 76 latentes como superficie viva es cómo 181 hooks que corren se
convierten en 257 y la superficie parece justificada. Van separados a propósito.

## Los tres registros que ya contestan la pregunta

| archivo | entradas |
|---|---|
| `hooks/_lib/registration-allowlist.txt` | 185 |
| `manifests/hook-registration-classification.yaml` | 109 |
| `tests/contracts/EXCLUDED_HOOKS.txt` | 125 |

72 de los sin registrar figuran en los tres. **102 de 103 figuran en al menos
uno.** El único que no figura en ninguno es `conflict-marker-guard.sh`, y no es
superficie muerta: llega por cuatro caminos (dispatcher ADR-311, perfil `full`,
perfiles de seguridad, `scripts/apply-efficiency-profile.sh`). Lo que incumple
es la línea de contrato del propio manifiesto: *"Every unregistered top-level
hook must appear here with status, rationale, and next_action"*.

### El ratchet tiene 102 asientos libres

`registration-allowlist.txt` dice en su encabezado que la lista **sólo puede
achicarse** a medida que los hooks se cablean. Medido:

- 83 entradas vivas (hook existe y no está registrado)
- **98 entradas de hooks que YA están registrados** — nunca se sacaron
- **4 entradas de hooks que no existen en disco**

Los 4 inexistentes, verificados con `readlink -f` y `find` (no con un check
ingenuo): `agent-work-tracker.sh` y `wiring-check.sh` sólo viven en
`archive/primitive-surface/hooks/`; `prompt-quality.sh` vive en
`packages/prompt-quality-gate/hooks/` pero no está symlinkeado a `hooks/`;
`test-baseline-diff.sh` no aparece en ningún lado del repo.

Un supresor que no suprime nada es un bug: 102 de 185 entradas de este ratchet
no están conteniendo nada, y el gate igual informa "intencionalmente sin
registrar".

## Lista nominal: los 53 con destino cero

Sin registrar, **sin declarar en `cognitive-os.yaml`**, fuera del dispatcher,
sin proyección de perfil. Su único vínculo con el sistema es una entrada de
registro que dice que están apagados. Es la respuesta honesta a "¿cuáles no van
a ninguna parte?".

```
adr-detector.sh                      agent-bus-monitor.sh
agent-output-verifier.sh             agent-quota-advisor.sh
agent-quota-redirect.sh              agent-qwen-bridge.sh
agnix-lint.sh                        background-agent-reminder.sh
clarification-interceptor.sh         code-review-on-commit.sh
cognitive-os-health.sh               completeness-check-llm.sh
confidence-gate-llm.sh               contextual-rule-loader.sh
conversation-capture.sh              cos-executor-heartbeat.sh
dry-run-preview.sh                   ecosystem-check.sh
engram-auto-import.sh                engram-auto-sync.sh
global-verify.sh                     idle-service-cleanup.sh
infra-intent-detector.sh             jupyter-sandbox.sh
memu-sync.sh                         metrics-calibrator-trigger.sh
metrics-rotation.sh                  mlflow-sync.sh
notify.sh                            orchestrator-mode-detect.sh
package-sync.sh                      pattern-check.sh
pre-cleanup-snapshot.sh              pre-commit-gate.sh
reaper-heartbeat.sh                  recap-sync.sh
registration-check.sh                resource-check.sh
secret-audit-pre-commit.sh           session-end-cleanup.sh
session-hygiene.sh                   session-knowledge-extractor.sh
session-state-save.sh                singularity-check.sh
sync-to-repo.sh                      task-bridge-notify.sh
task-panel-sync.sh                   telemetry-budget-violator-detect.sh
tool-discovery-trigger.sh            tool-loop-detector.sh
usage-health-check.sh                valkey-ensure.sh
worktree-submodule-fix.sh
```

Regenerar:

```bash
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 .venv/bin/python scripts/hook_surface_classifier.py --bucket omitted_reason
```

Dos de esos 53 tienen un ADR que los mandó y ninguna ruta de ejecución:
`secret-audit-pre-commit.sh` (ADR-215) y `telemetry-budget-violator-detect.sh`
(ADR-304). `subagent-input-schema-validator.sh` (ADR-038) está en el mismo
estado salvo que los perfiles `standard`/`paranoid` sí lo proyectan.

**Esto no es una lista para podar.** No se borra nada acá. Cada uno de los 53
tiene un motivo escrito y un `next_action` en
`manifests/hook-registration-classification.yaml`; la decisión de cablear,
archivar o dejar es del operador, y la pregunta que la decide es si el
`next_action` sigue siendo cierto.

## Correcciones a las premisas del encargo

1. **"~289 archivos `hooks/*.sh`" — no.** Son 257 de primer nivel (255 únicos).
   El 289 sale de sumar los 34 `hooks/_lib/*.sh`, que son librerías sourceadas
   por otros hooks, no hooks. `_lib` no se registra ni se puede registrar.

2. **"135 restantes" — son 103.** `257 − 154 = 103`.
   `255 + 34 = 289`, `289 − 154 = 135`: el 135 cuenta 34 librerías de shell como
   hooks sin instrumentar. Un `common.sh` no es un hook al que le falte
   telemetría.

3. **"154 scripts sobre 162 entradas" — confirmado.** Verificado contra
   `.claude/settings.json`: 162 entradas, 155 basenames `.sh` distintos, de los
   cuales uno (`scripts/hook-timing-wrapper.sh`) no vive en `hooks/`. Quedan 154.
   Todos los 154 existen en disco.

4. **"proyectado a otro arnés" — el bucket es 0, no un grupo.** De los 103 sin
   registrar, **1** aparece en `.codex/hooks.json` o `.opencode/cos-hooks.json`,
   y ese ya llega por otra vía. Codex proyecta 92 hooks y OpenCode 64, pero son
   básicamente subconjuntos de los que Claude Code ya registra. La hipótesis de
   que una parte de los sin registrar "viven en otro arnés" no se sostiene.

5. **Faltaba una ruta de proyección entera en el encuadre:**
   `templates/security-profiles/{minimal,standard,paranoid}.json` (109/145/159
   hooks). 14 de los sin registrar llegan sólo por ahí. Un mapa que mire
   `settings.json`, el yaml y el dispatcher se pierde ese grupo.

6. **"el grupo sin ninguna de las anteriores ← este es el hallazgo" — está
   vacío.** Cero hooks sin destino. La pregunta "¿qué son esos?" ya tenía
   respuesta escrita en el repo, en tres lugares distintos, antes de este
   informe. El hallazgo no es superficie sin explicar; es que hay **tres
   registros paralelos** contestando lo mismo (185 / 109 / 125 entradas, 72 en
   común) y que uno de ellos tiene 102 asientos libres.

7. **"se midió que 5 hooks disparan sin estar registrados" — son 27.** Los que
   referencia `hooks/bash-hot-path-dispatcher.sh`. Cuántos de esos 27 disparan
   de hecho depende de la forma del comando en cada invocación; el clasificador
   mide alcanzabilidad estructural, no disparos.

8. **`hooks/` no es un symlink**, pero 42 de sus 257 `.sh` sí lo son. El conteo
   está hecho con `readlink -f` y el informe reporta las dos cifras (257 / 255)
   en vez de elegir la que conviene.

9. **No se usó telemetría para clasificar, a propósito.** El encargo tiene razón
   sobre `hook-timing.jsonl` (rotada y muestreada), y la consecuencia es más
   fuerte que "no probar ausencia": esa señal no sirve para *ninguna* dirección
   de este análisis. La clasificación es 100% estructural.

10. **Sobre "instrumentar los 135 para poder medirlos":** además de estar mal
    por el motivo del encargo, es innecesario. 181 de 257 ya corren y 76 están
    apagados por decisión escrita con `next_action`. Instrumentar produciría 76
    series temporales planas en cero y ninguna decisión nueva.
