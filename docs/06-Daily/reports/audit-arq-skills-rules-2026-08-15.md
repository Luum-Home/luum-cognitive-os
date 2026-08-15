# Auditoría de arquitectura — `skills/`, `rules/` y el sistema de ruteo

**Fecha:** 2026-08-15
**Alcance:** `skills/` (192 alcanzables), `rules/` (129 + índice), `cos_lib/skill_router.py`,
`cos_lib/semantic_skill_matcher.py`, `cos_lib/rule_router.py`, `cos_lib/ref_key_loader.py`,
`cos_lib/primitive_parser.py`, `scripts/routing_quality_gate.py`
**Modo:** read-only. Ningún archivo del repo fue modificado salvo este informe.

---

## 1. Veredicto

La capa tiene un ruteo que **sí elige** —y elige razonablemente— pero desemboca en una sugerencia
textual que nadie ejecuta, y un corpus de reglas cuyo 96,9% no llega nunca al contexto por ningún
mecanismo automático: el "load on trigger" que RULES-COMPACT declara de sí mismo no existe en
producción.

---

## 2. ¿El ruteo elige algo?

### 2.1 Sí elige. El mecanismo

Cadena completa, de punta a punta:

1. `UserPromptSubmit` → `hooks/skill-router-prompt-suggest.sh` (registrado en `.claude/settings.json`).
2. El hook exporta **`COS_SKILL_ROUTER_DISABLE_SEMANTIC=1`** e invoca `SkillRouter().best_match(prompt)`.
3. `SkillRouter` arma la tabla en `_build_default_routing_table()`: frontmatter (`routing_patterns`,
   `routing_intents`) + una tabla hard-coded de ~970 líneas dentro del propio módulo.
4. `match()` corre regex compiladas contra el prompt. En `skill_router.py:1705` el fallback semántico
   está condicionado a `top_regex_conf < 0.75 AND COS_SKILL_ROUTER_DISABLE_SEMANTIC != "1"`.
   El hook fija esa variable ⇒ **en producción el ruteo es regex puro**.
5. Si `confidence >= 0.80`, el hook emite `additionalContext`: *"Skill router suggests `/x`
   (confidence 0.93)... Invoke it when the workflow fits better than a bespoke prompt."*
6. `PreToolUse` → `hooks/orchestrator-skill-invocation-gate.sh` (ADR-188) puede bloquear (exit 2) si
   hubo sugerencia `>=0.90` y el orquestador no la invocó ni escribió `SKILL_BYPASS:`.

### 2.2 Composición de la tabla

```
SKILL.md visibles para el router : 215
entradas desde frontmatter       : 200   (135 con regex, 65 SOLO routing_intents)
entradas hard-coded en el módulo :  79   (71 pisadas por frontmatter, 1 huérfana: sdd-new)
tabla final                      : 208 entradas / 206 skills / 566 regex compiladas
skills en disco SIN entrada       :  11
```

**Las 65 entradas "solo-intents" son inalcanzables en producción**: no tienen regex, y el único
camino que las podía activar (el matcher semántico) está apagado por el hook. Es el 31% de la tabla.

### 2.3 Qué muestra la telemetría

`.cognitive-os/metrics/skill-suggestion.jsonl`, 2026-06-10 → 2026-08-15:

| Métrica | Valor |
|---|---|
| Evaluaciones registradas | 281 |
| Sin match alguno | 189 (67,3%) |
| `threshold_met` (≥0.80) | 91 (32,4%) |
| Skills distintas propuestas | 39 |
| Distribución de confianza | 0.0 → 189 · 0.8 → 17 · 0.9 → 54 · 1.0 → 21 |

Nada entre 0.01 y 0.79: la confianza es bimodal porque no hay scoring, hay coincidencia de regex.
El número es un rótulo escrito a mano en el frontmatter, no una medida.

### 2.4 El eslabón que corta: nadie invoca

`.cognitive-os/metrics/skill-invocations.jsonl` — **5 eventos, 3 skills distintas**:
`encargo-refutable` (×3), `ruteo-de-agentes`, `evidencia-ejecutable`.

Ninguna de las tres pertenece a las 192 de `skills/`: son skills globales del perfil del operador.
**Cero de las 192 skills del repo tiene una invocación registrada**, contra 91 sugerencias emitidas
por encima del umbral.

**Caveat honesto sobre este número:** `hooks/skill-invocation-logger.sh:31` filtra
`tool_name == "Skill"`. Una skill invocada como slash-command (`/run-tests`) llega como
`SlashCommand` y **no queda registrada**. O sea: el ledger prueba que el camino `Skill` no se usa
para las skills del repo; no prueba que jamás se hayan corrido. El router propone `invoke_command`
en forma `/skill-name`, es decir, propone exactamente el camino que el logger no mide. Ese hueco de
instrumentación es en sí un hallazgo: el sistema no puede responder "¿se usó?" con evidencia.

**Respuesta a la pregunta:** el router elige, con señal pobre pero funcional; el problema está aguas
abajo — la elección se entrega como texto sugerido, y la única puerta que la haría obligatoria
(`orchestrator-skill-invocation-gate`) depende de `last_suggestion(session_id)`, y **todas las 281
filas de telemetría tienen `session_id: "unknown"`**, con lo que la correlación por sesión que el
gate necesita se degrada a un único cubo global.

### 2.5 Script de evidencia

```python
#!/usr/bin/env python3
"""Estado del ruteo de skills: tabla, alcanzabilidad y telemetria. Read-only."""
import os, sys, json, collections
os.environ["COS_SKILL_ROUTER_DISABLE_SEMANTIC"] = "1"   # mismo modo que el hook
sys.path.insert(0, ".")
from pathlib import Path
from cos_lib import skill_router as sr

root = Path(".").resolve()
fm   = sr._load_routing_from_frontmatter(root)
hand = sr._build_hand_coded_routing_table()
disk = sr._detect_skill_md_paths(root)
r    = sr.SkillRouter()

print("SKILL.md visibles      :", len(disk))
print("entradas frontmatter   :", len(fm),
      "| con regex:", sum(1 for e in fm if e.patterns),
      "| solo-intents:", sum(1 for e in fm if not e.patterns))
print("entradas hard-coded    :", len(hand))
print("tabla final            :", r.routing_entry_count, "/", len(r.known_skills), "skills")
print("regex compiladas       :", sum(len(e.patterns) for e in r.routing_table))
print("skills sin entrada     :", len(set(disk) - {e.skill_name for e in r.routing_table}))

rows = [json.loads(l) for l in open(".cognitive-os/metrics/skill-suggestion.jsonl") if l.strip()]
print("\nevaluaciones:", len(rows),
      "| sin match:", sum(1 for x in rows if not x.get("skill_name")),
      "| >=0.80:",    sum(1 for x in rows if x.get("threshold_met")))
print("skills distintas propuestas:",
      len({x["skill_name"] for x in rows if x.get("skill_name")}))
print("confianza:", dict(sorted(collections.Counter(
      round(x.get("confidence", 0), 1) for x in rows).items())))

inv = [json.loads(l) for l in open(".cognitive-os/metrics/skill-invocations.jsonl") if l.strip()]
print("invocaciones:", len(inv), "| skills:",
      sorted({x["payload"]["skill_name"] for x in inv}))
```

---

## 3. Los dos vocabularios: cuál gana

### 3.1 Quién lee qué

Frecuencia de claves en los 119 `SKILL.md` trackeados, contra sus lectores de producción
(`cos_lib/`, `scripts/`, `hooks/`, `packages/`, `mcp-server/`, `cmd/`, `internal/`):

| Clave | Archivos | Lectores de producción | ¿Rutea? |
|---|---|---|---|
| `description` | 119 | el harness (catálogo de skills) + `_llm_fallback_match` | **Sí — es lo único que ve el harness** |
| `routing_patterns` | 104 | `skill_router`, `rule_router`, `routing_pattern_deriver`, 2 hooks validadores | **Sí — es lo único que rutea en el camino propio** |
| `routing_intents` | 117 | `skill_router`, `semantic_skill_matcher`, `skill_description_enricher` | Sólo con matcher semántico → **apagado en producción** |
| `triggers` | 117 | `primitive_parser` + 4 scripts de auditoría | **No** |
| `platforms` | 111 | `skill_runner` (ejecución), `skill_platform_support_audit` | **No** |
| `summary_line` | 92 | `skill_router` (texto), `semantic_skill_matcher`, `generate_compact_catalog` | No (cosmético) |
| `prerequisites` | 95 | **ninguno** | **No** |
| `audience` | 118 | `primitive_parser`, `generate_compact_catalog`, `skill_runner` | No |

`metadata:` —la ubicación que pide la spec de Agent Skills— aparece en **10 de 192** archivos.

### 3.2 Quién gana

**Gana `description`, y no compite: los dos sistemas ni se rozan.**

- El harness construye su catálogo con `name` + `description` de las 192 skills. Esa es la única
  señal con la que el modelo decide invocar una skill por su cuenta. Cuesta ~4.813 tokens por
  sesión, permanentes.
- El router propio no toca `description` para decidir (sólo la usa como texto de reporte en
  `_llm_fallback_match`, camino muerto con el semántico apagado). Decide con `routing_patterns`.
- No hay conflicto porque **no hay punto de encuentro**: el harness no lee la salida del router, y
  el router no escribe en el catálogo del harness. Producen dos señales paralelas que llegan al
  mismo modelo por canales distintos (catálogo de tools vs. `additionalContext`).

El costo real de esa duplicación no es la competencia: es que el gate que cuida `description`
(`tests/audit/test_skill_descriptions_nonempty.py:39`, exige el literal `Use when`) tiene un verde
barato que ya se cobró **85 de 192 descripciones**, todas con la forma:

> `Use when you need this Cognitive OS skill: <descripción real>; do not use when a narrower skill directly matches the task.`

Es decir: el envoltorio que satisface al gate degrada exactamente la señal con la que el harness
—el único sistema que decide de verdad— elige. El gate protege la forma y arruina la función.

### 3.3 `triggers` no está muerto por decreto, pero sí por diseño

Medí si el vocabulario `triggers` rutea a su propia skill, corriendo el router en modo producción:

```
skills con triggers: 185
frases evaluadas:    796
  rutean a su skill: 495  (62,2%)
  rutean a OTRA:      55  ( 6,9%)
  no rutean a nada:  246  (30,9%)
```

El 62,2% no es mérito de `triggers`: es que muchas `routing_patterns` se derivaron de los mismos
textos (ver `cos_lib/routing_pattern_deriver.py`). El 30,9% que no rutea a nada es la medida de la
divergencia: casi un tercio de lo que una skill declara como su disparador no dispara nada.

```python
#!/usr/bin/env python3
"""¿El vocabulario `triggers:` rutea a su propia skill? Read-only."""
import os, sys, collections
os.environ["COS_SKILL_ROUTER_DISABLE_SEMANTIC"] = "1"
sys.path.insert(0, ".")
from pathlib import Path
import yaml
from cos_lib.skill_router import SkillRouter

router = SkillRouter()
hit = miss = nomatch = 0
for md in sorted(Path("skills").glob("*/SKILL.md")):
    txt = md.read_text(errors="replace")
    if not txt.startswith("---"):
        continue
    try:
        fm = yaml.safe_load(txt.split("---", 2)[1]) or {}
    except Exception:
        continue
    trig = fm.get("triggers")
    if not trig:
        continue
    for p in (trig if isinstance(trig, list) else [trig]):
        if not isinstance(p, str) or len(p) < 4:
            continue
        m = router.best_match(p)
        if   m is None:                    nomatch += 1
        elif m.skill_name == md.parent.name: hit += 1
        else:                              miss += 1
tot = hit + miss + nomatch
print(f"frases {tot} | propia {hit} ({100*hit/tot:.1f}%) "
      f"| otra {miss} ({100*miss/tot:.1f}%) | ninguna {nomatch} ({100*nomatch/tot:.1f}%)")
```

---

## 4. `RULES-COMPACT.md`: ¿existe el trigger?

**El expandidor existe. La expansión de producción no ocurre nunca.**

### 4.1 Lo que hay

- `cos_lib/ref_key_loader.py` implementa `find_ref_keys()`, `resolve()`, `expand()` con filtro por
  tier y logueo de misses. Funciona: tiene tests unitarios que pasan.
- **Un solo consumidor de producción**: `hooks/inject-phase-context.sh:362-379`.
- Un comando manual: `.claude/commands/rules-expand.md` (el operador escribe `/rules-expand <key>`
  y el agente hace `Read` a mano).

### 4.2 Por qué es un no-op

El único consumidor expande `CONTEXT_BUF`, que se compone (líneas 267-333 del mismo hook) de:
reglas de fase hard-coded en el `case "$PHASE"` (líneas 124-155), gotchas auto-detectados, avisos de
engram, contexto de proyecto, info de squad y `templates/project-gotchas.md`.

**Ninguna de esas fuentes contiene un marcador `[`ref-key`]`.** Las reglas de fase son cuatro bloques
de texto plano escritos a mano. El único `[`ref-key`]` en todo `hooks/` está dentro de un comentario
del propio `inject-phase-context.sh`.

Mientras tanto, la única fuente real de ref-keys —`rules/RULES-COMPACT.md`, con 138 marcadores— la
carga el harness como *project instruction* vía el symlink `.claude/rules/cos/RULES-COMPACT.md`,
creado por `hooks/self-install.sh:466`. Ese texto entra al contexto **ya renderizado, fuera del
alcance del expandidor**. El comentario de `self-install.sh:454` dice literalmente *"Other rules
reach agents via Stage 2 expand() of [ref-key] markers in RULES-COMPACT.md (see ADR-074)"* — y ése
es precisamente el camino que no existe.

**Evidencia:** `.cognitive-os/metrics/ref-key-misses.jsonl` tiene **2 filas**, ambas con la clave
`nonexistent-rule-xyz-9999` — es decir, las dos son de la suite de tests. Cero eventos de producción
en toda la vida del archivo.

### 4.3 Además, 11 ref-keys apuntan a la nada

De los 138 marcadores de `RULES-COMPACT.md`, **11 no tienen archivo `rules/<key>.md`**:
`cognitive-os-changes`, `component-classification`, `component-reality-check`, `cost-predictor`,
`dogfood-score`, `dogfooding`, `ecosystem-tools`, `library-selection`, `os-vs-project`, `plan-first`,
`stash-mutation-reversibility`. En la dirección inversa no hay huérfanos: las 128 rules tienen su
ref-key en el índice.

### 4.4 El canal alternativo que sí existe (y también es sugerencia)

`hooks/rule-router-prompt-suggest.sh` (ADR-179) corre `RuleRouter` en `UserPromptSubmit` y emite
*"Suggested rules to load: rules/x.md (0.85)"*. También sugiere; tampoco carga.

Y su alcance es mínimo: de las 129 rules, **12 tienen frontmatter y sólo 7 son ruteables**
(6 `agent-instruction` + 1 `hybrid`). En 77 evaluaciones registradas (2026-07-20 → 2026-08-15), 28
superaron el umbral, y las únicas rules jamás sugeridas fueron cinco: `trust-score`,
`adversarial-review`, `acceptance-criteria`, `definition-of-done`, `eas-evidence-artifact`.

**Conclusión de la pregunta 3:** el índice comprimido es **decorativo** en su función de índice.
Funciona como documento —se lee entero, 2.888 tokens por sesión— pero sus 138 referencias no son
enlaces: son texto. El diseño de "índice + expansión bajo demanda" está implementado a medias: la
mitad barata (el índice) se proyecta, la mitad cara (la expansión) no se cableó nunca a su corpus.

```bash
#!/usr/bin/env bash
# ¿Se expande algun [ref-key] en produccion? Read-only.
set -u
echo "== ref-keys en el indice =="
grep -oE '\[`[a-z0-9][a-z0-9._-]+`\]' rules/RULES-COMPACT.md | tr -d '[]`' | sort -u | wc -l
echo "== ref-keys sin archivo rules/<key>.md =="
grep -oE '\[`[a-z0-9][a-z0-9._-]+`\]' rules/RULES-COMPACT.md | tr -d '[]`' | sort -u \
  | while read -r k; do [ -f "rules/$k.md" ] || echo "  HUERFANO: $k"; done
echo "== consumidores de ref_key_loader en produccion =="
grep -rln 'ref_key_loader' hooks/ scripts/ cos_lib/ packages/ 2>/dev/null | grep -v ref_key_loader.py
echo "== ref-keys en las fuentes que ese consumidor expande =="
grep -cE '\[`[a-z0-9-]+`\]' templates/project-gotchas.md 2>/dev/null || echo "  0 en gotchas"
echo "== eventos de miss registrados =="
wc -l < .cognitive-os/metrics/ref-key-misses.jsonl
cut -d'"' -f8 .cognitive-os/metrics/ref-key-misses.jsonl 2>/dev/null | sort -u
echo "== rules proyectadas al harness =="
ls -1 .claude/rules/cos/
```

---

## 5. Deuda de contenido

Listadas sin unificar, con clasificación explícita.

### 5.1 Contradicción viva: `rate-limiting.md`

Es **una de las dos únicas rules siempre en contexto** (1.143 tokens por sesión) y se autodeclara
inoperante en su propio encabezado:

> *"Estado real, verificado 2026-08-15: el limitador NO está activo. `hooks/rate-limiter.sh` existe
> pero no está registrado en `.claude/settings.json` ... 0 disparos en 37.424 filas de telemetría."*

Mientras tanto, `RULES-COMPACT.md` §4 (Cost Governance) la lista sin salvedad entre los controles
activos: *"Rate limits: [`rate-limiting`] [`rate-limit-protection`]"*. El índice afirma un control
que el cuerpo desmiente, y el operador paga los dos textos en cada sesión.

Es la única rule que se autodeclara inactiva de forma detectable. Que sea justamente una de las dos
proyectadas es lo que la vuelve cara.

### 5.2 Referencias colgadas a módulos inexistentes (10 casos, 4 reales)

| Rule | Referencia | Clasificación |
|---|---|---|
| `rules/non-blocking-retry.md:63` | `lib/workload_scheduler.py` | **Deuda real** — `lib/` ya no existe |
| `rules/workload-scheduling.md` | `lib/workload_scheduler.py` | **Deuda real** — mismo módulo |
| `rules/orchestrator-mode.md` | `lib/file_lock_registry.py` | **Deuda real** |
| `rules/task-dag.md` | `lib/task_dag.py` | **Deuda real** |
| `rules/so-slo.md` | `lib/agent_heartbeat.py` | **Deuda real** |
| `rules/so-slo.md` | `scripts/so-slo-report.sh` | **Deuda real** — script inexistente |
| `rules/so-slo.md` | `hooks/_lib/hook-runtime-probe.sh` | **Deuda real** — hook inexistente |
| `rules/recommendation-grounding.md` | `scripts/lint_recommendation_grounding.py` | **Deuda real** — el linter que la regla exige no existe |
| `rules/python-naming.md` | `scripts/foo-bar.py` | **Coincidencia** — ejemplo ilustrativo de nombre prohibido |
| `rules/response-compression.md` | `lib/foo.py` | **Coincidencia** — placeholder en un ejemplo |

Nota sobre la premisa del encargo: encontré **6** referencias colgadas a `lib/` en `rules/`
(4 módulos reales + 2 placeholders de ejemplo), no 8. Si las 8 excepciones declaradas incluyen
archivos fuera de `rules/`, esa parte queda fuera de mi porción.

`rules/so-slo.md` merece mención aparte: cita **tres** rutas inexistentes de golpe. Una regla de SLO
cuyo reporte, cuya sonda y cuyo módulo de heartbeat no existen no es una regla, es una intención.

### 5.3 Duplicación: no la hay

Corrí un detector de solape léxico (Jaccard sobre tokens ≥5 caracteres, umbral 0.45) sobre los
128 pares posibles: **cero pares por encima del umbral**. El corpus de `rules/` no está duplicado.
El problema no es que las reglas se repitan; es que no se leen.

### 5.4 El envoltorio circular: 85 descripciones

85 de las 192 skills alcanzables tienen `description` con la forma
`Use when you need this Cognitive OS skill: <lo que realmente hace>; do not use when a narrower skill
directly matches the task.` El prefijo satisface `test_every_skill_description_starts_with_use_when`
y no aporta ninguna señal de ruteo; el sufijo tampoco. El encargo estimaba 73; el conteo actual
sobre `skills/` trackeadas es **85**.

### 5.5 `prerequisites`: 95 declaraciones, 0 lectores

Ningún módulo de `cos_lib/`, `scripts/`, `hooks/`, `packages/`, `mcp-server/`, `cmd/` ni `internal/`
accede a la clave `prerequisites`. 95 archivos trackeados la declaran (165 sobre el set de 192,
según la medición previa del encargo). Es metadata que nadie consume: ni valida, ni bloquea, ni
informa.

```python
#!/usr/bin/env python3
"""Deuda de contenido en rules/ y skills/. Exit 0 sin hallazgos, 1 con hallazgos."""
import re, subprocess, pathlib, sys, collections

def tracked(pat):
    out = subprocess.run(["git", "ls-files", pat], capture_output=True, text=True).stdout
    return [f for f in out.split() if f.endswith(".md")]

findings = collections.defaultdict(list)
MOD = re.compile(r"`((?:cos_lib|lib|scripts|hooks|packages)/[A-Za-z0-9_./-]+\.(?:py|sh))`")

for f in tracked("rules/"):
    t = pathlib.Path(f).read_text(errors="replace")
    for m in sorted(set(MOD.findall(t))):
        if not pathlib.Path(m).exists():
            findings["A_modulo_inexistente"].append(f"{f} -> {m}")
        if m.startswith("lib/"):
            findings["B_lib_colgado"].append(f"{f} -> {m}")
    if re.search(r"NO est[aá] activo|no est[aá] registrado|sin registrar|0 disparos", t, re.I):
        findings["C_autodeclarada_inactiva"].append(f)

CIRC = re.compile(r"^Use when you need this Cognitive OS skill:", re.I)
for f in tracked("skills/"):
    if not f.endswith("SKILL.md"):
        continue
    m = re.search(r"^description:\s*(.+)$", pathlib.Path(f).read_text(errors="replace"), re.M)
    if m and CIRC.match(m.group(1).strip().strip("\"'")):
        findings["D_description_circular"].append(f)

compact = pathlib.Path("rules/RULES-COMPACT.md").read_text(errors="replace")
for k in sorted(set(re.findall(r"\[`([a-z0-9][a-z0-9._-]+)`\]", compact))):
    if not pathlib.Path(f"rules/{k}.md").exists():
        findings["E_refkey_sin_archivo"].append(k)

for cat in sorted(findings):
    print(f"\n### {cat}  ({len(findings[cat])})")
    for x in sorted(set(findings[cat])):
        print("   ", x)
sys.exit(1 if findings else 0)
```

---

## 6. Costo del corpus

| Corpus | Archivos | Bytes | ~Tokens |
|---|---:|---:|---:|
| `rules/*.md` trackeados | 129 | 520.517 | ~130.129 |
| `SKILL.md` trackeados | 119 | 637.217 | ~159.304 |
| `SKILL.md` alcanzables (resolviendo symlinks) | 192 | 1.046.324 | ~261.581 |

**Lo que entra al contexto de cada sesión:**

| Ítem | ~Tokens | Mecanismo |
|---|---:|---|
| `RULES-COMPACT.md` | 2.888 | symlink en `.claude/rules/cos/` |
| `rate-limiting.md` | 1.143 | symlink en `.claude/rules/cos/` |
| Catálogo de skills (`name` + `description` × 192) | 4.813 | el harness lo arma solo |
| **Total permanente** | **~8.844** | |

**Lo que nunca entra por ningún mecanismo automático:**
504.394 bytes de cuerpo de reglas ≈ **126.098 tokens, el 96,9% del corpus de `rules/`**. Sólo llega
al contexto si el agente hace `Read` a mano, guiado por una sugerencia del rule-router (que alcanza a
7 de 129 reglas) o por `/rules-expand` (manual).

Del lado de skills, el cuerpo (~262k tokens) sólo se carga cuando la skill se invoca. Dado el
apartado 2.4, la fracción del corpus de skills efectivamente usada por invocación registrada es
**0 de 192**.

Comparación útil para dimensionar: el operador paga ~8.8k tokens por sesión para tener disponible un
corpus de ~392k tokens del cual, en dos meses de telemetría, se ejercitaron 39 skills como sugerencia
y 5 reglas como sugerencia. El resto es inventario.

```python
#!/usr/bin/env python3
"""Costo del corpus y fraccion proyectada al contexto. Read-only, exit 0."""
import subprocess, pathlib, os, re

def files(pat, suf):
    out = subprocess.run(["git", "ls-files", pat], capture_output=True, text=True).stdout
    return [f for f in out.split() if f.endswith(suf)]

def size(ps):  return sum(pathlib.Path(p).stat().st_size for p in ps if pathlib.Path(p).exists())
def toks(b):   return round(b / 4)

rules     = files("rules/", ".md")
skills    = files("skills/", "SKILL.md")
reachable = sorted({os.path.realpath(p) for p in pathlib.Path("skills").glob("*/SKILL.md")})
projected = sorted(pathlib.Path(".claude/rules/cos").glob("*.md"))

for label, ps in (("rules trackeadas", rules), ("SKILL.md trackeados", skills),
                  ("SKILL.md alcanzables", reachable)):
    print(f"{label:24} {len(ps):4}  {size(ps):9} B  ~{toks(size(ps)):7} tok")

pb = size([str(p) for p in projected])
print(f"\nrules proyectadas ({len(projected)}): ~{toks(pb)} tok")
for p in projected:
    print(f"   {p.name:22} ~{toks(p.stat().st_size)} tok")

cat = 0
for p in reachable:
    t = pathlib.Path(p).read_text(errors="replace")
    for key in ("name", "description"):
        m = re.search(rf"^{key}:\s*(.+)$", t, re.M)
        cat += len(m.group(1)) if m else 0
print(f"\ncatalogo de skills (name+description x {len(reachable)}): ~{toks(cat)} tok")
print(f"cuerpo de rules NUNCA proyectado: ~{toks(size(rules) - pb)} tok "
      f"({100 * (size(rules) - pb) / size(rules):.1f}% del corpus)")
```

---

## 7. Fuera de mi porción

Cosas que vi trabajando y que le tocan a otro juez:

1. **`hooks/skill-metrics-tracker.sh` no existe** — pero `scripts/generate-project-settings.sh:148`
   y `scripts/cos_init.py:106` lo registran en los settings que generan para proyectos consumidores.
   Un hook fantasma proyectado a terceros. → *instalador + packages*.

2. **`.cognitive-os/metrics/skill-metrics.jsonl` está contaminado**: 139 filas con 32 valores
   distintos en el campo `skill`, la mayoría palabras sueltas de descripciones de tarea (`juez`,
   `preparar`, `forense`, `decisi`, `arquitectura`, `triaje`, `censo`, `validaci` — visiblemente
   truncadas en el acento). Sólo 5 valores son nombres de skill reales. Ese stream alimenta
   `cos_lib/kpi_collector.py`, `cos_lib/singularity.py` (detector de "3 fallos consecutivos"),
   `cos_lib/performance_ledger.py`, `cos_lib/component_usage_tracker.py` y
   `cos_lib/repetition_detector.py`. Todo KPI derivado de ahí es ruido. → *tests + CI + telemetría*.

3. **`hooks/subagent-budget-enforcer.sh` bloquea sin bloquear**: corre en `PostToolUse`, o sea
   *después* de que el comando ya se ejecutó. Su "BLOCK — exceeding budget" inyecta texto de error
   pero el efecto ya ocurrió. Como control de gasto es un aviso caro disfrazado de gate.
   → *hooks (porción ya cerrada, queda anotado)*.

4. **`AGENTS.md` sigue documentando `lib/`** como ubicación de los módulos Python ("Lib | `lib/` |
   Python modules: cost tracking, skill routing..."), post-migración a `cos_lib/`. → *docs*.

5. **La tabla hard-coded del router**: ~970 líneas de `_RoutingEntry` con regex embebidas dentro de
   `cos_lib/skill_router.py` (79 entradas, de las cuales 71 quedan pisadas por el frontmatter y por
   lo tanto son código muerto en la ruta activa). El módulo tiene 2.004 líneas. → *`cos_lib` +
   `scripts`*.

6. **`session_id: "unknown"` en toda la telemetría de ruteo** (281 filas de skill-suggestion, 77 de
   rule-suggestion). El gate `orchestrator-skill-invocation-gate` correlaciona por sesión; con un
   único valor para todo, la correlación no distingue nada. → *telemetría / hooks*.

---

## 8. Correcciones a las premisas del encargo

| # | Premisa del encargo | Lo que encontré |
|---|---|---|
| 1 | "192 skills alcanzables y sólo 2 se invocaron alguna vez" | 192 alcanzables: **confirmado** (119 dirs reales + 75 symlinks a `packages/`, resueltos). Las invocadas son **3 distintas**, no 2 — y **ninguna pertenece a las 192**: son skills globales del perfil del operador. Cero de las 192 tiene invocación registrada. Con el caveat del §2.4: el logger sólo mide `tool_name == "Skill"`. |
| 2 | "119 `SKILL.md` trackeados" | **Confirmado** (`git ls-files` = 119, `find` sin seguir symlinks = 119). El salto a 192 lo produce el glob que sigue los 75 symlinks a `packages/*/skills/`. El router ve **215** porque además barre `packages/` y `.cognitive-os/skills/` directamente. |
| 3 | "188 de 192 skills usan claves que ninguna spec reconoce" | Matiz importante: de esas claves, **`routing_patterns` y `routing_intents` SÍ tienen lector de producción** (`skill_router`). Las que efectivamente no las lee nadie para rutear son `triggers` (117 archivos, sólo auditoría), `platforms` (111, sólo ejecución) y `prerequisites` (95, cero lectores). No es "188 claves muertas": es un vocabulario propio parcialmente cableado. |
| 4 | "`prerequisites` en 165 archivos con 0 lectores" | **0 lectores: confirmado.** El conteo de 165 corresponde al set de 192; sobre los 119 trackeados son **95**. |
| 5 | "el gate exige el literal 'Use when'; su verde barato arruinó 73 descripciones" | Gate confirmado en `tests/audit/test_skill_descriptions_nonempty.py:39`. El envoltorio circular está hoy en **85** descripciones, no 73. |
| 6 | "migración `lib/` → `cos_lib/` con 8 excepciones declaradas" | En `rules/` encontré **6** referencias colgadas a `lib/`, de las cuales **4 son deuda real** (`workload_scheduler`, `file_lock_registry`, `task_dag`, `agent_heartbeat`) y 2 son placeholders de ejemplo. Si las 8 incluyen archivos fuera de `rules/`, eso queda fuera de mi porción. Además hay **4 referencias colgadas que no son de `lib/`**: `scripts/so-slo-report.sh`, `hooks/_lib/hook-runtime-probe.sh` y `scripts/lint_recommendation_grounding.py`. |
| 7 | "~20 lectores de producción del frontmatter" | Consistente con lo medido, pero engañoso como agregado: la mayoría son scripts de auditoría que leen el frontmatter *para reportar sobre él*, no para decidir nada. Los lectores que cambian el comportamiento del sistema son **dos**: `cos_lib/skill_router.py` (`routing_patterns`) y el propio harness (`description`). |
| 8 | "¿el router no elige, o elige y nadie lo llama?" | **Elige y nadie lo llama** — pero con dos precisiones que la dicotomía no cubre: (a) el 67,3% de los prompts no produce match alguno, así que "elige" describe un tercio de los casos; (b) el 31% de la tabla (65 entradas solo-intents) es estructuralmente inalcanzable porque el hook de producción apaga el matcher semántico. |

---

## 9. Reproducción

Los cinco scripts de este informe corren desde la raíz del repo, son read-only y no dependen del
estado de la sesión. Requisitos: `python3` con `yaml`, `git`, `jq` no necesario.

```
python3 <script-del-§2.5>    # estado del ruteo + telemetría
python3 <script-del-§3.3>    # ¿triggers rutea a su propia skill?
bash    <script-del-§4.4>    # ¿se expande algún ref-key?
python3 <script-del-§5.5>    # deuda de contenido   (exit 1 con hallazgos)
python3 <script-del-§6>      # costo del corpus
```
