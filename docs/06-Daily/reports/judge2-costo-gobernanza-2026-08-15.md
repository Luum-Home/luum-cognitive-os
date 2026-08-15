# Juez 2 — Costo y gobernanza real

**Fecha:** 2026-08-15
**Repo:** `luum-agent-os` — rama `main`, HEAD `8602ddc70` (2026-07-28)
**Lente:** costo por sesión y gobernanza efectiva. Read-only.
**Baseline de no-mutación:** `git status --porcelain` idéntico al inicio y al final (10 entradas, ninguna mía salvo este archivo).

---

## 1. Veredicto

**¿Es un gastadero de tokens?** Sí, y está medido por el propio OS: **$3.005,18 en 38 sesiones**, 374.047 tokens de contexto releídos por turno, ~22 procesos de hook por cada tool call.
**¿No hay gobernanza?** Casi: hay **mecanismo** pero no **gobierno** — de 14 capas declaradas, 9 están registradas, 0 de las 4 capas bloqueantes del mesh bloqueó nunca, y la fase del repo (`reconstruction`) vuelve inalcanzable por construcción el camino de bloqueo de 3 de ellas desde el primer commit.

Matiz que corrige al operador: **sí mide su propio costo**, y bien. El problema no es ceguera, es que nadie mira el número.

---

## 2. Score: 31 / 100

| # | Dimensión | Peso | Nota | Comando que la sostiene |
|---|---|---:|---:|---|
| 1 | Costo fijo de contexto por sesión | 20 | 4/10 | `wc -c ~/.claude/CLAUDE.md ~/.claude/rules/context7.md rules/RULES-COMPACT.md rules/rate-limiting.md` + conteo de catálogo de skills (§4) |
| 2 | Costo por disparo (hooks/tool call) | 20 | 2/10 | agregación de `.cognitive-os/metrics/hook-timing.jsonl` (§3) |
| 3 | Mide su propio costo | 10 | 7/10 | agregación de `.cognitive-os/metrics/cost-events.jsonl` (§3) |
| 4 | Gates declarados que están registrados | 20 | 3/10 | `gate_audit.py` (§6) → 9/14 |
| 5 | Gates que efectivamente bloquean | 20 | 2/10 | distribución de `exit_code` en `hook-timing.jsonl` (§5) |
| 6 | Ausencia de trampa en los gates | 10 | 2/10 | §7 completo |

Ponderado: `(4·20 + 2·20 + 7·10 + 3·20 + 2·20 + 2·10) / 100 · 10 = 31`

---

## 3. A. El costo — medido, no estimado

### 3.1 Costo real registrado por el propio OS

El OS **sí** lleva contabilidad de tokens y dólares, en `cost-events.jsonl`, con `is_estimate: false` y `pricing_known: true`. Esto refuta la sospecha de que no se mide.

```bash
python3 - <<'PY'
import json
rows=[json.loads(L)['payload'] for L in open('.cognitive-os/metrics/cost-events.jsonl')
      if L.strip() and json.loads(L).get('event_type')=='cost.recorded']
tot=sum(p.get('actual_cost_usd',0) or 0 for p in rows)
turns=sum(p.get('turn_count',0) or 0 for p in rows)
cr=sum(p.get('cache_read_input_tokens',0) or 0 for p in rows)
print(f'sesiones={len(rows)} total=${tot:.2f} turnos={turns} $/turno={tot/turns:.3f}')
print(f'cache_read total={cr:,} -> {cr/turns:,.0f} tokens releidos por turno')
PY
```

| Métrica | Valor |
|---|---:|
| Sesiones con costo registrado | 38 |
| **Costo total acumulado** | **$3.005,18** |
| Turnos totales | 4.069 |
| **Costo por turno** | **$0,739** |
| `cache_read_input_tokens` acumulados | 1.521.998.308 |
| **Contexto releído por turno (promedio)** | **374.047 tokens** |
| Share de `cache_read` sobre todo el input | 96,5 % |

Las cinco sesiones más caras:

| session | turnos | USD | cache_read | tok/turno |
|---|---:|---:|---:|---:|
| `0921ef38` | 889 | 834,18 | 422.507.162 | 475.261 |
| `05404980` | 890 | 635,17 | 364.852.198 | 409.946 |
| `418e1384` | 737 | 591,31 | 296.553.415 | 402.379 |
| `3b810eb5` | 727 | 578,00 | 288.567.343 | 396.929 |
| `068fd608` | 423 | 226,03 | 101.031.265 | 238.844 |

**Lectura:** el 96,5 % del input es relectura de caché. Cuatro sesiones superan $575 cada una. Un turno cuesta 74 centavos promedio. La acusación del operador queda confirmada con la telemetría del propio producto.

### 3.2 Costo por disparo — hooks por tool call

```bash
python3 - <<'PY'
import json,collections
rows=[json.loads(L) for L in open('.cognitive-os/metrics/hook-timing.jsonl') if L.strip()]
for ev in ['PreToolUse','PostToolUse','SessionStart','UserPromptSubmit','Stop']:
    g=collections.defaultdict(list)
    for r in rows:
        if r.get('event')==ev: g[r['timestamp']].append(r.get('duration_ms') or 0)
    n=len(g) or 1
    print(f"{ev:18s} hooks/evento={sum(len(v) for v in g.values())/n:5.1f} "
          f"CPU_sum={sum(sum(v) for v in g.values())/n:7.0f}ms wall_max={sum(max(v) for v in g.values())/n:6.0f}ms")
PY
```

| Evento | Hooks por disparo | CPU sumado | Wall (máx paralelo) |
|---|---:|---:|---:|
| PreToolUse | 8,1 | 5.642 ms | 1.764 ms |
| PostToolUse | 13,0 | 7.317 ms | 1.374 ms |
| SessionStart | 26,9 | — | — |
| UserPromptSubmit | 11,8 | — | — |
| Stop | 22,9 | — | 25.015 ms (media) |

**~21 procesos de hook por cada ida y vuelta de tool call**, ~13 s de CPU sumada, **~3,1 s de pared como piso**. `Stop` promedia **25 segundos**.

Rango de los datos: 2026-07-20 → 2026-08-15, 30.515 invocaciones. `.claude/settings.json` registra **162 entradas de hook** en 10 eventos.

### 3.3 Amplificadores

El peor está medido por el propio OS:

```bash
python3 - <<'PY'
import json,collections
tok=collections.Counter(); n=collections.Counter()
for L in open('.cognitive-os/metrics/context-budget.jsonl'):
    if not L.strip(): continue
    r=json.loads(L); s=r.get('source','?')
    tok[s]+=r.get('tokens_estimate',0) or 0; n[s]+=1
for s,v in tok.most_common(): print(f'{s:34s} n={n[s]:4d} tot={v:>9,d} media={v/n[s]:.0f}')
PY
```

| Fuente | n | Tokens totales | Media |
|---|---:|---:|---:|
| `subagent-context-injector` | 659 | 1.470.239 | **2.231** |
| `context-budget-meter` | 520 | 156.322 | 301 |
| `inject-phase-context` | 336 | 70.071 | 209 |
| `adr-relevance-suggest` | 192 | 13.425 | 70 |
| `rule-router-prompt-suggest` | 135 | 6.474 | 48 |
| `skill-router-prompt-suggest` | 106 | 3.598 | 34 |

Cada lanzamiento de sub-agente arrastra **2.231 tokens** de contexto inyectado. Y el medidor es parcial: mide 6 fuentes, pero **26 hooks emiten `additionalContext`**.

```bash
grep -rl "additionalContext" hooks/*.sh | wc -l   # -> 26
```

O sea: el propio medidor de contexto cubre el **23 %** de los inyectores. Los otros 20 inyectan sin quedar registrados.

Amplificador estructural extra: `hooks/quality-duplicates.sh` promedia **565.803 ms (9,4 min)** por ejecución, 29 ejecuciones, 16.408.300 ms acumulados — el 92 % de todo el tiempo de `Stop`.

---

## 4. Tabla de costo fijo por sesión

**Método declarado: `bytes / 4` como estimador de tokens.** Es una aproximación gruesa (el ratio real para prosa técnica en inglés ronda 3,5–4,5 bytes/token); los números de esta tabla son **estimados**, a diferencia de los de §3.1 que son medidos.

```bash
wc -c ~/.claude/CLAUDE.md ~/.claude/rules/context7.md \
      rules/RULES-COMPACT.md rules/rate-limiting.md AGENTS.md
python3 -c "
import os,re
tot=0
for d in sorted(os.listdir('.claude/skills')):
    p=f'.claude/skills/{d}/SKILL.md'
    if not os.path.exists(p): continue
    m=re.search(r'^---\n(.*?)\n---', open(p,errors='replace').read(), re.S)
    desc=re.search(r'^description:\s*(.*)$', m.group(1), re.M) if m else None
    tot+=len(d)+len(desc.group(1).strip() if desc else '')+4
print('catalogo skills bytes:',tot)"
```

| Fuente | Bytes | Tokens est. (÷4) | ¿Siempre? |
|---|---:|---:|---|
| `~/.claude/CLAUDE.md` (global) | 22.020 | 5.505 | Sí |
| `rules/RULES-COMPACT.md` | 11.539 | 2.885 | Sí |
| `rules/rate-limiting.md` | 3.854 | 964 | Sí (inyectada por `contextual-rule-loader`) |
| `~/.claude/rules/context7.md` | 1.679 | 420 | Sí |
| Catálogo de skills (192 `SKILL.md`) | 19.905 | 4.976 | Sí |
| **Subtotal impuesto fijo** | **58.997** | **~14.749** | |
| `AGENTS.md` | 11.216 | 2.804 | Solo otros harnesses |
| Salida de 27 hooks `SessionStart` | — | **no medido** | Sí |

**~14,7 K tokens antes de que el agente lea una sola línea de código.** Y esa base se relee cada turno: §3.1 muestra 374 K tokens de `cache_read` por turno, o sea que el impuesto fijo es el piso, no el techo.

Verificación cruzada de que estas fuentes están efectivamente cargadas: `rules/RULES-COMPACT.md` y `rules/rate-limiting.md` aparecen literalmente en el system prompt de esta sesión de juez.

---

## 5. B. ¿Gobierna algo?

### 5.1 Bloqueos reales en 30.515 invocaciones

```bash
python3 -c "
import json,collections
c=collections.Counter(); h=collections.Counter()
for L in open('.cognitive-os/metrics/hook-timing.jsonl'):
    if not L.strip(): continue
    r=json.loads(L); ec=r.get('exit_code'); c[ec]+=1
    if ec not in (0,None): h[(r.get('hook'),ec)]+=1
print(dict(c)); [print(k,v) for k,v in h.most_common()]"
```

| exit_code | n | % |
|---|---:|---:|
| 0 | 30.462 | 99,83 % |
| **2 (BLOQUEA)** | **29** | **0,095 %** |
| 1 | 20 | 0,066 % |
| 141 (SIGPIPE) | 4 | 0,013 % |

Los 29 bloqueos, por hook:

| Hook | Bloqueos | ¿Es del mesh de 14 capas? |
|---|---:|---|
| `subagent-budget-enforcer` | 16 | No |
| `bash-hot-path-dispatcher` | 5 | No |
| `lethal-trifecta-gate` | 4 | No |
| `protected-config-write-guard` | 2 | No |
| `confidentiality-enforcer` | 2 | No |

**Ninguno de los 29 bloqueos vino del mesh de seguridad declarado.** Las cuatro capas bloqueantes registradas (`clarification-gate`, `scope-proportionality`, `claim-validator`, `confidence-gate`) dispararon 19 veces cada una y **bloquearon cero veces**.

### 5.2 Por qué no bloquean: la fase

```bash
grep -n "phase:" cognitive-os.yaml | head -1
# 9:  phase: reconstruction
git log -1 --format='%h %ad' --date=short -S'phase: reconstruction' -- cognitive-os.yaml
# db4100405 2026-03-27
grep -n "production\|maintenance" hooks/claim-validator.sh | head -4
```

`claim-validator.sh:141` y `:197`, `confidence-gate.sh:91`, `scope-proportionality.sh:79` — los tres condicionan `exit 2` a `PHASE == production || maintenance`. La fase es `reconstruction` **desde el commit inicial del repo (2026-03-27)** y nunca cambió.

**Tres de las cuatro capas bloqueantes registradas son inalcanzables por construcción, y lo fueron durante toda la historia del repo.** No es que no hayan tenido oportunidad de disparar: el camino de bloqueo no existe en esta configuración.

### 5.3 Evidencia de que algo sí bloquea (probado en vivo, sin tocar el repo)

Durante esta auditoría, `protected-config-write-guard` **bloqueó una de mis propias llamadas Bash read-only**:

```
=== PROTECTED CONFIG WRITE GUARD: BLOCKED ===
Protected control-plane path(s): hooks/event
```

La causa: mi script Python contenía la cadena literal `hooks/event` dentro de un `f-string` de impresión. El guard hace **match por subcadena sobre el texto del comando**, sin distinguir escritura de lectura ni ruta real de literal. Dos de los 29 bloqueos históricos son de este hook.

Conclusión doble: (a) el mecanismo de bloqueo **funciona** cuando se registra sin condicionar por fase; (b) su criterio de detección es sintáctico y produce falsos positivos sobre trabajo read-only.

---

## 6. La tabla de gates

Script reproducible: `gate_audit.py` (fuente completa en §11). Corrida:

```bash
python3 gate_audit.py .   # exit 1 = hallazgos
```

Las 14 capas son las declaradas en `docs/04-Concepts/root/safety-mesh.md:14`.
La quinta columna **"llega al consumidor"** responde a la ampliación del encargo (§9) y se marca `?` donde no puedo verificarlo desde el origen sin correr el instalador — cosa que tengo prohibida.

| # | Hook | Declarado | Registrado | Disparó | Bloquea (`exit 2` en fuente) | Llega al consumidor |
|---|---|---|---|---:|---|---|
| 1 | `clarification-gate.sh` | 2 BLOCK | sí | 19 | sí, alcanzable | ? |
| 2 | `blast-radius.sh` | 0 WARN | sí | 19 | no | ? |
| 3 | `dry-run-preview.sh` | 2 BLOCK | **NO** | **0** | sí (código muerto) | no aplica |
| 4 | `rate-limiter.sh` | 2 BLOCK | **NO** | **0** | sí (código muerto) | no aplica |
| 5 | `scope-proportionality.sh` | 2 BLOCK | sí | 19 | sí, **inalcanzable** (fase) | ? |
| 6 | `claim-validator.sh` | 2 BLOCK | sí | 19 | sí, **inalcanzable** (fase) | ? |
| 7 | `assumption-tracker.sh` | 0 WARN | sí | 19 | no | ? |
| 8 | `trust-score-validator.sh` | 0 LOG | sí | 19 | sí (contradice el doc) | ? |
| 9 | `confidence-gate.sh` | 2 BLOCK | sí | 19 | sí, **inalcanzable** (fase) | ? |
| 10 | `clarification-interceptor.sh` | 0 LOG | **NO** | **0** | no | no aplica |
| 11 | `auto-rollback-trigger.sh` | 2 BLOCK | sí | 19 | **no hay `exit 2`** | ? |
| 12 | `lib/cross_verifier.py` | library | ruta **inexistente** | — | — | ? |
| 13 | `reinvention-check.sh` | 0 WARN | sí | 19 | no | ? |
| 14 | `lib/memory_scanner.py` | library | ruta **inexistente** | — | — | ? |

Comandos de cada columna:

```bash
# registrado
grep -c 'hooks/rate-limiter.sh' .claude/settings.json          # -> 0
grep -c 'dry-run-preview' .claude/settings.json                # -> 0
grep -c 'clarification-interceptor' .claude/settings.json      # -> 0
grep -o 'hooks/rate-limit[a-z-]*\.sh' .claude/settings.json | sort -u
#   -> solo rate-limit-detector.sh y rate-limit-drain.sh

# disparo
python3 -c "import json;print(sum(1 for L in open('.cognitive-os/metrics/hook-timing.jsonl') if L.strip() and json.loads(L).get('hook')=='rate-limiter'))"   # -> 0

# bloquea
grep -n '^\s*exit 2' hooks/auto-rollback-trigger.sh            # -> sin salida

# rutas de las capas library
ls lib/cross_verifier.py lib/memory_scanner.py                 # -> No such file or directory
ls cos_lib/cross_verifier.py cos_lib/memory_scanner.py         # -> existen
```

### 6.1 La proporción dura

> ## **14 declarados / 9 registrados / 9 disparados / 0 que bloquearon**

Los cuatro comandos:

| Número | Comando |
|---|---|
| **14 declarados** | `sed -n '18,33p' docs/04-Concepts/root/safety-mesh.md \| grep -c '^\|'` — tabla de capas |
| **9 registrados** | `python3 gate_audit.py .` → columna `reg` |
| **9 disparados** | `python3 gate_audit.py .` → columna `fired` (19 disparos cada uno) |
| **0 bloquearon** | agregación de `exit_code` en `hook-timing.jsonl` (§5.1): los 29 `exit 2` pertenecen a 5 hooks, ninguno del mesh |

Si se cuenta "bloquea" como *capacidad estructural en la fase actual del repo*, el número sigue siendo bajo: **1 de 14** (`clarification-gate`, la única bloqueante registrada sin condicional de fase) — y esa nunca superó su umbral.

### 6.2 Falsación del claim de `README.md:26`

> "a 14-layer safety mesh (12 fire as PreTool/PostTool hooks, 2 are library/conditional)"

**Falso en las dos mitades:**

1. **"12 fire as PreTool/PostTool hooks"** → 9 están registradas. `dry-run-preview.sh`, `rate-limiter.sh` y `clarification-interceptor.sh` no aparecen en `.claude/settings.json` ni una vez.
2. **"2 are library/conditional"** → apuntan a `lib/cross_verifier.py` y `lib/memory_scanner.py`. **El directorio `lib/` no existe** (`ls -ld lib` → *No such file or directory*). El paquete es `cos_lib/`.

Contradicciones internas adicionales:

```bash
grep -n "12-layer\|0 of 12" docs/09-Quality/root/hook-security-profiles.md
# 27: **Safety mesh layers**: 0 of 12 (no safety mesh hooks registered)
# 135: Activates the complete 12-layer safety mesh ...
```

Un doc dice 14, otro dice 12. Y `README.md:35` atribuye `auto-rollback-trigger.sh` a "Layers 2 + 11" mientras la tabla canónica lo pone en la capa 11 y `blast-radius` en la 2 — la cita del README mezcla dos capas en una frase.

---

## 7. Gates sin trampa — hallazgos

Aplicando el criterio: *un supresor que no suprime nada es un bug*.

### 7.1 Auditor con 0 hallazgos que no audita lo que falla

```bash
python3 scripts/cos_install_projection_audit.py; echo "EXIT=$?"
# {"findings": 0, "runs": 12, ...}  EXIT=0
grep -c "importlib\|py_compile\|ModuleNotFound" scripts/cos_install_projection_audit.py
# -> 0
```

12 combinaciones de instalación auditadas, 0 hallazgos, exit 0. Pero el auditor **solo verifica que los archivos de hook referenciados en `settings.json` existan tras instalar** — no valida satisfacibilidad de imports de Python. Es un verde que no cubre la clase de falla que el insumo de §9 reporta. Verde legítimo en su alcance, engañoso como señal de "la instalación proyecta bien".

### 7.2 Streams de métricas que nunca registraron nada

```bash
find .cognitive-os/metrics -maxdepth 1 -name "*.jsonl" -size 0 | wc -l   # -> 16
find .cognitive-os/metrics -maxdepth 1 -name "*.jsonl" | wc -l           # -> 114
```

**16 de 114** streams están en 0 bytes. Entre ellos, gates con nombre de gobernanza:

| Stream vacío | Antigüedad |
|---|---|
| `governance-catches.jsonl` | desde 2026-06-17 |
| `hallucinations.jsonl` | desde 2026-06-17 |
| `decision-depth-gate.jsonl` | desde 2026-05-23 |
| `adversarial-review-gate.jsonl` | desde 2026-05-23 |
| `plan-claim-validator.jsonl` | desde 2026-05-27 |
| `auto-verify.jsonl` | desde 2026-06-17 |
| `repair-dispatch.jsonl` | desde 2026-06-17 |
| `push-collision-detect.jsonl` | desde 2026-07-19 |

Reglas instaladas que en 2–3 meses **nunca se vieron disparar**. Dan sensación de cobertura sin producir evidencia.

### 7.3 Degradación silenciosa masiva

```bash
python3 - <<'PY'
import ast,os
skip={'.venv','__pycache__','.git','node_modules','.pytest_cache','.ruff_cache'}
n=0; own=0
for root,dirs,files in os.walk('.'):
    dirs[:]=[d for d in dirs if d not in skip]
    for f in files:
        if not f.endswith('.py'): continue
        try: tree=ast.parse(open(os.path.join(root,f),errors='replace').read())
        except Exception: continue
        for node in ast.walk(tree):
            if not isinstance(node,ast.Try): continue
            if not any(isinstance(x,(ast.Import,ast.ImportFrom)) for x in node.body): continue
            if any(all(isinstance(s,ast.Pass) for s in h.body) for h in node.handlers):
                n+=1
                for x in node.body:
                    mods=[x.module or ''] if isinstance(x,ast.ImportFrom) else [a.name for a in getattr(x,'names',[])]
                    if any(m.startswith('cos_lib') for m in mods): own+=1
print('try/except: pass alrededor de imports:',n,'| de los cuales sobre cos_lib.*:',own)
PY
# -> 439 | de los cuales sobre cos_lib.*: 25
```

**439** bloques `try/except: pass` alrededor de imports. **25** de ellos silencian imports de módulos **propios del OS**, incluyendo primitivas de gobernanza: `rate_limit_tracker` (×2), `model_router`, `work_queue`, `engram_client`, `safe_engram`, `memory_retriever` (×2), `prompt_cache` (×2), `estimation_calibrator` (×2).

Si cualquiera de esos módulos falta o falla al importar, **la primitiva se apaga sin ruido y el gate sigue reportando verde**.

### 7.4 Podredumbre de rutas en documentación

```bash
python3 - <<'PY'
import re,os,glob
refs=set()
for pat in ['rules/**/*.md','docs/**/*.md','README.md','AGENTS.md']:
    for p in glob.glob(pat,recursive=True):
        refs.update(re.findall(r'\blib/[a-z0-9_]+\.py', open(p,errors='replace').read()))
miss=[r for r in refs if not os.path.exists(r)]
print('refs distintas lib/*.py:',len(refs),'| resuelven:',len(refs)-len(miss),
      '| existen bajo cos_lib/:',sum(1 for r in miss if os.path.exists('cos_'+r)))
PY
# -> refs distintas lib/*.py: 433 | resuelven: 0 | existen bajo cos_lib/: 369
```

**433 referencias distintas a `lib/*.py` en docs y reglas. Cero resuelven.** 369 existen bajo `cos_lib/`; **64 no existen en ninguna parte**.

Esto incluye `rules/RULES-COMPACT.md` —cargada en **todo** prompt— que cita `lib/rate_limiter.py`, `lib/cost_predictor.py`, `lib/dispatch.py`, `lib/decision_tracker.py`, `lib/harness_adapter/`. El agente recibe ~14,7 K tokens de instrucciones cuyas rutas no existen.

### 7.5 Contradicción entre regla cargada y realidad

`rules/rate-limiting.md` — inyectada en el contexto de esta sesión — afirma en tres lugares:

- línea 9: *"The rate limiter is active by default for Bash, Agent, Edit, and Write tool activity through `hooks/rate-limiter.sh`."*
- línea 88: *"**Hook**: `hooks/rate-limiter.sh` (PreToolUse on Bash, Agent, Edit, Write)"*

```bash
grep -c 'hooks/rate-limiter.sh' .claude/settings.json   # -> 0
```

**El hook no está registrado.** La tabla de límites, el bucket de tokens, la reserva del operador y la penalización por diversidad son doctrina que se paga en contexto cada turno y no gobierna nada. Lo registrado es `rate-limit-detector.sh` y `rate-limit-drain.sh`, que son otra cosa.

### 7.6 Supresiones

```bash
grep -rc "# noqa" --include="*.py" cos_lib/ scripts/ | awk -F: '{s+=$2} END{print s}'      # -> 187
grep -rc "type: ignore" --include="*.py" cos_lib/ scripts/ | awk -F: '{s+=$2} END{print s}' # -> 143
grep -rc "nosemgrep" --include="*.py" cos_lib/ scripts/ | awk -F: '{s+=$2} END{print s}'    # -> 0
```

187 `# noqa` y 143 `type: ignore`. **No los clasifico como trampa**: no comparé contra un baseline ni verifiqué si son acotados y motivados, y sin eso son un número sin veredicto. Queda como NO VERIFICADO (§10). `nosemgrep` en 0 es limpio.

---

## 8. Correcciones a las premisas del encargo

| Premisa del encargo | Veredicto | Evidencia |
|---|---|---|
| *"si hay métricas de costo, usalas; si no las hay, ese es el hallazgo"* | **Las hay, y son buenas.** El hallazgo se invierte | `cost-events.jsonl`: 38 sesiones, `is_estimate:false`, $3.005,18. El OS mide bien y nadie mira |
| *"buscá `hook-health.jsonl` o equivalente"* | Existe, pero el útil es otro | `hook-health.jsonl` (11.731 líneas) solo tiene `hook/exit_code/duration_ms`. `hook-timing.jsonl` (30.515 líneas) trae `event`, `skipped`, `session_kind` — es el que sirve |
| *"`README.md:26` afirma 14-layer / 12 hooks"* | **Confirmado como claim, falsado como dato** | §6.2 |
| *"config en `.claude/settings.json` y `cognitive-os.yaml`"* | Correcto, pero falta una | `.claude/settings.local.json` (27.702 B) también existe y no fue parte de mi alcance |
| *"no hay gobernanza"* | **Parcialmente falso** | Hay 29 bloqueos reales, de 5 hooks fuera del mesh declarado. El mecanismo existe; el mesh publicitado es el que no gobierna |
| *"es un gastadero de tokens"* | **Confirmado** | §3.1 |
| Fecha del panel previo (2026-07-28) vs HEAD | Coinciden | HEAD `8602ddc70` es del 2026-07-28. Los 6 informes previos son contemporáneos del HEAD; no re-corrí ninguno de sus comandos ni cito sus números |

---

## 9. Insumo de terceros — auditoría de `FinOpenPOS` (no verificado en origen)

> Diagnóstico recibido de otra sesión sobre un repo **consumidor**. **No lo trato como hecho.** Verifiqué lo que se puede verificar desde este origen; el resto queda abierto. **No corrí el instalador** (asignado al juez de funcionamiento).

| # | Afirmación de terceros | Qué verifiqué en el origen | Resultado |
|---|---|---|---|
| 1 | `confidentiality.yaml` existe pero está sin trackear | `find` + `git ls-files --error-unmatch` + `git check-ignore -v` | **SOSTIENE EL HECHO, CORRIGE LA CAUSA.** Ver §9.1 |
| 1b | 18/18 instalaciones ciegas en 3 de 4 categorías del scanner | — | **NO VERIFICADO.** Requiere correr el instalador |
| 2 | ~8 módulos descartados, referencias en `try/except: pass` | Escaneo AST repo-wide | **SOSTIENE EL PATRÓN, NO EL NÚMERO.** 439 `try/except: pass` sobre imports; 25 sobre módulos propios `cos_lib.*`. Qué módulos concretos descarta el instalador: no verificado |
| 2b | `circuit_breaker.py` se instala pero `record_completion` no; el `except` se traga el bloque | Lectura de `cos_lib/auto_repair.py:549-552` | **MECANISMO PLAUSIBLE, CADENA NO REPRODUCIDA.** `cos_lib/circuit_breaker.py` y `cos_lib/record_completion.py` existen ambos acá. El import de `CircuitBreaker` está en un lazy-load dentro de `_get_circuit_breaker()`. Que en el consumidor falte `record_completion` no lo puedo confirmar desde el origen |
| 3 | `_lib/cos-root` falta en 16/16 instalaciones | Lectura de `scripts/hook-timing-wrapper.sh` | **PREMISA ESTRUCTURAL CONFIRMADA.** `scripts/hook-timing-wrapper.sh:65` invoca `"$SCRIPT_DIR/cos-root"` — hermano en `scripts/`. `scripts/cos-root` existe. Que el instalador reubique el wrapper sin la dependencia: **no verificado** |
| — | Raíz común: el instalador envía un subconjunto y nunca valida sus propios imports | `grep -c "importlib\|py_compile\|ModuleNotFound" scripts/cos_install_projection_audit.py` → **0** | **SOSTIENE.** El único auditor de proyección de instalación **no valida imports**. Reporta `findings: 0` sobre 12 combinaciones y sale 0. Es exactamente el supresor que no suprime nada de §7.1 |

**Impacto sobre mi lente.** Si los puntos 1 y 3 se confirman del lado consumidor, la quinta columna de §6 se vuelve la columna que manda: gates registrados y disparando **acá adentro** que nunca llegaron afuera. Con `_lib/cos-root` faltante, `hook-timing-wrapper.sh` no resuelve `PROJECT_DIR` — y ese wrapper envuelve **las 162 entradas de hook** de `settings.json`. Es decir: **si el punto 3 se confirma, ningún hook del OS corrió jamás en ningún consumidor**, y toda la tabla de §6 describe gobernanza que existe solo en el repo de origen.

No puedo cerrar eso desde acá. Es la pregunta más cara del informe y le corresponde al juez de funcionamiento.

### 9.1 Corrección a mi propio hallazgo sobre `confidentiality.yaml`

Mi primera lectura fue "falta un `git add`". **Es incorrecta.** El archivo no está sin trackear por olvido: está **ignorado por diseño**.

```bash
git check-ignore -v .cognitive-os/templates/confidentiality.yaml
# .gitignore:8:.cognitive-os/*	.cognitive-os/templates/confidentiality.yaml
```

Todo `.cognitive-os/*` está en `.gitignore:8`. O sea que la plantilla vive en el **estado de runtime** del origen, no en el material versionado que se distribuye. El defecto no es de higiene de git: es que **el scanner de confidencialidad depende de config que vive en un directorio que, por contrato, no viaja**. Agregarla al índice sería pelear contra el `.gitignore`; la corrección correcta es moverla a material versionado (`templates/` del repo) o que el instalador la genere.

Esto **cambia mi recomendación** y confirma el matiz que planteó el coordinador. El síntoma que reportan (18/18 instalaciones ciegas en 3 de 4 categorías) queda igual de vivo; la causa raíz es otra.

### 9.2 Registraciones fantasma — verificado en el origen, y da limpio

El encargo pedía dos números con dos comandos. Acá están, sobre este origen.

**Número 1 — registraciones que no resuelven a un archivo real:**

```bash
python3 - <<'PY'
import json,os,re
d=json.load(open('.claude/settings.json'))
paths=[]
for ev,ms in d.get('hooks',{}).items():
    for m in ms:
        for h in m.get('hooks',[]):
            paths += [(ev,p) for p in re.findall(r'\$CLAUDE_PROJECT_DIR/([A-Za-z0-9._/-]+)', h.get('command',''))]
miss=[(ev,p) for ev,p in paths if not os.path.exists(os.path.realpath(p))]
print(f'referencias de path: {len(paths)} | resuelven: {len(paths)-len(miss)} | NO RESUELVEN: {len(miss)}')
PY
# -> referencias de path: 324 | resuelven: 324 | NO RESUELVEN: 0
```

**Número 2 — registraciones duplicadas:**

```bash
python3 - <<'PY'
import json,collections,re
d=json.load(open('.claude/settings.json'))
trip=collections.Counter(); byev=collections.defaultdict(collections.Counter)
for ev,ms in d.get('hooks',{}).items():
    for m in ms:
        for h in m.get('hooks',[]):
            trip[(ev,m.get('matcher',''),h.get('command',''))]+=1
            for f in re.findall(r'hooks/([A-Za-z0-9._-]+\.sh)', h.get('command','')):
                byev[ev][f]+=1
print('triples (evento,matcher,comando) duplicados:', sum(v-1 for v in trip.values() if v>1))
print('mismo hook >1 vez en el mismo evento:',
      {ev:{k:v for k,v in c.items() if v>1} for ev,c in byev.items() if any(v>1 for v in c.values())})
PY
# -> triples duplicados: 0
# -> {'PreToolUse': {'cross-session-event-emit.sh': 2, 'control-plane-audit.sh': 2},
#     'PostToolUse': {'audit-id-enricher.sh': 2, 'work-queue-sync.sh': 2}}
```

| Métrica en el origen | Valor |
|---|---:|
| Entradas de hook registradas | 162 |
| Referencias de path extraídas | 324 |
| **Resuelven con `realpath`** | **324 (100 %)** |
| **Fantasmas (no resuelven)** | **0** |
| **Triples `(evento, matcher, comando)` duplicados** | **0** |
| Mismo hook bajo >1 matcher del mismo evento | 4 (legítimo: matchers distintos) |

**El origen está limpio.** Cero fantasmas, cero duplicados exactos. Los 4 casos de hook repetido dentro de un evento son registros bajo matchers distintos —`cross-session-event-emit`, `control-plane-audit`, `audit-id-enricher`, `work-queue-sync`— que es la forma correcta de cubrir dos conjuntos de herramientas, no acumulación entre upgrades.

**Y ese es exactamente el hallazgo.** El contraste que pedía el coordinador:

| | Origen (verificado por mí) | Consumidor (reportado, no verificado) |
|---|---:|---:|
| Registraciones | 162 | 98 donde debería haber 47 |
| Que no resuelven | **0** | **162 tras correr `apply-efficiency-profile.sh`** |

Si el reporte del consumidor se confirma, entonces **`registrado` significa cosas distintas de cada lado**: acá es una promesa cumplida, allá es una intención. Mi tabla de §6 mide el origen y sólo el origen — la columna "registrado" **no transfiere**, y la quinta columna deja de ser un detalle para volverse la única que importa. El mecanismo propuesto (un script `os-only` que emite layout de origen sobre un layout instalado) es coherente con lo que veo acá: `hook-timing-wrapper.sh:65` resuelve `cos-root` como hermano en `scripts/`, un supuesto que sólo vale en este layout.

No verifiqué `scripts/apply-efficiency-profile.sh` ni los conteos 47/98/162: son del lado consumidor y no corro el instalador.

### 9.3 Script recomputable de terceros (no corrido por mí)

Los tres hallazgos de §9 son recomputables con:

```bash
bash ~/Projects/luum/FinOpenPOS/scripts/check-cos-install-integrity.sh [ORIGIN] [PROJECTS_ROOT]
```

Read-only, exit 0/1. **No lo corrí** — está asignado al juez de funcionamiento. Cualquier cifra del lado consumidor que aparezca en este informe sale de ahí, no de mí.

### 9.4 Límites declarados del insumo prestado

- **Circuit breaker:** el script de terceros prueba la **condición** (módulo presente, hermano ausente, mismo `try`), **no** que la llamada nunca se ejecute. Falsarlo requiere exhibir un camino donde el breaker se alcance igual. Si alguien se apoya en ese hallazgo, tiene que citarlo con este límite. No lo perseguí.
- **Contaminación:** `FinOpenPOS` **no sirve como control** — sus agentes repararon imports la noche previa. Todo conteo que la incluya está sesgado **a favor** del OS.
- **`apply-efficiency-profile.sh`:** los números 47 / 98 / 162 son de una copia sandbox de terceros. No reproducidos acá.

---

## 10. VERIFICADO vs NO VERIFICADO

### VERIFICADO (comando corrido en esta sesión, sobre este checkout)

- $3.005,18 en 38 sesiones, 4.069 turnos, $0,739/turno, 374.047 tokens de `cache_read` por turno — `cost-events.jsonl`
- 96,5 % del input es relectura de caché
- 162 entradas de hook en `.claude/settings.json`, 10 eventos
- 8,1 hooks por PreToolUse / 13,0 por PostToolUse / 26,9 por SessionStart / 22,9 por Stop
- 5.642 ms + 7.317 ms de CPU sumada por tool call; 3.138 ms de pared como piso
- 29 `exit 2` en 30.515 invocaciones (0,095 %), de 5 hooks, **ninguno del mesh de 14 capas**
- `phase: reconstruction` desde el commit inicial (`db4100405`, 2026-03-27), nunca modificada
- `claim-validator`, `confidence-gate`, `scope-proportionality` condicionan `exit 2` a `production||maintenance`
- `rate-limiter.sh`, `dry-run-preview.sh`, `clarification-interceptor.sh`: 0 apariciones en `settings.json`, 0 disparos
- `auto-rollback-trigger.sh` declarado BLOCK, sin `exit 2` en su fuente
- `lib/` no existe; `cos_lib/` es el paquete real
- 433 refs `lib/*.py` en docs+reglas, 0 resuelven, 64 no existen en ningún lado
- 439 `try/except: pass` sobre imports; 25 sobre `cos_lib.*`
- 16 de 114 streams de métricas en 0 bytes
- 26 hooks emiten `additionalContext`; el medidor `context-budget` cubre 6
- `subagent-context-injector`: 2.231 tokens de media × 659 lanzamientos
- `quality-duplicates.sh`: 565.803 ms de media, 92 % del tiempo de `Stop`
- `.cognitive-os/templates/confidentiality.yaml` es **untracked por `.gitignore:8` (`.cognitive-os/*`)**, o sea ignorado por diseño, no por olvido
- **162 entradas de hook registradas, 324 referencias de path, 324 resuelven con `realpath`, 0 fantasmas, 0 triples duplicados** — el origen está limpio
- `cos_install_projection_audit.py`: 0 findings, exit 0, y **0** referencias a validación de imports
- `protected-config-write-guard` bloquea de verdad y con falso positivo (probado en vivo, sin mutar el repo)
- Impuesto fijo de contexto: 58.997 bytes → **~14.749 tokens estimados** (método `bytes/4`, declarado como estimación)
- No-mutación: `git status --porcelain` idéntico antes y después

### NO VERIFICADO

- **Todo el comportamiento del lado consumidor** (§9): no corrí el instalador ni `check-cos-install-integrity.sh`, por instrucción
- `scripts/apply-efficiency-profile.sh` y los conteos 47 / 98 / 162 de registraciones fantasma en consumidores — reportados por terceros, no reproducidos
- Que la cadena `circuit_breaker` → `record_completion` sea inalcanzable en un consumidor: el script de terceros prueba la condición, no la inalcanzabilidad
- Si `dry-run-preview`, `rate-limiter` y `clarification-interceptor` están registrados en `.claude/settings.local.json` (27.702 B) — **no lo revisé**, mi alcance fue `settings.json`
- Si los 187 `# noqa` y 143 `type: ignore` son deuda acotada y motivada o supresión de conveniencia — hace falta comparar contra baseline
- Tokens reales de los 27 hooks `SessionStart` (los 20 inyectores fuera del medidor)
- Si el ratio `bytes/4` es correcto para este corpus — es estimación declarada, no medición
- Si `quality-duplicates.sh` a 9,4 min es un bug o trabajo legítimo
- **Ningún número de los 6 informes del panel del 2026-07-28** — no re-corrí sus comandos y no cito sus cifras
- Si los 19 disparos por capa del mesh son bajos por diseño (matcher `Agent`) o por defecto de registro

---

## 11. Las 3 acciones

### 1 — Registrar `rate-limiter.sh` o borrar `rules/rate-limiting.md`

La regla se paga en contexto **cada turno** (964 tokens estimados) y describe un hook que no corre. Cualquiera de las dos salidas sirve; mantener las dos cosas como están es lo único que no.

**Prueba de que quedó hecho:**
```bash
# opción A (registrar): ambos deben dar > 0
grep -c 'hooks/rate-limiter.sh' .claude/settings.json
python3 -c "import json;print(sum(1 for L in open('.cognitive-os/metrics/hook-timing.jsonl') if L.strip() and json.loads(L).get('hook')=='rate-limiter'))"

# opción B (borrar la doctrina): debe dar 0
git ls-files rules/rate-limiting.md | wc -l
```

### 2 — Decidir la fase, o sacar el condicional de fase de las capas bloqueantes

Tres de las cuatro capas bloqueantes registradas son inalcanzables desde 2026-03-27. Mientras `phase: reconstruction`, el mesh es un logger caro. Es una decisión del operador, no un bug: o el repo pasa a `stabilization`/`production`, o el README deja de venderlo como capa que bloquea.

**Prueba:**
```bash
# el gate deja de estar condicionado por fase, o la fase cambia
grep -n "phase:" cognitive-os.yaml | head -1
# y despues de la proxima sesion, tiene que aparecer al menos un exit 2 del mesh:
python3 -c "
import json,collections
mesh={'claim-validator','confidence-gate','scope-proportionality','clarification-gate'}
c=collections.Counter()
for L in open('.cognitive-os/metrics/hook-timing.jsonl'):
    if not L.strip(): continue
    r=json.loads(L)
    if r.get('hook') in mesh and r.get('exit_code')==2: c[r['hook']]+=1
print(dict(c))"   # hoy: {} — tiene que dejar de estar vacio
```

### 3 — Reescribir las 433 rutas `lib/` → `cos_lib/`, empezando por `RULES-COMPACT.md`

Es el arreglo más barato por token ahorrado: `RULES-COMPACT.md` entra en **todos** los prompts y manda al agente a rutas inexistentes. Los 64 refs que no existen en ninguna parte son, además, capacidades declaradas sin implementación — incluidas las capas 12 y 14 del mesh.

**Prueba:**
```bash
python3 -c "
import re,os,glob
refs=set()
for pat in ['rules/**/*.md','docs/**/*.md','README.md','AGENTS.md']:
    for p in glob.glob(pat,recursive=True):
        refs.update(re.findall(r'\blib/[a-z0-9_]+\.py', open(p,errors='replace').read()))
bad=[r for r in refs if not os.path.exists(r)]
print('rotas:',len(bad)); raise SystemExit(1 if bad else 0)"
# hoy: 433 (exit 1). Objetivo: 0 (exit 0)
```

---

## 12. Anexo — `gate_audit.py`

Script read-only, determinista, exit 0 sin hallazgos / 1 con hallazgos / 2 error. Incluye chequeo de no-mutación. Vive en el scratchpad de esta sesión; se transcribe acá para que sobreviva al reinicio.

```python
#!/usr/bin/env python3
"""Read-only audit: declared / registered / fired / blocks, for the 14-layer safety mesh."""
import json, os, re, subprocess, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

LAYERS = [
    (1, "clarification-gate.sh", "2 BLOCK"), (2, "blast-radius.sh", "0 WARN"),
    (3, "dry-run-preview.sh", "2 BLOCK"), (4, "rate-limiter.sh", "2 BLOCK"),
    (5, "scope-proportionality.sh", "2 BLOCK"), (6, "claim-validator.sh", "2 BLOCK"),
    (7, "assumption-tracker.sh", "0 WARN"), (8, "trust-score-validator.sh", "0 LOG"),
    (9, "confidence-gate.sh", "2 BLOCK"), (10, "clarification-interceptor.sh", "0 LOG"),
    (11, "auto-rollback-trigger.sh", "2 BLOCK"), (12, "lib/cross_verifier.py", "library"),
    (13, "reinvention-check.sh", "0 WARN"), (14, "lib/memory_scanner.py", "library"),
]

def registered_hooks():
    with open(os.path.join(ROOT, ".claude/settings.json")) as fh:
        data = json.load(fh)
    names = set()
    for _event, matchers in data.get("hooks", {}).items():
        for matcher in matchers:
            for hook in matcher.get("hooks", []):
                names.update(re.findall(r"hooks/([A-Za-z0-9._-]+\.sh)", hook.get("command", "")))
    return names

def fired_hooks():
    path = os.path.join(ROOT, ".cognitive-os/metrics/hook-timing.jsonl")
    seen = {}
    if not os.path.exists(path):
        return seen
    with open(path) as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("hook"):
                seen[rec["hook"]] = seen.get(rec["hook"], 0) + 1
    return seen

def blocks(script_rel):
    path = os.path.join(ROOT, "hooks", script_rel)
    if not os.path.exists(path):
        return None
    with open(path, errors="replace") as fh:
        return bool(re.search(r"^\s*exit\s+2\b", fh.read(), re.M))

def git_status():
    return subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                          capture_output=True, text=True, timeout=60).stdout

def main():
    before = git_status()
    reg, fired = registered_hooks(), fired_hooks()
    print(f"{'L':>3} {'hook':38s} {'declared':10s} {'reg':4s} {'fired':>7s} {'exit2':6s}")
    print("-" * 78)
    counts = dict(declared=0, registered=0, fired=0, blocks=0)
    findings = 0
    for num, hook, declared in LAYERS:
        counts["declared"] += 1
        base = os.path.basename(hook)
        stem = base[:-3] if base.endswith(".sh") else base
        is_lib = not base.endswith(".sh")
        is_reg, n_fired = base in reg, fired.get(stem, 0)
        does_block = blocks(base) if not is_lib else None
        counts["registered"] += is_reg
        counts["fired"] += bool(n_fired)
        counts["blocks"] += bool(does_block)
        flag = ""
        if not is_lib and not is_reg:
            flag, findings = "  <== DECLARED BUT NOT REGISTERED", findings + 1
        elif not is_lib and n_fired == 0:
            flag, findings = "  <== REGISTERED BUT NEVER FIRED", findings + 1
        elif "BLOCK" in declared and does_block is False:
            flag, findings = "  <== DECLARED BLOCK, NO exit 2 IN SOURCE", findings + 1
        print(f"{num:>3} {base:38s} {declared:10s} "
              f"{'yes' if is_reg else ('lib' if is_lib else 'NO'):4s} "
              f"{n_fired:>7d} {str(does_block):6s}{flag}")
    print(f"\nPROPORTION declared/registered/fired/blocking: "
          f"{counts['declared']}/{counts['registered']}/{counts['fired']}/{counts['blocks']}")
    print("\nNON-MUTATION CHECK:", "OK" if before == git_status() else "FAIL")
    return 1 if findings else 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(2)
```

Salida al 2026-08-15 sobre HEAD `8602ddc70`:

```
PROPORTION declared/registered/fired/blocking: 14/9/9/7
NON-MUTATION CHECK: OK (git status identical)
EXIT=1
```

(La columna `blocking=7` del script cuenta *presencia de `exit 2` en la fuente*, no alcanzabilidad. Corregido por fase y por disparos reales: **0**.)
