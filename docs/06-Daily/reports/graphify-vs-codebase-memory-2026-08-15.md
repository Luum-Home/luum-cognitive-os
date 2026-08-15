# Graphify vs codebase-memory-mcp — ¿duplicación, reemplazo o coincidencia?

- Fecha: 2026-08-15
- Alcance: medición y recomendación. **No se borró ni desregistró nada.**
- Criterio de existencia aplicado: ADR-342.

## Veredicto en una línea

No hay duplicación y no hay reemplazo. **Graphify está escrito, no vivo**: nunca
se lo vio decidir sobre una entrada real, y su dependencia externa no está
instalada en este checkout. El MCP tampoco es un reemplazo: **nunca indexó este
repositorio**. La directiva que manda usarlo primero **no la emite ningún hook
del repo** — vive en el perfil del operador, y en este checkout apunta a un
grafo que no contiene este código.

---

## Correcciones a las premisas del encargo

Cinco de las premisas recibidas no sobrevivieron al recuento.

| # | Premisa del encargo | Estado | Evidencia |
|---|---|---|---|
| 1 | «76 archivos no-doc de graphify» | **Cierto pero engañoso** | El 76 reproduce exacto, pero el grep usó `--include='*.py'` y **la implementación no es `.py`**: los 8 scripts son extensionless kebab-case (`scripts/cos-graphify-build`). El grep nunca vio el código. De los 76, 27 son `.ai/adapters/*/adapter.json` (metadata de proyección) y 10 `.ai/primitives/` (entradas de registro). |
| 2 | «El hook de SessionStart inyecta la directiva» | **Falso** | `grep -rn "Code Discovery Protocol\|tools FIRST\|FIRST for ANY"` sobre el repo → **0 hits**. Ninguno de los 27 hooks de SessionStart registrados la emite. La cadena solo aparece en transcripciones de sesión del perfil del operador. |
| 3 | «codebase-memory aparece en 1 archivo, el doc de investigación de abril» | **Cierto el conteo, falso el referente** | Ese hit es **la cita de un paper de arXiv** (`Codebase-Memory`, arxiv.org/abs/2603.27277) en un inventario de 43 fuentes. No es el MCP server. El repo tiene **cero** referencias al MCP. |
| 4 | «graphify viaja con el SO a los consumidores» (asimetría que justificaría los dos) | **Falso** | `runtime_projection: false` en las 9 entradas del registro; `distribution: team`/`maintainer`; `tag: os-only`; y **sin mención alguna** en `scripts/cos_init.py` ni en `manifests/primitive-install-boundary.yaml`. **Ninguno de los dos viaja.** |
| 5 | Hipótesis del coordinador: «graphify quedó atrás, alguien probó las dos y redirigió» | **Refutada por cronología** | El doc de abril se commiteó el **2026-05-12**; ADR-331 construyó graphify el **2026-05-22**, diez días *después*. Y el doc **no menciona graphify** en ninguna línea. Nadie comparó las dos ni redirigió nada. No hay decisión sin escribir: no hay decisión. |

### Comandos

```bash
# 1
grep -ril graphify --include='*.py' --include='*.sh' --include='*.yaml' --include='*.json' . | grep -v '^./.git/' | wc -l   # 76
find . -path ./.git -prune -o -iname '*graphify*' -print                                                                    # implementación: scripts/cos-graphify-*

# 2
grep -rn "Code Discovery Protocol\|tools FIRST\|FIRST for ANY" . | grep -v '^./.git/'                                       # 0

# 3
grep -n -i -B3 -A12 "codebase-memory" docs/04-Concepts/architecture/primitive-coverage-tooling-research-2026-04.md
grep -n -i "graphify" docs/04-Concepts/architecture/primitive-coverage-tooling-research-2026-04.md                           # 0

# 4
grep -n -i graphify manifests/primitive-install-boundary.yaml scripts/cos_init.py                                            # 0
grep -n -A8 'id: scripts/cos-graphify-build' manifests/agentic-primitive-registry.lock.yaml                                  # runtime_projection: false

# 5
git log --format='%ad %h %s' --date=short -- docs/04-Concepts/architecture/primitive-coverage-tooling-research-2026-04.md    # 2026-05-12
sed -n '1,6p' docs/02-Decisions/adrs/ADR-331-graphify-portable-context-optimization-primitive.md                             # date: 2026-05-22
```

---

## Pregunta 1 — ¿Graphify está vivo o escrito?

**Escrito. Falla la pregunta 4 de ADR-342 (nunca se lo vio decidir sobre una
entrada real) y hoy también falla la 1 (el nombre por el que se invoca no está
publicado en este host).**

### 1.1 ¿Hay un artefacto y existe?

El artefacto principal es `graphify-out/graph.json`
(`scripts/cos-graphify-build:227`). **No existe en ningún lado del repo**: el
único destino que aparece escrito es `/tmp/cos-graphify-manual/` en el
manual-test. Los artefactos persistentes que sí existen están vacíos o viejos:

| Artefacto | Tamaño | Última escritura |
|---|---|---|
| `.cognitive-os/metrics/graphify-context-replay-benchmark.jsonl` | **0 bytes** | 2026-06-12 |
| `.cognitive-os/metrics/graphify-token-reduction-smoke.jsonl` | **0 bytes** | 2026-07-19 |
| `.cognitive-os/reports/graphify-context-replay-benchmark.md` | 1047 bytes | 2026-05-22 |
| `.cognitive-os/reports/graphify-token-reduction-smoke-report.md` | 1188 bytes | 2026-06-12 |

Dos jsonl de métricas de **0 bytes** son la respuesta más limpia: el archivo se
creó, nunca se le escribió una fila.

```bash
stat -f '%Sm %z bytes' -t '%Y-%m-%d %H:%M' .cognitive-os/metrics/graphify-*.jsonl .cognitive-os/reports/graphify-*.md
grep -n 'graph_path' scripts/cos-graphify-build     # línea 227: out_root/"graphify-out"/"graph.json"
find . -name 'graph.json' -not -path './.git/*'     # 0 resultados
```

### 1.2 ¿Algo lo invoca en runtime?

**Nada.** Todas las referencias a `cos-graphify-*` fuera de `docs/` están en
tests (8 archivos) más una lista de patrones en `hooks/so-impact-eval-trigger.sh:56-57`
— y ahí las cadenas `"scripts/cos-graphify"` y `"skills/graphify-query/"` son
**patrones de rutas modificadas** que disparan el smoke de impacto, no una
invocación. El hook no ejecuta graphify.

```bash
grep -rn "cos-graphify" . --include='*.sh' --include='*.py' --include='*.md' --include='*.yaml' --include='*.json' \
  | grep -v '^./.git/' | grep -v '^./docs/' | grep -v '^./tests/' | grep -v __pycache__
# único hit no-test: hooks/so-impact-eval-trigger.sh:56,57 (patrones de path, no invocación)
```

### 1.3 La dependencia externa no está

`scripts/cos-graphify-build:70` resuelve `shutil.which("graphify")`, con fallback
a `uvx --from graphifyy graphify`. **El binario no está en el PATH** y el
fallback tampoco resuelve. En este checkout, `cos-graphify-build` no puede
correr.

```bash
command -v graphify || echo ABSENT          # ABSENT
npx --no-install graphify --version         # npm error: could not determine executable to run
```

Esto es la pregunta 1 de ADR-342 fallando: la primitiva declara un nombre de
herramienta que el host no publica.

### 1.4 Telemetría: cero decisiones

| Fuente | Hits «graphify» | Qué son en realidad |
|---|---|---|
| `so-vitals.jsonl` | 283 | El **inventario de archivos** de métricas (lista los nombres `graphify-*.jsonl`). No son ejecuciones. |
| `tool-sequences.jsonl` | 14 | **Comandos de esta auditoría**, hoy 18:00–18:04. No son históricos. |
| `skill-suggestion.jsonl` | 3 | El router **sugiriendo** el skill, 2026-07-03 → 2026-07-08. Ninguna invocación registrada. |
| `agent-heartbeat.jsonl` | 1 | Mención en un heartbeat. |

**Cero ejecuciones registradas de cualquier `cos-graphify-*` por un hook, skill o
agente, en toda la telemetría.** El 283 es el caso de manual de ADR-342: un
número grande que parece uso y es un censo de nombres de archivo.

```bash
for f in skill-suggestion agent-heartbeat tool-sequences aspirational-audit so-vitals; do
  printf '%-24s %s\n' "$f" "$(grep -ic graphify .cognitive-os/metrics/$f.jsonl)"; done
grep -i graphify .cognitive-os/metrics/tool-sequences.jsonl | head -3   # timestamps de hoy 18:0x = esta sesión
```

### 1.5 Los 12 tests: honestos, pero verdes por la razón equivocada

**No son tests falsos.** Siete de los ocho archivos hacen `subprocess` sobre el
script real y assertean salida real (`reduction_percent >= 20`,
`baseline_input_tokens > preload_input_tokens`, `archive.exists()`). Eso es más
de lo que se encontró en otros lotes de hoy.

Pero **cada aserción corre sobre fixtures sintéticas, ninguna sobre una entrada
real**, y hay dos detalles que importan:

- `test_cos_graphify_build.py:29,40` assertea que `_graphify_invocation` devuelve
  una ruta de binario **bajo mock** — o sea, verifica el armado del comando, no
  que el comando corra.
- `test_cos_graphify_phase_d_semantic.py:36-39` assertea
  `returncode == 2`, `mode == "blocked"`, `backend_ready is False`,
  `status == "blocked-backend-unavailable"`.

Ese último es un test de degradación legítimo, pero tiene una consecuencia
incómoda: **parte de la suite está verde precisamente porque el backend no
está**. Si mañana se instalara `graphify`, ese test seguiría pasando sin haber
probado nunca el camino con backend. 12 tests verdes, 0 entradas reales — que es
exactamente lo que ADR-342 §4 dice que no puede contarse como cobertura.

```bash
grep -hn "assert" tests/unit/test_cos_graphify_*.py
grep -ln "subprocess" tests/unit/test_cos_graphify_*.py   # 7 de 8
```

### 1.6 El repo ya lo sabía

`manifests/primitive-lifecycle.yaml:13758+` y el registry lock clasifican las 9
primitivas de graphify como `lifecycle_state: candidate`, `maturity: advisory`,
`distribution: team`, `runtime_projection: false`. Y dos campos lo dicen textual:

- `consumer_access_next_action:` «Keep as explicit team/advisory tooling until
  release packaging decides whether to project Graphify wrappers.»
- `sunset_criteria:` «Remove when Graphify is replaced by an owned COS context
  graph primitive with equivalent receipts.»

O sea: **la decisión de no proyectarlo ya está escrita**, y el criterio de
retiro también. Lo que falta no es una decisión — es cerrar ADR-331, que sigue en
`implementation_status: partial` desde el 2026-05-22.

---

## Pregunta 2 — ¿Se solapan, y en qué?

Corpus y propósito son distintos. **Graphify es un optimizador de presupuesto de
contexto** (qué archivos precargar antes de un cambio y cuántos tokens ahorra
eso). **El MCP es un motor de recuperación estructural** (quién llama a qué,
dónde está este símbolo). El solapamiento real es una sola capacidad de las
ocho.

Criterio de decisión aplicado (`gates-sin-trampa`): *¿un cambio en uno de los dos
conceptos debería obligar a tocar el otro?*

| Capacidad | Graphify | codebase-memory-mcp | Veredicto |
|---|---|---|---|
| Construir el grafo del repo | `cos-graphify-build` → `graph.json` (requiere binario externo, **ausente**) | `index_repository` (servidor propio, persistente) | **Duplicación real** — misma pregunta, mismo corpus, dos implementaciones |
| Relaciones entre símbolos | `graphify explain <symbol>` | `search_graph`, `query_graph` | **Duplicación real** — sustituibles |
| Camino entre dos símbolos | `graphify path <from> <to>` | `trace_path` | **Duplicación real** — sustituibles |
| Traer el código de un nodo | (no lo tiene) | `get_code_snippet` | Solo MCP |
| Búsqueda de texto/semántica | (no lo tiene) | `search_code` | Solo MCP |
| Vista de arquitectura | (no lo tiene) | `get_architecture` | Solo MCP |
| Gestión de ADRs | (no lo tiene) | `manage_adr` | Solo MCP — y **coincidencia**, el repo ya tiene su propio ciclo de ADR (`cos-adr-close`) |
| **Qué archivos precargar para un cambio** | `cos-graphify-preload-matrix` | (no lo tiene) | **Solo graphify** |
| **Cuántos tokens cuesta / ahorra esa precarga** | `cos-graphify-token-footprint`, `cos-graphify-token-reduction-smoke` | (no lo tiene) | **Solo graphify** |
| **Telemetría real de sesión pareada** | `cos-graphify-run-telemetry`, `cos-graphify-context-replay-benchmark` | (no lo tiene) | **Solo graphify** |
| Hotspots de optimización | `cos-graphify-hotspot-report` | (no lo tiene) | **Solo graphify** |

**Tres capacidades duplicadas, cuatro exclusivas de graphify, cuatro exclusivas
del MCP.** El MCP no tiene ningún concepto de presupuesto de tokens; graphify no
tiene recuperación de código. Un cambio en el modelo de costos de contexto no
obliga a tocar el MCP, y un cambio en el esquema del grafo del MCP no obliga a
tocar el estimador de tokens. **Para 8 de 11 capacidades: coincidencia,
aceptada.** Para las 3 de grafo: duplicación real — pero de una implementación
que no corre contra un servidor que no indexó este repo.

---

## Pregunta 3 — ¿La directiva del hook es correcta?

**La pregunta está mal planteada porque el hook no existe. Y el hallazgo real es
peor que el sospechado.**

### 3.1 No hay hook

Ningún hook del repo emite esa directiva (ver Corrección #2). Vive en la
configuración del perfil del operador. Consecuencia directa: **la directiva
tampoco viaja al consumidor** — el escenario «un consumidor sin ese MCP recibe la
orden de usarlo» no puede ocurrir por esta vía, porque el consumidor no recibe la
orden.

### 3.2 No hay detección ni fallback

```bash
grep -rn -i "codebase.memory\|search_graph\|query_graph" hooks/ scripts/ skills/ cos_lib/   # 0 hits
```

Nada en el repo detecta si el MCP está, nada cae a graphify. Si el MCP falta, el
agente no encuentra las herramientas y cae a `grep`. No hay degradación
diseñada — hay ausencia de diseño.

### 3.3 El MCP nunca indexó este repositorio

Verificado con una llamada read-only al propio MCP:

```
mcp__codebase-memory-mcp__list_projects  →  8 proyectos indexados
```

**Ninguno de los 8 es este repositorio.** (No se citan los nombres: son rutas y
proyectos privados del operador.)

O sea que en este checkout la directiva manda a cada agente a usar «primero» un
grafo que **no contiene este código**. El agente no recibe resultados malos:
recibe resultados vacíos, y cae a `grep`. Es exactamente lo que hizo esta
auditoría — toda la evidencia de este informe salió de `grep`, `find` y `git
log`, ninguna del MCP.

**Esto es el caso de manual de ADR-342 §1**, en la capa de la directiva en vez de
la del hook: una instrucción que nombra una superficie que el host no publica
para este corpus. La diferencia con los casos de hoy es que acá la superficie
existe — pero está vacía para este repo.

---

## Recomendación

**No borrar graphify. No apoyarse más en el MCP. Cerrar la decisión escrita.**

Ordenadas por costo:

**P1 — Cerrar ADR-331 con el estado real (costo: 1 sesión corta).**
ADR-331 está `implementation_status: partial` desde 2026-05-22 con 8 scripts que
nunca corrieron sobre una entrada real y una dependencia externa ausente. Bajo
ADR-342 no puede contarse como cobertura. Las dos salidas honestas son: (a)
instalar `graphifyy`, correr el controlled-trial de
`docs/09-Quality/manual-tests/graphify-controlled-trial.md` y producir el primer
`graph.json` real — con lo cual pasa la pregunta 4 y queda vivo; o (b) marcarlo
`dormant` en el lifecycle, con el motivo escrito, y sacarlo de cualquier cifra de
cobertura. **Señal de operador**: el propio `sunset_criteria` del manifest ya
plantea el retiro, y ADR-342 §«Decision rules» obliga a no contarlo mientras
tanto.

**P2 — La directiva del perfil (acción del operador, fuera del repo).**
Está apuntando a un índice que no cubre este repo. O se indexa el repo con
`index_repository`, o la directiva se acota a los proyectos que sí están
indexados. **No la toqué**: `~/.claude.json` es configuración personal del
operador y está fuera del alcance de este encargo.

**P3 — No hace falta ADR de «reemplazo».** Es la recomendación de no hacer algo:
el hueco de «40 de 173 superficies sin respaldo» no aplica acá, porque no hubo
reemplazo. Escribir un ADR que documente una decisión que nadie tomó sería
inventar la decisión.

### Choque con la política de congelamiento

`manifests/external-tool-adoption-freeze.yaml` está en **`frozen: true` desde
2026-05-11T17:35Z**, por decisión del operador (pivote comercial/SaaS, ADR-267
Gap 1), con cuatro condiciones de descongelamiento (revisión legal de IP,
búsquedas de patente y marca, firma del operador).

**Cualquier recomendación de apoyarse más en codebase-memory-mcp choca con esa
política** y no la hago. Nótese que el freeze gatea rutas de documentación y
`manifests/external-tools-adoption.yaml`; un MCP configurado en el perfil del
operador no pasa por ese gate — que es, en sí, una fuga del mecanismo digna de
mirar aparte: **la política congela la adopción documentada, no la adopción de
hecho vía perfil.**

---

## Lo que este informe NO puede afirmar

- **Si graphify funcionaría bien.** Nunca corrió acá. La única forma de saberlo
  es instalar el binario y correr el controlled-trial. Los receipts de mayo
  (`docs/06-Daily/reports/graphify-phase-*`) afirman que corrió entonces; no los
  reproduje.
- **Si el MCP es mejor.** No indexó este repo, así que no lo comparé sobre este
  corpus. La tabla de capacidades sale de las firmas de las herramientas, no de
  una corrida pareada.
- **Cuándo apareció la directiva en el perfil.** Está fuera del repo y no
  inspeccioné el historial del perfil del operador.

## Referencias

- `docs/02-Decisions/adrs/ADR-342-existence-criterion-for-primitives.md` — criterio aplicado
- `docs/02-Decisions/adrs/ADR-331-graphify-portable-context-optimization-primitive.md` — dueño de graphify, `partial`
- `manifests/primitive-lifecycle.yaml:13758+` — `candidate`/`advisory`, `sunset_criteria`
- `manifests/external-tool-adoption-freeze.yaml` — `frozen: true`
- `docs/04-Concepts/architecture/primitive-coverage-tooling-research-2026-04.md` — la cita de arXiv, no el MCP
- `docs/09-Quality/manual-tests/graphify-controlled-trial.md` — el camino para hacerlo pasar la pregunta 4
