# Juicio de diseño: ¿es correcto el modelo de distribución del SO?

**Fecha:** 2026-08-15
**Alcance:** read-only sobre `luum-agent-os` + las 16 instalaciones registradas en `~/.cognitive-os/installations.json`.
**Lente:** una sola — el modelo de entrega, no la calidad de las primitivas.

---

## 1. Veredicto

**Empaquetar el SO como plugin del harness** (`.claude-plugin/plugin.json` para Claude Code, `.codex-plugin/plugin.json` para Codex), y retirar el instalador que copia archivos al proyecto. Es el único de los cinco modelos donde la unidad de entrega es el repositorio entero fijado a un SHA y **el cableado viaja adentro del mismo paquete que los archivos que cablea** — con lo cual las dos mitades de la entrega parcial silenciosa (falta el archivo / sobra el cable) dejan de tener dónde ocurrir.

---

## 2. Qué se verificó antes de decidir

Los números del encargo estaban cerca pero no exactos, y la causa raíz que se les atribuía es otra. Esto es lo que devuelven los comandos.

### 2.1 El defecto dominante, con nombre y línea

Cinco módulos `cos_lib` faltan en las instalaciones:

```
python3 - <<'PY'
import json,os,pathlib,sys; sys.path.insert(0,'scripts')
import lib_closure as LC
d=json.load(open(os.path.expanduser('~/.cognitive-os/installations.json')))['installations']
for i in d:
    root=pathlib.Path(i['path'])/'.cognitive-os'
    libs={p.stem for p in (root/'cos_lib').glob('*.py')}
    miss={m for hk in (root/'hooks'/'cos').glob('*.sh')
            for m in LC.extract_lib_modules_from_hook(hk) if m not in libs}
    print(i['path'], len(libs), sorted(miss))
PY
```

| módulo | instalaciones donde falta | existe en el repo | SCOPE |
|---|---|---|---|
| `cos_lib.harness_environment` | 16 / 16 | sí | (sin header) |
| `cos_lib.dispatch_model_advisor` | 15 / 16 | sí | `both` |
| `cos_lib.project_profile_bootstrap` | 15 / 16 | sí | `both` |
| `cos_lib.record_completion` | 15 / 16 | sí | `both` |
| `cos_lib.user_model` | 15 / 16 | sí | `both` |

Prueba de ejecución:

```
python3 -c "import sys;sys.path.insert(0,'$HOME/Projects/luum/aisotropy/.cognitive-os');import cos_lib.harness_environment"
# ModuleNotFoundError: No module named 'cos_lib.harness_environment'
```

**La causa NO es el filtro de scope.** Cuatro de los cinco son `SCOPE: both` y el quinto no tiene header — el filtro los deja pasar. La causa es que hay **dos caminos de copiado que no se hablan**:

- `scripts/cos_init.py:1897` computa una clausura de dependencias (`lib_closure.compute_closure`) cuya **semilla es exclusivamente `hooks/*.sh`**.
- `scripts/cos_init.py:1849` y `:1871` copian `hooks/_lib/` entero con `shutil.copytree`, **sin pasar por la clausura**.
- Los cuatro importadores rotos viven precisamente ahí: `hooks/cos/_lib/dispatch_gate_check.py`, `recap_adapter.py`, `session_init_helper.py`, `task_panel_adapter.py`.

La clausura nunca los mira. Y cuando un módulo no aparece, `scripts/lib_closure.py:168` documenta la decisión:

> `# Static-closure miss (§2.3): module referenced but not present on disk. Skip — the fail-open backstop covers this at runtime.`

`--full` no lo arregla: `luum-lang` proyecta 155 hooks y 83 módulos y **le faltan exactamente los mismos cinco**. Más archivos no cierra la clausura.

### 2.2 Por qué falla en silencio (esto es literal, no metafórico)

Los cuatro helpers rotos se invocan así:

| archivo | línea | invocación |
|---|---|---|
| `hooks/dispatch-gate.sh` | 107 | `python3 .../_lib/dispatch_gate_check.py 2>/dev/null \|\| echo '{...}'` |
| `hooks/session-init.sh` | 276 | `python3 .../_lib/session_init_helper.py 2>/dev/null \|\| true` |
| `hooks/task-panel-sync.sh` | 33 | `python3 .../_lib/task_panel_adapter.py 2>/dev/null \|\| true` |
| `hooks/recap-sync.sh` | 30 | idem vía `$LIB_DIR/recap_adapter.py` |

Un `ModuleNotFoundError` es indistinguible de "no había nada que hacer". Y el fallback de `dispatch-gate.sh:108` no degrada a seguro, degrada a **permisivo**:

```
{"max_agents":5,"active":0,...,"cb_blocked":false,...,"model_directive":"MODEL_ADVICE: sonnet",...,"error":"python-failed"}
```

`cb_blocked:false` hardcodeado = el circuit breaker de agentes está abierto en las 16 instalaciones. El campo `"error":"python-failed"` **no lo lee nadie** (`grep -n error hooks/dispatch-gate.sh` muestra que el único manejo de error es el de `queue_result`, línea 69, otra rama).

### 2.3 El gate que ya existe, y por qué no sirvió

`scripts/runtime_hook_reality.py --dependency-closure` detecta el problema perfectamente:

```
python3 scripts/runtime_hook_reality.py \
  --project-root ~/Projects/luum/aisotropy \
  --settings ~/Projects/luum/aisotropy/.claude/settings.json \
  --dependency-closure --install-scope project --fail-on-findings
# summary.status = "fail", 8 findings
```

| hook | referencia faltante |
|---|---|
| `completion-gate.sh` | `scripts/agent_work_ledger.py`, `scripts/claim_task.py`, `scripts/resource_lease.py` |
| `inject-phase-context.sh` | `scripts/_lib/settings-driver-claude-code.sh`, `scripts/apply-efficiency-profile.sh`, `scripts/cos-lib-symlink-invariant-audit.py` |
| `large-file-advisor.sh` | `hooks/large-file-advisor.sh` |
| driver (settings) | `hooks/block-destructive-bash.sh` — **cableado y no entregado** |

Son 8 rutas más, encima de los 5 módulos. El gate existe, es correcto, y **la única vez que se corre es contra una instalación recién creada en `tmp_path`, y sólo con `--harness codex`** (`tests/behavior/test_consumer_project_projection.py:204`). En `tests/unit/test_cos_architecture_readiness.py` está directamente mockeado (`patch.object(readiness, "check_runtime_hook_reality", return_value=Check(..., "pass", ...))`, líneas 23, 120, 154, 297). Nunca se apunta a las 16 instalaciones reales. Es verde barato de manual: la medición se cumple, el problema no se toca.

### 2.4 El cableado colgado, y por qué es estructural

```
python3 - <<'PY'
import re,pathlib,json,os
d=json.load(open(os.path.expanduser('~/.cognitive-os/installations.json')))['installations']
for i in d:
    r=pathlib.Path(i['path']); st=r/'.claude/settings.json'
    if not st.is_file(): continue
    wired=set(re.findall(r'\.cognitive-os/hooks/cos/([a-z0-9-]+)\.sh',st.read_text()))
    disk={p.stem for p in (r/'.cognitive-os/hooks/cos').glob('*.sh')}
    print(i['path'], 'dangling:',sorted(wired-disk), 'inert:',len(disk-wired))
PY
```

| instalación | cableados sin archivo | entregados sin cablear |
|---|---|---|
| `n1u` | `completeness-check`, `direct-main-guard`, `engram-obsidian-export-on-stop`, `plan-claim-validator` | 0 |
| `cienciayjusticia-voting` | los mismos 4 | 1 |
| `aisotropy` | 0 (pero ver 2.3: `block-destructive-bash` vía otra ruta) | 8 |
| `FinOpenPOS` | 0 | 2 |

Dos de esos cuatro (`completeness-check`, `engram-obsidian-export-on-stop`) son `SCOPE: os-only`. O sea: **el proyector de archivos aplicó el filtro de scope y el generador de settings no**. Son dos decisiones independientes sobre la misma pregunta, tomadas por dos piezas distintas de código. Mientras el cableado se genere aparte de la copia, van a poder discrepar.

Y la copia misma no es consistente con su propio filtro: de 22 call-sites de `shutil.copy2`/`copytree` en `scripts/cos_init.py`, **14 no tienen `scope_allows` en las 6 líneas previas** (L388, L420, L476, L1431, L1439, L1507, L1629, L1822, L1849, L1855, L1871, L1877, L1891, L1963). Algunos son legítimos —el guard está dentro de la función llamadora— pero los dos que importan son `L1849`/`L1871`: el `copytree` ciego de `hooks/_lib/` que arrastra los imports que nadie resuelve.

### 2.5 Correcciones a los números del encargo

| premisa | medición |
|---|---|
| 17 instalaciones | **16** registradas, las 16 vivas en disco |
| 155 hooks registrados | **154** (`grep -o 'hooks/[a-z0-9-]*\.sh' .claude/settings.json \| sort -u \| wc -l`) |
| 78 proyectados | **43** en las instalaciones default; 156 son `SCOPE: both/project`, o sea *proyectables*. El 78 no reproduce. |
| 31 dispararon | **33** distintos en `aisotropy` y **35** en `FinOpenPOS` de 43/45 entregados; y **149** distintos disparan en el propio repo del SO (17.887 filas de `hook-timing.jsonl`) |
| 3 de 17 con telemetría | **2 de 16** con telemetría real (aisotropy 245.701 filas, FinOpenPOS 54.414). Otras 4 tienen 1-2 filas (ruido de instalación). 10 tienen cero. |
| "congelada en la versión del día que se instaló; una parada en marzo, otra de julio" | **Falso como se enuncia.** Las 16 declaran `0.29.39` = `VERSION` del repo, y los 43 hooks proyectados tienen hash idéntico a HEAD en 15 de 16 (`FinOpenPOS` es la única con 21 archivos divergentes). |
| 13 call-sites saltean el scope | **14** de 22, con la salvedad de 2.4 |
| `install.sh:416`/`:425` `rm -rf` | **confirmado**, y `TARGET_DIR=".cognitive-os"` (`install.sh:14`) — es donde viven las 245.701 filas de métricas de `aisotropy` |

**Lo que sí está roto en la actualización, y es peor que "congelado":** `scripts/auto-update-projects.sh` es `SCOPE: os-only`, lee un registro en `~/.cognitive-os/`, y se dispara sólo desde los git hooks locales `post-merge` y `pre-push` del repo del mantenedor (`scripts/setup-git-hooks.sh:198,242,264`). **No hay lado pull.** Ninguna instalación puede actualizarse sola; depende de que el mantenedor mergee en *esa* máquina. Los 16 `updated_at` dicen `2026-07-20`; el repo tiene commits del `2026-08-15`. Son 26 días de deriva no aplicada, y para cualquier consumidor que no sea el mantenedor la deriva es infinita.

### 2.6 El dato que reordena todo el análisis

```
python3 - <<'PY'
import json,os,pathlib
d=json.load(open(os.path.expanduser('~/.cognitive-os/installations.json')))['installations']
for i in d:
    r=pathlib.Path(i['path'])
    print(i['path'], [m for m in ['.claude/settings.json','.codex/hooks.json','.agents/skills','AGENTS.md'] if (r/m).exists()])
PY
```

**12 de 16 instalaciones no tienen `.claude/settings.json`.** Son Codex-only. Sólo 4 tienen cableado de Claude: `n1u`, `FinOpenPOS`, `cienciayjusticia-voting`, `aisotropy` — y las 2 con telemetría real son exactamente dos de esas cuatro.

Es decir: el 75% del parque instalado depende de que Codex ejecute `.codex/hooks.json`, que es justo la pregunta abierta del forense. Ese no es un matiz del análisis, es el análisis.

---

## 3. Las cinco alternativas

| alternativa | qué elimina **de raíz** | qué no toca | costo de migrar | qué rompe hoy | modo de falla nuevo |
|---|---|---|---|---|---|
| **1. Statu quo + self-check** | Nada de raíz. Agrega un chequeo más al modelo que ya tiene el chequeo correcto (`runtime_hook_reality.py`) y no lo corre contra la realidad (§2.3). El instalador sigue eligiendo archivo por archivo. | Todo lo estructural: dos caminos de copiado, cableado generado aparte, ausencia de lado pull, `rm -rf` sobre el estado. | Bajo (1-2 semanas: apuntar el gate existente a las 16 instalaciones + CI). | Nada. | El gate nuevo se vuelve baseline: el día que 3 hallazgos sean "conocidos y aceptados", el 4º entra sin ruido. Ya pasó con este gate. |
| **2. Plugin del harness** ✅ | (a) Módulo faltante: la unidad de instalación es el repo a un SHA, no una allowlist. (b) Cable colgado: `hooks/hooks.json` viaja adentro del paquete que cablea. (c) Sin lado pull: `version` en el manifiesto, el usuario recibe al bumpear. (d) `rm -rf` destructivo: el código vive en `~/.claude/plugins/`, el estado en `${CLAUDE_PROJECT_DIR}`. (e) Discrepancia `install-meta.json`: no hay meta, hay manifiesto. | 214 hooks que nadie habilita. 2/16 con telemetría. Si las primitivas sirven. El plugin no crea demanda. | **Alto**: reescribir 257 hooks para `${CLAUDE_PLUGIN_ROOT}` (código) vs `${CLAUDE_PROJECT_DIR}` (estado). 183/257 ya usan `CLAUDE_PROJECT_DIR` y 120/257 resuelven `dirname "$0"` — ambos patrones sobreviven, pero hay que separarlos hook por hook. 4-6 semanas. | Las 16 instalaciones: `.cognitive-os/hooks/` y el bloque `hooks` de `.claude/settings.json` quedan obsoletos. El estado (`metrics/`, `sessions/`) se conserva. | El `os-only` se filtra: el paquete se entrega entero, así que hay que **partir en dos plugins** (público / mantenedor) en vez de filtrar por header. Y una versión mala llega a todos a la vez (mitigable con pin a SHA). |
| **3. Servicio / CI** | Entrega parcial: no hay entrega, el SO corre desde su propio checkout. | **Cambia qué es el producto.** Los gates PreToolUse que bloquean a un agente en el medio de la sesión no son ejecutables desde CI: CI es post-hoc. `dispatch-gate`, `blast-radius`, `block-destructive-bash` dejan de existir como control y pasan a ser reporte. | Alto y además es un rediseño de producto, no una migración. | Todo el modelo de gate en línea. | El SO se vuelve un linter tardío: encuentra lo que ya pasó. |
| **4. Biblioteca versionada** | Entrega parcial **del código**: pip/npm resuelven la clausura, que es exactamente el problema de §2.1, y lo hacen bien. | **Entrega parcial del cableado.** El `settings.json` sigue habiendo que generarlo y copiarlo al proyecto → el defecto de §2.4 (generador y proyector discrepando sobre scope) sobrevive intacto. También sobrevive el `rm -rf` si el generador maneja `.cognitive-os/`. | Medio (empaquetar `cos_lib` + `scripts` como wheel: 2-3 semanas). | Poco: se puede convivir. | Falso cierre: "los imports resuelven" se lee como "la entrega está completa", y la mitad que falla —el cable— queda sin gate porque el gate de la biblioteca no la ve. |
| **5. No distribuir** | Todo, por eliminación del consumidor. Con 2/16 instalaciones produciendo evidencia, es la opción más honesta de la lista. | Convierte 14 instalaciones en deuda a limpiar, no en producto. | Cero técnico. | Nada. | Ninguno técnico. Es una decisión sobre la ambición, no sobre el mecanismo — y no responde la pregunta que se hizo. |

---

## 4. Por qué el plugin hace imposible la entrega parcial silenciosa

No por tener mejores chequeos. Por no tener el paso donde el defecto ocurre.

**Hoy hay tres decisiones separadas** que pueden estar en desacuerdo y ninguna se entera:

1. *Qué archivos copio* — allowlist de `install.sh:452-470` + `default_hooks` + filtro `scope_allows` en 8 de 22 call-sites.
2. *Qué dependencias arrastro* — `lib_closure.compute_closure`, sembrada sólo con `hooks/*.sh`, fail-open cuando no encuentra (§2.1).
3. *Qué cableo* — el generador de settings, que aplica su propio criterio de scope (§2.4).

Cada una es una oportunidad de entregar de menos. La #2 falla-abierta por diseño escrito. La #3 discrepa con la #1 en 2 instalaciones probadas.

**Bajo el modelo de plugin las tres desaparecen, no se chequean:**

- El manifiesto declara identidad y versión, no inventario de archivos. La instalación es fetch del repo al SHA pinneado (fuente `github` / `git-subdir` / `archive`). No existe "el subconjunto que mando": mando el repo. Que falte un archivo requiere que falte **del repo del mantenedor**, cosa que git hace visible en el momento y `claude plugin validate` chequea antes de publicar.
- Los hooks referencian `"${CLAUDE_PLUGIN_ROOT}"/scripts/x.sh`. Hook y dependencia son el mismo commit del mismo directorio. La pregunta "¿llegó `cos_lib.harness_environment`?" no se puede contestar que no, salvo que tampoco esté en el repo.
- El cableado es `hooks/hooks.json` **dentro del plugin**. No hay generador. Un hook cableado y no entregado exigiría que `hooks.json` y el archivo hermano estuvieran en commits distintos del mismo directorio — no es una condición alcanzable.
- El estado del proyecto vive en `${CLAUDE_PROJECT_DIR}`, el código en el plugin root. Actualizar es bumpear `version`; nunca toca directorios del proyecto. El `rm -rf` de `install.sh:416`/`:425` deja de tener a qué apuntar.

**Lo que igual queda expuesto, y hay que decirlo:** la documentación es explícita en que Claude Code **no verifica que existan los componentes declarados en rutas custom** del manifiesto (`"skills": ["./custom/skills/"]` con el directorio vacío carga igual, sin skills). Eso sí es entrega parcial silenciosa residual — pero se cierra usando **rutas por defecto** (`skills/`, `hooks/hooks.json`, `agents/`) en lugar de rutas custom, con lo cual no hay declaración que pueda mentir. Es una decisión de empaquetado de una línea, no un gate a mantener.

El resto de lo que "sobrevive" no es entrega parcial: es que 214 hooks no le sirven a nadie y que 14 de 16 instalaciones no generan telemetría. Eso es un problema de valor, no de distribución, y ningún modelo de la lista lo arregla.

---

## 5. Plan de migración para las 16 instalaciones

Ordenado por lo que se puede hacer sin romper nada mientras se decide.

**Fase 0 — parar la hemorragia (hoy, 1 día, no requiere decidir nada)**
1. Sacar los `2>/dev/null` de los 4 call-sites de §2.2. Que un `ModuleNotFoundError` se vea. Es reversible y no depende del veredicto.
2. `dispatch-gate.sh:108`: el fallback debe fallar cerrado o al menos emitir el `error` a stderr. Un circuit breaker que se abre solo cuando el intérprete falla es peor que no tenerlo.
3. Correr `runtime_hook_reality.py --dependency-closure` contra **las 16 instalaciones**, no contra `tmp_path`. Ya está escrito, es read-only, y devuelve `fail` hoy.

**Fase 1 — empaquetar (2-3 semanas)**
4. Crear `.claude-plugin/plugin.json` y `.codex-plugin/plugin.json` en el repo, con `hooks/hooks.json` derivado **una sola vez** del `.claude/settings.json` actual (el formato del bloque `hooks` es idéntico, según la doc de migración).
5. Partir en dos paquetes según el header `SCOPE`: `cognitive-os` (los 156 `both`/`project`) y `cognitive-os-maintainer` (los 101 `os-only`). El filtro deja de ser una función que 14 call-sites olvidan llamar y pasa a ser un límite de repositorio.
6. Reescribir referencias: código → `${CLAUDE_PLUGIN_ROOT}` / `${PLUGIN_ROOT}`; estado → `${CLAUDE_PROJECT_DIR}`. Los 183 hooks que ya usan `CLAUDE_PROJECT_DIR` para estado no se tocan; los 120 con `dirname "$0"` resuelven bien dentro del plugin.
7. `claude plugin validate --strict` en CI. Reemplaza a `runtime_hook_reality.py` como gate de publicación (el segundo queda como auditoría de las instalaciones legacy hasta que no queden).

**Fase 2 — marketplace privado (1 semana)**
8. `marketplace.json` en un repo privado del equipo. Las entradas pinnean SHA. Esto le da lado pull al modelo por primera vez: hoy `auto-update-projects.sh` sólo corre en la máquina del mantenedor (§2.5).

**Fase 3 — cortar las 16 (2 semanas, gradual)**
9. Orden: primero `cos-consumer-e2e-drill` (es el drill, para eso está), después las 10 con telemetría cero (`accounting`, `luum-talent`, `live-profile`, `luum-lang`, `cognitive-layer`, `luum-cybersecurity`, `magil-openclaw`, `luum-woocommerce-distrinorth`, `luum-interface-layer`, `luum-platform-lab`), y último las 2 vivas (`aisotropy`, `FinOpenPOS`).
10. En cada una: instalar el plugin, verificar que el hook-timing sigue apareciendo, y **recién entonces** borrar `.cognitive-os/hooks/`, `.cognitive-os/cos_lib/`, `.cognitive-os/skills/` y el bloque `hooks` de `.claude/settings.json`. **No tocar** `.cognitive-os/metrics/`, `sessions/`, `agent-runs/`: son 245.701 + 54.414 filas de historia y no se regeneran.
11. Retirar `install.sh` y `auto-update-projects.sh`. El `rm -rf` de `:416`/`:425` se va con ellos.
12. Purgar `~/.cognitive-os/installations.json` a medida que cada una migra. El registro sobrevive sólo mientras haya instalaciones legacy.

**Lo que rompe en cada una:** nada de estado, todo de cableado. Las 12 Codex-only además necesitan que se resuelva §6 antes de migrar — si sus hooks nunca corrieron, migrarlas es empaquetar decoración.

---

## 6. Cómo cambia el veredicto según el forense de Codex

La pregunta abierta —¿Codex ejecuta los hooks proyectados en `.codex/hooks.json`?— decide **12 de las 16 instalaciones** (§2.6). Los tres escenarios:

**A. Codex los ejecuta.** El veredicto no cambia y se refuerza: Codex tiene su propio mecanismo de plugin, con manifiesto en `.codex-plugin/plugin.json`, `hooks/hooks.json` por defecto en el plugin root, y `PLUGIN_ROOT` / `PLUGIN_DATA` como variables — estructuralmente equivalente al de Claude Code. La alternativa 2 cubre 16/16, no 4/16, con dos manifiestos sobre el mismo árbol de archivos. Es el mejor caso para el plugin.

**B. Codex NO los ejecuta.** El veredicto tampoco cambia, pero por otro motivo: si 12 instalaciones son decoración, el parque real es de 4 y la alternativa **5 (no distribuir)** sube de "opción honesta" a "candidata seria". Aun así elegiría plugin, porque migrar 4 instalaciones es barato y porque el paquete resuelve el mismo problema en el repo del propio SO. Lo que sí cambiaría es el **orden**: primero apagar las 12 (borrar `.codex/hooks.json` y `.agents/skills`, dejar `AGENTS.md` si aporta), después empaquetar. Migrar cosas que nunca corrieron es trabajo puro.

**C. Los ejecuta pero sólo con opt-in / trust no otorgado.** La documentación de Codex dice que los hooks están habilitados por defecto (se desactivan con `[features] hooks = false`) y que **los hooks project-local sólo cargan cuando la capa `.codex/` del proyecto está confiada**. `~/.codex/config.toml` de esta máquina tiene `[features]` con sólo `js_repl = false`, o sea que no están desactivados — pero las 12 instalaciones tienen `metrics/` vacío, lo cual es consistente con trust no otorgado. Si es este el caso, es el escenario más caro: el modelo actual no sólo entrega de menos, sino que **el consumidor tiene que hacer un paso manual que nadie le pide y cuya omisión no produce ningún error**. Es entrega parcial silenciosa con un eslabón más. Refuerza el veredicto y agrega un requisito: el plugin de Codex debe documentar el trust como paso de instalación verificable, no asumirlo.

En los tres, plugin. Lo que cambia es el orden de la Fase 3 y cuánto trabajo hay que tirar.

---

## 7. Correcciones a las premisas del encargo

1. **"5 módulos no llegan porque el instalador no valida sus propios imports."** El instalador **sí** computa una clausura de imports (`lib_closure.compute_closure`). El bug no es que no valide: es que la clausura se siembra sólo con `hooks/*.sh` mientras `hooks/_lib/*.py` se copia por un camino paralelo (`copytree`, `cos_init.py:1849`/`:1871`) que la clausura no mira. Y cuando un módulo no aparece, `lib_closure.py:168` lo omite a propósito, delegando en un "fail-open backstop" que a la práctica es un `2>/dev/null`.

2. **"13 call-sites saltean el filtro de scope."** Son 14 de 22 sin `scope_allows` en las 6 líneas previas, y varios son falsos positivos (el guard está en la función llamadora). El número no es el problema: el problema es que dos de esos call-sites arrastran los imports rotos, y que el generador de settings aplica un criterio de scope distinto al del proyector de archivos.

3. **"Cada instalación queda congelada en la versión del día que se instaló; una parada en marzo, otra de julio."** No reproduce. Las 16 declaran `0.29.39` = `VERSION` del repo y 15 tienen hash idéntico a HEAD en los 43 hooks proyectados. Lo que sí es cierto —y es peor— es que la actualización sólo existe como push desde los git hooks locales del mantenedor: no hay lado pull, y el último `updated_at` es 26 días viejo contra un repo con commits de hoy.

4. **"La cadena de entrega es del 12%: 257 → 155 → 78 → 44 → 31."** Los extremos reproducen (257 en disco, 154 registrados), el medio no: 156 son proyectables por scope, 43 se proyectan en default, y en las 2 instalaciones vivas disparan 33 y 35. El 78 y el 44 no los pude reproducir con ningún comando. Además el ratio confunde dos cosas: **en el repo del propio SO disparan 149 hooks distintos** (17.887 filas). El SO funciona en casa. Lo que falla es la entrega.

5. **"De 17 instalaciones, 3 producen telemetría."** Son 16, y con telemetría real 2 (otras 4 tienen 1-2 filas de ruido de instalación).

6. **Lo que el encargo no menciona y decide el problema:** 12 de las 16 instalaciones son Codex-only. La pregunta del forense no pesa sobre "la alternativa 2 y 3": pesa sobre el 75% del parque instalado.

---

## 8. VERIFICADO / NO VERIFICADO

### VERIFICADO (comando en el cuerpo del informe)
- 16 instalaciones, todas vivas, todas declarando `0.29.39`.
- 5 módulos `cos_lib` faltantes en 15-16 de 16; `ModuleNotFoundError` reproducido.
- Los 4 importadores rotos están en `hooks/cos/_lib/` y se invocan con supresión de stderr (`dispatch-gate.sh:107`, `session-init.sh:276`, `task-panel-sync.sh:33`, `recap-sync.sh:30`).
- El fallback de `dispatch-gate.sh:108` fija `cb_blocked:false` y su campo `error` no lo lee nadie.
- Semilla de la clausura = `hooks/*.sh` (`cos_init.py:1897`); `hooks/_lib/` copiado por `copytree` sin clausura (`:1849`, `:1871`); fail-open documentado en `lib_closure.py:168`.
- `runtime_hook_reality.py` devuelve `fail` con 8 hallazgos sobre `aisotropy`, incluyendo `block-destructive-bash.sh` cableado y ausente.
- El gate sólo se corre contra `tmp_path` con `--harness codex` (`test_consumer_project_projection.py:204`) y está mockeado en `test_cos_architecture_readiness.py`.
- 4 hooks cableados sin archivo en `n1u` y `cienciayjusticia-voting`; 2 de ellos `SCOPE: os-only`.
- 14 de 22 call-sites de copiado sin `scope_allows` próximo.
- `install.sh:14` `TARGET_DIR=".cognitive-os"`; `:416`/`:425` `rm -rf`.
- `auto-update-projects.sh` es `SCOPE: os-only`, disparado por `post-merge`/`pre-push` locales (`setup-git-hooks.sh:198,242,264`); `post-rewrite` ni siquiera está instalado en `.git/hooks/`.
- 12 de 16 instalaciones sin `.claude/settings.json`; las 2 con telemetría real son Claude-wired.
- 257 hooks en disco, 154 registrados, 156 `SCOPE: both/project`, 43 proyectados, 149 disparando en el repo del SO.

### VERIFICADO CON FUENTE EXTERNA (consultadas 2026-08-15)
- Estructura de plugin de Claude Code, `plugin.json`, `hooks/hooks.json`, `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PROJECT_DIR}`, `claude plugin validate [--strict]`, resolución de versión, marketplaces privados, y la migración `.claude/settings.json` → `hooks/hooks.json`: [code.claude.com/docs/en/plugins](https://code.claude.com/docs/en/plugins) y [code.claude.com/docs/en/plugins-reference](https://code.claude.com/docs/en/plugins-reference).
- Que Claude Code **no** verifica la existencia de componentes declarados en rutas custom del manifiesto: misma fuente, sección de validación.
- Hooks de Codex habilitados por defecto (`[features] hooks = false` para desactivar), hooks project-local en `<repo>/.codex/hooks.json` cargando **sólo con la capa `.codex/` confiada**, y plugins de Codex con manifiesto `.codex-plugin/plugin.json`, `hooks/hooks.json` por defecto y variables `PLUGIN_ROOT`/`PLUGIN_DATA`: [learn.chatgpt.com/docs/hooks](https://learn.chatgpt.com/docs/hooks) (redirect 308 desde `developers.openai.com/codex/hooks`).

### NO VERIFICADO
- Si Codex efectivamente ejecuta los `.codex/hooks.json` proyectados por el SO en las 12 instalaciones. Pregunta del forense en paralelo; §6 cubre los tres escenarios. Evidencia indirecta: `metrics/` vacío en las 12.
- Si la capa `.codex/` está confiada en alguno de esos 12 proyectos. No lo chequeé — requiere inspeccionar estado de trust de Codex, fuera del alcance read-only que me fijé.
- El costo real de reescribir los 257 hooks a `${CLAUDE_PLUGIN_ROOT}`. La estimación de 4-6 semanas sale de contar patrones (183 usan `CLAUDE_PROJECT_DIR`, 120 usan `dirname "$0"`), no de haber migrado ninguno.
- Si `FinOpenPOS` (21 hooks divergentes de HEAD) está así por una instalación parcial, una edición local o una actualización a medias. No lo investigué.
- Los números 78 y 44 de la cadena de entrega del encargo. No pude reproducirlos con ningún comando; puede que salgan de una definición de "proyectado"/"cableado" distinta a la que usé.
- No corrí `install.sh` ni la suite de tests, por instrucción explícita del encargo.
