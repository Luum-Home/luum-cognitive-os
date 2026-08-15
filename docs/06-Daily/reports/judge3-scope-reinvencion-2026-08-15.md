# Juez 3 — ¿El mecanismo `SCOPE:` reinventa la rueda?

**Fecha:** 2026-08-15
**Alcance:** read-only sobre `luum-agent-os` @ `8602ddc70` (working tree sucio de otra sesión, no tocado)
**Lente:** ¿`# SCOPE: os-only | project | both` duplica algo que Claude Code ya ofrece nativamente?
**Condiciones:** máquina degradada (swap 36.9 GB / 37.9 GB, load 12.7). Sin suite de tests. Mediciones por greps acotados y un script propio.

---

## 1. Veredicto

**`HÍBRIDO — apoyarse en el nativo y conservar solo la parte que falta`.**

El nativo no tiene ninguna marca por archivo de "esto es para desarrollar el SO" vs "esto se entrega al consumidor", así que `SCOPE:` **no es un duplicado de una feature existente**. Pero el nativo sí resuelve el mismo problema en otra granularidad — el **plugin** es la unidad de distribución — y esa forma de resolverlo hace que el cierre de dependencias sea estructural en vez de declarativo. El mecanismo propio eligió explícitamente no partir directorios (ADR-019 rechazó la separación por directorios "porque rompería imports, symlinks y referencias"), y esa decisión es la causa directa de los 18 archivos rotos que se miden abajo: un comentario de cabecera no puede sostener un grafo de imports.

Lo que queda del lado propio es real y no tiene equivalente nativo: `cos_lib/*.py` no es un tipo de componente de Claude Code, el nativo no tiene nada que decir sobre él, y ahí viven 6 de las 18 violaciones.

---

## 2. Mapeo contra lo nativo

| Qué resuelve `SCOPE:` | Mecanismo nativo equivalente | ¿Lo cubre? | Fuente |
|---|---|---|---|
| Que una skill de mantenimiento del SO no aparezca en un proyecto consumidor | Plugin como unidad de distribución + marketplace privado ("To keep a plugin internal to your team, host the marketplace in a private repository") | **Sí, pero por plugin entero**, no por archivo. Requiere partir el árbol en dos plugins | `code.claude.com/docs/en/plugins` (consultado 2026-08-15) |
| Separar "mío" de "del proyecto" | `~/.claude/skills` (personal) vs `.claude/skills` (proyecto) vs plugin namespaceado | **No — es otro eje.** Es *dónde se instala*, no *para quién es*. Un archivo os-only del SO vive en el repo del SO, no en `~/.claude` | `code.claude.com/docs/en/skills` (2026-08-15) |
| Apagar/prender primitivas por proyecto | `enabledPlugins` en la jerarquía managed → user → project → local | **Parcial.** Prende/apaga plugins enteros, y es decisión del consumidor, no del que publica | `code.claude.com/docs/en/plugins-reference` (2026-08-15) |
| Excluir archivos concretos del paquete que se entrega | **No existe.** No hay ignore-file estilo `.gitignore`, ni allowlist `files` en `plugin.json`, ni flag de visibilidad por componente | **No** | `plugins-reference` (2026-08-15) |
| Elegir qué subdirectorio de skills/agents/hooks se publica | Campos `skills` / `commands` / `agents` / `hooks` del manifiesto apuntando a rutas | **Sí, a nivel directorio**, y solo para esos tipos de componente | `plugins-reference` (2026-08-15) |
| Que una skill exista pero no la invoque el modelo | `disable-model-invocation: true` en el frontmatter | **No es lo mismo** — es visibilidad en sesión, el archivo igual se entrega | `code.claude.com/docs/en/skills` (2026-08-15) |
| Que un módulo Python de librería (`cos_lib/*.py`) no viaje al consumidor | **Nada.** `cos_lib` no es un tipo de componente de Claude Code; el nativo solo conoce `skills/`, `agents/`, `hooks/`, `commands/`, `.mcp.json`, `.lsp.json`, `monitors/`, `bin/`, `settings.json` | **No** | `code.claude.com/docs/en/plugins` §"Plugin structure overview" (2026-08-15) |
| Gobernanza de la organización sobre qué se puede instalar | Managed settings: `strictKnownMarketplaces`, `blockedMarketplaces`, `permissionRules` con `from_plugin(...)` | **Sí, del lado del consumidor** — no ayuda al que publica a decidir qué mete en el paquete | `plugins-reference` (2026-08-15) |

**Lectura de la tabla.** De ocho cosas, el nativo cubre bien dos (distribución del paquete, gobernanza del consumidor), cubre parcialmente dos (habilitación, selección de subdirectorios) y no cubre cuatro. Las cuatro que no cubre comparten una característica: **granularidad por archivo dentro de un árbol compartido**. El nativo asume que si dos cosas viven en el mismo plugin, van juntas.

---

## 3. Salud del mecanismo propio

### 3.1 Cobertura de marcadores

Sobre archivos regulares `.py`/`.sh` en `cos_lib/`, `scripts/`, `hooks/` (sin symlinks, sin `__pycache__`), leyendo **las primeras 3 líneas**, que es exactamente lo que lee `scope_allows`:

```bash
find cos_lib scripts hooks -type f \( -name '*.py' -o -name '*.sh' \) -not -path '*/__pycache__/*' \
 -exec sh -c 'v=$(head -3 "$1" | grep -oE "(# SCOPE:|<!-- SCOPE:) *[a-zA-Z_/-]+" | head -1 | sed "s/.*: *//"); echo "${v:-SIN-MARCADOR}"' _ {} \; \
 | sort | uniq -c | sort -rn
```

| Valor | Archivos |
|---|---|
| `os-only` | 478 |
| `both` | 423 |
| `project` | 14 |
| **sin marcador** | **75** |
| **Total** | **990** |

Cobertura: **92.4 %** (915 / 990).

**Qué pasa con los 75 sin marcador: se proyectan.** `scripts/cos_init.py:294` — *"No SCOPE header → include unconditionally"*. El default es entregar. En `cos_lib/` hay 69 sin marcador, entre ellos `maintainer_experiment.py`, `maintainer_proposals.py`, `public_claim_gate.py`, `cross_stack_adoption_truth.py`, `language_dependence_audit.py`. Por el nombre parecen os-only; por el mecanismo, viajan al consumidor. Es una fuga silenciosa en la dirección opuesta a la que el mecanismo dice cuidar.

### 3.2 Violaciones del contrato

**18 archivos marcados `both`/`project` importan un módulo `cos_lib` marcado `os-only`. 20 aristas.** Script reproducible (read-only, determinista, exit 0 sin hallazgos / 1 con hallazgos):

```bash
python3 - <<'PY'
import re, sys
from pathlib import Path
REPO = Path(".").resolve()
PAT = re.compile(r'(?:# SCOPE:|<!-- SCOPE:)\s+([a-zA-Z_/-]+)')
def scope(p):
    try:
        with p.open(encoding="utf-8", errors="replace") as f:
            head = [f.readline() for _ in range(3)]
    except OSError:
        return "SIN"
    for l in head:
        m = PAT.search(l)
        if m:
            return m.group(1).strip()
    return "SIN"
files = [p for d in ("cos_lib", "scripts", "hooks") for p in (REPO / d).rglob("*")
         if p.is_file() and not p.is_symlink() and p.suffix in (".py", ".sh")
         and "__pycache__" not in p.parts]
sc = {p: scope(p) for p in files}
osm = {p.stem for p in files if p.suffix == ".py" and "cos_lib" in p.parts and sc[p] == "os-only"}
IP = re.compile(r'^\s*(?:from\s+(?:cos_lib|lib)\.([A-Za-z_]\w*)|import\s+(?:cos_lib|lib)\.([A-Za-z_]\w*))', re.M)
v = []
for p in files:
    if sc[p] not in ("both", "project"):
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    h = {(m.group(1) or m.group(2)) for m in IP.finditer(t)} & osm
    if h:
        v.append((str(p.relative_to(REPO)), sc[p], sorted(h)))
print(f"archivos={len(files)} modulos_os_only={len(osm)} violadores={len(v)} aristas={sum(len(x[2]) for x in v)}")
for f, s, m in sorted(v):
    print(f"  {f} [{s}] -> {', '.join(m)}")
sys.exit(1 if v else 0)
PY
```

Salida (2026-08-15):

```
archivos=990 modulos_os_only=89 violadores=18 aristas=20
  cos_lib/agent_context_injector.py [both] -> memory
  cos_lib/model_router.py [both] -> gateway_selector
  cos_lib/openai_compatible_agent_loop.py [both] -> smart_truncator
  cos_lib/primitive_fitness.py [both] -> dogfood_scorer, kpi_collector
  cos_lib/record_completion.py [both] -> learning_pipeline, mlflow_bridge
  cos_lib/record_error.py [both] -> learning_pipeline
  scripts/cos_agent_message.py [both] -> script_helpers
  scripts/cos_cleanup_preserved_wip.py [both] -> script_helpers
  scripts/cos_remote_branch_triage.py [both] -> script_helpers
  scripts/cos_session_coordination.py [both] -> script_helpers
  scripts/cos_task_claims.py [both] -> script_helpers
  scripts/cos_worktree_triage.py [both] -> script_helpers
  scripts/doc_review_personas.py [both] -> doc_review_personas
  scripts/document_feature_append.py [project] -> document_feature_writer
  scripts/documentation_truth_audit.py [both] -> script_helpers
  scripts/domain_model.py [project] -> domain_model
  scripts/ops_runbook.py [project] -> ops_runbook
  scripts/project_shell_ci.py [both] -> script_helpers
```

**No son imports perezosos ni guardados.** Verificado uno por uno en los cuatro casos más representativos: `cos_lib/record_error.py:6` (`from cos_lib.learning_pipeline import LearningPipeline`), `cos_lib/primitive_fitness.py:16`, `scripts/cos_task_claims.py:12` son imports duros a nivel de módulo. Solo `cos_lib/model_router.py:539` es diferido dentro de una función. En un consumidor donde el módulo `os-only` no fue proyectado, los primeros tres explotan al importar.

`script_helpers` solo explica 7 de las 18. Es el ofensor único más grande.

### 3.3 El comportamiento está documentado en el código como bug conocido

`scripts/cos_init.py:1898-1909`, comentario textual:

> `A `both`/`project`-scoped hook that only works via an os-only module is a real dependency bug in that hook, not a reason to leak the os-only module — skip it here (the existing static-closure-miss fail-open backstop in lib_closure.py already tolerates modules that are absent from the projected package).`

Y `scripts/lib_closure.py:168-170`:

> `# Static-closure miss (§2.3): module referenced but not present on disk. Skip — the fail-open backstop covers this at runtime.`

Es decir: se sabe que el caso existe, se decidió **no** taparlo filtrando el módulo os-only (bien), y se decidió tolerarlo con un fail-open (discutible), pero **no se construyó el detector que encuentra los casos**. La clase de bug está nombrada en un comentario y no medida en ningún lado.

### 3.4 Gates: existen dos, y ninguno verifica esto

| Gate | Qué verifica | Estado hoy |
|---|---|---|
| `.githooks/pre-commit` gate 3g → `scripts/cos-scope-both-portability-audit --strict` | Que todo artefacto `SCOPE: both` tenga un test emparejado en `tests/red_team/portability/` | **Activo, bloquea commits** |
| `.githooks/pre-commit` gate 3g → `scripts/cos-scope-projection-audit --strict` | Marcadores válidos, proof emparejada, rutas hardcodeadas, y *opcionalmente* fuga de os-only en una instalación consumidora | **Corre y da verde: `findings: []`** |
| Cierre de dependencias `both` → `os-only` | — | **No existe** |

Corrida propia:

```bash
python3 scripts/cos-scope-projection-audit --repo-root . --strict --no-write --json
# EXIT=0, "findings": [], "projection_root": null, "install_smoke": {"status": "not-requested"}
```

El gate da verde con `projection_root: null` — o sea, en el pre-commit el escaneo de fuga sobre una instalación real **no se ejecuta**. Solo verifica el árbol fuente.

### 3.5 Las 923 "portability proofs" no prueban portabilidad de proyección

Hay 909 `test_*.py` en `tests/red_team/portability/`. El pre-commit bloquea si falta uno. Contenido real de la proof de un archivo violador (`tests/red_team/portability/test_record_error.py`):

```python
def test_record_error_imports_from_arbitrary_project_root(tmp_path, monkeypatch):
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))   # ← el repo COMPLETO en el path
    ...
    spec.loader.exec_module(module)
```

El test importa el módulo con **el repo entero en `sys.path`**, donde `learning_pipeline.py` sí existe. Prueba que el import no depende del `cwd`. **No prueba que el módulo sobreviva a la proyección**, que es el invariante que el nombre del gate sugiere. En una instalación consumidora real, donde `learning_pipeline.py` no se copió, ese mismo import falla y esta proof nunca se entera.

206 de 909 proofs usan ese patrón `sys.path.insert(0, str(REPO_ROOT))`. Es el caso de manual de gate con verde barato: la etiqueta dice "portability proof", el gate bloquea por su ausencia, y la aserción mide otra cosa.

### 3.6 Resumen de salud

| Dimensión | Valor |
|---|---|
| Cobertura de marcadores | 92.4 % (915/990) |
| Archivos sin marcador (se entregan por default) | 75 |
| Módulos `cos_lib` `os-only` | 89 |
| Archivos `both`/`project` con dependencia `os-only` | **18** (4.1 % de los 437 `both`+`project`) |
| Aristas rotas | 20 |
| De esas, imports duros a nivel de módulo | 17 de 20 |
| Gate que detecta la clase de bug | **ninguno** |
| Gates que existen y dan verde igual | 2 |

El mecanismo **funciona en su eje principal**: 478 archivos os-only efectivamente no se proyectan, y el contrato de fuga (que no aparezca un marcador `os-only` en la instalación consumidora) sí tiene test — `tests/contracts/test_primitive_scope_governance.py:149`, que hace una instalación real por harness. Lo que falla es el eje complementario: nada verifica que lo que **sí** se proyecta sea autosuficiente.

---

## 4. Correcciones a las premisas del encargo

1. **"1018 de 1097 archivos tienen marcador SCOPE"** — inflado por symlinks. `cos_lib/` tiene ~70 symlinks a `packages/`, y `find` sin `-type f` los cuenta doble. Sobre archivos regulares: **915 de 990 (92.4 %)**. La cobertura real es un poco peor de lo declarado, no mejor.

2. **"90 módulos de `cos_lib` son os-only"** — **89** contando solo archivos regulares. Diferencia menor, mismo orden.

3. **"20 archivos marcados `both`/`project` importan un módulo `os-only`"** — **18 archivos, 20 aristas**. El fenómeno se confirma; el conteo de archivos estaba un poco alto porque dos archivos aportan dos aristas cada uno.

4. **"y nada lo detecta"** — **correcto en lo esencial, pero la premisa subestima lo que sí hay.** Existen dos gates activos en `.githooks/pre-commit`, 909 tests de portabilidad, un audit de proyección con instalación real por harness, y cinco ADRs (019, 306, 314, 320, 321). El mecanismo tiene bastante más infraestructura de la que sugiere el encargo. Lo que no existe es el detector específico de cierre de dependencias — y eso, con toda esa infraestructura alrededor, es peor señal que la ausencia total: hay una sensación de cobertura que no se corresponde con lo cubierto.

5. **"`cos_init.py:298` bloquea os-only para instalaciones project/both"** — correcto (la línea exacta es 298 en la rama `scope_val == "os-only" → return False`).

6. **Sobre la premisa del operador ("reinventó la rueda")** — **no del todo**. El nativo no tiene marca de audiencia por archivo. La ADR-019 sí evaluó alternativas (separación por directorios, filtrado en runtime, no hacer nada), pero **ninguna de las tres es un mecanismo nativo de Claude Code**: en 2026-04-13 la decisión se tomó sin contrastar contra plugins ni marketplaces. Eso es un hueco del proceso de decisión, no prueba de reinvención.

---

## 5. VERIFICADO vs NO VERIFICADO

### Verificado en este repo (comandos arriba, reproducibles)

- 990 archivos regulares `.py`/`.sh` en `cos_lib`/`scripts`/`hooks`; 478 `os-only`, 423 `both`, 14 `project`, 75 sin marcador.
- `scope_allows` lee **solo las 3 primeras líneas** y devuelve `True` ante ausencia de marcador (`scripts/cos_init.py:255-300`).
- 18 archivos `both`/`project` con 20 aristas hacia módulos `cos_lib` `os-only`; 17 de esas aristas son imports duros a nivel de módulo.
- `scripts/cos_init.py:1898-1909` documenta el caso como "a real dependency bug", decide no filtrar y delega en un fail-open.
- `scripts/lib_closure.py:168-170` salta los static-closure miss por diseño.
- `cos-scope-projection-audit --strict --no-write` sale 0 con `findings: []` y `projection_root: null`.
- `tests/red_team/portability/test_record_error.py` importa con `sys.path.insert(0, str(REPO_ROOT))`; 206 de 909 proofs usan ese patrón.
- `tests/contracts/test_primitive_scope_governance.py:149` hace instalación real por harness y verifica que no haya marcadores `os-only` proyectados.
- ADR-019 "Alternatives Considered" no menciona ningún mecanismo nativo de Claude Code.

### Verificado contra documentación externa (consultada 2026-08-15)

- El plugin es la unidad de distribución; empaqueta `skills/`, `agents/`, `hooks/`, `commands/`, `.mcp.json`, `.lsp.json`, `monitors/`, `bin/`, `settings.json`. — `https://code.claude.com/docs/en/plugins`
- Para mantener un plugin interno al equipo: marketplace en repo privado. — mismo doc, §"Share your plugins"
- Escopos de instalación `user` / `project` / `local` / `managed`, con `enabledPlugins` y precedencia managed → `--settings` → user → project → local. — `https://code.claude.com/docs/en/plugins-reference`
- **No existe** ignore-file estilo `.gitignore` para plugins, ni allowlist `files` en `plugin.json`, ni flag de visibilidad interno/privado por componente. — `plugins-reference`
- Los campos `skills`/`commands`/`agents`/`hooks` del manifiesto permiten seleccionar rutas (el primero suma al default, los otros lo reemplazan). — `plugins-reference`
- Skills personales `~/.claude/skills` vs de proyecto `.claude/skills` vs de plugin (namespaceadas `/plugin:skill`); `disable-model-invocation` controla invocación, no distribución. — `https://code.claude.com/docs/en/skills`

### NO verificado

- **Si la instalación consumidora efectivamente rompe.** No corrí `cos_init.py --default` en un directorio limpio para ver si los 18 archivos fallan al importar. La máquina está a 97 % de swap y la instrucción era no correr suites. La conclusión "explota al importar" es una inferencia de leer los imports y el fail-open, no una observación. **Es el primer experimento a correr.**
- **Los 75 archivos sin marcador**: no clasifiqué uno por uno si deberían ser `os-only`. La lectura de nombres (`maintainer_experiment`, `maintainer_proposals`, `public_claim_gate`) es indicio, no veredicto.
- **`packages/`**: la medición cubre `cos_lib`/`scripts`/`hooks`. No medí `packages/*/lib` ni `packages/*/hooks`, donde ADR-019 declara ~75 SKILL.md adicionales.
- **Skills y rules**: `skill_scope_allows` y el filtrado de `rules/` y `templates/` no fueron medidos. El conteo de violaciones es solo del plano Python.
- **ADR-306, 314, 320, 321**: leí solo ADR-019 completo. Los otros cuatro pueden contener decisiones que cambien la lectura de §3.3 y §3.4.
- **Costo real de migrar a dos plugins**: no estimado. La afirmación de que "el cierre sería estructural" es arquitectónica, no medida.

---

## 6. Tres acciones, en orden

**1. Correr la instalación consumidora contra los 18 archivos y ver si rompen.** Es el desempate de todo el informe: si los 18 explotan al importar en un consumidor, esto es deuda entregada a clientes; si el fail-open los degrada silenciosamente, es deuda de comportamiento. Cuando baje el swap:

```bash
git worktree add /tmp/wt-scope HEAD && cd /tmp/wt-scope
mkdir /tmp/consumer && cd /tmp/consumer
python3 /tmp/wt-scope/scripts/cos_init.py --default --harness claude
# para cada uno de los 18: intentar importarlo desde la proyección
```

**2. Convertir el script de §3.2 en gate.** El detector ya está escrito y da exit 1 hoy. Va a `scripts/` con nombre propio y se engancha al gate 3g de `.githooks/pre-commit`, junto a los dos audits que ya están. Con baseline en 18 y ratchet descendente — no con baseline en 25 "por si acaso", que sería el colchón que la norma de gates prohíbe. Esto cierra la clase de bug que `cos_init.py:1901` nombra y nadie mide.

**3. Decidir el eje grueso antes de seguir puliendo el fino.** La pregunta que el operador tiene que contestar, y que ADR-019 nunca contestó porque en 2026-04 se decidió sin mirar el nativo: **¿el SO se entrega como plugin?** Si sí, el corte os-only/consumidor se apoya en el límite del plugin (dos plugins, o uno público más un marketplace privado), el cierre de dependencias pasa a ser estructural, y `SCOPE:` se achica al residuo genuino — `cos_lib/*.py`, que el nativo no modela. Si no se entrega como plugin, `SCOPE:` queda como extensión legítima y hay que bancarla con el gate del punto 2 más el barrido de los 75 sin marcador. Las acciones 1 y 2 valen en los dos escenarios; ésta las ordena.
