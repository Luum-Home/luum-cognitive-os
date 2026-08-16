# Censo de procesos colgados — 2026-08-15

Pregunta de población: **¿cuántas primitivas de este SO dejan procesos colgados,
y cuáles?** No es la forensia de `cos_primitive_closure_check` (eso lo hace otro
agente); es si esa fuga es única o miembro de una familia.

**Respuesta corta:** es una familia — 5 scripts distintos produjeron raíces
huérfanas en la misma ventana de 5 minutos — pero **no es una fuga acumulativa**.
La población huérfana está en régimen estacionario: ~70-76 procesos vivos con
95% de recambio cada 5 minutos y ningún huérfano que pase de ~8,5 minutos. El
hallazgo que vale no es el número: es que **el SO no puede distinguir un
desprendimiento intencional de una fuga**, porque el mecanismo que existe para
declarar la intención (`_register_bg` + registry) tiene 1 cliente de 29 sitios
y su archivo de estado no existe.

## Evidencia ejecutable

Censo reproducible: `scripts/audit_hanging_processes.py` (nuevo, read-only,
exit 0 sin huérfanos / 1 con huérfanos / 2 error).

```bash
# foto
python3 scripts/audit_hanging_processes.py

# serie: dos muestras separadas, con veredicto churn/accumulating
python3 scripts/audit_hanging_processes.py --snapshot /tmp/orphans-A.json
python3 scripts/audit_hanging_processes.py --compare /tmp/orphans-A.json
```

Lee la tabla de procesos, reconstruye el árbol de padres y clasifica cada
proceso del repo en exactamente una clase. No grepea código para enumerar.

## 1. Qué procesos deja vivos el SO, agrupados por script

Muestra A, `t=1786837419` (`date +%s`), 87 procesos del repo vivos:

| Script | daemon | live-child | orphan-root | orphan-desc |
|---|---|---|---|---|
| `scripts/cos_primitive_closure_check.py` | | | 32 | 4 |
| `scripts/derived_artifact_gate.py` | | | 3 | 9 |
| `scripts/family_conformance_probe.py` | | | 6 | 4 |
| `scripts/docs_reader_audit.py` | | | 3 | 1 |
| `hooks/pre-commit-gate.sh` | | | 2 | 5 |
| `scripts/python_stdin_antipattern_audit.py` | | | 1 | |
| `scripts/aspirational_audit.py` | | | | 1 |
| `scripts/cos_efficiency_primitives.py` | | | | 1 |
| `scripts/cos_lib_rename_codemod.py` | | | | 1 |
| `scripts/generate_adr_index.py` | | | | 1 |
| `scripts/prompt_aggressive_language_audit.py` | | | | 1 |
| `scripts/provenance_scan.py` | | | | 1 |
| `scripts/hook-timing-wrapper.sh` | | 3 | | |
| `hooks/quality-duplicates.sh` + `cos_quality_duplicates.py` | | 4 | | |
| `hooks/bash-hot-path-dispatcher.sh` | | 1 | | |
| `hooks/destructive-rm-blocker.sh` | | 1 | | |
| `scripts/so_session_watchdog.py --daemon` | 1 | | | |

Totales muestra A: **daemon 1, live-child 10, orphan-root 47, orphan-desc 29.**

## 2. La partición en tres clases, y el criterio de cada una

La partición vale más que el total, así que va el criterio explícito:

- **daemon (1).** `scripts/so_session_watchdog.py --daemon --interval 60`,
  `ppid=1`, 1h23m de vida. **`ppid=1` acá NO es evidencia de fuga**: nació
  detached a propósito. Criterio implementado: marcador declarativo en el argv
  (`--daemon` / `--serve` / `daemon-launcher`). Es el único proceso del repo
  que se comporta como demonio y el único cuyo `ppid=1` está justificado.
  Confirmado: el encargo tenía razón en advertirlo — reportarlo como fuga es el
  error espejo del verde barato.
- **live-child (10-24).** Su cadena de ancestros llega a un proceso vivo que no
  es huérfano: en todos los casos el harness (`claude ... --output-format
  stream-json`, PID 35623, 9h35m). Ejemplo de cadena completa:
  `claude(35623) → hook-timing-wrapper.sh Stop(86676) → quality-duplicates.sh(87214)
  → cos_quality_duplicates.py(88952, 91.7% CPU)`. Son hijos legítimos aunque
  lleven 12 minutos: hay un dueño vivo.
- **orphan-root (38-47).** `ppid=1` y sin marcador de demonio: reparentados a
  init porque quien los lanzó murió antes. Ninguno declara intención de
  detachearse.
- **orphan-descendant (29-31).** Todavía tienen padre vivo, pero el tope de su
  cadena es un orphan-root: el árbol entero quedó sin dueño. Contarlos aparte
  importa porque **la fuga se amplifica**: cada `cos_primitive_closure_check.py`
  huérfano estaba corriendo `acc_pipeline.py --brief` → `cos_init.py --harness X`
  → `settings-driver-opencode.sh` → venv python, con hijos al 20-25% de CPU.
  Un huérfano no es un proceso dormido; es la raíz de un árbol de trabajo activo.

## 3. Las dos muestras temporales, y qué cambió

| | Muestra A (`t=1786837419`) | Muestra B (`t=1786837707`, +288 s) |
|---|---|---|
| daemon | 1 | 1 |
| live-child | 10 | 24 |
| orphan-root | 47 | 38 |
| orphan-descendant | 29 | 31 |
| huérfano más viejo | 330 s | 329 s |

Diff de PIDs (`--compare`): `previous=76, current=69, collected=72, new=65,
survived=4`. **Veredicto: churn.** El 95% de la población huérfana se recolectó
en menos de 5 minutos y fue reemplazada por otra.

Esto invierte el diagnóstico. Antes de las dos muestras había una tercera foto
que lo hace evidente: a `t=1786836971` había 28 raíces huérfanas de
`cos_primitive_closure_check.py`; a `t=1786837056` (85 segundos después) quedaba
**una sola** raíz `ppid=1`, el watchdog, y 4 procesos del repo en total.
Desaparecieron solas — no hubo `kill` (nadie lo ejecutó) y el commit log de esos
minutos no toca nada de procesos. Terminaron su trabajo: `.cognitive-os/metrics/
install-timing.jsonl` quedó modificado, que es la salida de la matriz de
instalación que estaban corriendo.

El techo de vida observado es ~330 s en A/B y 505 s (`08:25`) en la foto previa,
así que **no hay un reaper actuando a plazo fijo**: es la duración natural del
trabajo. Consistente con que no exista `.cognitive-os/processes-live.json` ni
`.cognitive-os/metrics/processes.jsonl`, y con que no haya ningún proceso reaper
vivo.

Nota de honestidad sobre las cifras absolutas: en esta ventana corren al menos
dos sesiones de agente concurrentes sobre el mismo checkout, y
`scripts/family_conformance_probe.py` (6 raíces huérfanas) es de la otra sesión.
La magnitud es dependiente de la carga de sesión; lo que no lo es son las
**clases** y la **forma** del defecto.

## 4. Qué primitivas podrían fugar aunque hoy no se las vea

Enumerado por forma, sobre `git ls-files` (8.512 archivos) **sin filtro de
extensión** — el filtro por extensión es exactamente lo que dejó afuera a
`scripts/cos-test-laptop-bg` y `scripts/cos-graphify-build`, dos ejecutables
kebab-case sin extensión que sí spawnean.

**Forma 1 — spawn en background de shell (línea que termina en `&` pelado): 24
sitios de código.**

```bash
git ls-files -z | xargs -0 grep -cE '(^|[^&>0-9])&[[:space:]]*$' | grep -v ':0$' \
  | grep -vE '^(docs|CHANGELOG|\.ai)' | grep -vE '\.(md|json|yaml|yml|txt|lock)'
```

`.githooks/pre-push`, `hooks/_lib/execute-repair.sh`, `hooks/_lib/register-bg.sh`(2),
`hooks/aspirational-audit-weekly.sh`, `hooks/auto-verify.sh`, `hooks/completion-gate.sh`,
`hooks/engram-daemon-launcher.sh`, `hooks/host-tool-doctor.sh`, `hooks/infra-health.sh`(2),
`hooks/pending-truth-verify-weekly.sh`, `hooks/profile-drift-autoapply.sh`,
`hooks/reaper-daemon-launcher.sh`, `hooks/reaper-heartbeat.sh`, `hooks/review-spawner.sh`,
`hooks/self-knowledge-refresh.sh`, `hooks/session-init.sh`(2),
`hooks/session-watchdog-launcher.sh`, `packages/agent-lifecycle/hooks/review-spawner.sh`,
`packages/quality-gates/hooks/completion-gate.sh`, `scripts/chaos/snapshot-concurrent-race.sh`,
`scripts/cos-merge-queue-worker.sh`, **`scripts/cos-test-laptop-bg`**,
`scripts/cos-validation-capsule.sh`, `scripts/setup-git-hooks.sh`.

**Forma 2 — desprendimiento explícito (`nohup` / `setsid` / `start_new_session=True`):**
`cos_lib/claude_executor.py`, `hooks/engram-daemon-launcher.sh`,
`hooks/pending-truth-verify-weekly.sh`, `hooks/self-knowledge-refresh.sh`,
`hooks/session-watchdog-launcher.sh`, `scripts/cos-test-laptop-bg`,
`scripts/cos_daemon.py`, `scripts/family_conformance_probe.py`, `workflows/lib/agent.py`,
`Makefile`.

**Forma 3 — `Popen` fire-and-forget (nunca `.wait()` / `.communicate()` / `.poll()`):**
`scripts/hook_timing_report.py`, `scripts/cos_daemon.py`. Los otros cuatro sitios
`Popen` (`cos_lib/claude_executor.py`, `scripts/cos-graphify-build`,
`scripts/family_conformance_probe.py`, `workflows/lib/agent.py`) sí esperan.

**Forma 4 — `subprocess.run` sin `timeout=`: 25 sitios fuera de tests** (1.193
con tests). Ya está medido por la primitiva existente:
`python3 scripts/cos-subprocess-timeout-audit.py`. Es la forma más numerosa y
la que explica el techo de ~5-8 minutos: un padre que se queda esperando sin
límite es un padre que puede ser matado por timeout de hook, y su hijo sigue.

**Forma 5 — el padre muere por timeout mientras el hijo sigue.** Es la que
produjo lo que se ve: `hooks/pre-commit-gate.sh` aparece a la vez como
`live-child` (invocado por el harness) y como `orphan-root` ×2 con 5 hijos
python. El hook queda sin invocador y sus hijos siguen.

## 5. El patrón común, y dónde se arregla para todas

No comparten invocador ni dispatcher: no hay un `xargs -P` ni un pool común en
el camino de hooks (`grep -nE 'xargs -P|ThreadPoolExecutor' hooks/pre-commit-gate.sh
scripts/cos-ci-local.sh` no devuelve nada relevante). Lo que comparten es que
**ninguno declara que se desprendió**.

El SO ya construyó la solución y la dejó a mitad de camino: **ADR-028 D1.B**
—`hooks/_lib/register-bg.sh` (`_register_bg owner ttl kind cmd...`) +
`cos_lib/process_registry.py` + reaper— existe desde abril. Estado real hoy:

- **1 cliente de 29 sitios de spawn.** Único consumidor de código:
  `hooks/skill-usage-tracker.sh:103`. El resto está documentado como deuda
  diferida en `docs/06-Daily/reports/d1b-clients-todo.md` (creado 2026-04-20,
  «Initial sprint wired the top 5 highest-value background-spawn sites» — la
  tabla de migrados tiene 1 fila).
- **El registry no tiene archivo de estado.** `.cognitive-os/processes-live.json`
  no existe. Sin registro no hay nada que el reaper pueda considerar «manejado».
- **`.cognitive-os/metrics/processes.jsonl` no existe**: cero eventos
  `orphan_detected` desde que se instaló el mecanismo.
- **El reaper está registrado en `.claude/settings.json`** (`reaper-daemon-launcher.sh`,
  SessionStart) y `cognitive-os.yaml` lo declara `reaper.enabled: true`, pero
  **no hay proceso reaper vivo** (`ps -eo pid,ppid,etime,args | grep -i reaper`
  devuelve vacío).

**El único lugar donde se arregla para todas** es el predicado de visibilidad,
`cos_lib/process_registry.py:190` — `detect_orphans(hook_basenames)`. Hoy filtra
así (línea 232):

```python
if any(b in command for b in hook_basenames) and pid not in registered_pids:
```

y `scripts/so-reaper.sh:42` alimenta `hook_basenames` con `ls "$PROJECT_DIR/hooks/"*.sh`.
O sea: **el detector de huérfanos sólo ve hooks `.sh`**. Los 47 orphan-roots de
hoy son `scripts/*.py` — invisibles por construcción. Cambiar ese único predicado
por «el comando referencia la raíz del repo y el PID no está registrado» hace
visibles a los 47 de una sola vez. Es el mismo defecto que describe el encargo:
enumerar por texto (nombre de archivo) una familia definida por comportamiento
(`ppid=1` sin declaración de intención).

Segundo lugar, mismo eje: `scripts/cos-orphan-process-audit.py` (ADR-279) exige
las tres cosas a la vez — `ppid == 1`, edad `> 3600 s`, y que el comando contenga
uno de `SAFE_SCAN_TOKENS = (".cognitive-os", ".codex", "docs/04-Concepts/architecture", ...)`.
Los huérfanos medidos fallan las tres. Corrido ahora mismo:

```bash
python3 scripts/cos-orphan-process-audit.py --no-metric
```

devuelve **1 candidato, y no es del repo**: es el updater Sparkle de ChatGPT
(`~/Library/Caches/com.openai.codex/.../Updater.app`, 34.798 s, `ppid=1`), que
matchea porque su ruta contiene la subcadena `.codex`. Con `--kill`, esa
primitiva le manda SIGTERM/SIGKILL a un proceso ajeno mientras ignora los 47
propios. **Es un falso positivo peligroso, no sólo un falso negativo** —
severidad alta, y lo dejo señalado sin tocar (el arreglo no es de este encargo).

## 6. PIDs a limpiar

**Ninguno requiere intervención manual, y no ejecuté ningún `kill`.**

Justificación: la serie temporal muestra recolección (72 de 76 huérfanos
desaparecieron solos en 288 s; ninguno supera ~8,5 min). Matar PIDs de una
población con 95% de recambio en 5 minutos es actuar sobre una foto vencida.

El único proceso de larga vida con `ppid=1` es **PID 69175 —
`scripts/so_session_watchdog.py --daemon --interval 60`, 1h23m — y es un demonio
legítimo: dejarlo.**

Si el operador quiere la lista vigente en el momento de decidir:

```bash
python3 scripts/audit_hanging_processes.py | python3 -c \
  "import json,sys; print(json.load(sys.stdin)['orphan_pids'])"
```

Lo que sí amerita decisión del operador, en este orden:

1. Ampliar el predicado de `detect_orphans()` (un `if`), para que el SO vea su
   propia familia.
2. Arreglar `SAFE_SCAN_TOKENS` de ADR-279 antes de que alguien corra `--kill`.
3. Retomar la migración D1.B: 28 sitios de spawn sin `_register_bg`.

## Correcciones a las premisas del encargo

- **«30 huérfanos» → falso en ambas direcciones, y la métrica es inestable.**
  Recontado: 28 raíces `ppid=1` en la primera foto (`t=1786836971`), 47 en la
  muestra A (`t=1786837419`), 38 en la B (`t=1786837707`). No es un número: es
  una tasa.
- **«¿se acumulan o se reciclan?» → se reciclan.** El encargo planteó los dos
  diagnósticos como abiertos y con razón. El dato: `collected=72, new=65,
  survived=4` en 288 s. Concluir «fuga acumulativa» desde la foto de 30 habría
  sido incorrecto. Es la corrección más importante de este informe.
- **«es una familia» → confirmado, con matiz.** 5 scripts distintos generaron
  raíces huérfanas en la misma ventana, así que no es un caso aislado. Pero la
  familia no está unida por un invocador común (lo busqué: no hay dispatcher
  compartido), sino por la ausencia de declaración de intención. Y una parte de
  la población —`family_conformance_probe.py`— la genera la sesión concurrente,
  no el SO en reposo.
- **«`ppid=1` sólo significa huérfano si el proceso no nació demonio» →
  confirmado y adoptado como criterio implementado**, no como nota al pie:
  `DAEMON_MARKERS` en `scripts/audit_hanging_processes.py`. El watchdog quedó
  correctamente fuera del conteo de fugas.
- **«enumerá sin filtros de extensión» → verificado con dos casos concretos.**
  `scripts/cos-test-laptop-bg` (spawn en background) y `scripts/cos-graphify-build`
  (`Popen`) no tienen extensión. Un `--include='*.sh'` o `--include='*.py'` los
  pierde.
- **Premisa que no verifiqué y debo declarar:** el encargo pidió no tocar
  `tests/audit/test_family_conformance.py` ni `tests/fixtures/family-probe/`
  porque los trabaja otro agente. No los toqué. Sí verifiqué con `git status` /
  `git log` que `scripts/audit_hanging_processes.py` no existía ni estaba en
  curso, y que `scripts/cos-orphan-process-audit.py` y
  `scripts/cos-subprocess-timeout-audit.py` son código ya commiteado (último
  toque: `785ced2f3`), no trabajo en vuelo de otra sesión.
- **Premisa mía, no del encargo, que sí falló:** asumí que si el SO tenía una
  primitiva de auditoría de huérfanos (ADR-279), medía esta familia. La corrí
  antes de escribir nada y no mide nada de esto. Reinventé el censo a propósito
  recién después de comprobarlo.

## Incidente de concurrencia durante este trabajo (para el operador)

Dos errores propios, ambos por escritores concurrentes sobre el mismo checkout.
Van escritos porque el repo no debe mentir sobre cómo llegó a este estado.

1. **Nombre de archivo compartido en el scratchpad.** Escribí el mensaje de
   commit en `<scratchpad>/msg.txt` y una sesión hermana sobrescribió ese mismo
   path entre mi `cat >` y mi `git commit -F`. El commit salió con el mensaje de
   otro (`docs(research): investigar A2A e interop…`). Lección concreta: los
   archivos del scratchpad de sesión también compiten — el nombre tiene que ser
   único por tarea, no genérico.
2. **`git commit --amend` no respeta el pathspec.** Al corregir el mensaje,
   `--amend` commiteó el **índice entero** y se llevó cinco archivos que otra
   sesión tenía staged (`censo-terminologia-arneses-2026-08-15.md`,
   `familia-rutas-cierre-2026-08-15.md`, `forense-procesos-huerfanos-2026-08-15.md`,
   `scripts/home-path-family-mutation-check.sh`,
   `tests/audit/test_family_probe_no_orphans.py`). Quedaron dentro del commit
   `3506e1481`, que lleva mi mensaje.

**Nada se perdió** — los cinco archivos están íntegros en el árbol y la sesión
dueña commiteó encima (`4488b58ae`). No intenté deshacerlo: para cuando fui a
reparar, HEAD ya era de otra sesión, y reescribir historia sobre la que otro ya
construyó es peor que el problema. `git reset --soft` quedó además bloqueado por
`destructive-git-blocker` (ADR-055b), correctamente.

Vale como dato para la norma de escritores concurrentes: `git commit --only --
<paths>` sí respeta el alcance, **`git commit --amend` no tiene equivalente**.
Bajo sesiones concurrentes, amend es una operación de índice completo y no
debería usarse en un checkout compartido.

## Límite conocido de la medición

`scripts/audit_hanging_processes.py` clasifica por comportamiento, no por
intención: **no puede distinguir un desprendimiento deliberado de una fuga.**
Eso no es un defecto del script — es el estado del sistema. El mecanismo que
existe para declarar intención (`_register_bg` → `processes-live.json`) tiene 1
cliente y registry vacío, así que hoy no hay ningún dato contra el cual
contrastar. Migrar los 28 sitios restantes de D1.B es lo que convierte este
censo de «47 procesos sin dueño» en «N desprendimientos declarados y M fugas».
