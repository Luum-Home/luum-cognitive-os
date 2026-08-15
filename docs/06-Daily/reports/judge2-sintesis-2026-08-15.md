# Síntesis del panel de jueces — 2026-08-15

> Dieciséis jueces independientes, read-only, sobre `luum-agent-os` @ `8602ddc70`.
> Cada uno escribió su informe; este consolida, resuelve los desacuerdos y corrige
> las cifras que no reprodujeron — incluidas varias que este documento publicó en
> su primera versión.

**Preguntas del operador:** ¿vale la pena? ¿la documentación es consistente?
¿funciona todo? ¿reinventamos mecanismos que ya son estándar?

---

## Veredicto en cuatro líneas

1. **¿Vale la pena?** Sí, **podando** — dos consumidores reales y valor medible, sobre 8x más superficie de la que se entrega. Criterio fechado al 2026-09-15.
2. **¿La documentación es consistente?** No. 30/100. Deuda **mecánica**: el 93,8% de los links rotos apunta a un archivo cuyo basename existe.
3. **¿Funciona todo?** Compila y arranca. **Instala mal.** La suite se corrió recién al cierre de la sesión (ver §Estado final).
4. **¿Reinventamos?** **No.** El repo proyecta hacia AGENTS.md, Agent Skills y MCP. Lo propio cubre la única familia sin estándar (hooks). El riesgo real es otro: **la abstracción no está validada**.

---

## El hilo que une los dieciséis informes

**Acá la ausencia no falla: se traga.** Un solo mecanismo, en seis capas:

| Capa | Forma que toma |
|---|---|
| Imports | **61** `try` con import cuyos handlers son todos `pass`, en 42 archivos |
| Shell | `\|\| true` en el wrapper de timing: telemetría a `/`, silencio |
| Auditores | `cos_doc_path_audit.py` → 2733 findings, `exit 0` · `cos-scope-projection-audit --strict` → `projection_total: 0` |
| Instalador | envía un subconjunto y **nunca valida que satisfaga sus propios imports** |
| Configuración | `phase: reconstruction` desde el commit inicial ⇒ 3 de 4 capas bloqueantes inalcanzables |
| Tests | **62,6% de 922 proofs** cambian el `cwd`, no el árbol de archivos: prueban lo que no importa |

Un sistema que se anuncia como *governance layer* y cuyo modo de falla dominante es **fallar en silencio con rc=0** tiene un problema de tesis, no de bugs.

---

## Los números que deciden

**Costo:** $3.005,18 en 38 sesiones · $0,739/turno · **374.047 tokens de contexto releídos por turno** (96,5% cache read) · ~22 procesos de hook por tool call · piso 3,1 s, `Stop` 25 s.

**Gobernanza:** 14 declarados / 9 registrados / 9 disparados / **0 que bloquearon**. 29 `exit 2` en 30.515 invocaciones, **ninguno del mesh de 14 capas**. Los cinco hooks que sí gobiernan no pertenecen al mesh anunciado.

**Entrega:** 257 en disco → 155 registrados → 78 proyectados → 44 cableados → 31 dispararon = **12%**. Análogos: `cos_lib` 39/369 · skills 10/197 · scripts 0/741.

**Primitivas:** skills 192 existen, 192 alcanzables, **2 invocadas alguna vez**. workflows 7, **0 cableados**. agents 1, **0**. squads 1, **0**. De 32 muestreadas contra su documentación: 13 hacen lo que dicen, 10 hacen menos, 6 hacen otra cosa, **8 no hacen nada**.

**Documentación:** link rot **1744/3095 = 56,3%** · 6 archivos concentran 1197 · **9268** citas a rutas inexistentes en 48,6% de los `.md` · **1020 (42,9%)** commiteados una sola vez.

**Conformidad:** **189 de 194** SKILL.md usan vocabulario que ninguna spec reconoce · 128 descripciones no dicen cuándo usarlas · el repo define 1 subagente y el harness carga **0**.

**Remediación:** **0 de 41** hallazgos del panel del 2026-07-28, porque `git log --all --since=2026-07-29` devolvía **0 commits**. El repo se había detenido — diagnóstico distinto de ignorar los hallazgos.

---

## La respuesta sobre reinvención

| Familia | ¿Hay estándar? | ¿Se usa? | ¿Como lo dicta? |
|---|---|---|---|
| Instrucciones | AGENTS.md (AAIF/Linux Foundation) | Sí | **Sí** |
| Skills | Agent Skills / SKILL.md | Sí | **No** — 6 desvíos duros |
| Hooks | **no existe** | — | Extensión legítima |
| Herramientas | MCP | Sí | Sí, hasta donde se leyó |

**`SCOPE:` no es reinvención pura: es híbrido.** Lo nativo no tiene marca de audiencia por archivo, pero resuelve el mismo problema con otra granularidad — **el plugin es la unidad de distribución**, y ahí el cierre de dependencias es estructural en vez de declarativo. ADR-019 rechazó partir directorios "porque rompería imports y symlinks", y esa decisión es la causa directa de las 18 violaciones de hoy. El ADR **nunca evaluó un mecanismo nativo**: comparó tres alternativas propias entre sí.

**La abstracción multi-harness es el riesgo real:** 27 harnesses registrados, **2** con ciclo de vida nativo, 1 con wrapper, **19 con prueba solo estructural compartiendo un único archivo de test**, y `external-adoption-evidence.yaml` con `reports: []` — **cero instalaciones de terceros**.

**Y el desvío que más cuesta:** `opencode.json > instructions` cargaba los SKILL.md como instrucciones siempre activas — anula el progressive disclosure y duplica, porque OpenCode además descubre `.claude/skills/` nativamente. **Corregido hoy.**

---

## Bugs concretos, con archivo y línea

1. **`--help/`** la creó `scripts/context_budget_meter_fast.py`: `:53` `Path(argv[1]).resolve()` sin validar → `:72` arma `project/.cognitive-os/metrics` → `:46` `mkdir(parents=True)`. La creó el propio panel anterior el 2026-07-28 22:41.
2. **`cos-root` no llega al destino.** `hook-timing-wrapper.sh:65` lo invoca; el instalador re-ubica el wrapper sin su dependencia. **36 de 36 hooks** instalados pasan por ahí. Matiz: el timing **funcionó y dejó de funcionar** — 141.679 registros hasta el 2026-07-19.
3. **`record_completion` → `learning_pipeline` (os-only), a nivel de módulo** → `ImportError` en todo consumidor, tragado por un `except` compartido con `CircuitBreaker`. **El circuit breaker estuvo muerto en toda instalación. Arreglado hoy.**
4. **`confidentiality-enforcer` falló abierto 2.408 veces en agosto** en dos consumidores. 26 días de control muerto.
5. **`manifests/provenance-scan.yaml`** es la denylist de confidencialidad y para funcionar nombra proyectos privados. Se copia con `shutil.copy2` **sin `scope_allows`** (`cos_init.py:1436-1440`), está **trackeada en git** y presente en **16 de 16 instalaciones**, incluidas organizaciones distintas. **Sin resolver.**
6. **`check_entrypoint_adr_links.py`** resuelve contra `docs/02-Decisions/adrs/` en vez del directorio del archivo. Arreglo de una línea.
7. **`safety-mesh.md` se contradice tres veces** sobre la capa de `auto-rollback-trigger.sh` (11 / 10 / 9) y documenta 12 capas bajo un título de 14.
8. **`settings-driver-claude-code.sh`** declara canónico a `cognitive-os.yaml > harness.hooks`, asigna `CONFIG_FILE` y **nunca lo usa**: 184 literales hardcodeados, **36 hooks del YAML nunca se ejecutan**, y su `--check` se compara contra su propio emit.
9. **`lib_closure.py:92-96`** descarta `from cos_lib import x` entero — 6 módulos, 16 usos. Produce imports colgantes en consumidores.
10. **13 call-sites de copiado saltean `scope_allows`**, no 3.

---

## Correcciones a este mismo panel

Un panel que no se corrige a sí mismo no verificó nada. Lo que no reprodujo:

| Publicado | Medido | Por qué falló |
|---|---|---|
| 439 `try/except: pass` | **61** | patrón laxo, sin AST |
| 433 refs a `lib/*.py` | `rules/` 96 · `docs/` 6580 | depende del patrón |
| 20 violaciones de scope | **18 archivos / 20 aristas** | symlinks sin resolver |
| ~75 archivos sin marcador | **70** en `cos_lib` · **144** que aterrizan | dos preguntas distintas |
| ~8 módulos no enviados | **5** (instalación nueva) · **9** (parque instalado) | dos preguntas distintas |
| 8 archivos con `# scope:` minúscula | riesgo **cero** | los 106 tienen mayúscula en la línea 1 |
| 1018/1097 con marcador | **915/990** | symlinks |
| `cos_lib.providers` dangling | **existe**, 13 importadores | — |
| `5ba9de934` fue verde barato | **las dos cosas** | ver abajo |

**Sobre `5ba9de934`:** dos jueces lo declararon corrección legítima, uno dijo ambas cosas. Desempata `cos_init.py:1888-1893`, que **sintetiza un `__init__.py` vacío** si el fuente no está — así que "Python necesita su `__init__.py`" justifica que exista un archivo en el destino, no que se copie el fuente. El gate en rojo lee el marcador en las primeras 8 líneas de lo instalado: editar la línea 1 es la acción más corta que lo apaga sin cambiar lo que viaja.

**El corolario, que vale más que el caso:** un número con comando que no reproduce es peor que uno sin comando, porque compra credibilidad que no tiene.

---

## Lo que se arregló hoy

| Commit | Qué |
|---|---|
| `05a852f7a` | esquema de confidencialidad atado a su parser · plantilla versionada · test de contrato |
| `6bb75a580` | circuit breaker revivido · `cb_evaluated` · gate de clausura de scope |
| `3682bd75a` | tres superficies dejan de afirmar comportamiento que no tienen |
| `f03f7d319` | 19 informes de jueces, incluidos 6 que llevaban 18 días sin commitear |
| `3a6e737ba` | los dos guards de rutas distinguen una fuga de un documento sobre fugas |
| `e8f8e725b` | el gate caza imports colgantes y deja de crashear con clases nuevas |

Más: 125 symlinks absolutos convertidos a relativos, y ~21,9K tokens de carga fija por prompt eliminados de `opencode.json`.

---

## Lo que NO se midió

- **El mecanismo de duplicación de registraciones** (98 donde debería haber 36–47). Localizado el driver, no leído.
- **Si `forbidden_terms` viaja poblada** en las otras 15 instalaciones. Es un `grep -c` y decide la severidad del hallazgo 5.
- **Los 19 harnesses estructurales** en runtime.
- **Si los consumidores hubieran avanzado igual sin el OS.** Decide el ROI real y ningún comando la contesta.

---

## Orden de trabajo

**Antes de podar** — podar sobre una cadena de entrega que no se sabe medir borra primitivas que nunca dispararon *porque nunca llegaron*:

1. Self-check de clausura de imports en el instalador, que **falle la instalación**.
2. `cos-root` viaja con su wrapper, o la dependencia se elimina.
3. Alertar sobre cualquier `*_fail_open`.

**Barato y de alto retorno:** `lib/` → `cos_lib/` en `rules/` (129 archivos, es el corpus que entra al contexto de todo agente) · prefijo de los 6 índices peores (liquida 1197 de 1744 links rotos) · superficie pública en un commit · bajar el número de harnesses de la portada de 22 a 3.

**Decisión del operador, no bug:** elegir la fase. Mientras siga en `reconstruction`, el mesh no puede bloquear nada.

---

## Criterio de go/no-go, fechado

Al **2026-09-15**, cuatro condiciones con comando:

- `hooks/*.sh` ≤ 60 — hoy 257
- `scan_error_fail_open` de 7 días == 0 en ambos consumidores — hoy > 0
- un tag con fecha ≥ 2026-08-16 — hoy el último es del 2026-07-20
- clausura de imports en cero sobre una instalación que no sea FinOpenPOS — hoy 4

**Si la segunda o la cuarta siguen > 0 al 2026-09-15, pasa a CONGELAR.** Sin prórroga.

Dato que abarata cualquier decisión drástica: **archivar este repo no rompe a los consumidores.** Sus `settings.json` apuntan a su propio `.cognitive-os/`.

---

## Informes de origen

**Panel 1 (2026-07-28):** `judge-{adversarial,codigo,documentacion,funcionamiento,primitivas,vale-la-pena}-2026-07-28.md`

**Panel 2 — vigencia y estado:** [sentido](judge2-sentido-2026-08-15.md) · [vigencia](judge2-vigencia-2026-08-15.md) · [costo-gobernanza](judge2-costo-gobernanza-2026-08-15.md) · [docs](judge2-docs-2026-08-15.md) · [funcionamiento](judge2-funcionamiento-2026-08-15.md)

**Panel 3 — primitivas y estándares:** [primitivas](judge3-primitivas-2026-08-15.md) · [scope-reinvención](judge3-scope-reinvencion-2026-08-15.md) · [harness-reinvención](judge3-harness-reinvencion-2026-08-15.md) · [conformidad](judge3-conformidad-2026-08-15.md)

**Panel 4 — la fuga de los sin marcador:** [censo](judge4-fuga-censo-2026-08-15.md) · [triaje](judge4-fuga-triaje-2026-08-15.md) · [default](judge4-fuga-default-2026-08-15.md)

**Panel 5 — verde barato:** [forense](judge5-verde-barato-forense-2026-08-15.md) · [patrón](judge5-verde-barato-patron-2026-08-15.md) · [arreglo](judge5-verde-barato-arreglo-2026-08-15.md)
