# Auditoría de costo: qué cuesta tener el SO instalado

**Fecha:** 2026-08-15
**Alcance:** las 21 carpetas con `.cognitive-os/` bajo `~/Projects`
**Lente:** costo. El valor lo mide otro juez; acá está el número solo.
**Modo:** read-only. No se corrió `install.sh`, no se corrió la suite, no se escribió en ningún repo consumidor.

---

## 1. Veredicto

**El costo no depende de tener el SO instalado: depende de si el harness lo proyecta.**
De las 17 instalaciones reales, **10 cuestan exactamente cero bajo Claude Code** (no tienen
`.claude/`: ni contexto inyectado, ni hooks). Las 4 que sí están cableadas a Claude Code
pagan **~1.000 tokens fijos por prompt** y **~0,5–0,85 s de latencia de hooks por tool call**.
El único lugar donde hay dólares medidos es el repo del SO: **$3.005,18 en 10 sesiones /
4.069 turnos = $0,7386 por turno, $300,52 por sesión** — y ahí el impuesto fijo de markdown
es **el 1,08%** de lo que realmente se re-lee por turno.

---

## 2. Tabla por cohorte

Cohorte = `distribución | harness | versión | fecha de instalación`.
`inj_tok` = impuesto fijo por prompt (estimación bytes/4). `disco_tok` = reglas presentes
pero NO inyectadas. `hooks/call` = hooks que disparan en una llamada a Bash (estático,
resuelto contra los matchers del driver activo). `filas` = invocaciones de hook registradas.

| Cohorte | n | inj_tok | disco_tok | wired | hooks/call | filas telemetría | USD medido |
|---|--:|--:|--:|--:|--:|--:|--:|
| `core \| codex \| 0.29.39 \| 2026-07-20` | 10 | 358 | 21.674 | 17 | 5 | 0 | 0,00 |
| `core \| claude \| 0.29.39 \| 2026-07-20` | 3 | 1.024 | 43.699 | 78 | 16 | 141.679 | 0,00 |
| `core \| claude \| 0.29.26 \| 2026-06-05` | 1 | 842 | 43.586 | 47 | 12 | 2.210 | 0,00 |
| `core \| agents-md \| 0.29.39 \| 2026-07-20` | 1 | 568 | 21.397 | 0 | 0 | 0 | 0,00 |
| `full \| codex \| 0.29.39 \| 2026-07-20` | 1 | 1.536 | 113.201 | 41 | 8 | 0 | 0,00 |
| `standard \| claude \| d9ecd3e \| 2026-03-31` | 1 | 0 | 15.841 | 24 | 5 | 0 | 0,00 |
| `none \| source \| — ` (el repo del SO) | 1 | 2.888 | 10.866 | 162 | 21 | 11.986 | **3.005,18** |
| residuos (no son instalaciones) | 3 | 0 | 0 | 0 | 0 | 0 | 0,00 |

### Lo que dice cada cohorte

**`core|codex` (10 instalaciones — la mayoría).** Es la cohorte dominante y **bajo Claude Code
no cuesta nada**: no existe el directorio `.claude/`, las reglas quedan en
`.cognitive-os/rules/cos/` sin proyectar, y los 16–20 hooks están cableados en
`.codex/hooks.json`, que Claude Code no lee. Bajo Codex sí cuesta: 16 hooks cableados,
5 por llamada a bash. Cero filas de telemetría en las 10.

**`core|claude` (4 instalaciones: aisotropy, n1u, cienciayjusticia-voting, FinOpenPOS).**
Es la cohorte que realmente paga. Impuesto fijo ~842–1.166 tokens por prompt
(`.claude/CLAUDE.md`, 4,6 KB). 38 a 100 hooks cableados. 9 hooks por llamada a Bash,
7 por Edit/Write, 2 por Read, 1 por Grep/Task. Solo 2 de las 4 tienen telemetría.

**`full|codex` (luum-lang).** Único caso de distribución `full`: 112 reglas en disco
(113.201 tokens de material) contra 15 en `core`. **5,2x el peso en disco** de una
instalación `core`, con 41 hooks cableados. Cero telemetría: el peso está, el uso no.

**`standard|d9ecd3e` (rbvm-platform).** Fósil de 2026-03-31, cuatro meses y medio sin
reinstalar, con un identificador de versión que es un SHA y no un semver. 24 hooks
cableados, cero contexto inyectado, cero telemetría.

**`source` (el repo del SO).** No es una instalación, es el origen — y es la única fuente
de dólares duros. 162 hooks cableados: **21 disparan en cada llamada a Bash**, contra 9
en un consumidor `claude`. Es el caso más caro que existe y no describe a ningún consumidor.

---

## 3. Las tres preguntas separadas

El encargo pide no mezclarlas. No se mezclan.

### 3a. Costo por sesión

| | Fuente | Valor |
|---|---|---|
| Repo del SO (dato duro) | `cost-events.jsonl`, `is_estimate:false` | **$300,52 / sesión** (10 sesiones, 4.069 turnos) |
| Repo del SO (latencia) | `hook-timing.jsonl` | 6.751 s de hooks en 189 arranques = **35,7 s/sesión** |
| Consumidor `claude` (aisotropy) | `hook-timing.jsonl` | 19.102 s en 263 arranques = **72,6 s/sesión**, 538 invocaciones/sesión |
| Consumidor `claude` (dólares) | — | **NO MEDIDO**: ningún consumidor escribe `cost-events.jsonl` |

Las sesiones del SO varían tres órdenes de magnitud: de $2,29 (12 turnos) a $834,18
(889 turnos). El promedio de $300,52 no describe a ninguna; **$0,7386 por turno sí**,
porque el costo escala con turnos, no con sesiones.

### 3b. Costo por tool call

Dos componentes. La latencia está medida; los tokens no.

| Cohorte | hooks por Bash | p50 por hook | latencia serie | wall total medido |
|---|--:|--:|--:|--:|
| `core\|claude` (aisotropy) | 9 | 94 ms | ~846 ms | 14.453 s en 135.938 invocaciones |
| `core\|claude` (FinOpenPOS) | 12 | 136 ms | ~1.632 ms | 316 s en 2.089 invocaciones |
| `core\|codex` | 5 | sin datos | — | 0 |
| `source` (repo del SO) | 21 | 170 ms | ~3.570 ms | 2.791 s en 10.884 invocaciones |

Cruce de sanidad en aisotropy: 14.453 s de wall de hooks sobre ~27.000 tool calls estimadas
da **~535 ms por tool call**, del mismo orden que los 846 ms del cálculo estático en serie.
La diferencia es que los hooks corren en paralelo, así que **846 ms es techo, no realidad**.

**Los tokens que los hooks inyectan por tool call NO están medidos.** `hook-timing.jsonl`
registra duración y exit code, nunca el tamaño del stdout. Lo más cerca que hay es
`truncation-events.jsonl` (175 filas), que solo aparece cuando el `result-truncator`
recorta algo por encima de ~5K caracteres.

El cola larga importa más que la mediana: el evento `Stop` en aisotropy tiene **p95 de
11.992 ms**, y en el repo del SO 10.457 ms. Casi doce segundos de espera en el 5% peor
de los turnos, al final de cada turno.

### 3c. Costo acumulado histórico

| Instalación | Ventana | Acumulado |
|---|---|---|
| Repo del SO | 2026-07-02 → 2026-08-15 (44 días) | **$3.005,18** duros + $0,71 en 28 filas estimadas |
| Los otros 20 | — | **$0,00 registrados** — ninguno instrumenta costo |

De los $3.005,18: **96,5% del input facturado es cache read**. Se re-leen 374.047 tokens
por turno desde cache, y el total facturado como input son 387.480 tokens por turno.

---

## 4. Método de estimación, y qué es duro y qué no

### Estimación de tokens — declarada

`tokens = bytes / 4`. Es la **misma heurística que usan los tests del propio SO**
(`tests/unit/test_efficiency_stress.py`: `len(content) / 4`), elegida a propósito para que
los números de este informe sean comparables contra los presupuestos declarados ahí.
**Es una estimación**, no un conteo con tokenizador: subestima markdown denso en símbolos
y sobreestima prosa. No se usó tokenizador real porque implicaba traer una dependencia
para medir una cota que se compara contra presupuestos ya expresados en la misma unidad.

### Qué es medición dura

- **Los $3.005,18, los 4.069 turnos, y el desglose de tokens.** Vienen de
  `cost-events.jsonl` con `is_estimate:false` y `pricing_known:true`, producidos por
  `token-usage-normalizer.v1` a partir de los transcripts. El script no re-deriva pricing:
  usa los dólares que el normalizador ya calculó.
- **Latencias e invocaciones de hooks.** `hook-timing.jsonl`, un registro por invocación
  con `duration_ms` real.
- **Hooks cableados y fan-out por herramienta.** Se resuelven los matchers del driver
  activo contra el nombre de la herramienta. Es lectura de configuración, no muestreo.
- **Presencia/ausencia de `.claude/`, reglas proyectadas y bytes en disco.** `stat`.

### Qué es estimación

- **Todo número en tokens que salga de bytes/4**, incluido el impuesto fijo por prompt.
- **La "latencia en serie"** de la tabla 3b: multiplica fan-out por p50 asumiendo ejecución
  secuencial. Los hooks corren en paralelo, así que es un **techo**.
- **Las ~27.000 tool calls de aisotropy**: derivadas de dividir invocaciones por fan-out
  ponderado según una mezcla supuesta de herramientas. Orden de magnitud, no cuenta.
- **Los tokens de `context-budget.jsonl`** son estimaciones que hizo el propio medidor del
  SO, registradas por evento real. Evento duro, magnitud estimada.

### Lo que directamente no se pudo medir

- **Tokens inyectados por hook.** No hay instrumentación. Es el agujero grande: el
  segundo componente del costo por tool call no existe como dato.
- **Bytes que `SessionStart` inyecta al contexto.** Medir esto exigía ejecutar los 27 hooks
  de `SessionStart`, y el primero es `self-install.sh`, que escribe symlinks. Read-only gana.
  Sí está medida su **latencia**: p50 303 ms, p95 2.037 ms en el repo del SO.
- **Dólares en cualquier consumidor.** Nadie los registra.

---

## 5. Correcciones a las premisas del encargo

**1. "38 sesiones" → son 10.**
38 es el número de filas de `cost-events.jsonl`, no de sesiones. 28 de esas filas son
estimaciones blandas (`is_estimate:true`, `source:record_completion`) que suman **$0,71 en
total**. Los $3.005,18 salen de las **10 filas duras**, que agregan 4.069 turnos.
Mezclarlas infla el denominador casi 4x.

**2. "$0,739/turno" → correcto.** $0,7386. Se sostiene.

**3. "374.047 tokens de contexto releídos por turno (96,5% cache read)" → correcto, con un
matiz.** 374.047 es exactamente `cache_read / turnos`, y el 96,5% es la porción que ese
cache read representa del input facturado. El input facturado completo es **387.480 tokens
por turno**. Son dos números distintos y conviene no cruzarlos.

**4. "El test que falla es tu mejor aliado" → el test no mide el SO.**
Ésta es la corrección que más cambia el veredicto. `test_claude_md_token_budget` mide
`Path.home() / ".claude" / "CLAUDE.md"` — el **archivo global personal del operador**, que
el instalador nunca escribe ni toca. Hoy pesa 22.020 B ≈ **5.505 tokens** (creció desde los
5.453 citados). **Cero por ciento de ese exceso es atribuible a instalar el SO.**
El presupuesto combinado de 7.000 está igual de mal repartido: hoy da **8.393 tokens**, de
los cuales 5.505 son del archivo global del operador y **2.888 del SO** (`RULES-COMPACT.md`).
La parte que el SO controla es el **34%**, y por sí sola está holgadamente bajo los 7.000.
El presupuesto declarado existe, sí, pero apunta mayormente a un archivo que el instalador
no gobierna.

**5. "47.554 invocaciones de hook en 18 días" → no reproducible.**
Ninguna instalación devuelve ese par. La telemetría de consumidor más grande es aisotropy:
**141.679 filas en `hook-timing.jsonl` sobre 10 días** (14.168/día) y 98.095 filas en
`hook-health.jsonl` sobre 36 días. Puede que el número original sea previo a una rotación
de métricas (existe `tests/integration/test_metrics_rotation.py`), pero con los archivos
de hoy no se reconstruye.

**6. "las 21 instalaciones" → son 17 instalaciones, 1 repo fuente y 3 residuos.**
- `~/Projects/luum/.cognitive-os` — 8 archivos, solo `cache/` y `sessions/`. Es contaminación
  del directorio padre, no una instalación.
- `~/Projects/luum/cognitive-os-demo/.cognitive-os` — 8 archivos, sin `install-meta.json`.
- `~/Projects/luum/luum-agent-os/--help/.cognitive-os` — **un directorio llamado `--help`**,
  creado por una invocación de CLI que tomó el flag como ruta. Aparece como `?? --help/`
  en el `git status` del repo del SO. Es basura, y conviene borrarla antes de que alguien
  la cuente como instalación otra vez.

**7. La premisa de fondo: "cuánto cuesta tener esto instalado" asume que instalarlo cuesta.**
Para 10 de las 17 instalaciones reales, bajo Claude Code, **el costo es exactamente cero**:
son `harness: codex`, no tienen `.claude/`, y sus hooks viven en un driver que Claude Code
no lee. La pregunta correcta no es por instalación sino **por proyección de harness**.

---

## 6. Dos hallazgos de costo que el encargo no pedía

**El impuesto fijo de markdown es el 1% del problema.** En el repo del SO, medido contra
el propio system prompt de esta sesión, se inyectan **9.956 tokens** por prompt:

| Archivo | Bytes | Tokens (est.) | Dueño |
|---|--:|--:|---|
| `~/.claude/CLAUDE.md` | 22.020 | 5.505 | operador |
| `rules/RULES-COMPACT.md` | 11.551 | 2.888 | SO |
| `rules/rate-limiting.md` (contextual) | 4.572 | 1.143 | SO |
| `~/.claude/rules/context7.md` | 1.679 | 420 | operador |
| **Total** | **39.822** | **9.956** | |

De esos, 4.031 son del SO. Contra los **374.047 tokens que se re-leen por turno**, el
impuesto fijo del SO es el **1,08%**. El 98,9% restante es acumulación de conversación y
salida de herramientas. **Recortar `RULES-COMPACT.md` a la mitad bajaría la factura un 0,4%.**
El presupuesto de tokens vigila el 1% barato mientras el 99% no tiene gate.

**14 de 21 tienen hooks cableados y cero telemetría.** Incluye `n1u` con **100 hooks**
cableados y `cienciayjusticia-voting` con **97** — cero invocaciones registradas en ambas.
Además el manifiesto miente sobre el cableado en 13 instalaciones: `install-meta.json`
declara `hooks_installed: 43` donde el driver activo cablea 16 (gap de 27), y en `luum-lang`
declara 155 contra 41 cableados (gap de 114). El campo cuenta **archivos copiados**, no
entradas cableadas, y se lee como si contara lo segundo. Si alguien audita cobertura de
hooks por el manifiesto, ve 43 donde corren 16.

---

## 7. Evidencia ejecutable

```bash
# Corrida completa sobre las 21 (1,1 s, read-only)
python3 cost_per_install.py --root ~/Projects --depth 4

# Solo el resumen por cohorte
python3 cost_per_install.py --quiet

# JSON para pipeline
python3 cost_per_install.py --json
```

Exit codes: `0` sin hallazgos · `1` hay hallazgos (instalación cableada sin telemetría, o
presupuesto de contexto excedido) · `2` error. La corrida de hoy devuelve **1**.

Reproducción de los números duros sin el script:

```bash
cd ~/Projects/luum/luum-agent-os
python3 - <<'PY'
import json
h=[json.loads(l)['payload'] for l in open('.cognitive-os/metrics/cost-events.jsonl')]
h=[p for p in h if p.get('is_estimate') is False]
t=sum(p['turn_count'] for p in h); cr=sum(p['cache_read_input_tokens'] for p in h)
cc=sum(p['cache_creation_input_tokens'] for p in h); i=sum(p['input_tokens'] for p in h)
usd=sum(p['actual_cost_usd'] for p in h)
print(f"sesiones={len(h)} turnos={t} usd={usd:.2f} usd/turno={usd/t:.4f}")
print(f"cache_read/turno={cr//t} input_total/turno={(cr+cc+i)//t} share={cr/(cr+cc+i)*100:.1f}%")
PY
```

Salida: `sesiones=10 turnos=4069 usd=3005.18 usd/turno=0.7386` /
`cache_read/turno=374047 input_total/turno=387480 share=96.5%`

---

## 8. El script

`cost_per_install.py` — read-only, determinista, sin estado de sesión, exit 0/1/2.
Vive en el scratchpad y va pegado entero acá por la norma de durabilidad del artefacto.

```python
#!/usr/bin/env python3
"""cost_per_install.py — What does it cost to have the Cognitive OS installed?

READ-ONLY. Opens no repo for writing, runs no installer, mutates nothing.

Measures four cost dimensions per install, grouped by cohort:

  1. FIXED CONTEXT TAX  — bytes/tokens the SO injects into every prompt before
                          the agent does anything. STATIC estimate (bytes/4).
  2. PER-TOOL-CALL COST — how many hooks fire per tool call (static, from the
                          settings driver + matchers) and how long they take
                          (MEASURED, from hook-timing.jsonl).
  3. HARD MEASURED COST — actual_cost_usd from cost-events.jsonl rows with
                          is_estimate=false and pricing_known=true. HARD.
  4. STARTUP COST       — SessionStart hook latency (MEASURED) and the
                          injected-token estimates recorded by the SO's own
                          context meter (context-budget.jsonl).

Cohort = (active_distribution, harness, version, install date).

Usage:
    python3 cost_per_install.py [--root DIR] [--depth N] [--json] [--quiet]

Exit codes:
    0 — ran clean, no budget findings
    1 — findings (an install exceeds a declared context budget, or a cohort
        carries wired hooks with zero telemetry = paying without running)
    2 — error (bad root, unreadable tree)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Declared budgets. Source: tests/unit/test_efficiency_stress.py in the SO repo
#   test_claude_md_token_budget      -> 3500 tokens for ~/.claude/CLAUDE.md
#   test_total_always_loaded_budget  -> 7000 tokens for CLAUDE.md + RULES-COMPACT
# NOTE: both budgets are asserted against the OPERATOR's *global* file, which
# the installer never writes. Reported here separately, not charged per install.
# ---------------------------------------------------------------------------
BUDGET_GLOBAL_CLAUDE_MD_TOKENS = 3500
BUDGET_ALWAYS_LOADED_TOKENS = 7000

# Estimation constant. Declared, not measured: 4 bytes per token is the
# same heuristic the SO's own tests use (`len(content) / 4`), so the numbers
# here are comparable to the budgets above. It is an ESTIMATE.
BYTES_PER_TOKEN = 4.0

# Tool names probed for the static per-tool-call hook fan-out.
PROBE_TOOLS = ["Bash", "Edit", "Write", "Read", "Task", "Grep"]


def est_tokens(nbytes: int) -> float:
    """Estimate tokens from bytes. ESTIMATE — bytes/4, see BYTES_PER_TOKEN."""
    return nbytes / BYTES_PER_TOKEN


def safe_bytes(path: Path) -> int:
    """Size of a regular file, following symlinks. 0 if absent/unreadable."""
    try:
        if path.is_file():
            return path.stat().st_size
    except OSError:
        pass
    return 0


def read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def iter_jsonl(path: Path, limit: int | None = None):
    """Stream a JSONL file. Tolerates truncated/corrupt trailing lines."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if limit is not None and i >= limit:
                    return
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except ValueError:
                    continue
    except OSError:
        return


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
def discover_installs(root: Path, depth: int) -> list[Path]:
    """Find every project dir containing .cognitive-os/, up to `depth`."""
    found: list[Path] = []
    root = root.resolve()
    for dirpath, dirnames, _ in os.walk(root):
        rel_depth = len(Path(dirpath).relative_to(root).parts)
        if rel_depth >= depth:
            dirnames[:] = []
            continue
        # never descend into heavy or vendored trees
        dirnames[:] = [
            d for d in dirnames
            if d not in {"node_modules", ".git", "vendor", "dist", "build", "__pycache__"}
        ]
        if ".cognitive-os" in dirnames:
            found.append(Path(dirpath))
    return sorted(found)


# ---------------------------------------------------------------------------
# Hook wiring (static)
# ---------------------------------------------------------------------------
def count_wired_hooks(settings_path: Path) -> tuple[int, dict[str, int]]:
    """Count hook entries actually wired in a settings/hooks driver file."""
    data = read_json(settings_path)
    if not isinstance(data, dict):
        return 0, {}
    hooks = data.get("hooks", data)
    if not isinstance(hooks, dict):
        return 0, {}
    per_event: dict[str, int] = {}
    total = 0
    for event, matchers in hooks.items():
        if not isinstance(matchers, list):
            continue
        n = 0
        for m in matchers:
            if isinstance(m, dict):
                n += len(m.get("hooks", []) or [])
        if n:
            per_event[event] = n
            total += n
    return total, per_event


def hooks_firing_for_tool(settings_path: Path, tool: str) -> int:
    """How many Pre/PostToolUse hooks fire for one call to `tool`.

    A matcher is an ERE against the tool name; empty/'*' matches everything.
    This is the STATIC per-tool-call fan-out.
    """
    data = read_json(settings_path)
    if not isinstance(data, dict):
        return 0
    hooks = data.get("hooks", data)
    if not isinstance(hooks, dict):
        return 0
    fired = 0
    for event in ("PreToolUse", "PostToolUse"):
        for m in hooks.get(event, []) or []:
            if not isinstance(m, dict):
                continue
            pattern = (m.get("matcher") or "").strip()
            if pattern in ("", "*"):
                match = True
            else:
                # Case-insensitive: harnesses disagree on tool casing
                # (Claude Code emits "Bash", the codex driver matches "bash").
                try:
                    match = re.search(pattern, tool, re.IGNORECASE) is not None
                except re.error:
                    match = pattern.lower() == tool.lower()
            if match:
                fired += len(m.get("hooks", []) or [])
    return fired


# ---------------------------------------------------------------------------
# Dimension 1 — fixed context tax
# ---------------------------------------------------------------------------
def context_tax(project: Path, harness: str) -> dict[str, Any]:
    """Bytes the SO puts in front of the agent, split by whether the ACTIVE
    harness actually loads them.

    injected  — loaded unconditionally on every prompt by the active harness
    on_disk   — present but NOT projected into the harness (loaded on demand,
                or not at all: the install is paying disk, not context)
    """
    injected: dict[str, int] = {}
    on_disk: dict[str, int] = {}

    claude_dir = project / ".claude"
    cos_dir = project / ".cognitive-os"

    # Claude Code unconditionally loads: <proj>/CLAUDE.md and <proj>/.claude/CLAUDE.md
    claude_md_root = safe_bytes(project / "CLAUDE.md")
    claude_md_dot = safe_bytes(claude_dir / "CLAUDE.md")
    # AGENTS.md is the driver for the agents-md harness (and read by codex)
    agents_md = safe_bytes(project / "AGENTS.md")
    # Project-instruction rules the SO registers at repo root
    rules_compact = safe_bytes(project / "rules" / "RULES-COMPACT.md")

    claude_active = harness in ("claude", "auto", "unknown", "source")
    # AGENTS.md is the driver ONLY for the agents-md/codex harnesses. Claude Code
    # does not load it: verified against a live session in the SO source repo,
    # whose injected project instructions were rules/RULES-COMPACT.md and a
    # contextual rule — AGENTS.md was absent. Charging it to `source` would
    # inflate the fixed tax by ~2,800 tokens that are never sent.
    agents_active = harness in ("agents-md", "codex")

    def put(name: str, nbytes: int, live: bool) -> None:
        if nbytes <= 0:
            return
        (injected if live else on_disk)[name] = nbytes

    put("CLAUDE.md", claude_md_root, claude_active)
    put(".claude/CLAUDE.md", claude_md_dot, claude_active)
    put("AGENTS.md", agents_md, agents_active)
    put("rules/RULES-COMPACT.md", rules_compact, claude_active)

    # Projected rule set: .claude/rules/cos/*.md is on disk for the agent to
    # read on demand. It is NOT auto-injected unless imported from CLAUDE.md,
    # so it is charged as on-disk potential, never as fixed tax.
    for label, rules_dir in (
        ("claude/rules/cos", claude_dir / "rules" / "cos"),
        ("cognitive-os/rules/cos", cos_dir / "rules" / "cos"),
    ):
        total = 0
        try:
            for f in rules_dir.glob("*.md"):
                total += safe_bytes(f)
        except OSError:
            pass
        if total:
            on_disk[label] = total

    inj_bytes = sum(injected.values())
    disk_bytes = sum(on_disk.values())
    return {
        "injected_files": injected,
        "injected_bytes": inj_bytes,
        "injected_tokens_est": round(est_tokens(inj_bytes)),
        "on_disk_files": on_disk,
        "on_disk_bytes": disk_bytes,
        "on_disk_tokens_est": round(est_tokens(disk_bytes)),
    }


# ---------------------------------------------------------------------------
# Dimension 2/4 — measured hook telemetry
# ---------------------------------------------------------------------------
def pctl(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, int(len(sorted_vals) * q))
    return sorted_vals[idx]


def hook_telemetry(cos_dir: Path) -> dict[str, Any]:
    """MEASURED: invocation counts and latency per hook event."""
    path = cos_dir / "metrics" / "hook-timing.jsonl"
    by_event: dict[str, list[float]] = defaultdict(list)
    distinct: dict[str, set] = defaultdict(set)
    sessions: set = set()
    rows = 0
    for r in iter_jsonl(path):
        rows += 1
        event = r.get("event") or "?"
        by_event[event].append(float(r.get("duration_ms") or 0))
        distinct[event].add(r.get("hook"))
        sid = r.get("session_id")
        if sid:
            sessions.add(sid)
    out: dict[str, Any] = {"rows": rows, "sessions_seen": len(sessions), "events": {}}
    for event, durations in by_event.items():
        s = sorted(durations)
        out["events"][event] = {
            "invocations": len(s),
            "distinct_hooks": len(distinct[event]),
            "p50_ms": round(pctl(s, 0.50)),
            "p95_ms": round(pctl(s, 0.95)),
            "total_ms": round(sum(s)),
        }
    health = cos_dir / "metrics" / "hook-health.jsonl"
    out["health_rows"] = sum(1 for _ in iter_jsonl(health))
    return out


def injected_context_measured(cos_dir: Path) -> dict[str, Any]:
    """MEASURED-BY-THE-SO: per-injection token estimates the SO's own context
    meter recorded. Still a token ESTIMATE, but recorded per real event."""
    path = cos_dir / "metrics" / "context-budget.jsonl"
    n: Counter = Counter()
    tok: Counter = Counter()
    for r in iter_jsonl(path):
        src = r.get("source") or "?"
        n[src] += 1
        tok[src] += float(r.get("tokens_estimate") or 0)
    return {
        src: {"events": n[src], "avg_tokens": round(tok[src] / n[src])}
        for src in n
    }


# ---------------------------------------------------------------------------
# Dimension 3 — hard measured dollars
# ---------------------------------------------------------------------------
def hard_cost(cos_dir: Path) -> dict[str, Any]:
    """HARD: rows with is_estimate=false and pricing_known=true."""
    path = cos_dir / "metrics" / "cost-events.jsonl"
    hard: list[dict] = []
    soft_rows = 0
    soft_usd = 0.0
    for r in iter_jsonl(path):
        p = r.get("payload") or {}
        if p.get("is_estimate") is False and p.get("pricing_known"):
            hard.append({"ts": r.get("timestamp"), **p})
        else:
            soft_rows += 1
            soft_usd += float(p.get("estimated_cost_usd") or 0)

    if not hard:
        return {"sessions": 0, "soft_rows": soft_rows, "soft_usd": round(soft_usd, 4)}

    usd = sum(float(h.get("actual_cost_usd") or 0) for h in hard)
    turns = sum(int(h.get("turn_count") or 0) for h in hard)
    cache_read = sum(int(h.get("cache_read_input_tokens") or 0) for h in hard)
    cache_create = sum(int(h.get("cache_creation_input_tokens") or 0) for h in hard)
    inp = sum(int(h.get("input_tokens") or 0) for h in hard)
    out = sum(int(h.get("output_tokens") or 0) for h in hard)
    total_in = cache_read + cache_create + inp
    return {
        "sessions": len(hard),
        "usd_total": round(usd, 2),
        "turns": turns,
        "usd_per_turn": round(usd / turns, 4) if turns else 0,
        "usd_per_session": round(usd / len(hard), 2),
        "cache_read_tokens": cache_read,
        "cache_creation_tokens": cache_create,
        "input_tokens": inp,
        "output_tokens": out,
        # Two different "context re-read" numbers — do not mix them:
        #   cache_read_per_turn  = context re-fed from cache each turn
        #   input_total_per_turn = everything billed as input (cache+fresh)
        "cache_read_per_turn": round(cache_read / turns) if turns else 0,
        "input_total_per_turn": round(total_in / turns) if turns else 0,
        "cache_read_share": round(cache_read / total_in, 4) if total_in else 0,
        "first": min(h["ts"] for h in hard),
        "last": max(h["ts"] for h in hard),
        "soft_rows": soft_rows,
        "soft_usd": round(soft_usd, 4),
    }


# ---------------------------------------------------------------------------
# Per-install assembly
# ---------------------------------------------------------------------------
def analyze(project: Path) -> dict[str, Any]:
    cos_dir = project / ".cognitive-os"
    meta = read_json(cos_dir / "install-meta.json") or {}

    harness = meta.get("harness")
    if not harness:
        # No install-meta: this is either the SO source repo itself or a bare
        # directory. Infer from what is actually wired, not from the manifest.
        if count_wired_hooks(project / ".claude" / "settings.json")[0] > 0:
            harness = "source" if (project / "hooks" / "self-install.sh").exists() else "claude"
        elif meta:
            harness = "unknown"
        else:
            harness = "none"
    driver_rel = meta.get("settings_driver") or ".claude/settings.json"
    driver = project / driver_rel

    claude_settings = project / ".claude" / "settings.json"
    codex_hooks = project / ".codex" / "hooks.json"

    wired_active, per_event = count_wired_hooks(driver)
    wired_claude, _ = count_wired_hooks(claude_settings)
    wired_codex, _ = count_wired_hooks(codex_hooks)

    tax = context_tax(project, harness)
    tel = hook_telemetry(cos_dir)
    hard = hard_cost(cos_dir)
    inj = injected_context_measured(cos_dir)

    fanout = {t: hooks_firing_for_tool(driver, t) for t in PROBE_TOOLS}

    # per-tool-call latency: static fan-out x measured p50 of the tool events
    pre = tel["events"].get("PreToolUse", {})
    post = tel["events"].get("PostToolUse", {})
    p50 = pre.get("p50_ms") or post.get("p50_ms") or 0
    bash_fanout = fanout.get("Bash", 0)

    installed_at = meta.get("installed_at") or ""
    cohort = "|".join([
        meta.get("active_distribution") or meta.get("mode") or "none",
        harness,
        str(meta.get("version") or "none"),
        installed_at[:10] or "none",
    ])

    return {
        "project": str(project),
        "name": project.name,
        "cohort": cohort,
        "harness": harness,
        "distribution": meta.get("active_distribution") or meta.get("mode") or "none",
        "version": meta.get("version") or "none",
        "installed_at": installed_at,
        "meta_claims": {
            "rules": meta.get("rules_installed"),
            "hooks": meta.get("hooks_installed"),
            "skills": meta.get("skills_installed"),
        },
        "wired_hooks_active_driver": wired_active,
        "wired_hooks_per_event": per_event,
        "wired_hooks_claude": wired_claude,
        "wired_hooks_codex": wired_codex,
        "context_tax": tax,
        "tool_call_fanout": fanout,
        "per_tool_call": {
            "bash_hooks": bash_fanout,
            "hook_p50_ms": p50,
            "serial_latency_ms_est": round(bash_fanout * p50),
        },
        "telemetry": tel,
        "hard_cost": hard,
        "measured_injections": inj,
        # a wired install with zero telemetry is paying setup for nothing
        "dormant": wired_active > 0 and tel["rows"] == 0,
        # manifest claims hooks the active driver does not actually wire
        "manifest_gap": (meta.get("hooks_installed") or 0) - wired_active,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def redact(path_str: str) -> str:
    home = str(Path.home())
    return path_str.replace(home, "~")


def global_context_check() -> dict[str, Any]:
    """The declared budgets are asserted against the OPERATOR's global file,
    which the installer does not write. Measured once, charged to nobody."""
    g = Path.home() / ".claude" / "CLAUDE.md"
    gb = safe_bytes(g)
    gt = est_tokens(gb)
    return {
        "global_claude_md_bytes": gb,
        "global_claude_md_tokens_est": round(gt),
        "budget": BUDGET_GLOBAL_CLAUDE_MD_TOKENS,
        "over_budget": gt >= BUDGET_GLOBAL_CLAUDE_MD_TOKENS,
        "installer_owns_this_file": False,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(Path.home() / "Projects"),
                    help="tree to scan for .cognitive-os/ installs")
    ap.add_argument("--depth", type=int, default=4, help="max scan depth")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    ap.add_argument("--quiet", action="store_true", help="cohort summary only")
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser()
    if not root.is_dir():
        print(f"ERROR: root not found: {redact(str(root))}", file=sys.stderr)
        return 2

    try:
        projects = discover_installs(root, args.depth)
    except OSError as exc:
        print(f"ERROR: scan failed: {exc}", file=sys.stderr)
        return 2

    if not projects:
        print(f"No .cognitive-os/ installs under {redact(str(root))}", file=sys.stderr)
        return 2

    installs = [analyze(p) for p in projects]
    gctx = global_context_check()

    if args.json:
        print(json.dumps(
            {"global_context": gctx,
             "installs": [{**i, "project": redact(i["project"])} for i in installs]},
            indent=2))
    else:
        print("=" * 100)
        print(f"COST PER INSTALL — {len(installs)} installs under {redact(str(root))}")
        print("=" * 100)
        print()
        print("SHARED CONTEXT (not charged per install — installer does not own it)")
        print(f"  ~/.claude/CLAUDE.md : {gctx['global_claude_md_bytes']:>8,} B  "
              f"~{gctx['global_claude_md_tokens_est']:>6,} tok  "
              f"budget {gctx['budget']:,}  "
              f"{'OVER' if gctx['over_budget'] else 'ok'}")
        print()

        if not args.quiet:
            print("PER INSTALL")
            hdr = (f"{'install':<34}{'harness':<10}{'dist':<8}"
                   f"{'wired':>6}{'inj_tok':>9}{'disk_tok':>10}{'hookrows':>10}{'usd':>10}")
            print(hdr)
            print("-" * len(hdr))
            for i in sorted(installs, key=lambda x: (x["cohort"], x["name"])):
                usd = i["hard_cost"].get("usd_total", 0)
                print(f"{i['name'][:33]:<34}{i['harness'][:9]:<10}{i['distribution'][:7]:<8}"
                      f"{i['wired_hooks_active_driver']:>6}"
                      f"{i['context_tax']['injected_tokens_est']:>9,}"
                      f"{i['context_tax']['on_disk_tokens_est']:>10,}"
                      f"{i['telemetry']['rows']:>10,}"
                      f"{usd:>10,.2f}")
            print()

        # ---- cohort roll-up ----
        print("BY COHORT  (distribution | harness | version | install date)")
        cohorts: dict[str, list[dict]] = defaultdict(list)
        for i in installs:
            cohorts[i["cohort"]].append(i)

        hdr = (f"{'cohort':<44}{'n':>3}{'inj_tok':>9}{'disk_tok':>10}"
               f"{'wired':>7}{'bash/call':>10}{'hookrows':>10}{'usd':>11}")
        print(hdr)
        print("-" * len(hdr))
        for cohort in sorted(cohorts):
            group = cohorts[cohort]
            n = len(group)
            inj = sum(g["context_tax"]["injected_tokens_est"] for g in group) / n
            disk = sum(g["context_tax"]["on_disk_tokens_est"] for g in group) / n
            wired = sum(g["wired_hooks_active_driver"] for g in group) / n
            bash = sum(g["per_tool_call"]["bash_hooks"] for g in group) / n
            rows = sum(g["telemetry"]["rows"] for g in group)
            usd = sum(g["hard_cost"].get("usd_total", 0) for g in group)
            print(f"{cohort[:43]:<44}{n:>3}{inj:>9,.0f}{disk:>10,.0f}"
                  f"{wired:>7,.0f}{bash:>10,.0f}{rows:>10,}{usd:>11,.2f}")
        print()

        # ---- hard cost detail ----
        print("HARD MEASURED COST  (is_estimate=false, pricing_known=true)")
        any_hard = False
        for i in installs:
            h = i["hard_cost"]
            if not h.get("sessions"):
                continue
            any_hard = True
            print(f"  {i['name']}")
            print(f"    sessions={h['sessions']}  turns={h['turns']:,}  "
                  f"total=${h['usd_total']:,.2f}")
            print(f"    ${h['usd_per_turn']:.4f}/turn   ${h['usd_per_session']:,.2f}/session")
            print(f"    context re-read per turn: {h['cache_read_per_turn']:,} tok from cache"
                  f"  ({h['cache_read_share']*100:.1f}% of billed input)")
            print(f"    total billed input/turn : {h['input_total_per_turn']:,} tok")
            print(f"    window: {h['first'][:10]} .. {h['last'][:10]}")
        if not any_hard:
            print("  (none)")
        print()

        # ---- startup + per-tool-call, only where telemetry exists ----
        print("STARTUP AND PER-TOOL-CALL  (only installs with hook telemetry)")
        for i in installs:
            ev = i["telemetry"]["events"]
            if not ev:
                continue
            print(f"  {i['name']}  [{i['harness']}]")
            ss = ev.get("SessionStart")
            if ss:
                print(f"    SessionStart : {ss['invocations']:,} runs x "
                      f"{ss['distinct_hooks']} hooks  p50={ss['p50_ms']}ms "
                      f"p95={ss['p95_ms']}ms  wall_total={ss['total_ms']/1000:,.0f}s")
            for name in ("PreToolUse", "PostToolUse", "UserPromptSubmit", "Stop"):
                e = ev.get(name)
                if not e:
                    continue
                print(f"    {name:<13}: {e['invocations']:,} inv x "
                      f"{e['distinct_hooks']} hooks  p50={e['p50_ms']}ms "
                      f"p95={e['p95_ms']}ms  wall_total={e['total_ms']/1000:,.0f}s")
            ptc = i["per_tool_call"]
            print(f"    per Bash call: {ptc['bash_hooks']} hooks x "
                  f"{ptc['hook_p50_ms']}ms p50 = ~{ptc['serial_latency_ms_est']:,}ms "
                  f"if serial")
            inj = i["measured_injections"]
            if inj:
                tot = sum(v["avg_tokens"] for k, v in inj.items()
                          if k != "context-budget-meter")
                print(f"    measured context injection (SO's own meter): "
                      f"~{tot:,} tok across {len(inj)} sources")
                for src, v in sorted(inj.items(), key=lambda kv: -kv[1]["avg_tokens"]):
                    print(f"        {src:<32} n={v['events']:>5,} "
                          f"avg={v['avg_tokens']:>6,} tok")
        print()

        # ---- findings ----
        dormant = [i for i in installs if i["dormant"]]
        print("FINDINGS")
        print(f"  installs with wired hooks and ZERO hook telemetry: "
              f"{len(dormant)}/{len(installs)}")
        for i in dormant:
            print(f"    - {i['name']} ({i['harness']}, "
                  f"{i['wired_hooks_active_driver']} wired)")
        gaps = [i for i in installs if i["manifest_gap"] > 0]
        print(f"  installs whose manifest claims more hooks than the driver wires: "
              f"{len(gaps)}")
        for i in gaps:
            print(f"    - {i['name']}: manifest {i['meta_claims']['hooks']} vs "
                  f"wired {i['wired_hooks_active_driver']} "
                  f"(gap {i['manifest_gap']})")

    findings = any(i["dormant"] for i in installs) or gctx["over_budget"]
    return 1 if findings else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(2)
```

---

## 9. VERIFICADO vs NO VERIFICADO

### VERIFICADO

| Afirmación | Cómo |
|---|---|
| 21 carpetas con `.cognitive-os/`; 17 son instalaciones reales, 1 es el repo fuente, 3 son residuos | `find ~/Projects -maxdepth 4 -type d -name .cognitive-os` + inspección de `install-meta.json` y conteo de archivos |
| $3.005,18 en 10 sesiones / 4.069 turnos / $0,7386 por turno | 10 filas `is_estimate:false, pricing_known:true` de `cost-events.jsonl`, normalizadas por `token-usage-normalizer.v1` |
| 374.047 tokens de cache read por turno, 96,5% del input facturado | mismas 10 filas, `cache_read_input_tokens / turn_count` |
| 10 instalaciones `harness: codex` no tienen directorio `.claude/` | `ls .claude/` vacío en las 10; reglas presentes solo en `.cognitive-os/rules/cos/` |
| 9 hooks por llamada a Bash en aisotropy, 21 en el repo del SO | resolución de matchers del driver activo contra el nombre de herramienta |
| 141.679 invocaciones de hook en aisotropy en 10 días | `hook-timing.jsonl`, una fila por invocación, ventana 2026-07-08 → 2026-07-19 |
| p95 de `Stop` = 11.992 ms en aisotropy, 10.457 ms en el repo del SO | percentil sobre `duration_ms` |
| El presupuesto de 3.500 tokens mide `~/.claude/CLAUDE.md`, no un archivo del SO | `tests/unit/test_efficiency_stress.py` y `tests/unit/test_efficiency_optimization.py`: `Path.home() / ".claude" / "CLAUDE.md"` |
| 9.956 tokens inyectados por prompt en el repo del SO, 4.031 atribuibles al SO | `wc -c` sobre los cuatro archivos que el system prompt de esta sesión declara cargados |
| 14 de 21 tienen hooks cableados y cero filas de telemetría | conteo de entradas del driver vs filas de `hook-timing.jsonl` |
| El manifiesto declara 43 hooks donde el driver cablea 16 (114 de gap en `luum-lang`) | `install-meta.json:hooks_installed` vs conteo de entradas cableadas |
| El directorio `--help/` es basura de una invocación de CLI | 2 archivos, sin `install-meta.json`, aparece como `?? --help/` en `git status` |

### NO VERIFICADO

| Afirmación | Por qué |
|---|---|
| **Cuántos tokens inyecta cada hook al contexto** | No existe la instrumentación. `hook-timing.jsonl` registra duración y exit code, nunca el tamaño del stdout. Es el hueco más grande del informe |
| **Cuántos bytes inyecta `SessionStart`** | Medirlo exigía ejecutar sus 27 hooks, y el primero (`self-install.sh`) escribe symlinks. Se respetó read-only. La latencia sí está medida |
| **Dólares en cualquier consumidor** | Ninguno de los 20 escribe `cost-events.jsonl`. Los $0,00 de la tabla significan "sin instrumentar", **no** "gratis" |
| **Las ~27.000 tool calls de aisotropy** | Derivadas de dividir invocaciones por un fan-out ponderado según una mezcla supuesta de herramientas. Orden de magnitud |
| **Que las cohortes `codex` cuesten cero en su propio harness** | Se verificó que cuestan cero **bajo Claude Code**. Bajo Codex tienen 16–41 hooks cableados y cero telemetría: no hay evidencia de que hayan corrido nunca |
| **"47.554 invocaciones en 18 días"** | No se reproduce contra ningún archivo actual. Puede ser previo a una rotación de métricas |
| **Si la telemetría está completa** | Existe `tests/integration/test_metrics_rotation.py`, así que los conteos pueden ser posteriores a una rotación y subestimar el histórico. FinOpenPOS tiene 2.210 filas todas del 2026-08-15, lo que sugiere rotación reciente o primer uso hoy |
| **Que la estimación bytes/4 sea exacta** | Es la heurística de los propios tests del SO, elegida por comparabilidad. No se corrió tokenizador real |

### Sobre el modo de trabajo

Read-only respetado en los 21 repos: no se corrió `install.sh` (`:416` y `:425` hacen
`rm -rf "$TARGET_DIR"` y habrían destruido la telemetría que se estaba midiendo), no se
corrió la suite de tests, y no se usó `git checkout --`, `git stash`, `git clean`, `git add`
ni `git commit`. El único archivo escrito en el repo es este informe. El script vive en
el scratchpad y está pegado entero arriba.
