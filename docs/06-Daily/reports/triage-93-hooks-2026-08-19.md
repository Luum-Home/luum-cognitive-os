<!-- SCOPE: os-only -->
# Triage de los hooks de "BORRAR TRAS DECISIÓN" — qué se rompe si se sacan

> Fecha: 2026-08-19 · Alcance: los **24 hooks** que
> `docs/06-Daily/reports/lista-de-poda-2026-08-19.md` clasificó como
> BORRAR TRAS DECISIÓN. **No se borró, ni se commiteó, ni se modificó nada.**
> El único archivo escrito es éste.

## Resumen ejecutivo

- Cubiertos **24 de 24**. **Sin cubrir: 0.** (El encargo hablaba de 46 hooks; el
  censo tiene 24 — ver correcciones.)
- **CONSERVAR 7 · ARREGLAR 6 · BORRAR 5 · NO PUEDO DECIDIRLO 6.**
- **Ninguno de los 24 corre hoy**: 0 filas en 273.382 de `hook-timing` (vivo + 9
  rotados) y 0 en 90.962 de `hook-health`. Verificado con control positivo
  (`protected-config-write-guard` 12.098, `bash-hot-path-dispatcher` 9.787,
  `destructive-git-blocker` 1.121 en `hook-health`).
- **Ninguno es hijo del dispatcher.** Los 29 hijos de `_run_gate` están listados
  en `hooks/bash-hot-path-dispatcher.sh:128-182` y **no se solapan** con estos 24.
- **Fricción runtime eliminada por borrar los 24: cero.** Ninguno interrumpe,
  ninguno corre por tool call. Lo único que cuesta mantenerlos son **~6 asientos
  de manifest y 2-10 archivos de test por hook**.
- **El hallazgo que cambia el veredicto: 5 de los 24 SÍ están registrados** — en
  `templates/security-profiles/{minimal,standard,paranoid}.json`. Es un octavo
  mecanismo de registro que ni el censo ni el encargo listaban.
- **Tres motivos escritos son falsos** (`notify`, `infra-intent-detector`,
  `telemetry-budget-violator-detect`): el manifest nombra un consumidor que no
  existe en el código. Esos no sobran: están rotos.

## Correcciones a las premisas del encargo

1. **"Vos tomás las 46 de tipo `hooks`" — son 24.** El censo dice literalmente
   "BORRAR TRAS DECISIÓN: 93 (24 hooks + 52 skills + 17 rules)"
   (`lista-de-poda-2026-08-19.md:13`) y la tabla de la sección
   `### 24 hooks` tiene 24 filas. 24+52+17 = 93. **No hay 46 hooks; el reparto
   cierra sin invadir.** Cubrí los 24.

2. **La premisa "sin vía de ejecución" es falsa para 5 de los 24.** Están
   cableados en los perfiles de seguridad que el repo shippea:

   | Hook | Perfil(es) | Evento |
   |---|---|---|
   | `cosd-intent-submit.sh` | minimal + standard + paranoid | `PreToolUse` / Bash |
   | `subagent-input-schema-validator.sh` | standard + paranoid | `PreToolUse` / Agent |
   | `guardrails-validator.sh` | paranoid | — |
   | `parry-scan.sh` | paranoid | — |
   | `semgrep-scan.sh` | paranoid | — |

   `scripts/set-security-profile.sh:87` **copia el JSON del perfil encima de
   `.claude/settings.json`**. O sea: el día que alguien corre
   `set-security-profile standard`, `cosd-intent-submit.sh` empieza a correr en
   **cada llamada a Bash**. Borrarlo hoy no rompe nada; rompe el día que se
   aplique el perfil, que es la peor forma de romperse.

3. **`.claude/settings.json` en vivo (162 comandos de hook) diverge de
   `templates/security-profiles/standard.json`.** Los dos hooks que standard
   registra no están en el settings vivo. La divergencia es un hecho medido, no
   una hipótesis: `grep -c 'subagent-input-schema-validator\|cosd-intent-submit'
   .claude/settings.json` → `0`.

4. **`scripts/hook_exercise_audit.py` NO puede contestar la pregunta 2 para estos
   24.** Su denominador son los **200 hooks registrados en `cognitive-os.yaml`
   (harness.hooks)** — ninguno de los 24 entra. Corrida limpia:
   `EXERCISED 181 · NAMED_ONLY 2 · UNCLASSIFIABLE 12 · NO_TEST 5` sobre 200.
   El encargo lo daba como el instrumento que separa "ejercita" de "nombra"; para
   esta población no aplica. Lo resolví a mano leyendo los tests.

5. **Contar `grep -c "<nombre>" .claude/settings.json` da falsos positivos.**
   `notify` devuelve 1 y es `dequeue-notify.sh`. Mismo problema con
   `parry-scan`/`semgrep-scan` contra `security_red_team.py`, que solo los
   **espera en una lista**, no los invoca. Todo lo de abajo usa el nombre
   completo con `.sh` y descarta las coincidencias por substring.

6. **La telemetría relevante no es solo `hook-timing.jsonl`.** Los hijos del
   dispatcher no pasan por el wrapper: `destructive-git-blocker` da **0** en
   `hook-timing` (273.382 filas) y **1.121** en `hook-health`. Si hubiera contado
   solo el primero, lo habría declarado muerto — que es exactamente el falso
   negativo que el encargo pedía evitar. Los 24 dan 0 en **las dos** fuentes.

## Tabla, ordenada por fricción eliminada

La fricción runtime de los 24 es **cero** (ninguno corre). Así que el orden real
es *riesgo de romper algo al borrar*, de mayor a menor: primero lo que tiene vía
de ejecución latente, después lo que tiene motivo escrito falso, después lo que
solo ocupa asientos.

| # | Hook | ¿Corre hoy? | Qué se rompe exactamente | Motivo escrito | Veredicto |
|---|---|---|---|---|---|
| 1 | `cosd-intent-submit.sh` | No (0/273.382, 0/90.962) | Los **3** perfiles de seguridad lo registran en `PreToolUse:Bash`. Aplicar cualquiera con el archivo borrado deja un hook inexistente **en el camino caliente de Bash**. `manifests/script-exposure-dispositions.yaml:307` lo rutea. | `manual_trigger` — "no lifecycle event payload can supply its intent arguments **yet**" | **CONSERVAR** |
| 2 | `subagent-input-schema-validator.sh` | No | standard + paranoid lo registran en `PreToolUse:Agent`. Tiene test propio que lo **ejecuta** (`tests/hooks/test_subagent_input_schema_validator.py`). Se pierde la validación de `INPUT SCHEMA` de sub-agentes (ADR-038 Wave 2). | `conditional_opt_in` — "promote to standard after one sprint of observation" | **CONSERVAR** |
| 3 | `semgrep-scan.sh` | No | Perfil paranoid + `packages/ecosystem-tools/rules/ecosystem-tools.md:63` + `packages/ecosystem-tools/skills/semgrep-scan/SKILL.md:112` ("runs automatically after sdd-apply"). Borrarlo deja skill y rule prometiendo un hook ausente. | `conditional_opt_in` — requiere Semgrep | **CONSERVAR** |
| 4 | `guardrails-validator.sh` | No | Perfil paranoid + `cognitive-os.yaml:446` (NeMo migrado a pip in-process) + test de caos que lo ejercita. | `conditional_opt_in` — requiere `GUARDRAILS_ENABLED` | **CONSERVAR** |
| 5 | `parry-scan.sh` | No | Perfil paranoid + `packages/ecosystem-tools/rules/ecosystem-tools.md:76`. | `conditional_opt_in` — requiere Parry | **CONSERVAR** |
| 6 | `pre-commit-gate.sh` | No | **Footgun activo:** `scripts/install-pre-commit.sh:11` symlinkea este archivo (7.943 B) **encima de `.git/hooks/pre-commit`**, que hoy es un archivo regular de 10.062 B con gates que el hook no tiene (términos de proyecto, `check_absolute_paths.py`, ADR-208). Correr el instalador documentado hoy **degrada** el gate que sí corre. 10 archivos de test lo nombran; `cos_lib/singularity.py:474` lee un payload que dice escribir. | `git_or_manual` — "installed through git hooks" | **ARREGLAR** |
| 7 | `notify.sh` | No | El motivo dice "es llamado por otros flujos": **cero llamadores** en todo el repo (las coincidencias son `dequeue-notify.sh` y `task-bridge-notify.sh`, otros archivos). `tests/red_team/portability/test_notify.py` lo **ejecuta** con `subprocess.run(["bash", ARTIFACT])` → borrarlo rompe un test real, no de inventario. 8 manifests, 9 archivos de test, 3 asientos en cada ratchet. | `manual_trigger` — "called by other flows" · **falso** | **ARREGLAR** |
| 8 | `infra-intent-detector.sh` | No | El motivo dice "consumed by agent-prelaunch": **ningún hook lo invoca**. Lo único que lo nombra en código es `cos_lib/capability_levels.py:45`, que lo mete en la lista de auto-disable de nivel 5 — una lista que apaga algo que nadie prende. `cognitive-os.yaml:571` lo repite. 7 archivos de test. | `internal_helper` — "consumed by agent-prelaunch" · **falso** | **ARREGLAR** |
| 9 | `telemetry-budget-violator-detect.sh` | No | El motivo dice "invocado por el lane horario de `cos-control-plane-audit`": **ese lane no existe**. `grep -rl telemetry-budget-violator` fuera de docs/reportes devuelve solo `EXCLUDED_HOOKS.txt` y un test de familia. No hay script, ni entrada en `manifests/control-plane-audits.yaml`. ADR-304 lo declara y nada lo corre. | `conditional_opt_in` — lane horario · **falso** | **ARREGLAR** |
| 10 | `pre-cleanup-snapshot.sh` | No | Motivo: "invoke from cleanup skills only". **Ningún skill lo invoca.** Y `rules/RULES-COMPACT.md` §Change Safety promete `[capability-protection] snapshot before cleanup`: la red de seguridad está escrita como norma y no tiene ejecutor. 7 archivos de test, `cos_lib/capability_levels.py`. | `manual_trigger` — "invoke from cleanup skills" · **sin ejecutor** | **ARREGLAR** |
| 11 | `mlflow-sync.sh` | No | `cos_lib/record_completion.py:435` afirma en su docstring que *"Stop-time `mlflow-sync.sh` remains the default"* — para un hook que no está registrado en ningún evento `Stop`. Claim falso adentro de la librería, no del manifest. 6 archivos de test. | `conditional_opt_in` — requiere MLflow | **ARREGLAR** |
| 12 | `conversation-capture.sh` | No | Dos hooks declaran su orden **contra** él en el header: `hooks/session-knowledge-extractor.sh:4` ("después de conversation-capture.sh") y `packages/engram-sync/hooks/memu-sync.sh:4`. Contratos de orden apuntando a un hook que nadie corre. `cos_lib/anchored_summarizer.py` lo nombra. | `future` — contrato de privacidad/retención pendiente | **ARREGLAR** |
| 13 | `cognitive-os-health.sh` | No | `manifests/script-exposure-dispositions.yaml:432` **rutea** una exposición de operador a él (`route: hooks/cognitive-os-health.sh, hooks/session-watchdog-launcher.sh`). Son 10.320 B de reporte de salud invocable; borrarlo deja la ruta colgando y al operador sin el comando. | `manual_trigger` — "expose via /cos-status or doctor" | **CONSERVAR** |
| 14 | `jupyter-sandbox.sh` | No | `packages/ecosystem-tools/skills/jupyter-execute/SKILL.md:121` documenta que con `JUPYTER_SANDBOX=true` **este hook** intercepta la ejecución de Python. Borrarlo convierte esa promesa en mentira. `cognitive-os.yaml:450` declara la migración a pip. | `conditional_opt_in` — perfil jupyter | **CONSERVAR** |
| 15 | `agent-output-verifier.sh` | No | El `next_action` es un compromiso vivo: "no borrar hasta que un contrato estructurado de retorno de Agent provea claims machine-readable". `scripts/cos_agent_flicker_report.py:155` lo referencia. 5 archivos de test, 6 manifests, `silent-failure-allowlist`, `primitive-harness-gap-policy`. Decisión de arquitectura, no de poda. | `demoted` — coherente y explícito | **NO PUEDO DECIDIRLO** |
| 16 | `worktree-submodule-fix.sh` | No | `tests/unit/test_worktree_submodule_fix.py` es un test unitario de su lógica, no de inventario. La función (reparar metadata de submódulos tras operaciones de worktree) es real y ADR-223 usa worktrees por agente. No sé si el problema que arregla sigue ocurriendo. | `manual_trigger` — "mutates git metadata, keep explicit" | **NO PUEDO DECIDIRLO** |
| 17 | `session-end-cleanup.sh` | No | Solo 3 asientos de manifest. El `next_action` dice literalmente "promote to active after operator opt-in via `cognitive-os.yaml`": **es una decisión de operador por construcción**, no algo que un agente pueda cerrar. | `conditional_opt_in` — ADR-238 follow-up | **NO PUEDO DECIDIRLO** |
| 18 | `registration-check.sh` | No | `cos_lib/component_registry.py:4` lo nombra como consumidor del registry junto al skill `/register-component`. Motivo coherente (auditoría manual/CI). Bajo valor, costo nulo; no tengo evidencia para forzar el borrado. | `manual_trigger` — coherente | **NO PUEDO DECIDIRLO** |
| 19 | `session-knowledge-extractor.sh` | No | Solapa con Engram y con `mem_session_summary`, que sí corren. Pero es el único hook que declara el orden `Stop` de la cadena de captura, y `memu-sync.sh` se ordena contra él. Borrarlo sin resolver #12 deja la cadena a medias. | `future` — revisar tras consolidar memoria | **NO PUEDO DECIDIRLO** |
| 20 | `code-review-on-commit.sh` | No | **Nada lo instala.** A diferencia de `pre-commit-gate.sh`, no tiene instalador (`install-pre-commit.sh` no lo menciona), `.git/hooks/pre-commit` no lo llama, ningún perfil lo registra. La capacidad ya la cubren el skill `code-review` y `pr-review`. Se rompen 7 asientos de manifest y 7 archivos de test, **ninguna capacidad**. | `git_or_manual` — camino nunca adoptado | **BORRAR** |
| 21 | `singularity-check.sh` | No | Env-gated a `SINGULARITY_CHECK=true`, que no se setea en ningún lado. `rules/RULES-COMPACT.md` §Infra ya lo dice: `[singularity] MAPE-K(inactive)`. 1.903 B. Se rompen 6 manifests y 2 archivos de test de familia. **Ninguna capacidad.** | `conditional_opt_in` — "keep opt-in" | **BORRAR** |
| 22 | `session-state-save.sh` | No | 1.145 B. Su propio `next_action` dice que **hay que consolidarlo** con el ciclo de sesión antes de proyectarlo — y ese ciclo ya existe y corre (backlog, session files). Es la versión vieja de algo que ya está hecho. Sin llamador, sin perfil, sin skill. | `future` — "consolidate with session lifecycle" | **BORRAR** |
| 23 | `tool-discovery-trigger.sh` | No | 922 B. El skill `tool-discovery` ya cubre el descubrimiento a demanda, que es lo que el propio `next_action` pide ("run scheduled/manual discovery"). El hook es el disparador automático que se decidió no tener. | `future` — descubrimiento manual/programado | **BORRAR** |
| 24 | `secret-audit-pre-commit.sh` | No | **El más barato de los 24.** 485 B de wrapper. Cero llamadores, **cero asiento en `hooks/_lib/registration-allowlist.txt`**, solo 2 manifests y 1 archivo de test. La capacidad real la da `secret-detector.sh`, que corre (10.728 veces según el censo). | `conditional_opt_in` — perfil de seguridad futuro | **BORRAR** |

## Los ARREGLAR: rotos, no sobrantes

Seis hooks que el censo iba a mandar a poda **están rotos, no de más**. En los
tres primeros el manifest nombra un consumidor que no existe: no es documentación
desactualizada, es un supresor que no suprime nada — el `rationale` es lo que
impide que alguien lo mire, y dice algo falso.

1. **`notify.sh`** — `rationale: "called by other flows"`. Cero llamadores.
   Arreglo: o se cablea (hay `cos_lib/notifications.py`), o el status pasa a
   `future`/`demoted` con el motivo real. Hoy el motivo escrito protege al hook de
   ser revisado con un argumento falso.
2. **`infra-intent-detector.sh`** — `rationale: "consumed by agent-prelaunch"`.
   Ningún hook lo invoca. Peor: `cos_lib/capability_levels.py:45` lo apaga en
   nivel 5, o sea que hay código de gobernanza administrando un hook muerto.
3. **`telemetry-budget-violator-detect.sh`** — `rationale`: lane horario de
   `cos-control-plane-audit`. **El lane no existe** (`manifests/control-plane-audits.yaml`
   no lo menciona). ADR-304 lo declaró y nadie lo cableó.
4. **`pre-commit-gate.sh`** — el peor de los seis, porque el daño es al revés:
   correr el instalador que el repo documenta (`scripts/install-pre-commit.sh`)
   **reemplaza** el `.git/hooks/pre-commit` actual (10.062 B, con 3 gates que el
   hook no tiene) por este symlink de 7.943 B. Hay que reconciliar los dos
   archivos **antes** de que alguien siga la documentación.
5. **`pre-cleanup-snapshot.sh`** — `rules/RULES-COMPACT.md` promete
   "snapshot before cleanup" como norma activa; ningún skill de limpieza lo llama.
   La norma está escrita, la red no está puesta.
6. **`mlflow-sync.sh`** — `cos_lib/record_completion.py:435` afirma que es "the
   default" en `Stop`. No está registrado en ningún `Stop`. Claim falso dentro de
   la librería.

## Los que no alcancé a mirar

**Ninguno.** Cubrí los 24 de 24 que el censo clasificó como hooks
BORRAR TRAS DECISIÓN. Lo que **no** cubrí, y queda declarado:

- Los **52 skills** y **17 rules** del mismo lote: son del otro agente.
- Los **77 hooks con actividad cero** del censo completo: solo miré los 24 de
  esta categoría. Los otros 53 quedaron fuera del encargo.
- **No verifiqué por ejecución** que borrar cada hook rompa los tests que lo
  nombran. La máquina está saturada (load ~136) y no corrí la suite. La distinción
  "ejercita vs nombra" la hice leyendo el test: los de
  `tests/red_team/portability/` ejecutan el hook con
  `subprocess.run(["bash", ARTIFACT])` (verificado en `test_notify.py:26-31`), y
  los de `tests/contracts/` leen listas. Es lectura de código, no corrida.
- **No revisé `manifests/primitive-behavior-evidence.yaml` fila por fila.** Conté
  asientos con `grep -rl` sobre `manifests/`; el conteo por archivo es exacto, el
  contenido de cada asiento no lo leí.

## Apéndice: comandos

```bash
# 1. Actividad: vivo + los 9 rotados, en las DOS fuentes
{ cat .cognitive-os/metrics/hook-timing.jsonl;
  gzcat .cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz; } > /tmp/t.jsonl
{ cat .cognitive-os/metrics/hook-health.jsonl;
  gzcat .cognitive-os/metrics/.archive/hook-health-*.jsonl.gz; } > /tmp/h.jsonl
grep -c '"hook":"<nombre>"' /tmp/t.jsonl /tmp/h.jsonl
# control positivo obligatorio:
#   protected-config-write-guard -> 12098 / 0
#   bash-hot-path-dispatcher     ->  9787 / 0
#   destructive-git-blocker      ->     0 / 1121   <-- hijo del dispatcher

# 2. Hijos del dispatcher (los que no dejan telemetría)
grep -n 'hooks/.*\.sh' hooks/bash-hot-path-dispatcher.sh | sed -n '/_run_gate/,$p'

# 3. Registro real: los 8 mecanismos, no 6
grep -c 'CLAUDE_PROJECT_DIR/hooks/' .claude/settings.json          # 162
grep -l '<hook>.sh' templates/security-profiles/*.json             # perfiles
grep -rn '<hook>\.sh' hooks scripts cos_lib lib skills packages templates manifests

# 4. Asientos a limpiar por hook
grep -rl '<hook>\.sh' manifests/ ; grep -rl '<hook>' tests/ --include='*.py'
grep -n '<hook>' tests/contracts/EXCLUDED_HOOKS.txt hooks/_lib/registration-allowlist.txt

# 5. El instrumento que NO sirve para esta población
.venv/bin/python3 scripts/hook_exercise_audit.py --json | \
  .venv/bin/python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["totals"], d["denominator_total"])'
# -> {"EXERCISED":181,"NAMED_ONLY":2,"UNCLASSIFIABLE":12,"NO_TEST":5} 200
#    denominador = hooks REGISTRADOS; ninguno de los 24 entra.
```
