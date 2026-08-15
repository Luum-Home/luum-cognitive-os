# Juez 3 — Conformidad con la spec publicada

**Fecha:** 2026-08-15
**Alcance:** `luum-agent-os` @ `8602ddc70` (working tree sucio de otra sesión; no se tocó nada)
**Lente:** de las primitivas que SÍ tienen especificación publicada, ¿las estamos escribiendo como la spec lo dicta?
**Modo:** read-only. Único archivo escrito: este.

**Degradación declarada.** Al arrancar: `vm.swapusage` = 37047.75M usados de 37888.00M (97.8%), `uptime` load 13.81. No se corrió la suite de tests, ni `pytest`, ni ningún gate. Todo lo de abajo sale de lectura de archivos y parseo — nada que compile, arranque un harness o levante un proceso. Eso acota qué puedo afirmar: ver §6.

---

## 1. Veredicto

Las tres familias con spec pasan el piso duro (194 de 195 primitivas cargan), pero la conformidad de *convención* está prácticamente en cero: 189 de 194 skills usan un vocabulario de frontmatter que ninguna de las dos specs de Agent Skills reconoce, 128 tienen una `description` que no dice cuándo usarlas — el campo del que depende el ruteo — y el único subagente del repo vive en un directorio del que Claude Code no carga subagentes.

---

## 2. Tabla por familia

| Familia | Total | Conformes | No canónicas | Violan | Spec usada (fuente + fecha de acceso) |
|---|---:|---:|---:|---:|---|
| **Skills** (`SKILL.md` únicos por `realpath`) | 194 | 4 | 189 | 1 | `code.claude.com/docs/en/skills.md` + `platform.claude.com/docs/en/agents-and-tools/agent-skills/{overview,best-practices}` — 2026-08-15 |
| **Hooks** (registrados en `cognitive-os.yaml > harness.hooks`) | 200 | 176 | 24 | 0 | `code.claude.com/docs/en/hooks.md` — 2026-08-15 |
| **Subagentes** (`agents/`, `.claude/agents/`) | 1 | 0 | 0 | 1 | `code.claude.com/docs/en/sub-agents.md` — 2026-08-15 |
| **Rules** (`rules/*.md`) | 129 | — | — | — | **Sin spec publicada.** Solo consistencia interna: 10 ref-keys del índice apuntan a archivos inexistentes |
| **MCP** (`mcp-server/cos_mcp.py`) | 1 | — | — | — | **NO EVALUADA.** Ver §6 |

La regla de agregación es *worst-of*: una skill con una sola desviación de convención cuenta como no canónica aunque cumpla las otras nueve reglas. Por eso "4 conformes" no significa "190 rotas" — significa que casi ninguna está escrita como la spec la escribe. El desglose regla por regla está en §5.

### Skills: conformidad regla por regla (194)

| Regla | Nivel | Cumplen | Fallan |
|---|---|---:|---:|
| `SKILL.md` con frontmatter YAML parseable | MUST | 193 | **1** |
| `name` presente y no vacío | MUST (canal API) | 193 | 1 |
| `description` presente y no vacía | MUST | 193 | 1 |
| `name` ≤ 64 chars | MUST (canal API) | 193 | 0 |
| `name` solo `[a-z0-9-]` | MUST (canal API) | 192 | **1** (`__contracts__`) |
| `description` ≤ 1024 chars | MUST (canal API) | 193 | 0 (máx real: 517) |
| **`description` dice CUÁNDO usar la skill** | **MUST** | **65** | **128** |
| body < 500 líneas | SHOULD | 194 | 0 (máx real: 369) |
| Frontmatter dentro del vocabulario de Claude Code | — (lista abierta) | 5 | **189** |
| Frontmatter dentro de los 6 campos de la Skills API | MUST (canal API) | 5 | **189** |
| `name` == nombre del directorio | **NO ES REGLA** | 190 | 3 (ver §5) |

---

## 3. Los desvíos que rompen

### 3.1 VIOLA — `skills/patch-release/SKILL.md:1` — comentario HTML antes del frontmatter

```
skills/patch-release/SKILL.md
  1  <!-- SCOPE: both -->
  2  ---
  3  name: patch-release
  4  description: Use when preparing, validating, publishing, or diagnosing a Cognitive OS patch release…
```

**La regla:** "Every Skill requires a `SKILL.md` file with YAML frontmatter." — `platform.claude.com/docs/en/agents-and-tools/agent-skills/overview`, acc. 2026-08-15. El frontmatter YAML se delimita en la **primera** línea del archivo; una línea previa lo invalida.

**Evidencia de que rompe, no de que un linter se queje.** El listado de skills que el harness inyectó en el prompt de esta misma sesión — o sea, lo que Claude realmente ve para decidir el ruteo — dice:

```
- patch-release: <!-- SCOPE: both -->
```

Ese es el comentario HTML ocupando el lugar de la descripción. Las otras 193 skills aparecen en ese listado con su descripción real o sin descripción; ésta aparece con el comentario. El campo `description` del archivo, que sí está bien escrito y sí dice cuándo usarla, **nunca llega al ruteador**. La skill está en disco, tiene 1 desviación de un carácter de posición, y es inelegible.

Reproducción independiente del listado:

```
$ python3 -c "
import re,yaml
t=open('skills/patch-release/SKILL.md').read()
print(re.match(r'^---\r?\n(.*?)\r?\n---\r?\n',t,re.S))"
None
```

Es el único archivo del repo con este defecto: `for f in $(find -L skills -name SKILL.md); do head -1 "$f" | grep -q '^<!--' && echo "$f"; done` devuelve exactamente uno.

### 3.2 VIOLA — `agents/test-coverage-enforcer.md` — ubicación de la que no se cargan subagentes

**La regla:** los subagentes se resuelven desde `.claude/agents/` (proyecto), `~/.claude/agents/` (personal), `<plugin>/agents/` (plugin) y managed settings. — `code.claude.com/docs/en/sub-agents.md`, tabla "Choose the subagent scope", acc. 2026-08-15. `agents/` en la raíz del repo no está en esa lista.

**Evidencia de que rompe:**

```
$ find .claude/agents -maxdepth 1 -name '*.md' | wc -l
0
$ ls .claude/agents
_archived
```

`.claude/agents/` no contiene ni un `.md` cargable ni un symlink a `agents/`. El repo tiene exactamente un subagente definido y el harness carga cero. No es teoría: los tipos de agente disponibles en esta sesión (`general-purpose`, `Explore`, `claude-code-guide`, …) vienen del perfil y de plugins; `test-coverage-enforcer` no está entre ellos.

Agrava que el propio repo lo dio por vivo: `docs/04-Concepts/architecture/functional-audit/sprint-2a-orphan-fate.md:82` lo marca **KEEP** con el argumento "Most structured frontmatter (`name`, `description`, `triggers:`); referenced by squad templates". El frontmatter está bien formado; el problema es dónde está el archivo, que esa auditoría no miró.

Segundo defecto del mismo archivo, menor: `triggers:` no es campo de subagente (los válidos son `tools`, `model`, `color`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`, `isolation`, `initialPrompt`, `disallowedTools` — misma fuente). Sería NO CANÓNICO si el archivo se cargara.

### 3.3 Índice de rules roto — 10 de 138 ref-keys apuntan a la nada

`rules/RULES-COMPACT.md` se declara "Compressed index. Full rules loaded on trigger via `[ref-key]`". Diez de esas claves no tienen archivo, ni en `rules/` ni en `packages/*/rules/`:

`cognitive-os-changes`, `component-classification`, `component-reality-check`, `cost-predictor`, `dogfood-score`, `dogfooding`, `library-selection`, `os-vs-project`, `plan-first`, `stash-mutation-reversibility`

No hay spec externa que esto viole — es el contrato que el propio índice declara. El mecanismo de expansión no puede resolverlas. Un archivo (`ROADMAP.md`) está en `rules/` sin ser citado por el índice.

### 3.4 No rompen, pero conviene saberlo

- **`matcher` en 4 eventos que no lo aceptan.** `.claude/settings.json` emite `"matcher": ""` en `UserPromptSubmit[0]`, `Stop[0]`, `TeammateIdle[0]`, `TaskCreated[0]`. La spec lista esos cuatro entre los eventos **sin** matcher (`code.claude.com/docs/en/hooks.md`, acc. 2026-08-15). Con string vacío el efecto es nulo, pero es el generador emitiendo un campo que el evento no tiene — el mismo generador que mañana podría emitir un matcher no vacío ahí. **NO CANÓNICO**, en `scripts/_lib/settings-driver-claude-code.sh`.
- **24 hooks NO CANÓNICOS.** Doce `PostToolUse` con `exit 2`, evento donde la spec dice que exit 2 no bloquea (`hooks.md`, sección exit codes, acc. 2026-08-15): el efecto real es mostrarle stderr a Claude, que es un uso documentado, así que el riesgo es que el autor haya creído que bloqueaba. Doce más (7 `PreToolUse`/`PostToolUse`, 5 `UserPromptSubmit`) no acceden al stdin del contrato ni directamente ni por `_lib/` — deciden con estado de disco y variables de entorno, no con el `tool_input` que el evento les entrega. Lista completa con `-v`.
- **`TaskCompleted` proyectado con cero grupos.** Está registrado en `cognitive-os.yaml` con `hooks/task-completed.sh` y `settings.json` emite `"TaskCompleted": []`. **Es deliberado y está documentado** en `scripts/_lib/settings-driver-claude-code.sh:475` ("ADR-126/133: TaskCompleted is demoted from default projection"). No lo cuento como defecto de conformidad; lo dejo escrito porque el registro dice que el hook existe y la proyección lo apaga, y esa combinación se lee mal desde el registro solo.

---

## 4. El problema de fondo en skills: `description` no rutea

La spec es explícita en para qué sirve el campo: *"The description must include both what the Skill does and when Claude should use it."* — `platform.claude.com/docs/en/agents-and-tools/agent-skills/overview`, acc. 2026-08-15. Es el único texto que el modelo ve antes de decidir si abre la skill (nivel 1 de progressive disclosure).

**128 de 193 descripciones no dicen cuándo.** Se parten en dos formas:

**(a) 73 con el envoltorio circular del generador.** El patrón es literal:

> `Use when you need this Cognitive OS skill: <qué hace>; do not use when a narrower skill directly matches the task.`

Sintácticamente empieza con "Use when". Semánticamente el criterio de activación es "usala cuando la necesites", y el núcleo es una descripción de *qué hace*. Ejemplos tal cual están en disco:

- `add-hook`: "…: Step-by-step guide for adding a new hook to the Cognitive OS; …"
- `agent-dashboard`: "…: Show real-time status of all running background agents; …"
- `__contracts__`: "…: Structural namespace for shared Cognitive OS skill contracts used by other agentic primitives; …"

**(b) 55 sin ningún criterio**, solo el qué: `retrospective` ("Weekly analysis of all squads with trend analysis and auto-reconfiguration proposals"), `squad-manager`, `arena`, `secret-audit`, `impact-analysis`, `sandbox-sample`, `trust-audit`, `smoke-test`, `repair-status`, `tool-discovery`, `sprint`, …

**Declaro el criterio y su borde.** La clasificación (a) es discutible: "Step-by-step guide for adding a new hook" le deja al modelo inferir el cuándo. La conté como no canónica porque la spec pide que el cuándo *esté*, no que se infiera, y porque el envoltorio inflaría cualquier grep ingenuo de "use when" a 138/193 falsos conformes. El script separa las tres cajas para que se pueda re-clasificar sin re-correrlo.

**El dato que cierra el punto:** el campo que Claude Code destina exactamente a esto, `when_to_use`, se usa **0 veces** en las 194 skills. En su lugar hay `triggers:` (189 usos), que no existe en ninguna de las dos specs y que el harness no lee.

### El vocabulario paralelo

189 de 194 skills declaran al menos un campo que Claude Code no reconoce. Los más frecuentes:

| Campo | Usos | ¿En spec? |
|---|---:|---|
| `audience` | 189 | no |
| `version` | 189 | no |
| `triggers` | 189 | no |
| `routing_intents` | 188 | no |
| `platforms` | 183 | no |
| `prerequisites` | 167 | no |
| `summary_line` | 147 | no |
| `routing_patterns` | 125 | no |
| `last-updated` | 83 | no |
| `tags` | 55 | no |
| `auto-generated` | 54 | no |
| `user-invocable` | 75 | **sí** (Claude Code) |
| `effort` / `model` / `metadata` / `license` | 36/33/33/30 | **sí** |
| `disable-model-invocation` | 12 | **sí** |
| `allowed-tools` | 4 | **sí** |

Esto no rompe nada hoy: Claude Code ignora las claves que no conoce. Tiene dos consecuencias medibles. Una, el ruteo del repo corre por un motor propio (`routing_patterns`/`routing_intents`, leído por su skill-router) en paralelo al del harness, que solo ve `description` — y `description`, según arriba, está vacía de criterio en 128 casos. Dos, si alguna de estas skills se empaqueta para la Skills API, **189 de 194 son rechazadas por el validador**: la lista fuera de Claude Code es cerrada en seis campos (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`) y el error es literal — "Unexpected key(s) in SKILL.md frontmatter: … Allowed properties are: …" (`code.claude.com/docs/en/skills.md`, sección "Using skill frontmatter outside Claude Code", acc. 2026-08-15).

Las 4 que sobreviven a todo: `packages/quality-gates/skills/dod-check`, `packages/sdd-compound/skills/plan-chore`, `packages/sdd-compound/skills/plan-feature`, `skills/skill-creator`.

---

## 5. El script

Read-only, determinista, sin estado de sesión. `exit 0` sin hallazgos / `1` con hallazgos / `2` error. Guardarlo y correr `python3 conformidad.py <repo_root> [-v]`.

```python
#!/usr/bin/env python3
# conformidad.py — read-only. Uso: python3 conformidad.py <repo_root> [-v]
# Reglas fetcheadas 2026-08-15 de code.claude.com/docs/en/{skills,hooks,sub-agents}.md
# y platform.claude.com/docs/en/agents-and-tools/agent-skills/{overview,best-practices}
import os,re,sys,json,glob,subprocess,collections
import yaml
os.chdir(sys.argv[1]); V='-v' in sys.argv

# ── SPEC ───────────────────────────────────────────────────────────────────────
EVENTS={"SessionStart","Setup","UserPromptSubmit","UserPromptExpansion","PreToolUse",
"PermissionRequest","PermissionDenied","PostToolUse","PostToolUseFailure","PostToolBatch",
"Notification","MessageDisplay","SubagentStart","SubagentStop","TaskCreated","TaskCompleted",
"Stop","StopFailure","TeammateIdle","InstructionsLoaded","ConfigChange","CwdChanged",
"DirectoryAdded","FileChanged","WorktreeCreate","WorktreeRemove","PreCompact","PostCompact",
"Elicitation","ElicitationResult","SessionEnd"}
NO_MATCHER={"UserPromptSubmit","PostToolBatch","Stop","TeammateIdle","TaskCreated",
"TaskCompleted","WorktreeCreate","WorktreeRemove","MessageDisplay","CwdChanged"}
CANT_BLOCK_EXIT2={"PostToolUse","PostToolUseFailure","PermissionDenied","Notification",
"StopFailure","SubagentStart","SessionStart","Setup","SessionEnd","CwdChanged",
"DirectoryAdded","FileChanged","PostCompact","InstructionsLoaded","MessageDisplay"}
CC_FM={'name','description','when_to_use','argument-hint','arguments','disable-model-invocation',
'user-invocable','allowed-tools','disallowed-tools','model','effort','context','agent',
'background','hooks','paths','shell','metadata','license','compatibility'}   # canal Claude Code
API_FM={'name','description','license','compatibility','metadata','allowed-tools'}  # canal Skills API
AG_REQ={'name','description'}
AG_OPT={'tools','disallowedTools','model','color','permissionMode','maxTurns','skills',
'mcpServers','hooks','memory','background','effort','isolation','initialPrompt'}
AG_MODEL={'sonnet','opus','haiku','fable','inherit'}

def fm_of(path):
    t=open(path,encoding='utf-8',errors='replace').read()
    m=re.match(r'^---\r?\n(.*?)\r?\n---\r?\n?(.*)$',t,re.S)
    if not m: return None,t,'FRONTMATTER_NO_PARSEA'
    try: fm=yaml.safe_load(m.group(1))
    except Exception as e: return None,m.group(2),'YAML_ERROR:'+str(e)[:80]
    return (fm,m.group(2),None) if isinstance(fm,dict) else (None,m.group(2),'FM_NO_MAPPING')

def bucket(viola,nocanon): return 'VIOLA' if viola else ('NO_CANONICO' if nocanon else 'CONFORME')

# ── SKILLS (dedup por realpath: un symlink y su destino son UNA primitiva) ─────
HEAD=re.compile(r'^\s*Use when you need this Cognitive OS skill:\s*',re.I)
TAIL=re.compile(r';?\s*do not use when a narrower skill directly matches the task\.?\s*$',re.I)
WHEN=re.compile(r"\b(use (?:this )?(?:skill )?when|use when|when the user|when you(?:'re| are)?\b"
r"|triggers? on|trigger:|activates? (?:on|for|when)|invoke when|call when|whenever"
r"|usar (?:siempre )?(?:antes|cuando)|se usa cuando|before |after |during |if the )",re.I)
paths=subprocess.run(['find','-L','skills','-name','SKILL.md'],capture_output=True,text=True).stdout.split()
uniq=sorted({os.path.realpath(p) for p in paths})
S=collections.Counter(); s_viola=[]; s_nc=[]; nodesc_when=0
for rp in uniq:
    rel=os.path.relpath(rp); d=os.path.basename(os.path.dirname(rp))
    fm,body,err=fm_of(rp); viola=[]; nc=[]
    if err: viola.append(err)
    else:
        n,de=fm.get('name'),fm.get('description')
        if not isinstance(n,str) or not n: viola.append('name ausente/no-str')
        if not isinstance(de,str) or not de: viola.append('description ausente/vacia')
        if isinstance(n,str):
            if len(n)>64: viola.append(f'name>64 ({len(n)})')
            if not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*',n): nc.append(f'name charset invalido: {n!r}')
            if n!=d: nc.append(f'name({n}) != dir({d})')
        if isinstance(de,str):
            if len(de)>1024: viola.append(f'description>1024 ({len(de)})')
            core=TAIL.sub('',HEAD.sub('',de)).strip()   # descuenta el boilerplate del generador
            if not WHEN.search(core): nc.append('description sin criterio de CUANDO'); nodesc_when+=1
        extra=set(fm)-CC_FM
        if extra: nc.append('campos fuera de spec CC: '+','.join(sorted(extra)[:5]))
        if body.count('\n')+1>500: nc.append('body>500 lineas')
    b=bucket(viola,nc); S[b]+=1
    if b=='VIOLA': s_viola.append((rel,viola))
    elif b=='NO_CANONICO' and V: s_nc.append((rel,nc))

# ── HOOKS (registro canónico = cognitive-os.yaml > harness.hooks, ADR-064) ─────
reg=yaml.safe_load(open('cognitive-os.yaml'))['harness']['hooks']
STDIN=re.compile(r'\$\(\s*cat\b|read_stdin_json|normalize-stdin|stdin_field|hook_get_field'
r'|HOOK_RAW_INPUT|/dev/stdin|_lib/common\.sh|_lib/hook-pipe\.sh')
def reads_stdin(p,depth=0,seen=None):   # sigue el source de _lib/ hasta 3 niveles
    seen=seen or set()
    if p in seen or depth>3 or not os.path.exists(p): return False
    seen.add(p); t=open(p,encoding='utf-8',errors='replace').read()
    if STDIN.search(t): return True
    return any(reads_stdin('hooks/_lib/'+l,depth+1,seen) for l in re.findall(r'_lib/([\w\-]+\.sh)',t))
H=collections.Counter(); h_viola=[]; h_nc=[]
for name,v in sorted(reg.items()):
    p,ev=v['script'],v['event']; viola=[]; nc=[]
    if not os.path.exists(p): viola.append('script inexistente')
    else:
        if not os.access(p,os.X_OK): viola.append('no ejecutable')
        t=open(p,encoding='utf-8',errors='replace').read()
        if not t.startswith('#!'): viola.append('sin shebang')
        if ev not in EVENTS: viola.append(f'evento invalido: {ev}')
        if not reads_stdin(p) and ev in {'PreToolUse','PostToolUse','UserPromptSubmit'}:
            nc.append('no accede al stdin del contrato')
        if '2' in set(re.findall(r'\bexit\s+(\d+)',t)) and ev in CANT_BLOCK_EXIT2:
            nc.append(f'exit 2 en {ev} (no bloquea segun spec)')
    b=bucket(viola,nc); H[b]+=1
    if b=='VIOLA': h_viola.append((name,p,viola))
    elif V: h_nc.append((name,p,nc))
st=json.load(open('.claude/settings.json'))['hooks']
proj_bad=[]
for ev,arr in st.items():
    if ev not in EVENTS: proj_bad.append(f'evento invalido en settings.json: {ev}')
    if not arr: proj_bad.append(f'{ev}: clave emitida con 0 grupos')
    for i,m in enumerate(arr):
        if ev in NO_MATCHER and 'matcher' in m:
            proj_bad.append(f'{ev}[{i}]: matcher={m["matcher"]!r} en evento que NO acepta matcher')
        for h in m.get('hooks',[]):
            if h.get('type')!='command': proj_bad.append(f'{ev}[{i}]: type={h.get("type")!r}')
n_proj=sum(len(m.get('hooks',[])) for a in st.values() for m in a)

# ── SUBAGENTES ────────────────────────────────────────────────────────────────
A=collections.Counter(); a_det=[]
for p in sorted(glob.glob('.claude/agents/*.md')+glob.glob('agents/*.md')):
    fm,_,err=fm_of(p); viola=[]; nc=[]
    if not p.startswith('.claude/agents/'):
        viola.append('ubicacion invalida: se cargan de .claude/agents/, ~/.claude/agents/ o <plugin>/agents/')
    if err: viola.append(err)
    else:
        for k in AG_REQ:
            if not fm.get(k): viola.append(f'{k} ausente')
        n=fm.get('name')
        if isinstance(n,str) and ':' in n: viola.append('name contiene ":" (no carga)')
        if isinstance(n,str) and not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*',n): nc.append('name charset')
        if fm.get('model') and str(fm['model']) not in AG_MODEL and not str(fm['model']).startswith('claude-'):
            viola.append(f'model invalido: {fm["model"]!r}')
        extra=set(fm)-AG_REQ-AG_OPT
        if extra: nc.append('campos fuera de spec: '+','.join(sorted(extra)))
    b=bucket(viola,nc); A[b]+=1; a_det.append((p,b,viola+nc))

# ── RULES (sin spec publicada: solo consistencia del indice) ───────────────────
idx=open('rules/RULES-COMPACT.md').read()
refs=set(re.findall(r'\[`([a-z0-9\-]+)`\]',idx))
files={os.path.splitext(os.path.basename(p))[0] for p in glob.glob('rules/*.md')}
pkg={os.path.splitext(os.path.basename(p))[0] for p in glob.glob('packages/*/rules/*.md')}
dangling=sorted(refs-files-pkg); orphan=sorted(files-refs-{'RULES-COMPACT'})

# ── SALIDA ────────────────────────────────────────────────────────────────────
print(f"SKILLS  total={sum(S.values())}  CONFORME={S['CONFORME']}  NO_CANONICO={S['NO_CANONICO']}  VIOLA={S['VIOLA']}")
print(f"        description sin criterio de CUANDO: {nodesc_when}")
for r,w in s_viola: print(f"        VIOLA: {r} :: {'; '.join(w)}")
print(f"HOOKS   registrados={sum(H.values())}  CONFORME={H['CONFORME']}  NO_CANONICO={H['NO_CANONICO']}  VIOLA={H['VIOLA']}")
print(f"        proyectados a .claude/settings.json: {n_proj}  (gap: {sum(H.values())-n_proj})")
for x in proj_bad: print(f"        PROYECCION: {x}")
for n,p,w in h_viola: print(f"        VIOLA: {n} ({p}) :: {'; '.join(w)}")
print(f"AGENTS  total={sum(A.values())}  CONFORME={A['CONFORME']}  NO_CANONICO={A['NO_CANONICO']}  VIOLA={A['VIOLA']}")
for p,b,w in a_det: print(f"        {b}: {p} :: {'; '.join(w) or 'ok'}")
print(f"RULES   archivos rules/*.md={len(files)}  ref-keys en el indice={len(refs)}")
print(f"        ref-keys sin archivo: {len(dangling)} -> {', '.join(dangling)}")
print(f"        archivos no citados: {len(orphan)} -> {', '.join(orphan)}")
if V:
    for r,w in s_nc[:40]: print("  NC-skill",r,w)
    for n,p,w in h_nc[:40]: print("  NC-hook",n,w)
sys.exit(1 if (S['VIOLA'] or H['VIOLA'] or A['VIOLA'] or dangling or proj_bad) else 0)
```

Salida en `8602ddc70`:

```
SKILLS  total=194  CONFORME=4  NO_CANONICO=189  VIOLA=1
        description sin criterio de CUANDO: 128
        VIOLA: skills/patch-release/SKILL.md :: FRONTMATTER_NO_PARSEA
HOOKS   registrados=200  CONFORME=176  NO_CANONICO=24  VIOLA=0
        proyectados a .claude/settings.json: 162  (gap: 38)
        PROYECCION: UserPromptSubmit[0]: matcher='' en evento que NO acepta matcher
        PROYECCION: Stop[0]: matcher='' en evento que NO acepta matcher
        PROYECCION: TeammateIdle[0]: matcher='' en evento que NO acepta matcher
        PROYECCION: TaskCreated[0]: matcher='' en evento que NO acepta matcher
        PROYECCION: TaskCompleted: clave emitida con 0 grupos
AGENTS  total=1  CONFORME=0  NO_CANONICO=0  VIOLA=1
        VIOLA: agents/test-coverage-enforcer.md :: ubicacion invalida…; campos fuera de spec: triggers
RULES   archivos rules/*.md=129  ref-keys en el indice=138
        ref-keys sin archivo: 10 -> cognitive-os-changes, component-classification,
        component-reality-check, cost-predictor, dogfood-score, dogfooding,
        library-selection, os-vs-project, plan-first, stash-mutation-reversibility
        archivos no citados: 1 -> ROADMAP
EXIT=1
```

**Sin muestreo.** Las 194 skills, los 200 hooks registrados, los 129 archivos de rules y el único subagente se evaluaron completos.

---

## 6. VERIFICADO vs NO VERIFICADO

### VERIFICADO (comando propio, re-corrido en esta sesión)

- 194 `SKILL.md` únicos por `realpath`. Descomposición: 118 directorios reales en `skills/` (uno, `auto-generated/`, sin `SKILL.md`) + 2 anidados a profundidad 3 (`skills/__contracts__/canonical-event-emitter`, `skills/experimental/auto-bash-agent-bash-9c6b89`) + 75 symlinks a `packages/*/skills/`. Ningún `realpath` alcanzable por dos rutas: `find -L skills -name SKILL.md | xargs -I{} readlink -f {} | sort -u | wc -l` = 194 con 0 duplicados. Ningún symlink roto.
- 1 skill con frontmatter que no parsea, con evidencia de impacto en el listado del harness.
- 128/193 descripciones sin criterio de activación (73 con envoltorio circular + 55 sin nada), con el criterio de clasificación declarado y separable.
- 189/194 skills con frontmatter fuera de la spec; `when_to_use` usado 0 veces.
- 0 skills con `description` > 1024 chars (máx 517), 0 con `name` > 64, 0 con body > 500 líneas (máx 369).
- 200 entradas en `cognitive-os.yaml > harness.hooks` sobre 190 scripts únicos; **0** apuntan a archivos inexistentes, **0** sin permiso de ejecución, **0** sin shebang, **0** con evento fuera de la lista de la spec.
- 162 entradas de hook proyectadas a `.claude/settings.json`; gap de 38 respecto del registro, explicado por el filtro de perfil en `scripts/_lib/settings-driver-claude-code.sh` — es una decisión de perfil, no un defecto de conformidad.
- `.claude/skills/` es proyección exacta de `skills/` (`diff <(ls -1 skills) <(ls -1 .claude/skills)` vacío, 0 symlinks colgados).
- 10 ref-keys de `RULES-COMPACT.md` sin archivo (chequeado también contra `packages/*/rules/`).
- `.claude/agents/` sin ningún `.md` cargable.

### Reglas de spec externa aplicadas (fuente + fecha)

Todas fetcheadas el **2026-08-15**:

| # | Regla | Nivel | Fuente |
|---|---|---|---|
| 1 | "Every Skill requires a `SKILL.md` file with YAML frontmatter" | MUST | `platform.claude.com/docs/en/agents-and-tools/agent-skills/overview` |
| 2 | Required fields: `name` y `description` (canal Skills API) | MUST | ídem |
| 3 | `name`: ≤64 chars, solo `[a-z0-9-]`, sin tags XML, sin "anthropic"/"claude" | MUST | ídem + `.../best-practices` |
| 4 | `description`: no vacía, ≤1024 chars | MUST | ídem |
| 5 | "The description must include both what the Skill does and when Claude should use it" | MUST | ídem |
| 6 | Fuera de Claude Code el frontmatter es lista cerrada de 6 campos | MUST | `code.claude.com/docs/en/skills.md`, §"Using skill frontmatter outside Claude Code" |
| 7 | "Keep `SKILL.md` under 500 lines" | SHOULD | ídem + `.../best-practices` |
| 8 | Lista de 31 eventos de hook válidos | MUST | `code.claude.com/docs/en/hooks.md` |
| 9 | Qué eventos aceptan `matcher` y cuáles no | MUST | ídem |
| 10 | Exit 2 bloquea; lista de eventos donde exit 2 no puede bloquear | MUST | ídem |
| 11 | Subagentes: solo `name` y `description` obligatorios; ubicaciones válidas; `model` ∈ {sonnet, opus, haiku, fable, inherit, claude-*} | MUST | `code.claude.com/docs/en/sub-agents.md` |

**Divergencia entre canales, relevante para leer la tabla de §2.** Claude Code y la Skills API no piden lo mismo. Claude Code: *"All fields are optional. Only `description` is recommended so Claude knows when to use the skill."* La Skills API: `name` y `description` obligatorios, lista cerrada de 6 campos. Los MUST de las filas 2-6 rigen si el repo se distribuye fuera de Claude Code; dentro de Claude Code son SHOULD de facto. Por eso `patch-release` es la única VIOLA dura: falla en los dos canales.

### NO VERIFICADO — y no lo afirmo

- **MCP no evaluada.** `mcp-server/` es un solo archivo (`cos_mcp.py`). Verificar conformidad de protocolo exige levantar el server y correr el handshake `initialize` → `notifications/initialized`, y con swap al 97.8% no arranqué procesos. Además quedó abierto cuál es la revisión estable hoy: la doc oficial sirve `2025-06-18` como autoritativa, pero hay señal de una `2025-11-25` posterior sin confirmar. Sin esa base no hay criterio; queda como familia no evaluada.
- **Que las skills se carguen efectivamente.** Verifiqué que el frontmatter parsea, no que el harness las indexe. La única carga observada empíricamente es el listado inyectado en esta sesión (que sí confirma `patch-release`).
- **Que los hooks se disparen.** Verifiqué registro, existencia, permisos, shebang, evento y forma. No ejecuté ninguno ni observé un disparo real. "0 VIOLA en hooks" significa "nada que impida cargarlos", no "los 200 funcionan".
- **Los 12 hooks que no leen stdin.** Confirmé que ni el script ni sus `_lib/` sourceadas hasta 3 niveles tocan stdin. No descarto que reciban el contexto por variable de entorno que el harness exporte y yo no esté mirando; por eso van como NO CANÓNICO y no como VIOLA.
- **Los 12 `PostToolUse` con `exit 2`.** No verifiqué si el autor pretendía bloquear. Si era intencional mostrarle stderr a Claude, son conformes.
- **`name` de subagente: longitud máxima.** No documentada. No se chequeó.
- **`tools` de subagente en formato lista YAML.** La doc solo muestra string con comas; no está documentado que la lista YAML falle. No se chequeó.
- **Que `name` de skill deba coincidir con el directorio.** No es regla: en skills de proyecto y personales, `name` es solo la etiqueta de display y el comando sale del nombre del directorio (`code.claude.com/docs/en/skills.md`). Los 3 casos de `name` ≠ dirname (`caveman-compress`/`compress`, `component-classifier`/`primitive-classifier`, `cost-predictor`/`cost-predict`) **no violan nada** — quedan como NO CANÓNICO por el desfase entre la etiqueta y el comando, que es confusión operativa, no incumplimiento. Confirmado empíricamente: el listado del harness muestra los tres con el nombre del directorio.

---

## 7. Correcciones a las premisas del encargo

| Premisa del encargo | Realidad medida |
|---|---|
| "~117 directorios canónicos con `SKILL.md`" | **119.** 117 a profundidad 2 + 2 anidados a profundidad 3 que un `find -maxdepth 2` no ve. `skills/` tiene 118 directorios reales, uno (`auto-generated/`) sin `SKILL.md` |
| "75 symlinks" | **Correcto.** 75, todos resuelven, 0 rotos, 0 duplicados por `realpath` |
| "257 archivos de hook en disco" | **Correcto** para `hooks/*.sh` de primer nivel (257, de los cuales 42 son symlinks → 255 `realpath` únicos). El total recursivo incluyendo `_lib/` y subdirectorios es 287 `realpath` únicos, de los cuales 32 son librerías de `_lib/`, no hooks |
| "155 registrados" | **200.** `cognitive-os.yaml > harness.hooks` tiene 200 entradas sobre 190 scripts únicos (10 scripts registrados en más de un evento). Los 162 proyectados a `settings.json` tampoco dan 155 |
| "`.claude/settings.json` es generado; el canónico sería `cognitive-os.yaml > harness.hooks`" | **Se sostiene.** El registro es un mapping (no una lista) de `nombre → {script, event, async, scope}`; el driver es `scripts/_lib/settings-driver-claude-code.sh` y aplica un filtro por perfil que explica el gap 200→162 |
| "Los otros jueces se ocupan del inventario" | El inventario había que rehacerlo igual: los cuatro números del brief que toqué, tres estaban mal |

---

## 8. Correcciones al juez anterior (`judge-primitivas-2026-07-28.md`)

- **"Universo real de skills = 192" → 194.** El conteo salió de `find skills -maxdepth 2 -mindepth 2 -name SKILL.md` = 117, que por construcción no ve las dos anidadas a profundidad 3. El propio informe tiene el número correcto en otra tabla ("119 `skills/`", línea 58) y no lo reconcilió con el 192 del veredicto.
- **"0 hooks registrados apuntan a archivos inexistentes" → confirmado, re-corrido.** Sobre 200 entradas (no las que contó él): 0 inexistentes, 0 sin permiso de ejecución, 0 sin shebang. Este es su hallazgo más sólido y se sostiene.
- **"92% de las rules resuelven" → 138 ref-keys, 10 sin archivo = 92.8%.** Consistente. Mi conteo de archivos difiere (129 vs su base) pero la proporción coincide.
- **No hay contradicción con su tesis central** (que el auditor propio del repo mira `lib/` cuando el directorio es `cos_lib/`). No lo re-verifiqué: está fuera de mi lente.
- **Lo que su lente no podía ver, y esta sí:** él midió *si hay algo ejecutable detrás* (REAL/DORMANT/METADATA). Yo mido *si está escrito como la spec lo dicta*. Son ortogonales: `patch-release` tiene implementación y él la habría contado REAL; su `description` no llega al ruteador igual.

---

## 9. Las tres acciones que más conformidad compran por unidad de esfuerzo

**1. Borrar una línea: `skills/patch-release/SKILL.md:1`.**
Un carácter de posición separa a esa skill de ser ruteable. Elimina la única VIOLA dura de la familia más grande.

```bash
head -1 skills/patch-release/SKILL.md | grep -q '^---$' && \
python3 -c "import re,yaml;t=open('skills/patch-release/SKILL.md').read();
m=re.match(r'^---\r?\n(.*?)\r?\n---\r?\n',t,re.S);
print('OK' if m and yaml.safe_load(m.group(1)).get('description') else 'SIGUE ROTO')"
# esperado: OK
```

Vale de paso agregar el guard al `find` que ya existe, para que no vuelva:

```bash
for f in $(find -L skills -name SKILL.md); do head -1 "$f" | grep -q '^<!--' && echo "$f"; done
# esperado: sin salida
```

**2. Mover el subagente a `.claude/agents/`.**
Un `git mv` convierte la única definición de subagente del repo de decorativa en cargable, y de paso corrige un doc que lo daba por vivo (`docs/04-Concepts/architecture/functional-audit/sprint-2a-orphan-fate.md:82`).

```bash
test -f .claude/agents/test-coverage-enforcer.md && \
python3 -c "
import re,yaml;t=open('.claude/agents/test-coverage-enforcer.md').read()
fm=yaml.safe_load(re.match(r'^---\r?\n(.*?)\r?\n---',t,re.S).group(1))
print('OK' if fm.get('name') and fm.get('description') else 'FALTAN CAMPOS')"
# esperado: OK   |   y: find .claude/agents -maxdepth 1 -name '*.md' | wc -l  → 1
```

**3. Reescribir el generador de `description` para que emita el CUÁNDO en vez del envoltorio circular.**
Es la acción de mayor rendimiento del informe: 73 skills se arreglan de una, sin tocar 73 archivos a mano, cambiando el template que las produjo (las que tienen `auto-generated: true` en el frontmatter son 54; el patrón alcanza a 73). Las 55 restantes quedan como trabajo manual acotado y ya están enumeradas por el script con `-v`. Si se quiere el camino más barato aún, `when_to_use` es un campo que Claude Code sí lee y hoy tiene 0 usos: llenarlo en las 128 arregla el ruteo del harness sin tocar `description`.

```bash
python3 conformidad.py . 2>&1 | grep 'sin criterio de CUANDO'
# hoy: 128   |   objetivo tras el cambio de template: ≤ 55
```

Las tres juntas llevan las VIOLA a 0 y bajan el déficit de ruteo a menos de la mitad. Ninguna toca el vocabulario de frontmatter paralelo (189 skills): eso es una decisión de arquitectura — mantener un motor de ruteo propio o converger al del harness — y no una corrección de conformidad. La decide el operador, no este informe.
