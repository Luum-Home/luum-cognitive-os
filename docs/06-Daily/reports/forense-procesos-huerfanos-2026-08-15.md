# Forense: fuga de procesos huérfanos — 2026-08-15

**Veredicto:** la fuga es real, pero no es del script que aparece en el censo. El
que fuga es `scripts/family_conformance_probe.py`, que ejecuta scripts
arbitrarios del repo como candidatos y, cuando su timeout de 10s vence, mata
**sólo al hijo directo**. Todo el árbol que ese candidato ya había forkeado
sobrevive reparentado a init. Arreglado en el origen: cada candidato corre en su
propio grupo de procesos y el timeout mata el grupo entero.

---

## Correcciones a las premisas del encargo

| Premisa del encargo | Estado | Evidencia |
|---|---|---|
| «30 instancias vivas simultáneas» | **Corregida: 28** en el primer censo | `ps -eo pid,ppid,etime,pcpu,args \| grep -c '[c]os_primitive_closure_check'` → `28` |
| «casi todas con `ppid=1`» | **Confirmada** — 28/28 en el primer censo | mismo comando, columna 2 |
| «0.0% de CPU, edades 2:02–6:06» | **Confirmado el 0.0%; el rango era 1:21–7:50**, más ancho que lo reportado | mismo comando |
| «el script no lee stdin» | **Confirmada** | `grep -nE 'stdin\|input\(\|read\(\|sys\.stdin\|fileinput' scripts/cos_primitive_closure_check.py` → sin coincidencias |
| «`fd 0` es un PIPE» | **Confirmada** — y `fd 1` y `fd 2` también | `lsof -p 223` |
| Hipótesis: «bloqueados escribiendo, buffer del pipe lleno» | **REFUTADA** | stack real: `select_poll_poll` → `poll` — están esperando a un hijo, no escribiendo |
| «`sample <pid> 2 -mayberestart`» | **La opción no existe.** `sample` la rechaza con `[invalid usage]` | el flag correcto es `-mayDie`; con el del encargo el comando no produce stack |
| «unas pocas con ppid real, de segundos: las recién nacidas» | **Confirmada y decisiva** — fue el hilo que llevó al padre | ver §Quién los spawnea |
| «`git grep -n 'cos-primitive-closure-check'` sólo da metadata y ADR-336» | **Confirmada, y la conclusión que sugería es la trampa**: el spawner no lo nombra nunca — lo descubre por glob | ver §Quién los spawnea |
| «no toques `tests/audit/test_family_conformance.py` ni `tests/fixtures/family-probe/`» | **Respetada, y verificada como no bloqueante**: el arreglo cae en `scripts/family_conformance_probe.py`, que no está en esa lista | `git status --porcelain` sobre los tres paths → vacío; el script del arreglo estaba limpio y commiteado |
| «el arreglo puede caer en `hooks/**` (config protegida)» | **No aplicó.** El arreglo cae en `scripts/` | — |

Además, dos hallazgos que el encargo no contemplaba:

- **Los huérfanos no están colgados para siempre.** Entre el primer censo y el
  segundo (~3 min) el conteo cayó de **28 a 2**. Terminan solos; son *lentos*,
  no *deadlockeados*. Eso descarta cualquier explicación de bloqueo permanente,
  incluida la del buffer lleno.
- **El proceso fugado no es uno solo.** También hay `family_conformance_probe.py`
  con `ppid=1` (6 en el censo final) y `acc_pipeline.py` colgando de los
  huérfanos. La fuga es de *árboles*, no de un ejecutable.

---

## 1. El censo, recontado

```bash
ps -eo pid,ppid,etime,pcpu,args | grep '[c]os_primitive_closure_check'
ps -eo pid,ppid,etime,pcpu,args | grep -c '[c]os_primitive_closure_check'
```

| Momento | Instancias | `ppid=1` | Rango de edad | CPU |
|---|---|---|---|---|
| t0 | **28** | 28 | 1:21 – 7:50 | 0.0% |
| t0 + ~3 min | **2** | — | — | 0.0% |
| t0 + ~25 min (final) | **25** | 19 | 0:03 – 3:25 | 0.0% |

El conteo **oscila**: sube mientras el probe corre, cae cuando los huérfanos
terminan su cadena. No es un pozo que sólo crece; es un caudal.

Censo de los otros dos actores del mismo árbol:

```bash
ps -eo pid,ppid,etime,args | grep '[f]amily_conformance_probe' | awk '$2==1'
ls -d /private/var/folders/*/*/T/famprobe-* | wc -l
```

- **6** `family_conformance_probe.py` con `ppid=1`.
- Sandboxes `famprobe-*` sin borrar: **1063** en el primer conteo, **1278** ~25
  min después. Crecen ~9/min.

---

## 2. Dónde bloquean de verdad

El encargo pedía mirar el stack, no inferir. El flag del encargo no existe:

```
$ sample 223 1 -mayberestart
[invalid usage]: unrecognized option '-mayberestart'
```

Con el flag correcto:

```bash
sample <pid> 1 -mayDie
```

```
888 _PyEval_EvalFrameDefault  (in Python) + 21564
  888 select_poll_poll  (in select.cpython-314-darwin.so) + 300
    888 poll  (in libsystem_kernel.dylib) + 8
```

**888 de 888 muestras en `poll()`.** Eso es `subprocess.communicate()` esperando
a que un hijo cierre sus pipes — no es un `write()` bloqueado. La hipótesis del
buffer de 64 KB queda **descartada por evidencia directa**.

Confirmación independiente: los huérfanos **tienen hijos vivos**.

```bash
ps -eo pid,ppid,etime,args | awk '$2==223 || $2==572 || $2==2206'
```

```
89873   572    01:25  python3 scripts/acc_pipeline.py --brief
90333  2206    00:32  python3 scripts/acc_pipeline.py --brief
90336   223    00:32  python3 scripts/acc_pipeline.py --brief
```

Un proceso de 3:29 con un hijo de 0:32 **avanzó**: ya pasó otros pasos y está en
uno nuevo. No está colgado: está corriendo una cadena larga y cara.

Por qué es cara: `scripts/cos_primitive_closure_check.py` corre pasos con
`timeout=600` (`acc_pipeline.py --refresh`) y `timeout=300`
(`acc_pipeline.py --brief`), y su helper `_run` usa **`cwd=ROOT`** — el repo
real, no el sandbox. Aunque el probe lo lance dentro de una copia aislada, el
script sale del aislamiento y trabaja contra el árbol de verdad, durante
minutos.

---

## 3. Quién los spawnea, y cómo se encontró

El encargo tenía razón en que buscar por nombre no alcanza. `git grep` del nombre
kebab-case no llega al spawner porque **el spawner nunca lo nombra**.

El hilo que sí funcionó fue el `cwd`, no el nombre:

```bash
lsof -p 223 | head -3
```

```
Python 223 ... cwd DIR ... /private/var/folders/.../T/famprobe-6mpm9252/sbx-pos-0
```

`famprobe-` es un prefijo literal. Un solo grep lo ubica:

```bash
git grep -rn 'famprobe' -- .
```

```
scripts/family_conformance_probe.py:301:  workdir = Path(tempfile.mkdtemp(prefix="famprobe-"))
```

El probe **descubre sus candidatos por glob**, no por nombre
(`screen_candidates`, línea 251): recorre `family.candidate_globs` y admite todo
archivo cuyo texto contenga alguna aguja de `channel_screen` (p. ej.
`git diff --cached`). `cos_primitive_closure_check.py` entra porque menciona esa
aguja. Por eso ningún `grep` por nombre lo encuentra: **la trampa acá fue
«registro por glob», una variante del «registro por delegación» del catálogo.**

Y el multiplicador, visible en `ps`:

```
61530 61528  00:09  python3 scripts/family_conformance_probe.py
64262 61530  00:06  python3 .../scripts/family_conformance_probe.py
68503 64262  00:02  python3 .../scripts/family_conformance_probe.py
```

**El probe se ejecuta a sí mismo como candidato, recursivamente.** Cada nivel
abre un `ThreadPoolExecutor(max_workers=16)`. Eso es lo que convierte una fuga
lineal en una de decenas de procesos: no hay «alguien que lo lanza 30 veces», hay
un fan-out de 16 por nivel, con niveles anidados.

---

## 4. La causa raíz

`scripts/family_conformance_probe.py`, `run_candidate` (pre-fix, línea 208):

```python
proc = subprocess.run(cmd, cwd=sandbox, env=env, input=stdin,
                      capture_output=True, text=True, timeout=TIMEOUT_S)
except subprocess.TimeoutExpired:
    return UNMEASURABLE, "timeout"
```

Con `TIMEOUT_S = 10`.

`subprocess.run(timeout=...)` manda **SIGKILL al hijo directo y a nadie más**. El
hijo directo muere; sus descendientes no reciben nada y quedan reparentados a
init. La cadena completa:

1. El probe admite como candidatos a scripts que **son a su vez spawners** — el
   closure check (que lanza `acc_pipeline`) y el propio probe (que lanza 16
   hilos de candidatos).
2. A los 10s el candidato todavía está a la mitad de una cadena de minutos.
3. El timeout mata al candidato. **El subárbol sobrevive.**
4. Ese subárbol sigue corriendo contra el repo real (`cwd=ROOT` en el closure
   check), 0% CPU la mayor parte del tiempo porque está en `poll()` esperando a
   sus propios hijos.
5. Como el candidato murió por SIGKILL, el `finally: shutil.rmtree(workdir)` de
   `probe_one` **nunca corre** en los niveles anidados → los 1278 sandboxes
   `famprobe-*` sin borrar son el rastro contable de la misma causa.

El propio docstring de `screen_candidates` ya había anticipado el riesgo:
ejecutar todo lo que hay bajo `hooks/` y `scripts/` «no es ni rápido ni seguro
(instaladores, dispatchers de LLM, demonios viven ahí)». El screen filtra *qué*
se ejecuta; nunca acotó *hasta dónde llega el timeout*.

---

## 5. El arreglo, y por qué éste y no los otros

**Archivo:** `scripts/family_conformance_probe.py` (no es `hooks/**`; no requiere
diff propuesto).

Dos cambios:

1. Cada candidato se lanza con `start_new_session=True`, lo que lo vuelve líder
   de su propio grupo de procesos.
2. Al vencer el timeout, se manda `SIGKILL` **al grupo** (`os.killpg`), no al
   proceso. Un solo `killpg` alcanza todo lo que el candidato haya forkeado.

```python
def _kill_candidate_tree(proc: subprocess.Popen) -> None:
    try:
        pgid = os.getpgid(proc.pid)
    except (ProcessLookupError, PermissionError):
        return
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
```

`subprocess.run` no sabe matar grupos, así que el bloque pasó a `Popen` +
`communicate(timeout=...)`, conservando **exactamente** la semántica de veredictos
previa (`>=126` → UNMEASURABLE, `!=0` → BLOCKED, marcadores → BLOCKED, resto →
SILENT) y la entrega de `stdin`.

### Alternativas descartadas, con el motivo

| Alternativa | Por qué no |
|---|---|
| Cron o barrido que mate huérfanos | Es el verde barato del lote: apaga el síntoma, deja la causa, y vuelve verde cualquier medición futura de «¿hay fuga?». Además borraría trabajo legítimo del operador con el mismo nombre. |
| Subir `TIMEOUT_S` | Empeora: más tiempo por candidato, misma fuga por candidato, y el closure check tarda **minutos** — habría que subirlo a 600s, con lo que el probe deja de terminar. El encargo lo marcó como verde barato y lo es. |
| Excluir el closure check del screen (lista negra por nombre) | Trata **un** candidato. La fuga es de la mecánica del timeout: cualquier candidato que forkee filtra igual. Y una lista por nombre es justo lo que este mismo forense demostró que no encuentra nada. |
| Que el closure check «escriba menos» | Parte de la hipótesis refutada (bloqueo en `write`). El stack dice `poll`. Arreglaría un problema que no existe. |
| `shutil.rmtree` más agresivo / limpiar sandboxes | Los sandboxes son **consecuencia**, no causa. Con el grupo muerto, el `finally` vuelve a correr solo. |
| Que el probe no se ejecute a sí mismo | Es el **amplificador**, no la causa: sin recursión la fuga sigue, sólo que de a uno. Con `killpg`, además, la recursión queda acotada: matar el grupo del nivel 1 arrastra todos los niveles inferiores. Vale como endurecimiento aparte, no como el arreglo. |

---

## 6. Cómo se verifica que dejó de pasar

Evidencia ejecutable, en el repo:
`tests/audit/test_family_probe_no_orphans.py`

```bash
.venv/bin/python -m pytest tests/audit/test_family_probe_no_orphans.py -q
```

El test ejecuta el `run_candidate` real contra un candidato que forkea un nieto
de larga vida y después se cuelga — exactamente la forma que fugaba — y afirma
que el nieto está muerto una vez que venció el timeout. El segundo test verifica
que los veredictos ordinarios (SILENT / BLOCKED) y la entrega de `stdin` no
cambiaron.

**Es un test de regresión de verdad, no una tautología: falla en el código
pre-fix.** Comprobado extrayendo la versión anterior y corriéndolo contra ella:

```bash
git show HEAD:scripts/family_conformance_probe.py > <scratch>/prefix/scripts/family_conformance_probe.py
cp tests/audit/test_family_probe_no_orphans.py <scratch>/prefix/tests/audit/
.venv/bin/python -m pytest <scratch>/prefix/tests/audit/test_family_probe_no_orphans.py -q
```

| Código | Resultado |
|---|---|
| pre-fix (`HEAD`) | `1 failed, 1 passed` — `AssertionError: grandchild pid 32826 survived the probe timeout` |
| post-fix (árbol) | `2 passed in 3.98s` |

Verificación de campo, además del test (correr **después** de que termine el
probe que está activo ahora):

```bash
# 1. no deben quedar huérfanos del árbol del probe
ps -eo pid,ppid,args | grep -E '[c]os_primitive_closure_check|[f]amily_conformance_probe|[a]cc_pipeline' | awk '$2==1'
# 2. los sandboxes deben dejar de acumularse
ls -d /private/var/folders/*/*/T/famprobe-* 2>/dev/null | wc -l
```

Criterio: (1) sin filas, (2) el conteo deja de crecer entre dos corridas
separadas por unos minutos.

> **Nota importante sobre el estado al cierre:** el conteo **sigue subiendo**
> mientras se escribe esto, porque hay otra sesión corriendo `family_conformance_probe.py`
> con el código pre-fix ya cargado en memoria (PIDs 61530 / 64262 / 68503 al
> momento del hallazgo). El arreglo aplica a **corridas nuevas**. La verificación
> de campo no da verde hasta que esa corrida termine y se lance una nueva.

---

## 7. Limpieza pendiente — NO EJECUTADA

No se mató ningún proceso. Es la máquina del operador y el nombre `acc_pipeline`
coincide con trabajo legítimo.

**Estos PIDs son un snapshot y ya están vencidos** — el conteo rota cada pocos
minutos. Hay que **re-enumerar antes de actuar**, y sólo después de que termine
la corrida activa del probe:

```bash
# re-enumerar (read-only) — huérfanos del árbol del probe, ppid=1
ps -eo pid,ppid,etime,args \
  | grep -E '[c]os_primitive_closure_check|[f]amily_conformance_probe|[a]cc_pipeline' \
  | awk '$2==1 {print $1, $3}'
```

Snapshot al cierre, a título ilustrativo (19 closure-check + 6 probe con `ppid=1`):

- `cos_primitive_closure_check.py`: 247, 8037, 14766, 22430, 23770, 24592, 33959,
  36026, 38059, 42888, 64133, 68076, 71967, 75644, 83307, 83335, 90619, 95176, 99881
- `family_conformance_probe.py`: 3849, 23489, 24590, 37416, 39824, 43429

Los que en ese mismo censo tenían `ppid` real (46288, 46470, 50699, 51229, 56389)
**no son huérfanos** y no deben tocarse.

Y los sandboxes, que son basura pura (el probe ya no los usa):

```bash
# revisar primero
ls -d /private/var/folders/*/*/T/famprobe-* | wc -l
# borrar (decisión del operador)
find /private/var/folders/*/*/T -maxdepth 1 -name 'famprobe-*' -type d -mmin +60 -exec rm -rf {} +
```

Un residuo propio, para transparencia: el test de regresión, al correr contra el
código **pre-fix**, dejó por diseño un nieto huérfano (`python -c "time.sleep(120)"`,
pid 32826 en esa corrida). Se autotermina a los 120s; no requiere acción. Contra
el código arreglado no deja nada — que es justamente lo que el test afirma.

---

## 8. Qué de este encargo era falso

1. **«30 instancias»** — eran 28. La diferencia no cambia el diagnóstico, pero el
   número del encargo no se reprodujo.
2. **«edades de 2:02 a 6:06»** — el rango real era 1:21–7:50.
3. **La hipótesis del `write()` bloqueado** — falsa. El stack dice `poll()`. La
   inferencia era plausible («0% CPU + vivo + huérfano») pero la causa era la
   contraria: no estaban bloqueados escribiendo hacia un lector muerto, estaban
   esperando a hijos vivos.
4. **`sample <pid> 2 -mayberestart`** — la opción no existe en `sample`. El
   comando falla entero. Es el mismo error que el encargo se auto-reprocha en el
   punto 1 de sus errores: **un comando que falla puede no dar nada, o dar algo
   de otra cosa.** Acá no dio nada, que es el caso benigno.
5. **«Algo los está lanzando 30 veces»** — encuadre engañoso. Nadie los lanza N
   veces: un fan-out de 16 hilos, recursivo, deja un residuo variable en cada
   pasada. Buscar «el que llama 30 veces» no lleva a ningún lado.
6. **«los procesos con `ppid` real y pocos segundos te dan el padre vivo»** —
   la pista era buena pero **en el primer censo no había ninguno**: los 28 tenían
   `ppid=1`. Lo que destrabó el caso fue el `cwd` del `lsof`, no el `ppid`.
7. **«si el arreglo cae en `hooks/**`, entregá el diff y pará»** — restricción
   verificada y no aplicable: el arreglo cae en `scripts/`. Se comprobó con
   `git status --porcelain`, no se asumió.

Lo que el encargo **acertó** y conviene dejar escrito: que buscar por nombre no
iba a alcanzar, que la lista de trampas de catálogo era el camino (fue una
variante de «registro por delegación»: registro por **glob**), y que matar los
huérfanos era el verde barato.

---

## 9. El commit quedó bloqueado por trabajo de otra sesión

El arreglo **no llegó a commitearse**. El pre-commit lo rechaza:

```
BLOCKED: SCOPE: both artifact lacks a paired portability proof.
  Run: scripts/cos-scope-both-portability-audit --strict
```

El artefacto que falta **no es ninguno de los tres míos**:

```bash
python3 -c "
import json
d=json.load(open('.cognitive-os/reports/scope-both-portability-audit.json'))
for r in d['rows']:
    if r.get('status')!='covered': print(r['status'], r['artifact'])"
```

```
missing scripts/audit_hanging_processes.py
```

Ese archivo está **sin trackear** (`git status --porcelain` → `??`), lo declara
otra sesión concurrente, y es un censo de procesos colgados para esta misma
investigación — con una distinción bien planteada entre `daemon` y `orphan-root`
que es justo el error nº2 que el encargo se auto-reprocha. Está `SCOPE: both` y
todavía no tiene su prueba de portabilidad.

El gate **camina el filesystem, no el índice**, así que un artefacto en vuelo de
otra sesión bloquea el commit de cualquiera, aunque el cambio propio no agregue
ni un `SCOPE: both`.

**Qué NO se hizo, a propósito:**

- No se usó el env var de bypass. Es el verde barato del gate: apaga el rojo sin
  tocar la causa y no deja rastro.
- No se escribió la prueba de portabilidad de `scripts/audit_hanging_processes.py`.
  Es de otra sesión; escribirle un test a un archivo ajeno en vuelo es pisarle el
  trabajo.
- No se stageó ni se commiteó nada de esa sesión. Verificado:
  `git diff --cached --name-only | grep audit_hanging_processes` → vacío.

**Estado real:** los tres archivos están en el repo y en disco (sobreviven a un
reinicio). Los dos nuevos están **stageados**; el arreglo de
`scripts/family_conformance_probe.py` está modificado sin stagear.

**Para cerrarlo**, una vez que la otra sesión commitee su archivo con su prueba
(o lo saque del árbol):

```bash
git add -- tests/audit/test_family_probe_no_orphans.py \
           docs/06-Daily/reports/forense-procesos-huerfanos-2026-08-15.md
git commit --only -F <mensaje> -- \
  scripts/family_conformance_probe.py \
  tests/audit/test_family_probe_no_orphans.py \
  docs/06-Daily/reports/forense-procesos-huerfanos-2026-08-15.md
```

---

## Archivos

- `scripts/family_conformance_probe.py` — arreglo de raíz (grupo de procesos + `killpg`) — **modificado, sin commitear**
- `tests/audit/test_family_probe_no_orphans.py` — evidencia ejecutable (falla pre-fix, pasa post-fix) — **stageado, sin commitear**
- `docs/06-Daily/reports/forense-procesos-huerfanos-2026-08-15.md` — este informe — **stageado, sin commitear**
