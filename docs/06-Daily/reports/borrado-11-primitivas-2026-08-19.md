<!-- SCOPE: os-only -->
# Borrado de las 11 primitivas "BORRAR YA" — qué se fue y qué se frenó

> Fecha: 2026-08-19 · Encargo: ejecutar la lista BORRAR YA de
> `docs/06-Daily/reports/lista-de-poda-2026-08-19.md` (10 skills + 1 hook),
> verificando cada fila antes de tocarla.

## Resumen ejecutivo

- **Borrada: 1 de 11** — `hooks/rate-limit-protection.sh`, con sus 5 asientos.
- **Frenadas: 10 de 11.** Ninguna de las diez pasó la verificación de consumidor.
- El argumento que cerraba las ocho envolturas —"están bajo el freeze"— **es falso**:
  `manifests/external-tool-adoption-freeze.yaml` no menciona ninguna de las ocho
  (`grep -c` → 0 en las ocho), y el freeze gobierna **rutas de commit**, no
  instalación de herramientas.
- Tres de las ocho (`deepeval`, `ragas`, `cognee`) tienen **línea viva y sin comentar
  en `requirements.txt`** y verdict `ADOPT`/`INTEGRATE` con `status: optional` en
  `manifests/external-tools-adoption.yaml`: son dependencias opcionales por decisión
  escrita, no basura.
- `find_spec` es el instrumento equivocado para al menos tres: `promptfoo` es un CLI
  de Node (`install via npm`), `automaker` es una app externa, y `memu`/`jupyter`/
  `phoenix` son servicios de docker/lane pesado. Un `None` ahí no prueba nada.
- El borrado **destapó un asiento falso**: el único proof de comportamiento de
  `rules/rate-limit-protection.md` era el test pareado del shim, o sea de un script
  que no hace nada. Se reemplazó por un proof real contra la implementación viva.

## Correcciones a las premisas del encargo

1. **"Ocho envoltorios congelados por `external-tool-adoption-freeze.yaml`" — no.**
   Verificado uno por uno:
   ```bash
   for t in deepeval promptfoo ragas strands phoenix cognee memu automaker; do
     printf "%-12s freeze=%s\n" "$t" \
       "$(grep -ci "$t" manifests/external-tool-adoption-freeze.yaml)"; done
   ```
   Devuelve `0` para las ocho. Los nombres que sí están bajo el freeze son otros
   (HippoRAG, graphiti, gepa, mempalace, SWE-agent). Además el freeze gatea
   `gated_path_globs` —docs de research y `manifests/external-tools-adoption.yaml`—
   o sea **bloquea documentar adopciones nuevas**, no instalar paquetes; y trae
   `unfreeze_requires` con cuatro condiciones, es decir es **reversible por diseño**.
   El encargo pedía verificar esto explícitamente: no se sostiene.

2. **"`find_spec` → `None` significa herramienta no instalada" — cierto pero
   inaplicable en al menos tres filas.** `requirements.txt:40` dice
   `# promptfoo  # Red teaming + prompt regression (Node.js CLI, install via npm)`:
   ningún `find_spec` de Python lo va a encontrar nunca, esté instalado o no.
   `automaker-bridge` no envuelve un paquete: su `SKILL.md` dice *"Configure
   AutoMaker to use Cognitive OS as its execution brain"* — es una app externa.
   `phoenix` vive en `requirements/dependency-lanes/observability.txt`
   (`arize-phoenix>=4.0`), un lane pesado deliberadamente fuera de `pyproject.toml`,
   y hay un test de auditoría que **exige** que siga afuera.

3. **Tres de las ocho tienen decisión escrita de adoptarlas.**
   `requirements.txt` líneas 20/36/37: `cognee>=0.1`, `deepeval>=1.0`, `ragas>=0.4`,
   sin comentar. Y en `manifests/external-tools-adoption.yaml`: `deepeval` verdict
   `ADOPT`, `ragas` verdict `ADOPT`, `cognee` verdict `INTEGRATE`, las tres con
   `status: optional` y `allowed_surfaces.os_repo: optional`. No están instaladas en
   este `.venv` porque son opcionales, que es exactamente lo que la decisión dice.

4. **`memu` tiene dos decisiones escritas que se contradicen.** El manifest de
   adopción dice verdict `REMOVE`, `allowed_surfaces` todo en `false`, status
   `verify_package_then_cleanup`. Pero `tests/contracts/test_service_sunset_policy.py`
   tiene `test_memu_preserves_historical_review_marker_while_remaining_pip` que
   afirma *"ADR-060 keeps MemU pip-first"* y exige la entrada `memu` en
   `cognitive-os.yaml` con `mode: pip`. Además existen `hooks/memu-sync.sh`,
   `cos_lib/smart_infra.py` con el servicio, y `scripts/cos-bootstrap.sh
   --profile memory`. Es deuda de verdad documental, no una vía libre para borrar.

5. **`browser-task` no es un skill huérfano: es entregable de un ADR aceptado.**
   `docs/02-Decisions/adrs/ADR-288-web-automation-adapter-for-dispatch.md` tiene
   `status: accepted`, lista `skills/browser-task/SKILL.md` entre sus artefactos, y
   documenta `/browser-task` como entrada soportada. `pyproject.toml:41-45` define el
   extra `web-automation` que existe *para* esa ruta. El "equivalente nativo" no
   invalida un ADR aceptado hace poco; lo que correspondería es un ADR que lo
   reemplace, no un `rm`.

6. **El censo original ya lo había advertido y el encargo no lo trasladó.** El propio
   informe fuente dice en su corrección 7 que la telemetría de skills tiene **6 filas
   en total**, y que por eso "este skill nunca se usó" es indecidible. Las diez filas
   de skills de BORRAR YA se apoyan en esa columna de actividad cero.

7. **Premisa de propiedad, verificada y no recordada.** `git status --porcelain`
   sobre los 8 archivos que toqué, antes de tocarlos: vacío. El orquestador tenía
   dirty ~20 hooks en paralelo; ninguno de los míos. `git add` con rutas explícitas.

8. **`destructive-git-blocker` bloquea hoy, confirmado en vivo.** Intenté
   `git worktree add` para medir el baseline del audit contra HEAD y el hook me
   frenó con `exit 2` vía `bash-hot-path-dispatcher.sh`. No es un dato de telemetría:
   me pasó. Cambié de método (comparar findings por nombre) en vez de forzarlo.

## Las cuatro verificaciones, primitiva por primitiva

Leyenda: **D** = ¿la invoca `hooks/bash-hot-path-dispatcher.sh`? · **T** = telemetría
(vivo + 16 rotados `.archive/*.gz`, 24 archivos) · **C** = consumidor real ·
**M** = motivo de omisión escrito.

| # | Primitiva | D | T | C | M | Veredicto |
|---|---|---|---|---|---|---|
| 1 | `skills/browser-task` | no | 0 | **ADR-288 `accepted` + `pyproject.toml` extra `web-automation` + `lib/web_automation_router.route()`** | — | **FRENADA** |
| 2 | `skills/jupyter-execute` | no | 0 | **`cognitive-os.yaml:533` servicio `jupyter` `mode: pip`, `profile: jupyter`; `hooks/jupyter-sandbox.sh`; `cos-bootstrap --profile jupyter`** | adopción `jupyter` = `DEFER`/`heavy_optional` | **FRENADA** |
| 3 | `skills/deepeval-integration` | no | 0 | **`requirements.txt:36` sin comentar** | verdict `ADOPT`, `status: optional` | **FRENADA** |
| 4 | `skills/promptfoo-integration` | no | 0 | — (`find_spec` inaplicable: CLI de Node) | `requirements.txt:40` comentado, sin verdict `REMOVE` | **FRENADA** |
| 5 | `skills/ragas-integration` | no | 0 | **`requirements.txt:37` sin comentar** | verdict `ADOPT`, `status: optional` | **FRENADA** |
| 6 | `skills/strands-evals-integration` | no | 0 | — | `requirements.txt:41` comentado, sin verdict `REMOVE` | **FRENADA** |
| 7 | `skills/phoenix-trace-ui` | no | 0 | **`tests/audit/test_phoenix_license_boundary.py` exige que `skills/phoenix-trace-ui/SKILL.md` exista y declare el límite ELv2** | `arize-phoenix>=4.0` en lane `observability` a propósito | **FRENADA** |
| 8 | `skills/cognee-integration` | no | 0 | **`requirements.txt:20` sin comentar**; `cos-bootstrap --profile memory` | verdict `INTEGRATE`, `status: optional` | **FRENADA** |
| 9 | `skills/memu-context` | no | 0 | **`cognitive-os.yaml` servicio `memu`; `hooks/memu-sync.sh`; `cos_lib/smart_infra.py`; contrato `test_service_sunset_policy.py`** | verdict `REMOVE` **contradicho** por ADR-060 | **FRENADA** |
| 10 | `skills/automaker-bridge` | no | 0 | — (`find_spec` inaplicable: app externa) | sin verdict; `automaker` sí está en el sunset policy | **FRENADA** |
| 11 | `hooks/rate-limit-protection.sh` | **no** (`grep rate-limit hooks/bash-hot-path-dispatcher.sh` → sin match) | **0** en 24 archivos; el sucesor `token-budget-monitor` tiene **206** | **ninguno**: 0 en `.claude/settings.json`, 0 en perfiles, 0 invocadores; todo lo demás apunta al **rule** `.md` | `status: deprecated`, `next_action: "Archive after external caller compatibility window."` | **BORRADA** |

### Por qué la 11 sí pasa

Las cuatro, con el comando:

```bash
grep -n "rate-limit" hooks/bash-hot-path-dispatcher.sh          # sin match
grep -c "rate-limit-protection" .claude/settings.json           # 0
git log -3 --format='%h %ad' --date=short -- hooks/rate-limit-protection.sh  # 2026-04-20
```

El archivo **no hace nada**: es un shim de 14 líneas que imprime un warning de
deprecación y hace `exit 0`. Su reemplazo `hooks/token-budget-monitor.sh` está
registrado y corriendo. La ventana de compatibilidad que su `next_action` pide
esperar lleva **~4 meses** abierta con **cero** invocaciones registradas, y
`hooks/self-install.sh:348` ya mapea la regla al nombre nuevo, así que ninguna
instalación actual puede emitir el viejo.

## Las que NO borré y por qué

Agrupadas por el motivo que las salva, que no es el mismo:

- **Entregable de un ADR aceptado (1):** `browser-task`. Borrarla contradice
  ADR-288 sin un ADR que lo reemplace.
- **Superficie de operador de un servicio configurado (3):** `jupyter-execute`,
  `cognee-integration`, `memu-context`. Los tres servicios están definidos en
  `cognitive-os.yaml` y arrancables por `cos-bootstrap`. Borrar el skill deja el
  servicio sin forma de manejarlo: eso es perder capacidad, no podar.
- **Dependencia opcional con verdict escrito (3):** `deepeval`, `ragas`, `cognee`.
  Línea viva en `requirements.txt` + `ADOPT`/`INTEGRATE`.
- **Postura legal bajo test (1):** `phoenix-trace-ui`. `test_phoenix_license_boundary.py`
  exige que el SKILL.md exista y declare ELv2. Borrarlo pone rojo una auditoría de
  licencia; el verde barato sería sacar la ruta de la lista del test.
- **Envoltura de herramienta no-Python, sin decisión de remover (2):**
  `promptfoo-integration`, `automaker-bridge`. Son las dos candidatas más plausibles
  de la lista, pero la evidencia que traía el encargo (`find_spec`) no aplica y no
  encontré ninguna otra. Van a **BORRAR TRAS DECISIÓN**, no a BORRAR YA: hace falta
  que el operador diga "no vamos a usar promptfoo ni AutoMaker", que es una frase que
  hoy no está escrita en ningún lado del repo.

## Asientos limpiados

Los 5 asientos de `hooks/rate-limit-protection.sh`, más el proof:

| Asiento | Archivo | Qué era |
|---|---|---|
| ratchet de registro | `hooks/_lib/registration-allowlist.txt:145` | línea suelta; sacarla es el movimiento legal (solo encoge) |
| ratchet de contrato | `tests/contracts/EXCLUDED_HOOKS.txt:168` | `DEPRECATED: renamed to token-budget-monitor.sh` |
| clasificación | `manifests/hook-registration-classification.yaml` | entrada `status: deprecated` completa |
| disponibilidad | `manifests/primitive-consumer-availability.yaml` | entrada `shared-surface` |
| **supresor** | `manifests/silent-failure-allowlist.yaml` | `max_occurrences: 2`, `degradation_class: legacy_audited` — un supresor apuntando a un archivo que ya no existe es un asiento libre |
| proof pareado | `tests/red_team/portability/test_rate-limit-protection.py` | **reescrito**, ver abajo |
| regenerado | `manifests/hook-quality.yaml` | vía `--sync` |

**NO se tocó** `rules/rate-limit-protection.md` ni sus asientos
(`manifests/rule-routing-coverage.yaml`, `primitive-lifecycle.yaml`,
`agentic-primitive-registry.lock.yaml`, `scripts/validate_tier_filter.py`,
`scripts/primitive_scope_classifier.py`, `hooks/self-install.sh:348`): la **regla**
sigue viva y documenta el hook nuevo.

### El asiento falso que el borrado destapó

`scripts/primitive_behavior_depth_audit.py` parea cada primitiva con
`tests/<lane>/test_<stem>.py`. Como el shim y la regla comparten stem, **el único
proof de comportamiento de `rules/rate-limit-protection.md` era el test del shim** —
es decir, la regla estaba "probada" por un script que solo imprime un warning. Al
borrar el shim el audit tiró:

```
behavior-depth-below-minimum  rules/rate-limit-protection.md  depth none below required structural
behavior-depth-budget-exceeded  behavior_depth:none  none has 1 primitives, above budget 0
```

El verde barato acá era subir el budget de `none` de 0 a 1. **No se hizo.** Se
reescribió el proof para que ejercite la implementación que la regla realmente
describe (`hooks/token-budget-monitor.sh`), con 6 aserciones sobre comportamiento
observable y ningún `skip`:

- corte por `RATE_LIMIT_OVERRIDE=true` (§Override), antes de escribir métricas;
- presupuesto fresco → `exit 0`, y escribe solo bajo el project dir del que lo llama;
- 98 % del presupuesto horario → `exit 2` + `RATE LIMIT REACHED` (§Thresholds);
- banda 85 % → `exit 0` con `WARNING`, distinguible del bloqueo;
- override gana incluso con el presupuesto agotado (con precondición que verifica
  que sin override ese mismo presupuesto sí bloquea);
- la regla nombra un hook que existe, y ya no nombra al shim.

Todos escriben bajo `tmp_path`; ninguno toca `.cognitive-os/metrics/` del repo.
El proof nuevo es **más fuerte** que el que reemplaza: el anterior probaba
invariancia de cwd sobre un no-op.

## Los gates después del borrado

```
$ COS_ALLOW_PROTECTED_CONFIG_WRITE=1 .venv/bin/python3 scripts/hook_quality_audit.py --sync
hook-quality: wrote manifests/hook-quality.yaml

$ .venv/bin/python3 scripts/hook_quality_audit.py --check
hook-quality: OK (200 hooks, 200 syntax checks)
exit=0

$ .venv/bin/python3 scripts/primitive_behavior_depth_audit.py
{"by_behavior_depth": {"adversarial": 32, "functional": 146, "projection": 812,
 "smoke": 2, "structural": 460}, ..., "findings": 0, "findings_by_code": {},
 "total": 1452}
exit=0

$ .venv/bin/python3 -m pytest "tests/red_team/portability/test_rate-limit-protection.py" -q
6 passed in 0.99s
```

`findings` pasó de 2 (inducidos por el borrado) a **0**, arreglando el asiento y no
el presupuesto. `by_behavior_depth` ya no tiene la clave `none`.

```
$ .venv/bin/python3 -m pytest tests/contracts/ -q
3 failed, 856 passed, 4 skipped, 16 xfailed, 2 warnings in 651.60s (0:10:51)

FAILED tests/contracts/test_cross_session_event_taxonomy.py::test_settings_driver_wires_event_emitters_and_context_hooks
FAILED tests/contracts/test_p95_hook_latency.py::test_no_hook_p95_exceeds_ceiling
FAILED tests/contracts/test_ram_ceiling.py::test_so_vitals_reports_disk_under_ceiling
```

**Las tres fallas son ajenas a este borrado**, y no por descarte sino con el chequeo:

- ninguna nombra nada de este diff: `grep -c rate-limit-protection` sobre la salida
  completa de pytest devuelve **0**;
- ninguno de los tres tests lee un archivo de este diff (se grepearon los seis
  asientos tocados y `rate-limit` en los tres archivos de test: sin match);
- `test_p95_hook_latency` cae por `post-git-orphan-notifier` p95=2000 ms con
  `uptime` marcando `load averages: 99.15 119.97 132.27` — es la máquina, no un hook;
- `test_ram_ceiling` cae por 400,3 MiB contra techo de 400,0. `du -sm` sobre el
  subdirectorio de métricas da 68 MiB: el crecimiento no viene de ahí y no lo produjo
  esta tarea, que no escribió ni borró nada bajo ese subdirectorio;
- `test_cross_session_event_taxonomy` busca `cross-session-peer-context.sh` dentro
  del driver de settings; es cableado de otra tanda concurrente, que al momento de
  correr tenía ~20 archivos sucios de otra sesión.

No se movió ningún techo ni presupuesto para apagarlas. Quedan como estaban.

## Lo que este borrado dice del censo

El informe fuente ya había concluido que *"no hay materia muerta que se pueda borrar
sin decidir"* y calculó la poda sin decisión en 2 %. Ejecutar su propia lista BORRAR
YA da **1 de 11 ≈ 0,2 %**. La conclusión se sostiene más fuerte de lo que su propio
autor la escribió: la única fila que pasó las cuatro verificaciones es un shim de
compatibilidad de 14 líneas cuyo `next_action` escrito ya pedía archivarlo.

El patrón de las diez frenadas es uno solo: **actividad cero se leyó como muerte, y
en las diez la primitiva estaba apagada a propósito** —dependencia opcional, servicio
opt-in, lane pesado, extra de instalación, límite legal—. La columna que faltaba no
era telemetría: era la decisión escrita, y estaba en `requirements.txt`, en
`cognitive-os.yaml` y en un ADR aceptado, no en los seis lugares de omisión que el
encargo listaba.
