# Juez 3 — Inventario real de primitivas y veracidad de su documentación

**Fecha:** 2026-08-15 · **HEAD:** `8602ddc70` (2026-07-28) · **Modo:** read-only
**Único archivo escrito en el repo:** este informe.

**Estado de la máquina al arrancar (declarado por exigencia del encargo):**

```bash
sysctl vm.swapusage   # total = 37888.00M  used = 37169.31M  free = 718.69M
uptime                # load averages: 9.51 8.11 10.38
```

Swap al 98%, load 9.5. **Plan degradado:** no se corrió la suite de tests, no se
ejecutó ningún hook, y todo comando se acotó (sin `find` sobre el árbol completo,
sin lecturas de los JSONL de 10 MB fuera de parseo en streaming). Lo que quedó sin
hacer por esta razón está listado en §6.

---

## 1. Veredicto (una línea)

El inventario está **inflado por un factor de ~1.4 en hooks y de 3–5 en las familias
chicas**, pero el hallazgo grave no es el conteo sino que **el registro que la
documentación declara canónico (`cognitive-os.yaml > harness.hooks`, ADR-064) no lo
lee nadie en el camino de Claude Code**: el `settings.json` se genera desde una lista
**hardcodeada en bash**, y 36 hooks declarados canónicos —incluido el `rate-limiter`
que una rule del proyecto describe como "activo por defecto"— nunca llegan a ejecutarse.

---

## 2. Censo y cableado por familia

Tercera columna: **muestreada, no censada** — la veracidad documental exige leer código
contra prosa y se hizo sobre 32 primitivas (§4). Se reporta como `verdaderas / muestreadas`.

| familia | existen | cableadas | doc veraz (muestra) |
|---|---|---|---|
| **skills** | **192** (de 197 entradas) | **192** alcanzables por el router · **2** invocadas alguna vez | 4/7 |
| **hooks** | **255** únicos (257 entradas) | **181** con camino de ejecución · **156** dispararon alguna vez | 5/12 |
| **rules** | **128** (+1 índice) | **127** resuelven desde el índice; cargador cableado | 2/6 |
| **workflows** | **7** `.py` (16 entradas) | **0** | 1/2 |
| **agents** | **1** | **0** | 0/1 |
| **squads** | **1** | **0** | 0/1 |
| **templates** | **30** archivos raíz (60 en total, 5 subdirs) | **29** referenciados; **1** con consumidor programático verificado | 1/2 |

### 2.1 Skills — comandos

```bash
ls -1 skills/ | wc -l                                       # 197  ← el ls crudo
find skills -maxdepth 1 -mindepth 1 -type d | wc -l         # 118  directorios
find skills -maxdepth 1 -mindepth 1 -type l | wc -l         #  75  symlinks
find skills -maxdepth 1 -mindepth 1 -type f | wc -l         #   4  catálogos, no primitivas
find skills -maxdepth 2 -mindepth 2 -name SKILL.md | wc -l  # 117
for d in $(find skills -maxdepth 1 -mindepth 1 -type d); do [ -f "$d/SKILL.md" ] || echo "$d"; done
                                                            # skills/auto-generated  (solo .gitkeep)
find skills -maxdepth 1 -type l ! -exec test -e {} \; -print   # (vacío: 0 symlinks rotos)
```

- **4 no-primitivas:** `CATALOG.md`, `CATALOG-COMPACT.md`, `CATALOG-MICRO.md`, `REGISTRY.lock`.
- **1 directorio vacío:** `skills/auto-generated/`.
- **75 symlinks** a `packages/*/skills/*`, todos resuelven; ninguno apunta dentro de `skills/`
  (verificado con `readlink -f`), así que **no hay doble conteo**: universo real **192**.
- `.claude/skills/` tiene 197 entradas pero **191 son symlinks** y sólo 6 `SKILL.md` propios:
  es proyección, no inventario adicional.

**Cableado.** El router auto-descubre; no hay registro por skill:

```bash
sed -n '408,430p' cos_lib/skill_router.py   # search_roots = skills/, .cognitive-os/skills/, packages/*/skills/
                                            # for skill_md in sorted(root.glob("*/SKILL.md"))
```

Las 192 tienen frontmatter de ruteo (`routing_intents: 191`, `routing_patterns: 127`,
**0 sin ninguno**), así que "estar registrada" es uniforme y **no discrimina nada**.
La señal que sí discrimina es la invocación real, y es casi nula:

```bash
cat .cognitive-os/metrics/skill-invocations.jsonl | wc -l   # 3 eventos en toda la vida del archivo
```

3 eventos, **2 skills distintas** (`encargo-refutable`, `ruteo-de-agentes`), y dos de los
tres son de esta misma sesión (`2026-08-15T03:14`). Cualquier afirmación del tipo "esta
skill se usa" no tiene base. Sugerencias del router sí hay (246 eventos en
`skill-suggestion.jsonl`), pero sugerir no es invocar.

**Inconsistencia de catálogo:** 6 skills existen y no figuran en `CATALOG.md`
(`epistemic-review`, `so-impact-eval`, `lean-code`, `artifact-workflow`,
`agent-run-supervision`, `skill-optimization`). `REGISTRY.lock` sí las tiene.

### 2.2 Hooks — comandos

```bash
find hooks -name '*.sh' | wc -l                                        # 289
find hooks/_lib -name '*.sh' | wc -l                                   #  32  helpers, no son hooks
find hooks -type l | wc -l                                             #  42  symlinks
find hooks -name '*.sh' -exec readlink -f {} \; | sort -u | wc -l      # 287  ← 2 menos: hay alias internos
find hooks -type l | while read -r l; do t=$(readlink -f "$l"); \
  case "$t" in "$PWD/hooks/"*) echo "$l -> ${t#$PWD/}";; esac; done
#   hooks/reaper-heartbeat.sh        -> hooks/reaper-daemon-launcher.sh
#   hooks/cos-executor-heartbeat.sh  -> hooks/cos-executor-daemon-launcher.sh
```

**Universo real: 255 hooks** (289 − 32 helpers − 2 alias internos). 40 de los 42 symlinks
apuntan a `packages/*/hooks/` y son la misma primitiva; 0 rotos.

**Las tres superficies de registro, medidas por separado:**

```bash
python3 - <<'EOF'
import json,re,yaml
from pathlib import Path
def paths(f):
    d=json.load(open(f)); s=set()
    for ev,arr in d.get('hooks',{}).items():
        for m in arr:
            for hk in m.get('hooks',[]):
                s|=set(re.findall(r'hooks/[\w./-]+\.sh',hk.get('command','')))
    return s
cur  = paths('.claude/settings.json')
disp = set(re.findall(r'hooks/[\w./-]+\.sh', Path('hooks/bash-hot-path-dispatcher.sh').read_text()))
yy   = {v['script'] for v in yaml.safe_load(open('cognitive-os.yaml'))['harness']['hooks'].values()}
print(len(cur), len(disp), len(cur|disp), len(yy), len(yy-cur-disp))
EOF
# 154 29 181 190 9
```

| superficie | n | qué es |
|---|---|---|
| `cognitive-os.yaml > harness.hooks` | **190** scripts (200 entradas) | el registro **declarado** canónico |
| `.claude/settings.json` (perfil vigente `maintainer`) | **154** | lo que Claude Code realmente carga |
| fan-out de `hooks/bash-hot-path-dispatcher.sh` | **29** | gates que corren dentro del hot path de Bash |
| **cableado efectivo** (unión) | **181** | |
| perfil `full` (máximo posible) | **183** | ni el perfil máximo llega a 190 |
| **nunca dispararon** (`hook-timing` ∪ `hook-health`) | **101** de 257 | |

```bash
# disparos reales, sobre las dos telemetrías
python3 -c "
import json,re
from pathlib import Path
fire=set()
for fn in ('.cognitive-os/metrics/hook-timing.jsonl','.cognitive-os/metrics/hook-health.jsonl'):
    for line in open(fn):
        try: r=json.loads(line)
        except ValueError: continue
        h=re.sub(r'\.sh$','',re.sub(r'^.*/','',str(r.get('hook') or '')))
        if h: fire.add(h)
disk={re.sub(r'\.sh\$','',f.name) for f in Path('hooks').iterdir() if f.is_file() and f.suffix=='.sh'}
print(len(fire), len(disk-fire))"
# 156 dispararon alguna vez · 101 nunca
# ventana de hook-timing.jsonl: 2026-07-20T14:28Z → 2026-08-15T03:53Z (37.424 filas)
```

**Los 6 declarados canónicos que no tienen ningún camino de ejecución en ningún perfil:**
`auto-refine.sh`, `auto-verify.sh`, `concurrent-write-guard-codex-proxy.sh`, `dod-gate.sh`,
`publication-safety.sh`, `task-completed.sh`. `rate-limiter.sh`, `rate-limit-precheck.sh` y
`agent-bash-cwd-enforcer.sh` sólo aparecen bajo `PROFILE=full`, que **no es el perfil vigente**.

### 2.3 El contrato de proyección que el encargo pedía verificar: **no se sostiene**

El brief dice que `cognitive-os.yaml > harness.hooks` es el registro canónico y que
`scripts/_lib/settings-driver-claude-code.sh` lo proyecta. Lo segundo es falso.

```bash
grep -n 'CONFIG_FILE' scripts/_lib/settings-driver-claude-code.sh
# 39:CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"     ← asignado y NUNCA usado
grep -c 'yaml' scripts/_lib/settings-driver-claude-code.sh   # sólo en comentarios
grep -o 'hooks/[a-z0-9._-]*\.sh' scripts/_lib/settings-driver-claude-code.sh | sort -u | wc -l
# 184  ← lista hardcodeada dentro del bash
```

El driver **no abre el YAML**: emite una lista literal escrita a mano. Prueba de que su
salida es exactamente el `settings.json` actual, y de que el YAML no participa:

```bash
bash scripts/_lib/settings-driver-claude-code.sh --emit > /tmp/emit.json   # exit 0
# emit == settings.json actual: True   (154 == 154, diferencia simétrica vacía)
# en el YAML y NO en settings.json: 36
```

Consecuencias:

1. Hay **dos fuentes de verdad**, y la que manda es el bash. Escribir un hook en
   `harness.hooks` no lo cablea.
2. El `--check` del driver imprime `OK: settings.json is in sync with canonical harness.hooks`
   comparando el archivo **contra su propio emit hardcodeado**. Es un gate que no puede fallar
   por la razón que dice medir.
3. El test `tests/unit/test_cognitive_os_yaml_harness_hooks.py` sólo exige que
   `harness.hooks` sea **superconjunto** de `settings.json` (línea ~170). 190 ⊃ 154 pasa; que
   36 declarados no se ejecuten nunca **no lo ve nadie**.
4. Los drivers `bare` y `opencode` dicen leer el YAML (0 y 1 literal `hooks/*.sh`
   respectivamente) — **no verificado**, ver §6.

### 2.4 Rules

```bash
find rules -name '*.md' | wc -l                                   # 129
find rules -type l | wc -l                                        #  17  (→ packages/*, 0 rotos)
find rules -name '*.md' -exec readlink -f {} \; | sort -u | wc -l # 129  (sin alias internos)
find rules -mindepth 1 -type d | wc -l                            #   0
```

**128 rules + 1 índice** (`RULES-COMPACT.md`, que no es una rule).

```bash
python3 -c "
import re
from pathlib import Path
k=sorted(set(re.findall(r'\[\`([a-z0-9-]+)\`\]',Path('rules/RULES-COMPACT.md').read_text())))
miss=[x for x in k if not (Path('rules')/f'{x}.md').is_file()]
files={p.stem for p in Path('rules').glob('*.md')}-{'RULES-COMPACT'}
print(len(k), len(k)-len(miss), miss, sorted(files-set(k)))"
# 138 ref-keys · 127 resuelven · 11 sin archivo · 1 huérfano: ['ROADMAP']
```

Faltantes: `cognitive-os-changes`, `component-classification`, `component-reality-check`,
`cost-predictor`, `dogfood-score`, `dogfooding`, `ecosystem-tools`, `library-selection`,
`os-vs-project`, `plan-first`, `stash-mutation-reversibility`.

**Cableado:** `cos_lib/ref_key_loader.py` ← `hooks/inject-phase-context.sh`, que **sí** está
en `settings.json` y disparó 24 veces. La cadena de carga existe.

### 2.5 Workflows, agents, squads, templates

```bash
find workflows -maxdepth 1 -type f | wc -l   # 10 (7 .py + README + DEPRECATED + pyproject)
find workflows -maxdepth 1 -mindepth 1 -type d | wc -l   # 6
find agents -type f | wc -l    # 1
find squads -type f | wc -l    # 1
find templates -maxdepth 1 -type f | wc -l   # 30   ·  find templates -type f | wc -l  # 60
```

- **workflows:** `DEPRECATED.md` declara el directorio entero legado del proyecto *Sazonia*
  y "superseded by the `lib/` modules". Ninguno de los 6 pipelines tiene una sola referencia
  fuera del propio directorio. **Cableadas: 0.**
- **agents: 1 archivo.** `agents/test-coverage-enforcer.md` declara
  `triggers: [file_pattern: "**/*.go"]`. Ningún ejecutable parsea ese frontmatter
  (`grep -rn '/agents/' cos_lib hooks scripts` sólo devuelve inventariadores:
  `primitive_readiness_ledger.py`, `primitive_usage_map.py`). **Cableadas: 0.**
- **squads: 1 archivo.** `squads/organization.yaml` nombra 6 agentes; **1 existe**
  (`test-coverage-enforcer`). El único lector, `hooks/inject-phase-context.sh:167-173`,
  busca `"$SQUADS_DIR/$ACTIVE_SQUAD.md"` — **extensión `.md`**, y no hay ni un `.md` en
  `squads/` (`find squads -name '*.md' | wc -l` → 0), ni `active_squad` en `cognitive-os.yaml`
  (`grep -c active_squad cognitive-os.yaml` → 0). El camino es doblemente muerto. **Cableadas: 0.**
- **templates:** 29 de 30 archivos raíz están referenciados por al menos un archivo de
  `scripts/hooks/cos_lib/skills/rules/manifests`; el único sin referencia es
  `templates/confidentiality.yaml`, que es **archivo sin commitear del operador** y no se tocó.

---

## 3. Duplicación conceptual (listada, no unificada)

| # | primitivas | evidencia del solape |
|---|---|---|
| 1 | `rate-limiter.sh` · `rate-limit-precheck.sh` · `rate-limit-detector.sh` · `rate-limit-drain.sh` | 4 hooks, un concepto. Registro: `detector` 1 / `drain` 1 / `limiter` 0 / `precheck` 0. Disparos: 1653 / 1288 / 0 / 0. `precheck` invoca a `limiter`, y ninguno de los dos corre. |
| 2 | `confidence-gate.sh` · `confidence-gate-llm.sh` | El header de `-llm` lo dice solo: *"the legacy confidence-gate.sh handles blocking"*. `-llm` no está en `settings.json` (`grep -c` → 0). Dos implementaciones del mismo gate, ninguna bloqueando hoy. |
| 3 | `red-team` · `security-red-team` · `redteam-harness` · `pentest-self` | `security-red-team` se autodescribe *"Unified red-team primitive"* y las otras tres siguen existiendo como skills separadas. La unificación que declara no ocurrió. |
| 4 | `session-wrapup` · `os-session-wrapup` · `session-backlog` · `session-pending-brief` · `session-pending-close` · `session-report-executive` | 6 skills de cierre/apertura de sesión. `os-session-wrapup` declara explícitamente *"Runs the generic session-wrapup first, then adds…"* — envoltorio de otra skill promovido a primitiva. |
| 5 | `skills/CATALOG.md` · `CATALOG-COMPACT.md` · `CATALOG-MICRO.md` · `REGISTRY.lock` | 4 índices del mismo conjunto, ya divergentes: `CATALOG.md` omite 6 skills que `REGISTRY.lock` tiene. |
| 6 | `cognitive-os.yaml > harness.hooks` · lista hardcodeada del driver CC | §2.3. Dos registros del mismo hecho, con 36 de diferencia. |
| 7 | `scripts/aspirational_audit.py` · `scripts/primitive_usage_map.py` · `scripts/primitive_readiness_ledger.py` · `scripts/primitive-coherence-audit.py` | 4 auditores de la misma pregunta ("¿esta primitiva está cableada?"), cada uno con su propio criterio; el primero devuelve 0.0% por construcción (§4). |

---

## 4. Muestreo de veracidad documental — 32 primitivas

**Cómo se eligieron (declarado):** 32 sobre un universo de ~600 (192 skills + 255 hooks +
128 rules + 39 del resto). Muestreo **estratificado y dirigido, no aleatorio** — el objetivo
era falsar, no estimar. Por familia: (a) toda primitiva sobre la que `RULES-COMPACT.md`
hace un claim binario y verificable (*"hook-enforced"*, *"CI-enforced"*, *"CLI"*) — son las
más caras de tener mal; (b) en hooks, los 5 de mayor conteo de disparos y 5 declarados que
nunca dispararon; (c) en skills, las que citan un ejecutable concreto (falsables) más una de
prosa pura como control; (d) las familias de 1 archivo, censadas completas.
**Sesgo consciente:** la muestra sobrerrepresenta lo falsable, así que la tasa de acierto
observada (**13/32**) es un **piso**, no la del universo.

| # | primitiva | qué promete | qué hace | categoría | comando |
|---|---|---|---|---|---|
| 1 | `hooks/rate-limiter.sh` | header: *"PreToolUse hook on Bash, Agent, Edit, Write. Blocks (exit 2)"* | no está en `settings.json` ni en el dispatcher; **0 disparos** en 37.424 filas | **NO HACE NADA** | `grep -c rate-limiter .claude/settings.json` → 0 |
| 2 | `rules/rate-limiting.md` | *"El rate limiter está activo por defecto para Bash, Agent, Edit y Write a través de `hooks/rate-limiter.sh`"* | el hook no corre (#1); además cita `lib/rate_limiter.py`, que no existe | **NO HACE NADA** | `ls lib/` → No such file |
| 3 | `hooks/rate-limit-drain.sh` | drena la cola de reintentos que llena el limiter | registrado, **1288 disparos** — drenando una cola cuyo único productor nunca corre (`rate-limit-queue.jsonl` sin escribir desde 2026-05-01) | **HACE MENOS** | `ls -la .cognitive-os/rate-limit-queue.jsonl` |
| 4 | `hooks/rate-limit-precheck.sh` | invoca al limiter antes del tool call | no registrado, 0 disparos | **NO HACE NADA** | `grep -c rate-limit-precheck .claude/settings.json` → 0 |
| 5 | `hooks/blast-radius.sh` | `RULES-COMPACT` §5: *"Blast radius **hook-enforced**"* | su propio header, línea 5: *"Advisory only (exit 0) — does NOT block"* | **HACE MENOS** | `sed -n '5p' hooks/blast-radius.sh` |
| 6 | `hooks/confidence-gate.sh` | `RULES-COMPACT` §3: *"Confidence gate **hook-enforced**"* | bloquea sólo en `production`/`maintenance`; la fase vigente es `reconstruction` → advisory | **HACE MENOS** | `grep -n '^ *phase:' cognitive-os.yaml` → `reconstruction` |
| 7 | `hooks/confidence-gate-llm.sh` | evaluación LLM del Trust Report | *"Advisory only — never blocks"* **y** no registrado (0 en `settings.json`) | **NO HACE NADA** | `grep -c confidence-gate-llm .claude/settings.json` → 0 |
| 8 | `hooks/content-policy.sh` | `RULES-COMPACT` §10: *"Content policy + confidentiality **hook-enforced**"* | tiene `exit 2` (línea 122), pero está registrado como **PostToolUse** en `Edit\|Write`: corre **después** de escribir | **HACE MENOS** | `python3 -c "…"` → `event=PostToolUse matcher='Edit\|Write'` |
| 9 | `hooks/clarification-gate.sh` | header: *"BLOCKING: exit 2 if ambiguity score > 60"* | registrado PreToolUse:Agent, 24 disparos, `exit 2` en línea 199 | **HACE LO QUE DICE** (alcance: sólo tool `Agent`) | `sed -n '199p' hooks/clarification-gate.sh` |
| 10 | `hooks/destructive-rm-blocker.sh` | bloquea `rm` destructivos | no está en `settings.json`; lo llama el dispatcher cuando el comando matchea `(rm\|rmdir\|mv\|ln)`; 23 filas en `hook-health` | **HACE LO QUE DICE** (vía dispatcher) | `grep -c destructive-rm-blocker .cognitive-os/metrics/hook-health.jsonl` → 23 |
| 11 | `hooks/bash-hot-path-dispatcher.sh` | *"Full profile still projects the exhaustive hook mesh"* | fan-out real a 29 gates, 1308 disparos; `PROFILE=full` proyecta **183**, no los 255 en disco ni los 190 del YAML | **HACE MENOS** | `PROFILE=full bash scripts/_lib/settings-driver-claude-code.sh --emit \| grep -o 'hooks/[a-z0-9._-]*\.sh' \| sort -u \| wc -l` → 183 |
| 12 | `hooks/cognitive-os-health.sh` | cuenta squads/agents/rules como chequeo de salud | no registrado, 0 disparos | **NO HACE NADA** | `grep -c cognitive-os-health .claude/settings.json` → 0 |
| 13 | `hooks/skill-invocation-logger.sh` | registra invocaciones de skills para el auditor | escribe `payload.skill_name`; `aspirational_audit.py:345` lee `payload.skill` → siempre `""` | **HACE OTRA COSA** | `sed -n '345p' scripts/aspirational_audit.py` |
| 14 | `scripts/_lib/settings-driver-claude-code.sh` | header: *"Project cognitive-os.yaml > harness.hooks"* | `CONFIG_FILE` asignado en la línea 39 y jamás usado; emite 184 literales hardcodeados | **HACE OTRA COSA** | `grep -n CONFIG_FILE scripts/_lib/settings-driver-claude-code.sh` |
| 15 | `RULES-COMPACT` §4/§5/§7/§12 | cita `lib/dispatch.py`, `lib/cost_predictor`, `lib/harness_adapter`, `lib/decision_tracker`, `lib/dogfood_scorer` | el directorio `lib/` no existe; los módulos viven en `cos_lib/` (369 `.py`) | **HACE OTRA COSA** | `ls -d lib` → No such file; `ls cos_lib/*.py \| wc -l` → 369 |
| 16 | `RULES-COMPACT` §17 (goal-loop) | *"`cos goal set/status/clear` CLI"* | `cmd/cos` no contiene la palabra `goal`; el CLI real es `scripts/cos-goal` → `scripts/cos_goal.py` | **HACE OTRA COSA** (existe, con otro nombre) | `grep -rl goal cmd/` → vacío; `bash scripts/cos-goal status` → `No active goal.` |
| 17 | `rules/python-naming.md` | enforced por `tests/audit/test_python_naming.py` | el archivo existe (**no se ejecutó**, §6) | **HACE LO QUE DICE** (existencia) | `ls tests/audit/test_python_naming.py` |
| 18 | `rules/bash-naming.md` | enforced por `tests/audit/test_bash_naming.py` | idem | **HACE LO QUE DICE** (existencia) | `ls tests/audit/test_bash_naming.py` |
| 19 | `RULES-COMPACT` §14 (Go) | *"preservado como `.github/workflows/go-quality.yml.disabled`"* | existe | **HACE LO QUE DICE** | `ls .github/workflows/go-quality.yml.disabled` |
| 20 | skill `component-reality-check` | *"REAL / DORMANT / UNWIRED / METADATA counts + worst offenders + trend"* | corrida de hoy: `METADATA 89, REAL 135, ON_DEMAND 686`, ratio `0.0`, `worst_offenders: []`. No entrega DORMANT, ni UNWIRED, ni ofensores | **HACE MENOS** | `python3 scripts/aspirational_audit.py --dry-run --json` |
| 21 | `scripts/aspirational_audit.py` | auditar los componentes del SO | `walk_lib()` línea 430 mira `project_root / "lib"`, inexistente, y **retorna en silencio**: 369 módulos jamás auditados | **HACE MENOS** | `sed -n '429,432p' scripts/aspirational_audit.py` |
| 22 | skill `cost-predictor` | `scripts/cost_predict.py` + `cos_lib/cost_predictor.py` | ambos existen, el CLI corre y responde `--help` | **HACE LO QUE DICE** | `python3 scripts/cost_predict.py --help` → exit 0 |
| 23 | skill `dogfood-score` | `scripts/dogfood_score.py` + `cos_lib/dogfood_scorer.py` | ambos existen, CLI corre | **HACE LO QUE DICE** | `python3 scripts/dogfood_score.py --help` → exit 0 |
| 24 | skill `stash-quarantine` | `scripts/stash_quarantine_audit.py` | existe, CLI corre | **HACE LO QUE DICE** | `python3 scripts/stash_quarantine_audit.py --help` → exit 0 |
| 25 | skill `deep-tool-research` | su único gancho ejecutable es `hooks/deep-research-axis-gate.sh` | el archivo **no existe** (ya reportado el 2026-07-28; sigue igual 18 días después) | **NO HACE NADA** | `ls hooks/deep-research-axis-gate.sh` → No such file |
| 26 | skill `product-answer` | prosa: tarjetas de respuesta de producto (ADR-282) | no cita ningún ejecutable; no hay nada que la contradiga ni que la pruebe | **HACE LO QUE DICE** (no falsable) | `grep -cE '(scripts\|cos_lib\|hooks)/' skills/product-answer/SKILL.md` → 0 |
| 27 | skill `security-red-team` | *"Unified red-team primitive"* | `red-team`, `redteam-harness` y `pentest-self` siguen existiendo como skills separadas | **HACE MENOS** | `ls -1 skills \| grep -E 'red-?team\|pentest'` |
| 28 | `workflows/DEPRECATED.md` | *"superseded by the `lib/` modules"* | `lib/` no existe; el sucesor declarado es una ruta muerta | **HACE OTRA COSA** | `ls -d lib` → No such file |
| 29 | `workflows/run.py` | uso documentado: `uv run .cognitive-os/workflows/run.py feature …` | `.cognitive-os/workflows/` existe pero sólo tiene 2 `.yaml`; **no hay `run.py` ahí** | **HACE OTRA COSA** | `ls .cognitive-os/workflows/` → `bugfix-pipeline.yaml feature-pipeline.yaml` |
| 30 | `agents/test-coverage-enforcer.md` | frontmatter `triggers: [file_pattern: "**/*.go"]` — auto-chequeo al cambiar fuentes | ningún ejecutable parsea ese frontmatter; sólo lo leen inventariadores | **NO HACE NADA** | `grep -rn '/agents/' cos_lib hooks scripts` → sólo `primitive_*_map/ledger.py` |
| 31 | `squads/organization.yaml` | 6 agentes con `agentRef` | 1 de 6 existe; el único lector busca `$ACTIVE_SQUAD.md` y no hay `.md` en `squads/`, ni `active_squad` en el config | **NO HACE NADA** | `find squads -name '*.md' \| wc -l` → 0 |
| 32 | `templates/agent-preamble.md` vs `templates/hook-template.sh` | ambas, plantillas del sistema | `agent-preamble` lo lee `cos_lib/prompt_builder.py:68` por ruta; `hook-template.sh` sólo aparece en un `cp` de prosa dentro de `skills/add-hook` | preamble **HACE LO QUE DICE** / hook-template **HACE MENOS** | `grep -n agent-preamble cos_lib/prompt_builder.py` |

**Resumen del muestreo:** HACE LO QUE DICE **13** · HACE MENOS **10** · HACE OTRA COSA **6** ·
NO HACE NADA **8** (33 veredictos sobre 32 filas: la #32 contrasta dos templates).
**41% de acierto sobre una muestra elegida para falsar.**

---

## 5. Correcciones

### 5.1 A las premisas del encargo

| premisa | qué dice | qué mide |
|---|---|---|
| "257 archivos de hook en disco" | 257 | **257 entradas, 255 primitivas.** `hooks/reaper-heartbeat.sh` y `hooks/cos-executor-heartbeat.sh` son symlinks a otros hooks **dentro de `hooks/`**. `readlink -f \| sort -u` → 287 de 289. |
| "155 registrados en el origen" | 155 | **190 en el origen declarado** (`cognitive-os.yaml`), **154 en la proyección** (`settings.json`). El 155 se parece al segundo número, no al primero — y el encargo llama "origen" al que no manda. |
| "`.claude/settings.json` es generado; el registro canónico sería `cognitive-os.yaml`, proyectado por el driver" | — | **La primera mitad es cierta, la segunda es falsa.** El driver no abre el YAML (§2.3). El registro que gobierna es la lista hardcodeada en bash. |
| "36 registraciones en una instalación fresca" | 36 | No reproducible desde este checkout (requiere instalar en un proyecto limpio). **Coincidencia digna de mirar:** 36 es exactamente el número de hooks declarados en el YAML que **no** llegan a `settings.json`. Puede ser el mismo fenómeno visto desde otro lado, o casualidad. **No verificado.** |
| "31 que dispararon alguna vez en un consumidor" | 31 | No reproducible acá. En **este** repo dispararon **156** distintos (`hook-timing` ∪ `hook-health`, ventana 2026-07-20 → 2026-08-15). |

### 5.2 Al juez anterior (`judge-primitivas-2026-07-28.md`)

Lo que **se confirma** re-corriendo sus comandos: skills 197/118/75/117 y universo 192;
rules 138 ref-keys / 127 resuelven / 11 faltan / 1 huérfano; `aspirational_audit.py` sigue
devolviendo `total 910, ratio 0.0, worst_offenders []`; `walk_lib` sigue apuntando a `lib/`;
`aspirational_audit.py:345` sigue leyendo `payload.skill`; `deep-tool-research` sigue citando
un hook inexistente. **18 días, cero reparaciones.**

Lo que **no se sostiene**:

1. **"257 hooks standalone"** — son 255. No resolvió los 2 alias internos (§5.1).
2. **"67 no registrados"** — son **65** contra la unión que él mismo definió, y **74** si se
   mide contra el mejor camino posible (`full` ∪ dispatcher). Arrastró el denominador malo.
3. **"0 registrados apuntan a archivo inexistente ⇒ la dimensión más sana"** — el dato es
   correcto y la conclusión no. Que los 190 del YAML existan en disco no dice nada sobre si
   se ejecutan: **36 de esos 190 no llegan a ningún camino de ejecución**. Midió existencia
   de archivo y lo reportó como salud del cableado.
4. **"no hay guardas de seguridad huérfanas… los 9 restantes sí están registrados, en
   `cognitive-os.yaml:1157+`"** — la conclusión es cierta pero **por otro motivo**.
   `destructive-rm-blocker`, `destructive-git-blocker`, `direct-main-guard` y
   `conflict-marker-guard` corren porque los llama `bash-hot-path-dispatcher.sh`, **no**
   porque estén en el YAML: el YAML no cablea nada. Con su razonamiento, `rate-limiter.sh`
   —que también está en el YAML— debería estar activo, y tiene **0 disparos**.
5. **"`destructive-rm-blocker.sh` → REAL: fires actively (14 rows in hook-health.jsonl)"** —
   aceptó la etiqueta del auditor sin ver que ese hook tiene **0 filas en `hook-timing.jsonl`**:
   el dispatcher invoca a sus hijos con `bash "$path"` directo, **sin** pasar por
   `hook-timing-wrapper.sh`. Los 29 gates del fan-out son un punto ciego de la telemetría
   principal, y él usó esa telemetría como su "parte sana del auditor".
6. **"`squads` y `agents` son inflación de vocabulario: se nombran como familias y son un
   archivo cada una"** — se quedó corto. No sólo son un archivo: el **único lector de squads
   busca `.md` y el archivo es `.yaml`**, y **nada parsea** el frontmatter `triggers:` del
   agente. No es vocabulario inflado, es código muerto por incompatibilidad de tipo.
7. **"packages/, templates/, workflows/ recibieron conteo, no clasificación"** — honesto, y
   por eso se le escapó que `workflows/` está declarado deprecado por su propio `DEPRECATED.md`
   y tiene **0 referencias externas**: no es una familia con clasificación pendiente, es una
   familia muerta.
8. **No revisó la veracidad documental de ninguna primitiva.** Es la pregunta donde está el
   daño: 19 de 32 primitivas muestreadas prometen algo distinto de lo que hacen.

---

## 6. VERIFICADO / NO VERIFICADO

### VERIFICADO (comando corrido en esta sesión, sobre este checkout)

- Censo de las 7 familias con symlinks resueltos vía `readlink -f`, incluidos los 2 alias
  internos de `hooks/` y los 0 symlinks rotos en `skills/`, `hooks/` y `rules/`.
- Las tres superficies de registro de hooks (190 / 154 / 29 → 181 efectivo) y la salida del
  driver por perfil (core 128, team 133, maintainer 154, lab 154, full 183).
- Que `settings.json` es **byte-equivalente** al `--emit` del driver, y que el driver **no lee**
  `cognitive-os.yaml`.
- Disparos reales: 156 hooks distintos, 101 nunca, ventana 2026-07-20 → 2026-08-15,
  37.424 filas de timing + 14.105 de health.
- Invocaciones de skills: 3 eventos, 2 skills, en toda la historia del archivo.
- `aspirational_audit.py --dry-run --json` corrido hoy, y los defectos de sus líneas 345 y 430.
- Existencia/CLI de `cost_predict.py`, `dogfood_score.py`, `stash_quarantine_audit.py`,
  `scripts/cos-goal` (los tres primeros con `--help` exit 0; `cos-goal status` → `No active goal.`).
- Rutas rotas: `lib/` (6 citas en `RULES-COMPACT`), `hooks/deep-research-axis-gate.sh`,
  `.cognitive-os/workflows/run.py`, 5 de 6 `agentRef` de `squads/organization.yaml`.

### NO VERIFICADO (no lo lea como probado)

1. **No se corrió la suite de tests** (swap al 98%, prohibido por el encargo). Que
   `test_python_naming.py` y `test_bash_naming.py` existan **no prueba que pasen ni que corran en CI**.
2. **No se ejecutó ningún hook.** "181 cableados" es *tiene camino de ejecución*, no *corre sin error*.
3. **Los drivers `bare` y `opencode`**: dicen leer el YAML y no se auditaron. Si alguno sí lo lee,
   los 36 hooks huérfanos podrían estar vivos en **otro** harness — nunca en Claude Code.
4. **Los números del encargo sobre instalación fresca (36) y consumidor (31)** no son
   reproducibles desde este checkout; la coincidencia del 36 queda como hipótesis.
5. **`cos_lib/` (369 módulos) no se auditó** — sólo se probó que el auditor del repo lo ignora.
   Sigue siendo el hueco más grande, igual que hace 18 días.
6. **`packages/` (37) no se clasificó**, sólo se contó y se resolvieron sus symlinks.
7. **La veracidad documental es una muestra dirigida de 32**, elegida para falsar. El 41% de
   acierto es un piso de la muestra, **no** una estimación del universo de ~600 primitivas.
8. **`hook-health.jsonl` como señal de disparo** no se validó contra ejecución real: mide que el
   hook escribió su fila, no que hizo su trabajo.

---

## 7. Las 3 acciones, en orden

**1. Hacer que el registro canónico sea el registro.**
Que `settings-driver-claude-code.sh` lea `cognitive-os.yaml > harness.hooks` en vez de su
lista hardcodeada, o —si la lista hardcodeada es la decisión— borrar `harness.hooks` y el
claim de ADR-064. Hoy hay dos verdades y la documentada es la que no manda.

```bash
# prueba de que quedó hecho: el YAML y la proyección coinciden, y no hay huérfanos
python3 -c "
import json,re,yaml
from pathlib import Path
d=json.load(open('.claude/settings.json'))
cur={p for ev,a in d['hooks'].items() for m in a for h in m['hooks'] for p in re.findall(r'hooks/[\w./-]+\.sh',h['command'])}
disp=set(re.findall(r'hooks/[\w./-]+\.sh',Path('hooks/bash-hot-path-dispatcher.sh').read_text()))
yy={v['script'] for v in yaml.safe_load(open('cognitive-os.yaml'))['harness']['hooks'].values()}
huerfanos=sorted(yy-cur-disp); print(len(huerfanos), huerfanos); assert not huerfanos"
# debe imprimir: 0 []
```

**2. Cerrar la brecha entre lo que las rules prometen y lo que los hooks hacen.**
`blast-radius`, `confidence-gate` y `content-policy` están descritos como *hook-enforced*
y son advisory, post-hoc o dependientes de una fase que no es la vigente. O se cambian los
hooks, o se cambia el texto — pero no pueden convivir. Mismo caso: `rules/rate-limiting.md`
describe como "activo por defecto" un hook con 0 disparos.

```bash
# prueba: ningún hook declarado 'hook-enforced' es advisory ni PostToolUse-sobre-Edit/Write
for h in blast-radius confidence-gate content-policy consequence-evaluator \
         clarification-gate scope-proportionality auto-rollback-trigger; do
  printf '%-26s advisory=%s settings=%s\n' "$h" \
    "$(grep -ci 'advisory only\|does NOT block\|never blocks' hooks/$h.sh)" \
    "$(grep -c "/$h.sh" .claude/settings.json)"
done
# debe dar advisory=0 y settings=1 en cada línea, o la rule debe decir 'advisory'
```

**3. Sacar del inventario lo que no es primitiva.**
`workflows/` (7 `.py`, deprecado por su propio README, 0 referencias), `agents/` (1 archivo
cuyo frontmatter nadie parsea), `squads/` (1 archivo cuyo lector busca otra extensión).
Archivar en `packages/_archived/` o cablearlos, pero dejar de contarlos como familias.

```bash
# prueba: o la familia desapareció, o tiene un consumidor ejecutable real
find squads -name '*.md' | wc -l            # >0 si el lector .md quedó satisfecho
grep -rn "frontmatter\|triggers:" --include='*.py' --include='*.sh' \
  cos_lib hooks scripts | grep -c 'agents/'  # >0 si algo parsea agents/
grep -rln 'backend_feature_pipeline\|backend_bug_pipeline' \
  --include='*.py' --include='*.sh' scripts hooks cos_lib | wc -l   # >0 si workflows revivió
# los tres en 0 y el directorio todavía presente = sigue siendo inventario, no capacidad
```
