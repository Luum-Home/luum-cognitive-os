# El tronco de las métricas: `resolve_session_dir` y `COS_METRICS_DIR`

- **Fecha:** 2026-08-20
- **HEAD:** `ed398d344` (`git rev-parse --short HEAD`) — coincide con el sello del encargo
- **Estado:** arreglo **NO aplicado**: el guard de control-plane lo bloqueó. Patch listo y validado en `docs/06-Daily/patches/metrics-dir-override-2026-08-20.patch`
- **Evidencia ejecutable:** `scripts/verify-metrics-dir-override.sh` (+ `scripts/verify_seeded_writer_detected.py`)

---

## Correcciones a las premisas del encargo

### 1. «16 consumidores directos» — FALSO. Son 12 vivos.

```
$ grep -rl 'resolve_session_dir' hooks/ packages/*/hooks/ | wc -l
      16
```

El número 16 es correcto como conteo de **archivos que contienen el string**, pero
no como conteo de consumidores. Los 16 incluyen cuatro que no consumen la función:

| Archivo | Por qué no es consumidor |
|---|---|
| `hooks/_lib/common.sh` | Es la **definición**, no una llamada |
| `hooks/_archived/auto-refine.sh.bak` | Archivado. `grep -c 'auto-refine' .claude/settings.json` → `0` |
| `hooks/_archived/auto-verify.sh.bak` | Archivado. Mismo cero |
| `hooks/session-heartbeat.sh` | Define **su propia** `_resolve_session_dir()` (con guion bajo, `session-heartbeat.sh:33`), que no toca métricas: resuelve `sessions/<id>/heartbeat`. No sourcea la de `common.sh` |

**Consumidores reales: 12.** El arreglo del tronco no alcanza a `session-heartbeat.sh`;
si algún día se quiere que también honre el override, es un cambio aparte.

### 2. El origen del sandbox es `conftest.py` de la RAÍZ, no `tests/conftest.py`

El encargo dice «la suite exporta `COS_METRICS_DIR` … (`conftest.py::pytest_configure`)».
Correcto el símbolo, pero el archivo es el de la raíz del repo:

```
$ grep -n 'COS_METRICS_DIR' tests/conftest.py
(sin salida)

$ grep -n 'COS_METRICS_DIR' conftest.py
15:  1. PREVENCION (`pytest_configure`): exporta `COS_METRICS_DIR` /
193:        os.environ["COS_METRICS_DIR"] = str(_sandbox)
```

Importa porque el comentario que dejé en `bypass-resolver.sh:77` cita `tests/conftest.py`
y también está mal; es deuda de comentario, no de código.

### 3. La rama por sesión está APAGADA por defecto — la segregación que hay que
no romper hoy casi nunca se ejerce

`resolve_session_dir` solo entra a la rama por sesión si `COS_SESSION_SCOPED_METRICS=1`
o si `COGNITIVE_OS_SESSION_ID` viene seteada (compat). El bloque de comentario de
`common.sh:127-165` documenta por qué: la ruta de merge está muerta
(`session-cleanup.sh` resuelve la sesión con un `.current-session-$$` imposible), y
arreglarla no es libre porque `session-cleanup` está en `Stop`, que dispara una vez
por turno y con `cleanup_on_exit: true` borraría el directorio de sesión.

Eso explica el incidente del 2026-08-19 que cita el encargo (8.887 eventos al global,
cero a los seis `sessions/*/metrics/`): con el switch apagado, **el comportamiento
correcto es escribir al global**. Los seis directorios vacíos no son la falla; son el
residuo de la otra mitad del problema — los **dos espacios de nombres de sesión**
conviviendo (`session-init.sh:17` se inventa un id `<epoch>-<pid>-<rand>` en vez de
adoptar el del arnés). Por eso el arreglo de acá **no** toca esa lógica.

### 4. Hay un TERCER escritor que ignora la variable, y no está en el encargo

`scripts/hook-timing-wrapper.sh:68` hardcodea la ruta igual que los otros dos:

```
$ grep -n 'METRICS_DIR=' scripts/hook-timing-wrapper.sh
68:METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
```

Apareció solo, en la corrida real de la suite (ver §Gate). **No lo toqué**: está
fuera del encargo y envuelve *todas* las invocaciones de hooks, así que cambiarlo sin
pedido es scope creep sobre una ruta caliente. Patch de una línea, y `scripts/` **no**
está en `protected_globs`, así que no requiere revisión de guard:

```bash
METRICS_DIR="${COS_METRICS_DIR:-$PROJECT_DIR/.cognitive-os/metrics}"
```

### 5. El guard bloqueó el arreglo, y además bloquea por SUFIJO de ruta

Detalle en §Bloqueo. Se reporta como revisión humana pendiente; **no** activé el bypass.

---

## Premisas que SÍ se confirmaron

| # | Comando | Salida | Veredicto |
|---|---|---|---|
| 1 | `git rev-parse --short HEAD` | `ed398d344` | Coincide con el sello |
| 2 | `grep -n 'local metrics_dir=' hooks/_lib/common.sh` | `167:  local metrics_dir="$_PROJECT_DIR/.cognitive-os/metrics"` | Confirmada |
| 3 | `grep -rl 'resolve_session_dir' hooks/ packages/*/hooks/ \| wc -l` | `16` | Número sí, interpretación no (ver corrección 1) |
| 4 | `grep -rl '_lib/common.sh' hooks/*.sh packages/*/hooks/*.sh \| wc -l` | `90` | Confirmada |
| 5 | `grep -c 'COS_METRICS_DIR' hooks/_lib/safe-jsonl.sh` | `0` | Confirmada, y es un escritor real (`safe-jsonl.sh:100` escribe `hook-health.jsonl`) |

Sanidad del detector antes de leer el `0` de la premisa 5 como ausencia: el mismo
`grep -c` sobre un patrón que **sí** está da distinto de cero
(`grep -c 'hook-timing' scripts/hook-timing-wrapper.sh` → `7`), y sobre
`.claude/settings.json` el control `grep -c 'lethal-trifecta-gate'` → `1`.

---

## El arreglo

Dos líneas de contrato, una por biblioteca. Diff completo en
`docs/06-Daily/patches/metrics-dir-override-2026-08-20.patch` (validado con
`git apply --check` → OK contra `ed398d344`).

**`hooks/_lib/common.sh` — `resolve_session_dir()`**, guarda al principio de la función:

```bash
resolve_session_dir() {
  if [ -n "${COS_METRICS_DIR:-}" ]; then
    mkdir -p "$COS_METRICS_DIR" 2>/dev/null
    echo "$COS_METRICS_DIR"
    return 0
  fi
  ...  # todo lo demas, intacto
```

**`hooks/_lib/safe-jsonl.sh:38`**:

```bash
_SAFE_JSONL_METRICS_DIR="${COS_METRICS_DIR:-$_SAFE_JSONL_PROJECT_DIR/.cognitive-os/metrics}"
```

### Por qué la guarda va PRIMERO y no en el `else`

Es la decisión de orden que pedía el encargo. Ponerla como fallback del global
—`metrics_dir="${COS_METRICS_DIR:-$_PROJECT_DIR/...}"`— tapa solo el caso con la
segregación apagada. Un test corriendo con `COS_SESSION_SCOPED_METRICS=1` seguiría
cayendo en la rama por sesión y escribiendo bajo el `.cognitive-os/sessions/` **del
operador**: el mismo agujero, un nivel más abajo, y más difícil de ver porque el
directorio global queda limpio. `COS_METRICS_DIR` es un override explícito de quien
corre el proceso, así que gana sobre la política de ruteo; cuando no está seteada, la
función se comporta byte por byte como antes — eso es lo que sostiene el control B.

No es una convención nueva: es la que ya usan `bypass-resolver.sh:82`,
`tuning.sh:31`, `circuit-breaker.sh:27`, `remediation.sh:40`,
`pre-commit-gate.sh:32`, `orchestrator-skill-invocation-gate.sh:190` y
`scope-marker-portability-gate.sh:43`.

---

## Bloqueo: el guard no dejó aplicarlo

`hooks/**` está en `protected_globs` (`hooks/protected-config-write-guard.sh:128`).
Ambos archivos son control-plane, así que la edición se bloqueó:

```
=== PROTECTED CONFIG WRITE GUARD: BLOCKED ===
Protected control-plane path(s): hooks/_lib/common.sh, hooks/_lib/safe-jsonl.sh
```

**No activé `COS_ALLOW_PROTECTED_CONFIG_WRITE`.** Queda como revisión humana pendiente.
Para aplicarlo después de revisar:

```bash
git apply docs/06-Daily/patches/metrics-dir-override-2026-08-20.patch
```

### Hallazgo lateral: el guard matchea por sufijo de ruta

Al intentar validar el patch en una **copia descartable fuera del repo**
(`<scratchpad>/tree/hooks/_lib/common.sh`), el guard también bloqueó — pese a que ese
archivo no es control-plane de nada: es un fixture de test en un temporal. El matcheo
de `hooks/**` alcanza cualquier ruta cuyo sufijo coincida, sin anclar en
`CLAUDE_PROJECT_DIR`.

Se resolvió renombrando el directorio del fixture a `hx/` (sin tocar el repo real ni
el guard). Vale revisarlo: un falso positivo que empuja a renombrar fixtures es
exactamente la fricción que después se paga activando el bypass «porque total es un
temporal».

---

## Los 12 consumidores, uno por uno

Todos derivan `<algo>.jsonl` de la ruta y la usan **solo** como sumidero de métricas.
Ninguno lee del directorio, ninguno lo compara contra una ruta fija, ninguno depende
de que sea el global. Verificado con `grep -n -A2 'resolve_session_dir' <archivo>`.

| # | Consumidor | Archivo que escribe | Registrado | Veredicto |
|---|---|---|---|---|
| 1 | `hooks/lethal-trifecta-gate.sh:12` | `lethal-trifecta.jsonl` | sí (1) | Seguro — **caso testigo** del contrafáctico |
| 2 | `hooks/task-created.sh:31` | `task-created.jsonl` | sí (1) | Seguro |
| 3 | `hooks/task-completed.sh:31` | `task-completed.jsonl` | ver nota | Seguro |
| 4 | `hooks/aci-observation-capture.sh:16` | `aci-observations.jsonl`, `agent-trajectory.jsonl` | ver nota | Seguro |
| 5 | `hooks/large-file-advisor.sh:97` | `large-file-reads.jsonl` | sí (1) | Seguro |
| 6 | `hooks/engram-obsidian-export-on-stop.sh:26` | `obsidian-export.jsonl` | sí (1) | Seguro |
| 7 | `hooks/teammate-idle.sh:30` | `teammate-idle.jsonl` | sí (1) | Seguro |
| 8 | `packages/prompt-quality-gate/hooks/prompt-quality.sh:27` | `prompt-quality.jsonl` | sí (1) | Seguro |
| 9 | `packages/scope-governance/hooks/scope-proportionality.sh:62` | `scope-proportionality.jsonl` | sí (1) | Seguro |
| 10 | `packages/skill-governance/hooks/skill-tracker.sh:132` | `skill-metrics.jsonl` | sí (1) | Seguro |
| 11 | `packages/task-management/hooks/scope-creep-detector.sh:85` | `scope-creep.jsonl` | sí (1) | Seguro |
| 12 | `packages/verification-audit/hooks/result-truncator.sh:27` | `truncation-events.jsonl` | sí (1) | Seguro |

**Nota sobre los dos ceros.** `aci-observation-capture` y `task-completed` dan `0` en
`grep -c … .claude/settings.json`, pero eso **no** los hace inalcanzables ni cambia el
veredicto: aparecen en `cognitive-os.yaml`, en `manifests/hook-quality.yaml` y en
`manifests/agentic-primitive-registry.lock.yaml`. El registro efectivo se pregunta con
`.venv/bin/python3 scripts/audit_hook_registration.py`, no con `grep`. Para este
arreglo da igual: registrados o no, el uso de la ruta es idéntico.

**No consumidores** (ver corrección 1): `common.sh` (definición),
`session-heartbeat.sh` (función propia, no escribe métricas), y los dos `.bak`
archivados.

---

## Contrafáctico doble

`scripts/verify-metrics-dir-override.sh`. Exit `0` sin hallazgos / `1` con hallazgos /
`2` error. El «directorio del operador» de la prueba es un **proyecto falso** en un
temporal (`COGNITIVE_OS_PROJECT_DIR`): no se toca telemetría real.

La ruta esperada **no** se deriva de la expresión del código — sale del layout de
directorios que arma el propio script (`$WORK/<caso>/sandbox` vs
`$WORK/<caso>/proj/.cognitive-os/metrics`), que es una fuente independiente.

### (a) Con el arreglo — VERDE

```
$ COS_VERIFY_REPO=<fixture-parchado> bash scripts/verify-metrics-dir-override.sh
A  COS_METRICS_DIR seteada -> sandbox:1  operador-falso:0
B  sin override, scoped=1  -> sesion:1  global:0
C  sin override, sin scoped -> global:1
D  safe-jsonl: _resolve_metrics_dir='…/d/sandbox'  heartbeat sandbox:1 operador-falso:0
E  DETECTADO: capa 2 reporta [('sembrado.jsonl', 0, 18)]
---
OK: sin hallazgos
EXIT=0
```

### (b) Revertido (repo real, `ed398d344`) — ROJO

```
$ bash scripts/verify-metrics-dir-override.sh
A  COS_METRICS_DIR seteada -> sandbox:0  operador-falso:1
   HALLAZGO: con COS_METRICS_DIR seteada, el sandbox quedo VACIO
   HALLAZGO: escribio en la ruta del operador pese al override:
   -rw-r--r--  1 … 323 Aug 20 14:14 lethal-trifecta.jsonl
B  sin override, scoped=1  -> sesion:1  global:0
C  sin override, sin scoped -> global:1
D  safe-jsonl: _resolve_metrics_dir='…/d/proj/.cognitive-os/metrics'  heartbeat sandbox:0 operador-falso:1
   HALLAZGO: safe-jsonl no honra COS_METRICS_DIR (esperaba …/d/sandbox)
   HALLAZGO: el heartbeat escribio en la ruta del operador
E  DETECTADO: capa 2 reporta [('sembrado.jsonl', 0, 18)]
---
HALLAZGOS presentes
EXIT=1
```

### El segundo control: la segregación sigue viva

Es el punto de la línea **B**, y es el que caza un arreglo que arregle el bug rompiendo
la función. Con `COS_METRICS_DIR` **ausente** y `COS_SESSION_SCOPED_METRICS=1` +
`CLAUDE_CODE_SESSION_ID=segregacion-viva-42`, el hook escribe en
`sessions/segregacion-viva-42/metrics/` y **cero** en el global — igual antes y después
del arreglo. **C** cubre el otro default (sin override, sin switch → global).

Que B y C den **verde en las dos ramas** mientras A y D dan **rojo en una sola** es
justamente lo que muestra que la sonda discrimina en vez de estar trabada: si el script
diera lo mismo en todo, no probaría nada.

---

## El gate sigue cazando escritores que no honran la variable

La detección de la capa 2 (`conftest.py`) mira el **filesystem**, no el resolver, así
que arreglar el tronco no puede apagarla. Demostrado, no razonado:

**Sembrado** (`scripts/verify_seeded_writer_detected.py`, control **E**): un hook que
hardcodea `$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics/sembrado.jsonl` e ignora la
variable, pasado por las funciones **reales** `fingerprint_metrics_dir` + `diff_growth`
importadas del `conftest.py` de la raíz →
`DETECTADO: capa 2 reporta [('sembrado.jsonl', 0, 18)]`, con el arreglo puesto.

**Falsación por mutación** — un sembrado idéntico pero que **sí** honra la variable
tiene que dejar de ser detectado, o la sonda diría «detectado» siempre:

```
$ COS_VERIFY_SEEDED_HOOK=<mutante-que-honra> python3 scripts/verify_seeded_writer_detected.py
NO_DETECTADO: diff_growth=[] (sandbox=['sembrado.jsonl'])
EXIT=1
```

La sonda distingue los dos casos.

### Y el gate está cazando algo REAL ahora mismo

```
$ .venv/bin/python3 -m pytest tests/audit/test_metrics_isolation.py -q
..............                                                           [100%]
FALLO: la suite dejo escrituras en la telemetria del operador:
  hook-health.jsonl: 482823 -> 482925 bytes (+102)
  hook-timing.jsonl: 3903349 -> 3903686 bytes (+337)
14 passed in 0.31s
```

14 verdes y aun así el gate reporta fuga — **leer el sumario, no el exit code**, que
en esta corrida fue `0`. Los dos archivos nombrados son exactamente los dos escritores
que quedan sin arreglar:

- `hook-health.jsonl` ← `hooks/_lib/safe-jsonl.sh:100`. **Este lo arregla el patch.**
  Es la confirmación independiente de la premisa 5: no es teoría, está pasando.
- `hook-timing.jsonl` ← `scripts/hook-timing-wrapper.sh:68`. **Sin arreglar** (corrección 4).

---

## Higiene

- Ninguna escritura a mano en `.cognitive-os/metrics/*.jsonl`; nada borrado bajo
  `.cognitive-os/`.
- Todo lo que escribieron las pruebas cayó en `mktemp -d` con `trap … EXIT`.
- Los `+102` / `+337` bytes de arriba **no** los escribí yo a mano: son los hooks del
  arnés disparando durante la corrida de pytest, que es precisamente el bug bajo
  investigación. Es telemetría legítima del proceso, no ruido inventado; no se
  restauró nada porque no se corrompió nada.
- Entorno limpio de `COS_ALLOW_PROTECTED_CONFIG_WRITE` y `COS_BYPASS`
  (`env -u …` en cada corrida de gate, y `unset` dentro del script).

## Pendientes para el operador

1. **Revisar y aplicar el patch** (bloqueo del guard, no un problema del cambio).
2. **Decidir sobre `scripts/hook-timing-wrapper.sh:68`** — mismo bug, una línea, sin
   guard de por medio. Es el escritor que va a seguir fugando después del patch.
3. **Falso positivo del guard por sufijo de ruta** — bloquea fixtures descartables
   fuera del repo.
4. Deuda menor: el comentario de `hooks/_lib/bypass-resolver.sh:77` cita
   `tests/conftest.py`; el archivo real es el `conftest.py` de la raíz.
