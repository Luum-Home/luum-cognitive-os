# Síntesis del panel de jueces — 2026-08-15

> Cinco jueces independientes, read-only, sobre `luum-agent-os` @ `8602ddc70` (main).
> Cada uno escribió su propio informe; este consolida y resuelve los desacuerdos.
> Todo número acá lleva su informe de origen. Lo que no se midió, se declara.

**Pregunta del operador:** ¿vale la pena, la documentación es consistente, funciona todo?

---

## Veredicto en tres líneas

1. **¿Vale la pena?** Sí, pero **podando** — hay dos consumidores reales y valor medible, sobre 8x más superficie de la que se entrega.
2. **¿La documentación es consistente?** No. 30/100. Pero es deuda **mecánica**, no mentira: se renombró un directorio y no se barrió.
3. **¿Funciona todo?** Compila y arranca. **Instala mal.** La suite de tests quedó **sin medir** (máquina saturada) — no estimada: sin medir.

---

## El hilo que une los cinco informes

**Acá la ausencia no falla: se traga.** Es un solo mecanismo, repetido en cinco capas distintas:

| Capa | Forma que toma | Fuente |
|---|---|---|
| Imports | **61** `try` con import cuyos handlers son todos `pass`, en 42 archivos sobre 3037 `.py` (ver §Correcciones — el 439 del informe de costo-gobernanza **no reproduce**) | recuento propio por AST |
| Shell | `\|\| true` en el wrapper de timing: telemetría a `/.cognitive-os/metrics/`, silencio | funcionamiento |
| Auditores | `cos_doc_path_audit.py` → 2733 findings, `exit 0`. `check_entrypoint_adr_links.py` → 96 links rotos, imprime `ok` | vigencia + docs |
| Instalador | envía un subconjunto y **nunca valida que satisfaga sus propios imports** | funcionamiento |
| Configuración | `phase: reconstruction` desde el commit inicial ⇒ 3 de 4 capas bloqueantes inalcanzables | costo-gobernanza |

Un sistema que se anuncia como *governance layer* y cuyo modo de falla dominante es **fallar en silencio con rc=0** tiene un problema de tesis, no de bugs.

---

## Los números que deciden

### Costo (confirma la acusación del operador)

| Métrica | Valor | Fuente |
|---|---|---|
| Gasto acumulado | **$3.005,18 / 38 sesiones** | costo-gobernanza |
| Por turno | $0,739 | ídem |
| Contexto releído por turno | **374.047 tokens** (96,5% cache read) | ídem |
| Procesos de hook por tool call | ~22 · piso ~3,1 s · `Stop` 25 s | ídem |
| Impuesto fijo por sesión | ~14.749 tokens | ídem |

El OS **sí mide su propio costo** (`cost-events.jsonl`, `is_estimate: false`). El problema no es ceguera: el número está, con cuatro sesiones arriba de $575, y nadie lo mira.

### Gobernanza (confirma la segunda acusación)

**14 declarados / 9 registrados / 9 disparados / 0 que bloquearon.**
29 `exit 2` en 30.515 invocaciones (0,095%), **ninguno del mesh de 14 capas**.

Los cinco hooks que **sí** gobiernan no pertenecen al mesh anunciado. `subagent-budget-enforcer` explica 16 de los 29 bloqueos y produjo dos más durante esta misma auditoría.

### Entrega

Cadena medida, origen → consumidor: **257** en disco → **155** registrados → **78** proyectados → **44** cableados → **31** dispararon. **12%.**
Análogos: `cos_lib` 39/369 · skills 10/197 · scripts 0/741.

### Documentación

Link rot **1744/3095 = 56,3%** · **6 archivos concentran 1197 de los rotos** · **9268** citas a rutas inexistentes en 48,6% de los `.md` · **1020 `.md` (42,9%)** commiteados una sola vez.

### Remediación

**0 de 41 hallazgos del panel del 2026-07-28.** Causa: `git log --all --since=2026-07-29` → **0 commits en 18 días**. No es desidia frente a los hallazgos; el repo se detuvo.

---

## Bugs concretos, con archivo y línea

1. **`--help/`** la creó `scripts/context_budget_meter_fast.py`: `:53` `Path(argv[1]).resolve()` sin `argparse` ni validación → `:72` arma `project/.cognitive-os/metrics` → `:46` `mkdir(parents=True)`. Reproducido en dir vacío: rc=0 y el mismo árbol. **La creó el propio panel anterior** durante su barrido de `--help`, el 2026-07-28 22:41.
2. **`cos-root` no llega al destino.** `hook-timing-wrapper.sh:65` lo invoca; el instalador re-ubica el wrapper sin su dependencia. `PROJECT_DIR` vacío → telemetría a `/.cognitive-os/metrics/` → `|| true`. **36 de 36 hooks** instalados pasan por ahí. Matiz que corrige al consumidor y a este mismo informe en su primera versión: **el timing funcionó y dejó de funcionar** — 141.679 registros hasta el 2026-07-19. "Nunca funcionó" es más fuerte que los datos.
3. **5 módulos no llegan** (`harness_environment`, `record_completion`, `dispatch_model_advisor`, `user_model`, `project_profile_bootstrap`). Dos **sin guarda**: `ModuleNotFoundError` ejecutado, no inferido. Medido aparte sobre `luum-talent` (instalación prístina, no FinOpenPOS): **4 módulos que los hooks importan nunca se empaquetaron** — `capability_levels`, `context_budget`, `performance_monitor`, `process_registry` — y los cuatro fallan callados por `except Exception: pass` en `common.sh:143` y `2>/dev/null || true` en `timing.sh:60`. **19 hooks sourcean `common.sh`.**
4. **`confidentiality-enforcer` falla abierto 2.408 veces en agosto** entre los dos consumidores (`ModuleNotFoundError: cos_lib` → `exit=0`). 26 días de control muerto, con el evento en el propio directorio de métricas.
5. **`check_entrypoint_adr_links.py` normaliza el bug que debería detectar** — resuelve contra `docs/02-Decisions/adrs/` en vez del directorio del archivo. Arreglo de **una línea**.
6. **`safety-mesh.md` se contradice tres veces sobre el mismo número** (capa 11 / 10 / 9 para `auto-rollback-trigger.sh`), se titula "14-Layer" y documenta 12.
7. **`protected-config-write-guard.sh`** hace substring match sobre el texto del comando, no sobre el destino: bloqueó una escritura al scratchpad por contener `hooks/cos/_lib`. Falso positivo.

---

## Correcciones a este mismo panel

Dos números que este panel publicó **no reproducen**, y se corrigen acá con el comando que los mide:

| Publicado | Medido | Comando |
|---|---|---|
| "439 `try/except: pass`" (costo-gobernanza) | **61**, en 42 archivos sobre 3037 `.py` | recuento por AST: `ast.Try` cuyo `body` contiene `Import`/`ImportFrom` y **todos** sus handlers son exactamente `pass` (`scratchpad/recount.py`) |
| "433 referencias a `lib/*.py`, cero resuelven" (costo-gobernanza) | depende del patrón: `rules/` **96**, `docs/` **6580** | `/usr/bin/grep -rEoh 'lib/[a-z_0-9]+\.py' rules/ \| wc -l` |

El fenómeno es real en los dos casos; la cifra publicada no. Un panel cuyo argumento central es *"un número sin comando es opinión con dígitos"* tiene que aceptar el corolario: **un número con comando que no reproduce es peor que uno sin comando**, porque compra credibilidad que no tiene. Mismo defecto que este panel le señaló al del 2026-07-28 (tres off-by-one con cero commits de por medio).

**Corrección a la sesión consumidora:** `cos_lib.providers` **no es dangling**. Existe como paquete (`cos_lib/providers/__init__.py`, `claude_sdk.py`) con 13 importadores. El resto de su triaje de imports no se auditó.

---

## Riesgo destructivo — leer antes de reinstalar

`install.sh:416` y `install.sh:425` hacen **`rm -rf "$TARGET_DIR"`** en el camino `--force` y en el interactivo-sí. **Verificado en este repo.** Borra `.cognitive-os/` completo: `metrics/`, `sessions/`, `runtime/`, `cache/`, `reports/` y cualquier agregado local. Con 16 instalaciones y la telemetría viviendo ahí adentro, un `--force` destruye la única evidencia sobre la que se apoya toda esta auditoría.

Antes de cualquier reinstalación: `cp -R .cognitive-os .cognitive-os.bak`. FinOpenPOS última y a mano — tiene ~19 rutas untracked ahí adentro.

---

## Cobertura de matchers: el control se rodea sin romperlo

Los matchers registrados en `.claude/settings.json` son:

`Agent` · `Bash` · `Bash|Edit|Write` · `Edit|Write` · `Edit|Write|MultiEdit` · `Read` · `Read|Grep|Glob|LS` · `Skill` · `TodoWrite` · dos de engram · uno vacío.

**No hay matcher para `Monitor`, `Task`, `WebFetch`, `WebSearch` ni para el resto de MCP.** La sesión consumidora reportó haber esquivado sin querer su propio rate limiter corriendo trabajo por `Monitor`, que ningún matcher cubre. No derrotaron el control: lo rodearon. Cuarta instancia de la misma familia — **un control cuyo modo de falla es el silencio**.

---

## Desacuerdos del panel, resueltos

| Cuestión | Resolución |
|---|---|
| ¿Cuántos ADRs? | **351 ADRs reales.** Los 501 son archivos `ADR-*.md`, de los cuales 150 son `.synthesis.md`. Los 505 incluyen INDEX/README/STATUS-TAXONOMY/templates. Vigencia midió 350; la diferencia de uno no se arbitró. |
| ¿`confidentiality.yaml` sin `git add`? | **No.** Está ignorado por diseño (`.gitignore:8` → `.cognitive-os/*`). El defecto es que el scanner depende de config que vive donde el contrato dice que nada viaja. Cambia el arreglo. |
| ¿Registraciones fantasma en el origen? | **No.** 162 entradas, 324 refs, **324 resuelven, 0 fantasmas, 0 duplicados**. El defecto está en la traducción de layout al instalar. |
| ¿Todos los auto-auditores son gates falsos? | **No.** `documentation_truth_audit.py` sí está gateado con `--fail-on-block`. Los otros dos no. |
| Caso peor de los imports | **Los dos son reales y son defectos distintos.** El juez de funcionamiento reportó que `circuit_breaker`/`record_completion` "no tiene la forma descrita" y **se equivocó**: el bloque está en `hooks/_lib/dispatch_gate_check.py:172-182`, copia única (verificado con `find` + `readlink -f`, sin symlinks), con los dos imports consecutivos en un solo `try`, `cb.can_launch()` dentro del mismo bloque y un `except` que acumula el error en un string que nadie lee. `record_completion.py` no se envía ⇒ la línea 174 aborta el bloque y el breaker nunca se evalúa. `harness_environment` es peor en severidad —import **sin guarda**, revienta el hook entero— pero no lo reemplaza. |
| ¿`check_test_ratchet.py --help` cuelga? | **Sin arbitrar.** Un juez dice que cuelga a los 20s, otro que ejecuta con exit 0. |

---

## Lo que NO se midió

- **La suite de tests.** Swap 37,6 GB de 38,9 · load 21,27. Correrla habría sido irresponsable. Queda pendiente.
- **El mecanismo de duplicación de registraciones** (98 donde debería haber 36–47). Se localizó el driver `scripts/_lib/settings-driver-claude-code.sh` (614 líneas); no se leyó.
- **Si los 214 hooks podables están rotos o solo no se gatillaron.**
- **Si los consumidores hubieran avanzado igual sin el OS.** Decide el ROI real y ningún comando la contesta.

---

## Orden de trabajo

**Hoy, irreversible si no se hace:** `git push origin main` — 4 commits sin pushear hace 26 días; la última feature existe en una sola máquina.

**Antes de podar** (podar sobre una cadena de entrega que no se sabe medir borra primitivas que nunca dispararon *porque nunca llegaron*):

1. Un self-check de cierre de imports en el instalador — falla el install si un módulo enviado no puede satisfacer sus imports en destino.
2. `cos-root` viaja con su wrapper.
3. Alertar sobre cualquier `*_fail_open`.

**Barato y de alto retorno:**

4. `lib/` → `cos_lib/` en `rules/` (129 archivos, sustitución literal). Es el corpus que entra al contexto de todo agente.
5. Prefijo de los 6 índices peores → liquida 1197 de 1744 links rotos.
6. Superficie pública en un commit: `VERSION`/badge/`package.json`, los 4 badges con `<org>/<repo>`, `npm test`, el hash de `TRANSPARENCY.md`, las 21 entradas falsas del CHANGELOG.

**Decisión del operador, no bug:** elegir la fase, o sacarles el condicional de fase a las capas bloqueantes. Mientras siga en `reconstruction`, el mesh no puede bloquear nada.

**Después:** la poda (216 hooks, 330 módulos, 187 skills, instalaciones inertes) y retención de checkpoints — `aisotropy` tiene 11G en `.cognitive-os`, 440x lo versionado del OS entero (25M).

---

## Criterio de go/no-go, fechado

Al **2026-09-15**, tres condiciones con comando:

- `hooks/*.sh` ≤ 60 — hoy 257
- `scan_error_fail_open` de los últimos 7 días == 0 en ambos consumidores — hoy 126
- un tag con fecha ≥ 2026-08-16 — hoy el último es del 2026-07-20

**Si la segunda sigue > 0 al 2026-09-15, pasa a CONGELAR.** Sin discusión.

Dato que abarata cualquier decisión drástica: **archivar este repo no rompe a los consumidores.** Sus `settings.json` apuntan a su propio `.cognitive-os/`, nunca acá.

---

## Informes de origen

- [judge2-sentido-2026-08-15.md](judge2-sentido-2026-08-15.md) — go/no-go
- [judge2-vigencia-2026-08-15.md](judge2-vigencia-2026-08-15.md) — vigencia de los hallazgos del 2026-07-28
- [judge2-costo-gobernanza-2026-08-15.md](judge2-costo-gobernanza-2026-08-15.md) — costo y gates
- [judge2-docs-2026-08-15.md](judge2-docs-2026-08-15.md) — consistencia documental
- [judge2-funcionamiento-2026-08-15.md](judge2-funcionamiento-2026-08-15.md) — instalación, compilación, entrypoints

Panel anterior, sin commitear, del 2026-07-28: `judge-*-2026-07-28.md` (6 informes).
