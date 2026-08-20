# Aislamiento de métricas en `cos_bypass_audit`

Fecha: 2026-08-20
Entregable: `hooks/_lib/bypass-resolver.sh` (fix) + `tests/audit/test_metrics_isolation.py::test_bypass_audit_honors_cos_metrics_dir` (gate)

## Resumen ejecutivo

`cos_bypass_audit()` en `hooks/_lib/bypass-resolver.sh:76` calculaba el
directorio de métricas a mano —
`dir="$(_cos_bypass_project_dir)/.cognitive-os/metrics"`— sin mirar
`COS_METRICS_DIR`. Confirmado corriendo (no leyendo): ejercer un bypass real
con `COS_METRICS_DIR` apuntado a un temporal seguía escribiendo en
`.cognitive-os/metrics/bypass-activation.jsonl` del operador, +231/+233 bytes
deterministas por invocación, mientras el temporal solo recibía la métrica del
hook llamador (que sí honra la variable). El arreglo es un fallback de una
línea: `dir="${COS_METRICS_DIR:-$(_cos_bypass_project_dir)/.cognitive-os/metrics}"`,
sin cambiar el valor por defecto. Nueve funciones más en `hooks/_lib/*.sh`
comparten exactamente el mismo patrón sin arreglar — quedan inventariadas, no
tocadas, al final de este informe.

## 1. Defecto confirmado corriendo

Hook ejercido: `hooks/scope-marker-portability-gate.sh`, que llama
`cos_bypass_audit` cuando `unproven_scope_both` está activo (línea 227-230).
Es el mismo camino que dispara cualquier `git commit` real con el bypass
prendido.

```bash
BEFORE=$(wc -c < .cognitive-os/metrics/bypass-activation.jsonl)   # 10122

COS_ALLOW_PROTECTED_CONFIG_WRITE=1 env -u COS_BYPASS \
  COS_METRICS_DIR="$TMPMETRICS" \
  COS_ALLOW_UNPROVEN_SCOPE_BOTH=1 \
  COS_UNPROVEN_SCOPE_REASON="prueba-aislamiento-metricas-2026-08-20" \
  CLAUDE_PROJECT_DIR="$PWD" \
  bash hooks/scope-marker-portability-gate.sh <<'JSON'
{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}
JSON

AFTER=$(wc -c < .cognitive-os/metrics/bypass-activation.jsonl)    # 10353
```

Resultado: **10122 → 10353 bytes** (+231) en el archivo REAL del operador,
pese a que `COS_METRICS_DIR` apuntaba a
`/private/tmp/.../metrics-isolation-check/metrics-before`. Ese temporal solo
contenía `scope-marker-portability-gate.jsonl` (134 bytes, el propio hook sí
honra la variable en su línea 43) — **cero** rastro de
`bypass-activation.jsonl`. La fila agregada era exactamente la de esta
corrida (`"reason": "prueba-aislamiento-metricas-2026-08-20"`,
`"pid": 63736`), así que la atribución es inequívoca, no una coincidencia de
tamaño.

`COS_ALLOW_PROTECTED_CONFIG_WRITE=1` como prefijo de comando es el mecanismo
que el propio `protected-config-write-guard.sh` documenta para invocar un
hook protegido desde Bash (queda registrado en
`.cognitive-os/metrics/protected-config-bypass.jsonl`); acá se usó solo para
ejecutar el hook con fines de prueba, no para editarlo.

Después de medir, se restauró el archivo del operador con
`truncate -s 10122 .cognitive-os/metrics/bypass-activation.jsonl` (la fila
agregada era la última y única línea nueva). `git status` sobre ese path
volvió a "nothing to commit" antes y después.

## 2. Otros escritores con la ruta hardcodeada

```bash
git grep -nE '="?\$\{?[A-Za-z_]*(PROJECT_DIR|ROOT)[^"]*\.cognitive-os/metrics|=".*/\.cognitive-os/metrics"' \
  -- hooks/ hooks/_lib/ scripts/ | grep -v 'COS_METRICS_DIR'
```

Ese comando lista **todo** el que fija el directorio de métricas con una
ruta armada a mano, en `hooks/`, `hooks/_lib/` y `scripts/`. Da ~90 hooks de
primer nivel y ~10 scripts. Esa población NO es nueva: `conftest.py` (raíz)
ya la mide y la documenta —

```
grep -rl 'cognitive-os/metrics' hooks/*.sh | wc -l          -> 111
for f in $(grep -rl 'cognitive-os/metrics' hooks/*.sh); do \
    grep -q COS_METRICS_DIR "$f" && echo "$f"; done | wc -l -> 3
```

— y `tests/audit/test_metrics_isolation.py::test_cos_metrics_dir_adoption_only_goes_up`
ya fija ese `3` (hoy `4`, tras este cambio no — ver corrección de premisas más
abajo) como piso ratcheado. Ese ratchet cubre **solo `hooks/*.sh` de primer
nivel**: no ve `hooks/_lib/`.

Filtrando a la familia que sí importa para este hallazgo — **librerías
compartidas en `hooks/_lib/` que escriben métricas**, el mismo nivel de
`bypass-resolver.sh` —:

```bash
for f in $(git grep -l '\.cognitive-os/metrics' -- hooks/_lib/); do
  grep -c 'COS_METRICS_DIR' "$f" || true
done
```

Nueve archivos, **cero** de nueve honran `COS_METRICS_DIR`:

| Archivo | Qué escribe |
|---|---|
| `hooks/_lib/bypass-resolver.sh` | `bypass-activation.jsonl` — **arreglado en este cambio** |
| `hooks/_lib/circuit-breaker.sh` | `circuit-breaker/`, `repair-outcomes.jsonl` |
| `hooks/_lib/common.sh` | directorio de métricas por sesión (helper base) |
| `hooks/_lib/primitive-intervention.sh` | `primitive-interventions.jsonl` |
| `hooks/_lib/remediation.sh` | directorio de métricas (helper, 3 usos) |
| `hooks/_lib/safe-jsonl.sh` | `_SAFE_JSONL_METRICS_DIR` (helper base, usado por otros hooks) |
| `hooks/_lib/safe-worktree-remove.sh` | `worktree-removals.jsonl` |
| `hooks/_lib/singularity-suggestion.sh` | `singularity-events.jsonl`, `error-learning.jsonl`, `stale-docs.jsonl` |
| `hooks/_lib/tuning.sh` | `hook-tuning.jsonl` |

Ninguno de estos ocho se tocó en este cambio: el hallazgo asignado nombraba
puntualmente `bypass-resolver.sh:76`, y extenderlo a los otros ocho exige
revisar cada uno por separado (algunos son helpers de base usados por decenas
de hooks — `common.sh` y `safe-jsonl.sh` en particular). Quedan flagueados
para una tarea de seguimiento (ver cierre).

## 3. Arreglo

`hooks/_lib/bypass-resolver.sh`, función `cos_bypass_audit()`:

```diff
 cos_bypass_audit() {
   local key="$1" hook="$2" reason="$3" dir
-  dir="$(_cos_bypass_project_dir)/.cognitive-os/metrics"
+  dir="${COS_METRICS_DIR:-$(_cos_bypass_project_dir)/.cognitive-os/metrics}"
   mkdir -p "$dir" 2>/dev/null || true
```

Producción sin cambios: se verificó explícitamente que, SIN `COS_METRICS_DIR`
en el entorno, el bypass sigue escribiendo en la ruta de siempre —

```bash
BEFORE=10122
# (sin COS_METRICS_DIR)
AFTER=10353   # crece exactamente igual que antes del fix
```

## 4. Gate con contrafáctico

Nuevo test:
`tests/audit/test_metrics_isolation.py::test_bypass_audit_honors_cos_metrics_dir`.
Ejerce `hooks/scope-marker-portability-gate.sh` con el bypass real activo
(subprocess real, no un stub) y `COS_METRICS_DIR` apuntado a un
`tmp_path`. La aserción central compara un fingerprint del filesystem REAL de
`.cognitive-os/metrics/` (`conftest.fingerprint_metrics_dir` /
`diff_growth`, ya usadas en este archivo para la "capa 2" de detección) antes
y después — **no** recalcula la ruta esperada con el mismo criterio que usa
el código bajo prueba
(`_cos_bypass_project_dir()/.cognitive-os/metrics`), que es la trampa
señalada en el encargo: derivarla igual habría certificado en verde
exactamente el bug que hay que vigilar.

**Corrida con el arreglo (verde):**

```
$ .venv/bin/python3 -m pytest tests/audit/test_metrics_isolation.py::test_bypass_audit_honors_cos_metrics_dir -q
.                                                                        [100%]
1 passed in 0.31s
```

**Revertido el fix (`dir="$(_cos_bypass_project_dir)/.cognitive-os/metrics"`, sin fallback) y corrido de nuevo (rojo):**

```
$ .venv/bin/python3 -m pytest tests/audit/test_metrics_isolation.py::test_bypass_audit_honors_cos_metrics_dir -q
F                                                                        [100%]
FALLO: la suite dejo escrituras en la telemetria del operador (.cognitive-os/metrics/):
  bypass-activation.jsonl: 10122 -> 10355 bytes (+233)
  Un test no puede escribir aca. Redirigi el escritor a COS_METRICS_DIR o corre con COS_ALLOW_OPERATOR_METRICS_WRITES=1 si sabes que hay una sesion viva del operador escribiendo en paralelo.

E   AssertionError: cos_bypass_audit escribio en la telemetria REAL del operador aunque COS_METRICS_DIR apuntaba a un sandbox: [('bypass-activation.jsonl', 10122, 10355)]
1 failed in 0.26s
```

Nótese que el revert también disparó el detector de sesión completa del
propio `conftest.py` de la raíz (la línea `FALLO: la suite dejo
escrituras...`) — dos capas independientes viendo el mismo rojo, ninguna
derivada de la otra.

Fix restaurado, `bash -n` limpio, y el archivo completo vuelve a estar verde:

```
$ .venv/bin/python3 -m pytest tests/audit/test_metrics_isolation.py -q
.........                                                                [100%]
9 passed in 0.43s
```

Regresión sobre los otros consumidores conocidos de `bypass-resolver.sh`
(`tests/behavior/test_bypass_resolver.py`,
`tests/unit/test_primitive_scope_unknown_triage.py`,
`tests/red_team/portability/test_bypass-resolver.py`,
`tests/hooks/test_scope_marker_gate_trigger.py`,
`tests/hooks/test_research_bypass_cannot_self_grant.py`): **39 passed**, sin
crecimiento en `bypass-activation.jsonl` (el aviso que imprimió esa corrida
es de otros tres archivos ajenos a este hallazgo — `hook-health.jsonl`,
`hook-timing.jsonl`, `lethal-trifecta.jsonl` — parte de la población ya
documentada en `conftest.py`, no de esta clase).

`.cognitive-os/metrics/bypass-activation.jsonl` quedó en 10122 bytes al
cierre de la sesión — mismo tamaño que al empezar, `git status` limpio.

## Correcciones a las premisas del encargo

1. **"Arreglar uno de seis da una falsa sensación de aislamiento" — el número
   real de siblings es más alto que seis, y en dos capas distintas.** Dentro
   de `hooks/_lib/` (la familia de librerías compartidas, el mismo nivel que
   `bypass-resolver.sh`) hay **nueve** archivos con el patrón, no un puñado
   cercano a seis. Y por fuera de esa familia, la población de
   `hooks/*.sh` de primer nivel que hardcodea la ruta es de **~90**, ya
   medida y ya ratcheada por `conftest.py` / `test_cos_metrics_dir_adoption_only_goes_up`
   desde antes de este encargo (piso 3-de-111, hoy con este fix `bypass-resolver.sh`
   no cambia ese número porque vive en `_lib/`, fuera del glob que ese test
   recorre). Arreglar el finding puntual no cierra la clase; ya había una
   decisión escrita (el piso del ratchet) de no cerrarla toda de una vez.

2. **El mecanismo de "aislamiento de métricas en tests" ya existe y es más
   amplio de lo que el encargo daba a entender.** `conftest.py` en la raíz
   del repo (no un archivo nuevo de esta sesión) ya exporta `COS_METRICS_DIR`
   a un sandbox para TODA la suite y ya compara un fingerprint del directorio
   real del operador antes/después de la sesión completa
   (`pytest_sessionfinish`), fallando la corrida si algo creció. Ese
   mecanismo de sesión completa detectó el defecto revertido igual que el
   test puntual (ver la línea `FALLO: la suite dejo escrituras...` en la
   sección 4) — son dos capas independientes, no una reimplementación de la
   otra, y vale aclarar que el gate nuevo de este cambio no es el único que
   hubiera atrapado la regresión.

3. **No se tocaron los otros ocho escritores de `hooks/_lib/`.** El hallazgo
   nombraba una línea específica (`bypass-resolver.sh:76`); extender el
   arreglo a `common.sh` o `safe-jsonl.sh` sin auditar cada call-site
   individualmente hubiera sido más cambio del que este encargo pidió
   revisar con evidencia. Quedan inventariados en la sección 2 y flagueados
   como tarea de seguimiento, no como "arreglado".

## Cierre

- Se abrió un chip de seguimiento (`spawn_task`) para auditar y arreglar los
  ocho escritores restantes de `hooks/_lib/*.sh` listados en la sección 2,
  uno por uno (dos de ellos, `common.sh` y `safe-jsonl.sh`, son helpers base
  con múltiples consumidores y necesitan revisión de cada call-site antes de
  tocarlos).
- Estado final verificado: `git status` limpio sobre
  `.cognitive-os/metrics/bypass-activation.jsonl`; único cambio de código en
  `hooks/_lib/bypass-resolver.sh` (una línea) y el test nuevo en
  `tests/audit/test_metrics_isolation.py`.

RESULT:
  status: completed
  summary: Confirmado y arreglado que `cos_bypass_audit()` en `hooks/_lib/bypass-resolver.sh:76` ignoraba `COS_METRICS_DIR` y escribía siempre en la telemetría real del operador; agregado gate con contrafáctico corrido (revertido -> rojo, arreglado -> verde). Ocho siblings en `hooks/_lib/` con el mismo patrón quedaron inventariados y flagueados, no arreglados.
  files_created: [docs/06-Daily/reports/aislamiento-de-metricas-en-bypass-2026-08-20.md]
  files_modified: [hooks/_lib/bypass-resolver.sh, tests/audit/test_metrics_isolation.py]
  tests: [9 passed (tests/audit/test_metrics_isolation.py), 39 passed (regresión sobre consumidores conocidos de bypass-resolver.sh)]
  blockers: none

TRUST_REPORT: SCORE=88 STATUS=HIGH EVIDENCE=9 UNCERTAINTIES=2
---
WHAT I VERIFIED:
- Defecto confirmado corriendo el hook real dos veces (antes/después), con tamaños de archivo pegados arriba (10122 -> 10353, +231 bytes) y la fila de operator confirmada como la propia de la corrida (reason/pid coinciden).
- Arreglo verificado con y sin `COS_METRICS_DIR` en el entorno (sandbox aislado / comportamiento de producción sin cambios).
- Gate nuevo corrido en las dos direcciones: verde con el fix, rojo revirtiendo el fix (pegado arriba), verde de nuevo tras restaurar.
- Regresión sobre 5 archivos de test que ya ejercitaban `bypass-resolver.sh` por otros caminos: 39 passed.
- Telemetría del operador restaurada a su tamaño original (`truncate -s 10122`) y confirmada con `git status` limpio, dos veces (una por cada corrida de prueba manual).
- Inventario de siblings en `hooks/_lib/` con el comando pegado, cross-chequeado contra el mecanismo ya existente en `conftest.py` (no reinventé el censo).

UNSURE ABOUT:
- No verifiqué línea por línea que los ocho siblings de `hooks/_lib/` NO tengan ya alguna forma indirecta de honrar `COS_METRICS_DIR` (p. ej. vía una variable de entorno con otro nombre, o un caller que ya redirige antes de llamarlos) — solo confirmé la ausencia del string `COS_METRICS_DIR` en cada archivo, que es evidencia fuerte pero no una prueba de comportamiento como la que sí corrí para `bypass-resolver.sh`.
- No corrí la suite COMPLETA de tests (miles de archivos) tras el fix, solo el archivo de aislamiento y los 5 consumidores conocidos de `bypass-resolver.sh`; es posible que exista algún otro test que dependa del layout exacto de `hooks/_lib/bypass-resolver.sh` (línea de comentario, número de línea) y no lo haya encontrado con el grep usado.

HUMAN SHOULD CHECK:
- Decidir si la tarea de seguimiento sobre los ocho siblings de `hooks/_lib/` se prioriza pronto: son helpers de base (`common.sh`, `safe-jsonl.sh`) usados por muchos hooks, así que el mismo patrón de contaminación de telemetría en tests probablemente se repite cada vez que esos hooks corren con un bypass o un evento activo.
- Revisar si conviene sumar `bypass-resolver.sh` (y en general `hooks/_lib/*.sh`) al glob que recorre `test_cos_metrics_dir_adoption_only_goes_up`, hoy limitado a `hooks/*.sh` de primer nivel — eso es una decisión de ampliar el ratchet, no algo que corresponda tomar unilateralmente en este cambio.
