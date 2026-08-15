# Juez independiente — ¿cuánto de lo declarado está realmente cableado?

**Fecha:** 2026-07-28
**Alcance:** skills, hooks, rules, packages/squads/agents/templates/workflows, y juicio sobre `scripts/aspirational_audit.py`
**Modo:** read-only. Único archivo escrito en el repo: este informe.

---

## Veredicto (una línea)

El sistema está **mucho más cableado de lo que un escéptico esperaría (~73% de las skills tienen algo ejecutable detrás, 0 hooks registrados apuntan a archivos inexistentes, 92% de las rules resuelven)** — pero **su propio auditor `scripts/aspirational_audit.py` es estructuralmente incapaz de detectar un problema y hoy reporta 0.0% de deuda por construcción, no por salud**.

---

## 1. Correcciones a las premisas del encargo

Ninguno de los dos números del brief sobrevivió el recuento. Se aplicó la cláusula de refutación.

### "~197 skills" → **192**, y 75 de ellas son symlinks

```bash
ls -1 skills/ | wc -l                                  # 197  ← el número del brief
find skills -maxdepth 1 -mindepth 1 -type d | wc -l     # 118  directorios
find skills -maxdepth 1 -mindepth 1 -type l | wc -l     # 75   symlinks → packages/
find skills -maxdepth 2 -mindepth 2 -name SKILL.md | wc -l  # 117
```

Desglose de los 197:
- **117** directorios canónicos con `SKILL.md`
- **75** symlinks a `packages/*/skills/*` (todos resuelven; 0 rotos)
- **1** directorio vacío (`skills/auto-generated/`, solo `.gitkeep`)
- **4** archivos que no son skills (`CATALOG.md`, `CATALOG-COMPACT.md`, `CATALOG-MICRO.md`, `REGISTRY.lock`)

**Universo real de skills = 192.** El `ls` crudo contó catálogos y un directorio vacío como si fueran capacidades.

### "~690 scripts bash" → **485** son del SO; el resto es vendoreado o generado

```bash
find . -name '*.sh' -not -path './.git/*' | sed 's|^\./||' | cut -d/ -f1 | sort | uniq -c | sort -rn
```

| top dir | `.sh` | ¿es el SO? |
|---|---|---|
| `hooks/` | 289 | sí |
| `scripts/` | 153 | sí |
| `reference/` | 112 | **no** — código de terceros vendoreado (`reference/agentic/...`) |
| `packages/` | 43 | sí |
| `.cognitive-os/` | 37 | **no** — generado en runtime, no versionado |
| `.claude/` | 22 | **no** — proyección de harness |
| resto | 34 | mixto |

`git ls-files '*.sh' | wc -l` → **519** versionados. La superficie bash propia del SO es ≈ **485**, no 690. El 690 incluía 112 archivos de terceros y 59 generados.

### Contaminación análoga en `SKILL.md`

```bash
find . -name SKILL.md -not -path './.git/*' | cut -d/ -f2 | sort | uniq -c | sort -rn
# 163 .claude/  119 skills/  75 packages/  62 .cognitive-os/  9 .codex/  1 examples/
```

429 `SKILL.md` en disco, pero **solo 119 son fuente**. Los 163 de `.claude/` y 62 de `.cognitive-os/` son proyecciones generadas de los mismos originales. Cualquier auditoría que cuente 429 está contando cada skill hasta 4 veces.

---

## 2. Distribución REAL / DORMANT / METADATA (skills)

Script propio: `judge_primitives.py` (fuente completa en el Anexo A; no reutiliza el auditor del repo).

**Premisa arquitectónica verificada primero** — `cos_lib/skill_router.py` descubre las skills dinámicamente:

```bash
grep -n "glob" cos_lib/skill_router.py | head
# 423:  for skill_md in sorted(root.glob("*/SKILL.md")):
```

Las skills **nunca se registran individualmente**: el router las globea y construye el índice desde el frontmatter. Por lo tanto "estar en un registro" es uniforme para las 192 y **no discrimina nada**. El discriminador honesto es: *si alguien invoca esta skill, ¿pasa algo?*

Taxonomía usada:
- **REAL** — código que se ejecuta la despacha (`hooks/`, `scripts/`, `cos_lib/`, `settings.json`, `Makefile`, `.claude/commands`), o hay telemetría de invocación.
- **DORMANT** — alcanzable por el router **y** los comandos que cita resuelven en disco, pero nada la llama.
- **METADATA** — prosa sola: no cita comando ejecutable ni tiene implementación hermana, o todas las rutas que cita están rotas.

```bash
python3 judge_primitives.py
```

| clase | n | % |
|---|---|---|
| REAL | 140 | **72.9%** |
| DORMANT | 20 | **10.4%** |
| METADATA | 32 | **16.7%** |
| **total** | **192** | |

Señales colaterales del mismo script:
- alcanzables por el router (tienen `routing_patterns`/`routing_intents`): **191/192**
- listadas en inventarios (`manifests/`, `CATALOG*`) pero nunca llamadas: **52**
- **invocaciones registradas en telemetría: 1 evento, 1 skill distinta** (`.cognitive-os/metrics/skill-invocations.jsonl` tiene **una sola línea**)

> **Advertencia sobre mi propio número.** El 72.9% es un **techo, no un piso**. Verifiqué REAL a mano y encontré falsos positivos por coincidencia de substring: `caveman` matcheó un **comentario** en `hooks/agent-qwen-bridge.sh`; `sprint` matcheó `sprint-status.yaml` (otro concepto); `scout` matcheó `scout-pattern.md` y `repo-scout`. Endurecí el test (excluir comentarios; exigir `skills/<n>`, `skill_name="<n>"`, `"<n>",` o `/<n>`) pero **la corrida estricta no llegó a completarse** — ver §6 "No verificado". El REAL verdadero está por debajo de 140.

La telemetría de invocaciones es inútil como señal: **1 evento en todo el archivo**. Nadie puede afirmar "esta skill se usa" con esa base.

---

## 3. Los peores 15 casos, nombrados

### 3a. Punteros rotos — la skill cita un archivo del repo que no existe

```bash
python3 judge_primitives.py    # sección "Skills citing repo paths that DO NOT EXIST"
```

| # | skill | ruta citada que NO existe |
|---|---|---|
| 1 | `deep-tool-research` | `hooks/deep-research-axis-gate.sh` |
| 2 | `sandbox-sample` | `cmd/main.go` |
| 3 | `validate-config` | `hooks/old-hook.sh` |
| 4 | `add-hook` | `packages/efficiency-profiles/profiles/standard.json`, `tests/run-all-tests.sh` |
| 5 | `add-skill` | `tests/unit/test-skills.sh` |
| 6 | `session-pending-close` | `tests/red_team/portability/test_X.py` |

(4–6 se detectan cuando se escanea también el frontmatter; 1–3 aparecen ya escaneando solo el cuerpo.) `deep-tool-research` es el peor: **9.694 bytes de prosa cuyo único gancho ejecutable no existe**.

### 3b. METADATA más pesadas — prosa grande sin nada ejecutable detrás

Verificado a mano que ninguna tiene `scripts/<nombre>.*`:

| # | skill | bytes |
|---|---|---|
| 7 | `plan-chore` | 8.406 |
| 8 | `product-answer` | 7.725 |
| 9 | `automaker-bridge` | 7.300 |
| 10 | `harness-audit` | 7.239 |
| 11 | `squad-manager` | 5.983 |
| 12 | `review-output` | 5.942 |
| 13 | `add-mcp` | 5.932 |
| 14 | `compat-test` | 5.777 |
| 15 | `install-skill` | 5.622 |

Comprobación puntual:

```bash
ls scripts/patch-release* scripts/detect-stack* scripts/harness-audit* scripts/compat-test*
# zsh: no matches found  (para las cuatro)
```

**Matiz honesto:** una skill es, por diseño, *instrucciones para el LLM*. Que `product-answer` sea prosa pura **no es automáticamente un defecto** — es prosa que el agente lee y ejecuta con su criterio. Lo que sí es cierto es que **su funcionamiento no es verificable por ningún test ni gate**: nadie puede probar que "funciona". Ese es el sentido de clasificarlas aparte, no acusarlas de fraude.

Las 20 DORMANT más notorias (implementación que resuelve, cero llamadores): `research-protocol` (14.877 B), `apply-improvements`, `scaffold-project`, `add-rule`, `install-hook`, `coordination-status`, `browser-task`, `install-recommended`, `bump-version`, `tag-release`, `validate-release`, `adr-tombstone`, `vuln-remediation-flow`, `cost-predictor`, `primitive-surface-reduction`, `cos-maintainer-operations`, `primitive-usage-map`, `stash-quarantine`, `cos-install-operations`, `docs-execution-audit`.

---

## 4. Juicio sobre `scripts/aspirational_audit.py`: **NO es confiable**

### Lo que reporta hoy

```bash
python3 scripts/aspirational_audit.py --dry-run --json
```
```json
{"total": 910,
 "counts": {"METADATA": 89, "REAL": 130, "ON_DEMAND": 691},
 "dormant_aspirational_ratio": 0.0,
 "worst_offenders": []}
```

**Cero DORMANT. Cero ASPIRATIONAL. Cero peores ofensores.** Eso no es un sistema sano; es un instrumento roto. Cuatro defectos independientes lo explican.

### Defecto 1 — `lib/` no existe: 369 módulos jamás auditados

```bash
sed -n '429,435p' scripts/aspirational_audit.py
#   lib_dir = project_root / "lib"
#   if not lib_dir.is_dir():
#       return                       ← return silencioso, sin warning
ls -d lib cos_lib          # ls: lib: No such file or directory  /  cos_lib
ls cos_lib/*.py | wc -l    # 369
```

El repo renombró `lib/` → `cos_lib/`. El auditor sigue mirando `lib/`, no lo encuentra y **retorna en silencio**. Toda la capa de librerías —369 archivos Python, el corazón del SO— queda fuera de la auditoría sin que nada lo señale. Se confirma en la salida: no hay un solo evento con componente `lib/` o `cos_lib/`.

### Defecto 2 — mismatch de esquema: ninguna skill puede ser REAL, nunca

El logger escribe una clave; el lector lee otra.

```bash
grep -n "skill_name" hooks/skill-invocation-logger.sh    # 57:  "skill_name": sys.argv[3],
sed -n '345p'  scripts/aspirational_audit.py             # skill = row.get("skill", row.get("payload", {}).get("skill", ""))
```

Prueba sobre la línea real que el logger produjo:

```bash
python3 -c "
import json; r=json.loads(open('.cognitive-os/metrics/skill-invocations.jsonl').readline())
print('payload keys :', list(r['payload'].keys()))
print('lo que lee el auditor:', repr(r.get('skill', r.get('payload',{}).get('skill',''))))"
# payload keys : ['args', 'session_id', 'skill_name']
# lo que lee el auditor: ''
```

`invocations` es **siempre 0**. La rama `if invocations > 0 → REAL` de `classify_skill` es **código muerto**.

### Defecto 3 — la escotilla "invocation contract" la pasa el 100% del universo

```bash
sed -n '80,99p' scripts/aspirational_audit.py
# busca, en las primeras 80 líneas y en minúsculas:
# "user-invocable: true", "triggers:", "trigger:", "command:", "invoke:",
# "routing_patterns:", "routing_intents:"
```

Toda `SKILL.md` del repo lleva `triggers:` y `routing_intents:` en el frontmatter. Medición:

```bash
python3 - <<'EOF'
from pathlib import Path
m=("user-invocable: true","triggers:","trigger:","command:","invoke:","routing_patterns:","routing_intents:")
t=h=0
for p in Path("skills").rglob("SKILL.md"):
    t+=1; head="\n".join(p.read_text(errors="replace").splitlines()[:80]).lower()
    h+= any(x in head for x in m)
print(f"{h}/{t} pasan la escotilla")
EOF
# 119/119 pasan la escotilla   (100%)
```

**Combinando 2 y 3: toda skill cae determinísticamente en ON_DEMAND.** Las ramas `DORMANT` y `ASPIRATIONAL` de `classify_skill` son inalcanzables. Confirmado empíricamente — las 192 skills salieron ON_DEMAND, sin una sola excepción:

```bash
python3 -c "
import json,collections
L=[json.loads(l) for l in open('.cognitive-os/metrics/aspirational-audit.jsonl') if l.strip()]
last=max(e['timestamp'] for e in L)
c=collections.Counter((e['payload']['component'].split('/')[0], e['payload']['classification'])
                      for e in L if e['timestamp']==last)
print(sorted(c.items()))"
# [(('hooks','METADATA'),89), (('hooks','ON_DEMAND'),123), (('hooks','REAL'),77),
#  (('scripts','ON_DEMAND'),377), (('scripts','REAL'),52),
#  (('skills','ON_DEMAND'),192)]        ← 192/192, poder discriminante = 0
```

El comentario del propio código delata la intención (líneas 713-715):

> `# Honor @on-demand marker before falling to DORMANT/ASPIRATIONAL.`
> `# Skill-side parity with classify_hook/classify_lib (commit 30406bad's`
> `# marker batch couldn't drop the ratio without this check).`

La escotilla se agregó explícitamente **para bajar el ratio**, no para medir mejor.

### Defecto 4 — ON_DEMAND se oculta del reporte pero infla el denominador

```bash
sed -n '826,836p' scripts/aspirational_audit.py   # ratio = (dormant + aspirational) / total
sed -n '859,861p' scripts/aspirational_audit.py   # for cls in ("REAL","DORMANT","ASPIRATIONAL","METADATA")
```

Doble efecto: `ON_DEMAND` **no aparece** en la tabla del reporte (el loop no lo incluye), pero **sí cuenta en `total`**, que es el denominador del ratio. 691 de 910 componentes (**76%**) se van a un cubo invisible que además diluye la métrica. El gate `--threshold` **no puede fallar nunca**.

### Las 10 verificaciones manuales

El talón de Aquiles es `has_covering_test`: hace *substring matching* del nombre contra el **texto completo** de todo archivo de test (líneas 122-131).

```bash
python3 - <<'EOF'   # reproduce qué archivo matcheó y por qué
from pathlib import Path
def why(stem):
    snake=stem.replace("-","_"); T=Path("tests")
    if list(T.rglob(f"test_{snake}.py"))+list(T.rglob(f"test_{stem}.py")): return "EXACT",""
    for pat in ("test_*.py","*_test.py"):
        for f in T.rglob(pat):
            t=f.read_text(errors="replace")
            if stem in t or snake in t:
                for ln in t.splitlines():
                    if stem in ln or snake in ln: return "SUBSTRING", f"{f}: {ln.strip()[:90]}"
    return "NO-TEST",""
for s in ["arena","experimental","caveman","singularity","nemo-guardrails",
          "component-reality-check","sprint","scout","private-mode","gpu-sandbox"]:
    print(s, why(s))
EOF
```

| # | primitiva | auditor dice | realidad verificada | ¿correcto? |
|---|---|---|---|---|
| 1 | `arena` | ON_DEMAND "covered by test" | matchea `"optional_arena"` en `test_publication_safety_cli.py` | ❌ falso |
| 2 | `experimental` | ON_DEMAND "covered by test" | matchea la clave `opencode["experimental"]` en `test_consumer_project_projection.py` | ❌ falso |
| 3 | `caveman` | ON_DEMAND "covered by test" | matchea un `mkdir` de `.claude/plugins/caveman` en `test_check_upstream_changes.py` | ❌ falso |
| 4 | `nemo-guardrails` | ON_DEMAND "covered by test" | matchea `SERVICE_COMPOSE_MAP["nemo-guardrails"]` en `test_smart_infra.py` | ❌ falso |
| 5 | `component-reality-check` | ON_DEMAND "covered by test" | matchea un **comentario** en `test_skill_router.py` | ❌ falso |
| 6 | `sprint` | ON_DEMAND "covered by test" | matchea `test_no_sprint_still_adds_...` — "sprint" dentro de "no_sprint" | ❌ falso |
| 7 | `scout` | ON_DEMAND "covered by test" | matchea el literal `"scout",` en una lista | ❌ falso |
| 8 | `singularity` | ON_DEMAND "covered by test" | **sí**: `tests/behavior/test_singularity.py` existe | ✅ correcto |
| 9 | `private-mode` | ON_DEMAND (contrato) | **sí**: `tests/behavior/test_private_mode.py` existe | ✅ correcto |
| 10 | `gpu-sandbox` | ON_DEMAND "invocation contract" | **NO-TEST**; clasificada por la escotilla del §3, no por test | ⚠️ etiqueta técnicamente cierta, señal vacía |

**7 de 10 mal clasificadas por la razón declarada.** De las 8 que alegaron "covered by test", **6 son ruido de substring**.

Dos verificaciones adicionales, para ser justo: `hooks/destructive-rm-blocker.sh` → REAL "fires actively (14 rows in hook-health.jsonl last 7d)" y `scripts/aspirational_audit.py` → REAL "writes to an existing metrics JSONL". **Ambas correctas.** La detección de hooks vía telemetría de disparos real (`fire_count_7d`) es la parte sana del auditor.

### Sentencia

`scripts/aspirational_audit.py` **no miente deliberadamente, pero su resultado no es utilizable como evidencia**:

- **En hooks** funciona razonablemente: usa disparos reales de `hook-health.jsonl`.
- **En skills** tiene **poder discriminante cero**: 192/192 idénticas, por dos bugs independientes (§ defectos 2 y 3).
- **En `lib/`** no audita nada y no avisa (§ defecto 1).
- **Su métrica de titular (`0.0%`) e incluso su lista de "worst offenders" (vacía) son artefactos de diseño**, no hallazgos.

El skill `/component-reality-check` que lo envuelve promete "REAL / DORMANT / UNWIRED / METADATA counts + worst offenders + trend". **Hoy no puede entregar ni DORMANT, ni UNWIRED, ni worst offenders.**

---

## 5. Hooks, rules y primitivas secundarias

### Hooks — **la dimensión más sana; 0 registros rotos**

Corrección a mi propio primer pase: `settings.json` **no** es la única superficie de registro. `cognitive-os.yaml → harness.hooks` es un superconjunto (190 ⊃ 154).

```bash
python3 - <<'EOF'
import json,re,yaml
from pathlib import Path
reg={p for ev,a in json.load(open(".claude/settings.json")).get("hooks",{}).items()
       for m in a for hk in m.get("hooks",[]) for p in re.findall(r'hooks/[\w./-]+\.sh',hk.get("command",""))}
yreg={v["script"] for v in (yaml.safe_load(open("cognitive-os.yaml"))["harness"]["hooks"] or {}).values()
      if isinstance(v,dict) and v.get("script")}
disk={str(f) for f in Path("hooks").rglob("*.sh")}; top=disk-{p for p in disk if "_lib/" in p}
u=reg|yreg
print("settings.json:",len(reg)," cognitive-os.yaml:",len(yreg)," union:",len(u))
print("REGISTRADOS PERO SIN ARCHIVO:",len(u-disk))
print("standalone en disco:",len(top)," NO REGISTRADOS:",len(top-u))
EOF
```

| métrica | valor |
|---|---|
| `.sh` en `hooks/` | 289 |
| de los cuales `hooks/_lib/` (helpers, no son hooks) | 32 |
| hooks standalone | 257 |
| registrados (`cognitive-os.yaml` ∪ `settings.json`) | **190** |
| **registrados que apuntan a archivo inexistente** | **0** |
| no registrados en ninguna superficie | 67 (**26%**) |

Y hay gobernanza real sobre los no registrados: de los 103 ausentes de `settings.json`, **94 están documentados** en `manifests/hook-registration-classification.yaml` con `status`, `rationale` y `next_action` (p. ej. `conditional_opt_in` con motivo explícito). Los 9 restantes —incluidos `destructive-rm-blocker`, `destructive-git-blocker`, `direct-main-guard`, `conflict-marker-guard`— **sí están registrados**, en `cognitive-os.yaml:1157+`. Es decir: **no hay guardas de seguridad huérfanas**. Esta es la parte del sistema que mejor resiste la auditoría.

### Rules — 92% resuelven

```bash
python3 - <<'EOF'
import re
from pathlib import Path
k=sorted(set(re.findall(r'\[`([a-z0-9-]+)`\]',Path("rules/RULES-COMPACT.md").read_text())))
miss=[x for x in k if not (Path("rules")/f"{x}.md").is_file()]
print(f"ref-keys: {len(k)}  resuelven: {len(k)-len(miss)}  faltan: {len(miss)}"); print(miss)
files={p.stem for p in Path("rules").glob("*.md")}-{"RULES-COMPACT"}
print("archivos rules/*.md:",len(files),"| huérfanos:",sorted(files-set(k)))
EOF
```

- ref-keys distintas en `RULES-COMPACT.md`: **138**
- con `rules/<key>.md` real: **127 (92%)**
- **faltantes (11):** `cognitive-os-changes`, `component-classification`, `component-reality-check`, `cost-predictor`, `dogfood-score`, `dogfooding`, `ecosystem-tools`, `library-selection`, `os-vs-project`, `plan-first`, `stash-mutation-reversibility`
- archivos `rules/*.md`: 128 · nunca referenciados: **1** (`ROADMAP`)

La premisa del brief ("decenas de claves sin archivo") **no se sostiene**: son 11, y varias apuntan a skills que sí existen (`component-reality-check`, `cost-predictor`, `dogfood-score`) — el ref-key confunde skill con rule, no es capacidad inventada.

### Primitivas secundarias (tratamiento superficial, por diseño)

```bash
for d in packages squads agents templates workflows; do echo "$d: $(ls -1 $d | wc -l)"; done
```

| dir | entradas | lectura |
|---|---|---|
| `packages/` | 37 | **sustancial y real** — 75 de las 192 skills viven acá y se exponen por symlink; incluye `_archived` |
| `templates/` | 34 | plausible; plantillas `.md`/`.j2` referenciadas por skills |
| `workflows/` | 16 | pipelines Python reales (`backend_*_pipeline.py`), pero contiene `DEPRECATED.md` |
| `squads/` | **1** | un solo `organization.yaml`. La palabra "squads" en la documentación sugiere una capacidad que **es un archivo** |
| `agents/` | **1** | un solo `test-coverage-enforcer.md`. Idem |

**`squads` y `agents` son los casos más claros de inflación de vocabulario:** se nombran como familias de primitivas y son un archivo cada una.

---

## 6. No verificado

Explícito, para que nadie lo lea como probado:

1. **La corrida "estricta" de mi clasificador no completó.** El endurecimiento (excluir comentarios; exigir `skills/<n>`, `skill_name="<n>"`, `"<n>",` o `/<n>`) está en el Anexo A, pero **la distribución final es la del test permisivo**. Por eso el 72.9% REAL es **techo, no valor**. Falsos positivos ya confirmados a mano: `caveman`, `sprint`, `scout`.
2. **No ejecuté los 257 hooks.** "0 registrados apuntan a archivo inexistente" es existencia de archivo, **no** que corran sin error. La pregunta 2 del encargo ("¿cuántos ejecutan sin error?") **queda sin responder** — ejecutarlos tiene efectos secundarios y el encargo era read-only.
3. **No corrí la suite de tests**, así que no sé cuántos de los tests que el auditor invoca como evidencia efectivamente pasan hoy.
4. **No audité `cos_lib/` (369 módulos) por mi cuenta.** Solo probé que el auditor del repo los ignora. La proporción REAL/DORMANT de la capa de librerías **se desconoce** — y es el hueco más grande que queda abierto.
5. **`packages/`, `templates/`, `workflows/` recibieron conteo, no clasificación.** No apliqué el clasificador a sus contenidos.
6. **La telemetría (`skill-invocations.jsonl`, 1 línea; `hook-health.jsonl`) no fue validada** contra la actividad real de sesiones. Si el logger no se dispara, "fires actively (14 rows)" mide el logger, no el hook.
7. **No verifiqué los 75 symlinks de packages uno por uno** más allá de que ninguno esté roto.

---

## Anexo A — `judge_primitives.py`

Guardado en scratchpad durante la sesión; se incluye íntegro acá para que el informe sea autosuficiente y reproducible. Read-only, exit 0.

```python
#!/usr/bin/env python3
"""
judge_primitives.py — clasificador REAL/DORMANT/METADATA independiente.
NO reutiliza scripts/aspirational_audit.py.

Premisa verificada: cos_lib/skill_router.py auto-descubre todo */SKILL.md y
arma el ruteo desde el frontmatter. Las skills NUNCA se registran una por una,
así que "estar en un registro" es uniforme y no discrimina. El discriminador
honesto es si invocar la skill hace algo.

  REAL     = código que se ejecuta la despacha, o hay telemetría de invocación.
  DORMANT  = alcanzable por el router Y su implementación resuelve, sin llamador.
  METADATA = sin implementación: no cita comando ejecutable ni tiene hermano
             ejecutable, o toda ruta que cita está rota.

manifests/ + CATALOG* + docs/ se cuentan aparte como `inventory_only`:
estar listado en un inventario es una declaración, no cableado.

Uso: python3 judge_primitives.py [--json]
"""
from __future__ import annotations
import json, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
for cand in [Path.cwd(), *Path.cwd().parents]:
    if (cand / "cognitive-os.yaml").is_file() and (cand / "skills").is_dir():
        ROOT = cand
        break
SKILLS = ROOT / "skills"


def read(p: Path) -> str:
    try:
        return p.read_text(errors="replace")
    except OSError:
        return ""


def _strip_comments(text: str) -> str:
    """Una skill nombrada en un comentario no es cableado."""
    return "\n".join(ln for ln in text.splitlines()
                     if not ln.lstrip().startswith(("#", "//")))


def build_exec_corpus() -> str:
    parts = []
    for rel in (".claude/settings.json", ".claude/settings.local.json", "Makefile"):
        p = ROOT / rel
        if p.is_file():
            parts.append(read(p))
    for rel, pats in (("hooks", ("*.sh",)), ("scripts", ("*.sh", "*.py")),
                      ("cos_lib", ("*.py",)), (".claude/commands", ("*.md",))):
        d = ROOT / rel
        if d.is_dir():
            for pat in pats:
                for f in d.rglob(pat):
                    parts.append(_strip_comments(read(f)))
    return "\n".join(parts)


def build_inventory_corpus() -> str:
    parts = []
    d = ROOT / "manifests"
    if d.is_dir():
        for pat in ("*.yaml", "*.yml", "*.json"):
            for f in d.rglob(pat):
                parts.append(read(f))
    for rel in ("skills/CATALOG.md", "skills/CATALOG-COMPACT.md",
                "skills/CATALOG-MICRO.md", "skills/REGISTRY.lock"):
        p = ROOT / rel
        if p.is_file():
            parts.append(read(p))
    return "\n".join(parts)


def load_invocations() -> Counter:
    """Parsea con el esquema que el logger REALMENTE escribe (skill_name)."""
    c = Counter()
    for line in read(ROOT / ".cognitive-os/metrics/skill-invocations.jsonl").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        pl = r.get("payload", {}) or {}
        n = r.get("skill") or pl.get("skill") or pl.get("skill_name") or ""
        if n:
            c[n] += 1
    return c


PATH_RE = re.compile(r"(?<![\w/.-])((?:scripts|cos_lib|hooks|bin|cmd|packages|templates)"
                     r"/[\w./-]+?\.(?:py|sh|go))(?![\w/])")
CLI_RE = re.compile(r"(?:^|[`\s])(cos-[a-z0-9-]+|cos\s+[a-z][a-z0-9-]+)", re.M)


def strip_frontmatter(txt: str):
    if txt.startswith("---"):
        end = txt.find("\n---", 3)
        if end != -1:
            return txt[:end], txt[end + 4:]
    return "", txt


def main() -> int:
    exec_corpus, inv_corpus = build_exec_corpus(), build_inventory_corpus()
    invocations = load_invocations()
    rows = []
    for entry in sorted(SKILLS.iterdir()):
        md = entry / "SKILL.md"
        if not md.is_file():
            continue
        name = entry.name
        fm, body = strip_frontmatter(read(md))
        cited = sorted(set(PATH_RE.findall(body)))
        ok = [p for p in cited if (ROOT / p).exists()]
        bad = [p for p in cited if not (ROOT / p).exists()]
        has_cli = bool(CLI_RE.search(body))
        sib = [f for f in entry.rglob("*")
               if f.is_file() and f.suffix in (".py", ".sh", ".go", ".js")]
        routable = ("routing_patterns:" in fm) or ("routing_intents:" in fm)

        # Test de despacho ESTRICTO: el match pelado es ruido de substring
        # ("sprint" matchea sprint-status.yaml; "scout" matchea repo-scout).
        n = re.escape(name)
        dispatch = re.compile(
            r"skills/" + n + r"(?![\w-])"
            r"|skill_name\s*=\s*[\"']" + n + r"[\"']"
            r"|[\"']" + n + r"[\"']\s*[,:\]\)]"
            r"|(?<![\w-])/" + n + r"(?![\w-])")
        called = bool(dispatch.search(exec_corpus))
        listed = bool(re.search(r"(?<![\w-])" + n + r"(?![\w-])", inv_corpus))
        invoked = invocations.get(name, 0)
        has_impl = bool(ok or sib or has_cli)

        if invoked or called:
            cls, why = "REAL", (f"invoked={invoked}" if invoked else "called by executing code")
        elif has_impl and routable:
            cls, why = "DORMANT", (f"impl resolves ({len(ok)} paths, {len(sib)} files,"
                                   f" cli={has_cli}); router-reachable; no caller")
        elif bad and not ok:
            cls, why = "METADATA", f"cites {len(bad)} repo paths, NONE resolve"
        else:
            cls, why = "METADATA", "no runnable command, no sibling impl, no caller"

        rows.append(dict(name=name, kind="package-symlink" if entry.is_symlink() else "canonical",
                         classification=cls, reason=why, invoked=invoked, called=called,
                         inventory_only=(listed and not called), routable=routable,
                         cited_ok=len(ok), cited_broken=len(bad), broken=bad[:6],
                         sib=len(sib), cli=has_cli, bytes=md.stat().st_size))

    total = len(rows)
    counts = Counter(r["classification"] for r in rows)
    if "--json" in sys.argv:
        print(json.dumps(dict(total=total, counts=dict(counts), rows=rows), indent=2))
        return 0
    print(f"SKILLS — clasificación independiente (n={total})")
    for c in ("REAL", "DORMANT", "METADATA"):
        n_ = counts.get(c, 0)
        print(f"  {c:<9} {n_:4d}  {100.0*n_/total:5.1f}%")
    print(f"  router-reachable: {sum(1 for r in rows if r['routable'])}/{total}")
    print(f"  inventariadas pero nunca llamadas: {sum(1 for r in rows if r['inventory_only'])}")
    print(f"  invocaciones en telemetría: {sum(invocations.values())} "
          f"en {len(invocations)} skills distintas")
    print("\n--- Skills que citan rutas INEXISTENTES ---")
    for r in sorted([r for r in rows if r["cited_broken"]], key=lambda r: -r["cited_broken"]):
        print(f"  {r['name']:<32} {r['cited_broken']} rotas  {r['broken']}")
    for cls in ("METADATA", "DORMANT"):
        sel = sorted([r for r in rows if r["classification"] == cls], key=lambda r: -r["bytes"])
        print(f"\n--- {cls} (top 20 por tamaño) ---")
        for r in sel[:20]:
            print(f"  {r['name']:<32} {r['bytes']:6d}B  {r['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## Cierre

Lo declarado y lo cableado **no están tan lejos como sugería el encargo**: el 73% de las skills tiene algo ejecutable detrás (techo), los 190 hooks registrados apuntan todos a archivos que existen, el 92% de las rules resuelve, y los hooks sin registrar tienen justificación escrita en un manifiesto. El problema no es un sistema hueco.

**El problema es el instrumento.** El auditor propio reporta `0.0%` de deuda y una lista vacía de peores ofensores — y ese resultado se produce por tres bugs (`lib/` inexistente, mismatch `skill_name`/`skill`, escotilla que pasa el 100%) más una métrica que esconde al 76% de los componentes en un cubo que no se imprime. Un gate que no puede fallar no es un gate.

Prioridad de reparación, en orden: **(1)** `walk_lib` → `cos_lib` (369 módulos a ciegas); **(2)** leer `payload.skill_name`; **(3)** eliminar `"trigger:"`/`"triggers:"`/`"routing_intents:"` de la escotilla de contrato — con el router auto-descubriendo, el frontmatter de ruteo lo tiene todo el mundo y no prueba nada; **(4)** reemplazar el substring-match de `has_covering_test` por archivo de test exacto; **(5)** imprimir `ON_DEMAND` en la tabla y decidir explícitamente si entra o no en el ratio.
