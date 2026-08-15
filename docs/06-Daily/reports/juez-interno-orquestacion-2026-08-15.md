# Juez interno — qué construimos para orquestar agentes con modelos distintos

- Fecha: 2026-08-15
- Alcance: este repo, medido con comandos. Sin borrar, desregistrar ni refactorizar nada.
- Criterio de existencia: ADR-342 (`docs/02-Decisions/adrs/ADR-342-existence-criterion-for-primitives.md`).
- Contraparte: hay un juez externo midiendo el estado del arte afuera, sin ver esto.

## Veredicto en una línea

Hay **dos cosas distintas** con el mismo nombre, y el encargo las confunde:
una **capa de dispatch multi-proveedor** (`cos_lib/dispatch.py`, 1069 líneas, cascada
real de 7 proveedores, budget gate, sandbox plan) que **nunca fue vista decidir — cero
registros, jamás**; y un **gate de concurrencia** (`hooks/dispatch-gate.sh`) que sí
está vivo, con 143 decisiones registradas, y que **no rutea modelos: cuenta slots**.
La orquestación multi-modelo no es "una sola función en vez de una capa" —
arquitectónicamente es una capa. Es una capa **inerte**.

Y lo que sí viaja al consumidor de todo este lote es **un solo archivo**:
`hooks/_lib/dispatch_gate_check.py`, en estado `candidate`.

---

## 1. El censo, con su comando

Enumerado sin filtro de extensión, como pide el encargo.

```bash
git ls-files | grep -i -E 'dispatch|provider|routing|router|orchestr|harness|driver|adapter' \
  | grep -v -E '^docs/|^\.cognitive-os/|^tests/|synthesis' | wc -l
```

De ahí, las piezas con función real (el resto son `.ai/adapters/*/README.md` y
`.ai/primitives/**/*.json`, que son metadatos, no ejecutables):

| # | Pieza | Qué es |
|---|---|---|
| 1 | `cos_lib/dispatch.py` (1069 líneas) | cascada multi-proveedor + métricas + budget gate |
| 2 | `scripts/orchestrator.py` (435 líneas) | CLI `run/list-live/scan-stale/kill-hung/control/answer` |
| 3 | `hooks/dispatch-gate.sh` | PreToolUse sobre Agent — gate de concurrencia |
| 4 | `hooks/_lib/dispatch_gate_check.py` | el cerebro Python del anterior (slots, circuit breaker, model advice) |
| 5 | `cos_lib/dispatch_model_advisor.py` | espejo ejecutable de `rules/model-routing.md` |
| 6 | `cos_lib/agent_redirect_protocol.py` + `hooks/agent-quota-redirect.sh` | redirige el tool Agent nativo hacia `orchestrator.py` |
| 7 | `packages/llm-providers/lib/{qwen,openrouter,gemini,ollama,openai,deepseek,claude_sdk}.py` | 7 adaptadores de proveedor |
| 8 | `scripts/_lib/settings-driver-{claude-code,codex,opencode,bare}.sh` | proyección de hooks a cada harness |
| 9 | `hooks/orchestrator-claim-gate.sh` + `scripts/orchestrator_claim_gate.py` | gate de claims en pre-commit/pre-push |
| 10 | `manifests/{harness-driver-capabilities.yaml, ai-agent-harness-landscape.yaml, harness-projection-registry.json, agent-orchestration-adapters.yaml, primitive-install-boundary.yaml}` | los cinco manifiestos declarativos |

`.ai/adapters/` tiene 27 directorios (`ls .ai/adapters/ | wc -l` → 27) y
`manifests/harness-projection-registry.json` declara 22 harnesses en
`implemented_order`. Ninguno de esos dos números mide código que corra: son
proyecciones declaradas.

---

## 2. Vida, pieza por pieza (ADR-342)

Las cuatro preguntas: (1) ¿el host publica el nombre? (2) ¿corre donde todavía
puede hacer algo? (3) ¿llega el campo? (4) ¿se la vio decidir?

### 2.1 `cos_lib/dispatch.py` — **NO EXISTE como control** (falla Q4, total)

```bash
ls .cognitive-os/metrics/llm-dispatch.jsonl
# ls: .cognitive-os/metrics/llm-dispatch.jsonl: No such file or directory
find . -name 'llm-dispatch*' -not -path './.git/*'
# solo rules/llm-dispatch.md y dos runbooks — ningún .jsonl, ni rotado
```

Esto no es "sin instrumentar". Es lo contrario: **cada camino de retorno de
`dispatch()` emite una métrica**, verificado sobre el código:

```bash
grep -n '_metric_sink or _log_metric' cos_lib/dispatch.py
# 665, 700, 725  → los tres return paths (sandbox unavailable, budget refuse, cascada)
```

Y el docstring dice `appended, never truncated`. Archivo ausente + emisión en
todos los caminos ⇒ **`dispatch()` nunca se ejecutó en este checkout**. Cero
decisiones sobre entrada real. Bajo ADR-342 §Decision rules eso es
`unmeasured`, no `healthy`, y **no puede contarse como cobertura**.

Refuerzo desde el entorno: los proveedores están habilitados en config pero sin
credenciales.

```bash
python3 -c "import yaml;d=yaml.safe_load(open('cognitive-os.yaml'))['llm_providers'];[print(k,v.get('enabled'),v.get('tier')) for k,v in d.items()]"
# qwen True 1 / openrouter True 2 / gemini True 3 / ollama False 4 / openai False 5 / deepseek False 5 / claude_sdk False 6
env | grep -oE '^(QWEN|DASHSCOPE|OPENROUTER|GEMINI|GOOGLE|OPENAI|DEEPSEEK)[A-Z_]*' | sort -u
# (vacío)
```

Tres proveedores habilitados en YAML, cero llaves. La cascada no puede pasar del
tier 1 aunque se la invoque.

Y ninguna telemetría del sistema menciona un proveedor no-Claude en un evento de
dispatch:

```bash
grep -c 'qwen' .cognitive-os/metrics/*.jsonl | grep -v ':0'
# aspirational-audit.jsonl:5   aci-observations.jsonl:57   reinvention-checks.jsonl:1
```
Los tres son **auditorías que hablan de qwen**, no dispatches a qwen.

### 2.2 `hooks/dispatch-gate.sh` — **VIVO**, pero no es lo que el encargo cree

```bash
grep -c 'dispatch-gate' .claude/settings.json          # 1  (PreToolUse, vía hook-timing-wrapper)
wc -l < .cognitive-os/metrics/dispatch-gate.jsonl      # 182
```
```bash
python3 -c "
import json,collections; c=collections.Counter(); ts=[]; ok=bad=0
for l in open('.cognitive-os/metrics/dispatch-gate.jsonl'):
    l=l.strip()
    if not l: continue
    try: d=json.loads(l); ok+=1
    except: bad+=1; continue
    c[d.get('action')]+=1; ts.append(d.get('timestamp'))
print(ok,bad,c,min(ts),max(ts))"
# 143 parseadas, 26 corruptas, Counter({'allow': 143}), 2026-07-02T18:51:09Z → 2026-08-15T21:33:24Z
```

- Q1 ✅ el matcher es `Agent` y Claude Code lo publica.
- Q2 ✅ `PreToolUse` — corre antes del lanzamiento, puede prevenir (`exit 2`).
- Q3 ✅ lee `.tool_input.prompt/description/task`, campos que sí llegan.
- Q4 ✅ **143 decisiones sobre entrada real en 6 semanas.** Pero **143 de 143 son
  `allow`, cero bloqueos.** Nunca se lo vio *prevenir*. Es un gate que existe y
  que todavía no ejerció.

Nota de método que confirma la advertencia del encargo: `hook-timing.jsonl`
registra este hook **13 veces** contra **182 filas** en su propio ledger.

```bash
python3 -c "
import json,collections;c=collections.Counter()
[c.update([json.loads(l).get('hook')]) for l in open('.cognitive-os/metrics/hook-timing.jsonl') if l.strip()]
print(sum(c.values()), c['dispatch-gate'])"
# 11113   13
```
Medir liveness por `hook-timing.jsonl` habría dado un veredicto 14× más bajo.

**Y lo importante: este gate no elige modelo. Cuenta slots** (`active` vs
`max_agents`, default 5). El campo `action` es lo único que decide.

### 2.3 Model routing (`rules/model-routing.md` + `cos_lib/dispatch_model_advisor.py`) — **instrumento, no gate; y en la rama que importa, mudo**

La regla es un documento. El único camino ejecutable que la aplica es:

```
hooks/dispatch-gate.sh:118  →  hooks/_lib/dispatch_gate_check.py:212  →  recommend_model()
                                                                       (cos_lib/dispatch_model_advisor.py)
```

`dispatch_gate_check.py` produce `result["model_directive"]` y
`result["model_advice"]`. Ahora, **cómo salen**:

```bash
sed -n '217,236p' hooks/dispatch-gate.sh
```
```
if [[ "$MODEL_DIRECTIVE" == MODEL_DISABLED:* ]]; then ... exit 2   ← esta rama SÍ llega al modelo
...
echo "$MODEL_DIRECTIVE" >&2
echo "  ${MODEL_ADVICE_LINE}" >&2
_log_event "allow"
exit 0                                                             ← esta rama va a stderr con exit 0
```

En Claude Code, el stderr de un PreToolUse que sale **0** va al usuario, no al
modelo; solo el `exit 2` alimenta al modelo. Es decir: **la recomendación de
modelo (opus/sonnet/haiku) se emite exactamente donde el que tiene que obedecerla
no la lee.** Es la forma #2 de ADR-342 —"corre donde ya no puede hacer nada"—
aplicada a un consejo en vez de a un bloqueo.

Peor para Q4: el ledger del propio gate **no registra `model_directive`**.

```bash
python3 -c "
import json,collections;c=collections.Counter()
[c.update([tuple(sorted(json.loads(l)))]) for l in open('.cognitive-os/metrics/dispatch-gate.jsonl') if l.strip() and l.strip()[0]=='{']
print(c.most_common(2))"
# claves: action, active, cb_evaluated, description, max, timestamp  → ningún campo de modelo
```

No hay forma de mostrar, desde fuera de la primitiva, que el ruteo de modelo haya
influido en un solo lanzamiento. **Falla Q4.** Comparar con el 0 de bloqueos del
gate: las dos únicas ramas que llegan al modelo (`MODEL_DISABLED` y slots llenos)
nunca dispararon.

### 2.4 `scripts/orchestrator.py` — vivo como CLI, **cero evidencia de uso**

Existe, tiene 6 subcomandos, `cmd_run` importa `dispatch` en la línea 309. Pero su
única salida observable sería `llm-dispatch.jsonl`, que no existe (§2.1). **Falla
Q4.** No hay ledger propio.

### 2.5 `hooks/agent-quota-redirect.sh` + `cos_lib/agent_redirect_protocol.py` — **NO EXISTE (falla Q1/Q2: no está registrado)**

```bash
grep -c 'agent-quota-redirect' .claude/settings.json   # 0
grep -c 'agent-quota-advisor'  .claude/settings.json   # 0
```

Ésta era la pieza conceptualmente más interesante del lote: el hook que
intercepta el tool `Agent` nativo y **redirige el sub-agente a la cascada** para
preservar Claude Max. Es exactamente el problema que el harness no resuelve. Y
**no está registrado en ningún evento.** Aparece en
`.ai/adapters/claude-code/adapter.json`, pero ahí mismo declara
`"claims_runtime_enforcement": false, "fidelity": "documented-only"` — el propio
manifiesto avisa que es proyección documental, no cableado.

### 2.6 Los cuatro drivers — **dos vivos, uno huérfano, uno inexistente**

```bash
grep -n 'settings-driver' cmd/cos/internal/cli/derive.go
# 86: settings-driver-claude-code.sh
# 87: settings-driver-codex.sh
```
Solo dos se invocan. El de opencode aparece únicamente como
`generated_by` dentro de su propio output (`.opencode/cos-hooks.json`) — no
tiene un llamador en `derive.go`. El de **bare** no tiene ningún llamador en todo
el repo fuera de docs; `.cognitive-os/plans/architecture/adr-064-implementation-plan.md`
lo sigue listando como **`pending`** (tarea 2.4). "Los cuatro drivers" del
encargo son, medidos, **dos**.

### 2.7 `hooks/orchestrator-claim-gate.sh` — vivo por git, y **nunca encontró nada**

```bash
grep -c 'orchestrator-claim-gate' .claude/settings.json  # 0   (no es hook del harness)
wc -l < .cognitive-os/metrics/orchestrator-claim-gate.jsonl  # 735
python3 -c "
import json,collections;c=collections.Counter()
[c.update([(json.loads(l)['ok'], len(json.loads(l)['findings']))]) for l in open('.cognitive-os/metrics/orchestrator-claim-gate.jsonl') if l.strip()]
print(c)"
# Counter({(True, 0): 735})    modes: pre-commit / pre-push, 2026-05-14 → 2026-08-15
```
735 corridas, **735 con `findings: []`**. Pasa Q1–Q3 (corre en pre-commit, ve el
diff), y en Q4 está en el borde: se lo vio *correr* 735 veces y **nunca decidir
distinto**. Bajo el criterio de ADR-342 "cero decisiones sobre N corridas es un
hallazgo, no un estado sano".

---

## 3. ¿Viaja al consumidor?

```bash
python3 - <<'EOF'
import json,glob
for f in glob.glob('.ai/primitives/**/*.json',recursive=True):
    d=json.load(open(f)); s=str(d.get('canonical_source') or d.get('source_id') or '')
    if any(t in s for t in ('dispatch','orchestr','provider','quota-redirect','model-routing','settings-driver')):
        lc=d.get('lifecycle',{}); print(s, lc.get('distribution'), lc.get('runtime_projection'), lc.get('lifecycle_state'))
EOF
```

| Pieza | distribution | runtime_projection | estado |
|---|---|---|---|
| `hooks/_lib/dispatch_gate_check.py` | **core** | **true** | candidate |
| `hooks/dispatch-gate.sh` | maintainer | true | blocking |
| `hooks/agent-quota-redirect.sh` | maintainer | true | advisory |
| `scripts/orchestrator.py` | maintainer | **false** | advisory |
| `rules/llm-dispatch.md` | lab | **false** | advisory |
| `rules/model-routing.md` | lab | **false** | advisory |
| `rules/orchestrator-mode.md` | lab | false | advisory |
| `scripts/cos_dispatch_smoke.py` | maintainer | false | active |
| `scripts/cos-provider-call` | team | false | sandbox |
| `hooks/orchestrator-claim-gate.sh` | team | true | blocking |
| `hooks/bash-hot-path-dispatcher.sh` | team | true | blocking |

**De las 20 primitivas de este dominio, exactamente una tiene
`distribution: core` + `runtime_projection: true`**: el helper Python del gate de
concurrencia — y está en `candidate`.

Toda la orquestación multi-modelo (`orchestrator.py`, `rules/llm-dispatch.md`,
`rules/model-routing.md`, los smokes de proveedor) es **`maintainer`/`lab` con
`runtime_projection: false`**. Resuelve un problema de este repo, no del
ecosistema. Eso cambia la conversación sobre reinvención: no se está compitiendo
con nadie, porque no se está entregando a nadie.

### Contradicción entre dos manifiestos (hallazgo)

```bash
python3 -c "
import json,yaml
p=json.load(open('.ai/primitives/rules/rules-model-routing-md-30905656d2.json'))['lifecycle']
b=yaml.safe_load(open('manifests/primitive-install-boundary.yaml'))
print('primitives:', p['distribution'], p['runtime_projection'])
print('install-boundary default core:', 'rules/model-routing.md' in b['profiles']['default']['primitives']['rules'])"
# primitives: lab False
# install-boundary default core: True
```

`.ai/primitives` dice que `rules/model-routing.md` es **lab, no proyectable**.
`manifests/primitive-install-boundary.yaml` la lista en el perfil **`default`
(`primitive_distribution: core`)**. Los dos manifiestos que gobiernan qué viaja
**se contradicen sobre el mismo archivo**. No lo toqué (el encargo mide, no
arregla), pero cualquier cifra de cobertura que se apoye en uno de los dos hereda
el error.

---

## 4. Qué problema resuelve cada pieza, en una frase

| Pieza | Si no estuviera… |
|---|---|
| `cos_lib/dispatch.py` | …no habría forma de mandar un sub-agente a Qwen/OpenRouter/Gemini con reintentos, tope de costo y cascada. **Hoy no la hay igual: nunca corrió.** |
| `hooks/dispatch-gate.sh` | …nada limitaría los agentes concurrentes a 5, y una sesión podría abrir N y agotar contexto. Es el único control de este lote que ejerce sobre entrada real. |
| `hooks/_lib/dispatch_gate_check.py` | …el gate no sabría cuántos agentes hay activos ni si el skill está en circuit-breaker. Es la única pieza que viaja al consumidor. |
| `cos_lib/dispatch_model_advisor.py` | …no existiría una versión ejecutable de la tabla opus/sonnet/haiku. **Existe, y su salida va a stderr con exit 0.** |
| `hooks/agent-quota-redirect.sh` | …no habría manera de que el tool `Agent` nativo se desvíe a la cascada. **No la hay: el hook no está registrado.** |
| `scripts/orchestrator.py` | …no habría CLI para lanzar/listar/matar sub-agentes fuera del harness. Sin uso registrado. |
| `packages/llm-providers/lib/*.py` | …cada llamada a un proveedor sería HTTP a mano en el sitio de uso. 7 adaptadores, ninguno visto ejecutar. |
| `scripts/_lib/settings-driver-{claude-code,codex}.sh` | …los hooks canónicos no se proyectarían al `settings.json` de cada harness, y habría que mantener dos registros a mano. **Éste sí resuelve algo real y corre.** |
| `settings-driver-{opencode,bare}.sh` | …nada cambiaría hoy: uno no tiene llamador, el otro está `pending` en su plan. |
| `hooks/orchestrator-claim-gate.sh` | …los commits podrían afirmar cosas sin respaldo. 735 corridas, 0 hallazgos. |
| Los 5 manifiestos | …no habría inventario de qué harness soporta qué evento. Son el activo declarativo más honesto del lote (`harness-driver-capabilities.yaml` documenta explícitamente el `codex_tool_coverage_gap`). |

**Donde no pude escribir la frase**: `.ai/adapters/` (27 dirs) y los 22 harnesses
de `harness-projection-registry.json`. Si desaparecieran, ningún comando cambiaría
de resultado — son metadatos sobre harnesses que nadie proyecta. Ése es el
hallazgo, según el propio encargo.

---

## 5. Qué del encargo era falso

1. **"por defecto van `--providers qwen,claude`"** — **falso.**
   ```bash
   sed -n '384,388p' scripts/orchestrator.py
   # default="qwen,openrouter,gemini,ollama,claude"
   ```
   Son cinco proveedores (ADR-062), no dos. El help del propio flag llama a
   `qwen,claude` *"legacy 2-tier"*. Y **`rules/RULES-COMPACT.md:19` repite la
   versión vieja** — el error no lo inventó el orquestador, lo copió del índice de
   reglas del repo:
   ```bash
   grep -n 'qwen,claude' rules/RULES-COMPACT.md
   # 19: ... default `--providers qwen,claude` ... Metrics→`llm-dispatch.jsonl`.
   ```
   Esa misma línea 19 es también la fuente del punto 2. Vale la pena arreglar el
   índice, no el brief.

2. **"Métricas a `llm-dispatch.jsonl`"** — **es una intención, no un hecho.** El
   archivo no existe (§2.1). Citarlo como fuente de verificación es exactamente
   lo que ADR-342 llama responder desde la primitiva misma: el código dice que
   escribe ahí, y eso se tomó por evidencia de que escribió.

3. **"Los cuatro drivers"** — **dos.** `opencode` sin llamador, `bare` `pending`
   (§2.6).

4. **"buscá si hay un package de orquestación"** — no hay ninguno llamado así.
   Lo más cercano es `packages/llm-providers/` (7 adaptadores, sin ledger) y
   `packages/agent-coordination/` (rules+skills, sin lib de dispatch). La
   orquestación vive en `cos_lib/` + `hooks/`, no en `packages/`.

5. **Kill-switches `COS_DISABLE_LLM_FALLBACK=1` / `COS_FORCE_CLAUDE_PRIMARY=1`** —
   esto **sí es cierto**, están implementados (`cos_lib/dispatch.py:153`,
   `scripts/orchestrator.py:69`). Pero son kill-switches de un camino que nunca
   se recorrió: apagan algo que no está prendido.

6. **`.ai/adapters/` "(27)"** — reproduce exacto (`ls .ai/adapters/ | wc -l` → 27).
   Una de las pocas cifras del brief que sobrevive el recuento.

---

## 6. El verde barato que no compré

El atajo disponible era concluir **"esto es reinvención: el harness ya tiene
subagentes con `model:`"**. La pregunta que decide, según la norma de la casa:
*¿un cambio en uno de los dos conceptos debería obligar a tocar el otro?*

**No.** El tool `Agent` de Claude Code elige entre modelos **de Anthropic**;
`cos_lib/dispatch.py` elige entre **proveedores distintos** para preservar cuota
de Claude Max. Si Anthropic agrega un modelo, la cascada no cambia; si Qwen cae,
el tool `Agent` no se entera. **Son conceptos distintos y la coincidencia de
nombre es eso, coincidencia** — queda aceptada con este motivo escrito.

El atajo inverso —"no es reinvención, mirá qué grande y cuántos tests tiene"—
tampoco: 1069 líneas y una batería de tests en `tests/unit/test_dispatch_*.py` no
mueven ninguna de las cuatro respuestas de ADR-342. El veredicto de §2.1 sigue
siendo cero decisiones observadas.

La conclusión honesta no es "reinvención" ni "original". Es: **el concepto es
genuinamente distinto del que ofrece el harness, y todavía no existe** en el
sentido de ADR-342.

---

## 7. Comandos para rehacer este informe

```bash
ls .cognitive-os/metrics/llm-dispatch.jsonl                       # ausente ⇒ 0 dispatches
grep -n 'default=' scripts/orchestrator.py | sed -n '1,12p'       # cascada real de 5
wc -l < .cognitive-os/metrics/dispatch-gate.jsonl                 # 182
grep -c 'agent-quota-redirect' .claude/settings.json              # 0
grep -n 'settings-driver' cmd/cos/internal/cli/derive.go          # 2 drivers invocados
grep -c 'orchestrator-claim-gate' .claude/settings.json           # 0 (corre por git, no por harness)
ls .ai/adapters/ | wc -l                                          # 27
```

Todos read-only. Ningún archivo de `.cognitive-os/metrics/`, `hooks/**` ni
`rules/**` fue modificado por esta medición.
