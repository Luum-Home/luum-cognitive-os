<!-- SCOPE: os-only -->
# Triaje de los 16 hooks observe-only sin `behavior_test`

Fecha: 2026-08-19 · Alcance: los 16 hooks observe-only del hallazgo posterior a `1395537c9`.

## Resumen ejecutivo

- **MERECE TEST: 3** — `control-plane-audit-hourly`, `pending-truth-drift-detector`,
  `skill-drift-detector`. Escritos, con prueba falla-y-pasa (13 tests nuevos).
- **NO AMERITA: 8** — cinco ya tenían un test de comportamiento real fuera de los
  roots que mira el auditor; tres son wrappers de <30 líneas cuya falla es ruidosa.
- **ROTO O MUERTO: 5** — `decision-depth-gate`, `post-git-orphan-notifier`,
  `stash-budget-warn`, `skill-post-execution-analysis`, `teammate-idle`.
  Ninguno recibió test: fijarlos sería congelar el defecto.
- El hallazgo más caro no es la falta de tests: es que **dos de los hooks muertos
  ya tienen suites verdes** (`test_stash_budget_warn.py` 7 pass,
  `test_skill_post_execution_hook.py` 10 pass) sobre hooks que en producción no
  escribieron una sola fila en 176 y 330 invocaciones.
- Contestando al operador: escribir los 16 habría sido cobertura y nada más.
  Once de los 16 no necesitaban test; cinco necesitaban un ticket.

## Correcciones a las premisas del encargo

1. **"19 hooks registrados sin ningún `behavior_test`" está inflado por el
   descubrimiento, no por la ausencia.** Al empezar,
   `TEST_ROOTS = tests/{unit,behavior,contracts,chaos}` —
   `tests/hooks/`, `tests/integration/`, `tests/e2e/`, `tests/audit/` y
   `tests/red_team/` no se escaneaban. Los 16 tienen al menos un test que los
   nombra; cinco tienen suites sustanciales (asserts: 46, 31, 23, 15, 13).
   Comando: `grep -rl -- "<hook>" tests/`.
   **Mientras corría, la sesión padre agregó `hooks` a `TEST_ROOTS`** (diff vivo en
   `scripts/hook_quality_audit.py`). Siguen ciegos `integration`, `e2e`, `audit`,
   `red_team`, que es donde viven los tests de `stash-budget-warn`,
   `skill-post-execution-analysis`, `self-knowledge-refresh`,
   `session-start-worktree-nudge` e `history-rewrite-documented`.

2. **"Los 16 son observe-only" es falso para `teammate-idle`.** Sale con `exit 2`
   para retener al teammate (`hooks/teammate-idle.sh`, dos rutas). Es un hook que
   decide. Da igual en la práctica: **0 filas en 245.527** registros de
   `hook-timing` vivo + 7 rotados; el evento `TeammateIdle` nunca se dispara acá.

3. **El encargo pide escribir en `tests/hooks/`, que al momento de recibirlo era
   invisible para el auditor.** Escribí en `tests/behavior/` — root escaneado
   desde antes y desde después del cambio del padre. Los tres quedaron
   registrados en `manifests/hook-quality.yaml`.

4. **Hipótesis propia refutada, la dejo escrita.** Sospeché que
   `[ -f "$STAMP" ] && last=...` bajo `set -e` cortaba `control-plane-audit-hourly`
   en su primera corrida. Falso: bash exime las AND-list.
   `/bin/bash -c 'set -euo pipefail; [ -f /nope ] && x=1; echo REACHED'` → `REACHED`, rc=0.

5. **El working tree tiene cambios que no son míos** (`hooks/adversarial-review-gate.sh`,
   `hooks/rate-limit-precheck.sh`, `tests/hooks/test_*.py`, `scripts/hook_exercise_audit.py`).
   Corrí `--sync`, así que `manifests/hook-quality.yaml` incorpora también esos tests.

## Tabla de triaje

| Hook | Corridas (vivo+rotados) | Categoría | Motivo |
|---|---|---|---|
| `cos-session-start-projector` | 75 | NO AMERITA | Wrapper de 21 líneas que hace `exec` del proyector; la lógica está en `scripts/cos-session-start-projector` y una rotura propaga exit code a SessionStart, o sea es ruidosa. |
| `session-sanity` | 75 | NO AMERITA | Dos ramas sobre "¿existe `cognitive-os.yaml` o `.cognitive-os/`?"; en este repo la respuesta es siempre sí, así que nunca puede hablar. |
| `session-start-worktree-nudge` | 75 | NO AMERITA | Ya cubierto por `tests/integration/test_session_start_worktree_nudge.py` (7 subprocesos, 13 asserts); el problema es que el auditor no mira ese root. |
| `session-token-aggregator` | 301 | NO AMERITA | Wrapper; su propia cabecera declara la cobertura en `tests/behavior/test_aggregate_session_tokens.py` (21 KB), que existe y es donde vive la lógica. |
| `session-wrapup-trigger` | 330 | NO AMERITA | Ya cubierto por `tests/hooks/test_session_wrapup_trigger.py` (46 asserts) y `tests/integration/test_auto_trigger_honoured.py`; 63 emisiones reales en `auto-trigger-events.jsonl`. |
| `control-plane-audit-hourly` | 301 | **MERECE TEST** | Decide si corre un barrido que llegó a 174 s, y decide en silencio: el exit code es 0 tanto si barrió como si no. |
| `decision-depth-gate` | 176 | **ROTO O MUERTO** | Lee `.tool_result`, campo fantasma en este harness; 176 corridas y su JSONL sigue en 0 bytes desde el 23 de mayo. |
| `history-rewrite-documented` | 74 | NO AMERITA | Vivo y cubierto: 100 filas en su log y `tests/integration/test_history_rewrite_documented_hook.sh`. |
| `pending-truth-drift-detector` | 975 | **MERECE TEST** | El más corrido de la familia; toda su salida es un JSON en stdout que el harness parsea, y tanto "dejó de matchear" como "dejó de ser JSON válido" son invisibles. |
| `pending-truth-verify-weekly` | 301 | NO AMERITA | Su única decisión es un umbral de 7 días cuya consecuencia —correr el verificador de fondo— es idempotente y se autocorrige a la corrida siguiente. |
| `post-git-orphan-notifier` | 8244 | **ROTO O MUERTO** | `SCAN_EXIT=$?` se captura después de `\|\| true`: siempre 0, así que el aviso al operador es código inalcanzable. |
| `self-knowledge-refresh` | 75 | NO AMERITA | Vivo y cubierto: 30 filas de métricas y `tests/integration/test_self_knowledge_refresh.py` (15 asserts). |
| `skill-drift-detector` | 75 | **MERECE TEST** | Detecta mutación de skills contra `REGISTRY.lock`; sale 0 igual si encontró drift, si no encontró, o si el detector explotó. |
| `skill-post-execution-analysis` | 176 | **ROTO O MUERTO** | Necesita un `skill_name` que ningún payload de Agent trae; `skill_store.db` sigue en 0 bytes desde el 6 de mayo. |
| `stash-budget-warn` | 330 | **ROTO O MUERTO** | `grep -c ... \|\| echo "0"` devuelve `"0\n0"`; el guard explota y cae al aviso: dispara "BUDGET EXCEEDED" con cero stashes. |
| `teammate-idle` | 0 | **ROTO O MUERTO** | Cero disparos en 245.527 filas de telemetría; el evento `TeammateIdle` no existe en este harness. |

## Los ROTO O MUERTO, en detalle

### 1. `decision-depth-gate` — lee un campo que el harness no manda

`hooks/decision-depth-gate.sh:31`:

```bash
AGENT_OUTPUT=$(echo "$INPUT" | jq -r '.tool_result // .output // empty' 2>/dev/null)
```

El payload PostToolUse de Claude Code trae `tool_response`. Prueba directa, mismo
payload en las dos formas:

```
=== decision-depth-gate: payload moderno (tool_response) ===
rc=0
--- rows: NOFILE
=== decision-depth-gate: payload legacy (tool_result) ===
WARNING [decision-depth-gate]: Closing a finding by documentation without investigating...
rc=0
--- rows: 7
```

Corroboración en producción: el hook escribe una fila **en las dos ramas** (`pass` y
`shallow_resolution`), y sin embargo `.cognitive-os/metrics/decision-depth-gate.jsonl`
está en `rows=0 size=0 mtime=May 23` tras 176 invocaciones desde el 20 de julio.
`tests/audit/test_payload_field_contracts.py` ya lista campos fantasma de otros
hooks; `hooks/decision-depth-gate.sh` + `.tool_result` no está en esa lista.

**Decisión para el operador:** migrar a `.tool_response` (y decidir si el gate debe
leer el texto del sub-agente o su `<result>`), o desregistrarlo. Hoy paga 763 ms de
p50 por no hacer nada.

### 2. `post-git-orphan-notifier` — el aviso es código inalcanzable

`hooks/post-git-orphan-notifier.sh`:

```bash
SCAN_OUTPUT=$(python3 "$SCANNER" ... 2>/dev/null) || true
SCAN_EXIT=$?
...
if [ "$SCAN_EXIT" -eq 1 ] && [ -n "$SCAN_OUTPUT" ]; then   # nunca
```

`|| true` fija `$?` en 0 antes de que se lo lea. Prueba:

```
$ /bin/bash -c 'OUT=$(bash -c "echo hi; exit 1") || true; E=$?; echo "SCAN_EXIT = $E"'
SCAN_EXIT = 0 (el scanner realmente salió 1)
```

8244 invocaciones, p50 263 ms, máximo 61 s, y lo único que el hook existe para
imprimir no puede imprimirse nunca. El `orphan-notifier.jsonl` que sí tiene
contenido lo escribe `scripts/orphan_commit_scan.py`, no el hook.
Además ya figura en `KNOWN_PHANTOM` por `.tool_response.exit_code`.

**Decisión:** mover `SCAN_EXIT=$?` antes del `|| true` (o usar `if ! SCAN_OUTPUT=$(...)`),
o aceptar que el hook es un lanzador del scanner y borrar el bloque de aviso.

### 3. `stash-budget-warn` — falso positivo en cada prompt

`hooks/stash-budget-warn.sh:44-48`:

```bash
STASH_COUNT=$(git -C "$PROJECT_DIR" stash list 2>/dev/null \
  | grep -c -E 'auto-pre-agent-|auto-checkpoint-' || echo "0")
if [ "$STASH_COUNT" -le "$THRESHOLD" ]; then
```

`grep -c` **imprime `0` y devuelve 1**, así que el `|| echo "0"` agrega un segundo
`0`: `STASH_COUNT` queda en `"0\n0"`. Corrida real del hook contra un repo con
cero stashes (el estado actual: `git stash list | wc -l` → `0`):

```
hooks/stash-budget-warn.sh: line 48: [: 0
0: integer expression expected

╔══════════════════════════════════════════════════════════╗
║  [stash-budget-warn] AUTO-STASH BUDGET EXCEEDED          ║
╠══════════════════════════════════════════════════════════╣
hooks/stash-budget-warn.sh: line 108: printf: 0
0: invalid number
║  Stash count : 0 (threshold: 3)
rc=0
--- metrics dir contents:   (vacío)
```

Tres consecuencias encadenadas: el guard falla y **cae** al aviso; el `printf`
revienta y el `trap 'exit 0' ERR` mata el hook a mitad del cuadro; y como muere
antes, **no escribe el archivo de cooldown ni la fila de métricas** — por eso
`.cognitive-os/metrics/stash-budget.jsonl` no existe pese a 330 corridas, y por
eso el cooldown de 5 minutos nunca entra en vigencia. Dispara en cada prompt.

**Y `tests/integration/test_stash_budget_warn.py` pasa: `7 passed in 4.95s`.**

**Decisión:** `STASH_COUNT=$(... | grep -c -E '...' || true)` y validar numérico.

### 4. `skill-post-execution-analysis` — pide un campo que nadie manda

Necesita `payload.skill_name`, `tool_response.skill_name` o `tool_input.skill`.
El `tool_input` de Agent trae `subagent_type`, `prompt`, `description`. Sin
`SKILL_NAME` el hook sale antes de escribir nada. Evidencia de producción:

```
.cognitive-os/skill_store.db   0 bytes   May 6 18:00     (176 invocaciones desde el 20/7)
docs/06-Daily/reports/skill-analysis-proposals/   No such file or directory
```

**Y `tests/integration/test_skill_post_execution_hook.py` pasa: `10 passed in 2.53s`** —
alimenta payloads sintéticos que sí traen `skill_name`.

**Decisión:** derivar el nombre de skill de lo que el harness sí manda
(`tool_input.subagent_type` / el skill invocado), o desregistrar el hook.

### 5. `teammate-idle` — el evento no existe

0 filas en 245.527 registros de `hook-timing` (vivo + 7 rotados, 2026-07-18 a
2026-08-19). Ningún otro de los 16 baja de 74. Además **no es observe-only**: tiene
dos `exit 2`. Está registrado en `.claude/settings.json` sobre `TeammateIdle`, y
`scripts/hook_quality_audit.py` clasifica ese evento como `cos_owned`, o sea que su
disparo depende de un runtime propio del SO, no del harness.

**Decisión:** o hay un lanzador de `TeammateIdle` que nunca se conectó, o el hook y
su registro son restos. No es un test lo que falta.

## Otros hallazgos: cabeceras que no dicen la verdad

Ninguno bloquea, todos desorientan a quien lea el archivo antes de tocarlo.

| Hook | Dice | Es |
|---|---|---|
| `skill-drift-detector` | `Budget: <50ms on warm mtime cache` | p50 284 ms medido |
| `skill-drift-detector` | `Never blocks unless COS_SKILL_DRIFT_POLICY=block` | el wrapper cierra con `\|\| true` y `exit 0`: `block` no puede bloquear |
| `session-start-worktree-nudge` | `p95 latency target: <30ms` | p50 288 ms medido |
| `session-token-aggregator` | `Async-safe: runs in the background` | corre sincrónico; máximo observado 896.380 ms (14,9 min) en un hook Stop |
| `pending-truth-drift-detector` | `STAGING: not yet deployed to hooks/` | desplegado, registrado, 975 corridas |
| `pending-truth-verify-weekly` | `STAGING: not yet deployed to hooks/` | desplegado, registrado, 301 corridas |
| `session-sanity` | `@on-demand: invoke manually` | registrado en `SessionStart`, 75 corridas automáticas |

Las latencias declaradas se miden con el wrapper de timing incluido, así que parte
de esos 280 ms es arranque de bash+python; aun así el número declarado es de otro
orden y nadie lo revisó desde que se escribió.

## Los tests que escribí

Tres archivos en `tests/behavior/`, 13 tests. Cada uno ejercita el hook por
subproceso con payload realista y afirma sobre salida y efectos en disco.

### `tests/behavior/test_control_plane_audit_hourly_cooldown.py` (4 tests)

Proyecto temporal cuyo `hooks/control-plane-audit.sh` es un stub que registra su
propia invocación y su entorno. Se afirma la decisión, no la existencia.

**Fallando** (mutante 1: guard de cooldown removido, `if false; then`):

```
PASS test_first_stop_ever_runs_the_sweep_and_stamps_the_clock
FAIL test_second_stop_inside_the_window_does_not_re_sweep: the cooldown must suppress the second sweep, not merely delay it
PASS test_stop_after_the_window_sweeps_again
PASS test_unreadable_stamp_is_treated_as_never_swept
exit=1
```

**Fallando** (mutante 2: `if [ -f "$STAMP" ]`, el barrido se retira para siempre):

```
PASS test_first_stop_ever_runs_the_sweep_and_stamps_the_clock
PASS test_second_stop_inside_the_window_does_not_re_sweep
FAIL test_stop_after_the_window_sweeps_again: a stamp older than the cooldown must not keep the sweep retired
FAIL test_unreadable_stamp_is_treated_as_never_swept: an empty stamp must not be read as 'swept just now'
exit=1
```

**Pasando** (hook intacto):

```
PASS test_first_stop_ever_runs_the_sweep_and_stamps_the_clock
PASS test_second_stop_inside_the_window_does_not_re_sweep
PASS test_stop_after_the_window_sweeps_again
PASS test_unreadable_stamp_is_treated_as_never_swept
exit=0
```

### `tests/behavior/test_pending_truth_drift_detector_nudge.py` (5 tests)

Ledger sintético con un ítem abierto y uno `verified-done` sobre el mismo archivo.

**Fallando** (mutante A: filtro de ítems cerrados removido):

```
PASS test_an_unrelated_edit_stays_silent
FAIL test_closed_items_never_nudge: verified-done items must not be re-nudged; got: '{"hookSpecificOutput":...
PASS test_editing_a_file_named_by_an_open_item_emits_a_parseable_nudge
PASS test_no_ledger_means_no_output_and_no_failure
FAIL test_only_the_open_item_is_reported_when_both_exist
exit=1
```

**Fallando** (mutante B: emite texto plano en vez del sobre JSON):

```
PASS test_an_unrelated_edit_stays_silent
PASS test_closed_items_never_nudge
FAIL test_editing_a_file_named_by_an_open_item_emits_a_parseable_nudge: JSONDecodeError: Expecting value: line 1 column 1
PASS test_no_ledger_means_no_output_and_no_failure
FAIL test_only_the_open_item_is_reported_when_both_exist: JSONDecodeError: Expecting value: line 1 column 1
exit=1
```

**Pasando** (hook intacto): los 5 `PASS`, `exit=0`.

### `tests/behavior/test_skill_drift_detector_warn_path.py` (4 tests)

`REGISTRY.lock` sintético que fija el sha de un cuerpo conocido; se afirma el aviso
que nombra el skill, la fila de auditoría, el silencio en árbol limpio y el killswitch.

**Fallando** (mutante: guard del lock invertido, el hook se vuelve no-op):

```
FAIL test_a_mutated_skill_is_named_in_the_warning: AssertionError: drift went unreported: ''
FAIL test_a_project_without_a_lock_file_is_a_silent_no_op
PASS test_an_unmodified_skill_produces_no_warning
PASS test_killswitch_silences_a_real_drift
exit=1
```

**Pasando** (hook intacto): los 4 `PASS`, `exit=0`.

Honestidad sobre este archivo: un tercer mutante que borra el chequeo de
`COS_DISABLE_SKILL_DRIFT_DETECTOR` del wrapper **no** hace fallar el test, porque
`cos_lib/skill_drift_detector.main()` chequea la misma variable. El test afirma el
contrato (el killswitch es total), que sobrevive a que se caiga una de las dos
implementaciones. Lo dejo dicho en vez de presentarlo como caza.

### Verificación posterior

```
$ .venv/bin/python3 -m pytest tests/behavior/test_control_plane_audit_hourly_cooldown.py \
    tests/behavior/test_pending_truth_drift_detector_nudge.py \
    tests/behavior/test_skill_drift_detector_warn_path.py -q
13 passed in 2.71s

$ COS_ALLOW_PROTECTED_CONFIG_WRITE=1 .venv/bin/python3 scripts/hook_quality_audit.py --sync
hook-quality: wrote manifests/hook-quality.yaml

$ .venv/bin/python3 scripts/hook_quality_audit.py --check
hook-quality: OK (200 hooks, 200 syntax checks)
```

Los tres quedaron registrados en `manifests/hook-quality.yaml`:

```
control-plane-audit-hourly    ['tests/behavior/test_control_plane_audit_hourly_cooldown.py']
pending-truth-drift-detector  ['tests/behavior/test_pending_truth_drift_detector_nudge.py']
skill-drift-detector          ['tests/behavior/test_skill_drift_detector_warn_path.py']
```

## Lo que NO hice y por qué

- **No escribí 13 de los 16 tests.** Ocho no ameritan (cinco ya tienen suite real,
  tres son wrappers ruidosos al romperse) y cinco están rotos: un test sobre ellos
  fijaría el defecto. `stash-budget-warn` y `skill-post-execution-analysis` son la
  demostración de a dónde lleva eso — ya tienen suites verdes sobre hooks muertos.
- **No arreglé los cinco hooks rotos.** El encargo es triar, y cuatro de los cinco
  arreglos son decisiones de producto, no de código: si `decision-depth-gate` debe
  leer el texto del sub-agente o su `<result>`; de dónde saca
  `skill-post-execution-analysis` el nombre del skill; si `teammate-idle` espera un
  lanzador que falta o es resto. Sólo `post-git-orphan-notifier` y
  `stash-budget-warn` tienen un arreglo mecánico de una línea cada uno.
- **No toqué ningún hook.** `git status --porcelain` sobre `hooks/` sólo muestra los
  dos archivos de la sesión padre.
- **No moví baselines ni `REQUIRED_BEHAVIOR_COVERAGE`.** El auditor ya daba `OK`
  antes y después; los tres tests nuevos no lo apagan, lo alimentan.
- **No escribí en `tests/hooks/`** como pedía el encargo: ver corrección 3.
- **No commiteé nada.**
