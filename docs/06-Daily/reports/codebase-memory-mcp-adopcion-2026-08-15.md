# codebase-memory-mcp — instalar, recomendar, o arreglar la directiva

**Fecha:** 2026-08-15 · **Decisión:** ADR-343 · **Veredicto: recomendar, no instalar** —
y traer la directiva al repo volviéndola condicional.

## Resumen

El encargo ofrecía instalar el MCP desde el SO o recomendarlo. Medido el terreno,
ninguna de las dos era el problema. **El defecto real es una directiva sin
precondición**: existe una orden de "usar las herramientas del grafo PRIMERO" que
vive fuera de este repo, es incondicional, y aplicada acá apunta a un grafo que no
contiene este proyecto. El agente gasta la llamada, descubre que está vacío, y
greppea igual.

Lo que se hizo: un script de detección que responde la precondición, una regla que
la usa, y la excepción al freeze por escrito. Lo que **no** se hizo: instalar nada.

## Qué del encargo era falso

| # | Premisa del encargo | Veredicto | Comando |
|---|---|---|---|
| 1 | «El repo tiene cero referencias al MCP» | **Cierto** — los 7 hits son informes de hoy citándose a sí mismos | `grep -rn "codebase-memory" . \| grep -v '^./.git/'` |
| 2 | «`grep` de la directiva sobre el repo → 0» | **Cierto en lo funcional**: los 2 hits son la cita del grep dentro de un informe | `grep -rn "Code Discovery Protocol\|tools FIRST" . \| grep -v '^./.git/'` |
| 3 | «El MCP nunca indexó este repo» | **Cierto** — 8 proyectos, ninguno es éste | `python3 scripts/check_codebase_memory_readiness.py` |
| 4 | «Verificá cómo se instala: ¿npx? ¿binario? ¿servicio?» | **Las dos cosas.** Hay paquete npm público **y** el binario local está hand-placed | `npm view codebase-memory-mcp version` → `0.10.5`; el binario configurado reporta `0.8.1` |
| 5 | «Cada harness configura MCP distinto, no inventes el formato» | **Cierto, y resulta irrelevante**: el propio binario trae instalador multi-harness para 9 agentes | `codebase-memory-mcp --help` |
| 6 | *(implícito)* «el SO no tiene maquinaria de MCP» | **Falso** — existe desde ADR-231 | `git ls-files \| grep -i mcp` |
| 7 | «El gate del freeze está inerte» | **Cierto, recontado** | `grep -c 'adoption-freeze-gate' .claude/settings.json` → `0`; `.githooks/pre-commit` no existe |
| 8 | *(corrección del coordinador)* «el MCP reemplaza a graphify» | **Falso, y el diseño nunca lo afirmó** | `sunset_criteria` exige un primitive **owned** con receipts equivalentes |

**El hallazgo que más cambió el diseño es el 6.** El SO ya tiene
`manifests/mcp-server-registration.yaml` (ADR-231), la sección `mcp_servers:` de
`manifests/dependencies.yaml`, `scripts/register-mcps.sh` y
`scripts/check_mcp_servers.py` — que **ya detecta este MCP hoy, sin código nuevo**.
Diseñar un mecanismo de detección desde cero habría sido reinvención.

## Instalar vs recomendar — con el motivo

**Instalar es técnicamente posible.** Verificado, no supuesto:

```
npm view codebase-memory-mcp repository.url license
  repository.url = 'git+https://github.com/DeusData/codebase-memory-mcp.git'
  license = 'MIT'
```

Pasa `rules/license-policy` (ALLOW MIT). O sea que el argumento en contra **no** es
que no se pueda.

**Se decide no instalar, por cuatro razones medidas:**

1. **El valor es cero hasta que cada proyecto esté indexado**, y indexar es una
   operación por proyecto, con estado y costo, que el SO no puede hacer en tiempo
   de instalación. Un servidor instalado y sin indexar *es* el defecto de arriba,
   distribuido más ancho.
2. **El instalador es del proveedor y cubre nueve harnesses.** `--help` declara
   auto-detección de Claude Code, Codex CLI, Gemini CLI, Zed, OpenCode,
   Antigravity, Aider, KiloCode y Kiro. Emitir nuestro propio `.mcp.json` /
   `.codex/config.toml` sería afirmar tres contratos de harness contra una
   herramienta que ya implementa los nueve. Hoy mismo apareció en este repo un
   driver de 228 líneas escrito contra un contrato imaginado: el comando de
   instalación correcto es `codebase-memory-mcp install`, no el nuestro.
3. **Radio de explosión**: instalar agrega una dependencia externa y un runtime a
   cada instalación consumidora. Recomendar no rompe nada si el MCP no está.
4. **Nadie midió su eficiencia sobre este repo.** No hay benchmark grafo-vs-grep
   acá, y este repo no está en el grafo. Recomendarlo por "es mejor" sería una
   afirmación sin comando. **El diseño no se apoya en esa afirmación**: se apoya
   en que una directiva no debe dispararse contra un grafo vacío, que sí está
   medido.

**La tercera opción resultó ser la principal**, y las dos se combinan: traer la
directiva adentro volviéndola condicional (arregla un defecto real, no adopta
nada) + recomendar (radio chico, compatible con un freeze activo).

## Qué se implementó y qué se demostró corriendo

### Landed y demostrado

`scripts/check_codebase_memory_readiness.py` — read-only, determinista, sin red,
sin estado de sesión. `0` READY / `1` NOT_READY / `2` ERROR.

La pieza que lo hace posible: el binario tiene modo headless
`codebase-memory-mcp cli <tool> [json]`, así que la precondición se resuelve desde
un script, sin sesión MCP. Un solo comando responde las dos condiciones a la vez
—si corre, el servidor está; su salida dice si este repo está indexado— y por eso
**no hace falta parsear ni inventar el formato de config de ningún harness** para
decidir.

Los tres estados, corridos:

```
$ python3 scripts/check_codebase_memory_readiness.py            # este repo
NOT_READY: codebase-memory-mcp
  server present    True
  project indexed   False
  projects in graph 8
  -> structural-search directive must NOT fire; use grep/Glob.
exit 1

$ COGNITIVE_OS_PROJECT_DIR=<un repo indexado> python3 scripts/check_codebase_memory_readiness.py
READY: codebase-memory-mcp
  project indexed   True
exit 0

$ env HOME=/tmp/nohome-cbm CODEX_HOME=/tmp/nohome-cbm python3 scripts/check_codebase_memory_readiness.py
NOT_READY: codebase-memory-mcp
  server present    False
exit 1
```

Higiene de privacidad: la salida redacta `$HOME` **y** el home real de la cuenta,
así que un `HOME` sobrescrito no filtra la ruta del operador. Verificado:

```
env HOME=/tmp/nohome-cbm python3 scripts/check_codebase_memory_readiness.py 2>&1 \
  | grep -c "$(python3 -c 'import pwd,os;print(pwd.getpwuid(os.getuid()).pw_dir)')"   # 0
```

### Landed

`manifests/external-tool-adoption-freeze.yaml` → bloque `operator_exceptions`.
`frozen`, `unfreeze_requires` y `gated_path_globs` **sin tocar** (verificado por
carga YAML).

### Bloqueado — entregado como parche verificado

`rules/codebase-memory-directive.md` **no se pudo escribir**: `rules/**` es ruta
protegida por `hooks/protected-config-write-guard.sh`, y el env var de aprobación
no alcanza a un agente porque el guard corre en su propio proceso. Va como parche
en `docs/05-Methodology/runbooks/codebase-memory-directive-2026-08-15/`, con la
misma forma que los cuatro precedentes de hoy.

```
git apply --check .../conditional-directive.patch   # aplica limpio, no aplicado
```

**No se probó** que la regla cambie el comportamiento de ningún agente: es
advisory, nada la hace correr, y ningún hook la enforcea. Eso es diseño, no
omisión — cablearla es una decisión aparte, y `hooks/**` un agente no lo escribe.

### No hecho a propósito

- **Sin entrada en `manifests/dependencies.yaml`.** Declararla ahí sin agregarla a
  ningún `mcp_servers_recommended` de perfil habría sido inerte; agregarla a un
  perfil la habría convertido en instalación vía `register-mcps.sh`, que escribe
  en el perfil del operador. Ninguna de las dos es lo decidido.
- **Sin línea en `rules/RULES-COMPACT.md`** — también protegido y editado por
  sesiones concurrentes. **Consecuencia honesta: la regla, una vez aplicada, está
  en disco pero no indexada.**

## Qué pasa cuando el MCP no está, o el proyecto no está indexado

| Estado | Exit | Comportamiento |
|---|---|---|
| Servidor ausente | 1 | La regla no dispara. `Grep`/`Glob`. Nada se rompe, ninguna instalación consumidora gana una dependencia. |
| Presente, proyecto sin indexar | 1 | Igual. **Es el estado de este repo hoy**, y el caso que la directiva incondicional hacía mal. El agente **no** debe indexar por iniciativa propia: indexar es acción del operador. |
| Presente e indexado | 0 | El grafo es primera jugada legítima para preguntas estructurales. |
| Error | 2 | Se trata como NOT_READY y se dice que el chequeo falló. |

## Cobertura multi-harness real

**Verificado:** el script *lee* ubicaciones candidatas de Claude Code y Codex para
descubrir un comando, y usa `PATH` como señal primaria. Que la ruta de
`~/.claude.json` es real está comprobado estructuralmente —aparece en
`discovery_sources`— sin leer ni citar su contenido.

**No verificado, y no hace falta:** opencode, Cursor, Zed, Gemini CLI, Antigravity,
Aider, KiloCode, Kiro. **El script no escribe config para ningún harness**, así que
no afirma ningún contrato. Si algún día el SO emitiera config MCP, primero tiene
que producir manifiestos de esquema con `sources:`/`verified:` y tests de
conformidad, como `manifests/codex-hooks-schema.yaml`.

## Cómo quedó registrada la excepción al freeze

En `manifests/external-tool-adoption-freeze.yaml`, bloque `operator_exceptions`,
id `codebase-memory-mcp-2026-08-15`, apuntando a ADR-343. **No descongela nada.**

El argumento de por qué esto no es una adopción: no se vendorea, portea ni
reimplementa nada upstream — ni código, ni algoritmo, ni esquema. Lo que aterriza
es un script escrito acá y una regla que *restringe* cuándo puede dispararse una
directiva que ya existía. La superficie de IP que el freeze protege no se toca, y
`unfreeze_requires` no se satisface ni se invoca.

Se registra igual porque la decisión del operador es **adyacente** a la política, y
un manifiesto que dice `frozen: true` mientras la práctica adopta es peor que
cualquiera de las dos posturas.

### Los dos agujeros, declarados en el propio manifiesto

1. **`gated_path_globs` no cubre `manifests/dependencies.yaml`** — declarar ahí una
   recomendación de MCP nunca llegaría al gate, ni con el gate cableado.
2. **Un MCP configurado en el perfil no pasa por el gate.** La política congela la
   adopción *documentada*, no la *de hecho*. Este servidor ya es alcanzable en esta
   máquina por ese camino. **Mi implementación NO cierra ese agujero** — cerrarlo
   es una decisión de alcance del operador, no un arreglo de documentación.

Y el enforcer está inerte igual: `hooks/adoption-freeze-gate.sh` no está registrado
ni en `.claude/settings.json` ni en `.githooks/pre-commit` (que no existe). Eso hace
la excepción escrita **más** importante, no menos: no hay mecanismo que la registre.

### Inventario de licencias: sin entrada, a propósito

`manifests/external-tool-licenses.yaml` trackea herramientas *"vendored or ported
into Cognitive OS"*, y `NOTICE` lleva su atribución. Acá no se portea nada, así que
**correctamente no va en ninguno de los dos**. Queda dicho explícito para que una
auditoría futura no lea la ausencia como el hueco de `aider`/`dspy`, donde hay
código genuinamente adoptado que falta en ambos inventarios.

## Relación con Graphify

**No lo reemplaza y no habilita retirarlo.** `manifests/primitive-lifecycle.yaml`
exige, para el sunset, "un primitive de grafo **owned** del COS con receipts
equivalentes". Un MCP de terceros no es owned y no exhibió receipts equivalentes.
Solapamiento medido: 3 de 11 capacidades; las otras 8 no compiten. Conviven.

## ADR

**ADR-343** — `docs/02-Decisions/adrs/ADR-343-codebase-memory-mcp-recommend-only-and-conditional-discovery-directive.md`
`status: accepted`, `implementation_status: partial-blocked`.

Numeración recontada contando archivos sin trackear, y otra vez justo antes de
guardar (`git status --porcelain docs/02-Decisions/adrs/` → vacío; máximo ADR-342).

```
python3 scripts/audit_adr_status_links.py        # 3 hallazgos, todos preexistentes, ninguno de ADR-343
.venv/bin/python -m pytest tests/contracts/test_adr_status_taxonomy.py -q   # 14 passed
.venv/bin/python scripts/generate_adr_index.py   # wrote INDEX.md
.venv/bin/python scripts/cos-adr-partial-ledger  # wrote adr-partial-backlog-latest.{md,json}
```

## Incertidumbres

- **La regla es advisory y no se demostró que cambie conducta de agentes.** Que el
  script decide bien está demostrado; que un agente lo consulte, no.
- **No hay benchmark grafo-vs-grep sobre este repo**, y el diseño deliberadamente
  no depende de que lo haya.
- **La detección del comando** se apoya en `PATH` y en un puñado de rutas de config;
  un harness que lo registre en otro lado daría falso NOT_READY. El fallback de un
  falso NOT_READY es `grep`, o sea que falla del lado seguro.
